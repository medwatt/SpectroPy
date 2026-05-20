import matplotlib.pyplot as plt
import numpy as np

from spectropy import SpectreSession, Circuit, SubCircuit, simulations
from examples.config import BACKEND, OUTDIR, FREEPDK45_DIR

VDD = 1.0
TEMPS = [(-40, "dc_cold"), (27, "dc_nom"), (85, "dc_hot")]


def build_netlist() -> Circuit:
    inv = SubCircuit(
        name="inverter",
        nodes=["in", "out", "vdd", "vss"],
        params={"l_n": "45n", "w_n": "90n", "l_p": "45n", "w_p": "180n"},
    )
    inv.M("n", ("out", "in", "vss", "vss"), "NMOS_VTH", w="w_n", l="l_n")
    inv.M("p", ("out", "in", "vdd", "vdd"), "PMOS_VTH", w="w_p", l="l_p")

    ckt = Circuit("CMOS Inverter: Alter Temperature Demo")
    ckt.include(f"{FREEPDK45_DIR}/nmos_vth.inc")
    ckt.include(f"{FREEPDK45_DIR}/pmos_vth.inc")
    ckt.global_nodes("0")
    ckt.parameters(vin=0.5)
    ckt.V("dd", ("vdd", "0"), dc=VDD)
    ckt.V("in", ("in", "0"), dc="vin")
    ckt.X("inv", ("in", "out", "vdd", "0"), inv, params={"w_n": "500n", "w_p": "1u"})
    ckt.save("in", "out")
    return ckt


def main() -> None:
    session = SpectreSession(backend=BACKEND)
    session.load_netlist(build_netlist().get_netlist())

    # Build the run sequence: set temperature, then sweep.
    runnables = []
    for i, (temp, dc_name) in enumerate(TEMPS):
        runnables.append(simulations.Alter(name=f"set_temp_{i}", param="temp", value=temp))
        runnables.append(simulations.DC(param="vin", start=0, stop=VDD, step=0.005, name=dc_name))

    # Run the simulations
    result = session.run(*runnables, stem="inverter_alter", outdir=OUTDIR)

    # result has exactly len(TEMPS) entries; Alter instances are skipped.
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    colors = ["steelblue", "forestgreen", "tomato"]

    ax_vout = axes[0]
    ax_gain = axes[1]

    for i, (temp, _) in enumerate(TEMPS):
        dc = result[i]
        vin = dc.voltages["in"]
        vout = np.real(dc.voltages["out"])
        gain = np.gradient(vout, vin)

        label = f"T = {temp} C"
        ax_vout.plot(vin, vout, color=colors[i], linewidth=2, label=label)
        ax_gain.plot(vin, gain, color=colors[i], linewidth=2, label=label)

    ax_vout.set_xlabel("$V_{in}$ (V)")
    ax_vout.set_ylabel("$V_{out}$ (V)")
    ax_vout.set_title("DC Transfer Characteristic")
    ax_vout.set_xlim(0, VDD)
    ax_vout.set_ylim(-0.05, VDD + 0.05)
    ax_vout.legend()
    ax_vout.grid(True, linestyle="--", alpha=0.4)

    ax_gain.set_xlabel("$V_{in}$ (V)")
    ax_gain.set_ylabel("$dV_{out}/dV_{in}$")
    ax_gain.set_title("Small-Signal Voltage Gain")
    ax_gain.set_xlim(0, VDD)
    ax_gain.legend()
    ax_gain.grid(True, linestyle="--", alpha=0.4)

    fig.suptitle("CMOS Inverter: Temperature Effect via Alter", fontsize=13)
    fig.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()
