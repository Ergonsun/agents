import asyncio
import sys


def main() -> None:
    """Entry point for sentinel agent."""
    try:
        asyncio.run(_run())
    except KeyboardInterrupt:
        print("\n[Sentinel] Shutting down.")
        sys.exit(0)


async def _run() -> None:
    """Main async entry point."""
    print("[Sentinel] Starting...")


if __name__ == "__main__":
    main()
