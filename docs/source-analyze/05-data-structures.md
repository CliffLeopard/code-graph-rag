# Code-Graph-RAG 工作流程详解 - 第五部分：关键数据结构

## 1. 核心数据结构

### 1.1 FunctionRegistryTrie

**位置**: `codebase_rag/graph_updater.py`

```python
class FunctionRegistryTrie:
    def __init__(self, simple_name_lookup: SimpleNameLookup | None = None):
        self.root: TrieNode = {}  # Trie 根节点
        self._entries: FunctionRegistry = {}  # FQN -> NodeType 映射
        self._simple_name_lookup = simple_name_lookup  # 简单名称索引

    def insert(self, qualified_name: QualifiedName, func_type: NodeType) -> None:
        # 插入到字典
        self._entries[qualified_name] = func_type

        # 插入到 Trie
        parts = qualified_name.split(cs.SEPARATOR_DOT)
        current = self.root
        for part in parts:
            if part not in current:
                current[part] = {}
            current = current[part]
        current[cs.TRIE_TYPE_KEY] = func_type
        current[cs.TRIE_QN_KEY] = qualified_name
```

**用途**:
- 存储所有函数/方法的完全限定名
- 支持前缀搜索
- 快速查找同名函数

**示例**:
```python
registry = FunctionRegistryTrie()
registry.insert("com.example.User.getName", "Method")
registry.insert("com.example.User.setName", "Method")

# 查找所有 User 类的方法
methods = registry.find_with_prefix("com.example.User")
# 返回: [("com.example.User.getName", "Method"), ...]
```

### 1.2 SimpleNameLookup

**类型**: `defaultdict[str, set[str]]`

```python
simple_name_lookup: SimpleNameLookup = defaultdict(set)

# 使用示例
simple_name_lookup["getName"].add("com.example.User.getName")
simple_name_lookup["getName"].add("com.example.Product.getName")

# 查找所有名为 "getName" 的方法
all_getName_methods = simple_name_lookup["getName"]
```

**用途**:
- 从简单名称快速查找所有匹配的 FQN
- 支持方法重载查找

### 1.3 BoundedASTCache

**位置**: `codebase_rag/graph_updater.py`

```python
class BoundedASTCache:
    def __init__(
        self,
        max_entries: int | None = None,
        max_memory_mb: int | None = None,
    ):
        self.cache: OrderedDict[Path, tuple[Node, SupportedLanguage]] = OrderedDict()
        self.max_entries = max_entries or settings.CACHE_MAX_ENTRIES
        self.max_memory_bytes = max_memory_mb * cs.BYTES_PER_MB
```

**用途**:
- 缓存已解析的 AST
- 使用 LRU 策略
- 限制内存使用

### 1.4 LanguageQueries

**位置**: `codebase_rag/types_defs.py`

```python
class LanguageQueries(TypedDict):
    functions: Query | None  # 函数查询模式
    classes: Query | None    # 类查询模式
    calls: Query | None      # 调用查询模式
    imports: Query | None     # 导入查询模式
    locals: Query | None     # 局部变量查询模式
    config: LanguageSpec     # 语言配置
    language: Language       # tree-sitter Language 对象
    parser: Parser           # tree-sitter Parser 对象
```

**用途**:
- 存储每种语言的 tree-sitter 查询模式
- 用于在 AST 中查找特定节点

## 2. Java 特定数据结构

### 2.1 JavaClassInfo

**位置**: `codebase_rag/types_defs.py`

```python
class JavaClassInfo(TypedDict):
    name: str | None                    # 类名
    type: str                           # 类型: "class", "interface", "enum", etc.
    superclass: str | None              # 父类名
    interfaces: list[str]              # 实现的接口列表
    modifiers: list[str]                # 修饰符: ["public", "final"]
    type_parameters: list[str]          # 泛型参数: ["T", "E"]
```

**示例**:
```python
class_info = JavaClassInfo(
    name="StringUtils",
    type="class",
    superclass="Object",
    interfaces=["Serializable"],
    modifiers=["public", "final"],
    type_parameters=[],
)
```

### 2.2 JavaMethodInfo

**位置**: `codebase_rag/types_defs.py`

```python
class JavaMethodInfo(TypedDict):
    name: str | None                    # 方法名
    type: str                           # "method" 或 "constructor"
    return_type: str | None            # 返回类型
    parameters: list[str]              # 参数类型列表
    modifiers: list[str]               # 修饰符
    type_parameters: list[str]         # 泛型参数
    annotations: list[str]             # 注解
```

**示例**:
```python
method_info = JavaMethodInfo(
    name="isEmpty",
    type="method",
    return_type="boolean",
    parameters=["String"],
    modifiers=["public", "static"],
    type_parameters=[],
    annotations=["@Nullable"],
)
```

### 2.3 JavaMethodCallInfo

**位置**: `codebase_rag/types_defs.py`

```python
class JavaMethodCallInfo(TypedDict):
    name: str | None                    # 方法名
    object: str | None                 # 调用对象: "this", "super", 或变量名
    arguments: int                      # 参数数量
```

**示例**:
```python
call_info = JavaMethodCallInfo(
    name="toString",
    object="this",
    arguments=0,
)
```

### 2.4 JavaFieldInfo

**位置**: `codebase_rag/types_defs.py`

```python
class JavaFieldInfo(TypedDict):
    name: str | None                    # 字段名
    type: str | None                   # 字段类型
    modifiers: list[str]               # 修饰符
    annotations: list[str]              # 注解
```

## 3. 数据库相关数据结构

### 3.1 NodeBatchRow

**位置**: `codebase_rag/types_defs.py`

```python
class NodeBatchRow(TypedDict):
    id: PropertyValue                   # 唯一标识符值
    props: PropertyDict                 # 其他属性
```

**用途**: 批量插入节点时的数据格式

### 3.2 RelBatchRow

**位置**: `codebase_rag/types_defs.py`

```python
class RelBatchRow(TypedDict):
    from_val: PropertyValue            # 源节点标识符值
    to_val: PropertyValue              # 目标节点标识符值
    props: PropertyDict                # 关系属性
```

**用途**: 批量插入关系时的数据格式

### 3.3 PropertyDict

**类型**: `dict[str, PropertyValue]`

```python
PropertyValue = str | int | float | bool | list | dict | None
PropertyDict = dict[str, PropertyValue]
```

**用途**: 节点和关系的属性字典

### 3.4 ResultRow

**类型**: `dict[str, ResultValue]`

```python
ResultValue = str | int | float | bool | list | dict | None
ResultRow = dict[str, ResultValue]
```

**用途**: 查询结果的行数据

## 4. 配置数据结构

### 4.1 LanguageSpec

**位置**: `codebase_rag/language_spec.py`

```python
class LanguageSpec(BaseModel):
    language: SupportedLanguage | str
    extensions: list[str]              # 文件扩展名: [".java"]
    function_node_types: tuple[str, ...]  # 函数节点类型
    class_node_types: tuple[str, ...]   # 类节点类型
    call_node_types: tuple[str, ...]     # 调用节点类型
    import_node_types: tuple[str, ...]    # 导入节点类型
    import_from_node_types: tuple[str, ...]
    module_node_types: tuple[str, ...]
    function_query: str | None          # 自定义函数查询
    class_query: str | None             # 自定义类查询
    call_query: str | None              # 自定义调用查询
```

**Java 示例**:
```python
java_spec = LanguageSpec(
    language=SupportedLanguage.JAVA,
    extensions=[".java"],
    function_node_types=("method_declaration", "constructor_declaration"),
    class_node_types=("class_declaration", "interface_declaration", ...),
    call_node_types=("method_invocation",),
    import_node_types=("import_declaration",),
    ...
)
```

## 5. 处理器数据结构

### 5.1 ProcessorFactory 组件

```python
class ProcessorFactory:
    _import_processor: ImportProcessor | None
    _structure_processor: StructureProcessor | None
    _definition_processor: DefinitionProcessor | None
    _type_inference: TypeInferenceEngine | None
    _call_processor: CallProcessor | None

    module_qn_to_file_path: dict[str, Path]  # 模块限定名 -> 文件路径
```

### 5.2 ImportProcessor 数据结构

```python
class ImportProcessor:
    import_mapping: dict[str, dict[str, str]]
    # 外层 key: 模块限定名
    # 内层 key: 本地名称
    # 内层 value: 完整限定名

    # 示例:
    # {
    #   "com.example.ClassA": {
    #     "List": "java.util.List",
    #     "String": "java.lang.String",
    #     "*java.util": "java.util"
    #   }
    # }
```

## 6. 类型推断数据结构

### 6.1 局部变量类型映射

```python
local_var_types: dict[str, str]
# key: 变量名
# value: 类型限定名

# 示例:
# {
#   "user": "com.example.User",
#   "list": "java.util.List",
#   "count": "int"
# }
```

### 6.2 类继承映射

```python
class_inheritance: dict[str, list[str]]
# key: 类限定名
# value: 父类限定名列表

# 示例:
# {
#   "com.example.ChildClass": ["com.example.ParentClass"],
#   "com.example.ParentClass": ["java.lang.Object"]
# }
```

## 7. 查询结果数据结构

### 7.1 QueryGraphData

**位置**: `codebase_rag/schemas.py`

```python
class QueryGraphData(BaseModel):
    query_used: str                    # 使用的 Cypher 查询
    results: list[ResultRow]           # 查询结果
    summary: str                       # 结果摘要
```

### 7.2 CodeSnippet

**位置**: `codebase_rag/schemas.py`

```python
class CodeSnippet(BaseModel):
    qualified_name: str                # 完全限定名
    source_code: str                   # 源代码
    file_path: str                     # 文件路径
    line_start: int                    # 起始行号
    line_end: int                      # 结束行号
    docstring: str | None             # 文档字符串
    found: bool = True                 # 是否找到
    error_message: str | None         # 错误信息
```

### 7.3 SemanticSearchResult

**位置**: `codebase_rag/types_defs.py`

```python
class SemanticSearchResult(TypedDict):
    node_id: int                       # 节点 ID
    qualified_name: str                # 完全限定名
    similarity_score: float            # 相似度分数
```

## 8. 常量定义

### 8.1 节点标签

**位置**: `codebase_rag/constants.py`

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

### 8.2 关系类型

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

### 8.3 属性键

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

## 9. 数据结构关系图

```
FunctionRegistryTrie
  ├─→ _entries: FunctionRegistry (FQN -> NodeType)
  ├─→ root: TrieNode (前缀树)
  └─→ _simple_name_lookup: SimpleNameLookup (简单名 -> FQN 集合)

BoundedASTCache
  └─→ cache: OrderedDict[Path, (Node, Language)]

LanguageQueries
  ├─→ functions: Query
  ├─→ classes: Query
  ├─→ calls: Query
  ├─→ imports: Query
  └─→ config: LanguageSpec

ImportProcessor
  └─→ import_mapping: dict[module_qn, dict[local_name, full_name]]

GraphUpdater
  ├─→ function_registry: FunctionRegistryTrie
  ├─→ simple_name_lookup: SimpleNameLookup
  ├─→ ast_cache: BoundedASTCache
  └─→ factory: ProcessorFactory
```

## 10. 相关文档

- [第一部分：总览和入口流程](./01-overview-and-entry.md)
- [第二部分：Java 语法解析详细流程](./02-java-parsing.md)
- [第三部分：数据库插入逻辑](./03-database-insertion.md)
- [第四部分：查询逻辑](./04-query-logic.md)
- [第六部分：完整流程图](./06-flowcharts.md)
