# Language Grammar 添加流程详解 - 第二部分：Git 子模块添加流程

## 1. Git 子模块添加概述

Git 子模块是 code-graph-rag 管理 tree-sitter 语法库的方式。每个添加的语言都会作为 Git 子模块存储在 `grammars/` 目录下。

## 2. 核心函数：_add_git_submodule()

### 2.1 函数签名

**位置**: `codebase_rag/tools/language.py`

```python
def _add_git_submodule(
    grammar_url: str,      # 语法库 Git URL
    grammar_path: str      # 本地存储路径
) -> SubmoduleResult | None:
```

### 2.2 执行流程

```python
def _add_git_submodule(grammar_url: str, grammar_path: str) -> SubmoduleResult | None:
    try:
        # 步骤 1: 显示添加信息
        click.echo(f"🔄 {cs.LANG_MSG_ADDING_SUBMODULE.format(url=grammar_url)}")

        # 步骤 2: 执行 git submodule add 命令
        subprocess.run(
            ["git", "submodule", "add", grammar_url, grammar_path],
            check=True,                    # 检查返回码
            capture_output=True,           # 捕获输出
            text=True,                     # 文本模式
        )

        # 步骤 3: 显示成功信息
        click.echo(f"✅ {cs.LANG_MSG_SUBMODULE_SUCCESS.format(path=grammar_path)}")

        # 步骤 4: 返回成功结果
        return SubmoduleResult(success=True, grammar_path=grammar_path)

    except subprocess.CalledProcessError as e:
        # 步骤 5: 处理错误
        return _handle_submodule_error(e, grammar_url, grammar_path)
```

### 2.3 Git 命令详解

**执行的命令**:
```bash
git submodule add <grammar_url> <grammar_path>
```

**示例**:
```bash
# 标准方式
git submodule add https://github.com/tree-sitter/tree-sitter-kotlin grammars/tree-sitter-kotlin

# 自定义方式
git submodule add https://github.com/CliffLeopard/tree-sitter-kotlin.git grammars/tree-sitter-kotlin
```

**命令效果**:
1. 克隆远程仓库到指定路径
2. 在 `.gitmodules` 文件中添加子模块配置
3. 在 `.git/config` 中添加子模块配置
4. 创建 `.git/modules/grammars/tree-sitter-kotlin/` 目录

## 3. 错误处理：_handle_submodule_error()

### 3.1 函数签名

```python
def _handle_submodule_error(
    error: subprocess.CalledProcessError,
    grammar_url: str,
    grammar_path: str
) -> SubmoduleResult | None:
```

### 3.2 错误类型判断

```python
def _handle_submodule_error(...) -> SubmoduleResult | None:
    error_output = error.stderr or str(error)

    # 情况 1: 子模块已存在
    if "already exists in the index" in error_output:
        return _reinstall_existing_submodule(grammar_url, grammar_path)

    # 情况 2: 仓库不存在
    if "does not exist" in error_output or "not found" in error_output:
        logger.error(cs.LANG_ERR_REPO_NOT_FOUND.format(url=grammar_url))
        click.echo(f"❌ {cs.LANG_ERR_REPO_NOT_FOUND.format(url=grammar_url)}")
        click.echo(f"💡 {cs.LANG_ERR_CUSTOM_URL_HINT}")
        return None

    # 情况 3: 其他 Git 错误
    logger.error(cs.LANG_ERR_GIT.format(error=error_output))
    click.echo(f"❌ {cs.LANG_ERR_GIT.format(error=error_output)}")
    raise error
```

## 4. 重新安装已存在的子模块：_reinstall_existing_submodule()

### 4.1 函数签名

```python
def _reinstall_existing_submodule(
    grammar_url: str,
    grammar_path: str
) -> SubmoduleResult | None:
```

### 4.2 执行流程

```python
def _reinstall_existing_submodule(...) -> SubmoduleResult | None:
    # 步骤 1: 显示警告
    click.secho(
        f"⚠️  {cs.LANG_MSG_SUBMODULE_EXISTS.format(path=grammar_path)}",
        fg=cs.Color.YELLOW,
    )

    try:
        # 步骤 2: 取消初始化子模块
        click.echo(cs.LANG_MSG_REMOVING_ENTRY)
        subprocess.run(
            ["git", "submodule", "deinit", "-f", grammar_path],
            check=True,
            capture_output=True,
            text=True,
        )

        # 步骤 3: 从 Git 索引中移除
        subprocess.run(
            ["git", "rm", "-f", grammar_path],
            check=True,
            capture_output=True,
            text=True,
        )

        # 步骤 4: 清理 .git/modules 目录
        modules_path = cs.LANG_GIT_MODULES_PATH.format(path=grammar_path)
        # 例如: .git/modules/grammars/tree-sitter-kotlin
        if os.path.exists(modules_path):
            shutil.rmtree(modules_path)

        # 步骤 5: 重新添加子模块（使用 --force）
        click.echo(cs.LANG_MSG_READDING_SUBMODULE)
        subprocess.run(
            ["git", "submodule", "add", "--force", grammar_url, grammar_path],
            check=True,
            capture_output=True,
            text=True,
        )

        # 步骤 6: 显示成功信息
        click.echo(f"✅ {cs.LANG_MSG_REINSTALL_SUCCESS.format(path=grammar_path)}")
        return SubmoduleResult(success=True, grammar_path=grammar_path)

    except (subprocess.CalledProcessError, OSError) as reinstall_e:
        # 步骤 7: 处理重新安装失败
        return _handle_reinstall_failure(reinstall_e, grammar_path)
```

### 4.3 Git 命令序列

**重新安装过程执行的命令**:
```bash
# 1. 取消初始化
git submodule deinit -f grammars/tree-sitter-kotlin

# 2. 从索引移除
git rm -f grammars/tree-sitter-kotlin

# 3. 删除 .git/modules 目录（手动）
rm -rf .git/modules/grammars/tree-sitter-kotlin

# 4. 强制重新添加
git submodule add --force https://github.com/... grammars/tree-sitter-kotlin
```

## 5. 重新安装失败处理：_handle_reinstall_failure()

### 5.1 函数签名

```python
def _handle_reinstall_failure(
    error: subprocess.CalledProcessError | OSError,
    grammar_path: str
) -> None:
```

### 5.2 执行流程

```python
def _handle_reinstall_failure(...) -> None:
    error_msg = error.stderr if hasattr(error, "stderr") else str(error)

    # 记录错误
    logger.error(cs.LANG_ERR_REINSTALL_FAILED.format(error=error_msg))
    click.secho(
        f"❌ {cs.LANG_ERR_REINSTALL_FAILED.format(error=error_msg)}",
        fg=cs.Color.RED,
    )

    # 提供手动操作提示
    click.echo(f"💡 {cs.LANG_ERR_MANUAL_REMOVE_HINT}")
    click.echo(f"   git submodule deinit -f {grammar_path}")
    click.echo(f"   git rm -f {grammar_path}")
    click.echo(f"   rm -rf {cs.LANG_GIT_MODULES_PATH.format(path=grammar_path)}")
```

## 6. 子模块数据结构

### 6.1 SubmoduleResult

```python
@dataclass
class SubmoduleResult:
    success: bool          # 操作是否成功
    grammar_path: str      # 语法库的本地路径
```

**使用场景**:
- 返回给调用者表示操作结果
- 后续步骤使用 `grammar_path` 访问语法库文件

## 7. 文件系统结构

### 7.1 添加后的目录结构

```
项目根目录/
├── grammars/
│   └── tree-sitter-kotlin/          # 子模块目录
│       ├── src/                      # 语法源文件
│       ├── bindings/                 # 绑定文件
│       ├── tree-sitter.json          # 语法配置
│       ├── node-types.json           # 节点类型定义
│       └── ...
├── .git/
│   ├── modules/
│   │   └── grammars/
│   │       └── tree-sitter-kotlin/   # Git 子模块元数据
│   └── config                        # 包含子模块配置
└── .gitmodules                       # 子模块列表文件
```

### 7.2 .gitmodules 文件内容

```ini
[submodule "grammars/tree-sitter-kotlin"]
    path = grammars/tree-sitter-kotlin
    url = https://github.com/tree-sitter/tree-sitter-kotlin
```

## 8. 两种命令方式的子模块添加

### 8.1 标准方式：`cgr language add-grammar kotlin`

```python
grammar_url = "https://github.com/tree-sitter/tree-sitter-kotlin"
grammar_path = "grammars/tree-sitter-kotlin"

# 执行
git submodule add https://github.com/tree-sitter/tree-sitter-kotlin grammars/tree-sitter-kotlin
```

### 8.2 自定义方式：`cgr language add-grammar --grammar-url https://github.com/CliffLeopard/tree-sitter-kotlin.git`

```python
grammar_url = "https://github.com/CliffLeopard/tree-sitter-kotlin.git"
grammar_path = "grammars/tree-sitter-kotlin"

# 执行
git submodule add https://github.com/CliffLeopard/tree-sitter-kotlin.git grammars/tree-sitter-kotlin
```

**差异**:
- URL 来源不同（官方 vs 自定义）
- 自定义 URL 需要用户确认
- 最终存储路径相同（基于仓库名）

## 9. 错误场景处理

### 9.1 子模块已存在

**错误信息**: `"already exists in the index"`

**处理**:
1. 取消初始化现有子模块
2. 从 Git 索引移除
3. 清理元数据
4. 强制重新添加

### 9.2 仓库不存在

**错误信息**: `"does not exist"` 或 `"not found"`

**处理**:
1. 显示错误信息
2. 提示使用自定义 URL
3. 返回 None，终止流程

### 9.3 其他 Git 错误

**处理**:
1. 记录错误日志
2. 显示错误信息
3. 抛出异常

## 10. 相关文档

- [第一部分：总览和入口流程](./01-overview-and-entry.md)
- [第三部分：语言信息检测流程](./03-language-detection.md)
- [第四部分：节点类型分析流程](./04-node-types-analysis.md)
- [第五部分：配置文件更新流程](./05-config-update.md)
- [第六部分：完整流程图](./06-flowcharts.md)
