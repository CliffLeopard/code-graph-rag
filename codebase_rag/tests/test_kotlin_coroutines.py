from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from codebase_rag.tests.conftest import (
    get_nodes,
    get_qualified_names,
    run_updater,
)


@pytest.fixture
def kotlin_coroutines_project(temp_repo: Path) -> Path:
    """Create a Kotlin project for testing coroutines."""
    project_path = temp_repo / "kotlin_coroutines_test"
    project_path.mkdir()

    (project_path / "src").mkdir()
    (project_path / "src" / "main").mkdir()
    (project_path / "src" / "main" / "kotlin").mkdir()
    (project_path / "src" / "main" / "kotlin" / "com").mkdir()
    (project_path / "src" / "main" / "kotlin" / "com" / "example").mkdir()

    return project_path


def test_suspend_functions(
    kotlin_coroutines_project: Path,
    mock_ingestor: MagicMock,
) -> None:
    """Test suspend functions."""
    test_file = (
        kotlin_coroutines_project
        / "src"
        / "main"
        / "kotlin"
        / "com"
        / "example"
        / "SuspendFunctions.kt"
    )
    test_file.write_text(
        """
package com.example

class CoroutineExamples {
    // Basic suspend function
    suspend fun fetchData(): String {
        return "Data"
    }

    // Suspend function with parameters
    suspend fun processData(data: String): String {
        return data.uppercase()
    }

    // Suspend function returning nullable
    suspend fun fetchOptionalData(): String? {
        return null
    }

    // Suspend extension function
    suspend fun String.processAsync(): String {
        return this.reversed()
    }

    // Suspend function with generic type
    suspend fun <T> fetchGeneric(): T? {
        return null
    }
}
"""
    )

    run_updater(kotlin_coroutines_project, mock_ingestor, skip_if_missing="kotlin")

    function_nodes = get_nodes(mock_ingestor, "Method")
    qualified_names = get_qualified_names(function_nodes)
    # (H) Suspend functions inside classes should be methods
    assert any("fetchData" in qn for qn in qualified_names)
    assert any("processData" in qn for qn in qualified_names)


def test_coroutine_builders(
    kotlin_coroutines_project: Path,
    mock_ingestor: MagicMock,
) -> None:
    """Test coroutine builders."""
    test_file = (
        kotlin_coroutines_project
        / "src"
        / "main"
        / "kotlin"
        / "com"
        / "example"
        / "CoroutineBuilders.kt"
    )
    test_file.write_text(
        """
package com.example

class CoroutineBuilderExamples {
    suspend fun demonstrateLaunch() {
        // launch would be called from coroutine scope
        // launch {
        //     println("Running in coroutine")
        // }
    }

    suspend fun demonstrateAsync() {
        // async {
        //     fetchData()
        // }
    }

    suspend fun demonstrateRunBlocking() {
        // runBlocking {
        //     fetchData()
        // }
    }

    suspend fun demonstrateWithContext() {
        // withContext(Dispatchers.IO) {
        //     fetchData()
        // }
    }

    suspend fun fetchData(): String = "Data"
}
"""
    )

    run_updater(kotlin_coroutines_project, mock_ingestor, skip_if_missing="kotlin")


def test_flow_api(
    kotlin_coroutines_project: Path,
    mock_ingestor: MagicMock,
) -> None:
    """Test Flow API."""
    test_file = (
        kotlin_coroutines_project
        / "src"
        / "main"
        / "kotlin"
        / "com"
        / "example"
        / "Flow.kt"
    )
    test_file.write_text(
        """
package com.example

class FlowExamples {
    // Flow builder
    fun createFlow(): kotlinx.coroutines.flow.Flow<Int> {
        return kotlinx.coroutines.flow.flow {
            for (i in 1..5) {
                emit(i)
            }
        }
    }

    // Flow operators
    suspend fun processFlow() {
        // createFlow()
        //     .map { it * 2 }
        //     .filter { it > 5 }
        //     .collect { value ->
        //         println(value)
        //     }
    }

    // StateFlow
    // private val _state = MutableStateFlow(0)
    // val state: StateFlow<Int> = _state.asStateFlow()

    // SharedFlow
    // private val _events = MutableSharedFlow<String>()
    // val events: SharedFlow<String> = _events.asSharedFlow()
}
"""
    )

    run_updater(kotlin_coroutines_project, mock_ingestor, skip_if_missing="kotlin")


def test_coroutine_scopes(
    kotlin_coroutines_project: Path,
    mock_ingestor: MagicMock,
) -> None:
    """Test coroutine scopes."""
    test_file = (
        kotlin_coroutines_project
        / "src"
        / "main"
        / "kotlin"
        / "com"
        / "example"
        / "Scopes.kt"
    )
    test_file.write_text(
        """
package com.example

class ScopeExamples {
    // CoroutineScope interface
    // class MyScope : CoroutineScope {
    //     override val coroutineContext: CoroutineContext
    //         get() = Dispatchers.Default
    // }

    suspend fun demonstrateScope() {
        // coroutineScope {
        //     launch {
        //         fetchData()
        //     }
        // }
    }

    suspend fun demonstrateSupervisorScope() {
        // supervisorScope {
        //     launch {
        //         fetchData()
        //     }
        // }
    }

    suspend fun fetchData(): String = "Data"
}
"""
    )

    run_updater(kotlin_coroutines_project, mock_ingestor, skip_if_missing="kotlin")
