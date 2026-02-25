#!/usr/bin/env python3
"""Inspect user roles for a given email using app models.

Usage: PYTHONPATH=. python scripts/inspect_user_roles.py <email>
"""
import sys
import asyncio
from app.database import AsyncSessionLocal
from app.models import User

async def main(email):
    async with AsyncSessionLocal() as session:
        from sqlalchemy import text
        result = await session.execute(
            text("SELECT id, email, roles FROM users WHERE email = :email"),
            {"email": email},
        )
        row = result.first()
        if not row:
            print(f"No user found for email={email}")
            return
        print("User row:")
        print(row)

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python scripts/inspect_user_roles.py <email>")
        sys.exit(1)
    email = sys.argv[1]
    asyncio.run(main(email))
