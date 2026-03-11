"""Async health check poller with timeout and error handling."""

import asyncio
import time
from datetime import datetime, timezone

from aiohttp import ClientSession, ClientTimeout

from sentinel.config import TargetConfig
from sentinel.health import HealthRecord, HealthRingBuffer, ServiceStatus

# 10 second timeout per health check — generous but bounded
_TIMEOUT = ClientTimeout(total=10)


async def poll_target(session: ClientSession, target: TargetConfig) -> HealthRecord:
    """Poll a single target and return a health record."""
    start = time.monotonic()
    try:
        async with session.get(target.url, timeout=_TIMEOUT) as resp:
            elapsed = (time.monotonic() - start) * 1000
            status = ServiceStatus.HEALTHY if resp.status < 400 else ServiceStatus.UNHEALTHY
            return HealthRecord(
                target_name=target.name,
                status=status,
                response_time_ms=elapsed,
                status_code=resp.status,
                timestamp=datetime.now(timezone.utc),
            )
    except Exception as exc:
        elapsed = (time.monotonic() - start) * 1000
        return HealthRecord(
            target_name=target.name,
            status=ServiceStatus.UNREACHABLE,
            response_time_ms=elapsed,
            timestamp=datetime.now(timezone.utc),
            error=str(exc),
        )


async def poll_all_targets(
    session: ClientSession,
    targets: list[TargetConfig],
    buffer: HealthRingBuffer,
) -> list[HealthRecord]:
    """Poll all targets concurrently and add results to the buffer."""
    records = await asyncio.gather(
        *(poll_target(session, t) for t in targets)
    )
    for record in records:
        buffer.add(record)
    return list(records)
