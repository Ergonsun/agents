"""Tests for sentinel.alerting — Signal, email, and alert router."""

import pytest
from aioresponses import aioresponses
from unittest.mock import AsyncMock, patch, MagicMock

from sentinel.alerting import (
    AlertRouter,
    send_signal_message,
    send_email_alert,
)
from sentinel.config import SignalConfig, EmailConfig
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
async def test_send_email_alert() -> None:
    email_cfg = EmailConfig(
        enabled=True,
        smtp_host="smtp.test.com",
        smtp_port=587,
        username="user",
        password="pass",
        from_addr="from@test.com",
        to_addr="to@test.com",
    )
    with patch("sentinel.alerting.aiosmtplib.send", new_callable=AsyncMock) as mock_send:
        result = await send_email_alert(email_cfg, "Service Down", "ADGA is unreachable")
    assert result is True
    mock_send.assert_called_once()


@pytest.mark.asyncio
async def test_send_email_disabled() -> None:
    email_cfg = EmailConfig(enabled=False)
    result = await send_email_alert(email_cfg, "Test", "Body")
    assert result is False


@pytest.mark.asyncio
async def test_alert_router_fires_on_new_failure() -> None:
    signal_cfg = SignalConfig(enabled=True, api_url="http://localhost:8080",
                              phone_number="+111", recipient="+222")
    email_cfg = EmailConfig(enabled=False)
    router = AlertRouter(signal_cfg, email_cfg)

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
    router = AlertRouter(signal_cfg, EmailConfig(enabled=False))
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
    router = AlertRouter(SignalConfig(enabled=False), EmailConfig(enabled=False))
    router._alerted_targets.add("ADGA")

    record = HealthRecord(
        target_name="ADGA",
        status=ServiceStatus.HEALTHY,
        response_time_ms=50,
        timestamp=datetime.now(timezone.utc),
    )
    await router.process(record)
    assert "ADGA" not in router._alerted_targets
