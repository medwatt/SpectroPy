"""
Shared configuration for the examples.

The committed defaults are intentionally generic and assume Spectre runs on a
remote machine accessed through sshfs. For machine-specific settings, create an
ignored ``examples/config_local.py`` file that overrides any of these names.
"""

from pathlib import Path

from spectropy import SSHBackend

EXAMPLES_DIR = Path(__file__).resolve().parent
DESIGN_FILES_DIR = EXAMPLES_DIR / "design_files"

BACKEND = SSHBackend(
    host="user@remote-host",
    local_mount_point="/path/to/local/sshfs/mount",
    remote_mount_source="/path/on/remote/matching/mount",
    env_script="/path/on/remote/to/spectre_setup.sh",
)

OUTDIR = str(EXAMPLES_DIR / "spectropy_results")
FREEPDK45_DIR = str(DESIGN_FILES_DIR / "freepdk45")
VA_DIR = str(DESIGN_FILES_DIR / "veriloga_models")

try:
    from examples.config_local import *
except ImportError:
    pass
