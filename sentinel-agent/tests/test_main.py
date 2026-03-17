import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from sentinel.__main__ import _run
from sentinel.config import SentinelConfig, TargetConfig, SignalConfig, NtfyConfig


@pytest.mark.asyncio
async def test_run_loads_config_and_polls(sample_config: dict) -> None:
    """Test that main loop loads config and runs at least one poll cycle."""
    config = SentinelConfig.from_dict(sample_config)

    poll_called = False

    async def fake_poll(session, targets, buffer):
        nonlocal poll_called
        poll_called = True
        from sentinel.health import HealthRecord, ServiceStatus
        from datetime import datetime, timezone
        records = []
        for t in targets:
            records.append(HealthRecord(
                target_name=t.name,
                status=ServiceStatus.HEALTHY,
                response_time_ms=10,
                timestamp=datetime.now(timezone.utc),
            ))
            buffer.add(records[-1])
        return records

    async def fake_shutdown(*args, **kwargs):
        raise KeyboardInterrupt()

    with (
        patch("sentinel.__main__.load_config", return_value=config),
        patch("sentinel.__main__.poll_all_targets", side_effect=fake_poll),
        patch("sentinel.__main__.fetch_incoming_messages", return_value=[]),
        patch("asyncio.sleep", side_effect=fake_shutdown),
    ):
        with pytest.raises(KeyboardInterrupt):
            await _run()

    assert poll_called


@pytest.mark.asyncio
async def test_run_triggers_setup_when_no_config() -> None:
    """Test that first-run setup is triggered when no config exists."""
    config = SentinelConfig(
        targets=[TargetConfig(name="Test", url="http://localhost/health")],
    )

    with (
        patch("sentinel.__main__.load_config", return_value=None),
        patch("sentinel.__main__.run_first_time_setup", new_callable=AsyncMock, return_value=config) as mock_setup,
        patch("sentinel.__main__.poll_all_targets", new_callable=AsyncMock, return_value=[]),
        patch("sentinel.__main__.fetch_incoming_messages", return_value=[]),
        patch("asyncio.sleep", side_effect=KeyboardInterrupt()),
    ):
        with pytest.raises(KeyboardInterrupt):
            await _run()

    mock_setup.assert_called_once()
