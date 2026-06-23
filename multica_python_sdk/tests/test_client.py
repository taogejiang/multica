"""Tests for client.py - MulticaClient API methods."""

import pytest
from unittest.mock import ANY, MagicMock

from client import MulticaClient, MulticaConfig, MulticaAPIError


def mock_response(json_data=None, status_code=200, text=None):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data if json_data is not None else {}
    resp.text = text or ""
    return resp


# ── MulticaConfig ─────────────────────────────────────────────

class TestMulticaConfig:
    def test_init_defaults(self):
        config = MulticaConfig(base_url="http://localhost", api_token="mul_test")
        assert config.base_url == "http://localhost"
        assert config.api_token == "mul_test"
        assert config.timeout == 30

    def test_init_custom_timeout(self):
        config = MulticaConfig(base_url="http://localhost", api_token="mul_test", timeout=60)
        assert config.timeout == 60

    def test_from_env(self, monkeypatch):
        monkeypatch.setenv("MULTICA_BASE_URL", "https://multica.example.com")
        monkeypatch.setenv("MULTICA_API_TOKEN", "mul_env1234567890")
        monkeypatch.setenv("MULTICA_TIMEOUT", "45")
        config = MulticaConfig.from_env()
        assert config.base_url == "https://multica.example.com"
        assert config.api_token == "mul_env1234567890"
        assert config.timeout == 45

    def test_from_env_trailing_slash_stripped(self, monkeypatch):
        monkeypatch.setenv("MULTICA_BASE_URL", "https://multica.example.com/")
        monkeypatch.setenv("MULTICA_API_TOKEN", "mul_test")
        config = MulticaConfig.from_env()
        assert config.base_url == "https://multica.example.com"

    def test_from_env_missing_base_url(self, monkeypatch):
        monkeypatch.delenv("MULTICA_BASE_URL", raising=False)
        monkeypatch.setenv("MULTICA_API_TOKEN", "mul_test")
        with pytest.raises(ValueError, match="MULTICA_BASE_URL"):
            MulticaConfig.from_env()

    def test_from_env_missing_api_token(self, monkeypatch):
        monkeypatch.setenv("MULTICA_BASE_URL", "https://multica.example.com")
        monkeypatch.delenv("MULTICA_API_TOKEN", raising=False)
        with pytest.raises(ValueError, match="MULTICA_API_TOKEN"):
            MulticaConfig.from_env()

    def test_from_env_default_timeout(self, monkeypatch):
        monkeypatch.setenv("MULTICA_BASE_URL", "https://multica.example.com")
        monkeypatch.setenv("MULTICA_API_TOKEN", "mul_test")
        monkeypatch.delenv("MULTICA_TIMEOUT", raising=False)
        config = MulticaConfig.from_env()
        assert config.timeout == 30


# ── MulticaAPIError ───────────────────────────────────────────

class TestMulticaAPIError:
    def test_basic(self):
        err = MulticaAPIError(404, "Not found")
        assert err.status_code == 404
        assert err.message == "Not found"
        assert str(err) == "HTTP 404: Not found"

    def test_with_details(self):
        err = MulticaAPIError(400, "Bad request", {"field": "title"})
        assert err.details == {"field": "title"}

    def test_details_default(self):
        err = MulticaAPIError(500, "Server error")
        assert err.details == {}


# ── Workspaces ────────────────────────────────────────────────

class TestWorkspaces:
    def test_list_workspaces(self, client, mock_request, sample_workspace):
        mock_request.return_value = mock_response([sample_workspace])
        result = client.list_workspaces()
        assert result == [sample_workspace]
        mock_request.assert_called_once()

    def test_list_workspaces_empty(self, client, mock_request):
        mock_request.return_value = mock_response([])
        result = client.list_workspaces()
        assert result == []

    def test_get_workspace(self, client, mock_request, sample_workspace):
        mock_request.return_value = mock_response(sample_workspace)
        result = client.get_workspace("ws-001")
        assert result == sample_workspace
        call_args = mock_request.call_args
        assert "ws-001" in call_args[0][1]


# ── Projects ──────────────────────────────────────────────────

class TestProjects:
    def test_list_projects(self, client, mock_request, sample_project):
        mock_request.return_value = mock_response({"projects": [sample_project], "total": 1})
        result = client.list_projects()
        assert result["projects"] == [sample_project]
        assert result["total"] == 1

    def test_list_projects_with_filters(self, client, mock_request):
        mock_request.return_value = mock_response({"projects": [], "total": 0})
        client.list_projects(workspace_id="ws-001", status="in_progress")
        call_args = mock_request.call_args
        assert call_args.kwargs["params"]["workspace_id"] == "ws-001"
        assert call_args.kwargs["params"]["status"] == "in_progress"

    def test_get_project(self, client, mock_request, sample_project):
        mock_request.return_value = mock_response(sample_project)
        result = client.get_project("proj-001")
        assert result == sample_project

    def test_search_projects(self, client, mock_request, sample_project):
        mock_request.return_value = mock_response([sample_project])
        result = client.search_projects("code_review")
        assert result == [sample_project]

    def test_find_project_by_name_exact(self, client, mock_request, sample_project):
        mock_request.return_value = mock_response({"projects": [sample_project], "total": 1})
        result = client.find_project_by_name("auto_code_review", workspace_id="ws-001")
        assert result == sample_project

    def test_find_project_by_name_case_insensitive(self, client, mock_request, sample_project):
        mock_request.return_value = mock_response({"projects": [sample_project], "total": 1})
        result = client.find_project_by_name("AUTO_CODE_REVIEW", workspace_id="ws-001")
        assert result == sample_project

    def test_find_project_by_name_partial(self, client, mock_request, sample_project):
        sample_project["title"] = "auto_code_review_v2"
        mock_request.return_value = mock_response({"projects": [sample_project], "total": 1})
        result = client.find_project_by_name("code_review", workspace_id="ws-001")
        assert result == sample_project

    def test_find_project_by_name_not_found(self, client, mock_request):
        mock_request.return_value = mock_response({"projects": [], "total": 0})
        result = client.find_project_by_name("nonexistent", workspace_id="ws-001")
        assert result is None

    def test_find_project_by_name_direct_list(self, client, mock_request, sample_project):
        mock_request.return_value = mock_response([sample_project])
        result = client.find_project_by_name("auto_code_review", workspace_id="ws-001")
        assert result == sample_project


# ── Agents ────────────────────────────────────────────────────

class TestAgents:
    def test_list_agents(self, client, mock_request, sample_agent):
        mock_request.return_value = mock_response([sample_agent])
        result = client.list_agents()
        assert result == [sample_agent]

    def test_list_agents_with_archived(self, client, mock_request):
        mock_request.return_value = mock_response([])
        client.list_agents(include_archived=True)
        call_args = mock_request.call_args
        assert call_args.kwargs["params"]["include_archived"] == "true"

    def test_get_agent(self, client, mock_request, sample_agent):
        mock_request.return_value = mock_response(sample_agent)
        result = client.get_agent("agent-001")
        assert result == sample_agent

    def test_find_agent_by_name_exact(self, client, mock_request, sample_agent):
        mock_request.return_value = mock_response([sample_agent])
        result = client.find_agent_by_name("code_reviewer", workspace_id="ws-001")
        assert result == sample_agent

    def test_find_agent_by_name_case_insensitive(self, client, mock_request, sample_agent):
        mock_request.return_value = mock_response([sample_agent])
        result = client.find_agent_by_name("CODE_REVIEWER", workspace_id="ws-001")
        assert result == sample_agent

    def test_find_agent_by_name_partial(self, client, mock_request, sample_agent):
        sample_agent["name"] = "code_reviewer_v2"
        mock_request.return_value = mock_response([sample_agent])
        result = client.find_agent_by_name("reviewer", workspace_id="ws-001")
        assert result == sample_agent

    def test_find_agent_by_name_not_found(self, client, mock_request):
        mock_request.return_value = mock_response([])
        result = client.find_agent_by_name("nonexistent", workspace_id="ws-001")
        assert result is None


# ── Issues ────────────────────────────────────────────────────

class TestIssues:
    def test_create_issue_minimal(self, client, mock_request, sample_issue):
        mock_request.return_value = mock_response(sample_issue)
        result = client.create_issue(title="Fix login page bug")
        assert result == sample_issue
        call_args = mock_request.call_args
        assert call_args.kwargs["json"]["title"] == "Fix login page bug"

    def test_create_issue_full(self, client, mock_request, sample_issue):
        mock_request.return_value = mock_response(sample_issue)
        client.create_issue(title="Fix bug", description="A bug to fix", status="todo",
                           priority="high", assignee_agent_id="agent-001",
                           project_id="proj-001", start_date="2026-07-01", due_date="2026-07-15")
        sent_json = mock_request.call_args.kwargs["json"]
        assert sent_json["assignee_type"] == "agent"
        assert sent_json["project_id"] == "proj-001"
        assert sent_json["start_date"] == "2026-07-01"

    def test_create_issue_with_user_assignee(self, client, mock_request, sample_issue):
        mock_request.return_value = mock_response(sample_issue)
        client.create_issue(title="Test", assignee_user_id="user-001")
        sent_json = mock_request.call_args.kwargs["json"]
        assert sent_json["assignee_type"] == "user"
        assert sent_json["assignee_id"] == "user-001"

    def test_create_issue_both_assignees_raises(self, client):
        with pytest.raises(ValueError, match="cannot be specified simultaneously"):
            client.create_issue(title="Test", assignee_agent_id="a-1", assignee_user_id="u-1")

    def test_create_issue_invalid_status(self, client):
        with pytest.raises(ValueError, match="Invalid status"):
            client.create_issue(title="Test", status="not_a_status")

    def test_create_issue_invalid_priority(self, client):
        with pytest.raises(ValueError, match="Invalid priority"):
            client.create_issue(title="Test", priority="super_high")

    def test_create_issue_with_attachments(self, client, mock_request, sample_issue):
        mock_request.return_value = mock_response(sample_issue)
        client.create_issue(title="Test", attachment_ids=["att-1", "att-2"])
        assert mock_request.call_args.kwargs["json"]["attachment_ids"] == ["att-1", "att-2"]

    def test_create_issue_allow_duplicate(self, client, mock_request, sample_issue):
        mock_request.return_value = mock_response(sample_issue)
        client.create_issue(title="Test", allow_duplicate=True)
        assert mock_request.call_args.kwargs["json"]["allow_duplicate"] is True

    def test_create_issue_with_parent(self, client, mock_request, sample_issue):
        mock_request.return_value = mock_response(sample_issue)
        client.create_issue(title="Subtask", parent_issue_id="issue-parent-001")
        assert mock_request.call_args.kwargs["json"]["parent_issue_id"] == "issue-parent-001"


# ── create_issue_by_name ─────────────────────────────────────

class TestCreateIssueByName:
    def test_by_name_success(self, client, mock_request, sample_project, sample_agent, sample_issue):
        mock_request.side_effect = [
            mock_response({"projects": [sample_project], "total": 1}),
            mock_response([sample_agent]),
            mock_response(sample_issue),
        ]
        result = client.create_issue_by_name(
            title="Test task", project_name="auto_code_review",
            agent_name="code_reviewer", workspace_id="ws-001", priority="high",
        )
        assert result == sample_issue
        assert mock_request.call_count == 3
        create_call = mock_request.call_args_list[-1]
        sent_json = create_call.kwargs["json"]
        assert sent_json["project_id"] == "proj-001"
        assert sent_json["assignee_type"] == "agent"
        assert sent_json["assignee_id"] == "agent-001"
        assert sent_json["priority"] == "high"

    def test_by_name_project_not_found(self, client, mock_request):
        mock_request.return_value = mock_response({"projects": [], "total": 0})
        with pytest.raises(ValueError, match="Project not found"):
            client.create_issue_by_name(
                title="Test", project_name="nonexistent", workspace_id="ws-001",
            )

    def test_by_name_agent_not_found(self, client, mock_request, sample_project):
        mock_request.side_effect = [
            mock_response({"projects": [sample_project], "total": 1}),
            mock_response([]),
        ]
        with pytest.raises(ValueError, match="Agent not found"):
            client.create_issue_by_name(
                title="Test", project_name="auto_code_review",
                agent_name="nonexistent", workspace_id="ws-001",
            )

    def test_by_name_workspace_required(self, client, mock_request):
        with pytest.raises(ValueError, match="workspace_id or workspace_slug"):
            client.find_project_by_name("auto_code_review")

    def test_by_name_no_project_or_agent(self, client, mock_request, sample_issue):
        mock_request.return_value = mock_response(sample_issue)
        result = client.create_issue_by_name(title="Just a task")
        assert result == sample_issue


# ── Quick create ──────────────────────────────────────────────

class TestQuickCreate:
    def test_quick_create_minimal(self, client, mock_request, sample_issue):
        mock_request.return_value = mock_response(sample_issue)
        result = client.quick_create_issue(title="Urgent fix")
        assert result == sample_issue
        assert mock_request.call_args.kwargs["json"] == {"title": "Urgent fix"}

    def test_quick_create_full(self, client, mock_request, sample_issue):
        mock_request.return_value = mock_response(sample_issue)
        client.quick_create_issue(title="Urgent", project_id="proj-001",
                                  assignee_agent_id="agent-001", description="ASAP")
        sent_json = mock_request.call_args.kwargs["json"]
        assert sent_json["project_id"] == "proj-001"
        assert sent_json["assignee_id"] == "agent-001"
        assert sent_json["assignee_type"] == "agent"


# ── CRUD ──────────────────────────────────────────────────────

class TestIssueCRUD:
    def test_get_issue(self, client, mock_request, sample_issue):
        mock_request.return_value = mock_response(sample_issue)
        assert client.get_issue("issue-001") == sample_issue

    def test_update_issue(self, client, mock_request, sample_issue):
        sample_issue["status"] = "in_progress"
        mock_request.return_value = mock_response(sample_issue)
        result = client.update_issue("issue-001", status="in_progress", priority="urgent")
        assert result["status"] == "in_progress"
        assert mock_request.call_args.kwargs["json"] == {"status": "in_progress", "priority": "urgent"}

    def test_list_issues(self, client, mock_request, sample_issue):
        mock_request.return_value = mock_response([sample_issue])
        assert client.list_issues() == [sample_issue]

    def test_list_issues_with_filters(self, client, mock_request):
        mock_request.return_value = mock_response([])
        client.list_issues(project_id="proj-001", status="todo", assignee_id="agent-001")
        params = mock_request.call_args.kwargs["params"]
        assert params["project_id"] == "proj-001"
        assert params["status"] == "todo"
        assert params["assignee_id"] == "agent-001"

    def test_search_issues(self, client, mock_request, sample_issue):
        mock_request.return_value = mock_response([sample_issue])
        assert client.search_issues("login") == [sample_issue]


# ── Comments ──────────────────────────────────────────────────

class TestComments:
    def test_create_comment(self, client, mock_request):
        comment_resp = {"id": "cmt-001", "content": "Looks good"}
        mock_request.return_value = mock_response(comment_resp)
        result = client.create_comment("issue-001", "Looks good")
        assert result == comment_resp
        assert mock_request.call_args.kwargs["json"] == {"content": "Looks good"}


# ── Labels ────────────────────────────────────────────────────

class TestLabels:
    def test_list_labels(self, client, mock_request):
        labels = [{"id": "lbl-1", "name": "bug"}]
        mock_request.return_value = mock_response(labels)
        assert client.list_labels() == labels

    def test_create_label_minimal(self, client, mock_request):
        label = {"id": "lbl-1", "name": "feature"}
        mock_request.return_value = mock_response(label)
        assert client.create_label("feature") == label
        assert mock_request.call_args.kwargs["json"] == {"name": "feature"}

    def test_create_label_with_color(self, client, mock_request):
        label = {"id": "lbl-2", "name": "urgent", "color": "#ff0000"}
        mock_request.return_value = mock_response(label)
        result = client.create_label("urgent", color="#ff0000")
        assert result == label
        assert mock_request.call_args.kwargs["json"] == {"name": "urgent", "color": "#ff0000"}


# ── Error Handling ────────────────────────────────────────────

class TestErrorHandling:
    def test_http_error_raises(self, client, mock_request):
        mock_request.return_value = mock_response({"error": "Issue not found"}, status_code=404)
        with pytest.raises(MulticaAPIError) as exc:
            client.get_issue("nonexistent")
        assert exc.value.status_code == 404
        assert "Issue not found" in str(exc.value)

    def test_connection_error(self, client, mock_request):
        import requests
        mock_request.side_effect = requests.exceptions.ConnectionError("refused")
        with pytest.raises(ConnectionError, match="Cannot connect"):
            client.list_workspaces()

    def test_timeout_error(self, client, mock_request):
        import requests
        mock_request.side_effect = requests.exceptions.Timeout("timed out")
        with pytest.raises(TimeoutError, match="timeout"):
            client.list_workspaces()

    def test_204_no_content(self, client, mock_request):
        mock_request.return_value = mock_response(status_code=204)
        result = client._request("DELETE", "/api/some/resource")
        assert result == {}

    def test_non_json_response(self, client, mock_request):
        mock_request.return_value = mock_response(json_data=None, status_code=200, text="plain text")
        mock_request.return_value.json.side_effect = ValueError("not json")
        result = client._request("GET", "/api/some/text")
        assert result == {"raw": "plain text"}