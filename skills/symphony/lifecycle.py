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

# Project field IDs (v2 API). Regenerable via
#   gh project field-list 1 --owner bdf1992 --format json
# Status option IDs were rotated 2026-05-08 when "In Review" was added
# via `updateProjectV2Field` mutation (which replaces options rather
# than appending — all option IDs change atomically).
PROJECT_ID = "PVT_kwHOAKOWQc4BXJ2l"
STATUS_FIELD_ID = "PVTSSF_lAHOAKOWQc4BXJ2lzhSYwCA"
STATUS_OPTION_TODO = "bbc3c912"
STATUS_OPTION_IN_PROGRESS = "5a8a4fc8"
STATUS_OPTION_IN_REVIEW = "0fbc7e01"
STATUS_OPTION_DONE = "e16a313d"
RETRY_COUNT_FIELD_ID = "PVTF_lAHOAKOWQc4BXJ2lzhSZRak"


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


def dispatch(issue_number: int) -> int:
    """Manual orchestrator-side dispatch — what cc-symphony does automatically.

    Adds `symphony-doing` label, sets project Status to In Progress, and
    creates (or switches to) the local branch `issue-<N>`. Caller is
    expected to do the work on that branch, then call `mark_done`.
    """
    rc, _, err = _run(["gh", "issue", "edit", str(issue_number), "--repo", REPO,
                       "--add-label", "symphony-doing"])
    if rc != 0:
        sys.stderr.write(f"add label failed: {err.strip()}\n")
        return rc
    item_id = _project_item_id_for_issue(issue_number)
    if item_id:
        _set_status(item_id, STATUS_OPTION_IN_PROGRESS)
    branch = f"issue-{issue_number}"
    rc2, _, _ = _run(["git", "switch", "-c", branch])
    if rc2 != 0:
        rc3, _, err3 = _run(["git", "switch", branch])
        if rc3 != 0:
            sys.stderr.write(f"branch '{branch}' could not be created or switched: {err3.strip()}\n")
            print(f"dispatched: #{issue_number} symphony-doing + Status=In Progress (branch op failed)")
            return rc3
        print(f"dispatched: #{issue_number} symphony-doing + Status=In Progress, switched to existing '{branch}'")
        return 0
    print(f"dispatched: #{issue_number} symphony-doing + Status=In Progress, branch '{branch}' created")
    return 0


def mark_done(issue_number: int, comment: str | None) -> int:
    """Agent-side completion: add `symphony-done`, remove `symphony-doing`, set
    project Status to In Review, optionally post a completion comment.

    Per cc-symphony spec the agent adds `symphony-done` and the orchestrator
    removes `symphony-doing`. Without cc-symphony, the agent is also the
    orchestrator — this subcommand bundles both label edits AND moves the
    project Status to In Review (the column added 2026-05-08 to make the
    "agent done, awaiting operator" state visible on the kanban board).

    The agent does NOT close the issue; that's the operator's `approve`.
    """
    rc, _, err = _run(["gh", "issue", "edit", str(issue_number), "--repo", REPO,
                       "--add-label", "symphony-done",
                       "--remove-label", "symphony-doing"])
    if rc != 0:
        sys.stderr.write(f"label edit failed: {err.strip()}\n")
        return rc
    item_id = _project_item_id_for_issue(issue_number)
    if item_id:
        _set_status(item_id, STATUS_OPTION_IN_REVIEW)
    if comment and comment.strip():
        rc2, _, err2 = _run(["gh", "issue", "comment", str(issue_number),
                             "--repo", REPO, "--body", comment])
        if rc2 != 0:
            sys.stderr.write(f"comment post failed: {err2.strip()}\n")
            return rc2
        print(f"mark-done: #{issue_number} symphony-done + symphony-doing removed + Status=In Review + comment posted")
    else:
        print(f"mark-done: #{issue_number} symphony-done + symphony-doing removed + Status=In Review")
    return 0


def pr(issue_number: int, title: str, body: str, base: str = "master") -> int:
    """Agent-side: open a PR on branch `issue-<N>` against `base`.

    Caller is responsible for having committed + pushed the branch.
    """
    branch = f"issue-{issue_number}"
    rc, out, _ = _run(["git", "ls-remote", "--heads", "origin", branch])
    if rc != 0 or not out.strip():
        sys.stderr.write(f"pr: branch '{branch}' not found on origin — push it first\n")
        return 1
    rc2, out2, err2 = _run(["gh", "pr", "create", "--repo", REPO,
                            "--base", base, "--head", branch,
                            "--title", title, "--body-file", "-"],
                           stdin_input=body)
    if rc2 != 0:
        sys.stderr.write(f"pr create failed: {err2.strip()}\n")
        return rc2
    pr_url = out2.strip().splitlines()[-1]
    print(f"pr: opened {pr_url}")
    print(f"  base: {base}  head: {branch}  title: {title}")
    return 0


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
    canonical = ("Todo", "In Progress", "In Review", "Done")
    columns: dict[str, list[tuple[int, str]]] = {c: [] for c in canonical}
    columns["(no status)"] = []
    for item in data.get("items", []):
        c = item.get("content", {}) if isinstance(item.get("content"), dict) else {}
        col = item.get("status") or "(no status)"
        columns.setdefault(col, []).append((c.get("number", 0), c.get("title", "?")))
    print(f"=== {PROJECT_OWNER}/projects/{PROJECT_NUMBER} ===")
    for col in canonical:
        rows = sorted(columns.get(col, []))
        print(f"\n[{col}] ({len(rows)})")
        for num, title in rows:
            print(f"  #{num}  {title}")
    other = {k: v for k, v in columns.items() if k not in canonical and v}
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


def _read_retry_count(item_id: str) -> int:
    rc, data = _gh_json("project", "item-list", PROJECT_NUMBER,
                        "--owner", PROJECT_OWNER, "--format", "json", "-L", "200")
    if rc != 0 or not isinstance(data, dict):
        return 0
    for item in data.get("items", []):
        if item.get("id") == item_id:
            value = item.get("Retry count") or item.get("retry count") or 0
            try:
                return int(value)
            except (TypeError, ValueError):
                return 0
    return 0


def _set_retry_count(item_id: str, n: int) -> int:
    rc, _, err = _run([
        "gh", "project", "item-edit", "--id", item_id,
        "--project-id", PROJECT_ID, "--field-id", RETRY_COUNT_FIELD_ID,
        "--number", str(n),
    ])
    if rc != 0:
        sys.stderr.write(f"set_retry_count failed: {err.strip()}\n")
    return rc


def approve(issue_number: int, merge: str | None = None) -> int:
    """Operator-side: close issue, set Status=Done. With `merge` set
    ('squash' | 'merge' | 'rebase'), also merges the linked PR with that
    strategy and deletes the head branch.
    """
    rc, _, err = _run(["gh", "issue", "close", str(issue_number),
                       "--repo", REPO, "--reason", "completed"])
    if rc != 0:
        sys.stderr.write(f"issue close failed: {err.strip()}\n")
        return rc
    item_id = _project_item_id_for_issue(issue_number)
    if item_id:
        _set_status(item_id, STATUS_OPTION_DONE)
    if merge:
        rc2, pr_data = _gh_json("pr", "list", "--repo", REPO,
                                "--search", f"linked:#{issue_number}",
                                "--json", "number,state")
        prs = [p for p in (pr_data or []) if isinstance(p, dict) and p.get("state") == "OPEN"]
        if not prs:
            print(f"approved: #{issue_number} closed, Status → Done. (no open linked PR; --merge skipped)")
            return 0
        pr_number = prs[0]["number"]
        rc3, _, err3 = _run(["gh", "pr", "merge", str(pr_number), "--repo", REPO,
                             f"--{merge}", "--delete-branch"])
        if rc3 != 0:
            sys.stderr.write(f"pr merge failed: {err3.strip()}\n")
            print(f"approved: #{issue_number} closed, Status → Done. (PR #{pr_number} merge FAILED)")
            return rc3
        print(f"approved: #{issue_number} closed, Status → Done, PR #{pr_number} {merge}-merged + branch deleted")
        return 0
    print(f"approved: #{issue_number} closed, project Status → Done")
    return 0


def bulk_approve(issue_numbers: list[int], merge: str | None = None) -> int:
    """Operator-side: close + Status=Done for multiple issues in one call.

    For legacy/concurrent acceptance cleanup (multiple acceptances landing
    same day; pre-existing task-level queue from before outcome-level
    framing was clear). Calls `approve` for each issue. With `merge` set,
    each linked PR is merged with that strategy.

    NOT a sub-issue / parent-child mechanism. Per memory:
    feedback_outcome_authoring_not_task_authoring.md — operator never
    authors task-level groupings. This is a batch helper for when
    multiple independent acceptances are pending, not a way to flatten
    a task list back into operator view.
    """
    print(f"=== bulk-approve {len(issue_numbers)} issue(s) "
          f"{'with ' + merge + '-merge' if merge else 'without merge'} ===")
    failures: list[int] = []
    for n in issue_numbers:
        print(f"\n--- #{n} ---")
        rc = approve(n, merge=merge)
        if rc != 0:
            failures.append(n)
    print()
    if failures:
        print(f"bulk-approve: {len(issue_numbers) - len(failures)}/{len(issue_numbers)} succeeded; "
              f"failed: {failures}")
        return 1
    print(f"bulk-approve: {len(issue_numbers)}/{len(issue_numbers)} succeeded")
    return 0


def reject(issue_number: int, reason: str | None = None) -> int:
    """Operator-side: route back through the lifecycle for retry.

    Removes `symphony-done`, increments the project's Retry count field,
    sets Status to In Progress, optionally posts a rejection comment.
    cc-symphony's reconciliation will detect `symphony-doing` still
    present + `symphony-done` absent and re-dispatch with `attempt`
    incremented (per cc-symphony spec).
    """
    rc, _, err = _run(["gh", "issue", "edit", str(issue_number), "--repo", REPO,
                       "--remove-label", "symphony-done"])
    if rc != 0:
        sys.stderr.write(f"label remove failed: {err.strip()}\n")
    item_id = _project_item_id_for_issue(issue_number)
    if item_id:
        _set_status(item_id, STATUS_OPTION_IN_PROGRESS)
        new_count = _read_retry_count(item_id) + 1
        _set_retry_count(item_id, new_count)
    if reason and reason.strip():
        _run(["gh", "issue", "comment", str(issue_number), "--repo", REPO,
              "--body", f"Rejected by operator. Reason: {reason}"])
    print(f"rejected: #{issue_number} symphony-done removed, Status → In Progress, Retry count incremented")
    return 0


def probe_inline() -> bool:
    """Probe cc-symphony's HTTP server. Returns True if reachable."""
    try:
        with urllib.request.urlopen(f"{SYMPHONY_HTTP}/api/status",
                                    timeout=PROBE_TIMEOUT_S) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        running = payload.get("running_count", "?")
        retrying = payload.get("retrying_count", "?")
        completed = payload.get("completed_count", "?")
        print(f"cc-symphony: running ({SYMPHONY_HTTP}) — "
              f"running={running} retrying={retrying} completed={completed}")
        return True
    except (urllib.error.URLError, ConnectionError, OSError, TimeoutError):
        print(f"cc-symphony: not_running ({SYMPHONY_HTTP} unreachable)")
        return False


def probe() -> int:
    return 0 if probe_inline() else 1
