#!/usr/bin/env python3
"""Inspect RoutePermission for a given path and method.

Usage: PYTHONPATH=. python scripts/inspect_route_permission.py "/daily-snippets" POST
"""
import sys
import asyncio
from sqlalchemy import text
from app.database import AsyncSessionLocal

async def main(path, method):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text("SELECT id, path, method, is_public, roles FROM route_permissions WHERE path = :path AND method = :method"),
            {"path": path, "method": method},
        )
        row = result.first()
        if not row:
            print(f"No RoutePermission found for {path} {method}")
            return
        print("RoutePermission row:")
        print(row)

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python scripts/inspect_route_permission.py <path> <method>")
        sys.exit(1)
    path = sys.argv[1]
    method = sys.argv[2]
    asyncio.run(main(path, method))
