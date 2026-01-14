from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from codebase_rag.tests.conftest import run_updater


@pytest.fixture
def kotlin_imports_project(temp_repo: Path) -> Path:
    """Create a Kotlin project for testing imports."""
    project_path = temp_repo / "kotlin_imports_test"
    project_path.mkdir()

    (project_path / "src").mkdir()
    (project_path / "src" / "main").mkdir()
    (project_path / "src" / "main" / "kotlin").mkdir()
    (project_path / "src" / "main" / "kotlin" / "com").mkdir()
    (project_path / "src" / "main" / "kotlin" / "com" / "example").mkdir()

    return project_path


def test_basic_imports(
    kotlin_imports_project: Path,
    mock_ingestor: MagicMock,
) -> None:
    """Test basic Kotlin imports."""
    test_file = (
        kotlin_imports_project
        / "src"
        / "main"
        / "kotlin"
        / "com"
        / "example"
        / "BasicImports.kt"
    )
    test_file.write_text(
        """
package com.example

import java.util.List
import java.util.ArrayList
import java.util.Map
import java.util.HashMap

class BasicImports {
    fun useImports() {
        val list: List<String> = ArrayList()
        val map: Map<String, Int> = HashMap()
    }
}
"""
    )

    run_updater(kotlin_imports_project, mock_ingestor, skip_if_missing="kotlin")


def test_wildcard_imports(
    kotlin_imports_project: Path,
    mock_ingestor: MagicMock,
) -> None:
    """Test wildcard imports."""
    test_file = (
        kotlin_imports_project
        / "src"
        / "main"
        / "kotlin"
        / "com"
        / "example"
        / "WildcardImports.kt"
    )
    test_file.write_text(
        """
package com.example

import java.util.*
import kotlin.collections.*

class WildcardImports {
    fun useWildcardImports() {
        val list = ArrayList<String>()
        val map = HashMap<String, Int>()
    }
}
"""
    )

    run_updater(kotlin_imports_project, mock_ingestor, skip_if_missing="kotlin")


def test_import_aliases(
    kotlin_imports_project: Path,
    mock_ingestor: MagicMock,
) -> None:
    """Test import aliases."""
    test_file = (
        kotlin_imports_project
        / "src"
        / "main"
        / "kotlin"
        / "com"
        / "example"
        / "ImportAliases.kt"
    )
    test_file.write_text(
        """
package com.example

import java.util.ArrayList as AL
import java.util.HashMap as HM
import java.util.List as L

class ImportAliases {
    fun useAliases() {
        val list: L<String> = AL()
        val map = HM<String, Int>()
    }
}
"""
    )

    run_updater(kotlin_imports_project, mock_ingestor, skip_if_missing="kotlin")


def test_cross_package_imports(
    kotlin_imports_project: Path,
    mock_ingestor: MagicMock,
) -> None:
    """Test cross-package imports."""
    # (H) Create multiple packages
    (
        kotlin_imports_project / "src" / "main" / "kotlin" / "com" / "example" / "utils"
    ).mkdir()
    (
        kotlin_imports_project
        / "src"
        / "main"
        / "kotlin"
        / "com"
        / "example"
        / "models"
    ).mkdir()

    # (H) Create utility class
    utils_file = (
        kotlin_imports_project
        / "src"
        / "main"
        / "kotlin"
        / "com"
        / "example"
        / "utils"
        / "StringUtils.kt"
    )
    utils_file.write_text(
        """
package com.example.utils

object StringUtils {
    fun capitalize(str: String): String {
        return str.capitalize()
    }
}
"""
    )

    # (H) Create model class
    model_file = (
        kotlin_imports_project
        / "src"
        / "main"
        / "kotlin"
        / "com"
        / "example"
        / "models"
        / "User.kt"
    )
    model_file.write_text(
        """
package com.example.models

data class User(val name: String, val age: Int)
"""
    )

    # (H) Create main file that imports from other packages
    main_file = (
        kotlin_imports_project
        / "src"
        / "main"
        / "kotlin"
        / "com"
        / "example"
        / "Main.kt"
    )
    main_file.write_text(
        """
package com.example

import com.example.utils.StringUtils
import com.example.models.User

class Main {
    fun useCrossPackage() {
        val user = User("Alice", 30)
        val capitalized = StringUtils.capitalize(user.name)
    }
}
"""
    )

    run_updater(kotlin_imports_project, mock_ingestor, skip_if_missing="kotlin")


def test_static_imports(
    kotlin_imports_project: Path,
    mock_ingestor: MagicMock,
) -> None:
    """Test static imports (companion object members)."""
    test_file = (
        kotlin_imports_project
        / "src"
        / "main"
        / "kotlin"
        / "com"
        / "example"
        / "StaticImports.kt"
    )
    test_file.write_text(
        """
package com.example

class Constants {
    companion object {
        const val PI = 3.14159
        const val E = 2.71828
    }
}

// Import companion object members
import com.example.Constants.Companion.PI
import com.example.Constants.Companion.E

class StaticImports {
    fun useConstants() {
        val area = PI * 2 * 2
        val value = E
    }
}
"""
    )

    run_updater(kotlin_imports_project, mock_ingestor, skip_if_missing="kotlin")
