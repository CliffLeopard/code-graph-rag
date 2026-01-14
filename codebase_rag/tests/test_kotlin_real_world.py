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
def kotlin_real_world_project(temp_repo: Path) -> Path:
    """Create a Kotlin project with real-world patterns."""
    project_path = temp_repo / "kotlin_real_world_test"
    project_path.mkdir()

    (project_path / "src").mkdir()
    (project_path / "src" / "main").mkdir()
    (project_path / "src" / "main" / "kotlin").mkdir()
    (project_path / "src" / "main" / "kotlin" / "com").mkdir()
    (project_path / "src" / "main" / "kotlin" / "com" / "example").mkdir()

    return project_path


def test_repository_pattern(
    kotlin_real_world_project: Path,
    mock_ingestor: MagicMock,
) -> None:
    """Test repository pattern implementation."""
    test_file = (
        kotlin_real_world_project
        / "src"
        / "main"
        / "kotlin"
        / "com"
        / "example"
        / "Repository.kt"
    )
    test_file.write_text(
        """
package com.example

interface Repository<T, ID> {
    fun findById(id: ID): T?
    fun findAll(): List<T>
    fun save(entity: T): T
    fun delete(id: ID)
}

data class User(val id: Int, val name: String, val email: String)

class UserRepository : Repository<User, Int> {
    private val users = mutableMapOf<Int, User>()

    override fun findById(id: Int): User? {
        return users[id]
    }

    override fun findAll(): List<User> {
        return users.values.toList()
    }

    override fun save(entity: User): User {
        users[entity.id] = entity
        return entity
    }

    override fun delete(id: Int) {
        users.remove(id)
    }
}
"""
    )

    run_updater(kotlin_real_world_project, mock_ingestor, skip_if_missing="kotlin")

    project_name = kotlin_real_world_project.name
    class_nodes = get_nodes(mock_ingestor, "Class")
    interface_nodes = get_nodes(mock_ingestor, "Interface")
    created_classes = get_qualified_names(class_nodes)
    created_interfaces = get_qualified_names(interface_nodes)

    expected_classes = {
        f"{project_name}.src.main.kotlin.com.example.Repository.User",
        f"{project_name}.src.main.kotlin.com.example.Repository.UserRepository",
    }
    expected_interfaces = {
        f"{project_name}.src.main.kotlin.com.example.Repository.Repository",
    }

    missing_classes = expected_classes - created_classes
    missing_interfaces = expected_interfaces - created_interfaces

    assert not missing_classes, (
        f"Missing expected classes: {sorted(list(missing_classes))}"
    )
    assert not missing_interfaces, (
        f"Missing expected interfaces: {sorted(list(missing_interfaces))}"
    )


def test_builder_pattern(
    kotlin_real_world_project: Path,
    mock_ingestor: MagicMock,
) -> None:
    """Test builder pattern."""
    test_file = (
        kotlin_real_world_project
        / "src"
        / "main"
        / "kotlin"
        / "com"
        / "example"
        / "Builder.kt"
    )
    test_file.write_text(
        """
package com.example

class HttpRequestBuilder {
    private var url: String = ""
    private var method: String = "GET"
    private var headers: Map<String, String> = emptyMap()
    private var body: String? = null

    fun url(url: String) = apply { this.url = url }
    fun method(method: String) = apply { this.method = method }
    fun header(key: String, value: String) = apply {
        this.headers = this.headers + (key to value)
    }
    fun body(body: String) = apply { this.body = body }

    fun build(): HttpRequest {
        return HttpRequest(url, method, headers, body)
    }
}

data class HttpRequest(
    val url: String,
    val method: String,
    val headers: Map<String, String>,
    val body: String?
)

// Usage
fun createRequest(): HttpRequest {
    return HttpRequestBuilder()
        .url("https://api.example.com")
        .method("POST")
        .header("Content-Type", "application/json")
        .body("{\"key\": \"value\"}")
        .build()
}
"""
    )

    run_updater(kotlin_real_world_project, mock_ingestor, skip_if_missing="kotlin")

    project_name = kotlin_real_world_project.name
    node_names = get_node_names(mock_ingestor, "Class")
    expected_classes = {
        f"{project_name}.src.main.kotlin.com.example.Builder.HttpRequestBuilder",
        f"{project_name}.src.main.kotlin.com.example.Builder.HttpRequest",
    }
    missing_classes = expected_classes - node_names
    assert not missing_classes, (
        f"Missing expected classes: {sorted(list(missing_classes))}"
    )


def test_observer_pattern(
    kotlin_real_world_project: Path,
    mock_ingestor: MagicMock,
) -> None:
    """Test observer pattern."""
    test_file = (
        kotlin_real_world_project
        / "src"
        / "main"
        / "kotlin"
        / "com"
        / "example"
        / "Observer.kt"
    )
    test_file.write_text(
        """
package com.example

interface Observer<T> {
    fun update(data: T)
}

class Observable<T> {
    private val observers = mutableListOf<Observer<T>>()

    fun addObserver(observer: Observer<T>) {
        observers.add(observer)
    }

    fun removeObserver(observer: Observer<T>) {
        observers.remove(observer)
    }

    fun notifyObservers(data: T) {
        observers.forEach { it.update(data) }
    }
}

class NewsPublisher : Observable<String>() {
    fun publishNews(news: String) {
        notifyObservers(news)
    }
}

class NewsSubscriber(private val name: String) : Observer<String> {
    override fun update(data: String) {
        println("$name received: $data")
    }
}
"""
    )

    run_updater(kotlin_real_world_project, mock_ingestor, skip_if_missing="kotlin")

    project_name = kotlin_real_world_project.name
    class_nodes = get_nodes(mock_ingestor, "Class")
    interface_nodes = get_nodes(mock_ingestor, "Interface")
    created_classes = get_qualified_names(class_nodes)
    created_interfaces = get_qualified_names(interface_nodes)

    expected_classes = {
        f"{project_name}.src.main.kotlin.com.example.Observer.Observable",
        f"{project_name}.src.main.kotlin.com.example.Observer.NewsPublisher",
        f"{project_name}.src.main.kotlin.com.example.Observer.NewsSubscriber",
    }
    expected_interfaces = {
        f"{project_name}.src.main.kotlin.com.example.Observer.Observer",
    }

    missing_classes = expected_classes - created_classes
    missing_interfaces = expected_interfaces - created_interfaces

    assert not missing_classes, (
        f"Missing expected classes: {sorted(list(missing_classes))}"
    )
    assert not missing_interfaces, (
        f"Missing expected interfaces: {sorted(list(missing_interfaces))}"
    )


def test_factory_pattern(
    kotlin_real_world_project: Path,
    mock_ingestor: MagicMock,
) -> None:
    """Test factory pattern."""
    test_file = (
        kotlin_real_world_project
        / "src"
        / "main"
        / "kotlin"
        / "com"
        / "example"
        / "Factory.kt"
    )
    test_file.write_text(
        """
package com.example

interface Shape {
    fun draw()
}

class Circle : Shape {
    override fun draw() {
        println("Drawing circle")
    }
}

class Rectangle : Shape {
    override fun draw() {
        println("Drawing rectangle")
    }
}

class ShapeFactory {
    fun createShape(type: String): Shape {
        return when (type.lowercase()) {
            "circle" -> Circle()
            "rectangle" -> Rectangle()
            else -> throw IllegalArgumentException("Unknown shape type: $type")
        }
    }
}

// Companion object factory
class Product private constructor(val name: String) {
    companion object {
        fun create(name: String): Product {
            return Product(name)
        }
    }
}
"""
    )

    run_updater(kotlin_real_world_project, mock_ingestor, skip_if_missing="kotlin")

    project_name = kotlin_real_world_project.name
    class_nodes = get_nodes(mock_ingestor, "Class")
    interface_nodes = get_nodes(mock_ingestor, "Interface")
    created_classes = get_qualified_names(class_nodes)
    created_interfaces = get_qualified_names(interface_nodes)

    expected_classes = {
        f"{project_name}.src.main.kotlin.com.example.Factory.Circle",
        f"{project_name}.src.main.kotlin.com.example.Factory.Rectangle",
        f"{project_name}.src.main.kotlin.com.example.Factory.ShapeFactory",
        f"{project_name}.src.main.kotlin.com.example.Factory.Product",
    }
    expected_interfaces = {
        f"{project_name}.src.main.kotlin.com.example.Factory.Shape",
    }

    missing_classes = expected_classes - created_classes
    missing_interfaces = expected_interfaces - created_interfaces

    assert not missing_classes, (
        f"Missing expected classes: {sorted(list(missing_classes))}"
    )
    assert not missing_interfaces, (
        f"Missing expected interfaces: {sorted(list(missing_interfaces))}"
    )


def test_dependency_injection_pattern(
    kotlin_real_world_project: Path,
    mock_ingestor: MagicMock,
) -> None:
    """Test dependency injection pattern."""
    test_file = (
        kotlin_real_world_project
        / "src"
        / "main"
        / "kotlin"
        / "com"
        / "example"
        / "DependencyInjection.kt"
    )
    test_file.write_text(
        """
package com.example

interface Database {
    fun save(data: String)
    fun load(id: String): String?
}

class MySQLDatabase : Database {
    override fun save(data: String) {
        println("Saving to MySQL: $data")
    }

    override fun load(id: String): String? {
        return "Data from MySQL"
    }
}

class PostgreSQLDatabase : Database {
    override fun save(data: String) {
        println("Saving to PostgreSQL: $data")
    }

    override fun load(id: String): String? {
        return "Data from PostgreSQL"
    }
}

class UserService(private val database: Database) {
    fun saveUser(user: String) {
        database.save(user)
    }

    fun getUser(id: String): String? {
        return database.load(id)
    }
}

// Usage with dependency injection
fun createUserService(): UserService {
    val database: Database = MySQLDatabase()
    return UserService(database)
}
"""
    )

    run_updater(kotlin_real_world_project, mock_ingestor, skip_if_missing="kotlin")

    project_name = kotlin_real_world_project.name
    class_nodes = get_nodes(mock_ingestor, "Class")
    interface_nodes = get_nodes(mock_ingestor, "Interface")
    created_classes = get_qualified_names(class_nodes)
    created_interfaces = get_qualified_names(interface_nodes)

    expected_classes = {
        f"{project_name}.src.main.kotlin.com.example.DependencyInjection.MySQLDatabase",
        f"{project_name}.src.main.kotlin.com.example.DependencyInjection.PostgreSQLDatabase",
        f"{project_name}.src.main.kotlin.com.example.DependencyInjection.UserService",
    }
    expected_interfaces = {
        f"{project_name}.src.main.kotlin.com.example.DependencyInjection.Database",
    }

    missing_classes = expected_classes - created_classes
    missing_interfaces = expected_interfaces - created_interfaces

    assert not missing_classes, (
        f"Missing expected classes: {sorted(list(missing_classes))}"
    )
    assert not missing_interfaces, (
        f"Missing expected interfaces: {sorted(list(missing_interfaces))}"
    )
