import asyncio
import sys
from pathlib import Path

# Allow this script to be executed directly from backend/scripts on Windows/Linux.
# This adds the backend directory to Python's import path so `app` resolves.
BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.database import close_database, initialize_database, run_migrations


async def main() -> None:
    await initialize_database()
    try:
        await run_migrations()
    finally:
        await close_database()


if __name__ == "__main__":
    asyncio.run(main())
