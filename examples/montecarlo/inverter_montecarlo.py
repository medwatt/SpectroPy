import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import norm

from spectropy import SpectreSession, Circuit, SubCircuit, simulations
from examples.config import BACKEND, OUTDIR, FREEPDK45_DIR

VDD = 1.0
W_N_NOM = "500n"
W_P_NOM = "1u"
NUMRUNS = 100


def build_netlist() -> Circuit:
    inv = SubCircuit(
        name="inverter",
        nodes=["in", "out", "vdd", "vss"],
        params={"w_n": W_N_NOM, "w_p": W_P_NOM},
    )
    inv.M("n", ("out", "in", "vss", "vss"), "NMOS_VTH", w="w_n", l="45n")
    inv.M("p", ("out", "in", "vdd", "vdd"), "PMOS_VTH", w="w_p", l="45n")

    ckt = Circuit("CMOS Inverter Monte Carlo")
    ckt.include(f"{FREEPDK45_DIR}/nmos_vth.inc")
    ckt.include(f"{FREEPDK45_DIR}/pmos_vth.inc")
    ckt.global_nodes("0")
    ckt.parameters(vin=0.5, w_n=W_N_NOM, w_p=W_P_NOM)
    ckt.V("dd", ("vdd", "0"), dc=VDD)
    ckt.V("in", ("in", "0"), dc="vin")
    ckt.X("inv", ("in", "out", "vdd", "0"), inv, params={"w_n": "w_n", "w_p": "w_p"})
    ckt.save("in", "out")
    return ckt


def switching_point(vin: np.ndarray, vout: np.ndarray) -> float:
    """Find the input voltage where Vout = Vin."""
    diff = vout - vin
    idx = np.where(np.diff(np.sign(diff)))[0]
    if len(idx) == 0:
        return float("nan")
    i = idx[0]
    return float(vin[i] - diff[i] * (vin[i + 1] - vin[i]) / (diff[i + 1] - diff[i]))


def main() -> None:
    session = SpectreSession(backend=BACKEND)
    session.load_netlist(build_netlist().get_netlist())

    dc_nom = simulations.DC(param="vin", start=0, stop=VDD, step=0.005, name="dc_nom")

    stats = simulations.Statistics(
        process=[
            simulations.Vary("w_n", dist="gauss", std=10, percent=True),
            simulations.Vary("w_p", dist="gauss", std=10, percent=True),
        ]
    )

    mc = simulations.MonteCarlo(
        inner=[simulations.DC(param="vin", start=0, stop=VDD, step=0.005)],
        numruns=NUMRUNS,
        variations="process",
        seed=42,
    )

    results = session.run(dc_nom, stats, mc, stem="inverter_montecarlo", outdir=OUTDIR)
    nom_result = results[0]
    mc_result = results[1]

    vin_nom = nom_result["vin"]
    vout_nom = np.real(nom_result.voltages["out"])
    vm_nom = switching_point(vin_nom, vout_nom)

    vm_vals = []
    for run in mc_result:
        vin_run = run["vin"]
        vout_run = np.real(run.voltages["out"])
        vm = switching_point(vin_run, vout_run)
        if not np.isnan(vm):
            vm_vals.append(vm)

    vm_arr = np.array(vm_vals)
    mu, sigma = vm_arr.mean(), vm_arr.std()
    print(f"Vm nominal : {vm_nom * 1e3:.1f} mV")
    print(f"Vm MC mean : {mu * 1e3:.1f} mV  $\\sigma$ = {sigma * 1e3:.2f} mV")

    fig, (ax_dc, ax_hist) = plt.subplots(1, 2, figsize=(12, 5))

    for run in mc_result:
        vin_run = run["vin"]
        vout_run = np.real(run.voltages["out"])
        ax_dc.plot(vin_run, vout_run, color="steelblue", alpha=0.12, linewidth=0.8)

    ax_dc.plot(vin_nom, vout_nom, color="black", linewidth=2, label="Nominal")
    ax_dc.plot([0, VDD], [0, VDD], color="gray", linestyle="--", linewidth=1, label="$V_{out}=V_{in}$")
    ax_dc.axvline(vm_nom, color="black", linestyle=":", linewidth=1, label=f"$V_m$ = {vm_nom*1e3:.0f} mV")
    ax_dc.set_xlabel("$V_{in}$ (V)")
    ax_dc.set_ylabel("$V_{out}$ (V)")
    ax_dc.set_title("DC Transfer Characteristic")
    ax_dc.set_xlim(0, VDD)
    ax_dc.set_ylim(-0.05, VDD + 0.05)
    ax_dc.legend(fontsize=9)
    ax_dc.grid(True, linestyle="--", alpha=0.3)

    ax_hist.hist(
        vm_arr * 1e3, bins=20, density=True,
        color="steelblue", alpha=0.7, edgecolor="white"
    )
    x = np.linspace(vm_arr.min(), vm_arr.max(), 300) * 1e3
    ax_hist.plot(x, norm.pdf(x, mu * 1e3, sigma * 1e3), color="tomato", linewidth=2, label="Gaussian fit")
    ax_hist.axvline(mu * 1e3, color="black", linestyle="--", linewidth=1.2, label=f"Mean = {mu*1e3:.1f} mV")
    ax_hist.axvline((mu - sigma) * 1e3, color="gray", linestyle=":", linewidth=1)
    ax_hist.axvline((mu + sigma) * 1e3, color="gray", linestyle=":", linewidth=1, label=f"$\\sigma$ = {sigma*1e3:.2f} mV")
    ax_hist.set_xlabel("$V_m$ (mV)")
    ax_hist.set_ylabel("Probability density")
    ax_hist.set_title("Switching Point Distribution")
    ax_hist.legend(fontsize=9)
    ax_hist.grid(True, linestyle="--", alpha=0.3)

    fig.suptitle(
        f"CMOS Inverter: Monte Carlo Switching Point ({NUMRUNS} runs)\n"
        r"Process: $\sigma_{W_N} = \sigma_{W_P} = 10\%$",
        fontsize=12,
    )
    fig.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()
