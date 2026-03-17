import pytest


@pytest.fixture
def sample_config() -> dict:
    """Minimal valid config for testing."""
    return {
        "targets": [
            {"name": "ADGA", "url": "http://localhost:8000/health"},
            {"name": "Blacksmith", "url": "http://localhost:3000/health"},
        ],
        "poll_interval_seconds": 300,
        "signal": {
            "enabled": True,
            "api_url": "http://localhost:8080",
            "phone_number": "+1234567890",
            "recipient": "+0987654321",
        },
        "ntfy": {
            "enabled": True,
            "server_url": "https://ntfy.sh",
            "topic": "test-topic",
            "priority": "high",
        },
        "slack": {
            "enabled": True,
            "webhook_url": "https://hooks.slack.com/services/T00/B00/xxx",
            "channel": "#sentinel-alerts",
        },
        "github": {
            "enabled": True,
            "repo": "Ergonsun/adga",
            "workflow": "deploy.yml",
            "token": "ghp_test123",
        },
        "hetzner": {
            "enabled": True,
            "token": "hcloud_test_token",
            "server_names": ["adga-prod", "blacksmith-prod"],
        },
    }


@pytest.fixture
def github_run_success() -> dict:
    """GitHub API response for a successful workflow run."""
    return {
        "workflow_runs": [
            {
                "id": 12345,
                "status": "completed",
                "conclusion": "success",
                "head_sha": "d1c0b84e36653859da591e611c1d2517911540ce",
                "html_url": "https://github.com/Ergonsun/adga/actions/runs/12345",
                "created_at": "2026-03-17T14:28:11Z",
                "updated_at": "2026-03-17T14:45:00Z",
            }
        ]
    }


@pytest.fixture
def github_run_in_progress() -> dict:
    """GitHub API response for an in-progress workflow run."""
    return {
        "workflow_runs": [
            {
                "id": 12346,
                "status": "in_progress",
                "conclusion": None,
                "head_sha": "abc12345def67890abcdef1234567890abcdef12",
                "html_url": "https://github.com/Ergonsun/adga/actions/runs/12346",
                "created_at": "2026-03-17T15:00:00Z",
                "updated_at": "2026-03-17T15:05:00Z",
            }
        ]
    }


@pytest.fixture
def hetzner_servers_response() -> dict:
    """Hetzner API response for server listing."""
    return {
        "servers": [
            {
                "id": 1001,
                "name": "adga-prod",
                "status": "running",
                "server_type": {"name": "cx22"},
                "public_net": {"ipv4": {"ip": "46.62.196.38"}, "ipv6": None},
                "datacenter": {"name": "fsn1-dc14"},
            },
            {
                "id": 1002,
                "name": "blacksmith-prod",
                "status": "running",
                "server_type": {"name": "cx32"},
                "public_net": {"ipv4": {"ip": "46.62.216.88"}, "ipv6": None},
                "datacenter": {"name": "fsn1-dc14"},
            },
        ]
    }
