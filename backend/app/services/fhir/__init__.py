"""
FHIR Integration Services
Handles FHIR API communication and resource processing for EHR integration
"""

from app.services.fhir.fhir_client import FhirClient, FhirAuthType
from app.services.fhir.encounter_service import FhirEncounterService
from app.services.fhir.note_service import FhirNoteService
from app.services.fhir.write_back_service import FhirWriteBackService
from app.services.fhir.sync_service import FhirSyncService, create_sync_service

__all__ = [
    "FhirClient",
    "FhirAuthType",
    "FhirEncounterService",
    "FhirNoteService",
    "FhirWriteBackService",
    "FhirSyncService",
    "create_sync_service",
]
