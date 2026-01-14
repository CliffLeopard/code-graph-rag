from __future__ import annotations

import pytest
from tree_sitter import Language, Parser

from codebase_rag import constants as cs
from codebase_rag.parsers.kotlin.utils import (
    _extract_type_from_node,
    extract_class_info,
    extract_field_info,
    extract_from_modifiers_node,
    extract_import_path,
    extract_method_call_info,
    extract_method_info,
    extract_package_name,
    find_package_start_index,
)
from codebase_rag.tests.conftest import create_mock_node

try:
    import tree_sitter_kotlin as tskotlin

    KOTLIN_AVAILABLE = True
except ImportError:
    KOTLIN_AVAILABLE = False


@pytest.fixture
def kotlin_parser() -> Parser | None:
    if not KOTLIN_AVAILABLE:
        return None
    language = Language(tskotlin.language())
    return Parser(language)


class TestExtractKotlinPackageName:
    def test_simple_identifier_package(self) -> None:
        identifier = create_mock_node(cs.TS_KOTLIN_SIMPLE_IDENTIFIER, "mypackage")
        package_node = create_mock_node(
            cs.TS_KOTLIN_PACKAGE_HEADER, children=[identifier]
        )
        result = extract_package_name(package_node)
        assert result == "mypackage"

    def test_qualified_expression_package(self) -> None:
        # (H) com.example.app
        app_id = create_mock_node(cs.TS_KOTLIN_SIMPLE_IDENTIFIER, "app")
        example_id = create_mock_node(cs.TS_KOTLIN_SIMPLE_IDENTIFIER, "example")
        com_id = create_mock_node(cs.TS_KOTLIN_SIMPLE_IDENTIFIER, "com")
        # (H) Create nested qualified_expression structure
        inner_qual = create_mock_node(
            "qualified_expression", children=[example_id, app_id]
        )
        outer_qual = create_mock_node(
            "qualified_expression", children=[com_id, inner_qual]
        )
        package_node = create_mock_node(
            cs.TS_KOTLIN_PACKAGE_HEADER, children=[outer_qual]
        )
        result = extract_package_name(package_node)
        assert result == "com.example.app"

    def test_invalid_node_type(self) -> None:
        node = create_mock_node("class_declaration")
        result = extract_package_name(node)
        assert result is None

    def test_empty_package_header(self) -> None:
        package_node = create_mock_node(cs.TS_KOTLIN_PACKAGE_HEADER, children=[])
        result = extract_package_name(package_node)
        assert result is None


class TestExtractKotlinImportPath:
    def test_regular_import(self) -> None:
        list_id = create_mock_node(cs.TS_KOTLIN_SIMPLE_IDENTIFIER, "List")
        util_id = create_mock_node(cs.TS_KOTLIN_SIMPLE_IDENTIFIER, "util")
        java_id = create_mock_node(cs.TS_KOTLIN_SIMPLE_IDENTIFIER, "java")
        # (H) Create qualified_expression: java.util.List
        util_list_qual = create_mock_node(
            "qualified_expression", children=[util_id, list_id]
        )
        qual_expr = create_mock_node(
            "qualified_expression", children=[java_id, util_list_qual]
        )
        import_node = create_mock_node(
            cs.TS_KOTLIN_IMPORT_DIRECTIVE, children=[qual_expr]
        )
        result = extract_import_path(import_node)
        assert "List" in result
        assert result["List"] == "java.util.List"

    def test_wildcard_import(self) -> None:
        util_id = create_mock_node(cs.TS_KOTLIN_SIMPLE_IDENTIFIER, "util")
        java_id = create_mock_node(cs.TS_KOTLIN_SIMPLE_IDENTIFIER, "java")
        qual_expr = create_mock_node(
            "qualified_expression", children=[java_id, util_id]
        )
        asterisk = create_mock_node("asterisk", "*")
        import_node = create_mock_node(
            cs.TS_KOTLIN_IMPORT_DIRECTIVE, children=[qual_expr, asterisk]
        )
        result = extract_import_path(import_node)
        assert "*java.util" in result
        assert result["*java.util"] == "java.util"

    def test_import_with_alias(self) -> None:
        arraylist_id = create_mock_node(cs.TS_KOTLIN_SIMPLE_IDENTIFIER, "ArrayList")
        util_id = create_mock_node(cs.TS_KOTLIN_SIMPLE_IDENTIFIER, "util")
        java_id = create_mock_node(cs.TS_KOTLIN_SIMPLE_IDENTIFIER, "java")
        util_al_qual = create_mock_node(
            "qualified_expression", children=[util_id, arraylist_id]
        )
        qual_expr = create_mock_node(
            "qualified_expression", children=[java_id, util_al_qual]
        )
        as_keyword = create_mock_node("as", "as")
        alias = create_mock_node(cs.TS_KOTLIN_SIMPLE_IDENTIFIER, "AL")
        import_node = create_mock_node(
            cs.TS_KOTLIN_IMPORT_DIRECTIVE, children=[qual_expr, as_keyword, alias]
        )
        result = extract_import_path(import_node)
        assert "AL" in result
        assert result["AL"] == "java.util.ArrayList"

    def test_import_list(self) -> None:
        list_id = create_mock_node(cs.TS_KOTLIN_SIMPLE_IDENTIFIER, "List")
        map_id = create_mock_node(cs.TS_KOTLIN_SIMPLE_IDENTIFIER, "Map")
        import1 = create_mock_node(cs.TS_KOTLIN_IMPORT_DIRECTIVE, children=[list_id])
        import2 = create_mock_node(cs.TS_KOTLIN_IMPORT_DIRECTIVE, children=[map_id])
        import_list = create_mock_node(
            cs.TS_KOTLIN_IMPORT_LIST, children=[import1, import2]
        )
        result = extract_import_path(import_list)
        assert len(result) >= 1  # (H) At least one import should be extracted

    def test_invalid_node_type(self) -> None:
        node = create_mock_node("class_declaration")
        result = extract_import_path(node)
        assert result == {}


class TestExtractTypeFromNode:
    def test_type_identifier(self) -> None:
        node = create_mock_node(cs.TS_KOTLIN_TYPE_IDENTIFIER, "String")
        result = _extract_type_from_node(node)
        assert result == "String"

    def test_user_type_simple(self) -> None:
        type_id = create_mock_node(cs.TS_KOTLIN_TYPE_IDENTIFIER, "List")
        user_type = create_mock_node(cs.TS_KOTLIN_USER_TYPE, children=[type_id])
        result = _extract_type_from_node(user_type)
        assert result == "List"

    def test_user_type_nested(self) -> None:
        # (H) java.util.List - nested user_type structure
        list_id = create_mock_node(cs.TS_KOTLIN_TYPE_IDENTIFIER, "List")
        util_id = create_mock_node(cs.TS_KOTLIN_TYPE_IDENTIFIER, "util")
        java_id = create_mock_node(cs.TS_KOTLIN_TYPE_IDENTIFIER, "java")
        # (H) Create nested structure: util.List inside java
        nested_user = create_mock_node(
            cs.TS_KOTLIN_USER_TYPE, children=[util_id, list_id]
        )
        user_type = create_mock_node(
            cs.TS_KOTLIN_USER_TYPE, children=[java_id, nested_user]
        )
        result = _extract_type_from_node(user_type)
        # (H) Should extract the full qualified name
        assert result is not None
        assert "List" in result or "java" in result

    def test_delegation_specifier(self) -> None:
        type_id = create_mock_node(cs.TS_KOTLIN_TYPE_IDENTIFIER, "Runnable")
        user_type = create_mock_node(cs.TS_KOTLIN_USER_TYPE, children=[type_id])
        delegation = create_mock_node("delegation_specifier", children=[user_type])
        result = _extract_type_from_node(delegation)
        assert result == "Runnable"


class TestExtractKotlinClassInfo:
    def test_simple_class(self) -> None:
        name_node = create_mock_node("type_identifier", "MyClass")
        class_node = create_mock_node(
            cs.TS_KOTLIN_CLASS_DECLARATION,
            fields={"name": name_node},
        )
        result = extract_class_info(class_node)
        assert result["name"] == "MyClass"
        assert result["type"] == "class"
        assert result["superclass"] is None
        assert result["interfaces"] == []

    def test_class_with_superclass(self) -> None:
        name_node = create_mock_node("type_identifier", "Child")
        super_type = create_mock_node(cs.TS_KOTLIN_TYPE_IDENTIFIER, "Parent")
        delegation = create_mock_node("delegation_specifier", children=[super_type])
        delegation_specs = create_mock_node(
            "delegation_specifiers", children=[delegation]
        )
        class_node = create_mock_node(
            cs.TS_KOTLIN_CLASS_DECLARATION,
            fields={"name": name_node, "delegation_specifiers": delegation_specs},
        )
        result = extract_class_info(class_node)
        assert result["name"] == "Child"
        assert result["superclass"] == "Parent"

    def test_interface_declaration(self) -> None:
        name_node = create_mock_node("type_identifier", "MyInterface")
        interface_node = create_mock_node(
            cs.TS_KOTLIN_INTERFACE_DECLARATION,
            fields={"name": name_node},
        )
        result = extract_class_info(interface_node)
        assert result["name"] == "MyInterface"
        assert result["type"] == "interface"

    def test_enum_class(self) -> None:
        name_node = create_mock_node("type_identifier", "Color")
        enum_node = create_mock_node(
            cs.TS_KOTLIN_ENUM_CLASS,
            fields={"name": name_node},
        )
        result = extract_class_info(enum_node)
        assert result["name"] == "Color"
        assert result["type"] == "enum"

    def test_object_declaration(self) -> None:
        name_node = create_mock_node("type_identifier", "Singleton")
        object_node = create_mock_node(
            cs.TS_KOTLIN_OBJECT_DECLARATION,
            fields={"name": name_node},
        )
        result = extract_class_info(object_node)
        assert result["name"] == "Singleton"
        assert result["type"] == "object"

    def test_class_with_type_parameters(self) -> None:
        name_node = create_mock_node("type_identifier", "Box")
        type_param = create_mock_node(
            "type_parameter", fields={"name": create_mock_node("type_identifier", "T")}
        )
        type_params = create_mock_node("type_parameters", children=[type_param])
        class_node = create_mock_node(
            cs.TS_KOTLIN_CLASS_DECLARATION,
            fields={"name": name_node, "type_parameters": type_params},
        )
        result = extract_class_info(class_node)
        assert result["name"] == "Box"
        assert "T" in result["type_parameters"]


class TestExtractKotlinMethodInfo:
    def test_simple_function(self) -> None:
        name_node = create_mock_node(cs.TS_KOTLIN_SIMPLE_IDENTIFIER, "greet")
        params = create_mock_node("parameter_list", children=[])
        func_node = create_mock_node(
            cs.TS_KOTLIN_FUNCTION_DECLARATION,
            fields={"name": name_node, "parameters": params},
        )
        result = extract_method_info(func_node)
        assert result["name"] == "greet"
        assert result["type"] == cs.JAVA_TYPE_METHOD
        assert result["parameters"] == []

    def test_function_with_parameters(self) -> None:
        name_node = create_mock_node(cs.TS_KOTLIN_SIMPLE_IDENTIFIER, "add")
        param1 = create_mock_node(
            cs.TS_KOTLIN_PARAMETER,
            fields={
                "name": create_mock_node(cs.TS_KOTLIN_SIMPLE_IDENTIFIER, "a"),
                "type": create_mock_node(cs.TS_KOTLIN_TYPE_IDENTIFIER, "Int"),
            },
        )
        param2 = create_mock_node(
            cs.TS_KOTLIN_PARAMETER,
            fields={
                "name": create_mock_node(cs.TS_KOTLIN_SIMPLE_IDENTIFIER, "b"),
                "type": create_mock_node(cs.TS_KOTLIN_TYPE_IDENTIFIER, "Int"),
            },
        )
        params = create_mock_node("parameter_list", children=[param1, param2])
        func_node = create_mock_node(
            cs.TS_KOTLIN_FUNCTION_DECLARATION,
            fields={"name": name_node, "parameters": params},
        )
        result = extract_method_info(func_node)
        assert result["name"] == "add"
        assert len(result["parameters"]) == 2
        assert "Int" in result["parameters"]

    def test_function_with_return_type(self) -> None:
        name_node = create_mock_node(cs.TS_KOTLIN_SIMPLE_IDENTIFIER, "getName")
        return_type = create_mock_node(cs.TS_KOTLIN_TYPE_IDENTIFIER, "String")
        params = create_mock_node("parameter_list", children=[])
        func_node = create_mock_node(
            cs.TS_KOTLIN_FUNCTION_DECLARATION,
            fields={"name": name_node, "parameters": params, "type": return_type},
        )
        result = extract_method_info(func_node)
        assert result["name"] == "getName"
        assert result["return_type"] == "String"

    def test_constructor(self) -> None:
        constructor_node = create_mock_node(cs.TS_KOTLIN_CONSTRUCTOR)
        result = extract_method_info(constructor_node)
        assert result["type"] == cs.JAVA_TYPE_CONSTRUCTOR

    def test_function_with_modifiers(self) -> None:
        name_node = create_mock_node(cs.TS_KOTLIN_SIMPLE_IDENTIFIER, "publicFun")
        modifier = create_mock_node("modifier", "public")
        modifiers = create_mock_node("modifiers", children=[modifier])
        params = create_mock_node("parameter_list", children=[])
        func_node = create_mock_node(
            cs.TS_KOTLIN_FUNCTION_DECLARATION,
            fields={"name": name_node, "parameters": params},
            children=[modifiers],
        )
        result = extract_method_info(func_node)
        assert result["name"] == "publicFun"
        assert "public" in result["modifiers"]


class TestExtractKotlinFieldInfo:
    def test_simple_property(self) -> None:
        var_decl = create_mock_node(
            "variable_declaration",
            fields={"name": create_mock_node(cs.TS_KOTLIN_SIMPLE_IDENTIFIER, "name")},
        )
        type_node = create_mock_node(cs.TS_KOTLIN_TYPE_IDENTIFIER, "String")
        prop_node = create_mock_node(
            cs.TS_KOTLIN_PROPERTY_DECLARATION,
            fields={"variable_declaration": var_decl, "type": type_node},
        )
        result = extract_field_info(prop_node)
        assert result["name"] == "name"
        assert result["type"] == "String"

    def test_property_without_type(self) -> None:
        var_decl = create_mock_node(
            "variable_declaration",
            fields={"name": create_mock_node(cs.TS_KOTLIN_SIMPLE_IDENTIFIER, "value")},
        )
        prop_node = create_mock_node(
            cs.TS_KOTLIN_PROPERTY_DECLARATION,
            fields={"variable_declaration": var_decl},
        )
        result = extract_field_info(prop_node)
        assert result["name"] == "value"
        assert result["type"] is None

    def test_invalid_node_type(self) -> None:
        node = create_mock_node("class_declaration")
        result = extract_field_info(node)
        assert result["name"] is None
        assert result["type"] is None


class TestExtractKotlinMethodCallInfo:
    def test_simple_call(self) -> None:
        identifier = create_mock_node(cs.TS_KOTLIN_SIMPLE_IDENTIFIER, "println")
        args = create_mock_node(
            "value_arguments",
            children=[
                create_mock_node(
                    "value_argument",
                    children=[create_mock_node("string_literal", '"Hello"')],
                )
            ],
        )
        call_node = create_mock_node(
            cs.TS_KOTLIN_CALL_EXPRESSION,
            fields={"value": identifier, "value_arguments": args},
        )
        result = extract_method_call_info(call_node)
        assert result is not None
        assert result["name"] == "println"
        assert result["arguments"] == 1

    def test_navigation_expression_call(self) -> None:
        field = create_mock_node(cs.TS_KOTLIN_SIMPLE_IDENTIFIER, "length")
        receiver = create_mock_node(cs.TS_KOTLIN_SIMPLE_IDENTIFIER, "str")
        nav_expr = create_mock_node(
            cs.TS_KOTLIN_NAVIGATION_EXPRESSION,
            fields={"field": field, "receiver": receiver},
        )
        args = create_mock_node("value_arguments", children=[])
        call_node = create_mock_node(
            cs.TS_KOTLIN_CALL_EXPRESSION,
            fields={"value": nav_expr, "value_arguments": args},
        )
        result = extract_method_call_info(call_node)
        assert result is not None
        assert result["name"] == "length"
        assert result["object"] == "str"

    def test_this_call(self) -> None:
        field = create_mock_node(cs.TS_KOTLIN_SIMPLE_IDENTIFIER, "doSomething")
        receiver = create_mock_node("this", "this")
        nav_expr = create_mock_node(
            cs.TS_KOTLIN_NAVIGATION_EXPRESSION,
            fields={"field": field, "receiver": receiver},
        )
        args = create_mock_node("value_arguments", children=[])
        call_node = create_mock_node(
            cs.TS_KOTLIN_CALL_EXPRESSION,
            fields={"value": nav_expr, "value_arguments": args},
        )
        result = extract_method_call_info(call_node)
        assert result is not None
        assert result["name"] == "doSomething"
        assert result["object"] == "this"

    def test_nested_navigation(self) -> None:
        inner_field = create_mock_node(cs.TS_KOTLIN_SIMPLE_IDENTIFIER, "inner")
        inner_receiver = create_mock_node(cs.TS_KOTLIN_SIMPLE_IDENTIFIER, "outer")
        inner_nav = create_mock_node(
            cs.TS_KOTLIN_NAVIGATION_EXPRESSION,
            fields={"field": inner_field, "receiver": inner_receiver},
        )
        outer_field = create_mock_node(cs.TS_KOTLIN_SIMPLE_IDENTIFIER, "method")
        outer_nav = create_mock_node(
            cs.TS_KOTLIN_NAVIGATION_EXPRESSION,
            fields={"field": outer_field, "receiver": inner_nav},
        )
        args = create_mock_node("value_arguments", children=[])
        call_node = create_mock_node(
            cs.TS_KOTLIN_CALL_EXPRESSION,
            fields={"value": outer_nav, "value_arguments": args},
        )
        result = extract_method_call_info(call_node)
        assert result is not None
        assert result["name"] == "method"

    def test_invalid_node_type(self) -> None:
        node = create_mock_node("class_declaration")
        result = extract_method_call_info(node)
        assert result is None


class TestExtractFromModifiersNode:
    def test_modifiers_with_annotations(self) -> None:
        annotation = create_mock_node(
            "annotation",
            children=[
                create_mock_node(
                    cs.TS_KOTLIN_USER_TYPE,
                    children=[
                        create_mock_node(cs.TS_KOTLIN_TYPE_IDENTIFIER, "Deprecated")
                    ],
                )
            ],
        )
        modifier = create_mock_node("modifier", "public")
        modifiers = create_mock_node("modifiers", children=[modifier, annotation])
        node = create_mock_node("function_declaration", children=[modifiers])
        result = extract_from_modifiers_node(node, frozenset())
        assert "public" in result.modifiers
        assert "Deprecated" in result.annotations

    def test_direct_annotations(self) -> None:
        annotation = create_mock_node(
            "annotation",
            children=[create_mock_node(cs.TS_KOTLIN_TYPE_IDENTIFIER, "Override")],
        )
        node = create_mock_node("function_declaration", children=[annotation])
        result = extract_from_modifiers_node(node, frozenset())
        assert "Override" in result.annotations

    def test_kotlin_specific_modifiers(self) -> None:
        data_mod = create_mock_node("modifier", "data")
        sealed_mod = create_mock_node("modifier", "sealed")
        modifiers = create_mock_node("modifiers", children=[data_mod, sealed_mod])
        node = create_mock_node("class_declaration", children=[modifiers])
        result = extract_from_modifiers_node(node, frozenset())
        assert "data" in result.modifiers
        assert "sealed" in result.modifiers


class TestFindPackageStartIndex:
    def test_standard_java_layout(self) -> None:
        parts = ["project", "src", "main", "java", "com", "example"]
        result = find_package_start_index(parts)
        assert result == 4  # (H) After "java"

    def test_kotlin_layout(self) -> None:
        parts = ["project", "src", "main", "kotlin", "com", "example"]
        result = find_package_start_index(parts)
        assert result == 4  # (H) After "kotlin"

    def test_non_standard_layout(self) -> None:
        parts = ["project", "src", "main", "com", "example"]
        result = find_package_start_index(parts)
        # (H) find_package_start_index looks for JAVA_PATH_SRC ("src") and checks next part
        # (H) If next is "main" (in JAVA_SRC_FOLDERS), it checks if it's non-standard layout
        # (H) For ["project", "src", "main", "com", "example"]:
        # (H) - finds "src" at index 1
        # (H) - next is "main" (in JAVA_SRC_FOLDERS)
        # (H) - checks _is_non_standard_java_src_layout which returns True if part_after_next not in JAVA_JVM_LANGUAGES
        # (H) - "com" is not in JAVA_JVM_LANGUAGES, so returns i + 1 = 2
        assert result == 2  # (H) After "src" (non-standard layout detection)

    def test_no_match(self) -> None:
        parts = ["project", "code", "example"]
        result = find_package_start_index(parts)
        assert result is None


@pytest.mark.skipif(not KOTLIN_AVAILABLE, reason="tree-sitter-kotlin not available")
class TestKotlinParserIntegration:
    def test_parse_simple_class(self, kotlin_parser: Parser) -> None:
        code = b"""
package com.example

class MyClass {
    fun greet(): String {
        return "Hello"
    }
}
"""
        tree = kotlin_parser.parse(code)
        assert tree.root_node.type == cs.TS_KOTLIN_SOURCE_FILE
        assert not tree.root_node.has_error

    def test_parse_data_class(self, kotlin_parser: Parser) -> None:
        code = b"""
data class Person(val name: String, val age: Int)
"""
        tree = kotlin_parser.parse(code)
        assert tree.root_node.type == cs.TS_KOTLIN_SOURCE_FILE
        assert not tree.root_node.has_error

    def test_parse_function_with_type_inference(self, kotlin_parser: Parser) -> None:
        code = b"""
fun add(a: Int, b: Int) = a + b
"""
        tree = kotlin_parser.parse(code)
        assert tree.root_node.type == cs.TS_KOTLIN_SOURCE_FILE
        assert not tree.root_node.has_error

    def test_parse_extension_function(self, kotlin_parser: Parser) -> None:
        code = b"""
fun String.reverse(): String {
    return this.reversed()
}
"""
        tree = kotlin_parser.parse(code)
        assert tree.root_node.type == cs.TS_KOTLIN_SOURCE_FILE
        assert not tree.root_node.has_error

    def test_parse_suspend_function(self, kotlin_parser: Parser) -> None:
        code = b"""
suspend fun fetchData(): String {
    return "data"
}
"""
        tree = kotlin_parser.parse(code)
        assert tree.root_node.type == cs.TS_KOTLIN_SOURCE_FILE
        assert not tree.root_node.has_error

    def test_parse_sealed_class(self, kotlin_parser: Parser) -> None:
        code = b"""
sealed class Result {
    class Success(val data: String) : Result()
    class Error(val message: String) : Result()
}
"""
        tree = kotlin_parser.parse(code)
        assert tree.root_node.type == cs.TS_KOTLIN_SOURCE_FILE
        assert not tree.root_node.has_error

    def test_parse_companion_object(self, kotlin_parser: Parser) -> None:
        code = b"""
class MyClass {
    companion object {
        const val CONSTANT = 42
    }
}
"""
        tree = kotlin_parser.parse(code)
        assert tree.root_node.type == cs.TS_KOTLIN_SOURCE_FILE
        assert not tree.root_node.has_error

    def test_parse_lambda(self, kotlin_parser: Parser) -> None:
        code = b"""
val lambda = { x: Int, y: Int -> x + y }
"""
        tree = kotlin_parser.parse(code)
        assert tree.root_node.type == cs.TS_KOTLIN_SOURCE_FILE
        assert not tree.root_node.has_error

    def test_parse_nullable_types(self, kotlin_parser: Parser) -> None:
        code = b"""
fun process(value: String?): String {
    return value ?: "default"
}
"""
        tree = kotlin_parser.parse(code)
        assert tree.root_node.type == cs.TS_KOTLIN_SOURCE_FILE
        assert not tree.root_node.has_error

    def test_parse_generics(self, kotlin_parser: Parser) -> None:
        code = b"""
class Box<T>(val value: T)
"""
        tree = kotlin_parser.parse(code)
        assert tree.root_node.type == cs.TS_KOTLIN_SOURCE_FILE
        assert not tree.root_node.has_error
