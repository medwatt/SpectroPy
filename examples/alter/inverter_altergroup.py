import matplotlib.pyplot as plt
import numpy as np

from spectropy import SpectreSession, Circuit, SubCircuit, simulations
from examples.config import BACKEND, OUTDIR, FREEPDK45_DIR

VDD = 1.0

CORNERS = [
    ("nominal",   "500n", "1u",    27,  "forestgreen"),
    ("fast_hot",  "900n", "1800n", 85,  "tomato"),
    ("slow_cold", "250n", "500n",  -40, "steelblue"),
]


def build_netlist() -> Circuit:
    inv = SubCircuit(
        name="inverter",
        nodes=["in", "out", "vdd", "vss"],
        params={"w_n": "500n", "w_p": "1u"},
    )
    inv.M("n", ("out", "in", "vss", "vss"), "NMOS_VTH", w="w_n", l="45n")
    inv.M("p", ("out", "in", "vdd", "vdd"), "PMOS_VTH", w="w_p", l="45n")

    ckt = Circuit("CMOS Inverter: Corner Simulation via AlterGroup")
    ckt.include(f"{FREEPDK45_DIR}/nmos_vth.inc")
    ckt.include(f"{FREEPDK45_DIR}/pmos_vth.inc")
    ckt.global_nodes("0")
    ckt.parameters(vin=0.5, w_n="500n", w_p="1u")
    ckt.V("dd", ("vdd", "0"), dc=VDD)
    ckt.V("in", ("in", "0"), dc="vin")
    ckt.X("inv", ("in", "out", "vdd", "0"), inv, params={"w_n": "w_n", "w_p": "w_p"})
    ckt.save("in", "out")
    return ckt


def main() -> None:
    session = SpectreSession(backend=BACKEND)
    session.load_netlist(build_netlist().get_netlist())

    runnables = []
    for name, w_n, w_p, temp, _ in CORNERS:
        runnables.append(
            simulations.AlterGroup(
                name=f"corner_{name}",
                parameters={"w_n": w_n, "w_p": w_p},
                options={"temp": temp},
            )
        )
        runnables.append(
            simulations.DC(param="vin", start=0, stop=VDD, step=0.005, name=f"dc_{name}")
        )

    result = session.run(*runnables, stem="inverter_corners", outdir=OUTDIR)

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    ax_vout, ax_gain = axes

    for i, (name, w_n, w_p, temp, color) in enumerate(CORNERS):
        dc = result[i]
        vin = dc["vin"]
        vout = np.real(dc.voltages["out"])
        gain = np.gradient(vout, vin)
        label = f"{name}  (W_n={w_n}, W_p={w_p}, T={temp} C)"
        ax_vout.plot(vin, vout, color=color, linewidth=2, label=label)
        ax_gain.plot(vin, gain, color=color, linewidth=2, label=label)

    ax_vout.set_xlabel("$V_{in}$ (V)")
    ax_vout.set_ylabel("$V_{out}$ (V)")
    ax_vout.set_title("DC Transfer Characteristic")
    ax_vout.set_xlim(0, VDD)
    ax_vout.set_ylim(-0.05, VDD + 0.05)
    ax_vout.legend(fontsize=8)
    ax_vout.grid(True, linestyle="--", alpha=0.4)

    ax_gain.set_xlabel("$V_{in}$ (V)")
    ax_gain.set_ylabel("$dV_{out}/dV_{in}$")
    ax_gain.set_title("Small-Signal Voltage Gain")
    ax_gain.set_xlim(0, VDD)
    ax_gain.legend(fontsize=8)
    ax_gain.grid(True, linestyle="--", alpha=0.4)

    fig.suptitle("CMOS Inverter: Process Corners via AlterGroup", fontsize=13)
    fig.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()
