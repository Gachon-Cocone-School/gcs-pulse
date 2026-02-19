from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.core.config import settings

database_url = (
    settings.TEST_DATABASE_URL
    if settings.ENVIRONMENT == "test" and settings.TEST_DATABASE_URL
    else settings.DATABASE_URL
)

engine = create_async_engine(
    database_url, echo=(settings.ENVIRONMENT == "development")
)
AsyncSessionLocal = async_sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False
)

Base = declarative_base()


async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
