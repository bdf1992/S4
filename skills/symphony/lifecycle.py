"""Deterministic gh-CLI orchestration for the symphony lifecycle skill.

No LLM in this module — the agent does judgment work upstream (drafting
issue bodies, reviewing context); this module is pure 1.0 (per
foundations/collection-program.md: deterministic, source-walking,
re-runnable). Each function is a thin wrapper around `gh` subprocess
calls plus JSON parsing.

The repo target (bdf1992/S4), project number (1), and project owner
(bdf1992) are pinned at module-scope constants — these are the
operator's actual setup. Future generalization could read them from
config; for v0 they're hardcoded since the lifecycle is single-tenant.
"""
from __future__ import annotations

import json
import subprocess
import sys
import urllib.error
import urllib.request

REPO = "bdf1992/S4"
PROJECT_NUMBER = "1"
PROJECT_OWNER = "bdf1992"
SYMPHONY_HTTP = "http://127.0.0.1:8080"
PROBE_TIMEOUT_S = 2

# Project Status field IDs (v2 API). Captured at project-creation time;
# regenerable via `gh project field-list 1 --owner bdf1992 --format json`.
STATUS_FIELD_ID = "PVTSSF_lAHOAKOWQc4BXJ2lzhSYwCA"
STATUS_OPTION_TODO = "f75ad846"
STATUS_OPTION_IN_PROGRESS = "47fc9ee4"
STATUS_OPTION_DONE = "98236657"
PROJECT_ID = "PVT_kwHOAKOWQc4BXJ2l"


def _run(cmd: list[str], stdin_input: str | None = None) -> tuple[int, str, str]:
    res = subprocess.run(cmd, capture_output=True, text=True,
                         input=stdin_input, encoding="utf-8")
    return res.returncode, res.stdout, res.stderr


def _gh_json(*args: str, stdin_input: str | None = None) -> tuple[int, object]:
    rc, out, err = _run(["gh", *args], stdin_input=stdin_input)
    if rc != 0:
        sys.stderr.write(f"gh error ({' '.join(args[:3])}): {err.strip()}\n")
        return rc, None
    try:
        return rc, json.loads(out)
    except json.JSONDecodeError:
        return rc, out


def _project_item_id_for_issue(issue_number: int) -> str | None:
    rc, data = _gh_json("project", "item-list", PROJECT_NUMBER,
                        "--owner", PROJECT_OWNER, "--format", "json", "-L", "200")
    if rc != 0 or not isinstance(data, dict):
        return None
    for item in data.get("items", []):
        c = item.get("content", {}) if isinstance(item.get("content"), dict) else {}
        if c.get("number") == issue_number:
            return item.get("id")
    return None


def _set_status(item_id: str, option_id: str) -> int:
    rc, _, err = _run([
        "gh", "project", "item-edit", "--id", item_id,
        "--project-id", PROJECT_ID, "--field-id", STATUS_FIELD_ID,
        "--single-select-option-id", option_id,
    ])
    if rc != 0:
        sys.stderr.write(f"set_status failed: {err.strip()}\n")
    return rc


def new(title: str, kind: str, body: str) -> int:
    valid_kinds = {"debt", "feature", "refactor"}
    if kind not in valid_kinds:
        sys.stderr.write(f"new: --kind must be one of {sorted(valid_kinds)}\n")
        return 2
    label_csv = f"symphony,kind:{kind}"
    rc, out, err = _run([
        "gh", "issue", "create", "--repo", REPO,
        "--title", title, "--label", label_csv, "--body-file", "-",
    ], stdin_input=body)
    if rc != 0:
        sys.stderr.write(f"issue create failed: {err.strip()}\n")
        return rc
    issue_url = out.strip().splitlines()[-1]
    issue_number = int(issue_url.rsplit("/", 1)[-1])
    rc2, _, err2 = _run([
        "gh", "project", "item-add", PROJECT_NUMBER,
        "--owner", PROJECT_OWNER, "--url", issue_url,
    ])
    if rc2 != 0:
        sys.stderr.write(f"project item-add failed: {err2.strip()}\n")
    item_id = _project_item_id_for_issue(issue_number)
    if item_id:
        _set_status(item_id, STATUS_OPTION_TODO)
    print(f"opened: {issue_url}")
    print(f"  title: {title}")
    print(f"  labels: {label_csv}")
    print(f"  status: Todo")
    return 0


def status() -> int:
    rc, data = _gh_json("project", "item-list", PROJECT_NUMBER,
                        "--owner", PROJECT_OWNER, "--format", "json", "-L", "200")
    if rc != 0 or not isinstance(data, dict):
        return rc or 1
    columns: dict[str, list[tuple[int, str]]] = {
        "Todo": [], "In Progress": [], "Done": [], "(no status)": [],
    }
    for item in data.get("items", []):
        c = item.get("content", {}) if isinstance(item.get("content"), dict) else {}
        col = item.get("status") or "(no status)"
        columns.setdefault(col, []).append((c.get("number", 0), c.get("title", "?")))
    print(f"=== {PROJECT_OWNER}/projects/{PROJECT_NUMBER} ===")
    for col in ("Todo", "In Progress", "Done"):
        rows = sorted(columns.get(col, []))
        print(f"\n[{col}] ({len(rows)})")
        for num, title in rows:
            print(f"  #{num}  {title}")
    other = {k: v for k, v in columns.items() if k not in ("Todo", "In Progress", "Done") and v}
    if other:
        for col, rows in other.items():
            print(f"\n[{col}] ({len(rows)})")
            for num, title in sorted(rows):
                print(f"  #{num}  {title}")
    print()
    probe_inline()
    return 0


def review(issue_number: int) -> int:
    rc, issue_data = _gh_json("issue", "view", str(issue_number), "--repo", REPO,
                              "--json", "title,body,labels,state,url,comments,assignees")
    if rc != 0 or not isinstance(issue_data, dict):
        return rc or 1
    title = issue_data.get("title", "?")
    state = issue_data.get("state", "?")
    labels = [lbl.get("name", "") for lbl in issue_data.get("labels", [])]
    url = issue_data.get("url", "")
    body = issue_data.get("body", "")
    comments = issue_data.get("comments", [])
    has_done = "symphony-done" in labels
    has_doing = "symphony-doing" in labels
    print(f"=== Issue #{issue_number}: {title} ===")
    print(f"  state: {state}")
    print(f"  labels: {', '.join(labels) if labels else '(none)'}")
    print(f"  url: {url}")
    print(f"  symphony-doing: {'yes' if has_doing else 'no'}")
    print(f"  symphony-done:  {'yes' if has_done else 'no'}")
    print()
    print("--- body ---")
    print(body)
    if comments:
        print()
        print(f"--- comments ({len(comments)}) ---")
        for cm in comments:
            author = cm.get("author", {}).get("login", "?")
            print(f"  [{author}] {cm.get('body', '')[:300]}")
    rc2, pr_data = _gh_json("pr", "list", "--repo", REPO,
                            "--search", f"linked:#{issue_number}",
                            "--json", "number,title,state,url,headRefName")
    if rc2 == 0 and isinstance(pr_data, list) and pr_data:
        print()
        print("--- linked PRs ---")
        for pr in pr_data:
            print(f"  PR #{pr.get('number')}  [{pr.get('state')}]  {pr.get('title')}  ({pr.get('url')})")
    elif rc2 == 0:
        print()
        print("--- linked PRs --- (none)")
    return 0


def approve(issue_number: int) -> int:
    rc, _, err = _run(["gh", "issue", "close", str(issue_number),
                       "--repo", REPO, "--reason", "completed"])
    if rc != 0:
        sys.stderr.write(f"issue close failed: {err.strip()}\n")
        return rc
    item_id = _project_item_id_for_issue(issue_number)
    if item_id:
        _set_status(item_id, STATUS_OPTION_DONE)
    print(f"approved: #{issue_number} closed, project Status → Done")
    return 0


def reject(issue_number: int) -> int:
    rc, _, err = _run(["gh", "issue", "edit", str(issue_number), "--repo", REPO,
                       "--remove-label", "symphony-done"])
    if rc != 0:
        sys.stderr.write(f"label remove failed: {err.strip()}\n")
    item_id = _project_item_id_for_issue(issue_number)
    if item_id:
        _set_status(item_id, STATUS_OPTION_IN_PROGRESS)
    print(f"rejected: #{issue_number} symphony-done removed, Status → In Progress")
    return 0


def probe_inline() -> bool:
    try:
        with urllib.request.urlopen(f"{SYMPHONY_HTTP}/api/status",
                                    timeout=PROBE_TIMEOUT_S) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        active = payload.get("active_runs") or payload.get("in_flight") or "?"
        completed = payload.get("completed_count", "?")
        print(f"cc-symphony: running ({SYMPHONY_HTTP}) — active={active} completed={completed}")
        return True
    except (urllib.error.URLError, ConnectionError, OSError, TimeoutError):
        print(f"cc-symphony: not_running ({SYMPHONY_HTTP} unreachable)")
        return False


def probe() -> int:
    return 0 if probe_inline() else 1
