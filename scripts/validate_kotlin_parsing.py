#!/usr/bin/env python3
"""
Kotlin SDK 解析验证脚本

使用 code_graph_rag 解析 kotlin-sdk 项目，并验证：
1. 类是否被正确检测
2. 接口是否被正确检测
3. 方法是否被正确检测
4. 调用关系是否被正确解析
5. 继承关系是否被正确解析
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from codebase_rag import constants as cs
from codebase_rag.graph_updater import GraphUpdater
from codebase_rag.main import connect_memgraph
from codebase_rag.parser_loader import load_parsers


def _extract_qn(node_tuple: tuple) -> str:
    """从节点元组中提取 qualified_name"""
    if isinstance(node_tuple, tuple) and len(node_tuple) > 2:
        return node_tuple[2]
    elif isinstance(node_tuple, dict):
        return node_tuple.get("qualified_name", node_tuple.get("name", str(node_tuple)))
    else:
        return str(node_tuple)


def delete_project_if_exists(project_path: Path) -> bool:
    """
    如果项目存在于数据库中，则删除它。
    
    使用官方 API：MemgraphIngestor.delete_project()，与 MCP index_repository 的实现方式一致。
    参考：codebase_rag/mcp/tools.py 中的 index_repository 方法
    """
    project_name = project_path.resolve().name
    
    try:
        # 使用官方 connect_memgraph 函数连接数据库（与 CLI 和 MCP 一致）
        # 参考：codebase_rag/main.py 中的 connect_memgraph
        with connect_memgraph(batch_size=1000) as ingestor:
            # 检查项目是否存在
            existing_projects = ingestor.list_projects()
            
            if project_name in existing_projects:
                print(f"\n发现已存在的项目: {project_name}")
                print(f"正在删除项目 '{project_name}' 及其所有数据...")
                # 使用官方 API 删除项目（与 MCP index_repository 的实现一致）
                ingestor.delete_project(project_name)
                print(f"✓ 项目 '{project_name}' 已成功删除")
                return True
            else:
                print(f"\n项目 '{project_name}' 不存在于数据库中，无需删除")
                return False
                
    except Exception as e:
        # 如果连接失败（例如数据库未运行），则跳过删除步骤
        print(f"\n⚠ 无法连接到 Memgraph 数据库: {e}")
        print("  跳过项目删除步骤（可能只是用于测试验证）")
        return False


def analyze_kotlin_project(project_path: Path) -> dict:
    """分析 Kotlin 项目并返回统计信息"""
    print(f"\n{'=' * 60}")
    print(f"分析 Kotlin 项目: {project_path}")
    print(f"{'=' * 60}\n")

    # 在解析前删除已存在的项目数据
    print("步骤 1: 清理已存在的项目数据...")
    delete_project_if_exists(project_path)
    
    # 加载解析器
    print("\n步骤 2: 正在加载解析器...")
    parsers, queries = load_parsers()

    if cs.SupportedLanguage.KOTLIN not in parsers:
        print("错误: Kotlin 解析器不可用!")
        return {}

    print("✓ Kotlin 解析器已加载")

    # 创建 mock ingestor 来收集所有数据
    mock_ingestor = MagicMock()

    # 创建并运行更新器
    print("\n正在解析项目...")
    updater = GraphUpdater(
        ingestor=mock_ingestor,
        repo_path=project_path,
        parsers=parsers,
        queries=queries,
    )
    updater.run()

    # 分析收集的数据
    stats = {
        "modules": [],
        "classes": [],
        "interfaces": [],
        "enums": [],
        "objects": [],
        "methods": [],
        "functions": [],
        "calls": [],
        "inherits": [],
        "implements": [],
        "imports": [],
    }

    # 处理 ensure_node_batch 调用
    for call in mock_ingestor.ensure_node_batch.call_args_list:
        label = call.args[0] if call.args else call.kwargs.get("label")
        props = (
            call.args[1] if len(call.args) > 1 else call.kwargs.get("properties", {})
        )
        qn = props.get("qualified_name", props.get("name", "N/A"))

        label_str = str(label.value) if hasattr(label, "value") else str(label)

        if label_str == "Module":
            stats["modules"].append(qn)
        elif label_str == "Class":
            stats["classes"].append(qn)
        elif label_str == "Interface":
            stats["interfaces"].append(qn)
        elif label_str == "Enum":
            stats["enums"].append(qn)
        elif label_str == "Object":
            stats["objects"].append(qn)
        elif label_str == "Method":
            stats["methods"].append(qn)
        elif label_str == "Function":
            stats["functions"].append(qn)

    # 处理 ensure_relationship_batch 调用
    for call in mock_ingestor.ensure_relationship_batch.call_args_list:
        rel_type = call.args[1] if len(call.args) > 1 else call.kwargs.get("rel_type")
        from_node = call.args[0] if call.args else call.kwargs.get("from_node")
        to_node = call.args[2] if len(call.args) > 2 else call.kwargs.get("to_node")

        rel_str = str(rel_type.value) if hasattr(rel_type, "value") else str(rel_type)

        if rel_str == "CALLS":
            stats["calls"].append((from_node, to_node))
        elif rel_str == "INHERITS":
            stats["inherits"].append((from_node, to_node))
        elif rel_str == "IMPLEMENTS":
            stats["implements"].append((from_node, to_node))
        elif rel_str == "IMPORTS":
            stats["imports"].append((from_node, to_node))

    return stats


def print_stats(stats: dict) -> None:
    """打印统计信息"""
    print(f"\n{'=' * 60}")
    print("解析统计")
    print(f"{'=' * 60}")

    print(f"\n模块数量: {len(stats['modules'])}")
    print(f"类数量: {len(stats['classes'])}")
    print(f"接口数量: {len(stats['interfaces'])}")
    print(f"枚举数量: {len(stats['enums'])}")
    print(f"Object 数量: {len(stats['objects'])}")
    print(f"方法数量: {len(stats['methods'])}")
    print(f"函数数量: {len(stats['functions'])}")
    print(f"调用关系数量: {len(stats['calls'])}")
    print(f"继承关系数量: {len(stats['inherits'])}")
    print(f"实现关系数量: {len(stats['implements'])}")
    print(f"导入关系数量: {len(stats['imports'])}")


def print_sample_data(stats: dict, sample_size: int = 10) -> None:
    """打印示例数据"""
    print(f"\n{'=' * 60}")
    print("示例数据")
    print(f"{'=' * 60}")

    if stats["classes"]:
        print(f"\n--- 类（前 {sample_size} 个）---")
        for cls in sorted(stats["classes"])[:sample_size]:
            print(f"  {cls}")

    if stats["interfaces"]:
        print(f"\n--- 接口（前 {sample_size} 个）---")
        for iface in sorted(stats["interfaces"])[:sample_size]:
            print(f"  {iface}")

    if stats["enums"]:
        print(f"\n--- 枚举（前 {sample_size} 个）---")
        for enum in sorted(stats["enums"])[:sample_size]:
            print(f"  {enum}")

    if stats["objects"]:
        print(f"\n--- Objects（前 {sample_size} 个）---")
        for obj in sorted(stats["objects"])[:sample_size]:
            print(f"  {obj}")

    if stats["methods"]:
        print(f"\n--- 方法（前 {sample_size} 个）---")
        for method in sorted(stats["methods"])[:sample_size]:
            print(f"  {method}")

    if stats["calls"]:
        print(f"\n--- 调用关系（前 {sample_size} 个）---")
        for from_node, to_node in stats["calls"][:sample_size]:
            from_qn = _extract_qn(from_node)
            to_qn = _extract_qn(to_node)
            from_label = from_node[0] if isinstance(from_node, tuple) and len(from_node) > 0 else "Unknown"
            to_label = to_node[0] if isinstance(to_node, tuple) and len(to_node) > 0 else "Unknown"
            print(f"  [{from_label}] {from_qn} -> [{to_label}] {to_qn}")

    if stats["inherits"]:
        print(f"\n--- 继承关系（前 {sample_size} 个）---")
        for from_node, to_node in stats["inherits"][:sample_size]:
            from_qn = _extract_qn(from_node)
            to_qn = _extract_qn(to_node)
            print(f"  {from_qn} extends {to_qn}")

    if stats["implements"]:
        print(f"\n--- 实现关系（前 {sample_size} 个）---")
        for from_node, to_node in stats["implements"][:sample_size]:
            from_qn = _extract_qn(from_node)
            to_qn = _extract_qn(to_node)
            print(f"  {from_qn} implements {to_qn}")


def validate_parsing(stats: dict) -> bool:
    """验证解析结果"""
    print(f"\n{'=' * 60}")
    print("验证结果")
    print(f"{'=' * 60}")

    all_passed = True

    # 验证类被检测
    if stats["classes"]:
        print(f"\n✓ 类检测: 通过 ({len(stats['classes'])} 个类)")
    else:
        print("\n✗ 类检测: 失败 (没有检测到任何类)")
        all_passed = False

    # 验证接口被检测
    if stats["interfaces"]:
        print(f"✓ 接口检测: 通过 ({len(stats['interfaces'])} 个接口)")
    else:
        print("✗ 接口检测: 失败 (没有检测到任何接口)")
        all_passed = False

    # 验证方法被检测
    if stats["methods"]:
        print(f"✓ 方法检测: 通过 ({len(stats['methods'])} 个方法)")
    else:
        print("✗ 方法检测: 失败 (没有检测到任何方法)")
        all_passed = False

    # 验证调用关系
    if stats["calls"]:
        print(f"✓ 调用关系: 通过 ({len(stats['calls'])} 个调用)")
        # 验证调用关系的质量
        unique_callers = len(set(_extract_qn(c[0]) for c in stats["calls"]))
        unique_callees = len(set(_extract_qn(c[1]) for c in stats["calls"]))
        print(f"  - 唯一调用者: {unique_callers}")
        print(f"  - 唯一被调用者: {unique_callees}")
        
        # 检查是否有方法调用方法、函数调用函数等
        method_to_method = 0
        function_to_function = 0
        method_to_function = 0
        function_to_method = 0
        
        for from_node, to_node in stats["calls"]:
            from_label = from_node[0] if isinstance(from_node, tuple) and len(from_node) > 0 else ""
            to_label = to_node[0] if isinstance(to_node, tuple) and len(to_node) > 0 else ""
            
            if from_label == "Method" and to_label == "Method":
                method_to_method += 1
            elif from_label == "Function" and to_label == "Function":
                function_to_function += 1
            elif from_label == "Method" and to_label == "Function":
                method_to_function += 1
            elif from_label == "Function" and to_label == "Method":
                function_to_method += 1
        
        if method_to_method > 0:
            print(f"  - 方法 -> 方法: {method_to_method}")
        if function_to_function > 0:
            print(f"  - 函数 -> 函数: {function_to_function}")
        if method_to_function > 0:
            print(f"  - 方法 -> 函数: {method_to_function}")
        if function_to_method > 0:
            print(f"  - 函数 -> 方法: {function_to_method}")
    else:
        print("⚠ 调用关系: 警告 (没有检测到调用关系)")

    # 验证继承关系
    if stats["inherits"]:
        print(f"✓ 继承关系: 通过 ({len(stats['inherits'])} 个继承)")
    else:
        print("⚠ 继承关系: 警告 (没有检测到继承关系)")

    # 验证实现关系
    if stats["implements"]:
        print(f"✓ 实现关系: 通过 ({len(stats['implements'])} 个实现)")
    else:
        print("⚠ 实现关系: 警告 (没有检测到实现关系)")

    return all_passed


def print_all_calls(stats: dict, max_display: int | None = None) -> None:
    """打印所有解析出的 call 关系"""
    print(f"\n{'=' * 60}")
    print("所有 Call 关系解析结果")
    print(f"{'=' * 60}")
    
    calls = stats["calls"]
    total_count = len(calls)
    
    print(f"\n总计: {total_count} 个调用关系\n")
    
    if not calls:
        print("⚠ 没有检测到任何调用关系")
        return
    
    # 按调用者分组统计
    caller_stats: dict[str, int] = {}
    callee_stats: dict[str, int] = {}
    
    for from_node, to_node in calls:
        from_qn = _extract_qn(from_node)
        to_qn = _extract_qn(to_node)
        caller_stats[from_qn] = caller_stats.get(from_qn, 0) + 1
        callee_stats[to_qn] = callee_stats.get(to_qn, 0) + 1
    
    # 打印统计信息
    print(f"--- 调用者统计（前 20 个）---")
    sorted_callers = sorted(caller_stats.items(), key=lambda x: x[1], reverse=True)
    for caller, count in sorted_callers[:20]:
        print(f"  {caller}: {count} 次调用")
    
    print(f"\n--- 被调用者统计（前 20 个）---")
    sorted_callees = sorted(callee_stats.items(), key=lambda x: x[1], reverse=True)
    for callee, count in sorted_callees[:20]:
        print(f"  {callee}: 被调用 {count} 次")
    
    # 打印所有调用关系
    print(f"\n--- 所有调用关系详情 ---")
    display_count = max_display if max_display else total_count
    
    for idx, (from_node, to_node) in enumerate(calls[:display_count], 1):
        from_qn = _extract_qn(from_node)
        to_qn = _extract_qn(to_node)
        from_label = from_node[0] if isinstance(from_node, tuple) and len(from_node) > 0 else "Unknown"
        to_label = to_node[0] if isinstance(to_node, tuple) and len(to_node) > 0 else "Unknown"
        print(f"  {idx:4d}. [{from_label}] {from_qn}")
        print(f"       -> [{to_label}] {to_qn}")
    
    if max_display and total_count > max_display:
        print(f"\n  ... 还有 {total_count - max_display} 个调用关系未显示")
    
    # 按调用者分组显示
    print(f"\n--- 按调用者分组的调用关系 ---")
    caller_groups: dict[str, list[str]] = {}
    for from_node, to_node in calls:
        from_qn = _extract_qn(from_node)
        to_qn = _extract_qn(to_node)
        if from_qn not in caller_groups:
            caller_groups[from_qn] = []
        caller_groups[from_qn].append(to_qn)
    
    sorted_callers_by_qn = sorted(caller_groups.items())[:30]  # 显示前30个调用者
    for caller, callees in sorted_callers_by_qn:
        print(f"\n  {caller} 调用了 {len(callees)} 个方法/函数:")
        for callee in sorted(set(callees))[:10]:  # 每个调用者最多显示10个被调用者
            print(f"    -> {callee}")
        if len(set(callees)) > 10:
            print(f"    ... 还有 {len(set(callees)) - 10} 个")


def search_specific_patterns(stats: dict) -> None:
    """搜索特定模式"""
    print(f"\n{'=' * 60}")
    print("特定模式搜索")
    print(f"{'=' * 60}")

    # 搜索 Server 相关类
    server_classes = [c for c in stats["classes"] if "Server" in c]
    print(f"\n--- Server 相关类 ({len(server_classes)} 个) ---")
    for cls in server_classes[:20]:
        print(f"  {cls}")

    # 搜索 Client 相关类
    client_classes = [c for c in stats["classes"] if "Client" in c]
    print(f"\n--- Client 相关类 ({len(client_classes)} 个) ---")
    for cls in client_classes[:20]:
        print(f"  {cls}")

    # 搜索 Transport 相关类
    transport_classes = [c for c in stats["classes"] if "Transport" in c]
    print(f"\n--- Transport 相关类 ({len(transport_classes)} 个) ---")
    for cls in transport_classes[:20]:
        print(f"  {cls}")

    # 搜索 data class (通常包含特定后缀或命名)
    data_classes = [
        c
        for c in stats["classes"]
        if any(x in c for x in ["Request", "Response", "Result", "Info", "Config"])
    ]
    print(f"\n--- 可能的 Data Class ({len(data_classes)} 个) ---")
    for cls in data_classes[:20]:
        print(f"  {cls}")

    # 搜索 Protocol 相关继承
    if stats["inherits"]:
        print(f"\n--- Protocol 相关继承关系 ---")
        for from_node, to_node in stats["inherits"]:
            from_qn = from_node[2] if len(from_node) > 2 else str(from_node)
            to_qn = to_node[2] if len(to_node) > 2 else str(to_node)
            if "Protocol" in from_qn or "Protocol" in to_qn:
                print(f"  {from_qn} extends {to_qn}")

        print(f"\n--- Client 相关继承关系 ---")
        for from_node, to_node in stats["inherits"]:
            from_qn = from_node[2] if len(from_node) > 2 else str(from_node)
            to_qn = to_node[2] if len(to_node) > 2 else str(to_node)
            if "Client" in from_qn:
                print(f"  {from_qn} extends {to_qn}")

        print(f"\n--- Transport 相关继承关系 ---")
        for from_node, to_node in stats["inherits"]:
            from_qn = from_node[2] if len(from_node) > 2 else str(from_node)
            to_qn = to_node[2] if len(to_node) > 2 else str(to_node)
            if "Transport" in from_qn or "Transport" in to_qn:
                print(f"  {from_qn} extends {to_qn}")

    # 搜索 Transport 接口实现关系
    if stats["implements"]:
        print(f"\n--- Transport 接口实现关系 ---")
        for from_node, to_node in stats["implements"]:
            from_qn = from_node[2] if len(from_node) > 2 else str(from_node)
            to_qn = to_node[2] if len(to_node) > 2 else str(to_node)
            if "Transport" in from_qn or "Transport" in to_qn:
                print(f"  {from_qn} implements {to_qn}")


def main():
    """主函数"""
    project_path = Path("/Users/cliffleopard/Desktop/code-graph-rag/examples/kotlin-grammer-case")
    # project_path = Path("/Users/cliffleopard/Desktop/CodeAgent/McpSdk/kotlin-sdk")

    if not project_path.exists():
        print(f"错误: 项目路径不存在: {project_path}")
        sys.exit(1)

    # 分析项目
    stats = analyze_kotlin_project(project_path)

    if not stats:
        print("解析失败!")
        sys.exit(1)

    # 打印统计信息
    print_stats(stats)

    # 打印示例数据
    print_sample_data(stats, sample_size=15)

    # 打印所有 call 关系
    print_all_calls(stats, max_display=100)  # 最多显示100个详细关系

    # 搜索特定模式
    search_specific_patterns(stats)

    # 验证结果
    passed = validate_parsing(stats)

    print(f"\n{'=' * 60}")
    if passed:
        print("✓ 所有基本验证通过!")
    else:
        print("✗ 部分验证失败!")
    print(f"{'=' * 60}\n")

    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
