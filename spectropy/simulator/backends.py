# imports <<<
from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable
# >>>

# abstract class <<<
@runtime_checkable
class Backend(Protocol):
    """Interface that all Spectre backends must implement.

    A backend is responsible for two things:

    ``to_local(path)``
        Translate a path as spectre will see it into the corresponding path
        on the local filesystem, so that Python can perform file I/O there
        (write the netlist, read back results).  For backends where spectre
        runs locally this is a no-op.

    ``build_argv(outdir, netlist)``
        Build the command-line argv list that launches spectre.  Paths passed
        here are always in the coordinate system of the machine running spectre
        (i.e. already the remote/container side for SSH and Docker backends).
    """

    def to_local(self, path: Path) -> Path: ...
    def build_argv(self, outdir: Path, netlist: Path) -> list[str]: ...
# >>>

# native <<<
class NativeBackend:
    """Run spectre directly on the local machine.

    Parameters
    ----------
    executable:
        Name or full path of the spectre binary.
    """

    def __init__(self, executable: str = "spectre") -> None:
        self.executable = executable

    def to_local(self, path: Path) -> Path:
        return path

    def build_argv(self, outdir: Path, netlist: Path) -> list[str]:
        return [self.executable, "-f", "psfascii", "-outdir", str(outdir), str(netlist)]
# >>>

# docker <<<
class DockerBackend:
    """Run spectre inside a Docker container that bind-mounts the host filesystem.

    The container is expected to expose the host filesystem under a fixed
    prefix (``path_prefix``), so a host path ``/foo/bar`` is seen inside the
    container as ``<path_prefix>/foo/bar``.

    Parameters
    ----------
    wrapper:
        Shell wrapper or entry-point script that launches the container
        and forwards the spectre command to it.
    executable:
        Name of the spectre binary as it appears inside the container.
    path_prefix:
        Prefix prepended to every host path when building the in-container
        path (e.g. ``"/mnt"`` means ``/home/user/results`` ->
        ``/mnt/home/user/results`` inside the container).
    """

    def __init__(
        self,
        wrapper: str = "analog",
        executable: str = "spectre",
        path_prefix: str = "/mnt",
    ) -> None:
        self.wrapper = wrapper
        self.executable = executable
        self.path_prefix = path_prefix

    def to_local(self, path: Path) -> Path:
        return path

    def build_argv(self, outdir: Path, netlist: Path) -> list[str]:
        cmd = (
            f"{self.executable} -f psfascii"
            f" -outdir {self.path_prefix}{outdir}"
            f" {self.path_prefix}{netlist}"
        )
        return [self.wrapper, cmd]
# >>>

# sshfs <<<
class SSHBackend:
    """Run spectre on a remote server whose filesystem is mounted locally via sshfs.

    Workflow
    --------
    The server is mounted with::

        sshfs <host>:<remote_mount_source> <local_mount_point>

    ``outdir`` is always given as a server-side path (the path spectre will
    see).  The backend translates it to a local path through the sshfs mount
    for Python file I/O, and passes it unchanged to spectre over SSH.

    Example
    -------
    Mount command::

        sshfs user@myserver:/home/user ~/mount/server

    Backend configuration::

        SSHBackend(
            host="user@myserver",
            local_mount_point="~/mount/server",
            remote_mount_source="/home/user",
            env_script="/home/user/setup.csh",
            remote_shell="tcsh",
        )

    Session usage::

        session.run(..., outdir="/home/user/sim_results/")

    Parameters
    ----------
    host:
        SSH target in ``user@hostname`` form.
    local_mount_point:
        Local directory where the server filesystem is mounted: the second argument to the sshfs command.
    remote_mount_source:
        Server-side directory that was mounted: the path after ``:`` in the first argument to sshfs.  Defaults to ``"/"`` (server root).
    env_script:
        Path on the server to a script that must be sourced before running spectre (sets PATH, license variables, etc.).
    executable:
        Name or full path of the spectre binary on the server.
    remote_shell:
        Shell to invoke on the server (e.g. ``"tcsh"``).  Required when ``env_script`` uses shell-specific syntax such as ``setenv``.
    """

    def __init__(
        self,
        host: str,
        local_mount_point: str | Path,
        remote_mount_source: str = "/",
        env_script: str | None = None,
        executable: str = "spectre",
        remote_shell: str | None = None,
    ) -> None:
        self.host = host
        self.local_mount_point = Path(local_mount_point)
        self.remote_mount_source = remote_mount_source.rstrip("/")
        self.env_script = env_script
        self.executable = executable
        self.remote_shell = remote_shell

    def to_local(self, path: Path) -> Path:
        relative = str(path)[len(self.remote_mount_source) :]
        return self.local_mount_point / relative.lstrip("/")

    def build_argv(self, outdir: Path, netlist: Path) -> list[str]:
        cmd = f"{self.executable} -f psfascii -outdir {outdir} {netlist}"
        if self.env_script:
            cmd = f"source {self.env_script} && {cmd}"
        if self.remote_shell:
            cmd = f"{self.remote_shell} -c '{cmd}'"
        return ["ssh", self.host, cmd]
# >>>
