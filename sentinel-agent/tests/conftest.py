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
        "email": {
            "enabled": True,
            "smtp_host": "smtp.example.com",
            "smtp_port": 587,
            "username": "sentinel@example.com",
            "password": "secret",
            "from_addr": "sentinel@example.com",
            "to_addr": "roger@example.com",
        },
    }
