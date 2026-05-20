# imports <<<
from __future__ import annotations

from collections.abc import Mapping, Sequence

from .base import Runnable, Simulation
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

# op analysis <<<
class OP(Simulation):
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
class DC(Simulation):
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
class AC(Simulation):
    """Small-signal AC analysis.
    """

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
class Tran(Simulation):
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
class XF(Simulation):
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
class Noise(Simulation):
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
class STB(Simulation):
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

class PZ(Simulation):
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

# sweep analysis <<<
class Sweep(Runnable):
    """Parametric sweep wrapper.

    Wraps one or more inner analyses and sweeps a parameter such as a circuit
    temperature or a top-level netlist parameter. Specify the sweep range via
    ``values`` (explicit list) or ``start`` + ``stop``.
    """

    def __init__(
        self,
        inner: Sequence[Simulation],
        param: str,
        name: str = "swp",
        values: Sequence[object] | None = None,
        start: object | None = None,
        stop: object | None = None,
        step: object | None = None,
        sweep_type: str = "lin",
        points: object | None = None,
        **params: object,
    ) -> None:
        if not inner:
            raise ValueError("Sweep requires at least one inner analysis")
        self.inner = tuple(inner)
        self.param = param
        self.name = name
        self.values = tuple(values) if values is not None else None
        self.start = start
        self.stop = stop
        self.step = step
        self.sweep_type = sweep_type
        self.points = points
        self.params = params
        if self.values is None and (self.start is None or self.stop is None):
            raise ValueError("Sweep requires either 'values' or 'start'+'stop'")
        if self.sweep_type not in {"lin", "dec", "log"}:
            raise ValueError("sweep_type must be one of: lin, dec, log")

    def build_command(self) -> str:
        header = f"{self.name} sweep param={self.param}"
        if self.values is not None:
            vals = " ".join(str(v) for v in self.values)
            header += f" values=[{vals}]"
        else:
            header += f" start={self.start} stop={self.stop}"
            if self.points is not None:
                header += f" {self.sweep_type}={self.points}"
            elif self.step is not None:
                header += f" step={self.step}"
        if self.params:
            header += " " + " ".join(f"{k}={v}" for k, v in self.params.items())
        inner_lines = "\n    ".join(s.build_command() for s in self.inner)
        return f"{header} {{\n    {inner_lines}\n}}"
# >>>

# montecarlo analysis <<<
class MonteCarlo(Runnable):
    """Monte Carlo analysis wrapping one or more inner analyses.

    A ``statistics`` block must appear earlier in the netlist to define
    the random-variable distributions. ``variations`` controls which
    distributions are sampled: ``all``, ``process``, or ``mismatch``.
    ``seed`` pins the random number generator for reproducibility.
    """

    _VALID_VARIATIONS = frozenset({"all", "process", "mismatch"})

    def __init__(
        self,
        inner: Sequence[Simulation],
        name: str = "mc",
        numruns: int = 100,
        variations: str = "all",
        seed: int | None = None,
        savefamilyplots: bool = True,
        **params: object,
    ) -> None:
        if variations not in self._VALID_VARIATIONS:
            raise ValueError(
                f"variations must be one of: {', '.join(sorted(self._VALID_VARIATIONS))}"
            )
        if not inner:
            raise ValueError("MonteCarlo requires at least one inner analysis")
        self.inner = tuple(inner)
        self.name = name
        self.numruns = numruns
        self.variations = variations
        self.seed = seed
        self.savefamilyplots = savefamilyplots
        self.params = params

    def build_command(self) -> str:
        parts = [
            f"{self.name} montecarlo",
            f"numruns={self.numruns}",
            f"variations={self.variations}",
        ]
        if self.seed is not None:
            parts.append(f"seed={self.seed}")
        parts.append(f"savefamilyplots={'yes' if self.savefamilyplots else 'no'}")
        parts.extend(f"{k}={v}" for k, v in self.params.items())
        header = " ".join(parts)
        inner_lines = "\n    ".join(s.build_command() for s in self.inner)
        return f"{header} {{\n    {inner_lines}\n}}"
# >>>

# corner analysis <<<
class Corner:
    """A single entry in a corners sweep: one PVT operating point.

    ``section`` is the named section to load from ``file``.
    ``temp`` optionally overrides the simulation temperature for this corner
    through an ``options`` statement inside the altergroup. ``parameters`` can
    be used for voltage corners when supply sources reference top-level
    parameters (for example ``parameters={"vdd": 0.9}``).

    The label used to index into ``CornersResult`` is ``section`` when neither
    voltage nor temperature is given, ``"<section>@<temp>"`` for temperature
    corners, or the explicit ``label`` when provided.
    """

    def __init__(
        self,
        section: str,
        file: str,
        temp: float | None = None,
        parameters: Mapping[str, object] | None = None,
        options: Mapping[str, object] | None = None,
        label: str | None = None,
    ) -> None:
        if not section:
            raise ValueError("Corner requires a non-empty section")
        if not file:
            raise ValueError("Corner requires a non-empty file")
        self.section = section
        self.file = file
        self.temp = temp
        self.parameters = dict(parameters) if parameters else {}
        self.options = dict(options) if options else {}
        if temp is not None:
            existing_temp = self.options.get("temp")
            if existing_temp is not None and existing_temp != temp:
                raise ValueError("Corner temp conflicts with options['temp']")
            self.options["temp"] = temp
        self._label = label

    @property
    def label(self) -> str:
        if self._label is not None:
            return self._label
        if self.temp is not None:
            return f"{self.section}@{int(self.temp)}"
        return self.section

    def build_lines(self, alter_name: str) -> list[str]:
        lines: list[str] = [f'include "{self.file}" section={self.section}']
        if self.parameters:
            params = " ".join(f"{k}={v}" for k, v in self.parameters.items())
            lines.append(f"parameters {params}")
        if self.options:
            opts = " ".join(f"{k}={v}" for k, v in self.options.items())
            lines.append(f"{alter_name}_opts options {opts}")
        return lines

    def build_line(self) -> str:
        """Return the include line for backward-compatible tests/debugging."""
        return f'    include "{self.file}" section={self.section}'


class Corners(Runnable):
    """Corners sweep: run inner analyses once per model library section.

    Spectre runs each ``Corner`` entry in sequence and writes PSF files
    named ``<name>_NNN_<inner_stem>``.  Results
    are returned as a ``CornersResult`` which supports both integer indexing
    and label-based access (``result["tt"]``, ``result["ss@85"]``, etc.).

    Process corners example::

        Corners(
            corners=[
                Corner("tt", f"{PDK_DIR}/cornerMOShv_psp.scs"),
                Corner("ss", f"{PDK_DIR}/cornerMOShv_psp.scs"),
                Corner("ff", f"{PDK_DIR}/cornerMOShv_psp.scs"),
                Corner("sf", f"{PDK_DIR}/cornerMOShv_psp.scs"),
                Corner("fs", f"{PDK_DIR}/cornerMOShv_psp.scs"),
            ],
            inner=[DC(param="vin", start=0, stop=1.0, step=0.005)],
        )

    PVT example (process + supply voltage + temperature)::

        Corners(
            corners=[
                Corner(
                    "tt",
                    model_file,
                    temp=27,
                    parameters={"vdd": 1.0},
                    label="tt_1v0_27c",
                ),
                Corner(
                    "ss",
                    model_file,
                    temp=125,
                    parameters={"vdd": 0.9},
                    label="ss_0v9_125c",
                ),
                Corner(
                    "ff",
                    model_file,
                    temp=-40,
                    parameters={"vdd": 1.1},
                    label="ff_1v1_m40c",
                ),
            ],
            inner=[DC(param="vin", start=0, stop=1.0, step=0.005)],
        )
    """

    def __init__(
        self,
        corners: Sequence[Corner],
        inner: Sequence[Simulation],
        name: str = "pvt",
    ) -> None:
        if not corners:
            raise ValueError("Corners requires at least one corner entry")
        if not inner:
            raise ValueError("Corners requires at least one inner analysis")
        self.corners = list(corners)
        self.inner = tuple(inner)
        self.name = name

    @property
    def labels(self) -> list[str]:
        return [c.label for c in self.corners]

    def build_command(self) -> str:
        blocks: list[str] = []
        for i, corner in enumerate(self.corners):
            alter_name = f"{self.name}_alter_{i:03d}"
            alt_body = "\n    ".join(corner.build_lines(alter_name))
            blocks.append(f"{alter_name} altergroup {{\n    {alt_body}\n}}")
            for inner in self.inner:
                cmd = inner.build_command()
                prefixed_name = f"{self.name}_{i:03d}_{inner.name}"
                blocks.append(prefixed_name + cmd[len(inner.name) :])
        return "\n".join(blocks)
# >>>
