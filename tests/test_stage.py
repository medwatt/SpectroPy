import numpy as np
import pytest

from spectropy import analyses
from spectropy.simulator.base import Runnable, Analysis, Scope
from spectropy.simulator.results import GroupResult, DcResult


def test_stage_is_scope():
    stage = analyses.Stage(inner=[analyses.OP()])
    assert isinstance(stage, Runnable)
    assert isinstance(stage, Scope)
    assert not isinstance(stage, Analysis)


def test_stage_rejects_empty_inner():
    with pytest.raises(ValueError, match="at least one inner"):
        analyses.Stage(inner=[])


def test_stage_emits_setup_then_inner_in_order():
    stage = analyses.Stage(
        name="cold",
        setup=[analyses.Alter(name="set_temp", param="temp", value=-40)],
        inner=[analyses.DC(param="vin", start=0, stop=1, step=0.1, name="dc_cold")],
    )
    cmd = stage.build_command()
    assert cmd == (
        "set_temp alter param=temp value=-40\n"
        "dc_cold dc param=vin start=0 stop=1 step=0.1"
    )


def test_stage_supports_altergroup_setup():
    stage = analyses.Stage(
        name="corner",
        setup=[analyses.AlterGroup(name="ag", parameters={"w": "1u"})],
        inner=[analyses.OP()],
    )
    cmd = stage.build_command()
    assert cmd.index("ag altergroup") < cmd.index("OpPoint dc")


def test_stage_no_setup_emits_only_inner():
    stage = analyses.Stage(inner=[analyses.OP(name="op")])
    assert stage.build_command() == "op dc"


def test_stage_collection_keyed_by_inner_name(tmp_path, monkeypatch):
    raw_dir = tmp_path / "spectre.raw"
    raw_dir.mkdir()
    (raw_dir / "dc_cold.dc").touch()

    monkeypatch.setattr(
        "spectropy.simulator.collection.parse_psf",
        lambda p: ({}, "vin", np.array([0.0, 1.0]), {"out": np.array([1.0, 2.0])}),
    )

    stage = analyses.Stage(
        name="cold",
        setup=[analyses.Alter(name="set_temp", param="temp", value=-40)],
        inner=[analyses.DC(param="vin", start=0, stop=1, step=0.5, name="dc_cold")],
    )

    group = stage.collect(raw_dir)
    assert isinstance(group, GroupResult)
    assert group.labels == ["dc_cold"]
    assert isinstance(group["dc_cold"], DcResult)
    assert isinstance(group[0], DcResult)
