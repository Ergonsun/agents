"""Hetzner Cloud server status monitor — tracks server health via API."""

import logging

import aiohttp

from sentinel.config import HetznerMonitorConfig

logger = logging.getLogger("sentinel.hetzner_monitor")

_API_BASE = "https://api.hetzner.cloud/v1"
_TIMEOUT = aiohttp.ClientTimeout(total=15)


class HetznerMonitor:
    """Monitors Hetzner Cloud server status and alerts on changes.

    Tracks server status (running, off, etc.) and alerts when a
    monitored server changes state unexpectedly.
    """

    __slots__ = ("_config", "_last_statuses")

    def __init__(self, config: HetznerMonitorConfig) -> None:
        self._config = config
        # server_name -> last known status
        self._last_statuses: dict[str, str] = {}

    async def check(self) -> list[str]:
        """Poll Hetzner API and return alert messages for status changes.

        Returns a list of human-readable messages (empty if no changes).
        """
        if not self._config.enabled or not self._config.token:
            return []

        servers = await self._fetch_servers()
        if servers is None:
            return []

        messages: list[str] = []
        monitored = set(self._config.server_names) if self._config.server_names else None

        for server in servers:
            name = server["name"]
            status = server["status"]
            ip = server.get("ipv4", "?")

            # If server_names is configured, only monitor those
            if monitored and name not in monitored:
                continue

            prev = self._last_statuses.get(name)
            self._last_statuses[name] = status

            if prev is None:
                # First check — no alert, just record
                continue

            if status != prev:
                if status == "running" and prev != "running":
                    messages.append(
                        f":white_check_mark: *{name}* is now running ({ip})"
                    )
                elif prev == "running" and status != "running":
                    messages.append(
                        f":rotating_light: *{name}* is no longer running — status: `{status}` ({ip})"
                    )
                else:
                    messages.append(
                        f":warning: *{name}* status changed: `{prev}` -> `{status}` ({ip})"
                    )

        # Check for servers that disappeared
        current_names = {s["name"] for s in servers}
        for name in list(self._last_statuses):
            if monitored and name not in monitored:
                continue
            if name not in current_names:
                messages.append(f":rotating_light: *{name}* has disappeared from Hetzner!")
                del self._last_statuses[name]

        return messages

    async def _fetch_servers(self) -> list[dict] | None:
        """Fetch all servers from Hetzner Cloud API."""
        try:
            headers = {
                "Authorization": f"Bearer {self._config.token}",
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{_API_BASE}/servers",
                    headers=headers,
                    timeout=_TIMEOUT,
                ) as resp:
                    if resp.status != 200:
                        logger.warning("Hetzner API returned %d", resp.status)
                        return None
                    data = await resp.json()

            return [
                {
                    "id": s["id"],
                    "name": s["name"],
                    "status": s["status"],
                    "server_type": s["server_type"]["name"],
                    "ipv4": s["public_net"]["ipv4"]["ip"] if s["public_net"].get("ipv4") else None,
                    "datacenter": s["datacenter"]["name"],
                }
                for s in data.get("servers", [])
            ]

        except Exception as exc:
            logger.error("Failed to fetch Hetzner servers: %s", exc)
            return None

    async def get_status_summary(self) -> str:
        """Get a human-readable summary of all monitored servers."""
        servers = await self._fetch_servers()
        if servers is None:
            return "Hetzner: Unable to fetch server status."

        monitored = set(self._config.server_names) if self._config.server_names else None

        lines = ["*Hetzner Cloud Servers:*"]
        for s in servers:
            if monitored and s["name"] not in monitored:
                continue
            icon = ":white_check_mark:" if s["status"] == "running" else ":x:"
            lines.append(f"  {icon} {s['name']}: `{s['status']}` ({s['server_type']}, {s['ipv4']})")

        return "\n".join(lines) if len(lines) > 1 else "Hetzner: No monitored servers found."
