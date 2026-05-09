"""Process management for the cc-symphony daemon.

Closes the verbal-only loop on cc-symphony lifecycle: operator never has
to set GITHUB_TOKEN manually, never has to run `taskkill /F /IM
symphony.exe`, never has to remember the binary path. `start` resolves
the token from gh CLI's keychain (so it stays out of operator-visible
env vars and chat transcripts), launches cc-symphony detached so the
daemon survives this Claude Code session ending; `stop` kills it.

Detached on Windows via `subprocess.Popen` with
`DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP` so the child does not die
when the parent's terminal closes.
"""
from __future__ import annotations

import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

CC_SYMPHONY_BIN = Path.home() / "cc-symphony" / "rust" / "target" / "release" / "symphony.exe"
WORKFLOW_MD = Path.cwd() / "WORKFLOW.md"
PORT = 8080
PROBE_TIMEOUT_S = 2


def _is_running() -> bool:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/api/status",
                                    timeout=PROBE_TIMEOUT_S):
            return True
    except (urllib.error.URLError, ConnectionError, OSError, TimeoutError):
        return False


def _gh_token() -> str | None:
    res = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True)
    if res.returncode != 0:
        sys.stderr.write(f"gh auth token failed: {res.stderr.strip()}\n")
        return None
    token = res.stdout.strip()
    return token if token else None


def start() -> int:
    """Launch cc-symphony detached. Returns 0 on success, 1 on failure."""
    if not CC_SYMPHONY_BIN.exists():
        sys.stderr.write(f"start: cc-symphony binary not found at {CC_SYMPHONY_BIN}\n")
        sys.stderr.write("       build it: cd ~/cc-symphony/rust && cargo build --release --features http-server\n")
        return 1
    if not WORKFLOW_MD.exists():
        sys.stderr.write(f"start: WORKFLOW.md not at {WORKFLOW_MD}\n")
        return 1
    if _is_running():
        print(f"start: cc-symphony already running on http://127.0.0.1:{PORT}")
        return 0
    token = _gh_token()
    if not token:
        sys.stderr.write("start: GITHUB_TOKEN unavailable from gh CLI keychain\n")
        return 1
    env = os.environ.copy()
    env["GITHUB_TOKEN"] = token
    flags = 0
    if sys.platform == "win32":
        flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    proc = subprocess.Popen(
        [str(CC_SYMPHONY_BIN), str(WORKFLOW_MD), "--port", str(PORT)],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=flags,
    )
    print(f"start: cc-symphony launched detached, pid={proc.pid}, port={PORT}")
    print(f"  workflow: {WORKFLOW_MD}")
    print(f"  dashboard: http://127.0.0.1:{PORT}/")
    print(f"  stop later: python -m skills.symphony stop")
    return 0


def stop() -> int:
    """Stop cc-symphony. Returns 0 on success, 1 on failure."""
    was_running = _is_running()
    if sys.platform != "win32":
        sys.stderr.write("stop: only Windows taskkill is implemented; on POSIX use `pkill symphony`\n")
        return 1
    res = subprocess.run(["taskkill", "/F", "/IM", "symphony.exe"],
                         capture_output=True, text=True)
    if res.returncode == 0:
        print("stop: cc-symphony killed")
        return 0
    if not was_running:
        print("stop: cc-symphony was not running")
        return 0
    sys.stderr.write(f"stop: taskkill returned non-zero: {res.stderr.strip() or res.stdout.strip()}\n")
    return 1
