### 解析单个文件

```shell
uv run python scripts/validate_kotlin_parsing.py --project-path examples/Etar-Calendar -f "app/src/main/java/com/android/calendar/settings/CalendarPreferences.kt" -o etar_calendar_prefs_out2.txt
```
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
