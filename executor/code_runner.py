"""
Code Runner — executes shell commands (npm install, npm run build, etc.)
in generated project directories.
"""

from __future__ import annotations

import asyncio
import logging
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class CommandResult:
    """Outcome of a shell command execution."""
    command: str
    return_code: int
    stdout: str
    stderr: str
    success: bool = True

    def to_dict(self):
        return {
            "command": self.command,
            "return_code": self.return_code,
            "stdout": self.stdout[-2000:],  # truncate long output
            "stderr": self.stderr[-2000:],
            "success": self.success,
        }


class CodeRunner:
    """Run npm / node commands inside a project directory."""

    def __init__(self, timeout: int = 120):
        self.timeout = timeout

    # ------------------------------------------------------------------
    # Synchronous helpers (used in non-async contexts)
    # ------------------------------------------------------------------
    def run(self, command: str, cwd: str) -> CommandResult:
        """Run a shell command synchronously."""
        logger.info("Running: %s  (cwd=%s)", command, cwd)
        try:
            result = subprocess.run(
                command,
                cwd=cwd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
            return CommandResult(
                command=command,
                return_code=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
                success=result.returncode == 0,
            )
        except subprocess.TimeoutExpired:
            return CommandResult(
                command=command,
                return_code=-1,
                stdout="",
                stderr=f"Command timed out after {self.timeout}s",
                success=False,
            )
        except Exception as exc:
            return CommandResult(
                command=command,
                return_code=-1,
                stdout="",
                stderr=str(exc),
                success=False,
            )

    # ------------------------------------------------------------------
    # Async version
    # ------------------------------------------------------------------
    async def run_async(self, command: str, cwd: str) -> CommandResult:
        """Run a shell command asynchronously."""
        logger.info("Running (async): %s  (cwd=%s)", command, cwd)
        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                cwd=cwd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=self.timeout
            )
            return CommandResult(
                command=command,
                return_code=proc.returncode or 0,
                stdout=stdout.decode(errors="replace"),
                stderr=stderr.decode(errors="replace"),
                success=proc.returncode == 0,
            )
        except asyncio.TimeoutError:
            return CommandResult(
                command=command,
                return_code=-1,
                stdout="",
                stderr=f"Command timed out after {self.timeout}s",
                success=False,
            )
        except Exception as exc:
            return CommandResult(
                command=command,
                return_code=-1,
                stdout="",
                stderr=str(exc),
                success=False,
            )

    # ------------------------------------------------------------------
    # Convenience wrappers
    # ------------------------------------------------------------------
    def npm_install(self, project_dir: str) -> CommandResult:
        return self.run("npm install", cwd=project_dir)

    async def npm_install_async(self, project_dir: str) -> CommandResult:
        return await self.run_async("npm install", cwd=project_dir)

    def npm_build(self, project_dir: str) -> CommandResult:
        return self.run("npm run build", cwd=project_dir)

    async def npm_build_async(self, project_dir: str) -> CommandResult:
        return await self.run_async("npm run build", cwd=project_dir)

    def npm_lint(self, project_dir: str) -> CommandResult:
        return self.run("npm run lint", cwd=project_dir)

    async def npm_lint_async(self, project_dir: str) -> CommandResult:
        return await self.run_async("npm run lint", cwd=project_dir)
