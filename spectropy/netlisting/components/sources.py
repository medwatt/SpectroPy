# imports <<<
from __future__ import annotations
from collections.abc import Sequence
from .base import Component, TwoPortComponent
# >>>


def V(self, id: str, nodes: tuple[str, str], **params: object) -> None:
    """Add an independent voltage source (vsource).

    Pass waveform parameters directly as keyword arguments. For common
    waveform shapes use the dedicated methods: VoltageSin, VoltagePulse,
    VoltagePWL.

    id: Unique identifier.
    nodes: (plus_node, minus_node).
    **params: Spectre vsource parameters (e.g. ``dc=1.8``, ``mag=1``).

    Example::

        ckt.V("bias", ("vdd", "0"), dc=1.8)
        ckt.V("stim", ("in",  "0"), dc=0, mag=1)  # AC stimulus
    """
    self._add_component(
        Component(id=id, nodes=nodes, spice_prefix="V", master="vsource", params=params)
    )


def I(self, id: str, nodes: tuple[str, str], **params: object) -> None:
    """Add an independent current source (isource).

    id: Unique identifier.
    nodes: (plus_node, minus_node).
    **params: Spectre isource parameters (e.g. ``dc="10u"``).

    Example::

        ckt.I("bias", ("vdd", "drain"), dc="10u")
    """
    self._add_component(
        Component(id=id, nodes=nodes, spice_prefix="I", master="isource", params=params)
    )


def VoltageSin(
    self,
    id: str,
    nodes: tuple[str, str],
    amplitude: object,
    freq: object,
    dc: object = 0,
    phase: object | None = None,
    delay: object | None = None,
    **params: object,
) -> None:
    """Add a sinusoidal voltage source (vsource type=sine).

    Spectre parameters emitted: ``type=sine dc ampl freq [phase] [delay]``

    id: Unique identifier.
    nodes: (plus_node, minus_node).
    amplitude: Peak amplitude (``ampl``).
    freq: Frequency in Hz.
    dc: DC offset (default 0).
    phase: Phase offset in degrees (default omitted).
    delay: Waveform start delay in seconds (default omitted).
    **params: Additional Spectre parameters.
    """
    p: dict[str, object] = {"type": "sine", "dc": dc, "ampl": amplitude, "freq": freq}
    if phase is not None:
        p["phase"] = phase
    if delay is not None:
        p["delay"] = delay
    p.update(params)
    self._add_component(
        Component(id=id, nodes=nodes, spice_prefix="V", master="vsource", params=p)
    )


def CurrentSin(
    self,
    id: str,
    nodes: tuple[str, str],
    amplitude: object,
    freq: object,
    dc: object = 0,
    phase: object | None = None,
    delay: object | None = None,
    **params: object,
) -> None:
    """Add a sinusoidal current source (isource type=sine).

    Spectre parameters emitted: ``type=sine dc ampl freq [phase] [delay]``

    id: Unique identifier.
    nodes: (plus_node, minus_node).
    amplitude: Peak amplitude (``ampl``).
    freq: Frequency in Hz.
    dc: DC offset (default 0).
    phase: Phase offset in degrees (default omitted).
    delay: Waveform start delay in seconds (default omitted).
    **params: Additional Spectre parameters.
    """
    p: dict[str, object] = {"type": "sine", "dc": dc, "ampl": amplitude, "freq": freq}
    if phase is not None:
        p["phase"] = phase
    if delay is not None:
        p["delay"] = delay
    p.update(params)
    self._add_component(
        Component(id=id, nodes=nodes, spice_prefix="I", master="isource", params=p)
    )


def VoltagePulse(
    self,
    id: str,
    nodes: tuple[str, str],
    val0: object,
    val1: object,
    period: object,
    width: object,
    delay: object = 0,
    rise: object | None = None,
    fall: object | None = None,
    **params: object,
) -> None:
    """Add a pulse voltage source (vsource type=pulse).

    Spectre parameters emitted:
    ``type=pulse val0 val1 period width [delay] [rise] [fall]``

    id: Unique identifier.
    nodes: (plus_node, minus_node).
    val0: Low voltage level.
    val1: High voltage level.
    period: Waveform period.
    width: Pulse width (high time).
    delay: Delay before first edge (default 0).
    rise: Rise time (default omitted; Spectre uses simulation step).
    fall: Fall time (default omitted).
    **params: Additional Spectre parameters.
    """
    p: dict[str, object] = {
        "type": "pulse",
        "val0": val0,
        "val1": val1,
        "period": period,
        "width": width,
        "delay": delay,
    }
    if rise is not None:
        p["rise"] = rise
    if fall is not None:
        p["fall"] = fall
    p.update(params)
    self._add_component(
        Component(id=id, nodes=nodes, spice_prefix="V", master="vsource", params=p)
    )


def CurrentPulse(
    self,
    id: str,
    nodes: tuple[str, str],
    val0: object,
    val1: object,
    period: object,
    width: object,
    delay: object = 0,
    rise: object | None = None,
    fall: object | None = None,
    **params: object,
) -> None:
    """Add a pulse current source (isource type=pulse).

    Spectre parameters emitted:
    ``type=pulse val0 val1 period width [delay] [rise] [fall]``

    id: Unique identifier.
    nodes: (plus_node, minus_node).
    val0: Low current level.
    val1: High current level.
    period: Waveform period.
    width: Pulse width (high time).
    delay: Delay before first edge (default 0).
    rise: Rise time (default omitted).
    fall: Fall time (default omitted).
    **params: Additional Spectre parameters.
    """
    p: dict[str, object] = {
        "type": "pulse",
        "val0": val0,
        "val1": val1,
        "period": period,
        "width": width,
        "delay": delay,
    }
    if rise is not None:
        p["rise"] = rise
    if fall is not None:
        p["fall"] = fall
    p.update(params)
    self._add_component(
        Component(id=id, nodes=nodes, spice_prefix="I", master="isource", params=p)
    )


def VoltagePWL(
    self,
    id: str,
    nodes: tuple[str, str],
    wave: Sequence[tuple[object, object]],
    pwlperiod: object | None = None,
    **params: object,
) -> None:
    """Add a piecewise-linear voltage source (vsource type=pwl).

    Spectre parameters emitted: ``type=pwl wave=[t0 v0 t1 v1 ...] [pwlperiod]``

    id: Unique identifier.
    nodes: (plus_node, minus_node).
    wave: Sequence of (time, value) pairs, e.g. [(0, 0), ("1n", 1)].
    pwlperiod: If given, the waveform repeats with this period.
    **params: Additional Spectre parameters.
    """
    wave_str = "[" + " ".join(f"{t} {v}" for t, v in wave) + "]"
    p: dict[str, object] = {"type": "pwl", "wave": wave_str}
    if pwlperiod is not None:
        p["pwlperiod"] = pwlperiod
    p.update(params)
    self._add_component(
        Component(id=id, nodes=nodes, spice_prefix="V", master="vsource", params=p)
    )


def CurrentPWL(
    self,
    id: str,
    nodes: tuple[str, str],
    wave: Sequence[tuple[object, object]],
    pwlperiod: object | None = None,
    **params: object,
) -> None:
    """Add a piecewise-linear current source (isource type=pwl).

    Spectre parameters emitted: ``type=pwl wave=[t0 i0 t1 i1 ...] [pwlperiod]``

    id: Unique identifier.
    nodes: (plus_node, minus_node).
    wave: Sequence of (time, value) pairs.
    pwlperiod: If given, the waveform repeats with this period.
    **params: Additional Spectre parameters.
    """
    wave_str = "[" + " ".join(f"{t} {v}" for t, v in wave) + "]"
    p: dict[str, object] = {"type": "pwl", "wave": wave_str}
    if pwlperiod is not None:
        p["pwlperiod"] = pwlperiod
    p.update(params)
    self._add_component(
        Component(id=id, nodes=nodes, spice_prefix="I", master="isource", params=p)
    )


def G(
    self,
    id: str,
    out_nodes: tuple[str, str],
    ctrl_nodes: tuple[str, str],
    gm: object,
    **params: object,
) -> None:
    """Add a voltage-controlled current source (vccs).

    Renders as: ``Gid (out_p out_n)(ctrl_p ctrl_n) vccs gm=value``

    id: Unique identifier.
    out_nodes: Output terminal pair (positive, negative).
    ctrl_nodes: Controlling voltage terminal pair (positive, negative).
    gm: Transconductance in A/V.
    **params: Additional Spectre parameters.
    """
    self._add_component(
        TwoPortComponent(
            id=id,
            out_nodes=out_nodes,
            ctrl_nodes=ctrl_nodes,
            spice_prefix="G",
            master="vccs",
            params={"gm": gm, **params},
        )
    )


def E(
    self,
    id: str,
    out_nodes: tuple[str, str],
    ctrl_nodes: tuple[str, str],
    gain: object,
    **params: object,
) -> None:
    """Add a voltage-controlled voltage source (vcvs).

    Renders as: ``Eid (out_p out_n)(ctrl_p ctrl_n) vcvs gain=value``

    id: Unique identifier.
    out_nodes: Output terminal pair (positive, negative).
    ctrl_nodes: Controlling voltage terminal pair (positive, negative).
    gain: Voltage gain (dimensionless).
    **params: Additional Spectre parameters.
    """
    self._add_component(
        TwoPortComponent(
            id=id,
            out_nodes=out_nodes,
            ctrl_nodes=ctrl_nodes,
            spice_prefix="E",
            master="vcvs",
            params={"gain": gain, **params},
        )
    )


def F(
    self,
    id: str,
    nodes: tuple[str, str],
    probe: str,
    gain: object,
    **params: object,
) -> None:
    """Add a current-controlled current source (cccs).

    Renders as: ``Fid (n+ n-) cccs probe=source_id gain=value``

    The controlling current is sensed through an existing voltage source
    named ``probe`` (acting as a zero-volt ammeter).

    id: Unique identifier.
    nodes: (plus_node, minus_node).
    probe: Id of the voltage source used as the current probe.
    gain: Current gain (dimensionless).
    **params: Additional Spectre parameters.
    """
    self._add_component(
        Component(
            id=id,
            nodes=nodes,
            spice_prefix="F",
            master="cccs",
            params={"probe": probe, "gain": gain, **params},
        )
    )


def H(
    self,
    id: str,
    nodes: tuple[str, str],
    probe: str,
    transresistance: object,
    **params: object,
) -> None:
    """Add a current-controlled voltage source (ccvs).

    Renders as: ``Hid (n+ n-) ccvs probe=source_id transresistance=value``

    The controlling current is sensed through an existing voltage source
    named ``probe`` (acting as a zero-volt ammeter).

    id: Unique identifier.
    nodes: (plus_node, minus_node).
    probe: Id of the voltage source used as the current probe.
    transresistance: Transresistance in Ω.
    **params: Additional Spectre parameters.
    """
    self._add_component(
        Component(
            id=id,
            nodes=nodes,
            spice_prefix="H",
            master="ccvs",
            params={"probe": probe, "transresistance": transresistance, **params},
        )
    )


def B(
    self,
    id: str,
    nodes: tuple[str, str],
    *,
    voltage: str | None = None,
    current: str | None = None,
    **params: object,
) -> None:
    """Add a behavioral source (bsource).

    Provide exactly one of ``voltage`` or ``current`` as a Spectre
    expression string.

    id: Unique identifier.
    nodes: (plus_node, minus_node).
    voltage: Voltage expression string (mutually exclusive with current).
    current: Current expression string (mutually exclusive with voltage).
    **params: Additional Spectre parameters.

    Raises:
        ValueError: If neither or both of voltage/current are provided.

    Example::

        ckt.B("1", ("a", "b"), voltage="v(x)*2")
        ckt.B("2", ("a", "b"), current="i(Vbias)")
    """
    if (voltage is None) == (current is None):
        raise ValueError("Specify exactly one of voltage= or current=")
    expr_param = {"v": voltage} if voltage is not None else {"i": current}
    self._add_component(
        Component(
            id=id,
            nodes=nodes,
            spice_prefix="B",
            master="bsource",
            params={**expr_param, **params},
        )
    )
