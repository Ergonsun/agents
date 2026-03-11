import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from aioresponses import aioresponses

from sentinel.config import SignalConfig
from sentinel.health import HealthRecord, HealthRingBuffer, ServiceStatus
from sentinel.signal_listener import (
    fetch_incoming_messages,
    generate_health_response,
)
from datetime import datetime, timezone


@pytest.mark.asyncio
async def test_fetch_incoming_messages() -> None:
    config = SignalConfig(
        enabled=True,
        api_url="http://localhost:8080",
        phone_number="+111",
        recipient="+222",
    )
    with aioresponses() as mocked:
        mocked.get(
            "http://localhost:8080/v1/receive/+111",
            payload=[
                {
                    "envelope": {
                        "source": "+222",
                        "dataMessage": {"message": "status", "timestamp": 123},
                    }
                }
            ],
        )
        messages = await fetch_incoming_messages(config)

    assert len(messages) == 1
    assert messages[0]["text"] == "status"
    assert messages[0]["sender"] == "+222"


@pytest.mark.asyncio
async def test_fetch_incoming_messages_disabled() -> None:
    config = SignalConfig(enabled=False)
    messages = await fetch_incoming_messages(config)
    assert messages == []


@pytest.mark.asyncio
async def test_generate_health_response() -> None:
    buffer = HealthRingBuffer()
    buffer.add(HealthRecord(
        target_name="ADGA",
        status=ServiceStatus.HEALTHY,
        response_time_ms=42,
        timestamp=datetime.now(timezone.utc),
    ))

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="All systems operational. ADGA is healthy.")]
    mock_client.messages.create = AsyncMock(return_value=mock_response)

    with patch("sentinel.signal_listener.anthropic.AsyncAnthropic", return_value=mock_client):
        response = await generate_health_response("How is everything?", buffer)

    assert "ADGA" in response or "operational" in response


@pytest.mark.asyncio
async def test_generate_health_response_no_api_key() -> None:
    """Falls back to summary when no API key is available."""
    buffer = HealthRingBuffer()
    buffer.add(HealthRecord(
        target_name="ADGA",
        status=ServiceStatus.HEALTHY,
        response_time_ms=42,
        timestamp=datetime.now(timezone.utc),
    ))

    with patch("sentinel.signal_listener.anthropic.AsyncAnthropic", side_effect=Exception("No API key")):
        response = await generate_health_response("status?", buffer)

    # Falls back to plain summary
    assert "ADGA" in response
