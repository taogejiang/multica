import logging
import os
from contextvars import ContextVar
from typing import Any

import httpx
from fastmcp import FastMCP
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


BASE_URL = _env("MULTICA_BASE_URL", "http://host.docker.internal:38080").rstrip("/")
DEFAULT_WORKSPACE_ID = _env("MULTICA_WORKSPACE_ID")
REQUEST_TIMEOUT_SECONDS = float(_env("REQUEST_TIMEOUT_SECONDS", "20") or "20")
LOG_LEVEL = _env("LOG_LEVEL", "INFO").upper()

REQUEST_AUTHORIZATION: ContextVar[str] = ContextVar("request_authorization", default="")

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger("multica_mcp_server")

# Create FastMCP instance
mcp = FastMCP(name="multica_mcp_server", version="0.2.0")


class RequestAuthorizationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        authorization = request.headers.get("authorization", "")
        token = REQUEST_AUTHORIZATION.set(authorization)
        if request.url.path == "/mcp":
            scheme, prefix, token_len = _auth_meta(authorization)
            logger.info(
                "MCP inbound request %s %s auth_scheme=%s auth_token_prefix=%s auth_token_len=%d",
                request.method,
                request.url.path,
                scheme,
                prefix,
                token_len,
            )
        try:
            return await call_next(request)
        finally:
            REQUEST_AUTHORIZATION.reset(token)


def _auth_meta(authorization: str) -> tuple[str, str, int]:
    auth = (authorization or "").strip()
    if not auth:
        return "", "", 0
    scheme = ""
    token = auth
    if " " in auth:
        scheme, token = auth.split(" ", 1)
        token = token.strip()
    prefix = token[:8]
    return scheme, prefix, len(token)


def _auth_headers() -> dict[str, str]:
    authorization = REQUEST_AUTHORIZATION.get().strip()
    if not authorization:
        raise ValueError("Authorization header is required")
    return {
        "Authorization": authorization,
        "Content-Type": "application/json",
    }


def _merge_workspace(path: str, workspace_id: str | None) -> str:
    resolved = (workspace_id or DEFAULT_WORKSPACE_ID or "").strip()
    if not resolved:
        return path
    joiner = "&" if "?" in path else "?"
    return f"{path}{joiner}workspace_id={resolved}"


async def _multica_get(path: str) -> Any:
    url = f"{BASE_URL}{path}"
    scheme, prefix, token_len = _auth_meta(REQUEST_AUTHORIZATION.get())
    logger.info(
        "Forwarding GET %s auth_scheme=%s auth_token_prefix=%s auth_token_len=%d",
        path,
        scheme,
        prefix,
        token_len,
    )
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT_SECONDS) as client:
        resp = await client.get(url, headers=_auth_headers())
    if resp.status_code >= 400:
        raise RuntimeError(f"Multica API error: {resp.status_code} {resp.text}")
    return resp.json()


async def _multica_post(path: str, payload: dict[str, Any]) -> Any:
    url = f"{BASE_URL}{path}"
    scheme, prefix, token_len = _auth_meta(REQUEST_AUTHORIZATION.get())
    logger.info(
        "Forwarding POST %s auth_scheme=%s auth_token_prefix=%s auth_token_len=%d",
        path,
        scheme,
        prefix,
        token_len,
    )
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT_SECONDS) as client:
        resp = await client.post(url, headers=_auth_headers(), json=payload)
    if resp.status_code >= 400:
        raise RuntimeError(f"Multica API error: {resp.status_code} {resp.text}")
    if not resp.text:
        return {"ok": True}
    return resp.json()


async def _multica_put(path: str, payload: dict[str, Any]) -> Any:
    url = f"{BASE_URL}{path}"
    scheme, prefix, token_len = _auth_meta(REQUEST_AUTHORIZATION.get())
    logger.info(
        "Forwarding PUT %s auth_scheme=%s auth_token_prefix=%s auth_token_len=%d",
        path,
        scheme,
        prefix,
        token_len,
    )
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT_SECONDS) as client:
        resp = await client.put(url, headers=_auth_headers(), json=payload)
    if resp.status_code >= 400:
        raise RuntimeError(f"Multica API error: {resp.status_code} {resp.text}")
    return resp.json()


# Define tools using FastMCP decorator
@mcp.tool
async def list_workspaces() -> str:
    """List workspaces from Multica."""
    result = await _multica_get("/api/workspaces")
    return str(result)


@mcp.tool
async def list_agents(workspace_id: str | None = None) -> str:
    """List agents in a workspace."""
    path = _merge_workspace("/api/agents", workspace_id)
    result = await _multica_get(path)
    return str(result)


@mcp.tool
async def create_issue(
    title: str,
    description: str | None = None,
    assignee_agent_id: str | None = None,
    workspace_id: str | None = None,
) -> str:
    """Create an issue in Multica."""
    payload: dict[str, Any] = {"title": title}
    if description:
        payload["description"] = description
    if assignee_agent_id:
        payload["assignee_agent_id"] = assignee_agent_id
    path = _merge_workspace("/api/issues", workspace_id)
    result = await _multica_post(path, payload)
    return str(result)


@mcp.tool
async def comment_issue(issue_id: str, content: str) -> str:
    """Add a comment to an issue."""
    payload = {"content": content}
    result = await _multica_post(f"/api/issues/{issue_id}/comments", payload)
    return str(result)


@mcp.tool
async def update_issue_status(issue_id: str, status: str, workspace_id: str | None = None) -> str:
    """Update issue status."""
    payload = {"status": status}
    path = _merge_workspace(f"/api/issues/{issue_id}", workspace_id)
    result = await _multica_put(path, payload)
    return str(result)


# Add custom routes for health check and health endpoint
@mcp.custom_route("/health", methods=["GET"])
async def health(_: Request):
    """Health check endpoint."""
    return JSONResponse({"status": "ok", "service": "multica_mcp_server"})


def create_app():
    """Create ASGI application for uvicorn."""
    app = mcp.http_app()
    app.add_middleware(RequestAuthorizationMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    return app


# Export ASGI app for uvicorn
app = create_app()
