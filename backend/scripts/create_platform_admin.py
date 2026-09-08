import argparse
import asyncio
import getpass
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.database import close_database, get_pool, initialize_database
from app.core.security import hash_password, validate_password


async def main() -> None:
    parser = argparse.ArgumentParser(description="Create a ShuleLink platform administrator")
    parser.add_argument("--email", required=True)
    parser.add_argument("--first-name", required=True)
    parser.add_argument("--last-name", required=True)
    args = parser.parse_args()
    password = getpass.getpass("Password: ")
    confirmation = getpass.getpass("Confirm password: ")
    if password != confirmation:
        raise SystemExit("Passwords do not match")
    try:
        validate_password(password)
    except ValueError as exc:
        raise SystemExit(str(exc))

    from uuid import uuid4
    await initialize_database()
    try:
        pool = get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT 1 FROM platform_users WHERE email=%s LIMIT 1", (args.email.lower().strip(),))
                if await cur.fetchone():
                    raise SystemExit("A platform user with that email already exists")
                user_id = str(uuid4())
                await cur.execute(
                    "INSERT INTO platform_users (id,email,first_name,last_name,password_hash,status) VALUES (%s,%s,%s,%s,%s,'active')",
                    (user_id,args.email.lower().strip(),args.first_name.strip(),args.last_name.strip(),hash_password(password)),
                )
                await cur.execute("INSERT INTO platform_user_roles (platform_user_id,platform_role_id) VALUES (%s,'00000000-0000-0000-0000-000000000001')", (user_id,))
        print(f"Platform administrator created: {args.email.lower().strip()}")
    finally:
        await close_database()


if __name__ == "__main__":
    asyncio.run(main())
