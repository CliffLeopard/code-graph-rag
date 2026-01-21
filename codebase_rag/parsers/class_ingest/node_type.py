from __future__ import annotations

from loguru import logger
from tree_sitter import Node

from ... import constants as cs
from ... import logs
from ...types_defs import NodeType
from ..utils import safe_decode_with_fallback


def determine_node_type(
    class_node: Node,
    class_name: str | None,
    class_qn: str,
    language: cs.SupportedLanguage,
) -> NodeType:
    # (H) For Kotlin, check children to distinguish interface/enum from class
    # (H) since all use class_declaration node type
    if (
        language == cs.SupportedLanguage.KOTLIN
        and class_node.type == cs.TS_KOTLIN_CLASS_DECLARATION
    ):
        is_interface = False
        is_enum = False

        for child in class_node.children:
            # (H) Check for 'interface' keyword anywhere in children
            if child.type == "interface":
                is_interface = True
                break
            # (H) Check modifiers for enum class
            if child.type == "modifiers":
                for mod_child in child.children:
                    if mod_child.type == "class_modifier":
                        mod_text = safe_decode_with_fallback(mod_child)
                        if mod_text == "enum":
                            is_enum = True
                            break
            # (H) Stop at class body - we've seen all relevant children
            if child.type == "class_body":
                break

        if is_interface:
            logger.info(logs.CLASS_FOUND_INTERFACE.format(name=class_name, qn=class_qn))
            return NodeType.INTERFACE
        if is_enum:
            logger.info(logs.CLASS_FOUND_ENUM.format(name=class_name, qn=class_qn))
            return NodeType.ENUM
        # (H) Default to CLASS for regular Kotlin class declarations
        logger.info(logs.CLASS_FOUND_CLASS.format(name=class_name, qn=class_qn))
        return NodeType.CLASS

    match class_node.type:
        # (H) Note: TS_KOTLIN_INTERFACE_DECLARATION is aliased to class_declaration,
        # (H) but Kotlin classes are handled above, so this only matches non-Kotlin interfaces
        case cs.TS_INTERFACE_DECLARATION:
            logger.info(logs.CLASS_FOUND_INTERFACE.format(name=class_name, qn=class_qn))
            return NodeType.INTERFACE
        # (H) Note: Kotlin enum classes are handled above in Kotlin-specific check
        # (H) because TS_KOTLIN_ENUM_CLASS is aliased to 'class_declaration'
        case cs.TS_ENUM_DECLARATION | cs.TS_ENUM_SPECIFIER | cs.TS_ENUM_CLASS_SPECIFIER:
            logger.info(logs.CLASS_FOUND_ENUM.format(name=class_name, qn=class_qn))
            return NodeType.ENUM
        case cs.TS_TYPE_ALIAS_DECLARATION | cs.TS_KOTLIN_TYPE_ALIAS:
            logger.info(logs.CLASS_FOUND_TYPE.format(name=class_name, qn=class_qn))
            return NodeType.TYPE
        case cs.TS_STRUCT_SPECIFIER:
            logger.info(logs.CLASS_FOUND_STRUCT.format(name=class_name, qn=class_qn))
            return NodeType.CLASS
        case cs.TS_UNION_SPECIFIER:
            logger.info(logs.CLASS_FOUND_UNION.format(name=class_name, qn=class_qn))
            return NodeType.UNION
        case cs.CppNodeType.TEMPLATE_DECLARATION:
            node_type = extract_template_class_type(class_node) or NodeType.CLASS
            logger.info(
                logs.CLASS_FOUND_TEMPLATE.format(
                    node_type=node_type, name=class_name, qn=class_qn
                )
            )
            return node_type
        case cs.CppNodeType.FUNCTION_DEFINITION if language == cs.SupportedLanguage.CPP:
            log_exported_class_type(class_node, class_name, class_qn)
            return NodeType.CLASS
        case _:
            logger.info(logs.CLASS_FOUND_CLASS.format(name=class_name, qn=class_qn))
            return NodeType.CLASS


def log_exported_class_type(
    class_node: Node, class_name: str | None, class_qn: str
) -> None:
    node_text = safe_decode_with_fallback(class_node) if class_node.text else ""
    match _detect_export_type(node_text):
        case cs.CPP_EXPORT_STRUCT_PREFIX:
            logger.info(
                logs.CLASS_FOUND_EXPORTED_STRUCT.format(name=class_name, qn=class_qn)
            )
        case cs.CPP_EXPORT_UNION_PREFIX:
            logger.info(
                logs.CLASS_FOUND_EXPORTED_UNION.format(name=class_name, qn=class_qn)
            )
        case cs.CPP_EXPORT_TEMPLATE_PREFIX:
            logger.info(
                logs.CLASS_FOUND_EXPORTED_TEMPLATE.format(name=class_name, qn=class_qn)
            )
        case _:
            logger.info(
                logs.CLASS_FOUND_EXPORTED_CLASS.format(name=class_name, qn=class_qn)
            )


def _detect_export_type(node_text: str) -> str | None:
    return next(
        (prefix for prefix in cs.CPP_EXPORT_PREFIXES if prefix in node_text),
        None,
    )


def extract_template_class_type(template_node: Node) -> NodeType | None:
    for child in template_node.children:
        match child.type:
            case cs.CppNodeType.CLASS_SPECIFIER | cs.TS_STRUCT_SPECIFIER:
                return NodeType.CLASS
            case cs.TS_ENUM_SPECIFIER:
                return NodeType.ENUM
            case cs.TS_UNION_SPECIFIER:
                return NodeType.UNION
    return None
