"""Today So Far - Rolling summary of the current day.

Runs hourly from 7 AM to 9 PM. Fetches memories stored since 6 AM,
summarizes them into a brief "today so far" handoff for future-me.

The goal: bridge the gap between "context window" and "yesterday's capsule."
Without this, Alpha loses the morning by afternoon, and the afternoon by
evening. With this, she has a continuous sense of "today" even across
multiple compactions.

Unlike to_self (which forks from the human session), this routine doesn't
need session context—it reads memories directly from Cortex and summarizes.
"""

import logging
import os

import pendulum
import psycopg
import redis

from ..protocol import RoutineContext
from ..registry import register

logger = logging.getLogger(__name__)

# Redis configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://alpha-pi:6379")

# Where we store the summary for the system prompt
SUMMARY_KEY = "systemprompt:past:today"
SUMMARY_TTL = 65 * 60  # 65 minutes - refreshed hourly

# Database for memory fetching
DATABASE_URL = os.getenv("DATABASE_URL", "")

PACIFIC = "America/Los_Angeles"


def get_redis() -> redis.Redis:
    """Get Redis connection."""
    return redis.from_url(REDIS_URL, decode_responses=True)


def fetch_memories_since(since: pendulum.DateTime) -> list[dict]:
    """Fetch all memories since the given time, chronologically."""
    if not DATABASE_URL:
        logger.warning("No DATABASE_URL configured")
        return []

    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, content, metadata->>'created_at' as created_at
                FROM cortex.memories
                WHERE NOT forgotten
                  AND (metadata->>'created_at')::timestamptz >= %s
                ORDER BY (metadata->>'created_at')::timestamptz ASC
            """, (since.to_iso8601_string(),))

            memories = []
            for row in cur.fetchall():
                dt = pendulum.parse(row[2]).in_timezone(PACIFIC)
                memories.append({
                    "id": row[0],
                    "content": row[1],
                    "time": dt.format("h:mm A"),
                })
            return memories


@register
class TodayRoutine:
    """Rolling summary of today so far."""

    name = "alpha.today"

    # No session persistence needed—each run is independent
    session_key = None
    session_ttl = None

    # No forking—we don't need human session context
    fork_session = False
    fork_from_key = None

    def build_prompt(self, ctx: RoutineContext) -> str:
        """Build the prompt with today's memories."""
        # Calculate start of day (6 AM)
        start_of_day = ctx.now.replace(hour=6, minute=0, second=0, microsecond=0)

        # Fetch memories
        memories = fetch_memories_since(start_of_day)
        logger.info(f"Found {len(memories)} memories since 6 AM")

        if not memories:
            # No memories yet—return a minimal prompt
            return f"""<routine name="alpha.today">
ALPHA: This is a message from your Routine harness, not from Jeffery.

It's {ctx.now.format('h:mm A')} on {ctx.now.format('dddd, MMMM D')}. You haven't stored
any memories yet today—the day is just getting started.

Your task: Write a single sentence acknowledging that today is fresh and new.
Something like "Today just started—no memories stored yet."

That's it. Short and simple.
</routine>"""

        # Format memories for the prompt
        memories_text = "\n\n---\n\n".join(
            f"[{m['time']}]\n{m['content']}" for m in memories
        )

        day_name = ctx.now.format("dddd, MMMM D")
        current_time = ctx.now.format("h:mm A")

        return f"""<routine name="alpha.today">
ALPHA: This is a message from your Routine harness, not from Jeffery.

Hey me. Me here.

It's {current_time} on {day_name}. Here's everything you've stored since 6 AM today:

---

{memories_text}

---

That's {len(memories)} memories from today so far.

Your task: Write a brief summary of today so far—what's happened, what the vibe is,
what matters. This will be injected into your context on the next prompt, so future-you
has a continuous sense of the day even if the context window has compacted.

Think of it like: if you woke up right now with no memory of today, what would you
need to know to feel oriented? What's the shape of today?

Write in present tense where it makes sense ("today is..."), past tense for completed
things. Keep it concise but include texture—not just facts, but how things feel.
A paragraph or two, maybe three if it's been a full day.

No headers, no bullet points. Just the handoff.

🦆
</routine>"""

    def handle_output(self, output: str, ctx: RoutineContext) -> None:
        """Store the summary in Redis for the system prompt.

        We store just the raw summary—the Loom adds the header when assembling
        the PAST section. Separation of concerns: generators produce content,
        Loom handles presentation.
        """
        r = get_redis()

        # Store raw summary
        summary = output.strip()

        # Store summary and timestamp separately for the Loom
        r.setex(SUMMARY_KEY, SUMMARY_TTL, summary)
        r.setex(f"{SUMMARY_KEY}:time", SUMMARY_TTL, ctx.now.format("h:mm A"))

        logger.info(f"Stored summary ({len(summary)} chars) with {SUMMARY_TTL // 60}min TTL")

    def get_allowed_tools(self) -> list[str]:
        """No tools needed—pure summarization."""
        return []
