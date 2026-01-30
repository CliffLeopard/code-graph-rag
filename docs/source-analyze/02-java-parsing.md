# Code-Graph-RAG 工作流程详解 - 第二部分：Java 语法解析详细流程

## 1. Java 文件识别

### 1.1 语言检测

**位置**: `codebase_rag/language_spec.py`

```python
def get_language_spec(suffix: str) -> LanguageSpec | None:
    # .java 文件会被识别为 Java 语言
    # 返回对应的 LanguageSpec 配置
```

### 1.2 解析器加载

**位置**: `codebase_rag/parser_loader.py`

```python
def load_parsers() -> tuple[dict, dict]:
    # 加载 tree-sitter-java 解析器
    # 创建 Parser 和 LanguageQueries 对象
```

## 2. 文件处理入口

### 2.1 DefinitionProcessor.process_file()

**位置**: `codebase_rag/parsers/definition_processor.py`

```python
def process_file(
    self,
    file_path: Path,
    language: SupportedLanguage,
    queries: dict[SupportedLanguage, LanguageQueries],
    structural_elements: dict[Path, str | None],
) -> tuple[ASTNode, SupportedLanguage] | None:
```

### 2.2 处理步骤

#### 步骤 1: 读取文件并解析 AST

```python
source_bytes = file_path.read_bytes()
lang_queries = queries[language]
parser = lang_queries.get(cs.KEY_PARSER)
tree = parser.parse(source_bytes)
root_node = tree.root_node
```

#### 步骤 2: 构建模块限定名

```python
# 例如: project_name.com.example.utils.StringUtils
module_qn = cs.SEPARATOR_DOT.join(
    [self.project_name] + list(relative_path.with_suffix("").parts)
)
```

#### 步骤 3: 创建模块节点

```python
self.ingestor.ensure_node_batch(
    cs.NodeLabel.MODULE,
    {
        cs.KEY_QUALIFIED_NAME: module_qn,
        cs.KEY_NAME: file_path.name,
        cs.KEY_PATH: relative_path_str,
    },
)
```

#### 步骤 4: 创建模块关系

```python
# 模块 -> 父容器（包/文件夹/项目）
self.ingestor.ensure_relationship_batch(
    (parent_label, parent_key, parent_val),
    cs.RelationshipType.CONTAINS_MODULE,
    (cs.NodeLabel.MODULE, cs.KEY_QUALIFIED_NAME, module_qn),
)
```

## 3. 导入解析 (ImportProcessor)

### 3.1 Java 导入语法

Java 支持以下导入类型：

- `import java.util.List;` - 普通导入
- `import static java.lang.Math.*;` - 静态导入
- `import java.util.*;` - 通配符导入

### 3.2 解析流程

**位置**: `codebase_rag/parsers/import_processor.py`

```python
def _parse_java_imports(self, captures: dict, module_qn: str) -> None:
    for import_node in captures.get(cs.CAPTURE_IMPORT, []):
        if import_node.type == cs.TS_IMPORT_DECLARATION:
            # 解析导入声明
            is_static = False
            imported_path = None
            is_wildcard = False

            # 提取导入路径
            for child in import_node.children:
                if child.type == cs.TS_STATIC:
                    is_static = True
                elif child.type == cs.TS_SCOPED_IDENTIFIER:
                    imported_path = safe_decode_with_fallback(child)
                elif child.type == cs.TS_ASTERISK:
                    is_wildcard = True

            # 解析路径
            resolved_path = self._resolve_java_import_path(imported_path)

            # 存储到 import_mapping
            if is_wildcard:
                self.import_mapping[module_qn][f"*{resolved_path}"] = resolved_path
            else:
                imported_name = parts[-1]
                self.import_mapping[module_qn][imported_name] = resolved_path
```

### 3.3 导入关系创建

```python
# 创建 IMPORTS 关系
self.ingestor.ensure_relationship_batch(
    (cs.NodeLabel.MODULE, cs.KEY_QUALIFIED_NAME, module_qn),
    cs.RelationshipType.IMPORTS,
    (cs.NodeLabel.MODULE, cs.KEY_QUALIFIED_NAME, module_path),
)
```

## 4. 类解析 (ClassIngestMixin)

### 4.1 类节点查询

**位置**: `codebase_rag/parsers/class_ingest/mixin.py`

```python
def _ingest_classes_and_methods(
    self,
    root_node: Node,
    module_qn: str,
    language: SupportedLanguage,
    queries: dict[SupportedLanguage, LanguageQueries],
) -> None:
    # 使用 tree-sitter 查询查找所有类节点
    query = lang_queries[cs.QUERY_CLASSES]
    cursor = QueryCursor(query)
    captures = cursor.captures(root_node)
    class_nodes = captures.get(cs.CAPTURE_CLASS, [])
```

### 4.2 类信息提取

**位置**: `codebase_rag/parsers/java/utils.py`

```python
def extract_class_info(class_node: ASTNode) -> JavaClassInfo:
    # 提取类名
    name = safe_decode_text(class_node.child_by_field_name(cs.TS_FIELD_NAME))

    # 提取类类型（class/interface/enum/annotation/record）
    class_type = class_node.type.replace(cs.JAVA_DECLARATION_SUFFIX, "")

    # 提取父类
    superclass = _extract_superclass(class_node)

    # 提取实现的接口
    interfaces = _extract_interfaces(class_node)

    # 提取修饰符
    modifiers = _extract_class_modifiers(class_node)

    # 提取类型参数
    type_parameters = _extract_type_parameters(class_node)

    return JavaClassInfo(
        name=name,
        type=class_type,
        superclass=superclass,
        interfaces=interfaces,
        modifiers=modifiers,
        type_parameters=type_parameters,
    )
```

### 4.3 类限定名构建

**位置**: `codebase_rag/parsers/class_ingest/identity.py`

```python
def resolve_class_identity(
    class_node: Node,
    module_qn: str,
    language: SupportedLanguage,
    ...
) -> tuple[str, str, bool] | None:
    # 构建类的完全限定名
    # 例如: project_name.com.example.utils.StringUtils
    class_qn = f"{module_qn}.{class_name}"

    # 判断是否导出（public 类）
    is_exported = "public" in modifiers

    return (class_qn, class_name, is_exported)
```

### 4.4 类节点创建

```python
class_props: PropertyDict = {
    cs.KEY_QUALIFIED_NAME: class_qn,
    cs.KEY_NAME: class_name,
    cs.KEY_DECORATORS: self._extract_decorators(class_node),
    cs.KEY_START_LINE: class_node.start_point[0] + 1,
    cs.KEY_END_LINE: class_node.end_point[0] + 1,
    cs.KEY_DOCSTRING: self._get_docstring(class_node),
    cs.KEY_IS_EXPORTED: is_exported,
}

self.ingestor.ensure_node_batch(node_type, class_props)
self.function_registry[class_qn] = node_type
self.simple_name_lookup[class_name].add(class_qn)
```

### 4.5 类关系创建

**位置**: `codebase_rag/parsers/class_ingest/relationships.py`

```python
def create_class_relationships(...) -> None:
    # 1. 提取父类
    parent_classes = extract_parent_classes(...)
    class_inheritance[class_qn] = parent_classes

    # 2. 创建 DEFINES 关系（模块 -> 类）
    ingestor.ensure_relationship_batch(
        (cs.NodeLabel.MODULE, cs.KEY_QUALIFIED_NAME, module_qn),
        cs.RelationshipType.DEFINES,
        (node_type, cs.KEY_QUALIFIED_NAME, class_qn),
    )

    # 3. 创建继承关系
    for parent_class_qn in parent_classes:
        create_inheritance_relationship(...)

    # 4. 创建实现关系
    if class_node.type == cs.TS_CLASS_DECLARATION:
        for interface_qn in extract_implemented_interfaces(...):
            create_implements_relationship(...)
```

## 5. 方法解析

### 5.1 方法信息提取

**位置**: `codebase_rag/parsers/java/utils.py`

```python
def extract_method_info(method_node: ASTNode) -> JavaMethodInfo:
    # 提取方法名
    name = safe_decode_text(method_node.child_by_field_name(cs.TS_FIELD_NAME))

    # 判断是方法还是构造函数
    method_type = _get_method_type(method_node)

    # 提取返回类型
    return_type = _extract_method_return_type(method_node)

    # 提取参数类型列表
    parameters = _extract_method_parameters(method_node)

    # 提取修饰符
    modifiers = extract_from_modifiers_node(...).modifiers

    # 提取注解
    annotations = extract_from_modifiers_node(...).annotations

    return JavaMethodInfo(
        name=name,
        type=method_type,
        return_type=return_type,
        parameters=parameters,
        modifiers=modifiers,
        annotations=annotations,
    )
```

### 5.2 方法限定名构建

**位置**: `codebase_rag/parsers/handlers/java.py`

```python
def build_method_qualified_name(
    self,
    class_qn: str,
    method_name: str,
    method_node: ASTNode,
) -> str:
    # Java 方法包含参数签名以支持重载
    # 例如: com.example.User.getName()
    #       com.example.User.setName(String)
    if method_info[cs.FIELD_PARAMETERS]:
        param_sig = cs.SEPARATOR_COMMA_SPACE.join(method_info[cs.FIELD_PARAMETERS])
        return f"{class_qn}{cs.SEPARATOR_DOT}{method_name}({param_sig})"
    return f"{class_qn}{cs.SEPARATOR_DOT}{method_name}"
```

### 5.3 方法节点创建

**位置**: `codebase_rag/parsers/utils.py`

```python
def ingest_method(
    method_node: Node,
    class_qn: str,
    parent_type: str,
    ingestor: IngestorProtocol,
    function_registry: FunctionRegistryTrieProtocol,
    simple_name_lookup: SimpleNameLookup,
    get_docstring: Callable,
    language: SupportedLanguage,
    extract_decorators: Callable | None = None,
    method_qualified_name: str | None = None,
) -> None:
    # 构建方法属性
    method_props = {
        cs.KEY_QUALIFIED_NAME: method_qn,
        cs.KEY_NAME: method_name,
        cs.KEY_START_LINE: method_node.start_point[0] + 1,
        cs.KEY_END_LINE: method_node.end_point[0] + 1,
        cs.KEY_DOCSTRING: get_docstring(method_node),
        ...
    }

    # 创建方法节点
    ingestor.ensure_node_batch(cs.NodeLabel.METHOD, method_props)

    # 注册到 function_registry
    function_registry[method_qn] = cs.NodeLabel.METHOD
    simple_name_lookup[method_name].add(method_qn)

    # 创建 DEFINES_METHOD 关系（类 -> 方法）
    ingestor.ensure_relationship_batch(
        (parent_type, cs.KEY_QUALIFIED_NAME, class_qn),
        cs.RelationshipType.DEFINES_METHOD,
        (cs.NodeLabel.METHOD, cs.KEY_QUALIFIED_NAME, method_qn),
    )
```

## 6. 包声明解析

### 6.1 包名提取

**位置**: `codebase_rag/parsers/java/utils.py`

```python
def extract_package_name(package_node: ASTNode) -> str | None:
    if package_node.type != cs.TS_PACKAGE_DECLARATION:
        return None

    # 提取包名，例如: com.example.utils
    return next(
        (
            safe_decode_text(child)
            for child in package_node.children
            if child.type in [cs.TS_SCOPED_IDENTIFIER, cs.TS_IDENTIFIER]
        ),
        None,
    )
```

### 6.2 包节点创建

包节点在 `StructureProcessor.identify_structure()` 中创建，用于表示 Java 包结构。

## 7. 字段解析

### 7.1 字段信息提取

**位置**: `codebase_rag/parsers/java/utils.py`

```python
def extract_field_info(field_node: ASTNode) -> JavaFieldInfo:
    # 提取字段类型
    field_type = safe_decode_text(
        field_node.child_by_field_name(cs.TS_FIELD_TYPE)
    )

    # 提取字段名
    name = safe_decode_text(
        field_node.child_by_field_name(cs.TS_FIELD_DECLARATOR)
        .child_by_field_name(cs.TS_FIELD_NAME)
    )

    # 提取修饰符和注解
    mods_and_annots = extract_from_modifiers_node(...)

    return JavaFieldInfo(
        name=name,
        type=field_type,
        modifiers=mods_and_annots.modifiers,
        annotations=mods_and_annots.annotations,
    )
```

## 8. 特殊方法处理

### 8.1 main 方法识别

```python
def is_main_method(method_node: ASTNode) -> bool:
    # 检查方法名是否为 "main"
    # 检查返回类型是否为 void
    # 检查修饰符是否包含 public static
    # 检查参数是否为 String[] args
    ...
```

### 8.2 构造函数处理

构造函数使用特殊的方法类型标识：`JAVA_TYPE_CONSTRUCTOR`

## 9. 数据流总结

```
Java 源文件
  ↓
tree-sitter 解析 → AST
  ↓
提取包声明 → 包节点
  ↓
提取导入 → 导入关系
  ↓
提取类 → 类节点 + DEFINES 关系
  ├─→ 提取父类 → 继承关系
  ├─→ 提取接口 → 实现关系
  └─→ 提取方法 → 方法节点 + DEFINES_METHOD 关系
       ├─→ 提取参数类型
       ├─→ 提取返回类型
       └─→ 提取修饰符和注解
  ↓
注册到 function_registry
  ↓
注册到 simple_name_lookup
```

## 10. 相关文档

- [第一部分：总览和入口流程](./01-overview-and-entry.md)
- [第三部分：数据库插入逻辑](./03-database-insertion.md)
- [第四部分：查询逻辑](./04-query-logic.md)
