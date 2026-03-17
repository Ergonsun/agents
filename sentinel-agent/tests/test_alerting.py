"""Tests for sentinel.alerting — Signal, ntfy, Slack, and alert router."""

import pytest
from aioresponses import aioresponses

from sentinel.alerting import (
    AlertRouter,
    send_signal_message,
    send_ntfy_alert,
    send_slack_alert,
)
from sentinel.config import SignalConfig, NtfyConfig, SlackConfig
from sentinel.health import HealthRecord, ServiceStatus
from datetime import datetime, timezone


@pytest.mark.asyncio
async def test_send_signal_message() -> None:
    signal_cfg = SignalConfig(
        enabled=True,
        api_url="http://localhost:8080",
        phone_number="+1111111111",
        recipient="+2222222222",
    )
    with aioresponses() as mocked:
        mocked.post("http://localhost:8080/v2/send", status=201)
        result = await send_signal_message(signal_cfg, "Test alert")
    assert result is True


@pytest.mark.asyncio
async def test_send_signal_message_disabled() -> None:
    signal_cfg = SignalConfig(enabled=False)
    result = await send_signal_message(signal_cfg, "Test")
    assert result is False


@pytest.mark.asyncio
async def test_send_ntfy_alert() -> None:
    ntfy_cfg = NtfyConfig(
        enabled=True,
        server_url="https://ntfy.sh",
        topic="test-topic",
        priority="high",
    )
    with aioresponses() as mocked:
        mocked.post("https://ntfy.sh/test-topic", status=200)
        result = await send_ntfy_alert(ntfy_cfg, "Service Down", "ADGA is unreachable")
    assert result is True


@pytest.mark.asyncio
async def test_send_ntfy_disabled() -> None:
    ntfy_cfg = NtfyConfig(enabled=False)
    result = await send_ntfy_alert(ntfy_cfg, "Test", "Body")
    assert result is False


@pytest.mark.asyncio
async def test_send_slack_alert() -> None:
    slack_cfg = SlackConfig(
        enabled=True,
        webhook_url="https://hooks.slack.com/services/T00/B00/xxx",
        channel="#sentinel-alerts",
    )
    with aioresponses() as mocked:
        mocked.post("https://hooks.slack.com/services/T00/B00/xxx", status=200)
        result = await send_slack_alert(slack_cfg, "Test alert to Slack")
    assert result is True


@pytest.mark.asyncio
async def test_send_slack_disabled() -> None:
    slack_cfg = SlackConfig(enabled=False)
    result = await send_slack_alert(slack_cfg, "Test")
    assert result is False


@pytest.mark.asyncio
async def test_alert_router_fires_on_new_failure() -> None:
    signal_cfg = SignalConfig(enabled=True, api_url="http://localhost:8080",
                              phone_number="+111", recipient="+222")
    ntfy_cfg = NtfyConfig(enabled=False)
    router = AlertRouter(signal_cfg, ntfy_cfg)

    record = HealthRecord(
        target_name="ADGA",
        status=ServiceStatus.UNREACHABLE,
        response_time_ms=0,
        timestamp=datetime.now(timezone.utc),
        error="Connection refused",
    )

    with aioresponses() as mocked:
        mocked.post("http://localhost:8080/v2/send", status=201)
        await router.process(record)

    assert "ADGA" in router._alerted_targets


@pytest.mark.asyncio
async def test_alert_router_no_duplicate_alerts() -> None:
    signal_cfg = SignalConfig(enabled=True, api_url="http://localhost:8080",
                              phone_number="+111", recipient="+222")
    router = AlertRouter(signal_cfg, NtfyConfig(enabled=False))
    router._alerted_targets.add("ADGA")  # Already alerted

    record = HealthRecord(
        target_name="ADGA",
        status=ServiceStatus.UNREACHABLE,
        response_time_ms=0,
        timestamp=datetime.now(timezone.utc),
    )
    # Should NOT fire any HTTP calls — no mocking needed, would fail if it tries
    await router.process(record)


@pytest.mark.asyncio
async def test_alert_router_clears_on_recovery() -> None:
    router = AlertRouter(SignalConfig(enabled=False), NtfyConfig(enabled=False))
    router._alerted_targets.add("ADGA")

    record = HealthRecord(
        target_name="ADGA",
        status=ServiceStatus.HEALTHY,
        response_time_ms=50,
        timestamp=datetime.now(timezone.utc),
    )
    await router.process(record)
    assert "ADGA" not in router._alerted_targets


@pytest.mark.asyncio
async def test_alert_router_broadcasts_to_all_channels() -> None:
    """Router sends to Signal, ntfy, AND Slack when all enabled."""
    signal_cfg = SignalConfig(enabled=True, api_url="http://localhost:8080",
                              phone_number="+111", recipient="+222")
    ntfy_cfg = NtfyConfig(enabled=True, server_url="https://ntfy.sh",
                           topic="test", priority="high")
    slack_cfg = SlackConfig(enabled=True,
                            webhook_url="https://hooks.slack.com/services/T00/B00/xxx")

    router = AlertRouter(signal_cfg, ntfy_cfg, slack_cfg)

    record = HealthRecord(
        target_name="ADGA",
        status=ServiceStatus.UNREACHABLE,
        response_time_ms=0,
        timestamp=datetime.now(timezone.utc),
    )

    with aioresponses() as mocked:
        mocked.post("http://localhost:8080/v2/send", status=201)
        mocked.post("https://ntfy.sh/test", status=200)
        mocked.post("https://hooks.slack.com/services/T00/B00/xxx", status=200)
        await router.process(record)

    assert "ADGA" in router._alerted_targets
