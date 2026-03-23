from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.core.config import settings

if settings.ENVIRONMENT == "production":
    database_url = settings.DATABASE_URL
elif settings.ENVIRONMENT == "test" and settings.TEST_DATABASE_URL:
    database_url = settings.TEST_DATABASE_URL
else:
    database_url = settings.DEV_DATABASE_URL

if database_url.startswith("postgresql"):
    engine = create_async_engine(
        database_url,
        echo=(settings.ENVIRONMENT == "development"),
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        pool_timeout=settings.DB_POOL_TIMEOUT,
        pool_pre_ping=settings.DB_POOL_PRE_PING,
        pool_recycle=settings.DB_POOL_RECYCLE,
        connect_args={
            "server_settings": {"tcp_keepalives_idle": "60", "tcp_keepalives_interval": "10", "tcp_keepalives_count": "5"},
        },
    )
else:
    engine = create_async_engine(
        database_url,
        echo=(settings.ENVIRONMENT == "development"),
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
