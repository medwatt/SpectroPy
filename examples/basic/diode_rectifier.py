import matplotlib.pyplot as plt

from spectropy import SpectreSession, Circuit, simulations
from examples.config import BACKEND, OUTDIR


def build_netlist() -> Circuit:
    ckt = Circuit("Half-Wave Diode Rectifier")
    ckt.global_nodes("0")
    ckt.model("D1N4148", "diode", {"is": 2.52e-9, "n": 1.752, "rs": 0.568, "tt": "20n", "cjo": "4p"})
    ckt.VoltageSin("1", ("vin", "0"), amplitude=1, freq="1k")
    ckt.D("1", ("vin", "vout"), "D1N4148")
    ckt.R("1", ("vout", "0"), "1k")
    ckt.save("vin", "vout")
    return ckt


def main() -> None:
    session = SpectreSession(backend=BACKEND)
    session.load_netlist(build_netlist().get_netlist())

    result = session.run(
        simulations.Tran(stop="3m", step="1u"),
        stem="diode_rectifier",
        outdir=OUTDIR,
    )

    time = result.time
    vin = result.voltages["vin"]
    vout = result.voltages["vout"]

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(time * 1e3, vin, label="$V_{in}$ (sine)")
    ax.plot(time * 1e3, vout, label="$V_{out}$ (rectified)")
    ax.set_xlabel("Time (ms)")
    ax.set_ylabel("Voltage (V)")
    ax.set_title("Half-Wave Diode Rectifier: Transient Response")
    ax.legend()
    ax.grid(True, linestyle="--", alpha=0.4)
    fig.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()
