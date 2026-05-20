import matplotlib.pyplot as plt
import numpy as np

from spectropy import Circuit, SpectreSession, SubCircuit, simulations
from examples.config import BACKEND, OUTDIR, FREEPDK45_DIR

VDD_NOM = 1.0
VDD_MAX = 1.1
MODEL_FILE = f"{FREEPDK45_DIR}/freepdk45_corners.scs"

PVT_CORNERS = [
    ("tt_1v0_27c", "tt", 1.0, 27),
    ("ss_0v9_125c", "ss", 0.9, 125),
    ("ff_1v1_m40c", "ff", 1.1, -40),
    ("sf_1v0_27c", "sf", 1.0, 27),
    ("fs_1v0_27c", "fs", 1.0, 27),
]

STYLE = {
    "tt": {"color": "black", "label": "tt, 1.0 V, 27 C", "ls": "-", "lw": 2.0},
    "ss": {"color": "steelblue", "label": "ss, 0.9 V, 125 C", "ls": "--", "lw": 1.5},
    "ff": {"color": "tomato", "label": "ff, 1.1 V, -40 C", "ls": "--", "lw": 1.5},
    "sf": {"color": "seagreen", "label": "sf, 1.0 V, 27 C", "ls": ":", "lw": 1.7},
    "fs": {"color": "darkorange", "label": "fs, 1.0 V, 27 C", "ls": ":", "lw": 1.7},
}


def build_netlist() -> Circuit:
    inv = SubCircuit(name="inverter", nodes=["in", "out", "vdd", "vss"])
    inv.M("n", ("out", "in", "vss", "vss"), "NMOS_VTH", w="500n", l="45n")
    inv.M("p", ("out", "in", "vdd", "vdd"), "PMOS_VTH", w="1u", l="45n")

    ckt = Circuit("FreePDK-style inverter corner analysis")
    ckt.include(MODEL_FILE, section="tt")
    ckt.global_nodes("0")
    ckt.parameters(vin=0.5, vdd=VDD_NOM)
    ckt.V("dd", ("vdd", "0"), dc="vdd")
    ckt.V("in", ("in", "0"), dc="vin")
    ckt.X("inv", ("in", "out", "vdd", "0"), inv)
    ckt.save("in", "out")
    return ckt


def switching_point(vin: np.ndarray, vout: np.ndarray) -> float:
    """Find the input voltage where Vout = Vin."""
    diff = vout - vin
    crossings = np.where(np.diff(np.sign(diff)))[0]
    if len(crossings) == 0:
        return float("nan")
    i = crossings[0]
    return float(vin[i] - diff[i] * (vin[i + 1] - vin[i]) / (diff[i + 1] - diff[i]))


def main() -> None:
    session = SpectreSession(backend=BACKEND)
    session.load_netlist(build_netlist().get_netlist())

    corners = simulations.Corners(
        corners=[
            simulations.Corner(
                section=section,
                file=MODEL_FILE,
                temp=temp,
                parameters={"vdd": vdd},
                label=label,
            )
            for label, section, vdd, temp in PVT_CORNERS
        ],
        inner=[simulations.DC(param="vin", start=0, stop=VDD_MAX, step=0.005)],
        name="pvt",
    )

    result = session.run(corners, stem="inverter_corners", outdir=OUTDIR)[0]

    vm: dict[str, float] = {}
    print("Switching point Vm per PVT corner:")
    for label, corner_result in result.items():
        vin = corner_result["vin"]
        vout = np.real(corner_result.voltages["out"])
        vm[label] = switching_point(vin, vout)
        print(f"  {label:12s}: {vm[label] * 1e3:.1f} mV")

    fig, (ax_curve, ax_bar) = plt.subplots(1, 2, figsize=(12, 5))
    ax_curve.plot(
        [0, VDD_MAX],
        [0, VDD_MAX],
        color="lightgray",
        linestyle="--",
        linewidth=1,
        label="$V_{out}=V_{in}$",
    )

    for label, section, _vdd, _temp in PVT_CORNERS:
        corner_result = result[label]
        vin = corner_result["vin"]
        vout = np.real(corner_result.voltages["out"])
        style = STYLE[section]
        ax_curve.plot(
            vin,
            vout,
            color=style["color"],
            linestyle=style["ls"],
            linewidth=style["lw"],
            label=style["label"],
        )
        ax_curve.axvline(
            vm[label],
            color=style["color"],
            linestyle=style["ls"],
            linewidth=0.8,
            alpha=0.5,
        )

    ax_curve.set_xlabel("$V_{in}$ (V)")
    ax_curve.set_ylabel("$V_{out}$ (V)")
    ax_curve.set_title("DC Transfer Curves")
    ax_curve.set_xlim(0, VDD_MAX)
    ax_curve.set_ylim(-0.05, VDD_MAX + 0.05)
    ax_curve.grid(True, linestyle="--", alpha=0.3)
    ax_curve.legend(fontsize=9)

    labels = [label for label, _section, _vdd, _temp in PVT_CORNERS]
    colors = [STYLE[section]["color"] for _label, section, _vdd, _temp in PVT_CORNERS]
    bars = ax_bar.bar(labels, [vm[label] * 1e3 for label in labels], color=colors)
    ax_bar.axhline(
        VDD_NOM / 2 * 1e3,
        color="gray",
        linestyle="--",
        linewidth=1,
        label=f"$V_{{DD,nom}}/2$ = {VDD_NOM / 2 * 1e3:.0f} mV",
    )
    for bar, label in zip(bars, labels):
        value = vm[label] * 1e3
        ax_bar.text(
            bar.get_x() + bar.get_width() / 2,
            value + 2,
            f"{value:.1f}",
            ha="center",
            va="bottom",
            fontsize=9,
        )
    ax_bar.set_ylabel("$V_m$ (mV)")
    ax_bar.set_title("Switching Point")
    ax_bar.tick_params(axis="x", labelrotation=30)
    ax_bar.grid(True, axis="y", linestyle="--", alpha=0.3)
    ax_bar.legend(fontsize=9)

    fig.suptitle("Inverter PVT Corner Analysis")
    fig.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()
