import numpy as np
import pytest

from spectropy import analyses
from spectropy.simulator.collector import collect_results
from spectropy.simulator.results import GroupResult, AcResult, DcResult, OpResult
from spectropy.simulator.base import Runnable, Analysis, Scope


def test_sweep_is_scope_not_analysis():
    sweep = analyses.Sweep(inner=(analyses.OP(),), param="temp", values=(0, 27))
    assert isinstance(sweep, Runnable)
    assert isinstance(sweep, Scope)
    assert not isinstance(sweep, Analysis)


def test_sweep_renders_multiple_inner_analyses():
    sweep = analyses.Sweep(
        inner=(
            analyses.OP(),
            analyses.AC(start=1, stop=1e6, sweep_type="dec", points=10),
        ),
        param="temp",
        values=(0, 27),
        name="tempswp",
    )
    cmd = sweep.build_command()
    assert cmd.startswith("tempswp sweep param=temp values=[0 27] {")
    assert "OpPoint dc" in cmd
    assert "analAC ac start=1 stop=1000000.0 dec=10" in cmd


def test_sweep_rejects_missing_range():
    with pytest.raises(ValueError, match="values"):
        analyses.Sweep(inner=(analyses.OP(),), param="temp")


def test_sweep_single_inner_collection(tmp_path, monkeypatch):
    raw_dir = tmp_path / "spectre.raw"
    raw_dir.mkdir()
    (raw_dir / "tempswp-000_dcswp.dc").touch()
    (raw_dir / "tempswp-001_dcswp.dc").touch()

    def fake_parse(path):
        idx = int(path.name.split("-")[1].split("_")[0])
        return {}, "vin", np.array([0.0, 1.0]), {"out": np.array([idx, idx + 1])}

    monkeypatch.setattr("spectropy.simulator.collection.parse_psf", fake_parse)

    sweep = analyses.Sweep(
        inner=(analyses.DC(param="vin", start=0, stop=1, step=0.1),),
        param="temp",
        values=(0, 27),
        name="tempswp",
    )

    result = collect_results(raw_dir, (sweep,))
    group = result["tempswp"]

    assert isinstance(group, GroupResult)
    assert len(group) == 2
    assert group.labels == ["0", "27"]
    assert isinstance(group[0], DcResult)
    assert np.array_equal(group[0]["out"], np.array([0, 1]))
    assert np.array_equal(group["27"]["out"], np.array([1, 2]))


def test_sweep_multiple_inner_collection_groups_by_point(tmp_path, monkeypatch):
    raw_dir = tmp_path / "spectre.raw"
    raw_dir.mkdir()
    for idx in range(2):
        (raw_dir / f"tempswp-{idx:03d}_OpPoint.dc").touch()
        (raw_dir / f"tempswp-{idx:03d}_analAC.ac").touch()

    def fake_parse(path):
        idx = int(path.name.split("-")[1].split("_")[0])
        if "OpPoint" in path.name:
            return {}, None, None, {"out": np.array([idx])}
        return {}, "freq", np.array([1.0, 10.0]), {"out": np.array([idx, idx + 1])}

    monkeypatch.setattr("spectropy.simulator.collection.parse_psf", fake_parse)

    sweep = analyses.Sweep(
        inner=(
            analyses.OP(),
            analyses.AC(start=1, stop=10, sweep_type="dec", points=1),
        ),
        param="temp",
        values=(0, 27),
        name="tempswp",
    )

    group = collect_results(raw_dir, (sweep,))["tempswp"]

    assert len(group) == 2
    assert isinstance(group[0], list)
    assert isinstance(group[0][0], OpResult)
    assert isinstance(group[0][1], AcResult)
    assert np.array_equal(group[0][0]["out"], np.array([0]))
    assert np.array_equal(group[1][1]["out"], np.array([1, 2]))
