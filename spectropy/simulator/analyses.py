# imports <<<
from __future__ import annotations

from .base import Runnable, Analysis, Scope
from .scopes import Stage, Sweep, MonteCarlo, Corner, Corners
from .statements import Alter, AlterGroup, Vary, Correlate, Statistics
from .results import (
    OpResult,
    DcResult,
    AcResult,
    TranResult,
    XfResult,
    NoiseResult,
    StbResult,
    PzResult,
)
# >>>

# This module doubles as the public ``analyses`` namespace: it defines the leaf
# analyses (OP, DC, …) and re-exports the scopes (Stage, Sweep, MonteCarlo,
# Corners) and the configuration objects (Alter, Statistics, …) that they
# consume, so user code can reach everything through ``analyses.<Name>``.


# op analysis <<<
class OP(Analysis):
    """
    Operating-point analysis.
    """

    def __init__(self, name: str = "OpPoint", **params: object) -> None:
        self.name = name
        self.params = params

    @property
    def psf_stem(self) -> str:
        return f"{self.name}.dc"

    def build_command(self) -> str:
        parts = [f"{self.name} dc"]
        parts.extend(f"{k}={v}" for k, v in self.params.items())
        return " ".join(parts)

    def make_result(self, meta, sweep_name, sweep, signals) -> OpResult:
        return OpResult(meta=meta, signals=signals)


# >>>


# dc analysis <<<
class DC(Analysis):
    """DC sweep analysis.

    Use ``param`` to sweep a circuit, instance, model, or subcircuit
    parameter. The common temperature sweep is ``param='temp'``.
    """

    def __init__(
        self,
        param: str,
        start: object,
        stop: object,
        step: object,
        name: str = "dcswp",
        **params: object,
    ) -> None:
        self.param = param
        self.start = start
        self.stop = stop
        self.step = step
        self.name = name
        self.params = params

    @property
    def psf_stem(self) -> str:
        return f"{self.name}.dc"

    def build_command(self) -> str:
        parts = [
            f"{self.name} dc",
            f"param={self.param}",
            f"start={self.start}",
            f"stop={self.stop}",
            f"step={self.step}",
        ]
        parts.extend(f"{k}={v}" for k, v in self.params.items())
        return " ".join(parts)

    def make_result(self, meta, sweep_name, sweep, signals) -> DcResult:
        return DcResult(
            meta=meta,
            sweep_name=sweep_name or "",
            sweep=self._sweep_array(sweep),
            signals=signals,
        )


# >>>


# ac analysis <<<
class AC(Analysis):
    """Small-signal AC analysis."""

    def __init__(
        self,
        name: str = "analAC",
        start: object = "1",
        stop: object = "1e6",
        sweep_type: str = "dec",
        points: object = 10,
        **params: object,
    ) -> None:
        if sweep_type not in {"dec", "lin", "oct"}:
            raise ValueError("sweep_type must be one of: dec, lin, oct")
        self.name = name
        self.start = start
        self.stop = stop
        self.sweep_type = sweep_type
        self.points = points
        self.params = params

    @property
    def psf_stem(self) -> str:
        return f"{self.name}.ac"

    def build_command(self) -> str:
        parts = [
            f"{self.name} ac",
            f"start={self.start}",
            f"stop={self.stop}",
            f"{self.sweep_type}={self.points}",
        ]
        parts.extend(f"{k}={v}" for k, v in self.params.items())
        return " ".join(parts)

    def make_result(self, meta, sweep_name, sweep, signals) -> AcResult:
        return AcResult(
            meta=meta,
            sweep_name=sweep_name or "",
            sweep=self._sweep_array(sweep),
            signals=signals,
        )


# >>>


# transient analysis <<<
class Tran(Analysis):
    """Transient analysis.

    ``stop`` and ``step`` are required. Common options include ``start``,
    ``maxstep``, ``outputstart``, ``autostop``, ``skipdc``, ``ic``,
    ``readic``, ``useprevic``, ``linearic``, ``method``, and ``errpreset``.
    """

    def __init__(
        self,
        name: str = "analTran",
        stop: object = "1",
        step: object = "1",
        start: object | None = None,
        maxstep: object | None = None,
        uic: bool = False,
        **params: object,
    ) -> None:
        self.name = name
        self.stop = stop
        self.step = step
        self.start = start
        self.maxstep = maxstep
        self.uic = uic
        self.params = params

    @property
    def psf_stem(self) -> str:
        return f"{self.name}.tran"

    def build_command(self) -> str:
        parts = [f"{self.name} tran", f"stop={self.stop}", f"step={self.step}"]
        if self.start is not None:
            parts.append(f"start={self.start}")
        if self.maxstep is not None:
            parts.append(f"maxstep={self.maxstep}")
        if self.uic:
            parts.append("uic=yes")
        parts.extend(f"{k}={v}" for k, v in self.params.items())
        return " ".join(parts)

    def make_result(self, meta, sweep_name, sweep, signals) -> TranResult:
        return TranResult(
            meta=meta,
            sweep_name=sweep_name or "",
            sweep=self._sweep_array(sweep),
            signals=signals,
        )


# >>>


# transfer-function analysis <<<
class XF(Analysis):
    """Small-signal transfer-function analysis.

    This sweeps frequency around the DC operating point. Use
    ``probe`` to select the driving source or ``stimuli='nodes_and_terminals'``
    to work with node/terminal stimuli.
    """

    def __init__(
        self,
        start: object = "1",
        stop: object = "1e9",
        sweep_type: str = "dec",
        points: object = 10,
        name: str = "analXF",
        output_pos: str | None = None,
        output_neg: str = "0",
        probe: str | None = None,
        stimuli: str = "sources",
        **params: object,
    ) -> None:
        if sweep_type not in {"dec", "lin", "log"}:
            raise ValueError("sweep_type must be one of: dec, lin, log")
        if stimuli not in {"sources", "nodes_and_terminals"}:
            raise ValueError("stimuli must be 'sources' or 'nodes_and_terminals'")
        self.start = start
        self.stop = stop
        self.sweep_type = sweep_type
        self.points = points
        self.name = name
        self.output_pos = output_pos
        self.output_neg = output_neg
        self.probe = probe
        self.stimuli = stimuli
        self.params = params

    @property
    def psf_stem(self) -> str:
        return f"{self.name}.xf"

    def build_command(self) -> str:
        node_str = f" ({self.output_pos} {self.output_neg})" if self.output_pos is not None else ""
        parts = [
            f"{self.name}{node_str}",
            "xf",
            f"start={self.start}",
            f"stop={self.stop}",
            f"{self.sweep_type}={self.points}",
        ]
        if self.probe is not None:
            parts.append(f"probe={self.probe}")
        if self.stimuli != "sources":
            parts.append(f"stimuli={self.stimuli}")
        parts.extend(f"{k}={v}" for k, v in self.params.items())
        return " ".join(parts)

    def make_result(self, meta, sweep_name, sweep, signals) -> XfResult:
        return XfResult(
            meta=meta,
            sweep_name=sweep_name or "",
            sweep=self._sweep_array(sweep),
            signals=signals,
        )


# >>>


# noise analysis <<<
class Noise(Analysis):
    """Small-signal noise analysis.

    Specify the output with ``output_pos``/``output_neg`` or use ``oprobe``
    and ``iprobe`` for probe-based noise setup.
    """

    def __init__(
        self,
        start: object = "1",
        stop: object = "1e9",
        sweep_type: str = "dec",
        points: object = 10,
        name: str = "analNoise",
        output_pos: str | None = None,
        output_neg: str = "0",
        oprobe: str | None = None,
        iprobe: str | None = None,
        **params: object,
    ) -> None:
        if sweep_type not in {"dec", "lin", "log"}:
            raise ValueError("sweep_type must be one of: dec, lin, log")
        self.start = start
        self.stop = stop
        self.sweep_type = sweep_type
        self.points = points
        self.name = name
        self.output_pos = output_pos
        self.output_neg = output_neg
        self.oprobe = oprobe
        self.iprobe = iprobe
        self.params = params

    @property
    def psf_stem(self) -> str:
        return f"{self.name}.noise"

    def build_command(self) -> str:
        node_str = f" ({self.output_pos} {self.output_neg})" if self.output_pos is not None else ""
        parts = [
            f"{self.name}{node_str}",
            "noise",
            f"start={self.start}",
            f"stop={self.stop}",
            f"{self.sweep_type}={self.points}",
        ]
        if self.oprobe is not None:
            parts.append(f"oprobe={self.oprobe}")
        if self.iprobe is not None:
            parts.append(f"iprobe={self.iprobe}")
        parts.extend(f"{k}={v}" for k, v in self.params.items())
        return " ".join(parts)

    def make_result(self, meta, sweep_name, sweep, signals) -> NoiseResult:
        return NoiseResult(
            meta=meta,
            sweep_name=sweep_name or "",
            sweep=self._sweep_array(sweep),
            signals=signals,
        )


# >>>


# stability analysis <<<
class STB(Analysis):
    """Small-signal stability analysis using Middlebrook's method.

    ``probe`` identifies the loop-breaking probe.
    """

    def __init__(
        self,
        probe: str,
        start: object = "1",
        stop: object = "1e9",
        sweep_type: str = "dec",
        points: object = 10,
        name: str = "analSTB",
        **params: object,
    ) -> None:
        if sweep_type not in {"dec", "lin", "log"}:
            raise ValueError("sweep_type must be one of: dec, lin, log")
        self.probe = probe
        self.start = start
        self.stop = stop
        self.sweep_type = sweep_type
        self.points = points
        self.name = name
        self.params = params

    @property
    def psf_stem(self) -> str:
        return f"{self.name}.stb"

    @property
    def margin_psf_stem(self) -> str:
        return f"{self.name}.margin.stb"

    def build_command(self) -> str:
        parts = [
            f"{self.name} stb",
            f"start={self.start}",
            f"stop={self.stop}",
            f"{self.sweep_type}={self.points}",
            f"probe={self.probe}",
        ]
        parts.extend(f"{k}={v}" for k, v in self.params.items())
        return " ".join(parts)

    def make_result(self, meta, sweep_name, sweep, signals) -> StbResult:
        return StbResult(
            meta=meta,
            sweep_name=sweep_name or "",
            sweep=self._sweep_array(sweep),
            signals=signals,
        )


# >>>


# pz analysis <<<
class PZ(Analysis):
    """Pole-zero analysis.

    Use ``output_pos``/``output_neg`` for node-based PZ, or ``iprobe`` and
    ``oprobe`` for probe-based setups. ``zeroonly=True`` computes only zeros.
    """

    def __init__(
        self,
        name: str = "analPZ",
        output_pos: str | None = None,
        output_neg: str = "0",
        iprobe: str | None = None,
        oprobe: str | None = None,
        fmax: object | None = None,
        zeroonly: bool = False,
        **params: object,
    ) -> None:
        self.name = name
        self.output_pos = output_pos
        self.output_neg = output_neg
        self.iprobe = iprobe
        self.oprobe = oprobe
        self.fmax = fmax
        self.zeroonly = zeroonly
        self.params = params

    @property
    def psf_stem(self) -> str:
        return f"{self.name}.pz"

    def build_command(self) -> str:
        node_str = f" ({self.output_pos} {self.output_neg})" if self.output_pos is not None else ""
        parts = [f"{self.name}{node_str}", "pz"]
        if self.iprobe is not None:
            parts.append(f"iprobe={self.iprobe}")
        if self.oprobe is not None:
            parts.append(f"oprobe={self.oprobe}")
        if self.fmax is not None:
            parts.append(f"fmax={self.fmax}")
        if self.zeroonly:
            parts.append("zeroonly=yes")
        parts.extend(f"{k}={v}" for k, v in self.params.items())
        return " ".join(parts)

    def make_result(self, meta, sweep_name, sweep, signals) -> PzResult:
        return PzResult(meta=meta, signals=signals)


# >>>


__all__ = [
    # base
    "Runnable",
    "Analysis",
    "Scope",
    # analyses
    "OP",
    "DC",
    "AC",
    "Tran",
    "XF",
    "Noise",
    "STB",
    "PZ",
    # scopes
    "Stage",
    "Sweep",
    "MonteCarlo",
    "Corner",
    "Corners",
    # configuration objects
    "Alter",
    "AlterGroup",
    "Vary",
    "Correlate",
    "Statistics",
]
