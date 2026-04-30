# multica_mcp_server

A FastMCP-based MCP-over-HTTP bridge for Multica.

It exposes a Streamable HTTP endpoint at `/mcp` and proxies tool calls to Multica REST API via the MCP protocol.

## Features

- Docker startup with `docker compose`
- Built on **FastMCP 3.2.4** for reliable tool definitions and schema generation
- Streamable HTTP MCP transport at `/mcp`
- Health check at `/health`
- Built-in tools (auto-schemas from function signatures):
  - `list_workspaces` — List all workspaces
  - `list_agents` — List agents in a workspace
  - `create_issue` — Create a new issue with optional assignment
  - `comment_issue` — Add comments to existing issues
  - `update_issue_status` — Update issue status
- Support for workspace context (optional default workspace via env)

## Quick Start

1. Prepare env file:

```bash
cd /path/to/multica_mcp_server
cp .env.example .env
```

2. Edit `.env`:

- `MULTICA_BASE_URL`: your Multica backend URL (e.g., `http://backend:8080`)
- `MULTICA_WORKSPACE_ID`: optional default workspace ID for tool calls
- `REQUEST_TIMEOUT_SECONDS`: HTTP timeout (default: 20)
- `LOG_LEVEL`: logging level (default: INFO)

3. Start with Docker:

```bash
docker compose up -d --build
```

4. Check health:

```bash
curl -s http://127.0.0.1:8090/health
```

Expected:

```json
{"status":"ok","service":"multica_mcp_server"}
```

## MCP Endpoints

### GET /health

Health check endpoint.

```bash
curl -s http://127.0.0.1:8090/health
```

### POST /mcp

Streamable HTTP MCP endpoint. Accepts JSON-RPC 2.0 requests.

Clients must send a Multica API token in the request headers. The MCP server forwards this header to the backend API for authentication and authorization.

```http
Authorization: Bearer <mul_... token>
```

## Usage Examples

### Initialize (discovery)

```bash
curl -s http://127.0.0.1:8090/mcp \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}'
```

Returns MCP protocol version and server capabilities.

### List tools

```bash
curl -s http://127.0.0.1:8090/mcp \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}'
```

Returns auto-generated tool schemas with descriptions and argument types.

### Call tools

#### list_workspaces

```bash
curl -s http://127.0.0.1:8090/mcp \
  -H 'Content-Type: application/json' \
  -d '{
    "jsonrpc":"2.0",
    "id":3,
    "method":"tools/call",
    "params":{
      "name":"list_workspaces",
      "arguments":{}
    }
  }'
```

#### create_issue

```bash
curl -s http://127.0.0.1:8090/mcp \
  -H 'Content-Type: application/json' \
  -d '{
    "jsonrpc":"2.0",
    "id":4,
    "method":"tools/call",
    "params":{
      "name":"create_issue",
      "arguments":{
        "title":"Fix login flow",
        "description":"Update OAuth callback URL",
        "workspace_id":"ws_abc123",
        "assignee_agent_id":"agt_xyz789"
      }
    }
  }'
```

#### update_issue_status

```bash
curl -s http://127.0.0.1:8090/mcp \
  -H 'Content-Type: application/json' \
  -d '{
    "jsonrpc":"2.0",
    "id":5,
    "method":"tools/call",
    "params":{
      "name":"update_issue_status",
      "arguments":{
        "issue_id":"ABC-123",
        "status":"in_review",
        "workspace_id":"ws_abc123"
      }
    }
  }'
```

## Feishu Integration

### Bot Configuration

Configure your Feishu bot with these MCP settings:

| Setting | Value |
|---------|-------|
| **MCP Endpoint URL** | `https://aihub.quectel.com/multica/mcp` (or your domain) |
| **Protocol** | `HTTP POST to /mcp` |
| **Content-Type** | `application/json` |
| **Request Format** | JSON-RPC 2.0 |

### Feishu Bot Backend Example

Node.js/Express example for Feishu webhook handler:

```javascript
const axios = require('axios');

const MCP_ENDPOINT = 'https://aihub.quectel.com/multica/mcp';

async function callMCPTool(toolName, toolArgs) {
  const payload = {
    jsonrpc: '2.0',
    id: Math.random().toString(36).substr(2, 9),
    method: 'tools/call',
    params: {
      name: toolName,
      arguments: toolArgs
    }
  };

  const response = await axios.post(MCP_ENDPOINT, payload, {
    headers: { 'Content-Type': 'application/json' }
  });

  return response.data;
}

// Handle Feishu message event
app.post('/feishu/webhook', async (req, res) => {
  const event = req.body;

  // Example: Create issue from Feishu command
  if (event.text && event.text.startsWith('/create-issue')) {
    const title = event.text.replace('/create-issue', '').trim();

    const result = await callMCPTool('create_issue', {
      title: title,
      description: `Created from Feishu: ${event.sender_id}`,
      workspace_id: process.env.MULTICA_WORKSPACE_ID
    });

    // Send result back to Feishu
    res.json({
      text: `Issue created: ${result.result.short_id}`
    });
  }
});
```

### Python Flask Example

```python
import requests
import json

MCP_ENDPOINT = 'https://aihub.quectel.com/multica/mcp'

def call_mcp_tool(tool_name: str, tool_args: dict):
    """Call a tool via the MCP endpoint."""
    payload = {
        "jsonrpc": "2.0",
        "id": "feishu-bot-" + str(time.time()),
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": tool_args
        }
    }
    
    response = requests.post(
        MCP_ENDPOINT,
        json=payload,
        headers={"Content-Type": "application/json"}
    )
    
    return response.json()

@app.route('/feishu/webhook', methods=['POST'])
def feishu_webhook():
    event = request.json
    
    if event.get('text', '').startswith('/create-issue'):
        title = event['text'].replace('/create-issue', '').strip()
        
        result = call_mcp_tool('create_issue', {
            'title': title,
            'workspace_id': os.getenv('MULTICA_WORKSPACE_ID')
        })
        
        return {
            'text': f"Issue created: {result['result']['short_id']}"
        }
```

### Feishu Message Card with MCP

Send rich cards from Feishu bot that trigger MCP actions:

```json
{
  "msg_type": "interactive",
  "card": {
    "config": {
      "wide_screen_mode": true
    },
    "elements": [
      {
        "tag": "markdown",
        "content": "**Click to create a new issue in Multica:**"
      },
      {
        "tag": "action",
        "actions": [
          {
            "type": "button",
            "text": "Create Issue",
            "value": "/create-issue New Feature Request"
          }
        ]
      }
    ]
  }
}
```

## Architecture

```
Feishu Bot
  ↓ (sends JSON-RPC request)
aihub.quectel.com/multica/mcp (Nginx reverse proxy)
  ↓
localhost:38090/mcp (Docker: multica-mcp-server)
  ↓ (FastMCP with tools)
Tools call Multica REST API (/api/workspaces, /api/issues, etc.)
  ↓
Multica Backend (localhost:8080)
```

## Security Notes

This service is currently exposed publicly at `https://aihub.quectel.com/multica/mcp`. Before production use, add:

- **API Key authentication**: Require `X-API-Key` header on Nginx or MCP
- **IP allowlist**: Restrict access to known Feishu or bot IPs
- **Rate limiting**: Implement request throttling
- **Request signing**: Use Feishu bot signature verification

See [Advanced Configuration](#advanced-configuration) below for examples.

## Advanced Configuration

### Enable IP Allowlist (Nginx)

Add to `/etc/nginx/conf.d/default.conf` before the `/multica/mcp` location:

```nginx
geo $feishu_ip {
    default 0;
    1.2.3.4 1;      # Your Feishu bot IP
    5.6.7.8 1;      # Additional IPs
}

location ^~ /multica/mcp {
    if ($feishu_ip = 0) {
        return 403;
    }
    proxy_pass http://127.0.0.1:38090/mcp;
    # ... rest of config
}
```

### Add API Key Check

Add environment variable to Docker Compose:

```yaml
environment:
  MCP_API_KEY: "your-secret-key-here"
```

Then add a custom route in `app/main.py`:

```python
@mcp.custom_route("/mcp", methods=["POST"])
async def mcp_with_auth(request: Request):
    api_key = request.headers.get("X-API-Key")
    if api_key != os.getenv("MCP_API_KEY"):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    # Forward to MCP handler
```

## Troubleshooting

### MCP endpoint returns 404

- Verify `MULTICA_BASE_URL` is reachable from container
- Check `MULTICA_TOKEN` is valid (should start with `mul_`)
- Review container logs: `docker logs multica-private-mcp-server-1`

### Feishu bot gets no response

- Ensure `https://aihub.quectel.com/multica/mcp` is reachable
- Check Nginx logs: `tail -f /etc/nginx/log/access.log`
- Test locally: `curl -s https://aihub.quectel.com/multica/mcp -H 'Content-Type: application/json' -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}'`

## Notes

- This project is an MCP bridge for external callers (e.g., Feishu bots, AI agents).
- Tools are auto-discovered; schemas are generated from function signatures by FastMCP.
- Secure deployment is strongly recommended before exposing this service publicly:
  - run behind reverse proxy ✓ (already done via Nginx)
  - add IP allowlist
  - add auth/signature check at ingress
  - add rate limiting
