"""Routine registry - maps names to routine classes."""

import logging
from typing import Type

from .protocol import Routine

logger = logging.getLogger(__name__)

# Registry maps fully-qualified names to Routine classes
_registry: dict[str, Type[Routine]] = {}


def register(routine_class: Type[Routine]) -> Type[Routine]:
    """Decorator to register a routine class.

    Usage:
        @register
        class ToSelfRoutine:
            name = "alpha.to_self"
            ...
    """
    name = routine_class.name
    _registry[name] = routine_class
    logger.debug(f"Registered routine: {name}")
    return routine_class


def get(name: str) -> Routine:
    """Get a routine instance by name.

    Args:
        name: Fully qualified routine name (e.g., 'alpha.to_self').

    Returns:
        An instance of the routine.

    Raises:
        KeyError: If routine not found.
    """
    if name not in _registry:
        available = ", ".join(sorted(_registry.keys()))
        raise KeyError(f"Unknown routine: {name}. Available: {available}")

    return _registry[name]()


def list_all() -> list[str]:
    """List all registered routine names."""
    return sorted(_registry.keys())


def load_routines():
    """Import all routine modules to trigger registration.

    Call this at startup to populate the registry.
    """
    # Import routine modules here - they use @register decorator
    from .alpha import to_self  # noqa: F401
    from .alpha import today  # noqa: F401
    from .alpha import solitude  # noqa: F401

    logger.info(f"Loaded {len(_registry)} routines")
