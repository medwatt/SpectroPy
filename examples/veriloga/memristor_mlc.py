import matplotlib.pyplot as plt
import numpy as np

from spectropy import (
    SpectreSession,
    Circuit,
    SubCircuit,
    WaveformGenerator,
    simulations,
)

from examples.config import BACKEND, OUTDIR, FREEPDK45_DIR, VA_DIR

T_DURATION = 1000                   # ns: BL trinagle time
TR = 10e-3                          # ns: Transition time (10 ps)
WL_SET_LEVELS = [0.5, 0.7, 1.0]     # V:  WL during SET   (positive triangle)
WL_RESET_LEVELS = [0.5, 0.7, 1.0]   # V:  WL during RESET (negative triangle)
VTE_LEVELS = [2.8, 2.8, 2.8]        # V:  BL sweep amplitudes

def build_cell() -> SubCircuit:
    cell = SubCircuit(name="cell_1t1r", nodes=["bl", "wl", "sl"], params={"gap_ini": "19e-10"})
    cell.M("n", ("d", "wl", "sl", "sl"), "NMOS_VTH", w="2u", l="45n")
    cell.va(
        "rram", ("bl", "d"), "rram_v_1_0_0",
        gap_ini="gap_ini",
        model_switch=0,
    )
    return cell


def build_netlist(wl_set_v: float, wl_reset_v: float, vte: float) -> Circuit:
    cell = build_cell()
    ckt = Circuit("1T1R MLC Butterfly")
    ckt.global_nodes("0")
    ckt.ahdl_include(f"{VA_DIR}/rram_v_1_0_0.va")
    ckt.include(f"{FREEPDK45_DIR}/nmos_vth.inc")
    ckt.temperature(27)

    w_vte = WaveformGenerator(scale="n", transition_time=TR)
    w_vte.triangle(duration=T_DURATION, peak_value=+vte)  # SET sweep
    w_vte.triangle(duration=T_DURATION, peak_value=-vte)  # RESET sweep

    w_wl = WaveformGenerator(scale="n", transition_time=TR)
    w_wl.step(duration=T_DURATION, delta=wl_set_v)
    w_wl.step(duration=T_DURATION, delta=wl_reset_v - wl_set_v)

    ckt.VoltagePWL("stim", ("bl_src", "0"), wave=w_vte.generate())
    ckt.V("sense", ("bl_src", "bl"), dc=0)
    ckt.VoltagePWL("wl", ("wl", "0"), wave=w_wl.generate())
    ckt.X("cell", ("bl", "wl", "0"), cell)
    ckt.save("bl", "Vsense:p")
    return ckt


def main() -> None:
    session = SpectreSession(backend=BACKEND)

    stop = 2 * T_DURATION
    palette = [
        "#0C5DA5",
        "#00B945",
        "#FF9500",
        "#FF2C00",
        "#845B97",
        "#00B4D8",
        "#E377C2",
        "#8C564B",
        "#474747",
        "#9e9e9e",
    ]
    colors = palette[: len(WL_SET_LEVELS)]

    fig, ax = plt.subplots(figsize=(8, 6))

    for wl_set_v, wl_reset_v, vte_level, color in zip(
        WL_SET_LEVELS, WL_RESET_LEVELS, VTE_LEVELS, colors
    ):
        print(f"WL set={wl_set_v}V  reset={wl_reset_v}V, vte={vte_level}V")
        session.load_netlist(build_netlist(wl_set_v, wl_reset_v, vte_level).get_netlist())
        result = session.run(
            simulations.Tran(stop=f"{stop}n", step="1n"),
            stem="memristor_mlc",
            outdir=OUTDIR,
        )

        vbl = result.voltages["bl"]
        imem = result.currents["Vsense:p"]

        label = f"WL set={wl_set_v}V / rst={wl_reset_v}V / vte={vte_level}V"
        ax.semilogy(
            vbl,
            np.abs(imem) + 1e-12,
            color=color,
            linewidth=1.5,
            label=label,
        )

    ax.set_xlabel("BL Voltage (V)")
    ax.set_ylabel("log|Current (mA)|")
    ax.set_title("1T1R MLC Butterfly")
    ax.legend(title="WL voltage", fontsize=9)
    ax.set_ylim(bottom=1e-8)
    ax.grid(True, linestyle="--", alpha=0.4)

    fig.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()
