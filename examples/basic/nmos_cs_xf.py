import matplotlib.pyplot as plt
import numpy as np

from spectropy import SpectreSession, Circuit, simulations
from examples.config import BACKEND, OUTDIR, FREEPDK45_DIR

VDD = 1.0
VGS_BIAS = 0.7
W, L = "1u", "45n"
RD = 5000


def build_netlist() -> Circuit:
    ckt = Circuit("NMOS Common-Source Amplifier Transfer Function")
    ckt.include(f"{FREEPDK45_DIR}/nmos_vth.inc")
    ckt.global_nodes("0")
    ckt.V("dd", ("vdd", "0"), dc=VDD)
    ckt.V("g", ("gate", "0"), dc=VGS_BIAS)
    ckt.R("d", ("vdd", "out"), RD)
    ckt.M("n", ("out", "gate", "0", "0"), "NMOS_VTH", w=W, l=L)
    ckt.save("out", "gate")
    return ckt


def main() -> None:
    session = SpectreSession(backend=BACKEND)
    session.load_netlist(build_netlist().get_netlist())

    result = session.run(
        simulations.OP(),
        simulations.XF(
            start="1",
            stop="100e9",
            sweep_type="dec",
            points=20,
            output_pos="out",
        ),
        stem="nmos_cf_xf",
        outdir=OUTDIR,
    )

    op_result = result[0]
    xf_result = result[1]

    print("\nOperating Point:")
    for name, val in op_result.voltages.items():
        print(f"  {name} = {np.real(val).item():.4f} V")

    freq = xf_result.frequency
    tfs = xf_result.transfer_functions
    h_vg = tfs.get("Vg")
    h_vdd = tfs.get("Vdd")

    n_plots = sum(h is not None for h in (h_vg, h_vdd))
    fig, axes = plt.subplots(2, n_plots, figsize=(6 * n_plots, 7), sharex=True, squeeze=False)

    def plot_tf(col, h, label):
        mag_db = 20.0 * np.log10(np.abs(h) + 1e-300)
        phase_deg = np.angle(h, deg=True)
        axes[0, col].semilogx(freq, mag_db, linewidth=2)
        axes[0, col].set_ylabel("Magnitude (dB)")
        axes[0, col].set_title(label)
        axes[0, col].grid(True, which="both", linestyle="--", alpha=0.4)
        axes[1, col].semilogx(freq, phase_deg, linewidth=2)
        axes[1, col].set_xlabel("Frequency (Hz)")
        axes[1, col].set_ylabel("Phase (deg)")
        axes[1, col].grid(True, which="both", linestyle="--", alpha=0.4)

    col = 0
    if h_vg is not None:
        plot_tf(col, h_vg, r"$V_{out}/V_g$: Voltage Gain")
        col += 1
    if h_vdd is not None:
        plot_tf(col, h_vdd, r"$V_{out}/V_{dd}$: Supply Rejection")

    fig.suptitle("NMOS CS Amplifier: Transfer Function Analysis")
    fig.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()
