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
def kotlin_project(temp_repo: Path) -> Path:
    """Create a comprehensive Kotlin project structure."""
    project_path = temp_repo / "kotlin_test"
    project_path.mkdir()

    (project_path / "src").mkdir()
    (project_path / "src" / "main").mkdir()
    (project_path / "src" / "main" / "kotlin").mkdir()
    (project_path / "src" / "main" / "kotlin" / "com").mkdir()
    (project_path / "src" / "main" / "kotlin" / "com" / "example").mkdir()
    (project_path / "src" / "test").mkdir()
    (project_path / "src" / "test" / "kotlin").mkdir()

    return project_path


def test_basic_kotlin_classes(
    kotlin_project: Path,
    mock_ingestor: MagicMock,
) -> None:
    """Test basic Kotlin class parsing including inheritance and interfaces."""
    test_file = (
        kotlin_project
        / "src"
        / "main"
        / "kotlin"
        / "com"
        / "example"
        / "BasicClasses.kt"
    )
    test_file.write_text(
        """
package com.example

// Basic class declaration
class BasicClass(val name: String) {
    private var value: Int = 0

    fun getValue(): Int {
        return value
    }

    fun setValue(newValue: Int) {
        value = newValue
    }
}

// Class with inheritance
open class BaseClass(val id: Int) {
    open fun display() {
        println("Base: $id")
    }
}

class ExtendedClass(id: Int, val flag: Boolean) : BaseClass(id) {
    override fun display() {
        super.display()
        println("Extended: $flag")
    }
}

// Interface declaration
interface Drawable {
    fun draw()
    fun clear() {
        println("Clearing...")
    }
}

// Class implementing interface
class Circle(val radius: Double) : Drawable {
    override fun draw() {
        println("Drawing circle with radius: $radius")
    }
}

// Abstract class
abstract class Shape {
    protected var color: String = "black"

    abstract fun area(): Double
    abstract fun perimeter(): Double

    fun setColor(newColor: String) {
        color = newColor
    }
}

// Concrete implementation
class Rectangle(val width: Double, val height: Double) : Shape() {
    override fun area(): Double = width * height
    override fun perimeter(): Double = 2 * (width + height)
}
"""
    )

    run_updater(kotlin_project, mock_ingestor, skip_if_missing="kotlin")

    project_name = kotlin_project.name
    node_names = get_node_names(mock_ingestor, "Class")
    expected_classes = {
        f"{project_name}.src.main.kotlin.com.example.BasicClasses.BasicClass",
        f"{project_name}.src.main.kotlin.com.example.BasicClasses.ExtendedClass",
        f"{project_name}.src.main.kotlin.com.example.BasicClasses.Circle",
        f"{project_name}.src.main.kotlin.com.example.BasicClasses.Rectangle",
    }
    missing_classes = expected_classes - node_names
    assert not missing_classes, (
        f"Missing expected classes: {sorted(list(missing_classes))}"
    )


def test_data_classes(
    kotlin_project: Path,
    mock_ingestor: MagicMock,
) -> None:
    """Test Kotlin data class parsing."""
    test_file = (
        kotlin_project
        / "src"
        / "main"
        / "kotlin"
        / "com"
        / "example"
        / "DataClasses.kt"
    )
    test_file.write_text(
        """
package com.example

// Simple data class
data class Point(val x: Int, val y: Int)

// Data class with default values
data class Person(
    val name: String,
    val age: Int = 0,
    val email: String = ""
) {
    fun getDisplayName(): String {
        return name.uppercase()
    }
}

// Data class with validation
data class User(val username: String, val password: String) {
    init {
        require(username.isNotBlank()) { "Username cannot be blank" }
        require(password.length >= 8) { "Password must be at least 8 characters" }
    }
}

// Data class with copy
data class Product(
    val id: Int,
    val name: String,
    val price: Double
) {
    fun applyDiscount(discount: Double): Product {
        return copy(price = price * (1 - discount))
    }
}

// Nested data class
data class Address(
    val street: String,
    val city: String,
    val zipCode: String
)

data class Company(
    val name: String,
    val address: Address
)
"""
    )

    run_updater(kotlin_project, mock_ingestor, skip_if_missing="kotlin")

    project_name = kotlin_project.name
    node_names = get_node_names(mock_ingestor, "Class")
    expected_classes = {
        f"{project_name}.src.main.kotlin.com.example.DataClasses.Point",
        f"{project_name}.src.main.kotlin.com.example.DataClasses.Person",
        f"{project_name}.src.main.kotlin.com.example.DataClasses.User",
        f"{project_name}.src.main.kotlin.com.example.DataClasses.Product",
        f"{project_name}.src.main.kotlin.com.example.DataClasses.Company",
    }
    missing_classes = expected_classes - node_names
    assert not missing_classes, (
        f"Missing expected classes: {sorted(list(missing_classes))}"
    )


def test_sealed_classes(
    kotlin_project: Path,
    mock_ingestor: MagicMock,
) -> None:
    """Test Kotlin sealed class parsing."""
    test_file = (
        kotlin_project
        / "src"
        / "main"
        / "kotlin"
        / "com"
        / "example"
        / "SealedClasses.kt"
    )
    test_file.write_text(
        """
package com.example

// Sealed class for Result type
sealed class Result<out T> {
    data class Success<T>(val data: T) : Result<T>()
    data class Error(val message: String, val code: Int) : Result<Nothing>()
    object Loading : Result<Nothing>()
}

// Sealed class for network states
sealed class NetworkState {
    object Idle : NetworkState()
    object Loading : NetworkState()
    data class Success(val data: String) : NetworkState()
    data class Error(val exception: Throwable) : NetworkState()
}

// Sealed class with methods
sealed class Expression {
    data class Number(val value: Int) : Expression()
    data class Add(val left: Expression, val right: Expression) : Expression()
    data class Multiply(val left: Expression, val right: Expression) : Expression()

    fun evaluate(): Int = when (this) {
        is Number -> value
        is Add -> left.evaluate() + right.evaluate()
        is Multiply -> left.evaluate() * right.evaluate()
    }
}
"""
    )

    run_updater(kotlin_project, mock_ingestor, skip_if_missing="kotlin")

    project_name = kotlin_project.name
    node_names = get_node_names(mock_ingestor, "Class")
    expected_classes = {
        f"{project_name}.src.main.kotlin.com.example.SealedClasses.Result",
        f"{project_name}.src.main.kotlin.com.example.SealedClasses.NetworkState",
        f"{project_name}.src.main.kotlin.com.example.SealedClasses.Expression",
    }
    missing_classes = expected_classes - node_names
    assert not missing_classes, (
        f"Missing expected classes: {sorted(list(missing_classes))}"
    )


def test_enum_classes(
    kotlin_project: Path,
    mock_ingestor: MagicMock,
) -> None:
    """Test Kotlin enum class parsing."""
    test_file = (
        kotlin_project / "src" / "main" / "kotlin" / "com" / "example" / "Enums.kt"
    )
    test_file.write_text(
        """
package com.example

// Simple enum
enum class Direction {
    NORTH, SOUTH, EAST, WEST
}

// Enum with properties
enum class Color(val rgb: Int) {
    RED(0xFF0000),
    GREEN(0x00FF00),
    BLUE(0x0000FF);

    fun containsRed(): Boolean = (rgb and 0xFF0000) != 0
}

// Enum with methods
enum class Planet(val mass: Double, val radius: Double) {
    MERCURY(3.303e+23, 2.4397e6),
    VENUS(4.869e+24, 6.0518e6),
    EARTH(5.976e+24, 6.37814e6),
    MARS(6.421e+23, 3.3972e6);

    private val G = 6.67300E-11

    fun surfaceGravity(): Double {
        return G * mass / (radius * radius)
    }

    fun surfaceWeight(otherMass: Double): Double {
        return otherMass * surfaceGravity()
    }
}
"""
    )

    run_updater(kotlin_project, mock_ingestor, skip_if_missing="kotlin")

    project_name = kotlin_project.name
    enum_nodes = get_nodes(mock_ingestor, "Enum")
    created_enums = get_qualified_names(enum_nodes)

    expected_enums = {
        f"{project_name}.src.main.kotlin.com.example.Enums.Direction",
        f"{project_name}.src.main.kotlin.com.example.Enums.Color",
        f"{project_name}.src.main.kotlin.com.example.Enums.Planet",
    }

    missing_enums = expected_enums - created_enums

    assert not missing_enums, f"Missing expected enums: {sorted(list(missing_enums))}"


def test_object_declarations(
    kotlin_project: Path,
    mock_ingestor: MagicMock,
) -> None:
    """Test Kotlin object declarations (singletons)."""
    test_file = (
        kotlin_project / "src" / "main" / "kotlin" / "com" / "example" / "Objects.kt"
    )
    test_file.write_text(
        """
package com.example

// Object declaration (singleton)
object DatabaseManager {
    private var connectionCount = 0

    fun connect() {
        connectionCount++
        println("Connected. Total connections: $connectionCount")
    }

    fun disconnect() {
        connectionCount--
        println("Disconnected. Remaining connections: $connectionCount")
    }

    fun getConnectionCount(): Int = connectionCount
}

// Object implementing interface
interface Logger {
    fun log(message: String)
}

object ConsoleLogger : Logger {
    override fun log(message: String) {
        println("[LOG] $message")
    }
}

// Companion object
class MyClass {
    companion object {
        const val CONSTANT = 42
        fun create(): MyClass = MyClass()
        fun createWithValue(value: Int): MyClass {
            val instance = MyClass()
            instance.value = value
            return instance
        }
    }

    var value: Int = 0
}

// Named companion object
class Factory {
    companion object Factory {
        fun create(): Factory = Factory()
    }
}
"""
    )

    run_updater(kotlin_project, mock_ingestor, skip_if_missing="kotlin")

    project_name = kotlin_project.name
    node_names = get_node_names(mock_ingestor, "Class")
    expected_classes = {
        f"{project_name}.src.main.kotlin.com.example.Objects.DatabaseManager",
        f"{project_name}.src.main.kotlin.com.example.Objects.ConsoleLogger",
        f"{project_name}.src.main.kotlin.com.example.Objects.MyClass",
        f"{project_name}.src.main.kotlin.com.example.Objects.Factory",
    }
    missing_classes = expected_classes - node_names
    assert not missing_classes, (
        f"Missing expected classes: {sorted(list(missing_classes))}"
    )


def test_extension_functions(
    kotlin_project: Path,
    mock_ingestor: MagicMock,
) -> None:
    """Test Kotlin extension functions."""
    test_file = (
        kotlin_project / "src" / "main" / "kotlin" / "com" / "example" / "Extensions.kt"
    )
    test_file.write_text(
        """
package com.example

// Extension function for String
fun String.reverse(): String {
    return this.reversed()
}

// Extension property
val String.lastChar: Char
    get() = this[length - 1]

// Extension function with receiver
fun String.removeWhitespace(): String {
    return this.replace(" ", "")
}

// Extension function for collections
fun <T> List<T>.secondOrNull(): T? {
    return if (size >= 2) this[1] else null
}

// Extension function for nullable types
fun String?.isNullOrEmptyOrBlank(): Boolean {
    return this == null || this.isEmpty() || this.isBlank()
}

// Extension function with generic receiver
fun <T> T.print(): T {
    println(this)
    return this
}

// Extension function for Int
fun Int.isEven(): Boolean = this % 2 == 0

// Extension function for custom class
class Person(val name: String)

fun Person.greet(): String {
    return "Hello, I'm $name"
}
"""
    )

    run_updater(kotlin_project, mock_ingestor, skip_if_missing="kotlin")

    # (H) Extension functions should be parsed as functions
    function_nodes = get_nodes(mock_ingestor, "Function")
    qualified_names = get_qualified_names(function_nodes)
    assert any("reverse" in qn for qn in qualified_names)
    assert any("removeWhitespace" in qn for qn in qualified_names)


def test_inline_functions(
    kotlin_project: Path,
    mock_ingestor: MagicMock,
) -> None:
    """Test Kotlin inline functions."""
    test_file = (
        kotlin_project
        / "src"
        / "main"
        / "kotlin"
        / "com"
        / "example"
        / "InlineFunctions.kt"
    )
    test_file.write_text(
        """
package com.example

// Inline function
inline fun <T> measureTime(block: () -> T): T {
    val start = System.currentTimeMillis()
    val result = block()
    val end = System.currentTimeMillis()
    println("Execution time: ${end - start}ms")
    return result
}

// Inline function with reified type parameter
inline fun <reified T> List<*>.filterIsInstance(): List<T> {
    return this.filterIsInstance<T>()
}

// Inline function with crossinline
inline fun executeWithCallback(
    crossinline callback: () -> Unit,
    action: () -> Unit
) {
    action()
    callback()
}

// Inline extension function
inline fun String.ifEmpty(defaultValue: () -> String): String {
    return if (isEmpty()) defaultValue() else this
}
"""
    )

    run_updater(kotlin_project, mock_ingestor, skip_if_missing="kotlin")

    function_nodes = get_nodes(mock_ingestor, "Function")
    qualified_names = get_qualified_names(function_nodes)
    assert any("measureTime" in qn for qn in qualified_names)


def test_type_aliases(
    kotlin_project: Path,
    mock_ingestor: MagicMock,
) -> None:
    """Test Kotlin type aliases."""
    test_file = (
        kotlin_project
        / "src"
        / "main"
        / "kotlin"
        / "com"
        / "example"
        / "TypeAliases.kt"
    )
    test_file.write_text(
        """
package com.example

// Simple type alias
typealias Name = String
typealias Age = Int

// Function type alias
typealias StringMapper = (String) -> String
typealias Predicate<T> = (T) -> Boolean

// Generic type alias
typealias StringList = List<String>
typealias IntMap = Map<Int, String>

// Complex type alias
typealias EventHandler = (String, Int) -> Unit
typealias AsyncCallback<T> = (Result<T>) -> Unit

// Using type aliases
class User(val name: Name, val age: Age) {
    fun processName(mapper: StringMapper): Name {
        return mapper(name)
    }
}
"""
    )

    run_updater(kotlin_project, mock_ingestor, skip_if_missing="kotlin")

    project_name = kotlin_project.name
    node_names = get_node_names(mock_ingestor, "Class")
    expected_classes = {
        f"{project_name}.src.main.kotlin.com.example.TypeAliases.User",
    }
    missing_classes = expected_classes - node_names
    assert not missing_classes, (
        f"Missing expected classes: {sorted(list(missing_classes))}"
    )


def test_properties_and_fields(
    kotlin_project: Path,
    mock_ingestor: MagicMock,
) -> None:
    """Test Kotlin properties and fields."""
    test_file = (
        kotlin_project / "src" / "main" / "kotlin" / "com" / "example" / "Properties.kt"
    )
    test_file.write_text(
        """
package com.example

class PropertiesExample {
    // Simple property
    var name: String = "default"

    // Read-only property
    val id: Int = 42

    // Property with custom getter
    val isEmpty: Boolean
        get() = name.isEmpty()

    // Property with custom setter
    var value: Int = 0
        set(newValue) {
            if (newValue >= 0) {
                field = newValue
            }
        }

    // Property with backing field
    private var _count: Int = 0
    val count: Int
        get() = _count

    // Lazy property
    val lazyValue: String by lazy {
        println("Computing lazy value")
        "Lazy"
    }

    // Lateinit property
    lateinit var lateInitProperty: String

    // Const property (must be in companion object)
    companion object {
        const val CONSTANT = "constant"
    }
}
"""
    )

    run_updater(kotlin_project, mock_ingestor, skip_if_missing="kotlin")

    project_name = kotlin_project.name
    node_names = get_node_names(mock_ingestor, "Class")
    expected_classes = {
        f"{project_name}.src.main.kotlin.com.example.Properties.PropertiesExample",
    }
    missing_classes = expected_classes - node_names
    assert not missing_classes, (
        f"Missing expected classes: {sorted(list(missing_classes))}"
    )
