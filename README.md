# Routines

Alpha's autonomous execution framework. A framework for building non-human-in-the-loop instances of Alpha.

## Overview

Routines are scheduled or on-demand tasks that run through the full AlphaPattern pipeline. They inherit hooks and get proper orientation (HUD, weather, calendars, todos) just like Duckpond sessions.

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
3. **Initialize the Claude Agent SDK** with `setting_sources=["project"]` and `cwd="/Pondside"`
4. **Run the agent** with the routine's prompt
5. **Collect output** and call the routine's handler
6. **Save session state** (if applicable)

Because routines use `setting_sources=["project"]`, they load the hooks from `/Pondside/.claude/`. Those hooks inject pattern metadata, which routes through AlphaPattern. This means routines get the full Alpha experience—soul, HUD, memories, the works.

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

## Client Header

Routines identify themselves via `x-loom-client: routine:{name}`. This header:
- Excludes routines from human session tracking
- Enables future routing decisions in the Loom
- Provides observability in traces
