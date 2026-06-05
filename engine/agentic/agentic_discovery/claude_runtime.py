"""Runtime diagnostics for the Claude Agent SDK backend."""

from __future__ import annotations

import importlib.metadata
import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class ClaudeAgentSdkUnavailable(ImportError):
    """Raised when the Claude Agent SDK runtime cannot be used."""


@dataclass
class ClaudeSdkDiagnostic:
    available: bool
    package_version: str
    module_file: str
    bundled_cli_path: str
    bundled_cli_version: str
    global_cli_path: str
    node_path: str
    anthropic_api_key_present: bool
    auth_status: dict[str, Any]
    message: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "available": self.available,
            "package_version": self.package_version,
            "module_file": self.module_file,
            "bundled_cli_path": self.bundled_cli_path,
            "bundled_cli_version": self.bundled_cli_version,
            "global_cli_path": self.global_cli_path,
            "node_path": self.node_path,
            "anthropic_api_key_present": self.anthropic_api_key_present,
            "auth_status": self.auth_status,
            "message": self.message,
        }


def diagnose_claude_sdk() -> ClaudeSdkDiagnostic:
    try:
        version = importlib.metadata.version("claude-agent-sdk")
        import claude_agent_sdk
    except Exception as exc:
        return ClaudeSdkDiagnostic(
            available=False,
            package_version="",
            module_file="",
            bundled_cli_path="",
            bundled_cli_version="",
            global_cli_path=shutil.which("claude") or "",
            node_path=shutil.which("node") or "",
            anthropic_api_key_present=bool(os.environ.get("ANTHROPIC_API_KEY")),
            auth_status={},
            message=f"Claude Agent SDK is not importable: {exc}",
        )

    bundled = bundled_claude_cli_path()
    bundled_version = _run_text([str(bundled), "--version"]) if bundled.exists() else ""
    auth_status = _auth_status(bundled)
    has_auth = bool(os.environ.get("ANTHROPIC_API_KEY")) or bool(auth_status.get("loggedIn"))
    message = "Claude Agent SDK is importable."
    if not bundled.exists():
        message = "Claude Agent SDK is importable, but bundled Claude CLI was not found."
    elif not has_auth:
        message = (
            "Claude Agent SDK is importable, but no ANTHROPIC_API_KEY or Claude plan "
            "login was detected."
        )

    return ClaudeSdkDiagnostic(
        available=bundled.exists() and has_auth,
        package_version=version,
        module_file=str(Path(claude_agent_sdk.__file__).resolve()),
        bundled_cli_path=str(bundled) if bundled.exists() else "",
        bundled_cli_version=bundled_version,
        global_cli_path=shutil.which("claude") or "",
        node_path=shutil.which("node") or "",
        anthropic_api_key_present=bool(os.environ.get("ANTHROPIC_API_KEY")),
        auth_status=auth_status,
        message=message,
    )


def bundled_claude_cli_path() -> Path:
    import claude_agent_sdk

    return Path(claude_agent_sdk.__file__).resolve().parent / "_bundled" / "claude"


def require_claude_runtime() -> Path:
    diagnostic = diagnose_claude_sdk()
    if not diagnostic.bundled_cli_path:
        raise ClaudeAgentSdkUnavailable(diagnostic.message)
    if not diagnostic.anthropic_api_key_present and not diagnostic.auth_status.get("loggedIn"):
        raise ClaudeAgentSdkUnavailable(diagnostic.message)
    return Path(diagnostic.bundled_cli_path)


def _auth_status(cli_path: Path) -> dict[str, Any]:
    if not cli_path.exists():
        return {}
    output = _run_text([str(cli_path), "auth", "status"])
    if not output:
        return {}
    try:
        return json.loads(output)
    except json.JSONDecodeError:
        return {"raw": output}


def _run_text(command: list[str]) -> str:
    try:
        result = subprocess.run(command, check=False, capture_output=True, text=True, timeout=20)
    except Exception as exc:
        return f"error: {exc}"
    return (result.stdout or result.stderr).strip()
