# Code-Graph-RAG MCP 协议详解 - 第一部分：MCP 协议概述和服务器初始化

## 1. MCP 协议简介

### 1.1 什么是 MCP？

Model Context Protocol (MCP) 是一个开放标准，用于 AI 应用程序与外部数据源和工具之间的安全、结构化通信。code-graph-rag 实现了 MCP 服务器，提供代码库知识图谱的查询和操作能力。

### 1.2 MCP 服务器特点

- **标准化协议**: 基于 JSON-RPC 2.0
- **stdio 通信**: 通过标准输入/输出进行通信
- **工具化接口**: 提供多个工具供客户端调用
- **类型安全**: 使用 JSON Schema 定义输入参数

## 2. 服务器启动入口

### 2.1 CLI 命令

**位置**: `codebase_rag/cli.py`

```python
@app.command(name=ch.CLICommandName.MCP_SERVER, help=ch.CMD_MCP_SERVER)
def mcp_server() -> None:
    try:
        from codebase_rag.mcp import main as mcp_main
        asyncio.run(mcp_main())
    except KeyboardInterrupt:
        app_context.console.print(style(cs.CLI_MSG_MCP_TERMINATED, cs.Color.RED))
    except ValueError as e:
        app_context.console.print(style(cs.CLI_ERR_CONFIG.format(error=e), cs.Color.RED))
        app_context.console.print(style(cs.CLI_MSG_HINT_TARGET_REPO, cs.Color.YELLOW))
    except Exception as e:
        app_context.console.print(style(cs.CLI_ERR_MCP_SERVER.format(error=e), cs.Color.RED))
```

### 2.2 主函数

**位置**: `codebase_rag/mcp/server.py`

```python
async def main() -> None:
    logger.info(lg.MCP_SERVER_STARTING)

    # 创建服务器和数据库连接
    server, ingestor = create_server()
    logger.info(lg.MCP_SERVER_CREATED)

    # 使用上下文管理器管理数据库连接
    with ingestor:
        logger.info(
            lg.MCP_SERVER_CONNECTED.format(
                host=settings.MEMGRAPH_HOST,
                port=settings.MEMGRAPH_PORT
            )
        )
        try:
            # 启动 stdio 服务器
            async with stdio_server() as (read_stream, write_stream):
                await server.run(
                    read_stream,
                    write_stream,
                    server.create_initialization_options()
                )
        except Exception as e:
            logger.error(lg.MCP_SERVER_FATAL_ERROR.format(error=e))
            raise
        finally:
            logger.info(lg.MCP_SERVER_SHUTDOWN)
```

## 3. 服务器创建：create_server()

### 3.1 函数签名

```python
def create_server() -> tuple[Server, MemgraphIngestor]:
```

### 3.2 执行流程

```python
def create_server() -> tuple[Server, MemgraphIngestor]:
    # 步骤 1: 设置日志
    setup_logging()

    # 步骤 2: 获取项目根目录
    try:
        project_root = get_project_root()
        logger.info(lg.MCP_SERVER_USING_ROOT.format(path=project_root))
    except ValueError as e:
        logger.error(lg.MCP_SERVER_CONFIG_ERROR.format(error=e))
        raise

    # 步骤 3: 初始化服务
    logger.info(lg.MCP_SERVER_INIT_SERVICES)

    # 步骤 4: 创建数据库连接器
    ingestor = MemgraphIngestor(
        host=settings.MEMGRAPH_HOST,
        port=settings.MEMGRAPH_PORT,
        batch_size=settings.MEMGRAPH_BATCH_SIZE,
    )

    # 步骤 5: 创建 Cypher 查询生成器
    cypher_generator = CypherGenerator()

    # 步骤 6: 创建工具注册表
    tools = create_mcp_tools_registry(
        project_root=str(project_root),
        ingestor=ingestor,
        cypher_gen=cypher_generator,
    )

    logger.info(lg.MCP_SERVER_INIT_SUCCESS)

    # 步骤 7: 创建 MCP 服务器
    server = Server(cs.MCP_SERVER_NAME)  # "graph-code"

    # 步骤 8: 注册工具列表处理器
    @server.list_tools()
    async def list_tools() -> list[Tool]:
        # ...

    # 步骤 9: 注册工具调用处理器
    @server.call_tool()
    async def call_tool(name: str, arguments: MCPToolArguments) -> list[TextContent]:
        # ...

    return server, ingestor
```

## 4. 项目根目录解析：get_project_root()

### 4.1 函数签名

```python
def get_project_root() -> Path:
```

### 4.2 解析优先级

```python
def get_project_root() -> Path:
    # 优先级 1: 环境变量 TARGET_REPO_PATH
    repo_path: str | None = (
        os.environ.get(cs.MCPEnvVar.TARGET_REPO_PATH)
        or settings.TARGET_REPO_PATH
    )

    # 优先级 2: 环境变量 CLAUDE_PROJECT_ROOT
    if not repo_path:
        repo_path = os.environ.get(cs.MCPEnvVar.CLAUDE_PROJECT_ROOT)

    # 优先级 3: 环境变量 PWD
    if not repo_path:
        repo_path = os.environ.get(cs.MCPEnvVar.PWD)

    # 优先级 4: 当前工作目录
    if not repo_path:
        repo_path = str(Path.cwd())
        logger.info(lg.MCP_SERVER_NO_ROOT.format(path=repo_path))

    project_root = Path(repo_path).resolve()

    # 验证路径
    if not project_root.exists():
        raise ValueError(te.MCP_PATH_NOT_EXISTS.format(path=project_root))

    if not project_root.is_dir():
        raise ValueError(te.MCP_PATH_NOT_DIR.format(path=project_root))

    logger.info(lg.MCP_SERVER_ROOT_RESOLVED.format(path=project_root))
    return project_root
```

### 4.3 环境变量

```python
class MCPEnvVar:
    TARGET_REPO_PATH = "TARGET_REPO_PATH"
    CLAUDE_PROJECT_ROOT = "CLAUDE_PROJECT_ROOT"
    PWD = "PWD"
```

## 5. 日志设置：setup_logging()

### 5.1 函数签名

```python
def setup_logging() -> None:
```

### 5.2 执行流程

```python
def setup_logging() -> None:
    logger.remove()  # 移除默认处理器
    logger.add(
        sys.stderr,                    # 输出到标准错误
        level=cs.MCP_LOG_LEVEL_INFO,   # INFO 级别
        format=cs.MCP_LOG_FORMAT,      # 格式化字符串
    )
```

### 5.3 日志格式

```python
MCP_LOG_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
    "<level>{level: <8}</level> | "
    "<level>{message}</level>"
)
```

**示例输出**:

```
2024-01-15 10:30:45 | INFO     | MCP server starting...
```

## 6. 工具列表处理器：list_tools()

### 6.1 装饰器注册

```python
@server.list_tools()
async def list_tools() -> list[Tool]:
```

### 6.2 执行流程

```python
@server.list_tools()
async def list_tools() -> list[Tool]:
    # 步骤 1: 获取所有工具的模式
    schemas = tools.get_tool_schemas()

    # 步骤 2: 转换为 MCP Tool 对象
    return [
        Tool(
            name=schema.name,
            description=schema.description,
            inputSchema={**schema.inputSchema},
        )
        for schema in schemas
    ]
```

### 6.3 返回格式

每个 `Tool` 对象包含：

- **`name`**: 工具名称（字符串）
- **`description`**: 工具描述（字符串）
- **`inputSchema`**: JSON Schema 对象（定义输入参数）

## 7. 工具调用处理器：call_tool()

### 7.1 装饰器注册

```python
@server.call_tool()
async def call_tool(
    name: str,
    arguments: MCPToolArguments
) -> list[TextContent]:
```

### 7.2 执行流程

```python
@server.call_tool()
async def call_tool(name: str, arguments: MCPToolArguments) -> list[TextContent]:
    logger.info(lg.MCP_SERVER_CALLING_TOOL.format(name=name))

    try:
        # 步骤 1: 获取工具处理器
        handler_info = tools.get_tool_handler(name)
        if not handler_info:
            error_msg = cs.MCP_UNKNOWN_TOOL_ERROR.format(name=name)
            logger.error(lg.MCP_SERVER_UNKNOWN_TOOL.format(name=name))
            return _create_error_content(error_msg)

        # 步骤 2: 解包处理器信息
        handler, returns_json = handler_info

        # 步骤 3: 调用工具处理器
        result = await handler(**arguments)

        # 步骤 4: 格式化结果
        if returns_json:
            result_text = json.dumps(result, indent=cs.MCP_JSON_INDENT)
        else:
            result_text = str(result)

        # 步骤 5: 返回 TextContent
        return [TextContent(type=cs.MCP_CONTENT_TYPE_TEXT, text=result_text)]

    except Exception as e:
        error_msg = cs.MCP_TOOL_EXEC_ERROR.format(name=name, error=e)
        logger.exception(lg.MCP_SERVER_TOOL_ERROR.format(name=name, error=e))
        return _create_error_content(error_msg)
```

### 7.3 错误内容创建

```python
def _create_error_content(message: str) -> list[TextContent]:
    return [
        TextContent(
            type=cs.MCP_CONTENT_TYPE_TEXT,
            text=te.ERROR_WRAPPER.format(message=message),
        )
    ]
```

## 8. 关键类和接口

### 8.1 Server 类

**来源**: `mcp.server.Server`

```python
server = Server(cs.MCP_SERVER_NAME)  # "graph-code"
```

**方法**:

- `list_tools()`: 装饰器，注册工具列表处理器
- `call_tool()`: 装饰器，注册工具调用处理器
- `run()`: 运行服务器
- `create_initialization_options()`: 创建初始化选项

### 8.2 MemgraphIngestor

**位置**: `codebase_rag/services/graph_service.py`

```python
ingestor = MemgraphIngestor(
    host=settings.MEMGRAPH_HOST,
    port=settings.MEMGRAPH_PORT,
    batch_size=settings.MEMGRAPH_BATCH_SIZE,
)
```

**用途**: 管理与 Memgraph 数据库的连接和操作

### 8.3 CypherGenerator

**位置**: `codebase_rag/services/llm.py`

```python
cypher_generator = CypherGenerator()
```

**用途**: 将自然语言查询转换为 Cypher 查询

### 8.4 MCPToolsRegistry

**位置**: `codebase_rag/mcp/tools.py`

```python
tools = create_mcp_tools_registry(
    project_root=str(project_root),
    ingestor=ingestor,
    cypher_gen=cypher_generator,
)
```

**用途**: 管理所有 MCP 工具的注册和调度

## 9. stdio 通信

### 9.1 stdio_server()

**来源**: `mcp.server.stdio.stdio_server`

```python
async with stdio_server() as (read_stream, write_stream):
    await server.run(read_stream, write_stream, ...)
```

**功能**:

- 创建标准输入/输出流
- 处理 JSON-RPC 消息
- 管理连接生命周期

### 9.2 通信流程

```
客户端 (Claude Desktop)
  ↓ (stdin)
JSON-RPC 请求
  ↓
MCP 服务器
  ↓
处理请求
  ↓
JSON-RPC 响应
  ↓ (stdout)
客户端
```

## 10. 服务器配置

### 10.1 服务器名称

```python
MCP_SERVER_NAME = "graph-code"
```

### 10.2 内容类型

```python
MCP_CONTENT_TYPE_TEXT = "text"
```

### 10.3 JSON 缩进

```python
MCP_JSON_INDENT = 2
```

## 11. 相关文档

- [第二部分：MCP 协议消息格式](./02-message-format.md)
- [第三部分：工具注册和调度](./03-tool-registry.md)
- [第四部分：工具实现详解](./04-tool-implementations.md)
- [第五部分：数据结构和类型定义](./05-data-structures.md)
- [第六部分：完整流程图](./06-flowcharts.md)
