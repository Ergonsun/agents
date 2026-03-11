"""Alert routing via Signal and email with deduplication."""

import logging
from email.message import EmailMessage

import aiohttp
import aiosmtplib

from sentinel.config import EmailConfig, SignalConfig
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


async def send_email_alert(config: EmailConfig, subject: str, body: str) -> bool:
    """Send an email alert via SMTP. Returns True on success."""
    if not config.enabled:
        return False
    try:
        msg = EmailMessage()
        msg["From"] = config.from_addr
        msg["To"] = config.to_addr
        msg["Subject"] = f"[Sentinel] {subject}"
        msg.set_content(body)

        await aiosmtplib.send(
            msg,
            hostname=config.smtp_host,
            port=config.smtp_port,
            username=config.username,
            password=config.password,
            start_tls=True,
        )
        return True
    except Exception as exc:
        logger.error("Failed to send email: %s", exc)
        return False


class AlertRouter:
    """Routes health records to alert channels with deduplication.

    Only alerts once per target failure. Clears alert state on recovery.
    """

    __slots__ = ("_signal_cfg", "_email_cfg", "_alerted_targets")

    def __init__(self, signal_cfg: SignalConfig, email_cfg: EmailConfig) -> None:
        self._signal_cfg = signal_cfg
        self._email_cfg = email_cfg
        self._alerted_targets: set[str] = set()

    async def process(self, record: HealthRecord) -> None:
        """Process a health record and fire alerts if needed."""
        if record.is_healthy:
            if record.target_name in self._alerted_targets:
                self._alerted_targets.discard(record.target_name)
                msg = f"✅ {record.target_name} has recovered ({record.response_time_ms:.0f}ms)"
                await send_signal_message(self._signal_cfg, msg)
                await send_email_alert(self._email_cfg, f"{record.target_name} Recovered", msg)
            return

        # Unhealthy — only alert if we haven't already
        if record.target_name in self._alerted_targets:
            return

        self._alerted_targets.add(record.target_name)
        error_detail = f" - {record.error}" if record.error else ""
        msg = (
            f"🚨 {record.target_name} is {record.status}{error_detail}\n"
            f"Timestamp: {record.timestamp.isoformat()}"
        )
        await send_signal_message(self._signal_cfg, msg)
        await send_email_alert(self._email_cfg, f"{record.target_name} DOWN", msg)
