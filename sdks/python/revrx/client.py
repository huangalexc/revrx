"""
RevRx Python SDK Client
"""

import httpx
from typing import List, Optional, Dict, Any
from .exceptions import (
    RevRxError,
    AuthenticationError,
    RateLimitError,
    ValidationError,
    NotFoundError,
    ServerError,
)
from .models import Encounter, Report, Webhook, WebhookDelivery, ApiKey


class RevRxClient:
    """
    Official Python client for the Post-Facto Coding Review API

    Example:
        >>> client = RevRxClient(api_key="revx_...")
        >>> encounter = client.encounters.submit({
        ...     "clinical_note": "Patient presents with...",
        ...     "billed_codes": ["99213"]
        ... })
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.revrx.com/api/v1",
        timeout: int = 30,
    ):
        """
        Initialize RevRx client

        Args:
            api_key: Your RevRx API key (starts with "revx_")
            base_url: API base URL (default: production API)
            timeout: Request timeout in seconds (default: 30)
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

        self._client = httpx.Client(
            headers={
                "X-API-Key": api_key,
                "Content-Type": "application/json",
                "User-Agent": "RevRx-Python-SDK/0.1.0",
            },
            timeout=timeout,
        )

        # Initialize resource namespaces
        self.encounters = EncounterResource(self)
        self.reports = ReportResource(self)
        self.webhooks = WebhookResource(self)
        self.api_keys = ApiKeyResource(self)

    def _request(
        self,
        method: str,
        path: str,
        json: Optional[Dict] = None,
        params: Optional[Dict] = None,
        files: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """
        Make HTTP request to API

        Args:
            method: HTTP method
            path: API endpoint path
            json: JSON request body
            params: Query parameters
            files: Files to upload

        Returns:
            Response JSON

        Raises:
            RevRxError: On API errors
        """
        url = f"{self.base_url}{path}"

        try:
            if files:
                # For file uploads, don't send Content-Type header
                headers = {k: v for k, v in self._client.headers.items() if k != "Content-Type"}
                response = self._client.request(
                    method=method,
                    url=url,
                    params=params,
                    files=files,
                    headers=headers,
                )
            else:
                response = self._client.request(
                    method=method,
                    url=url,
                    json=json,
                    params=params,
                )

            # Handle rate limiting
            if response.status_code == 429:
                retry_after = response.headers.get("Retry-After")
                limit = response.headers.get("X-RateLimit-Limit")
                remaining = response.headers.get("X-RateLimit-Remaining")
                reset = response.headers.get("X-RateLimit-Reset")

                raise RateLimitError(
                    "Rate limit exceeded",
                    retry_after=int(retry_after) if retry_after else None,
                    limit=int(limit) if limit else None,
                    remaining=int(remaining) if remaining else None,
                    reset=int(reset) if reset else None,
                )

            # Handle authentication errors
            if response.status_code == 401:
                raise AuthenticationError(
                    "Authentication failed. Check your API key.",
                    status_code=401,
                )

            # Handle not found
            if response.status_code == 404:
                error_detail = response.json().get("detail", "Resource not found")
                raise NotFoundError(error_detail, status_code=404)

            # Handle validation errors
            if response.status_code == 422:
                error_detail = response.json().get("detail", "Validation error")
                raise ValidationError(error_detail, status_code=422, response=response.json())

            # Handle server errors
            if response.status_code >= 500:
                raise ServerError(
                    f"Server error: {response.status_code}",
                    status_code=response.status_code,
                )

            # Handle other client errors
            if 400 <= response.status_code < 500:
                error_detail = response.json().get("detail", "Request failed")
                raise RevRxError(error_detail, status_code=response.status_code)

            # Success - return JSON or empty dict
            if response.status_code == 204:
                return {}

            return response.json()

        except httpx.TimeoutException:
            raise RevRxError(f"Request timeout after {self.timeout}s")
        except httpx.RequestError as e:
            raise RevRxError(f"Request failed: {str(e)}")

    def close(self):
        """Close the HTTP client"""
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class EncounterResource:
    """Encounter API operations"""

    def __init__(self, client: RevRxClient):
        self.client = client

    def submit(
        self,
        clinical_note: str,
        billed_codes: List[Dict[str, str]],
        patient_age: Optional[int] = None,
        patient_sex: Optional[str] = None,
        visit_date: Optional[str] = None,
    ) -> Encounter:
        """
        Submit encounter for analysis

        Args:
            clinical_note: Clinical documentation text
            billed_codes: List of billed codes with type and code
            patient_age: Patient age (optional)
            patient_sex: Patient sex (optional)
            visit_date: Visit date in ISO format (optional)

        Returns:
            Created Encounter object
        """
        data = {
            "clinicalNote": clinical_note,
            "billedCodes": billed_codes,
        }
        if patient_age:
            data["patientAge"] = patient_age
        if patient_sex:
            data["patientSex"] = patient_sex
        if visit_date:
            data["visitDate"] = visit_date

        response = self.client._request("POST", "/integrations/encounters", json=data)
        return Encounter.from_dict(response["encounter"])

    def get(self, encounter_id: str) -> Encounter:
        """Get encounter by ID"""
        response = self.client._request("GET", f"/encounters/{encounter_id}")
        return Encounter.from_dict(response)

    def list(self, limit: int = 50, offset: int = 0) -> List[Encounter]:
        """List encounters"""
        response = self.client._request(
            "GET", "/encounters", params={"limit": limit, "offset": offset}
        )
        return [Encounter.from_dict(e) for e in response["encounters"]]


class ReportResource:
    """Report API operations"""

    def __init__(self, client: RevRxClient):
        self.client = client

    def get(self, encounter_id: str) -> Report:
        """Get report for encounter"""
        response = self.client._request("GET", f"/reports/{encounter_id}")
        return Report.from_dict(response)


class WebhookResource:
    """Webhook API operations"""

    def __init__(self, client: RevRxClient):
        self.client = client

    def create(
        self,
        url: str,
        events: List[str],
        api_key_id: Optional[str] = None,
    ) -> Webhook:
        """
        Create webhook

        Args:
            url: Webhook endpoint URL
            events: List of event types to subscribe to
            api_key_id: Optional API key to associate

        Returns:
            Created Webhook with secret
        """
        data = {"url": url, "events": events}
        if api_key_id:
            data["api_key_id"] = api_key_id

        response = self.client._request("POST", "/webhooks", json=data)
        return Webhook.from_dict(response)

    def list(self) -> List[Webhook]:
        """List webhooks"""
        response = self.client._request("GET", "/webhooks")
        return [Webhook.from_dict(w) for w in response["webhooks"]]

    def get(self, webhook_id: str) -> Webhook:
        """Get webhook by ID"""
        response = self.client._request("GET", f"/webhooks/{webhook_id}")
        return Webhook.from_dict(response)

    def update(
        self,
        webhook_id: str,
        url: Optional[str] = None,
        events: Optional[List[str]] = None,
        is_active: Optional[bool] = None,
    ) -> Webhook:
        """Update webhook"""
        data = {}
        if url:
            data["url"] = url
        if events:
            data["events"] = events
        if is_active is not None:
            data["is_active"] = is_active

        response = self.client._request("PATCH", f"/webhooks/{webhook_id}", json=data)
        return Webhook.from_dict(response)

    def delete(self, webhook_id: str) -> None:
        """Delete webhook"""
        self.client._request("DELETE", f"/webhooks/{webhook_id}")

    def list_deliveries(
        self,
        webhook_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> List[WebhookDelivery]:
        """List webhook deliveries"""
        response = self.client._request(
            "GET",
            f"/webhooks/{webhook_id}/deliveries",
            params={"limit": limit, "offset": offset},
        )
        return [WebhookDelivery.from_dict(d) for d in response["deliveries"]]


class ApiKeyResource:
    """API Key operations"""

    def __init__(self, client: RevRxClient):
        self.client = client

    def create(
        self,
        name: str,
        rate_limit: int = 100,
        expires_in_days: Optional[int] = None,
    ) -> ApiKey:
        """
        Create API key

        Args:
            name: Descriptive name for the key
            rate_limit: Requests per minute limit
            expires_in_days: Optional expiration in days

        Returns:
            Created ApiKey (key is only returned once)
        """
        data = {"name": name, "rate_limit": rate_limit}
        if expires_in_days:
            data["expires_in_days"] = expires_in_days

        response = self.client._request("POST", "/api-keys", json=data)
        return ApiKey.from_dict(response)

    def list(self) -> List[ApiKey]:
        """List API keys"""
        response = self.client._request("GET", "/api-keys")
        return [ApiKey.from_dict(k) for k in response["api_keys"]]

    def get(self, api_key_id: str) -> ApiKey:
        """Get API key by ID"""
        response = self.client._request("GET", f"/api-keys/{api_key_id}")
        return ApiKey.from_dict(response)

    def update(
        self,
        api_key_id: str,
        name: Optional[str] = None,
        is_active: Optional[bool] = None,
        rate_limit: Optional[int] = None,
    ) -> ApiKey:
        """Update API key"""
        data = {}
        if name:
            data["name"] = name
        if is_active is not None:
            data["is_active"] = is_active
        if rate_limit:
            data["rate_limit"] = rate_limit

        response = self.client._request("PATCH", f"/api-keys/{api_key_id}", json=data)
        return ApiKey.from_dict(response)

    def delete(self, api_key_id: str) -> None:
        """Delete API key"""
        self.client._request("DELETE", f"/api-keys/{api_key_id}")
