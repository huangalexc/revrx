"""
FHIR Client Base Service
Handles authentication and HTTP communication with FHIR servers
"""

from typing import Dict, List, Any, Optional
from enum import Enum
import structlog
import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)
from datetime import datetime, timedelta

logger = structlog.get_logger(__name__)


class FhirAuthType(str, Enum):
    """FHIR authentication types"""
    OAUTH2 = "OAUTH2"
    BASIC = "BASIC"
    API_KEY = "API_KEY"
    SMART_ON_FHIR = "SMART_ON_FHIR"


class FhirClientError(Exception):
    """Base exception for FHIR client errors"""
    pass


class FhirAuthenticationError(FhirClientError):
    """FHIR authentication failed"""
    pass


class FhirOperationOutcomeError(FhirClientError):
    """FHIR server returned OperationOutcome error"""
    def __init__(self, message: str, operation_outcome: Dict[str, Any]):
        super().__init__(message)
        self.operation_outcome = operation_outcome


class FhirClient:
    """
    FHIR Client for communicating with FHIR R4/R5 servers

    Supports multiple authentication methods:
    - OAuth2 (Epic, Cerner)
    - SMART on FHIR
    - Basic Auth
    - API Key
    """

    def __init__(
        self,
        fhir_server_url: str,
        fhir_version: str = "R4",
        auth_type: FhirAuthType = FhirAuthType.OAUTH2,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        token_endpoint: Optional[str] = None,
        scope: Optional[str] = None,
        api_key: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        timeout: int = 30,
    ):
        """
        Initialize FHIR client

        Args:
            fhir_server_url: Base URL of FHIR server (e.g., https://fhir.epic.com/interconnect-fhir-oauth)
            fhir_version: FHIR version (R4 or R5)
            auth_type: Authentication method
            client_id: OAuth2/SMART client ID
            client_secret: OAuth2 client secret
            token_endpoint: OAuth2 token endpoint URL
            scope: OAuth2 scopes (space-separated)
            api_key: API key for API_KEY auth
            username: Username for BASIC auth
            password: Password for BASIC auth
            timeout: HTTP request timeout in seconds
        """
        self.fhir_server_url = fhir_server_url.rstrip("/")
        self.fhir_version = fhir_version
        self.auth_type = auth_type
        self.client_id = client_id
        self.client_secret = client_secret
        self.token_endpoint = token_endpoint
        self.scope = scope or "patient/*.read"
        self.api_key = api_key
        self.username = username
        self.password = password
        self.timeout = timeout

        # Token management
        self._access_token: Optional[str] = None
        self._token_expires_at: Optional[datetime] = None

        # HTTP client
        self._http_client: Optional[httpx.AsyncClient] = None

        logger.info(
            "fhir_client_initialized",
            fhir_server_url=fhir_server_url,
            fhir_version=fhir_version,
            auth_type=auth_type.value,
        )

    async def __aenter__(self):
        """Async context manager entry"""
        await self._init_http_client()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()

    async def _init_http_client(self):
        """Initialize HTTP client"""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout),
                follow_redirects=True,
            )

    async def close(self):
        """Close HTTP client"""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None

    async def authenticate(self) -> str:
        """
        Authenticate with FHIR server and get access token

        Returns:
            Access token string

        Raises:
            FhirAuthenticationError: If authentication fails
        """
        if self.auth_type == FhirAuthType.OAUTH2:
            return await self._authenticate_oauth2()
        elif self.auth_type == FhirAuthType.SMART_ON_FHIR:
            return await self._authenticate_smart_on_fhir()
        elif self.auth_type == FhirAuthType.API_KEY:
            # API key doesn't require token exchange
            return self.api_key or ""
        elif self.auth_type == FhirAuthType.BASIC:
            # Basic auth doesn't require token exchange
            return ""
        else:
            raise FhirAuthenticationError(f"Unsupported auth type: {self.auth_type}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(httpx.RequestError),
    )
    async def _authenticate_oauth2(self) -> str:
        """
        Perform OAuth2 client credentials flow

        Returns:
            Access token
        """
        if not self.token_endpoint:
            raise FhirAuthenticationError("token_endpoint required for OAuth2")
        if not self.client_id or not self.client_secret:
            raise FhirAuthenticationError("client_id and client_secret required for OAuth2")

        await self._init_http_client()

        try:
            logger.info("fhir_oauth2_authenticating", token_endpoint=self.token_endpoint)

            response = await self._http_client.post(
                self.token_endpoint,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "scope": self.scope,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            response.raise_for_status()

            token_data = response.json()
            self._access_token = token_data["access_token"]

            # Calculate token expiration (default to 1 hour if not provided)
            expires_in = token_data.get("expires_in", 3600)
            self._token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

            logger.info(
                "fhir_oauth2_authenticated",
                expires_in=expires_in,
                scope=token_data.get("scope"),
            )

            return self._access_token

        except httpx.HTTPStatusError as e:
            logger.error(
                "fhir_oauth2_authentication_failed",
                status_code=e.response.status_code,
                error=str(e),
            )
            raise FhirAuthenticationError(f"OAuth2 authentication failed: {e}")
        except Exception as e:
            logger.error("fhir_oauth2_authentication_error", error=str(e))
            raise FhirAuthenticationError(f"OAuth2 authentication error: {e}")

    async def _authenticate_smart_on_fhir(self) -> str:
        """
        Perform SMART on FHIR authentication
        Similar to OAuth2 but with FHIR-specific scopes and discovery

        Returns:
            Access token
        """
        # SMART on FHIR uses OAuth2 flow with FHIR-specific scopes
        # For client credentials flow, it's essentially the same as OAuth2
        return await self._authenticate_oauth2()

    def _is_token_expired(self) -> bool:
        """Check if access token is expired or will expire soon"""
        if not self._access_token or not self._token_expires_at:
            return True
        # Refresh if token expires in less than 5 minutes
        return datetime.utcnow() >= (self._token_expires_at - timedelta(minutes=5))

    async def _ensure_authenticated(self):
        """Ensure we have a valid access token"""
        if self._is_token_expired():
            await self.authenticate()

    def _get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers based on auth type"""
        headers = {
            "Accept": "application/fhir+json",
            "Content-Type": "application/fhir+json",
        }

        if self.auth_type in (FhirAuthType.OAUTH2, FhirAuthType.SMART_ON_FHIR):
            if self._access_token:
                headers["Authorization"] = f"Bearer {self._access_token}"
        elif self.auth_type == FhirAuthType.API_KEY:
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
        elif self.auth_type == FhirAuthType.BASIC:
            # Basic auth is handled by httpx.BasicAuth
            pass

        return headers

    def _handle_operation_outcome(self, response_data: Dict[str, Any]):
        """
        Handle FHIR OperationOutcome errors

        Raises:
            FhirOperationOutcomeError: If response is an OperationOutcome with errors
        """
        if response_data.get("resourceType") == "OperationOutcome":
            issues = response_data.get("issue", [])
            error_messages = []

            for issue in issues:
                severity = issue.get("severity", "error")
                if severity in ("error", "fatal"):
                    diagnostics = issue.get("diagnostics", "Unknown error")
                    error_messages.append(f"{severity}: {diagnostics}")

            if error_messages:
                raise FhirOperationOutcomeError(
                    "; ".join(error_messages),
                    operation_outcome=response_data,
                )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(httpx.RequestError),
    )
    async def get_resource(self, resource_type: str, resource_id: str) -> Dict[str, Any]:
        """
        Fetch a single FHIR resource by ID

        Args:
            resource_type: FHIR resource type (e.g., "Encounter", "Patient")
            resource_id: Resource ID

        Returns:
            FHIR resource as dict

        Raises:
            FhirClientError: If request fails
        """
        await self._ensure_authenticated()
        await self._init_http_client()

        url = f"{self.fhir_server_url}/{resource_type}/{resource_id}"

        try:
            logger.info(
                "fhir_get_resource",
                resource_type=resource_type,
                resource_id=resource_id,
                url=url,
            )

            auth = None
            if self.auth_type == FhirAuthType.BASIC:
                auth = httpx.BasicAuth(self.username, self.password)

            response = await self._http_client.get(
                url,
                headers=self._get_auth_headers(),
                auth=auth,
            )
            response.raise_for_status()

            resource_data = response.json()
            self._handle_operation_outcome(resource_data)

            logger.info(
                "fhir_get_resource_success",
                resource_type=resource_type,
                resource_id=resource_id,
            )

            return resource_data

        except httpx.HTTPStatusError as e:
            logger.error(
                "fhir_get_resource_failed",
                resource_type=resource_type,
                resource_id=resource_id,
                status_code=e.response.status_code,
                error=str(e),
            )
            raise FhirClientError(f"Failed to get {resource_type}/{resource_id}: {e}")
        except Exception as e:
            logger.error(
                "fhir_get_resource_error",
                resource_type=resource_type,
                resource_id=resource_id,
                error=str(e),
            )
            raise FhirClientError(f"Error getting {resource_type}/{resource_id}: {e}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(httpx.RequestError),
    )
    async def search_resources(
        self,
        resource_type: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search FHIR resources with query parameters

        Args:
            resource_type: FHIR resource type (e.g., "Encounter")
            params: Search parameters (e.g., {"patient": "123", "date": "2024-01-01"})

        Returns:
            List of FHIR resources

        Raises:
            FhirClientError: If search fails
        """
        await self._ensure_authenticated()
        await self._init_http_client()

        url = f"{self.fhir_server_url}/{resource_type}"
        params = params or {}

        try:
            logger.info(
                "fhir_search_resources",
                resource_type=resource_type,
                params=params,
            )

            auth = None
            if self.auth_type == FhirAuthType.BASIC:
                auth = httpx.BasicAuth(self.username, self.password)

            response = await self._http_client.get(
                url,
                params=params,
                headers=self._get_auth_headers(),
                auth=auth,
            )
            response.raise_for_status()

            bundle_data = response.json()
            self._handle_operation_outcome(bundle_data)

            # Extract resources from Bundle
            resources = []
            if bundle_data.get("resourceType") == "Bundle":
                entries = bundle_data.get("entry", [])
                resources = [entry["resource"] for entry in entries if "resource" in entry]

            logger.info(
                "fhir_search_resources_success",
                resource_type=resource_type,
                count=len(resources),
            )

            return resources

        except httpx.HTTPStatusError as e:
            logger.error(
                "fhir_search_resources_failed",
                resource_type=resource_type,
                status_code=e.response.status_code,
                error=str(e),
            )
            raise FhirClientError(f"Failed to search {resource_type}: {e}")
        except Exception as e:
            logger.error(
                "fhir_search_resources_error",
                resource_type=resource_type,
                error=str(e),
            )
            raise FhirClientError(f"Error searching {resource_type}: {e}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(httpx.RequestError),
    )
    async def create_resource(
        self,
        resource_type: str,
        data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Create a new FHIR resource

        Args:
            resource_type: FHIR resource type
            data: FHIR resource data

        Returns:
            Created FHIR resource

        Raises:
            FhirClientError: If creation fails
        """
        await self._ensure_authenticated()
        await self._init_http_client()

        url = f"{self.fhir_server_url}/{resource_type}"

        try:
            logger.info(
                "fhir_create_resource",
                resource_type=resource_type,
            )

            auth = None
            if self.auth_type == FhirAuthType.BASIC:
                auth = httpx.BasicAuth(self.username, self.password)

            response = await self._http_client.post(
                url,
                json=data,
                headers=self._get_auth_headers(),
                auth=auth,
            )
            response.raise_for_status()

            resource_data = response.json()
            self._handle_operation_outcome(resource_data)

            logger.info(
                "fhir_create_resource_success",
                resource_type=resource_type,
                resource_id=resource_data.get("id"),
            )

            return resource_data

        except httpx.HTTPStatusError as e:
            logger.error(
                "fhir_create_resource_failed",
                resource_type=resource_type,
                status_code=e.response.status_code,
                error=str(e),
            )
            raise FhirClientError(f"Failed to create {resource_type}: {e}")
        except Exception as e:
            logger.error(
                "fhir_create_resource_error",
                resource_type=resource_type,
                error=str(e),
            )
            raise FhirClientError(f"Error creating {resource_type}: {e}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(httpx.RequestError),
    )
    async def update_resource(
        self,
        resource_type: str,
        resource_id: str,
        data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Update an existing FHIR resource

        Args:
            resource_type: FHIR resource type
            resource_id: Resource ID
            data: Updated FHIR resource data

        Returns:
            Updated FHIR resource

        Raises:
            FhirClientError: If update fails
        """
        await self._ensure_authenticated()
        await self._init_http_client()

        url = f"{self.fhir_server_url}/{resource_type}/{resource_id}"

        try:
            logger.info(
                "fhir_update_resource",
                resource_type=resource_type,
                resource_id=resource_id,
            )

            auth = None
            if self.auth_type == FhirAuthType.BASIC:
                auth = httpx.BasicAuth(self.username, self.password)

            response = await self._http_client.put(
                url,
                json=data,
                headers=self._get_auth_headers(),
                auth=auth,
            )
            response.raise_for_status()

            resource_data = response.json()
            self._handle_operation_outcome(resource_data)

            logger.info(
                "fhir_update_resource_success",
                resource_type=resource_type,
                resource_id=resource_id,
            )

            return resource_data

        except httpx.HTTPStatusError as e:
            logger.error(
                "fhir_update_resource_failed",
                resource_type=resource_type,
                resource_id=resource_id,
                status_code=e.response.status_code,
                error=str(e),
            )
            raise FhirClientError(f"Failed to update {resource_type}/{resource_id}: {e}")
        except Exception as e:
            logger.error(
                "fhir_update_resource_error",
                resource_type=resource_type,
                resource_id=resource_id,
                error=str(e),
            )
            raise FhirClientError(f"Error updating {resource_type}/{resource_id}: {e}")
