"""Signal message listener and LLM-powered response generation."""

import logging
from typing import Any

import aiohttp
import anthropic

from sentinel.config import SignalConfig
from sentinel.health import HealthRingBuffer

logger = logging.getLogger("sentinel.signal_listener")

_SYSTEM_PROMPT = """\
You are Sentinel, a production monitoring agent for the AtelierLabs platform. \
You monitor service health endpoints, GitHub Actions deploy pipelines, and \
Hetzner Cloud server infrastructure.

You will be given current health data, deploy status, and server status. \
Answer the user's question based on this data. Be concise, direct, and factual. \
If services are down, say so clearly. If everything is healthy, confirm briefly.

Keep responses under 300 characters (Signal message limit friendly).\
"""


async def fetch_incoming_messages(config: SignalConfig) -> list[dict[str, Any]]:
    """Fetch unread messages from signal-cli-rest-api."""
    if not config.enabled:
        return []
    try:
        async with aiohttp.ClientSession() as session:
            url = f"{config.api_url}/v1/receive/{config.phone_number}"
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status != 200:
                    return []
                raw = await resp.json()

        messages = []
        for item in raw:
            envelope = item.get("envelope", {})
            data_msg = envelope.get("dataMessage")
            if data_msg and data_msg.get("message"):
                messages.append({
                    "sender": envelope.get("source", ""),
                    "text": data_msg["message"],
                    "timestamp": data_msg.get("timestamp", 0),
                })
        return messages
    except Exception as exc:
        logger.error("Failed to fetch Signal messages: %s", exc)
        return []


async def generate_health_response(
    query: str,
    buffer: HealthRingBuffer,
    *,
    github_monitor: Any = None,
    hetzner_monitor: Any = None,
) -> str:
    """Generate an LLM-powered response about system status.

    Includes health check data plus GitHub Actions and Hetzner status
    when monitors are available. Falls back to plain summary if the
    LLM call fails.
    """
    sections = [buffer.summary()]

    # Add GitHub deploy status if available
    if github_monitor:
        try:
            gh_summary = await github_monitor.get_status_summary()
            sections.append(gh_summary)
        except Exception:
            pass

    # Add Hetzner server status if available
    if hetzner_monitor:
        try:
            hz_summary = await hetzner_monitor.get_status_summary()
            sections.append(hz_summary)
        except Exception:
            pass

    full_summary = "\n\n".join(sections)

    try:
        client = anthropic.AsyncAnthropic()
        response = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=256,
            system=_SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": f"Current system data:\n{full_summary}\n\nUser question: {query}",
                }
            ],
        )
        return response.content[0].text
    except Exception as exc:
        logger.warning("LLM call failed (%s), falling back to summary", exc)
        return full_summary
