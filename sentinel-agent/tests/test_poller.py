# tests/test_poller.py
import pytest
from aiohttp import ClientSession
from aioresponses import aioresponses

from sentinel.config import TargetConfig
from sentinel.health import HealthRingBuffer, ServiceStatus
from sentinel.poller import poll_target, poll_all_targets


@pytest.mark.asyncio
async def test_poll_target_healthy() -> None:
    target = TargetConfig(name="ADGA", url="http://localhost:8000/health")
    with aioresponses() as mocked:
        mocked.get("http://localhost:8000/health", status=200, payload={"status": "ok"})
        async with ClientSession() as session:
            record = await poll_target(session, target)

    assert record.status == ServiceStatus.HEALTHY
    assert record.target_name == "ADGA"
    assert record.status_code == 200
    assert record.response_time_ms >= 0


@pytest.mark.asyncio
async def test_poll_target_unhealthy_status() -> None:
    target = TargetConfig(name="ADGA", url="http://localhost:8000/health")
    with aioresponses() as mocked:
        mocked.get("http://localhost:8000/health", status=503)
        async with ClientSession() as session:
            record = await poll_target(session, target)

    assert record.status == ServiceStatus.UNHEALTHY
    assert record.status_code == 503


@pytest.mark.asyncio
async def test_poll_target_unreachable() -> None:
    target = TargetConfig(name="ADGA", url="http://localhost:8000/health")
    with aioresponses() as mocked:
        mocked.get("http://localhost:8000/health", exception=ConnectionError("refused"))
        async with ClientSession() as session:
            record = await poll_target(session, target)

    assert record.status == ServiceStatus.UNREACHABLE
    assert record.error is not None


@pytest.mark.asyncio
async def test_poll_all_targets() -> None:
    targets = [
        TargetConfig(name="ADGA", url="http://localhost:8000/health"),
        TargetConfig(name="Blacksmith", url="http://localhost:3000/health"),
    ]
    buffer = HealthRingBuffer()
    with aioresponses() as mocked:
        mocked.get("http://localhost:8000/health", status=200)
        mocked.get("http://localhost:3000/health", status=200)
        async with ClientSession() as session:
            records = await poll_all_targets(session, targets, buffer)

    assert len(records) == 2
    assert len(buffer) == 2
    assert all(r.is_healthy for r in records)
