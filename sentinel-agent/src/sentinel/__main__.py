"""Sentinel Agent — lightweight production monitoring with multi-channel alerting."""

import asyncio
import logging
import sys

from aiohttp import ClientSession

from sentinel.alerting import AlertRouter, send_signal_message
from sentinel.config import load_config
from sentinel.github_monitor import GitHubActionsMonitor
from sentinel.health import HealthRingBuffer
from sentinel.hetzner_monitor import HetznerMonitor
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

    # Log enabled channels
    channels = []
    if config.signal.enabled:
        channels.append("Signal")
    if config.ntfy.enabled:
        channels.append("ntfy")
    if config.slack.enabled:
        channels.append("Slack")
    logger.info("Alert channels: %s", ", ".join(channels) or "none")

    # Log enabled monitors
    monitors = []
    if config.github.enabled:
        monitors.append(f"GitHub ({config.github.repo})")
    if config.hetzner.enabled:
        server_list = ", ".join(config.hetzner.server_names) if config.hetzner.server_names else "all"
        monitors.append(f"Hetzner ({server_list})")
    logger.info("Infrastructure monitors: %s", ", ".join(monitors) or "none")

    buffer = HealthRingBuffer(max_size=100)
    router = AlertRouter(config.signal, config.ntfy, config.slack)

    # Infrastructure monitors
    github_monitor = GitHubActionsMonitor(config.github)
    hetzner_monitor = HetznerMonitor(config.hetzner)

    # Reuse a single session for all polling (memory efficient)
    async with ClientSession() as session:
        poll_counter = 0
        signal_poll_interval = 30  # seconds
        health_poll_interval = config.poll_interval_seconds
        checks_per_health_poll = max(1, health_poll_interval // signal_poll_interval)

        # GitHub Actions polls every 60s (2 ticks) for fast deploy feedback
        github_poll_ticks = max(1, 60 // signal_poll_interval)

        # Hetzner polls on the same schedule as health checks (5 min)
        hetzner_poll_ticks = checks_per_health_poll

        while True:
            # ── Health endpoint polling ────────────────────────────
            if poll_counter % checks_per_health_poll == 0:
                logger.info("Polling health endpoints...")
                records = await poll_all_targets(session, config.targets, buffer)
                for record in records:
                    await router.process(record)
                    status = "OK" if record.is_healthy else "FAIL"
                    logger.info("  %s %s: %s (%.0fms)",
                                status, record.target_name, record.status,
                                record.response_time_ms)

            # ── GitHub Actions deploy monitoring ───────────────────
            if config.github.enabled and poll_counter % github_poll_ticks == 0:
                try:
                    gh_messages = await github_monitor.check()
                    for msg in gh_messages:
                        logger.info("GitHub: %s", msg.split("\n")[0])
                        await router.send_deploy_alert(msg)
                except Exception as exc:
                    logger.error("GitHub monitor error: %s", exc)

            # ── Hetzner server monitoring ──────────────────────────
            if config.hetzner.enabled and poll_counter % hetzner_poll_ticks == 0:
                try:
                    hz_messages = await hetzner_monitor.check()
                    for msg in hz_messages:
                        logger.info("Hetzner: %s", msg.split("\n")[0])
                        await router.send_infra_alert(msg)
                except Exception as exc:
                    logger.error("Hetzner monitor error: %s", exc)

            # ── Signal inbox polling ───────────────────────────────
            messages = await fetch_incoming_messages(config.signal)
            for msg in messages:
                logger.info("Signal message from %s: %s", msg["sender"], msg["text"])
                reply = await generate_health_response(
                    msg["text"],
                    buffer,
                    github_monitor=github_monitor,
                    hetzner_monitor=hetzner_monitor,
                )
                await send_signal_message(config.signal, reply)

            poll_counter += 1
            await asyncio.sleep(signal_poll_interval)


if __name__ == "__main__":
    main()
