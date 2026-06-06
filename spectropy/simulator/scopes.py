# imports <<<
from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path

from .base import Runnable, Scope
from .results import GroupResult
from .statements import Alter, AlterGroup, Statistics
from . import collection
# >>>

# stage <<<
class Stage(Scope):
    """Apply control statements, then run inner analyses under the mutated deck.

    A ``Stage`` emits each ``setup`` statement (``Alter`` / ``AlterGroup``) and
    then each inner runnable. Its result is a ``GroupResult`` keyed by each inner
    runnable's ``name``.

    Sequencing, not isolation: Spectre's ``alter`` is sticky -- it mutates global
    deck state for everything that follows until overwritten.  A ``Stage`` groups
    emission for clarity and 1:1 result mapping; it does **not** reset state
    afterwards.  For isolated scenarios, make each stage self-contained (set
    everything it depends on) or use ``Corners``.

    Inner analyses across stages share the global netlist namespace, so give
    them distinct names to avoid colliding on PSF output filenames.
    """

    def __init__(
        self,
        inner: Sequence[Runnable],
        setup: Sequence[Alter | AlterGroup] = (),
        name: str = "stage",
    ) -> None:
        if not inner:
            raise ValueError("Stage requires at least one inner runnable")
        self.inner = tuple(inner)
        self.setup = tuple(setup)
        self.name = name

    def build_command(self) -> str:
        lines = [s.build_command() for s in self.setup]
        lines.extend(r.build_command() for r in self.inner)
        return "\n".join(lines)

    def collect(self, raw_dir: Path) -> GroupResult:
        runs = [[r.collect(raw_dir)] for r in self.inner]
        return GroupResult(runs, labels=[r.name for r in self.inner])


# >>>

# sweep <<<
class Sweep(Scope):
    """Parametric sweep wrapper.

    Wraps one or more inner analyses and sweeps a parameter such as a circuit
    temperature or a top-level netlist parameter. Specify the sweep range via
    ``values`` (explicit list) or ``start`` + ``stop``.
    """

    def __init__(
        self,
        inner: Sequence[Runnable],
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

    def collect(self, raw_dir: Path) -> GroupResult:
        labels = [str(v) for v in self.values] if self.values is not None else None
        return collection.grouped_result(raw_dir, self.name, self.inner, ("-",), labels)


# >>>

# montecarlo <<<
class MonteCarlo(Scope):
    """Monte Carlo analysis wrapping one or more inner analyses.

    Pass the random-variable distributions directly via ``statistics``; the
    ``statistics { … }`` block is emitted immediately before the
    ``montecarlo { … }`` block that consumes it.  ``variations`` controls which
    distributions are sampled: ``all``, ``process``, or ``mismatch``.  ``seed``
    pins the random number generator for reproducibility.
    """

    _VALID_VARIATIONS = frozenset({"all", "process", "mismatch"})

    def __init__(
        self,
        inner: Sequence[Runnable],
        statistics: Statistics | None = None,
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
        self.statistics = statistics
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
        block = f"{header} {{\n    {inner_lines}\n}}"
        if self.statistics is not None:
            return f"{self.statistics.build_command()}\n{block}"
        return block

    def collect(self, raw_dir: Path) -> GroupResult:
        return collection.grouped_result(raw_dir, self.name, self.inner, ("-",))


# >>>

# corners <<<
class Corner:
    """A single entry in a corners sweep: one PVT operating point.

    ``section`` is the named section to load from ``file``.
    ``temp`` optionally overrides the simulation temperature for this corner
    through an ``options`` statement inside the altergroup. ``parameters`` can
    be used for voltage corners when supply sources reference top-level
    parameters (for example ``parameters={"vdd": 0.9}``).

    The label used to index into the corner ``GroupResult`` is ``section`` when
    neither voltage nor temperature is given, ``"<section>@<temp>"`` for
    temperature corners, or the explicit ``label`` when provided.
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


class Corners(Scope):
    """Corners sweep: run inner analyses once per model library section.

    Spectre runs each ``Corner`` entry in sequence and writes PSF files named
    ``<name>_NNN_<inner_stem>``.  Results are returned as a ``GroupResult`` which
    supports both integer indexing and label-based access (``result["tt"]``,
    ``result["ss@85"]``, etc.).

    Process corners example::

        Corners(
            corners=[
                Corner("tt", f"{PDK_DIR}/cornerMOShv_psp.scs"),
                Corner("ss", f"{PDK_DIR}/cornerMOShv_psp.scs"),
                Corner("ff", f"{PDK_DIR}/cornerMOShv_psp.scs"),
            ],
            inner=[DC(param="vin", start=0, stop=1.0, step=0.005)],
        )

    PVT example (process + supply voltage + temperature)::

        Corners(
            corners=[
                Corner("tt", model_file, temp=27, parameters={"vdd": 1.0}, label="tt_1v0_27c"),
                Corner("ss", model_file, temp=125, parameters={"vdd": 0.9}, label="ss_0v9_125c"),
                Corner("ff", model_file, temp=-40, parameters={"vdd": 1.1}, label="ff_1v1_m40c"),
            ],
            inner=[DC(param="vin", start=0, stop=1.0, step=0.005)],
        )
    """

    def __init__(
        self,
        corners: Sequence[Corner],
        inner: Sequence[Runnable],
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

    def collect(self, raw_dir: Path) -> GroupResult:
        return collection.grouped_result(raw_dir, self.name, self.inner, ("_", "-"), self.labels)


# >>>
