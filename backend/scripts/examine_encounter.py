#!/usr/bin/env python3
"""
Examine encounter and report billed codes
"""

import asyncio
import sys
import os
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
os.environ.setdefault('ENV_FILE', str(Path(__file__).parent.parent / '.env'))

from app.core.database import prisma

REPORT_ID = "8b9f1292-f8c7-4d10-9bf7-fc2ce03be65e"


async def examine_encounter():
    """Examine encounter and billed codes"""
    await prisma.connect()

    try:
        report = await prisma.report.find_unique(
            where={"id": REPORT_ID},
            include={"encounter": True}
        )

        if not report:
            print(f"Report {REPORT_ID} not found")
            return

        encounter = report.encounter

        print("="*80)
        print(f"ENCOUNTER {encounter.id}")
        print("="*80)
        print(f"Date of Service: {encounter.dateOfService}")
        print(f"Encounter Type: {encounter.encounterType}")
        print(f"Status: {encounter.status}")
        print()

        print("BILLED CODES (from Report):")
        print("="*80)
        if report.billedCodes:
            if len(report.billedCodes) == 0:
                print("⚠️  NO BILLED CODES FOUND")
                print("   This means no codes were originally submitted for this encounter.")
            else:
                for i, code in enumerate(report.billedCodes, 1):
                    print(f"{i}. {code.get('code')} ({code.get('code_type')})")
                    print(f"   Description: {code.get('description', 'N/A')}")
                    print()
        else:
            print("⚠️  billedCodes field is None/empty")

        print()
        print("REVENUE ANALYSIS:")
        print("="*80)
        print(f"Incremental Revenue: ${report.incrementalRevenue or 0:.2f}")
        print()
        print("Suggested Codes Count:", len(report.suggestedCodes) if report.suggestedCodes else 0)

        if report.suggestedCodes:
            total_suggested = sum(code.get('revenue_impact', 0) for code in report.suggestedCodes)
            print(f"Sum of Per-Code Revenue: ${total_suggested:.2f}")
            print()
            print("Per-Code Breakdown:")
            for code in report.suggestedCodes:
                print(f"  • {code.get('code')}: ${code.get('revenue_impact', 0):.2f}")

        print()
        print("="*80)
        print("RAW BILLED CODES JSON:")
        print("="*80)
        print(json.dumps(report.billedCodes, indent=2))

    finally:
        await prisma.disconnect()


if __name__ == "__main__":
    asyncio.run(examine_encounter())
