import asyncio
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from app.main import app
from app.database import engine
from app.models import RoutePermission
from sqlalchemy.future import select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession

AsyncSessionLocal = sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False
)

async def check_missing_routes():
    # 1. Get all routes from FastAPI
    all_app_routes = []
    for route in app.routes:
        if hasattr(route, "path") and hasattr(route, "methods"):
            for method in route.methods:
                all_app_routes.append((route.path, method))
    
    # 2. Get all routes from DB
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(RoutePermission))
        db_perms = result.scalars().all()
        db_routes = [(p.path, p.method) for p in db_perms]
        
    print(f"Total App Routes: {len(all_app_routes)}")
    print(f"Total DB Routes: {len(db_routes)}")
    
    missing = []
    for path, method in all_app_routes:
        if (path, method) not in db_routes:
            missing.append(f"{method} {path}")
            
    if missing:
        print("\n❌ Missing routes in DB:")
        for m in missing:
            print(f"  - {m}")
    else:
        print("\n✅ All app routes are in DB.")

if __name__ == "__main__":
    asyncio.run(check_missing_routes())
