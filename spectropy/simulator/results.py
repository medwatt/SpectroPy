# imports <<<
from __future__ import annotations
from collections.abc import Iterator, Sequence
from typing import Any
import numpy as np
# >>>


class AnalysisResult:
    """Shared base class for all results returned by a single runnable.

    Provides a common type for containers that may hold either a
    ``SpectreResult`` (swept/point analyses) or a ``MonteCarloResult``.
    """


class SpectreResult(AnalysisResult):
    """Base for all Spectre analysis results."""

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


class _SweptResult(SpectreResult):
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


class OpResult(SpectreResult):
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


class PzResult(SpectreResult):
    """Pole-zero analysis result."""

    @property
    def poles(self) -> np.ndarray | None:
        vals = [complex(np.squeeze(v)) for k, v in self._signals.items() if "pole" in k.lower()]
        return np.array(vals) if vals else None

    @property
    def zeros(self) -> np.ndarray | None:
        vals = [complex(np.squeeze(v)) for k, v in self._signals.items() if "zero" in k.lower()]
        return np.array(vals) if vals else None


class _IndexedRunResult(AnalysisResult):
    """Shared base for result containers that hold one list-of-lists per run."""

    def __init__(self, runs: Sequence[Sequence[SpectreResult]]) -> None:
        self._runs: list[list[SpectreResult]] = [list(r) for r in runs]

    def __len__(self) -> int:
        return len(self._runs)

    def __iter__(self):
        for run in self._runs:
            yield run[0] if len(run) == 1 else run

    def _get_run(self, idx: int) -> SpectreResult | list[SpectreResult]:
        run = self._runs[idx]
        return run[0] if len(run) == 1 else run


class SweepPointResult(AnalysisResult):
    """One parameter-sweep point containing multiple child analysis results."""

    def __init__(self, results: Sequence[SpectreResult]) -> None:
        self._results: list[SpectreResult] = list(results)

    def __len__(self) -> int:
        return len(self._results)

    def __iter__(self) -> Iterator[SpectreResult]:
        return iter(self._results)

    def __getitem__(self, index: int) -> SpectreResult:
        return self._results[index]


class MonteCarloResult(_IndexedRunResult):
    """Results from a Monte Carlo analysis.

    Indexing and iteration: if the MonteCarlo had a single inner analysis,
    ``result[run_idx]`` returns the ``SpectreResult`` for that run directly.
    With multiple inner analyses, ``result[run_idx]`` returns a
    ``list[SpectreResult]`` in inner-analysis declaration order.
    """

    def __getitem__(self, idx: int) -> SpectreResult | list[SpectreResult]:
        return self._get_run(idx)

    @property
    def numruns(self) -> int:
        return len(self._runs)


class CornersResult(_IndexedRunResult):
    """Results from a corners sweep.

    Corners can be accessed by integer index or by label (the section name,
    or ``"<section>@<temp>"`` when a temperature was specified).

    With a single inner analysis, ``result[key]`` returns the
    ``SpectreResult`` directly.  With multiple inner analyses it returns a
    ``list[SpectreResult]`` in declaration order.

    ``result.items()`` iterates over ``(label, result)`` pairs.
    """

    def __init__(
        self,
        labels: Sequence[str],
        runs: Sequence[Sequence[SpectreResult]],
    ) -> None:
        super().__init__(runs)
        self._labels: list[str] = list(labels)

    def __getitem__(self, key: int | str) -> SpectreResult | list[SpectreResult]:
        idx = self._labels.index(key) if isinstance(key, str) else key
        return self._get_run(idx)

    @property
    def labels(self) -> list[str]:
        return list(self._labels)

    def items(self):
        """Iterate over ``(label, result)`` pairs."""
        for label, run in zip(self._labels, self._runs):
            yield label, (run[0] if len(run) == 1 else run)


class SpectreRunResult:
    """Container for one or more Spectre results from a single run.

    For a single-analysis run, attributes are delegated to the result directly,
    so ``result.frequency`` works without indexing. For multi-analysis runs,
    index into the container: ``result[0]``, ``result[1]``, etc.
    """

    def __init__(self, results: list[AnalysisResult], completed=None) -> None:
        self._results = results
        self.completed = completed

    def __len__(self) -> int:
        return len(self._results)

    def __iter__(self) -> Iterator[AnalysisResult]:
        return iter(self._results)

    def __getitem__(self, index: int) -> Any:
        return self._results[index]

    def __getattr__(self, name: str):
        results = self.__dict__.get("_results", [])
        if len(results) == 1:
            return getattr(results[0], name)
        raise AttributeError(
            f"'{type(self).__name__}' has no attribute '{name}'"
            f" (run produced {len(results)} results; index into the container first)"
        )
