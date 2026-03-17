"""Alert routing via Signal, ntfy, and Slack with deduplication."""

import json
import logging

import aiohttp

from sentinel.config import NtfyConfig, SignalConfig, SlackConfig
from sentinel.health import HealthRecord

logger = logging.getLogger("sentinel.alerting")


async def send_signal_message(config: SignalConfig, message: str) -> bool:
    """Send a message via signal-cli-rest-api. Returns True on success."""
    if not config.enabled:
        return False
    try:
        async with aiohttp.ClientSession() as session:
            payload = {
                "message": message,
                "number": config.phone_number,
                "recipients": [config.recipient],
            }
            async with session.post(
                f"{config.api_url}/v2/send",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status < 300:
                    return True
                logger.warning("Signal API returned %d", resp.status)
                return False
    except Exception as exc:
        logger.error("Failed to send Signal message: %s", exc)
        return False


async def send_ntfy_alert(config: NtfyConfig, title: str, message: str) -> bool:
    """Send a push notification via ntfy.sh. Returns True on success."""
    if not config.enabled:
        return False
    try:
        url = f"{config.server_url.rstrip('/')}/{config.topic}"
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                data=message.encode("utf-8"),
                headers={
                    "Title": f"[Sentinel] {title}",
                    "Priority": config.priority,
                    "Tags": "warning" if "DOWN" in title else "white_check_mark",
                },
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status < 300:
                    return True
                logger.warning("ntfy returned %d", resp.status)
                return False
    except Exception as exc:
        logger.error("Failed to send ntfy notification: %s", exc)
        return False


async def send_slack_alert(config: SlackConfig, message: str) -> bool:
    """Send a message to Slack via incoming webhook. Returns True on success."""
    if not config.enabled or not config.webhook_url:
        return False
    try:
        async with aiohttp.ClientSession() as session:
            payload = {"text": message}
            if config.channel:
                payload["channel"] = config.channel
            async with session.post(
                config.webhook_url,
                data=json.dumps(payload),
                headers={"Content-Type": "application/json"},
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status < 300:
                    return True
                logger.warning("Slack webhook returned %d", resp.status)
                return False
    except Exception as exc:
        logger.error("Failed to send Slack alert: %s", exc)
        return False


class AlertRouter:
    """Routes health records to alert channels with deduplication.

    Only alerts once per target failure. Clears alert state on recovery.
    """

    __slots__ = ("_signal_cfg", "_ntfy_cfg", "_slack_cfg", "_alerted_targets")

    def __init__(
        self,
        signal_cfg: SignalConfig,
        ntfy_cfg: NtfyConfig,
        slack_cfg: SlackConfig | None = None,
    ) -> None:
        self._signal_cfg = signal_cfg
        self._ntfy_cfg = ntfy_cfg
        self._slack_cfg = slack_cfg or SlackConfig()
        self._alerted_targets: set[str] = set()

    async def _broadcast(self, title: str, message: str) -> None:
        """Send an alert to all configured channels."""
        await send_signal_message(self._signal_cfg, message)
        await send_ntfy_alert(self._ntfy_cfg, title, message)
        await send_slack_alert(self._slack_cfg, message)

    async def process(self, record: HealthRecord) -> None:
        """Process a health record and fire alerts if needed."""
        if record.is_healthy:
            if record.target_name in self._alerted_targets:
                self._alerted_targets.discard(record.target_name)
                msg = f":white_check_mark: {record.target_name} has recovered ({record.response_time_ms:.0f}ms)"
                await self._broadcast(f"{record.target_name} Recovered", msg)
            return

        # Unhealthy — only alert if we haven't already
        if record.target_name in self._alerted_targets:
            return

        self._alerted_targets.add(record.target_name)
        error_detail = f" - {record.error}" if record.error else ""
        msg = (
            f":rotating_light: {record.target_name} is {record.status}{error_detail}\n"
            f"Timestamp: {record.timestamp.isoformat()}"
        )
        await self._broadcast(f"{record.target_name} DOWN", msg)

    async def send_deploy_alert(self, message: str) -> None:
        """Send a deploy-related alert to all channels (no dedup)."""
        await self._broadcast("Deploy Update", message)

    async def send_infra_alert(self, message: str) -> None:
        """Send an infrastructure alert to all channels (no dedup)."""
        await self._broadcast("Infrastructure Alert", message)
