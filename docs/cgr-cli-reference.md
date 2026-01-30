# cgr 命令行参考

本文档描述当前项目中 **cgr**（Codebase Graph RAG）命令可用的所有参数、参数值及含义。
cgr 与 **graph-code** 为同一入口的两种名称（见 `pyproject.toml` 中的 `project.scripts`）。

---

## 1. 命令入口与全局选项

### 1.1 调用方式

```bash
cgr <命令> [选项...]
# 或
uv run cgr <命令> [选项...]
```

### 1.2 全局选项（所有命令前均可使用）

| 选项 | 简写 | 类型 | 默认值 | 含义 |
|------|------|------|--------|------|
| `--quiet` | `-q` | 布尔 | `false` | 静默模式：抑制非必要输出（进度、横幅、信息日志），仅保留错误。 |

示例：

```bash
cgr -q start --repo-path /path/to/repo
cgr --quiet export -o graph.json
```

---

## 2. 命令一览

| 命令 | 说明 |
|------|------|
| **start** | 启动与代码库的交互式对话；可选先更新图并导出。 |
| **index** | 将代码库索引为 protobuf 文件，供离线使用。 |
| **export** | 从 Memgraph 导出知识图到 JSON 文件。 |
| **optimize** | 在指定语言下启动 AI 引导的代码库优化会话。 |
| **mcp-server** | 启动 MCP 服务，供 Claude Code 等集成。 |
| **graph-loader** | 加载并显示已导出的图 JSON 摘要。 |
| **language** | 管理语言语法（添加、删除、列表、清理）。 |

---

## 3. start

**说明**：启动与代码库的交互式 RAG 对话；若指定 `--update-graph`，会先解析仓库并更新 Memgraph 中的知识图；可选更新后导出为 JSON。

### 3.1 参数与选项

| 选项 / 参数 | 简写 | 类型 | 默认值 | 含义 |
|-------------|------|------|--------|------|
| `--repo-path` | — | 字符串 | `TARGET_REPO_PATH` 或 `.` | 目标代码库路径，用于检索与（可选）更新图。 |
| `--update-graph` | — | 布尔 | `false` | 在启动对话前，先解析仓库并更新知识图。 |
| `--clean` | — | 布尔 | `false` | 更新图前先清空数据库（例如首次导入仓库时使用）。 |
| `--output` | `-o` | 字符串 | — | 更新图后将图导出到该 JSON 文件路径；**必须与 `--update-graph` 同时使用**。 |
| `--orchestrator` | — | 字符串 | 环境/配置 | 主模型，格式：`provider:model`（如 `ollama:llama3.2`、`openai:gpt-4`、`google:gemini-2.5-pro`）。 |
| `--cypher` | — | 字符串 | 环境/配置 | Cypher 生成用模型，格式：`provider:model`（如 `ollama:codellama`、`google:gemini-2.5-flash`）。 |
| `--no-confirm` | — | 布尔 | `false` | 关闭编辑类操作前的确认提示（“YOLO 模式”）。 |
| `--batch-size` | — | 整数 | `MEMGRAPH_BATCH_SIZE`（默认 1000） | 写入 Memgraph 前缓冲的节点/关系数量，须 ≥ 1。 |
| `--exclude` | — | 列表（可多次） | — | 额外要排除的目录/模式，与 `.cgrignore` 合并；可多次指定。 |
| `--interactive-setup` | — | 布尔 | `false` | 以交互方式选择要保留/排除的目录；未指定时按忽略规则自动排除。 |

### 3.2 约束与说明

- 仅当传入 `--update-graph` 时，`--output` / `-o` 才有效；否则会报错并退出。
- `--clean` 仅在 `--update-graph` 时生效，用于“先清库再全量建图”。

### 3.3 示例

```bash
# 仅启动对话（使用当前目录或 TARGET_REPO_PATH）
cgr start

# 指定仓库并更新图
cgr start --repo-path /path/to/repo --update-graph

# 清空库、更新图并导出 JSON
cgr start --repo-path /path/to/repo --update-graph --clean -o graph.json

# 使用指定模型并排除若干目录
cgr start --repo-path . --update-graph --orchestrator openai:gpt-4 --cypher google:gemini-2.5-flash --exclude node_modules --exclude .git
```

---

## 4. index

**说明**：将代码库解析并索引为 protobuf 文件（单文件或拆分为 nodes/relationships），供离线使用。

### 4.1 参数与选项

| 选项 / 参数 | 简写 | 类型 | 默认值 | 含义 |
|-------------|------|------|--------|------|
| `--repo-path` | — | 字符串 | `TARGET_REPO_PATH` 或 `.` | 要索引的代码库路径。 |
| `--output-proto-dir` | `-o` | 字符串 | **必填** | 输出 protobuf 索引的目录路径。 |
| `--split-index` | — | 布尔 | `false` | 将索引拆分为 `nodes.bin` 与 `relationships.bin` 写入。 |
| `--exclude` | — | 列表（可多次） | — | 额外排除的目录/模式，可多次指定。 |
| `--interactive-setup` | — | 布尔 | `false` | 交互式选择要保留/排除的目录。 |

### 4.2 示例

```bash
cgr index -o ./proto_index
cgr index --repo-path /path/to/repo -o ./out --split-index
```

---

## 5. export

**说明**：从已运行的 Memgraph 导出当前知识图到 JSON 文件。

### 5.1 参数与选项

| 选项 / 参数 | 简写 | 类型 | 默认值 | 含义 |
|-------------|------|------|--------|------|
| `--output` | `-o` | 字符串 | **必填** | 导出 JSON 的文件路径。 |
| `--json` / `--no-json` | — | 布尔 | `true`（JSON） | 当前仅支持 JSON；`--no-json` 会报错退出。 |
| `--batch-size` | — | 整数 | 配置默认值 | 与 Memgraph 交互时的批大小，≥ 1。 |

### 5.2 示例

```bash
cgr export -o graph.json
cgr export --output ./my_graph.json --batch-size 2000
```

---

## 6. optimize

**说明**：针对指定编程语言，启动 AI 引导的代码库优化会话（需连接 Memgraph 与配置好的模型）。

### 6.1 参数与选项

| 选项 / 参数 | 简写 | 类型 | 默认值 | 含义 |
|-------------|------|------|--------|------|
| `language` | — | **位置参数** | **必填** | 优化目标语言，如：`python`、`java`、`javascript`、`typescript`、`cpp`、`rust`、`kotlin`、`go`、`scala`、`c-sharp`、`php`、`lua`。 |
| `--repo-path` | — | 字符串 | `TARGET_REPO_PATH` 或 `.` | 要优化的代码库路径。 |
| `--reference-document` | — | 字符串 | — | 参考文档/书籍路径，用于引导优化方向。 |
| `--orchestrator` | — | 字符串 | 环境/配置 | 主模型，格式：`provider:model`。 |
| `--cypher` | — | 字符串 | 环境/配置 | Cypher 模型，格式：`provider:model`。 |
| `--no-confirm` | — | 布尔 | `false` | 关闭编辑前的确认提示。 |
| `--batch-size` | — | 整数 | 配置默认值 | Memgraph 批大小，≥ 1。 |

### 6.2 支持的语言（与 `SupportedLanguage` 一致）

- **python**, **javascript**, **typescript**, **rust**, **go**, **scala**, **java**, **kotlin**, **cpp**, **c-sharp**, **php**, **lua**

### 6.3 示例

```bash
cgr optimize python --repo-path /path/to/repo
cgr optimize java --reference-document ./docs/style-guide.md --no-confirm
```

---

## 7. mcp-server

**说明**：启动 MCP（Model Context Protocol）服务，用于与 Claude Code 等客户端集成。

### 7.1 参数与选项

无额外参数。依赖环境/配置中的 Memgraph 与模型设置；若配置有误会报错并提示（如 `TARGET_REPO_PATH`）。

### 7.2 示例

```bash
cgr mcp-server
```

---

## 8. graph-loader

**说明**：加载已导出的图 JSON 文件并打印摘要（节点数、关系数、节点类型、关系类型、导出时间等）。

### 8.1 参数与选项

| 参数 | 类型 | 含义 |
|------|------|------|
| `graph_file` | **位置参数（必填）** | 导出的图 JSON 文件路径。 |

### 8.2 示例

```bash
cgr graph-loader graph.json
cgr graph-loader ./output/etar_graph.json
```

---

## 9. language

**说明**：管理项目中的语言语法（tree-sitter 语法子模块与配置）。子命令：`add`、`list`、`remove`、`cleanup`。

### 9.1 language add

添加新语言语法。

| 选项 / 参数 | 类型 | 默认值 | 含义 |
|-------------|------|--------|------|
| `language_name` | 位置参数 | 可选 | 语言名称；若未提供且未提供 `--grammar-url`，会交互提示。 |
| `--grammar-url` | 字符串 | — | tree-sitter 语法仓库 URL；未提供时默认使用 `https://github.com/tree-sitter/tree-sitter-<language_name>`。 |

### 9.2 language list

列出当前已配置的所有语言及其扩展名、函数/类/调用节点类型等（无参数）。

### 9.3 language remove

从配置中移除语言，并可选择是否删除 git 子模块。

| 选项 / 参数 | 类型 | 默认值 | 含义 |
|-------------|------|--------|------|
| `language_name` | 位置参数（必填） | — | 要移除的语言名。 |
| `--keep-submodule` | 布尔 | `false` | 保留 git 子模块（仅从配置中移除）；不指定则尝试删除子模块。 |

### 9.4 language cleanup

清理未被 `.gitmodules` 引用的孤立语法子模块（无参数）。

### 9.5 示例

```bash
cgr language add kotlin
cgr language add --grammar-url https://github.com/your/tree-sitter-mylang
cgr language list
cgr language remove mylang --keep-submodule
cgr language cleanup
```

---

## 10. 环境与配置

以下与 cgr 行为相关，多通过环境变量或 `.env` 配置（见 `config.py`）：

| 名称 | 含义 | 典型默认 |
|------|------|----------|
| `TARGET_REPO_PATH` | 未指定 `--repo-path` 时的默认仓库路径 | `.` |
| `MEMGRAPH_HOST` / `MEMGRAPH_PORT` | Memgraph 连接地址与端口 | `localhost` / `7687` |
| `MEMGRAPH_BATCH_SIZE` | 默认批大小 | `1000` |
| `ORCHESTRATOR_PROVIDER` / `ORCHESTRATOR_MODEL` | 默认主模型 | 可空，回退到 Ollama 等 |
| `CYPHER_PROVIDER` / `CYPHER_MODEL` | 默认 Cypher 模型 | 可空 |
| `.cgrignore` | 仓库根目录下的忽略/反忽略规则 | 与 `--exclude` 合并 |

模型字符串格式为：`provider:model`，例如 `ollama:llama3.2`、`openai:gpt-4`、`google:gemini-2.5-flash`。

---

## 11. 文档与代码索引

- 入口：`main.py` → `codebase_rag.cli.app`
- 命令与全局选项：`codebase_rag/cli.py`
- 帮助文案常量：`codebase_rag/cli_help.py`
- 配置与默认值：`codebase_rag/config.py`
- `language` 子命令：`codebase_rag/tools/language.py`

本文档根据上述源码整理，覆盖当前 cgr 命令的全部参数与含义。
