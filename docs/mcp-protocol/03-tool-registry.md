# Code-Graph-RAG MCP 协议详解 - 第三部分：工具注册和调度

## 1. MCPToolsRegistry 概述

### 1.1 类定义

**位置**: `codebase_rag/mcp/tools.py`

```python
class MCPToolsRegistry:
    def __init__(
        self,
        project_root: str,
        ingestor: MemgraphIngestor,
        cypher_gen: CypherGenerator,
    ) -> None:
```

### 1.2 核心职责

- 注册所有 MCP 工具
- 管理工具元数据
- 提供工具查找和调用接口
- 处理工具输入参数验证

## 2. 初始化流程

### 2.1 构造函数执行

```python
def __init__(self, project_root: str, ingestor: MemgraphIngestor, cypher_gen: CypherGenerator):
    # 步骤 1: 存储依赖
    self.project_root = project_root
    self.ingestor = ingestor
    self.cypher_gen = cypher_gen

    # 步骤 2: 加载解析器
    self.parsers, self.queries = load_parsers()

    # 步骤 3: 创建工具实例
    self.code_retriever = CodeRetriever(project_root, ingestor)
    self.file_editor = FileEditor(project_root=project_root)
    self.file_reader = FileReader(project_root=project_root)
    self.file_writer = FileWriter(project_root=project_root)
    self.directory_lister = DirectoryLister(project_root=project_root)

    # 步骤 4: 创建工具包装器
    self._query_tool = create_query_tool(ingestor=ingestor, cypher_gen=cypher_gen, console=None)
    self._code_tool = create_code_retrieval_tool(code_retriever=self.code_retriever)
    self._file_editor_tool = create_file_editor_tool(file_editor=self.file_editor)
    self._file_reader_tool = create_file_reader_tool(file_reader=self.file_reader)
    self._file_writer_tool = create_file_writer_tool(file_writer=self.file_writer)
    self._directory_lister_tool = create_directory_lister_tool(directory_lister=self.directory_lister)

    # 步骤 5: 注册所有工具
    self._tools: dict[str, ToolMetadata] = {
        # ... 工具注册
    }
```

## 3. 工具注册机制

### 3.1 工具字典结构

```python
self._tools: dict[str, ToolMetadata] = {
    "list_projects": ToolMetadata(...),
    "delete_project": ToolMetadata(...),
    "wipe_database": ToolMetadata(...),
    # ... 更多工具
}
```

### 3.2 ToolMetadata 结构

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

### 3.3 工具注册示例

#### list_projects 工具

```python
cs.MCPToolName.LIST_PROJECTS: ToolMetadata(
    name=cs.MCPToolName.LIST_PROJECTS,  # "list_projects"
    description=td.MCP_TOOLS[cs.MCPToolName.LIST_PROJECTS],
    input_schema=MCPInputSchema(
        type=cs.MCPSchemaType.OBJECT,  # "object"
        properties={},                  # 无参数
        required=[],
    ),
    handler=self.list_projects,         # 处理函数
    returns_json=True,                  # 返回 JSON
)
```

#### query_code_graph 工具

```python
cs.MCPToolName.QUERY_CODE_GRAPH: ToolMetadata(
    name=cs.MCPToolName.QUERY_CODE_GRAPH,  # "query_code_graph"
    description=td.MCP_TOOLS[cs.MCPToolName.QUERY_CODE_GRAPH],
    input_schema=MCPInputSchema(
        type=cs.MCPSchemaType.OBJECT,
        properties={
            cs.MCPParamName.NATURAL_LANGUAGE_QUERY: MCPInputSchemaProperty(
                type=cs.MCPSchemaType.STRING,
                description=td.MCP_PARAM_NATURAL_LANGUAGE_QUERY,
            )
        },
        required=[cs.MCPParamName.NATURAL_LANGUAGE_QUERY],
    ),
    handler=self.query_code_graph,
    returns_json=True,
)
```

## 4. 工具查找：get_tool_handler()

### 4.1 函数签名

```python
def get_tool_handler(
    self,
    name: str
) -> tuple[MCPHandlerType, bool] | None:
```

### 4.2 执行流程

```python
def get_tool_handler(self, name: str) -> tuple[MCPHandlerType, bool] | None:
    # 步骤 1: 查找工具元数据
    metadata = self._tools.get(name)

    # 步骤 2: 如果不存在，返回 None
    if metadata is None:
        return None

    # 步骤 3: 返回处理器和返回类型标志
    return (metadata.handler, metadata.returns_json)
```

### 4.3 返回值

- **成功**: `(handler_function, returns_json_flag)`
- **失败**: `None`

## 5. 工具模式获取：get_tool_schemas()

### 5.1 函数签名

```python
def get_tool_schemas(self) -> list[MCPToolSchema]:
```

### 5.2 执行流程

```python
def get_tool_schemas(self) -> list[MCPToolSchema]:
    return [
        MCPToolSchema(
            name=metadata.name,
            description=metadata.description,
            inputSchema=metadata.input_schema,
        )
        for metadata in self._tools.values()
    ]
```

### 5.3 MCPToolSchema 结构

**位置**: `codebase_rag/types_defs.py`

```python
class MCPToolSchema(NamedTuple):
    name: str
    description: str
    inputSchema: MCPInputSchema
```

## 6. 工具调度流程

### 6.1 在 call_tool 中的使用

```python
@server.call_tool()
async def call_tool(name: str, arguments: MCPToolArguments) -> list[TextContent]:
    # 步骤 1: 查找工具处理器
    handler_info = tools.get_tool_handler(name)

    if not handler_info:
        # 工具不存在
        return _create_error_content(...)

    # 步骤 2: 解包处理器信息
    handler, returns_json = handler_info
    # handler: 异步函数
    # returns_json: 布尔值，指示是否返回 JSON

    # 步骤 3: 调用处理器（展开参数）
    result = await handler(**arguments)
    # arguments: {"natural_language_query": "..."}
    # 调用: handler(natural_language_query="...")

    # 步骤 4: 格式化结果
    if returns_json:
        result_text = json.dumps(result, indent=2)
    else:
        result_text = str(result)

    # 步骤 5: 返回 TextContent
    return [TextContent(type="text", text=result_text)]
```

## 7. 输入参数验证

### 7.1 参数展开

MCP 框架会自动根据 `inputSchema` 验证参数，然后展开传递给处理器：

```python
# MCP 请求参数
arguments = {
    "natural_language_query": "Find all classes"
}

# 展开为函数参数
await handler(natural_language_query="Find all classes")
```

### 7.2 必需参数检查

MCP 框架会检查 `required` 字段：

```python
input_schema = {
    "type": "object",
    "properties": {
        "natural_language_query": {...}
    },
    "required": ["natural_language_query"]  # 必需参数
}
```

如果缺少必需参数，MCP 框架会返回错误，不会调用处理器。

## 8. 工具处理器类型

### 8.1 MCPHandlerType

**位置**: `codebase_rag/types_defs.py`

```python
MCPHandlerType = Callable[..., Awaitable[MCPResultType]]
```

**特点**:

- 异步函数
- 可变参数（\*\*kwargs）
- 返回 `MCPResultType`

### 8.2 MCPResultType

```python
MCPResultType = (
    str                    # 文本响应
    | QueryResultDict      # 查询结果
    | CodeSnippetResultDict # 代码片段
    | ListProjectsResult   # 项目列表
    | DeleteProjectResult  # 删除项目结果
)
```

## 9. 工具分类

### 9.1 项目管理工具

- `list_projects`: 列出所有项目
- `delete_project`: 删除指定项目
- `wipe_database`: 清空整个数据库
- `index_repository`: 索引仓库

### 9.2 代码查询工具

- `query_code_graph`: 查询代码图谱
- `get_code_snippet`: 获取代码片段

### 9.3 文件操作工具

- `read_file`: 读取文件
- `write_file`: 写入文件
- `list_directory`: 列出目录

### 9.4 代码编辑工具

- `surgical_replace_code`: 精确替换代码

## 10. 工具创建函数

### 10.1 create_mcp_tools_registry()

**位置**: `codebase_rag/mcp/tools.py`

```python
def create_mcp_tools_registry(
    project_root: str,
    ingestor: MemgraphIngestor,
    cypher_gen: CypherGenerator,
) -> MCPToolsRegistry:
    return MCPToolsRegistry(
        project_root=project_root,
        ingestor=ingestor,
        cypher_gen=cypher_gen,
    )
```

### 10.2 使用场景

在 `create_server()` 中调用：

```python
tools = create_mcp_tools_registry(
    project_root=str(project_root),
    ingestor=ingestor,
    cypher_gen=cypher_generator,
)
```

## 11. 工具注册表结构

### 11.1 内部工具字典

```python
_tools: dict[str, ToolMetadata]
```

**键**: 工具名称（字符串）
**值**: ToolMetadata 对象

### 11.2 工具查找流程

```
工具名称
  ↓
_tools.get(name)
  ↓
ToolMetadata
  ↓
提取 handler 和 returns_json
  ↓
返回 (handler, returns_json)
```

## 12. 相关文档

- [第一部分：MCP 协议概述和服务器初始化](./01-overview-and-initialization.md)
- [第二部分：MCP 协议消息格式](./02-message-format.md)
- [第四部分：工具实现详解](./04-tool-implementations.md)
- [第五部分：数据结构和类型定义](./05-data-structures.md)
- [第六部分：完整流程图](./06-flowcharts.md)
