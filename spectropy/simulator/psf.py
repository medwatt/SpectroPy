# imports <<<
from __future__ import annotations

from pathlib import Path

import numpy as np
from psf_utils import PSF
# >>>

def parse_psf(
    path: Path,
) -> tuple[dict, str | None, np.ndarray | None, dict[str, np.ndarray]]:
    psf = PSF(str(path))

    sweep_name: str | None = None
    sweep: np.ndarray | None = None
    if psf.sweeps:
        sw = psf.get_sweep()
        if sw is not None:
            sweep_name = sw.name
            sweep = np.asarray(sw.abscissa, dtype=float)

    signals: dict[str, np.ndarray] = {}
    for sig in psf.all_signals():
        if isinstance(sig.ordinate, str):
            continue
        signals[sig.name] = np.atleast_1d(np.asarray(sig.ordinate))

    return dict(psf.meta), sweep_name, sweep, signals


def parse_stb_margins(path: Path) -> dict:
    margins: dict = {}
    for sig in PSF(str(path)).all_signals():
        if isinstance(sig.ordinate, str):
            continue
        try:
            margins[sig.name] = float(complex(sig.ordinate).real)
        except (TypeError, ValueError):
            pass
    return margins
