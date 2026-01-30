# Language Grammar 添加流程详解 - 第五部分：配置文件更新流程

## 1. 配置文件更新概述

在完成语言信息检测和节点类型分析后，系统需要将新语言的配置添加到 `codebase_rag/language_spec.py` 文件中，使其在后续的代码解析中可用。

## 2. 核心函数：_update_config_file()

### 2.1 函数签名

**位置**: `codebase_rag/tools/language.py`

```python
def _update_config_file(
    language_name: str,      # 语言名称
    spec: LanguageSpec      # 语言配置对象
) -> bool:
```

### 2.2 执行流程

```python
def _update_config_file(language_name: str, spec: LanguageSpec) -> bool:
    # 步骤 1: 构建配置条目字符串
    config_entry = f"""    "{language_name}": LanguageSpec(
        language="{spec.language}",
        file_extensions={spec.file_extensions},
        function_node_types={spec.function_node_types},
        class_node_types={spec.class_node_types},
        module_node_types={spec.module_node_types},
        call_node_types={spec.call_node_types},
    ),"""

    try:
        # 步骤 2: 写入配置文件
        return _write_language_config(config_entry, language_name)
    except Exception as e:
        # 步骤 3: 错误处理
        logger.error(cs.LANG_ERR_UPDATE_CONFIG.format(error=e))
        click.echo(f"❌ {cs.LANG_ERR_UPDATE_CONFIG.format(error=e)}")
        click.echo(click.style(cs.LANG_FALLBACK_MANUAL_ADD, bold=True))
        click.echo(click.style(config_entry, fg=cs.Color.GREEN))
        return False
```

## 3. 配置条目格式

### 3.1 生成的配置条目示例

```python
    "kotlin": LanguageSpec(
        language="kotlin",
        file_extensions=(".kt", ".kts"),
        function_node_types=("function_declaration", "method_declaration"),
        class_node_types=("class_declaration", "interface_declaration"),
        module_node_types=("compilation_unit",),
        call_node_types=("call_expression",),
    ),
```

### 3.2 字段说明

- **`language`**: 语言名称（字符串）
- **`file_extensions`**: 文件扩展名元组
- **`function_node_types`**: 函数节点类型元组
- **`class_node_types`**: 类节点类型元组
- **`module_node_types`**: 模块节点类型元组
- **`call_node_types`**: 调用节点类型元组

## 4. 写入配置文件：_write_language_config()

### 4.1 函数签名

```python
def _write_language_config(
    config_entry: str,        # 配置条目字符串
    language_name: str       # 语言名称
) -> bool:
```

### 4.2 执行流程

```python
def _write_language_config(config_entry: str, language_name: str) -> bool:
    # 步骤 1: 读取现有配置文件
    config_content = pathlib.Path(cs.LANG_CONFIG_FILE).read_text()
    # cs.LANG_CONFIG_FILE = "codebase_rag/language_spec.py"

    # 步骤 2: 查找 LANGUAGE_SPECS 字典的结束位置
    closing_brace_pos = config_content.rfind("}")

    if closing_brace_pos == -1:
        raise ValueError(cs.LANG_ERR_CONFIG_NOT_FOUND)

    # 步骤 3: 在结束大括号前插入新配置
    new_content = (
        config_content[:closing_brace_pos]
        + config_entry
        + "\n"
        + config_content[closing_brace_pos:]
    )

    # 步骤 4: 写入文件
    with open(cs.LANG_CONFIG_FILE, "w") as f:
        f.write(new_content)

    # 步骤 5: 显示成功信息
    click.echo(f"✅ {cs.LANG_MSG_LANG_ADDED.format(name=language_name)}")
    click.echo(f"📝 {cs.LANG_MSG_UPDATED_CONFIG.format(path=cs.LANG_CONFIG_FILE)}")

    # 步骤 6: 显示审查提示
    _show_review_hints()
    return True
```

### 4.3 文件插入位置

**插入前**:
```python
LANGUAGE_SPECS = {
    "python": LanguageSpec(...),
    "java": LanguageSpec(...),
}  # ← 在这里插入
```

**插入后**:
```python
LANGUAGE_SPECS = {
    "python": LanguageSpec(...),
    "java": LanguageSpec(...),
    "kotlin": LanguageSpec(...),  # ← 新插入的配置
}
```

## 5. 审查提示：_show_review_hints()

### 5.1 函数签名

```python
def _show_review_hints() -> None:
```

### 5.2 执行流程

```python
def _show_review_hints() -> None:
    click.echo()

    # 步骤 1: 显示审查提示标题
    click.echo(
        click.style(f"📋 {cs.LANG_MSG_REVIEW_PROMPT}", bold=True, fg=cs.Color.YELLOW)
    )
    # 提示: "Please review the detected node types:"

    # 步骤 2: 显示审查说明
    click.echo(cs.LANG_MSG_REVIEW_HINT)
    # 提示: "   The auto-detection is good but may need manual adjustments."

    # 步骤 3: 显示编辑提示
    click.echo(cs.LANG_MSG_EDIT_HINT.format(path=cs.LANG_CONFIG_FILE))
    # 提示: "   Edit the configuration in: codebase_rag/language_spec.py"

    click.echo()

    # 步骤 4: 显示常见问题
    click.echo(f"🎯 {cs.LANG_MSG_COMMON_ISSUES}")
    click.echo(f"   • {cs.LANG_MSG_ISSUE_MISCLASSIFIED.strip()}")
    # 提示: "   - Remove misclassified types (e.g., table_constructor in functions)"
    click.echo(f"   • {cs.LANG_MSG_ISSUE_MISSING.strip()}")
    # 提示: "   - Add missing types that should be included"
    click.echo(f"   • {cs.LANG_MSG_ISSUE_CLASS_TYPES.strip()}")
    # 提示: "   - Verify class_node_types includes all relevant class-like constructs"
    click.echo(f"   • {cs.LANG_MSG_ISSUE_CALL_TYPES.strip()}")
    # 提示: "   - Check call_node_types covers all function call patterns"

    click.echo()

    # 步骤 5: 显示列表命令提示
    click.echo(f"💡 {cs.LANG_MSG_LIST_HINT}")
    # 提示: "You can run 'cgr language list-languages' to see the current config."
```

## 6. LanguageSpec 对象创建

### 6.1 在主流程中创建

```python
# 步骤 1: 收集所有信息
language_name = "kotlin"
file_extension = [".kt", ".kts"]
functions = ["function_declaration", "method_declaration"]
classes = ["class_declaration", "interface_declaration"]
modules = ["compilation_unit"]
calls = ["call_expression"]

# 步骤 2: 创建 LanguageSpec 对象
new_language_spec = LanguageSpec(
    language=language_name,
    file_extensions=tuple(file_extension),
    function_node_types=tuple(functions),
    class_node_types=tuple(classes),
    module_node_types=tuple(modules),
    call_node_types=tuple(calls),
)

# 步骤 3: 更新配置文件
_update_config_file(language_name, new_language_spec)
```

### 6.2 LanguageSpec 定义

**位置**: `codebase_rag/models.py`

```python
class LanguageSpec(BaseModel):
    language: SupportedLanguage | str
    file_extensions: tuple[str, ...]
    function_node_types: tuple[str, ...]
    class_node_types: tuple[str, ...]
    module_node_types: tuple[str, ...]
    call_node_types: tuple[str, ...]
    import_node_types: tuple[str, ...] = ()
    import_from_node_types: tuple[str, ...] = ()
    function_query: str | None = None
    class_query: str | None = None
    call_query: str | None = None
```

## 7. 配置文件结构

### 7.1 language_spec.py 文件结构

```python
from .models import LanguageSpec

LANGUAGE_SPECS: dict[str, LanguageSpec] = {
    "python": LanguageSpec(
        language="python",
        file_extensions=(".py",),
        function_node_types=("function_definition",),
        class_node_types=("class_definition",),
        module_node_types=("module",),
        call_node_types=("call",),
    ),
    "java": LanguageSpec(
        language="java",
        file_extensions=(".java",),
        function_node_types=("method_declaration", "constructor_declaration"),
        class_node_types=("class_declaration", "interface_declaration"),
        module_node_types=("program",),
        call_node_types=("method_invocation",),
    ),
    # ... 其他语言
    # 新添加的语言会插入到这里
}
```

### 7.2 插入位置查找

```python
# 查找最后一个 } 的位置
closing_brace_pos = config_content.rfind("}")

# 在 } 之前插入新配置
new_content = (
    config_content[:closing_brace_pos]  # 原有内容
    + config_entry                      # 新配置
    + "\n"                              # 换行
    + config_content[closing_brace_pos:]  # 结束大括号
)
```

## 8. 错误处理

### 8.1 配置文件不存在

```python
config_content = pathlib.Path(cs.LANG_CONFIG_FILE).read_text()
# 如果文件不存在，会抛出 FileNotFoundError
```

**处理**: 异常会被捕获，显示错误信息并提供手动添加提示

### 8.2 找不到结束大括号

```python
closing_brace_pos = config_content.rfind("}")

if closing_brace_pos == -1:
    raise ValueError(cs.LANG_ERR_CONFIG_NOT_FOUND)
```

**处理**: 抛出 `ValueError`，显示错误信息

### 8.3 写入失败

```python
with open(cs.LANG_CONFIG_FILE, "w") as f:
    f.write(new_content)
# 可能因为权限问题失败
```

**处理**: 异常会被捕获，显示错误信息并提供手动添加的配置内容

## 9. 手动添加提示

### 9.1 触发条件

当自动更新配置文件失败时，系统会显示手动添加提示。

### 9.2 提示内容

```
❌ Error updating config file: <error>
FALLBACK: Please manually add the following entry to 'LANGUAGE_SPECS' in 'codebase_rag/language_spec.py':

    "kotlin": LanguageSpec(
        language="kotlin",
        file_extensions=(".kt", ".kts"),
        function_node_types=("function_declaration", "method_declaration"),
        class_node_types=("class_declaration", "interface_declaration"),
        module_node_types=("compilation_unit",),
        call_node_types=("call_expression",),
    ),
```

## 10. 两种命令方式的配置更新

### 10.1 标准方式：`cgr language add-grammar kotlin`

```python
# 配置条目
config_entry = '''
    "kotlin": LanguageSpec(
        language="kotlin",
        file_extensions=(".kt", ".kts"),
        ...
    ),
'''

# 写入配置文件
_write_language_config(config_entry, "kotlin")
```

### 10.2 自定义方式：`cgr language add-grammar --grammar-url ...`

```python
# 配置条目（相同格式）
config_entry = '''
    "kotlin": LanguageSpec(
        language="kotlin",
        file_extensions=(".kt", ".kts"),
        ...
    ),
'''

# 写入配置文件（相同逻辑）
_write_language_config(config_entry, "kotlin")
```

**差异**: 两种方式的配置更新逻辑完全相同，差异仅在于语言名称的来源。

## 11. 配置验证

### 11.1 语法验证

写入的配置需要符合 Python 语法，系统通过以下方式确保：
- 使用正确的缩进（4 个空格）
- 使用正确的引号（双引号）
- 元组格式正确

### 11.2 导入验证

配置写入后，下次导入 `language_spec.py` 时会自动验证：
- `LanguageSpec` 类是否可导入
- 配置是否符合 `LanguageSpec` 模型定义

## 12. 配置使用

### 12.1 在解析器加载时使用

**位置**: `codebase_rag/parser_loader.py`

```python
def load_parsers():
    for lang_key, lang_config in LANGUAGE_SPECS.items():
        # 使用配置创建解析器
        language = Language(lang_lib())
        parser = Parser(language)
        queries = _create_language_queries(language, parser, lang_config, lang_name)
```

### 12.2 在文件识别时使用

**位置**: `codebase_rag/language_spec.py`

```python
def get_language_spec(file_extension: str) -> LanguageSpec | None:
    return _EXTENSION_TO_SPEC.get(file_extension)
```

## 13. 相关文档

- [第一部分：总览和入口流程](./01-overview-and-entry.md)
- [第二部分：Git 子模块添加流程](./02-git-submodule.md)
- [第三部分：语言信息检测流程](./03-language-detection.md)
- [第四部分：节点类型分析流程](./04-node-types-analysis.md)
- [第六部分：完整流程图](./06-flowcharts.md)
