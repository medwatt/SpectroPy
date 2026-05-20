import matplotlib.pyplot as plt
import numpy as np

from spectropy import SpectreSession, Circuit, SubCircuit, simulations
from examples.config import BACKEND, OUTDIR, FREEPDK45_DIR

VDD = 1.0
L_N, W_N = "45n", "90n"
L_P, W_P = "45n", "180n"


def build_netlist() -> Circuit:
    inv = SubCircuit(
        name="inverter",
        nodes=["in", "out", "vdd", "vss"],
        params={"l_n": L_N, "w_n": W_N, "l_p": L_P, "w_p": W_P},
    )
    inv.M("n", ("out", "in", "vss", "vss"), "NMOS_VTH", w="w_n", l="l_n")
    inv.M("p", ("out", "in", "vdd", "vdd"), "PMOS_VTH", w="w_p", l="l_p")

    ckt = Circuit("CMOS Inverter DC Transfer")
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

    result = session.run(
        simulations.OP(),
        simulations.DC(param="vin", start=0, stop=VDD, step=0.01),
        stem="inverter_dc",
        outdir=OUTDIR,
    )

    op_result = result[0]
    dc_result = result[1]

    print("\nOperating Point:")
    for name, val in op_result.voltages.items():
        print(f"  {name} = {np.real(val).item():.4f} V")

    vin = dc_result.voltages["in"]
    vout = np.real(dc_result.voltages["out"])

    fig, ax = plt.subplots(figsize=(7, 5))
    ax.plot(vin, vout, linewidth=2)
    ax.set_xlabel("$V_{in}$ (V)")
    ax.set_ylabel("$V_{out}$ (V)")
    ax.set_title("CMOS Inverter DC Transfer Characteristic")
    ax.set_xlim(vin[0], vin[-1])
    ax.set_ylim(-0.05, VDD + 0.05)
    ax.grid(True, linestyle="--", alpha=0.4)
    fig.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()
