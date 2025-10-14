"""
Encounter Schemas - Pydantic models for encounter validation
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
from enum import Enum


class EncounterStatus(str, Enum):
    """Encounter processing status"""
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"


class FileType(str, Enum):
    """Supported file types"""
    TXT = "txt"
    PDF = "pdf"
    DOCX = "docx"
    CSV = "csv"
    JSON = "json"


class BillingCodeType(str, Enum):
    """Billing code types"""
    CPT = "CPT"
    ICD10 = "ICD-10"
    HCPCS = "HCPCS"


class BillingCode(BaseModel):
    """Billing code model"""
    code: str = Field(..., min_length=1, max_length=20)
    type: BillingCodeType
    description: Optional[str] = None

    @validator('code')
    def validate_code_format(cls, v, values):
        """Validate code format based on type"""
        if 'type' not in values:
            return v

        code_type = values['type']
        if code_type == BillingCodeType.CPT:
            # CPT codes are 5 digits
            if not v.isdigit() or len(v) != 5:
                raise ValueError('CPT codes must be 5 digits')
        elif code_type == BillingCodeType.ICD10:
            # ICD-10 codes are alphanumeric (A00-Z99)
            if len(v) < 3 or len(v) > 7:
                raise ValueError('ICD-10 codes must be 3-7 characters')
        elif code_type == BillingCodeType.HCPCS:
            # HCPCS codes start with a letter followed by 4 digits
            if len(v) != 5 or not v[0].isalpha() or not v[1:].isdigit():
                raise ValueError('HCPCS codes must be 1 letter followed by 4 digits')

        return v.upper()


class BillingCodesUpload(BaseModel):
    """Request body for billing codes upload"""
    codes: List[BillingCode] = Field(..., min_items=1)


class EncounterCreate(BaseModel):
    """Schema for creating a new encounter"""
    user_id: str = Field(..., description="User ID creating the encounter")
    file_name: str = Field(..., min_length=1, max_length=255)
    file_type: FileType
    file_size: int = Field(..., gt=0, description="File size in bytes")


class EncounterSource(str, Enum):
    """Encounter source"""
    FILE_UPLOAD = "FILE_UPLOAD"
    FHIR = "FHIR"


class EncounterResponse(BaseModel):
    """Schema for encounter response"""
    id: str
    userId: str
    status: EncounterStatus
    processingTime: Optional[int] = None  # milliseconds
    createdAt: datetime
    updatedAt: datetime

    # Optional fields
    patientAge: Optional[int] = None
    patientSex: Optional[str] = None
    visitDate: Optional[datetime] = None
    errorMessage: Optional[str] = None

    # Search/matching metadata
    fileHash: Optional[str] = None
    providerInitials: Optional[str] = None
    dateOfService: Optional[datetime] = None
    encounterType: Optional[str] = None

    # FHIR integration fields
    fhirEncounterId: Optional[str] = None
    fhirPatientId: Optional[str] = None
    fhirProviderId: Optional[str] = None
    fhirSourceSystem: Optional[str] = None
    encounterSource: EncounterSource = EncounterSource.FILE_UPLOAD

    class Config:
        from_attributes = True


class EncounterListResponse(BaseModel):
    """Schema for paginated encounter list"""
    encounters: List[EncounterResponse]
    total: int
    page: int
    page_size: int


class FileUploadResponse(BaseModel):
    """Response after file upload"""
    encounter_id: str
    file_name: str
    file_size: int
    status: str
    message: str


class FileValidationError(BaseModel):
    """File validation error details"""
    field: str
    message: str
    code: str
