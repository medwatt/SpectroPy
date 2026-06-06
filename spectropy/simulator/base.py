# imports <<<
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

import numpy as np

from .results import AnalysisResult, Result
from . import collection
# >>>


class Runnable(ABC):
    """A self-contained, composable node in a Spectre run.

    Every runnable knows how to (1) emit its own deck text via
    ``build_command()`` and (2) collect its own results via ``collect()``.
    Everything passed to ``SpectreSession.run()`` is a ``Runnable`` and produces
    a result; there are no result-less peers.  Adding a new construct therefore
    means implementing these two methods on one class and nothing else.
    """

    #: Identifier used both in the netlist and as the key into ``RunResult``.
    name: str

    @abstractmethod
    def build_command(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def collect(self, raw_dir: Path) -> Result:
        """Gather this runnable's results from the Spectre ``.raw`` directory."""
        raise NotImplementedError

    def __str__(self) -> str:
        return self.build_command()


class Analysis(Runnable):
    """Base class for Spectre analyses -- the leaves of the run tree.

    An analysis emits a single analysis statement and produces exactly one
    ``AnalysisResult``.
    """

    @property
    def psf_stem(self) -> str:
        """Filename stem used by Spectre for this analysis' PSF output."""
        raise NotImplementedError

    def make_result(
        self,
        meta: dict,
        sweep_name: str | None,
        sweep: np.ndarray | None,
        signals: dict[str, np.ndarray],
    ) -> AnalysisResult:
        """Construct the result object for this analysis from parsed PSF data.

        Subclasses override this to return the appropriate ``AnalysisResult``
        subclass.  The default returns a bare ``AnalysisResult``.
        """
        return AnalysisResult(meta=meta, signals=signals)

    def collect(self, raw_dir: Path) -> AnalysisResult:
        return collection.single_result(raw_dir, self)

    @staticmethod
    def _sweep_array(sweep: np.ndarray | None) -> np.ndarray:
        return sweep if sweep is not None else np.array([], dtype=float)


class Scope(Runnable):
    """Base class for runnables that own a set of inner runnables.

    A scope establishes some deck configuration (a sweep header, a Monte Carlo
    block, a corner altergroup, arbitrary setup statements) and runs its
    ``inner`` runnables under it, producing a ``GroupResult`` that mirrors the
    declaration structure.

    ``inner`` is typed as a sequence of ``Runnable`` so the tree is recursive by
    construction; collection of deeply nested scopes is validated incrementally
    (see ``collection``).
    """

    inner: tuple[Runnable, ...]
