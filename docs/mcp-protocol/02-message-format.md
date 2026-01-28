# Code-Graph-RAG MCP 协议详解 - 第二部分：MCP 协议消息格式

## 1. MCP 协议基础

### 1.1 协议栈

```
应用层: MCP 工具调用
  ↓
协议层: JSON-RPC 2.0
  ↓
传输层: stdio (标准输入/输出)
  ↓
编码: UTF-8
```

### 1.2 JSON-RPC 2.0 基础

MCP 基于 JSON-RPC 2.0 协议，所有消息都是 JSON 格式。

**基本结构**:

```json
{
  "jsonrpc": "2.0",
  "id": <request_id>,
  "method": "<method_name>",
  "params": { ... }
}
```

## 2. 初始化请求

### 2.1 客户端初始化请求

**格式**:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "initialize",
  "params": {
    "protocolVersion": "2024-11-05",
    "capabilities": {},
    "clientInfo": {
      "name": "claude-desktop",
      "version": "1.0.0"
    }
  }
}
```

### 2.2 服务器初始化响应

**格式**:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "protocolVersion": "2024-11-05",
    "capabilities": {
      "tools": {}
    },
    "serverInfo": {
      "name": "graph-code",
      "version": "1.0.0"
    }
  }
}
```

## 3. 工具列表请求/响应

### 3.1 请求格式

**方法**: `tools/list`

**请求**:

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/list",
  "params": {}
}
```

### 3.2 响应格式

**响应**:

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "result": {
    "tools": [
      {
        "name": "list_projects",
        "description": "List all indexed projects...",
        "inputSchema": {
          "type": "object",
          "properties": {},
          "required": []
        }
      },
      {
        "name": "query_code_graph",
        "description": "Query the codebase knowledge graph...",
        "inputSchema": {
          "type": "object",
          "properties": {
            "natural_language_query": {
              "type": "string",
              "description": "Your question in plain English..."
            }
          },
          "required": ["natural_language_query"]
        }
      }
      // ... 更多工具
    ]
  }
}
```

### 3.3 工具模式结构

每个工具的模式包含：

- **`name`**: 工具名称（字符串）
- **`description`**: 工具描述（字符串）
- **`inputSchema`**: JSON Schema 对象
  - `type`: 通常是 "object"
  - `properties`: 参数字典
  - `required`: 必需参数列表

## 4. 工具调用请求/响应

### 4.1 请求格式

**方法**: `tools/call`

**请求**:

```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "method": "tools/call",
  "params": {
    "name": "query_code_graph",
    "arguments": {
      "natural_language_query": "Find all classes in the user module"
    }
  }
}
```

### 4.2 成功响应格式

**响应**:

```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "{\n  \"query_used\": \"MATCH (c:Class)...\",\n  \"results\": [...],\n  \"summary\": \"Found 5 classes\"\n}"
      }
    ],
    "isError": false
  }
}
```

### 4.3 错误响应格式

**响应**:

```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "error": {
    "code": -32603,
    "message": "Internal error",
    "data": {
      "content": [
        {
          "type": "text",
          "text": "Error executing tool 'query_code_graph': Connection failed"
        }
      ],
      "isError": true
    }
  }
}
```

## 5. TextContent 结构

### 5.1 定义

**位置**: `mcp.types.TextContent`

```python
class TextContent:
    type: str = "text"
    text: str
```

### 5.2 使用场景

所有工具响应都包装在 `TextContent` 中：

```python
return [TextContent(type="text", text=result_text)]
```

### 5.3 内容格式

**JSON 工具** (returns_json=True):

```json
{
  "type": "text",
  "text": "{\n  \"query_used\": \"...\",\n  \"results\": [...],\n  \"summary\": \"...\"\n}"
}
```

**文本工具** (returns_json=False):

```json
{
  "type": "text",
  "text": "Successfully indexed repository at /path/to/repo"
}
```

## 6. 工具参数格式

### 6.1 MCPToolArguments

**类型定义**:

```python
MCPToolArguments = dict[str, str | int | None]
```

**示例**:

```python
{
    "natural_language_query": "Find all functions",
    "project_name": "my-project",
    "offset": 10,
    "limit": 50
}
```

### 6.2 参数验证

参数根据工具的 `inputSchema` 进行验证：

```python
inputSchema = {
    "type": "object",
    "properties": {
        "natural_language_query": {
            "type": "string",
            "description": "..."
        }
    },
    "required": ["natural_language_query"]
}
```

## 7. 错误处理格式

### 7.1 错误包装

**位置**: `codebase_rag/tool_errors.py`

```python
ERROR_WRAPPER = "Error: {message}"
```

### 7.2 错误响应结构

```json
{
  "type": "text",
  "text": "Error: Unknown tool: invalid_tool_name"
}
```

### 7.3 错误类型

#### 未知工具错误

```json
{
  "type": "text",
  "text": "Error: Unknown tool: {name}"
}
```

#### 工具执行错误

```json
{
  "type": "text",
  "text": "Error: Error executing tool '{name}': {error}"
}
```

## 8. 具体工具请求示例

### 8.1 list_projects

**请求**:

```json
{
  "jsonrpc": "2.0",
  "id": 4,
  "method": "tools/call",
  "params": {
    "name": "list_projects",
    "arguments": {}
  }
}
```

**响应**:

```json
{
  "jsonrpc": "2.0",
  "id": 4,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "{\n  \"projects\": [\"project1\", \"project2\"],\n  \"count\": 2\n}"
      }
    ]
  }
}
```

### 8.2 query_code_graph

**请求**:

```json
{
  "jsonrpc": "2.0",
  "id": 5,
  "method": "tools/call",
  "params": {
    "name": "query_code_graph",
    "arguments": {
      "natural_language_query": "Show me all classes that contain 'user' in their name"
    }
  }
}
```

**响应**:

```json
{
  "jsonrpc": "2.0",
  "id": 5,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "{\n  \"query_used\": \"MATCH (c:Class) WHERE toLower(c.name) CONTAINS 'user' RETURN c.name AS name, c.qualified_name AS qualified_name LIMIT 50\",\n  \"results\": [\n    {\"name\": \"UserService\", \"qualified_name\": \"com.example.UserService\"},\n    {\"name\": \"UserController\", \"qualified_name\": \"com.example.UserController\"}\n  ],\n  \"summary\": \"Found 2 classes matching 'user'\"\n}"
      }
    ]
  }
}
```

### 8.3 get_code_snippet

**请求**:

```json
{
  "jsonrpc": "2.0",
  "id": 6,
  "method": "tools/call",
  "params": {
    "name": "get_code_snippet",
    "arguments": {
      "qualified_name": "com.example.UserService.createUser"
    }
  }
}
```

**响应**:

```json
{
  "jsonrpc": "2.0",
  "id": 6,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "{\n  \"qualified_name\": \"com.example.UserService.createUser\",\n  \"source_code\": \"public User createUser(String name) {\\n  return new User(name);\\n}\",\n  \"file_path\": \"src/main/java/com/example/UserService.java\",\n  \"line_start\": 10,\n  \"line_end\": 12,\n  \"docstring\": \"Creates a new user\",\n  \"found\": true\n}"
      }
    ]
  }
}
```

### 8.4 read_file

**请求**:

```json
{
  "jsonrpc": "2.0",
  "id": 7,
  "method": "tools/call",
  "params": {
    "name": "read_file",
    "arguments": {
      "file_path": "src/main/java/com/example/UserService.java",
      "offset": 0,
      "limit": 50
    }
  }
}
```

**响应**:

```json
{
  "jsonrpc": "2.0",
  "id": 7,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "# Lines 1-50 of 200\npackage com.example;\n\npublic class UserService {\n  // ... 文件内容 ..."
      }
    ]
  }
}
```

### 8.5 surgical_replace_code

**请求**:

```json
{
  "jsonrpc": "2.0",
  "id": 8,
  "method": "tools/call",
  "params": {
    "name": "surgical_replace_code",
    "arguments": {
      "file_path": "src/main/java/com/example/UserService.java",
      "target_code": "public User createUser(String name) {\n  return new User(name);\n}",
      "replacement_code": "public User createUser(String name) {\n  User user = new User(name);\n  user.setCreatedAt(LocalDateTime.now());\n  return user;\n}"
    }
  }
}
```

**响应**:

```json
{
  "jsonrpc": "2.0",
  "id": 8,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "Successfully replaced code block in src/main/java/com/example/UserService.java"
      }
    ]
  }
}
```

## 9. 分页响应格式

### 9.1 read_file 分页

当使用 `offset` 和 `limit` 参数时，响应包含分页头：

**格式**:

```
# Lines {start}-{end} of {total}
<文件内容>
```

**示例**:

```
# Lines 1-50 of 200
package com.example;

public class UserService {
  // ... 50 行内容 ...
```

### 9.2 分页头常量

```python
MCP_PAGINATION_HEADER = "# Lines {start}-{end} of {total}\n"
```

## 10. JSON 响应格式化

### 10.1 JSON 工具响应

对于 `returns_json=True` 的工具，结果会被格式化为 JSON：

```python
if returns_json:
    result_text = json.dumps(result, indent=cs.MCP_JSON_INDENT)
    # indent=2
```

### 10.2 格式化示例

**输入** (Python dict):

```python
{
    "query_used": "MATCH (c:Class) RETURN c",
    "results": [{"name": "User"}],
    "summary": "Found 1 class"
}
```

**输出** (JSON 字符串):

```json
{
  "query_used": "MATCH (c:Class) RETURN c",
  "results": [
    {
      "name": "User"
    }
  ],
  "summary": "Found 1 class"
}
```

## 11. 相关文档

- [第一部分：MCP 协议概述和服务器初始化](./01-overview-and-initialization.md)
- [第三部分：工具注册和调度](./03-tool-registry.md)
- [第四部分：工具实现详解](./04-tool-implementations.md)
- [第五部分：数据结构和类型定义](./05-data-structures.md)
- [第六部分：完整流程图](./06-flowcharts.md)
