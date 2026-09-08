import asyncio

from app.core.database import close_database, initialize_database, run_migrations


async def main() -> None:
    await initialize_database()
    try:
        await run_migrations()
    finally:
        await close_database()


if __name__ == "__main__":
    asyncio.run(main())
