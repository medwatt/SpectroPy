# imports <<<
from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np

from .results import SpectreResult
# >>>


class Runnable(ABC):
    """Anything that can contribute Spectre analysis statements to a run."""

    @abstractmethod
    def build_command(self) -> str:
        raise NotImplementedError

    def __str__(self) -> str:
        return self.build_command()


class Statement(Runnable):
    """Base class for Spectre control statements that do not produce results."""


class Simulation(Runnable):
    """Base class for Spectre analyses."""

    name: str

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
    ) -> SpectreResult:
        """Construct the result object for this analysis from parsed PSF data.

        Subclasses override this to return the appropriate SpectreResult
        subclass. The default returns a bare SpectreResult.
        """
        return SpectreResult(meta=meta, signals=signals)

    @staticmethod
    def _sweep_array(sweep: np.ndarray | None) -> np.ndarray:
        return sweep if sweep is not None else np.array([], dtype=float)
