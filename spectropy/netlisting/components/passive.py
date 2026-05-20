# imports <<<
from __future__ import annotations
from .base import Component
# >>>


def R(self, id: str, nodes: tuple[str, str], resistance: object, **params: object) -> None:
    """Add a resistor.

    id: Unique identifier.
    nodes: (plus_node, minus_node).
    resistance: Resistance value (``r`` parameter).
    **params: Additional Spectre parameters.
    """
    self._add_component(Component(
        id=id, nodes=nodes, spice_prefix="R", master="resistor",
        params={"r": resistance, **params},
    ))


def C(self, id: str, nodes: tuple[str, str], capacitance: object, **params: object) -> None:
    """Add a capacitor.

    id: Unique identifier.
    nodes: (plus_node, minus_node).
    capacitance: Capacitance value (``c`` parameter).
    **params: Additional Spectre parameters.
    """
    self._add_component(Component(
        id=id, nodes=nodes, spice_prefix="C", master="capacitor",
        params={"c": capacitance, **params},
    ))


def L(self, id: str, nodes: tuple[str, str], inductance: object, **params: object) -> None:
    """Add an inductor.

    id: Unique identifier.
    nodes: (plus_node, minus_node).
    inductance: Inductance value (``l`` parameter).
    **params: Additional Spectre parameters.
    """
    self._add_component(Component(
        id=id, nodes=nodes, spice_prefix="L", master="inductor",
        params={"l": inductance, **params},
    ))
