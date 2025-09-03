# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Plugin Development Commands

Use `llm install .` to install LLM plugins from the current directory (not pip install).

Test the plugin after installation:
```bash
llm tools  # List available tools to verify registration
llm prompt -m gpt-4o-mini "Please start a new todo session" --tool Todo  # Test functionality
```

## Architecture Overview

This is an LLM plugin that provides session-based todo management tools through a Toolbox pattern. The plugin exposes 6 todo management functions bundled in a single `Todo` class.

### Core Components

**Todo** (`plugin.py:246`): Main toolbox class that bundles all todo tools
- Extends `llm.Toolbox` 
- Methods become available as tools with naming pattern `Todo_method_name`
- Contains 6 todo management methods: `begin`, `end`, `list`, `write`, `add`, `complete`

**TodoStore** (`plugin.py:26`): Handles persistent storage and retrieval
- Async file-based storage using JSON
- Session-specific temp files: `/tmp/llm-todos-{session_id}.json`
- Validates data through `TodoItem` pydantic model

**TodoItem** (`plugin.py:16`): Pydantic model defining todo structure
- Fields: `id`, `content`, `status` (pending/in_progress/completed), `priority` (high/medium/low), timestamps
- Handles validation and serialization

### Session Management

**Session-based Architecture**: Each todo session gets a unique 8-character UUID
- Sessions are cached in `_session_stores` global dict
- Session files stored in temp directory as `llm-todos-{session_id}.json`
- Session lifecycle: `begin()` → use tools → `end()` (cleanup)

### Key Implementation Details

- All todo functions are standalone and wrapped by Todo toolbox methods
- Uses `asyncio.run()` to handle async storage operations in sync tool functions
- Session store factory pattern with `_get_session_store()` for lazy initialization
- JSON storage format: `{"todos": [...], "updated_at": "..."}`