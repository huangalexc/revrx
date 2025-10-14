"""
Performance tests for bulk upload functionality.

Tests system behavior under load and with varying batch sizes.
"""

import pytest
import asyncio
import io
import time
import uuid
from httpx import AsyncClient
from fastapi import status as http_status
from app.main import app
from app.models.prisma_client import prisma


@pytest.mark.performance
class TestBulkUploadPerformance:
    """Performance tests for bulk upload operations."""

    @pytest.mark.asyncio
    async def test_upload_10_files_performance(self, auth_headers, sample_clinical_note_1):
        """Test performance with 10 files in a batch."""
        async with AsyncClient(app=app, base_url="http://test", timeout=30.0) as client:
            batch_id = str(uuid.uuid4())
            file_count = 10
            start_time = time.time()

            # Upload 10 files
            for i in range(file_count):
                content = sample_clinical_note_1 + f"\nFile number: {i}".encode()
                files = {"file": (f"note_{i}.txt", io.BytesIO(content), "text/plain")}
                data = {"batch_id": batch_id}

                response = await client.post(
                    "/api/v1/encounters/upload-note",
                    files=files,
                    data=data,
                    headers=auth_headers
                )

                assert response.status_code == http_status.HTTP_201_CREATED

            end_time = time.time()
            duration = end_time - start_time

            # Performance assertions
            avg_time_per_file = duration / file_count
            print(f"\n10 files uploaded in {duration:.2f}s")
            print(f"Average time per file: {avg_time_per_file:.2f}s")

            # Should complete within reasonable time (< 30 seconds for 10 files)
            assert duration < 30.0
            assert avg_time_per_file < 3.0

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_upload_50_files_performance(self, auth_headers, sample_clinical_note_1):
        """Test performance with 50 files (recommended batch size limit)."""
        async with AsyncClient(app=app, base_url="http://test", timeout=120.0) as client:
            batch_id = str(uuid.uuid4())
            file_count = 50
            start_time = time.time()

            # Upload 50 files
            for i in range(file_count):
                content = sample_clinical_note_1 + f"\nFile number: {i}".encode()
                files = {"file": (f"note_{i}.txt", io.BytesIO(content), "text/plain")}
                data = {"batch_id": batch_id}

                response = await client.post(
                    "/api/v1/encounters/upload-note",
                    files=files,
                    data=data,
                    headers=auth_headers
                )

                assert response.status_code == http_status.HTTP_201_CREATED

            end_time = time.time()
            duration = end_time - start_time

            # Performance metrics
            avg_time_per_file = duration / file_count
            print(f"\n50 files uploaded in {duration:.2f}s")
            print(f"Average time per file: {avg_time_per_file:.2f}s")

            # Should complete within 2 minutes
            assert duration < 120.0
            assert avg_time_per_file < 2.5

    @pytest.mark.asyncio
    async def test_parallel_upload_performance(self, auth_headers, sample_clinical_note_1):
        """Test performance of parallel file uploads."""
        async with AsyncClient(app=app, base_url="http://test", timeout=30.0) as client:
            batch_id = str(uuid.uuid4())
            file_count = 10

            async def upload_file(index: int):
                content = sample_clinical_note_1 + f"\nFile number: {index}".encode()
                files = {"file": (f"note_{index}.txt", io.BytesIO(content), "text/plain")}
                data = {"batch_id": batch_id}

                response = await client.post(
                    "/api/v1/encounters/upload-note",
                    files=files,
                    data=data,
                    headers=auth_headers
                )
                return response

            # Upload files in parallel
            start_time = time.time()
            tasks = [upload_file(i) for i in range(file_count)]
            responses = await asyncio.gather(*tasks)
            end_time = time.time()

            duration = end_time - start_time

            # Verify all succeeded
            for response in responses:
                assert response.status_code == http_status.HTTP_201_CREATED

            print(f"\n10 files uploaded in parallel in {duration:.2f}s")

            # Parallel should be faster than sequential
            # Should complete in < 10 seconds (vs ~30s sequential)
            assert duration < 10.0

    @pytest.mark.asyncio
    async def test_duplicate_check_performance(self, auth_headers, sample_clinical_note_1):
        """Test duplicate checking performance with many existing files."""
        async with AsyncClient(app=app, base_url="http://test", timeout=30.0) as client:
            # Upload 50 different files first
            for i in range(50):
                content = sample_clinical_note_1 + f"\nUnique file {i}".encode()
                files = {"file": (f"file_{i}.txt", io.BytesIO(content), "text/plain")}
                await client.post(
                    "/api/v1/encounters/upload-note",
                    files=files,
                    headers=auth_headers
                )

            # Now check for duplicate
            start_time = time.time()
            check_files = {"file": ("check.txt", io.BytesIO(sample_clinical_note_1), "text/plain")}
            response = await client.post(
                "/api/v1/encounters/check-duplicate",
                files=check_files,
                headers=auth_headers
            )
            end_time = time.time()

            duration = end_time - start_time

            assert response.status_code == http_status.HTTP_200_OK
            print(f"\nDuplicate check with 50 existing files: {duration:.3f}s")

            # Should be very fast even with many files (< 500ms)
            assert duration < 0.5

    @pytest.mark.asyncio
    async def test_batch_status_query_performance(self, auth_headers, sample_clinical_note_1):
        """Test batch status endpoint performance with large batch."""
        async with AsyncClient(app=app, base_url="http://test", timeout=30.0) as client:
            batch_id = str(uuid.uuid4())

            # Create batch with 20 files
            for i in range(20):
                content = sample_clinical_note_1 + f"\nFile {i}".encode()
                files = {"file": (f"note_{i}.txt", io.BytesIO(content), "text/plain")}
                data = {"batch_id": batch_id}
                await client.post(
                    "/api/v1/encounters/upload-note",
                    files=files,
                    data=data,
                    headers=auth_headers
                )

            # Query batch status
            start_time = time.time()
            response = await client.post(
                f"/api/v1/encounters/batch/{batch_id}/status",
                headers=auth_headers
            )
            end_time = time.time()

            duration = end_time - start_time

            assert response.status_code == http_status.HTTP_200_OK
            result = response.json()
            assert result["total_count"] == 20

            print(f"\nBatch status query for 20 files: {duration:.3f}s")

            # Should be fast (< 1 second)
            assert duration < 1.0

    @pytest.mark.asyncio
    async def test_hash_computation_performance(self, sample_clinical_note_1):
        """Test file hash computation performance."""
        from app.utils.file_hash import compute_file_hash

        # Test with various file sizes
        file_sizes = [
            (1024, "1KB"),
            (10 * 1024, "10KB"),
            (100 * 1024, "100KB"),
            (1024 * 1024, "1MB"),
        ]

        for size, label in file_sizes:
            content = b"X" * size

            start_time = time.time()
            file_hash = compute_file_hash(content)
            end_time = time.time()

            duration = end_time - start_time

            print(f"\nHash computation for {label}: {duration:.4f}s")

            # Should be very fast even for 1MB files (< 100ms)
            assert duration < 0.1
            assert len(file_hash) == 64

    @pytest.mark.asyncio
    async def test_streaming_hash_performance(self):
        """Test streaming hash computation for memory efficiency."""
        from app.utils.file_hash import compute_file_hash_streaming

        # Create 5MB file
        size = 5 * 1024 * 1024
        content = b"X" * size

        start_time = time.time()
        file_obj = io.BytesIO(content)
        file_hash = compute_file_hash_streaming(file_obj)
        end_time = time.time()

        duration = end_time - start_time

        print(f"\nStreaming hash for 5MB file: {duration:.4f}s")

        # Should handle large files efficiently (< 200ms)
        assert duration < 0.2
        assert len(file_hash) == 64


@pytest.mark.performance
class TestConcurrentUserPerformance:
    """Test performance with concurrent users."""

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_concurrent_bulk_uploads(self, sample_clinical_note_1):
        """Test system performance with multiple users uploading simultaneously."""
        async with AsyncClient(app=app, base_url="http://test", timeout=60.0) as client:

            async def user_bulk_upload(user_index: int):
                """Simulate one user uploading 10 files."""
                # Create test user
                user = await prisma.user.create(
                    data={
                        "email": f"perf_test_user_{user_index}@example.com",
                        "firstName": f"User{user_index}",
                        "lastName": "Test",
                        "role": "MEMBER",
                        "isVerified": True
                    }
                )

                from app.utils.auth import create_access_token
                token = create_access_token(data={"sub": user.id, "email": user.email})
                headers = {"Authorization": f"Bearer {token}"}

                batch_id = str(uuid.uuid4())

                # Upload 10 files
                for i in range(10):
                    content = sample_clinical_note_1 + f"\nUser {user_index} File {i}".encode()
                    files = {"file": (f"note_{i}.txt", io.BytesIO(content), "text/plain")}
                    data = {"batch_id": batch_id}

                    await client.post(
                        "/api/v1/encounters/upload-note",
                        files=files,
                        data=data,
                        headers=headers
                    )

                # Cleanup
                await prisma.encounter.delete_many(where={"userId": user.id})
                await prisma.user.delete(where={"id": user.id})

                return user_index

            # Simulate 5 concurrent users
            start_time = time.time()
            tasks = [user_bulk_upload(i) for i in range(5)]
            results = await asyncio.gather(*tasks)
            end_time = time.time()

            duration = end_time - start_time

            print(f"\n5 users uploading 10 files each concurrently: {duration:.2f}s")

            # Should handle concurrent users efficiently (< 60 seconds)
            assert duration < 60.0
            assert len(results) == 5

    @pytest.mark.asyncio
    async def test_database_connection_pool_efficiency(self, auth_headers, sample_clinical_note_1):
        """Test database connection pooling under load."""
        async with AsyncClient(app=app, base_url="http://test", timeout=30.0) as client:

            async def rapid_upload(index: int):
                content = sample_clinical_note_1 + f"\nRapid upload {index}".encode()
                files = {"file": (f"rapid_{index}.txt", io.BytesIO(content), "text/plain")}

                return await client.post(
                    "/api/v1/encounters/upload-note",
                    files=files,
                    headers=auth_headers
                )

            # 20 rapid concurrent requests
            start_time = time.time()
            tasks = [rapid_upload(i) for i in range(20)]
            responses = await asyncio.gather(*tasks)
            end_time = time.time()

            duration = end_time - start_time

            # All should succeed
            for response in responses:
                assert response.status_code == http_status.HTTP_201_CREATED

            print(f"\n20 concurrent uploads: {duration:.2f}s")

            # Should handle efficiently with connection pooling
            assert duration < 15.0


@pytest.mark.performance
class TestMemoryEfficiency:
    """Test memory efficiency of bulk upload operations."""

    @pytest.mark.asyncio
    async def test_large_file_upload_memory(self, auth_headers):
        """Test memory efficiency with large files."""
        # Create 10MB file
        large_content = b"X" * (10 * 1024 * 1024)

        async with AsyncClient(app=app, base_url="http://test", timeout=30.0) as client:
            files = {"file": ("large_note.txt", io.BytesIO(large_content), "text/plain")}

            start_time = time.time()
            response = await client.post(
                "/api/v1/encounters/upload-note",
                files=files,
                headers=auth_headers
            )
            end_time = time.time()

            duration = end_time - start_time

            # Should handle large files without timeout
            assert response.status_code == http_status.HTTP_201_CREATED
            print(f"\n10MB file upload: {duration:.2f}s")

            # Should complete reasonably quickly
            assert duration < 10.0

    @pytest.mark.asyncio
    async def test_batch_processing_memory_footprint(self, auth_headers, sample_clinical_note_1):
        """Test that batch processing doesn't cause memory bloat."""
        async with AsyncClient(app=app, base_url="http://test", timeout=60.0) as client:
            batch_id = str(uuid.uuid4())

            # Process 30 files sequentially
            for i in range(30):
                content = sample_clinical_note_1 + f"\nFile {i}".encode()
                files = {"file": (f"note_{i}.txt", io.BytesIO(content), "text/plain")}
                data = {"batch_id": batch_id}

                response = await client.post(
                    "/api/v1/encounters/upload-note",
                    files=files,
                    data=data,
                    headers=auth_headers
                )

                assert response.status_code == http_status.HTTP_201_CREATED

                # Each file should process independently
                # Memory should be released between uploads

            # Verify all files were processed
            status_response = await client.post(
                f"/api/v1/encounters/batch/{batch_id}/status",
                headers=auth_headers
            )

            result = status_response.json()
            assert result["total_count"] == 30


@pytest.mark.performance
class TestDatabaseQueryOptimization:
    """Test database query performance."""

    @pytest.mark.asyncio
    async def test_duplicate_check_with_index(self, auth_headers, sample_clinical_note_1):
        """Verify duplicate check uses database index efficiently."""
        from app.utils.file_hash import compute_file_hash

        async with AsyncClient(app=app, base_url="http://test", timeout=30.0) as client:
            # Upload 100 files with different hashes
            for i in range(100):
                content = sample_clinical_note_1 + f"\nFile {i}".encode()
                files = {"file": (f"file_{i}.txt", io.BytesIO(content), "text/plain")}
                await client.post(
                    "/api/v1/encounters/upload-note",
                    files=files,
                    headers=auth_headers
                )

            # Check duplicate
            test_content = sample_clinical_note_1 + b"\nFile 50"
            test_hash = compute_file_hash(test_content)

            start_time = time.time()

            # This should use the fileHash index for fast lookup
            check_files = {"file": ("check.txt", io.BytesIO(test_content), "text/plain")}
            response = await client.post(
                "/api/v1/encounters/check-duplicate",
                files=check_files,
                headers=auth_headers
            )

            end_time = time.time()
            duration = end_time - start_time

            # Should be found as duplicate
            result = response.json()
            assert result["is_duplicate"] is True

            print(f"\nDuplicate check with 100 files (indexed): {duration:.3f}s")

            # With proper indexing, should be very fast (< 200ms)
            assert duration < 0.2

    @pytest.mark.asyncio
    async def test_batch_query_optimization(self, auth_headers, sample_clinical_note_1):
        """Test batch status query uses batchId index."""
        async with AsyncClient(app=app, base_url="http://test", timeout=30.0) as client:
            # Create multiple batches
            for batch_num in range(10):
                batch_id = str(uuid.uuid4())

                for file_num in range(10):
                    content = sample_clinical_note_1 + f"\nBatch {batch_num} File {file_num}".encode()
                    files = {"file": (f"note_{file_num}.txt", io.BytesIO(content), "text/plain")}
                    data = {"batch_id": batch_id}

                    await client.post(
                        "/api/v1/encounters/upload-note",
                        files=files,
                        data=data,
                        headers=auth_headers
                    )

                # Query this batch
                start_time = time.time()
                response = await client.post(
                    f"/api/v1/encounters/batch/{batch_id}/status",
                    headers=auth_headers
                )
                end_time = time.time()

                duration = end_time - start_time

                result = response.json()
                assert result["total_count"] == 10

                print(f"\nBatch {batch_num} query with 100 total encounters: {duration:.3f}s")

                # Should be fast with batchId index (< 300ms)
                assert duration < 0.3
