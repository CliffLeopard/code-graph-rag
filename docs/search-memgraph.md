# 查看项目中 call 关系的定义和查询方式：

在 Memgraph Lab 中查询 CALLS 关系的 Cypher 查询示例：

## 在 Memgraph Lab 中查询 CALLS 关系

### 1. 打开 Memgraph Lab

- 访问：http://localhost:3000
- 连接到：`memgraph:7687`（或 `localhost:7687`）

### 2. 基础查询示例

#### 查询所有 CALLS 关系

```cypher
MATCH (caller)-[r:CALLS]->(callee)
RETURN caller.name AS caller_name,
       caller.qualified_name AS caller_qn,
       callee.name AS callee_name,
       callee.qualified_name AS callee_qn,
       labels(caller) AS caller_type,
       labels(callee) AS callee_type
LIMIT 100
```

#### 可视化所有 CALLS 关系（图形视图）

```cypher
MATCH (caller)-[r:CALLS]->(callee)
RETURN caller, r, callee
LIMIT 50
```

#### 查询特定函数的调用关系

```cypher
// 查询某个函数调用了哪些函数
MATCH (caller:Function {qualified_name: 'your.project.module.functionName'})-[r:CALLS]->(callee)
RETURN caller.qualified_name AS caller,
       callee.qualified_name AS callee,
       callee.name AS callee_name,
       labels(callee) AS callee_type
```

#### 查询哪些函数调用了特定函数

```cypher
// 查询哪些函数调用了某个函数
MATCH (caller)-[r:CALLS]->(callee:Function {qualified_name: 'your.project.module.targetFunction'})
RETURN caller.qualified_name AS caller,
       caller.name AS caller_name,
       labels(caller) AS caller_type
```

#### 查询调用链（递归查询）

```cypher
// 查询调用链：A 调用 B，B 调用 C
MATCH path = (caller)-[:CALLS*1..3]->(callee)
WHERE caller.qualified_name = 'your.project.module.startFunction'
RETURN path
LIMIT 20
```

#### 统计 CALLS 关系数量

```cypher
// 统计总共有多少 CALLS 关系
MATCH ()-[r:CALLS]->()
RETURN count(r) AS total_calls
```

#### 查询被调用最多的函数

```cypher
// 找出被调用次数最多的函数
MATCH (caller)-[:CALLS]->(callee)
RETURN callee.qualified_name AS function,
       callee.name AS name,
       labels(callee) AS type,
       count(*) AS call_count
ORDER BY call_count DESC
LIMIT 20
```

#### 查询调用其他函数最多的函数

```cypher
// 找出调用其他函数最多的函数
MATCH (caller)-[:CALLS]->(callee)
RETURN caller.qualified_name AS function,
       caller.name AS name,
       labels(caller) AS type,
       count(*) AS calls_made
ORDER BY calls_made DESC
LIMIT 20
```

#### 查询 Kotlin 特定的调用关系

```cypher
// 查询 Kotlin 项目中的调用关系
MATCH (caller)-[r:CALLS]->(callee)
WHERE caller.qualified_name STARTS WITH 'your-kotlin-project.'
   OR callee.qualified_name STARTS WITH 'your-kotlin-project.'
RETURN caller.qualified_name AS caller,
       callee.qualified_name AS callee,
       labels(caller) AS caller_type,
       labels(callee) AS callee_type
LIMIT 100
```

#### 查询特定类的方法调用

```cypher
// 查询某个类的所有方法调用
MATCH (caller)-[:CALLS]->(callee:Method)
WHERE callee.qualified_name STARTS WITH 'your.project.ClassName.'
RETURN caller.qualified_name AS caller,
       callee.qualified_name AS method,
       callee.name AS method_name
```

### 3. 在 Memgraph Lab 中使用

1. 打开查询编辑器：在 Memgraph Lab 左侧找到 "Query" 或 "Cypher" 标签
2. 输入查询：将上述任一查询粘贴到编辑器中
3. 执行查询：
   - 点击 "Run" 或按 `Ctrl+Enter`（Windows/Linux）或 `Cmd+Enter`（Mac）
4. 查看结果：
   - Table 视图：表格形式显示结果
   - Graph 视图：图形可视化（适合带 `RETURN path` 或返回节点的查询）

### 4. 提示

- 使用 `LIMIT` 限制结果数量，避免查询过大
- 图形视图适合查看关系结构
- 使用 `WHERE` 子句过滤特定项目或模块
- 使用 `STARTS WITH` 匹配项目名称前缀

这些查询可帮助你在 Memgraph Lab 中探索和分析代码的调用关系。
