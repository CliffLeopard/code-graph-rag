# Language Grammar 添加流程详解 - 第四部分：节点类型分析流程

## 1. 节点类型分析概述

节点类型分析是自动识别语法库中 AST 节点类型的关键步骤。系统需要将语法库中的节点类型分类为：

- **函数节点** (Functions): 方法、函数定义等
- **类节点** (Classes): 类、接口、结构体等
- **模块节点** (Modules): 文件、编译单元等
- **调用节点** (Calls): 函数调用、方法调用等

## 2. 查找节点类型文件：\_find_node_types_path()

### 2.1 函数签名

**位置**: `codebase_rag/tools/language.py`

```python
def _find_node_types_path(
    grammar_path: str,      # 语法库路径
    language_name: str      # 语言名称
) -> str | None:
```

### 2.2 可能的路径

```python
def _find_node_types_path(grammar_path: str, language_name: str) -> str | None:
    possible_paths = [
        # 路径 1: 直接在 src 目录下
        os.path.join(grammar_path, cs.LANG_SRC_DIR, cs.LANG_NODE_TYPES_JSON),
        # 例如: grammars/tree-sitter-kotlin/src/node-types.json

        # 路径 2: 在语言名子目录下
        os.path.join(
            grammar_path, language_name, cs.LANG_SRC_DIR, cs.LANG_NODE_TYPES_JSON
        ),
        # 例如: grammars/tree-sitter-kotlin/kotlin/src/node-types.json

        # 路径 3: 语言名使用下划线
        os.path.join(
            grammar_path,
            language_name.replace("-", "_"),
            cs.LANG_SRC_DIR,
            cs.LANG_NODE_TYPES_JSON,
        ),
        # 例如: grammars/tree-sitter-kotlin/kotlin/src/node-types.json
    ]

    # 返回第一个存在的路径
    return next((path for path in possible_paths if os.path.exists(path)), None)
```

### 2.3 路径查找逻辑

系统按顺序检查以下路径，返回第一个存在的：

1. `grammars/tree-sitter-kotlin/src/node-types.json`
2. `grammars/tree-sitter-kotlin/kotlin/src/node-types.json`
3. `grammars/tree-sitter-kotlin/kotlin_/src/node-types.json` (如果语言名包含连字符)

## 3. 解析节点类型文件：\_parse_node_types_file()

### 3.1 函数签名

```python
def _parse_node_types_file(
    node_types_path: str
) -> NodeCategories | None:
```

### 3.2 执行流程

```python
def _parse_node_types_file(node_types_path: str) -> NodeCategories | None:
    try:
        # 步骤 1: 读取 JSON 文件
        with open(node_types_path) as f:
            node_types = json.load(f)

        # 步骤 2: 提取所有节点名称
        all_node_names: set[str] = set()

        def extract_types(obj: dict | list) -> None:
            if isinstance(obj, dict):
                if "type" in obj and isinstance(obj["type"], str):
                    all_node_names.add(obj["type"])
                for value in obj.values():
                    if isinstance(value, dict | list):
                        extract_types(value)
            elif isinstance(obj, list):
                for item in obj:
                    if isinstance(item, dict | list):
                        extract_types(item)

        extract_types(node_types)

        # 步骤 3: 提取语义分类
        semantic_categories = _extract_semantic_categories(node_types)

        # 步骤 4: 显示统计信息
        click.echo(
            f"📊 {cs.LANG_MSG_FOUND_NODE_TYPES.format(count=len(all_node_names))}"
        )
        click.echo(f"🌳 {cs.LANG_MSG_SEMANTIC_CATEGORIES}")

        # 步骤 5: 显示每个分类
        for category, subtypes in semantic_categories.items():
            preview = f"{subtypes[:5]}{cs.LANG_ELLIPSIS if len(subtypes) > 5 else ''}"
            click.echo(
                cs.LANG_MSG_CATEGORY_FORMAT.format(
                    category=category, subtypes=preview, count=len(subtypes)
                )
            )

        # 步骤 6: 分类节点类型
        categories = _categorize_node_types(semantic_categories, node_types)

        # 步骤 7: 显示分类结果
        click.echo(f"🎯 {cs.LANG_MSG_MAPPED_CATEGORIES}")
        click.echo(cs.LANG_MSG_FUNCTIONS.format(nodes=categories.functions))
        click.echo(cs.LANG_MSG_CLASSES.format(nodes=categories.classes))
        click.echo(cs.LANG_MSG_MODULES.format(nodes=categories.modules))
        click.echo(cs.LANG_MSG_CALLS.format(nodes=categories.calls))

        return categories

    except Exception as e:
        logger.error(cs.LANG_ERR_PARSE_NODE_TYPES.format(error=e))
        click.echo(cs.LANG_ERR_PARSE_NODE_TYPES.format(error=e))
        return None
```

## 4. 提取语义分类：\_extract_semantic_categories()

### 4.1 函数签名

```python
def _extract_semantic_categories(
    node_types_json: list[dict]
) -> dict[str, list[str]]:
```

### 4.2 执行流程

```python
def _extract_semantic_categories(node_types_json: list[dict]) -> dict[str, list[str]]:
    categories: dict[str, list[str]] = {}

    # 遍历所有节点类型
    for node in node_types_json:
        if isinstance(node, dict) and "type" in node and "subtypes" in node:
            # 提取子类型
            subtypes = [
                subtype["type"]
                for subtype in node["subtypes"]
                if "type" in subtype
            ]
            # 按主类型分组
            categories.setdefault(node["type"], []).extend(subtypes)

    # 去重
    for category, values in categories.items():
        categories[category] = list(set(values))

    return categories
```

### 4.3 node-types.json 格式示例

```json
[
  {
    "type": "declaration",
    "subtypes": [
      { "type": "function_declaration" },
      { "type": "class_declaration" },
      { "type": "variable_declaration" }
    ]
  },
  {
    "type": "expression",
    "subtypes": [{ "type": "call_expression" }, { "type": "binary_expression" }]
  }
]
```

### 4.4 提取结果示例

```python
semantic_categories = {
    "declaration": [
        "function_declaration",
        "class_declaration",
        "variable_declaration"
    ],
    "expression": [
        "call_expression",
        "binary_expression"
    ]
}
```

## 5. 分类节点类型：\_categorize_node_types()

### 5.1 函数签名

```python
def _categorize_node_types(
    semantic_categories: dict[str, list[str]],
    node_types: list[dict]
) -> NodeCategories:
```

### 5.2 执行流程

```python
def _categorize_node_types(...) -> NodeCategories:
    functions: list[str] = []
    classes: list[str] = []
    modules: list[str] = []
    calls: list[str] = []

    # 遍历所有语义分类的子类型
    for subtypes in semantic_categories.values():
        for subtype in subtypes:
            subtype_lower = subtype.lower()

            # 判断是否为函数节点
            if (
                any(kw in subtype_lower for kw in cs.LANG_FUNCTION_KEYWORDS)
                and cs.LANG_CALL_KEYWORD_EXCLUDE not in subtype_lower
            ):
                functions.append(subtype)

            # 判断是否为类节点
            elif any(kw in subtype_lower for kw in cs.LANG_CLASS_KEYWORDS) and all(
                kw not in subtype_lower for kw in cs.LANG_EXCLUSION_KEYWORDS
            ):
                classes.append(subtype)

            # 判断是否为调用节点
            elif any(kw in subtype_lower for kw in cs.LANG_CALL_KEYWORDS):
                calls.append(subtype)

            # 判断是否为模块节点
            elif any(kw in subtype_lower for kw in cs.LANG_MODULE_KEYWORDS):
                modules.append(subtype)

    # 添加根节点作为模块节点
    root_nodes = [
        node["type"]
        for node in node_types
        if isinstance(node, dict) and node.get("root")
    ]
    modules.extend(root_nodes)

    # 去重并返回
    return NodeCategories(
        functions=list(set(functions)),
        classes=list(set(classes)),
        modules=list(set(modules)),
        calls=list(set(calls)),
    )
```

### 5.3 关键词匹配

#### 函数关键词

```python
LANG_FUNCTION_KEYWORDS = frozenset({
    "function",
    "method",
    "procedure",
    "routine",
    "subroutine",
    "func",
    "def",
    "fn",
    "constructor",
    "destructor",
})
```

#### 类关键词

```python
LANG_CLASS_KEYWORDS = frozenset({
    "class",
    "struct",
    "interface",
    "trait",
    "type",
    "enum",
    "union",
    "record",
    "object",
    "module",
})
```

#### 调用关键词

```python
LANG_CALL_KEYWORDS = frozenset({
    "call",
    "invoke",
    "invocation"
})
```

#### 模块关键词

```python
LANG_MODULE_KEYWORDS = frozenset({
    "program",
    "source_file",
    "compilation_unit",
    "module",
    "chunk"
})
```

#### 排除关键词

```python
LANG_EXCLUSION_KEYWORDS = frozenset({
    "access",
    "call"
})
```

## 6. 手动输入节点分类：\_prompt_for_node_categories()

### 6.1 触发条件

当 `node-types.json` 文件不存在或解析失败时触发。

### 6.2 函数签名

```python
def _prompt_for_node_categories() -> NodeCategories:
```

### 6.3 执行流程

```python
def _prompt_for_node_categories() -> NodeCategories:
    # 步骤 1: 显示可用节点类型
    click.echo(cs.LANG_MSG_AVAILABLE_NODES)
    click.echo(cs.LANG_MSG_FUNCTIONS.format(nodes=list(cs.LANG_DEFAULT_FUNCTION_NODES)))
    click.echo(cs.LANG_MSG_CLASSES.format(nodes=list(cs.LANG_DEFAULT_CLASS_NODES)))

    # 步骤 2: 提示输入函数节点
    functions = [
        node.strip()
        for node in click.prompt(cs.LANG_PROMPT_FUNCTIONS, type=str).split(",")
    ]
    # 提示: "Select nodes representing FUNCTIONS (comma-separated)"
    # 用户输入: "function_declaration, method_declaration"

    # 步骤 3: 提示输入类节点
    classes = [
        node.strip()
        for node in click.prompt(cs.LANG_PROMPT_CLASSES, type=str).split(",")
    ]
    # 提示: "Select nodes representing CLASSES (comma-separated)"

    # 步骤 4: 提示输入模块节点
    modules = [
        node.strip()
        for node in click.prompt(cs.LANG_PROMPT_MODULES, type=str).split(",")
    ]
    # 提示: "Select nodes representing MODULES (comma-separated)"

    # 步骤 5: 提示输入调用节点
    calls = [
        node.strip()
        for node in click.prompt(cs.LANG_PROMPT_CALLS, type=str).split(",")
    ]
    # 提示: "Select nodes representing FUNCTION CALLS (comma-separated)"

    return NodeCategories(functions, classes, modules, calls)
```

## 7. NodeCategories 数据结构

### 7.1 定义

```python
class NodeCategories(NamedTuple):
    functions: list[str]   # 函数节点类型列表
    classes: list[str]     # 类节点类型列表
    modules: list[str]     # 模块节点类型列表
    calls: list[str]       # 调用节点类型列表
```

### 7.2 使用示例

```python
categories = NodeCategories(
    functions=["function_declaration", "method_declaration"],
    classes=["class_declaration", "interface_declaration"],
    modules=["compilation_unit"],
    calls=["call_expression", "method_invocation"]
)
```

## 8. 默认值处理

### 8.1 当解析失败时使用默认值

```python
if categories := _parse_node_types_file(node_types_path):
    # 解析成功，使用解析结果
    functions = categories.functions
    classes = categories.classes
    modules = categories.modules
    calls = categories.calls
else:
    # 解析失败，使用默认值
    functions = [cs.LANG_FALLBACK_METHOD_NODE]  # ["method_declaration"]
    classes = list(cs.LANG_DEFAULT_CLASS_NODES)  # ["class_declaration"]
    modules = list(cs.LANG_DEFAULT_MODULE_NODES)  # ["compilation_unit"]
    calls = list(cs.LANG_DEFAULT_CALL_NODES)      # ["invocation_expression"]
```

### 8.2 默认值定义

```python
LANG_DEFAULT_FUNCTION_NODES = ("function_definition", "method_definition")
LANG_DEFAULT_CLASS_NODES = ("class_declaration",)
LANG_DEFAULT_MODULE_NODES = ("compilation_unit",)
LANG_DEFAULT_CALL_NODES = ("invocation_expression",)
LANG_FALLBACK_METHOD_NODE = "method_declaration"
```

## 9. 两种命令方式的节点类型分析

### 9.1 标准方式：`cgr language add-grammar kotlin`

```python
# 查找路径
node_types_path = _find_node_types_path(
    "grammars/tree-sitter-kotlin",
    "kotlin"
)
# 可能找到: grammars/tree-sitter-kotlin/src/node-types.json

# 解析节点类型
categories = _parse_node_types_file(node_types_path)
# 自动分类 Kotlin 的节点类型
```

### 9.2 自定义方式：`cgr language add-grammar --grammar-url ...`

```python
# 查找路径（相同逻辑）
node_types_path = _find_node_types_path(
    "grammars/tree-sitter-kotlin",
    "kotlin"  # 从 tree-sitter.json 或 URL 提取
)

# 解析节点类型（相同逻辑）
categories = _parse_node_types_file(node_types_path)
```

**差异**: 两种方式的节点类型分析逻辑完全相同，差异仅在于语言名称的来源。

## 10. 分类示例：Kotlin

### 10.1 输入（node-types.json 片段）

```json
[
  {
    "type": "declaration",
    "subtypes": [
      { "type": "function_declaration" },
      { "type": "class_declaration" },
      { "type": "property_declaration" }
    ]
  },
  {
    "type": "expression",
    "subtypes": [
      { "type": "call_expression" },
      { "type": "postfix_expression" }
    ]
  }
]
```

### 10.2 处理过程

1. **提取语义分类**:

   ```python
   semantic_categories = {
       "declaration": ["function_declaration", "class_declaration", "property_declaration"],
       "expression": ["call_expression", "postfix_expression"]
   }
   ```

2. **分类节点类型**:

   - `function_declaration` → functions（包含 "function"）
   - `class_declaration` → classes（包含 "class"）
   - `call_expression` → calls（包含 "call"）

3. **最终结果**:
   ```python
   NodeCategories(
       functions=["function_declaration"],
       classes=["class_declaration"],
       modules=["compilation_unit"],  # 从 root 节点添加
       calls=["call_expression"]
   )
   ```

## 11. 相关文档

- [第一部分：总览和入口流程](./01-overview-and-entry.md)
- [第二部分：Git 子模块添加流程](./02-git-submodule.md)
- [第三部分：语言信息检测流程](./03-language-detection.md)
- [第五部分：配置文件更新流程](./05-config-update.md)
- [第六部分：完整流程图](./06-flowcharts.md)
