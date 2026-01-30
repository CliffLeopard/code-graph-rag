# Language Grammar 添加流程详解 - 第一部分：总览和入口流程

## 1. 命令概述

`cgr language add-grammar` 命令用于向 code-graph-rag 添加新的编程语言支持。该命令支持两种使用方式：

### 1.1 标准语法库方式

```bash
cgr language add-grammar kotlin
```

**执行的操作**：

- 使用默认的 tree-sitter 语法库 URL
- 自动构建语法库路径
- 从官方 tree-sitter 组织获取语法

### 1.2 自定义语法库方式

```bash
cgr language add-grammar --grammar-url https://github.com/CliffLeopard/tree-sitter-kotlin.git
```

**执行的操作**：

- 使用用户提供的自定义语法库 URL
- 支持任意 GitHub 仓库
- 需要用户确认（安全提示）

## 2. 命令入口

### 2.1 CLI 路由

**位置**: `codebase_rag/cli.py`

```python
@app.command(
    name=ch.CLICommandName.LANGUAGE,
    help=ch.CMD_LANGUAGE,
    context_settings={"allow_extra_args": True, "allow_interspersed_args": False},
)
def language_command(ctx: typer.Context) -> None:
    language_cli(ctx.args, standalone_mode=False)
```

### 2.2 Language CLI 入口

**位置**: `codebase_rag/tools/language.py`

```python
@click.group(help=ch.CMD_LANGUAGE_GROUP)
def cli() -> None:
    pass

@cli.command(help=ch.CMD_LANGUAGE_ADD)
@click.argument("language_name", required=False)
@click.option("--grammar-url", help=ch.HELP_GRAMMAR_URL)
def add_grammar(
    language_name: str | None = None,
    grammar_url: str | None = None
) -> None:
```

## 3. 主执行流程

### 3.1 参数验证和 URL 构建

```python
def add_grammar(language_name, grammar_url):
    # 步骤 1: 参数验证
    if not language_name and not grammar_url:
        language_name = click.prompt(cs.LANG_PROMPT_LANGUAGE_NAME)

    # 步骤 2: 构建语法库 URL
    if not grammar_url:
        if not language_name:
            click.echo(f"❌ {cs.LANG_ERR_MISSING_ARGS}")
            return
        # 使用默认 URL 模板
        grammar_url = cs.LANG_DEFAULT_GRAMMAR_URL.format(name=language_name)
        # 例如: https://github.com/tree-sitter/tree-sitter-kotlin
        click.echo(f"🔍 {cs.LANG_MSG_USING_DEFAULT_URL.format(url=grammar_url)}")
```

### 3.2 自定义 URL 安全提示

```python
    # 步骤 3: 自定义 URL 安全检查
    if grammar_url and cs.LANG_TREE_SITTER_URL_MARKER not in grammar_url:
        # 如果不是官方 tree-sitter URL，显示警告
        click.secho(
            f"⚠️ {cs.LANG_MSG_CUSTOM_URL_WARNING}",
            fg=cs.Color.YELLOW,
            bold=True,
        )
        if not click.confirm(cs.LANG_PROMPT_CONTINUE):
            return
```

### 3.3 目录准备

```python
    # 步骤 4: 创建 grammars 目录（如果不存在）
    if not os.path.exists(cs.LANG_GRAMMARS_DIR):
        os.makedirs(cs.LANG_GRAMMARS_DIR)
    # cs.LANG_GRAMMARS_DIR = "grammars"
```

### 3.4 路径计算

```python
    # 步骤 5: 计算语法库目录名和路径
    grammar_dir_name = os.path.basename(grammar_url).removesuffix(cs.LANG_GIT_SUFFIX)
    # 例如: https://github.com/CliffLeopard/tree-sitter-kotlin.git
    #      -> tree-sitter-kotlin

    grammar_path = os.path.join(cs.LANG_GRAMMARS_DIR, grammar_dir_name)
    # 例如: grammars/tree-sitter-kotlin
```

## 4. 核心执行步骤

### 4.1 添加 Git 子模块

```python
    # 步骤 6: 添加 Git 子模块
    result = _add_git_submodule(grammar_url, grammar_path)
    if result is None:
        return
```

**详细流程见**: [第二部分：Git 子模块添加流程](./02-git-submodule.md)

### 4.2 解析语言信息

```python
    # 步骤 7: 解析 tree-sitter.json 获取语言信息
    tree_sitter_json_path = os.path.join(grammar_path, cs.LANG_TREE_SITTER_JSON)

    if lang_info := _parse_tree_sitter_json(
        tree_sitter_json_path, grammar_dir_name, language_name
    ):
        language_name = lang_info.name
        file_extension = lang_info.extensions
    else:
        # 如果无法自动检测，提示用户输入
        click.echo(cs.LANG_ERR_TREE_SITTER_JSON_WARNING.format(path=grammar_path))
        info = _prompt_for_language_info(language_name)
        language_name = info.name
        file_extension = info.extensions
```

**详细流程见**: [第三部分：语言信息检测流程](./03-language-detection.md)

### 4.3 分析节点类型

```python
    # 步骤 8: 查找并分析 node-types.json
    assert language_name is not None

    if node_types_path := _find_node_types_path(grammar_path, language_name):
        if categories := _parse_node_types_file(node_types_path):
            functions = categories.functions
            classes = categories.classes
            modules = categories.modules
            calls = categories.calls
        else:
            # 使用默认值
            functions = [cs.LANG_FALLBACK_METHOD_NODE]
            classes = list(cs.LANG_DEFAULT_CLASS_NODES)
            modules = list(cs.LANG_DEFAULT_MODULE_NODES)
            calls = list(cs.LANG_DEFAULT_CALL_NODES)
    else:
        # 如果找不到 node-types.json，提示用户输入
        click.echo(cs.LANG_ERR_NODE_TYPES_WARNING.format(name=language_name))
        categories = _prompt_for_node_categories()
        functions = categories.functions
        classes = categories.classes
        modules = categories.modules
        calls = categories.calls
```

**详细流程见**: [第四部分：节点类型分析流程](./04-node-types-analysis.md)

### 4.4 创建语言配置

```python
    # 步骤 9: 创建 LanguageSpec 对象
    new_language_spec = LanguageSpec(
        language=language_name,
        file_extensions=tuple(file_extension),
        function_node_types=tuple(functions),
        class_node_types=tuple(classes),
        module_node_types=tuple(modules),
        call_node_types=tuple(calls),
    )
```

### 4.5 更新配置文件

```python
    # 步骤 10: 更新 language_spec.py 配置文件
    _update_config_file(language_name, new_language_spec)
```

**详细流程见**: [第五部分：配置文件更新流程](./05-config-update.md)

## 5. 关键数据结构

### 5.1 SubmoduleResult

**位置**: `codebase_rag/tools/language.py`

```python
@dataclass
class SubmoduleResult:
    success: bool          # 是否成功
    grammar_path: str      # 语法库路径
```

### 5.2 LanguageInfo

```python
class LanguageInfo(NamedTuple):
    name: str              # 语言名称
    extensions: list[str]  # 文件扩展名列表
```

### 5.3 NodeCategories

```python
class NodeCategories(NamedTuple):
    functions: list[str]   # 函数节点类型
    classes: list[str]     # 类节点类型
    modules: list[str]     # 模块节点类型
    calls: list[str]       # 调用节点类型
```

### 5.4 LanguageSpec

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

## 6. 关键常量

### 6.1 路径常量

```python
LANG_GRAMMARS_DIR = "grammars"
LANG_CONFIG_FILE = "codebase_rag/language_spec.py"
LANG_TREE_SITTER_JSON = "tree-sitter.json"
LANG_NODE_TYPES_JSON = "node-types.json"
LANG_SRC_DIR = "src"
```

### 6.2 URL 常量

```python
LANG_DEFAULT_GRAMMAR_URL = "https://github.com/tree-sitter/tree-sitter-{name}"
LANG_TREE_SITTER_URL_MARKER = "github.com/tree-sitter/tree-sitter"
LANG_GIT_SUFFIX = ".git"
```

### 6.3 默认节点类型

```python
LANG_DEFAULT_FUNCTION_NODES = ("function_definition", "method_definition")
LANG_DEFAULT_CLASS_NODES = ("class_declaration",)
LANG_DEFAULT_MODULE_NODES = ("compilation_unit",)
LANG_DEFAULT_CALL_NODES = ("invocation_expression",)
LANG_FALLBACK_METHOD_NODE = "method_declaration"
```

## 7. 两种命令方式的差异

### 7.1 `cgr language add-grammar kotlin`

**流程**：

1. 使用默认 URL: `https://github.com/tree-sitter/tree-sitter-kotlin`
2. 无需安全确认（官方 URL）
3. 自动检测语言名称为 "kotlin"

### 7.2 `cgr language add-grammar --grammar-url https://github.com/CliffLeopard/tree-sitter-kotlin.git`

**流程**：

1. 使用自定义 URL
2. **需要安全确认**（显示警告提示）
3. 从 URL 提取语言名称或从 tree-sitter.json 检测

## 8. 执行流程图概览

```
命令入口
  ↓
参数验证
  ├─→ 无参数 → 提示输入语言名
  └─→ 有参数 → 继续
  ↓
URL 构建
  ├─→ 无 grammar_url → 构建默认 URL
  └─→ 有 grammar_url → 使用自定义 URL
  ↓
安全检查（自定义 URL）
  ↓
目录准备
  ↓
添加 Git 子模块
  ↓
解析语言信息
  ↓
分析节点类型
  ↓
创建 LanguageSpec
  ↓
更新配置文件
  ↓
完成
```

## 9. 相关文档

- [第二部分：Git 子模块添加流程](./02-git-submodule.md)
- [第三部分：语言信息检测流程](./03-language-detection.md)
- [第四部分：节点类型分析流程](./04-node-types-analysis.md)
- [第五部分：配置文件更新流程](./05-config-update.md)
- [第六部分：完整流程图](./06-flowcharts.md)
