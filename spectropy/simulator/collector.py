# imports <<<
from __future__ import annotations

from pathlib import Path

from .base import Runnable
from .results import RunResult
# >>>


def collect_results(
    raw_dir: Path, runnables: tuple[Runnable, ...], completed: object = None
) -> RunResult:
    """Build the ``RunResult`` for a finished run.

    Each runnable collects its own results (polymorphically), so this function
    stays a thin assembler: adding a new construct never requires editing it.
    """
    results = [r.collect(raw_dir) for r in runnables]
    names = [r.name for r in runnables]
    return RunResult(results, names, completed=completed)
