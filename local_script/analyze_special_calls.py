#!/usr/bin/env python3
"""
从图 JSON 中提取与指定类/文件相关的所有 CALLS 关系，并生成分析 Markdown 文档。

默认使用 analyze_docs/kotlin-analyze-before-treesitter.json，
分析 grammer_cases/kotlin-grammer-case/src/main/java/cases/interop/JavaService.java 相关的 CALLS。
"""
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# 默认：kotlin-analyze JSON + JavaService.java（path 子串与 qualified_name 前缀）
DEFAULT_GRAPH_PATH = REPO_ROOT / "analyze_docs" / "kotlin-analyze-before-treesitter.json"
DEFAULT_PATH_SUBSTRING = "JavaService.java"
DEFAULT_QUALIFIED_PREFIX = "kotlin-grammer-case.src.main.java.cases.interop.JavaService"
DEFAULT_OUTPUT_PATH = REPO_ROOT / "analyze_docs" / "javaservice_calls_analysis.md"


def load_graph(json_path: Path) -> tuple[list, list]:
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)
    return data.get("nodes", []), data.get("relationships", [])


def collect_relevant_node_ids(
    nodes: list,
    relationships: list,
    path_substring: str,
    qualified_name_prefix: str,
) -> tuple[set[int], dict[int, dict]]:
    """收集与目标文件/类相关的所有 node_id。

    包含两类节点：
    1. 目标文件/类本身：path 含目标文件 或 qualified_name 以目标前缀开头（File、Module、Class 等）。
    2. 属于该文件/类的子节点：Method、Function 等（同上 qualified_name 前缀），以及通过 DEFINES/DEFINES_METHOD/CONTAINS_* 从 1 可达的节点。
    这样 CALLS 的 from_id/to_id 只要等于上述任一节点即视为与 JavaService.java 相关。
    """
    id_to_node = {}
    relevant_ids = set()

    for node in nodes:
        nid = node.get("node_id")
        props = node.get("properties", {})
        qn = props.get("qualified_name") or ""
        path = props.get("path") or ""

        id_to_node[nid] = {
            "node_id": nid,
            "labels": node.get("labels", []),
            "qualified_name": qn,
            "name": props.get("name", ""),
            "path": path,
        }

        if path_substring in path or qn.startswith(qualified_name_prefix):
            relevant_ids.add(nid)

    def_added = True
    while def_added:
        def_added = False
        for rel in relationships:
            rtype = rel.get("type") or ""
            from_id = rel.get("from_id")
            to_id = rel.get("to_id")
            if from_id not in relevant_ids or to_id in relevant_ids:
                continue
            if rtype in ("DEFINES", "DEFINES_METHOD") or (
                rtype.startswith("CONTAINS_")
            ):
                relevant_ids.add(to_id)
                def_added = True

    return relevant_ids, id_to_node


def collect_call_edges(relationships: list, relevant_ids: set[int]) -> list[dict]:
    """收集 CALLS 中任意一端在 relevant_ids 内的边（含 File/Module/Class/Method/Function 等）。"""
    edges = []
    for rel in relationships:
        if rel.get("type") != "CALLS":
            continue
        from_id = rel.get("from_id")
        to_id = rel.get("to_id")
        if from_id in relevant_ids or to_id in relevant_ids:
            edges.append({"from_id": from_id, "to_id": to_id, "type": "CALLS"})
    return edges


def short_name(qn: str) -> str:
    if not qn:
        return ""
    if "." in qn:
        return qn.split(".")[-1]
    return qn


def format_node(info: dict) -> str:
    labels = "+".join(info.get("labels", []))
    qn = info.get("qualified_name", "")
    name = info.get("name", "")
    path = info.get("path", "")
    part = f"**{name or short_name(qn)}**"
    if path:
        part += f" `{path}`"
    part += f" ({labels})"
    return part


def main() -> None:
    graph_path = DEFAULT_GRAPH_PATH
    path_substring = DEFAULT_PATH_SUBSTRING
    qualified_prefix = DEFAULT_QUALIFIED_PREFIX
    out_path = DEFAULT_OUTPUT_PATH

    if not graph_path.exists():
        print(f"Error: {graph_path} not found", file=sys.stderr)
        sys.exit(1)

    nodes, relationships = load_graph(graph_path)
    relevant_ids, id_to_node = collect_relevant_node_ids(
        nodes, relationships, path_substring, qualified_prefix
    )
    call_edges = collect_call_edges(relationships, relevant_ids)

    by_caller: dict[int, list[int]] = {}
    by_callee: dict[int, list[int]] = {}
    for e in call_edges:
        by_caller.setdefault(e["from_id"], []).append(e["to_id"])
        by_callee.setdefault(e["to_id"], []).append(e["from_id"])

    title = "JavaService.java CALLS 关系分析"
    target_desc = "grammer_cases/kotlin-grammer-case/src/main/java/cases/interop/JavaService.java"

    lines = [
        f"# {title}",
        "",
        f"基于 `{graph_path.name}`，与以下类相关的 **CALLS** 关系：",
        "",
        f"- **JavaService.java** — `{target_desc}`",
        "",
        "---",
        "",
        "## 1. 统计概览",
        "",
        f"- 相关节点数：**{len(relevant_ids)}**",
        f"- 与上述节点有关的 CALLS 边数：**{len(call_edges)}**",
        "",
    ]
    if not call_edges:
        call_ids = set()
        for rel in relationships:
            if rel.get("type") == "CALLS":
                call_ids.add(rel.get("from_id"))
                call_ids.add(rel.get("to_id"))
        msg = (
            f"- **验证说明**：图中所有 CALLS 边的 from_id/to_id 仅涉及 {sorted(call_ids)}，"
            + f"不包含 JavaService 的节点 {sorted(relevant_ids)}，故第 3、4、5 节无数据。"
        )
        lines.append(msg)
    lines.extend([
        "",
        "---",
        "",
        "## 2. 相关节点列表",
        "",
    ])

    for nid in sorted(relevant_ids):
        info = id_to_node.get(nid, {})
        qn = info.get("qualified_name", "")
        lines.append(f"- `{nid}` — {format_node(info)}")
        lines.append(f"  - `{qn}`")
        lines.append("")

    lines.extend([
        "---",
        "",
        "## 3. CALLS 关系明细",
        "",
        "格式：**调用方 (from_id) → 被调用方 (to_id)**",
        "",
    ])

    if not call_edges:
        lines.append("（当前图中暂无与 JavaService 相关的 CALLS 边；若已用 code-graph-rag 解析并导出图，可重新运行本脚本生成。）")
        lines.append("")

    seen = set()
    for e in sorted(call_edges, key=lambda x: (x["from_id"], x["to_id"])):
        key = (e["from_id"], e["to_id"])
        if key in seen:
            continue
        seen.add(key)
        from_info = id_to_node.get(e["from_id"], {})
        to_info = id_to_node.get(e["to_id"], {})
        from_qn = from_info.get("qualified_name", "?")
        to_qn = to_info.get("qualified_name", "?")
        from_short = from_info.get("name") or short_name(from_qn)
        to_short = to_info.get("name") or short_name(to_qn)
        lines.append(f"- **{from_short}** (`{e['from_id']}`) → **{to_short}** (`{e['to_id']}`)")
        lines.append(f"  - Caller: `{from_qn}`")
        lines.append(f"  - Callee: `{to_qn}`")
        lines.append("")

    lines.extend([
        "---",
        "",
        "## 4. 按调用方分组（JavaService 谁调用了谁）",
        "",
    ])

    if not call_edges:
        lines.append("（无：当前图中暂无相关 CALLS。）")
        lines.append("")

    for nid in sorted(relevant_ids):
        callees = by_caller.get(nid, [])
        if not callees:
            continue
        info = id_to_node.get(nid, {})
        name = info.get("name") or short_name(info.get("qualified_name", ""))
        lines.append(f"### 调用方: {name} (node_id={nid})")
        lines.append("")
        for to_id in sorted(set(callees)):
            to_info = id_to_node.get(to_id, {})
            to_qn = to_info.get("qualified_name", "?")
            to_name = to_info.get("name") or short_name(to_qn)
            lines.append(f"- → **{to_name}** (`{to_id}`) — `{to_qn}`")
        lines.append("")

    lines.extend([
        "---",
        "",
        "## 5. 按被调用方分组（谁被 JavaService 调用）",
        "",
    ])

    if not call_edges:
        lines.append("（无：当前图中暂无相关 CALLS。）")
        lines.append("")

    for nid in sorted(relevant_ids):
        callers = by_callee.get(nid, [])
        if not callers:
            continue
        info = id_to_node.get(nid, {})
        name = info.get("name") or short_name(info.get("qualified_name", ""))
        lines.append(f"### 被调用方: {name} (node_id={nid})")
        lines.append("")
        for from_id in sorted(set(callers)):
            from_info = id_to_node.get(from_id, {})
            from_qn = from_info.get("qualified_name", "?")
            from_name = from_info.get("name") or short_name(from_qn)
            lines.append(f"- ← **{from_name}** (`{from_id}`) — `{from_qn}`")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append(f"*由 local_script/analyze_etar_calls.py 根据 {graph_path.name} 自动生成。*")
    lines.append("")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote: {out_path}")
    print(f"Relevant nodes: {len(relevant_ids)}, CALLS edges: {len(call_edges)}")


if __name__ == "__main__":
    main()
