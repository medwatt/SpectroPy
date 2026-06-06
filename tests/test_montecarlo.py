import numpy as np
import pytest
from spectropy import analyses
from spectropy.simulator.base import Runnable, Analysis, Scope
from spectropy.simulator.collector import collect_results
from spectropy.simulator.results import GroupResult, OpResult, DcResult


# ---------------------------------------------------------------------------
# Class hierarchy
# ---------------------------------------------------------------------------

def test_montecarlo_is_scope():
    mc = analyses.MonteCarlo(inner=[analyses.OP()])
    assert isinstance(mc, Runnable)
    assert isinstance(mc, Scope)


def test_montecarlo_is_not_analysis():
    mc = analyses.MonteCarlo(inner=[analyses.OP()])
    assert not isinstance(mc, Analysis)


# ---------------------------------------------------------------------------
# build_command rendering
# ---------------------------------------------------------------------------

def test_montecarlo_basic():
    mc = analyses.MonteCarlo(
        inner=[analyses.OP()], name="mc", numruns=100, variations="all"
    )
    cmd = mc.build_command()
    assert cmd.startswith("mc montecarlo")
    assert "numruns=100" in cmd
    assert "variations=all" in cmd


def test_montecarlo_seed():
    mc = analyses.MonteCarlo(inner=[analyses.OP()], numruns=50, seed=42)
    assert "seed=42" in mc.build_command()


def test_montecarlo_no_seed_omitted():
    mc = analyses.MonteCarlo(inner=[analyses.OP()], numruns=50)
    assert "seed" not in mc.build_command()


def test_montecarlo_inner_rendered():
    mc = analyses.MonteCarlo(
        inner=[analyses.DC(param="vin", start=0, stop=1, step=0.01)],
        name="mc",
        numruns=10,
    )
    cmd = mc.build_command()
    assert "dcswp dc" in cmd
    assert "param=vin" in cmd


def test_montecarlo_no_statistics_omits_block():
    mc = analyses.MonteCarlo(inner=[analyses.OP()], numruns=5)
    assert "statistics" not in mc.build_command()


def test_montecarlo_block_braces():
    mc = analyses.MonteCarlo(inner=[analyses.OP()], name="mc", numruns=5)
    cmd = mc.build_command()
    assert "{" in cmd and "}" in cmd
    assert cmd.endswith("}")


def test_montecarlo_str_delegates():
    mc = analyses.MonteCarlo(inner=[analyses.OP()])
    assert str(mc) == mc.build_command()


def test_montecarlo_savefamilyplots_default_yes():
    mc = analyses.MonteCarlo(inner=[analyses.OP()], numruns=10)
    assert "savefamilyplots=yes" in mc.build_command()


def test_montecarlo_savefamilyplots_false():
    mc = analyses.MonteCarlo(inner=[analyses.OP()], numruns=10, savefamilyplots=False)
    assert "savefamilyplots=no" in mc.build_command()


def test_montecarlo_extra_params():
    mc = analyses.MonteCarlo(inner=[analyses.OP()], numruns=10, donominal="yes")
    assert "donominal=yes" in mc.build_command()


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def test_montecarlo_rejects_empty_inner():
    with pytest.raises(ValueError, match="at least one inner"):
        analyses.MonteCarlo(inner=[])


def test_montecarlo_rejects_invalid_variations():
    with pytest.raises(ValueError, match="variations must be one of"):
        analyses.MonteCarlo(inner=[analyses.OP()], variations="random")


# ---------------------------------------------------------------------------
# collect_results routes MonteCarlo to a GroupResult keyed by name
# ---------------------------------------------------------------------------

def test_collect_results_routes_mc(tmp_path, monkeypatch):
    raw_dir = tmp_path / "spectre.raw"
    raw_dir.mkdir()
    for i in range(3):
        (raw_dir / f"mc-{i:03d}_OpPoint.dc").touch()

    monkeypatch.setattr(
        "spectropy.simulator.collection.parse_psf",
        lambda p: ({}, None, None, {"out": np.array([0.5])}),
    )

    mc = analyses.MonteCarlo(inner=[analyses.OP()], numruns=3, name="mc")
    result = collect_results(raw_dir, (mc,))

    assert len(result) == 1
    group = result["mc"]
    assert isinstance(group, GroupResult)
    assert group.numruns == 3
    assert isinstance(group[0], OpResult)


# ---------------------------------------------------------------------------
# GroupResult interface (shared by all scopes)
# ---------------------------------------------------------------------------

def _make_op() -> OpResult:
    return OpResult(meta={}, signals={"out": np.array([0.5])})


def test_group_single_inner_indexing():
    runs = [[_make_op()] for _ in range(3)]
    group = GroupResult(runs)
    assert len(group) == 3
    assert isinstance(group[0], OpResult)


def test_group_single_inner_iteration():
    runs = [[_make_op()] for _ in range(4)]
    group = GroupResult(runs)
    for run in group:
        assert isinstance(run, OpResult)


def test_group_multiple_inner_returns_list():
    op = _make_op()
    dc = DcResult(meta={}, sweep_name="vin", sweep=np.array([0.0]), signals={})
    runs = [[op, dc] for _ in range(2)]
    group = GroupResult(runs)
    run = group[0]
    assert isinstance(run, list)
    assert isinstance(run[0], OpResult)
    assert isinstance(run[1], DcResult)


def test_group_numruns():
    group = GroupResult([[_make_op()] for _ in range(7)])
    assert group.numruns == 7


def test_group_empty():
    group = GroupResult([])
    assert len(group) == 0
    assert group.numruns == 0
