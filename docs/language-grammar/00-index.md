# Language Grammar 添加流程详解 - 文档索引

本文档系列详细梳理了 `cgr language add-grammar` 命令的完整执行流程，包括两种使用方式：
1. `cgr language add-grammar kotlin` - 标准方式
2. `cgr language add-grammar --grammar-url https://github.com/CliffLeopard/tree-sitter-kotlin.git` - 自定义方式

## 文档结构

### [第一部分：总览和入口流程](./01-overview-and-entry.md)
- 命令概述
- CLI 路由和入口
- 主执行流程
- 关键数据结构
- 两种命令方式的差异

### [第二部分：Git 子模块添加流程](./02-git-submodule.md)
- Git 子模块添加概述
- `_add_git_submodule()` 函数详解
- 错误处理机制
- 重新安装已存在的子模块
- 文件系统结构

### [第三部分：语言信息检测流程](./03-language-detection.md)
- 语言信息检测概述
- `_parse_tree_sitter_json()` 函数详解
- tree-sitter.json 文件格式
- 语言名称确定逻辑
- 文件扩展名处理
- 手动输入流程

### [第四部分：节点类型分析流程](./04-node-types-analysis.md)
- 节点类型分析概述
- `_find_node_types_path()` 函数详解
- `_parse_node_types_file()` 函数详解
- 语义分类提取
- 节点类型分类逻辑
- 关键词匹配规则
- 手动输入节点分类

### [第五部分：配置文件更新流程](./05-config-update.md)
- 配置文件更新概述
- `_update_config_file()` 函数详解
- `_write_language_config()` 函数详解
- 配置条目格式
- 审查提示
- 错误处理
- 配置使用

### [第六部分：完整流程图](./06-flowcharts.md)
- 整体流程图
- Git 子模块添加详细流程
- 语言信息检测流程
- 节点类型分析流程
- 配置文件更新流程
- 两种方式的对比流程
- 错误处理流程
- 数据流图

## 快速导航

### 按主题查找

**想了解整体流程？**
→ [第一部分：总览和入口流程](./01-overview-and-entry.md)

**想了解 Git 子模块如何添加？**
→ [第二部分：Git 子模块添加流程](./02-git-submodule.md)

**想了解语言信息如何检测？**
→ [第三部分：语言信息检测流程](./03-language-detection.md)

**想了解节点类型如何分析？**
→ [第四部分：节点类型分析流程](./04-node-types-analysis.md)

**想了解配置文件如何更新？**
→ [第五部分：配置文件更新流程](./05-config-update.md)

**想查看流程图？**
→ [第六部分：完整流程图](./06-flowcharts.md)

## 关键概念速查

### 核心函数
- `add_grammar()`: 主入口函数
- `_add_git_submodule()`: 添加 Git 子模块
- `_parse_tree_sitter_json()`: 解析语言信息
- `_parse_node_types_file()`: 分析节点类型
- `_update_config_file()`: 更新配置文件

### 关键数据结构
- `SubmoduleResult`: 子模块操作结果
- `LanguageInfo`: 语言信息（名称和扩展名）
- `NodeCategories`: 节点类型分类
- `LanguageSpec`: 语言配置规范

### 关键文件
- `tree-sitter.json`: 语法库配置文件
- `node-types.json`: 节点类型定义文件
- `language_spec.py`: 语言配置主文件
- `.gitmodules`: Git 子模块列表

### 关键目录
- `grammars/`: 语法库存储目录
- `.git/modules/grammars/`: Git 子模块元数据

## 两种命令方式对比

### 标准方式：`cgr language add-grammar kotlin`

**特点**:
- 使用默认 tree-sitter URL
- 无需安全确认
- 自动从语言名构建 URL

**流程**:
1. 构建 URL: `https://github.com/tree-sitter/tree-sitter-kotlin`
2. 添加子模块
3. 检测语言信息
4. 分析节点类型
5. 更新配置

### 自定义方式：`cgr language add-grammar --grammar-url ...`

**特点**:
- 使用用户提供的 URL
- 需要安全确认
- 支持任意 GitHub 仓库

**流程**:
1. 显示安全警告
2. 用户确认
3. 添加子模块（使用自定义 URL）
4. 检测语言信息
5. 分析节点类型
6. 更新配置

## 典型执行流程示例

### 添加 Kotlin 支持（标准方式）

```bash
$ cgr language add-grammar kotlin
🔍 Using default tree-sitter URL: https://github.com/tree-sitter/tree-sitter-kotlin
🔄 Adding submodule from https://github.com/tree-sitter/tree-sitter-kotlin...
✅ Successfully added submodule at grammars/tree-sitter-kotlin
Auto-detected language: kotlin
Auto-detected file extensions: ['.kt', '.kts']
📊 Found 156 total node types in grammar
🎯 Mapped to our categories:
Functions: ['function_declaration', 'method_declaration']
Classes: ['class_declaration', 'interface_declaration']
Modules: ['compilation_unit']
Calls: ['call_expression']

✅ Language 'kotlin' has been added to the configuration!
📝 Updated codebase_rag/language_spec.py
```

### 添加 Kotlin 支持（自定义方式）

```bash
$ cgr language add-grammar --grammar-url https://github.com/CliffLeopard/tree-sitter-kotlin.git
⚠️  WARNING: You are adding a grammar from a custom URL...
Do you want to continue? [y/N]: y
🔄 Adding submodule from https://github.com/CliffLeopard/tree-sitter-kotlin.git...
✅ Successfully added submodule at grammars/tree-sitter-kotlin
# ... 后续流程相同
```

## 技术栈

- **Git 子模块**: 管理语法库依赖
- **tree-sitter**: 语法解析框架
- **JSON 解析**: 读取配置和节点类型
- **关键词匹配**: 自动分类节点类型
- **文件操作**: 更新配置文件

## 相关资源

- 主要实现文件: `codebase_rag/tools/language.py`
- 配置文件: `codebase_rag/language_spec.py`
- 常量定义: `codebase_rag/constants.py`
- 模型定义: `codebase_rag/models.py`
