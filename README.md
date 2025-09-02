# llm-tools-todo

[![PyPI](https://img.shields.io/pypi/v/llm-tools-todo.svg)](https://pypi.org/project/llm-tools-todo/)
[![Changelog](https://img.shields.io/github/v/release/dannyob/llm-tools-todo?include_prereleases&label=changelog)](https://github.com/dannyob/llm-tools-todo/releases)
[![Tests](https://github.com/dannyob/llm-tools-todo/actions/workflows/test.yml/badge.svg)](https://github.com/dannyob/llm-tools-todo/actions/workflows/test.yml)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://github.com/dannyob/llm-tools-todo/blob/main/LICENSE)

LLM plugin providing session-based todo management tools for Simon Willison's `llm`, a la Claude Code.

## Installation

Install this plugin in the same environment as [LLM](https://llm.datasette.io/). You'll need at least LLM [0.26a1](https://llm.datasette.io/en/latest/changelog.html#a1-2025-05-25) or later.

### From PyPI (recommended)

```bash
llm install llm-tools-todo
```

### From source

```bash
git clone https://github.com/dannyob/llm-tools-todo
cd llm-tools-todo
llm install .
```

## Usage

The plugin provides a single `Todo` toolbox with six todo management operations:

### Available Tools

- `todo_begin` - Start a new todo session
- `todo_end` - End current session and cleanup
- `todo_list` - Display all todos in current session
- `todo_write` - Replace entire todo list
- `todo_add` - Add new todo items
- `todo_complete` - Mark todos as completed

### Basic Usage

```bash
# Start a new todo session
llm prompt -m gpt-4o-mini "Please start a new todo session" --tool Todo

# Add some tasks
llm -c prompt -m gpt-4o-mini "Add tasks: review code, run tests, update docs" --tool Todo

# Mark tasks complete
llm -c prompt -m gpt-4o-mini "Mark the first task as completed" --tool Todo
```

### Session Management

Each todo session gets a unique identifier and stores data in temporary files. Sessions are automatically managed:

- Session files stored as `/tmp/llm-todos-{session_id}.json`
- Data persists until session is ended with `todo_end`
- Multiple concurrent sessions supported

### Todo Item Structure

Each todo item includes:
- Unique ID
- Content description
- Status (pending/in_progress/completed)
- Priority (high/medium/low)
- Created and updated timestamps

## Development

### Setup Development Environment

```bash
# Clone and set up development environment
git clone https://github.com/dannyob/llm-tools-todo
cd llm-tools-todo
make dev-setup
source .venv/bin/activate
```

### Testing

```bash
make test           # Run all tests
make test-coverage  # Run tests with coverage report
make quick-test     # Fast test run (exits on first failure)
```

### Plugin Testing

After installation, verify the plugin is working:

```bash
llm tools  # Should list Todo tools
llm prompt "Please start a new todo session" --tool Todo
llm -c "What is in my todo list?" --tool Todo
```

## Credits and Thanks

Inspired by Claude Code's simple Todo functionality, and [Joe
Haddad](https://github.com/joehaddad2000/)'s [`claude-todo-emulator`](https://github.com/joehaddad2000/claude-todo-emulator).

Coded with Claude.
