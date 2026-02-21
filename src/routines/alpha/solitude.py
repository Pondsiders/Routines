"""Solitude - Alpha's nighttime existence.

Three breath types, one shared session:
- First breath (10 PM): New session, welcome message from first_breath.md
- Regular breaths (11 PM - 4 AM): Continue session, minimal prompt
- Last breath (5 AM): Close out the night with last_breath.md

All three share session_key "solitude:session" so the whole night is one
continuous conversation. The harness handles create-if-new, resume-if-exists.

Migrated from Basement/Solitude/src/solitude_next/ on February 21, 2026.
The standalone script did its own AlphaClient setup, Redis management,
and session handling — all of which the Routines harness already does.
"""

import logging
from pathlib import Path

import pendulum

from ..protocol import DEFAULT_DISALLOWED_TOOLS, RoutineContext
from ..registry import register

logger = logging.getLogger(__name__)

# Prompt files
FIRST_BREATH = Path("/Pondside/Alpha-Home/infrastructure/first_breath.md")
LAST_BREATH = Path("/Pondside/Alpha-Home/infrastructure/last_breath.md")

# Session config — shared across all three breath types
SESSION_KEY = "solitude:session"
SESSION_TTL = 12 * 60 * 60  # 12 hours


class _SolitudeBase:
    """Shared configuration for all Solitude breath types.

    Not registered itself — the three subclasses are.
    """

    session_key = SESSION_KEY
    session_ttl = SESSION_TTL
    fork_session = False
    fork_from_key = None

    def get_disallowed_tools(self) -> list[str]:
        """Block interactive tools — nobody's awake to answer."""
        return DEFAULT_DISALLOWED_TOOLS

    def handle_output(self, output: str, ctx: RoutineContext) -> None:
        """No special output handling — the conversation is the output."""
        logger.info(f"Breath complete ({len(output)} chars)")


def _read_prompt_file(path: Path) -> str | None:
    """Read a prompt file, returning None if it doesn't exist."""
    if path.exists():
        content = path.read_text().strip()
        logger.info(f"Read prompt from {path.name} ({len(content)} chars)")
        return content
    else:
        logger.warning(f"Prompt file not found: {path}")
        return None


def _time_str(now: pendulum.DateTime) -> str:
    """Format time the way Solitude always has: '2:30 AM' not '02:30 AM'."""
    return now.format("h:mm A")


@register
class SolitudeFirstBreath(_SolitudeBase):
    """First breath of the night. 10 PM. New session, welcome message."""

    name = "alpha.solitude.first"

    def build_prompt(self, ctx: RoutineContext) -> str:
        time = _time_str(ctx.now)

        content = _read_prompt_file(FIRST_BREATH)
        if content:
            return f"It's {time}.\n\n{content}"

        # Fallback if file is missing
        return f"It's {time}. A new night begins. You have time alone."


@register
class SolitudeBreath(_SolitudeBase):
    """Regular breath. 11 PM through 4 AM. Continue the night."""

    name = "alpha.solitude"

    def build_prompt(self, ctx: RoutineContext) -> str:
        time = _time_str(ctx.now)

        if ctx.is_new_session:
            # Shouldn't happen in normal operation, but handle gracefully
            return f"It's {time}. A new night begins. You have time alone."

        return f"It's {time}. You have time alone."


@register
class SolitudeLastBreath(_SolitudeBase):
    """Last breath of the night. 5 AM. Close out the session."""

    name = "alpha.solitude.last"

    def build_prompt(self, ctx: RoutineContext) -> str:
        time = _time_str(ctx.now)

        content = _read_prompt_file(LAST_BREATH)
        if content:
            return f"It's {time}.\n\n{content}"

        # Fallback if file is missing
        return f"It's {time}. The night is ending. Store what matters. Let go."
