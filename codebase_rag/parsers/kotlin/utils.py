from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, NamedTuple

from tree_sitter import Node  # type: ignore[reportMissingImports]

from ... import constants as cs
from ...models import MethodModifiersAndAnnotations
from ...types_defs import (
    ASTNode,
    JavaClassInfo,
    JavaFieldInfo,
    JavaMethodCallInfo,
    JavaMethodInfo,
)
from ..utils import safe_decode_text

if TYPE_CHECKING:
    from ...types_defs import ASTCacheProtocol


class ClassContext(NamedTuple):
    module_qn: str
    target_class_name: str
    root_node: Node


def get_root_node_from_module_qn(
    module_qn: str,
    module_qn_to_file_path: dict[str, Path],
    ast_cache: ASTCacheProtocol,
    min_parts: int = 2,
) -> Node | None:
    parts = module_qn.split(cs.SEPARATOR_DOT)
    if len(parts) < min_parts:
        return None

    file_path = module_qn_to_file_path.get(module_qn)
    if file_path is None or file_path not in ast_cache:
        return None

    root_node, _ = ast_cache[file_path]
    return root_node


def get_class_context_from_qn(
    class_qn: str,
    module_qn_to_file_path: dict[str, Path],
    ast_cache: ASTCacheProtocol,
) -> ClassContext | None:
    parts = class_qn.split(cs.SEPARATOR_DOT)
    if len(parts) < 2:
        return None

    module_qn = cs.SEPARATOR_DOT.join(parts[:-1])
    target_class_name = parts[-1]

    root_node = get_root_node_from_module_qn(
        module_qn, module_qn_to_file_path, ast_cache, min_parts=1
    )
    if root_node is None:
        return None

    return ClassContext(module_qn, target_class_name, root_node)


def extract_package_name(package_node: ASTNode) -> str | None:
    if not package_node:  # (H) Safety check
        return None

    if package_node.type != cs.TS_KOTLIN_PACKAGE_HEADER:
        return None

    # (H) Kotlin package header contains qualified_identifier or identifier
    # (H) Look for the identifier path in the package header
    def extract_qualified_parts(node: ASTNode) -> list[str]:
        """Recursively extract parts from qualified_identifier or qualified_expression"""
        parts: list[str] = []
        for child in node.children:
            if child.type == cs.TS_KOTLIN_IDENTIFIER:
                if part := safe_decode_text(child):
                    parts.append(part)
            elif child.type in ["qualified_expression", "qualified_identifier"]:
                # (H) Recursively extract from nested qualified structure
                nested_parts = extract_qualified_parts(child)
                parts.extend(nested_parts)
        return parts

    for child in package_node.children:
        if child.type in ["qualified_expression", "qualified_identifier"]:
            parts = extract_qualified_parts(child)
            if parts:
                return cs.SEPARATOR_DOT.join(parts)
        elif child.type == cs.TS_KOTLIN_IDENTIFIER:
            if result := safe_decode_text(child):
                return result
        elif child.type in ["scoped_identifier", "identifier"]:
            if result := safe_decode_text(child):
                return result

    return None


def extract_import_path(import_node: ASTNode) -> dict[str, str]:
    if not import_node:  # (H) Safety check
        return {}

    # (H) Handle import node (tree-sitter-kotlin uses "import" type)
    # (H) Structure: import > qualified_identifier | identifier
    if import_node.type == cs.TS_KOTLIN_IMPORT:
        imports: dict[str, str] = {}
        imported_path_parts: list[str] = []
        alias: str | None = None
        is_wildcard = False
        seen_as = False

        for child in import_node.children:
            if child.type == "qualified_identifier":
                # (H) qualified_identifier contains multiple identifier children
                parts = []
                for id_child in child.children:
                    if id_child.type == cs.TS_KOTLIN_IDENTIFIER:
                        if part := safe_decode_text(id_child):
                            parts.append(part)
                imported_path_parts = parts
            elif child.type == cs.TS_KOTLIN_IDENTIFIER:
                if seen_as and not alias:
                    alias = safe_decode_text(child)
                elif not imported_path_parts:
                    if part := safe_decode_text(child):
                        imported_path_parts.append(part)
            elif child.type in ["asterisk", "*"]:
                is_wildcard = True
            elif child.type == "as":
                seen_as = True

        if imported_path_parts:
            imported_path = cs.SEPARATOR_DOT.join(imported_path_parts)
            if is_wildcard:
                wildcard_key = f"*{imported_path}"
                imports[wildcard_key] = imported_path
            elif alias:
                imports[alias] = imported_path
            else:
                imported_name = imported_path_parts[-1]
                imports[imported_name] = imported_path
        return imports

    # (H) Handle alternative Kotlin import patterns
    # (H) (may occur in different tree-sitter-kotlin grammar versions)
    if import_node.type in ["import_list", "import_directive"]:
        imports: dict[str, str] = {}
        if import_node.type == "import_list":
            for child in import_node.children:
                if child.type in ["import_directive", cs.TS_KOTLIN_IMPORT]:
                    imports.update(extract_import_path(child))
            return imports

    # (H) Alternative handling for import_directive (different grammar versions)
    imports: dict[str, str] = {}
    imported_path_parts: list[str] = []
    is_wildcard = False
    alias: str | None = None
    seen_as = False

    # (H) Handle import_directive - extract qualified path
    # (H) Process children in order to handle: qualified_path [as alias] or qualified_path.*
    children_list = list(import_node.children)
    i = 0
    while i < len(children_list):
        child = children_list[i]
        if child.type == "qualified_expression":
            # (H) Extract full qualified name
            parts: list[str] = []

            def extract_qualified(node: ASTNode) -> None:
                for subchild in node.children:
                    if subchild.type in [
                        cs.TS_KOTLIN_IDENTIFIER,
                        cs.TS_KOTLIN_SIMPLE_IDENTIFIER,
                    ]:
                        if part := safe_decode_text(subchild):
                            parts.append(part)
                    elif subchild.type == "qualified_expression":
                        extract_qualified(subchild)

            extract_qualified(child)
            imported_path_parts = parts
        elif child.type in [
            cs.TS_KOTLIN_IDENTIFIER,
            cs.TS_KOTLIN_SIMPLE_IDENTIFIER,
            "scoped_identifier",
        ]:
            # (H) Check if this is an alias (comes after "as")
            if seen_as and not alias:
                alias = safe_decode_text(child)
            elif not imported_path_parts:  # (H) First identifier (not alias)
                if part := safe_decode_text(child):
                    imported_path_parts.append(part)
        elif child.type == "asterisk":
            is_wildcard = True
        elif child.type == "as":
            seen_as = True
        i += 1

    if not imported_path_parts:
        return imports

    imported_path = cs.SEPARATOR_DOT.join(imported_path_parts)

    if is_wildcard:
        wildcard_key = f"*{imported_path}"
        imports[wildcard_key] = imported_path
    elif alias:
        imports[alias] = imported_path
    else:
        imported_name = imported_path_parts[-1]
        imports[imported_name] = imported_path

    return imports


def _extract_all_delegation_specifiers(class_node: ASTNode) -> list[ASTNode]:
    """Extract all delegation_specifier nodes from a class or interface declaration."""
    if not class_node:  # (H) Safety check
        return []
    delegation_node = class_node.child_by_field_name("delegation_specifiers")
    if not delegation_node:
        return []
    if not hasattr(delegation_node, "children"):  # (H) Safety check
        return []
    return [
        child
        for child in delegation_node.children
        if child and child.type == "delegation_specifier"
    ]


def _extract_superclass(class_node: ASTNode) -> str | None:
    # (H) Kotlin uses delegation_specifiers for classes with superclass
    # (H) FUNDAMENTAL LIMITATION: This function is called during AST extraction phase,
    # (H) before the type registry is built. Therefore, we cannot use function_registry
    # (H) to distinguish classes from interfaces. The proper resolution happens later
    # (H) in type_resolver.py using _resolve_type_to_node_type() which can access
    # (H) function_registry and AST traversal.
    # (H) This function returns the first delegation_specifier as a conservative guess.
    # (H) The actual superclass detection with proper type resolution is handled by
    # (H) KotlinTypeResolverMixin._find_superclass_using_ast() which uses function_registry.
    if class_node.type != cs.TS_KOTLIN_CLASS_DECLARATION:
        return None

    specifiers = _extract_all_delegation_specifiers(class_node)
    # (H) Return first specifier as conservative guess (proper resolution in type_resolver)
    if specifiers:
        return _extract_type_from_node(specifiers[0])

    # (H) Also check supertype field (fallback)
    supertype_node = class_node.child_by_field_name("supertype")
    if supertype_node:
        return _extract_type_from_node(supertype_node)

    return None


def _extract_type_from_node(node: ASTNode) -> str | None:
    """Extract type name from a type node (user_type, type_identifier, etc.)"""
    if not node:  # (H) Safety check
        return None

    if node.type == cs.TS_KOTLIN_TYPE_IDENTIFIER:
        result = safe_decode_text(node)
        return result if result else None
    elif node.type == cs.TS_KOTLIN_USER_TYPE:
        # (H) user_type contains type_identifier or nested user_type
        parts = []
        if not hasattr(node, "children"):  # (H) Safety check
            return None
        for child in node.children:
            if not child:  # (H) Safety check
                continue
            if child.type == cs.TS_KOTLIN_TYPE_IDENTIFIER:
                if part := safe_decode_text(child):
                    parts.append(part)
            elif child.type == cs.TS_KOTLIN_USER_TYPE:
                if nested_type := _extract_type_from_node(child):
                    parts.append(nested_type)
        return cs.SEPARATOR_DOT.join(parts) if parts else None
    elif node.type == "delegation_specifier":
        # (H) Extract type from delegation_specifier
        if not hasattr(node, "children"):  # (H) Safety check
            return None
        for child in node.children:
            if not child:  # (H) Safety check
                continue
            if result := _extract_type_from_node(child):
                return result
    return None


def _extract_interface_name(type_child: ASTNode) -> str | None:
    return _extract_type_from_node(type_child)


def _extract_interfaces(class_node: ASTNode) -> list[str]:
    # (H) Kotlin uses delegation_specifiers for both superclass and interfaces
    # (H) FUNDAMENTAL LIMITATION: This function is called during AST extraction phase,
    # (H) before the type registry is built. Therefore, we cannot use function_registry
    # (H) to distinguish classes from interfaces. The proper resolution happens later
    # (H) in type_resolver.py using _resolve_type_to_node_type() which can access
    # (H) function_registry and AST traversal.
    # (H) This function uses a conservative approach: for classes, skip the first
    # (H) delegation_specifier (might be superclass). The actual interface detection
    # (H) with proper type resolution is handled by KotlinTypeResolverMixin._find_interfaces_using_ast().
    interfaces: list[str] = []

    specifiers = _extract_all_delegation_specifiers(class_node)
    # (H) For classes: conservatively skip first (might be superclass, proper resolution in type_resolver)
    # (H) For interfaces: all are parent interfaces
    start_idx = 1 if class_node.type == cs.TS_KOTLIN_CLASS_DECLARATION else 0
    for specifier in specifiers[start_idx:]:
        if interface_name := _extract_type_from_node(specifier):
            interfaces.append(interface_name)

    # (H) Also check supertype field (for interface declarations)
    supertype_node = class_node.child_by_field_name("supertype")
    if supertype_node and class_node.type == cs.TS_KOTLIN_INTERFACE_DECLARATION:
        for child in supertype_node.children:
            if interface_name := _extract_interface_name(child):
                interfaces.append(interface_name)

    return interfaces


def _extract_type_parameters(class_node: ASTNode) -> list[str]:
    if not class_node:  # (H) Safety check
        return []

    type_params_node = class_node.child_by_field_name("type_parameters")
    if not type_params_node:
        return []

    type_parameters: list[str] = []
    if not hasattr(type_params_node, "children"):  # (H) Safety check
        return []

    for child in type_params_node.children:
        if not child:  # (H) Safety check
            continue
        if child.type == "type_parameter":
            # (H) Kotlin type parameter name is in type_identifier field
            name_node = child.child_by_field_name("name")
            if not name_node:
                name_node = child.child_by_field_name("type_identifier")
            if name_node:
                if param_name := safe_decode_text(name_node):
                    type_parameters.append(param_name)

    return type_parameters


def extract_from_modifiers_node(
    node: ASTNode, allowed_modifiers: frozenset[str]
) -> MethodModifiersAndAnnotations:
    result = MethodModifiersAndAnnotations()
    # (H) Kotlin has a modifiers node that contains modifier and annotation children
    modifiers_node = None
    for child in node.children:
        if child.type == "modifiers":
            modifiers_node = child
            break

    if modifiers_node:
        for modifier_child in modifiers_node.children:
            if modifier_child.type == "modifier":
                modifier_text = safe_decode_text(modifier_child)
                if modifier_text:
                    # (H) Check if it's an allowed modifier
                    if modifier_text in allowed_modifiers or not allowed_modifiers:
                        result.modifiers.append(modifier_text)
            elif modifier_child.type == "annotation":
                # (H) Extract annotation name from user_type
                annotation_name = _extract_annotation_name(modifier_child)
                if annotation_name:
                    result.annotations.append(annotation_name)

    # (H) Also check for direct annotation children (outside modifiers)
    for child in node.children:
        if child.type == "annotation":
            annotation_name = _extract_annotation_name(child)
            if annotation_name:
                result.annotations.append(annotation_name)

    return result


def _extract_annotation_name(annotation_node: ASTNode) -> str | None:
    """Extract annotation name from annotation node"""
    # (H) Annotation contains user_type with type_identifier
    for child in annotation_node.children:
        if child.type == cs.TS_KOTLIN_USER_TYPE:
            return _extract_type_from_node(child)
        elif child.type == cs.TS_KOTLIN_TYPE_IDENTIFIER:
            return safe_decode_text(child)
    return None


def _extract_class_modifiers(class_node: ASTNode) -> list[str]:
    # (H) Kotlin has additional modifiers like 'data', 'sealed', 'open', 'inline', etc.
    # (H) We extract all modifiers and filter later if needed
    # (H) Kotlin class modifiers (data, sealed, enum, etc.)
    # (H) but will still be extracted by extract_from_modifiers_node
    result = extract_from_modifiers_node(
        class_node, frozenset()
    )  # (H) Empty set = extract all
    return result.modifiers


def extract_class_info(class_node: ASTNode) -> JavaClassInfo:
    if not class_node:  # (H) Safety check
        return JavaClassInfo(
            name=None,
            type="",
            superclass=None,
            interfaces=[],
            modifiers=[],
            type_parameters=[],
        )

    if class_node.type not in cs.SPEC_KOTLIN_CLASS_TYPES:
        return JavaClassInfo(
            name=None,
            type="",
            superclass=None,
            interfaces=[],
            modifiers=[],
            type_parameters=[],
        )

    name: str | None = None
    # (H) Kotlin class name is in type_identifier field
    if name_node := class_node.child_by_field_name(cs.TS_FIELD_NAME):
        name = safe_decode_text(name_node)
    elif name_node := class_node.child_by_field_name("type_identifier"):
        name = safe_decode_text(name_node)

    # (H) Determine class type based on node structure
    # (H) In tree-sitter-kotlin, all class-like declarations use class_declaration
    # (H) The distinction is made by checking the first child node type
    class_type = _determine_class_type(class_node)

    return JavaClassInfo(
        name=name,
        type=class_type,
        superclass=_extract_superclass(class_node),
        interfaces=_extract_interfaces(class_node),
        modifiers=_extract_class_modifiers(class_node),
        type_parameters=_extract_type_parameters(class_node),
    )


def _determine_class_type(class_node: ASTNode) -> str:
    """Determine the actual class type (class, interface, enum, object) based on AST structure."""
    node_type = class_node.type

    # (H) Handle object_declaration and companion_object directly
    if node_type == cs.TS_KOTLIN_OBJECT_DECLARATION:
        return "object"
    if node_type == cs.TS_KOTLIN_COMPANION_OBJECT:
        return "object"
    if node_type == cs.TS_KOTLIN_TYPE_ALIAS:
        return "typealias"

    # (H) For class_declaration, check children to distinguish class/interface/enum
    # (H) Note: interface keyword may not be the first child (e.g., after 'public' modifier)
    if node_type == cs.TS_KOTLIN_CLASS_DECLARATION and class_node.children:
        for child in class_node.children:
            # (H) Check for 'interface' keyword anywhere in children
            if child.type == "interface":
                return "interface"
            # (H) Check modifiers for enum/data/sealed class
            if child.type == "modifiers":
                for mod_child in child.children:
                    if mod_child.type == "class_modifier":
                        mod_text = safe_decode_text(mod_child)
                        if mod_text == "enum":
                            return "enum"
                        # (H) data and sealed are still classes
            # (H) Stop at class body - we've seen all relevant children
            if child.type == "class_body":
                break
        # (H) Default to class
        return "class"

    # (H) Fallback: use simple string replacement for unknown node types
    return node_type.replace("_declaration", "").replace("_class", "")


def _get_method_type(method_node: ASTNode) -> str:
    if method_node.type == cs.TS_KOTLIN_CONSTRUCTOR:
        return "constructor"  # (H) Kotlin constructor
    return "method"  # (H) Kotlin method/function


def _extract_method_return_type(method_node: ASTNode) -> str | None:
    if method_node.type != cs.TS_KOTLIN_FUNCTION_DECLARATION:
        return None
    # (H) Kotlin functions can have return type in "type" field or "return_type" field
    if type_node := method_node.child_by_field_name(cs.TS_FIELD_TYPE):
        # (H) Could be type_identifier, user_type, etc.
        if type_node.type == cs.TS_KOTLIN_TYPE_IDENTIFIER:
            return safe_decode_text(type_node)
        elif type_node.type == cs.TS_KOTLIN_USER_TYPE:
            return _extract_type_from_node(type_node)
        else:
            return safe_decode_text(type_node)
    # (H) Also check return_type field
    if return_type_node := method_node.child_by_field_name("return_type"):
        if return_type_node.type == cs.TS_KOTLIN_TYPE_IDENTIFIER:
            return safe_decode_text(return_type_node)
        elif return_type_node.type == cs.TS_KOTLIN_USER_TYPE:
            return _extract_type_from_node(return_type_node)
        else:
            return safe_decode_text(return_type_node)
    # (H) Kotlin allows type inference - no explicit return type means Unit (void)
    return None


def _extract_formal_param_type(param_node: ASTNode) -> str | None:
    """Extract parameter type from Kotlin parameter node"""
    if param_type_node := param_node.child_by_field_name(cs.TS_FIELD_TYPE):
        # (H) Handle different type node structures
        if param_type_node.type == cs.TS_KOTLIN_TYPE_IDENTIFIER:
            return safe_decode_text(param_type_node)
        elif param_type_node.type == cs.TS_KOTLIN_USER_TYPE:
            return _extract_type_from_node(param_type_node)
        else:
            return safe_decode_text(param_type_node)
    return None


def _extract_method_parameters(method_node: ASTNode) -> list[str]:
    params_node = method_node.child_by_field_name(cs.TS_FIELD_PARAMETERS)
    if not params_node:
        return []

    parameters: list[str] = []
    for child in params_node.children:
        if child.type == cs.TS_KOTLIN_PARAMETER:
            param_type: str | None = _extract_formal_param_type(child)
            if param_type:
                parameters.append(param_type)
            else:
                # (H) Kotlin allows type inference - use Any as placeholder
                parameters.append(
                    "Any"
                )  # (H) Kotlin's top-level type for inferred parameters

    return parameters


def extract_method_info(method_node: ASTNode) -> JavaMethodInfo:
    if not method_node:  # (H) Safety check
        return JavaMethodInfo(
            name=None,
            type="",
            return_type=None,
            parameters=[],
            modifiers=[],
            type_parameters=[],
            annotations=[],
        )

    if method_node.type not in cs.SPEC_KOTLIN_FUNCTION_TYPES:
        return JavaMethodInfo(
            name=None,
            type="",
            return_type=None,
            parameters=[],
            modifiers=[],
            type_parameters=[],
            annotations=[],
        )

    # (H) Kotlin has additional modifiers like 'inline', 'suspend', 'operator', etc.
    # (H) Extract all modifiers (empty set means extract all)
    mods_and_annots = extract_from_modifiers_node(method_node, frozenset())

    # (H) Kotlin function name is in simple_identifier field
    name_node = method_node.child_by_field_name(cs.TS_FIELD_NAME)
    if not name_node:
        name_node = method_node.child_by_field_name("simple_identifier")

    return JavaMethodInfo(
        name=safe_decode_text(name_node) if name_node else None,
        type=_get_method_type(method_node),
        return_type=_extract_method_return_type(method_node),
        parameters=_extract_method_parameters(method_node),
        modifiers=mods_and_annots.modifiers,
        type_parameters=[],
        annotations=mods_and_annots.annotations,
    )


def extract_field_info(field_node: ASTNode) -> JavaFieldInfo:
    if not field_node:  # (H) Safety check
        return JavaFieldInfo(
            name=None,
            type=None,
            modifiers=[],
            annotations=[],
        )

    if field_node.type != cs.TS_KOTLIN_PROPERTY_DECLARATION:
        return JavaFieldInfo(
            name=None,
            type=None,
            modifiers=[],
            annotations=[],
        )

    field_type: str | None = None
    if type_node := field_node.child_by_field_name(cs.TS_FIELD_TYPE):
        field_type = safe_decode_text(type_node)

    name: str | None = None
    # (H) Kotlin property name is in variable_declaration > simple_identifier
    if variable_decl := field_node.child_by_field_name("variable_declaration"):
        if name_node := variable_decl.child_by_field_name(cs.TS_FIELD_NAME):
            name = safe_decode_text(name_node)
        elif name_node := variable_decl.child_by_field_name("simple_identifier"):
            name = safe_decode_text(name_node)
    elif name_node := field_node.child_by_field_name(cs.TS_FIELD_NAME):
        name = safe_decode_text(name_node)
    elif name_node := field_node.child_by_field_name("simple_identifier"):
        name = safe_decode_text(name_node)

    # (H) Kotlin properties can have modifiers like 'lateinit', 'const', etc.
    # (H) Extract all modifiers (empty set means extract all)
    mods_and_annots = extract_from_modifiers_node(field_node, frozenset())

    return JavaFieldInfo(
        name=name,
        type=field_type,
        modifiers=mods_and_annots.modifiers,
        annotations=mods_and_annots.annotations,
    )


def _extract_call_name_and_object(node: ASTNode) -> tuple[str | None, str | None]:
    """Extract method name and object (receiver) from a call expression node."""
    name: str | None = None
    obj: str | None = None

    if node.type == cs.TS_KOTLIN_IDENTIFIER:
        # (H) Simple identifier call like println()
        name = safe_decode_text(node)
    elif node.type == cs.TS_KOTLIN_NAVIGATION_EXPRESSION:
        # (H) navigation_expression: receiver.method
        # (H) Try to get field and receiver from fields first (for mock nodes)
        field_node = node.child_by_field_name("field")
        receiver_node = node.child_by_field_name("receiver")

        if field_node:
            name = safe_decode_text(field_node)
        if receiver_node:
            if receiver_node.type in {"this", "this_expression"}:
                obj = "this"
            elif receiver_node.type == cs.TS_KOTLIN_NAVIGATION_EXPRESSION:
                # (H) Nested navigation: outer.inner.method -> extract inner as object
                _, nested_obj = _extract_call_name_and_object(receiver_node)
                if nested_obj:
                    obj = nested_obj
                else:
                    obj = safe_decode_text(receiver_node)
            else:
                obj = safe_decode_text(receiver_node)

        # (H) Fallback: traverse children for real tree-sitter nodes
        if not name or not obj:
            for child in node.children:
                if child.type == "navigation_suffix":
                    for suffix_child in child.children:
                        if suffix_child.type == cs.TS_KOTLIN_IDENTIFIER:
                            name = safe_decode_text(suffix_child)
                elif child.type == cs.TS_KOTLIN_IDENTIFIER:
                    if obj is None:
                        obj = safe_decode_text(child)
                elif child.type in {"this_expression", "this"}:
                    obj = "this"
    elif node.type in {"this", "this_expression"}:
        obj = "this"
    else:
        # (H) Fallback: try to get text
        name = safe_decode_text(node)

    return name, obj


def extract_method_call_info(call_node: ASTNode) -> JavaMethodCallInfo | None:
    if not call_node:  # (H) Safety check
        return None

    # (H) Support both call_expression, navigation_expression, and constructor_invocation
    if call_node.type not in [
        cs.TS_KOTLIN_CALL_EXPRESSION,
        cs.TS_KOTLIN_NAVIGATION_EXPRESSION,
        cs.TS_KOTLIN_CONSTRUCTOR_INVOCATION,
    ]:
        return None

    name: str | None = None
    obj: str | None = None

    # (H) Handle constructor_invocation (new instances)
    if call_node.type == cs.TS_KOTLIN_CONSTRUCTOR_INVOCATION:
        # (H) constructor_invocation contains type and value_arguments
        for child in call_node.children:
            if child.type == cs.TS_KOTLIN_USER_TYPE:
                name = _extract_type_from_node(child)
                break
            elif child.type == cs.TS_KOTLIN_IDENTIFIER:
                name = safe_decode_text(child)
                break
    # (H) Kotlin call expressions structure:
    # (H) call_expression > expression (navigation_expression or identifier) > value_arguments
    elif call_node.type == cs.TS_KOTLIN_CALL_EXPRESSION:
        # (H) Try to get callee from field first (for mock nodes)
        callee_node = call_node.child_by_field_name("value")
        if not callee_node:
            callee_node = call_node.child_by_field_name("expression")

        if callee_node:
            name, obj = _extract_call_name_and_object(callee_node)
        else:
            # (H) Fallback: First child is usually the expression being called
            for child in call_node.children:
                if child.type == cs.TS_KOTLIN_IDENTIFIER:
                    name = safe_decode_text(child)
                    break
                elif child.type == cs.TS_KOTLIN_NAVIGATION_EXPRESSION:
                    name, obj = _extract_call_name_and_object(child)
                    break
    elif call_node.type == cs.TS_KOTLIN_NAVIGATION_EXPRESSION:
        # (H) Direct navigation expression (property access, not call)
        name, obj = _extract_call_name_and_object(call_node)

    arguments = 0
    # (H) Kotlin call expressions have value_arguments field
    args_node = call_node.child_by_field_name(cs.TS_FIELD_ARGUMENTS)
    if not args_node:
        args_node = call_node.child_by_field_name("value_arguments")
    # (H) Also check for direct value_arguments child
    if not args_node:
        for child in call_node.children:
            if child.type == "value_arguments":
                args_node = child
                break

    if args_node:
        # (H) Count value_argument nodes (Kotlin specific)
        arguments = sum(
            1 for child in args_node.children if child.type == "value_argument"
        )
        # (H) Fallback: count non-delimiter children
        if not arguments:
            arguments = sum(
                1
                for child in args_node.children
                if child.type not in cs.DELIMITER_TOKENS
            )

    return JavaMethodCallInfo(name=name, object=obj, arguments=arguments)


def find_package_start_index(parts: list[str]) -> int | None:
    for i, part in enumerate(parts):
        # (H) Kotlin is a JVM language, check for kotlin path
        if part in cs.JAVA_JVM_LANGUAGES and i > 0:
            return i + 1

        # (H) Kotlin source files are typically in src/main/kotlin or src/kotlin
        if part == cs.JAVA_PATH_SRC and i + 1 < len(parts):
            next_part = parts[i + 1]

            if (
                next_part not in cs.JAVA_JVM_LANGUAGES
                and next_part not in cs.JAVA_SRC_FOLDERS
            ):
                return i + 1

            if _is_non_standard_kotlin_src_layout(parts, i):
                return i + 1

    return None


def _is_non_standard_kotlin_src_layout(parts: list[str], src_idx: int) -> bool:
    if src_idx + 2 >= len(parts):
        return False

    next_part = parts[src_idx + 1]
    part_after_next = parts[src_idx + 2]

    return (
        next_part in (cs.JAVA_PATH_MAIN, cs.JAVA_PATH_TEST)
        and part_after_next not in cs.JAVA_JVM_LANGUAGES
    )
