import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import norm

from spectropy import SpectreSession, Circuit, simulations
from examples.config import BACKEND, OUTDIR, FREEPDK45_DIR

VDD = 1.0
VGS_BIAS_NOM = 0.7
W, L = "1u", "45n"
RD_NOM = 5000
NUMRUNS = 200


def build_netlist() -> Circuit:
    ckt = Circuit("NMOS CS Amplifier: Monte Carlo Process Variation")
    ckt.include(f"{FREEPDK45_DIR}/nmos_vth.inc")
    ckt.global_nodes("0")
    ckt.parameters(rd_val=RD_NOM, vgs_bias=VGS_BIAS_NOM)
    ckt.V("dd", ("vdd", "0"), dc=VDD)
    ckt.V("g", ("gate", "0"), dc="vgs_bias")
    ckt.R("d", ("vdd", "out"), "rd_val")
    ckt.M("n", ("out", "gate", "0", "0"), "NMOS_VTH", w=W, l=L)
    ckt.save("out")
    return ckt


def main() -> None:
    session = SpectreSession(backend=BACKEND)
    session.load_netlist(build_netlist().get_netlist())

    stats = simulations.Statistics(
        process=[
            simulations.Vary("rd_val", dist="gauss", std=5, percent=True),
            simulations.Vary("vgs_bias", dist="gauss", std=2, percent=True),
        ]
    )

    mc = simulations.MonteCarlo(
        inner=[simulations.OP()],
        numruns=NUMRUNS,
        variations="process",
        seed=42,
    )

    result = session.run(stats, mc, stem="nmos_montecarlo", outdir=OUTDIR)
    mc_result = result[0]

    vout_vals = np.array([np.real(run.voltages["out"]).item() for run in mc_result])

    mu, sigma = vout_vals.mean(), vout_vals.std()
    print(f"Vout: mean={mu:.4f} V  sigma={sigma:.4f} V  ({sigma / mu * 100:.2f}%)")

    fig, ax = plt.subplots(figsize=(8, 5))

    ax.hist(
        vout_vals,
        bins=30,
        density=True,
        color="steelblue",
        alpha=0.7,
        edgecolor="white",
        label="MC samples",
    )

    x = np.linspace(vout_vals.min(), vout_vals.max(), 300)
    ax.plot(x, norm.pdf(x, mu, sigma), color="tomato", linewidth=2, label="Gaussian fit")

    ax.axvline(mu, color="black", linestyle="--", linewidth=1.2, label=f"Mean = {mu:.4f} V")
    ax.axvline(mu - sigma, color="gray", linestyle=":", linewidth=1)
    ax.axvline(
        mu + sigma, color="gray", linestyle=":", linewidth=1, label=f"±1σ = {sigma * 1e3:.2f} mV"
    )

    ax.set_xlabel("$V_{out}$ (V)")
    ax.set_ylabel("Probability density")
    ax.set_title(
        f"NMOS CS Amplifier: Monte Carlo Output Voltage ({NUMRUNS} runs)\n"
        r"Process: $\sigma_{R_D}=5\%$, $\sigma_{V_{GS}}=2\%$"
    )
    ax.legend()
    ax.grid(True, linestyle="--", alpha=0.4)
    fig.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()
