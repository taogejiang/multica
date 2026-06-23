"""
Multica SDK Core Client
"""

import json
import os
import sys
from dataclasses import dataclass
from typing import Any, Optional
from urllib.parse import urljoin

import requests


@dataclass
class MulticaConfig:
    """Multica API configuration"""
    base_url: str
    api_token: str
    timeout: int = 30

    @classmethod
    def from_env(cls) -> "MulticaConfig":
        """Load configuration from environment variables"""
        base_url = os.environ.get("MULTICA_BASE_URL", "").rstrip("/")
        api_token = os.environ.get("MULTICA_API_TOKEN", "")

        if not base_url:
            raise ValueError("Environment variable MULTICA_BASE_URL is required")
        if not api_token:
            raise ValueError("Environment variable MULTICA_API_TOKEN is required")

        timeout = int(os.environ.get("MULTICA_TIMEOUT", "30"))
        return cls(base_url=base_url, api_token=api_token, timeout=timeout)


class MulticaAPIError(Exception):
    """Multica API error"""
    def __init__(self, status_code: int, message: str, details: Optional[dict] = None):
        self.status_code = status_code
        self.message = message
        self.details = details or {}
        super().__init__(f"HTTP {status_code}: {message}")


class MulticaClient:
    """Multica REST API client"""

    def __init__(self, config: MulticaConfig):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {config.api_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        })

    def _request(self, method: str, path: str, **kwargs) -> Any:
        """Send HTTP request"""
        url = urljoin(self.config.base_url + "/", path.lstrip("/"))
        kwargs.setdefault("timeout", self.config.timeout)
        
        try:
            resp = self.session.request(method, url, **kwargs)
        except requests.exceptions.ConnectionError as e:
            raise ConnectionError(f"Cannot connect to {self.config.base_url}: {e}")
        except requests.exceptions.Timeout:
            raise TimeoutError(f"Request timeout ({self.config.timeout}s)")

        if resp.status_code >= 400:
            error_body = {}
            try:
                error_body = resp.json()
                msg = error_body.get("error") or error_body.get("message") or resp.text
            except (json.JSONDecodeError, ValueError):
                msg = resp.text
            raise MulticaAPIError(resp.status_code, msg, error_body if isinstance(error_body, dict) else {})

        if resp.status_code == 204:
            return {}

        try:
            return resp.json()
        except (json.JSONDecodeError, ValueError):
            return {"raw": resp.text}

    # ── Workspaces ────────────────────────────────────────────

    def list_workspaces(self) -> list[dict]:
        """List all workspaces"""
        return self._request("GET", "/api/workspaces/")

    def get_workspace(self, workspace_id: str) -> dict:
        """Get workspace details"""
        return self._request("GET", f"/api/workspaces/{workspace_id}/")

    def find_workspace_by_name(self, name: str) -> Optional[dict]:
        """Find workspace by name (exact or case-insensitive)."""
        name_lower = name.lower()
        for ws in self.list_workspaces():
            if ws.get("name", "").lower() == name_lower:
                return ws
        return None

    def find_workspace_by_slug(self, slug: str) -> Optional[dict]:
        """Find workspace by slug."""
        for ws in self.list_workspaces():
            if ws.get("slug") == slug:
                return ws
        return None

    def _resolve_workspace_id(
        self,
        workspace_id: Optional[str] = None,
        workspace_slug: Optional[str] = None,
        workspace_name: Optional[str] = None,
    ) -> str:
        """
        Resolve the workspace ID.

        Priority: workspace_id > workspace_name > workspace_slug.
        Raises ValueError if none provided or if the provided identifier
        cannot be resolved.
        """
        if workspace_id:
            return workspace_id

        if workspace_name:
            ws = self.find_workspace_by_name(workspace_name)
            if ws:
                return ws["id"]
            raise ValueError(f"Workspace not found by name: {workspace_name}")

        if workspace_slug:
            ws = self.find_workspace_by_slug(workspace_slug)
            if ws:
                return ws["id"]
            raise ValueError(f"Workspace not found by slug: {workspace_slug}")

        raise ValueError(
            "workspace_id or workspace_slug is required. "
            "Use --workspace or --workspace-slug to specify one."
        )

    # ── Projects ──────────────────────────────────────────────

    def list_projects(self, workspace_id: Optional[str] = None,
                      status: Optional[str] = None,
                      priority: Optional[str] = None) -> dict:
        """List projects"""
        params = {}
        if workspace_id:
            params["workspace_id"] = workspace_id
        if status:
            params["status"] = status
        if priority:
            params["priority"] = priority
        return self._request("GET", "/api/projects/", params=params)

    def get_project(self, project_id: str) -> dict:
        """Get project details"""
        return self._request("GET", f"/api/projects/{project_id}/")

    def search_projects(self, query: str) -> list[dict]:
        """Search projects"""
        return self._request("GET", "/api/projects/search", params={"q": query})

    def find_project_by_name(self, project_name: str, workspace_id: Optional[str] = None,
                             workspace_slug: Optional[str] = None,
                             workspace_name: Optional[str] = None) -> Optional[dict]:
        """
        Find project by name
        
        Args:
            project_name: Project name (e.g., "auto_code_review")
            workspace_id: Optional workspace ID. Auto-detected if not provided.
            workspace_slug: Optional workspace slug.
            
        Returns:
            Matching project dict, or None if not found
        """
        ws_id = self._resolve_workspace_id(workspace_id, workspace_slug, workspace_name)
        projects_result = self.list_projects(workspace_id=ws_id)
        projects = projects_result.get("projects", projects_result) if isinstance(projects_result, dict) else projects_result

        # Exact match
        for project in projects:
            if project.get("title") == project_name:
                return project

        # Case-insensitive match
        project_name_lower = project_name.lower()
        for project in projects:
            if project.get("title", "").lower() == project_name_lower:
                return project

        # Partial match
        for project in projects:
            if project_name_lower in project.get("title", "").lower():
                return project

        return None

    # ── Agents ────────────────────────────────────────────────

    def list_agents(self, workspace_id: Optional[str] = None,
                    include_archived: bool = False) -> list[dict]:
        """List all agents"""
        params = {}
        if workspace_id:
            params["workspace_id"] = workspace_id
        if include_archived:
            params["include_archived"] = "true"
        return self._request("GET", "/api/agents/", params=params)

    def get_agent(self, agent_id: str) -> dict:
        """Get agent details"""
        return self._request("GET", f"/api/agents/{agent_id}/")

    def find_agent_by_name(self, agent_name: str, workspace_id: Optional[str] = None,
                           workspace_slug: Optional[str] = None,
                           workspace_name: Optional[str] = None) -> Optional[dict]:
        """
        Find agent by name
        
        Args:
            agent_name: Agent name (e.g., "code_reviewer")
            workspace_id: Optional workspace ID. Auto-detected if not provided.
            workspace_slug: Optional workspace slug.
            
        Returns:
            Matching agent dict, or None if not found
        """
        ws_id = self._resolve_workspace_id(workspace_id, workspace_slug, workspace_name)
        agents = self.list_agents(workspace_id=ws_id)
        
        # Exact match
        for agent in agents:
            if agent.get("name") == agent_name:
                return agent
        
        # Case-insensitive match
        agent_name_lower = agent_name.lower()
        for agent in agents:
            if agent.get("name", "").lower() == agent_name_lower:
                return agent
        
        # Partial match
        for agent in agents:
            if agent_name_lower in agent.get("name", "").lower():
                return agent
        
        return None

    # ── Issues ────────────────────────────────────────────────

    def create_issue(
        self,
        title: str,
        description: Optional[str] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        assignee_agent_id: Optional[str] = None,
        assignee_user_id: Optional[str] = None,
        project_id: Optional[str] = None,
        parent_issue_id: Optional[str] = None,
        start_date: Optional[str] = None,
        due_date: Optional[str] = None,
        attachment_ids: Optional[list[str]] = None,
        allow_duplicate: bool = False,
        workspace_id: Optional[str] = None,
    ) -> dict:
        """
        Create an issue

        Args:
            title: Issue title (required)
            description: Issue description
            status: Status (backlog|todo|in_progress|in_review|done|blocked|cancelled)
            priority: Priority (urgent|high|medium|low|none)
            assignee_agent_id: Assigned agent ID
            assignee_user_id: Assigned user ID (mutually exclusive with agent_id)
            project_id: Project ID
            parent_issue_id: Parent issue ID
            start_date: Start date (YYYY-MM-DD)
            due_date: Due date (YYYY-MM-DD)
            attachment_ids: List of attachment IDs
            allow_duplicate: Whether to allow duplicate titles
            workspace_id: Workspace ID (required by API)
        """
        body: dict = {"title": title}

        if description is not None:
            body["description"] = description
        if status is not None:
            valid_statuses = {"backlog", "todo", "in_progress", "in_review", "done", "blocked", "cancelled"}
            if status not in valid_statuses:
                raise ValueError(f"Invalid status: {status}. Valid values: {', '.join(sorted(valid_statuses))}")
            body["status"] = status
        if priority is not None:
            valid_priorities = {"urgent", "high", "medium", "low", "none"}
            if priority not in valid_priorities:
                raise ValueError(f"Invalid priority: {priority}. Valid values: {', '.join(sorted(valid_priorities))}")
            body["priority"] = priority

        # Assign to agent or user
        if assignee_agent_id and assignee_user_id:
            raise ValueError("assignee_agent_id and assignee_user_id cannot be specified simultaneously")
        if assignee_agent_id:
            body["assignee_type"] = "agent"
            body["assignee_id"] = assignee_agent_id
        elif assignee_user_id:
            body["assignee_type"] = "user"
            body["assignee_id"] = assignee_user_id

        if project_id is not None:
            body["project_id"] = project_id
        if parent_issue_id is not None:
            body["parent_issue_id"] = parent_issue_id
        if start_date is not None:
            body["start_date"] = start_date
        if due_date is not None:
            body["due_date"] = due_date
        if attachment_ids:
            body["attachment_ids"] = attachment_ids
        if allow_duplicate:
            body["allow_duplicate"] = True

        params = {}
        if workspace_id is not None:
            params["workspace_id"] = workspace_id

        result = self._request("POST", "/api/issues/", json=body, params=params)
        identifier = result.get("identifier")
        if identifier:
            result["url"] = self.build_issue_url(identifier)
        return result

    def create_issue_by_name(
        self,
        title: str,
        project_name: Optional[str] = None,
        agent_name: Optional[str] = None,
        workspace_id: Optional[str] = None,
        workspace_slug: Optional[str] = None,
        description: Optional[str] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        parent_issue_id: Optional[str] = None,
        start_date: Optional[str] = None,
        due_date: Optional[str] = None,
        attachment_ids: Optional[list[str]] = None,
        allow_duplicate: bool = False,
    ) -> dict:
        """
        Create an issue by project name and agent name
        
        Args:
            title: Issue title (required)
            project_name: Project name (e.g., "auto_code_review")
            agent_name: Agent name (e.g., "code_reviewer")
            workspace_id: Workspace ID. Auto-detected if not provided.
            workspace_slug: Workspace slug (e.g., "my-workspace").
            description: Issue description
            status: Status
            priority: Priority
            parent_issue_id: Parent issue ID
            start_date: Start date (YYYY-MM-DD)
            due_date: Due date (YYYY-MM-DD)
            attachment_ids: List of attachment IDs
            allow_duplicate: Whether to allow duplicate titles
        """
        project_id = None
        agent_id = None
        ws_id = None

        # Resolve workspace_id
        if workspace_id or workspace_slug:
            ws_id = self._resolve_workspace_id(workspace_id, workspace_slug)
        
        # Find project by name
        if project_name:
            project = self.find_project_by_name(project_name, workspace_id, workspace_slug)
            if not project:
                raise ValueError(f"Project not found: {project_name}")
            project_id = project["id"]
        
        # Find agent by name
        if agent_name:
            agent = self.find_agent_by_name(agent_name, workspace_id, workspace_slug)
            if not agent:
                raise ValueError(f"Agent not found: {agent_name}")
            agent_id = agent["id"]
        
        # Call the original create_issue method
        return self.create_issue(
            title=title,
            description=description,
            status=status,
            priority=priority,
            assignee_agent_id=agent_id,
            project_id=project_id,
            parent_issue_id=parent_issue_id,
            start_date=start_date,
            due_date=due_date,
            attachment_ids=attachment_ids,
            allow_duplicate=allow_duplicate,
            workspace_id=ws_id,
        )

    def quick_create_issue(
        self,
        title: str,
        project_id: Optional[str] = None,
        assignee_agent_id: Optional[str] = None,
        description: Optional[str] = None,
    ) -> dict:
        """
        Quick create an issue

        Args:
            title: Issue title (required)
            project_id: Project ID
            assignee_agent_id: Assigned agent ID
            description: Issue description
        """
        body: dict = {"title": title}
        if project_id:
            body["project_id"] = project_id
        if assignee_agent_id:
            body["assignee_id"] = assignee_agent_id
            body["assignee_type"] = "agent"
        if description:
            body["description"] = description

        return self._request("POST", "/api/issues/quick-create", json=body)

    def get_issue(self, issue_id: str) -> dict:
        """Get issue details"""
        return self._request("GET", f"/api/issues/{issue_id}/")

    def update_issue(self, issue_id: str, workspace_id: Optional[str] = None, **fields) -> dict:
        """
        Update an issue

        Supported fields: title, description, status, priority, assignee_type,
                   assignee_id, project_id, start_date, due_date
        """
        params = {}
        if workspace_id:
            params["workspace_id"] = workspace_id
        return self._request("PUT", f"/api/issues/{issue_id}/", json=fields, params=params)

    def list_issues(self, project_id: Optional[str] = None,
                    status: Optional[str] = None,
                    assignee_id: Optional[str] = None,
                    workspace_id: Optional[str] = None) -> list[dict]:
        """List issues"""
        params = {}
        if project_id:
            params["project_id"] = project_id
        if status:
            params["status"] = status
        if assignee_id:
            params["assignee_id"] = assignee_id
        if workspace_id:
            params["workspace_id"] = workspace_id
        return self._request("GET", "/api/issues/", params=params)

    def search_issues(self, query: str) -> list[dict]:
        """Search issues"""
        return self._request("GET", "/api/issues/search", params={"q": query})

    # ── Comments ──────────────────────────────────────────────

    def build_issue_url(self, identifier: str) -> str:
        """Build the web URL for an issue."""
        return f"{self.config.base_url.rstrip('/')}/issues/{identifier}"

    def create_comment(self, issue_id: str, content: str) -> dict:
        """Add a comment to an issue"""
        return self._request("POST", f"/api/issues/{issue_id}/comments", json={"content": content})

    # ── Labels ────────────────────────────────────────────────

    def list_labels(self) -> list[dict]:
        """List all labels"""
        return self._request("GET", "/api/labels/")

    def create_label(self, name: str, color: Optional[str] = None) -> dict:
        """Create a label"""
        body = {"name": name}
        if color:
            body["color"] = color
        return self._request("POST", "/api/labels/", json=body)
