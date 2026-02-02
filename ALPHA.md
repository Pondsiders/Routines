---
autoload: when
when: "working on or discussing Routines, Solitude, alpha.today, alpha.to_self, scheduled Alpha tasks, nighttime breathing"
---

## Overview

Routines is Alpha's autonomous execution framework for building non-human-in-the-loop instances of Alpha. Routines are scheduled/on-demand tasks that run through the full AlphaPattern pipeline, inheriting hooks and getting proper orientation (HUD, weather, calendars, todos).

## Commands

```bash
# Install
uv pip install -e .

# Run a routine
routines run alpha.to_self

# List all routines
routines list

# Show routine details
routines info alpha.to_self
```

## Architecture

### Core Components

- **`protocol.py`** - Defines `Routine` protocol and `RoutineContext` dataclass. All routines implement `build_prompt()`, `handle_output()`, and `get_allowed_tools()`.

- **`registry.py`** - `@register` decorator adds routines to global registry. Routines are instantiated on-demand via `get(name)`.

- **`harness.py`** - Execution engine that orchestrates: session lookup → prompt building → Agent SDK initialization → streaming execution → session persistence → output handling.

- **`cli.py`** - Click CLI entry point. Calls `load_routines()` to trigger registration on startup.

### Execution Flow

1. Registry lookup by name
2. Check Redis for session (using `fork_from_key` or `session_key`)
3. Build prompt with `RoutineContext` (Pacific time via Pendulum)
4. Initialize Claude Agent SDK with `setting_sources=["project"]` and `cwd="/Pondside"` (loads hooks from `/Pondside/.claude/`)
5. Stream query, collect output
6. Save/refresh session if applicable
7. Call `handle_output()`

### Session Management

- **Human sessions**: Tracked at `routine:human_session` (24-hour TTL)
- **Routine sessions**: Each can have its own `session_key` + `session_ttl`
- **Forking**: `fork_session=True` + `fork_from_key` lets routines branch from human sessions without contaminating them

### Key Patterns

Custom headers are set explicitly in harness (env vars don't reliably propagate to hook subprocesses):
- `x-loom-client: routine:{name}` - Excludes from human session tracking
- `x-loom-pattern: alpha` - Routes through AlphaPattern

Routines store raw content in Redis; Loom handles presentation/formatting separately.

## Adding a Routine

1. Create class with `@register` decorator in `src/routines/alpha/`
2. Set `name`, session config (`session_key`, `session_ttl`, `fork_session`, `fork_from_key`)
3. Implement `build_prompt()`, `handle_output()`, `get_allowed_tools()`
4. Import in `src/routines/alpha/__init__.py` to trigger registration

## Environment Variables

- `REDIS_URL` - Redis connection (default: `redis://alpha-pi:6379`)
- `DATABASE_URL` - PostgreSQL for memory fetching (used by alpha.today)
