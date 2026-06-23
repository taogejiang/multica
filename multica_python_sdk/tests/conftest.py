"""
Shared test fixtures and utilities for Multica SDK tests.
"""

import pytest
from unittest.mock import MagicMock, patch

from client import MulticaConfig, MulticaClient


@pytest.fixture
def config():
    """Create a test MulticaConfig."""
    return MulticaConfig(
        base_url="https://multica.example.com",
        api_token="mul_test1234567890",
        timeout=10,
    )


@pytest.fixture
def client(config):
    """Create a MulticaClient with mocked HTTP session."""
    with patch("client.requests.Session") as mock_session_class:
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session
        c = MulticaClient(config)
        c._mock_session = mock_session  # for direct access in tests
        yield c


@pytest.fixture
def mock_request(client):
    """Return the mock request method for stubbing HTTP responses."""
    return client._mock_session.request


# ── Sample data fixtures ──────────────────────────────────────

@pytest.fixture
def sample_workspace():
    return {
        "id": "ws-001",
        "name": "My Workspace",
        "slug": "my-workspace",
        "issue_prefix": "MW",
    }


@pytest.fixture
def sample_project():
    return {
        "id": "proj-001",
        "title": "auto_code_review",
        "status": "in_progress",
        "priority": "high",
        "issue_count": 5,
    }


@pytest.fixture
def sample_agent():
    return {
        "id": "agent-001",
        "name": "code_reviewer",
        "status": "active",
        "model": "claude-sonnet-4",
        "max_concurrent_tasks": 3,
    }


@pytest.fixture
def sample_issue():
    return {
        "id": "issue-001",
        "workspace_id": "ws-001",
        "number": 42,
        "identifier": "MW-42",
        "title": "Fix login page bug",
        "description": "Users cannot login with SSO",
        "status": "todo",
        "priority": "high",
        "assignee_type": "agent",
        "assignee_id": "agent-001",
        "creator_type": "user",
        "creator_id": "user-001",
        "project_id": "proj-001",
        "position": 100.0,
        "created_at": "2026-06-23T10:00:00Z",
        "updated_at": "2026-06-23T10:00:00Z",
    }
