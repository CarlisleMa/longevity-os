"""Code execution engine for agents.

Provides a persistent Python namespace where agents execute code against
the scripts/ API. Uses in-process exec() so module-level caches (e.g.
measurement.csv, participant_index.parquet) persist across turns.
"""

import ast
import io
import sys
import signal
import traceback
from dataclasses import dataclass

import matplotlib
matplotlib.use("Agg")

from . import config


@dataclass
class ToolResult:
    success: bool
    output: str
    error: str | None = None


def create_namespace() -> dict:
    """Create a pre-seeded execution namespace."""
    import pandas as pd
    import numpy as np
    import matplotlib.pyplot as plt
    import seaborn as sns
    from scipy import stats

    # Ensure scripts/ is importable
    if str(config.PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(config.PROJECT_ROOT))

    return {
        "__builtins__": __builtins__,
        "pd": pd,
        "np": np,
        "plt": plt,
        "sns": sns,
        "stats": stats,
    }


def _truncate(text: str, max_chars: int = config.MAX_OUTPUT_CHARS) -> str:
    """Truncate output with indicator."""
    if len(text) <= max_chars:
        return text
    half = max_chars // 2
    return (
        text[:half]
        + f"\n\n[... truncated {len(text) - max_chars} chars ...]\n\n"
        + text[-half:]
    )


class _Timeout:
    """Context manager for code execution timeout."""

    def __init__(self, seconds: int):
        self.seconds = seconds

    def _handler(self, signum, frame):
        raise TimeoutError(f"Code execution timed out after {self.seconds}s")

    def __enter__(self):
        if hasattr(signal, "SIGALRM"):
            self._old = signal.signal(signal.SIGALRM, self._handler)
            signal.alarm(self.seconds)
        return self

    def __exit__(self, *args):
        if hasattr(signal, "SIGALRM"):
            signal.alarm(0)
            signal.signal(signal.SIGALRM, self._old)


def execute_python(code: str, namespace: dict) -> ToolResult:
    """Execute Python code in a persistent namespace.

    Captures stdout and the repr of the last expression (Jupyter-style).
    Returns ToolResult with success/output/error.
    """
    stdout_capture = io.StringIO()
    old_stdout = sys.stdout

    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return ToolResult(success=False, output="", error=f"SyntaxError: {e}")

    try:
        sys.stdout = stdout_capture

        with _Timeout(config.MAX_CODE_RUNTIME_SEC):
            # Check if last statement is an expression (auto-display like Jupyter)
            last_node = tree.body[-1] if tree.body else None
            if isinstance(last_node, ast.Expr):
                # Execute everything except the last expression
                module = ast.Module(body=tree.body[:-1], type_ignores=[])
                exec(compile(module, "<agent>", "exec"), namespace)
                # Evaluate and display the last expression
                result = eval(
                    compile(ast.Expression(body=last_node.value), "<agent>", "eval"),
                    namespace,
                )
                if result is not None:
                    print(repr(result), file=stdout_capture)
            else:
                exec(compile(tree, "<agent>", "exec"), namespace)

        output = stdout_capture.getvalue()
        return ToolResult(success=True, output=_truncate(output))

    except Exception:
        output = stdout_capture.getvalue()
        tb = traceback.format_exc()
        return ToolResult(
            success=False,
            output=output,
            error=tb,
        )
    finally:
        sys.stdout = old_stdout


# ── Anthropic tool definition ─────────────────────────────────────────────

TOOL_DEFINITION = {
    "name": "execute_python",
    "description": (
        "Execute Python code in a persistent namespace. "
        "The scripts/ API is available via import (e.g. from scripts.features import load_feature_matrix). "
        "pandas (pd), numpy (np), scipy.stats (stats), matplotlib.pyplot (plt), seaborn (sns) are pre-imported. "
        "Variables persist across calls. "
        "Returns stdout + the repr of the last expression, or the error traceback."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "code": {
                "type": "string",
                "description": "Python code to execute.",
            }
        },
        "required": ["code"],
    },
}
