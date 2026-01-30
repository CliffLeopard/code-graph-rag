# JavaService.java CALLS 关系分析

基于 `kotlin-analyze-before-treesitter.json`，与以下类相关的 **CALLS** 关系：

- **JavaService.java** — `grammer_cases/kotlin-grammer-case/src/main/java/cases/interop/JavaService.java`

---

## 1. 统计概览

- 相关节点数：**7**
- 与上述节点有关的 CALLS 边数：**0**

- **验证说明**：图中所有 CALLS 边的 from_id/to_id 仅涉及 [82, 93, 94, 98, 99, 101, 102, 110]，不包含 JavaService 的节点 [54, 89, 95, 103, 104, 105, 106]，故第 3、4、5 节无数据。

---

## 2. 相关节点列表

- `54` — **JavaService.java** `src\main\java\cases\interop\JavaService.java` (File)
  - ``

- `89` — **JavaService.java** `src\main\java\cases\interop\JavaService.java` (Module)
  - `kotlin-grammer-case.src.main.java.cases.interop.JavaService`

- `95` — **JavaService** (Class)
  - `kotlin-grammer-case.src.main.java.cases.interop.JavaService.JavaService`

- `103` — **useKotlinHelper** (Method)
  - `kotlin-grammer-case.src.main.java.cases.interop.JavaService.JavaService.useKotlinHelper(int)`

- `104` — **useKotlinResult** (Method)
  - `kotlin-grammer-case.src.main.java.cases.interop.JavaService.JavaService.useKotlinResult(String)`

- `105` — **useKotlinSingleton** (Method)
  - `kotlin-grammer-case.src.main.java.cases.interop.JavaService.JavaService.useKotlinSingleton()`

- `106` — **chainKotlinAndJava** (Method)
  - `kotlin-grammer-case.src.main.java.cases.interop.JavaService.JavaService.chainKotlinAndJava(int,int)`

---

## 3. CALLS 关系明细

格式：**调用方 (from_id) → 被调用方 (to_id)**

（当前图中暂无与 JavaService 相关的 CALLS 边；若已用 code-graph-rag 解析并导出图，可重新运行本脚本生成。）

---

## 4. 按调用方分组（JavaService 谁调用了谁）

（无：当前图中暂无相关 CALLS。）

---

## 5. 按被调用方分组（谁被 JavaService 调用）

（无：当前图中暂无相关 CALLS。）

---

*由 local_script/analyze_etar_calls.py 根据 kotlin-analyze-before-treesitter.json 自动生成。*
