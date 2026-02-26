import os


def pytest_configure(config):
    os.environ.setdefault("ENVIRONMENT", "test")
