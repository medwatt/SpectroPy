import matplotlib.pyplot as plt
import numpy as np

from spectropy import SpectreSession, Circuit, simulations
from examples.config import BACKEND, OUTDIR


def build_netlist() -> Circuit:
    ckt = Circuit("RC Low-Pass Filter")
    ckt.global_nodes("0")
    ckt.V("1", ("in", "0"), dc=0, mag=1)
    ckt.R("1", ("in", "out"), "1k")
    ckt.C("1", ("out", "0"), "100n")
    ckt.save("in", "out")
    return ckt


def main() -> None:
    session = SpectreSession(backend=BACKEND)
    session.load_netlist(build_netlist().get_netlist())

    result = session.run(
        simulations.AC(start="100", stop="1e6", sweep_type="dec", points=20),
        stem="rc_low_pass_ac",
        outdir=OUTDIR,
    )

    freq = result.frequency
    vout = result.voltages["out"]
    vin = result.voltages["in"]

    gain_db = 20.0 * np.log10(np.abs(vout / vin))
    phase_deg = np.angle(vout / vin, deg=True)

    fig, (ax_mag, ax_phase) = plt.subplots(2, 1, figsize=(9, 7), sharex=True)
    ax_mag.semilogx(freq, gain_db, linewidth=2)
    ax_mag.set_ylabel("Gain (dB)")
    ax_mag.grid(True, which="both", linestyle="--", alpha=0.4)
    ax_phase.semilogx(freq, phase_deg, linewidth=2)
    ax_phase.set_xlabel("Frequency (Hz)")
    ax_phase.set_ylabel("Phase (deg)")
    ax_phase.grid(True, which="both", linestyle="--", alpha=0.4)
    fig.suptitle("RC Low-Pass Filter AC Response")
    fig.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()
