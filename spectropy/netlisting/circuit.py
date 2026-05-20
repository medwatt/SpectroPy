# imports <<<
from __future__ import annotations
import copy
from .components.base import SubCircuitInstance, _join_kv
# >>>


class Circuit:

    # component methods <<<
    from .components.passive import R, C, L
    from .components.sources import (
        V, I,
        VoltageSin, CurrentSin,
        VoltagePulse, CurrentPulse,
        VoltagePWL, CurrentPWL,
        G, E, F, H, B,
    )
    from .components.switch import S
    from .components.semiconductors import M, Q, D
    from .components.instance import X, va
    # >>>

    def __init__(self, title: str = "Default Circuit") -> None:
        self.title = title
        self.components = []
        self.subcircuits = {}
        self.includes = []
        self.global_defs = []
        self.param_defs = []
        self.option_defs = []
        self._option_index = 0
        self.models = []
        self.save_signals = []
        self.initial_conditions = []
        self.nodesets = []
        self.raw_spice_commands = []
        self.used_ids = {}

    # control <<<
    def include(self, path: str, section: str | None = None) -> None:
        if section is None:
            self.includes.append(f'include "{path}"')
        else:
            self.includes.append(f'include "{path}" section={section}')

    def ahdl_include(self, path: str) -> None:
        self.includes.append(f'ahdl_include "{path}"')

    def global_nodes(self, *nodes: str) -> None:
        self.global_defs.append("global " + " ".join(nodes))

    def parameters(self, **params: object) -> None:
        self.param_defs.append("parameters " + _join_kv(params))

    def options(self, **params: object) -> None:
        if not params:
            return
        self._option_index += 1
        self.option_defs.append(f"o{self._option_index} options " + _join_kv(params))

    def temperature(self, temp: object) -> None:
        """Set the simulator temperature through an options statement."""
        self.options(temp=temp)

    def model(self, name: str, master: str, params: dict[str, object] | None = None, **kwargs: object) -> None:
        all_params = {**(params or {}), **kwargs}
        line = f"model {name} {master}"
        if all_params:
            line += " " + _join_kv(all_params)
        self.models.append(line)

    def save(self, *signals: str) -> None:
        self.save_signals.append("save " + " ".join(signals))

    def ic(self, **conditions: object) -> None:
        self.initial_conditions.append("ic " + _join_kv(conditions))

    def nodeset(self, **conditions: object) -> None:
        self.nodesets.append("nodeset " + _join_kv(conditions))

    def raw(self, line: str) -> None:
        self.raw_spice_commands.append(line)
    # >>>

    # build <<<
    def _check_id(self, prefix: str, id: str) -> None:
        if prefix not in self.used_ids:
            self.used_ids[prefix] = set()
        if id in self.used_ids[prefix]:
            raise ValueError(
                f"Identifier '{id}' is already used for component type '{prefix}'."
            )
        self.used_ids[prefix].add(id)

    def _add_component(self, component) -> None:
        self._check_id(component.spice_prefix, component.id)
        self.components.append(component)
        if isinstance(component, SubCircuitInstance):
            subckt = component.subcircuit
            if component.copy and isinstance(subckt, SubCircuit):
                subckt = subckt.copy(component.id)
            if isinstance(subckt, SubCircuit) and subckt.name not in self.subcircuits:
                self.subcircuits[subckt.name] = subckt
    # >>>

    # netlist <<<
    def _extend_lines(self, lines: list[str]) -> None:
        lines.extend(self.includes)
        lines.extend(self.option_defs)
        lines.extend(self.global_defs)
        lines.extend(self.param_defs)
        lines.extend(self.models)
        for component in self.components:
            lines.append(str(component))
        lines.extend(self.save_signals)
        lines.extend(self.initial_conditions)
        lines.extend(self.nodesets)
        lines.extend(self.raw_spice_commands)

    def get_netlist(self) -> list[str]:
        lines = ["simulator lang=spectre", f"// {self.title}"]
        for subckt in self.subcircuits.values():
            lines.extend(subckt.get_netlist())
        self._extend_lines(lines)
        return lines

    def __str__(self) -> str:
        return "\n".join(self.get_netlist())
    # >>>


class SubCircuit(Circuit):
    def __init__(
        self,
        name: str,
        nodes: list[str],
        params: dict[str, object] | None = None,
        *,
        title: str | None = None,
    ) -> None:
        super().__init__(title=title or name)
        self.name = name
        self.nodes = nodes
        self.params = params or {}

    def copy(self, id_suffix: str) -> SubCircuit:
        new = copy.deepcopy(self)
        new.name = f"{self.name}_{id_suffix}"
        return new

    def get_netlist(self) -> list[str]:
        lines = [f"subckt {self.name} ({' '.join(self.nodes)})"]
        if self.params:
            lines.append("parameters " + _join_kv(self.params))
        for subckt in self.subcircuits.values():
            lines.extend(subckt.get_netlist())
        self._extend_lines(lines)
        lines.append(f"ends {self.name}")
        return lines

    def __str__(self) -> str:
        return "\n".join(self.get_netlist())
