from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from codebase_rag.tests.conftest import get_node_names, run_updater


@pytest.fixture
def kotlin_nested_project(temp_repo: Path) -> Path:
    """Create a Kotlin project for testing nested structures."""
    project_path = temp_repo / "kotlin_nested_test"
    project_path.mkdir()

    (project_path / "src").mkdir()
    (project_path / "src" / "main").mkdir()
    (project_path / "src" / "main" / "kotlin").mkdir()
    (project_path / "src" / "main" / "kotlin" / "com").mkdir()
    (project_path / "src" / "main" / "kotlin" / "com" / "example").mkdir()

    return project_path


def test_nested_classes(
    kotlin_nested_project: Path,
    mock_ingestor: MagicMock,
) -> None:
    """Test nested classes."""
    test_file = (
        kotlin_nested_project
        / "src"
        / "main"
        / "kotlin"
        / "com"
        / "example"
        / "NestedClasses.kt"
    )
    test_file.write_text(
        """
package com.example

class OuterClass {
    private val outerField = "outer"

    // Inner class
    inner class InnerClass {
        fun accessOuter() {
            println(outerField)  // Can access outer class members
        }
    }

    // Nested class (static by default)
    class NestedClass {
        // Cannot access outerField here
        fun doSomething() {
            println("Nested class")
        }
    }

    // Nested interface
    interface NestedInterface {
        fun nestedMethod()
    }

    // Nested enum
    enum class NestedEnum {
        VALUE1, VALUE2
    }

    // Nested object
    object NestedObject {
        fun nestedFunction() {
            println("Nested object")
        }
    }
}
"""
    )

    run_updater(kotlin_nested_project, mock_ingestor, skip_if_missing="kotlin")

    project_name = kotlin_nested_project.name
    node_names = get_node_names(mock_ingestor, "Class")
    expected_classes = {
        f"{project_name}.src.main.kotlin.com.example.NestedClasses.OuterClass",
    }
    missing_classes = expected_classes - node_names
    assert not missing_classes, (
        f"Missing expected classes: {sorted(list(missing_classes))}"
    )


def test_deeply_nested_classes(
    kotlin_nested_project: Path,
    mock_ingestor: MagicMock,
) -> None:
    """Test deeply nested class structures."""
    test_file = (
        kotlin_nested_project
        / "src"
        / "main"
        / "kotlin"
        / "com"
        / "example"
        / "DeeplyNested.kt"
    )
    test_file.write_text(
        """
package com.example

class Level1 {
    private val level1Field = "level1"

    inner class Level2 {
        private val level2Field = "level2"

        inner class Level3 {
            private val level3Field = "level3"

            inner class Level4 {
                private val level4Field = "level4"

                fun accessAllLevels() {
                    println(level1Field)
                    println(level2Field)
                    println(level3Field)
                    println(level4Field)
                }

                inner class Level5 {
                    fun deepAccess() {
                        accessAllLevels()
                    }
                }
            }
        }
    }
}
"""
    )

    run_updater(kotlin_nested_project, mock_ingestor, skip_if_missing="kotlin")


def test_nested_data_classes(
    kotlin_nested_project: Path,
    mock_ingestor: MagicMock,
) -> None:
    """Test nested data classes."""
    test_file = (
        kotlin_nested_project
        / "src"
        / "main"
        / "kotlin"
        / "com"
        / "example"
        / "NestedDataClasses.kt"
    )
    test_file.write_text(
        """
package com.example

class Container {
    data class NestedData(val value: Int)

    data class AnotherNestedData(val name: String, val nested: NestedData)

    fun useNestedData() {
        val nested = NestedData(42)
        val another = AnotherNestedData("test", nested)
    }
}
"""
    )

    run_updater(kotlin_nested_project, mock_ingestor, skip_if_missing="kotlin")


def test_nested_sealed_classes(
    kotlin_nested_project: Path,
    mock_ingestor: MagicMock,
) -> None:
    """Test nested sealed classes."""
    test_file = (
        kotlin_nested_project
        / "src"
        / "main"
        / "kotlin"
        / "com"
        / "example"
        / "NestedSealed.kt"
    )
    test_file.write_text(
        """
package com.example

class ResultContainer {
    sealed class Result<out T> {
        data class Success<T>(val data: T) : Result<T>()
        data class Error(val message: String) : Result<Nothing>()
        object Loading : Result<Nothing>()
    }

    fun processResult(result: Result<String>) {
        when (result) {
            is Result.Success -> println(result.data)
            is Result.Error -> println(result.message)
            is Result.Loading -> println("Loading...")
        }
    }
}
"""
    )

    run_updater(kotlin_nested_project, mock_ingestor, skip_if_missing="kotlin")


def test_nested_functions(
    kotlin_nested_project: Path,
    mock_ingestor: MagicMock,
) -> None:
    """Test nested functions."""
    test_file = (
        kotlin_nested_project
        / "src"
        / "main"
        / "kotlin"
        / "com"
        / "example"
        / "NestedFunctions.kt"
    )
    test_file.write_text(
        """
package com.example

class FunctionContainer {
    fun outerFunction() {
        val outerVar = "outer"

        fun innerFunction() {
            println(outerVar)  // Can access outer scope
            val innerVar = "inner"

            fun deeplyNestedFunction() {
                println(outerVar)  // Can access outer scope
                println(innerVar)  // Can access inner scope
            }

            deeplyNestedFunction()
        }

        innerFunction()
    }

    fun functionWithLocalClass() {
        class LocalClass {
            fun localMethod() {
                println("Local class method")
            }
        }

        val local = LocalClass()
        local.localMethod()
    }
}
"""
    )

    run_updater(kotlin_nested_project, mock_ingestor, skip_if_missing="kotlin")
