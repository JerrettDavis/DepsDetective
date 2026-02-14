from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path


class GitError(RuntimeError):
    pass


class GitRepo:
    def __init__(self, root: Path) -> None:
        self.root = root

    @staticmethod
    def clone(repo_url: str, destination: Path, base_branch: str) -> "GitRepo":
        _run(["git", "clone", "--depth", "1", "--branch", base_branch, repo_url, str(destination)])
        return GitRepo(destination)

    @staticmethod
    def detect_default_branch(repo_url: str) -> str:
        output = _run(["git", "ls-remote", "--symref", repo_url, "HEAD"])
        for line in output.splitlines():
            if line.startswith("ref: ") and line.endswith("\tHEAD"):
                # Example: ref: refs/heads/main\tHEAD
                branch_ref = line.split()[1]
                return branch_ref.removeprefix("refs/heads/")
        return "main"

    def run(self, args: list[str], env: dict[str, str] | None = None) -> str:
        return _run(["git", *args], cwd=self.root, env=env)

    def configure_identity(self) -> None:
        self.run(["config", "user.name", os.getenv("GIT_AUTHOR_NAME", "depdetective[bot]")])
        self.run(
            [
                "config",
                "user.email",
                os.getenv("GIT_AUTHOR_EMAIL", "depdetective-bot@users.noreply.github.com"),
            ]
        )

    def create_or_reset_branch(self, branch: str, base_branch: str) -> None:
        self.run(["fetch", "origin", base_branch])
        self.run(["checkout", "-B", branch, f"origin/{base_branch}"])

    def has_changes(self) -> bool:
        status = self.run(["status", "--porcelain"])
        return bool(status.strip())

    def commit_all(self, message: str) -> None:
        self.run(["add", "."])
        self.run(["commit", "-m", message])

    def push(self, branch: str) -> None:
        self.run(["push", "--force-with-lease", "origin", branch])


def _run(
    args: list[str],
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
) -> str:
    merged_env = dict(os.environ)
    if env:
        merged_env.update(env)
    result = subprocess.run(
        args,
        cwd=str(cwd) if cwd else None,
        env=merged_env,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        safe_args = " ".join(_redact_secret(arg) for arg in args)
        safe_stderr = _redact_secret(result.stderr.strip())
        raise GitError(f"Command failed: {safe_args}\n{safe_stderr}")
    return result.stdout


def _redact_secret(text: str) -> str:
    if not text:
        return text
    # Redact URLs with embedded credentials.
    text = re.sub(r"(https?://)([^/\s:@]+):([^/\s@]+)@", r"\1***:***@", text)
    text = re.sub(r"(https?://)([^/\s:@]+)@", r"\1***@", text)
    return text
