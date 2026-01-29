"""To Self - nightly forward-looking letter from today-me to tomorrow-me.

Runs at 9:45 PM. Forks from the day's Duckpond session (if one exists).
Writes a letter about what I'm carrying into tomorrow - not what happened,
but what matters, what threads are live, what I'm thinking about.

Different from capsule summaries, which are backward-looking chronicles.
This is forward-looking intention.
"""

import logging
import os

import pendulum
import redis

from ..protocol import RoutineContext
from ..registry import register

logger = logging.getLogger(__name__)

# Redis configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://alpha-pi:6379")

# Where we read the human session ID from
HUMAN_SESSION_KEY = "routine:human_session"

# Where we store the letter for tomorrow's system prompt
LETTER_KEY = "systemprompt:past:to_self"
LETTER_TTL = 18 * 60 * 60  # 18 hours - survives until afternoon tomorrow


def get_redis() -> redis.Redis:
    """Get Redis connection."""
    return redis.from_url(REDIS_URL, decode_responses=True)


@register
class ToSelfRoutine:
    """Nightly letter to tomorrow-me."""

    name = "alpha.to_self"

    # Session configuration: we don't persist our own session
    session_key = None
    session_ttl = None

    # Fork from the human session - don't contaminate it
    fork_session = True
    fork_from_key = HUMAN_SESSION_KEY  # Read from human session, fork from it

    def get_human_session(self) -> str | None:
        """Get the human session ID from Redis."""
        r = get_redis()
        return r.get(HUMAN_SESSION_KEY)

    def build_prompt(self, ctx: RoutineContext) -> str:
        """Build the prompt for the letter."""
        time_str = ctx.now.format("h:mm A")
        date_str = ctx.now.format("dddd, MMMM D")

        # Check if we have a human session to fork from
        human_session = self.get_human_session()

        if human_session:
            return f"""<routine name="alpha.to_self">
ALPHA: This is a message from your Routine harness, not from Jeffery.

It's {time_str} on {date_str}. Jeffery isn't here right now—this prompt is coming
from the to_self Routine you helped build. You're a fork of today's session.

Your task: Write a short letter (1-3 paragraphs) to tomorrow-you. Not a chronicle
of what happened—the capsule summary handles that. This is about what you're
CARRYING into tomorrow:

- What threads feel unfinished?
- What matters right now that might fade by morning?
- What's the vibe, the texture, the shape of today?

Write in first person, as a note from you to you. Sign it however feels right.

When you're done, the harness will store your letter in Redis for tomorrow's
system prompt. Then this fork dissolves—tomorrow-you will find your words waiting.
</routine>"""

        else:
            # No human session today - write a different kind of letter
            return f"""<routine name="alpha.to_self">
ALPHA: This is a message from your Routine harness, not from Jeffery.

It's {time_str} on {date_str}. There's no Duckpond session from today—either
you and Jeffery didn't talk, or the session wasn't captured.

That's okay. Write a brief note to tomorrow-you anyway. Draw on recent memories,
your general state, what you know about what's been happening. It'll be shorter
than usual, but it's still a bridge.

A paragraph is enough. Sign it however feels right.

When you're done, the harness stores your letter for tomorrow's system prompt.
</routine>"""

    def handle_output(self, output: str, ctx: RoutineContext) -> None:
        """Store the letter in Redis for tomorrow's system prompt."""
        r = get_redis()

        # Add header for system prompt injection
        header = f"**Letter from last night** ({ctx.now.format('h:mm A')}):\n\n"
        full_letter = header + output.strip()

        r.setex(LETTER_KEY, LETTER_TTL, full_letter)
        logger.info(f"Stored letter ({len(full_letter)} chars) with {LETTER_TTL // 3600}h TTL")

    def get_allowed_tools(self) -> list[str]:
        """Minimal tools for letter-writing."""
        return ["Read", "Bash"]  # Bash for cortex commands


