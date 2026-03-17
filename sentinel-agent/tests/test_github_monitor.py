"""Tests for sentinel.github_monitor — GitHub Actions deploy monitoring."""

import pytest
from aioresponses import aioresponses

from sentinel.config import GitHubConfig
from sentinel.github_monitor import GitHubActionsMonitor, WorkflowRun


@pytest.fixture
def github_cfg() -> GitHubConfig:
    return GitHubConfig(
        enabled=True,
        repo="Ergonsun/adga",
        workflow="deploy.yml",
        token="ghp_test",
    )


@pytest.mark.asyncio
async def test_detects_new_successful_deploy(github_cfg: GitHubConfig, github_run_success: dict) -> None:
    monitor = GitHubActionsMonitor(github_cfg)
    url = "https://api.github.com/repos/Ergonsun/adga/actions/workflows/deploy.yml/runs?per_page=1&branch=main"

    with aioresponses() as mocked:
        mocked.get(url, payload=github_run_success)
        messages = await monitor.check()

    assert len(messages) == 1
    assert "succeeded" in messages[0]
    assert "d1c0b84e" in messages[0]


@pytest.mark.asyncio
async def test_detects_new_deploy_started(github_cfg: GitHubConfig, github_run_in_progress: dict) -> None:
    monitor = GitHubActionsMonitor(github_cfg)
    url = "https://api.github.com/repos/Ergonsun/adga/actions/workflows/deploy.yml/runs?per_page=1&branch=main"

    with aioresponses() as mocked:
        mocked.get(url, payload=github_run_in_progress)
        messages = await monitor.check()

    assert len(messages) == 1
    assert "started" in messages[0]


@pytest.mark.asyncio
async def test_no_duplicate_on_same_run(github_cfg: GitHubConfig, github_run_success: dict) -> None:
    monitor = GitHubActionsMonitor(github_cfg)
    url = "https://api.github.com/repos/Ergonsun/adga/actions/workflows/deploy.yml/runs?per_page=1&branch=main"

    with aioresponses() as mocked:
        mocked.get(url, payload=github_run_success)
        messages1 = await monitor.check()

    with aioresponses() as mocked:
        mocked.get(url, payload=github_run_success)
        messages2 = await monitor.check()

    assert len(messages1) == 1
    assert len(messages2) == 0  # No change, no alert


@pytest.mark.asyncio
async def test_detects_status_transition(github_cfg: GitHubConfig, github_run_in_progress: dict, github_run_success: dict) -> None:
    """Detect when a run transitions from in_progress to completed."""
    monitor = GitHubActionsMonitor(github_cfg)
    url = "https://api.github.com/repos/Ergonsun/adga/actions/workflows/deploy.yml/runs?per_page=1&branch=main"

    # Same run ID but different status
    github_run_success["workflow_runs"][0]["id"] = github_run_in_progress["workflow_runs"][0]["id"]
    github_run_success["workflow_runs"][0]["head_sha"] = github_run_in_progress["workflow_runs"][0]["head_sha"]

    with aioresponses() as mocked:
        mocked.get(url, payload=github_run_in_progress)
        messages1 = await monitor.check()

    with aioresponses() as mocked:
        mocked.get(url, payload=github_run_success)
        messages2 = await monitor.check()

    assert len(messages1) == 1  # "started"
    assert len(messages2) == 1  # "succeeded"
    assert "succeeded" in messages2[0]


@pytest.mark.asyncio
async def test_disabled_returns_empty(github_run_success: dict) -> None:
    monitor = GitHubActionsMonitor(GitHubConfig(enabled=False))
    messages = await monitor.check()
    assert messages == []


@pytest.mark.asyncio
async def test_status_summary(github_cfg: GitHubConfig, github_run_success: dict) -> None:
    monitor = GitHubActionsMonitor(github_cfg)
    url = "https://api.github.com/repos/Ergonsun/adga/actions/workflows/deploy.yml/runs?per_page=1&branch=main"

    with aioresponses() as mocked:
        mocked.get(url, payload=github_run_success)
        summary = await monitor.get_status_summary()

    assert "d1c0b84e" in summary
    assert "success" in summary
