"""
Seed script for initial payers
Creates common insurance payers in the database
"""
import asyncio
from prisma import Prisma
from prisma.enums import PayerType
import structlog

logger = structlog.get_logger(__name__)


async def seed_payers():
    """Seed initial payer data"""
    prisma = Prisma()
    await prisma.connect()

    try:
        # Common commercial payers
        commercial_payers = [
            {
                "name": "Blue Cross Blue Shield",
                "payerCode": "BCBS",
                "payerType": PayerType.COMMERCIAL,
                "website": "https://www.bcbs.com",
                "notes": "National federation of independent insurance companies"
            },
            {
                "name": "UnitedHealthcare",
                "payerCode": "UHC",
                "payerType": PayerType.COMMERCIAL,
                "website": "https://www.uhc.com",
                "notes": "Largest health insurance carrier in the United States"
            },
            {
                "name": "Aetna",
                "payerCode": "AETNA",
                "payerType": PayerType.COMMERCIAL,
                "website": "https://www.aetna.com",
                "notes": "CVS Health subsidiary"
            },
            {
                "name": "Cigna",
                "payerCode": "CIGNA",
                "payerType": PayerType.COMMERCIAL,
                "website": "https://www.cigna.com",
                "notes": "Global health services company"
            },
            {
                "name": "Humana",
                "payerCode": "HUMANA",
                "payerType": PayerType.COMMERCIAL,
                "website": "https://www.humana.com",
                "notes": "For-profit health insurance company"
            },
        ]

        # Government payers
        government_payers = [
            {
                "name": "Medicare",
                "payerCode": "MEDICARE",
                "payerType": PayerType.MEDICARE,
                "website": "https://www.medicare.gov",
                "notes": "Federal health insurance program for people 65+"
            },
            {
                "name": "Medicaid",
                "payerCode": "MEDICAID",
                "payerType": PayerType.MEDICAID,
                "website": "https://www.medicaid.gov",
                "notes": "Joint federal and state program for low-income individuals"
            },
            {
                "name": "TRICARE",
                "payerCode": "TRICARE",
                "payerType": PayerType.TRICARE,
                "website": "https://www.tricare.mil",
                "notes": "Health care program for uniformed service members and families"
            },
        ]

        # Other payers
        other_payers = [
            {
                "name": "Workers' Compensation",
                "payerCode": "WORKERS_COMP",
                "payerType": PayerType.WORKERS_COMP,
                "notes": "Work-related injury and illness insurance"
            },
            {
                "name": "Self-Pay",
                "payerCode": "SELF_PAY",
                "payerType": PayerType.SELF_PAY,
                "notes": "Patient paying out-of-pocket"
            },
        ]

        all_payers = commercial_payers + government_payers + other_payers

        # Create payers
        created_count = 0
        for payer_data in all_payers:
            # Check if payer already exists
            existing = await prisma.payer.find_unique(
                where={"payerCode": payer_data["payerCode"]}
            )

            if existing:
                logger.info(f"Payer already exists: {payer_data['name']}")
                continue

            # Create new payer
            payer = await prisma.payer.create(data=payer_data)
            logger.info(f"Created payer: {payer.name} ({payer.payerCode})")
            created_count += 1

        logger.info(f"Seed complete. Created {created_count} new payers.")

    except Exception as e:
        logger.error(f"Error seeding payers: {str(e)}")
        raise
    finally:
        await prisma.disconnect()


if __name__ == "__main__":
    asyncio.run(seed_payers())
