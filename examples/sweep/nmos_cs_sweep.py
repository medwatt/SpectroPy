import matplotlib.pyplot as plt

from spectropy import SpectreSession, Circuit, simulations
from examples.config import BACKEND, OUTDIR, FREEPDK45_DIR

VDD = 1.0
W, L = "1u", "45n"
RD = 5000
TEMPS = [-40, 0, 27, 85, 125]


def build_netlist() -> Circuit:
    ckt = Circuit("NMOS CS Amplifier: Parametric Temperature Sweep")
    ckt.include(f"{FREEPDK45_DIR}/nmos_vth.inc")
    ckt.global_nodes("0")
    ckt.parameters(vgate=0)
    ckt.V("dd", ("vdd", "0"), dc=VDD)
    ckt.V("g", ("gate", "0"), dc="vgate")
    ckt.R("d", ("vdd", "out"), RD)
    ckt.M("n", ("out", "gate", "0", "0"), "NMOS_VTH", w=W, l=L)
    ckt.save("out")
    return ckt


def main() -> None:
    session = SpectreSession(backend=BACKEND)
    session.load_netlist(build_netlist().get_netlist())

    inner_dc = simulations.DC(param="vgate", start=0, stop=VDD, step=0.01)

    result = session.run(
        simulations.Sweep(
            inner=[inner_dc],
            param="temp",
            values=TEMPS,
            name="tempswp",
        ),
        stem="nmos_cs_sweep",
        outdir=OUTDIR,
    )

    fig, ax = plt.subplots(figsize=(8, 5))
    for i, temp in enumerate(TEMPS):
        if i >= len(result):
            break
        dc = result[i]
        ax.plot(dc.sweep, dc["out"], linewidth=2, label=f"T = {temp} C")

    ax.set_xlabel("$V_{GS}$ (V)")
    ax.set_ylabel("$V_{out}$ (V)")
    ax.set_title("NMOS CS Amplifier: $V_{out}$ vs $V_{GS}$ at Multiple Temperatures")
    ax.legend()
    ax.grid(True, linestyle="--", alpha=0.4)
    fig.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()
