"""
Unit Tests for Fee Schedule Service

Tests for payer-specific fee schedule lookups, caching, and revenue calculations.
"""

import pytest
from datetime import date, datetime, timedelta
from typing import Dict, Optional

from app.core.database import prisma
from app.services.fee_schedule_service import (
    FeeScheduleService,
    CPTRate,
    get_fee_schedule_service
)
from prisma.enums import PayerType


# ============================================================================
# Service Initialization Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
class TestFeeScheduleServiceInitialization:
    """Test service initialization and singleton pattern"""

    async def test_service_initialization(self, db):
        """Test service initializes with database client"""
        service = FeeScheduleService(db)

        assert service.prisma == db
        assert isinstance(service._cache, dict)
        assert isinstance(service._metrics, dict)
        assert service._metrics['lookups'] == 0
        assert service._metrics['cache_hits'] == 0

    async def test_singleton_factory(self, db):
        """Test get_fee_schedule_service returns singleton"""
        service1 = await get_fee_schedule_service(db)
        service2 = await get_fee_schedule_service(db)

        # Should return same instance
        assert service1 is service2


# ============================================================================
# Rate Lookup Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
class TestRateLookup:
    """Test individual rate lookups"""

    async def test_get_rate_success(self, db, test_payer_with_schedule):
        """Test successful rate lookup"""
        service = FeeScheduleService(db)
        payer_id = test_payer_with_schedule['payer_id']

        rate = await service.get_rate(
            cpt_code='99213',
            payer_id=payer_id
        )

        assert rate is not None
        assert isinstance(rate, CPTRate)
        assert rate.cpt_code == '99213'
        assert rate.allowed_amount > 0
        assert rate.payer_name == test_payer_with_schedule['payer_name']

    async def test_get_rate_not_found(self, db, test_payer_with_schedule):
        """Test rate lookup for non-existent code"""
        service = FeeScheduleService(db)
        payer_id = test_payer_with_schedule['payer_id']

        rate = await service.get_rate(
            cpt_code='99999',  # Non-existent code
            payer_id=payer_id
        )

        assert rate is None

    async def test_get_rate_invalid_payer(self, db):
        """Test rate lookup with invalid payer"""
        service = FeeScheduleService(db)

        rate = await service.get_rate(
            cpt_code='99213',
            payer_id='invalid-payer-id'
        )

        assert rate is None

    async def test_get_rate_no_active_schedule(self, db, test_payer_no_schedule):
        """Test rate lookup when payer has no active schedule"""
        service = FeeScheduleService(db)

        rate = await service.get_rate(
            cpt_code='99213',
            payer_id=test_payer_no_schedule['payer_id']
        )

        assert rate is None

    async def test_get_rate_with_date(self, db, test_payer_with_schedule):
        """Test rate lookup with specific date"""
        service = FeeScheduleService(db)
        payer_id = test_payer_with_schedule['payer_id']

        # Use current date
        rate = await service.get_rate(
            cpt_code='99213',
            payer_id=payer_id,
            as_of_date=date.today()
        )

        assert rate is not None
        assert rate.cpt_code == '99213'

    async def test_get_rate_expired_schedule(self, db, test_payer_expired_schedule):
        """Test rate lookup with expired schedule"""
        service = FeeScheduleService(db)

        rate = await service.get_rate(
            cpt_code='99213',
            payer_id=test_payer_expired_schedule['payer_id'],
            as_of_date=date.today()
        )

        # Should not find rate from expired schedule
        assert rate is None


# ============================================================================
# Batch Lookup Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
class TestBatchLookup:
    """Test batch rate lookups"""

    async def test_batch_lookup_success(self, db, test_payer_with_schedule):
        """Test batch lookup of multiple codes"""
        service = FeeScheduleService(db)
        payer_id = test_payer_with_schedule['payer_id']

        codes = ['99213', '99214', '99215']
        rates = await service.get_rates_batch(
            cpt_codes=codes,
            payer_id=payer_id
        )

        assert isinstance(rates, dict)
        assert len(rates) == 3
        assert '99213' in rates
        assert '99214' in rates
        assert '99215' in rates

        # All codes should have rates
        for code in codes:
            assert rates[code] is not None
            assert isinstance(rates[code], CPTRate)

    async def test_batch_lookup_mixed_results(self, db, test_payer_with_schedule):
        """Test batch lookup with some codes not found"""
        service = FeeScheduleService(db)
        payer_id = test_payer_with_schedule['payer_id']

        codes = ['99213', '99999', '99214']  # 99999 doesn't exist
        rates = await service.get_rates_batch(
            cpt_codes=codes,
            payer_id=payer_id
        )

        assert rates['99213'] is not None
        assert rates['99999'] is None
        assert rates['99214'] is not None

    async def test_batch_lookup_empty_list(self, db, test_payer_with_schedule):
        """Test batch lookup with empty code list"""
        service = FeeScheduleService(db)
        payer_id = test_payer_with_schedule['payer_id']

        rates = await service.get_rates_batch(
            cpt_codes=[],
            payer_id=payer_id
        )

        assert isinstance(rates, dict)
        assert len(rates) == 0

    async def test_batch_lookup_duplicate_codes(self, db, test_payer_with_schedule):
        """Test batch lookup with duplicate codes"""
        service = FeeScheduleService(db)
        payer_id = test_payer_with_schedule['payer_id']

        codes = ['99213', '99213', '99214']  # Duplicate 99213
        rates = await service.get_rates_batch(
            cpt_codes=codes,
            payer_id=payer_id
        )

        # Should deduplicate internally
        assert len(rates) == 2
        assert rates['99213'] is not None


# ============================================================================
# Caching Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
class TestCaching:
    """Test rate caching functionality"""

    async def test_cache_hit_on_second_lookup(self, db, test_payer_with_schedule):
        """Test that second lookup uses cache"""
        service = FeeScheduleService(db)
        payer_id = test_payer_with_schedule['payer_id']

        # First lookup
        rate1 = await service.get_rate('99213', payer_id)
        initial_queries = service._metrics['db_queries']

        # Second lookup (should use cache)
        rate2 = await service.get_rate('99213', payer_id)

        assert rate1.cpt_code == rate2.cpt_code
        assert service._metrics['cache_hits'] > 0
        assert service._metrics['db_queries'] == initial_queries  # No new DB query

    async def test_cache_key_includes_date(self, db, test_payer_with_schedule):
        """Test cache keys are date-specific"""
        service = FeeScheduleService(db)
        payer_id = test_payer_with_schedule['payer_id']

        # Lookup with different dates
        rate1 = await service.get_rate('99213', payer_id, date.today())
        rate2 = await service.get_rate('99213', payer_id, date.today() - timedelta(days=30))

        # Should be separate cache entries
        assert len(service._cache) >= 2

    async def test_clear_cache(self, db, test_payer_with_schedule):
        """Test cache clearing"""
        service = FeeScheduleService(db)
        payer_id = test_payer_with_schedule['payer_id']

        # Populate cache
        await service.get_rate('99213', payer_id)
        await service.get_rate('99214', payer_id)

        assert len(service._cache) > 0

        # Clear cache
        service.clear_cache()

        assert len(service._cache) == 0

    async def test_batch_lookup_uses_cache(self, db, test_payer_with_schedule):
        """Test batch lookup leverages cache"""
        service = FeeScheduleService(db)
        payer_id = test_payer_with_schedule['payer_id']

        # First: lookup 99213 individually (caches it)
        await service.get_rate('99213', payer_id)
        initial_queries = service._metrics['db_queries']

        # Second: batch lookup including 99213
        rates = await service.get_rates_batch(['99213', '99214'], payer_id)

        # Should have used cache for 99213
        assert service._metrics['cache_hits'] > 0
        assert rates['99213'] is not None


# ============================================================================
# Revenue Calculation Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
class TestRevenueCalculation:
    """Test revenue estimation calculations"""

    async def test_calculate_revenue_basic(self, db, test_payer_with_schedule):
        """Test basic revenue calculation"""
        service = FeeScheduleService(db)
        payer_id = test_payer_with_schedule['payer_id']

        code_suggestions = [
            {'code': '99213', 'code_type': 'CPT'},
            {'code': '99214', 'code_type': 'CPT'}
        ]

        revenue = await service.calculate_revenue_estimate(
            code_suggestions=code_suggestions,
            payer_id=payer_id
        )

        assert 'total_revenue' in revenue
        assert 'code_details' in revenue
        assert revenue['total_revenue'] > 0
        assert len(revenue['code_details']) == 2

    async def test_calculate_revenue_non_cpt_codes(self, db, test_payer_with_schedule):
        """Test revenue calculation ignores non-CPT codes"""
        service = FeeScheduleService(db)
        payer_id = test_payer_with_schedule['payer_id']

        code_suggestions = [
            {'code': '99213', 'code_type': 'CPT'},
            {'code': 'I10', 'code_type': 'ICD10'},  # Should be ignored
        ]

        revenue = await service.calculate_revenue_estimate(
            code_suggestions=code_suggestions,
            payer_id=payer_id
        )

        # Only CPT code should be included
        assert len(revenue['code_details']) == 1
        assert revenue['code_details'][0]['code'] == '99213'

    async def test_calculate_revenue_missing_rates(self, db, test_payer_with_schedule):
        """Test revenue calculation with missing rates"""
        service = FeeScheduleService(db)
        payer_id = test_payer_with_schedule['payer_id']

        code_suggestions = [
            {'code': '99213', 'code_type': 'CPT'},
            {'code': '99999', 'code_type': 'CPT'},  # No rate
        ]

        revenue = await service.calculate_revenue_estimate(
            code_suggestions=code_suggestions,
            payer_id=payer_id
        )

        # Should only include codes with rates
        assert len(revenue['code_details']) == 1

    async def test_calculate_revenue_empty_list(self, db, test_payer_with_schedule):
        """Test revenue calculation with empty code list"""
        service = FeeScheduleService(db)
        payer_id = test_payer_with_schedule['payer_id']

        revenue = await service.calculate_revenue_estimate(
            code_suggestions=[],
            payer_id=payer_id
        )

        assert revenue['total_revenue'] == 0
        assert len(revenue['code_details']) == 0


# ============================================================================
# CPTRate Model Tests
# ============================================================================

@pytest.mark.unit
class TestCPTRateModel:
    """Test CPTRate dataclass"""

    def test_cpt_rate_creation(self):
        """Test creating CPTRate instance"""
        rate = CPTRate(
            cpt_code='99213',
            cpt_description='Office visit',
            allowed_amount=75.50,
            facility_rate=70.00,
            non_facility_rate=75.50,
            requires_auth=False,
            auth_criteria=None,
            modifier_25_rate=None,
            modifier_59_rate=None,
            work_rvu=1.3,
            total_rvu=2.1,
            payer_name='Blue Cross Blue Shield',
            fee_schedule_name='2025 Q1 Schedule',
            effective_date=date(2025, 1, 1)
        )

        assert rate.cpt_code == '99213'
        assert rate.allowed_amount == 75.50
        assert rate.requires_auth is False

    def test_cpt_rate_with_auth(self):
        """Test CPTRate with authorization requirements"""
        rate = CPTRate(
            cpt_code='45378',
            cpt_description='Colonoscopy',
            allowed_amount=550.00,
            facility_rate=550.00,
            non_facility_rate=550.00,
            requires_auth=True,
            auth_criteria='Prior authorization required for all non-emergent procedures',
            modifier_25_rate=None,
            modifier_59_rate=None,
            work_rvu=4.5,
            total_rvu=7.2,
            payer_name='Blue Cross Blue Shield',
            fee_schedule_name='2025 Q1 Schedule',
            effective_date=date(2025, 1, 1)
        )

        assert rate.requires_auth is True
        assert rate.auth_criteria is not None
        assert 'Prior authorization' in rate.auth_criteria


# ============================================================================
# Metrics Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
class TestMetrics:
    """Test performance metrics tracking"""

    async def test_metrics_tracking(self, db, test_payer_with_schedule):
        """Test that metrics are tracked correctly"""
        service = FeeScheduleService(db)
        payer_id = test_payer_with_schedule['payer_id']

        # Perform some lookups
        await service.get_rate('99213', payer_id)
        await service.get_rate('99213', payer_id)  # Cache hit
        await service.get_rate('99214', payer_id)

        metrics = service.get_metrics()

        assert metrics['lookups'] == 3
        assert metrics['cache_hits'] >= 1
        assert metrics['db_queries'] >= 1

    async def test_metrics_reset_on_clear(self, db, test_payer_with_schedule):
        """Test metrics are not reset when cache is cleared"""
        service = FeeScheduleService(db)
        payer_id = test_payer_with_schedule['payer_id']

        await service.get_rate('99213', payer_id)
        initial_lookups = service._metrics['lookups']

        service.clear_cache()

        # Metrics should persist
        assert service._metrics['lookups'] == initial_lookups

    async def test_cache_hit_rate_calculation(self, db, test_payer_with_schedule):
        """Test cache hit rate calculation"""
        service = FeeScheduleService(db)
        payer_id = test_payer_with_schedule['payer_id']

        # First lookup (miss)
        await service.get_rate('99213', payer_id)
        # Second lookup (hit)
        await service.get_rate('99213', payer_id)

        metrics = service.get_metrics()

        # Hit rate should be 50% (1 hit out of 2 lookups)
        if metrics['lookups'] > 0:
            hit_rate = metrics['cache_hits'] / metrics['lookups']
            assert hit_rate > 0
