# imports <<<
from __future__ import annotations

import warnings
from pathlib import Path
from typing import cast

from .psf import parse_psf, parse_stb_margins
from .base import Runnable, Statement, Simulation
from .analyses import Sweep, MonteCarlo, Corners
from .results import (
    AnalysisResult,
    SpectreResult,
    SweepPointResult,
    MonteCarloResult,
    CornersResult,
)
# >>>


def _is_psf(path: Path) -> bool:
    return path.suffix != ".cache" and ".margin." not in path.name


def _run_index(path: Path, outer_name: str) -> int:
    """Extract the numeric run index from a Monte Carlo PSF filename."""
    name = path.name
    for separator in ("-", "_"):
        prefix = f"{outer_name}{separator}"
        if not name.startswith(prefix):
            continue
        rest = name[len(prefix):]
        idx_str = rest.split("_")[0]
        try:
            return int(idx_str)
        except ValueError:
            pass
    return 0


def _single_result(raw_dir: Path, runnable: Simulation) -> SpectreResult:
    stem = getattr(runnable, "psf_stem", None)
    if stem is None:
        return runnable.make_result({}, None, None, {})

    candidates = [p for p in sorted(raw_dir.glob(f"{stem}*")) if _is_psf(p)]
    if not candidates:
        warnings.warn(
            f"No PSF files matching '{stem}*' found in {raw_dir}. "
            "Returning an empty result: signal access will raise KeyError. "
            "If using SSHBackend, this may indicate stale sshfs cache; use a unique stem per run.",
            stacklevel=2,
        )
        return runnable.make_result({}, None, None, {})

    meta, sweep_name, sweep, signals = parse_psf(candidates[0])

    margin_stem = getattr(runnable, "margin_psf_stem", None)
    if margin_stem is not None:
        margin_files = [p for p in raw_dir.glob(f"{margin_stem}*") if _is_psf(p)]
        if margin_files:
            meta.update(parse_stb_margins(margin_files[0]))

    return runnable.make_result(meta, sweep_name, sweep, signals)


def _collect_inner_runs(
    raw_dir: Path,
    outer_name: str,
    inner: tuple[Simulation, ...],
    separators: tuple[str, ...],
) -> list[list[SpectreResult]]:
    inner_runs: list[list[SpectreResult]] = [[] for _ in inner]

    for i, analysis in enumerate(inner):
        stem = getattr(analysis, "psf_stem", None)
        if stem is None:
            continue
        step_files = [
            p
            for separator in separators
            for p in raw_dir.glob(f"{outer_name}{separator}*_{stem}*")
            if _is_psf(p)
        ]
        step_files = sorted(step_files, key=lambda p: _run_index(p, outer_name))
        for path in step_files:
            meta, sweep_name, sw, signals = parse_psf(path)
            inner_runs[i].append(analysis.make_result(meta, sweep_name, sw, signals))

    return inner_runs


def _group_inner_runs(
    inner_runs: list[list[SpectreResult]],
    inner_count: int,
) -> list[list[SpectreResult]]:
    if not any(inner_runs):
        return []

    num_runs = max(len(r) for r in inner_runs)
    return [
        [inner_runs[j][i] for j in range(inner_count) if i < len(inner_runs[j])]
        for i in range(num_runs)
    ]


def _mc_results(raw_dir: Path, mc: MonteCarlo) -> MonteCarloResult:
    inner_runs = _collect_inner_runs(raw_dir, mc.name, mc.inner, ("-",))
    return MonteCarloResult(_group_inner_runs(inner_runs, len(mc.inner)))


def _sweep_results(raw_dir: Path, sweep: Sweep) -> list[AnalysisResult]:
    inner_runs = _collect_inner_runs(raw_dir, sweep.name, sweep.inner, ("-",))
    runs = _group_inner_runs(inner_runs, len(sweep.inner))
    return [run[0] if len(run) == 1 else SweepPointResult(run) for run in runs]


def _corners_results(raw_dir: Path, corners: Corners) -> CornersResult:
    inner_runs = _collect_inner_runs(raw_dir, corners.name, corners.inner, ("_", "-"))
    runs = _group_inner_runs(inner_runs, len(corners.inner))

    if not runs:
        return CornersResult(corners.labels, [])

    return CornersResult(corners.labels[: len(runs)], runs)


def collect_results(
    raw_dir: Path, runnables: tuple[Runnable, ...]
) -> list[AnalysisResult]:
    results: list[AnalysisResult] = []
    for runnable in runnables:
        if isinstance(runnable, Statement):
            continue
        elif isinstance(runnable, Sweep):
            results.extend(_sweep_results(raw_dir, runnable))
        elif isinstance(runnable, MonteCarlo):
            results.append(_mc_results(raw_dir, runnable))
        elif isinstance(runnable, Corners):
            results.append(_corners_results(raw_dir, runnable))
        else:
            results.append(_single_result(raw_dir, cast(Simulation, runnable)))
    return results
