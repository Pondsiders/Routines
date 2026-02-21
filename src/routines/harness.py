"""Routine harness - the execution engine that runs routines.

This is the core of the framework. It:
1. Loads the routine by name
2. Checks Redis for session state (if applicable)
3. Runs the routine through AlphaClient (full Alpha transformation)
4. Collects output and calls the routine's handler
5. Saves session state (if applicable)

Uses AlphaClient from alpha_sdk, which handles:
- System prompt assembly (soul + orientation)
- Plugin loading (agents, skills)
- Memory recall and suggest
- Observability
"""

import logging
import os

import pendulum
import redis

from alpha_sdk import AlphaClient
from alpha_sdk.observability import configure as configure_logfire

from .protocol import Routine, RoutineContext

logger = logging.getLogger(__name__)

# Redis configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://alpha-pi:6379")


def get_redis() -> redis.Redis:
    """Get Redis connection."""
    return redis.from_url(REDIS_URL, decode_responses=True)


async def run_routine(routine: Routine) -> str:
    """Run a routine and return its output.

    This is the main execution function. It:
    1. Checks for existing session (if routine has session_key)
    2. Builds the prompt
    3. Runs through AlphaClient (handles soul, plugins, memories, everything)
    4. Collects output
    5. Saves session state (if applicable)
    6. Calls the routine's output handler

    Args:
        routine: The routine instance to run.

    Returns:
        The collected text output from the agent.
    """
    from claude_agent_sdk import AssistantMessage, ResultMessage

    # Configure Logfire with routine-specific service name
    configure_logfire(service_name=f"routine:{routine.name}")

    now = pendulum.now("America/Los_Angeles")
    r = get_redis()

    # === Check for existing session ===
    session_id = None
    is_new_session = True

    # Determine which key to read from:
    # - fork_from_key if set (for routines that fork from human sessions)
    # - session_key otherwise (for routines that manage their own sessions)
    read_key = getattr(routine, 'fork_from_key', None) or routine.session_key

    if read_key:
        session_id = r.get(read_key)
        if session_id:
            is_new_session = False
            logger.info(f"Found session from {read_key}: {session_id[:8]}...")
        else:
            logger.info(f"No session found at {read_key}, will create new")

    # === Build context and prompt ===
    ctx = RoutineContext(
        now=now,
        is_new_session=is_new_session,
        session_id=session_id,
        routine_name=routine.name,
    )

    prompt = routine.build_prompt(ctx)
    logger.info(f"Built prompt ({len(prompt)} chars)")

    # === Run through AlphaClient ===
    async with AlphaClient(
        cwd="/Pondside",
        client_name=f"routine:{routine.name}",
        permission_mode="bypassPermissions",
        disallowed_tools=routine.get_disallowed_tools(),
    ) as client:
        await client.query(prompt, session_id=session_id)

        output_parts: list[str] = []

        logger.info(f"Starting agent (session={'resume ' + session_id[:8] if session_id else 'new'}...)")

        async for event in client.stream():
            if isinstance(event, AssistantMessage):
                for block in event.content:
                    if hasattr(block, "text") and block.text:
                        output_parts.append(block.text)
                        # Stream to stdout for observability
                        print(block.text, end="", flush=True)

            elif isinstance(event, ResultMessage):
                logger.info(f"Agent complete: {event.subtype}")

        print()  # Newline after streaming output

        output = "".join(output_parts)
        captured_session_id = client.session_id

    # === Save session state ===
    if routine.session_key and routine.session_ttl:
        if is_new_session and captured_session_id:
            # New session - save the SDK's session ID
            r.setex(routine.session_key, routine.session_ttl, captured_session_id)
            logger.info(f"Saved new session: {captured_session_id[:8]}...")
        elif not is_new_session and not routine.fork_session:
            # Resumed session (not forked) - refresh TTL
            r.expire(routine.session_key, routine.session_ttl)
            logger.info("Refreshed session TTL")
        # If forked, we don't update the original session key

    # === Call output handler ===
    routine.handle_output(output, ctx)

    return output
