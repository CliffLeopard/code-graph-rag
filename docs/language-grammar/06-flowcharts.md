# Language Grammar 添加流程详解 - 第六部分：完整流程图

## 1. 整体流程图

```mermaid
graph TD
    A["cgr language add-grammar"] --> B{"有参数?"}
    B -->|无| C["提示输入语言名"]
    B -->|有| D{"有 grammar_url?"}

    C --> D
    D -->|无| E["构建默认 URL"]
    D -->|有| F["使用自定义 URL"]

    E --> G{"自定义 URL?"}
    F --> G

    G -->|是| H["显示安全警告"]
    G -->|否| I["继续"]

    H --> J{"用户确认?"}
    J -->|否| K["终止"]
    J -->|是| I

    I --> L["创建 grammars 目录"]
    L --> M["计算语法库路径"]
    M --> N["添加 Git 子模块"]
    N --> O{"子模块添加成功?"}

    O -->|否| K
    O -->|是| P["解析语言信息"]
    P --> Q{"自动检测成功?"}

    Q -->|是| R["使用检测结果"]
    Q -->|否| S["手动输入"]

    R --> T["查找节点类型文件"]
    S --> T

    T --> U{"找到 node-types.json?"}
    U -->|是| V["分析节点类型"]
    U -->|否| W["手动输入节点类型"]

    V --> X{"分析成功?"}
    X -->|是| Y["使用分析结果"]
    X -->|否| Z["使用默认值"]

    W --> AA["创建 LanguageSpec"]
    Y --> AA
    Z --> AA

    AA --> AB["更新配置文件"]
    AB --> AC{"更新成功?"}

    AC -->|是| AD["显示成功信息"]
    AC -->|否| AE["显示手动添加提示"]

    AD --> AF["完成"]
    AE --> AF
```

## 2. Git 子模块添加详细流程

```mermaid
graph TD
    A["_add_git_submodule"] --> B["执行 git submodule add"]
    B --> C{"执行成功?"}

    C -->|是| D["返回成功结果"]
    C -->|否| E["_handle_submodule_error"]

    E --> F{"错误类型"}
    F -->|已存在| G["_reinstall_existing_submodule"]
    F -->|不存在| H["显示错误并返回 None"]
    F -->|其他| I["抛出异常"]

    G --> J["取消初始化子模块"]
    J --> K["从索引移除"]
    K --> L["清理 .git/modules"]
    L --> M["强制重新添加"]
    M --> N{"重新添加成功?"}

    N -->|是| D
    N -->|否| O["_handle_reinstall_failure"]

    O --> P["显示错误和手动操作提示"]
    H --> Q["终止流程"]
    P --> Q
    D --> R["继续后续流程"]
```

## 3. 语言信息检测流程

```mermaid
graph TD
    A["_parse_tree_sitter_json"] --> B{"文件存在?"}
    B -->|否| C["返回 None"]
    B -->|是| D["读取 JSON 文件"]

    D --> E{"有 grammars 字段?"}
    E -->|否| C
    E -->|是| F["获取第一个语法配置"]

    F --> G["提取语言名称"]
    G --> H["提取文件扩展名"]
    H --> I["规范化扩展名"]
    I --> J["确定最终语言名"]

    J --> K["显示检测结果"]
    K --> L["返回 LanguageInfo"]

    C --> M["_prompt_for_language_info"]
    M --> N["提示输入语言名"]
    N --> O["提示输入扩展名"]
    O --> P["返回 LanguageInfo"]

    L --> Q["继续后续流程"]
    P --> Q
```

## 4. 节点类型分析流程

```mermaid
graph TD
    A["_find_node_types_path"] --> B["检查路径 1"]
    B --> C{"存在?"}
    C -->|是| D["返回路径"]
    C -->|否| E["检查路径 2"]

    E --> F{"存在?"}
    F -->|是| D
    F -->|否| G["检查路径 3"]

    G --> H{"存在?"}
    H -->|是| D
    H -->|否| I["返回 None"]

    D --> J["_parse_node_types_file"]
    I --> K["_prompt_for_node_categories"]

    J --> L["读取 node-types.json"]
    L --> M["提取所有节点名称"]
    M --> N["_extract_semantic_categories"]

    N --> O["提取语义分类"]
    O --> P["_categorize_node_types"]

    P --> Q["匹配函数关键词"]
    Q --> R["匹配类关键词"]
    R --> S["匹配调用关键词"]
    S --> T["匹配模块关键词"]
    T --> U["添加根节点"]

    U --> V["返回 NodeCategories"]

    K --> W["提示输入函数节点"]
    W --> X["提示输入类节点"]
    X --> Y["提示输入模块节点"]
    Y --> Z["提示输入调用节点"]
    Z --> AA["返回 NodeCategories"]

    V --> AB["继续后续流程"]
    AA --> AB
```

## 5. 配置文件更新流程

```mermaid
graph TD
    A["_update_config_file"] --> B["构建配置条目字符串"]
    B --> C["_write_language_config"]

    C --> D["读取现有配置文件"]
    D --> E["查找结束大括号位置"]
    E --> F{"找到?"}

    F -->|否| G["抛出 ValueError"]
    F -->|是| H["在结束大括号前插入配置"]

    H --> I["写入文件"]
    I --> J{"写入成功?"}

    J -->|是| K["显示成功信息"]
    J -->|否| L["捕获异常"]

    K --> M["_show_review_hints"]
    M --> N["显示审查提示"]
    N --> O["显示常见问题"]
    O --> P["显示列表命令提示"]

    L --> Q["显示错误信息"]
    Q --> R["显示手动添加提示"]
    R --> S["显示配置内容"]

    G --> Q
    P --> T["完成"]
    S --> T
```

## 6. 标准方式完整流程

```mermaid
graph LR
    A["cgr language add-grammar kotlin"] --> B["构建默认 URL"]
    B --> C["https://github.com/tree-sitter/tree-sitter-kotlin"]
    C --> D["添加子模块"]
    D --> E["解析 tree-sitter.json"]
    E --> F["检测语言: kotlin"]
    F --> G["检测扩展名: .kt, .kts"]
    G --> H["分析节点类型"]
    H --> I["创建 LanguageSpec"]
    I --> J["更新配置文件"]
    J --> K["完成"]
```

## 7. 自定义方式完整流程

```mermaid
graph LR
    A["cgr language add-grammar --grammar-url ..."] --> B["使用自定义 URL"]
    B --> C["显示安全警告"]
    C --> D{"用户确认?"}
    D -->|否| E["终止"]
    D -->|是| F["添加子模块"]
    F --> G["解析 tree-sitter.json"]
    G --> H["检测语言信息"]
    H --> I["分析节点类型"]
    I --> J["创建 LanguageSpec"]
    J --> K["更新配置文件"]
    K --> L["完成"]
```

## 8. 错误处理流程

```mermaid
graph TD
    A["执行操作"] --> B{"发生错误?"}
    B -->|否| C["继续"]
    B -->|是| D{"错误类型"}

    D -->|子模块已存在| E["重新安装子模块"]
    D -->|仓库不存在| F["显示错误并终止"]
    D -->|JSON 解析失败| G["手动输入语言信息"]
    D -->|节点类型文件不存在| H["手动输入节点类型"]
    D -->|配置文件更新失败| I["显示手动添加提示"]

    E --> J{"重新安装成功?"}
    J -->|是| C
    J -->|否| K["显示手动操作提示"]

    G --> L["继续流程"]
    H --> L
    I --> M["显示配置内容"]
    K --> N["终止"]
    F --> N
    M --> N
    L --> C
```

## 9. 数据流图

```mermaid
graph LR
    A["用户输入"] --> B["参数解析"]
    B --> C["URL 构建"]
    C --> D["Git 子模块"]
    D --> E["tree-sitter.json"]
    E --> F["LanguageInfo"]
    D --> G["node-types.json"]
    G --> H["NodeCategories"]
    F --> I["LanguageSpec"]
    H --> I
    I --> J["language_spec.py"]
    J --> K["LANGUAGE_SPECS"]
    K --> L["解析器加载"]
    L --> M["代码解析"]
```

## 10. 关键函数调用链

```mermaid
graph TD
    A["add_grammar"] --> B["_add_git_submodule"]
    A --> C["_parse_tree_sitter_json"]
    A --> D["_find_node_types_path"]
    A --> E["_parse_node_types_file"]
    A --> F["_update_config_file"]

    B --> B1["_handle_submodule_error"]
    B1 --> B2["_reinstall_existing_submodule"]
    B1 --> B3["_handle_reinstall_failure"]

    C --> C1["_prompt_for_language_info"]

    E --> E1["_extract_semantic_categories"]
    E --> E2["_categorize_node_types"]
    E --> E3["_prompt_for_node_categories"]

    F --> F1["_write_language_config"]
    F1 --> F2["_show_review_hints"]
```

## 11. 两种方式的对比流程

```mermaid
graph TD
    A["命令输入"] --> B{"命令类型"}

    B -->|标准方式| C["cgr language add-grammar kotlin"]
    B -->|自定义方式| D["cgr language add-grammar --grammar-url ..."]

    C --> E["构建默认 URL"]
    D --> F["使用自定义 URL"]

    E --> G["无需安全确认"]
    F --> H["需要安全确认"]

    G --> I["添加子模块"]
    H --> I

    I --> J["后续流程相同"]
    J --> K["解析语言信息"]
    J --> L["分析节点类型"]
    J --> M["更新配置文件"]

    K --> N["完成"]
    L --> N
    M --> N
```

## 12. 相关文档

- [第一部分：总览和入口流程](./01-overview-and-entry.md)
- [第二部分：Git 子模块添加流程](./02-git-submodule.md)
- [第三部分：语言信息检测流程](./03-language-detection.md)
- [第四部分：节点类型分析流程](./04-node-types-analysis.md)
- [第五部分：配置文件更新流程](./05-config-update.md)
