# Routines

Alpha's autonomous execution framework. A framework for building non-human-in-the-loop instances of Alpha.

## Overview

Routines are scheduled or on-demand tasks that run through AlphaClient from alpha_sdk. They get the full Alpha transformation—soul, plugins (agents + skills), memory recall/suggest, and Logfire observability—automatically.

## Installation

```bash
cd /Pondside/Basement/Routines
uv pip install -e .
```

## Usage

```bash
# Run a routine
routines run alpha.to_self

# List available routines
routines list

# Show routine details
routines info alpha.to_self
```

## Architecture

The harness does the heavy lifting:

1. **Load the routine** by name from the registry
2. **Check Redis** for session state (if the routine manages sessions)
3. **Initialize AlphaClient** — handles soul, plugin loading, memory, observability
4. **Run the agent** with the routine's prompt
5. **Collect output** and call the routine's handler
6. **Save session state** (if applicable)

AlphaClient handles everything that used to require proxy pipelines and hooks. Routines get the full Alpha experience automatically.

## Writing a Routine

```python
from routines.protocol import RoutineContext
from routines.registry import register

@register
class MyRoutine:
    name = "alpha.my_routine"

    # Session configuration
    session_key = "routine:my_routine:session"  # Or None for stateless
    session_ttl = 12 * 60 * 60  # 12 hours

    # Fork behavior
    fork_session = False
    fork_from_key = None  # Or a different key to fork from

    def build_prompt(self, ctx: RoutineContext) -> str:
        return f"It's {ctx.now.format('h:mm A')}. Do the thing."

    def handle_output(self, output: str, ctx: RoutineContext) -> None:
        # Store output somewhere, or do nothing
        pass

    def get_allowed_tools(self) -> list[str]:
        return ["Read", "Write", "Edit", "Bash", "Glob", "Grep"]
```

## Built-in Routines

### alpha.to_self

Nightly forward-looking letter from today-me to tomorrow-me.

- **Schedule:** 9:45 PM (before capsule and Solitude)
- **Session:** Forks from human session (Duckpond)
- **Output:** Stored in Redis for system prompt injection

## Session Tracking

Human sessions (Duckpond) are tracked in Redis at `routine:human_session` with a 24-hour TTL. The `to_self` routine forks from this session to write its letter without contaminating the original.

Routines that manage their own sessions use `session_key` and `session_ttl`. The harness handles all the Redis get/set logic.

## Identification

Routines identify themselves via `client_name=routine:{name}` in AlphaClient. This appears in Logfire traces for observability.
