"""
Data Retention Cleanup Script
Runs automated data retention cleanup according to HIPAA policy

Usage:
    python -m app.scripts.retention_cleanup

This script should be run as a scheduled job (daily cron or Kubernetes CronJob)
"""

import asyncio
import sys
import structlog

from app.core.logging import configure_logging
from app.core.database import prisma
from app.services.data_retention import data_retention_service


# Configure logging
configure_logging()
logger = structlog.get_logger(__name__)


async def main():
    """Run data retention cleanup"""
    try:
        logger.info("Starting data retention cleanup script")

        # Connect to database
        await prisma.connect()
        logger.info("Database connected")

        # Run cleanup
        stats = await data_retention_service.run_retention_cleanup(
            system_user_id="system-retention-cleanup"
        )

        # Log results
        logger.info(
            "Data retention cleanup completed",
            total_encounters_deleted=stats["total_encounters_deleted"],
            total_files_deleted=stats["total_files_deleted"],
            error_count=len(stats.get("errors", [])),
        )

        # Print summary
        print("\n" + "=" * 50)
        print("DATA RETENTION CLEANUP SUMMARY")
        print("=" * 50)
        print(f"Started: {stats['started_at']}")
        print(f"Completed: {stats.get('completed_at', 'In Progress')}")
        print(f"Encounters Deleted: {stats['total_encounters_deleted']}")
        print(f"Files Deleted: {stats['total_files_deleted']}")
        print(f"S3 Objects Deleted: {stats['total_s3_objects_deleted']}")

        if stats.get("errors"):
            print(f"\nErrors ({len(stats['errors'])}):")
            for error in stats["errors"]:
                print(f"  - {error}")
        else:
            print("\nNo errors encountered")

        print("=" * 50 + "\n")

        # Disconnect from database
        await prisma.disconnect()
        logger.info("Database disconnected")

        # Exit with appropriate code
        exit_code = 1 if stats.get("errors") else 0
        sys.exit(exit_code)

    except Exception as e:
        logger.error("Data retention cleanup failed", error=str(e))
        print(f"\nERROR: Data retention cleanup failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
