"""GitHub Actions workflow monitor — tracks deploy status and alerts on changes."""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone

import aiohttp

from sentinel.config import GitHubConfig

logger = logging.getLogger("sentinel.github_monitor")

_API_BASE = "https://api.github.com"
_TIMEOUT = aiohttp.ClientTimeout(total=15)


@dataclass
class WorkflowRun:
    """Represents a GitHub Actions workflow run."""
    id: int
    status: str  # queued, in_progress, completed
    conclusion: str | None  # success, failure, cancelled, etc.
    head_sha: str
    html_url: str
    created_at: str
    updated_at: str

    @property
    def is_done(self) -> bool:
        return self.status == "completed"

    @property
    def succeeded(self) -> bool:
        return self.is_done and self.conclusion == "success"

    @property
    def failed(self) -> bool:
        return self.is_done and self.conclusion == "failure"

    @property
    def short_sha(self) -> str:
        return self.head_sha[:8]

    @classmethod
    def from_api(cls, data: dict) -> "WorkflowRun":
        return cls(
            id=data["id"],
            status=data["status"],
            conclusion=data.get("conclusion"),
            head_sha=data["head_sha"],
            html_url=data["html_url"],
            created_at=data["created_at"],
            updated_at=data["updated_at"],
        )


class GitHubActionsMonitor:
    """Monitors GitHub Actions deploy workflows for status changes.

    Tracks the latest known run and alerts when:
    - A new run starts (in_progress)
    - A run completes successfully
    - A run fails
    """

    __slots__ = ("_config", "_last_seen_run_id", "_last_seen_status")

    def __init__(self, config: GitHubConfig) -> None:
        self._config = config
        self._last_seen_run_id: int | None = None
        self._last_seen_status: str | None = None  # "in_progress", "success", "failure"

    async def check(self) -> list[str]:
        """Poll GitHub Actions and return alert messages for any status changes.

        Returns a list of human-readable messages (empty if no changes).
        """
        if not self._config.enabled or not self._config.repo:
            return []

        run = await self._fetch_latest_run()
        if run is None:
            return []

        messages: list[str] = []
        effective_status = run.conclusion if run.is_done else run.status

        # New run we haven't seen
        if run.id != self._last_seen_run_id:
            self._last_seen_run_id = run.id
            self._last_seen_status = effective_status

            if run.is_done:
                if run.succeeded:
                    messages.append(
                        f":white_check_mark: *Deploy succeeded* (`{run.short_sha}`)\n"
                        f"{run.html_url}"
                    )
                elif run.failed:
                    messages.append(
                        f":x: *Deploy FAILED* (`{run.short_sha}`)\n"
                        f"{run.html_url}"
                    )
                else:
                    messages.append(
                        f":warning: Deploy completed with `{run.conclusion}` (`{run.short_sha}`)\n"
                        f"{run.html_url}"
                    )
            else:
                messages.append(
                    f":rocket: *Deploy started* (`{run.short_sha}`)\n"
                    f"{run.html_url}"
                )

        # Same run, status changed
        elif effective_status != self._last_seen_status:
            old_status = self._last_seen_status
            self._last_seen_status = effective_status

            if run.succeeded:
                messages.append(
                    f":white_check_mark: *Deploy succeeded* (`{run.short_sha}`)\n"
                    f"{run.html_url}"
                )
            elif run.failed:
                messages.append(
                    f":x: *Deploy FAILED* (`{run.short_sha}`)\n"
                    f"{run.html_url}"
                )
            elif run.is_done:
                messages.append(
                    f":warning: Deploy finished with `{run.conclusion}` (`{run.short_sha}`)\n"
                    f"{run.html_url}"
                )

        return messages

    async def _fetch_latest_run(self) -> WorkflowRun | None:
        """Fetch the most recent workflow run from GitHub API."""
        try:
            headers = {
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            }
            if self._config.token:
                headers["Authorization"] = f"Bearer {self._config.token}"

            url = (
                f"{_API_BASE}/repos/{self._config.repo}"
                f"/actions/workflows/{self._config.workflow}/runs"
                f"?per_page=1&branch=main"
            )

            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=_TIMEOUT) as resp:
                    if resp.status != 200:
                        logger.warning(
                            "GitHub API returned %d: %s",
                            resp.status,
                            await resp.text(),
                        )
                        return None
                    data = await resp.json()

            runs = data.get("workflow_runs", [])
            if not runs:
                return None

            return WorkflowRun.from_api(runs[0])

        except Exception as exc:
            logger.error("Failed to fetch GitHub workflow runs: %s", exc)
            return None

    async def get_status_summary(self) -> str:
        """Get a human-readable summary of the latest deploy status."""
        run = await self._fetch_latest_run()
        if run is None:
            return "GitHub Actions: No recent deploy runs found."

        if run.is_done:
            icon = ":white_check_mark:" if run.succeeded else ":x:"
            return f"GitHub Actions: {icon} Last deploy `{run.short_sha}` — {run.conclusion} ({run.updated_at})"
        else:
            return f"GitHub Actions: :hourglass_flowing_sand: Deploy `{run.short_sha}` in progress ({run.status})"
