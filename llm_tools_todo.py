"""LLM plugin for todo management."""

import json
import uuid
import tempfile
from pathlib import Path
from typing import Any, List, Dict

import llm
from datetime import datetime
from pydantic import BaseModel, ValidationError


class TodoItem(BaseModel):
    """Represents a single todo item."""

    id: str
    content: str
    status: str = "pending"  # pending, in_progress, completed
    priority: str = "medium"  # high, medium, low
    created_at: str = ""
    updated_at: str = ""


class TodoStore:
    """Handles storage and retrieval of todo items."""

    def __init__(self, file_path: str):
        """Initialize the store with a file path."""
        self.file_path = Path(file_path)
        self.file_path.parent.mkdir(parents=True, exist_ok=True)

    def read_todos(self) -> List[Dict[str, Any]]:
        """Read todos from the storage file."""
        if not self.file_path.exists():
            return []

        try:
            with open(self.file_path, "r") as f:
                data = json.load(f)
                return data.get("todos", [])
        except (json.JSONDecodeError, FileNotFoundError):
            return []

    def write_todos(self, todos_data: List[Dict[str, Any]]) -> int:
        """Write todos to the storage file with validation."""
        current_time = datetime.now().isoformat()

        # Validate and normalize todos
        validated_todos = []
        for todo_data in todos_data:
            # Set timestamps if not provided
            if "created_at" not in todo_data or not todo_data["created_at"]:
                todo_data["created_at"] = current_time
            todo_data["updated_at"] = current_time

            # Validate with pydantic model
            todo_item = TodoItem(**todo_data)
            validated_todos.append(todo_item.model_dump())

        # Write to file
        data = {"todos": validated_todos, "updated_at": current_time}

        with open(self.file_path, "w") as f:
            json.dump(data, f, indent=2)

        return len(validated_todos)


# Global session store cache
_session_stores = {}  # Cache of TodoStore instances by session_id


def _get_session_store(session_id: str) -> TodoStore:
    """Get or create a TodoStore for the given session."""
    if session_id not in _session_stores:
        # Create session-specific file in temp directory
        session_file = Path(tempfile.gettempdir()) / f"llm-todos-{session_id}.json"
        _session_stores[session_id] = TodoStore(str(session_file))
    return _session_stores[session_id]


def todo_begin() -> str:
    """Start a new todo session and return the session ID."""
    session_id = str(uuid.uuid4())[:8]
    # Initialize empty session
    store = _get_session_store(session_id)
    try:
        store.write_todos([])
        return f"Started new todo session: {session_id}"
    except Exception as e:
        return f"Error starting session: {str(e)}"


def todo_end(session_id: str) -> str:
    """End a todo session and clean up its data."""
    try:
        session_file = Path(tempfile.gettempdir()) / f"llm-todos-{session_id}.json"
        if session_file.exists():
            session_file.unlink()

        # Remove from cache
        if session_id in _session_stores:
            del _session_stores[session_id]

        return f"Ended todo session: {session_id}"
    except Exception as e:
        return f"Error ending session: {str(e)}"


def todo_list(session_id: str) -> str:
    """List all current todos for a session with their status and details."""
    try:
        store = _get_session_store(session_id)
        todos = store.read_todos()

        if not todos:
            return f"No todos found in session {session_id}."

        # Format as a nice table
        result = f"# Current Todos (Session: {session_id})\n\n"
        result += "| ID | Status | Priority | Content | Created | Updated |\n"
        result += "|---|---|---|---|---|---|\n"

        for todo in todos:
            status = todo["status"].replace("_", " ").title()
            priority = todo["priority"].title()
            content = todo["content"][:50] + (
                "..." if len(todo["content"]) > 50 else ""
            )
            created = todo["created_at"][:10]  # Just date
            updated = todo["updated_at"][:10]  # Just date

            result += f"| {todo['id']} | {status} | {priority} | {content} | {created} | {updated} |\n"

        return result

    except Exception as e:
        return f"Error reading todos: {str(e)}"


def todo_write(session_id: str, todos_json: str) -> str:
    """Replace the entire todo list with new todos (JSON format).

    Args:
        session_id: The session ID
        todos_json: JSON string containing array of todo objects

    Example:
        [{"id": "1", "content": "Fix bug", "status": "pending", "priority": "high"}]
    """
    try:
        store = _get_session_store(session_id)

        # Parse the JSON
        todos_data = json.loads(todos_json)

        if not isinstance(todos_data, list):
            return "Error: todos_json must be a JSON array of todo objects"

        # Run the async function
        count = store.write_todos(todos_data)

        return (
            f"Success! Updated todo list for session {session_id} with {count} items."
        )

    except json.JSONDecodeError as e:
        return f"Error: Invalid JSON format - {str(e)}"
    except ValidationError as e:
        return f"Validation error: {str(e)}"
    except Exception as e:
        return f"Error writing todos: {str(e)}"


def todo_add(session_id: str, content: str, priority: str = "medium") -> str:
    """Add a single new todo item to a session.

    Args:
        session_id: The session ID
        content: The todo item description
        priority: Priority level (high, medium, low)
    """
    try:
        store = _get_session_store(session_id)

        # Read existing todos
        todos = store.read_todos()

        # Validate priority
        if priority.lower() not in ["high", "medium", "low"]:
            return "Error: Priority must be 'high', 'medium', or 'low'"

        # Create new todo
        new_todo = {
            "id": str(uuid.uuid4())[:8],  # Short UUID
            "content": content,
            "status": "pending",
            "priority": priority.lower(),
        }

        # Add to existing todos
        todos.append(new_todo)

        # Convert todos to dict format for validation
        todos_data = [dict(todo) for todo in todos]

        # Write back
        count = store.write_todos(todos_data)

        return f"Added todo '{content}' with ID {new_todo['id']} to session {session_id}. Total: {count} todos."

    except Exception as e:
        return f"Error adding todo: {str(e)}"


def todo_complete(session_id: str, todo_id: str) -> str:
    """Mark a todo as completed by ID in a session.

    Args:
        session_id: The session ID
        todo_id: The ID of the todo to complete
    """
    try:
        store = _get_session_store(session_id)

        # Read existing todos
        todos = store.read_todos()

        # Find and update the todo
        found = False
        for todo in todos:
            if todo["id"] == todo_id:
                todo["status"] = "completed"
                found = True
                break

        if not found:
            return f"Error: Todo with ID '{todo_id}' not found in session {session_id}"

        # Convert todos to dict format for validation
        todos_data = [dict(todo) for todo in todos]

        # Write back
        count = store.write_todos(todos_data)

        return f"Marked todo '{todo_id}' as completed in session {session_id}. Total: {count} todos."

    except Exception as e:
        return f"Error completing todo: {str(e)}"


class Todo(llm.Toolbox):
    """Toolbox containing all todo management tools for structured task management.

    ## When to Use Todo Management
    Use this toolbox proactively in these scenarios:

    1. **Complex multi-step tasks** - When a task requires 3 or more distinct steps or actions
    2. **Non-trivial and complex tasks** - Tasks that require careful planning or multiple operations
    3. **User explicitly requests todo list** - When the user directly asks you to use the todo list
    4. **User provides multiple tasks** - When users provide a list of things to be done (numbered or comma-separated)
    5. **After receiving new instructions** - Immediately capture user requirements as todos
    6. **When you start working on a task** - Mark it as in_progress BEFORE beginning work. Ideally you should only have one todo as in_progress at a time
    7. **After completing a task** - Mark it as completed and add any new follow-up tasks discovered during implementation

    ## When NOT to Use Todo Management
    Skip using this toolbox when:
    1. There is only a single, straightforward task
    2. The task is trivial and tracking it provides no organizational benefit
    3. The task can be completed in less than 3 trivial steps
    4. The task is purely conversational or informational

    NOTE: You should not use this toolbox if there is only one trivial task to do. In this case you are better off just doing the task directly.

    ## Task States and Management Best Practices

    **Task States**: Use these states to track progress:
    - pending: Task not yet started
    - in_progress: Currently working on (limit to ONE task at a time)
    - completed: Task finished successfully

    **Task Management Rules**:
    - Update task status in real-time as you work
    - Mark tasks complete IMMEDIATELY after finishing (don't batch completions)
    - Exactly ONE task must be in_progress at any time (not less, not more)
    - Complete current tasks before starting new ones
    - Remove tasks that are no longer relevant from the list entirely

    **Task Completion Requirements**:
    - ONLY mark a task as completed when you have FULLY accomplished it
    - If you encounter errors, blockers, or cannot finish, keep the task as in_progress
    - When blocked, create a new task describing what needs to be resolved
    - Never mark a task as completed if implementation is partial or you encountered unresolved errors

    **Task Breakdown Guidelines**:
    - Create specific, actionable items
    - Break complex tasks into smaller, manageable steps
    - Use clear, descriptive task names
    - Focus on concrete deliverables rather than abstract goals

    When in doubt, use this toolbox. Being proactive with task management demonstrates attentiveness and ensures you complete all requirements successfully.
    """

    def todo_begin(self) -> str:
        """Start a new todo session and return the session ID.

        Use this to begin tracking a complex task with multiple steps. Always call this
        before using other todo management functions. The session ID will be used for
        all subsequent todo operations.

        Returns:
            Session ID string to use with other todo functions.
        """
        return todo_begin()

    def todo_end(self, session_id: str) -> str:
        """End a todo session and clean up its data.

        Call this when all tasks in a session are complete or when you no longer
        need to track the todos. This removes the session file and frees up resources.

        Args:
            session_id: The session ID returned from todo_begin()
        """
        return todo_end(session_id)

    def todo_list(self, session_id: str) -> str:
        """List all current todos for a session with their status and details.

        Use this to review your current progress and see which tasks are pending,
        in progress, or completed. Essential for maintaining awareness of your
        task pipeline.

        Args:
            session_id: The session ID to list todos for
        """
        return todo_list(session_id)

    def todo_write(self, session_id: str, todos_json: str) -> str:
        """Replace the entire todo list with new todos (JSON format).

        Use this for comprehensive task planning - when you receive complex requirements
        and need to break them down into organized, trackable steps. This is the primary
        method for setting up your task pipeline.

        CRITICAL: Always include exactly ONE task with status "in_progress" and the rest
        as "pending". Never have multiple tasks in_progress simultaneously.

        Args:
            session_id: The session ID
            todos_json: JSON string containing array of todo objects

        Example:
            [{"id": "1", "content": "Research existing implementation", "status": "in_progress", "priority": "high"},
             {"id": "2", "content": "Implement core functionality", "status": "pending", "priority": "high"}]
        """
        return todo_write(session_id, todos_json)

    def todo_add(self, session_id: str, content: str, priority: str = "medium") -> str:
        """Add a single new todo item to a session.

        Use this when you discover additional tasks during implementation that need
        to be tracked. Common scenarios: encountering unexpected requirements,
        identifying dependencies, or breaking down a complex task further.

        Args:
            session_id: The session ID
            content: The todo item description (be specific and actionable)
            priority: Priority level (high, medium, low)
        """
        return todo_add(session_id, content, priority)

    def todo_complete(self, session_id: str, todo_id: str) -> str:
        """Mark a todo as completed by ID in a session.

        CRITICAL: Only mark tasks as completed when they are FULLY accomplished.
        If you encounter errors, blockers, or partial implementation, keep the task
        as in_progress and create new todos for resolving the issues.

        After completing a task, immediately update the next pending task to in_progress.
        Maintain exactly ONE task as in_progress at all times.

        Args:
            session_id: The session ID
            todo_id: The ID of the todo to complete
        """
        return todo_complete(session_id, todo_id)


@llm.hookimpl
def register_tools(register):
    """Register todo management toolbox with LLM."""
    register(Todo)
