#!/usr/bin/env python3
"""Inspect user roles for a given google_sub using app models.

Usage: PYTHONPATH=. python scripts/inspect_user_roles.py <google_sub>
"""
import sys
import asyncio
from app.database import AsyncSessionLocal
from app.models import User

async def main(sub):
    async with AsyncSessionLocal() as session:
        from sqlalchemy import text
        result = await session.execute(
            text("SELECT id, google_sub, email, roles FROM users WHERE google_sub = :sub"),
            {"sub": sub},
        )
        row = result.first()
        if not row:
            print(f"No user found for sub={sub}")
            return
        print("User row:")
        print(row)

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python scripts/inspect_user_roles.py <google_sub>")
        sys.exit(1)
    sub = sys.argv[1]
    asyncio.run(main(sub))
