# Code-Graph-RAG 工作流程详解 - 文档索引

本文档系列详细梳理了 code-graph-rag 从 `cgr start --repo-path /path/to/repo1 --update-graph --clean` 指令开始，以 Java 为例的完整工作流程。

## 文档结构

### [第一部分：总览和入口流程](./01-overview-and-entry.md)
- CLI 命令解析
- GraphUpdater 初始化
- 主执行流程
- 关键类和接口
- 数据流概览

### [第二部分：Java 语法解析详细流程](./02-java-parsing.md)
- Java 文件识别
- 文件处理入口
- 导入解析
- 类解析
- 方法解析
- 包声明解析
- 字段解析
- 特殊方法处理

### [第三部分：数据库插入逻辑](./03-database-insertion.md)
- MemgraphIngestor 架构
- 节点插入流程
- 关系插入流程
- 节点类型和属性
- Java 特定插入示例
- 约束管理
- 数据库清理
- 性能优化

### [第四部分：查询逻辑](./04-query-logic.md)
- 查询系统架构
- Cypher 查询生成
- 语义搜索
- 函数调用解析
- 方法重写处理
- 代码检索工具
- RAG 编排器
- 查询优化
- 常见查询模式

### [第五部分：关键数据结构](./05-data-structures.md)
- 核心数据结构
- Java 特定数据结构
- 数据库相关数据结构
- 配置数据结构
- 处理器数据结构
- 类型推断数据结构
- 查询结果数据结构
- 常量定义
- 数据结构关系图

### [第六部分：完整流程图](./06-flowcharts.md)
- 整体流程图
- 文件处理详细流程
- Java 类解析流程
- Java 方法解析流程
- 方法调用解析流程
- 数据库插入流程
- 类型推断流程
- 查询流程
- 导入解析流程
- 方法重写检测流程
- 嵌入生成流程
- 完整数据流图

## 快速导航

### 按主题查找

**想了解整体流程？**
→ [第一部分：总览和入口流程](./01-overview-and-entry.md)

**想了解 Java 如何被解析？**
→ [第二部分：Java 语法解析详细流程](./02-java-parsing.md)

**想了解数据如何存储到数据库？**
→ [第三部分：数据库插入逻辑](./03-database-insertion.md)

**想了解如何查询数据？**
→ [第四部分：查询逻辑](./04-query-logic.md)

**想了解关键数据结构？**
→ [第五部分：关键数据结构](./05-data-structures.md)

**想查看流程图？**
→ [第六部分：完整流程图](./06-flowcharts.md)

## 关键概念速查

### 核心类
- `GraphUpdater`: 主更新器，协调整个流程
- `DefinitionProcessor`: 处理定义（类、函数等）
- `CallProcessor`: 处理调用关系
- `ImportProcessor`: 处理导入
- `MemgraphIngestor`: 数据库插入器

### 关键数据结构
- `FunctionRegistryTrie`: 函数注册表（Trie 结构）
- `SimpleNameLookup`: 简单名称查找索引
- `BoundedASTCache`: AST 缓存
- `LanguageQueries`: 语言查询模式

### 数据库节点类型
- `Project`: 项目
- `Package`: 包
- `Module`: 模块（文件）
- `Class`: 类
- `Interface`: 接口
- `Method`: 方法
- `Function`: 函数

### 关系类型
- `DEFINES`: 模块定义类
- `DEFINES_METHOD`: 类定义方法
- `INHERITS`: 继承关系
- `IMPLEMENTS`: 实现关系
- `CALLS`: 调用关系
- `IMPORTS`: 导入关系

## 典型工作流程示例

### 处理一个 Java 类文件

1. **文件识别** ([第一部分](./01-overview-and-entry.md#22-文件处理流程))
   - 识别为 `.java` 文件
   - 加载 Java 解析器

2. **AST 解析** ([第二部分](./02-java-parsing.md#22-处理步骤))
   - 使用 tree-sitter 解析
   - 生成 AST

3. **模块创建** ([第二部分](./02-java-parsing.md#22-处理步骤))
   - 构建模块限定名
   - 创建模块节点

4. **导入解析** ([第二部分](./02-java-parsing.md#3-导入解析-importprocessor))
   - 解析 import 语句
   - 创建导入关系

5. **类解析** ([第二部分](./02-java-parsing.md#4-类解析-classingestmixin))
   - 提取类信息
   - 创建类节点
   - 创建继承/实现关系

6. **方法解析** ([第二部分](./02-java-parsing.md#5-方法解析))
   - 提取方法信息
   - 创建方法节点
   - 注册到 function_registry

7. **数据库插入** ([第三部分](./03-database-insertion.md))
   - 批量插入节点
   - 批量插入关系

8. **调用解析** ([第四部分](./04-query-logic.md#4-函数调用解析))
   - 解析方法调用
   - 创建调用关系

## 技术栈

- **解析器**: tree-sitter
- **数据库**: Memgraph (Neo4j 兼容)
- **查询语言**: Cypher
- **向量搜索**: Milvus (可选)
- **嵌入模型**: UniXcoder
- **LLM**: 支持多种提供商 (OpenAI, Anthropic, Ollama 等)

## 相关资源

- 项目仓库: [code-graph-rag](https://github.com/...)
- 主要配置文件: `codebase_rag/config.py`
- 常量定义: `codebase_rag/constants.py`
- 类型定义: `codebase_rag/types_defs.py`
