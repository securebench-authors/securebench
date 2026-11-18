"""Pier, copying artifact directories out without changing their owner (for the fidelity study).

Pier's Unix `download_dir` runs `chown -R <host uid>` on the source inside the container
before `docker compose cp`. `equivalence.py` copies the scope roots that way before an
in-container verifier, which then graded files owned by another user: git refuses such a
repository. `docker compose cp` does not need the chown, because the daemon reads the files
as root and the host side is written as the invoking user. Pier's tar-based copy avoids the
chown too, but its extraction refuses absolute symlinks, which some scope roots hold.

`equivalence.py` runs this file with Pier's own interpreter in place of `pier`.
"""

import sys
from pathlib import Path

from pier.cli.main import app
from pier.environments.docker.docker_unix import UnixOps


async def _download_dir(self: UnixOps, source_dir: str, target_dir: Path | str) -> None:
    await self._env._run_docker_compose_command(
        ["cp", f"main:{source_dir}/.", str(target_dir)], check=True
    )


UnixOps.download_dir = _download_dir  # type: ignore[method-assign]
sys.exit(app())
