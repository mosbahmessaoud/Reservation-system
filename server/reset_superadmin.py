import asyncio
from server.models.user import User
from server.db import get_db, users_table
from server.auth_utils import get_password_hash


async def reset_superadmin_password():
    await get_db.connect()

    # Find super admin
    query = query(User).update().where(
        User.phone_number == "0658890501"
    ).values(
        password_hash=get_password_hash("M.super7admin!2002")
    )

    await get_db.execute(query)
    print("✅ Super admin password reset successfully!")

    await get_db.disconnect()

if __name__ == "__main__":
    asyncio.run(reset_superadmin_password())
