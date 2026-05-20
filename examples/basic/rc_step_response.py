import matplotlib.pyplot as plt

from spectropy import SpectreSession, Circuit, simulations
from examples.config import BACKEND, OUTDIR


def build_netlist() -> Circuit:
    ckt = Circuit("RC Step Response")
    ckt.global_nodes("0")
    ckt.VoltagePulse("1", ("vin", "0"), val0=0, val1=1, period="2m", width="1m")
    ckt.R("1", ("vin", "vout"), "1k")
    ckt.C("1", ("vout", "0"), "1u")
    ckt.save("vin", "vout")
    return ckt


def main() -> None:
    session = SpectreSession(backend=BACKEND)
    session.load_netlist(build_netlist().get_netlist())

    result = session.run(
        simulations.Tran(stop="4m", step="1u"),
        stem="rc_step_response",
        outdir=OUTDIR,
    )

    time = result.time
    vin = result.voltages["vin"]
    vout = result.voltages["vout"]

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(time * 1e3, vin, label="$V_{in}$ (pulse)")
    ax.plot(time * 1e3, vout, label="$V_{out}$ (RC response)")
    ax.set_xlabel("Time (ms)")
    ax.set_ylabel("Voltage (V)")
    ax.set_title("RC Circuit: Step Response (Transient)")
    ax.legend()
    ax.grid(True, linestyle="--", alpha=0.4)
    fig.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()
