# SpectroPy

SpectroPy is a Python library for building and simulating analog circuits using
[Cadence Spectre](https://en.wikipedia.org/wiki/Spectre_Circuit_Simulator) as
the simulation backend. Circuits are built programmatically through a Python
API and results are returned as numpy arrays.

## Requirements

- Python 3.10+
- numpy
- [psf-utils](https://github.com/kenkundert/psf_utils)
- Cadence Spectre (accessible locally or on a remote server)

## Installation

```bash
pip install git+https://github.com/medwatt/SpectroPy.git
```

## Running the Examples

The examples are kept in the [`examples/`](examples/) folder. They share
one configuration file, [`examples/config.py`](examples/config.py), instead
of repeating backend setup, output paths, model paths, and Verilog-A paths in
every example script.

Because the examples import that shared file as `examples.config`, Python
must be able to see the directory that contains the `examples` folder. If you
cloned the full repository, run examples from the repository root:

```bash
cd /path/to/SpectroPy
export PYTHONPATH="$PWD:$PYTHONPATH"
python -m examples.basic.rc_low_pass_ac
```

If you downloaded only the `examples` folder, set `PYTHONPATH` to the
directory that contains it:

```bash
export PYTHONPATH="/path/to/parent/of/examples:$PYTHONPATH"
python -m examples.basic.rc_low_pass_ac
```

Before running the examples, edit [`examples/config.py`](examples/config.py)
for your machine.

The files referenced by the examples under `examples/design_files/` must be
accessible to the `spectre` command. This is especially important when using a
remote backend: a path that exists only on your laptop is not enough if Spectre
runs on a server. Put the model files and Verilog-A files somewhere the Spectre
process can read them, then point `FREEPDK45_DIR`, `VA_DIR`, and any other
model-path variables at those locations.

## Backends

SpectroPy separates circuit description from where Spectre runs. A backend
is passed to `SpectreSession` and controls how the netlist is written and
how Spectre is invoked. If no backend is given, `NativeBackend` is used.

### NativeBackend (default)

Runs Spectre directly on the local machine. Spectre must be on `PATH`, or
you can provide the full path to the binary.

```python
from spectropy import SpectreSession, NativeBackend

# These two are equivalent
session = SpectreSession()
session = SpectreSession(backend=NativeBackend(executable="spectre"))
```

### SSHBackend

Runs Spectre on a remote server. SpectroPy writes the netlist and reads
back the results through an **sshfs** mount, then launches the simulation
over a plain SSH command. No special daemon is needed on the server; only
a standard SSH server and Spectre.

#### Step 1: Install sshfs

```bash
sudo apt install sshfs
```

#### Step 2: Mount the remote filesystem

Pick a local directory to serve as the mount point, then mount the remote
home directory (or whichever subtree Spectre will write results into):

```bash
mkdir -p ~/mount/myserver
sshfs user@myserver:/home/user ~/mount/myserver
```

The mount stays active until you log out or unmount it:

```bash
fusermount -u ~/mount/myserver
```

#### Step 3: Configure the backend

```python
from spectropy import SpectreSession, SSHBackend

session = SpectreSession(
    backend=SSHBackend(
        host="user@myserver",
        local_mount_point="~/mount/myserver",
        remote_mount_source="/home/user",
        env_script="/home/user/setup.csh",
        remote_shell="tcsh",
    )
)
```


| Parameter | Description |
|-----------|-------------|
| `host` | SSH target in `user@hostname` form |
| `local_mount_point` | Local directory where the server is mounted (second argument to `sshfs`) |
| `remote_mount_source` | Server-side directory that was mounted (path after `:` in the first `sshfs` argument) |
| `env_script` | Path on the server to a script sourced before running Spectre; sets `PATH`, license environment variables, etc. (optional) |
| `executable` | Name or full path of the Spectre binary on the server (default `"spectre"`) |
| `remote_shell` | Shell to invoke on the server, e.g. `"tcsh"`; required when `env_script` uses shell-specific syntax like `setenv` (optional) |


#### Step 4: Run simulations

Pass an `outdir` that is a path **on the server** (the path Spectre will
write to). SpectroPy translates it to the corresponding local path through the
mount for reading results back.

```python
result = session.run(
    simulations.AC(sweep_type="dec", points=20, fstart=1, fstop=1e9),
    outdir="/home/user/spectropy_results/",
)
```

## Minimal Example

This example builds a simple RC low-pass filter, runs an AC analysis, and reads
the output node as a numpy array.

```python
import numpy as np

from spectropy import Circuit, SpectreSession, simulations

ckt = Circuit("RC low-pass")
ckt.global_nodes("0")
ckt.V("in", ("in", "0"), dc=0, mag=1)
ckt.R("1", ("in", "out"), "1k")
ckt.C("1", ("out", "0"), "100n")
ckt.save("in", "out")

session = SpectreSession()
session.load_netlist(ckt.get_netlist())

result = session.run(
    simulations.AC(start="100", stop="1e6", sweep_type="dec", points=20),
    outdir="/tmp/spectropy_results",
)

gain_db = 20 * np.log10(np.abs(result.voltages["out"] / result.voltages["in"]))
print(gain_db)
```
