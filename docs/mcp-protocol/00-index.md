# Code-Graph-RAG MCP 协议详解 - 文档索引

本文档系列详细梳理了 code-graph-rag 作为 MCP (Model Context Protocol) 服务器时的输入输出数据格式和协议实现。

## 文档结构

### [第一部分：MCP 协议概述和服务器初始化](./01-overview-and-initialization.md)

- MCP 协议简介
- 服务器启动流程
- 项目根目录解析
- 服务初始化
- 关键类和接口

### [第二部分：MCP 协议消息格式](./02-message-format.md)

- MCP 协议基础
- 请求消息格式
- 响应消息格式
- 工具列表请求/响应
- 工具调用请求/响应
- 错误处理格式

### [第三部分：工具注册和调度](./03-tool-registry.md)

- MCPToolsRegistry 架构
- 工具注册机制
- 工具调度流程
- 输入参数验证
- 返回格式处理

### [第四部分：工具实现详解](./04-tool-implementations.md)

- 项目管理工具
- 代码查询工具
- 文件操作工具
- 代码检索工具
- 代码编辑工具

### [第五部分：数据结构和类型定义](./05-data-structures.md)

- MCP 相关类型定义
- 请求参数类型
- 响应结果类型
- 工具元数据结构
- 输入模式定义

### [第六部分：完整流程图](./06-flowcharts.md)

- MCP 服务器启动流程
- 工具调用流程
- 请求处理流程
- 响应生成流程
- 错误处理流程

## 快速导航

### 按主题查找

**想了解 MCP 协议基础？**
→ [第一部分：MCP 协议概述和服务器初始化](./01-overview-and-initialization.md)

**想了解消息格式？**
→ [第二部分：MCP 协议消息格式](./02-message-format.md)

**想了解工具如何注册和调度？**
→ [第三部分：工具注册和调度](./03-tool-registry.md)

**想了解具体工具的实现？**
→ [第四部分：工具实现详解](./04-tool-implementations.md)

**想了解数据结构？**
→ [第五部分：数据结构和类型定义](./05-data-structures.md)

**想查看流程图？**
→ [第六部分：完整流程图](./06-flowcharts.md)

## 关键概念速查

### 核心类

- `Server`: MCP 服务器实例
- `MCPToolsRegistry`: 工具注册表
- `MemgraphIngestor`: 数据库连接器
- `CypherGenerator`: Cypher 查询生成器

### 关键数据结构

- `MCPToolSchema`: 工具模式定义
- `MCPInputSchema`: 输入参数模式
- `MCPToolArguments`: 工具参数字典
- `TextContent`: MCP 响应内容

### 工具类型

- 项目管理: `list_projects`, `delete_project`, `wipe_database`, `index_repository`
- 代码查询: `query_code_graph`, `get_code_snippet`
- 文件操作: `read_file`, `write_file`, `list_directory`
- 代码编辑: `surgical_replace_code`

## MCP 协议基础

### 什么是 MCP？

Model Context Protocol (MCP) 是一个标准化的协议，允许 AI 助手与外部工具和数据源进行交互。code-graph-rag 实现了 MCP 服务器，提供代码库分析和操作能力。

### 通信方式

- **传输层**: stdio (标准输入/输出)
- **协议**: JSON-RPC 2.0
- **编码**: UTF-8

### 服务器名称

```
graph-code
```

## 相关资源

- MCP 官方文档: https://modelcontextprotocol.io
- 主要实现文件: `codebase_rag/mcp/server.py`, `codebase_rag/mcp/tools.py`
- 类型定义: `codebase_rag/types_defs.py`
- 常量定义: `codebase_rag/constants.py`
