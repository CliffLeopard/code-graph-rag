from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from codebase_rag.tests.conftest import (
    get_node_names,
    run_updater,
)


@pytest.fixture
def kotlin_methods_project(temp_repo: Path) -> Path:
    """Create a Kotlin project with method call patterns."""
    project_path = temp_repo / "kotlin_methods_test"
    project_path.mkdir()

    (project_path / "src").mkdir()
    (project_path / "src" / "main").mkdir()
    (project_path / "src" / "main" / "kotlin").mkdir()
    (project_path / "src" / "main" / "kotlin" / "com").mkdir()
    (project_path / "src" / "main" / "kotlin" / "com" / "example").mkdir()

    return project_path


def test_basic_method_calls(
    kotlin_methods_project: Path,
    mock_ingestor: MagicMock,
) -> None:
    """Test basic Kotlin method call parsing."""
    test_file = (
        kotlin_methods_project
        / "src"
        / "main"
        / "kotlin"
        / "com"
        / "example"
        / "BasicMethodCalls.kt"
    )
    test_file.write_text(
        """
package com.example

class BasicMethodCalls {
    private var name: String = ""

    fun instanceMethod() {
        println("Instance method called")
    }

    fun getName(): String {
        return name
    }

    fun setName(newName: String) {
        name = newName
    }

    fun demonstrateMethodCalls() {
        // Instance method calls
        instanceMethod()
        this.instanceMethod()

        // Getter/setter calls
        val currentName = getName()
        setName("New Name")

        // Method chaining
        val result = getName().uppercase().trim()

        // Extension function calls
        val reversed = "hello".reversed()
    }

    fun callOtherObject() {
        val other = BasicMethodCalls()
        other.instanceMethod()
        val otherName = other.getName()
    }
}
"""
    )

    run_updater(kotlin_methods_project, mock_ingestor, skip_if_missing="kotlin")

    project_name = kotlin_methods_project.name
    node_names = get_node_names(mock_ingestor, "Class")
    expected_classes = {
        f"{project_name}.src.main.kotlin.com.example.BasicMethodCalls.BasicMethodCalls",
    }
    missing_classes = expected_classes - node_names
    assert not missing_classes, (
        f"Missing expected classes: {sorted(list(missing_classes))}"
    )


def test_extension_function_calls(
    kotlin_methods_project: Path,
    mock_ingestor: MagicMock,
) -> None:
    """Test extension function calls."""
    test_file = (
        kotlin_methods_project
        / "src"
        / "main"
        / "kotlin"
        / "com"
        / "example"
        / "ExtensionCalls.kt"
    )
    test_file.write_text(
        """
package com.example

// Extension functions
fun String.reverse(): String {
    return this.reversed()
}

fun Int.square(): Int {
    return this * this
}

class ExtensionCallExamples {
    fun useExtensions() {
        val reversed = "hello".reverse()
        val squared = 5.square()

        // Chained extension calls
        val result = "test".reverse().uppercase()
    }
}
"""
    )

    run_updater(kotlin_methods_project, mock_ingestor, skip_if_missing="kotlin")


def test_infix_function_calls(
    kotlin_methods_project: Path,
    mock_ingestor: MagicMock,
) -> None:
    """Test infix function calls."""
    test_file = (
        kotlin_methods_project
        / "src"
        / "main"
        / "kotlin"
        / "com"
        / "example"
        / "InfixCalls.kt"
    )
    test_file.write_text(
        """
package com.example

infix fun Int.pow(exponent: Int): Int {
    return Math.pow(this.toDouble(), exponent.toDouble()).toInt()
}

class InfixCallExamples {
    fun useInfix() {
        val result = 2 pow 3  // Infix call
        val normal = 2.pow(3)  // Normal call
    }
}
"""
    )

    run_updater(kotlin_methods_project, mock_ingestor, skip_if_missing="kotlin")


def test_super_and_this_calls(
    kotlin_methods_project: Path,
    mock_ingestor: MagicMock,
) -> None:
    """Test super and this method calls."""
    test_file = (
        kotlin_methods_project
        / "src"
        / "main"
        / "kotlin"
        / "com"
        / "example"
        / "SuperThisCalls.kt"
    )
    test_file.write_text(
        """
package com.example

open class BaseClass {
    open fun display() {
        println("Base")
    }
}

class DerivedClass : BaseClass() {
    override fun display() {
        super.display()  // Call parent method
        println("Derived")
    }

    fun demonstrateThis() {
        this.display()  // Call own method
    }
}
"""
    )

    run_updater(kotlin_methods_project, mock_ingestor, skip_if_missing="kotlin")


def test_lambda_and_higher_order_functions(
    kotlin_methods_project: Path,
    mock_ingestor: MagicMock,
) -> None:
    """Test lambda and higher-order function calls."""
    test_file = (
        kotlin_methods_project
        / "src"
        / "main"
        / "kotlin"
        / "com"
        / "example"
        / "LambdaCalls.kt"
    )
    test_file.write_text(
        """
package com.example

class LambdaExamples {
    fun useLambdas() {
        val numbers = listOf(1, 2, 3, 4, 5)

        // Lambda as parameter
        val doubled = numbers.map { it * 2 }
        val filtered = numbers.filter { it > 3 }

        // Lambda with explicit parameter
        val squared = numbers.map { x -> x * x }

        // Lambda with multiple statements
        val processed = numbers.map { x ->
            val doubled = x * 2
            doubled + 1
        }
    }

    fun higherOrderFunction(operation: (Int) -> Int): Int {
        return operation(42)
    }

    fun useHigherOrder() {
        val result = higherOrderFunction { it * 2 }
    }
}
"""
    )

    run_updater(kotlin_methods_project, mock_ingestor, skip_if_missing="kotlin")
