"""Comprehensive tests for llm-tools-todo plugin."""

import pytest
import tempfile
import os
import json
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from llm_tools_todo import (
    Todo,
    TodoStore,
    TodoItem,
    todo_begin,
    todo_end,
    todo_list,
    todo_write,
    todo_add,
    todo_complete,
    _get_session_store,
    _session_stores,
)


class TestTodoItem:
    """Test TodoItem Pydantic model."""

    def test_todo_item_creation_minimal(self):
        """Test creating a TodoItem with minimal required fields."""
        item = TodoItem(id="test-id", content="Test task")
        assert item.id == "test-id"
        assert item.content == "Test task"
        assert item.status == "pending"
        assert item.priority == "medium"
        assert item.created_at == ""
        assert item.updated_at == ""

    def test_todo_item_creation_full(self):
        """Test creating a TodoItem with all fields."""
        now = datetime.now().isoformat()
        item = TodoItem(
            id="test-id",
            content="Complete the project",
            status="in_progress",
            priority="high",
            created_at=now,
            updated_at=now,
        )
        assert item.id == "test-id"
        assert item.content == "Complete the project"
        assert item.status == "in_progress"
        assert item.priority == "high"
        assert item.created_at == now
        assert item.updated_at == now

    def test_todo_item_defaults(self):
        """Test TodoItem default values."""
        item = TodoItem(id="1", content="Test")
        assert item.status == "pending"
        assert item.priority == "medium"
        assert item.created_at == ""
        assert item.updated_at == ""

    def test_todo_item_serialization(self):
        """Test TodoItem model_dump serialization."""
        item = TodoItem(id="1", content="Test task", status="completed", priority="low")
        data = item.model_dump()
        assert data["id"] == "1"
        assert data["content"] == "Test task"
        assert data["status"] == "completed"
        assert data["priority"] == "low"


class TestTodoStore:
    """Test TodoStore file operations."""

    def setup_method(self):
        """Set up test environment for each test."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_file = os.path.join(self.temp_dir, "test-todos.json")
        self.store = TodoStore(self.test_file)

    def teardown_method(self):
        """Clean up after each test."""
        if os.path.exists(self.test_file):
            os.unlink(self.test_file)
        os.rmdir(self.temp_dir)

    def test_read_todos_empty_file(self):
        """Test reading from non-existent file returns empty list."""
        todos = self.store.read_todos()
        assert todos == []

    def test_write_and_read_todos(self):
        """Test basic write and read operations."""
        test_todos = [
            {"id": "1", "content": "Task 1", "status": "pending", "priority": "high"},
            {"id": "2", "content": "Task 2", "status": "completed", "priority": "low"},
        ]

        # Write todos
        count = self.store.write_todos(test_todos)
        assert count == 2
        assert os.path.exists(self.test_file)

        # Read todos back
        loaded_todos = self.store.read_todos()
        assert len(loaded_todos) == 2
        assert loaded_todos[0]["id"] == "1"
        assert loaded_todos[0]["content"] == "Task 1"
        assert loaded_todos[1]["id"] == "2"
        assert loaded_todos[1]["content"] == "Task 2"

    def test_write_todos_adds_timestamps(self):
        """Test that write_todos adds created_at and updated_at timestamps."""
        test_todos = [
            {"id": "1", "content": "Task 1", "status": "pending", "priority": "medium"}
        ]

        self.store.write_todos(test_todos)
        loaded_todos = self.store.read_todos()

        assert loaded_todos[0]["created_at"] != ""
        assert loaded_todos[0]["updated_at"] != ""
        # Timestamps should be valid ISO format
        datetime.fromisoformat(loaded_todos[0]["created_at"])
        datetime.fromisoformat(loaded_todos[0]["updated_at"])

    def test_write_todos_preserves_created_at(self):
        """Test that write_todos preserves existing created_at timestamps."""
        original_time = "2024-01-01T12:00:00"
        test_todos = [
            {
                "id": "1",
                "content": "Task 1",
                "status": "pending",
                "priority": "medium",
                "created_at": original_time,
            }
        ]

        self.store.write_todos(test_todos)
        loaded_todos = self.store.read_todos()

        assert loaded_todos[0]["created_at"] == original_time
        assert loaded_todos[0]["updated_at"] != original_time  # Should be updated

    def test_write_todos_validation_error(self):
        """Test that invalid todo data raises ValidationError."""
        invalid_todos = [
            {"content": "Missing ID"}  # Missing required 'id' field
        ]

        with pytest.raises(Exception):  # Pydantic ValidationError
            self.store.write_todos(invalid_todos)

    def test_read_todos_corrupted_json(self):
        """Test reading from corrupted JSON file returns empty list."""
        # Write invalid JSON
        with open(self.test_file, "w") as f:
            f.write('{"invalid": json}')

        todos = self.store.read_todos()
        assert todos == []

    def test_file_structure(self):
        """Test the complete file structure with metadata."""
        test_todos = [
            {"id": "1", "content": "Test", "status": "pending", "priority": "medium"}
        ]

        self.store.write_todos(test_todos)

        # Check raw file contents
        with open(self.test_file, "r") as f:
            data = json.load(f)

        assert "todos" in data
        assert "updated_at" in data
        assert len(data["todos"]) == 1
        assert data["todos"][0]["id"] == "1"
        # Verify updated_at is valid timestamp
        datetime.fromisoformat(data["updated_at"])


class TestSessionManagement:
    """Test session management functions."""

    def setup_method(self):
        """Clear session cache before each test."""
        _session_stores.clear()

    def teardown_method(self):
        """Clean up session files after each test."""
        temp_dir = Path(tempfile.gettempdir())
        for file_path in temp_dir.glob("llm-todos-*.json"):
            try:
                file_path.unlink()
            except FileNotFoundError:
                pass
        _session_stores.clear()

    def test_get_session_store(self):
        """Test session store creation and caching."""
        session_id = "test123"

        # First call should create new store
        store1 = _get_session_store(session_id)
        assert isinstance(store1, TodoStore)
        assert session_id in _session_stores

        # Second call should return same store
        store2 = _get_session_store(session_id)
        assert store1 is store2

    def test_todo_begin(self):
        """Test starting a new todo session."""
        result = todo_begin()

        assert "Started new todo session:" in result
        session_id = result.split(": ")[1]
        assert len(session_id) == 8  # UUID truncated to 8 chars
        assert session_id in _session_stores

    def test_todo_end_existing_session(self):
        """Test ending an existing session."""
        # Start a session first
        begin_result = todo_begin()
        session_id = begin_result.split(": ")[1]

        # End the session
        result = todo_end(session_id)

        assert f"Ended todo session: {session_id}" == result
        assert session_id not in _session_stores

        # Check file was deleted
        session_file = Path(tempfile.gettempdir()) / f"llm-todos-{session_id}.json"
        assert not session_file.exists()

    def test_todo_end_nonexistent_session(self):
        """Test ending a non-existent session."""
        result = todo_end("nonexistent")
        assert "Ended todo session: nonexistent" == result


class TestTodoOperations:
    """Test individual todo operation functions."""

    def setup_method(self):
        """Set up test session for each test."""
        _session_stores.clear()
        self.session_id = "test123"
        # Pre-create session store
        _get_session_store(self.session_id)

    def teardown_method(self):
        """Clean up after each test."""
        temp_dir = Path(tempfile.gettempdir())
        for file_path in temp_dir.glob("llm-todos-*.json"):
            try:
                file_path.unlink()
            except FileNotFoundError:
                pass
        _session_stores.clear()

    def test_todo_list_empty_session(self):
        """Test listing todos from empty session."""
        result = todo_list(self.session_id)
        assert f"No todos found in session {self.session_id}" in result

    def test_todo_add(self):
        """Test adding a single todo item."""
        result = todo_add(self.session_id, "Test task", "high")

        assert "Added todo 'Test task'" in result
        assert f"to session {self.session_id}" in result
        assert "Total: 1 todos" in result

        # Verify it was added
        list_result = todo_list(self.session_id)
        assert "Test task" in list_result
        assert "High" in list_result  # Priority should be capitalized
        assert "Pending" in list_result  # Status should be capitalized

    def test_todo_add_invalid_priority(self):
        """Test adding todo with invalid priority."""
        result = todo_add(self.session_id, "Test task", "invalid")
        assert "Error: Priority must be 'high', 'medium', or 'low'" in result

    def test_todo_add_multiple(self):
        """Test adding multiple todo items."""
        # Add first todo
        result1 = todo_add(self.session_id, "Task 1", "high")
        assert "Total: 1 todos" in result1

        # Add second todo
        result2 = todo_add(self.session_id, "Task 2", "low")
        assert "Total: 2 todos" in result2

        # List should show both
        list_result = todo_list(self.session_id)
        assert "Task 1" in list_result
        assert "Task 2" in list_result

    def test_todo_complete(self):
        """Test completing a todo item."""
        # Add a todo first
        add_result = todo_add(self.session_id, "Complete me", "medium")

        # Extract the todo ID from the result
        # Format: "Added todo 'Complete me' with ID abc123def to session..."
        todo_id = add_result.split("with ID ")[1].split(" to session")[0]

        # Complete the todo
        result = todo_complete(self.session_id, todo_id)
        assert f"Marked todo '{todo_id}' as completed" in result

        # Verify it's marked as completed
        list_result = todo_list(self.session_id)
        assert "Completed" in list_result

    def test_todo_complete_nonexistent(self):
        """Test completing a non-existent todo."""
        result = todo_complete(self.session_id, "nonexistent")
        assert "Error: Todo with ID 'nonexistent' not found" in result

    def test_todo_write_valid_json(self):
        """Test replacing todos with valid JSON."""
        todos_json = """[
            {"id": "1", "content": "Task 1", "status": "pending", "priority": "high"},
            {"id": "2", "content": "Task 2", "status": "in_progress", "priority": "medium"}
        ]"""

        result = todo_write(self.session_id, todos_json)
        assert "Success! Updated todo list" in result
        assert "with 2 items" in result

        # Verify todos were written
        list_result = todo_list(self.session_id)
        assert "Task 1" in list_result
        assert "Task 2" in list_result
        assert "In Progress" in list_result

    def test_todo_write_invalid_json(self):
        """Test todo_write with invalid JSON."""
        result = todo_write(self.session_id, "invalid json")
        assert "Error: Invalid JSON format" in result

    def test_todo_write_not_array(self):
        """Test todo_write with JSON that's not an array."""
        result = todo_write(self.session_id, '{"not": "array"}')
        assert "Error: todos_json must be a JSON array" in result

    def test_todo_list_formatting(self):
        """Test todo_list output formatting."""
        # Add some todos with different statuses
        todos_json = """[
            {"id": "short", "content": "Short task", "status": "pending", "priority": "high"},
            {"id": "long", "content": "This is a very long task description that should be truncated", "status": "completed", "priority": "low"}
        ]"""

        todo_write(self.session_id, todos_json)
        result = todo_list(self.session_id)

        # Check table formatting
        assert "| ID | Status | Priority | Content | Created | Updated |" in result
        assert "|---|---|---|---|---|---|" in result
        assert "| short |" in result
        assert "| long |" in result
        assert "Short task" in result
        assert "..." in result  # Long content should be truncated
        assert "High" in result
        assert "Low" in result
        assert "Pending" in result
        assert "Completed" in result


class TestTodoToolbox:
    """Test the Todo toolbox class."""

    def setup_method(self):
        """Set up fresh toolbox for each test."""
        self.todo = Todo()
        _session_stores.clear()

    def teardown_method(self):
        """Clean up after each test."""
        temp_dir = Path(tempfile.gettempdir())
        for file_path in temp_dir.glob("llm-todos-*.json"):
            try:
                file_path.unlink()
            except FileNotFoundError:
                pass
        _session_stores.clear()

    def test_toolbox_todo_begin(self):
        """Test toolbox todo_begin method."""
        result = self.todo.todo_begin()
        assert "Started new todo session:" in result

    def test_toolbox_todo_end(self):
        """Test toolbox todo_end method."""
        # Start session first
        begin_result = self.todo.todo_begin()
        session_id = begin_result.split(": ")[1]

        # End session
        result = self.todo.todo_end(session_id)
        assert f"Ended todo session: {session_id}" == result

    def test_toolbox_todo_list(self):
        """Test toolbox todo_list method."""
        # Start session first
        begin_result = self.todo.todo_begin()
        session_id = begin_result.split(": ")[1]

        result = self.todo.todo_list(session_id)
        assert f"No todos found in session {session_id}" in result

    def test_toolbox_todo_add(self):
        """Test toolbox todo_add method."""
        begin_result = self.todo.todo_begin()
        session_id = begin_result.split(": ")[1]

        result = self.todo.todo_add(session_id, "Test task from toolbox")
        assert "Added todo 'Test task from toolbox'" in result

    def test_toolbox_todo_complete(self):
        """Test toolbox todo_complete method."""
        begin_result = self.todo.todo_begin()
        session_id = begin_result.split(": ")[1]

        # Add a todo first
        add_result = self.todo.todo_add(session_id, "Complete me")
        todo_id = add_result.split("with ID ")[1].split(" to session")[0]

        # Complete it
        result = self.todo.todo_complete(session_id, todo_id)
        assert f"Marked todo '{todo_id}' as completed" in result

    def test_toolbox_todo_write(self):
        """Test toolbox todo_write method."""
        begin_result = self.todo.todo_begin()
        session_id = begin_result.split(": ")[1]

        todos_json = '[{"id": "1", "content": "Toolbox test", "status": "pending", "priority": "medium"}]'
        result = self.todo.todo_write(session_id, todos_json)
        assert "Success! Updated todo list" in result

    def test_toolbox_inheritance(self):
        """Test that Todo inherits from llm.Toolbox."""
        assert hasattr(self.todo, "todo_begin")
        assert hasattr(self.todo, "todo_end")
        assert hasattr(self.todo, "todo_list")
        assert hasattr(self.todo, "todo_write")
        assert hasattr(self.todo, "todo_add")
        assert hasattr(self.todo, "todo_complete")


class TestErrorHandling:
    """Test error handling and edge cases."""

    def setup_method(self):
        _session_stores.clear()

    def teardown_method(self):
        temp_dir = Path(tempfile.gettempdir())
        for file_path in temp_dir.glob("llm-todos-*.json"):
            try:
                file_path.unlink()
            except FileNotFoundError:
                pass
        _session_stores.clear()

    @patch("llm_tools_todo.TodoStore.write_todos")
    def test_todo_begin_error(self, mock_run):
        """Test error handling in todo_begin."""
        mock_run.side_effect = Exception("Mock error")

        result = todo_begin()
        assert "Error starting session: Mock error" in result

    @patch("llm_tools_todo.TodoStore.write_todos")
    def test_todo_add_error(self, mock_run):
        """Test error handling in todo_add."""
        mock_run.side_effect = Exception("Mock error")

        result = todo_add("test", "content")
        assert "Error adding todo: Mock error" in result

    @patch("llm_tools_todo.TodoStore.read_todos")
    def test_todo_complete_error(self, mock_run):
        """Test error handling in todo_complete."""
        mock_run.side_effect = Exception("Mock error")

        result = todo_complete("test", "todo_id")
        assert "Error completing todo: Mock error" in result

    @patch("llm_tools_todo.TodoStore.read_todos")
    def test_todo_list_error(self, mock_run):
        """Test error handling in todo_list."""
        mock_run.side_effect = Exception("Mock error")

        result = todo_list("test")
        assert "Error reading todos: Mock error" in result
