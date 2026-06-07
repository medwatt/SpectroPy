# SpectroPy Reference

## Table of Contents

1. [Overview](#overview)
2. [Installation](#installation)
3. [Netlisting](#netlisting)
   - [Circuit](#circuit)
   - [Passive components](#passive-components)
   - [Independent sources](#independent-sources)
   - [Dependent sources](#dependent-sources)
   - [Semiconductors](#semiconductors)
   - [Switch](#switch)
   - [SubCircuit](#subcircuit)
   - [Verilog-A instances](#verilog-a-instances)
   - [Circuit control statements](#circuit-control-statements)
   - [Save statements](#save-statements)
   - [WaveformGenerator](#waveformgenerator)
4. [Simulation](#simulation)
   - [SpectreSession](#spectresession)
   - [Backends](#backends)
   - [Analyses](#analyses)
   - [Scopes](#scopes)
   - [Configuration objects](#configuration-objects)
   - [Accessing results](#accessing-results)
5. [Examples](#examples)

## Overview

SpectroPy is a Python library for building and simulating analog circuits using
Cadence Spectre as the simulation backend. Circuits are built programmatically
through a Python API and results are returned as numpy arrays.

```python
from spectropy import SpectreSession, Circuit, analyses

ckt = Circuit("RC Low-Pass Filter")
ckt.V("in", ("vin", "0"), dc=1, mag=1)
ckt.R("1", ("vin", "vout"), "1k")
ckt.C("1", ("vout", "0"), "1u")

session = SpectreSession()
session.load_netlist(ckt.get_netlist())

result = session.run(analyses.AC(start="1", stop="1e6", sweep_type="dec", points=20))
vout = result.voltages["vout"]
freq = result.frequency
```

## Installation

```bash
pip install git+https://github.com/medwatt/SpectroPy.git
```

Dependencies: `numpy`, `psf_utils`. Cadence Spectre must be accessible (locally
or on a remote server).

## Netlisting

### Circuit

All netlists start with a `Circuit` object. Components are added as method
calls. Call `get_netlist()` to obtain the list of strings for
`session.load_netlist()`, or `print(circuit)` to inspect the Spectre text.

```python
from spectropy import Circuit

ckt = Circuit("Diode Rectifier")
ckt.D("1", ("nout", "0"), "D1N4148")
ckt.R("1", ("nin", "nout"), "1k")
ckt.model("D1N4148", "diode", rs=10)

print(ckt)
netlist = ckt.get_netlist()
```

Component methods share the pattern `(id, nodes, ...)`. The `id` is
appended to the component letter (e.g. `"1"` produces `R1`). Nodes are
given as a tuple of strings. Duplicate `id` values for the same component
type raise a `ValueError`.

All component methods accept a trailing `**params` that are emitted as
Spectre keyword-value pairs.

### Passive components

```python
ckt.R("1", ("top", "bot"), "1k")                          # R1 top bot resistor r=1k
ckt.R("2", ("top", "bot"), "1k", temp="25")               # R2 top bot resistor r=1k temp=25
ckt.C("1", ("top", "bot"), "1n")                          # C1 top bot capacitor c=1n
ckt.L("1", ("top", "bot"), "1u")                          # L1 top bot inductor l=1u
```

### Independent sources

```python
# DC sources
ckt.V("in", ("vin", "0"), dc=5)                            # Vsource with dc=5
ckt.I("bias", ("net1", "0"), dc="10u")                     # Isource with dc=10u

# Sinusoidal
ckt.VoltageSin("1", ("in", "0"),
    amplitude="1", freq="1k", dc="0.5", phase=90, delay="1n")
ckt.CurrentSin("1", ("in", "0"), amplitude="1m", freq="1k")

# Pulse
ckt.VoltagePulse("1", ("in", "0"),
    val0=0, val1=3.3, period="1u", width="500n",
    delay="1n", rise="1n", fall="1n")
ckt.CurrentPulse("1", ("in", "0"),
    val0=0, val1="1m", period="1u", width="500n")

# Piecewise-linear
ckt.VoltagePWL("1", ("in", "0"),
    wave=[(0, 0), ("1m", 1), ("2m", 0)], pwlperiod="2m")
ckt.CurrentPWL("1", ("in", "0"),
    wave=[(0, 0), ("1u", "10u"), ("2u", 0)])
```

### Dependent sources

```python
# Voltage-controlled current source: out_nodes, ctrl_nodes
ckt.G("1", ("out", "0"), ("in", "0"), "1m")

# Voltage-controlled voltage source
ckt.E("1", ("out", "0"), ("in", "0"), "10")

# Current-controlled current source: probe is a voltage source id
ckt.F("1", ("out", "0"), "V1", gain="5")

# Current-controlled voltage source
ckt.H("1", ("out", "0"), "V1", transresistance="1k")

# Behavioral source: exactly one of voltage= or current=
ckt.B("1", ("out", "0"), voltage="V(a)*V(b)")
ckt.B("2", ("out", "0"), current="I(V1)*2")
```

### Semiconductors

```python
ckt.M("1", ("d", "g", "s", "b"), "NMOS_VTH", w="1u", l="45n")   # MOSFET
ckt.Q("1", ("c", "b", "e"), "NPN", area="10e-12")               # BJT
ckt.D("1", ("anode", "cathode"), "D1N4148")                     # Diode
```

Models are declared separately:

```python
ckt.model("NMOS_VTH", "nmos", vto=0.5, kp="200u")
ckt.model("D1N4148", "diode", rs=10, is="1e-14")
```

### Switch

```python
# 2-terminal series switch
ckt.S("1", ("n1", "n2"), position=0, ic_position=1)

# Multi-throw switch
ckt.S("1", ("common", "pos1", "pos2", "pos3"), position=0)
```

Accepts any switch parameters (`position`, `dc_position`, `ac_position`,
`tran_position`, `ic_position`, `offset`, `m`, etc.).

### SubCircuit

`SubCircuit` defines a reusable block. Instances are created with `ckt.X(...)`.

```python
from spectropy import SubCircuit

inv = SubCircuit(
    name="inverter",
    nodes=["in", "out", "vdd", "vss"],
    params={"l": "45n", "w_n": "1u", "w_p": "2u"},
)
inv.M("n", ("out", "in", "vss", "vss"), "NMOS_VTH", w="w_n", l="l")
inv.M("p", ("out", "in", "vdd", "vdd"), "PMOS_VTH", w="w_p", l="l")

ckt = Circuit("Inverter Test")
ckt.X("inv1", ("in", "out", "vdd", "0"), inv, params={"w_n": "2u", "w_p": "4u"})
ckt.X("inv2", ("out", "out2", "vdd", "0"), inv)              # uses defaults
```

Pass `copy=True` to give each instance an independent subcircuit definition:

```python
ckt.X("stage1", ("in", "mid"), rc, copy=True)
ckt.X("stage2", ("mid", "out"), rc, copy=True)
```

Subcircuits can be nested: a `SubCircuit` can instantiate another `SubCircuit`
via `.X(...)`.

### Verilog-A instances

Use `ckt.va()` to instantiate a Verilog-A module. The module must be compiled
and loaded via `ckt.ahdl_include()`.

```python
ckt.ahdl_include("/path/to/rram_v_1_0_0.va")
ckt.va("rram1", ("top", "bot"), "rram", Roff="1M", Ron="1k")
#                               ^module name, positional
# Emits: I<id> (<nodes>) <module> [**params]
```

### Circuit control statements

```python
# File inclusion
ckt.include("/path/to/models.scs")
ckt.include("/path/to/models.scs", section="tt")
ckt.ahdl_include("/path/to/module.va")

# Global nodes
ckt.global_nodes("0", "vdd")

# Parameters
ckt.parameters(vdd=1.8, temp=27)

# Options
ckt.options(reltol="1e-5", vabstol="1e-9")

# Temperature (convenience wrapper)
ckt.temperature(85)

# Models
ckt.model("NMOS", "nmos", vto=0.5, kp="200u")

# Initial conditions and nodesets
ckt.ic(vout=0, vin=1.8)
ckt.nodeset(vout=0.9)

# Raw Spectre commands verbatim
ckt.raw("options currents=selected")
```

### Save statements

By default, `DC`, `AC`, and `Tran` analyses automatically include
`save=lvlpub`, which saves all node voltages and voltage-source/inductor
branch currents. No explicit `save()` calls are needed for basic use.

```python
# Explicit signals
ckt.save("vout")                        # node voltage
ckt.save("M1:d")                        # drain current
ckt.save("M1:currents")                 # all terminal currents
ckt.save("M1:oppoint")                  # all operating-point parameters
ckt.save("M1:gm", "M1:vds", "M1:cgs")   # specific parameters
ckt.save(":pwr", "X1:pwr")              # total and instance power
ckt.save("X1.X2.M1:region")             # hierarchical device parameter

# Bulk convenience methods
ckt.save_all()                          # "save *" -- all node voltages
ckt.save_device_currents()              # "save *:1 sigtype=dev"
ckt.save_device_oppoints()              # "save *:oppoint"
ckt.save_nested(3)                      # "save * depth=3"
ckt.save_subcircuit("inv")              # "save * subckt=inv"
```

Override the save level on any analysis:

```python
analyses.Tran(stop="1u", step="1n", save="all")
analyses.DC(param="vin", start=0, stop=1, step=0.1, save="selected")
```

Available save levels: `lvlpub`, `lvl`, `allpub`, `all`, `selected`, `none`,
`nooutput`.

### WaveformGenerator

`WaveformGenerator` builds piecewise-linear waveforms from typed segments.
The output is a list of `(time, value)` pairs for use with `VoltagePWL` or
`CurrentPWL`.

```python
from spectropy import WaveformGenerator

wg = WaveformGenerator(scale="m", transition_time=0.001, dc_baseline=0)

wg.delay(duration=1)
wg.step(duration=10, delta=2, transition_time=0.1)
wg.triangle(duration=20, peak_value=2, cycles=3)
wg.pulse(duration=10, pulse_value=3, delay_before=1, delay_after=1, cycles=5)
wg.square(duration=10, start_value=0, end_value=1, cycles=3)
wg.sawtooth(duration=10, start_value=0, end_value=2, cycles=2)

pwl_data = wg.generate()
ckt.VoltagePWL("1", ("in", "0"), wave=pwl_data)
```


| Parameters | Default | Description |
|-----------|---------|-------------|
| `scale` | `"n"` | Time unit suffix (`"n"`, `"u"`, `"m"`) |
| `transition_time` | `0` | Default edge duration for segments |
| `dc_baseline` | `0` | Constant offset added to output values |


| Method | Parameters |
|--------|-----------|
| `delay(duration)` | Hold current level |
| `step(duration, delta, transition_time=None)` | Apply step of delta |
| `pulse(duration, pulse_value, delay_before=0, delay_after=0, cycles=1, transition_time=None)` | Pulse to value |
| `square(duration, start_value, end_value, delay_before=0, delay_after=0, cycles=1, transition_time=None)` | Square wave |
| `triangle(duration, peak_value, delay_before=0, delay_after=0, cycles=1)` | Triangle wave |
| `sawtooth(duration, start_value, end_value, delay_before=0, delay_after=0, cycles=1, transition_time=None)` | Sawtooth wave |
| `generate()` | Return list of `(time, value)` pairs |


## Simulation

### SpectreSession

`SpectreSession` manages the lifecycle of a Spectre simulation. Pass a
backend to control where Spectre runs (default: `NativeBackend`).

```python
from spectropy import SpectreSession

session = SpectreSession()
session.load_netlist(ckt.get_netlist())

result = session.run(
    analyses.OP(),
    analyses.Tran(stop="1m", step="1u"),
    stem="my_sim",
    outdir="/tmp/results",
)
```


| `session.run()` parameter | Default | Description |
|--------------------------|---------|-------------|
| `*runnables` | (required) | One or more `Runnable` objects (analyses, scopes) |
| `stem` | `"spectre"` | Base name for the netlist and output directory |
| `outdir` | auto tempdir | Directory for netlist and `.raw` output |


The returned `RunResult` is indexable by runnable name or position.

### Backends

Backends control *where* Spectre executes. Pass to `SpectreSession(backend=...)`.

#### NativeBackend (default)

Runs Spectre directly on the local machine.

```python
from spectropy import NativeBackend

session = SpectreSession(backend=NativeBackend(executable="spectre"))
```

#### SSHBackend

Runs Spectre on a remote server via SSH with an sshfs mount for file I/O.

```bash
# Step 1: mount the remote filesystem
mkdir -p ~/mount/myserver
sshfs user@myserver:/home/user ~/mount/myserver
```

```python
from spectropy import SSHBackend

session = SpectreSession(backend=SSHBackend(
    host="user@myserver",
    local_mount_point="/home/you/mount/myserver",
    remote_mount_source="/home/user",
    env_script="/home/user/setup.csh",
    executable="spectre",
    remote_shell="tcsh",
))

session.load_netlist(ckt.get_netlist())
result = session.run(
    analyses.Tran(stop="1u", step="1n"),
    outdir="/home/user/sim_results",  # server-side path
)
```

### Analyses

All analysis classes live in the `analyses` namespace. The three most common
analyses include `save=lvlpub` by default -- no explicit `save()` needed.

```python
from spectropy import analyses
```

#### Operating point: `OP`

```python
op = analyses.OP(name="OpPoint")
```


| Parameter | Default |
|-----------|---------|
| `name` | `"OpPoint"` |
| `**params` | -- |


#### DC sweep: `DC`

```python
dc = analyses.DC(param="vin", start=0, stop=1.8, step=0.01)
dc = analyses.DC(param="temp", start=-40, stop=125, step=5, name="temp_sweep")
```


| Parameter | Default | Description |
|-----------|---------|-------------|
| `param` | (required) | Parameter to sweep (e.g. `"vin"`, `"temp"`) |
| `start` | (required) | Start value |
| `stop` | (required) | Stop value |
| `step` | (required) | Step size |
| `name` | `"dcswp"` | Analysis name |
| `**params` | `{"save": "lvlpub"}` | Additional keywords (including `save` override) |


#### AC analysis: `AC`

```python
ac = analyses.AC(start="1", stop="1e6", sweep_type="dec", points=20)
ac = analyses.AC(start="1k", stop="100k", sweep_type="lin", points=100)
```


| Parameter | Default | Description |
|-----------|---------|-------------|
| `name` | `"analAC"` | Analysis name |
| `start` | `"1"` | Start frequency |
| `stop` | `"1e6"` | Stop frequency |
| `sweep_type` | `"dec"` | `"dec"`, `"lin"`, or `"oct"` |
| `points` | `10` | Points per decade/octave or total |
| `**params` | `{"save": "lvlpub"}` | Additional keywords |


#### Transient analysis: `Tran`

```python
tran = analyses.Tran(stop="1m", step="1u")
tran = analyses.Tran(stop="100u", step="10n", start="10u", maxstep="1n", uic=True)
```


| Parameter | Default | Description |
|-----------|---------|-------------|
| `name` | `"analTran"` | Analysis name |
| `stop` | `"1"` | Stop time |
| `step` | `"1"` | Output step |
| `start` | `None` | Start saving at this time |
| `maxstep` | `None` | Maximum internal timestep |
| `uic` | `False` | Use initial conditions |
| `**params` | `{"save": "lvlpub"}` | Additional keywords |


#### Transfer function: `XF`

```python
xf = analyses.XF(start="1", stop="1e9", sweep_type="dec", points=10,
                 output_pos="vout", output_neg="0", probe="V1")
```


| Parameter | Default | Description |
|-----------|---------|-------------|
| `start` | `"1"` | Start frequency |
| `stop` | `"1e9"` | Stop frequency |
| `sweep_type` | `"dec"` | `"dec"`, `"lin"`, or `"log"` |
| `points` | `10` | Points per decade |
| `name` | `"analXF"` | Analysis name |
| `output_pos` | `None` | Positive output node |
| `output_neg` | `"0"` | Negative output node |
| `probe` | `None` | Driving source probe |
| `stimuli` | `"sources"` | `"sources"` or `"nodes_and_terminals"` |
| `**params` | -- | |


#### Noise: `Noise`

```python
noise = analyses.Noise(start="1", stop="1e6", sweep_type="dec", points=10,
                       output_pos="vout", output_neg="0", iprobe="V1")
```


| Parameter | Default | Description |
|-----------|---------|-------------|
| `start` | `"1"` | Start frequency |
| `stop` | `"1e9"` | Stop frequency |
| `sweep_type` | `"dec"` | `"dec"`, `"lin"`, or `"log"` |
| `points` | `10` | Points per decade |
| `name` | `"analNoise"` | Analysis name |
| `output_pos` | `None` | Positive output node |
| `output_neg` | `"0"` | Negative output node |
| `oprobe` | `None` | Output probe |
| `iprobe` | `None` | Input probe |
| `**params` | -- | |


#### Stability: `STB`

Middlebrook stability analysis. `probe` is required.

```python
stb = analyses.STB(probe="iprobe", start="1", stop="1e9",
                   sweep_type="dec", points=10)
```


| Parameter | Default | Description |
|-----------|---------|-------------|
| `probe` | (required) | Loop-breaking probe |
| `start` | `"1"` | Start frequency |
| `stop` | `"1e9"` | Stop frequency |
| `sweep_type` | `"dec"` | `"dec"`, `"lin"`, or `"log"` |
| `points` | `10` | Points per decade |
| `name` | `"analSTB"` | Analysis name |
| `**params` | -- | |


#### Pole-zero: `PZ`

```python
pz = analyses.PZ(output_pos="vout", output_neg="0", iprobe="V1")
pz = analyses.PZ(output_pos="vout", zeroonly=True, fmax="1e10")
```


| Parameter | Default | Description |
|-----------|---------|-------------|
| `name` | `"analPZ"` | Analysis name |
| `output_pos` | `None` | Positive output node |
| `output_neg` | `"0"` | Negative output node |
| `iprobe` | `None` | Input probe |
| `oprobe` | `None` | Output probe |
| `fmax` | `None` | Maximum frequency for pole/zero search |
| `zeroonly` | `False` | Compute only zeros |
| `**params` | -- | |


### Scopes

Scopes wrap inner analyses in higher-level constructs. They produce
`GroupResult` objects.

#### Stage

Applies control statements before running inner analyses.

```python
stage = analyses.Stage(
    name="hot",
    setup=[analyses.Alter(name="set_temp", param="temp", value=85)],
    inner=[analyses.DC(param="vin", start=0, stop=1.8, step=0.01)],
)
```


| Parameter | Default | Description |
|-----------|---------|-------------|
| `inner` | (required) | Sequence of analyses to run |
| `setup` | `()` | `Alter` or `AlterGroup` objects |
| `name` | `"stage"` | Stage name |


#### Sweep

Parametric sweep over a circuit or model parameter.

```python
sweep = analyses.Sweep(
    inner=[analyses.DC(param="vin", start=0, stop=1.8, step=0.01)],
    param="temp",
    values=[-40, 0, 27, 85, 125],
)
```


| Parameter | Default | Description |
|-----------|---------|-------------|
| `inner` | (required) | Analyses to run at each point |
| `param` | (required) | Parameter to sweep |
| `values` | `None` | Explicit list of values; mutually exclusive with `start`/`stop` |
| `start` | `None` | Start of range |
| `stop` | `None` | End of range |
| `step` | `None` | Step size (for `lin` sweep) |
| `sweep_type` | `"lin"` | `"lin"`, `"dec"`, or `"log"` |
| `points` | `None` | Points per decade (for `dec`/`log`) |
| `name` | `"swp"` | Sweep name |
| `**params` | -- | |


#### MonteCarlo

Statistical Monte Carlo analysis.

```python
stats = analyses.Statistics(
    process=[analyses.Vary(param="rshsp", dist="gauss", std=12, percent=True)],
    mismatch=[analyses.Vary(param="vto", dist="gauss", std=0.05)],
)

mc = analyses.MonteCarlo(
    inner=[analyses.OP(), analyses.DC(param="vin", start=0, stop=1.8, step=0.01)],
    statistics=stats,
    numruns=100,
    seed=42,
    variations="all",
)
```


| Parameter | Default | Description |
|-----------|---------|-------------|
| `inner` | (required) | Analyses to run per iteration |
| `statistics` | `None` | `Statistics` object |
| `name` | `"mc"` | Monte Carlo name |
| `numruns` | `100` | Number of iterations |
| `variations` | `"all"` | `"all"`, `"process"`, or `"mismatch"` |
| `seed` | `None` | Random seed |
| `savefamilyplots` | `True` | Save per-iteration plot data |
| `**params` | -- | |


#### Corners

PVT corner sweep across model library sections.

```python
from spectropy import analyses  # Corner and Corners are exported

corners = analyses.Corners(
    corners=[
        analyses.Corner(section="tt", file="models.scs", temp=27, label="TT"),
        analyses.Corner(section="ss", file="models.scs", temp=85, label="SS"),
        analyses.Corner(section="ff", file="models.scs", temp=-40, label="FF"),
    ],
    inner=[analyses.DC(param="vin", start=0, stop=1.8, step=0.01)],
)
```


| `Corner` parameter | Default | Description |
|--------------------|---------|-------------|
| `section` | (required) | Model file section name |
| `file` | (required) | Path to model library |
| `temp` | `None` | Temperature override |
| `parameters` | `None` | Dict of netlist parameter overrides |
| `options` | `None` | Dict of options overrides |
| `label` | `None` | Custom label (defaults to `section`) |


| `Corners` parameter | Default | Description |
|---------------------|---------|-------------|
| `corners` | (required) | Sequence of `Corner` objects |
| `inner` | (required) | Analyses to run per corner |
| `name` | `"pvt"` | Corners name |


### Configuration objects

These objects configure scopes; they are **not** runnable on their own.

#### Alter

Mutates a single parameter.

```python
analyses.Alter(name="set_R", param="r", value="2k", dev="Rload")
analyses.Alter(name="set_temp", param="temp", value=-40)
analyses.Alter(name="set_vto", param="vto", value=0.55, mod="NMOS_VTH")
analyses.Alter(name="set_w", param="w", value="2u", sub="X1")
```


| Parameter | Default | Description |
|-----------|---------|-------------|
| `name` | (required) | Alter statement name |
| `param` | (required) | Parameter to change |
| `value` | (required) | New value |
| `dev` | `None` | Device instance target |
| `mod` | `None` | Model target |
| `sub` | `None` | Subcircuit instance target |


Exactly one of `dev`, `mod`, or `sub` may be specified (or none for global).

#### AlterGroup

Replaces a coherent set of definitions.

```python
analyses.AlterGroup(
    name="fast_corner",
    parameters={"w": "2u", "l": "40n"},
    options={"temp": -40, "reltol": "1e-4"},
    raw=["ahdl_include \"fast_model.va\""],
)
```


| Parameter | Default | Description |
|-----------|---------|-------------|
| `name` | (required) | AlterGroup name |
| `parameters` | `None` | Dict of parameter overrides |
| `options` | `None` | Dict of option overrides |
| `raw` | `None` | List of verbatim Spectre lines |


#### Vary

Defines a random-variable distribution for a `Statistics` block.

```python
analyses.Vary(param="rshsp", dist="gauss", std=12, percent=True)
analyses.Vary(param="vto", dist="lnorm", std=0.05)
analyses.Vary(param="deltaL", dist="unif", N=10)
```


| Parameter | Default | Description |
|-----------|---------|-------------|
| `param` | (required) | Parameter name |
| `dist` | (required) | `"gauss"`, `"lnorm"`, or `"unif"` |
| `std` | `None` | Standard deviation (mutually exclusive with `N`) |
| `N` | `None` | Sample count (mutually exclusive with `std`) |
| `percent` | `None` | Emits `percent=yes` if `True`, `percent=no` if `False` |


#### Correlate

Defines parameter correlation for a `Statistics` block.

```python
analyses.Correlate(cc=0.9, param=["vto_n", "vto_p"], dev=["M1", "M2"])
```


| Parameter | Default | Description |
|-----------|---------|-------------|
| `cc` | (required) | Correlation coefficient (-1.0 to 1.0) |
| `param` | `None` | List of parameters to correlate |
| `dev` | `None` | List of device instances (wildcards OK) |


#### Statistics

Container for random-variable distributions.

```python
stats = analyses.Statistics(
    process=[analyses.Vary(param="rshsp", dist="gauss", std=12)],
    mismatch=[analyses.Vary(param="vto", dist="gauss", std=0.05)],
    correlate=[analyses.Correlate(cc=0.9, param=["vto_n", "vto_p"])],
    truncate=3.0,
)
```


| Parameter | Default | Description |
|-----------|---------|-------------|
| `process` | `None` | List of process-level `Vary` |
| `mismatch` | `None` | List of mismatch-level `Vary` |
| `correlate` | `None` | List of `Correlate` objects |
| `truncate` | `None` | Global sigma cutoff |
| `process_truncate` | `None` | Per-process cutoff |
| `mismatch_truncate` | `None` | Per-mismatch cutoff |


### Accessing results

`session.run()` returns a `RunResult`. Access individual results by runnable
name or position:

```python
result = session.run(analyses.OP(), analyses.Tran(stop="1u", step="1n"))

op_result = result["OpPoint"]       # by name
tran_result = result[1]             # by position
for name, data in result.items():   # iterate
    print(name, data.names)
```

When only one runnable is passed, attributes delegate to that result:

```python
result = session.run(analyses.AC(start="1", stop="1e6", sweep_type="dec", points=20))
freq = result.frequency              # delegating to AcResult
vout = result.voltages["vout"]
```

#### Single-analysis results

All analysis results provide dictionary-like access to signals.

```python
result = session.run(analyses.OP())
op_result = result["OpPoint"]         # index RunResult by runnable name
vout = op_result["vout"]
vgs  = op_result["M1:vgs"]
for name in op_result:
    print(name, op_result[name].shape)
```


| Property | Description |
|----------|-------------|
| `.names` | Tuple of all signal names |
| `.values` | `dict[str, np.ndarray]` of all signals |
| `.voltages` | Signals without `:` (node voltages) |
| `.currents` | Signals with `:` and single-char suffix (terminal currents) |
| `.oppoints` | Signals with `:` and multi-char suffix (operating-point params) |


Swept results add a time/frequency axis:


| Class | Sweep accessor |
|-------|---------------|
| `DcResult` | `.sweep`, `.sweep_name` |
| `AcResult` | `.frequency` |
| `TranResult` | `.time` |
| `XfResult` | `.frequency`, `.transfer_functions` |
| `NoiseResult` | `.frequency`, `.output_noise`, `.input_referred_noise`, `.gain`, `.noise_figure` |
| `StbResult` | `.frequency`, `.loop_gain`, `.phase_margin`, `.gain_margin`, `.phase_margin_frequency`, `.gain_margin_frequency` |
| `PzResult` | `.poles`, `.zeros` |


#### Group results

Scopes (`Stage`, `Sweep`, `MonteCarlo`, `Corners`) return a `GroupResult`.
Index by integer position or string label:

```python
sweep = analyses.Sweep(
    inner=[analyses.DC(param="vin", start=0, stop=1, step=0.1)],
    param="temp", values=[-40, 27, 85],
)
result = session.run(sweep)
sweep_result = result["swp"]
for label, data in sweep_result.items():
    print(label, data.voltages["vout"])    # label = str(value)
```

```python
mc = analyses.MonteCarlo(inner=[analyses.OP()], numruns=100)
result = session.run(mc)
mc_result = result["mc"]
for run in mc_result:
    print(run.voltages["vout"])           # run = OpResult
```

```python
corners = analyses.Corners(
    corners=[analyses.Corner(section="tt", file="m.scs", label="TT"),
             analyses.Corner(section="ss", file="m.scs", label="SS")],
    inner=[analyses.DC(param="vin", start=0, stop=1, step=0.1)],
)
result = session.run(corners)
corners_result = result["pvt"]
tt_result = corners_result["TT"]          # by corner label
corners_result[0]                         # by positional index
```


| Property | Description |
|----------|-------------|
| `.labels` | List of run labels |
| `.numruns` | Number of runs |
| `.items()` | Iterator of `(label, entry)` pairs |
| `result[n]` | Run at index `n` |
| `result[label]` | Run with given label |


## Examples

Example scripts are in the `examples/` directory. Configure your backend in
`examples/config.py`, then run from the repository root:

```bash
export PYTHONPATH="$PWD:$PYTHONPATH"
python -m examples.basic.rc_low_pass_ac
python -m examples.basic.inverter_dc_sweep
python -m examples.montecarlo.inverter_montecarlo
python -m examples.corner.inverter_corners
```


| Example | Demonstrates |
|---------|-------------|
| `basic/rc_low_pass_ac.py` | RC circuit, AC analysis, gain/phase from complex signals |
| `basic/rc_step_response.py` | Voltage pulse source, transient analysis |
| `basic/rc_pz.py` | Pole-zero analysis |
| `basic/inverter_dc_sweep.py` | SubCircuit with parameters, DC sweep, OP |
| `basic/ota_dc.py` | OTA subcircuit, DC transfer, device operating regions |
| `basic/diode_rectifier.py` | Diode model, VoltageSin, transient |
| `basic/nmos_cs_xf.py` | Transfer function analysis, NMOS amplifier |
| `sweep/nmos_cs_sweep.py` | Parametric temperature sweep |
| `alter/inverter_alter.py` | Stage with Alter, temperature variants |
| `alter/inverter_altergroup.py` | Stage with AlterGroup, multi-parameter corner emulation |
| `corner/inverter_corners.py` | Corners scope, PVT with Corner labels |
| `montecarlo/inverter_montecarlo.py` | Monte Carlo with DC inner, switching-point extraction |
| `montecarlo/nmos_montecarlo.py` | Monte Carlo with process variation, histograms |
| `veriloga/memristor_mlc.py` | Verilog-A model, WaveformGenerator, step/triangle segments |
