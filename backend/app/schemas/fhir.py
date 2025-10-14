"""
FHIR Schemas - Pydantic models for FHIR integration validation
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Tuple
from datetime import datetime
from enum import Enum


class FhirAuthType(str, Enum):
    """FHIR authentication types"""
    OAUTH2 = "OAUTH2"
    BASIC = "BASIC"
    API_KEY = "API_KEY"
    SMART_ON_FHIR = "SMART_ON_FHIR"


class FhirConnectionCreate(BaseModel):
    """Schema for creating a new FHIR connection"""
    fhir_server_url: str = Field(..., min_length=1, max_length=500, description="Base URL of FHIR server")
    fhir_version: str = Field(default="R4", description="FHIR version (R4, R5, etc.)")
    auth_type: FhirAuthType = Field(..., description="Authentication type")

    # OAuth2 / SMART on FHIR fields
    client_id: Optional[str] = Field(None, max_length=255)
    client_secret: Optional[str] = Field(None, max_length=500)
    token_endpoint: Optional[str] = Field(None, max_length=500)
    scope: Optional[str] = Field(None, max_length=500)

    @validator('fhir_server_url')
    def validate_fhir_server_url(cls, v):
        """Validate FHIR server URL format"""
        if not v.startswith(('http://', 'https://')):
            raise ValueError('FHIR server URL must start with http:// or https://')
        return v.rstrip('/')

    @validator('client_secret', 'token_endpoint', 'scope')
    def validate_oauth2_fields(cls, v, values):
        """Validate OAuth2-specific fields are provided when auth_type is OAUTH2 or SMART_ON_FHIR"""
        auth_type = values.get('auth_type')
        if auth_type in (FhirAuthType.OAUTH2, FhirAuthType.SMART_ON_FHIR):
            if not v:
                raise ValueError(f'This field is required for {auth_type} authentication')
        return v


class FhirConnectionUpdate(BaseModel):
    """Schema for updating a FHIR connection"""
    fhir_server_url: Optional[str] = Field(None, min_length=1, max_length=500)
    fhir_version: Optional[str] = None
    auth_type: Optional[FhirAuthType] = None
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    token_endpoint: Optional[str] = None
    scope: Optional[str] = None
    is_active: Optional[bool] = None

    @validator('fhir_server_url')
    def validate_fhir_server_url(cls, v):
        """Validate FHIR server URL format"""
        if v and not v.startswith(('http://', 'https://')):
            raise ValueError('FHIR server URL must start with http:// or https://')
        return v.rstrip('/') if v else v


class FhirConnectionResponse(BaseModel):
    """Schema for FHIR connection response"""
    id: str
    userId: str
    fhirServerUrl: str
    fhirVersion: str
    authType: FhirAuthType
    clientId: Optional[str] = None
    tokenEndpoint: Optional[str] = None
    scope: Optional[str] = None
    isActive: bool
    lastSyncAt: Optional[datetime] = None
    lastError: Optional[str] = None
    createdAt: datetime
    updatedAt: datetime

    class Config:
        from_attributes = True


class FhirConnectionListResponse(BaseModel):
    """Schema for paginated FHIR connection list"""
    connections: List[FhirConnectionResponse]
    total: int


class FhirConnectionTestResponse(BaseModel):
    """Response from testing FHIR connection"""
    success: bool
    message: str
    fhir_version: Optional[str] = None
    server_info: Optional[dict] = None
    error: Optional[str] = None


class FhirEncounterIngestRequest(BaseModel):
    """Request to ingest a single FHIR encounter"""
    fhir_connection_id: str = Field(..., description="FHIR connection ID to use")
    fhir_encounter_id: str = Field(..., description="FHIR Encounter resource ID")


class FhirEncounterIngestResponse(BaseModel):
    """Response from FHIR encounter ingestion"""
    success: bool
    encounter_id: Optional[str] = None
    fhir_encounter_id: str
    status: str
    message: str
    is_duplicate: bool = False


class FhirSyncEncountersRequest(BaseModel):
    """Request to batch sync FHIR encounters"""
    fhir_connection_id: str = Field(..., description="FHIR connection ID to use")
    date_range_start: Optional[str] = Field(None, description="Start date (ISO format: YYYY-MM-DD)")
    date_range_end: Optional[str] = Field(None, description="End date (ISO format: YYYY-MM-DD)")
    patient_ids: Optional[List[str]] = Field(None, description="Optional list of patient IDs to sync")
    status: str = Field(default="finished", description="Encounter status filter")
    limit: Optional[int] = Field(None, gt=0, le=100, description="Maximum encounters to sync (max 100)")

    @validator('date_range_start', 'date_range_end')
    def validate_date_format(cls, v):
        """Validate date is in ISO format"""
        if v:
            try:
                datetime.fromisoformat(v)
            except ValueError:
                raise ValueError('Date must be in ISO format (YYYY-MM-DD)')
        return v


class FhirSyncEncountersResponse(BaseModel):
    """Response from batch FHIR encounter sync"""
    success: bool
    total_found: int
    new: int
    skipped: int
    processed: int
    failed: int
    encounter_ids: List[str]
    errors: List[str]
    message: str


class FhirSyncStatusResponse(BaseModel):
    """Response for FHIR sync status"""
    connection_id: str
    is_active: bool
    last_sync_at: Optional[str] = None
    last_error: Optional[str] = None
    total_encounters_synced: int
