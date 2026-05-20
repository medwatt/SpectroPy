import matplotlib.pyplot as plt
import numpy as np

from spectropy import SpectreSession, Circuit, SubCircuit, simulations
from examples.config import BACKEND, OUTDIR, FREEPDK45_DIR

VDD = 1.0
VCM = 0.5


def build_ota() -> SubCircuit:
    ota = SubCircuit(
        name="ota",
        nodes=["in_n", "in_p", "out", "vdd", "vss"],
    )
    ota.M("0", ("net2", "net2", "vss", "vss"), "NMOS_VTH", l="600n", w="1u")
    ota.M("1", ("out", "net2", "vss", "vss"), "NMOS_VTH", l="600n", w="1u")
    ota.I("10", ("net1", "vss"), dc="10u")
    ota.M("5", ("net1", "net1", "vdd", "vdd"), "PMOS_VTH", l="400n", w="5u")
    ota.M("4", ("net3", "net1", "vdd", "vdd"), "PMOS_VTH", l="400n", w="6u")
    ota.M("3", ("net2", "in_p", "net3", "vdd"), "PMOS_VTH", l="1500n", w="20u")
    ota.M("2", ("out", "in_n", "net3", "vdd"), "PMOS_VTH", l="1500n", w="20u")
    return ota


def build_netlist() -> Circuit:
    ota = build_ota()
    ckt = Circuit("OTA DC Transfer")
    ckt.include(f"{FREEPDK45_DIR}/nmos_vth.inc")
    ckt.include(f"{FREEPDK45_DIR}/pmos_vth.inc")
    ckt.global_nodes("0")
    ckt.parameters(vin=VCM)
    ckt.V("dd", ("vdd", "0"), dc=VDD)
    ckt.V("cm", ("vcm", "0"), dc=VCM)
    ckt.V("inp", ("inp", "0"), dc="vin")
    ckt.X("ota1", ("vcm", "inp", "out", "vdd", "0"), ota)
    ckt.save("out")
    ckt.save(
        "Xota1.M0:region",
        "Xota1.M1:region",
        "Xota1.M2:region",
        "Xota1.M3:region",
        "Xota1.M4:region",
        "Xota1.M5:region",
    )
    return ckt


def main() -> None:
    session = SpectreSession(backend=BACKEND)
    session.load_netlist(build_netlist().get_netlist())

    result = session.run(
        simulations.OP(),
        simulations.DC(param="vin", start=0, stop=VDD, step=0.01),
        stem="ota_dc",
        outdir=OUTDIR,
    )

    op_result = result[0]
    dc_result = result[1]

    print("\nOperating Point:")
    for name, val in op_result.voltages.items():
        print(f"  {name} = {np.real(val).item():.4f} V")

    vin = dc_result["vin"]
    vout = np.real(dc_result.voltages["out"])

    devices = ["M0", "M1", "M2", "M3", "M4", "M5"]
    regions = {dev: np.real(dc_result[f"Xota1.{dev}:region"]) for dev in devices}

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(7, 8), sharex=True)
    ax1.plot(vin, vout, linewidth=2)
    ax1.axvline(VCM, color="gray", linestyle="--", linewidth=1, label=f"$V_{{CM}}$ = {VCM} V")
    ax1.set_ylabel("$V_{out}$ (V)")
    ax1.set_title("OTA DC Transfer Characteristic")
    ax1.set_ylim(-0.05, VDD + 0.05)
    ax1.legend()
    ax1.grid(True, linestyle="--", alpha=0.4)
    for dev, region in regions.items():
        ax2.step(vin, region, where="post", label=dev)
    ax2.set_yticks([0, 1, 2, 3])
    ax2.set_yticklabels(["cutoff", "triode", "sat", "subth"])
    ax2.set_xlabel("$V_{in+}$ (V)")
    ax2.set_ylabel("Region")
    ax2.set_xlim(vin[0], vin[-1])
    ax2.legend(ncol=3)
    ax2.grid(True, linestyle="--", alpha=0.4)
    fig.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()
