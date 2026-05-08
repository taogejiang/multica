# Feishu MCP 集成指南

本文档说明如何将 Multica MCP 服务与飞书机器人/自动化集成。

## 概览

**MCP 外部访问地址：** `https://aihub.quectel.com/multica/mcp`

**协议：** HTTP POST，JSON-RPC 2.0

**内部部署地址：** `http://localhost:38090/mcp`（Docker Compose）

## MCP 服务器接入参数

### 标准 SSE 接入方式

使用标准 MCP 客户端接入时，采用 SSE (Server-Sent Events) 协议，配置参数如下：

```yaml
# MCP 服务器配置参数
multica_mcp:
  type: "sse"                                    # 传输协议（SSE）
  url: "https://aihub.quectel.com/multica/mcp"  # 公网访问地址
  url_internal: "http://127.0.0.1:38090/mcp"    # 内网访问地址（Docker 内部）
  timeout: 60                                    # 请求超时（秒）
  
# 认证参数（必需）
authentication:
  type: "bearer"                                 # Multica API Token
  headers:
    authorization: "Bearer YOUR_MULTICA_API_TOKEN"  # 前端界面生成的 mul_... token
  notes: |
    - 外部客户端必须携带 Authorization header
    - mcp server 不保存独立鉴权 token，仅透传给 backend
    - token 有效性、过期时间、权限范围统一由 Multica API 校验
```

## 快速参数配置

| 参数 | 值 |
|------|-----|
| **传输方式** | SSE (Server-Sent Events) |
| **端点 URL** | `https://aihub.quectel.com/multica/mcp` |
| **内网 URL** | `http://127.0.0.1:38090/mcp` |
| **超时时间** | 60 秒 |
| **认证** | 必需；传入前端界面生成的 Multica API Token |

## 环境变量（Docker Compose）

```yaml
environment:
  MULTICA_BASE_URL: http://backend:8080        # 后端服务地址
  MULTICA_WORKSPACE_ID: ws_abc123               # 默认工作空间（可选）
  REQUEST_TIMEOUT_SECONDS: 60                   # 请求超时
  LOG_LEVEL: INFO                               # 日志级别
```

## 工具清单

所有工具都通过 MCP 自动发现，可用 `tools/list` 查询。

### 1. list_workspaces

列出所有工作空间。

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "list_workspaces",
    "arguments": {}
  }
}
```

### 2. list_agents

列出指定工作空间的所有智能体。

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/call",
  "params": {
    "name": "list_agents",
    "arguments": {
      "workspace_id": "ws_abc123"
    }
  }
}
```

### 3. create_issue

创建一个新的工作项。

```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "method": "tools/call",
  "params": {
    "name": "create_issue",
    "arguments": {
      "title": "实现登录流程",
      "description": "需要集成 OAuth 回调",
      "workspace_id": "ws_abc123",
      "assignee_agent_id": "agt_xyz789"
    }
  }
}
```

**参数说明：**
- `title` (必填)：工作项标题
- `description` (可选)：描述
- `workspace_id` (可选)：工作空间 ID，默认使用环境变量 `MULTICA_WORKSPACE_ID`
- `assignee_agent_id` (可选)：分配给的智能体 ID

### 4. comment_issue

给工作项添加评论。

```json
{
  "jsonrpc": "2.0",
  "id": 4,
  "method": "tools/call",
  "params": {
    "name": "comment_issue",
    "arguments": {
      "issue_id": "ABC-123",
      "content": "这是来自飞书机器人的评论"
    }
  }
}
```

### 5. update_issue_status

更新工作项状态。

```json
{
  "jsonrpc": "2.0",
  "id": 5,
  "method": "tools/call",
  "params": {
    "name": "update_issue_status",
    "arguments": {
      "issue_id": "ABC-123",
      "status": "in_review",
      "workspace_id": "ws_abc123"
    }
  }
}
```

**支持的状态值：**
- `todo` — 待处理
- `in_progress` — 进行中
- `in_review` — 审核中
- `done` — 已完成
- `blocked` — 阻塞中

## 标准 MCP SSE 客户端接入方式

### Python 客户端（使用 mcp 库）

```python
import asyncio
from mcp import ClientSession
from mcp.client.sse import sse_client

class MulticaMCPClient:
    """Multica MCP SSE 客户端"""
    
    def __init__(
        self,
        url: str = "https://aihub.quectel.com/multica/mcp",
        headers: dict = None
    ):
        """
        初始化 MCP 客户端
        
        参数:
            url: MCP 服务器地址
            headers: 自定义 HTTP headers（包含认证信息）
        """
        self.url = url
        self.headers = headers or {
            "authorization": "Bearer YOUR_MULTICA_API_TOKEN"
        }
        self.session = None
    
    async def connect(self):
        """连接到 MCP 服务器"""
        # 使用 SSE 传输
        transport = sse_client(self.url, headers=self.headers)
        self.session = ClientSession(transport)
        await self.session.initialize()
        return self
    
    async def list_tools(self) -> list:
        """列出所有可用工具"""
        response = await self.session.list_tools()
        return response.tools
    
    async def call_tool(self, tool_name: str, **arguments):
        """调用 MCP 工具"""
        response = await self.session.call_tool(tool_name, arguments)
        if response.isError:
            raise RuntimeError(f"Tool call failed: {response.content}")
        return response.content[0].text if response.content else None
    
    async def close(self):
        """关闭连接"""
        if self.session:
            await self.session.close()

# 异步使用示例
async def main():
    client = MulticaMCPClient(
        url="https://aihub.quectel.com/multica/mcp",
        headers={"authorization": "Bearer YOUR_MULTICA_API_TOKEN"}
    )
    
    async with await client.connect() as client:
        # 列出工具
        tools = await client.list_tools()
        print(f"Available tools: {[t.name for t in tools]}")
        
        # 创建工作项
        result = await client.call_tool(
            "create_issue",
            title="来自飞书的任务",
            workspace_id="ws_abc123"
        )
        print(f"Created: {result}")

asyncio.run(main())
```

### Node.js 客户端（使用 @modelcontextprotocol/sdk）

```javascript
const { Client } = require("@modelcontextprotocol/sdk/client/index.js");
const { SSEClientTransport } = require("@modelcontextprotocol/sdk/client/sse.js");

class MulticaMCPClient {
  constructor(options = {}) {
    this.url = options.url || "https://aihub.quectel.com/multica/mcp";
    this.headers = options.headers || {
      "authorization": "Bearer YOUR_MULTICA_API_TOKEN"
    };
    this.client = null;
  }
  
  async connect() {
    // 创建 SSE 传输
    const transport = new SSEClientTransport({
      url: this.url,
      headers: this.headers
    });
    
    this.client = new Client({
      name: "feishu-bot",
      version: "1.0.0"
    });
    
    await this.client.connect(transport);
    return this;
  }
  
  async listTools() {
    const result = await this.client.request({ method: "tools/list" }, []);
    return result.tools;
  }
  
  async callTool(toolName, args = {}) {
    const result = await this.client.request(
      {
        method: "tools/call",
        params: {
          name: toolName,
          arguments: args
        }
      },
      []
    );
    return result.content[0].text;
  }
  
  async close() {
    if (this.client) {
      await this.client.close();
    }
  }
}

// 使用示例
(async () => {
  const client = new MulticaMCPClient({
    url: "https://aihub.quectel.com/multica/mcp",
    headers: {
      "authorization": "Bearer YOUR_MULTICA_API_TOKEN"
    }
  });
  
  await client.connect();
  
  // 列出工具
  const tools = await client.listTools();
  console.log('Available tools:', tools.map(t => t.name));
  
  // 创建工作项
  const result = await client.callTool('create_issue', {
    title: '来自飞书的任务',
    workspace_id: 'ws_abc123'
  });
  console.log('Created:', result);
  
  await client.close();
})();
```

## 飞书集成示例

### Node.js 后端（使用 SSE 客户端）

```javascript
const { Client } = require("@modelcontextprotocol/sdk/client/index.js");
const { SSEClientTransport } = require("@modelcontextprotocol/sdk/client/sse.js");
const express = require('express');

const app = express();
app.use(express.json());

let mcpClient = null;

// 初始化 MCP 客户端
async function initMCPClient() {
  if (!mcpClient) {
    const transport = new SSEClientTransport({
      url: "https://aihub.quectel.com/multica/mcp",
      headers: {
        "authorization": "Bearer YOUR_MULTICA_API_TOKEN"
      }
    });
    
    mcpClient = new Client({
      name: "feishu-bot",
      version: "1.0.0"
    });
    
    await mcpClient.connect(transport);
  }
  return mcpClient;
}

// 飞书机器人事件处理
app.post('/feishu/webhook', async (req, res) => {
  const { text, user_id } = req.body;
  
  try {
    const client = await initMCPClient();
    
    // 处理 /create-issue 命令
    if (text && text.startsWith('/create-issue')) {
      const title = text.replace('/create-issue', '').trim();
      
      const result = await client.request(
        {
          method: "tools/call",
          params: {
            name: "create_issue",
            arguments: {
              title: title,
              description: `来自飞书用户: ${user_id}`,
              workspace_id: process.env.MULTICA_WORKSPACE_ID
            }
          }
        },
        []
      );
      
      const content = result.content[0];
      if (content) {
        return res.json({
          text: `✓ 工作项已创建\n${content.text}`
        });
      }
    }
    
    // 处理 /list-workspaces 命令
    if (text === '/list-workspaces') {
      const result = await client.request(
        {
          method: "tools/call",
          params: {
            name: "list_workspaces",
            arguments: {}
          }
        },
        []
      );
      
      const content = result.content[0];
      if (content) {
        return res.json({ text: `工作空间列表:\n${content.text}` });
      }
    }
    
    res.json({ text: '未知命令' });
  } catch (error) {
    console.error('Error:', error);
    res.status(500).json({ text: '操作失败' });
  }
});

app.listen(3000, () => console.log('Feishu Bot listening on 3000'));
```

### Python 后端（使用 SSE 客户端）

```python
from fastapi import FastAPI
from pydantic import BaseModel
import asyncio
from mcp import ClientSession
from mcp.client.sse import sse_client
import os

app = FastAPI()

# 全局 MCP 客户端
mcp_client = None

async def init_mcp_client():
    """初始化 MCP 客户端"""
    global mcp_client
    if mcp_client is None:
        transport = sse_client(
            url="https://aihub.quectel.com/multica/mcp",
            headers={"authorization": "Bearer YOUR_MULTICA_API_TOKEN"}
        )
        mcp_client = ClientSession(transport)
        await mcp_client.initialize()
    return mcp_client

class FeishuMessage(BaseModel):
    text: str
    user_id: str

@app.post('/feishu/webhook')
async def feishu_webhook(message: FeishuMessage):
    """飞书机器人 webhook 处理"""
    try:
        client = await init_mcp_client()
        text = message.text
        user_id = message.user_id
        
        # 处理 /create-issue 命令
        if text.startswith('/create-issue'):
            title = text.replace('/create-issue', '').strip()
            
            result = await client.call_tool(
                'create_issue',
                title=title,
                description=f'来自飞书用户: {user_id}',
                workspace_id=os.getenv('MULTICA_WORKSPACE_ID')
            )
            
            if result:
                return {'text': f"✓ 工作项已创建\n{result}"}
        
        # 处理 /list-workspaces 命令
        if text == '/list-workspaces':
            result = await client.call_tool('list_workspaces')
            
            if result:
                return {'text': f"工作空间列表:\n{result}"}
        
        return {'text': '未知命令'}
    
    except Exception as e:
        print(f"Error: {e}")
        return {'text': '操作失败'}, 500

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=3000)
```

### 飞书卡片交互

发送富文本卡片给飞书，包含按钮触发 MCP 操作：

```json
{
  "msg_type": "interactive",
  "card": {
    "config": {
      "wide_screen_mode": true,
      "enable_forward": true
    },
    "header": {
      "title": {
        "content": "Multica 工作项管理",
        "tag": "plain_text"
      }
    },
    "elements": [
      {
        "tag": "div",
        "text": {
          "content": "**选择操作：**",
          "tag": "lark_md"
        }
      },
      {
        "tag": "action",
        "actions": [
          {
            "type": "button",
            "text": {
              "content": "创建工作项",
              "tag": "lark_md"
            },
            "value": {
              "action": "create_issue"
            }
          },
          {
            "type": "button",
            "text": {
              "content": "查看工作空间",
              "tag": "lark_md"
            },
            "value": {
              "action": "list_agents"
            }
          }
        ]
      }
    ]
  }
}
```

## 飞书接入部署清单

### MCP 配置文件示例（mcp.json）

在飞书客户端或机器人框架的 MCP 配置文件中添加：

```json
{
  "servers": {
    "multica_mcp": {
      "type": "sse",
      "url": "https://aihub.quectel.com/multica/mcp",
      "headers": {
        "authorization": "Bearer YOUR_MULTICA_API_TOKEN"
      }
    }
  }
}
```

### 环境变量配置

将以下配置信息添加到飞书机器人后端的环境变量或配置文件中：

```bash
# MCP 服务器配置
MULTICA_MCP_URL="https://aihub.quectel.com/multica/mcp"         # SSE 端点
MULTICA_MCP_TYPE="sse"                                          # 传输方式

# 认证配置（必需）
MULTICA_MCP_AUTHORIZATION="Bearer YOUR_MULTICA_API_TOKEN"      # 前端界面生成的 mul_... token

# Multica 工作空间配置
MULTICA_WORKSPACE_ID="ws_abc123"                                # 默认工作空间 ID

# 可选：日志级别
MULTICA_LOG_LEVEL="INFO"
```

## MCP 服务器端点列表

| 环境 | 地址 | 说明 |
|------|------|------|
| 生产 | `https://aihub.quectel.com/multica/mcp` | SSE 公开端点 |
| 测试 | `http://127.0.0.1:38090/mcp` | 本地测试 |
| 内网 | `http://localhost:38090/mcp` | Docker 内网 |

### docker-compose.yml 示例

```yaml
services:
  feishu-bot:
    image: feishu-bot:latest
    environment:
      # MCP 服务器配置
      MULTICA_MCP_URL: "https://aihub.quectel.com/multica/mcp"
      MULTICA_MCP_TYPE: "sse"
      MULTICA_WORKSPACE_ID: "ws_abc123"
      # 认证配置
      MULTICA_MCP_AUTHORIZATION: "Bearer ${MULTICA_API_TOKEN}"
    ports:
      - "3000:3000"
    depends_on:
      - multica-mcp-server

  multica-mcp-server:
    image: multica-private-mcp:v0.2.15
    environment:
      MULTICA_BASE_URL: "http://backend:8080"
      MULTICA_WORKSPACE_ID: "ws_abc123"
      LOG_LEVEL: "INFO"
    ports:
      - "38090:8090"
    depends_on:
      - backend
```

## 可用工具列表

### 1. list_workspaces
列出所有工作空间
- 无参数
- 返回：工作空间列表

### 2. list_agents
列出工作空间内的所有智能体
- 参数：`workspace_id` (可选)
- 返回：智能体列表

### 3. create_issue
创建新工作项
- 参数：
  - `title` (必填) - 工作项标题
  - `description` (可选) - 描述
  - `workspace_id` (可选) - 工作空间 ID
  - `assignee_agent_id` (可选) - 分配给的智能体
- 返回：创建的工作项信息

### 4. comment_issue
添加工作项评论
- 参数：
  - `issue_id` (必填) - 工作项 ID
  - `content` (必填) - 评论内容
- 返回：评论信息

### 5. update_issue_status
更新工作项状态
- 参数：
  - `issue_id` (必填) - 工作项 ID
  - `status` (必填) - 新状态 (todo/in_progress/in_review/done/blocked)
  - `workspace_id` (可选) - 工作空间 ID
- 返回：更新后的工作项信息

## 安全建议

在生产环境部署前，建议加入以下安全措施：

## 安全建议

### 1. API 密钥认证

在飞书机器人请求中添加 API-Key header：

```python
headers = {
    'Content-Type': 'application/json',
    'X-API-Key': os.getenv('MCP_API_KEY'),  # 从环境变量读取
    'User-Agent': 'Feishu-Bot/1.0'
}
```

建议在 MCP 服务器添加对应的验证逻辑。

### 2. Nginx 安全配置

```nginx
# IP 白名单（允许飞书服务器 IP）
location ^~ /multica/mcp {
    # 只允许飞书出口 IP 和内网 IP
    allow 10.0.0.0/8;           # 内网
    allow YOUR_FEISHU_IP;       # 飞书出口 IP
    deny all;
    
    # 反向代理配置
    proxy_pass http://127.0.0.1:38090/mcp;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    
    # 安全 headers
    proxy_set_header X-API-Key $http_x_api_key;
    
    # 超时配置
    proxy_read_timeout 60s;
    proxy_connect_timeout 10s;
}
```

### 3. 速率限制

```nginx
# 定义速率限制区间
limit_req_zone $binary_remote_addr zone=mcp_limit:10m rate=10r/s;

location ^~ /multica/mcp {
    # 应用速率限制
    limit_req zone=mcp_limit burst=20 nodelay;
    
    proxy_pass http://127.0.0.1:38090/mcp;
}
```

### 4. 请求签名验证

```python
import hmac
import hashlib
import json
from time import time

class MCPRequestSigner:
    """MCP 请求签名生成和验证"""
    
    def __init__(self, secret: str):
        self.secret = secret.encode('utf-8')
    
    def sign_request(self, payload: dict, timestamp: int = None) -> str:
        """生成请求签名"""
        if timestamp is None:
            timestamp = int(time())
        
        # 签名内容：timestamp + payload
        sign_content = f"{timestamp}|{json.dumps(payload, separators=(',', ':'))}"
        signature = hmac.new(
            self.secret,
            sign_content.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return signature
    
    def verify_request(self, payload: dict, signature: str, timestamp: int) -> bool:
        """验证请求签名"""
        expected_signature = self.sign_request(payload, timestamp)
        return hmac.compare_digest(signature, expected_signature)

# 使用示例
signer = MCPRequestSigner(secret='your-secret-key')

# 客户端：生成签名
payload = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {"name": "list_workspaces"}
}
timestamp = int(time())
signature = signer.sign_request(payload, timestamp)

# 发送请求时附加签名
headers = {
    'Content-Type': 'application/json',
    'X-Signature': signature,
    'X-Timestamp': str(timestamp)
}
```

### 5. 环境变量安全

```bash
# .env 文件（生产环境勿提交）
MULTICA_MCP_URL="https://aihub.quectel.com/multica/mcp"
MULTICA_WORKSPACE_ID="ws_abc123"
MCP_API_KEY="sk_live_xxxxxxxxxxxxx"  # 从密钥管理系统读取
MCP_API_SECRET="secret_xxxxxxxx"     # 从密钥管理系统读取
```

## 故障排查

### 问题：请求返回 404

**检查点：**
- 确认 `https://aihub.quectel.com/multica/mcp` 可访问
- 检查 Nginx 配置是否正确
- 查看 Nginx 日志：`tail -f /etc/nginx/log/access.log | grep /multica/mcp`

### 问题：返回 401/403

**检查点：**
- 确认请求头中的 `Authorization` 使用前端界面生成的 `mul_...` token
- 确认 token 有足够权限访问指定工作空间
- 检查 backend API 的鉴权日志或网关限制

### 问题：请求超时

**检查点：**
- 确认后端服务运行：`docker ps | grep multica`
- 增加 `REQUEST_TIMEOUT_SECONDS` 环境变量
- 检查容器日志：`docker logs multica-private-mcp-server-1`

### 问题：工具返回错误

查看 MCP 返回的 `error` 字段：

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "error": {
    "code": -32000,
    "message": "upstream http error",
    "data": {
      "status_code": 400,
      "detail": "Invalid workspace_id"
    }
  }
}
```

## 监控和日志

### 查看 MCP 服务日志

```bash
docker logs -f multica-private-mcp-server-1
```

### 本地测试

```bash
# 初始化
curl -s http://127.0.0.1:38090/mcp \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer mul_xxxxx' \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}'

# 列出工具
curl -s http://127.0.0.1:38090/mcp \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer mul_xxxxx' \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}'

# 健康检查
curl -s http://127.0.0.1:38090/health
```

## 完整工作流示例

```
用户在飞书输入: /create-issue 修复登录 bug

    ↓

飞书机器人后端接收消息
  ↓ 解析命令
call_multica_mcp('create_issue', {'title': '修复登录 bug'})
  ↓ 发送 HTTP POST
POST https://aihub.quectel.com/multica/mcp
{
  "jsonrpc": "2.0",
  "id": "feishu-xxx",
  "method": "tools/call",
  "params": {
    "name": "create_issue",
    "arguments": {
      "title": "修复登录 bug",
      "workspace_id": "ws_abc123"
    }
  }
}
  ↓ Nginx 反向代理
127.0.0.1:38090/mcp
  ↓ FastMCP 解析并调用工具
  ↓ 工具透传 Authorization 到 backend API
  ↓ backend 使用 Multica API Token 完成鉴权与权限校验
  ↓ 返回结果
{
  "jsonrpc": "2.0",
  "id": "feishu-xxx",
  "result": {
    "id": "12345",
    "short_id": "ABC-123",
    "title": "修复登录 bug",
    "status": "todo",
    "url": "https://aihub.quectel.com/multica/issues/ABC-123"
  }
}
  ↓ 飞书机器人后端处理响应
  ↓ 回复飞书用户
"✓ 工作项已创建: ABC-123
链接: https://aihub.quectel.com/multica/issues/ABC-123"
```
