# imports <<<
from __future__ import annotations
from .base import Component, SubCircuitInstance
# >>>


def X(
    self,
    id: str,
    nodes: tuple[str, ...],
    subcircuit: object,
    copy: bool = False,
    params: dict[str, object] | None = None,
) -> None:
    """Add a subcircuit instance.

    id: Unique identifier.
    nodes: Tuple of connecting nodes (must match the subcircuit's port order).
    subcircuit: SubCircuit definition object, or a string name for an
        externally defined subcircuit.
    copy: If True, deep-copies the subcircuit definition and renames
        it ``<name>_<id>`` so each instance gets its own copy.
    params: Parameter overrides for parameterised subcircuits.
    """
    self._add_component(SubCircuitInstance(id=id, nodes=nodes, subcircuit=subcircuit, copy=copy, params=params))


def va(
    self,
    id: str,
    nodes: tuple[str, ...],
    module: str,
    **params: object,
) -> None:
    """Add a VerilogA module instance.

    The ``module`` argument is the Verilog-A module name as declared in the ``.va`` file.

    id: Unique identifier.
    nodes: Tuple of connecting nodes (must match the module's port order).
    module: Verilog-A module name.
    **params: Module parameter overrides.
    """
    self._add_component(Component(id=id, nodes=nodes, spice_prefix="I", master=module, params=params))
