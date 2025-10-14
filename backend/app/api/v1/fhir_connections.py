"""
FHIR Connection Management API Endpoints
Handle FHIR connection configuration and testing
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi import status as http_status
from typing import List
import structlog

from app.schemas.fhir import (
    FhirConnectionCreate,
    FhirConnectionUpdate,
    FhirConnectionResponse,
    FhirConnectionListResponse,
    FhirConnectionTestResponse,
    FhirAuthType,
)
from app.core.deps import get_current_user
from app.core.database import prisma
from app.core.encryption import encryption_service
from app.services.fhir.fhir_client import FhirClient

router = APIRouter(prefix="/fhir-connections", tags=["fhir-connections"])
logger = structlog.get_logger(__name__)


@router.post("", response_model=FhirConnectionResponse, status_code=http_status.HTTP_201_CREATED)
async def create_fhir_connection(
    connection_data: FhirConnectionCreate,
    user = Depends(get_current_user)
):
    """
    Create a new FHIR connection

    - Validates connection configuration
    - Encrypts client secret before storage
    - Returns connection details (without secrets)
    """
    try:
        logger.info(
            "create_fhir_connection",
            user_id=user.id,
            fhir_server_url=connection_data.fhir_server_url,
            auth_type=connection_data.auth_type,
        )

        # Encrypt client secret if provided
        client_secret_hash = None
        if connection_data.client_secret:
            client_secret_hash = encryption_service.encrypt(connection_data.client_secret)

        # Create FHIR connection in database
        connection = await prisma.fhirconnection.create(
            data={
                "userId": user.id,
                "fhirServerUrl": connection_data.fhir_server_url,
                "fhirVersion": connection_data.fhir_version,
                "authType": connection_data.auth_type.value,
                "clientId": connection_data.client_id,
                "clientSecretHash": client_secret_hash,
                "tokenEndpoint": connection_data.token_endpoint,
                "scope": connection_data.scope,
                "isActive": True,
            }
        )

        logger.info(
            "fhir_connection_created",
            connection_id=connection.id,
            user_id=user.id,
        )

        return connection

    except Exception as e:
        logger.error(
            "create_fhir_connection_failed",
            user_id=user.id,
            error=str(e),
        )
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create FHIR connection: {str(e)}",
        )


@router.get("", response_model=FhirConnectionListResponse)
async def list_fhir_connections(
    user = Depends(get_current_user)
):
    """
    List all FHIR connections for the current user

    - Returns list of connections (without secrets)
    - Ordered by creation date (newest first)
    """
    try:
        logger.info("list_fhir_connections", user_id=user.id)

        connections = await prisma.fhirconnection.find_many(
            where={"userId": user.id},
            order={"createdAt": "desc"},
        )

        logger.info(
            "fhir_connections_listed",
            user_id=user.id,
            count=len(connections),
        )

        return {
            "connections": connections,
            "total": len(connections),
        }

    except Exception as e:
        logger.error(
            "list_fhir_connections_failed",
            user_id=user.id,
            error=str(e),
        )
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list FHIR connections: {str(e)}",
        )


@router.get("/{connection_id}", response_model=FhirConnectionResponse)
async def get_fhir_connection(
    connection_id: str,
    user = Depends(get_current_user)
):
    """
    Get a specific FHIR connection by ID

    - Returns connection details (without secrets)
    - Validates user owns the connection
    """
    try:
        logger.info(
            "get_fhir_connection",
            connection_id=connection_id,
            user_id=user.id,
        )

        connection = await prisma.fhirconnection.find_unique(
            where={"id": connection_id},
        )

        if not connection:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail="FHIR connection not found",
            )

        # Verify user owns this connection
        if connection.userId != user.id:
            raise HTTPException(
                status_code=http_status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to access this FHIR connection",
            )

        logger.info(
            "fhir_connection_retrieved",
            connection_id=connection_id,
            user_id=user.id,
        )

        return connection

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "get_fhir_connection_failed",
            connection_id=connection_id,
            user_id=user.id,
            error=str(e),
        )
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve FHIR connection: {str(e)}",
        )


@router.put("/{connection_id}", response_model=FhirConnectionResponse)
async def update_fhir_connection(
    connection_id: str,
    update_data: FhirConnectionUpdate,
    user = Depends(get_current_user)
):
    """
    Update a FHIR connection

    - Validates user owns the connection
    - Encrypts new client secret if provided
    - Returns updated connection (without secrets)
    """
    try:
        logger.info(
            "update_fhir_connection",
            connection_id=connection_id,
            user_id=user.id,
        )

        # Fetch existing connection
        connection = await prisma.fhirconnection.find_unique(
            where={"id": connection_id},
        )

        if not connection:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail="FHIR connection not found",
            )

        # Verify user owns this connection
        if connection.userId != user.id:
            raise HTTPException(
                status_code=http_status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to update this FHIR connection",
            )

        # Build update dict (only include provided fields)
        update_dict = {}

        if update_data.fhir_server_url is not None:
            update_dict["fhirServerUrl"] = update_data.fhir_server_url

        if update_data.fhir_version is not None:
            update_dict["fhirVersion"] = update_data.fhir_version

        if update_data.auth_type is not None:
            update_dict["authType"] = update_data.auth_type.value

        if update_data.client_id is not None:
            update_dict["clientId"] = update_data.client_id

        if update_data.client_secret is not None:
            # Encrypt new client secret
            update_dict["clientSecretHash"] = encryption_service.encrypt(update_data.client_secret)

        if update_data.token_endpoint is not None:
            update_dict["tokenEndpoint"] = update_data.token_endpoint

        if update_data.scope is not None:
            update_dict["scope"] = update_data.scope

        if update_data.is_active is not None:
            update_dict["isActive"] = update_data.is_active

        # Update connection
        updated_connection = await prisma.fhirconnection.update(
            where={"id": connection_id},
            data=update_dict,
        )

        logger.info(
            "fhir_connection_updated",
            connection_id=connection_id,
            user_id=user.id,
        )

        return updated_connection

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "update_fhir_connection_failed",
            connection_id=connection_id,
            user_id=user.id,
            error=str(e),
        )
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update FHIR connection: {str(e)}",
        )


@router.delete("/{connection_id}", status_code=http_status.HTTP_204_NO_CONTENT)
async def delete_fhir_connection(
    connection_id: str,
    user = Depends(get_current_user)
):
    """
    Delete a FHIR connection

    - Validates user owns the connection
    - Permanently deletes the connection
    """
    try:
        logger.info(
            "delete_fhir_connection",
            connection_id=connection_id,
            user_id=user.id,
        )

        # Fetch connection
        connection = await prisma.fhirconnection.find_unique(
            where={"id": connection_id},
        )

        if not connection:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail="FHIR connection not found",
            )

        # Verify user owns this connection
        if connection.userId != user.id:
            raise HTTPException(
                status_code=http_status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to delete this FHIR connection",
            )

        # Delete connection
        await prisma.fhirconnection.delete(
            where={"id": connection_id},
        )

        logger.info(
            "fhir_connection_deleted",
            connection_id=connection_id,
            user_id=user.id,
        )

        return None

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "delete_fhir_connection_failed",
            connection_id=connection_id,
            user_id=user.id,
            error=str(e),
        )
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete FHIR connection: {str(e)}",
        )


@router.post("/{connection_id}/test", response_model=FhirConnectionTestResponse)
async def test_fhir_connection(
    connection_id: str,
    user = Depends(get_current_user)
):
    """
    Test a FHIR connection

    - Validates user owns the connection
    - Attempts to authenticate with FHIR server
    - Fetches server capability statement
    - Returns success/failure with details
    """
    try:
        logger.info(
            "test_fhir_connection",
            connection_id=connection_id,
            user_id=user.id,
        )

        # Fetch connection
        connection = await prisma.fhirconnection.find_unique(
            where={"id": connection_id},
        )

        if not connection:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail="FHIR connection not found",
            )

        # Verify user owns this connection
        if connection.userId != user.id:
            raise HTTPException(
                status_code=http_status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to test this FHIR connection",
            )

        # Decrypt client secret if present
        client_secret = None
        if connection.clientSecretHash:
            try:
                client_secret = encryption_service.decrypt(connection.clientSecretHash)
            except Exception as e:
                logger.error("failed_to_decrypt_client_secret", error=str(e))
                return FhirConnectionTestResponse(
                    success=False,
                    message="Failed to decrypt client secret",
                    error=str(e),
                )

        # Initialize FHIR client
        fhir_client = FhirClient(
            fhir_server_url=connection.fhirServerUrl,
            fhir_version=connection.fhirVersion,
            auth_type=FhirAuthType(connection.authType),
            client_id=connection.clientId,
            client_secret=client_secret,
            token_endpoint=connection.tokenEndpoint,
            scope=connection.scope,
            timeout=10,  # Short timeout for testing
        )

        # Test connection
        async with fhir_client:
            try:
                # Attempt to authenticate
                await fhir_client.authenticate()

                # Fetch CapabilityStatement (metadata endpoint)
                capability_statement = await fhir_client.get_resource("metadata", "")

                server_info = {
                    "fhir_version": capability_statement.get("fhirVersion"),
                    "software": capability_statement.get("software", {}).get("name"),
                    "implementation": capability_statement.get("implementation", {}).get("description"),
                }

                logger.info(
                    "fhir_connection_test_success",
                    connection_id=connection_id,
                    fhir_version=server_info["fhir_version"],
                )

                return FhirConnectionTestResponse(
                    success=True,
                    message="Successfully connected to FHIR server",
                    fhir_version=server_info["fhir_version"],
                    server_info=server_info,
                )

            except Exception as e:
                logger.error(
                    "fhir_connection_test_failed",
                    connection_id=connection_id,
                    error=str(e),
                )
                return FhirConnectionTestResponse(
                    success=False,
                    message="Failed to connect to FHIR server",
                    error=str(e),
                )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "test_fhir_connection_error",
            connection_id=connection_id,
            user_id=user.id,
            error=str(e),
        )
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to test FHIR connection: {str(e)}",
        )
