from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from codebase_rag.tests.conftest import (
    get_node_names,
    get_nodes,
    get_qualified_names,
    run_updater,
)


@pytest.fixture
def kotlin_generics_project(temp_repo: Path) -> Path:
    """Create a Kotlin project for testing generics."""
    project_path = temp_repo / "kotlin_generics_test"
    project_path.mkdir()

    (project_path / "src").mkdir()
    (project_path / "src" / "main").mkdir()
    (project_path / "src" / "main" / "kotlin").mkdir()
    (project_path / "src" / "main" / "kotlin" / "com").mkdir()
    (project_path / "src" / "main" / "kotlin" / "com" / "example").mkdir()

    return project_path


def test_generic_classes(
    kotlin_generics_project: Path,
    mock_ingestor: MagicMock,
) -> None:
    """Test generic classes."""
    test_file = (
        kotlin_generics_project
        / "src"
        / "main"
        / "kotlin"
        / "com"
        / "example"
        / "GenericClasses.kt"
    )
    test_file.write_text(
        """
package com.example

// Simple generic class
class Box<T>(val value: T) {
    fun getValue(): T = value
}

// Generic class with multiple type parameters
class Pair<T, U>(val first: T, val second: U) {
    fun swap(): Pair<U, T> {
        return Pair(second, first)
    }
}

// Generic class with constraints
class Container<T : Number>(val value: T) {
    fun doubleValue(): Double {
        return value.toDouble() * 2
    }
}

// Generic class with multiple constraints
interface Comparable<T> {
    fun compareTo(other: T): Int
}

class SortedList<T> where T : Comparable<T>, T : Number {
    private val items = mutableListOf<T>()

    fun add(item: T) {
        items.add(item)
    }
}
"""
    )

    run_updater(kotlin_generics_project, mock_ingestor, skip_if_missing="kotlin")

    project_name = kotlin_generics_project.name
    node_names = get_node_names(mock_ingestor, "Class")
    expected_classes = {
        f"{project_name}.src.main.kotlin.com.example.GenericClasses.Box",
        f"{project_name}.src.main.kotlin.com.example.GenericClasses.Pair",
        f"{project_name}.src.main.kotlin.com.example.GenericClasses.Container",
    }
    missing_classes = expected_classes - node_names
    assert not missing_classes, (
        f"Missing expected classes: {sorted(list(missing_classes))}"
    )


def test_generic_functions(
    kotlin_generics_project: Path,
    mock_ingestor: MagicMock,
) -> None:
    """Test generic functions."""
    test_file = (
        kotlin_generics_project
        / "src"
        / "main"
        / "kotlin"
        / "com"
        / "example"
        / "GenericFunctions.kt"
    )
    test_file.write_text(
        """
package com.example

// Simple generic function
fun <T> identity(value: T): T {
    return value
}

// Generic function with constraints
fun <T : Comparable<T>> max(a: T, b: T): T {
    return if (a > b) a else b
}

// Generic extension function
fun <T> List<T>.firstOrNull(): T? {
    return if (isEmpty()) null else this[0]
}

// Generic function with multiple type parameters
fun <T, U> mapValue(value: T, mapper: (T) -> U): U {
    return mapper(value)
}

// Reified type parameter (inline function)
inline fun <reified T> List<*>.filterIsInstance(): List<T> {
    return this.filterIsInstance<T>()
}
"""
    )

    run_updater(kotlin_generics_project, mock_ingestor, skip_if_missing="kotlin")


def test_generic_interfaces(
    kotlin_generics_project: Path,
    mock_ingestor: MagicMock,
) -> None:
    """Test generic interfaces."""
    test_file = (
        kotlin_generics_project
        / "src"
        / "main"
        / "kotlin"
        / "com"
        / "example"
        / "GenericInterfaces.kt"
    )
    test_file.write_text(
        """
package com.example

// Generic interface
interface Repository<T> {
    fun save(entity: T)
    fun findById(id: Int): T?
    fun findAll(): List<T>
}

// Implementation of generic interface
class UserRepository : Repository<User> {
    override fun save(entity: User) {
        // Save user
    }

    override fun findById(id: Int): User? {
        return null
    }

    override fun findAll(): List<User> {
        return emptyList()
    }
}

class User(val id: Int, val name: String)

// Generic interface with constraints
interface Comparable<T> {
    fun compareTo(other: T): Int
}

class ComparableNumber(val value: Int) : Comparable<ComparableNumber> {
    override fun compareTo(other: ComparableNumber): Int {
        return value.compareTo(other.value)
    }
}
"""
    )

    run_updater(kotlin_generics_project, mock_ingestor, skip_if_missing="kotlin")

    project_name = kotlin_generics_project.name
    class_nodes = get_nodes(mock_ingestor, "Class")
    interface_nodes = get_nodes(mock_ingestor, "Interface")
    created_classes = get_qualified_names(class_nodes)
    created_interfaces = get_qualified_names(interface_nodes)

    expected_classes = {
        f"{project_name}.src.main.kotlin.com.example.GenericInterfaces.UserRepository",
        f"{project_name}.src.main.kotlin.com.example.GenericInterfaces.User",
    }
    expected_interfaces = {
        f"{project_name}.src.main.kotlin.com.example.GenericInterfaces.Repository",
    }

    missing_classes = expected_classes - created_classes
    missing_interfaces = expected_interfaces - created_interfaces

    assert not missing_classes, (
        f"Missing expected classes: {sorted(list(missing_classes))}"
    )
    assert not missing_interfaces, (
        f"Missing expected interfaces: {sorted(list(missing_interfaces))}"
    )


def test_variance(
    kotlin_generics_project: Path,
    mock_ingestor: MagicMock,
) -> None:
    """Test generic variance (in, out)."""
    test_file = (
        kotlin_generics_project
        / "src"
        / "main"
        / "kotlin"
        / "com"
        / "example"
        / "Variance.kt"
    )
    test_file.write_text(
        """
package com.example

// Covariance (out)
interface Producer<out T> {
    fun produce(): T
}

// Contravariance (in)
interface Consumer<in T> {
    fun consume(item: T)
}

// Invariant
interface Storage<T> {
    fun store(item: T)
    fun retrieve(): T
}

// Usage examples
class StringProducer : Producer<String> {
    override fun produce(): String = "Hello"
}

class AnyConsumer : Consumer<Any> {
    override fun consume(item: Any) {
        println(item)
    }
}
"""
    )

    run_updater(kotlin_generics_project, mock_ingestor, skip_if_missing="kotlin")

    project_name = kotlin_generics_project.name
    interface_nodes = get_nodes(mock_ingestor, "Interface")
    created_interfaces = get_qualified_names(interface_nodes)

    expected_interfaces = {
        f"{project_name}.src.main.kotlin.com.example.Variance.Producer",
        f"{project_name}.src.main.kotlin.com.example.Variance.Consumer",
        f"{project_name}.src.main.kotlin.com.example.Variance.Storage",
    }

    missing_interfaces = expected_interfaces - created_interfaces

    assert not missing_interfaces, (
        f"Missing expected interfaces: {sorted(list(missing_interfaces))}"
    )


def test_star_projections(
    kotlin_generics_project: Path,
    mock_ingestor: MagicMock,
) -> None:
    """Test star projections."""
    test_file = (
        kotlin_generics_project
        / "src"
        / "main"
        / "kotlin"
        / "com"
        / "example"
        / "StarProjections.kt"
    )
    test_file.write_text(
        """
package com.example

class StarProjectionExamples {
    // Star projection for read-only
    fun processList(list: List<*>) {
        for (item in list) {
            println(item)
        }
    }

    // Star projection with constraints
    fun processNumbers(numbers: List<out Number>) {
        for (number in numbers) {
            println(number.toDouble())
        }
    }

    // Star projection for function types
    fun processFunction(func: (Any) -> *) {
        func(42)
    }
}
"""
    )

    run_updater(kotlin_generics_project, mock_ingestor, skip_if_missing="kotlin")
