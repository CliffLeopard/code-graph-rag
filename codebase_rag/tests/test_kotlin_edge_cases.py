from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from codebase_rag.tests.conftest import run_updater


@pytest.fixture
def kotlin_edge_cases_project(temp_repo: Path) -> Path:
    """Create a Kotlin project structure for edge case testing."""
    project_path = temp_repo / "kotlin_edge_cases"
    project_path.mkdir()

    (project_path / "src").mkdir()
    (project_path / "src" / "main").mkdir()
    (project_path / "src" / "main" / "kotlin").mkdir()
    (project_path / "src" / "main" / "kotlin" / "com").mkdir()
    (project_path / "src" / "main" / "kotlin" / "com" / "example").mkdir()

    return project_path


def test_empty_classes_and_interfaces(
    kotlin_edge_cases_project: Path,
    mock_ingestor: MagicMock,
) -> None:
    """Test parsing of empty classes and interfaces."""
    test_file = (
        kotlin_edge_cases_project
        / "src"
        / "main"
        / "kotlin"
        / "com"
        / "example"
        / "EmptyTypes.kt"
    )
    test_file.write_text(
        """
package com.example

// Completely empty class
class EmptyClass {
}

// Empty class with just whitespace
class WhitespaceClass {

}

// Empty interface
interface EmptyInterface {
}

// Empty abstract class
abstract class EmptyAbstractClass {
}

// Empty enum
enum class EmptyEnum {
}

// Minimal classes with single elements
class SingleFieldClass {
    private val field: Int = 0
}

class SingleMethodClass {
    fun method() {}
}

class SinglePropertyClass {
    val property: String = "value"
}

// Interface with only default methods
interface DefaultOnlyInterface {
    fun defaultMethod() {
        println("Default")
    }
}

// Class with only companion object
class CompanionOnlyClass {
    companion object {
        const val CONSTANT = 42
    }
}

// Abstract class with only abstract methods
abstract class AbstractOnlyClass {
    abstract fun abstractMethod()
}
"""
    )

    run_updater(kotlin_edge_cases_project, mock_ingestor, skip_if_missing="kotlin")


def test_classes_with_special_characters(
    kotlin_edge_cases_project: Path,
    mock_ingestor: MagicMock,
) -> None:
    """Test classes with special characters in names."""
    test_file = (
        kotlin_edge_cases_project
        / "src"
        / "main"
        / "kotlin"
        / "com"
        / "example"
        / "SpecialNames.kt"
    )
    test_file.write_text(
        """
package com.example

// Class with underscore
class Class_With_Underscore {
    fun method_name(): String = "test"
}

// Class with numbers
class Class123 {
    fun method456(): Int = 123
}

// Interface with special naming
interface IInterface {
    fun doSomething()
}

// Data class with special characters
data class Data_Class(val value_1: Int, val value_2: String)
"""
    )

    run_updater(kotlin_edge_cases_project, mock_ingestor, skip_if_missing="kotlin")


def test_nullable_types_edge_cases(
    kotlin_edge_cases_project: Path,
    mock_ingestor: MagicMock,
) -> None:
    """Test nullable types edge cases."""
    test_file = (
        kotlin_edge_cases_project
        / "src"
        / "main"
        / "kotlin"
        / "com"
        / "example"
        / "NullableTypes.kt"
    )
    test_file.write_text(
        """
package com.example

class NullableExamples {
    // Nullable property
    var nullableString: String? = null

    // Non-nullable with null check
    fun processString(str: String?): String {
        return str ?: "default"
    }

    // Safe call operator
    fun getLength(str: String?): Int? {
        return str?.length
    }

    // Elvis operator
    fun getValueOrZero(value: Int?): Int {
        return value ?: 0
    }

    // Not-null assertion
    fun forceUnwrap(str: String?): String {
        return str!!
    }

    // Nullable generic type
    fun <T> processNullable(value: T?): T? {
        return value
    }

    // Nullable function type
    var callback: (() -> Unit)? = null

    // Nullable extension function
    fun String?.isNullOrEmptyOrBlank(): Boolean {
        return this == null || this.isEmpty() || this.isBlank()
    }
}
"""
    )

    run_updater(kotlin_edge_cases_project, mock_ingestor, skip_if_missing="kotlin")


def test_type_inference_edge_cases(
    kotlin_edge_cases_project: Path,
    mock_ingestor: MagicMock,
) -> None:
    """Test type inference edge cases."""
    test_file = (
        kotlin_edge_cases_project
        / "src"
        / "main"
        / "kotlin"
        / "com"
        / "example"
        / "TypeInference.kt"
    )
    test_file.write_text(
        """
package com.example

class TypeInferenceExamples {
    // Type inference for properties
    val inferredString = "Hello"
    val inferredInt = 42
    val inferredDouble = 3.14
    val inferredBoolean = true

    // Type inference for functions
    fun add(a: Int, b: Int) = a + b
    fun multiply(a: Double, b: Double) = a * b

    // Type inference with generics
    fun <T> identity(value: T) = value

    // Type inference in lambdas
    val lambda = { x: Int, y: Int -> x + y }
    val stringLambda = { s: String -> s.length }

    // Type inference with collections
    val list = listOf(1, 2, 3)
    val map = mapOf("key" to "value")

    // Explicit type when needed
    val explicit: List<String> = listOf("a", "b", "c")
}
"""
    )

    run_updater(kotlin_edge_cases_project, mock_ingestor, skip_if_missing="kotlin")


def test_operator_overloading(
    kotlin_edge_cases_project: Path,
    mock_ingestor: MagicMock,
) -> None:
    """Test operator overloading."""
    test_file = (
        kotlin_edge_cases_project
        / "src"
        / "main"
        / "kotlin"
        / "com"
        / "example"
        / "Operators.kt"
    )
    test_file.write_text(
        """
package com.example

data class Point(val x: Int, val y: Int) {
    // Plus operator
    operator fun plus(other: Point): Point {
        return Point(x + other.x, y + other.y)
    }

    // Minus operator
    operator fun minus(other: Point): Point {
        return Point(x - other.x, y - other.y)
    }

    // Times operator
    operator fun times(factor: Int): Point {
        return Point(x * factor, y * factor)
    }

    // Unary minus
    operator fun unaryMinus(): Point {
        return Point(-x, -y)
    }

    // Indexed access
    operator fun get(index: Int): Int {
        return when (index) {
            0 -> x
            1 -> y
            else -> throw IndexOutOfBoundsException()
        }
    }

    // Invoke operator
    operator fun invoke(): String {
        return "Point($x, $y)"
    }
}

// Comparison operators
data class Money(val amount: Double) {
    operator fun compareTo(other: Money): Int {
        return amount.compareTo(other.amount)
    }
}
"""
    )

    run_updater(kotlin_edge_cases_project, mock_ingestor, skip_if_missing="kotlin")


def test_infix_functions(
    kotlin_edge_cases_project: Path,
    mock_ingestor: MagicMock,
) -> None:
    """Test infix functions."""
    test_file = (
        kotlin_edge_cases_project
        / "src"
        / "main"
        / "kotlin"
        / "com"
        / "example"
        / "InfixFunctions.kt"
    )
    test_file.write_text(
        """
package com.example

class InfixExamples {
    // Infix function
    infix fun String.matches(pattern: String): Boolean {
        return this == pattern
    }

    // Infix extension function
    infix fun Int.pow(exponent: Int): Int {
        return Math.pow(this.toDouble(), exponent.toDouble()).toInt()
    }

    // Using infix functions
    fun usage() {
        val result = "test" matches "test"
        val power = 2 pow 3
    }
}

// Infix function in class
class Matrix {
    infix fun multiply(other: Matrix): Matrix {
        return Matrix()
    }
}
"""
    )

    run_updater(kotlin_edge_cases_project, mock_ingestor, skip_if_missing="kotlin")


def test_tailrec_functions(
    kotlin_edge_cases_project: Path,
    mock_ingestor: MagicMock,
) -> None:
    """Test tailrec functions."""
    test_file = (
        kotlin_edge_cases_project
        / "src"
        / "main"
        / "kotlin"
        / "com"
        / "example"
        / "Tailrec.kt"
    )
    test_file.write_text(
        """
package com.example

object TailrecExamples {
    // Tailrec factorial
    tailrec fun factorial(n: Int, acc: Int = 1): Int {
        return if (n <= 1) acc else factorial(n - 1, n * acc)
    }

    // Tailrec fibonacci
    tailrec fun fibonacci(n: Int, a: Int = 0, b: Int = 1): Int {
        return if (n == 0) a else fibonacci(n - 1, b, a + b)
    }

    // Tailrec sum
    tailrec fun sum(numbers: List<Int>, acc: Int = 0): Int {
        return if (numbers.isEmpty()) acc else sum(numbers.drop(1), acc + numbers.first())
    }
}
"""
    )

    run_updater(kotlin_edge_cases_project, mock_ingestor, skip_if_missing="kotlin")


def test_annotation_edge_cases(
    kotlin_edge_cases_project: Path,
    mock_ingestor: MagicMock,
) -> None:
    """Test parsing of annotation edge cases."""
    test_file = (
        kotlin_edge_cases_project
        / "src"
        / "main"
        / "kotlin"
        / "com"
        / "example"
        / "Annotations.kt"
    )
    test_file.write_text(
        """
package com.example

// Multiple annotations on class
@Deprecated("Use NewClass instead")
@Suppress("UNUSED")
class AnnotatedClass {
    // Multiple annotations on method
    @JvmStatic
    @Synchronized
    fun annotatedMethod() {}

    // Annotation with parameters
    @Suppress("UNCHECKED_CAST", "UNUSED_VARIABLE")
    fun suppressedMethod() {}

    // Annotation on property
    @Volatile
    var volatileProperty: Int = 0

    // Annotation on parameter
    fun methodWithAnnotatedParam(@NotNull param: String) {}

    // Annotation on constructor
    @JvmOverloads
    constructor(value: Int) {
        this.value = value
    }

    var value: Int = 0
}
"""
    )

    run_updater(kotlin_edge_cases_project, mock_ingestor, skip_if_missing="kotlin")


def test_when_expression_edge_cases(
    kotlin_edge_cases_project: Path,
    mock_ingestor: MagicMock,
) -> None:
    """Test when expression edge cases."""
    test_file = (
        kotlin_edge_cases_project
        / "src"
        / "main"
        / "kotlin"
        / "com"
        / "example"
        / "WhenExpressions.kt"
    )
    test_file.write_text(
        """
package com.example

class WhenExamples {
    // When as expression
    fun getStatus(code: Int): String {
        return when (code) {
            200 -> "OK"
            404 -> "Not Found"
            500 -> "Server Error"
            else -> "Unknown"
        }
    }

    // When with multiple conditions
    fun getType(value: Any): String {
        return when (value) {
            is String -> "String"
            is Int -> "Int"
            is Double -> "Double"
            else -> "Unknown"
        }
    }

    // When with ranges
    fun getGrade(score: Int): String {
        return when (score) {
            in 90..100 -> "A"
            in 80..89 -> "B"
            in 70..79 -> "C"
            else -> "F"
        }
    }

    // When without argument
    fun processValue(value: Int) {
        when {
            value < 0 -> println("Negative")
            value == 0 -> println("Zero")
            value > 0 -> println("Positive")
        }
    }
}
"""
    )

    run_updater(kotlin_edge_cases_project, mock_ingestor, skip_if_missing="kotlin")
