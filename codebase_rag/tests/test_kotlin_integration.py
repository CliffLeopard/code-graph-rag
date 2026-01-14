from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from codebase_rag import constants as cs
from codebase_rag.tests.conftest import run_updater as conftest_run_updater


def run_updater(
    repo_path: Path, mock_ingestor: MagicMock, expected_calls: int | None = None
) -> None:
    """Helper to run GraphUpdater and verify results"""
    conftest_run_updater(repo_path, mock_ingestor, skip_if_missing="kotlin")

    if expected_calls is not None:
        assert mock_ingestor.ensure_node_batch.call_count >= expected_calls


@pytest.mark.skipif(
    cs.SupportedLanguage.KOTLIN not in cs.LANGUAGE_METADATA,
    reason="Kotlin not configured",
)
class TestKotlinBasicSyntax:
    def test_simple_class(self, temp_repo: Path, mock_ingestor: MagicMock) -> None:
        """Test parsing a simple Kotlin class"""
        kotlin_dir = temp_repo / "src" / "main" / "kotlin" / "com" / "example"
        kotlin_dir.mkdir(parents=True, exist_ok=True)
        test_file = kotlin_dir / "SimpleClass.kt"
        test_file.write_text(
            """
package com.example

class SimpleClass {
    fun greet(): String {
        return "Hello"
    }
}
"""
        )

        run_updater(temp_repo, mock_ingestor, expected_calls=1)

        # (H) Verify class was created
        calls = [str(call) for call in mock_ingestor.ensure_node_batch.call_args_list]
        assert any("SimpleClass" in str(call) for call in calls)

    def test_data_class(self, temp_repo: Path, mock_ingestor: MagicMock) -> None:
        """Test parsing a Kotlin data class"""
        kotlin_dir = temp_repo / "src" / "main" / "kotlin" / "com" / "example"
        kotlin_dir.mkdir(parents=True, exist_ok=True)
        test_file = kotlin_dir / "Person.kt"
        test_file.write_text(
            """
package com.example

data class Person(val name: String, val age: Int)
"""
        )

        run_updater(temp_repo, mock_ingestor, expected_calls=1)

    def test_interface(self, temp_repo: Path, mock_ingestor: MagicMock) -> None:
        """Test parsing a Kotlin interface"""
        kotlin_dir = temp_repo / "src" / "main" / "kotlin" / "com" / "example"
        kotlin_dir.mkdir(parents=True, exist_ok=True)
        test_file = kotlin_dir / "Repository.kt"
        test_file.write_text(
            """
package com.example

interface Repository {
    fun save(data: String)
    fun load(id: String): String?
}
"""
        )

        run_updater(temp_repo, mock_ingestor, expected_calls=1)

    def test_enum_class(self, temp_repo: Path, mock_ingestor: MagicMock) -> None:
        """Test parsing a Kotlin enum class"""
        kotlin_dir = temp_repo / "src" / "main" / "kotlin" / "com" / "example"
        kotlin_dir.mkdir(parents=True, exist_ok=True)
        test_file = kotlin_dir / "Status.kt"
        test_file.write_text(
            """
package com.example

enum class Status {
    PENDING,
    ACTIVE,
    COMPLETED
}
"""
        )

        run_updater(temp_repo, mock_ingestor, expected_calls=1)

    def test_object_declaration(
        self, temp_repo: Path, mock_ingestor: MagicMock
    ) -> None:
        """Test parsing a Kotlin object declaration"""
        kotlin_dir = temp_repo / "src" / "main" / "kotlin" / "com" / "example"
        kotlin_dir.mkdir(parents=True, exist_ok=True)
        test_file = kotlin_dir / "Singleton.kt"
        test_file.write_text(
            """
package com.example

object Singleton {
    fun doSomething() {
        println("Singleton")
    }
}
"""
        )

        run_updater(temp_repo, mock_ingestor, expected_calls=1)

    def test_companion_object(self, temp_repo: Path, mock_ingestor: MagicMock) -> None:
        """Test parsing a Kotlin companion object"""
        kotlin_dir = temp_repo / "src" / "main" / "kotlin" / "com" / "example"
        kotlin_dir.mkdir(parents=True, exist_ok=True)
        test_file = kotlin_dir / "MyClass.kt"
        test_file.write_text(
            """
package com.example

class MyClass {
    companion object {
        const val CONSTANT = 42
        fun create(): MyClass = MyClass()
    }
}
"""
        )

        run_updater(temp_repo, mock_ingestor, expected_calls=1)

    def test_extension_function(
        self, temp_repo: Path, mock_ingestor: MagicMock
    ) -> None:
        """Test parsing a Kotlin extension function"""
        kotlin_dir = temp_repo / "src" / "main" / "kotlin" / "com" / "example"
        kotlin_dir.mkdir(parents=True, exist_ok=True)
        test_file = kotlin_dir / "Extensions.kt"
        test_file.write_text(
            """
package com.example

fun String.reverse(): String {
    return this.reversed()
}
"""
        )

        run_updater(temp_repo, mock_ingestor, expected_calls=1)

    def test_suspend_function(self, temp_repo: Path, mock_ingestor: MagicMock) -> None:
        """Test parsing a Kotlin suspend function"""
        kotlin_dir = temp_repo / "src" / "main" / "kotlin" / "com" / "example"
        kotlin_dir.mkdir(parents=True, exist_ok=True)
        test_file = kotlin_dir / "Coroutines.kt"
        test_file.write_text(
            """
package com.example

suspend fun fetchData(): String {
    return "data"
}
"""
        )

        run_updater(temp_repo, mock_ingestor, expected_calls=1)

    def test_sealed_class(self, temp_repo: Path, mock_ingestor: MagicMock) -> None:
        """Test parsing a Kotlin sealed class"""
        kotlin_dir = temp_repo / "src" / "main" / "kotlin" / "com" / "example"
        kotlin_dir.mkdir(parents=True, exist_ok=True)
        test_file = kotlin_dir / "Result.kt"
        test_file.write_text(
            """
package com.example

sealed class Result {
    class Success(val data: String) : Result()
    class Error(val message: String) : Result()
}
"""
        )

        run_updater(temp_repo, mock_ingestor, expected_calls=1)

    def test_generics(self, temp_repo: Path, mock_ingestor: MagicMock) -> None:
        """Test parsing Kotlin generics"""
        kotlin_dir = temp_repo / "src" / "main" / "kotlin" / "com" / "example"
        kotlin_dir.mkdir(parents=True, exist_ok=True)
        test_file = kotlin_dir / "Box.kt"
        test_file.write_text(
            """
package com.example

class Box<T>(val value: T) {
    fun getValue(): T = value
}
"""
        )

        run_updater(temp_repo, mock_ingestor, expected_calls=1)

    def test_nullable_types(self, temp_repo: Path, mock_ingestor: MagicMock) -> None:
        """Test parsing Kotlin nullable types"""
        kotlin_dir = temp_repo / "src" / "main" / "kotlin" / "com" / "example"
        kotlin_dir.mkdir(parents=True, exist_ok=True)
        test_file = kotlin_dir / "Nullable.kt"
        test_file.write_text(
            """
package com.example

fun process(value: String?): String {
    return value ?: "default"
}
"""
        )

        run_updater(temp_repo, mock_ingestor, expected_calls=1)

    def test_type_inference(self, temp_repo: Path, mock_ingestor: MagicMock) -> None:
        """Test Kotlin type inference"""
        kotlin_dir = temp_repo / "src" / "main" / "kotlin" / "com" / "example"
        kotlin_dir.mkdir(parents=True, exist_ok=True)
        test_file = kotlin_dir / "Inference.kt"
        test_file.write_text(
            """
package com.example

fun add(a: Int, b: Int) = a + b

val name = "Kotlin"
val count = 42
"""
        )

        run_updater(temp_repo, mock_ingestor, expected_calls=1)

    def test_lambda(self, temp_repo: Path, mock_ingestor: MagicMock) -> None:
        """Test parsing Kotlin lambdas"""
        kotlin_dir = temp_repo / "src" / "main" / "kotlin" / "com" / "example"
        kotlin_dir.mkdir(parents=True, exist_ok=True)
        test_file = kotlin_dir / "Lambdas.kt"
        test_file.write_text(
            """
package com.example

fun useLambda() {
    val lambda = { x: Int, y: Int -> x + y }
    val result = lambda(1, 2)
}
"""
        )

        run_updater(temp_repo, mock_ingestor, expected_calls=1)

    def test_when_expression(self, temp_repo: Path, mock_ingestor: MagicMock) -> None:
        """Test parsing Kotlin when expression"""
        kotlin_dir = temp_repo / "src" / "main" / "kotlin" / "com" / "example"
        kotlin_dir.mkdir(parents=True, exist_ok=True)
        test_file = kotlin_dir / "When.kt"
        test_file.write_text(
            """
package com.example

fun getStatus(code: Int): String {
    return when (code) {
        200 -> "OK"
        404 -> "Not Found"
        else -> "Unknown"
    }
}
"""
        )

        run_updater(temp_repo, mock_ingestor, expected_calls=1)

    def test_class_with_inheritance(
        self, temp_repo: Path, mock_ingestor: MagicMock
    ) -> None:
        """Test parsing Kotlin class with inheritance"""
        kotlin_dir = temp_repo / "src" / "main" / "kotlin" / "com" / "example"
        kotlin_dir.mkdir(parents=True, exist_ok=True)
        test_file = kotlin_dir / "Inheritance.kt"
        test_file.write_text(
            """
package com.example

open class Base {
    open fun method() {}
}

class Derived : Base() {
    override fun method() {
        super.method()
    }
}
"""
        )

        run_updater(temp_repo, mock_ingestor, expected_calls=2)

    def test_class_implementing_interface(
        self, temp_repo: Path, mock_ingestor: MagicMock
    ) -> None:
        """Test parsing Kotlin class implementing interface"""
        kotlin_dir = temp_repo / "src" / "main" / "kotlin" / "com" / "example"
        kotlin_dir.mkdir(parents=True, exist_ok=True)
        test_file = kotlin_dir / "Implementation.kt"
        test_file.write_text(
            """
package com.example

interface Drawable {
    fun draw()
}

class Circle : Drawable {
    override fun draw() {
        println("Drawing circle")
    }
}
"""
        )

        run_updater(temp_repo, mock_ingestor, expected_calls=2)

    def test_imports(self, temp_repo: Path, mock_ingestor: MagicMock) -> None:
        """Test parsing Kotlin imports"""
        kotlin_dir = temp_repo / "src" / "main" / "kotlin" / "com" / "example"
        kotlin_dir.mkdir(parents=True, exist_ok=True)
        test_file = kotlin_dir / "Imports.kt"
        test_file.write_text(
            """
package com.example

import java.util.List
import java.util.Map as HashMap
import java.util.*

fun useImports() {
    val list: List<String> = emptyList()
}
"""
        )

        run_updater(temp_repo, mock_ingestor, expected_calls=1)

    def test_method_calls(self, temp_repo: Path, mock_ingestor: MagicMock) -> None:
        """Test parsing Kotlin method calls"""
        kotlin_dir = temp_repo / "src" / "main" / "kotlin" / "com" / "example"
        kotlin_dir.mkdir(parents=True, exist_ok=True)
        test_file = kotlin_dir / "Calls.kt"
        test_file.write_text(
            """
package com.example

class Calculator {
    fun add(a: Int, b: Int): Int {
        return a + b
    }

    fun use() {
        val result = this.add(1, 2)
        val sum = add(3, 4)
    }
}
"""
        )

        run_updater(temp_repo, mock_ingestor, expected_calls=1)
