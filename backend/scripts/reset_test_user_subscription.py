"""
Reset test user subscription status to TRIAL
"""
import asyncio
from datetime import datetime, timedelta
from prisma import Prisma
from prisma.enums import SubscriptionStatus

TEST_USER_EMAIL = "huang.alex.c@gmail.com"


async def reset_subscription():
    """Reset test user's subscription to TRIAL with extended date"""
    prisma = Prisma()
    await prisma.connect()

    try:
        # Find the test user
        user = await prisma.user.find_unique(where={'email': TEST_USER_EMAIL})

        if not user:
            print(f"User not found: {TEST_USER_EMAIL}")
            return

        print(f"Found user: {user.email} (ID: {user.id})")
        print(f"Current subscription status: {user.subscriptionStatus}")
        print(f"Current trial end date: {user.trialEndDate}")

        # Set trial to 30 days from now
        new_trial_end = datetime.now() + timedelta(days=30)

        # Update user to TRIAL status with extended date
        updated_user = await prisma.user.update(
            where={'id': user.id},
            data={
                'subscriptionStatus': SubscriptionStatus.TRIAL,
                'trialEndDate': new_trial_end,
            }
        )

        print(f"\n✅ Successfully updated subscription!")
        print(f"New subscription status: {updated_user.subscriptionStatus}")
        print(f"New trial end date: {updated_user.trialEndDate}")
        print(f"\nThe test user can now access the application for 30 days.")

    except Exception as e:
        print(f"❌ Error updating subscription: {e}")
        raise
    finally:
        await prisma.disconnect()


if __name__ == "__main__":
    asyncio.run(reset_subscription())
