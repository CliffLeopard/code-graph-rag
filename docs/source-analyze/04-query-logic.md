# Code-Graph-RAG 工作流程详解 - 第四部分：查询逻辑

## 1. 查询系统架构

### 1.1 混合检索系统

Code-Graph-RAG 使用两种查询方式：

1. **结构化查询**: 使用 Cypher 查询知识图谱
2. **语义搜索**: 使用向量嵌入进行语义相似度搜索

### 1.2 查询工具

**位置**: `codebase_rag/tools/codebase_query.py`

```python
def create_query_tool(
    ingestor: QueryProtocol,
    cypher_gen: CypherGenerator,
    console: Console | None = None,
) -> Tool:
    # 创建查询工具，将自然语言转换为 Cypher 查询
```

## 2. Cypher 查询生成

### 2.1 CypherGenerator

**位置**: `codebase_rag/services/llm.py`

```python
class CypherGenerator:
    def __init__(self):
        config = settings.active_cypher_config
        llm = _create_provider_model(config)

        # 根据提供商选择不同的提示词
        system_prompt = (
            LOCAL_CYPHER_SYSTEM_PROMPT
            if config.provider == cs.Provider.OLLAMA
            else CYPHER_SYSTEM_PROMPT
        )

        self.agent = Agent(
            model=llm,
            system_prompt=system_prompt,
            output_type=str,
            retries=settings.AGENT_RETRIES,
        )

    async def generate(self, natural_language_query: str) -> str:
        # 将自然语言转换为 Cypher 查询
        result = await self.agent.run(natural_language_query)
        query = _clean_cypher_response(result.output)
        return query
```

### 2.2 查询提示词

**位置**: `codebase_rag/prompts.py`

包含：
- 图模式定义
- Cypher 查询规则
- 查询模式示例
- 优化规则

### 2.3 查询示例

#### 查找所有类

```cypher
MATCH (c:Class)
RETURN c.name AS name, c.qualified_name AS qualified_name, c.path AS path
LIMIT 50
```

#### 查找特定类的方法

```cypher
MATCH (c:Class {qualified_name: "my-project.com.example.User"})-[:DEFINES_METHOD]->(m:Method)
RETURN m.name AS name, m.qualified_name AS qualified_name
LIMIT 50
```

#### 查找类的继承关系

```cypher
MATCH (child:Class)-[:INHERITS]->(parent:Class)
RETURN child.qualified_name AS child, parent.qualified_name AS parent
LIMIT 50
```

#### 查找方法调用关系

```cypher
MATCH (caller:Method)-[:CALLS]->(callee:Method)
RETURN caller.qualified_name AS caller, callee.qualified_name AS callee
LIMIT 50
```

## 3. 语义搜索

### 3.1 向量嵌入生成

**位置**: `codebase_rag/embedder.py`

```python
def embed_code(source_code: str) -> list[float]:
    # 使用 UniXcoder 或类似模型生成代码嵌入向量
    # 返回 768 维向量
```

### 3.2 嵌入存储

**位置**: `codebase_rag/vector_store.py`

```python
def store_embedding(
    node_id: int,
    embedding: list[float],
    qualified_name: str,
) -> None:
    # 存储嵌入向量到向量数据库（如 Milvus）
    # 关联节点 ID 和限定名
```

### 3.3 语义搜索

**位置**: `codebase_rag/tools/semantic_search.py`

```python
def semantic_code_search(query: str, top_k: int = 5) -> list[SemanticSearchResult]:
    # 1. 将查询文本转换为嵌入向量
    query_embedding = embed_code(query)

    # 2. 在向量数据库中搜索相似向量
    search_results = search_embeddings(query_embedding, top_k=top_k)

    # 3. 获取对应的节点 ID
    node_ids = [node_id for node_id, _ in search_results]

    # 4. 从 Memgraph 查询节点详细信息
    with MemgraphIngestor(...) as ingestor:
        query = build_nodes_by_ids_query(node_ids)
        results = ingestor.fetch_all(query)

    # 5. 返回搜索结果
    return [SemanticSearchResult(...) for ... in results]
```

## 4. 函数调用解析

### 4.1 CallProcessor

**位置**: `codebase_rag/parsers/call_processor.py`

```python
class CallProcessor:
    def process_calls_in_file(
        self,
        file_path: Path,
        root_node: Node,
        language: SupportedLanguage,
        queries: dict[SupportedLanguage, LanguageQueries],
    ) -> None:
        # 1. 处理函数中的调用
        self._process_calls_in_functions(...)

        # 2. 处理类方法中的调用
        self._process_calls_in_classes(...)

        # 3. 处理模块级别的调用
        self._process_module_level_calls(...)
```

### 4.2 调用目标解析

```python
def _get_call_target_name(self, call_node: Node) -> str | None:
    # 提取调用目标名称
    # 支持多种调用形式：
    # - 直接调用: functionName()
    # - 方法调用: object.methodName()
    # - 操作符调用: obj1 + obj2
    ...
```

### 4.3 Java 方法调用解析

**位置**: `codebase_rag/parsers/java/method_resolver.py`

```python
class JavaMethodResolverMixin:
    def resolve_java_method_call(
        self,
        call_node: Node,
        module_qn: str,
        local_var_types: dict[str, str],
    ) -> tuple[str, str] | None:
        # 1. 提取调用对象类型
        object_type = self._infer_call_object_type(...)

        # 2. 提取方法名和参数
        method_name = ...
        arg_types = ...

        # 3. 在 function_registry 中查找匹配的方法
        # 考虑继承和方法重载
        method_qn = self._find_matching_method(
            object_type, method_name, arg_types
        )

        return (cs.NodeLabel.METHOD, method_qn) if method_qn else None
```

### 4.4 类型推断

**位置**: `codebase_rag/parsers/java/type_inference.py`

```python
class JavaTypeInferenceEngine:
    def build_local_variable_type_map(
        self,
        node: Node,
        module_qn: str,
        language: SupportedLanguage,
    ) -> dict[str, str]:
        # 分析局部变量声明
        # 返回变量名到类型的映射
        # 例如: {"user": "com.example.User", "list": "java.util.List"}
```

### 4.5 调用关系创建

```python
def _ingest_function_calls(...) -> None:
    # 1. 查找所有调用节点
    call_nodes = captures.get(cs.CAPTURE_CALL, [])

    for call_node in call_nodes:
        # 2. 解析调用目标
        call_name = self._get_call_target_name(call_node)

        # 3. 解析被调用者（考虑类型推断和继承）
        if language == SupportedLanguage.JAVA:
            callee_info = self._resolver.resolve_java_method_call(...)
        else:
            callee_info = self._resolver.resolve_function_call(...)

        # 4. 创建 CALLS 关系
        if callee_info:
            callee_type, callee_qn = callee_info
            self.ingestor.ensure_relationship_batch(
                (caller_type, cs.KEY_QUALIFIED_NAME, caller_qn),
                cs.RelationshipType.CALLS,
                (callee_type, cs.KEY_QUALIFIED_NAME, callee_qn),
            )
```

## 5. 方法重写处理

### 5.1 重写检测

**位置**: `codebase_rag/parsers/class_ingest/method_override.py`

```python
def process_all_method_overrides(
    function_registry: FunctionRegistryTrieProtocol,
    class_inheritance: dict[str, list[str]],
    ingestor: IngestorProtocol,
) -> None:
    # 1. 遍历所有类
    # 2. 检查父类中的方法
    # 3. 如果子类有同名同签名方法，创建 OVERRIDES 关系
```

### 5.2 继承链遍历

```python
def _find_all_ancestors(
    class_qn: str,
    class_inheritance: dict[str, list[str]],
) -> set[str]:
    # 递归查找所有祖先类
    ancestors = set()
    queue = [class_qn]

    while queue:
        current = queue.pop()
        parents = class_inheritance.get(current, [])
        for parent in parents:
            if parent not in ancestors:
                ancestors.add(parent)
                queue.append(parent)

    return ancestors
```

## 6. 代码检索工具

### 6.1 CodeRetriever

**位置**: `codebase_rag/tools/code_retrieval.py`

```python
class CodeRetriever:
    def retrieve_code(
        self,
        query: str,
        top_k: int = 5,
    ) -> list[CodeSnippet]:
        # 1. 使用语义搜索找到相关函数
        semantic_results = semantic_code_search(query, top_k)

        # 2. 从文件系统读取源代码
        # 3. 提取函数代码片段
        # 4. 返回代码片段列表
```

### 6.2 源代码提取

**位置**: `codebase_rag/utils/source_extraction.py`

```python
def extract_source_with_fallback(
    file_path: Path,
    start_line: int,
    end_line: int,
    qualified_name: str,
    ast_extractor: Callable | None = None,
) -> str | None:
    # 1. 尝试使用 AST 精确提取
    if ast_extractor:
        source = ast_extractor(qualified_name, file_path)
        if source:
            return source

    # 2. 回退到行号范围提取
    with open(file_path) as f:
        lines = f.readlines()
        return "".join(lines[start_line-1:end_line])
```

## 7. RAG 编排器

### 7.1 工具集成

**位置**: `codebase_rag/main.py`

```python
def _initialize_services_and_agent(
    repo_path: str,
    ingestor: QueryProtocol,
) -> tuple[Agent, ConfirmationToolNames]:
    # 创建各种工具
    query_tool = create_query_tool(ingestor, cypher_generator, console)
    code_tool = create_code_retrieval_tool(code_retriever)
    file_reader_tool = create_file_reader_tool(file_reader)
    semantic_search_tool = create_semantic_search_tool()
    ...

    # 创建 RAG 代理
    rag_agent = create_rag_orchestrator(tools=[...])
    return rag_agent, confirmation_tool_names
```

### 7.2 查询流程

```
用户自然语言问题
  ↓
RAG Orchestrator
  ├─→ 判断查询类型
  │   ├─→ 结构化查询 → CypherGenerator → Cypher 查询
  │   └─→ 语义查询 → SemanticSearch → 向量搜索
  ↓
执行查询
  ↓
获取结果
  ↓
代码检索（如需要）
  ↓
生成回答
```

## 8. 查询优化

### 8.1 查询限制

```cypher
-- 总是添加 LIMIT 避免返回过多结果
MATCH (c:Class)
RETURN c.name AS name
LIMIT 50
```

### 8.2 聚合查询

```cypher
-- 计数查询只返回数量
MATCH (c:Class)
RETURN count(c) AS total
```

### 8.3 路径查询

```cypher
-- 使用 STARTS WITH 进行路径匹配
MATCH (f:File)
WHERE f.path STARTS WITH 'com/example'
RETURN f.path AS path
LIMIT 50
```

## 9. 常见查询模式

### 9.1 查找类及其方法

```cypher
MATCH (c:Class {qualified_name: $class_qn})-[:DEFINES_METHOD]->(m:Method)
RETURN m.qualified_name AS method, m.name AS name
ORDER BY m.name
LIMIT 50
```

### 9.2 查找调用链

```cypher
MATCH path = (start:Method)-[:CALLS*1..5]->(end:Method)
WHERE start.qualified_name = $start_method
RETURN path
LIMIT 10
```

### 9.3 查找依赖关系

```cypher
MATCH (m1:Module)-[:IMPORTS]->(m2:Module)
WHERE m1.qualified_name = $module_qn
RETURN m2.qualified_name AS imported_module
LIMIT 50
```

### 9.4 查找继承层次

```cypher
MATCH path = (child:Class)-[:INHERITS*]->(ancestor:Class)
WHERE child.qualified_name = $class_qn
RETURN path
LIMIT 10
```

## 10. 相关文档

- [第一部分：总览和入口流程](./01-overview-and-entry.md)
- [第二部分：Java 语法解析详细流程](./02-java-parsing.md)
- [第三部分：数据库插入逻辑](./03-database-insertion.md)
- [第五部分：关键数据结构](./05-data-structures.md)
