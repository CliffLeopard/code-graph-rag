# Code-Graph-RAG MCP 协议详解 - 第四部分：工具实现详解

## 1. 工具实现概述

MCP 工具分为四大类：

1. **项目管理工具**: 管理知识图谱中的项目
2. **代码查询工具**: 查询代码图谱和检索代码
3. **文件操作工具**: 读写文件和列出目录
4. **代码编辑工具**: 精确替换代码块

### 1.1 MCP 实际暴露的工具清单（源码对账）

结论：**code-graph-rag 作为 MCP 服务器时，当前版本一共暴露 10 个工具**（在 `codebase_rag/constants.py` 的 `MCPToolName` 枚举里定义，并在 `codebase_rag/mcp/tools.py` 注册）。它并没有单独的“查调用位置”专用工具；这类需求通过 **`query_code_graph`（自然语言→Cypher→执行）** 查询图谱中的 `CALLS` 关系来实现。

- **项目管理（4）**
  - **`list_projects`**：列出数据库中已索引项目
  - **`delete_project`**：删除指定项目
  - **`wipe_database`**：清空整个数据库（需要 `confirm=true`）
  - **`index_repository`**：索引当前 `project_root` 到图谱（会先删同名 project 数据再重建）
- **图谱/代码查询（2）**
  - **`query_code_graph`**：自然语言查询图谱（LLM 生成 Cypher，再由 Memgraph 执行）
  - **`get_code_snippet`**：按 `qualified_name` 返回代码片段（依赖节点的 `path/start_line/end_line`）
- **文件/目录（3）**
  - **`read_file`**：读取文件（支持 `offset/limit` 分页）
  - **`write_file`**：写入文件
  - **`list_directory`**：列目录
- **代码编辑（1）**
  - **`surgical_replace_code`**：按 `target_code` 精确替换为 `replacement_code`

### 1.2 关键点：怎么“查调用位置/调用方/被调用方”？

虽然 MCP 只有 `query_code_graph`/`get_code_snippet` 两个“图谱/代码查询”工具，但它们足以覆盖“查调用位置”：

- **第 1 步：建图**：先调用 `index_repository`，确保当前项目已写入图谱，且 `CALLS` 关系已生成。
- **第 2 步：查调用关系**：用 `query_code_graph` 让系统生成并执行 Cypher，查询 `CALLS` 边：
  - **查某函数/方法的调用方（callers）**：`(caller)-[:CALLS]->(callee)`，过滤 `callee.qualified_name`
  - **查某函数/方法调用了谁（callees）**：`(caller)-[:CALLS]->(callee)`，过滤 `caller.qualified_name`
- **第 3 步：定位源码**：
  - 拿到调用方/被调用方的 `qualified_name` 后，用 `get_code_snippet` 获取其源码片段（文件路径 + 行号 + 源码）。
  - 或用 `read_file(file_path, offset, limit)` 读取更大范围上下文。

下面是“调用关系查询”在图数据库中常见的 Cypher 模板（图谱里存在 `CALLS` 关系类型，节点通常是 `Function/Method`）：
（注意：当前 MCP **不提供“直接提交 Cypher”工具**，所以你要用 `query_code_graph` 的自然语言让 LLM 生成等价查询；但理解这些模板能帮助你写出更稳定的自然语言提示。）

```cypher
// 1) 查 callers：谁调用了目标 callee
MATCH (caller)-[:CALLS]->(callee)
WHERE callee.qualified_name = $qn
RETURN caller.qualified_name AS caller_qn, caller.name AS caller_name, labels(caller) AS caller_type
LIMIT 50;
```

```cypher
// 2) 查 callees：目标 caller 调用了谁
MATCH (caller)-[:CALLS]->(callee)
WHERE caller.qualified_name = $qn
RETURN callee.qualified_name AS callee_qn, callee.name AS callee_name, labels(callee) AS callee_type
LIMIT 50;
```

```cypher
// 3) 查 callers + 源码定位信息（依赖图谱里写入的 start/end/path 等字段）
MATCH (caller)-[:CALLS]->(callee)
WHERE callee.qualified_name = $qn
OPTIONAL MATCH (m:Module)-[*]-(caller)
RETURN caller.qualified_name AS caller_qn,
       caller.start_line AS start_line,
       caller.end_line AS end_line,
       m.path AS path
LIMIT 50;
```

对应的自然语言请求（传给 `query_code_graph`）可以写得非常“结构化”，例如：

- **查 callers**：`Find all callers (functions or methods) that CALLS the entity with qualified_name = 'com.example.UserService.createUser'. Return caller qualified_name, name, and file path/line range if available.`
- **查 callees**：`For the function/method with qualified_name='com.example.UserService.createUser', list all callees it CALLS, returning callee qualified_name and type.`

## 2. 项目管理工具

### 2.1 list_projects

#### 功能

列出所有已索引的项目。

#### 实现

```python
async def list_projects(self) -> ListProjectsResult:
    logger.info(lg.MCP_LISTING_PROJECTS)
    try:
        # 调用数据库连接器获取项目列表
        projects = self.ingestor.list_projects()

        # 返回成功结果
        return ListProjectsSuccessResult(
            projects=projects,
            count=len(projects)
        )
    except Exception as e:
        logger.error(lg.MCP_ERROR_LIST_PROJECTS.format(error=e))
        # 返回错误结果
        return ListProjectsErrorResult(
            error=str(e),
            projects=[],
            count=0
        )
```

#### 输入参数

无

#### 返回格式

**成功**:

```json
{
  "projects": ["project1", "project2"],
  "count": 2
}
```

**失败**:

```json
{
  "projects": [],
  "count": 0,
  "error": "Connection failed"
}
```

### 2.2 delete_project

#### 功能

删除指定的项目及其所有相关节点。

#### 实现

```python
async def delete_project(self, project_name: str) -> DeleteProjectResult:
    logger.info(lg.MCP_DELETING_PROJECT.format(project_name=project_name))
    try:
        # 步骤 1: 获取所有项目
        projects = self.ingestor.list_projects()

        # 步骤 2: 检查项目是否存在
        if project_name not in projects:
            return DeleteProjectErrorResult(
                success=False,
                error=te.MCP_PROJECT_NOT_FOUND.format(
                    project_name=project_name,
                    projects=projects
                ),
            )

        # 步骤 3: 删除项目
        self.ingestor.delete_project(project_name)

        # 步骤 4: 返回成功结果
        return DeleteProjectSuccessResult(
            success=True,
            project=project_name,
            message=cs.MCP_PROJECT_DELETED.format(project_name=project_name),
        )
    except Exception as e:
        logger.error(lg.MCP_ERROR_DELETE_PROJECT.format(error=e))
        return DeleteProjectErrorResult(success=False, error=str(e))
```

#### 输入参数

- `project_name` (string, 必需): 项目名称

#### 返回格式

**成功**:

```json
{
  "success": true,
  "project": "my-project",
  "message": "Successfully deleted project 'my-project'."
}
```

**失败**:

```json
{
  "success": false,
  "error": "Project 'my-project' not found. Available projects: ['project1', 'project2']"
}
```

### 2.3 wipe_database

#### 功能

清空整个数据库，删除所有项目。

#### 实现

```python
async def wipe_database(self, confirm: bool) -> str:
    # 步骤 1: 检查确认标志
    if not confirm:
        return cs.MCP_WIPE_CANCELLED

    logger.warning(lg.MCP_WIPING_DATABASE)
    try:
        # 步骤 2: 清空数据库
        self.ingestor.clean_database()
        return cs.MCP_WIPE_SUCCESS
    except Exception as e:
        logger.error(lg.MCP_ERROR_WIPE.format(error=e))
        return cs.MCP_WIPE_ERROR.format(error=e)
```

#### 输入参数

- `confirm` (boolean, 必需): 必须为 `true` 才能执行

#### 返回格式

**成功**:

```
"Database completely wiped. All projects have been removed."
```

**取消**:

```
"Database wipe cancelled. Set confirm=true to proceed."
```

**失败**:

```
"Error wiping database: {error}"
```

### 2.4 index_repository

#### 功能

解析并索引当前仓库到知识图谱。

#### 实现

```python
async def index_repository(self) -> str:
    logger.info(lg.MCP_INDEXING_REPO.format(path=self.project_root))

    # 步骤 1: 获取项目名称（使用目录名）
    project_name = Path(self.project_root).resolve().name

    try:
        # 步骤 2: 清除现有项目数据
        logger.info(lg.MCP_CLEARING_PROJECT.format(project_name=project_name))
        self.ingestor.delete_project(project_name)

        # 步骤 3: 创建图更新器
        updater = GraphUpdater(
            ingestor=self.ingestor,
            repo_path=Path(self.project_root),
            parsers=self.parsers,
            queries=self.queries,
        )

        # 步骤 4: 运行索引
        updater.run()

        # 步骤 5: 返回成功消息
        return cs.MCP_INDEX_SUCCESS_PROJECT.format(
            path=self.project_root,
            project_name=project_name
        )
    except Exception as e:
        logger.error(lg.MCP_ERROR_INDEXING.format(error=e))
        return cs.MCP_INDEX_ERROR.format(error=e)
```

#### 输入参数

无

#### 返回格式

**成功**:

```
"Successfully indexed repository at /path/to/repo. Project 'repo' has been updated."
```

**失败**:

```
"Error indexing repository: {error}"
```

## 3. 代码查询工具

### 3.1 query_code_graph

#### 功能

使用自然语言查询代码图谱。**实现上不是“写死的查询”**，而是走一条链路：

- 自然语言 → `CypherGenerator.generate()`（LLM）→ Cypher
- Cypher → `MemgraphIngestor.fetch_all()` → `results`

#### 实现

```python
async def query_code_graph(self, natural_language_query: str) -> QueryResultDict:
    logger.info(lg.MCP_QUERY_CODE_GRAPH.format(query=natural_language_query))
    try:
        # 步骤 1: 调用查询工具
        graph_data = await self._query_tool.function(natural_language_query)

        # 步骤 2: 转换为字典
        result_dict: QueryResultDict = graph_data.model_dump()

        # 步骤 3: 记录结果数量
        logger.info(
            lg.MCP_QUERY_RESULTS.format(
                count=len(result_dict.get(cs.DICT_KEY_RESULTS, []))
            )
        )

        return result_dict
    except Exception as e:
        logger.exception(lg.MCP_ERROR_QUERY.format(error=e))
        # 返回错误结果
        return QueryResultDict(
            error=str(e),
            query_used=cs.QUERY_NOT_AVAILABLE,
            results=[],
            summary=cs.MCP_TOOL_EXEC_ERROR.format(
                name=cs.MCPToolName.QUERY_CODE_GRAPH,
                error=e
            ),
        )
```

#### 输入参数

- `natural_language_query` (string, 必需): 自然语言查询

#### 返回格式

**成功**:

```json
{
  "query_used": "MATCH (c:Class) WHERE toLower(c.name) CONTAINS 'user' RETURN c.name AS name, c.qualified_name AS qualified_name LIMIT 50",
  "results": [
    {
      "name": "UserService",
      "qualified_name": "com.example.UserService"
    }
  ],
  "summary": "Found 1 class matching 'user'"
}
```

**失败**:

```json
{
  "error": "Connection failed",
  "query_used": "N/A",
  "results": [],
  "summary": "Error executing tool 'query_code_graph': Connection failed"
}
```

### 3.2 get_code_snippet

#### 功能

根据完全限定名获取代码片段（并返回 `file_path/line_start/line_end`），用于“从图谱实体跳转到源码”。

它底层走的是固定 Cypher：`CYPHER_FIND_BY_QUALIFIED_NAME`（`codebase_rag/cypher_queries.py`），查询到 `path/start/end/docstring` 后，再从磁盘读取该区间行文本拼成 `source_code`。

#### 实现

```python
async def get_code_snippet(self, qualified_name: str) -> CodeSnippetResultDict:
    logger.info(lg.MCP_GET_CODE_SNIPPET.format(name=qualified_name))
    try:
        # 步骤 1: 调用代码检索工具
        snippet = await self._code_tool.function(qualified_name=qualified_name)

        # 步骤 2: 转换为字典
        result: CodeSnippetResultDict | None = snippet.model_dump()

        # 步骤 3: 检查结果
        if result is None:
            return CodeSnippetResultDict(
                error=te.MCP_TOOL_RETURNED_NONE,
                found=False,
                error_message=te.MCP_INVALID_RESPONSE,
            )

        return result
    except Exception as e:
        logger.error(lg.MCP_ERROR_CODE_SNIPPET.format(error=e))
        return CodeSnippetResultDict(
            error=str(e),
            found=False,
            error_message=str(e),
        )
```

#### 输入参数

- `qualified_name` (string, 必需): 完全限定名

#### 返回格式

**成功**:

```json
{
  "qualified_name": "com.example.UserService.createUser",
  "source_code": "public User createUser(String name) {\n  return new User(name);\n}",
  "file_path": "src/main/java/com/example/UserService.java",
  "line_start": 10,
  "line_end": 12,
  "docstring": "Creates a new user",
  "found": true
}
```

**失败**:

```json
{
  "error": "Function not found",
  "found": false,
  "error_message": "Function not found"
}
```

## 4. 文件操作工具

### 4.1 read_file

#### 功能

读取文件内容，支持分页。

#### 实现

```python
async def read_file(
    self,
    file_path: str,
    offset: int | None = None,
    limit: int | None = None
) -> str:
    logger.info(lg.MCP_READ_FILE.format(path=file_path, offset=offset, limit=limit))
    try:
        # 情况 1: 有分页参数
        if offset is not None or limit is not None:
            full_path = Path(self.project_root) / file_path
            start = offset if offset is not None else 0

            with open(full_path, encoding=cs.ENCODING_UTF8) as f:
                # 跳过前面的行
                skipped_count = sum(1 for _ in itertools.islice(f, start))

                # 读取指定数量的行
                if limit is not None:
                    sliced_lines = [line for _, line in zip(range(limit), f)]
                else:
                    sliced_lines = list(f)

                paginated_content = "".join(sliced_lines)

                # 计算剩余行数
                remaining_lines_count = sum(1 for _ in f)
                total_lines = skipped_count + len(sliced_lines) + remaining_lines_count

                # 添加分页头
                header = cs.MCP_PAGINATION_HEADER.format(
                    start=start + 1,
                    end=start + len(sliced_lines),
                    total=total_lines,
                )
                return header + paginated_content
        else:
            # 情况 2: 读取整个文件
            result = await self._file_reader_tool.function(file_path=file_path)
            return str(result)

    except Exception as e:
        logger.error(lg.MCP_ERROR_READ.format(error=e))
        return te.ERROR_WRAPPER.format(message=e)
```

#### 输入参数

- `file_path` (string, 必需): 文件路径（相对于项目根目录）
- `offset` (integer, 可选): 起始行号（0-based）
- `limit` (integer, 可选): 最大行数

#### 返回格式

**无分页**:

```
<文件完整内容>
```

**有分页**:

```
# Lines 1-50 of 200
<文件内容（第 1-50 行）>
```

### 4.2 write_file

#### 功能

写入文件内容，如果文件不存在则创建。

#### 实现

```python
async def write_file(self, file_path: str, content: str) -> str:
    logger.info(lg.MCP_WRITE_FILE.format(path=file_path))
    try:
        # 调用文件写入工具
        result = await self._file_writer_tool.function(
            file_path=file_path,
            content=content
        )

        # 检查结果
        if result.success:
            return cs.MCP_WRITE_SUCCESS.format(path=file_path)
        return te.ERROR_WRAPPER.format(message=result.error_message)
    except Exception as e:
        logger.error(lg.MCP_ERROR_WRITE.format(error=e))
        return te.ERROR_WRAPPER.format(message=e)
```

#### 输入参数

- `file_path` (string, 必需): 文件路径
- `content` (string, 必需): 文件内容

#### 返回格式

**成功**:

```
"Successfully wrote file: src/main/java/com/example/UserService.java"
```

**失败**:

```
"Error: Permission denied"
```

### 4.3 list_directory

#### 功能

列出目录内容。

#### 实现

```python
async def list_directory(
    self,
    directory_path: str = cs.MCP_DEFAULT_DIRECTORY
) -> str:
    logger.info(lg.MCP_LIST_DIR.format(path=directory_path))
    try:
        # 调用目录列表工具
        result = self._directory_lister_tool.function(directory_path=directory_path)
        return str(result)
    except Exception as e:
        logger.error(lg.MCP_ERROR_LIST_DIR.format(error=e))
        return te.ERROR_WRAPPER.format(message=e)
```

#### 输入参数

- `directory_path` (string, 可选): 目录路径（默认: "."）

#### 返回格式

```
src/
  main/
    java/
      com/
        example/
          UserService.java
          UserController.java
```

## 5. 代码编辑工具

### 5.1 surgical_replace_code

#### 功能

精确替换代码块，只修改指定的代码，其他部分保持不变。

#### 实现

```python
async def surgical_replace_code(
    self,
    file_path: str,
    target_code: str,
    replacement_code: str
) -> str:
    logger.info(lg.MCP_SURGICAL_REPLACE.format(path=file_path))
    try:
        # 调用文件编辑器工具
        result = await self._file_editor_tool.function(
            file_path=file_path,
            target_code=target_code,
            replacement_code=replacement_code,
        )
        return str(result)
    except Exception as e:
        logger.error(lg.MCP_ERROR_REPLACE.format(error=e))
        return te.ERROR_WRAPPER.format(message=e)
```

#### 输入参数

- `file_path` (string, 必需): 文件路径
- `target_code` (string, 必需): 要替换的目标代码
- `replacement_code` (string, 必需): 替换后的代码

#### 返回格式

**成功**:

```
"Successfully replaced code block in src/main/java/com/example/UserService.java"
```

**失败**:

```
"Error: Target code not found"
```

## 6. 工具依赖关系

### 6.1 底层工具实例

```python
# 代码查询相关
self._query_tool = create_query_tool(...)
self._code_tool = create_code_retrieval_tool(...)

# 文件操作相关
self._file_reader_tool = create_file_reader_tool(...)
self._file_writer_tool = create_file_writer_tool(...)
self._file_editor_tool = create_file_editor_tool(...)
self._directory_lister_tool = create_directory_lister_tool(...)
```

### 6.2 服务依赖

```python
# 数据库连接
self.ingestor: MemgraphIngestor

# Cypher 查询生成器
self.cypher_gen: CypherGenerator

# 解析器
self.parsers, self.queries = load_parsers()
```

## 7. 错误处理模式

### 7.1 统一错误格式

所有工具都使用 `ERROR_WRAPPER` 包装错误：

```python
te.ERROR_WRAPPER.format(message=error_message)
# 结果: "Error: {error_message}"
```

### 7.2 错误日志记录

```python
logger.error(lg.MCP_ERROR_XXX.format(error=e))
```

### 7.3 异常捕获

所有工具都使用 try-except 捕获异常：

```python
try:
    # 工具逻辑
    return success_result
except Exception as e:
    logger.error(...)
    return error_result
```

## 8. 相关文档

- [第一部分：MCP 协议概述和服务器初始化](./01-overview-and-initialization.md)
- [第二部分：MCP 协议消息格式](./02-message-format.md)
- [第三部分：工具注册和调度](./03-tool-registry.md)
- [第五部分：数据结构和类型定义](./05-data-structures.md)
- [第六部分：完整流程图](./06-flowcharts.md)
