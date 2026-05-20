# imports <<<
from __future__ import annotations

import shutil
import subprocess
import tempfile
import time
from pathlib import Path

from .backends import Backend, NativeBackend
from .simulations import Runnable
from .results import SpectreRunResult
from .collector import collect_results
# >>>

class SpectreSession:
    def __init__(
        self,
        *,
        backend: Backend | None = None,
    ) -> None:
        self.backend = backend if backend is not None else NativeBackend()
        self._netlist_lines: list[str] | None = None

    def load_netlist(self, netlist: list[str]) -> None:
        self._netlist_lines = netlist

    def run(
        self,
        *runnables: Runnable,
        stem: str = "spectre",
        outdir: str | Path | None = None,
    ) -> SpectreRunResult:
        if self._netlist_lines is None:
            raise RuntimeError("No netlist has been loaded")
        return self.run_netlist(
            self._netlist_lines, *runnables, stem=stem, outdir=outdir
        )

    def run_netlist(
        self,
        netlist: list[str],
        *runnables: Runnable,
        stem: str = "spectre",
        outdir: str | Path | None = None,
    ) -> SpectreRunResult:
        if outdir is None:
            outdir_path = Path(tempfile.mkdtemp(prefix="spectropy-"))
        else:
            outdir_path = Path(outdir)

        local_outdir = self.backend.to_local(outdir_path)
        local_outdir.mkdir(parents=True, exist_ok=True)

        # Remove the previous raw directory before writing a new netlist.
        # This guarantees that any network-filesystem cache (e.g. sshfs) for
        # the path is invalidated: spectre recreates the directory fresh, so
        # the next read always returns current data.
        raw_dir = local_outdir / f"{stem}.raw"
        if raw_dir.exists():
            shutil.rmtree(raw_dir)

        netlist_path = outdir_path / f"{stem}.scs"
        (local_outdir / f"{stem}.scs").write_text(
            "\n".join([*netlist, *(r.build_command() for r in runnables)]) + "\n",
            encoding="utf-8",
        )

        completed = subprocess.run(
            self.backend.build_argv(outdir_path, netlist_path),
            capture_output=True,
            text=True,
        )

        # Spectre returns 0 on success (including runs with warnings/notices)
        # and non-zero only on fatal errors.
        if completed.returncode != 0:
            raise RuntimeError(
                f"Spectre failed with return code {completed.returncode}\n"
                f"stdout:\n{completed.stdout}\n"
                f"stderr:\n{completed.stderr}"
            )

        # Some wrappers/container mounts return before the freshly-created PSF
        # directory is visible on the host side. Poll briefly before declaring
        # the successful Spectre process unusable.
        deadline = time.monotonic() + 10.0
        while not raw_dir.exists() and time.monotonic() < deadline:
            time.sleep(0.1)

        if not raw_dir.exists():
            raise RuntimeError(
                f"Spectre reported success but the output directory {raw_dir} does not exist. "
                "If you are using SSHBackend over sshfs, the mount may be stale.\n"
                f"stdout:\n{completed.stdout}\n"
                f"stderr:\n{completed.stderr}"
            )

        results = collect_results(raw_dir, runnables)
        return SpectreRunResult(results, completed=completed)
