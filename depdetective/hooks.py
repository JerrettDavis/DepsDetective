from __future__ import annotations

import logging
import subprocess
from pathlib import Path

LOGGER = logging.getLogger(__name__)


class HookError(RuntimeError):
    pass


def run_hook_commands(commands: list[str], cwd: Path, stage_name: str) -> None:
    for command in commands:
        LOGGER.info("Running hook (%s): %s", stage_name, command)
        result = subprocess.run(
            command,
            shell=True,
            cwd=str(cwd),
            text=True,
            capture_output=True,
            check=False,
        )
        if result.stdout.strip():
            LOGGER.info("Hook stdout (%s): %s", stage_name, result.stdout.strip())
        if result.stderr.strip():
            LOGGER.info("Hook stderr (%s): %s", stage_name, result.stderr.strip())
        if result.returncode != 0:
            raise HookError(
                f"Hook command failed in stage '{stage_name}' with exit code {result.returncode}: {command}"
            )

