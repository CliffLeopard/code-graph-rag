# Code-Graph-RAG MCP 协议详解 - 第五部分：数据结构和类型定义

## 1. MCP 核心类型定义

### 1.1 MCPToolArguments

**位置**: `codebase_rag/types_defs.py`

```python
MCPToolArguments = dict[str, str | int | None]
```

**说明**: 工具参数字典，键为参数名，值为参数值（字符串、整数或 None）

**示例**:
```python
{
    "natural_language_query": "Find all classes",
    "project_name": "my-project",
    "offset": 10,
    "limit": 50
}
```

### 1.2 MCPResultType

**位置**: `codebase_rag/types_defs.py`

```python
MCPResultType = (
    str                    # 文本响应
    | QueryResultDict      # 查询结果
    | CodeSnippetResultDict # 代码片段
    | ListProjectsResult   # 项目列表
    | DeleteProjectResult  # 删除项目结果
)
```

**说明**: 工具返回值的联合类型

## 2. 输入模式类型

### 2.1 MCPInputSchemaProperty

**位置**: `codebase_rag/types_defs.py`

```python
class MCPInputSchemaProperty(TypedDict, total=False):
    type: str              # 参数类型: "string", "integer", "boolean"
    description: str      # 参数描述
    default: str          # 默认值（可选）
```

**示例**:
```python
{
    "type": "string",
    "description": "Your question in plain English about the codebase"
}
```

### 2.2 MCPInputSchema

**位置**: `codebase_rag/types_defs.py`

```python
class MCPInputSchema(TypedDict):
    type: str                              # 总是 "object"
    properties: MCPInputSchemaProperties   # 参数字典
    required: list[str]                    # 必需参数列表
```

**示例**:
```python
{
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

### 2.3 MCPToolSchema

**位置**: `codebase_rag/types_defs.py`

```python
class MCPToolSchema(NamedTuple):
    name: str              # 工具名称
    description: str       # 工具描述
    inputSchema: MCPInputSchema  # 输入模式
```

## 3. 响应结果类型

### 3.1 QueryResultDict

**位置**: `codebase_rag/types_defs.py`

```python
class QueryResultDict(TypedDict, total=False):
    query_used: str        # 使用的 Cypher 查询
    results: list[ResultRow]  # 查询结果行
    summary: str           # 结果摘要
    error: str            # 错误信息（可选）
```

**示例**:
```python
{
    "query_used": "MATCH (c:Class) RETURN c",
    "results": [
        {"name": "UserService", "qualified_name": "com.example.UserService"}
    ],
    "summary": "Found 1 class"
}
```

### 3.2 CodeSnippetResultDict

**位置**: `codebase_rag/types_defs.py`

```python
class CodeSnippetResultDict(TypedDict, total=False):
    qualified_name: str    # 完全限定名
    source_code: str       # 源代码
    file_path: str         # 文件路径
    line_start: int        # 起始行号
    line_end: int          # 结束行号
    docstring: str | None  # 文档字符串
    found: bool            # 是否找到
    error_message: str | None  # 错误信息
    error: str            # 错误（可选）
```

**示例**:
```python
{
    "qualified_name": "com.example.UserService.createUser",
    "source_code": "public User createUser(String name) {...}",
    "file_path": "src/main/java/com/example/UserService.java",
    "line_start": 10,
    "line_end": 12,
    "docstring": "Creates a new user",
    "found": True
}
```

### 3.3 ListProjectsSuccessResult

**位置**: `codebase_rag/types_defs.py`

```python
class ListProjectsSuccessResult(TypedDict):
    projects: list[str]     # 项目名称列表
    count: int            # 项目数量
```

**示例**:
```python
{
    "projects": ["project1", "project2"],
    "count": 2
}
```

### 3.4 ListProjectsErrorResult

**位置**: `codebase_rag/types_defs.py`

```python
class ListProjectsErrorResult(TypedDict):
    projects: list[str]    # 空列表
    count: int             # 0
    error: str            # 错误信息
```

**示例**:
```python
{
    "projects": [],
    "count": 0,
    "error": "Connection failed"
}
```

### 3.5 ListProjectsResult

**位置**: `codebase_rag/types_defs.py`

```python
ListProjectsResult = ListProjectsSuccessResult | ListProjectsErrorResult
```

### 3.6 DeleteProjectSuccessResult

**位置**: `codebase_rag/types_defs.py`

```python
class DeleteProjectSuccessResult(TypedDict):
    success: bool          # True
    project: str          # 项目名称
    message: str         # 成功消息
```

**示例**:
```python
{
    "success": True,
    "project": "my-project",
    "message": "Successfully deleted project 'my-project'."
}
```

### 3.7 DeleteProjectErrorResult

**位置**: `codebase_rag/types_defs.py`

```python
class DeleteProjectErrorResult(TypedDict):
    success: bool          # False
    error: str           # 错误信息
```

**示例**:
```python
{
    "success": False,
    "error": "Project 'my-project' not found"
}
```

### 3.8 DeleteProjectResult

**位置**: `codebase_rag/types_defs.py`

```python
DeleteProjectResult = DeleteProjectSuccessResult | DeleteProjectErrorResult
```

## 4. 工具元数据类型

### 4.1 ToolMetadata

**位置**: `codebase_rag/models.py`

```python
@dataclass
class ToolMetadata:
    name: str                    # 工具名称
    description: str            # 工具描述
    input_schema: MCPInputSchema # 输入参数模式
    handler: MCPHandlerType     # 处理函数
    returns_json: bool          # 是否返回 JSON
```

**字段说明**:
- `name`: 工具的唯一标识符
- `description`: 工具的功能描述
- `input_schema`: JSON Schema 格式的输入参数定义
- `handler`: 异步处理函数
- `returns_json`: 指示返回值是否为 JSON 格式

### 4.2 MCPHandlerType

**位置**: `codebase_rag/types_defs.py`

```python
MCPHandlerType = Callable[..., Awaitable[MCPResultType]]
```

**说明**: 异步函数类型，接受可变参数，返回 `MCPResultType`

**示例**:
```python
async def query_code_graph(natural_language_query: str) -> QueryResultDict:
    # ...
```

## 5. MCP 协议类型

### 5.1 TextContent

**来源**: `mcp.types.TextContent`

```python
class TextContent:
    type: str = "text"
    text: str
```

**说明**: MCP 响应内容格式

**示例**:
```python
TextContent(
    type="text",
    text='{"query_used": "...", "results": [...]}'
)
```

### 5.2 Tool

**来源**: `mcp.types.Tool`

```python
class Tool:
    name: str
    description: str
    inputSchema: dict
```

**说明**: MCP 工具定义

## 6. 常量定义

### 6.1 工具名称

**位置**: `codebase_rag/constants.py`

```python
class MCPToolName(StrEnum):
    LIST_PROJECTS = "list_projects"
    DELETE_PROJECT = "delete_project"
    WIPE_DATABASE = "wipe_database"
    INDEX_REPOSITORY = "index_repository"
    QUERY_CODE_GRAPH = "query_code_graph"
    GET_CODE_SNIPPET = "get_code_snippet"
    SURGICAL_REPLACE_CODE = "surgical_replace_code"
    READ_FILE = "read_file"
    WRITE_FILE = "write_file"
    LIST_DIRECTORY = "list_directory"
```

### 6.2 参数名称

**位置**: `codebase_rag/constants.py`

```python
class MCPParamName(StrEnum):
    PROJECT_NAME = "project_name"
    CONFIRM = "confirm"
    NATURAL_LANGUAGE_QUERY = "natural_language_query"
    QUALIFIED_NAME = "qualified_name"
    FILE_PATH = "file_path"
    TARGET_CODE = "target_code"
    REPLACEMENT_CODE = "replacement_code"
    OFFSET = "offset"
    LIMIT = "limit"
    CONTENT = "content"
    DIRECTORY_PATH = "directory_path"
```

### 6.3 模式类型

**位置**: `codebase_rag/constants.py`

```python
class MCPSchemaType(StrEnum):
    OBJECT = "object"
    STRING = "string"
    INTEGER = "integer"
    BOOLEAN = "boolean"
```

### 6.4 服务器常量

**位置**: `codebase_rag/constants.py`

```python
MCP_SERVER_NAME = "graph-code"
MCP_CONTENT_TYPE_TEXT = "text"
MCP_DEFAULT_DIRECTORY = "."
MCP_JSON_INDENT = 2
MCP_LOG_LEVEL_INFO = "INFO"
MCP_PAGINATION_HEADER = "# Lines {start}-{end} of {total}\n"
```

### 6.5 响应消息键

**位置**: `codebase_rag/constants.py`

```python
MCP_KEY_RESULTS = "results"
MCP_KEY_ERROR = "error"
MCP_KEY_FOUND = "found"
MCP_KEY_ERROR_MESSAGE = "error_message"
MCP_KEY_QUERY_USED = "query_used"
MCP_KEY_SUMMARY = "summary"
MCP_NOT_AVAILABLE = "N/A"
```

## 7. 环境变量

### 7.1 MCPEnvVar

**位置**: `codebase_rag/constants.py`

```python
class MCPEnvVar:
    TARGET_REPO_PATH = "TARGET_REPO_PATH"
    CLAUDE_PROJECT_ROOT = "CLAUDE_PROJECT_ROOT"
    PWD = "PWD"
```

## 8. 错误包装

### 8.1 ERROR_WRAPPER

**位置**: `codebase_rag/tool_errors.py`

```python
ERROR_WRAPPER = "Error: {message}"
```

**使用**:
```python
te.ERROR_WRAPPER.format(message="Connection failed")
# 结果: "Error: Connection failed"
```

## 9. 类型转换

### 9.1 model_dump()

Pydantic 模型的序列化方法：

```python
result_dict: QueryResultDict = graph_data.model_dump()
```

**功能**: 将 Pydantic 模型转换为字典

### 9.2 JSON 序列化

```python
result_text = json.dumps(result, indent=cs.MCP_JSON_INDENT)
```

**功能**: 将 Python 对象序列化为 JSON 字符串

## 10. 数据结构关系图

```
MCPToolArguments
  ↓
传递给
  ↓
MCPHandlerType (异步函数)
  ↓
返回
  ↓
MCPResultType
  ├─→ str
  ├─→ QueryResultDict
  ├─→ CodeSnippetResultDict
  ├─→ ListProjectsResult
  └─→ DeleteProjectResult
  ↓
格式化
  ↓
TextContent
  ↓
JSON-RPC 响应
```

## 11. 工具注册表结构

```
MCPToolsRegistry
  ├─→ _tools: dict[str, ToolMetadata]
  │     ├─→ "list_projects": ToolMetadata
  │     ├─→ "query_code_graph": ToolMetadata
  │     └─→ ...
  │
  ├─→ get_tool_schemas() → list[MCPToolSchema]
  └─→ get_tool_handler(name) → (handler, returns_json)
```

## 12. 相关文档

- [第一部分：MCP 协议概述和服务器初始化](./01-overview-and-initialization.md)
- [第二部分：MCP 协议消息格式](./02-message-format.md)
- [第三部分：工具注册和调度](./03-tool-registry.md)
- [第四部分：工具实现详解](./04-tool-implementations.md)
- [第六部分：完整流程图](./06-flowcharts.md)
