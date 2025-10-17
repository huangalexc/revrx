"""
Fee Schedule Service
Provides payer-specific reimbursement rates for CPT codes
Pattern modeled after SNOMEDCrosswalkService
"""

from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import date, datetime
import structlog

logger = structlog.get_logger(__name__)


@dataclass
class CPTRate:
    """Represents a payer-specific reimbursement rate for a CPT code"""
    cpt_code: str
    cpt_description: Optional[str]
    allowed_amount: float
    facility_rate: Optional[float]
    non_facility_rate: Optional[float]
    requires_auth: bool
    auth_criteria: Optional[str]
    modifier_25_rate: Optional[float]
    modifier_59_rate: Optional[float]
    modifier_tc_rate: Optional[float]
    modifier_pc_rate: Optional[float]
    work_rvu: Optional[float]
    total_rvu: Optional[float]
    payer_name: str
    fee_schedule_name: str
    effective_date: date


class FeeScheduleService:
    """
    Service for looking up payer-specific CPT reimbursement rates
    Similar architecture to SNOMEDCrosswalkService
    """

    def __init__(self, prisma_client):
        self.prisma = prisma_client
        self._cache = {}  # In-memory cache
        self._metrics = {
            'lookups': 0,
            'cache_hits': 0,
            'db_queries': 0
        }

    async def get_active_fee_schedule(
        self,
        payer_id: str,
        as_of_date: Optional[date] = None
    ):
        """
        Get the active fee schedule for a payer

        Args:
            payer_id: Payer ID
            as_of_date: Date to check (defaults to today)

        Returns:
            FeeSchedule record or None
        """
        if as_of_date is None:
            as_of_date = date.today()

        # Convert date to datetime for Prisma query
        as_of_datetime = datetime.combine(as_of_date, datetime.min.time())

        schedule = await self.prisma.feeschedule.find_first(
            where={
                'payerId': payer_id,
                'isActive': True,
                'effectiveDate': {'lte': as_of_datetime},
                'OR': [
                    {'expirationDate': None},
                    {'expirationDate': {'gte': as_of_datetime}}
                ]
            },
            order={'effectiveDate': 'desc'},
            include={'payer': True}
        )

        return schedule

    async def get_rate(
        self,
        cpt_code: str,
        payer_id: str,
        as_of_date: Optional[date] = None
    ) -> Optional[CPTRate]:
        """
        Get reimbursement rate for a CPT code from a specific payer

        Args:
            cpt_code: CPT code (e.g., "99214")
            payer_id: Payer ID
            as_of_date: Date to check (defaults to today)

        Returns:
            CPTRate object or None if not found
        """
        self._metrics['lookups'] += 1

        # Check cache
        cache_key = f"{payer_id}:{cpt_code}:{as_of_date}"
        if cache_key in self._cache:
            self._metrics['cache_hits'] += 1
            return self._cache[cache_key]

        # Get active fee schedule
        fee_schedule = await self.get_active_fee_schedule(payer_id, as_of_date)

        if not fee_schedule:
            logger.warning(
                "No active fee schedule found",
                payer_id=payer_id,
                as_of_date=as_of_date
            )
            self._cache[cache_key] = None
            return None

        # Query rate
        self._metrics['db_queries'] += 1

        rate_record = await self.prisma.feeschedulerate.find_first(
            where={
                'feeScheduleId': fee_schedule.id,
                'cptCode': cpt_code
            }
        )

        if not rate_record:
            logger.info(
                "Rate not found for CPT code",
                cpt_code=cpt_code,
                payer_id=payer_id,
                fee_schedule_id=fee_schedule.id
            )
            self._cache[cache_key] = None
            return None

        # Convert to CPTRate
        rate = CPTRate(
            cpt_code=rate_record.cptCode,
            cpt_description=rate_record.cptDescription,
            allowed_amount=rate_record.allowedAmount,
            facility_rate=rate_record.facilityRate,
            non_facility_rate=rate_record.nonFacilityRate,
            requires_auth=rate_record.requiresAuth,
            auth_criteria=rate_record.authCriteria,
            modifier_25_rate=rate_record.modifier25Rate,
            modifier_59_rate=rate_record.modifier59Rate,
            modifier_tc_rate=rate_record.modifierTCRate,
            modifier_pc_rate=rate_record.modifierPCRate,
            work_rvu=rate_record.workRVU,
            total_rvu=rate_record.totalRVU,
            payer_name=fee_schedule.payer.name,
            fee_schedule_name=fee_schedule.name,
            effective_date=fee_schedule.effectiveDate.date()
        )

        # Cache result
        self._cache[cache_key] = rate

        logger.info(
            "Fee schedule rate lookup",
            cpt_code=cpt_code,
            payer_id=payer_id,
            allowed_amount=rate.allowed_amount,
            requires_auth=rate.requires_auth
        )

        return rate

    async def get_rates_batch(
        self,
        cpt_codes: List[str],
        payer_id: str,
        as_of_date: Optional[date] = None
    ) -> Dict[str, Optional[CPTRate]]:
        """
        Batch lookup of CPT reimbursement rates
        More efficient than individual lookups

        Args:
            cpt_codes: List of CPT codes
            payer_id: Payer ID
            as_of_date: Date to check (defaults to today)

        Returns:
            Dict mapping CPT code → CPTRate (or None if not found)
        """
        self._metrics['lookups'] += len(cpt_codes)

        # Check cache
        results = {}
        uncached_codes = []

        for cpt_code in cpt_codes:
            cache_key = f"{payer_id}:{cpt_code}:{as_of_date}"
            if cache_key in self._cache:
                self._metrics['cache_hits'] += 1
                results[cpt_code] = self._cache[cache_key]
            else:
                uncached_codes.append(cpt_code)

        # Get active fee schedule
        if uncached_codes:
            fee_schedule = await self.get_active_fee_schedule(payer_id, as_of_date)

            if not fee_schedule:
                # No active schedule - return None for all uncached codes
                for cpt_code in uncached_codes:
                    results[cpt_code] = None
                    cache_key = f"{payer_id}:{cpt_code}:{as_of_date}"
                    self._cache[cache_key] = None
                return results

            # Batch query rates
            self._metrics['db_queries'] += 1

            rate_records = await self.prisma.feeschedulerate.find_many(
                where={
                    'feeScheduleId': fee_schedule.id,
                    'cptCode': {'in': uncached_codes}
                }
            )

            # Convert to CPTRate objects
            for rate_record in rate_records:
                rate = CPTRate(
                    cpt_code=rate_record.cptCode,
                    cpt_description=rate_record.cptDescription,
                    allowed_amount=rate_record.allowedAmount,
                    facility_rate=rate_record.facilityRate,
                    non_facility_rate=rate_record.nonFacilityRate,
                    requires_auth=rate_record.requiresAuth,
                    auth_criteria=rate_record.authCriteria,
                    modifier_25_rate=rate_record.modifier25Rate,
                    modifier_59_rate=rate_record.modifier59Rate,
                    modifier_tc_rate=rate_record.modifierTCRate,
                    modifier_pc_rate=rate_record.modifierPCRate,
                    work_rvu=rate_record.workRVU,
                    total_rvu=rate_record.totalRVU,
                    payer_name=fee_schedule.payer.name,
                    fee_schedule_name=fee_schedule.name,
                    effective_date=fee_schedule.effectiveDate.date()
                )

                results[rate_record.cptCode] = rate

                # Cache result
                cache_key = f"{payer_id}:{rate_record.cptCode}:{as_of_date}"
                self._cache[cache_key] = rate

            # Add None for codes not found
            for cpt_code in uncached_codes:
                if cpt_code not in results:
                    results[cpt_code] = None
                    cache_key = f"{payer_id}:{cpt_code}:{as_of_date}"
                    self._cache[cache_key] = None

        logger.info(
            "Fee schedule batch lookup",
            cpt_codes_count=len(cpt_codes),
            rates_found=sum(1 for v in results.values() if v is not None),
            cache_hits=self._metrics['cache_hits']
        )

        return results

    async def calculate_revenue_estimate(
        self,
        code_suggestions: List[Dict],
        payer_id: str
    ) -> Dict:
        """
        Calculate total revenue estimate for suggested codes

        Args:
            code_suggestions: List of code dictionaries with 'code' and 'code_type' fields
            payer_id: Payer ID

        Returns:
            Dict with revenue breakdown
        """
        cpt_codes = [c['code'] for c in code_suggestions if c.get('code_type') == 'CPT']

        if not cpt_codes:
            return {
                'total_revenue': 0.0,
                'code_details': [],
                'payer_id': payer_id
            }

        # Batch lookup rates
        rates = await self.get_rates_batch(cpt_codes, payer_id)

        total_revenue = 0.0
        code_details = []

        for cpt_code in cpt_codes:
            rate = rates.get(cpt_code)

            if rate:
                # Use non-facility rate if available, otherwise allowed amount
                amount = rate.non_facility_rate or rate.allowed_amount
                total_revenue += amount

                code_details.append({
                    'cpt_code': cpt_code,
                    'description': rate.cpt_description,
                    'allowed_amount': rate.allowed_amount,
                    'estimated_reimbursement': amount,
                    'requires_auth': rate.requires_auth,
                    'auth_criteria': rate.auth_criteria
                })
            else:
                # Rate not found - use $0
                code_details.append({
                    'cpt_code': cpt_code,
                    'description': None,
                    'allowed_amount': 0.0,
                    'estimated_reimbursement': 0.0,
                    'requires_auth': False,
                    'auth_criteria': None,
                    'note': 'Rate not found in fee schedule'
                })

        return {
            'total_revenue': round(total_revenue, 2),
            'code_details': code_details,
            'payer_id': payer_id
        }

    def get_metrics(self) -> Dict:
        """Get service performance metrics"""
        return {
            'total_lookups': self._metrics['lookups'],
            'cache_hits': self._metrics['cache_hits'],
            'cache_hit_rate': self._metrics['cache_hits'] / max(self._metrics['lookups'], 1),
            'db_queries': self._metrics['db_queries'],
            'cache_size': len(self._cache)
        }

    def clear_cache(self):
        """Clear the in-memory cache"""
        self._cache.clear()
        logger.info("Fee schedule cache cleared")


# Singleton factory
_fee_schedule_service_instance = None


async def get_fee_schedule_service(prisma_client):
    """Get or create fee schedule service instance"""
    global _fee_schedule_service_instance
    if _fee_schedule_service_instance is None:
        _fee_schedule_service_instance = FeeScheduleService(prisma_client)
    return _fee_schedule_service_instance
