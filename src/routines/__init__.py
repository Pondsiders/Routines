"""Routines - Alpha's autonomous execution framework.

A framework for building non-human-in-the-loop instances of Alpha.
Routines are scheduled or on-demand tasks that run through the full
AlphaPattern pipeline, inheriting hooks and getting proper orientation.

Usage:
    routines run alpha.to_self      # Run the "to self" letter routine
    routines run alpha.solitude.first_breath
    routines list                    # List available routines
"""

__version__ = "0.1.0"
