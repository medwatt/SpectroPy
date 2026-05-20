from __future__ import annotations

from .base import Component


def M(
    self,
    id: str,
    nodes: tuple[str, str, str, str],
    model: str,
    **params: object,
) -> None:
    """Add a MOSFET instance.

    The master name is the model name (e.g. ``nmos``, ``pmos``, or a PDK
    model name). Nodes order: (drain, gate, source, bulk).

    id: Unique identifier.
    nodes: (drain, gate, source, bulk).
    model: Model name.
    **params: Additional Spectre parameters (e.g. ``w``, ``l``).
    """
    self._add_component(Component(id=id, nodes=nodes, spice_prefix="M", master=model, params=params))


def Q(
    self,
    id: str,
    nodes: tuple[str, str, str],
    model: str,
    **params: object,
) -> None:
    """Add a bipolar junction transistor (BJT) instance.

    The master name is the model name (e.g. ``npn``, ``pnp``).
    Nodes order: (collector, base, emitter).

    id: Unique identifier.
    nodes: (collector, base, emitter).
    model: Model name.
    **params: Additional Spectre parameters.
    """
    self._add_component(Component(id=id, nodes=nodes, spice_prefix="Q", master=model, params=params))


def D(
    self,
    id: str,
    nodes: tuple[str, str],
    model: str,
    **params: object,
) -> None:
    """Add a diode instance.

    The master name is the model name. Nodes order: (anode, cathode).

    id: Unique identifier.
    nodes: (anode, cathode).
    model: Model name.
    **params: Additional Spectre parameters.
    """
    self._add_component(Component(id=id, nodes=nodes, spice_prefix="D", master=model, params=params))
