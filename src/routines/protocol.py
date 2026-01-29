"""Routine protocol - the contract all routines must follow."""

from dataclasses import dataclass
from typing import Protocol
import pendulum


@dataclass
class RoutineContext:
    """Context passed to routines during execution."""

    now: pendulum.DateTime
    """Current time in Pacific."""

    is_new_session: bool
    """Whether this is a new session or resuming an existing one."""

    session_id: str | None
    """The session ID being resumed, if any."""

    routine_name: str
    """The fully qualified name of this routine (e.g., 'alpha.to_self')."""


class Routine(Protocol):
    """Protocol that all routines must implement."""

    name: str
    """Fully qualified routine name, e.g., 'alpha.solitude.first_breath'."""

    # Session configuration (optional)
    session_key: str | None
    """Redis key for session persistence. None = stateless (fresh session each run)."""

    session_ttl: int | None
    """TTL in seconds for session key. Ignored if session_key is None."""

    # Fork behavior (for routines that resume human sessions)
    fork_session: bool
    """If True, fork from the session instead of resuming it directly."""

    fork_from_key: str | None
    """Redis key to fork from (if different from session_key).

    Used by routines like to_self that fork from the human session
    but don't persist their own session state.
    """

    def build_prompt(self, ctx: RoutineContext) -> str:
        """Build the prompt for this routine.

        Args:
            ctx: Execution context with timing and session info.

        Returns:
            The prompt string to send to the agent.
        """
        ...

    def handle_output(self, output: str, ctx: RoutineContext) -> None:
        """Handle the routine's output.

        Called after the agent completes. Use this to store results
        to Redis, Postgres, or wherever they need to go.

        Args:
            output: The collected text output from the agent.
            ctx: Execution context.
        """
        ...

    def get_allowed_tools(self) -> list[str]:
        """Return the list of tools this routine is allowed to use.

        Override to customize. Default is a reasonable set for most routines.
        """
        ...
