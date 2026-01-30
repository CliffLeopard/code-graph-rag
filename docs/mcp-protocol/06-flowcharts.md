# Code-Graph-RAG MCP 协议详解 - 第六部分：完整流程图

## 1. MCP 服务器启动流程

```mermaid
graph TD
    A["cgr mcp-server"] --> B["mcp_server()"]
    B --> C["asyncio.run(mcp_main())"]
    C --> D["main()"]
    D --> E["create_server()"]

    E --> F["setup_logging()"]
    E --> G["get_project_root()"]
    E --> H["创建 MemgraphIngestor"]
    E --> I["创建 CypherGenerator"]
    E --> J["create_mcp_tools_registry()"]
    E --> K["创建 Server"]
    E --> L["注册 list_tools()"]
    E --> M["注册 call_tool()"]

    K --> N["返回 server, ingestor"]

    D --> O["with ingestor:"]
    O --> P["async with stdio_server()"]
    P --> Q["server.run()"]
    Q --> R["等待请求"]
```

## 2. 工具列表请求流程

```mermaid
graph TD
    A["客户端发送 tools/list"] --> B["JSON-RPC 请求"]
    B --> C["server.run() 接收"]
    C --> D["调用 list_tools()"]
    D --> E["tools.get_tool_schemas()"]
    E --> F["遍历 _tools.values()"]
    F --> G["创建 MCPToolSchema"]
    G --> H["转换为 Tool 对象"]
    H --> I["返回 list[Tool]"]
    I --> J["包装为 JSON-RPC 响应"]
    J --> K["发送给客户端"]
```

## 3. 工具调用请求流程

```mermaid
graph TD
    A["客户端发送 tools/call"] --> B["JSON-RPC 请求"]
    B --> C["server.run() 接收"]
    C --> D["调用 call_tool(name, arguments)"]
    D --> E["tools.get_tool_handler(name)"]
    E --> F{"工具存在?"}

    F -->|否| G["返回错误内容"]
    F -->|是| H["解包 (handler, returns_json)"]

    H --> I["await handler(**arguments)"]
    I --> J{"返回类型"}

    J -->|JSON| K["json.dumps(result, indent=2)"]
    J -->|文本| L["str(result)"]

    K --> M["创建 TextContent"]
    L --> M
    M --> N["返回 list[TextContent]"]
    N --> O["包装为 JSON-RPC 响应"]
    O --> P["发送给客户端"]

    G --> Q["包装为 JSON-RPC 错误响应"]
    Q --> P
```

## 4. 工具处理器查找流程

```mermaid
graph TD
    A["get_tool_handler(name)"] --> B["_tools.get(name)"]
    B --> C{"找到?"}
    C -->|否| D["返回 None"]
    C -->|是| E["获取 ToolMetadata"]
    E --> F["提取 handler"]
    E --> G["提取 returns_json"]
    F --> H["返回 (handler, returns_json)"]
    G --> H
```

## 5. query_code_graph 工具执行流程

```mermaid
graph TD
    A["query_code_graph(natural_language_query)"] --> B["记录日志"]
    B --> C["调用 _query_tool.function()"]
    C --> D["CypherGenerator 生成查询"]
    D --> E["执行 Cypher 查询"]
    E --> F["MemgraphIngestor 返回结果"]
    F --> G["转换为 QueryResultDict"]
    G --> H{"成功?"}

    H -->|是| I["记录结果数量"]
    I --> J["返回 QueryResultDict"]

    H -->|否| K["捕获异常"]
    K --> L["创建错误 QueryResultDict"]
    L --> M["返回错误结果"]
```

## 6. get_code_snippet 工具执行流程

```mermaid
graph TD
    A["get_code_snippet(qualified_name)"] --> B["记录日志"]
    B --> C["调用 _code_tool.function()"]
    C --> D["CodeRetriever 查找代码"]
    D --> E{"找到?"}

    E -->|是| F["转换为 CodeSnippetResultDict"]
    F --> G["返回结果"]

    E -->|否| H["返回 None"]
    H --> I["创建错误 CodeSnippetResultDict"]
    I --> J["返回错误结果"]

    C --> K{"异常?"}
    K -->|是| L["捕获异常"]
    L --> I
```

## 7. index_repository 工具执行流程

```mermaid
graph TD
    A["index_repository()"] --> B["获取项目名称"]
    B --> C["ingestor.delete_project()"]
    C --> D["创建 GraphUpdater"]
    D --> E["updater.run()"]
    E --> F["解析文件"]
    F --> G["提取定义"]
    G --> H["提取调用"]
    H --> I["插入数据库"]
    I --> J{"成功?"}

    J -->|是| K["返回成功消息"]
    J -->|否| L["捕获异常"]
    L --> M["返回错误消息"]
```

## 8. read_file 工具执行流程

```mermaid
graph TD
    A["read_file(file_path, offset, limit)"] --> B{"有分页参数?"}

    B -->|是| C["计算起始位置"]
    C --> D["打开文件"]
    D --> E["跳过前面的行"]
    E --> F{"有 limit?"}
    F -->|是| G["读取指定行数"]
    F -->|否| H["读取剩余所有行"]
    G --> I["计算总行数"]
    H --> I
    I --> J["添加分页头"]
    J --> K["返回分页内容"]

    B -->|否| L["调用 _file_reader_tool"]
    L --> M["返回完整文件内容"]
```

## 9. 错误处理流程

```mermaid
graph TD
    A["工具执行"] --> B{"发生异常?"}
    B -->|否| C["返回正常结果"]
    B -->|是| D["捕获异常"]
    D --> E["记录错误日志"]
    E --> F{"工具类型"}

    F -->|JSON 工具| G["创建错误结果字典"]
    F -->|文本工具| H["创建错误消息字符串"]

    G --> I["返回错误结果"]
    H --> J["ERROR_WRAPPER.format()"]
    J --> I

    I --> K["包装为 TextContent"]
    K --> L["返回给客户端"]
```

## 10. 数据流图

```mermaid
graph LR
    A["客户端请求"] --> B["JSON-RPC"]
    B --> C["server.run()"]
    C --> D["call_tool()"]
    D --> E["get_tool_handler()"]
    E --> F["handler()"]
    F --> G["工具实现"]
    G --> H["返回结果"]
    H --> I{"returns_json?"}
    I -->|是| J["JSON 序列化"]
    I -->|否| K["字符串转换"]
    J --> L["TextContent"]
    K --> L
    L --> M["JSON-RPC 响应"]
    M --> N["客户端"]
```

## 11. 工具注册表初始化流程

```mermaid
graph TD
    A["create_mcp_tools_registry()"] --> B["创建 MCPToolsRegistry"]
    B --> C["存储 project_root"]
    B --> D["存储 ingestor"]
    B --> E["存储 cypher_gen"]
    B --> F["load_parsers()"]
    B --> G["创建工具实例"]
    G --> H["CodeRetriever"]
    G --> I["FileEditor"]
    G --> J["FileReader"]
    G --> K["FileWriter"]
    G --> L["DirectoryLister"]
    B --> M["创建工具包装器"]
    M --> N["_query_tool"]
    M --> O["_code_tool"]
    M --> P["_file_editor_tool"]
    M --> Q["_file_reader_tool"]
    M --> R["_file_writer_tool"]
    M --> S["_directory_lister_tool"]
    B --> T["注册所有工具到 _tools"]
    T --> U["返回 MCPToolsRegistry"]
```

## 12. 完整请求-响应循环

```mermaid
graph TD
    A["客户端启动"] --> B["发送 initialize"]
    B --> C["服务器响应"]
    C --> D["客户端发送 tools/list"]
    D --> E["服务器返回工具列表"]
    E --> F["客户端选择工具"]
    F --> G["客户端发送 tools/call"]
    G --> H["服务器处理请求"]
    H --> I{"处理成功?"}
    I -->|是| J["返回结果"]
    I -->|否| K["返回错误"]
    J --> L["客户端接收结果"]
    K --> L
    L --> M{"继续?"}
    M -->|是| F
    M -->|否| N["结束"]
```

## 13. 项目根目录解析流程

```mermaid
graph TD
    A["get_project_root()"] --> B["检查 TARGET_REPO_PATH"]
    B --> C{"存在?"}
    C -->|是| D["使用该路径"]
    C -->|否| E["检查 CLAUDE_PROJECT_ROOT"]
    E --> F{"存在?"}
    F -->|是| D
    F -->|否| G["检查 PWD"]
    G --> H{"存在?"}
    H -->|是| D
    H -->|否| I["使用 Path.cwd()"]
    I --> D
    D --> J["Path.resolve()"]
    J --> K{"路径存在?"}
    K -->|否| L["抛出 ValueError"]
    K -->|是| M{"是目录?"}
    M -->|否| N["抛出 ValueError"]
    M -->|是| O["返回 project_root"]
```

## 14. 相关文档

- [第一部分：MCP 协议概述和服务器初始化](./01-overview-and-initialization.md)
- [第二部分：MCP 协议消息格式](./02-message-format.md)
- [第三部分：工具注册和调度](./03-tool-registry.md)
- [第四部分：工具实现详解](./04-tool-implementations.md)
- [第五部分：数据结构和类型定义](./05-data-structures.md)
