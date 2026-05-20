import numpy as np

from spectropy import SpectreSession, Circuit, simulations
from examples.config import BACKEND, OUTDIR

R = 1000
C = 159e-9


def build_netlist() -> Circuit:
    ckt = Circuit("RC Low-Pass Filter: Pole-Zero")
    ckt.global_nodes("0")
    ckt.V("in", ("vin", "0"), dc=0)
    ckt.R("1", ("vin", "out"), R)
    ckt.C("1", ("out", "0"), C)
    ckt.save("out")
    return ckt


def main() -> None:
    session = SpectreSession(backend=BACKEND)
    session.load_netlist(build_netlist().get_netlist())

    result = session.run(
        simulations.PZ(output_pos="out", iprobe="Vin"),
        stem="rc_pz",
        outdir=OUTDIR,
    )

    poles = result.poles
    zeros = result.zeros

    if poles is not None:
        print("\nPoles (Hz):")
        for p in poles:
            print(f"  {p:+.6g}  ->  |f| = {abs(p.real):.4g} Hz")

    if zeros is not None:
        print("\nZeros (Hz):")
        for z in zeros:
            print(f"  {z:+.6g}  ->  |f| = {abs(z.real):.4g} Hz")

    print(f"\nExpected pole at ≈ {1.0 / (2 * np.pi * R * C):.4g} Hz")


if __name__ == "__main__":
    main()
