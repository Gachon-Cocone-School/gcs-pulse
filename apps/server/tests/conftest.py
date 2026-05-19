import asyncio
import os


def pytest_configure(config):
    os.environ.setdefault("ENVIRONMENT", "test")


def pytest_sessionfinish(session, exitstatus):
    from app.database import engine

    asyncio.run(engine.dispose())
