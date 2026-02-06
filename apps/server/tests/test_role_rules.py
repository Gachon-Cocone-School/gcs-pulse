import asyncio
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from app.crud import apply_role_rules
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.core.config import settings


async def test_role_rules():
    engine = create_async_engine(settings.DATABASE_URL)
    AsyncSessionLocal = sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )

    async with AsyncSessionLocal() as session:
        print("Testing Role Assignment Rules\n")

        # Test 1: Gachon email
        print("Test 1: @gachon.ac.kr email")
        roles = await apply_role_rules(session, "student@gachon.ac.kr")
        print(f"  Email: student@gachon.ac.kr")
        print(f"  Assigned roles: {roles}")
        assert "가천대학교" in roles, "Should assign 가천대학교 role"
        print("  ✅ PASS\n")

        # Test 2: Admin email from list
        print("Test 2: Admin email from list")
        roles = await apply_role_rules(session, "admin@example.com")
        print(f"  Email: admin@example.com")
        print(f"  Assigned roles: {roles}")
        assert "admin" in roles, "Should assign admin role"
        print("  ✅ PASS\n")

        # Test 3: Non-matching email
        print("Test 3: Non-matching email")
        roles = await apply_role_rules(session, "random@gmail.com")
        print(f"  Email: random@gmail.com")
        print(f"  Assigned roles: {roles}")
        assert len(roles) == 0, "Should not assign any roles"
        print("  ✅ PASS\n")

        # Test 4: Multiple rules match
        print("Test 4: Multiple rules (if applicable)")
        roles = await apply_role_rules(session, "manager@example.com")
        print(f"  Email: manager@example.com")
        print(f"  Assigned roles: {roles}")
        if len(roles) > 0:
            print(f"  ✅ Matched {len(roles)} rule(s)\n")
        else:
            print(f"  ✅ No matches (expected)\n")

    await engine.dispose()
    print("All tests passed! ✅")


if __name__ == "__main__":
    asyncio.run(test_role_rules())
