import pytest
from spectropy import analyses
from spectropy.simulator.base import Runnable


# ---------------------------------------------------------------------------
# Vary
# ---------------------------------------------------------------------------

def test_vary_gauss_std():
    v = analyses.Vary("rshsp", dist="gauss", std=12)
    assert v.build_line() == "vary rshsp dist=gauss std=12"


def test_vary_with_string_std():
    v = analyses.Vary("rshpi", dist="gauss", std="rshpi_std")
    assert v.build_line() == "vary rshpi dist=gauss std=rshpi_std"


def test_vary_N():
    v = analyses.Vary("uuu", dist="unif", N=10)
    assert v.build_line() == "vary uuu dist=unif N=10"


def test_vary_percent_yes():
    v = analyses.Vary("rshsp", dist="gauss", std=12, percent=True)
    assert "percent=yes" in v.build_line()


def test_vary_percent_no():
    v = analyses.Vary("rshsp", dist="gauss", std=12, percent=False)
    assert "percent=no" in v.build_line()


def test_vary_lnorm():
    v = analyses.Vary("gain", dist="lnorm", std=12)
    assert "dist=lnorm" in v.build_line()


def test_vary_str_delegates():
    v = analyses.Vary("x", dist="gauss", std=1)
    assert str(v) == v.build_line()


def test_vary_rejects_invalid_dist():
    with pytest.raises(ValueError, match="dist must be one of"):
        analyses.Vary("x", dist="normal", std=1)


def test_vary_rejects_neither_std_nor_N():
    with pytest.raises(ValueError, match="either std or N"):
        analyses.Vary("x", dist="gauss")


def test_vary_rejects_both_std_and_N():
    with pytest.raises(ValueError, match="either std or N, not both"):
        analyses.Vary("x", dist="gauss", std=1, N=2)


# ---------------------------------------------------------------------------
# Correlate
# ---------------------------------------------------------------------------

def test_correlate_process_level():
    c = analyses.Correlate(param=["rshsp", "rshpi"], cc=0.6)
    assert c.build_line() == "correlate param=[rshsp rshpi] cc=0.6"


def test_correlate_instance_level():
    c = analyses.Correlate(dev=["m1", "m2"], param=["xisn", "xisp"], cc=0.8)
    assert c.build_line() == "correlate dev=[m1 m2] param=[xisn xisp] cc=0.8"


def test_correlate_dev_only():
    c = analyses.Correlate(dev=["m1", "m2"], cc=0.5)
    assert c.build_line() == "correlate dev=[m1 m2] cc=0.5"


def test_correlate_wildcard():
    c = analyses.Correlate(dev=["m1", "I*.*M3"], param=["xisn"], cc=0.8)
    assert "I*.*M3" in c.build_line()


def test_correlate_str_delegates():
    c = analyses.Correlate(param=["a", "b"], cc=0.5)
    assert str(c) == c.build_line()


def test_correlate_rejects_cc_out_of_range():
    with pytest.raises(ValueError, match="cc must be between"):
        analyses.Correlate(param=["a"], cc=1.5)

    with pytest.raises(ValueError, match="cc must be between"):
        analyses.Correlate(param=["a"], cc=-1.1)


def test_correlate_boundary_cc():
    analyses.Correlate(param=["a"], cc=1.0)
    analyses.Correlate(param=["a"], cc=-1.0)


# ---------------------------------------------------------------------------
# Statistics -- configuration object, not a Runnable
# ---------------------------------------------------------------------------

def test_statistics_is_not_runnable():
    s = analyses.Statistics()
    assert not isinstance(s, Runnable)


# ---------------------------------------------------------------------------
# Statistics -- rendering
# ---------------------------------------------------------------------------

def test_statistics_empty():
    s = analyses.Statistics()
    assert s.build_command() == "statistics {}"


def test_statistics_process_only():
    s = analyses.Statistics(
        process=[analyses.Vary("rshsp", dist="gauss", std=12)]
    )
    result = s.build_command()
    lines = result.splitlines()
    assert lines[0] == "statistics {"
    assert lines[1] == "    process {"
    assert lines[2] == "        vary rshsp dist=gauss std=12"
    assert lines[3] == "    }"
    assert lines[4] == "}"


def test_statistics_mismatch_only():
    s = analyses.Statistics(
        mismatch=[analyses.Vary("xisn", dist="gauss", std=0.5)]
    )
    result = s.build_command()
    assert "    mismatch {" in result
    assert "        vary xisn dist=gauss std=0.5" in result


def test_statistics_process_truncate():
    s = analyses.Statistics(
        process=[analyses.Vary("rshsp", dist="gauss", std=12)],
        process_truncate=2.0,
    )
    result = s.build_command()
    assert "        truncate tr=2.0" in result


def test_statistics_mismatch_truncate():
    s = analyses.Statistics(
        mismatch=[analyses.Vary("xisn", dist="gauss", std=0.5)],
        mismatch_truncate=7.0,
    )
    result = s.build_command()
    assert "        truncate tr=7.0" in result


def test_statistics_top_level_truncate():
    s = analyses.Statistics(truncate=6.0)
    result = s.build_command()
    assert "    truncate tr=6.0" in result


def test_statistics_correlate_at_top_level():
    s = analyses.Statistics(
        correlate=[analyses.Correlate(param=["rshsp", "rshpi"], cc=0.6)]
    )
    result = s.build_command()
    lines = result.splitlines()
    correlate_line = next(l for l in lines if "correlate" in l)
    assert correlate_line.startswith("    correlate"), (
        "correlate must be at statistics top level (4-space indent)"
    )


def test_statistics_full_block():
    s = analyses.Statistics(
        process=[
            analyses.Vary("rshsp", dist="gauss", std=12, percent=True),
            analyses.Vary("rshpi", dist="gauss", std="rshpi_std"),
        ],
        mismatch=[
            analyses.Vary("xisn", dist="gauss", std=0.5),
            analyses.Vary("xisp", dist="gauss", std=0.5),
        ],
        correlate=[
            analyses.Correlate(param=["rshsp", "rshpi"], cc=0.6),
            analyses.Correlate(dev=["m1", "m2"], param=["xisn", "xisp"], cc=0.8),
        ],
        process_truncate=2.0,
        mismatch_truncate=7.0,
        truncate=6.0,
    )
    result = s.build_command()
    assert result == (
        "statistics {\n"
        "    process {\n"
        "        vary rshsp dist=gauss std=12 percent=yes\n"
        "        vary rshpi dist=gauss std=rshpi_std\n"
        "        truncate tr=2.0\n"
        "    }\n"
        "    mismatch {\n"
        "        vary xisn dist=gauss std=0.5\n"
        "        vary xisp dist=gauss std=0.5\n"
        "        truncate tr=7.0\n"
        "    }\n"
        "    correlate param=[rshsp rshpi] cc=0.6\n"
        "    correlate dev=[m1 m2] param=[xisn xisp] cc=0.8\n"
        "    truncate tr=6.0\n"
        "}"
    )


def test_statistics_process_truncate_only_renders_block():
    s = analyses.Statistics(process_truncate=3.0)
    result = s.build_command()
    assert "    process {" in result
    assert "        truncate tr=3.0" in result


# ---------------------------------------------------------------------------
# Statistics is consumed by MonteCarlo, emitted before the montecarlo block
# ---------------------------------------------------------------------------

def test_statistics_emitted_by_montecarlo():
    mc = analyses.MonteCarlo(
        inner=[analyses.OP()],
        statistics=analyses.Statistics(
            process=[analyses.Vary("x", dist="gauss", std=1)]
        ),
        numruns=5,
        name="mc",
    )
    cmd = mc.build_command()
    assert cmd.index("statistics {") < cmd.index("mc montecarlo")
