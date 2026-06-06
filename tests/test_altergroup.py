import pytest
from spectropy import analyses
from spectropy.simulator.base import Runnable


# --- AlterGroup is a plain configuration object, not a Runnable ---

def test_altergroup_is_not_runnable():
    ag = analyses.AlterGroup(name="corner_tt")
    assert not isinstance(ag, Runnable)


# --- build_command rendering ---

def test_altergroup_empty():
    ag = analyses.AlterGroup(name="corner_tt")
    assert ag.build_command() == "corner_tt altergroup {}"


def test_altergroup_parameters_only():
    ag = analyses.AlterGroup(name="ag", parameters={"w_n": "500n", "w_p": "1u"})
    result = ag.build_command()
    assert result == "ag altergroup {\n    parameters w_n=500n w_p=1u\n}"


def test_altergroup_options_only():
    ag = analyses.AlterGroup(name="ag", options={"temp": 85})
    result = ag.build_command()
    assert result == "ag altergroup {\n    ag_opts options temp=85\n}"


def test_altergroup_parameters_and_options():
    ag = analyses.AlterGroup(
        name="corner_tt",
        parameters={"w_n": "500n", "w_p": "1u"},
        options={"temp": 27},
    )
    lines = ag.build_command().splitlines()
    assert lines[0] == "corner_tt altergroup {"
    assert lines[1] == "    parameters w_n=500n w_p=1u"
    assert lines[2] == "    corner_tt_opts options temp=27"
    assert lines[3] == "}"


def test_altergroup_raw_only():
    ag = analyses.AlterGroup(
        name="ag",
        raw=["model mybsim bsim3v3 lmax=1e-6", "m1 (n1 n2 n3 n4) mybsim w=0.3u l=1.2u"],
    )
    lines = ag.build_command().splitlines()
    assert lines[1] == "    model mybsim bsim3v3 lmax=1e-6"
    assert lines[2] == "    m1 (n1 n2 n3 n4) mybsim w=0.3u l=1.2u"


def test_altergroup_ordering_params_then_options_then_raw():
    ag = analyses.AlterGroup(
        name="ag",
        parameters={"p": 1},
        options={"temp": 27},
        raw=["model mymod resistor r1=1e3"],
    )
    lines = ag.build_command().splitlines()
    assert "parameters" in lines[1]
    assert "options" in lines[2]
    assert "model" in lines[3]


def test_altergroup_multiple_options():
    ag = analyses.AlterGroup(name="ag", options={"temp": 27, "tnom": 27})
    result = ag.build_command()
    assert "temp=27" in result
    assert "tnom=27" in result


def test_altergroup_str_delegates_to_build_command():
    ag = analyses.AlterGroup(name="ag", parameters={"x": 1})
    assert str(ag) == ag.build_command()


def test_altergroup_dicts_are_copied():
    params = {"x": 1}
    opts = {"temp": 27}
    ag = analyses.AlterGroup(name="ag", parameters=params, options=opts)
    params["y"] = 2
    opts["tnom"] = 27
    assert "y" not in ag.parameters
    assert "tnom" not in ag.options


# --- validation ---

def test_altergroup_rejects_empty_name():
    with pytest.raises(ValueError, match="non-empty name"):
        analyses.AlterGroup(name="")
