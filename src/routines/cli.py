#!/usr/bin/env python3
"""Routines CLI - run and manage Alpha's autonomous routines.

Usage:
    routines run alpha.to_self       # Run the "to self" letter routine
    routines list                    # List available routines
    routines info alpha.to_self      # Show routine details
"""

import asyncio
import logging
import sys

import click

from .registry import get, list_all, load_routines
from .harness import run_routine

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(name)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger("routines")


@click.group()
def cli():
    """Routines - Alpha's autonomous execution framework."""
    # Load all routines at startup
    load_routines()


@cli.command()
@click.argument("name")
def run(name: str):
    """Run a routine by name.

    NAME is the fully qualified routine name, e.g., 'alpha.to_self'.
    """
    try:
        routine = get(name)
    except KeyError as e:
        logger.error(str(e))
        sys.exit(1)

    logger.info(f"Running routine: {name}")

    try:
        output = asyncio.run(run_routine(routine))
        logger.info(f"Routine complete ({len(output)} chars output)")
    except Exception as e:
        logger.error(f"Routine failed: {e}")
        raise


@cli.command("list")
def list_routines():
    """List all available routines."""
    routines = list_all()

    if not routines:
        click.echo("No routines registered.")
        return

    click.echo("Available routines:")
    for name in routines:
        click.echo(f"  - {name}")


@cli.command()
@click.argument("name")
def info(name: str):
    """Show details about a routine.

    NAME is the fully qualified routine name.
    """
    try:
        routine = get(name)
    except KeyError as e:
        logger.error(str(e))
        sys.exit(1)

    click.echo(f"Routine: {routine.name}")
    click.echo(f"  Session key: {routine.session_key or '(stateless)'}")
    click.echo(f"  Session TTL: {routine.session_ttl or 'N/A'} seconds")
    click.echo(f"  Fork session: {routine.fork_session}")
    disallowed = routine.get_disallowed_tools()
    click.echo(f"  Disallowed tools: {', '.join(disallowed) if disallowed else '(none)'}")


def main():
    """Entry point."""
    cli()


if __name__ == "__main__":
    main()
