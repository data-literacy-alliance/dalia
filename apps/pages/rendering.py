"""Hardened Markdown -> HTML rendering through pandoc.

``run_pandoc`` is the single place that spawns pandoc (shared with the DOCX
conversion); ``render_markdown`` is the pure Markdown renderer used on save.
"""

import functools
import logging
import resource
import subprocess
import threading
from pathlib import Path

logger = logging.getLogger(__name__)

PANDOC_TIMEOUT_SECONDS = 20
PANDOC_MEMORY_LIMIT = "512m"
PANDOC_MEMORY_BYTES = 1024**3  # setrlimit fallback when RTS options are disabled
ERROR_LINE_MAX_CHARS = 300
FALLBACK_MAX_MARKDOWN_CHARS = 500_000  # plan value; used only if pages.validators is unavailable

LUA_FILTER_PATH = Path(__file__).resolve().parent / "pandoc" / "website.lua"

# Raw HTML/TeX/attribute syntaxes and every attribute-carrying extension are off:
# nothing but plain Markdown reaches the Lua filter.
MARKDOWN_READER = (
    "markdown-raw_html-raw_attribute-raw_tex-link_attributes-bracketed_spans"
    "-fenced_divs-native_divs-native_spans-header_attributes"
    "-fenced_code_attributes-inline_code_attributes"
)

_RTS_ARGS = ["+RTS", "-M" + PANDOC_MEMORY_LIMIT, "-RTS"]
_rts_lock = threading.Lock()
_use_rts = True  # flipped once per process when the pandoc build rejects RTS options


class RenderError(Exception):
    """Pandoc could not render the input (message is safe to show, not yet escaped)."""


def _max_markdown_chars() -> int:
    try:
        from pages.validators import MAX_MARKDOWN_CHARS
    except ImportError:  # S1 not landed yet
        return FALLBACK_MAX_MARKDOWN_CHARS
    return MAX_MARKDOWN_CHARS


def _first_error_line(stderr: str) -> str:
    """First meaningful stderr line; pandoc warnings are skipped."""
    lines = [line.strip() for line in (stderr or "").splitlines() if line.strip()]
    for line in lines:
        if not line.startswith("[WARNING]"):
            return line[:ERROR_LINE_MAX_CHARS]
    return (lines[0] if lines else "pandoc failed")[:ERROR_LINE_MAX_CHARS]


def _limit_address_space() -> None:
    resource.setrlimit(resource.RLIMIT_AS, (PANDOC_MEMORY_BYTES, PANDOC_MEMORY_BYTES))


def _spawn(args, stdin, cwd, timeout, use_rts):
    cmd = ["pandoc", *args, *(_RTS_ARGS if use_rts else [])]
    return subprocess.run(  # noqa: S603 - fixed binary, no shell
        cmd,
        input=stdin,
        capture_output=True,
        text=True,
        timeout=timeout,
        shell=False,
        cwd=cwd,
        preexec_fn=None if use_rts else _limit_address_space,
    )


# Messages of a pandoc build that does not accept RTS options. Heap exhaustion
# ("Use '+RTS -M<size>'") also mentions RTS but is an ordinary render failure.
_RTS_REJECTION_MARKERS = ("unknown rts option", "rts options are disabled")


def _rts_rejected(proc) -> bool:
    if proc.returncode == 0:
        return False
    stderr = (proc.stderr or "").lower()
    return any(marker in stderr for marker in _RTS_REJECTION_MARKERS)


def run_pandoc(
    args: list[str],
    *,
    stdin: str | None = None,
    cwd: str | None = None,
    timeout: int = PANDOC_TIMEOUT_SECONDS,
) -> str:
    """Run pandoc with a memory cap and return stdout.

    Raises ``RenderError`` on a missing binary, timeout or non-zero exit.
    """
    global _use_rts
    try:
        proc = _spawn(args, stdin, cwd, timeout, _use_rts)
        if _use_rts and _rts_rejected(proc):
            with _rts_lock:
                _use_rts = False
            logger.warning("pandoc rejects +RTS options; using RLIMIT_AS fallback")
            proc = _spawn(args, stdin, cwd, timeout, False)
    except FileNotFoundError as exc:
        logger.error("pandoc binary not found")
        raise RenderError("pandoc is not installed") from exc
    except subprocess.TimeoutExpired as exc:
        logger.error("pandoc timed out after %s s", timeout)
        raise RenderError(f"pandoc timed out after {timeout} s") from exc
    if proc.returncode != 0:
        message = _first_error_line(proc.stderr)
        logger.error("pandoc failed with exit code %s", proc.returncode)
        raise RenderError(message)
    return proc.stdout


@functools.lru_cache(maxsize=32)
def render_markdown(md: str) -> str:
    """Render untrusted Markdown to sanitised HTML (no raw HTML, no attributes)."""
    if len(md) > _max_markdown_chars():
        raise RenderError("Markdown is too long")
    if not md.strip():
        return ""
    return run_pandoc(
        [
            "--sandbox",
            "-f",
            MARKDOWN_READER,
            "-t",
            "html5",
            "--wrap=none",
            "--id-prefix=c-",
            "--lua-filter",
            str(LUA_FILTER_PATH),
        ],
        stdin=md,
    )
