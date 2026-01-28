# Code-Graph-RAG 工作流程详解 - 第三部分：数据库插入逻辑

## 1. MemgraphIngestor 架构

### 1.1 核心类

**位置**: `codebase_rag/services/graph_service.py`

```python
class MemgraphIngestor:
    def __init__(self, host: str, port: int, batch_size: int = 1000):
        self._host = host
        self._port = port
        self.batch_size = batch_size
        self.conn: mgclient.Connection | None = None
        self.node_buffer: list[tuple[str, dict]] = []
        self.relationship_buffer: list[tuple] = []
```

### 1.2 缓冲区机制

使用缓冲区批量插入，提高性能：

- **`node_buffer`**: 存储待插入的节点
- **`relationship_buffer`**: 存储待插入的关系
- **`batch_size`**: 缓冲区大小阈值（默认 1000）

## 2. 节点插入流程

### 2.1 ensure_node_batch()

```python
def ensure_node_batch(
    self,
    label: str,
    properties: dict[str, PropertyValue]
) -> None:
    # 添加到缓冲区
    self.node_buffer.append((label, properties))

    # 如果缓冲区满了，刷新
    if len(self.node_buffer) >= self.batch_size:
        self.flush_nodes()
```

### 2.2 flush_nodes()

```python
def flush_nodes(self) -> None:
    if not self.node_buffer:
        return

    # 按标签分组
    nodes_by_label: defaultdict[str, list[dict]] = defaultdict(list)
    for label, props in self.node_buffer:
        nodes_by_label[label].append(props)

    # 对每个标签批量插入
    for label, props_list in nodes_by_label.items():
        # 获取唯一约束键
        id_key = NODE_UNIQUE_CONSTRAINTS.get(label)

        # 构建批量插入数据
        batch_rows: list[NodeBatchRow] = []
        for props in props_list:
            if id_key not in props:
                continue
            row_props = {k: v for k, v in props.items() if k != id_key}
            batch_rows.append(
                NodeBatchRow(id=props[id_key], props=row_props)
            )

        # 执行批量插入
        query = build_merge_node_query(label, id_key)
        self._execute_batch(query, batch_rows)

    self.node_buffer.clear()
```

### 2.3 节点唯一约束

**位置**: `codebase_rag/constants.py`

```python
NODE_UNIQUE_CONSTRAINTS = {
    "Project": "name",
    "Package": "qualified_name",
    "Module": "qualified_name",
    "Class": "qualified_name",
    "Interface": "qualified_name",
    "Function": "qualified_name",
    "Method": "qualified_name",
    "Folder": "path",
    "File": "path",
    "ExternalPackage": "name",
}
```

### 2.4 Cypher 查询构建

**位置**: `codebase_rag/cypher_queries.py`

```python
def build_merge_node_query(label: str, id_key: str) -> str:
    # 使用 MERGE 确保唯一性
    # 使用 SET 更新属性
    return f"MERGE (n:{label} {{{id_key}: row.id}})\nSET n += row.props"
```

### 2.5 批量执行

```python
def _execute_batch(
    self,
    query: str,
    params_list: Sequence[BatchParams]
) -> None:
    # 使用 UNWIND 进行批量操作
    wrapped_query = wrap_with_unwind(query)
    # UNWIND $batch AS row
    # MERGE (n:Class {qualified_name: row.id})
    # SET n += row.props

    cursor.execute(wrapped_query, BatchWrapper(batch=params_list))
```

## 3. 关系插入流程

### 3.1 ensure_relationship_batch()

```python
def ensure_relationship_batch(
    self,
    from_spec: tuple[str, str, PropertyValue],  # (label, key, value)
    rel_type: str,
    to_spec: tuple[str, str, PropertyValue],
    properties: dict[str, PropertyValue] | None = None,
) -> None:
    self.relationship_buffer.append(
        (from_spec, rel_type, to_spec, properties)
    )

    if len(self.relationship_buffer) >= self.batch_size:
        self.flush_nodes()  # 先刷新节点
        self.flush_relationships()
```

### 3.2 flush_relationships()

```python
def flush_relationships(self) -> None:
    if not self.relationship_buffer:
        return

    # 按模式分组（from_label, from_key, rel_type, to_label, to_key）
    rels_by_pattern: defaultdict[tuple, list] = defaultdict(list)
    for from_node, rel_type, to_node, props in self.relationship_buffer:
        pattern = (
            from_node[0], from_node[1], rel_type,
            to_node[0], to_node[1]
        )
        rels_by_pattern[pattern].append(
            RelBatchRow(
                from_val=from_node[2],
                to_val=to_node[2],
                props=props or {}
            )
        )

    # 对每个模式批量插入
    for pattern, params_list in rels_by_pattern.items():
        from_label, from_key, rel_type, to_label, to_key = pattern

        query = build_merge_relationship_query(
            from_label, from_key, rel_type, to_label, to_key, has_props
        )

        results = self._execute_batch_with_return(query, params_list)
        # 统计成功创建的关系数
        ...

    self.relationship_buffer.clear()
```

### 3.3 关系查询构建

```python
def build_merge_relationship_query(
    from_label: str,
    from_key: str,
    rel_type: str,
    to_label: str,
    to_key: str,
    has_props: bool = False,
) -> str:
    query = (
        f"MATCH (a:{from_label} {{{from_key}: row.from_val}}), "
        f"(b:{to_label} {{{to_key}: row.to_val}})\n"
        f"MERGE (a)-[r:{rel_type}]->(b)\n"
    )
    if has_props:
        query += "SET r += row.props\n"
    query += "RETURN count(r) as created"
    return query
```

## 4. 节点类型和属性

### 4.1 节点类型（标签）

```python
class NodeLabel:
    PROJECT = "Project"
    PACKAGE = "Package"
    FOLDER = "Folder"
    FILE = "File"
    MODULE = "Module"
    CLASS = "Class"
    INTERFACE = "Interface"
    FUNCTION = "Function"
    METHOD = "Method"
    EXTERNAL_PACKAGE = "ExternalPackage"
```

### 4.2 关系类型

```python
class RelationshipType:
    CONTAINS_PACKAGE = "CONTAINS_PACKAGE"
    CONTAINS_FOLDER = "CONTAINS_FOLDER"
    CONTAINS_FILE = "CONTAINS_FILE"
    CONTAINS_MODULE = "CONTAINS_MODULE"
    DEFINES = "DEFINES"
    DEFINES_METHOD = "DEFINES_METHOD"
    INHERITS = "INHERITS"
    IMPLEMENTS = "IMPLEMENTS"
    IMPORTS = "IMPORTS"
    CALLS = "CALLS"
    DEPENDS_ON_EXTERNAL = "DEPENDS_ON_EXTERNAL"
```

### 4.3 属性键

```python
KEY_NAME = "name"
KEY_QUALIFIED_NAME = "qualified_name"
KEY_PATH = "path"
KEY_START_LINE = "start_line"
KEY_END_LINE = "end_line"
KEY_DOCSTRING = "docstring"
KEY_DECORATORS = "decorators"
KEY_IS_EXPORTED = "is_exported"
KEY_VERSION_SPEC = "version_spec"
KEY_IS_EXTERNAL = "is_external"
```

## 5. Java 特定插入示例

### 5.1 项目节点

```python
ingestor.ensure_node_batch(
    "Project",
    {"name": "my-project"}
)
```

生成的 Cypher:

```cypher
MERGE (n:Project {name: "my-project"})
```

### 5.2 包节点

```python
ingestor.ensure_node_batch(
    "Package",
    {"qualified_name": "my-project.com.example.utils"}
)
```

### 5.3 模块节点

```python
ingestor.ensure_node_batch(
    "Module",
    {
        "qualified_name": "my-project.com.example.utils.StringUtils",
        "name": "StringUtils.java",
        "path": "com/example/utils/StringUtils.java"
    }
)
```

### 5.4 类节点

```python
ingestor.ensure_node_batch(
    "Class",
    {
        "qualified_name": "my-project.com.example.utils.StringUtils",
        "name": "StringUtils",
        "start_line": 10,
        "end_line": 150,
        "docstring": "Utility class for string operations",
        "is_exported": True,
        "decorators": []
    }
)
```

### 5.5 方法节点

```python
ingestor.ensure_node_batch(
    "Method",
    {
        "qualified_name": "my-project.com.example.utils.StringUtils.isEmpty(String)",
        "name": "isEmpty",
        "start_line": 25,
        "end_line": 30,
        "docstring": "Checks if string is empty"
    }
)
```

### 5.6 关系示例

#### DEFINES 关系（模块 -> 类）

```python
ingestor.ensure_relationship_batch(
    ("Module", "qualified_name", "my-project.com.example.utils.StringUtils"),
    "DEFINES",
    ("Class", "qualified_name", "my-project.com.example.utils.StringUtils"),
)
```

生成的 Cypher:

```cypher
MATCH (a:Module {qualified_name: "my-project.com.example.utils.StringUtils"}),
      (b:Class {qualified_name: "my-project.com.example.utils.StringUtils"})
MERGE (a)-[r:DEFINES]->(b)
RETURN count(r) as created
```

#### DEFINES_METHOD 关系（类 -> 方法）

```python
ingestor.ensure_relationship_batch(
    ("Class", "qualified_name", "my-project.com.example.utils.StringUtils"),
    "DEFINES_METHOD",
    ("Method", "qualified_name", "my-project.com.example.utils.StringUtils.isEmpty(String)"),
)
```

#### INHERITS 关系（子类 -> 父类）

```python
ingestor.ensure_relationship_batch(
    ("Class", "qualified_name", "my-project.com.example.ChildClass"),
    "INHERITS",
    ("Class", "qualified_name", "my-project.com.example.ParentClass"),
)
```

#### IMPLEMENTS 关系（类 -> 接口）

```python
ingestor.ensure_relationship_batch(
    ("Class", "qualified_name", "my-project.com.example.MyClass"),
    "IMPLEMENTS",
    ("Interface", "qualified_name", "my-project.com.example.MyInterface"),
)
```

#### CALLS 关系（方法 -> 方法）

```python
ingestor.ensure_relationship_batch(
    ("Method", "qualified_name", "my-project.com.example.ClassA.method1()"),
    "CALLS",
    ("Method", "qualified_name", "my-project.com.example.ClassB.method2()"),
)
```

#### IMPORTS 关系（模块 -> 模块）

```python
ingestor.ensure_relationship_batch(
    ("Module", "qualified_name", "my-project.com.example.ClassA"),
    "IMPORTS",
    ("Module", "qualified_name", "my-project.com.example.ClassB"),
)
```

## 6. 约束管理

### 6.1 确保约束存在

```python
def ensure_constraints(self) -> None:
    for label, prop in NODE_UNIQUE_CONSTRAINTS.items():
        try:
            query = build_constraint_query(label, prop)
            # CREATE CONSTRAINT ON (n:Class) ASSERT n.qualified_name IS UNIQUE
            self._execute_query(query)
        except Exception:
            pass  # 约束可能已存在
```

### 6.2 约束查询构建

```python
def build_constraint_query(label: str, prop: str) -> str:
    return f"CREATE CONSTRAINT ON (n:{label}) ASSERT n.{prop} IS UNIQUE;"
```

## 7. 数据库清理

### 7.1 清理所有数据

```python
def clean_database(self) -> None:
    self._execute_query("MATCH (n) DETACH DELETE n;")
```

### 7.2 清理特定项目

```python
def delete_project(self, project_name: str) -> None:
    query = """
    MATCH (p:Project {name: $project_name})
    OPTIONAL MATCH (p)-[:CONTAINS_PACKAGE|CONTAINS_FOLDER|CONTAINS_FILE|CONTAINS_MODULE*]->(container)
    OPTIONAL MATCH (container)-[:DEFINES|DEFINES_METHOD*]->(defined)
    DETACH DELETE p, container, defined
    """
    self._execute_query(query, {KEY_PROJECT_NAME: project_name})
```

## 8. 性能优化

### 8.1 批量插入优势

- **减少网络往返**: 一次请求插入多条记录
- **事务优化**: 批量操作在同一事务中
- **内存管理**: 控制缓冲区大小避免内存溢出

### 8.2 刷新策略

```python
def flush_all(self) -> None:
    # 先刷新节点（关系依赖节点存在）
    self.flush_nodes()
    # 再刷新关系
    self.flush_relationships()
```

### 8.3 错误处理

```python
def _execute_batch(self, query: str, params_list: Sequence[BatchParams]) -> None:
    try:
        cursor.execute(wrap_with_unwind(query), BatchWrapper(batch=params_list))
    except Exception as e:
        # 忽略已存在的约束错误
        if ERR_SUBSTR_ALREADY_EXISTS not in str(e).lower():
            logger.error(...)
            raise
```

## 9. 数据流总结

```
节点/关系创建请求
  ↓
添加到缓冲区
  ↓
缓冲区满？
  ├─ 是 → flush_nodes() / flush_relationships()
  └─ 否 → 继续累积
  ↓
按标签/模式分组
  ↓
构建批量 Cypher 查询
  ↓
执行 UNWIND 批量操作
  ↓
返回结果统计
```

## 10. 相关文档

- [第一部分：总览和入口流程](./01-overview-and-entry.md)
- [第二部分：Java 语法解析详细流程](./02-java-parsing.md)
- [第四部分：查询逻辑](./04-query-logic.md)
