# Code-Graph-RAG 工作流程详解 - 第一部分：总览和入口流程

## 1. 命令入口

### 1.1 CLI 命令解析

当执行 `cgr start --repo-path /path/to/repo1 --update-graph --clean` 时，流程如下：

**入口文件**: `codebase_rag/cli.py`

```python
@app.command(help=ch.CMD_START)
def start(
    repo_path: str | None = typer.Option(None, "--repo-path", ...),
    update_graph: bool = typer.Option(False, "--update-graph", ...),
    clean: bool = typer.Option(False, "--clean", ...),
    ...
) -> None:
```

### 1.2 关键参数处理

1. **`--repo-path`**: 指定要处理的仓库路径
2. **`--update-graph`**: 启用图更新模式
3. **`--clean`**: 清理数据库（删除所有现有数据）

### 1.3 初始化流程

```python
# 1. 加载配置
target_repo_path = repo_path or settings.TARGET_REPO_PATH
effective_batch_size = settings.resolve_batch_size(batch_size)

# 2. 加载 .cgrignore 模式
cgrignore = load_cgrignore_patterns(repo_to_update)
exclude_paths = cli_excludes | cgrignore.exclude or None
unignore_paths = cgrignore.unignore or None

# 3. 连接 Memgraph 数据库
with connect_memgraph(effective_batch_size) as ingestor:
    if clean:
        ingestor.clean_database()  # 清理数据库
    ingestor.ensure_constraints()  # 确保约束存在

    # 4. 加载解析器
    parsers, queries = load_parsers()

    # 5. 创建 GraphUpdater
    updater = GraphUpdater(
        ingestor,
        repo_to_update,
        parsers,
        queries,
        unignore_paths,
        exclude_paths,
    )
    updater.run()  # 执行更新
```

## 2. GraphUpdater 初始化

**文件**: `codebase_rag/graph_updater.py`

### 2.1 核心组件

```python
class GraphUpdater:
    def __init__(
        self,
        ingestor: IngestorProtocol,      # 数据库插入器
        repo_path: Path,                  # 仓库路径
        parsers: dict[SupportedLanguage, Parser],  # 语言解析器
        queries: dict[SupportedLanguage, LanguageQueries],  # 查询模式
        unignore_paths: frozenset[str] | None,
        exclude_paths: frozenset[str] | None,
    ):
```

### 2.2 关键数据结构

1. **`function_registry`**: `FunctionRegistryTrie`

   - 存储所有函数/方法的完全限定名（FQN）
   - 使用 Trie 结构支持前缀搜索
   - 包含简单名称查找索引

2. **`simple_name_lookup`**: `defaultdict[str, set[str]]`

   - 从简单名称到 FQN 集合的映射
   - 用于快速查找同名函数

3. **`ast_cache`**: `BoundedASTCache`

   - 缓存已解析的 AST
   - 限制内存使用（最大条目数和内存大小）

4. **`factory`**: `ProcessorFactory`
   - 创建各种处理器（结构、定义、调用等）

## 3. 主执行流程 (GraphUpdater.run())

### 3.1 执行阶段

```python
def run(self) -> None:
    # 阶段 1: 创建项目节点
    self.ingestor.ensure_node_batch(
        cs.NODE_PROJECT,
        {cs.KEY_NAME: self.project_name}
    )

    # 阶段 2: 识别项目结构（包、文件夹等）
    logger.info(ls.PASS_1_STRUCTURE)
    self.factory.structure_processor.identify_structure()

    # 阶段 3: 处理所有文件
    logger.info(ls.PASS_2_FILES)
    self._process_files()

    # 阶段 4: 处理函数调用关系
    logger.info(ls.PASS_3_CALLS)
    self._process_function_calls()

    # 阶段 5: 处理方法重写
    self.factory.definition_processor.process_all_method_overrides()

    # 阶段 6: 刷新所有缓冲区
    self.ingestor.flush_all()

    # 阶段 7: 生成语义嵌入
    self._generate_semantic_embeddings()
```

### 3.2 文件处理流程

```python
def _process_files(self) -> None:
    for filepath in self.repo_path.rglob("*"):
        if filepath.is_file() and not should_skip_path(...):
            # 获取语言配置
            lang_config = get_language_spec(filepath.suffix)

            if lang_config and lang_config.language in self.parsers:
                # 处理源代码文件
                result = self.factory.definition_processor.process_file(
                    filepath,
                    lang_config.language,
                    self.queries,
                    self.factory.structure_processor.structural_elements,
                )
                if result:
                    root_node, language = result
                    self.ast_cache[filepath] = (root_node, language)
            elif self._is_dependency_file(filepath.name, filepath):
                # 处理依赖文件（pom.xml, package.json 等）
                self.factory.definition_processor.process_dependencies(filepath)

            # 处理通用文件
            self.factory.structure_processor.process_generic_file(
                filepath, filepath.name
            )
```

## 4. 关键类和接口

### 4.1 IngestorProtocol

**位置**: `codebase_rag/services/graph_service.py`

```python
class MemgraphIngestor:
    def ensure_node_batch(label: str, properties: dict) -> None
    def ensure_relationship_batch(
        from_spec: tuple[str, str, PropertyValue],
        rel_type: str,
        to_spec: tuple[str, str, PropertyValue],
        properties: dict | None = None,
    ) -> None
    def flush_nodes() -> None
    def flush_relationships() -> None
    def flush_all() -> None
```

### 4.2 ProcessorFactory

**位置**: `codebase_rag/parsers/factory.py`

负责创建各种处理器：

- `structure_processor`: 处理项目结构
- `definition_processor`: 处理定义（类、函数等）
- `import_processor`: 处理导入
- `call_processor`: 处理调用关系
- `type_inference`: 类型推断引擎

## 5. 数据流概览

```
CLI 命令
  ↓
GraphUpdater 初始化
  ↓
阶段 1: 结构识别 (StructureProcessor)
  ↓
阶段 2: 文件处理 (DefinitionProcessor)
  ├─→ 解析 AST (tree-sitter)
  ├─→ 提取模块
  ├─→ 提取导入
  ├─→ 提取类和函数
  └─→ 注册到 function_registry
  ↓
阶段 3: 调用处理 (CallProcessor)
  ├─→ 解析函数调用
  ├─→ 类型推断
  └─→ 创建 CALLS 关系
  ↓
阶段 4: 方法重写处理
  ↓
阶段 5: 刷新数据库
  ↓
阶段 6: 生成嵌入向量
```

## 6. 下一步

- [第二部分：Java 语法解析详细流程](./02-java-parsing.md)
- [第三部分：数据库插入逻辑](./03-database-insertion.md)
- [第四部分：查询逻辑](./04-query-logic.md)
- [第五部分：关键数据结构](./05-data-structures.md)
- [第六部分：完整流程图](./06-flowcharts.md)
