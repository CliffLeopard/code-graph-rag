### 解析

```shell
# 单个文件
 uv run python local_script/validate_kotlin_parsing.py --project-path ./grammer_cases/kotlin-grammer-case  -o ./analyze_docs/kotlin-analyze-before-treesitter.txt

# 官方解析
uv run cgr start --repo-path grammer_cases/kotlin-grammer-case --update-graph --clean -o ./analyze_docs/kotlin-analyze-before-treesitter.json

# 语法JSON CALL解析
uv run python local_script/analyze_special_calls.py

### Docker执行
```shell
```
### PreCommit
```shell
uv run pre-commit run --all-files
```

### SubModule
``` shell
# 添加
git submodule add https://github.com/CliffLeopard/kotlin-grammer-case.git grammer_cases/kotlin-grammer-case

# 初始化
git submodule update --init --recursive
```
