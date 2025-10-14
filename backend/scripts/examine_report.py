#!/usr/bin/env python3
"""
Examine a specific report to see revenue data
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


async def examine_report():
    """Examine report data"""
    await prisma.connect()

    try:
        report = await prisma.report.find_unique(
            where={"id": REPORT_ID}
        )

        if not report:
            print(f"Report {REPORT_ID} not found")
            return

        print("="*80)
        print(f"REPORT {REPORT_ID}")
        print("="*80)
        print(f"Status: {report.status}")
        print(f"Incremental Revenue: ${report.incrementalRevenue or 0:.2f}")
        print(f"Processing Time: {report.processingTimeMs/1000:.1f}s" if report.processingTimeMs else "N/A")
        print()

        print("SUGGESTED CODES:")
        print("="*80)
        if report.suggestedCodes:
            for i, code in enumerate(report.suggestedCodes, 1):
                print(f"\n{i}. {code.get('code')} ({code.get('code_type')})")
                print(f"   Description: {code.get('description', 'N/A')}")
                print(f"   Confidence: {code.get('confidence', 0)*100:.0f}%")
                print(f"   Revenue Impact: ${code.get('revenue_impact', 0):.2f}")
                print(f"   Justification: {code.get('justification', 'N/A')}")
        else:
            print("No suggested codes")

        print()
        print("="*80)
        print("RAW SUGGESTED CODES JSON:")
        print("="*80)
        print(json.dumps(report.suggestedCodes, indent=2))

    finally:
        await prisma.disconnect()


if __name__ == "__main__":
    asyncio.run(examine_report())
