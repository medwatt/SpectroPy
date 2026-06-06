import pytest
from spectropy import analyses
from spectropy.simulator.base import Runnable


# --- Alter is a plain configuration object, not a Runnable ---

def test_alter_is_not_runnable():
    a = analyses.Alter(name="chg1", param="temp", value=75)
    assert not isinstance(a, Runnable)


# --- build_command rendering ---

def test_alter_temperature():
    a = analyses.Alter(name="chg1", param="temp", value=75)
    assert a.build_command() == "chg1 alter param=temp value=75"


def test_alter_top_level_param():
    a = analyses.Alter(name="scale1", param="vds_val", value=0.25)
    assert a.build_command() == "scale1 alter param=vds_val value=0.25"


def test_alter_dev():
    a = analyses.Alter(name="bias1", param="dc", value=1.2, dev="VDD")
    assert a.build_command() == "bias1 alter dev=VDD param=dc value=1.2"


def test_alter_mod():
    a = analyses.Alter(name="rmod1", param="r1", value="1e3", mod="rtt")
    assert a.build_command() == "rmod1 alter mod=rtt param=r1 value=1e3"


def test_alter_sub():
    a = analyses.Alter(name="sub1", param="w", value="0.5u", sub="x1")
    assert a.build_command() == "sub1 alter sub=x1 param=w value=0.5u"


def test_alter_str_delegates_to_build_command():
    a = analyses.Alter(name="chg1", param="temp", value=27)
    assert str(a) == a.build_command()


# --- validation ---

def test_alter_rejects_multiple_targets():
    with pytest.raises(ValueError, match="at most one"):
        analyses.Alter(name="bad", param="r", value=1, dev="r1", mod="rmod")


def test_alter_rejects_dev_mod_sub_together():
    with pytest.raises(ValueError, match="at most one"):
        analyses.Alter(name="bad", param="r", value=1, dev="r1", sub="x1")
