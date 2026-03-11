"""Health check records and fixed-size ring buffer."""

from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum


class ServiceStatus(StrEnum):
    HEALTHY = "HEALTHY"
    UNHEALTHY = "UNHEALTHY"
    UNREACHABLE = "UNREACHABLE"


@dataclass(frozen=True, slots=True)
class HealthRecord:
    target_name: str
    status: ServiceStatus
    response_time_ms: float
    timestamp: datetime
    status_code: int | None = None
    error: str | None = None

    @property
    def is_healthy(self) -> bool:
        return self.status == ServiceStatus.HEALTHY


class HealthRingBuffer:
    """Fixed-size ring buffer for health records. Thread-safe via GIL for single-writer."""

    __slots__ = ("_buffer", "_max_size")

    def __init__(self, max_size: int = 100) -> None:
        self._buffer: deque[HealthRecord] = deque(maxlen=max_size)
        self._max_size = max_size

    def add(self, record: HealthRecord) -> None:
        self._buffer.append(record)

    def latest(self, target_name: str) -> HealthRecord | None:
        for record in reversed(self._buffer):
            if record.target_name == target_name:
                return record
        return None

    def history(self, target_name: str) -> list[HealthRecord]:
        return [r for r in self._buffer if r.target_name == target_name]

    def all_records(self) -> list[HealthRecord]:
        return list(self._buffer)

    def summary(self) -> str:
        """Human-readable summary of latest status per target."""
        seen: dict[str, HealthRecord] = {}
        for record in reversed(self._buffer):
            if record.target_name not in seen:
                seen[record.target_name] = record

        if not seen:
            return "No health data collected yet."

        lines = ["Service Health Summary", "=" * 40]
        for name, rec in sorted(seen.items()):
            status_icon = "OK" if rec.is_healthy else "DOWN"
            line = f"  [{status_icon}] {name}: {rec.status}"
            if rec.response_time_ms > 0:
                line += f" ({rec.response_time_ms:.0f}ms)"
            if rec.error:
                line += f" - {rec.error}"
            lines.append(line)
        lines.append(f"  Last check: {max(seen.values(), key=lambda r: r.timestamp).timestamp.isoformat()}")
        return "\n".join(lines)

    def __len__(self) -> int:
        return len(self._buffer)
