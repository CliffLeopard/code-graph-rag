from abc import abstractmethod
from typing import TYPE_CHECKING

from loguru import logger  # type: ignore[reportMissingImports]

from ... import constants as cs
from ... import logs as ls
from ...types_defs import ASTNode
from ..utils import safe_decode_text
from .utils import (
    _extract_type_from_node,
    extract_class_info,
    extract_field_info,
    extract_method_call_info,
    get_root_node_from_module_qn,
)

if TYPE_CHECKING:
    from pathlib import Path

    from ...types_defs import ASTCacheProtocol


class KotlinVariableAnalyzerMixin:
    ast_cache: "ASTCacheProtocol"
    module_qn_to_file_path: dict[str, "Path"]
    _lookup_cache: dict[str, str | None]
    _lookup_in_progress: set[str]

    @abstractmethod
    def _resolve_java_type_name(self, type_name: str, module_qn: str) -> str: ...

    @abstractmethod
    def _resolve_java_method_return_type(
        self, method_call: str, module_qn: str
    ) -> str | None: ...

    @abstractmethod
    def _find_containing_java_class(self, node: ASTNode) -> ASTNode | None: ...

    @abstractmethod
    def build_variable_type_map(
        self, scope_node: ASTNode, module_qn: str
    ) -> dict[str, str]: ...

    def _collect_all_variable_types(
        self, scope_node: ASTNode, local_var_types: dict[str, str], module_qn: str
    ) -> None:
        self._analyze_java_parameters(scope_node, local_var_types, module_qn)
        self._analyze_java_local_variables(scope_node, local_var_types, module_qn)
        self._analyze_java_class_fields(scope_node, local_var_types, module_qn)
        self._analyze_java_constructor_assignments(
            scope_node, local_var_types, module_qn
        )
        self._analyze_java_enhanced_for_loops(scope_node, local_var_types, module_qn)

    def _analyze_java_parameters(
        self, scope_node: ASTNode, local_var_types: dict[str, str], module_qn: str
    ) -> None:
        params_node = scope_node.child_by_field_name(cs.FIELD_PARAMETERS)
        if not params_node:
            return

        for child in params_node.children:
            match child.type:
                case cs.TS_KOTLIN_PARAMETER:  # (H) Kotlin uses "parameter"
                    self._process_formal_parameter(child, local_var_types, module_qn)
                case cs.TS_SPREAD_PARAMETER:
                    self._process_spread_parameter(child, local_var_types, module_qn)

    def _process_formal_parameter(
        self, param_node: ASTNode, local_var_types: dict[str, str], module_qn: str
    ) -> None:
        # (H) Kotlin parameter: simple_identifier : type
        param_name_node = param_node.child_by_field_name(cs.FIELD_NAME)
        if not param_name_node:
            param_name_node = param_node.child_by_field_name(
                cs.TS_KOTLIN_SIMPLE_IDENTIFIER
            )

        param_type_node = param_node.child_by_field_name(cs.FIELD_TYPE)

        if not param_name_node:
            return

        param_name = safe_decode_text(param_name_node)
        if not param_name:
            return

        # (H) Extract type from type node (could be user_type, type_identifier, etc.)
        param_type: str | None = None
        if param_type_node:
            # (H) Try to extract type from various type node structures
            if param_type_node.type == cs.TS_KOTLIN_TYPE_IDENTIFIER:
                param_type = safe_decode_text(param_type_node)
            elif param_type_node.type == cs.TS_KOTLIN_USER_TYPE:
                # (H) Extract from user_type
                param_type = _extract_type_from_node(param_type_node)
            else:
                param_type = safe_decode_text(param_type_node)

        if param_type:
            resolved_type = self._resolve_java_type_name(param_type, module_qn)
            local_var_types[param_name] = resolved_type
            logger.debug(ls.JAVA_PARAM.format(name=param_name, type=resolved_type))
        else:
            # (H) Kotlin allows type inference, so parameter might not have explicit type
            # (H) We'll use Any as fallback
            local_var_types[param_name] = cs.JAVA_TYPE_OBJECT
            logger.debug(
                ls.JAVA_PARAM.format(name=param_name, type=cs.JAVA_TYPE_OBJECT)
            )

    def _process_spread_parameter(
        self, param_node: ASTNode, local_var_types: dict[str, str], module_qn: str
    ) -> None:
        param_name = None
        param_type = None

        for subchild in param_node.children:
            if subchild.type == cs.TS_TYPE_IDENTIFIER:
                if decoded_text := safe_decode_text(subchild):
                    param_type = f"{decoded_text}{cs.JAVA_ARRAY_SUFFIX}"
            elif subchild.type == cs.TS_VARIABLE_DECLARATOR:
                if name_node := subchild.child_by_field_name(cs.FIELD_NAME):
                    param_name = safe_decode_text(name_node)

        if param_name and param_type:
            resolved_type = self._resolve_java_type_name(param_type, module_qn)
            local_var_types[param_name] = resolved_type
            logger.debug(
                ls.JAVA_VARARGS_PARAM.format(name=param_name, type=resolved_type)
            )

    def _analyze_java_local_variables(
        self, scope_node: ASTNode, local_var_types: dict[str, str], module_qn: str
    ) -> None:
        self._traverse_for_local_variables(scope_node, local_var_types, module_qn)

    def _traverse_for_local_variables(
        self, node: ASTNode, local_var_types: dict[str, str], module_qn: str
    ) -> None:
        # (H) Kotlin uses property_declaration for both class properties and local variables
        if node.type in [
            cs.TS_LOCAL_VARIABLE_DECLARATION,
            cs.TS_KOTLIN_PROPERTY_DECLARATION,
            "variable_declaration",
        ]:
            self._process_java_variable_declaration(node, local_var_types, module_qn)

        for child in node.children:
            self._traverse_for_local_variables(child, local_var_types, module_qn)

    def _process_java_variable_declaration(
        self, decl_node: ASTNode, local_var_types: dict[str, str], module_qn: str
    ) -> None:
        # (H) Kotlin variable declarations can be:
        # (H) 1. property_declaration with variable_declaration and type
        # (H) 2. variable_declaration directly
        # (H) 3. local_variable_declaration (Java style, for compatibility)

        # (H) Check if this is a property_declaration
        if decl_node.type == cs.TS_KOTLIN_PROPERTY_DECLARATION:
            var_decl = decl_node.child_by_field_name("variable_declaration")
            if var_decl:
                decl_node = var_decl

        # (H) Extract type
        type_node = decl_node.child_by_field_name(cs.FIELD_TYPE)
        declared_type: str | None = None
        if type_node:
            if type_node.type == cs.TS_KOTLIN_TYPE_IDENTIFIER:
                declared_type = safe_decode_text(type_node)
            elif type_node.type == cs.TS_KOTLIN_USER_TYPE:
                declared_type = _extract_type_from_node(type_node)
            else:
                declared_type = safe_decode_text(type_node)

        # (H) Extract variable name
        declarator_node = decl_node.child_by_field_name(cs.FIELD_DECLARATOR)
        if not declarator_node:
            # (H) Kotlin might have name directly in variable_declaration
            name_node = decl_node.child_by_field_name(cs.FIELD_NAME)
            if not name_node:
                name_node = decl_node.child_by_field_name(
                    cs.TS_KOTLIN_SIMPLE_IDENTIFIER
                )
            if name_node:
                var_name = safe_decode_text(name_node)
                if var_name:
                    if declared_type:
                        resolved_type = self._resolve_java_type_name(
                            declared_type, module_qn
                        )
                        local_var_types[var_name] = resolved_type
                    # (H) Type inference - try to infer from initializer
                    elif init_node := decl_node.child_by_field_name("initializer"):
                        if inferred_type := self._infer_java_type_from_expression(
                            init_node, module_qn
                        ):
                            resolved_type = self._resolve_java_type_name(
                                inferred_type, module_qn
                            )
                            local_var_types[var_name] = resolved_type
                        else:
                            local_var_types[var_name] = cs.JAVA_TYPE_OBJECT
            return

        if not declarator_node:
            return

        # (H) Kotlin variable declarator handling
        if declarator_node.type == cs.TS_VARIABLE_DECLARATOR and declared_type:
            self._process_variable_declarator(
                declarator_node, declared_type, local_var_types, module_qn
            )
        elif declarator_node.type == cs.TS_KOTLIN_SIMPLE_IDENTIFIER:
            # (H) Direct identifier (Kotlin style: val name: Type = value)
            var_name = safe_decode_text(declarator_node)
            if var_name:
                if declared_type:
                    resolved_type = self._resolve_java_type_name(
                        declared_type, module_qn
                    )
                    local_var_types[var_name] = resolved_type
                # (H) Try to infer from initializer
                elif init_node := decl_node.child_by_field_name("initializer"):
                    if inferred_type := self._infer_java_type_from_expression(
                        init_node, module_qn
                    ):
                        resolved_type = self._resolve_java_type_name(
                            inferred_type, module_qn
                        )
                        local_var_types[var_name] = resolved_type
                    else:
                        local_var_types[var_name] = cs.JAVA_TYPE_OBJECT
        else:
            for child in declarator_node.children:
                if child.type == cs.TS_VARIABLE_DECLARATOR and declared_type:
                    self._process_variable_declarator(
                        child, declared_type, local_var_types, module_qn
                    )
                elif child.type == cs.TS_KOTLIN_SIMPLE_IDENTIFIER:
                    var_name = safe_decode_text(child)
                    if var_name and declared_type:
                        resolved_type = self._resolve_java_type_name(
                            declared_type, module_qn
                        )
                        local_var_types[var_name] = resolved_type

    def _process_variable_declarator(
        self,
        declarator_node: ASTNode,
        declared_type: str,
        local_var_types: dict[str, str],
        module_qn: str,
    ) -> None:
        if not (name_node := declarator_node.child_by_field_name(cs.FIELD_NAME)):
            return

        if not (var_name := safe_decode_text(name_node)):
            return

        if value_node := declarator_node.child_by_field_name(cs.FIELD_VALUE):
            if inferred_type := self._infer_java_type_from_expression(
                value_node, module_qn
            ):
                resolved_type = self._resolve_java_type_name(inferred_type, module_qn)
                local_var_types[var_name] = resolved_type
                logger.debug(
                    ls.JAVA_LOCAL_VAR_INFERRED.format(name=var_name, type=resolved_type)
                )
                return

        resolved_type = self._resolve_java_type_name(declared_type, module_qn)
        local_var_types[var_name] = resolved_type
        logger.debug(
            ls.JAVA_LOCAL_VAR_DECLARED.format(name=var_name, type=resolved_type)
        )

    def _analyze_java_class_fields(
        self, scope_node: ASTNode, local_var_types: dict[str, str], module_qn: str
    ) -> None:
        if not (containing_class := self._find_containing_java_class(scope_node)):
            return

        # (H) Kotlin class body is "class_body" field
        body_node = containing_class.child_by_field_name(cs.FIELD_BODY)
        if not body_node:
            body_node = containing_class.child_by_field_name("class_body")

        if not body_node:
            return

        for child in body_node.children:
            # (H) Kotlin class body contains property_declaration, function_declaration, etc.
            if child.type in [
                cs.TS_FIELD_DECLARATION,
                cs.TS_KOTLIN_PROPERTY_DECLARATION,
            ]:
                field_info = extract_field_info(child)
                field_name = field_info.get(cs.FIELD_NAME)
                field_type = field_info.get(cs.FIELD_TYPE)

                if field_name:
                    this_field_ref = (
                        f"{cs.JAVA_KEYWORD_THIS}{cs.SEPARATOR_DOT}{field_name}"
                    )
                    if field_type:
                        resolved_type = self._resolve_java_type_name(
                            str(field_type), module_qn
                        )
                    else:
                        resolved_type = cs.JAVA_TYPE_OBJECT

                    local_var_types[this_field_ref] = resolved_type

                    if str(field_name) not in local_var_types:
                        local_var_types[str(field_name)] = resolved_type
                    logger.debug(
                        ls.JAVA_CLASS_FIELD.format(name=field_name, type=resolved_type)
                    )

    def _analyze_java_constructor_assignments(
        self, scope_node: ASTNode, local_var_types: dict[str, str], module_qn: str
    ) -> None:
        self._traverse_for_assignments(scope_node, local_var_types, module_qn)

    def _traverse_for_assignments(
        self, node: ASTNode, local_var_types: dict[str, str], module_qn: str
    ) -> None:
        if node.type == cs.TS_ASSIGNMENT_EXPRESSION:
            self._process_java_assignment(node, local_var_types, module_qn)

        for child in node.children:
            self._traverse_for_assignments(child, local_var_types, module_qn)

    def _process_java_assignment(
        self, assignment_node: ASTNode, local_var_types: dict[str, str], module_qn: str
    ) -> None:
        left_node = assignment_node.child_by_field_name(cs.FIELD_LEFT)
        right_node = assignment_node.child_by_field_name(cs.FIELD_RIGHT)

        if not left_node or not right_node:
            return

        if not (var_name := self._extract_java_variable_reference(left_node)):
            return

        if inferred_type := self._infer_java_type_from_expression(
            right_node, module_qn
        ):
            resolved_type = self._resolve_java_type_name(inferred_type, module_qn)
            local_var_types[var_name] = resolved_type
            logger.debug(ls.JAVA_ASSIGNMENT.format(name=var_name, type=resolved_type))

    def _extract_java_variable_reference(self, node: ASTNode) -> str | None:
        match node.type:
            case cs.TS_IDENTIFIER | cs.TS_KOTLIN_SIMPLE_IDENTIFIER:
                return safe_decode_text(node)
            case cs.TS_FIELD_ACCESS | cs.TS_KOTLIN_NAVIGATION_EXPRESSION:
                # (H) Kotlin uses navigation_expression for field access
                object_node = node.child_by_field_name(cs.FIELD_OBJECT)
                if not object_node:
                    object_node = node.child_by_field_name("receiver")
                field_node = node.child_by_field_name(cs.FIELD_FIELD)
                if not field_node:
                    field_node = node.child_by_field_name("field")

                if object_node and field_node:
                    object_name = safe_decode_text(object_node)
                    field_name = safe_decode_text(field_node)

                    if object_name and field_name:
                        return f"{object_name}{cs.SEPARATOR_DOT}{field_name}"
            case _:
                pass

        return None

    def _analyze_java_enhanced_for_loops(
        self, scope_node: ASTNode, local_var_types: dict[str, str], module_qn: str
    ) -> None:
        self._traverse_for_enhanced_for_loops(scope_node, local_var_types, module_qn)

    def _traverse_for_enhanced_for_loops(
        self, node: ASTNode, local_var_types: dict[str, str], module_qn: str
    ) -> None:
        # (H) Kotlin uses "for_statement" with "loop_parameter"
        if node.type in [cs.TS_ENHANCED_FOR_STATEMENT, "for_statement"]:
            self._process_enhanced_for_statement(node, local_var_types, module_qn)

        for child in node.children:
            self._traverse_for_enhanced_for_loops(child, local_var_types, module_qn)

    def _process_enhanced_for_statement(
        self, for_node: ASTNode, local_var_types: dict[str, str], module_qn: str
    ) -> None:
        # (H) Kotlin for loop: for (item in collection)
        # (H) Look for loop_parameter or variable_declaration
        loop_param = for_node.child_by_field_name("loop_parameter")
        if not loop_param:
            loop_param = for_node.child_by_field_name("variable_declaration")

        if not loop_param:
            return

        type_node = loop_param.child_by_field_name(cs.FIELD_TYPE)
        name_node = loop_param.child_by_field_name(cs.FIELD_NAME)
        if not name_node:
            name_node = loop_param.child_by_field_name(cs.TS_KOTLIN_SIMPLE_IDENTIFIER)

        if type_node and name_node:
            self._register_for_loop_variable(
                type_node, name_node, local_var_types, module_qn
            )
        elif name_node:
            # (H) Kotlin allows type inference in for loops
            var_name = safe_decode_text(name_node)
            if var_name:
                # (H) Try to infer type from collection
                collection_node = for_node.child_by_field_name("collection")
                if collection_node:
                    if inferred_type := self._infer_java_type_from_expression(
                        collection_node, module_qn
                    ):
                        # (H) Extract element type from collection type (e.g., List<String> -> String)
                        if "List<" in inferred_type or "Array<" in inferred_type:
                            # (H) Extract generic parameter
                            if "<" in inferred_type and ">" in inferred_type:
                                element_type = inferred_type.split("<")[1].split(">")[0]
                                resolved_type = self._resolve_java_type_name(
                                    element_type, module_qn
                                )
                                local_var_types[var_name] = resolved_type
                                return
                        # (H) Fallback to Object
                        local_var_types[var_name] = cs.JAVA_TYPE_OBJECT
                else:
                    local_var_types[var_name] = cs.JAVA_TYPE_OBJECT
        else:
            self._extract_for_loop_variable_from_children(
                for_node, local_var_types, module_qn
            )

    def _register_for_loop_variable(
        self,
        type_node: ASTNode,
        name_node: ASTNode,
        local_var_types: dict[str, str],
        module_qn: str,
    ) -> None:
        if (var_type := safe_decode_text(type_node)) and (
            var_name := safe_decode_text(name_node)
        ):
            resolved_type = self._resolve_java_type_name(var_type, module_qn)
            local_var_types[var_name] = resolved_type
            logger.debug(
                ls.JAVA_ENHANCED_FOR_VAR.format(name=var_name, type=resolved_type)
            )

    def _extract_for_loop_variable_from_children(
        self, for_node: ASTNode, local_var_types: dict[str, str], module_qn: str
    ) -> None:
        for child in for_node.children:
            if child.type != cs.TS_VARIABLE_DECLARATOR:
                continue

            if not (name_node := child.child_by_field_name(cs.FIELD_NAME)):
                continue

            if not (var_name := safe_decode_text(name_node)):
                continue

            if not (parent := child.parent):
                continue

            for sibling in parent.children:
                if sibling.type == cs.TS_TYPE_IDENTIFIER:
                    if var_type := safe_decode_text(sibling):
                        resolved_type = self._resolve_java_type_name(
                            var_type, module_qn
                        )
                        local_var_types[var_name] = resolved_type
                        logger.debug(
                            ls.JAVA_ENHANCED_FOR_VAR_ALT.format(
                                name=var_name, type=resolved_type
                            )
                        )
                        break

    def _infer_java_type_from_expression(
        self, expr_node: ASTNode, module_qn: str
    ) -> str | None:
        match expr_node.type:
            case cs.TS_OBJECT_CREATION_EXPRESSION:
                if type_node := expr_node.child_by_field_name(cs.FIELD_TYPE):
                    return safe_decode_text(type_node)

            case cs.TS_METHOD_INVOCATION:
                return self._infer_java_method_return_type(expr_node, module_qn)

            case cs.TS_IDENTIFIER:
                if var_name := safe_decode_text(expr_node):
                    return self._lookup_variable_type(var_name, module_qn)

            case cs.TS_FIELD_ACCESS:
                return self._infer_java_field_access_type(expr_node, module_qn)

            case cs.TS_STRING_LITERAL:
                return cs.JAVA_TYPE_STRING

            case cs.TS_INTEGER_LITERAL:
                return cs.JAVA_TYPE_INT

            case cs.TS_DECIMAL_FLOATING_POINT_LITERAL:
                return cs.JAVA_TYPE_DOUBLE

            case cs.TS_TRUE | cs.TS_FALSE:
                return cs.JAVA_TYPE_BOOLEAN

            case cs.TS_ARRAY_CREATION_EXPRESSION:
                if type_node := expr_node.child_by_field_name(cs.FIELD_TYPE):
                    if base_type := safe_decode_text(type_node):
                        return f"{base_type}{cs.JAVA_ARRAY_SUFFIX}"

            case _:
                pass

        return None

    def _infer_java_method_return_type(
        self, method_call_node: ASTNode, module_qn: str
    ) -> str | None:
        call_info = extract_method_call_info(method_call_node)
        if not call_info:
            return None

        method_name = call_info[cs.FIELD_NAME]
        if not method_name:
            return None

        object_ref = call_info[cs.FIELD_OBJECT]
        call_string = (
            f"{object_ref}{cs.SEPARATOR_DOT}{method_name}"
            if object_ref
            else str(method_name)
        )
        return self._resolve_java_method_return_type(call_string, module_qn)

    def _infer_java_field_access_type(
        self, field_access_node: ASTNode, module_qn: str
    ) -> str | None:
        object_node = field_access_node.child_by_field_name(cs.FIELD_OBJECT)
        field_node = field_access_node.child_by_field_name(cs.FIELD_FIELD)

        if not object_node or not field_node:
            return None

        object_name = safe_decode_text(object_node)
        field_name = safe_decode_text(field_node)

        if not object_name or not field_name:
            return None

        if object_type := self._lookup_variable_type(object_name, module_qn):
            return self._lookup_java_field_type(object_type, field_name, module_qn)
        return None

    def _lookup_variable_type(self, var_name: str, module_qn: str) -> str | None:
        if not var_name or not module_qn:
            return None

        cache_key = f"{module_qn}{cs.SEPARATOR_COLON}{var_name}"
        if cache_key in self._lookup_cache:
            return self._lookup_cache[cache_key]

        if cache_key in self._lookup_in_progress:
            return None

        self._lookup_in_progress.add(cache_key)

        try:
            result = self._do_variable_type_lookup(var_name, module_qn)
            self._lookup_cache[cache_key] = result
            return result

        finally:
            self._lookup_in_progress.discard(cache_key)

    def _do_variable_type_lookup(self, var_name: str, module_qn: str) -> str | None:
        root_node = get_root_node_from_module_qn(
            module_qn, self.module_qn_to_file_path, self.ast_cache
        )
        if not root_node:
            return None

        variable_types = self.build_variable_type_map(root_node, module_qn)

        this_var = f"{cs.JAVA_KEYWORD_THIS}{cs.SEPARATOR_DOT}{var_name}"
        return variable_types.get(var_name) or variable_types.get(this_var)

    def _lookup_java_field_type(
        self, class_type: str, field_name: str, module_qn: str
    ) -> str | None:
        if not class_type or not field_name:
            return None

        resolved_class_type = self._resolve_java_type_name(class_type, module_qn)

        class_qn = (
            resolved_class_type
            if cs.SEPARATOR_DOT in resolved_class_type
            else f"{module_qn}{cs.SEPARATOR_DOT}{resolved_class_type}"
        )

        parts = class_qn.split(cs.SEPARATOR_DOT)
        if len(parts) < 2:
            return None

        target_module_qn = cs.SEPARATOR_DOT.join(parts[:-1])
        target_class_name = parts[-1]

        file_path = self.module_qn_to_file_path.get(target_module_qn)
        if file_path is None or file_path not in self.ast_cache:
            return None

        root_node, _ = self.ast_cache[file_path]

        return self._find_field_type_in_class(
            root_node, target_class_name, field_name, target_module_qn
        )

    def _find_field_type_in_class(
        self, root_node: ASTNode, class_name: str, field_name: str, module_qn: str
    ) -> str | None:
        for child in root_node.children:
            if child.type == cs.TS_CLASS_DECLARATION:
                class_info = extract_class_info(child)
                if class_info.get(cs.FIELD_NAME) == class_name:
                    if class_body := child.child_by_field_name(cs.FIELD_BODY):
                        for field_child in class_body.children:
                            if field_child.type == cs.TS_FIELD_DECLARATION:
                                field_info = extract_field_info(field_child)
                                if field_info.get(cs.FIELD_NAME) == field_name:
                                    if field_type := field_info.get(cs.FIELD_TYPE):
                                        return self._resolve_java_type_name(
                                            str(field_type), module_qn
                                        )
        return None
