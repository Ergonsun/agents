"""Sentinel Agent — lightweight production monitoring with Signal + email alerting."""

import asyncio
import logging
import sys

from aiohttp import ClientSession

from sentinel.alerting import AlertRouter, send_signal_message
from sentinel.config import load_config
from sentinel.health import HealthRingBuffer
from sentinel.poller import poll_all_targets
from sentinel.setup import run_first_time_setup
from sentinel.signal_listener import fetch_incoming_messages, generate_health_response

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("sentinel")


def main() -> None:
    """Entry point for sentinel agent."""
    try:
        asyncio.run(_run())
    except KeyboardInterrupt:
        print("\n[Sentinel] Shutting down.")
        sys.exit(0)


async def _run() -> None:
    """Main async event loop."""
    logger.info("Starting Sentinel Agent...")

    # Load or create configuration
    config = load_config()
    if config is None:
        config = await run_first_time_setup()

    logger.info(
        "Monitoring %d target(s): %s",
        len(config.targets),
        ", ".join(t.name for t in config.targets),
    )
    logger.info("Signal: %s | Email: %s",
                "enabled" if config.signal.enabled else "disabled",
                "enabled" if config.email.enabled else "disabled")

    buffer = HealthRingBuffer(max_size=100)
    router = AlertRouter(config.signal, config.email)

    # Reuse a single session for all polling (memory efficient)
    async with ClientSession() as session:
        poll_counter = 0
        signal_poll_interval = 30  # seconds
        health_poll_interval = config.poll_interval_seconds
        checks_per_health_poll = max(1, health_poll_interval // signal_poll_interval)

        while True:
            # Health poll on schedule
            if poll_counter % checks_per_health_poll == 0:
                logger.info("Polling health endpoints...")
                records = await poll_all_targets(session, config.targets, buffer)
                for record in records:
                    await router.process(record)
                    status = "OK" if record.is_healthy else "FAIL"
                    logger.info("  %s %s: %s (%.0fms)",
                                status, record.target_name, record.status,
                                record.response_time_ms)

            # Check Signal inbox
            messages = await fetch_incoming_messages(config.signal)
            for msg in messages:
                logger.info("Signal message from %s: %s", msg["sender"], msg["text"])
                reply = await generate_health_response(msg["text"], buffer)
                await send_signal_message(config.signal, reply)

            poll_counter += 1
            await asyncio.sleep(signal_poll_interval)


if __name__ == "__main__":
    main()
