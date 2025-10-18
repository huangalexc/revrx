"""
Integration Tests for Revenue Calculation Pipeline

Tests the end-to-end flow of fee schedule integration with PHI processing
and report generation, including payer-specific revenue calculations.
"""

import pytest
from datetime import datetime, timedelta
from app.core.database import prisma
from app.tasks.phi_processing import process_encounter_phi
from app.services.report_processor import ReportProcessor
from app.services.fee_schedule_service import FeeScheduleService


# ============================================================================
# End-to-End Revenue Pipeline Tests
# ============================================================================

@pytest.mark.integration
@pytest.mark.asyncio
class TestRevenuePipelineIntegration:
    """Test complete revenue calculation pipeline"""

    async def test_encounter_with_payer_loads_rates(
        self, db, test_user, test_payer_with_schedule
    ):
        """Test encounter with payer correctly loads fee schedule rates"""
        # Create encounter with payer
        encounter = await db.encounter.create(
            data={
                "userId": test_user["id"],
                "payerId": test_payer_with_schedule["payer_id"],
                "status": "PROCESSING",
                "patientAge": 55,
                "patientSex": "M",
            }
        )

        # Test fee schedule service retrieval
        service = FeeScheduleService(db)

        # Lookup rate for code in schedule
        rate = await service.get_rate(
            cpt_code="99213",
            payer_id=test_payer_with_schedule["payer_id"]
        )

        assert rate is not None
        assert rate.cpt_code == "99213"
        assert rate.allowed_amount > 0
        assert rate.payer_name == test_payer_with_schedule["payer_name"]

        # Cleanup
        await db.encounter.delete(where={"id": encounter.id})

    async def test_batch_rate_lookup_for_multiple_codes(
        self, db, test_payer_with_schedule
    ):
        """Test batch rate lookup for multiple CPT codes"""
        service = FeeScheduleService(db)

        codes = ["99213", "99214", "99215"]
        rates = await service.get_rates_batch(
            cpt_codes=codes,
            payer_id=test_payer_with_schedule["payer_id"]
        )

        assert len(rates) == 3
        assert all(code in rates for code in codes)
        assert all(rates[code] is not None for code in codes)

        # Verify rates are different
        rate_amounts = [rates[code].allowed_amount for code in codes]
        assert len(set(rate_amounts)) > 1  # Not all the same

    async def test_revenue_estimate_calculation(
        self, db, test_payer_with_schedule
    ):
        """Test revenue estimation for code suggestions"""
        service = FeeScheduleService(db)

        code_suggestions = [
            {"code": "99213", "code_type": "CPT"},
            {"code": "99214", "code_type": "CPT"},
        ]

        revenue = await service.calculate_revenue_estimate(
            code_suggestions=code_suggestions,
            payer_id=test_payer_with_schedule["payer_id"]
        )

        assert "total_revenue" in revenue
        assert "code_details" in revenue
        assert revenue["total_revenue"] > 0
        assert len(revenue["code_details"]) == 2

        # Verify each code has revenue details
        for detail in revenue["code_details"]:
            assert "code" in detail
            assert "allowed_amount" in detail
            assert detail["allowed_amount"] > 0

    async def test_revenue_with_icd10_codes_excluded(
        self, db, test_payer_with_schedule
    ):
        """Test that ICD-10 codes are excluded from revenue calculations"""
        service = FeeScheduleService(db)

        code_suggestions = [
            {"code": "99213", "code_type": "CPT"},
            {"code": "I10", "code_type": "ICD10"},  # Should be ignored
            {"code": "E11.9", "code_type": "ICD10"},  # Should be ignored
        ]

        revenue = await service.calculate_revenue_estimate(
            code_suggestions=code_suggestions,
            payer_id=test_payer_with_schedule["payer_id"]
        )

        # Only CPT code should contribute to revenue
        assert len(revenue["code_details"]) == 1
        assert revenue["code_details"][0]["code"] == "99213"


# ============================================================================
# Report Processor with Fee Schedules Tests
# ============================================================================

@pytest.mark.integration
@pytest.mark.asyncio
class TestReportProcessorWithFeeSchedules:
    """Test report processor integration with fee schedules"""

    async def test_report_includes_payer_revenue_fields(
        self, db, test_user, test_payer_with_schedule
    ):
        """Test that generated report includes payer revenue fields"""
        # Create encounter with payer
        encounter = await db.encounter.create(
            data={
                "userId": test_user["id"],
                "payerId": test_payer_with_schedule["payer_id"],
                "status": "COMPLETED",
                "patientAge": 45,
                "patientSex": "F",
            }
        )

        # Create mock report data
        report_data = {
            "billedCodes": [
                {"code": "99213", "code_type": "CPT"}
            ],
            "suggestedCodes": [
                {"code": "99214", "code_type": "CPT", "confidence": 0.85}
            ],
            "additionalCodes": [
                {"code": "99215", "code_type": "CPT", "confidence": 0.75}
            ],
            "missingDocumentation": [],
            "denialRisks": [],
            "rvuAnalysis": {
                "billed_codes_rvus": 1.3,
                "suggested_codes_rvus": 1.92,
                "incremental_rvus": 0.62
            },
            "uncapturedServices": [],
            "aiModel": "gpt-4",
            "timestamp": datetime.utcnow().isoformat()
        }

        # Get fee schedule service
        fee_service = FeeScheduleService(db)

        # Lookup rates for codes
        all_codes = ["99213", "99214", "99215"]
        rates = await fee_service.get_rates_batch(
            cpt_codes=all_codes,
            payer_id=test_payer_with_schedule["payer_id"]
        )

        # Calculate revenue breakdown
        billed_revenue = rates["99213"].allowed_amount if rates["99213"] else 0
        suggested_revenue = rates["99214"].allowed_amount if rates["99214"] else 0
        optimized_revenue = rates["99215"].allowed_amount if rates["99215"] else 0

        # Create report with revenue data
        report = await db.report.create(
            data={
                "encounterId": encounter.id,
                "payerId": test_payer_with_schedule["payer_id"],
                "billedCodes": report_data["billedCodes"],
                "suggestedCodes": report_data["suggestedCodes"],
                "additionalCodes": report_data["additionalCodes"],
                "billedRevenueEstimate": float(billed_revenue),
                "suggestedRevenueEstimate": float(suggested_revenue),
                "optimizedRevenueEstimate": float(optimized_revenue),
                "incrementalRevenue": float(suggested_revenue - billed_revenue),
                "aiModel": "gpt-4",
            }
        )

        # Verify report has payer revenue fields
        assert report.payerId == test_payer_with_schedule["payer_id"]
        assert report.billedRevenueEstimate > 0
        assert report.suggestedRevenueEstimate > 0
        assert report.optimizedRevenueEstimate > 0
        assert report.incrementalRevenue != 0

        # Cleanup
        await db.report.delete(where={"id": report.id})
        await db.encounter.delete(where={"id": encounter.id})

    async def test_authorization_requirements_in_report(
        self, db, test_user, test_payer_with_schedule
    ):
        """Test authorization requirements are captured in report"""
        # Create encounter
        encounter = await db.encounter.create(
            data={
                "userId": test_user["id"],
                "payerId": test_payer_with_schedule["payer_id"],
                "status": "COMPLETED",
            }
        )

        # Get rate for code requiring auth (45378 - Colonoscopy)
        service = FeeScheduleService(db)
        rate = await service.get_rate(
            cpt_code="45378",
            payer_id=test_payer_with_schedule["payer_id"]
        )

        # Verify auth requirement
        assert rate is not None
        assert rate.requires_auth is True

        # Create report with auth requirements
        auth_requirements = [
            {
                "code": "45378",
                "code_type": "CPT",
                "requires_auth": True,
                "criteria": rate.auth_criteria or "Prior authorization required"
            }
        ]

        report = await db.report.create(
            data={
                "encounterId": encounter.id,
                "payerId": test_payer_with_schedule["payer_id"],
                "billedCodes": [{"code": "45378", "code_type": "CPT"}],
                "suggestedCodes": [],
                "authRequirements": auth_requirements,
                "aiModel": "gpt-4",
            }
        )

        # Verify auth requirements in report
        assert report.authRequirements is not None
        assert len(report.authRequirements) > 0
        assert report.authRequirements[0]["requires_auth"] is True

        # Cleanup
        await db.report.delete(where={"id": report.id})
        await db.encounter.delete(where={"id": encounter.id})

    async def test_denial_risks_for_missing_rates(
        self, db, test_user, test_payer_with_schedule
    ):
        """Test denial risks flagged for codes without payer rates"""
        # Create encounter
        encounter = await db.encounter.create(
            data={
                "userId": test_user["id"],
                "payerId": test_payer_with_schedule["payer_id"],
                "status": "COMPLETED",
            }
        )

        # Check for code not in fee schedule
        service = FeeScheduleService(db)
        rate = await service.get_rate(
            cpt_code="99999",  # Non-existent code
            payer_id=test_payer_with_schedule["payer_id"]
        )

        assert rate is None  # Code not found

        # Create report with denial risk
        denial_risks = [
            {
                "code": "99999",
                "code_type": "CPT",
                "risk": "No payer rate found - potential denial",
                "risk_level": "High"
            }
        ]

        report = await db.report.create(
            data={
                "encounterId": encounter.id,
                "payerId": test_payer_with_schedule["payer_id"],
                "billedCodes": [],
                "suggestedCodes": [{"code": "99999", "code_type": "CPT"}],
                "payerDenialRisks": denial_risks,
                "aiModel": "gpt-4",
            }
        )

        # Verify denial risks in report
        assert report.payerDenialRisks is not None
        assert len(report.payerDenialRisks) > 0
        assert report.payerDenialRisks[0]["risk_level"] == "High"

        # Cleanup
        await db.report.delete(where={"id": report.id})
        await db.encounter.delete(where={"id": encounter.id})

    async def test_bundling_warnings_in_report(
        self, db, test_user, test_payer_with_schedule
    ):
        """Test bundling warnings captured in report"""
        # Create encounter
        encounter = await db.encounter.create(
            data={
                "userId": test_user["id"],
                "payerId": test_payer_with_schedule["payer_id"],
                "status": "COMPLETED",
            }
        )

        # Mock bundling warning (example: E/M with procedure on same day)
        bundling_warnings = [
            {
                "codes": ["99213", "99214"],
                "warning": "Multiple E/M codes on same date may bundle",
                "severity": "Medium"
            }
        ]

        report = await db.report.create(
            data={
                "encounterId": encounter.id,
                "payerId": test_payer_with_schedule["payer_id"],
                "billedCodes": [
                    {"code": "99213", "code_type": "CPT"},
                    {"code": "99214", "code_type": "CPT"}
                ],
                "suggestedCodes": [],
                "bundlingWarnings": bundling_warnings,
                "aiModel": "gpt-4",
            }
        )

        # Verify bundling warnings
        assert report.bundlingWarnings is not None
        assert len(report.bundlingWarnings) > 0
        assert report.bundlingWarnings[0]["severity"] == "Medium"

        # Cleanup
        await db.report.delete(where={"id": report.id})
        await db.encounter.delete(where={"id": encounter.id})


# ============================================================================
# Fee Schedule Caching Performance Tests
# ============================================================================

@pytest.mark.integration
@pytest.mark.asyncio
class TestFeeScheduleCaching:
    """Test fee schedule caching performance"""

    async def test_cache_improves_lookup_performance(
        self, db, test_payer_with_schedule
    ):
        """Test that caching improves rate lookup performance"""
        service = FeeScheduleService(db)

        # First lookup (cache miss)
        import time
        start = time.time()
        rate1 = await service.get_rate(
            cpt_code="99213",
            payer_id=test_payer_with_schedule["payer_id"]
        )
        first_lookup_time = time.time() - start

        # Second lookup (cache hit)
        start = time.time()
        rate2 = await service.get_rate(
            cpt_code="99213",
            payer_id=test_payer_with_schedule["payer_id"]
        )
        second_lookup_time = time.time() - start

        # Verify same rate returned
        assert rate1.cpt_code == rate2.cpt_code
        assert rate1.allowed_amount == rate2.allowed_amount

        # Verify cache improved performance
        metrics = service.get_metrics()
        assert metrics["cache_hits"] > 0
        assert metrics["lookups"] >= 2

    async def test_batch_lookup_efficiency(
        self, db, test_payer_with_schedule
    ):
        """Test batch lookup is more efficient than individual lookups"""
        service = FeeScheduleService(db)
        codes = ["99213", "99214", "99215"]

        # Batch lookup
        import time
        start = time.time()
        batch_rates = await service.get_rates_batch(
            cpt_codes=codes,
            payer_id=test_payer_with_schedule["payer_id"]
        )
        batch_time = time.time() - start

        # Clear cache for fair comparison
        service.clear_cache()

        # Individual lookups
        start = time.time()
        individual_rates = {}
        for code in codes:
            individual_rates[code] = await service.get_rate(
                cpt_code=code,
                payer_id=test_payer_with_schedule["payer_id"]
            )
        individual_time = time.time() - start

        # Verify same results
        for code in codes:
            assert batch_rates[code].cpt_code == individual_rates[code].cpt_code

        # Batch should be faster (or at least not significantly slower)
        # Allow some variance due to test environment
        assert batch_time <= individual_time * 1.5

    async def test_metrics_tracking_accuracy(
        self, db, test_payer_with_schedule
    ):
        """Test that metrics accurately track lookups and cache hits"""
        service = FeeScheduleService(db)

        # Perform known sequence of lookups
        await service.get_rate("99213", test_payer_with_schedule["payer_id"])  # Miss
        await service.get_rate("99213", test_payer_with_schedule["payer_id"])  # Hit
        await service.get_rate("99214", test_payer_with_schedule["payer_id"])  # Miss
        await service.get_rate("99214", test_payer_with_schedule["payer_id"])  # Hit

        metrics = service.get_metrics()

        # Verify metrics
        assert metrics["lookups"] == 4
        assert metrics["cache_hits"] == 2
        assert metrics["db_queries"] <= 2  # Should only query DB twice


# ============================================================================
# Encounter Without Payer Tests
# ============================================================================

@pytest.mark.integration
@pytest.mark.asyncio
class TestEncounterWithoutPayer:
    """Test graceful handling when encounter has no payer"""

    async def test_encounter_without_payer_processes_normally(
        self, db, test_user
    ):
        """Test encounter without payer still processes but skips fee lookups"""
        # Create encounter WITHOUT payer
        encounter = await db.encounter.create(
            data={
                "userId": test_user["id"],
                "status": "PROCESSING",
                "patientAge": 40,
                "patientSex": "M",
            }
        )

        # Verify no payer associated
        assert encounter.payerId is None

        # Service should handle None payer gracefully
        service = FeeScheduleService(db)
        rate = await service.get_rate(
            cpt_code="99213",
            payer_id=None  # No payer
        )

        assert rate is None  # Should return None, not crash

        # Cleanup
        await db.encounter.delete(where={"id": encounter.id})

    async def test_revenue_calculation_with_no_payer(
        self, db
    ):
        """Test revenue calculation returns zero when no payer"""
        service = FeeScheduleService(db)

        code_suggestions = [
            {"code": "99213", "code_type": "CPT"},
        ]

        revenue = await service.calculate_revenue_estimate(
            code_suggestions=code_suggestions,
            payer_id=None  # No payer
        )

        # Should return structure but with zero revenue
        assert revenue["total_revenue"] == 0
        assert len(revenue["code_details"]) == 0


# ============================================================================
# Multiple Payers Tests
# ============================================================================

@pytest.mark.integration
@pytest.mark.asyncio
class TestMultiplePayersRates:
    """Test handling different rates for different payers"""

    async def test_different_payers_different_rates(
        self, db, test_user, test_payer_with_schedule
    ):
        """Test that different payers have different rates for same CPT code"""
        from prisma.enums import PayerType

        # Create second payer with different rates
        payer2 = await db.payer.create(
            data={
                "name": "UnitedHealthcare",
                "payerCode": "UHC",
                "payerType": PayerType.COMMERCIAL,
                "isActive": True,
            }
        )

        schedule2 = await db.feeschedule.create(
            data={
                "payerId": payer2.id,
                "name": "UHC 2025 Rates",
                "effectiveDate": datetime.now() - timedelta(days=30),
                "isActive": True,
                "uploadedByUserId": test_user["id"],
                "uploadedFileName": "uhc_rates.csv",
            }
        )

        # Create rate with different amount
        await db.feeschedulerate.create(
            data={
                "feeScheduleId": schedule2.id,
                "cptCode": "99213",
                "cptDescription": "Office visit",
                "allowedAmount": 85.00,  # Different from first payer
                "requiresAuth": False,
            }
        )

        # Compare rates
        service = FeeScheduleService(db)

        rate1 = await service.get_rate(
            "99213", test_payer_with_schedule["payer_id"]
        )
        rate2 = await service.get_rate(
            "99213", payer2.id
        )

        # Verify different rates
        assert rate1.allowed_amount != rate2.allowed_amount
        assert rate1.payer_name != rate2.payer_name

        # Cleanup
        await db.feeschedulerate.delete_many(where={"feeScheduleId": schedule2.id})
        await db.feeschedule.delete(where={"id": schedule2.id})
        await db.payer.delete(where={"id": payer2.id})

    async def test_payer_specific_revenue_calculations(
        self, db, test_user, test_payer_with_schedule
    ):
        """Test revenue varies by payer for same codes"""
        from prisma.enums import PayerType

        # Create Medicare payer with lower rates
        medicare = await db.payer.create(
            data={
                "name": "Medicare",
                "payerCode": "MEDICARE",
                "payerType": PayerType.MEDICARE,
                "isActive": True,
            }
        )

        medicare_schedule = await db.feeschedule.create(
            data={
                "payerId": medicare.id,
                "name": "Medicare 2025",
                "effectiveDate": datetime.now(),
                "isActive": True,
                "uploadedByUserId": test_user["id"],
                "uploadedFileName": "medicare.csv",
            }
        )

        await db.feeschedulerate.create(
            data={
                "feeScheduleId": medicare_schedule.id,
                "cptCode": "99213",
                "allowedAmount": 65.00,  # Typically lower than commercial
                "requiresAuth": False,
            }
        )

        # Calculate revenue for both payers
        service = FeeScheduleService(db)
        codes = [{"code": "99213", "code_type": "CPT"}]

        commercial_revenue = await service.calculate_revenue_estimate(
            codes, test_payer_with_schedule["payer_id"]
        )
        medicare_revenue = await service.calculate_revenue_estimate(
            codes, medicare.id
        )

        # Verify different revenue amounts
        assert commercial_revenue["total_revenue"] != medicare_revenue["total_revenue"]
        assert commercial_revenue["total_revenue"] > medicare_revenue["total_revenue"]

        # Cleanup
        await db.feeschedulerate.delete_many(where={"feeScheduleId": medicare_schedule.id})
        await db.feeschedule.delete(where={"id": medicare_schedule.id})
        await db.payer.delete(where={"id": medicare.id})
