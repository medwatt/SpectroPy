# imports <<<
from __future__ import annotations

from collections.abc import Mapping

from .base import Statement
# >>>


class Alter(Statement):
    """Mutates a single parameter in-place for analyses that follow in the deck.

    Targets:
      - temperature or a top-level parameter: omit dev/mod/sub
      - device instance parameter: dev=<instance_name>
      - model parameter: mod=<model_name>
      - subcircuit instance parameter: sub=<subcircuit_instance_name>
    """

    def __init__(
        self,
        name: str,
        param: str,
        value: object,
        dev: str | None = None,
        mod: str | None = None,
        sub: str | None = None,
    ) -> None:
        targets = [x for x in (dev, mod, sub) if x is not None]
        if len(targets) > 1:
            raise ValueError("Alter accepts at most one of: dev, mod, sub")
        self.name = name
        self.param = param
        self.value = value
        self.dev = dev
        self.mod = mod
        self.sub = sub

    def build_command(self) -> str:
        parts = [f"{self.name} alter"]
        if self.dev is not None:
            parts.append(f"dev={self.dev}")
        elif self.mod is not None:
            parts.append(f"mod={self.mod}")
        elif self.sub is not None:
            parts.append(f"sub={self.sub}")
        parts.append(f"param={self.param}")
        parts.append(f"value={self.value}")
        return " ".join(parts)


class AlterGroup(Statement):
    """Replaces a coherent set of model, instance, parameter, and option
    definitions for analyses that follow in the deck.

    Structured arguments are rendered first in this order:
      1. ``parameters`` dict  →  ``parameters k=v ...``
      2. ``options`` dict     →  ``<name>_opts options k=v ...``
      3. ``raw`` list         →  verbatim Spectre lines (escape hatch for model and instance statements)

    Allowed block content: parameters, options, model, and instance
    statements. Analyses, save, export, sens, and paramset are not valid
    inside an altergroup; Spectre enforces this at run time.
    """

    def __init__(
        self,
        name: str,
        parameters: Mapping[str, object] | None = None,
        options: Mapping[str, object] | None = None,
        raw: list[str] | None = None,
    ) -> None:
        if not name:
            raise ValueError("AlterGroup requires a non-empty name")
        self.name = name
        self.parameters = dict(parameters) if parameters else {}
        self.options = dict(options) if options else {}
        self.raw = list(raw) if raw else []

    def build_command(self) -> str:
        lines: list[str] = []
        if self.parameters:
            kv = " ".join(f"{k}={v}" for k, v in self.parameters.items())
            lines.append(f"parameters {kv}")
        if self.options:
            kv = " ".join(f"{k}={v}" for k, v in self.options.items())
            lines.append(f"{self.name}_opts options {kv}")
        lines.extend(self.raw)
        if not lines:
            return f"{self.name} altergroup {{}}"
        body = "\n    ".join(lines)
        return f"{self.name} altergroup {{\n    {body}\n}}"


class Vary:
    """A ``vary`` statement for use inside a statistics process or mismatch block.

    Exactly one of ``std`` or ``N`` must be supplied.
    ``percent=True`` emits ``percent=yes``; ``percent=False`` emits ``percent=no``.
    """

    _VALID_DISTS = frozenset({"gauss", "lnorm", "unif"})

    def __init__(
        self,
        param: str,
        dist: str,
        std: object | None = None,
        N: object | None = None,
        percent: bool | None = None,
    ) -> None:
        if dist not in self._VALID_DISTS:
            raise ValueError(f"dist must be one of: {', '.join(sorted(self._VALID_DISTS))}")
        if std is None and N is None:
            raise ValueError("Vary requires either std or N")
        if std is not None and N is not None:
            raise ValueError("Vary accepts either std or N, not both")
        self.param = param
        self.dist = dist
        self.std = std
        self.N = N
        self.percent = percent

    def build_line(self) -> str:
        parts = [f"vary {self.param}", f"dist={self.dist}"]
        if self.std is not None:
            parts.append(f"std={self.std}")
        else:
            parts.append(f"N={self.N}")
        if self.percent is not None:
            parts.append(f"percent={'yes' if self.percent else 'no'}")
        return " ".join(parts)

    def __str__(self) -> str:
        return self.build_line()


class Correlate:
    """A ``correlate`` statement for use inside a statistics block.

    Process-level (no ``dev``):
        ``correlate param=[p1 p2] cc=0.6``

    Instance-level (with ``dev``):
        ``correlate dev=[m1 m2] param=[p1 p2] cc=0.8``

    ``dev`` wildcards (``*``) are passed through unchanged.
    """

    def __init__(
        self,
        cc: float,
        param: list[str] | None = None,
        dev: list[str] | None = None,
    ) -> None:
        if not -1.0 <= float(cc) <= 1.0:
            raise ValueError("cc must be between -1 and 1")
        self.cc = cc
        self.param = list(param) if param else []
        self.dev = list(dev) if dev else []

    def build_line(self) -> str:
        parts = ["correlate"]
        if self.dev:
            parts.append(f"dev=[{' '.join(self.dev)}]")
        if self.param:
            parts.append(f"param=[{' '.join(self.param)}]")
        parts.append(f"cc={self.cc}")
        return " ".join(parts)

    def __str__(self) -> str:
        return self.build_line()


class Statistics(Statement):
    """Defines random-variable distributions consumed by Monte Carlo,
    dcmatch, and acmatch analyses.

    ``process`` variations are sampled once per Monte Carlo iteration.
    ``mismatch`` variations are sampled per subcircuit instance.
    ``correlate`` statements live at the top level of the block.
    ``truncate`` sets the default sigma cutoff for the whole block.
    ``process_truncate`` and ``mismatch_truncate`` set per-sub-block cutoffs.
    """

    def __init__(
        self,
        process: list[Vary] | None = None,
        mismatch: list[Vary] | None = None,
        correlate: list[Correlate] | None = None,
        truncate: object | None = None,
        process_truncate: object | None = None,
        mismatch_truncate: object | None = None,
    ) -> None:
        self.process = list(process) if process else []
        self.mismatch = list(mismatch) if mismatch else []
        self.correlate = list(correlate) if correlate else []
        self.truncate = truncate
        self.process_truncate = process_truncate
        self.mismatch_truncate = mismatch_truncate

    def _sub_block(
        self, keyword: str, vary_list: list[Vary], block_truncate: object | None
    ) -> list[str]:
        lines = [f"    {keyword} {{"]
        for v in vary_list:
            lines.append(f"        {v.build_line()}")
        if block_truncate is not None:
            lines.append(f"        truncate tr={block_truncate}")
        lines.append("    }")
        return lines

    def build_command(self) -> str:
        lines: list[str] = []

        if self.process or self.process_truncate is not None:
            lines.extend(self._sub_block("process", self.process, self.process_truncate))

        if self.mismatch or self.mismatch_truncate is not None:
            lines.extend(self._sub_block("mismatch", self.mismatch, self.mismatch_truncate))

        for c in self.correlate:
            lines.append(f"    {c.build_line()}")

        if self.truncate is not None:
            lines.append(f"    truncate tr={self.truncate}")

        if not lines:
            return "statistics {}"

        return "statistics {\n" + "\n".join(lines) + "\n}"
