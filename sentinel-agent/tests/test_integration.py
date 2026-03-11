# tests/test_integration.py
"""Integration test: full cycle from config -> poll -> alert -> Signal reply."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from aiohttp import ClientSession
from aioresponses import aioresponses
from datetime import datetime, timezone

from sentinel.config import SentinelConfig, TargetConfig, SignalConfig, EmailConfig
from sentinel.health import HealthRingBuffer, HealthRecord, ServiceStatus
from sentinel.poller import poll_all_targets
from sentinel.alerting import AlertRouter
from sentinel.signal_listener import generate_health_response


@pytest.mark.asyncio
async def test_full_monitoring_cycle() -> None:
    """Simulate: poll -> detect failure -> alert -> recover -> clear alert."""
    config = SentinelConfig(
        targets=[
            TargetConfig(name="ADGA", url="http://localhost:8000/health"),
            TargetConfig(name="Blacksmith", url="http://localhost:3000/health"),
        ],
        signal=SignalConfig(
            enabled=True,
            api_url="http://localhost:8080",
            phone_number="+111",
            recipient="+222",
        ),
        email=EmailConfig(enabled=False),
    )

    buffer = HealthRingBuffer(max_size=100)
    router = AlertRouter(config.signal, config.email)

    # Cycle 1: Both healthy
    with aioresponses() as mocked:
        mocked.get("http://localhost:8000/health", status=200)
        mocked.get("http://localhost:3000/health", status=200)
        async with ClientSession() as session:
            records = await poll_all_targets(session, config.targets, buffer)
        for r in records:
            await router.process(r)

    assert len(router._alerted_targets) == 0

    # Cycle 2: ADGA goes down
    with aioresponses() as mocked:
        mocked.get("http://localhost:8000/health", status=503)
        mocked.get("http://localhost:3000/health", status=200)
        mocked.post("http://localhost:8080/v2/send", status=201)  # alert fires
        async with ClientSession() as session:
            records = await poll_all_targets(session, config.targets, buffer)
        for r in records:
            await router.process(r)

    assert "ADGA" in router._alerted_targets

    # Cycle 3: ADGA recovers
    with aioresponses() as mocked:
        mocked.get("http://localhost:8000/health", status=200)
        mocked.get("http://localhost:3000/health", status=200)
        mocked.post("http://localhost:8080/v2/send", status=201)  # recovery fires
        async with ClientSession() as session:
            records = await poll_all_targets(session, config.targets, buffer)
        for r in records:
            await router.process(r)

    assert "ADGA" not in router._alerted_targets
    assert len(buffer) == 6  # 2 per cycle x 3 cycles


@pytest.mark.asyncio
async def test_signal_query_with_health_data() -> None:
    """Simulate: user asks health question -> LLM responds with context."""
    buffer = HealthRingBuffer()
    buffer.add(HealthRecord(
        target_name="ADGA", status=ServiceStatus.HEALTHY,
        response_time_ms=35, timestamp=datetime.now(timezone.utc),
    ))
    buffer.add(HealthRecord(
        target_name="Blacksmith", status=ServiceStatus.HEALTHY,
        response_time_ms=22, timestamp=datetime.now(timezone.utc),
    ))

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="All systems healthy. ADGA: 35ms, Blacksmith: 22ms.")]
    mock_client.messages.create = AsyncMock(return_value=mock_response)

    with patch("sentinel.signal_listener.anthropic.AsyncAnthropic", return_value=mock_client):
        reply = await generate_health_response("How's everything?", buffer)

    assert "healthy" in reply.lower() or "ADGA" in reply
