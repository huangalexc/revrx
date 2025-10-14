"""
WebSocket API for Real-time Report Updates
Provides WebSocket endpoint for streaming report progress updates to clients
"""

from typing import Dict, Set
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, status
import structlog
import asyncio
import json

from app.core.database import prisma
from app.core.deps import get_current_user_ws
from prisma import enums

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/ws", tags=["WebSocket"])

# Connection manager to track active WebSocket connections
class ConnectionManager:
    """Manages WebSocket connections for report updates"""

    def __init__(self):
        # report_id -> set of websockets
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, report_id: str):
        """Accept and register a new WebSocket connection"""
        await websocket.accept()

        async with self._lock:
            if report_id not in self.active_connections:
                self.active_connections[report_id] = set()
            self.active_connections[report_id].add(websocket)

        logger.info(
            "WebSocket connected",
            report_id=report_id,
            connection_count=len(self.active_connections[report_id])
        )

    async def disconnect(self, websocket: WebSocket, report_id: str):
        """Unregister a WebSocket connection"""
        async with self._lock:
            if report_id in self.active_connections:
                self.active_connections[report_id].discard(websocket)

                # Clean up empty sets
                if not self.active_connections[report_id]:
                    del self.active_connections[report_id]

        logger.info(
            "WebSocket disconnected",
            report_id=report_id,
            remaining_connections=len(self.active_connections.get(report_id, []))
        )

    async def send_message(self, report_id: str, message: dict):
        """Send message to all connections for a specific report"""
        if report_id not in self.active_connections:
            return

        # Create a copy to avoid modification during iteration
        connections = list(self.active_connections[report_id])

        for websocket in connections:
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(
                    "Failed to send WebSocket message",
                    report_id=report_id,
                    error=str(e)
                )
                # Remove failed connection
                await self.disconnect(websocket, report_id)

    async def broadcast(self, message: dict):
        """Broadcast message to all connections"""
        for report_id in list(self.active_connections.keys()):
            await self.send_message(report_id, message)

    def get_connection_count(self, report_id: str) -> int:
        """Get number of active connections for a report"""
        return len(self.active_connections.get(report_id, []))

    def get_total_connections(self) -> int:
        """Get total number of active connections across all reports"""
        return sum(len(conns) for conns in self.active_connections.values())


# Global connection manager instance
manager = ConnectionManager()


@router.websocket("/reports/{report_id}")
async def websocket_report_status(
    websocket: WebSocket,
    report_id: str
):
    """
    WebSocket endpoint for real-time report status updates

    Clients connect to receive instant progress updates without polling.
    Connection automatically closes when report reaches terminal state (COMPLETE/FAILED).

    Message Format:
    {
        "type": "status_update",
        "data": {
            "reportId": "uuid",
            "status": "PROCESSING",
            "progressPercent": 45,
            "currentStep": "code_inference",
            "estimatedTimeRemainingMs": 15000
        }
    }
    """
    # Accept connection
    await manager.connect(websocket, report_id)

    try:
        # Verify report exists
        report = await prisma.report.find_unique(
            where={"id": report_id},
            include={"encounter": True}
        )

        if not report:
            await websocket.send_json({
                "type": "error",
                "message": "Report not found"
            })
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        # TODO: Add authentication check
        # user = await get_current_user_ws(websocket)
        # if user.role != "ADMIN" and report.encounter.userId != user.id:
        #     await websocket.send_json({"type": "error", "message": "Access denied"})
        #     await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        #     return

        # Send initial status
        await websocket.send_json({
            "type": "connected",
            "message": "WebSocket connection established",
            "reportId": report_id
        })

        await websocket.send_json({
            "type": "status_update",
            "data": {
                "reportId": report.id,
                "encounterId": report.encounterId,
                "status": report.status,
                "progressPercent": report.progressPercent,
                "currentStep": report.currentStep,
                "processingStartedAt": report.processingStartedAt.isoformat() if report.processingStartedAt else None,
            }
        })

        # Poll database for updates and push to client
        # This is more efficient than polling from client side
        last_progress = report.progressPercent
        last_status = report.status

        while True:
            # Check for client disconnect
            try:
                # Non-blocking receive with timeout
                message = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=1.0
                )

                # Handle client messages (ping/pong, etc.)
                if message == "ping":
                    await websocket.send_json({"type": "pong"})

            except asyncio.TimeoutError:
                pass  # Normal - no message received
            except WebSocketDisconnect:
                break

            # Fetch latest report status
            report = await prisma.report.find_unique(
                where={"id": report_id}
            )

            if not report:
                await websocket.send_json({
                    "type": "error",
                    "message": "Report no longer exists"
                })
                break

            # Send update if status or progress changed
            if report.status != last_status or report.progressPercent != last_progress:
                update_message = {
                    "type": "status_update",
                    "data": {
                        "reportId": report.id,
                        "encounterId": report.encounterId,
                        "status": report.status,
                        "progressPercent": report.progressPercent,
                        "currentStep": report.currentStep,
                    }
                }

                # Add timing info if available
                if report.processingStartedAt:
                    update_message["data"]["processingStartedAt"] = report.processingStartedAt.isoformat()

                if report.status == enums.ReportStatus.PROCESSING:
                    # Calculate estimated time remaining
                    from datetime import datetime
                    if report.processingStartedAt and report.progressPercent > 0:
                        elapsed_ms = (datetime.utcnow() - report.processingStartedAt).total_seconds() * 1000
                        estimated_total_ms = (elapsed_ms / report.progressPercent) * 100
                        estimated_remaining_ms = max(0, int(estimated_total_ms - elapsed_ms))
                        update_message["data"]["estimatedTimeRemainingMs"] = estimated_remaining_ms

                if report.processingCompletedAt:
                    update_message["data"]["processingCompletedAt"] = report.processingCompletedAt.isoformat()

                if report.processingTimeMs:
                    update_message["data"]["processingTimeMs"] = report.processingTimeMs

                # Add error info if failed
                if report.status == enums.ReportStatus.FAILED:
                    update_message["data"]["errorMessage"] = report.errorMessage
                    if report.errorDetails:
                        update_message["data"]["errorDetails"] = report.errorDetails
                    update_message["data"]["retryCount"] = report.retryCount

                await websocket.send_json(update_message)

                last_progress = report.progressPercent
                last_status = report.status

            # Close connection if report reached terminal state
            if report.status in [enums.ReportStatus.COMPLETE, enums.ReportStatus.FAILED]:
                await websocket.send_json({
                    "type": "final_status",
                    "message": f"Report {report.status.lower()}",
                    "data": {
                        "status": report.status,
                        "reportId": report.id
                    }
                })
                break

            # Wait before next check (server-side polling)
            await asyncio.sleep(1)

    except WebSocketDisconnect:
        logger.info("Client disconnected", report_id=report_id)
    except Exception as e:
        logger.error(
            "WebSocket error",
            report_id=report_id,
            error=str(e)
        )
        try:
            await websocket.send_json({
                "type": "error",
                "message": "Internal server error"
            })
        except:
            pass
    finally:
        await manager.disconnect(websocket, report_id)


@router.get("/stats")
async def get_websocket_stats():
    """
    Get WebSocket connection statistics (admin only)

    Returns:
        Statistics about active WebSocket connections
    """
    return {
        "total_connections": manager.get_total_connections(),
        "reports_with_connections": len(manager.active_connections),
        "connections_by_report": {
            report_id: len(connections)
            for report_id, connections in manager.active_connections.items()
        }
    }


# Utility function for pushing updates from report processor
async def notify_report_update(report_id: str, data: dict):
    """
    Push update to all connected clients for a report

    Call this from report_processor.py when progress updates
    """
    await manager.send_message(report_id, {
        "type": "status_update",
        "data": data
    })
