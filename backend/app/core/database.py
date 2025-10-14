"""
Database Connection Management
Prisma ORM client configuration
"""

from prisma import Prisma

# Global Prisma client instance
prisma = Prisma()


async def get_db():
    """
    Dependency for getting database session in FastAPI routes
    """
    if not prisma.is_connected():
        await prisma.connect()
    return prisma
