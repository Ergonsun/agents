"""Tests for sentinel.hetzner_monitor — Hetzner Cloud server monitoring."""

import pytest
from aioresponses import aioresponses

from sentinel.config import HetznerMonitorConfig
from sentinel.hetzner_monitor import HetznerMonitor


@pytest.fixture
def hetzner_cfg() -> HetznerMonitorConfig:
    return HetznerMonitorConfig(
        enabled=True,
        token="hcloud_test_token",
        server_names=["adga-prod", "blacksmith-prod"],
    )


@pytest.mark.asyncio
async def test_first_check_no_alerts(hetzner_cfg: HetznerMonitorConfig, hetzner_servers_response: dict) -> None:
    """First check records state but doesn't alert."""
    monitor = HetznerMonitor(hetzner_cfg)
    url = "https://api.hetzner.cloud/v1/servers"

    with aioresponses() as mocked:
        mocked.get(url, payload=hetzner_servers_response)
        messages = await monitor.check()

    assert messages == []
    assert monitor._last_statuses["adga-prod"] == "running"
    assert monitor._last_statuses["blacksmith-prod"] == "running"


@pytest.mark.asyncio
async def test_detects_server_down(hetzner_cfg: HetznerMonitorConfig, hetzner_servers_response: dict) -> None:
    """Detects when a server goes from running to off."""
    monitor = HetznerMonitor(hetzner_cfg)
    url = "https://api.hetzner.cloud/v1/servers"

    # First check — baseline
    with aioresponses() as mocked:
        mocked.get(url, payload=hetzner_servers_response)
        await monitor.check()

    # Second check — adga-prod is off
    down_response = {
        "servers": [
            {**hetzner_servers_response["servers"][0], "status": "off"},
            hetzner_servers_response["servers"][1],
        ]
    }
    with aioresponses() as mocked:
        mocked.get(url, payload=down_response)
        messages = await monitor.check()

    assert len(messages) == 1
    assert "adga-prod" in messages[0]
    assert "no longer running" in messages[0]


@pytest.mark.asyncio
async def test_detects_server_recovery(hetzner_cfg: HetznerMonitorConfig, hetzner_servers_response: dict) -> None:
    """Detects when a server comes back online."""
    monitor = HetznerMonitor(hetzner_cfg)
    monitor._last_statuses["adga-prod"] = "off"
    monitor._last_statuses["blacksmith-prod"] = "running"
    url = "https://api.hetzner.cloud/v1/servers"

    with aioresponses() as mocked:
        mocked.get(url, payload=hetzner_servers_response)
        messages = await monitor.check()

    assert len(messages) == 1
    assert "adga-prod" in messages[0]
    assert "running" in messages[0]


@pytest.mark.asyncio
async def test_no_alert_when_stable(hetzner_cfg: HetznerMonitorConfig, hetzner_servers_response: dict) -> None:
    """No alerts when status hasn't changed."""
    monitor = HetznerMonitor(hetzner_cfg)
    monitor._last_statuses["adga-prod"] = "running"
    monitor._last_statuses["blacksmith-prod"] = "running"
    url = "https://api.hetzner.cloud/v1/servers"

    with aioresponses() as mocked:
        mocked.get(url, payload=hetzner_servers_response)
        messages = await monitor.check()

    assert messages == []


@pytest.mark.asyncio
async def test_disabled_returns_empty() -> None:
    monitor = HetznerMonitor(HetznerMonitorConfig(enabled=False))
    messages = await monitor.check()
    assert messages == []


@pytest.mark.asyncio
async def test_status_summary(hetzner_cfg: HetznerMonitorConfig, hetzner_servers_response: dict) -> None:
    monitor = HetznerMonitor(hetzner_cfg)
    url = "https://api.hetzner.cloud/v1/servers"

    with aioresponses() as mocked:
        mocked.get(url, payload=hetzner_servers_response)
        summary = await monitor.get_status_summary()

    assert "adga-prod" in summary
    assert "blacksmith-prod" in summary
    assert "running" in summary
