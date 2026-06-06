# imports <<<
from __future__ import annotations
from collections.abc import Iterator, Sequence
from typing import Any
import numpy as np
# >>>


class Result:
    """Marker base class for everything a runnable can produce.

    A ``Runnable`` produces either an ``AnalysisResult`` (a leaf analysis) or a
    ``GroupResult`` (a scope).  The result tree mirrors the declaration tree.
    """


class AnalysisResult(Result):
    """Base for all single-analysis results."""

    def __init__(self, meta: dict, signals: dict[str, np.ndarray]) -> None:
        self._meta = meta
        self._signals = signals

    def __getitem__(self, name: str) -> np.ndarray:
        return self._signals[name]

    def __iter__(self):
        return iter(self._signals)

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(self._signals)

    @property
    def values(self) -> dict[str, np.ndarray]:
        return dict(self._signals)

    @property
    def voltages(self) -> dict[str, np.ndarray]:
        return {k: v for k, v in self._signals.items() if ":" not in k}

    @property
    def currents(self) -> dict[str, np.ndarray]:
        return {k: v for k, v in self._signals.items() if ":" in k and len(k.split(":")[-1]) == 1}

    @property
    def oppoints(self) -> dict[str, np.ndarray]:
        return {k: v for k, v in self._signals.items() if ":" in k and len(k.split(":")[-1]) > 1}


class _SweptResult(AnalysisResult):
    """Base for results that sweep a single axis (frequency, time, or a DC parameter)."""

    def __init__(
        self,
        meta: dict,
        sweep_name: str,
        sweep: np.ndarray,
        signals: dict[str, np.ndarray],
    ) -> None:
        super().__init__(meta, signals)
        self._sweep_name = sweep_name
        self._sweep = sweep

    def __getitem__(self, name: str) -> np.ndarray:
        if name == self._sweep_name:
            return self._sweep
        return super().__getitem__(name)

    @property
    def names(self) -> tuple[str, ...]:
        return (self._sweep_name, *self._signals)


class OpResult(AnalysisResult):
    """Operating point result."""


class DcResult(_SweptResult):
    """DC sweep result: circuit variables swept over a netlist parameter."""

    @property
    def sweep(self) -> np.ndarray:
        return self._sweep

    @property
    def sweep_name(self) -> str:
        return self._sweep_name

    @property
    def parameters(self) -> dict[str, np.ndarray]:
        return {self._sweep_name: self._sweep}


class AcResult(_SweptResult):
    """AC small-signal analysis result: phasor signals swept over frequency."""

    @property
    def frequency(self) -> np.ndarray:
        return self._sweep


class TranResult(_SweptResult):
    """Transient analysis result: time-domain signals."""

    @property
    def time(self) -> np.ndarray:
        return self._sweep


class XfResult(_SweptResult):
    """Transfer function analysis result: small-signal transfer functions swept over frequency."""

    @property
    def frequency(self) -> np.ndarray:
        return self._sweep

    @property
    def transfer_functions(self) -> dict[str, np.ndarray]:
        return dict(self._signals)


class NoiseResult(_SweptResult):
    """Noise analysis result: noise spectral densities swept over frequency."""

    @property
    def frequency(self) -> np.ndarray:
        return self._sweep

    @property
    def output_noise(self) -> np.ndarray | None:
        return self._signals.get("out")

    @property
    def input_referred_noise(self) -> np.ndarray | None:
        return self._signals.get("in")

    @property
    def gain(self) -> np.ndarray | None:
        return self._signals.get("gain")

    @property
    def noise_figure(self) -> np.ndarray | None:
        return self._signals.get("NF")


class StbResult(_SweptResult):
    """Stability analysis result: loop gain swept over frequency, plus computed stability margins."""

    @property
    def frequency(self) -> np.ndarray:
        return self._sweep

    @property
    def loop_gain(self) -> np.ndarray | None:
        return next(iter(self._signals.values()), None)

    @property
    def phase_margin(self) -> float | None:
        return self._meta.get("phaseMargin")

    @property
    def phase_margin_frequency(self) -> float | None:
        return self._meta.get("phaseMarginFreq")

    @property
    def gain_margin(self) -> float | None:
        return self._meta.get("gainMargin")

    @property
    def gain_margin_frequency(self) -> float | None:
        return self._meta.get("gainMarginFreq")


class PzResult(AnalysisResult):
    """Pole-zero analysis result."""

    @property
    def poles(self) -> np.ndarray | None:
        vals = [complex(np.squeeze(v)) for k, v in self._signals.items() if "pole" in k.lower()]
        return np.array(vals) if vals else None

    @property
    def zeros(self) -> np.ndarray | None:
        vals = [complex(np.squeeze(v)) for k, v in self._signals.items() if "zero" in k.lower()]
        return np.array(vals) if vals else None


class GroupResult(Result):
    """Results produced by any ``Scope`` (Stage, Sweep, MonteCarlo, Corners).

    A group holds an ordered list of *runs*.  What a run represents depends on
    the scope: a Monte Carlo iteration, a sweep point, a corner, or (for
    ``Stage``) a single inner analysis.  Each run is a list of the inner
    analysis results in declaration order.

    Access:
      - integer index -> the run at that position
      - string label  -> the run with that label (when the scope assigns labels,
        e.g. corner labels or a Stage's inner-analysis names)

    For convenience, a run that contains a single result returns that result
    directly instead of a one-element list; ``items()`` yields ``(label, entry)``
    pairs and iteration yields entries in order.
    """

    def __init__(
        self,
        runs: Sequence[Sequence[AnalysisResult]],
        labels: Sequence[str] | None = None,
    ) -> None:
        self._runs: list[list[AnalysisResult]] = [list(r) for r in runs]
        self._labels: list[str] | None = list(labels) if labels is not None else None
        if self._labels is not None and len(self._labels) != len(self._runs):
            raise ValueError("GroupResult: number of labels must match number of runs")

    def _entry(self, idx: int) -> AnalysisResult | list[AnalysisResult]:
        run = self._runs[idx]
        return run[0] if len(run) == 1 else run

    def __len__(self) -> int:
        return len(self._runs)

    def __iter__(self) -> Iterator[Any]:
        for i in range(len(self._runs)):
            yield self._entry(i)

    def __getitem__(self, key: int | str) -> AnalysisResult | list[AnalysisResult]:
        if isinstance(key, str):
            if self._labels is None:
                raise KeyError(f"{key!r}: this group has no labels; index by position")
            idx = self._labels.index(key)
        else:
            idx = key
        return self._entry(idx)

    @property
    def labels(self) -> list[str]:
        """The run labels, or positional string indices when unlabeled."""
        if self._labels is not None:
            return list(self._labels)
        return [str(i) for i in range(len(self._runs))]

    @property
    def numruns(self) -> int:
        return len(self._runs)

    def items(self) -> Iterator[tuple[str, Any]]:
        """Iterate over ``(label, entry)`` pairs."""
        for i, label in enumerate(self.labels):
            yield label, self._entry(i)


class RunResult:
    """Everything produced by a single ``SpectreSession.run()`` call.

    Each top-level runnable contributes one entry, accessible by its ``name`` or
    by position::

        result["dc_nom"]      # by name
        result[0]             # by position
        result["pvt"]["ss"]   # nested scope access

    For a single-runnable run, attribute access is delegated to that result so
    ``result.frequency`` works without indexing.
    """

    def __init__(
        self,
        results: Sequence[Result],
        names: Sequence[str],
        completed: Any = None,
    ) -> None:
        self._results: list[Result] = list(results)
        self._names: list[str] = list(names)
        self.completed = completed

    def __len__(self) -> int:
        return len(self._results)

    def __iter__(self) -> Iterator[Result]:
        return iter(self._results)

    def __getitem__(self, key: int | str) -> Any:
        if isinstance(key, str):
            matches = [i for i, n in enumerate(self._names) if n == key]
            if not matches:
                raise KeyError(
                    f"{key!r}: no runnable with that name (have {self._names})"
                )
            if len(matches) > 1:
                raise KeyError(
                    f"{key!r}: ambiguous name shared by {len(matches)} runnables; index by position"
                )
            return self._results[matches[0]]
        return self._results[key]

    @property
    def names(self) -> list[str]:
        return list(self._names)

    def items(self) -> Iterator[tuple[str, Result]]:
        return zip(self._names, self._results)

    def __getattr__(self, name: str):
        results = self.__dict__.get("_results", [])
        if len(results) == 1:
            return getattr(results[0], name)
        raise AttributeError(
            f"'{type(self).__name__}' has no attribute '{name}'"
            f" (run produced {len(results)} results; index into the container first)"
        )
