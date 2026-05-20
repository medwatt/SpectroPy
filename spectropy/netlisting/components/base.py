# imports <<<
from __future__ import annotations
from dataclasses import dataclass, field
# >>>


def _join_kv(items: dict[str, object]) -> str:
    return " ".join(f"{k}={v}" for k, v in items.items())


@dataclass(slots=True)
class Component:
    id: str
    nodes: tuple[str, ...]
    spice_prefix: str
    master: str
    params: dict[str, object] = field(default_factory=dict)

    def __str__(self) -> str:
        parts = [f"{self.spice_prefix}{self.id}", f"({' '.join(self.nodes)})", self.master]
        if self.params:
            parts.append(_join_kv(self.params))
        return " ".join(parts)


@dataclass(slots=True)
class TwoPortComponent:
    """Spectre component with two separate node groups (e.g. dependent sources). """

    id: str
    out_nodes: tuple[str, ...]
    ctrl_nodes: tuple[str, ...]
    spice_prefix: str
    master: str
    params: dict[str, object] = field(default_factory=dict)

    def __str__(self) -> str:
        out = f"({' '.join(self.out_nodes)})"
        ctrl = f"({' '.join(self.ctrl_nodes)})"
        parts = [f"{self.spice_prefix}{self.id}", out + ctrl, self.master]
        if self.params:
            parts.append(_join_kv(self.params))
        return " ".join(parts)


class SubCircuitInstance:
    """Spectre subcircuit instance (X element). """

    def __init__(
        self,
        id: str,
        nodes: tuple[str, ...],
        subcircuit: object,
        copy: bool = False,
        params: dict[str, object] | None = None,
    ) -> None:
        self.id = id
        self.nodes = nodes
        self.subcircuit = subcircuit
        self.copy = copy
        self.params = params or {}

    @property
    def spice_prefix(self) -> str:
        return "X"

    def __str__(self) -> str:
        subckt_name = getattr(self.subcircuit, "name", str(self.subcircuit))
        if self.copy:
            subckt_name = f"{subckt_name}_{self.id}"
        parts = [f"X{self.id}", f"({' '.join(self.nodes)})", subckt_name]
        if self.params:
            parts.append(_join_kv(self.params))
        return " ".join(parts)
