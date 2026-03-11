from datetime import datetime, timezone

from sentinel.health import HealthRecord, HealthRingBuffer, ServiceStatus


def test_ring_buffer_add_and_latest() -> None:
    buf = HealthRingBuffer(max_size=5)
    record = HealthRecord(
        target_name="ADGA",
        status=ServiceStatus.HEALTHY,
        response_time_ms=42.0,
        timestamp=datetime.now(timezone.utc),
    )
    buf.add(record)
    assert buf.latest("ADGA") == record
    assert len(buf) == 1


def test_ring_buffer_eviction() -> None:
    buf = HealthRingBuffer(max_size=3)
    for i in range(5):
        buf.add(HealthRecord(
            target_name="ADGA",
            status=ServiceStatus.HEALTHY,
            response_time_ms=float(i),
            timestamp=datetime.now(timezone.utc),
        ))
    assert len(buf) == 3
    assert buf.latest("ADGA").response_time_ms == 4.0


def test_ring_buffer_history_per_target() -> None:
    buf = HealthRingBuffer(max_size=10)
    for name in ["ADGA", "Blacksmith", "ADGA"]:
        buf.add(HealthRecord(
            target_name=name,
            status=ServiceStatus.HEALTHY,
            response_time_ms=1.0,
            timestamp=datetime.now(timezone.utc),
        ))
    assert len(buf.history("ADGA")) == 2
    assert len(buf.history("Blacksmith")) == 1


def test_ring_buffer_latest_returns_none_for_unknown() -> None:
    buf = HealthRingBuffer(max_size=5)
    assert buf.latest("Unknown") is None


def test_health_record_unhealthy() -> None:
    record = HealthRecord(
        target_name="ADGA",
        status=ServiceStatus.UNREACHABLE,
        response_time_ms=0.0,
        timestamp=datetime.now(timezone.utc),
        error="Connection refused",
    )
    assert record.is_healthy is False


def test_health_summary() -> None:
    buf = HealthRingBuffer(max_size=10)
    buf.add(HealthRecord(
        target_name="ADGA",
        status=ServiceStatus.HEALTHY,
        response_time_ms=50.0,
        timestamp=datetime.now(timezone.utc),
    ))
    buf.add(HealthRecord(
        target_name="Blacksmith",
        status=ServiceStatus.UNREACHABLE,
        response_time_ms=0.0,
        timestamp=datetime.now(timezone.utc),
        error="timeout",
    ))
    summary = buf.summary()
    assert "ADGA" in summary
    assert "HEALTHY" in summary
    assert "UNREACHABLE" in summary
