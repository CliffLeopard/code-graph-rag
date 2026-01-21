# Language Grammar 添加流程详解 - 第三部分：语言信息检测流程

## 1. 语言信息检测概述

在添加语法库后，系统需要检测语言的基本信息：
- 语言名称
- 文件扩展名列表

这些信息可以从 `tree-sitter.json` 文件自动提取，如果无法提取则提示用户输入。

## 2. 核心函数：_parse_tree_sitter_json()

### 2.1 函数签名

**位置**: `codebase_rag/tools/language.py`

```python
def _parse_tree_sitter_json(
    json_path: str,              # tree-sitter.json 文件路径
    grammar_dir_name: str,       # 语法库目录名
    language_name: str | None    # 用户提供的语言名（可选）
) -> LanguageInfo | None:
```

### 2.2 执行流程

```python
def _parse_tree_sitter_json(...) -> LanguageInfo | None:
    # 步骤 1: 检查文件是否存在
    if not os.path.exists(json_path):
        return None

    # 步骤 2: 读取 JSON 文件
    with open(json_path) as f:
        config = json.load(f)

    # 步骤 3: 验证 grammars 字段
    if "grammars" not in config or len(config["grammars"]) == 0:
        return None

    # 步骤 4: 获取第一个语法配置
    grammar_info = config["grammars"][0]

    # 步骤 5: 提取语言名称
    detected_name = grammar_info.get("name", grammar_dir_name)

    # 步骤 6: 提取文件扩展名
    raw_extensions = grammar_info.get("file-types", [])
    extensions = [
        ext if ext.startswith(".") else f".{ext}"
        for ext in raw_extensions
    ]

    # 步骤 7: 确定最终语言名称
    name = language_name or detected_name

    # 步骤 8: 显示检测结果
    click.echo(cs.LANG_MSG_AUTO_DETECTED_LANG.format(name=detected_name))
    click.echo(cs.LANG_MSG_USING_LANG_NAME.format(name=name))
    click.echo(cs.LANG_MSG_AUTO_DETECTED_EXT.format(extensions=extensions))

    # 步骤 9: 返回语言信息
    return LanguageInfo(name=name, extensions=extensions)
```

## 3. tree-sitter.json 文件格式

### 3.1 标准格式

```json
{
  "grammars": [
    {
      "name": "kotlin",
      "file-types": ["kt", "kts"],
      "scope": "source.kotlin"
    }
  ]
}
```

### 3.2 字段说明

- **`grammars`**: 语法配置数组（通常只有一个元素）
- **`name`**: 语言名称（如 "kotlin", "java", "python"）
- **`file-types`**: 文件扩展名列表（不含点号）
- **`scope`**: 文本编辑器作用域（可选）

### 3.3 文件位置

```
grammars/tree-sitter-kotlin/
└── tree-sitter.json    # 语法配置文件
```

## 4. 语言名称确定逻辑

### 4.1 优先级顺序

1. **用户提供的语言名** (`language_name` 参数)
2. **tree-sitter.json 中的 name 字段**
3. **语法库目录名** (`grammar_dir_name`)

### 4.2 示例

```python
# 情况 1: 用户提供语言名
language_name = "kotlin"
detected_name = "kotlin"  # 从 tree-sitter.json
# 最终使用: "kotlin" (用户提供优先)

# 情况 2: 用户未提供，使用检测到的名称
language_name = None
detected_name = "kotlin"  # 从 tree-sitter.json
# 最终使用: "kotlin" (检测到的名称)

# 情况 3: tree-sitter.json 中没有 name
language_name = None
detected_name = None
grammar_dir_name = "tree-sitter-kotlin"
# 最终使用: "tree-sitter-kotlin" (目录名)
```

## 5. 文件扩展名处理

### 5.1 扩展名规范化

```python
raw_extensions = grammar_info.get("file-types", [])
# 例如: ["kt", "kts"]

extensions = [
    ext if ext.startswith(".") else f".{ext}"
    for ext in raw_extensions
]
# 结果: [".kt", ".kts"]
```

### 5.2 处理逻辑

- **已有点号**: 直接使用（如 `".kt"` → `".kt"`）
- **无点号**: 添加点号（如 `"kt"` → `".kt"`）

### 5.3 示例

```python
# 输入: ["kt", "kts", ".kt"]
# 输出: [".kt", ".kts", ".kt"]
```

## 6. 手动输入：_prompt_for_language_info()

### 6.1 触发条件

当 `_parse_tree_sitter_json()` 返回 `None` 时触发，可能原因：
- `tree-sitter.json` 文件不存在
- `grammars` 字段缺失或为空
- JSON 解析失败

### 6.2 函数签名

```python
def _prompt_for_language_info(
    language_name: str | None
) -> LanguageInfo:
```

### 6.3 执行流程

```python
def _prompt_for_language_info(language_name: str | None) -> LanguageInfo:
    # 步骤 1: 提示输入语言名称
    if not language_name:
        language_name = click.prompt(cs.LANG_PROMPT_COMMON_NAME)
        # 提示: "What is the common name for this language?"

    # 步骤 2: 提示输入文件扩展名
    extensions = [
        ext.strip()
        for ext in click.prompt(cs.LANG_PROMPT_EXTENSIONS).split(",")
    ]
    # 提示: "What file extensions should be associated with this language? (comma-separated)"
    # 用户输入: "kt, kts"
    # 结果: ["kt", "kts"]

    # 步骤 3: 返回语言信息
    return LanguageInfo(name=language_name, extensions=extensions)
```

### 6.4 用户交互示例

```
Warning: tree-sitter.json not found in grammars/tree-sitter-kotlin
What is the common name for this language? kotlin
What file extensions should be associated with this language? (comma-separated) kt, kts
```

## 7. LanguageInfo 数据结构

### 7.1 定义

```python
class LanguageInfo(NamedTuple):
    name: str              # 语言名称
    extensions: list[str]  # 文件扩展名列表
```

### 7.2 使用示例

```python
lang_info = LanguageInfo(
    name="kotlin",
    extensions=[".kt", ".kts"]
)
```

## 8. 两种命令方式的检测差异

### 8.1 标准方式：`cgr language add-grammar kotlin`

```python
# 初始参数
language_name = "kotlin"
grammar_url = "https://github.com/tree-sitter/tree-sitter-kotlin"

# 检测流程
tree_sitter_json_path = "grammars/tree-sitter-kotlin/tree-sitter.json"

# 如果 tree-sitter.json 存在
lang_info = _parse_tree_sitter_json(
    tree_sitter_json_path,
    "tree-sitter-kotlin",
    "kotlin"
)
# 结果: LanguageInfo(name="kotlin", extensions=[".kt", ".kts"])
```

### 8.2 自定义方式：`cgr language add-grammar --grammar-url https://github.com/CliffLeopard/tree-sitter-kotlin.git`

```python
# 初始参数
language_name = None  # 未提供
grammar_url = "https://github.com/CliffLeopard/tree-sitter-kotlin.git"

# 检测流程
tree_sitter_json_path = "grammars/tree-sitter-kotlin/tree-sitter.json"

# 如果 tree-sitter.json 存在
lang_info = _parse_tree_sitter_json(
    tree_sitter_json_path,
    "tree-sitter-kotlin",
    None  # 需要从 JSON 检测
)
# 结果: LanguageInfo(name="kotlin", extensions=[".kt", ".kts"])
# 或: LanguageInfo(name="tree-sitter-kotlin", extensions=[...])
```

## 9. 错误处理

### 9.1 文件不存在

```python
if not os.path.exists(json_path):
    return None
```

**处理**: 返回 `None`，触发手动输入流程

### 9.2 JSON 格式错误

```python
with open(json_path) as f:
    config = json.load(f)  # 可能抛出 JSONDecodeError
```

**处理**: 异常会被捕获，返回 `None`，触发手动输入

### 9.3 grammars 字段缺失

```python
if "grammars" not in config or len(config["grammars"]) == 0:
    return None
```

**处理**: 返回 `None`，触发手动输入流程

## 10. 检测结果使用

### 10.1 在主流程中的使用

```python
if lang_info := _parse_tree_sitter_json(
    tree_sitter_json_path, grammar_dir_name, language_name
):
    # 自动检测成功
    language_name = lang_info.name
    file_extension = lang_info.extensions
else:
    # 自动检测失败，手动输入
    click.echo(cs.LANG_ERR_TREE_SITTER_JSON_WARNING.format(path=grammar_path))
    info = _prompt_for_language_info(language_name)
    language_name = info.name
    file_extension = info.extensions
```

### 10.2 后续使用

检测到的语言信息用于：
1. 创建 `LanguageSpec` 对象
2. 更新配置文件
3. 在解析时识别文件类型

## 11. 相关文档

- [第一部分：总览和入口流程](./01-overview-and-entry.md)
- [第二部分：Git 子模块添加流程](./02-git-submodule.md)
- [第四部分：节点类型分析流程](./04-node-types-analysis.md)
- [第五部分：配置文件更新流程](./05-config-update.md)
- [第六部分：完整流程图](./06-flowcharts.md)
