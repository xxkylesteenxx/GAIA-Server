"""python -m gaia_server entry point."""
import asyncio

from gaia_server.entrypoint import main

if __name__ == "__main__":
    asyncio.run(main())
