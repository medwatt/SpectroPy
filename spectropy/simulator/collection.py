# imports <<<
from __future__ import annotations

import warnings
from pathlib import Path

from .psf import parse_psf, parse_stb_margins
from .results import AnalysisResult, GroupResult
# >>>

# These helpers know how Spectre names PSF output files.  They are duck-typed on
# the runnable (they only touch ``name``, ``psf_stem``, ``margin_psf_stem``,
# ``make_result``, and ``inner``) so this module has no dependency on the
# runnable class hierarchy and can be imported freely by it.


def is_psf(path: Path) -> bool:
    return path.suffix != ".cache" and ".margin." not in path.name


def run_index(path: Path, outer_name: str) -> int:
    """Extract the numeric run index from a swept/grouped PSF filename."""
    name = path.name
    for separator in ("-", "_"):
        prefix = f"{outer_name}{separator}"
        if not name.startswith(prefix):
            continue
        rest = name[len(prefix) :]
        idx_str = rest.split("_")[0]
        try:
            return int(idx_str)
        except ValueError:
            pass
    return 0


def single_result(raw_dir: Path, analysis) -> AnalysisResult:
    """Collect one analysis run from ``{psf_stem}*`` files in ``raw_dir``."""
    stem = getattr(analysis, "psf_stem", None)
    if stem is None:
        return analysis.make_result({}, None, None, {})

    candidates = [p for p in sorted(raw_dir.glob(f"{stem}*")) if is_psf(p)]
    if not candidates:
        warnings.warn(
            f"No PSF files matching '{stem}*' found in {raw_dir}. "
            "Returning an empty result: signal access will raise KeyError. "
            "If using SSHBackend, this may indicate stale sshfs cache; use a unique stem per run.",
            stacklevel=2,
        )
        return analysis.make_result({}, None, None, {})

    meta, sweep_name, sweep, signals = parse_psf(candidates[0])

    margin_stem = getattr(analysis, "margin_psf_stem", None)
    if margin_stem is not None:
        margin_files = [p for p in raw_dir.glob(f"{margin_stem}*") if is_psf(p)]
        if margin_files:
            meta.update(parse_stb_margins(margin_files[0]))

    return analysis.make_result(meta, sweep_name, sweep, signals)


def collect_inner_runs(
    raw_dir: Path,
    outer_name: str,
    inner: tuple,
    separators: tuple[str, ...],
) -> list[list[AnalysisResult]]:
    """For each inner analysis, gather its results across all grouped runs.

    Spectre writes one PSF per (run, inner analysis) named
    ``{outer_name}{sep}{index}_{inner_stem}*``.  Returns a list parallel to
    ``inner``; entry ``i`` holds inner analysis ``i``'s result for every run, in
    run-index order.
    """
    inner_runs: list[list[AnalysisResult]] = [[] for _ in inner]

    for i, analysis in enumerate(inner):
        stem = getattr(analysis, "psf_stem", None)
        if stem is None:
            continue
        step_files = [
            p
            for separator in separators
            for p in raw_dir.glob(f"{outer_name}{separator}*_{stem}*")
            if is_psf(p)
        ]
        step_files = sorted(step_files, key=lambda p: run_index(p, outer_name))
        for path in step_files:
            meta, sweep_name, sw, signals = parse_psf(path)
            inner_runs[i].append(analysis.make_result(meta, sweep_name, sw, signals))

    return inner_runs


def group_inner_runs(
    inner_runs: list[list[AnalysisResult]],
    inner_count: int,
) -> list[list[AnalysisResult]]:
    """Transpose per-inner result lists into per-run result lists."""
    if not any(inner_runs):
        return []

    num_runs = max(len(r) for r in inner_runs)
    return [
        [inner_runs[j][i] for j in range(inner_count) if i < len(inner_runs[j])]
        for i in range(num_runs)
    ]


def grouped_result(
    raw_dir: Path,
    outer_name: str,
    inner: tuple,
    separators: tuple[str, ...],
    labels: list[str] | None = None,
) -> GroupResult:
    """Collect a scope's runs into a ``GroupResult``."""
    inner_runs = collect_inner_runs(raw_dir, outer_name, inner, separators)
    runs = group_inner_runs(inner_runs, len(inner))
    if labels is not None:
        labels = labels[: len(runs)]
    return GroupResult(runs, labels=labels)
