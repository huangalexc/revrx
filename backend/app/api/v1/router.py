"""
API Router - Main router for all v1 endpoints
"""

from fastapi import APIRouter
from app.api.v1 import auth, users, encounters, admin, reports, audit_logs, fhir_connections, fhir, monitoring  # websocket
from app.api import subscriptions, webhooks, api_keys, integrations, webhooks_mgmt

api_router = APIRouter()

# Health check for API
@api_router.get("/health")
async def api_health():
    """API health check"""
    return {"status": "healthy", "api_version": "v1"}

# Include routers
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(encounters.router)
api_router.include_router(reports.router)
api_router.include_router(admin.router)
api_router.include_router(audit_logs.router)
api_router.include_router(subscriptions.router)
api_router.include_router(webhooks.router)
api_router.include_router(api_keys.router)
api_router.include_router(integrations.router)
api_router.include_router(webhooks_mgmt.router)
api_router.include_router(fhir_connections.router)
api_router.include_router(fhir.router)
# api_router.include_router(websocket.router)  # Temporarily disabled - missing get_current_user_ws dependency
api_router.include_router(monitoring.router)
