"""
Audit Log Cleanup Script

This script cleans up audit logs older than the retention period (6 years for HIPAA compliance).
Should be run as a scheduled cron job or Kubernetes CronJob.

Usage:
    python -m app.scripts.cleanup_audit_logs [--days DAYS] [--dry-run]
"""

import asyncio
import argparse
import structlog
from datetime import datetime, timedelta

from app.core.database import prisma
from app.core.audit import cleanup_old_audit_logs

logger = structlog.get_logger(__name__)


async def main():
    """Main cleanup function"""
    parser = argparse.ArgumentParser(description="Clean up old audit logs")
    parser.add_argument(
        "--days",
        type=int,
        default=2190,  # 6 years (HIPAA requirement)
        help="Number of days to retain audit logs (default: 2190 = 6 years)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be deleted without actually deleting",
    )

    args = parser.parse_args()

    logger.info(
        "audit_log_cleanup_started",
        retention_days=args.days,
        dry_run=args.dry_run,
    )

    try:
        # Connect to database
        await prisma.connect()
        logger.info("database_connected")

        if args.dry_run:
            # Count logs that would be deleted
            cutoff_date = datetime.utcnow() - timedelta(days=args.days)
            count = await prisma.auditlog.count(
                where={"createdAt": {"lt": cutoff_date}}
            )

            logger.info(
                "dry_run_result",
                count=count,
                cutoff_date=cutoff_date.isoformat(),
                message=f"Would delete {count} audit log entries",
            )
            print(f"[DRY RUN] Would delete {count} audit log entries older than {cutoff_date}")

        else:
            # Actually delete old logs
            deleted_count = await cleanup_old_audit_logs(days_to_retain=args.days)

            logger.info(
                "audit_log_cleanup_completed",
                deleted_count=deleted_count,
            )
            print(f"Successfully deleted {deleted_count} audit log entries")

    except Exception as e:
        logger.error(
            "audit_log_cleanup_failed",
            error=str(e),
            error_type=type(e).__name__,
        )
        print(f"ERROR: Cleanup failed - {e}")
        raise

    finally:
        # Disconnect from database
        await prisma.disconnect()
        logger.info("database_disconnected")


if __name__ == "__main__":
    asyncio.run(main())
