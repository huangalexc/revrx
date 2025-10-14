"""
RevRx SDK Data Models
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from dataclasses import dataclass


@dataclass
class Encounter:
    """Represents a clinical encounter"""

    id: str
    user_id: str
    status: str
    processing_time: Optional[int] = None
    patient_age: Optional[int] = None
    patient_sex: Optional[str] = None
    visit_date: Optional[datetime] = None
    error_message: Optional[str] = None
    created_at: datetime = None
    updated_at: datetime = None

    @classmethod
    def from_dict(cls, data: dict) -> "Encounter":
        """Create Encounter from API response"""
        return cls(
            id=data["id"],
            user_id=data["userId"],
            status=data["status"],
            processing_time=data.get("processingTime"),
            patient_age=data.get("patientAge"),
            patient_sex=data.get("patientSex"),
            visit_date=datetime.fromisoformat(data["visitDate"]) if data.get("visitDate") else None,
            error_message=data.get("errorMessage"),
            created_at=datetime.fromisoformat(data["createdAt"]) if data.get("createdAt") else None,
            updated_at=datetime.fromisoformat(data["updatedAt"]) if data.get("updatedAt") else None,
        )


@dataclass
class Report:
    """Represents a coding review report"""

    id: str
    encounter_id: str
    billed_codes: List[Dict[str, Any]]
    suggested_codes: List[Dict[str, Any]]
    incremental_revenue: float
    ai_model: str
    confidence_score: Optional[float] = None
    created_at: datetime = None

    @classmethod
    def from_dict(cls, data: dict) -> "Report":
        """Create Report from API response"""
        return cls(
            id=data["id"],
            encounter_id=data["encounterId"],
            billed_codes=data["billedCodes"],
            suggested_codes=data["suggestedCodes"],
            incremental_revenue=data["incrementalRevenue"],
            ai_model=data["aiModel"],
            confidence_score=data.get("confidenceScore"),
            created_at=datetime.fromisoformat(data["createdAt"]) if data.get("createdAt") else None,
        )


@dataclass
class Webhook:
    """Represents a webhook configuration"""

    id: str
    user_id: str
    url: str
    events: List[str]
    is_active: bool
    failure_count: int = 0
    last_success_at: Optional[datetime] = None
    last_failure_at: Optional[datetime] = None
    last_error: Optional[str] = None
    created_at: datetime = None
    updated_at: datetime = None

    @classmethod
    def from_dict(cls, data: dict) -> "Webhook":
        """Create Webhook from API response"""
        return cls(
            id=data["id"],
            user_id=data["userId"],
            url=data["url"],
            events=data["events"],
            is_active=data["isActive"],
            failure_count=data.get("failureCount", 0),
            last_success_at=datetime.fromisoformat(data["lastSuccessAt"]) if data.get("lastSuccessAt") else None,
            last_failure_at=datetime.fromisoformat(data["lastFailureAt"]) if data.get("lastFailureAt") else None,
            last_error=data.get("lastError"),
            created_at=datetime.fromisoformat(data["createdAt"]) if data.get("createdAt") else None,
            updated_at=datetime.fromisoformat(data["updatedAt"]) if data.get("updatedAt") else None,
        )


@dataclass
class WebhookDelivery:
    """Represents a webhook delivery attempt"""

    id: str
    webhook_id: str
    event: str
    status: str
    response_status: Optional[int] = None
    response_time: Optional[int] = None
    error: Optional[str] = None
    attempt_number: int = 1
    created_at: datetime = None
    delivered_at: Optional[datetime] = None

    @classmethod
    def from_dict(cls, data: dict) -> "WebhookDelivery":
        """Create WebhookDelivery from API response"""
        return cls(
            id=data["id"],
            webhook_id=data["webhookId"],
            event=data["event"],
            status=data["status"],
            response_status=data.get("responseStatus"),
            response_time=data.get("responseTime"),
            error=data.get("error"),
            attempt_number=data.get("attemptNumber", 1),
            created_at=datetime.fromisoformat(data["createdAt"]) if data.get("createdAt") else None,
            delivered_at=datetime.fromisoformat(data["deliveredAt"]) if data.get("deliveredAt") else None,
        )


@dataclass
class ApiKey:
    """Represents an API key"""

    id: str
    name: str
    key_prefix: str
    is_active: bool
    rate_limit: int
    usage_count: int
    last_used_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    created_at: datetime = None
    key: Optional[str] = None  # Only present when key is first created

    @classmethod
    def from_dict(cls, data: dict) -> "ApiKey":
        """Create ApiKey from API response"""
        return cls(
            id=data["id"],
            name=data["name"],
            key_prefix=data["keyPrefix"],
            is_active=data["isActive"],
            rate_limit=data["rateLimit"],
            usage_count=data["usageCount"],
            last_used_at=datetime.fromisoformat(data["lastUsedAt"]) if data.get("lastUsedAt") else None,
            expires_at=datetime.fromisoformat(data["expiresAt"]) if data.get("expiresAt") else None,
            created_at=datetime.fromisoformat(data["createdAt"]) if data.get("createdAt") else None,
            key=data.get("key"),  # Only present on creation
        )
