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
def kotlin_modern_project(temp_repo: Path) -> Path:
    """Create a Kotlin project for testing modern features."""
    project_path = temp_repo / "kotlin_modern_test"
    project_path.mkdir()

    (project_path / "src").mkdir()
    (project_path / "src" / "main").mkdir()
    (project_path / "src" / "main" / "kotlin").mkdir()
    (project_path / "src" / "main" / "kotlin" / "com").mkdir()
    (project_path / "src" / "main" / "kotlin" / "com" / "example").mkdir()

    return project_path


def test_destructuring_declarations(
    kotlin_modern_project: Path,
    mock_ingestor: MagicMock,
) -> None:
    """Test destructuring declarations."""
    test_file = (
        kotlin_modern_project
        / "src"
        / "main"
        / "kotlin"
        / "com"
        / "example"
        / "Destructuring.kt"
    )
    test_file.write_text(
        """
package com.example

data class Person(val name: String, val age: Int)
data class Point(val x: Int, val y: Int)

class DestructuringExamples {
    fun destructureDataClass() {
        val person = Person("Alice", 30)
        val (name, age) = person
        println("$name is $age years old")
    }

    fun destructureMap() {
        val map = mapOf("name" to "Bob", "age" to 25)
        for ((key, value) in map) {
            println("$key = $value")
        }
    }

    fun destructureList() {
        val list = listOf(1, 2, 3, 4, 5)
        val (first, second, third) = list
        println("First: $first, Second: $second, Third: $third")
    }

    fun destructureWithUnderscore() {
        val point = Point(10, 20)
        val (x, _) = point  // Ignore y
        println("x = $x")
    }

    fun destructureInLambda() {
        val pairs = listOf(Pair(1, "one"), Pair(2, "two"))
        pairs.forEach { (number, word) ->
            println("$number -> $word")
        }
    }
}
"""
    )

    run_updater(kotlin_modern_project, mock_ingestor, skip_if_missing="kotlin")

    project_name = kotlin_modern_project.name
    node_names = get_node_names(mock_ingestor, "Class")
    expected_classes = {
        f"{project_name}.src.main.kotlin.com.example.Destructuring.Person",
        f"{project_name}.src.main.kotlin.com.example.Destructuring.Point",
        f"{project_name}.src.main.kotlin.com.example.Destructuring.DestructuringExamples",
    }
    missing_classes = expected_classes - node_names
    assert not missing_classes, (
        f"Missing expected classes: {sorted(list(missing_classes))}"
    )


def test_smart_casts(
    kotlin_modern_project: Path,
    mock_ingestor: MagicMock,
) -> None:
    """Test smart casts."""
    test_file = (
        kotlin_modern_project
        / "src"
        / "main"
        / "kotlin"
        / "com"
        / "example"
        / "SmartCasts.kt"
    )
    test_file.write_text(
        """
package com.example

class SmartCastExamples {
    fun demonstrateSmartCast(value: Any) {
        if (value is String) {
            // Smart cast: value is automatically String here
            println(value.length)
            println(value.uppercase())
        }

        if (value !is String) {
            return
        }
        // Smart cast: value is String here too
        println(value.length)
    }

    fun smartCastWithWhen(value: Any): Int {
        return when (value) {
            is Int -> value * 2  // Smart cast to Int
            is String -> value.length  // Smart cast to String
            is List<*> -> value.size  // Smart cast to List
            else -> 0
        }
    }

    fun safeCast(value: Any): String? {
        return value as? String  // Safe cast returns null if fails
    }
}
"""
    )

    run_updater(kotlin_modern_project, mock_ingestor, skip_if_missing="kotlin")


def test_delegation(
    kotlin_modern_project: Path,
    mock_ingestor: MagicMock,
) -> None:
    """Test class delegation."""
    test_file = (
        kotlin_modern_project
        / "src"
        / "main"
        / "kotlin"
        / "com"
        / "example"
        / "Delegation.kt"
    )
    test_file.write_text(
        """
package com.example

interface Base {
    fun print()
}

class BaseImpl(val x: Int) : Base {
    override fun print() {
        println(x)
    }
}

// Class delegation
class Derived(b: Base) : Base by b {
    // Can override methods
    override fun print() {
        println("Derived")
    }
}

// Property delegation
class Delegate {
    private var value: String = ""

    operator fun getValue(thisRef: Any?, property: kotlin.reflect.KProperty<*>): String {
        return value
    }

    operator fun setValue(thisRef: Any?, property: kotlin.reflect.KProperty<*>, value: String) {
        this.value = value
    }
}

class PropertyDelegationExample {
    var delegatedProperty: String by Delegate()
}

// Lazy delegation
class LazyExample {
    val lazyValue: String by lazy {
        println("Computing lazy value")
        "Lazy"
    }
}
"""
    )

    run_updater(kotlin_modern_project, mock_ingestor, skip_if_missing="kotlin")

    project_name = kotlin_modern_project.name
    class_nodes = get_nodes(mock_ingestor, "Class")
    interface_nodes = get_nodes(mock_ingestor, "Interface")
    created_classes = get_qualified_names(class_nodes)
    created_interfaces = get_qualified_names(interface_nodes)

    expected_classes = {
        f"{project_name}.src.main.kotlin.com.example.Delegation.BaseImpl",
        f"{project_name}.src.main.kotlin.com.example.Delegation.Derived",
    }
    expected_interfaces = {
        f"{project_name}.src.main.kotlin.com.example.Delegation.Base",
    }

    missing_classes = expected_classes - created_classes
    missing_interfaces = expected_interfaces - created_interfaces

    assert not missing_classes, (
        f"Missing expected classes: {sorted(list(missing_classes))}"
    )
    assert not missing_interfaces, (
        f"Missing expected interfaces: {sorted(list(missing_interfaces))}"
    )


def test_inline_classes(
    kotlin_modern_project: Path,
    mock_ingestor: MagicMock,
) -> None:
    """Test inline classes (value classes)."""
    test_file = (
        kotlin_modern_project
        / "src"
        / "main"
        / "kotlin"
        / "com"
        / "example"
        / "InlineClasses.kt"
    )
    test_file.write_text(
        """
package com.example

// Value class (inline class)
@JvmInline
value class Password(val value: String)

@JvmInline
value class Username(val value: String)

@JvmInline
value class Email(val value: String)

class UserService {
    fun createUser(username: Username, password: Password, email: Email) {
        // Type-safe parameters
        println("Creating user: ${username.value}")
    }

    fun validatePassword(password: Password): Boolean {
        return password.value.length >= 8
    }
}

// Value class with methods
@JvmInline
value class Meters(val value: Double) {
    fun toKilometers(): Kilometers {
        return Kilometers(value / 1000.0)
    }
}

@JvmInline
value class Kilometers(val value: Double) {
    fun toMeters(): Meters {
        return Meters(value * 1000.0)
    }
}
"""
    )

    run_updater(kotlin_modern_project, mock_ingestor, skip_if_missing="kotlin")


def test_multiplatform_expect_actual(
    kotlin_modern_project: Path,
    mock_ingestor: MagicMock,
) -> None:
    """Test expect/actual declarations (multiplatform)."""
    test_file = (
        kotlin_modern_project
        / "src"
        / "main"
        / "kotlin"
        / "com"
        / "example"
        / "Platform.kt"
    )
    test_file.write_text(
        """
package com.example

// Expect declaration
expect class Platform() {
    val name: String
    fun getPlatformInfo(): String
}

// Actual implementation (would be in platform-specific source sets)
actual class Platform {
    actual val name: String = "JVM"

    actual fun getPlatformInfo(): String {
        return "Running on JVM"
    }
}

// Expect function
expect fun getCurrentTime(): Long

// Expect property
expect val platformName: String
"""
    )

    run_updater(kotlin_modern_project, mock_ingestor, skip_if_missing="kotlin")


def test_context_receivers(
    kotlin_modern_project: Path,
    mock_ingestor: MagicMock,
) -> None:
    """Test context receivers (experimental)."""
    test_file = (
        kotlin_modern_project
        / "src"
        / "main"
        / "kotlin"
        / "com"
        / "example"
        / "ContextReceivers.kt"
    )
    test_file.write_text(
        """
package com.example

interface LoggingContext {
    fun log(message: String)
}

interface DatabaseContext {
    fun query(sql: String): List<String>
}

class ContextExamples {
    // Context receiver function
    context(LoggingContext)
    fun processWithLogging(data: String) {
        log("Processing: $data")
    }

    // Multiple context receivers
    context(LoggingContext, DatabaseContext)
    fun processWithContext(data: String) {
        log("Querying database")
        val results = query("SELECT * FROM table")
        log("Found ${results.size} results")
    }
}
"""
    )

    run_updater(kotlin_modern_project, mock_ingestor, skip_if_missing="kotlin")


def test_data_class_copy_and_equals(
    kotlin_modern_project: Path,
    mock_ingestor: MagicMock,
) -> None:
    """Test data class copy and equals methods."""
    test_file = (
        kotlin_modern_project
        / "src"
        / "main"
        / "kotlin"
        / "com"
        / "example"
        / "DataClassFeatures.kt"
    )
    test_file.write_text(
        """
package com.example

data class User(
    val id: Int,
    val name: String,
    val email: String
) {
    // Custom equals (though data class provides it)
    override fun equals(other: Any?): Boolean {
        if (this === other) return true
        if (other !is User) return false
        return id == other.id && name == other.name && email == other.email
    }

    // Custom hashCode
    override fun hashCode(): Int {
        var result = id
        result = 31 * result + name.hashCode()
        result = 31 * result + email.hashCode()
        return result
    }
}

class DataClassUsage {
    fun demonstrateCopy() {
        val user1 = User(1, "Alice", "alice@example.com")
        val user2 = user1.copy(name = "Bob")  // Copy with modified name
        val user3 = user1.copy(email = "newemail@example.com")  // Copy with modified email
    }

    fun demonstrateEquals() {
        val user1 = User(1, "Alice", "alice@example.com")
        val user2 = User(1, "Alice", "alice@example.com")
        val areEqual = user1 == user2  // true (structural equality)
    }

    fun demonstrateComponentFunctions() {
        val user = User(1, "Alice", "alice@example.com")
        val (id, name, email) = user  // Destructuring
        println("ID: $id, Name: $name, Email: $email")
    }
}
"""
    )

    run_updater(kotlin_modern_project, mock_ingestor, skip_if_missing="kotlin")

    project_name = kotlin_modern_project.name
    node_names = get_node_names(mock_ingestor, "Class")
    expected_classes = {
        f"{project_name}.src.main.kotlin.com.example.DataClassFeatures.User",
        f"{project_name}.src.main.kotlin.com.example.DataClassFeatures.DataClassUsage",
    }
    missing_classes = expected_classes - node_names
    assert not missing_classes, (
        f"Missing expected classes: {sorted(list(missing_classes))}"
    )
