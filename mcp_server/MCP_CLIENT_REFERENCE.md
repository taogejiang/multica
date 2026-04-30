# MCP SSE 客户端标准接入参考

本文档为飞书机器人等第三方系统提供标准 MCP SSE 客户端接入方式。

## 快速接入参数

```
┌─────────────────────────────────────────────────────────────┐
│  MCP 服务器配置 (SSE Transport)                              │
├─────────────────────────────────────────────────────────────┤
│  Type:            Server-Sent Events (SSE)                  │
│  Endpoint URL:    https://aihub.quectel.com/multica/mcp     │
│  Internal URL:    http://127.0.0.1:38090/mcp                │
│  Protocol:        MCP 2.0                                   │
│  Timeout:         60 seconds                                │
│  Authentication:  Required (Multica API Token)              │
│  Headers:         authorization                             │
└─────────────────────────────────────────────────────────────┘
```

## 环境变量配置

```bash
# 必需
MULTICA_MCP_URL="https://aihub.quectel.com/multica/mcp"
MULTICA_MCP_TYPE="sse"

# 必需
MULTICA_MCP_AUTHORIZATION="Bearer YOUR_MULTICA_API_TOKEN"  # 前端界面生成的 mul_... token

# 可选
MULTICA_MCP_INTERNAL_URL="http://127.0.0.1:38090/mcp"
MULTICA_WORKSPACE_ID="ws_abc123"
```

## Python SSE 客户端实现

### 基础类

```python
import asyncio
from mcp import ClientSession
from mcp.client.sse import sse_client
import os
from typing import Any, Optional, Dict, List

class MulticaMCPSSEClient:
    """Multica MCP SSE 标准客户端"""
    
    def __init__(
        self,
        url: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None
    ):
        """
        初始化 SSE 客户端
        
        Args:
            url: MCP 服务器地址（默认读取环境变量）
            headers: HTTP headers（包含认证信息）
        """
        self.url = url or os.getenv(
            "MULTICA_MCP_URL",
            "https://aihub.quectel.com/multica/mcp"
        )
        self.headers = headers or {}
        
        # 从环境变量读取认证信息
        if not self.headers.get("authorization"):
            auth = os.getenv("MULTICA_MCP_AUTHORIZATION")
            if auth:
                self.headers["authorization"] = auth
        
        self.session = None
        self.transport = None
    
    async def connect(self):
        """连接到 MCP SSE 服务器"""
        try:
            self.transport = sse_client(self.url, headers=self.headers)
            self.session = ClientSession(self.transport)
            await self.session.initialize()
            return self
        except Exception as e:
            print(f"Connection failed: {e}")
            raise
    
    async def list_tools(self) -> List:
        """列出所有工具"""
        if not self.session:
            raise RuntimeError("Client not connected")
        
        response = await self.session.list_tools()
        return response.tools
    
    async def call_tool(
        self,
        tool_name: str,
        **arguments
    ) -> Optional[Any]:
        """
        调用 MCP 工具
        
        Args:
            tool_name: 工具名称
            **arguments: 工具参数
        
        Returns:
            工具执行结果
        
        Example:
            >>> async with await client.connect() as client:
            ...     result = await client.call_tool(
            ...         "create_issue",
            ...         title="New Task",
            ...         workspace_id="ws_123"
            ...     )
        """
        if not self.session:
            raise RuntimeError("Client not connected")
        
        try:
            response = await self.session.call_tool(tool_name, arguments)
            
            if response.isError:
                error_msg = response.content[0].text if response.content else "Unknown error"
                print(f"Tool error: {error_msg}")
                return None
            
            return response.content[0].text if response.content else None
        
        except Exception as e:
            print(f"Tool call failed: {e}")
            return None
    
    # 便利方法
    async def list_workspaces(self):
        """列出所有工作空间"""
        return await self.call_tool("list_workspaces")
    
    async def list_agents(self, workspace_id: Optional[str] = None):
        """列出工作空间内的智能体"""
        args = {}
        if workspace_id:
            args["workspace_id"] = workspace_id
        return await self.call_tool("list_agents", **args)
    
    async def create_issue(
        self,
        title: str,
        description: Optional[str] = None,
        workspace_id: Optional[str] = None,
        assignee_agent_id: Optional[str] = None
    ):
        """创建工作项"""
        args = {"title": title}
        if description:
            args["description"] = description
        if workspace_id:
            args["workspace_id"] = workspace_id
        if assignee_agent_id:
            args["assignee_agent_id"] = assignee_agent_id
        return await self.call_tool("create_issue", **args)
    
    async def comment_issue(self, issue_id: str, content: str):
        """添加评论"""
        return await self.call_tool(
            "comment_issue",
            issue_id=issue_id,
            content=content
        )
    
    async def update_issue_status(
        self,
        issue_id: str,
        status: str,
        workspace_id: Optional[str] = None
    ):
        """更新工作项状态"""
        args = {
            "issue_id": issue_id,
            "status": status
        }
        if workspace_id:
            args["workspace_id"] = workspace_id
        return await self.call_tool("update_issue_status", **args)
    
    async def close(self):
        """关闭连接"""
        if self.session:
            await self.session.close()
    
    async def __aenter__(self):
        return await self.connect()
    
    async def __aexit__(self, *args):
        await self.close()
```

### 使用示例

```python
import asyncio
from mcp_client import MulticaMCPSSEClient

async def main():
    # 方式 1：使用 context manager
    async with MulticaMCPSSEClient() as client:
        # 列出工具
        tools = await client.list_tools()
        print(f"Available tools: {[t.name for t in tools]}")
        
        # 创建工作项
        result = await client.create_issue(
            title="New Task",
            description="From Feishu",
            workspace_id="ws_abc123"
        )
        print(f"Created: {result}")
    
    # 方式 2：手动管理连接
    client = MulticaMCPSSEClient(
        headers={"authorization": "Bearer YOUR_TOKEN"}
    )
    await client.connect()
    
    try:
        # 调用工具
        workspaces = await client.list_workspaces()
        print(f"Workspaces: {workspaces}")
    finally:
        await client.close()

asyncio.run(main())
```

    
    def __init__(
        self,
        url: Optional[str] = None,
        timeout: int = 60,
        api_key: Optional[str] = None,
        **kwargs
    ):
        """
        初始化客户端
        
        Args:
            url: MCP 服务器地址（默认读取环境变量）
            timeout: 请求超时（秒）
            api_key: API 密钥（可选，生产环境推荐）
            **kwargs: 传递给 httpx.Client 的其他参数
## Python FastAPI 集成示例

```python
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import asyncio
from mcp_client import MulticaMCPSSEClient
import logging

app = FastAPI()
logger = logging.getLogger(__name__)

# 全局 MCP 客户端（在应用启动时初始化）
mcp_client: Optional[MulticaMCPSSEClient] = None

@app.on_event("startup")
async def startup():
        """应用启动时连接 MCP"""
        global mcp_client
        mcp_client = MulticaMCPSSEClient()
        try:
                await mcp_client.connect()
                logger.info("MCP client connected")
        except Exception as e:
                logger.error(f"Failed to connect to MCP: {e}")

@app.on_event("shutdown")
async def shutdown():
        """应用关闭时断开 MCP 连接"""
        global mcp_client
        if mcp_client:
                await mcp_client.close()
                logger.info("MCP client disconnected")

@app.post("/feishu/bot/webhook")
async def feishu_webhook(request: Request):
        """处理飞书机器人 webhook"""
        global mcp_client
    
        try:
                payload = await request.json()
        
                # 处理飞书消息
                if payload.get("type") == "url_verification":
                        return {"challenge": payload.get("challenge")}
        
                if payload.get("type") == "event_callback":
                        event = payload.get("event", {})
                        message = event.get("text", "")
            
                        # 调用 MCP 工具处理消息
                        if message.startswith("/create_issue"):
                                parts = message.split(maxsplit=1)
                                title = parts[1] if len(parts) > 1 else "Untitled"
                
                                result = await mcp_client.create_issue(
                                        title=title,
                                        description="From Feishu"
                                )
                
                                return JSONResponse({"status": "ok", "result": result})
        
                return JSONResponse({"status": "ok"})
    
        except Exception as e:
                logger.error(f"Error handling webhook: {e}")
                return JSONResponse({"error": str(e)}, status_code=500)
```

## Node.js SSE 客户端实现

### 基础类

```javascript
const { SSEClientTransport } = require("@modelcontextprotocol/sdk/client/sse.js");
const { Client } = require("@modelcontextprotocol/sdk/client/index.js");

class MulticaMCPSSEClient {
    constructor(options = {}) {
        this.url = options.url || process.env.MULTICA_MCP_URL || 
                             "https://aihub.quectel.com/multica/mcp";
        this.headers = options.headers || {};
    
        // 从环境变量读取认证信息
        if (!this.headers.authorization) {
            const auth = process.env.MULTICA_MCP_AUTHORIZATION;
            if (auth) {
                this.headers.authorization = auth;
            }
        }
    
        this.client = null;
    }
  
    async connect() {
        try {
            const transport = new SSEClientTransport({
                url: this.url,
                headers: this.headers
            });
      
            this.client = new Client({
                name: "multica-feishu-bot",
                version: "1.0.0"
            }, {
                capabilities: {}
            });
      
            await this.client.connect(transport);
            console.log("Connected to MCP SSE server");
            return this;
        } catch (error) {
            console.error("Connection failed:", error);
            throw error;
        }
    }
  
    async listTools() {
        if (!this.client) {
            throw new Error("Client not connected");
        }
    
        const response = await this.client.request({
            method: "tools/list"
        });
        return response.tools;
    }
  
    async callTool(toolName, arguments) {
        if (!this.client) {
            throw new Error("Client not connected");
        }
    
        try {
            const response = await this.client.request({
                method: "tools/call",
                params: {
                    name: toolName,
                    arguments: arguments
                }
            });
      
            if (response.isError) {
                console.error(`Tool error: ${response.content[0]?.text}`);
                return null;
            }
      
            return response.content[0]?.text;
        } catch (error) {
            console.error("Tool call failed:", error);
            return null;
        }
    }
  
    // 便利方法
    async listWorkspaces() {
        return this.callTool("list_workspaces", {});
    }
  
    async listAgents(workspaceId) {
        const args = workspaceId ? { workspace_id: workspaceId } : {};
        return this.callTool("list_agents", args);
    }
  
    async createIssue(title, options = {}) {
        const args = { title, ...options };
        return this.callTool("create_issue", args);
    }
  
    async commentIssue(issueId, content) {
        return this.callTool("comment_issue", {
            issue_id: issueId,
            content: content
        });
    }
  
    async updateIssueStatus(issueId, status, workspaceId) {
        const args = { issue_id: issueId, status };
        if (workspaceId) args.workspace_id = workspaceId;
        return this.callTool("update_issue_status", args);
    }
  
    async close() {
        if (this.client) {
            await this.client.close();
        }
    }
}

module.exports = MulticaMCPSSEClient;
```

### Node.js 使用示例

```javascript
const MulticaMCPSSEClient = require('./mcp_client');

async function main() {
    // 方式 1：手动连接管理
    const client = new MulticaMCPSSEClient({
        headers: { "authorization": "Bearer YOUR_TOKEN" }
    });
  
    await client.connect();
  
    try {
        // 列出工具
        const tools = await client.listTools();
        console.log("Available tools:", tools.map(t => t.name));
    
        // 创建工作项
        const result = await client.createIssue("New Task", {
            description: "From Feishu",
            workspace_id: "ws_abc123"
        });
        console.log("Created:", result);
    
    } finally {
        await client.close();
    }
}

main().catch(console.error);
```

### Node.js Express 集成示例

```javascript
const express = require('express');
const MulticaMCPSSEClient = require('./mcp_client');

const app = express();
app.use(express.json());

let mcpClient = null;

// 应用启动时连接 MCP
async function initMCP() {
    mcpClient = new MulticaMCPSSEClient();
    try {
        await mcpClient.connect();
        console.log("MCP client connected");
    } catch (error) {
        console.error("Failed to connect to MCP:", error);
        process.exit(1);
    }
}

// 处理飞书 Webhook
app.post('/feishu/bot/webhook', async (req, res) => {
    try {
        const payload = req.body;
    
        // 处理飞书 URL 验证
        if (payload.type === 'url_verification') {
            return res.json({ challenge: payload.challenge });
        }
    
        // 处理飞书事件
        if (payload.type === 'event_callback') {
            const event = payload.event;
            const message = event.text || '';
      
            // 调用 MCP 工具
            if (message.startsWith('/create_issue')) {
                const title = message.split(' ').slice(1).join(' ') || 'Untitled';
        
                const result = await mcpClient.createIssue(title, {
                    description: 'From Feishu'
                });
        
                return res.json({ status: 'ok', result });
            }
        }
    
        res.json({ status: 'ok' });
    } catch (error) {
        console.error('Error handling webhook:', error);
        res.status(500).json({ error: error.message });
    }
});

// 启动服务器
const PORT = process.env.PORT || 3000;
app.listen(PORT, async () => {
    await initMCP();
    console.log(`Server listening on port ${PORT}`);
});
```

## mcp.json 配置示例

```json
{
    "servers": {
        "multica_mcp": {
            "type": "sse",
            "url": "https://aihub.quectel.com/multica/mcp",
            "headers": {
                "authorization": "Bearer YOUR_MULTICA_API_TOKEN"
            },
            "env": {
                "MULTICA_WORKSPACE_ID": "ws_default_workspace"
            }
        }
    }
}
```

## MCP 工具文档

| 工具名 | 参数 | 说明 |
|--------|--------|--------|
| `list_workspaces` | 无 | 列出所有工作空间 |
| `list_agents` | `workspace_id` (可选) | 列出工作空间内的智能体 |
| `create_issue` | `title` (必需), `description` (可选), `workspace_id` (可选), `assignee_agent_id` (可选) | 创建工作项 |
| `comment_issue` | `issue_id` (必需), `content` (必需) | 添加评论 |
| `update_issue_status` | `issue_id` (必需), `status` (必需), `workspace_id` (可选) | 更新工作项状态 |

## 最佳实践

### 1. 连接管理

- 使用 context manager 或 try/finally 确保连接正确关闭
- 设置合理的超时时间（推荐 60 秒）
- 在生产环境中实现连接池以处理并发请求

### 2. 错误处理

```python
async with MulticaMCPSSEClient() as client:
        try:
                result = await client.call_tool("create_issue", title="Task")
        except RuntimeError as e:
                print(f"Connection error: {e}")
        except Exception as e:
                print(f"Tool execution error: {e}")
```

### 3. 认证

- 使用环境变量存储敏感信息（JWT token）
- 在生产环境中使用 HTTPS
- 定期轮换 token

### 4. 超时处理

```python
# Python
import asyncio
try:
        result = await asyncio.wait_for(
                client.call_tool("create_issue", title="Task"),
                timeout=30
        )
except asyncio.TimeoutError:
        print("Tool call timeout")

# Node.js
const timeoutPromise = new Promise((_, reject) =>
    setTimeout(() => reject(new Error('Timeout')), 30000)
);
const result = await Promise.race([
    client.callTool("create_issue", { title: "Task" }),
    timeoutPromise
]);
```

### 5. 日志记录

```python
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

async with MulticaMCPSSEClient() as client:
        logger.info(f"Connected to MCP server at {client.url}")
        result = await client.create_issue(title="Task")
        logger.info(f"Created issue: {result}")
```
            "jsonrpc": "2.0",
            "id": self._next_request_id(),
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }
        
        try:
            response = self.client.post(self.url, json=payload)
            response.raise_for_status()
            
            data = response.json()
            
            # 检查 JSON-RPC 错误
            if "error" in data:
                error = data["error"]
                print(f"MCP Error [{error.get('code')}]: {error.get('message')}")
                if "data" in error:
                    print(f"Details: {error['data']}")
                return None
            
            return data.get("result")
        
        except httpx.HTTPError as e:
            print(f"HTTP Error: {e}")
            return None
        except json.JSONDecodeError as e:
            print(f"JSON Decode Error: {e}")
            return None
        except Exception as e:
            print(f"Unexpected Error: {e}")
            return None
    
    def list_workspaces(self) -> Optional[list]:
        """列出所有工作空间"""
        return self.call_tool("list_workspaces")
    
    def list_agents(self, workspace_id: Optional[str] = None) -> Optional[list]:
        """列出工作空间内的智能体"""
        args = {}
        if workspace_id:
            args["workspace_id"] = workspace_id
        return self.call_tool("list_agents", **args)
    
    def create_issue(
        self,
        title: str,
        description: Optional[str] = None,
        workspace_id: Optional[str] = None,
        assignee_agent_id: Optional[str] = None
    ) -> Optional[Dict]:
        """创建工作项"""
        args = {"title": title}
        if description:
            args["description"] = description
        if workspace_id:
            args["workspace_id"] = workspace_id
        if assignee_agent_id:
            args["assignee_agent_id"] = assignee_agent_id
        return self.call_tool("create_issue", **args)
    
    def comment_issue(self, issue_id: str, content: str) -> Optional[Dict]:
        """添加评论"""
        return self.call_tool(
            "comment_issue",
            issue_id=issue_id,
            content=content
        )
    
    def update_issue_status(
        self,
        issue_id: str,
        status: str,
        workspace_id: Optional[str] = None
    ) -> Optional[Dict]:
        """更新工作项状态"""
        args = {
            "issue_id": issue_id,
            "status": status
        }
        if workspace_id:
            args["workspace_id"] = workspace_id
        return self.call_tool("update_issue_status", **args)
    
    def close(self):
        """关闭客户端"""
        self.client.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        self.close()
```

### 异步客户端

```python
import httpx
import json
import os
from typing import Any, Optional, Dict

class AsyncMulticaMCPClient:
    """Multica MCP 异步客户端"""
    
    def __init__(
        self,
        url: Optional[str] = None,
        timeout: int = 60,
        api_key: Optional[str] = None,
    ):
        self.url = url or os.getenv(
            "MULTICA_MCP_URL",
            "https://aihub.quectel.com/multica/mcp"
        )
        self.timeout = timeout
        self.api_key = api_key or os.getenv("MULTICA_MCP_API_KEY")
        self.request_id = 0
        
        self.headers = {"Content-Type": "application/json"}
        if self.api_key:
            self.headers["X-API-Key"] = self.api_key
        
        self.client = None
    
    async def __aenter__(self):
        self.client = httpx.AsyncClient(
            timeout=self.timeout,
            headers=self.headers
        )
        return self
    
    async def __aexit__(self, *args):
        await self.client.aclose()
    
    def _next_request_id(self) -> str:
        self.request_id += 1
        return str(self.request_id)
    
    async def call_tool(
        self,
        tool_name: str,
        **arguments
    ) -> Optional[Any]:
        """异步调用工具"""
        if not self.client:
            raise RuntimeError("Client not initialized. Use 'async with' context manager")
        
        payload = {
            "jsonrpc": "2.0",
            "id": self._next_request_id(),
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }
        
        try:
            response = await self.client.post(self.url, json=payload)
            response.raise_for_status()
            
            data = response.json()
            
            if "error" in data:
                error = data["error"]
                print(f"MCP Error: {error.get('message')}")
                return None
            
            return data.get("result")
        
        except Exception as e:
            print(f"Error: {e}")
            return None
```

## Node.js 客户端实现

### 基础类

```javascript
const axios = require('axios');

class MulticaMCPClient {
  constructor(options = {}) {
    this.url = options.url || process.env.MULTICA_MCP_URL 
               || "https://aihub.quectel.com/multica/mcp";
    this.timeout = options.timeout || 60000; // 毫秒
    this.apiKey = options.apiKey || process.env.MULTICA_MCP_API_KEY;
    this.requestId = 0;
    
    // 构建 headers
    this.headers = {
      'Content-Type': 'application/json',
      ...options.headers
    };
    
    if (this.apiKey) {
      this.headers['X-API-Key'] = this.apiKey;
    }
    
    // 创建 axios 实例
    this.instance = axios.create({
      timeout: this.timeout,
      headers: this.headers
    });
  }
  
  nextRequestId() {
    return String(++this.requestId);
  }
  
  async callTool(toolName, args = {}) {
    const payload = {
      jsonrpc: '2.0',
      id: this.nextRequestId(),
      method: 'tools/call',
      params: {
        name: toolName,
        arguments: args
      }
    };
    
    try {
      const response = await this.instance.post(this.url, payload);
      const data = response.data;
      
      if (data.error) {
        console.error(`MCP Error: ${data.error.message}`);
        return null;
      }
      
      return data.result || null;
    } catch (error) {
      console.error('MCP Call Failed:', error.message);
      return null;
    }
  }
  
  listWorkspaces() {
    return this.callTool('list_workspaces');
  }
  
  listAgents(workspaceId = null) {
    const args = workspaceId ? { workspace_id: workspaceId } : {};
    return this.callTool('list_agents', args);
  }
  
  createIssue(title, description = null, workspaceId = null) {
    const args = { title };
    if (description) args.description = description;
    if (workspaceId) args.workspace_id = workspaceId;
    return this.callTool('create_issue', args);
  }
  
  commentIssue(issueId, content) {
    return this.callTool('comment_issue', {
      issue_id: issueId,
      content
    });
  }
  
  updateIssueStatus(issueId, status, workspaceId = null) {
    const args = { issue_id: issueId, status };
    if (workspaceId) args.workspace_id = workspaceId;
    return this.callTool('update_issue_status', args);
  }
}

module.exports = MulticaMCPClient;
```

## 使用示例

### Python 同步

```python
from mcp_client import MulticaMCPClient

# 初始化客户端
client = MulticaMCPClient(api_key="your-api-key")

# 创建工作项
result = client.create_issue(
    title="来自飞书的任务",
    description="自动化工作流",
    workspace_id="ws_abc123"
)

print(f"Created: {result['short_id']}")

# 关闭客户端
client.close()
```

### Python 异步

```python
import asyncio
from mcp_client_async import AsyncMulticaMCPClient

async def main():
    async with AsyncMulticaMCPClient() as client:
        workspaces = await client.call_tool("list_workspaces")
        print(f"Found {len(workspaces)} workspaces")

asyncio.run(main())
```

### Node.js

```javascript
const MulticaMCPClient = require('./mcp-client');

const client = new MulticaMCPClient({
  apiKey: process.env.MCP_API_KEY
});

async function createIssue() {
  const result = await client.createIssue(
    '来自飞书的任务',
    '自动化工作流',
    'ws_abc123'
  );
  
  console.log(`Created: ${result.short_id}`);
}

createIssue().catch(console.error);
```

## 错误处理

```python
# Python 错误处理示例
try:
    result = client.create_issue(
        title="New Task",
        workspace_id="ws_invalid"
    )
    
    if result is None:
        print("Failed to create issue")
    else:
        print(f"Success: {result['id']}")

except Exception as e:
    print(f"Client error: {e}")

finally:
    client.close()
```

## HTTP 请求示例

### cURL

```bash
# 创建工作项
curl -X POST "https://aihub.quectel.com/multica/mcp" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sk_live_xxxxx" \
  -d '{
    "jsonrpc": "2.0",
    "id": "1",
    "method": "tools/call",
    "params": {
      "name": "create_issue",
      "arguments": {
        "title": "New Task",
        "workspace_id": "ws_abc123"
      }
    }
  }'

# 列出工作空间
curl -X POST "https://aihub.quectel.com/multica/mcp" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "1",
    "method": "tools/call",
    "params": {
      "name": "list_workspaces",
      "arguments": {}
    }
  }'
```

## 支持的工具列表

| 工具名 | 描述 | 参数 |
|--------|------|------|
| `list_workspaces` | 列出工作空间 | 无 |
| `list_agents` | 列出智能体 | `workspace_id` (可选) |
| `create_issue` | 创建工作项 | `title`, `description`, `workspace_id`, `assignee_agent_id` |
| `comment_issue` | 添加评论 | `issue_id`, `content` |
| `update_issue_status` | 更新状态 | `issue_id`, `status`, `workspace_id` |

## 最佳实践

1. **环境变量配置** - 从环境变量读取配置，避免硬编码
2. **错误处理** - 检查返回值，处理 JSON-RPC 错误
3. **连接复用** - 使用单例模式复用连接，减少开销
4. **超时设置** - 根据网络情况调整超时时间
5. **日志记录** - 记录所有请求和响应，便于调试
6. **API 密钥** - 生产环境必须使用 API-Key 认证
7. **重试机制** - 实现指数退避重试策略

## 监控和日志

```python
import logging

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

class MulticaMCPClient:
    def call_tool(self, tool_name: str, **arguments):
        logger.info(f"Calling tool: {tool_name} with args: {arguments}")
        result = super().call_tool(tool_name, **arguments)
        logger.info(f"Tool result: {result}")
        return result
```
