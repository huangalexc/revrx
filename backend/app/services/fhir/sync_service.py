"""
FHIR Batch Sync Service
Handles batch synchronization of multiple FHIR encounters from EHR systems
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import structlog

from app.core.database import prisma
from app.core.encryption import encryption_service
from app.services.fhir.fhir_client import FhirClient, FhirAuthType
from app.services.fhir.encounter_service import FhirEncounterService
from app.tasks.fhir_processing import process_fhir_encounter

logger = structlog.get_logger(__name__)


class FhirSyncService:
    """
    Service for batch synchronization of FHIR encounters

    Handles:
    - Querying FHIR API for encounters matching criteria
    - Filtering out already-processed encounters
    - Queueing encounters for background processing
    - Tracking sync progress and statistics
    """

    def __init__(self, fhir_connection_id: str):
        """
        Initialize sync service

        Args:
            fhir_connection_id: FhirConnection ID to use for syncing
        """
        self.fhir_connection_id = fhir_connection_id
        self.fhir_connection = None
        self.fhir_client = None

    async def initialize(self):
        """
        Initialize FHIR client from connection configuration

        Raises:
            ValueError: If connection not found or invalid
        """
        logger.info("initialize_fhir_sync", fhir_connection_id=self.fhir_connection_id)

        # Fetch FHIR connection
        self.fhir_connection = await prisma.fhirconnection.find_unique(
            where={"id": self.fhir_connection_id},
            include={"user": True},
        )

        if not self.fhir_connection:
            raise ValueError(f"FHIR connection not found: {self.fhir_connection_id}")

        if not self.fhir_connection.isActive:
            raise ValueError(f"FHIR connection is inactive: {self.fhir_connection_id}")

        logger.info(
            "fhir_connection_loaded",
            fhir_server_url=self.fhir_connection.fhirServerUrl,
            user_id=self.fhir_connection.userId,
        )

        # Decrypt client secret if present
        client_secret = None
        if self.fhir_connection.clientSecretHash:
            try:
                client_secret = encryption_service.decrypt(self.fhir_connection.clientSecretHash)
            except Exception as e:
                logger.error("failed_to_decrypt_client_secret", error=str(e))
                raise ValueError("Failed to decrypt FHIR client secret")

        # Initialize FHIR client
        self.fhir_client = FhirClient(
            fhir_server_url=self.fhir_connection.fhirServerUrl,
            fhir_version=self.fhir_connection.fhirVersion,
            auth_type=FhirAuthType(self.fhir_connection.authType),
            client_id=self.fhir_connection.clientId,
            client_secret=client_secret,
            token_endpoint=self.fhir_connection.tokenEndpoint,
            scope=self.fhir_connection.scope,
        )

        logger.info("fhir_sync_service_initialized")

    async def sync_encounters(
        self,
        date_range: Optional[Tuple[str, str]] = None,
        patient_ids: Optional[List[str]] = None,
        status: str = "finished",
        limit: Optional[int] = None,
        process_async: bool = True,
    ) -> Dict[str, Any]:
        """
        Sync encounters from FHIR server

        Args:
            date_range: Filter by date range as (start_date, end_date) in ISO format
            patient_ids: Filter by specific patient IDs
            status: Filter by encounter status (default: "finished")
            limit: Maximum number of encounters to sync
            process_async: If True, queue for background processing; if False, process synchronously

        Returns:
            Dictionary with sync results:
            {
                "total_found": int,
                "new": int,
                "skipped": int,
                "queued": int,
                "processed": int,
                "failed": int,
                "encounter_ids": List[str],
                "errors": List[str],
            }

        Raises:
            ValueError: If sync service not initialized
        """
        if not self.fhir_client or not self.fhir_connection:
            raise ValueError("Sync service not initialized. Call initialize() first.")

        logger.info(
            "sync_encounters_started",
            fhir_connection_id=self.fhir_connection_id,
            date_range=date_range,
            patient_ids=patient_ids,
            status=status,
            limit=limit,
        )

        sync_start_time = datetime.utcnow()

        results = {
            "total_found": 0,
            "new": 0,
            "skipped": 0,
            "queued": 0,
            "processed": 0,
            "failed": 0,
            "encounter_ids": [],
            "errors": [],
        }

        try:
            async with self.fhir_client:
                encounter_service = FhirEncounterService(self.fhir_client)

                # If patient_ids provided, sync encounters for each patient
                if patient_ids:
                    for patient_id in patient_ids:
                        patient_results = await self._sync_encounters_for_patient(
                            encounter_service=encounter_service,
                            patient_id=patient_id,
                            date_range=date_range,
                            status=status,
                            limit=limit,
                            process_async=process_async,
                        )

                        # Aggregate results
                        results["total_found"] += patient_results["total_found"]
                        results["new"] += patient_results["new"]
                        results["skipped"] += patient_results["skipped"]
                        results["queued"] += patient_results["queued"]
                        results["processed"] += patient_results["processed"]
                        results["failed"] += patient_results["failed"]
                        results["encounter_ids"].extend(patient_results["encounter_ids"])
                        results["errors"].extend(patient_results["errors"])

                else:
                    # Sync all encounters matching criteria (no patient filter)
                    patient_results = await self._sync_encounters_for_patient(
                        encounter_service=encounter_service,
                        patient_id=None,
                        date_range=date_range,
                        status=status,
                        limit=limit,
                        process_async=process_async,
                    )

                    results = patient_results

            # Update FHIR connection last sync time
            await prisma.fhirconnection.update(
                where={"id": self.fhir_connection_id},
                data={
                    "lastSyncAt": datetime.utcnow(),
                    "lastError": None if len(results["errors"]) == 0 else "; ".join(results["errors"][:3]),
                },
            )

            sync_duration = (datetime.utcnow() - sync_start_time).total_seconds()

            logger.info(
                "sync_encounters_completed",
                fhir_connection_id=self.fhir_connection_id,
                total_found=results["total_found"],
                new=results["new"],
                skipped=results["skipped"],
                queued=results["queued"],
                processed=results["processed"],
                failed=results["failed"],
                duration_seconds=sync_duration,
            )

            return results

        except Exception as e:
            logger.error(
                "sync_encounters_failed",
                fhir_connection_id=self.fhir_connection_id,
                error=str(e),
            )

            # Update FHIR connection with error
            await prisma.fhirconnection.update(
                where={"id": self.fhir_connection_id},
                data={"lastError": str(e)},
            )

            results["errors"].append(str(e))
            return results

    async def _sync_encounters_for_patient(
        self,
        encounter_service: FhirEncounterService,
        patient_id: Optional[str],
        date_range: Optional[Tuple[str, str]],
        status: str,
        limit: Optional[int],
        process_async: bool,
    ) -> Dict[str, Any]:
        """
        Sync encounters for a specific patient (or all patients if None)

        Args:
            encounter_service: FhirEncounterService instance
            patient_id: Patient ID or None for all patients
            date_range: Date range filter
            status: Encounter status filter
            limit: Maximum encounters to fetch
            process_async: Whether to process asynchronously

        Returns:
            Sync results dictionary
        """
        results = {
            "total_found": 0,
            "new": 0,
            "skipped": 0,
            "queued": 0,
            "processed": 0,
            "failed": 0,
            "encounter_ids": [],
            "errors": [],
        }

        try:
            # Fetch encounters from FHIR API
            logger.info(
                "fetch_fhir_encounters",
                patient_id=patient_id,
                date_range=date_range,
                status=status,
            )

            encounters = await encounter_service.fetch_encounters(
                patient_id=patient_id,
                date_range=date_range,
                status=status,
                limit=limit,
            )

            results["total_found"] = len(encounters)

            logger.info(
                "fhir_encounters_fetched",
                patient_id=patient_id,
                encounter_count=len(encounters),
            )

            # Process each encounter
            for fhir_encounter in encounters:
                fhir_encounter_id = fhir_encounter.get("id")

                if not fhir_encounter_id:
                    logger.warning("fhir_encounter_missing_id", encounter=fhir_encounter)
                    results["errors"].append("Encounter missing ID")
                    continue

                # Check if already processed
                existing_encounter = await prisma.encounter.find_unique(
                    where={"fhirEncounterId": fhir_encounter_id},
                )

                if existing_encounter:
                    logger.info(
                        "fhir_encounter_already_processed",
                        fhir_encounter_id=fhir_encounter_id,
                        existing_encounter_id=existing_encounter.id,
                    )
                    results["skipped"] += 1
                    continue

                # New encounter - process it
                results["new"] += 1

                if process_async:
                    # Queue for background processing
                    # TODO: Integrate with Celery or background task queue
                    # For now, we'll process synchronously
                    logger.info(
                        "queue_fhir_encounter_for_processing",
                        fhir_encounter_id=fhir_encounter_id,
                    )
                    results["queued"] += 1

                    # Process synchronously for now (until Celery integration)
                    try:
                        encounter_id = await process_fhir_encounter(
                            fhir_connection_id=self.fhir_connection_id,
                            fhir_encounter_id=fhir_encounter_id,
                            user_id=self.fhir_connection.userId,
                        )

                        if encounter_id:
                            results["processed"] += 1
                            results["encounter_ids"].append(encounter_id)
                            logger.info(
                                "fhir_encounter_processed",
                                fhir_encounter_id=fhir_encounter_id,
                                encounter_id=encounter_id,
                            )
                        else:
                            results["failed"] += 1
                            results["errors"].append(f"Processing failed: {fhir_encounter_id}")

                    except Exception as e:
                        logger.error(
                            "fhir_encounter_processing_error",
                            fhir_encounter_id=fhir_encounter_id,
                            error=str(e),
                        )
                        results["failed"] += 1
                        results["errors"].append(f"{fhir_encounter_id}: {str(e)}")

                else:
                    # Process synchronously
                    try:
                        encounter_id = await process_fhir_encounter(
                            fhir_connection_id=self.fhir_connection_id,
                            fhir_encounter_id=fhir_encounter_id,
                            user_id=self.fhir_connection.userId,
                        )

                        if encounter_id:
                            results["processed"] += 1
                            results["encounter_ids"].append(encounter_id)
                            logger.info(
                                "fhir_encounter_processed",
                                fhir_encounter_id=fhir_encounter_id,
                                encounter_id=encounter_id,
                            )
                        else:
                            results["failed"] += 1
                            results["errors"].append(f"Processing failed: {fhir_encounter_id}")

                    except Exception as e:
                        logger.error(
                            "fhir_encounter_processing_error",
                            fhir_encounter_id=fhir_encounter_id,
                            error=str(e),
                        )
                        results["failed"] += 1
                        results["errors"].append(f"{fhir_encounter_id}: {str(e)}")

        except Exception as e:
            logger.error(
                "sync_encounters_for_patient_failed",
                patient_id=patient_id,
                error=str(e),
            )
            results["errors"].append(str(e))

        return results

    async def get_sync_status(self) -> Dict[str, Any]:
        """
        Get current sync status for this FHIR connection

        Returns:
            Dictionary with sync status:
            {
                "connection_id": str,
                "is_active": bool,
                "last_sync_at": str (ISO),
                "last_error": str or None,
                "total_encounters_synced": int,
            }
        """
        if not self.fhir_connection:
            raise ValueError("Sync service not initialized. Call initialize() first.")

        # Count encounters synced from this connection
        total_synced = await prisma.encounter.count(
            where={
                "fhirSourceSystem": self.fhir_connection.fhirServerUrl,
                "userId": self.fhir_connection.userId,
            }
        )

        return {
            "connection_id": self.fhir_connection_id,
            "is_active": self.fhir_connection.isActive,
            "last_sync_at": self.fhir_connection.lastSyncAt.isoformat() if self.fhir_connection.lastSyncAt else None,
            "last_error": self.fhir_connection.lastError,
            "total_encounters_synced": total_synced,
        }


async def create_sync_service(fhir_connection_id: str) -> FhirSyncService:
    """
    Factory function to create and initialize a FhirSyncService

    Args:
        fhir_connection_id: FhirConnection ID

    Returns:
        Initialized FhirSyncService instance

    Raises:
        ValueError: If connection not found or invalid
    """
    sync_service = FhirSyncService(fhir_connection_id)
    await sync_service.initialize()
    return sync_service
