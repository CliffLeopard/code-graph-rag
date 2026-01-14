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
def kotlin_inheritance_project(temp_repo: Path) -> Path:
    """Create a Kotlin project for testing inheritance."""
    project_path = temp_repo / "kotlin_inheritance_test"
    project_path.mkdir()

    (project_path / "src").mkdir()
    (project_path / "src" / "main").mkdir()
    (project_path / "src" / "main" / "kotlin").mkdir()
    (project_path / "src" / "main" / "kotlin" / "com").mkdir()
    (project_path / "src" / "main" / "kotlin" / "com" / "example").mkdir()

    return project_path


def test_class_inheritance(
    kotlin_inheritance_project: Path,
    mock_ingestor: MagicMock,
) -> None:
    """Test class inheritance."""
    test_file = (
        kotlin_inheritance_project
        / "src"
        / "main"
        / "kotlin"
        / "com"
        / "example"
        / "ClassInheritance.kt"
    )
    test_file.write_text(
        """
package com.example

open class Animal(val name: String) {
    open fun makeSound() {
        println("Some sound")
    }
}

class Dog(name: String) : Animal(name) {
    override fun makeSound() {
        println("Woof!")
    }
}

class Cat(name: String) : Animal(name) {
    override fun makeSound() {
        println("Meow!")
    }
}

// Multi-level inheritance
open class Mammal(name: String) : Animal(name) {
    open fun giveBirth() {
        println("Giving birth")
    }
}

class Human(name: String) : Mammal(name) {
    override fun makeSound() {
        println("Hello!")
    }
}
"""
    )

    run_updater(kotlin_inheritance_project, mock_ingestor, skip_if_missing="kotlin")

    project_name = kotlin_inheritance_project.name
    node_names = get_node_names(mock_ingestor, "Class")
    expected_classes = {
        f"{project_name}.src.main.kotlin.com.example.ClassInheritance.Animal",
        f"{project_name}.src.main.kotlin.com.example.ClassInheritance.Dog",
        f"{project_name}.src.main.kotlin.com.example.ClassInheritance.Cat",
        f"{project_name}.src.main.kotlin.com.example.ClassInheritance.Mammal",
        f"{project_name}.src.main.kotlin.com.example.ClassInheritance.Human",
    }
    missing_classes = expected_classes - node_names
    assert not missing_classes, (
        f"Missing expected classes: {sorted(list(missing_classes))}"
    )


def test_interface_implementation(
    kotlin_inheritance_project: Path,
    mock_ingestor: MagicMock,
) -> None:
    """Test interface implementation."""
    test_file = (
        kotlin_inheritance_project
        / "src"
        / "main"
        / "kotlin"
        / "com"
        / "example"
        / "InterfaceImplementation.kt"
    )
    test_file.write_text(
        """
package com.example

interface Drawable {
    fun draw()
}

interface Clickable {
    fun click()
}

// Single interface
class Circle : Drawable {
    override fun draw() {
        println("Drawing circle")
    }
}

// Multiple interfaces
class Button : Drawable, Clickable {
    override fun draw() {
        println("Drawing button")
    }

    override fun click() {
        println("Button clicked")
    }
}

// Class with inheritance and interfaces
open class Shape {
    protected var color: String = "black"
}

class Rectangle : Shape(), Drawable {
    override fun draw() {
        println("Drawing rectangle")
    }
}
"""
    )

    run_updater(kotlin_inheritance_project, mock_ingestor, skip_if_missing="kotlin")

    project_name = kotlin_inheritance_project.name
    class_nodes = get_nodes(mock_ingestor, "Class")
    interface_nodes = get_nodes(mock_ingestor, "Interface")
    created_classes = get_qualified_names(class_nodes)
    created_interfaces = get_qualified_names(interface_nodes)

    expected_classes = {
        f"{project_name}.src.main.kotlin.com.example.InterfaceImplementation.Circle",
        f"{project_name}.src.main.kotlin.com.example.InterfaceImplementation.Button",
        f"{project_name}.src.main.kotlin.com.example.InterfaceImplementation.Rectangle",
    }
    expected_interfaces = {
        f"{project_name}.src.main.kotlin.com.example.InterfaceImplementation.Drawable",
        f"{project_name}.src.main.kotlin.com.example.InterfaceImplementation.Clickable",
    }

    missing_classes = expected_classes - created_classes
    missing_interfaces = expected_interfaces - created_interfaces

    assert not missing_classes, (
        f"Missing expected classes: {sorted(list(missing_classes))}"
    )
    assert not missing_interfaces, (
        f"Missing expected interfaces: {sorted(list(missing_interfaces))}"
    )


def test_abstract_classes(
    kotlin_inheritance_project: Path,
    mock_ingestor: MagicMock,
) -> None:
    """Test abstract classes."""
    test_file = (
        kotlin_inheritance_project
        / "src"
        / "main"
        / "kotlin"
        / "com"
        / "example"
        / "AbstractClasses.kt"
    )
    test_file.write_text(
        """
package com.example

abstract class Shape {
    abstract fun area(): Double
    abstract fun perimeter(): Double

    fun display() {
        println("Area: ${area()}, Perimeter: ${perimeter()}")
    }
}

class Rectangle(val width: Double, val height: Double) : Shape() {
    override fun area(): Double = width * height
    override fun perimeter(): Double = 2 * (width + height)
}

class Circle(val radius: Double) : Shape() {
    override fun area(): Double = Math.PI * radius * radius
    override fun perimeter(): Double = 2 * Math.PI * radius
}
"""
    )

    run_updater(kotlin_inheritance_project, mock_ingestor, skip_if_missing="kotlin")

    project_name = kotlin_inheritance_project.name
    node_names = get_node_names(mock_ingestor, "Class")
    expected_classes = {
        f"{project_name}.src.main.kotlin.com.example.AbstractClasses.Shape",
        f"{project_name}.src.main.kotlin.com.example.AbstractClasses.Rectangle",
        f"{project_name}.src.main.kotlin.com.example.AbstractClasses.Circle",
    }
    missing_classes = expected_classes - node_names
    assert not missing_classes, (
        f"Missing expected classes: {sorted(list(missing_classes))}"
    )


def test_override_keyword(
    kotlin_inheritance_project: Path,
    mock_ingestor: MagicMock,
) -> None:
    """Test override keyword."""
    test_file = (
        kotlin_inheritance_project
        / "src"
        / "main"
        / "kotlin"
        / "com"
        / "example"
        / "Override.kt"
    )
    test_file.write_text(
        """
package com.example

open class Base {
    open fun method1() {}
    open fun method2() {}
    open val property1: Int = 0
    open val property2: String = "base"
}

class Derived : Base() {
    override fun method1() {
        super.method1()
    }

    override fun method2() {
        println("Overridden")
    }

    override val property1: Int = 42
    override val property2: String = "derived"
}
"""
    )

    run_updater(kotlin_inheritance_project, mock_ingestor, skip_if_missing="kotlin")

    project_name = kotlin_inheritance_project.name
    node_names = get_node_names(mock_ingestor, "Class")
    expected_classes = {
        f"{project_name}.src.main.kotlin.com.example.Override.Base",
        f"{project_name}.src.main.kotlin.com.example.Override.Derived",
    }
    missing_classes = expected_classes - node_names
    assert not missing_classes, (
        f"Missing expected classes: {sorted(list(missing_classes))}"
    )
