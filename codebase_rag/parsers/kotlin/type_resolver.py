from collections.abc import Iterable
from typing import TYPE_CHECKING

from ... import constants as cs
from ...types_defs import ASTNode, NodeType
from .utils import (
    _extract_type_from_node,
    find_package_start_index,
    get_class_context_from_qn,
    get_root_node_from_module_qn,
    safe_decode_text,
)

if TYPE_CHECKING:
    from pathlib import Path

    from ...types_defs import ASTCacheProtocol, FunctionRegistryTrieProtocol
    from ..import_processor import ImportProcessor


class KotlinTypeResolverMixin:
    import_processor: "ImportProcessor"
    function_registry: "FunctionRegistryTrieProtocol"
    module_qn_to_file_path: dict[str, "Path"]
    ast_cache: "ASTCacheProtocol"
    _fqn_to_module_qn: dict[str, list[str]]

    def _module_qn_to_kotlin_fqn(self, module_qn: str) -> str | None:
        parts = module_qn.split(cs.SEPARATOR_DOT)
        package_start_idx = find_package_start_index(parts)
        if package_start_idx is None:
            return None
        class_parts = parts[package_start_idx:]
        return cs.SEPARATOR_DOT.join(class_parts) if class_parts else None

    def _calculate_module_distance(
        self, candidate_qn: str, caller_module_qn: str
    ) -> int:
        caller_parts = caller_module_qn.split(cs.SEPARATOR_DOT)
        candidate_parts = candidate_qn.split(cs.SEPARATOR_DOT)

        common_prefix = 0
        for caller_part, candidate_part in zip(caller_parts, candidate_parts):
            if caller_part == candidate_part:
                common_prefix += 1
            else:
                break

        base_distance = max(len(caller_parts), len(candidate_parts)) - common_prefix

        if (
            len(caller_parts) > 1
            and candidate_parts[: len(caller_parts) - 1] == caller_parts[:-1]
        ):
            base_distance -= 1

        return max(base_distance, 0)

    def _rank_module_candidates(
        self,
        candidates: list[str],
        class_qn: str,
        current_module_qn: str | None,
    ) -> list[str]:
        if not candidates or not current_module_qn:
            return candidates

        ranked: list[tuple[tuple[int, int, int], str]] = []
        for idx, candidate in enumerate(candidates):
            candidate_fqn = self._module_qn_to_kotlin_fqn(candidate)

            if candidate_fqn == class_qn:
                match_penalty = 0
            elif candidate_fqn and class_qn.endswith(candidate_fqn):
                match_penalty = 1
            else:
                match_penalty = 2

            distance = self._calculate_module_distance(candidate, current_module_qn)
            ranked.append(((match_penalty, distance, idx), candidate))

        ranked.sort(key=lambda item: item[0])
        return [candidate for _, candidate in ranked]

    def _find_registry_entries_under(self, prefix: str) -> Iterable[tuple[str, str]]:
        finder = getattr(self.function_registry, cs.METHOD_FIND_WITH_PREFIX, None)
        if callable(finder):
            if matches := list(finder(prefix)):
                return matches

        items = getattr(self.function_registry, cs.METHOD_ITEMS, None)
        if callable(items):
            prefix_with_dot = f"{prefix}{cs.SEPARATOR_DOT}"
            return [
                (qn, method_type)
                for qn, method_type in items()
                if qn.startswith(prefix_with_dot) or qn == prefix
            ]

        return []

    def _resolve_java_type_name(self, type_name: str, module_qn: str) -> str:
        """Resolve Kotlin type name to fully qualified name."""
        if not type_name:
            return "Any"  # (H) Kotlin's top-level type

        if cs.SEPARATOR_DOT in type_name:
            return type_name

        # (H) Kotlin uses nullable types with ? suffix
        is_nullable = type_name.endswith("?")
        base_type = type_name.rstrip("?")

        # (H) Kotlin primitive types (mapped to JVM types)
        kotlin_primitives = {
            "Int",
            "Long",
            "Double",
            "Float",
            "Boolean",
            "Char",
            "Byte",
            "Short",
        }
        if base_type in kotlin_primitives or base_type in cs.JAVA_PRIMITIVE_TYPES:
            return f"{base_type}?" if is_nullable else base_type

        # (H) Kotlin wrapper types (String, etc.)
        if base_type in cs.JAVA_WRAPPER_TYPES:
            # (H) Kotlin String is kotlin.String, but we use java.lang.String for compatibility
            resolved = f"{cs.JAVA_LANG_PREFIX}{base_type}"
            return f"{resolved}?" if is_nullable else resolved

        # (H) Kotlin uses Array<T> instead of T[]
        if base_type.startswith("Array<") and base_type.endswith(">"):
            inner_type = base_type[6:-1]
            resolved_inner = self._resolve_java_type_name(inner_type, module_qn)
            resolved = f"Array<{resolved_inner}>"
            return f"{resolved}?" if is_nullable else resolved

        if cs.CHAR_ANGLE_OPEN in base_type and cs.CHAR_ANGLE_CLOSE in base_type:
            base_type_only = base_type.split(cs.CHAR_ANGLE_OPEN)[0]
            resolved_base = self._resolve_java_type_name(base_type_only, module_qn)
            # (H) Reconstruct generic type
            generic_part = base_type.split(cs.CHAR_ANGLE_OPEN, 1)[1]
            resolved = f"{resolved_base}<{generic_part}"
            return f"{resolved}?" if is_nullable else resolved

        if module_qn in self.import_processor.import_mapping:
            import_map = self.import_processor.import_mapping[module_qn]
            if base_type in import_map:
                resolved = import_map[base_type]
                return f"{resolved}?" if is_nullable else resolved

        same_package_qn = f"{module_qn}{cs.SEPARATOR_DOT}{base_type}"
        if same_package_qn in self.function_registry and self.function_registry[
            same_package_qn
        ] in [NodeType.CLASS, NodeType.INTERFACE]:
            resolved = same_package_qn
            return f"{resolved}?" if is_nullable else resolved

        return type_name

    def _get_superclass_name(self, class_qn: str) -> str | None:
        ctx = get_class_context_from_qn(
            class_qn, self.module_qn_to_file_path, self.ast_cache
        )
        if not ctx:
            return None

        return self._find_superclass_using_ast(
            ctx.root_node, ctx.target_class_name, ctx.module_qn
        )

    def _find_superclass_using_ast(
        self, node: ASTNode, target_class_name: str, module_qn: str
    ) -> str | None:
        if node.type == cs.TS_KOTLIN_CLASS_DECLARATION:
            # (H) Check name field (type_identifier)
            name_node = node.child_by_field_name(cs.TS_FIELD_NAME)
            if not name_node:
                name_node = node.child_by_field_name("type_identifier")

            if name_node and safe_decode_text(name_node) == target_class_name:
                # (H) Check delegation_specifiers for superclass
                # (H) In Kotlin, the superclass can appear at any position in the delegation list.
                # (H) We iterate through all specifiers and check each one using function_registry
                # (H) to determine if it's a class (superclass) or interface.
                delegation_node = node.child_by_field_name("delegation_specifiers")
                if delegation_node:
                    specifiers = [
                        child
                        for child in delegation_node.children
                        if child.type == "delegation_specifier"
                    ]
                    # (H) Iterate through all specifiers to find the class (superclass)
                    # (H) Use robust type resolution to distinguish classes from interfaces
                    for specifier in specifiers:
                        if type_name := self._extract_type_name_from_node(specifier):
                            if not type_name:  # (H) Safety check
                                continue

                            # (H) Use unified type resolution to determine if it's a class
                            node_type = self._resolve_type_to_node_type(
                                type_name, module_qn
                            )
                            if node_type == NodeType.CLASS:
                                # (H) Return resolved type name
                                resolved_type = self._resolve_java_type_name(
                                    type_name, module_qn
                                )
                                if resolved_type:
                                    return resolved_type
                                # (H) Fallback to same package
                                same_package_qn = (
                                    f"{module_qn}{cs.SEPARATOR_DOT}{type_name}"
                                )
                                if same_package_qn in self.function_registry:
                                    return same_package_qn

                # (H) Also check supertype field (fallback, not mutually exclusive with delegation_specifiers)
                supertype_node = node.child_by_field_name("supertype")
                if supertype_node:
                    if superclass_name := self._extract_type_name_from_node(
                        supertype_node
                    ):
                        if superclass_name:  # (H) Safety check
                            resolved = self._resolve_java_type_name(
                                superclass_name, module_qn
                            )
                            if resolved:
                                return resolved

        for child in node.children:
            if result := self._find_superclass_using_ast(
                child, target_class_name, module_qn
            ):
                return result

        return None

    def _extract_type_name_from_node(self, parent_node: ASTNode) -> str | None:
        """Extract type name from various Kotlin type nodes"""
        return _extract_type_from_node(parent_node)

    def _get_implemented_interfaces(self, class_qn: str) -> list[str]:
        parts = class_qn.split(cs.SEPARATOR_DOT)
        if len(parts) < 2:
            return []

        module_qn = cs.SEPARATOR_DOT.join(parts[:-1])
        target_class_name = parts[-1]

        file_path = self.module_qn_to_file_path.get(module_qn)
        if file_path is None or file_path not in self.ast_cache:
            return []

        root_node, _ = self.ast_cache[file_path]

        return self._find_interfaces_using_ast(root_node, target_class_name, module_qn)

    def _find_interfaces_using_ast(
        self, node: ASTNode, target_class_name: str, module_qn: str
    ) -> list[str]:
        # (H) In tree-sitter-kotlin, both classes and interfaces use class_declaration
        if node.type == cs.TS_KOTLIN_CLASS_DECLARATION:
            # (H) Check name field
            name_node = node.child_by_field_name(cs.TS_FIELD_NAME)

            if name_node and safe_decode_text(name_node) == target_class_name:
                interface_list: list[str] = []

                # (H) Determine if this is an interface or class by checking children
                # (H) Note: interface keyword may not be the first child (e.g., after modifiers)
                is_interface = False
                for child in node.children:
                    if child.type == "interface":
                        is_interface = True
                        break
                    if child.type == "class_body":
                        break

                # (H) Check delegation_specifiers
                # (H) In Kotlin, the superclass can appear at any position in the delegation list.
                # (H) We iterate through all specifiers and check each one using function_registry
                # (H) to determine if it's a class (superclass) or interface.
                delegation_node = node.child_by_field_name("delegation_specifiers")
                if delegation_node:
                    specifiers = [
                        child
                        for child in delegation_node.children
                        if child.type == "delegation_specifier"
                    ]
                    # (H) For classes: iterate through all specifiers and only include interfaces
                    # (H) For interfaces: all delegation_specifiers are parent interfaces
                    # (H) Use robust type resolution to accurately distinguish classes from interfaces
                    for specifier in specifiers:
                        if type_name := self._extract_type_name_from_node(specifier):
                            if not type_name:  # (H) Safety check
                                continue

                            # (H) Use unified type resolution to determine type
                            specifier_node_type = self._resolve_type_to_node_type(
                                type_name, module_qn
                            )

                            # (H) Resolve type name for return value
                            resolved_type = self._resolve_java_type_name(
                                type_name, module_qn
                            )
                            if not resolved_type:
                                # (H) Fallback to same package
                                same_package_qn = (
                                    f"{module_qn}{cs.SEPARATOR_DOT}{type_name}"
                                )
                                if same_package_qn in self.function_registry:
                                    resolved_type = same_package_qn
                                else:
                                    resolved_type = type_name

                            # (H) For classes: only add interfaces (skip classes/superclass)
                            # (H) For interfaces: add all (they're all parent interfaces)
                            if is_interface:
                                # (H) For interface: add all (they're all parent interfaces)
                                interface_list.append(resolved_type)
                            elif specifier_node_type == NodeType.INTERFACE:
                                # (H) For class: only add if it's an interface
                                interface_list.append(resolved_type)
                            # (H) If type is unknown, skip it (don't assume it's an interface)
                            # (H) This avoids false positives and relies on proper type resolution

                # (H) Also check supertype field (fallback, not mutually exclusive with delegation_specifiers)
                supertype_node = node.child_by_field_name("supertype")
                if supertype_node:
                    self._extract_interface_names(
                        supertype_node, interface_list, module_qn
                    )
                return interface_list

        for child in node.children:
            if result := self._find_interfaces_using_ast(
                child, target_class_name, module_qn
            ):
                return result

        return []

    def _extract_interface_names(
        self, supertype_node: ASTNode, interface_list: list[str], module_qn: str
    ) -> None:
        if not supertype_node:  # (H) Safety check
            return
        for child in supertype_node.children:
            if interface_name := self._extract_type_name_from_node(child):
                if interface_name:  # (H) Safety check
                    resolved_interface = self._resolve_java_type_name(
                        interface_name, module_qn
                    )
                    if resolved_interface:  # (H) Safety check
                        interface_list.append(resolved_interface)

    def _get_current_class_name(self, module_qn: str) -> str | None:
        root_node = get_root_node_from_module_qn(
            module_qn, self.module_qn_to_file_path, self.ast_cache
        )
        if not root_node:
            return None

        class_names: list[str] = []
        self._traverse_for_class_declarations(root_node, class_names)

        return f"{module_qn}{cs.SEPARATOR_DOT}{class_names[0]}" if class_names else None

    def _traverse_for_class_declarations(
        self, node: ASTNode, class_names: list[str]
    ) -> None:
        # (H) In tree-sitter-kotlin, all class-like declarations use class_declaration
        # (H) or object_declaration node types
        if node.type in [
            cs.TS_KOTLIN_CLASS_DECLARATION,
            cs.TS_KOTLIN_OBJECT_DECLARATION,
        ]:
            name_node = node.child_by_field_name(cs.TS_FIELD_NAME)
            if name_node and (class_name := safe_decode_text(name_node)):
                class_names.append(class_name)

        for child in node.children:
            self._traverse_for_class_declarations(child, class_names)

    def _find_type_definition_in_ast(
        self, root_node: ASTNode, type_name: str, module_qn: str
    ) -> tuple[ASTNode | None, NodeType | None]:
        """
        Find a type definition in AST by name and return the node and its type.
        This is a fundamental solution to distinguish classes from interfaces.
        """
        if not root_node or not type_name:
            return None, None

        def traverse(node: ASTNode) -> tuple[ASTNode | None, NodeType | None]:
            if not node:
                return None, None

            # (H) Check if this is a class or object declaration
            # (H) Note: In Kotlin tree-sitter, all class-like declarations use class_declaration
            # (H) The distinction is made by checking the first child node type
            if node.type in [
                cs.TS_KOTLIN_CLASS_DECLARATION,
                cs.TS_KOTLIN_OBJECT_DECLARATION,
            ]:
                name_node = node.child_by_field_name(cs.TS_FIELD_NAME)
                if name_node:
                    node_name = safe_decode_text(name_node)
                    # (H) Check exact match or qualified match
                    if node_name == type_name:
                        # (H) Determine node type based on AST structure
                        if node.type == cs.TS_KOTLIN_OBJECT_DECLARATION:
                            return node, NodeType.CLASS

                        # (H) For class_declaration, check children to distinguish type
                        # (H) tree-sitter-kotlin uses: 'interface' keyword for interfaces,
                        # (H) 'class' keyword for classes, and 'modifiers' node for enum/data/sealed
                        # (H) Note: interface keyword may not be the first child (e.g., after modifiers)
                        is_interface = False
                        is_enum = False
                        for child in node.children:
                            if child.type == "interface":
                                is_interface = True
                                break
                            if child.type == "modifiers":
                                for mod_child in child.children:
                                    if mod_child.type == "class_modifier":
                                        mod_text = safe_decode_text(mod_child)
                                        if mod_text == "enum":
                                            is_enum = True
                                            break
                            if child.type == "class_body":
                                break
                        if is_interface:
                            return node, NodeType.INTERFACE
                        if is_enum:
                            return node, NodeType.ENUM
                        # (H) Default to CLASS for regular class declarations
                        return node, NodeType.CLASS

            # (H) Recursively search children
            for child in node.children:
                result_node, result_type = traverse(child)
                if result_node:
                    return result_node, result_type

            return None, None

        return traverse(root_node)

    def _resolve_type_to_node_type(
        self, type_name: str, module_qn: str
    ) -> NodeType | None:
        """
        Resolve a type name to its NodeType by checking function_registry and AST.
        This provides a robust way to distinguish classes from interfaces.
        """
        if not type_name:
            return None

        # (H) First check function_registry (fast path)
        resolved_type = self._resolve_java_type_name(type_name, module_qn)
        if resolved_type and resolved_type in self.function_registry:
            return self.function_registry[resolved_type]

        # (H) Also check same package
        same_package_qn = f"{module_qn}{cs.SEPARATOR_DOT}{type_name}"
        if same_package_qn in self.function_registry:
            return self.function_registry[same_package_qn]

        # (H) Fallback: search AST for type definition
        root_node = get_root_node_from_module_qn(
            module_qn, self.module_qn_to_file_path, self.ast_cache, min_parts=1
        )
        if root_node:
            _, node_type = self._find_type_definition_in_ast(
                root_node, type_name, module_qn
            )
            if node_type:
                return node_type

        return None
