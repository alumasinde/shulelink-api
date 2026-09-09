import asyncio
import logging

from app.core.database import close_database, initialize_database, run_migrations

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("shulelink.migrations")


async def main() -> None:
    await initialize_database()
    try:
        logger.info("starting database migrations")
        await run_migrations()
        logger.info("database migrations completed successfully")
    finally:
        await close_database()


if __name__ == "__main__":
    asyncio.run(main())
