# imports <<<
from __future__ import annotations

from .base import Component
# >>>

def S(
    self,
    id: str,
    nodes: tuple[str, ...],
    **params: object,
) -> None:
    """Add an ideal switch (switch).

    Spectre supports both 2-terminal series switches and 3+ terminal
    single-pole multiple-throw switches. For a simple series switch, pass two
    nodes, for example ``("vdd", "vbp")``. For a multi-throw switch, pass a
    common terminal followed by the throw terminals, for example
    ``("t0", "t1", "t2")`` where ``t0`` is the common terminal.

    id: Unique identifier.
    nodes: Switch terminals.
    **params: Spectre parameters.

        - ``position``: switch state. ``0`` means open. For a 2-terminal
          switch, ``1`` closes the switch and connects the two terminals. For
          a multi-throw switch, ``1`` connects the first throw to the common
          terminal, ``2`` connects the second throw, and so on.
        - ``dc_position``: override used at the start of DC analysis.
        - ``ac_position``: override used at the start of AC analysis.
        - ``tran_position``: override used at the start of transient analysis.
        - ``ic_position``: override used at the start of IC analysis.
        - ``offset``: offset voltage in series with the common terminal.
        - ``m``: multiplicity factor.

    Example::

        ckt.S("fb", ("vout", "fb"), position=0, ac_position=1)
    """
    self._add_component(
        Component(id=id, nodes=nodes, spice_prefix="S", master="switch", params=params)
    )
