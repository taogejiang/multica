# Multica Python SDK

Python SDK for creating and managing tasks, projects, and agents via Multica REST API.

## Installation

```bash
# Using uv
cd multica_python_sdk
uv sync

# Or using pip
pip install -e .
```

## Configuration

Set environment variables:

```bash
export MULTICA_BASE_URL="https://your-multica-instance.com"
export MULTICA_API_TOKEN="mul_xxxxx"
```

## Usage

> **Note:** Multica has its own CLI. This SDK is for Python API integration only.

### Python API

```python
from multica_sdk import MulticaClient, MulticaConfig

# Initialize client
config = MulticaConfig(
    base_url="https://your-multica-instance.com",
    api_token="mul_xxxxx"
)
client = MulticaClient(config)

# List workspaces
workspaces = client.list_workspaces()

# List projects
projects = client.list_projects()

# List agents
agents = client.list_agents()

# Create task by name
issue = client.create_issue_by_name(
    title="Fix login page bug",
    project_name="auto_code_review",
    agent_name="code_reviewer",
    workspace_slug="devops",
    priority="high",
    status="todo"
)

# Create task by ID
issue = client.create_issue(
    title="Fix Bug",
    project_id="<project_uuid>",
    assignee_agent_id="<agent_uuid>",
    priority="high"
)

# Update task
client.update_issue(
    issue_id="<issue_id>",
    status="in_progress"
)
```

## Features

- ✅ Workspace management
- ✅ Project management (supports lookup by name)
- ✅ Agent management (supports lookup by name)
- ✅ Task creation and management
- ✅ Task comments
- ✅ Task search
- ✅ Label management

## Authentication

Uses Personal Access Token (PAT):
- Create PAT in Multica Web UI (Settings -> API Tokens)
- Token format: `mul_xxxxx`
- Usage: `Authorization: Bearer mul_xxxxx`

## Development

```bash
# Install dev dependencies
uv sync --dev

# Run tests
uv run pytest

# Build
uv build
```
