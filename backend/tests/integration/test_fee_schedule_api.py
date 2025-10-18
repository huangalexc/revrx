"""
Integration Tests for Fee Schedule API Endpoints

Tests for fee schedule upload, listing, and rate retrieval endpoints.
"""

import pytest
from fastapi import status
from datetime import datetime, timedelta
from io import BytesIO
import csv
import io


# ============================================================================
# Fee Schedule Upload Tests
# ============================================================================

@pytest.mark.integration
@pytest.mark.asyncio
class TestFeeScheduleUpload:
    """Test fee schedule CSV upload endpoint"""

    async def test_upload_valid_csv(self, test_client, auth_headers, test_payer_with_schedule, db):
        """Test uploading valid fee schedule CSV"""
        # Create CSV content
        csv_content = """cpt_code,description,allowed_amount,facility_rate,non_facility_rate,requires_auth
99213,Office visit 15 min,75.50,70.00,75.50,false
99214,Office visit 25 min,110.25,105.00,110.25,false
99215,Office visit 40 min,148.00,140.00,148.00,false
45378,Colonoscopy diagnostic,550.00,550.00,550.00,true
"""

        files = {
            "file": ("schedule.csv", BytesIO(csv_content.encode()), "text/csv")
        }

        data = {
            "name": "2025 Q2 Fee Schedule",
            "effective_date": "2025-04-01",
            "expiration_date": "2025-06-30",
            "description": "Test fee schedule for Q2 2025"
        }

        response = await test_client.post(
            f"/api/v1/fee-schedules/{test_payer_with_schedule['payer_id']}/upload",
            headers=auth_headers,
            files=files,
            data=data
        )

        assert response.status_code == status.HTTP_200_OK
        result = response.json()
        assert result["status"] == "success"
        assert result["rates_uploaded"] == 4
        assert len(result["invalid_rows"]) == 0
        assert "fee_schedule_id" in result

    async def test_upload_csv_with_all_optional_fields(self, test_client, auth_headers, test_payer_with_schedule):
        """Test uploading CSV with all optional fields"""
        csv_content = """cpt_code,description,allowed_amount,facility_rate,non_facility_rate,requires_auth,auth_criteria,modifier_25_rate,modifier_59_rate,modifier_tc_rate,modifier_pc_rate,work_rvu,practice_rvu,malpractice_rvu,total_rvu,notes
99213,Office visit,75.50,70.00,75.50,false,,80.00,85.00,,,1.3,1.5,0.2,2.1,Standard E/M
45378,Colonoscopy,550.00,550.00,550.00,true,Prior auth required for screening,,,275.00,275.00,4.5,3.2,1.8,7.2,GI procedure
"""

        files = {
            "file": ("detailed_schedule.csv", BytesIO(csv_content.encode()), "text/csv")
        }

        data = {
            "name": "Detailed Fee Schedule",
            "effective_date": "2025-01-01",
        }

        response = await test_client.post(
            f"/api/v1/fee-schedules/{test_payer_with_schedule['payer_id']}/upload",
            headers=auth_headers,
            files=files,
            data=data
        )

        assert response.status_code == status.HTTP_200_OK
        result = response.json()
        assert result["rates_uploaded"] == 2

    async def test_upload_csv_missing_required_columns(self, test_client, auth_headers, test_payer_with_schedule):
        """Test uploading CSV missing required columns"""
        # Missing 'allowed_amount' column
        csv_content = """cpt_code,description
99213,Office visit
"""

        files = {
            "file": ("invalid.csv", BytesIO(csv_content.encode()), "text/csv")
        }

        data = {
            "name": "Invalid Schedule",
            "effective_date": "2025-01-01"
        }

        response = await test_client.post(
            f"/api/v1/fee-schedules/{test_payer_with_schedule['payer_id']}/upload",
            headers=auth_headers,
            files=files,
            data=data
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "missing required columns" in response.json()["detail"].lower()

    async def test_upload_csv_invalid_cpt_codes(self, test_client, auth_headers, test_payer_with_schedule):
        """Test uploading CSV with invalid CPT codes"""
        csv_content = """cpt_code,description,allowed_amount
123,Too short,75.50
ABCDE,Not numeric,110.25
99213,Valid code,85.00
"""

        files = {
            "file": ("invalid_codes.csv", BytesIO(csv_content.encode()), "text/csv")
        }

        data = {
            "name": "Mixed Valid/Invalid",
            "effective_date": "2025-01-01"
        }

        response = await test_client.post(
            f"/api/v1/fee-schedules/{test_payer_with_schedule['payer_id']}/upload",
            headers=auth_headers,
            files=files,
            data=data
        )

        assert response.status_code == status.HTTP_200_OK
        result = response.json()
        # Only the valid code should be uploaded
        assert result["rates_uploaded"] == 1
        assert len(result["invalid_rows"]) == 2

    async def test_upload_csv_invalid_amounts(self, test_client, auth_headers, test_payer_with_schedule):
        """Test uploading CSV with invalid amounts"""
        csv_content = """cpt_code,description,allowed_amount
99213,Negative amount,-75.50
99214,Zero amount,0
99215,Invalid text,ABC
99211,Valid amount,42.00
"""

        files = {
            "file": ("invalid_amounts.csv", BytesIO(csv_content.encode()), "text/csv")
        }

        data = {
            "name": "Invalid Amounts",
            "effective_date": "2025-01-01"
        }

        response = await test_client.post(
            f"/api/v1/fee-schedules/{test_payer_with_schedule['payer_id']}/upload",
            headers=auth_headers,
            files=files,
            data=data
        )

        assert response.status_code == status.HTTP_200_OK
        result = response.json()
        # Only the valid row should be uploaded
        assert result["rates_uploaded"] == 1
        assert len(result["invalid_rows"]) >= 3

    async def test_upload_csv_no_valid_rows(self, test_client, auth_headers, test_payer_with_schedule):
        """Test uploading CSV with no valid rows"""
        csv_content = """cpt_code,description,allowed_amount
123,Invalid,50.00
ABC,Invalid,75.00
"""

        files = {
            "file": ("no_valid.csv", BytesIO(csv_content.encode()), "text/csv")
        }

        data = {
            "name": "No Valid Rows",
            "effective_date": "2025-01-01"
        }

        response = await test_client.post(
            f"/api/v1/fee-schedules/{test_payer_with_schedule['payer_id']}/upload",
            headers=auth_headers,
            files=files,
            data=data
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "no valid rates" in response.json()["detail"].lower()

    async def test_upload_to_nonexistent_payer(self, test_client, auth_headers):
        """Test uploading to payer that doesn't exist"""
        csv_content = """cpt_code,description,allowed_amount
99213,Office visit,75.50
"""

        files = {
            "file": ("schedule.csv", BytesIO(csv_content.encode()), "text/csv")
        }

        data = {
            "name": "Test Schedule",
            "effective_date": "2025-01-01"
        }

        fake_payer_id = "00000000-0000-0000-0000-000000000000"
        response = await test_client.post(
            f"/api/v1/fee-schedules/{fake_payer_id}/upload",
            headers=auth_headers,
            files=files,
            data=data
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "payer not found" in response.json()["detail"].lower()

    async def test_upload_non_csv_file(self, test_client, auth_headers, test_payer_with_schedule):
        """Test uploading non-CSV file"""
        text_content = b"This is not a CSV file"

        files = {
            "file": ("schedule.txt", BytesIO(text_content), "text/plain")
        }

        data = {
            "name": "Test Schedule",
            "effective_date": "2025-01-01"
        }

        response = await test_client.post(
            f"/api/v1/fee-schedules/{test_payer_with_schedule['payer_id']}/upload",
            headers=auth_headers,
            files=files,
            data=data
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "csv" in response.json()["detail"].lower()

    async def test_upload_without_authentication(self, test_client, test_payer_with_schedule):
        """Test uploading without authentication"""
        csv_content = """cpt_code,description,allowed_amount
99213,Office visit,75.50
"""

        files = {
            "file": ("schedule.csv", BytesIO(csv_content.encode()), "text/csv")
        }

        data = {
            "name": "Test Schedule",
            "effective_date": "2025-01-01"
        }

        response = await test_client.post(
            f"/api/v1/fee-schedules/{test_payer_with_schedule['payer_id']}/upload",
            files=files,
            data=data
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_upload_deactivates_old_schedules(self, test_client, auth_headers, test_payer_with_schedule, db):
        """Test that uploading new schedule deactivates old ones (when no expiration)"""
        # First upload
        csv_content = """cpt_code,description,allowed_amount
99213,Office visit,75.50
"""

        files = {
            "file": ("schedule1.csv", BytesIO(csv_content.encode()), "text/csv")
        }

        data = {
            "name": "First Schedule",
            "effective_date": "2025-01-01"
            # No expiration_date = should deactivate old ones
        }

        response1 = await test_client.post(
            f"/api/v1/fee-schedules/{test_payer_with_schedule['payer_id']}/upload",
            headers=auth_headers,
            files=files,
            data=data
        )

        assert response1.status_code == status.HTTP_200_OK
        schedule1_id = response1.json()["fee_schedule_id"]

        # Second upload (should deactivate first)
        files2 = {
            "file": ("schedule2.csv", BytesIO(csv_content.encode()), "text/csv")
        }

        data2 = {
            "name": "Second Schedule",
            "effective_date": "2025-02-01"
        }

        response2 = await test_client.post(
            f"/api/v1/fee-schedules/{test_payer_with_schedule['payer_id']}/upload",
            headers=auth_headers,
            files=files2,
            data=data2
        )

        assert response2.status_code == status.HTTP_200_OK

        # Verify first schedule is now inactive
        first_schedule = await db.feeschedule.find_unique(where={"id": schedule1_id})
        assert first_schedule.isActive is False

    async def test_upload_with_expiration_keeps_old_active(self, test_client, auth_headers, test_payer_with_schedule, db):
        """Test that uploading with expiration date keeps old schedules active"""
        # First upload with expiration
        csv_content = """cpt_code,description,allowed_amount
99213,Office visit,75.50
"""

        files = {
            "file": ("schedule1.csv", BytesIO(csv_content.encode()), "text/csv")
        }

        data = {
            "name": "Q1 Schedule",
            "effective_date": "2025-01-01",
            "expiration_date": "2025-03-31"
        }

        response1 = await test_client.post(
            f"/api/v1/fee-schedules/{test_payer_with_schedule['payer_id']}/upload",
            headers=auth_headers,
            files=files,
            data=data
        )

        schedule1_id = response1.json()["fee_schedule_id"]

        # Second upload with expiration (different period)
        files2 = {
            "file": ("schedule2.csv", BytesIO(csv_content.encode()), "text/csv")
        }

        data2 = {
            "name": "Q2 Schedule",
            "effective_date": "2025-04-01",
            "expiration_date": "2025-06-30"
        }

        response2 = await test_client.post(
            f"/api/v1/fee-schedules/{test_payer_with_schedule['payer_id']}/upload",
            headers=auth_headers,
            files=files2,
            data=data2
        )

        assert response2.status_code == status.HTTP_200_OK

        # Verify first schedule is still active (different time period)
        first_schedule = await db.feeschedule.find_unique(where={"id": schedule1_id})
        assert first_schedule.isActive is True


# ============================================================================
# Fee Schedule Listing Tests
# ============================================================================

@pytest.mark.integration
@pytest.mark.asyncio
class TestFeeScheduleListing:
    """Test fee schedule listing endpoint"""

    async def test_list_schedules_for_payer(self, test_client, auth_headers, test_payer_with_schedule):
        """Test listing all schedules for a payer"""
        response = await test_client.get(
            f"/api/v1/fee-schedules/{test_payer_with_schedule['payer_id']}/schedules",
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        schedules = response.json()
        assert isinstance(schedules, list)
        assert len(schedules) > 0

        # Verify schedule structure
        schedule = schedules[0]
        assert "id" in schedule
        assert "name" in schedule
        assert "effectiveDate" in schedule
        assert "isActive" in schedule

    async def test_list_active_schedules_only(self, test_client, auth_headers, test_payer_with_schedule, db):
        """Test listing only active schedules"""
        # Create inactive schedule
        await db.feeschedule.create(
            data={
                "payerId": test_payer_with_schedule['payer_id'],
                "name": "Inactive Schedule",
                "effectiveDate": datetime.now() - timedelta(days=365),
                "isActive": False,
                "uploadedByUserId": test_payer_with_schedule['payer'].uploadedByUserId,
                "uploadedFileName": "old.csv"
            }
        )

        # Get active only (default)
        response = await test_client.get(
            f"/api/v1/fee-schedules/{test_payer_with_schedule['payer_id']}/schedules?active_only=true",
            headers=auth_headers
        )

        schedules = response.json()
        # Should only return active schedules
        for schedule in schedules:
            assert schedule["isActive"] is True

    async def test_list_all_schedules_including_inactive(self, test_client, auth_headers, test_payer_with_schedule, db):
        """Test listing all schedules including inactive"""
        # Create inactive schedule
        await db.feeschedule.create(
            data={
                "payerId": test_payer_with_schedule['payer_id'],
                "name": "Inactive Schedule",
                "effectiveDate": datetime.now() - timedelta(days=365),
                "isActive": False,
                "uploadedByUserId": test_payer_with_schedule['payer'].uploadedByUserId,
                "uploadedFileName": "old.csv"
            }
        )

        # Get all (active and inactive)
        response = await test_client.get(
            f"/api/v1/fee-schedules/{test_payer_with_schedule['payer_id']}/schedules?active_only=false",
            headers=auth_headers
        )

        schedules = response.json()
        # Should include both active and inactive
        active_count = sum(1 for s in schedules if s["isActive"])
        inactive_count = sum(1 for s in schedules if not s["isActive"])
        assert inactive_count > 0

    async def test_list_schedules_without_authentication(self, test_client, test_payer_with_schedule):
        """Test listing schedules without authentication"""
        response = await test_client.get(
            f"/api/v1/fee-schedules/{test_payer_with_schedule['payer_id']}/schedules"
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ============================================================================
# Fee Schedule Rate Retrieval Tests
# ============================================================================

@pytest.mark.integration
@pytest.mark.asyncio
class TestFeeScheduleRates:
    """Test fee schedule rate retrieval endpoint"""

    async def test_get_all_rates_for_schedule(self, test_client, auth_headers, test_payer_with_schedule):
        """Test getting all rates for a fee schedule"""
        response = await test_client.get(
            f"/api/v1/fee-schedules/{test_payer_with_schedule['fee_schedule_id']}/rates",
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        rates = response.json()
        assert isinstance(rates, list)
        assert len(rates) > 0

        # Verify rate structure
        rate = rates[0]
        assert "cptCode" in rate
        assert "allowedAmount" in rate
        assert rate["allowedAmount"] > 0

    async def test_get_rates_filtered_by_cpt(self, test_client, auth_headers, test_payer_with_schedule):
        """Test getting rates filtered by specific CPT code"""
        response = await test_client.get(
            f"/api/v1/fee-schedules/{test_payer_with_schedule['fee_schedule_id']}/rates?cpt_code=99213",
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        rates = response.json()

        # Should only return rates for 99213
        if len(rates) > 0:
            for rate in rates:
                assert rate["cptCode"] == "99213"

    async def test_get_rates_for_nonexistent_schedule(self, test_client, auth_headers):
        """Test getting rates for schedule that doesn't exist"""
        fake_schedule_id = "00000000-0000-0000-0000-000000000000"
        response = await test_client.get(
            f"/api/v1/fee-schedules/{fake_schedule_id}/rates",
            headers=auth_headers
        )

        # Should return empty list or 404
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]
        if response.status_code == status.HTTP_200_OK:
            assert len(response.json()) == 0

    async def test_get_rates_without_authentication(self, test_client, test_payer_with_schedule):
        """Test getting rates without authentication"""
        response = await test_client.get(
            f"/api/v1/fee-schedules/{test_payer_with_schedule['fee_schedule_id']}/rates"
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ============================================================================
# Edge Cases and Error Handling
# ============================================================================

@pytest.mark.integration
@pytest.mark.asyncio
class TestFeeScheduleEdgeCases:
    """Test edge cases and error handling"""

    async def test_upload_empty_csv(self, test_client, auth_headers, test_payer_with_schedule):
        """Test uploading empty CSV file"""
        csv_content = """cpt_code,description,allowed_amount
"""

        files = {
            "file": ("empty.csv", BytesIO(csv_content.encode()), "text/csv")
        }

        data = {
            "name": "Empty Schedule",
            "effective_date": "2025-01-01"
        }

        response = await test_client.post(
            f"/api/v1/fee-schedules/{test_payer_with_schedule['payer_id']}/upload",
            headers=auth_headers,
            files=files,
            data=data
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    async def test_upload_malformed_csv(self, test_client, auth_headers, test_payer_with_schedule):
        """Test uploading malformed CSV"""
        csv_content = """cpt_code,allowed_amount
99213,"75.50
99214,110.25
"""  # Missing closing quote

        files = {
            "file": ("malformed.csv", BytesIO(csv_content.encode()), "text/csv")
        }

        data = {
            "name": "Malformed",
            "effective_date": "2025-01-01"
        }

        response = await test_client.post(
            f"/api/v1/fee-schedules/{test_payer_with_schedule['payer_id']}/upload",
            headers=auth_headers,
            files=files,
            data=data
        )

        # Should either handle gracefully or return error
        assert response.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_200_OK]

    async def test_upload_with_invalid_date_format(self, test_client, auth_headers, test_payer_with_schedule):
        """Test uploading with invalid date format"""
        csv_content = """cpt_code,description,allowed_amount
99213,Office visit,75.50
"""

        files = {
            "file": ("schedule.csv", BytesIO(csv_content.encode()), "text/csv")
        }

        data = {
            "name": "Test Schedule",
            "effective_date": "not-a-date"
        }

        response = await test_client.post(
            f"/api/v1/fee-schedules/{test_payer_with_schedule['payer_id']}/upload",
            headers=auth_headers,
            files=files,
            data=data
        )

        assert response.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_422_UNPROCESSABLE_ENTITY]

    async def test_upload_large_csv(self, test_client, auth_headers, test_payer_with_schedule):
        """Test uploading CSV with many rates"""
        # Generate CSV with 1000 rates
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=['cpt_code', 'description', 'allowed_amount'])
        writer.writeheader()

        for i in range(1000):
            writer.writerow({
                'cpt_code': f'{10000 + i:05d}',
                'description': f'Procedure {i}',
                'allowed_amount': f'{50.00 + i:.2f}'
            })

        csv_content = output.getvalue()

        files = {
            "file": ("large.csv", BytesIO(csv_content.encode()), "text/csv")
        }

        data = {
            "name": "Large Schedule",
            "effective_date": "2025-01-01"
        }

        response = await test_client.post(
            f"/api/v1/fee-schedules/{test_payer_with_schedule['payer_id']}/upload",
            headers=auth_headers,
            files=files,
            data=data
        )

        assert response.status_code == status.HTTP_200_OK
        result = response.json()
        assert result["rates_uploaded"] == 1000

    async def test_upload_duplicate_cpt_codes_in_same_file(self, test_client, auth_headers, test_payer_with_schedule):
        """Test uploading CSV with duplicate CPT codes"""
        csv_content = """cpt_code,description,allowed_amount
99213,First entry,75.50
99213,Duplicate entry,80.00
99214,Different code,110.25
"""

        files = {
            "file": ("duplicates.csv", BytesIO(csv_content.encode()), "text/csv")
        }

        data = {
            "name": "Duplicate Codes",
            "effective_date": "2025-01-01"
        }

        response = await test_client.post(
            f"/api/v1/fee-schedules/{test_payer_with_schedule['payer_id']}/upload",
            headers=auth_headers,
            files=files,
            data=data
        )

        # Should handle duplicates (skip_duplicates=True in create_many)
        assert response.status_code == status.HTTP_200_OK
        result = response.json()
        # Either all uploaded or duplicates skipped
        assert result["rates_uploaded"] >= 2
