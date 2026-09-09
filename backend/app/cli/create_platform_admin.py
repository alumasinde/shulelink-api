"""Bootstrap a ShuleLink platform administrator from the command line."""

from __future__ import annotations

import argparse
import asyncio
import getpass
import sys

from pymysql.err import IntegrityError

from app.core.database import close_database, get_central_pool, initialize_database
from app.core.security import hash_password, validate_password

DEFAULT_ROLE = "platform_admin"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a ShuleLink platform user and assign a platform role."
    )
    parser.add_argument("--first-name", help="Platform user's first name")
    parser.add_argument("--last-name", help="Platform user's last name")
    parser.add_argument("--email", help="Platform user's email address")
    parser.add_argument(
        "--role",
        default=DEFAULT_ROLE,
        help=f"Platform role code (default: {DEFAULT_ROLE})",
    )
    return parser.parse_args()


def _required(value: str | None, prompt: str) -> str:
    value = (value or input(prompt)).strip()
    if not value:
        raise ValueError(f"{prompt.rstrip(': ')} is required")
    return value


def _read_password() -> str:
    while True:
        password = getpass.getpass("Password: ")
        confirmation = getpass.getpass("Confirm password: ")
        if password != confirmation:
            print("Passwords do not match. Please try again.")
            continue
        try:
            validate_password(password)
        except ValueError as exc:
            print(f"Invalid password: {exc}")
            continue
        return password


async def _create_admin(
    first_name: str,
    last_name: str,
    email: str,
    password: str,
    role_code: str,
) -> int:
    pool = get_central_pool()
    normalized_email = email.lower().strip()
    normalized_role = role_code.lower().strip()

    async with pool.acquire() as conn:
        await conn.begin()
        try:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT id FROM platform_users WHERE email=%s LIMIT 1",
                    (normalized_email,),
                )
                if await cur.fetchone():
                    raise ValueError(
                        f"A platform user with email {normalized_email} already exists."
                    )

                await cur.execute(
                    "SELECT id,name,is_active FROM platform_roles WHERE code=%s LIMIT 1",
                    (normalized_role,),
                )
                role = await cur.fetchone()
                if not role:
                    raise ValueError(
                        f"Platform role '{normalized_role}' does not exist."
                    )
                if not role[2]:
                    raise ValueError(
                        f"Platform role '{normalized_role}' is not active."
                    )

                await cur.execute(
                    """
                    INSERT INTO platform_users
                        (first_name,last_name,email,password_hash,status)
                    VALUES (%s,%s,%s,%s,'active')
                    """,
                    (
                        first_name.strip(),
                        last_name.strip(),
                        normalized_email,
                        hash_password(password),
                    ),
                )
                user_id = cur.lastrowid

                await cur.execute(
                    """
                    INSERT INTO platform_user_roles
                        (platform_user_id,role_id)
                    VALUES (%s,%s)
                    """,
                    (user_id, role[0]),
                )

                await conn.commit()
                return int(user_id)
        except IntegrityError as exc:
            await conn.rollback()
            raise ValueError(
                "The platform administrator could not be created because a database "
                "constraint was violated. The email may already exist."
            ) from exc
        except Exception:
            await conn.rollback()
            raise


async def main() -> int:
    args = _parse_args()
    try:
        first_name = _required(args.first_name, "First name: ")
        last_name = _required(args.last_name, "Last name: ")
        email = _required(args.email, "Email: ")
        password = _read_password()

        await initialize_database()
        try:
            user_id = await _create_admin(
                first_name,
                last_name,
                email,
                password,
                args.role,
            )
        finally:
            await close_database()

        print()
        print("Platform administrator created successfully.")
        print(f"User ID: {user_id}")
        print(f"Email: {email.lower().strip()}")
        print(f"Role: {args.role.lower().strip()}")
        print("Status: active")
        return 0
    except (KeyboardInterrupt, EOFError):
        print("\nOperation cancelled.", file=sys.stderr)
        return 130
    except (ValueError, RuntimeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
