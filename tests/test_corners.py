import numpy as np
import pytest

from spectropy import analyses
from spectropy.simulator.collection import run_index
from spectropy.simulator.results import GroupResult, DcResult
from spectropy.simulator.base import Runnable, Analysis, Scope


def test_corners_is_scope_not_analysis():
    corners = analyses.Corners(
        corners=[analyses.Corner("tt", "models.scs")],
        inner=[analyses.OP()],
    )
    assert isinstance(corners, Runnable)
    assert isinstance(corners, Scope)
    assert not isinstance(corners, Analysis)


def test_corner_rejects_empty_section_or_file():
    with pytest.raises(ValueError, match="section"):
        analyses.Corner("", "models.scs")
    with pytest.raises(ValueError, match="file"):
        analyses.Corner("tt", "")


def test_corner_temp_conflict_rejected():
    with pytest.raises(ValueError, match="conflicts"):
        analyses.Corner("tt", "models.scs", temp=27, options={"temp": 85})


def test_corners_basic_altergroup_rendering_uses_legal_analysis_names():
    corners = analyses.Corners(
        corners=[
            analyses.Corner("tt", "models.scs"),
            analyses.Corner("ss", "models.scs"),
        ],
        inner=[analyses.DC(param="vin", start=0, stop=1, step=0.01)],
        name="pvt",
    )

    cmd = corners.build_command()

    assert 'pvt_alter_000 altergroup {\n    include "models.scs" section=tt\n}' in cmd
    assert 'pvt_alter_001 altergroup {\n    include "models.scs" section=ss\n}' in cmd
    assert "pvt_000_dcswp dc param=vin start=0 stop=1 step=0.01" in cmd
    assert "pvt_001_dcswp dc param=vin start=0 stop=1 step=0.01" in cmd
    assert "pvt-000_dcswp" not in cmd


def test_corners_pvt_rendering():
    corners = analyses.Corners(
        corners=[
            analyses.Corner(
                "ss", "models.scs", temp=125, parameters={"vdd": 0.9}, label="ss_0v9_125c"
            ),
        ],
        inner=[analyses.OP()],
        name="pvt",
    )

    lines = corners.build_command().splitlines()

    assert lines[1] == '    include "models.scs" section=ss'
    assert lines[2] == "    parameters vdd=0.9"
    assert lines[3] == "    pvt_alter_000_opts options temp=125"
    assert corners.labels == ["ss_0v9_125c"]


def test_corners_reject_empty_inputs():
    with pytest.raises(ValueError, match="at least one corner"):
        analyses.Corners(corners=[], inner=[analyses.OP()])

    with pytest.raises(ValueError, match="at least one inner"):
        analyses.Corners(corners=[analyses.Corner("tt", "models.scs")], inner=[])


def test_run_index_accepts_underscore_and_hyphen_prefixes(tmp_path):
    underscore = tmp_path / "pvt_012_dcswp.dc"
    hyphen = tmp_path / "mc-034_dcswp.dc"

    assert run_index(underscore, "pvt") == 12
    assert run_index(hyphen, "mc") == 34


def test_corners_collection_label_indexing(tmp_path, monkeypatch):
    raw_dir = tmp_path / "spectre.raw"
    raw_dir.mkdir()
    for i in range(2):
        (raw_dir / f"pvt_{i:03d}_dcswp.dc").touch()

    monkeypatch.setattr(
        "spectropy.simulator.collection.parse_psf",
        lambda p: ({}, "vin", np.array([0.0, 1.0]), {"out": np.array([1.0, 0.0])}),
    )

    corners = analyses.Corners(
        corners=[analyses.Corner("tt", "m.scs"), analyses.Corner("ss", "m.scs")],
        inner=[analyses.DC(param="vin", start=0, stop=1, step=0.5)],
        name="pvt",
    )

    group = corners.collect(raw_dir)
    assert isinstance(group, GroupResult)
    assert group.labels == ["tt", "ss"]
    assert isinstance(group["tt"], DcResult)
    assert [label for label, _ in group.items()] == ["tt", "ss"]
