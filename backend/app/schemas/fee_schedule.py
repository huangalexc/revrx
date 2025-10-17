"""
Pydantic schemas for fee schedule API endpoints
"""
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from enum import Enum


class PayerTypeSchema(str, Enum):
    """Payer type enum"""
    COMMERCIAL = "COMMERCIAL"
    MEDICARE = "MEDICARE"
    MEDICAID = "MEDICAID"
    TRICARE = "TRICARE"
    WORKERS_COMP = "WORKERS_COMP"
    SELF_PAY = "SELF_PAY"


class PayerResponse(BaseModel):
    """Response model for payer data"""
    id: str
    name: str
    payer_code: Optional[str] = Field(None, alias="payerCode")
    payer_type: PayerTypeSchema = Field(alias="payerType")
    website: Optional[str] = None
    phone: Optional[str] = None
    is_active: bool = Field(alias="isActive")
    notes: Optional[str] = None
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")

    class Config:
        from_attributes = True
        populate_by_name = True


class FeeScheduleResponse(BaseModel):
    """Response model for fee schedule data"""
    id: str
    payer_id: str = Field(alias="payerId")
    name: str
    description: Optional[str] = None
    effective_date: datetime = Field(alias="effectiveDate")
    expiration_date: Optional[datetime] = Field(None, alias="expirationDate")
    is_active: bool = Field(alias="isActive")
    uploaded_by_user_id: str = Field(alias="uploadedByUserId")
    uploaded_file_name: Optional[str] = Field(None, alias="uploadedFileName")
    uploaded_at: datetime = Field(alias="uploadedAt")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")

    class Config:
        from_attributes = True
        populate_by_name = True


class FeeScheduleRateResponse(BaseModel):
    """Response model for individual rate data"""
    id: str
    fee_schedule_id: str = Field(alias="feeScheduleId")
    cpt_code: str = Field(alias="cptCode")
    cpt_description: Optional[str] = Field(None, alias="cptDescription")
    allowed_amount: float = Field(alias="allowedAmount")
    facility_rate: Optional[float] = Field(None, alias="facilityRate")
    non_facility_rate: Optional[float] = Field(None, alias="nonFacilityRate")
    modifier_25_rate: Optional[float] = Field(None, alias="modifier25Rate")
    modifier_59_rate: Optional[float] = Field(None, alias="modifier59Rate")
    modifier_tc_rate: Optional[float] = Field(None, alias="modifierTCRate")
    modifier_pc_rate: Optional[float] = Field(None, alias="modifierPCRate")
    requires_auth: bool = Field(alias="requiresAuth")
    auth_criteria: Optional[str] = Field(None, alias="authCriteria")
    work_rvu: Optional[float] = Field(None, alias="workRVU")
    practice_rvu: Optional[float] = Field(None, alias="practiceRVU")
    malpractice_rvu: Optional[float] = Field(None, alias="malpracticeRVU")
    total_rvu: Optional[float] = Field(None, alias="totalRVU")
    notes: Optional[str] = None
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")

    class Config:
        from_attributes = True
        populate_by_name = True


class FeeScheduleUploadResponse(BaseModel):
    """Response model for fee schedule upload"""
    fee_schedule_id: str
    payer_id: str
    name: str
    rates_uploaded: int
    invalid_rows: List[str] = []
    status: str
    message: str


class RateDetailResponse(BaseModel):
    """Detailed rate information for revenue calculation"""
    cpt_code: str
    description: Optional[str]
    allowed_amount: float
    estimated_reimbursement: float
    requires_auth: bool
    auth_criteria: Optional[str] = None
    note: Optional[str] = None


class RevenueEstimateResponse(BaseModel):
    """Response model for revenue estimates"""
    total_revenue: float
    code_details: List[RateDetailResponse]
    payer_id: str


class PayerCreateRequest(BaseModel):
    """Request model for creating a payer"""
    name: str
    payer_code: Optional[str] = None
    payer_type: PayerTypeSchema
    website: Optional[str] = None
    phone: Optional[str] = None
    notes: Optional[str] = None


class PayerUpdateRequest(BaseModel):
    """Request model for updating a payer"""
    name: Optional[str] = None
    payer_code: Optional[str] = None
    payer_type: Optional[PayerTypeSchema] = None
    website: Optional[str] = None
    phone: Optional[str] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None
