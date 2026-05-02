"""Render a list of kanban cards as a self-contained HTML page.

Columns are laid out horizontally (true kanban shape). Each column is a
stack of card tiles. Optional lanes (severity) split a column into sub-
groups with a small label above each.

Mirrors render.py's data shape exactly — same card dict, same `columns`
declaration, same `lanes` flag — so any caller that already produces
cards for the markdown renderer can render HTML by switching modules.

Usage:
  python -m boards.render_html <source_dir>
  python -m boards <name> --html [-o page.html]
"""
from __future__ import annotations

import datetime as _dt
import html as _html
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def _h(s) -> str:
    return _html.escape(str(s), quote=True)


def _today() -> _dt.date:
    return _dt.date.today()


def _age_days(date_str: str) -> int | None:
    try:
        d = _dt.date.fromisoformat(date_str)
    except (TypeError, ValueError):
        return None
    return (_today() - d).days


def _blocks_of(cards: list[dict]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for c in cards:
        for dep in c.get("depends_on", []) or []:
            out.setdefault(dep, []).append(c["id"])
    return out


def _edge_label(target_id: str, by_id: dict[str, dict]) -> str:
    target = by_id.get(target_id)
    if not target:
        return target_id
    teaser = (target.get("subject", "") or "")[:32]
    return f"{target_id} · {teaser}" if teaser else target_id


SEVERITY_CLASS = {
    "load_bearing": "sev-load",
    "cosmetic": "sev-cos",
    "unknown": "sev-unk",
}


def _card_html(c: dict, blocks_map: dict[str, list[str]],
               by_id: dict[str, dict],
               card_link_fn=None) -> str:
    sev = c.get("severity", "unknown") or "unknown"
    sev_cls = SEVERITY_CLASS.get(sev, "sev-unk")
    cid = c.get("id", "?")
    subject = c.get("subject", "(no subject)")
    payoff = (c.get("payoff", "") or "").strip()
    payoff_teaser = ""
    if payoff:
        teaser = payoff[:200] + ("…" if len(payoff) > 200 else "")
        payoff_teaser = f'<div class="card-body">{_h(teaser)}</div>'

    re_trigger = (c.get("re_trigger", "") or "").strip()
    rt_html = ""
    if re_trigger:
        rt = re_trigger[:140] + ("…" if len(re_trigger) > 140 else "")
        rt_html = (
            f'<div class="card-meta-row"><span class="meta-label">re-trigger</span>'
            f'<span class="meta-val">{_h(rt)}</span></div>'
        )

    deps = c.get("depends_on") or []
    blocks = blocks_map.get(cid, [])
    edges_html = ""
    edge_parts = []
    if deps:
        chips = "".join(
            f'<span class="chip chip-dep" title="{_h(_edge_label(d, by_id))}">⬅ {_h(d)}</span>'
            for d in deps
        )
        edge_parts.append(f'<div class="edges">{chips}</div>')
    if blocks:
        chips = "".join(
            f'<span class="chip chip-block" title="{_h(_edge_label(b, by_id))}">➡ {_h(b)}</span>'
            for b in blocks
        )
        edge_parts.append(f'<div class="edges">{chips}</div>')
    if edge_parts:
        edges_html = "".join(edge_parts)

    age = _age_days(c.get("last_updated_at", "") or "")
    age_html = (
        f'<span class="age">{age}d</span>' if age is not None and age > 0 else ""
    )

    sev_label = sev.replace("_", " ")
    sev_chip = (
        f'<span class="sev-chip {sev_cls}">{_h(sev_label)}</span>'
        if sev != "unknown" else ""
    )

    href = card_link_fn(c) if card_link_fn else None
    open_tag, close_tag = ("", "")
    article_cls = f"card {sev_cls}"
    if href:
        article_cls += " card-clickable"
        open_tag = f'<a class="card-link" href="{_h(href)}">'
        close_tag = '</a>'
    return (
        f'{open_tag}<article class="{article_cls}">'
        f'<header class="card-head">'
        f'<span class="card-id">{_h(cid)}</span>'
        f'<span class="card-subject">{_h(subject)}</span>'
        f'</header>'
        f'{payoff_teaser}'
        f'{rt_html}'
        f'{edges_html}'
        f'<footer class="card-foot">{sev_chip}{age_html}</footer>'
        f'</article>{close_tag}'
    )


def _column_html(col: str, cards_in_col: list[dict], *, lanes: bool,
                 blocks_map: dict[str, list[str]],
                 by_id: dict[str, dict],
                 card_link_fn=None) -> str:
    head = (
        f'<div class="col-head">'
        f'<span class="col-name">{_h(col.replace("_", " "))}</span>'
        f'<span class="col-count">{len(cards_in_col)}</span>'
        f'</div>'
    )
    if not cards_in_col:
        body = '<div class="col-empty">empty</div>'
        return f'<section class="col col-{_h(col)}">{head}{body}</section>'

    if lanes:
        severity_order = ["load_bearing", "unknown", "cosmetic"]
        by_lane: dict[str, list[dict]] = {}
        for c in cards_in_col:
            by_lane.setdefault(c.get("severity", "unknown") or "unknown", []).append(c)
        seen_lanes = [s for s in severity_order if s in by_lane] + \
                     [s for s in by_lane if s not in severity_order]
        parts = []
        for lane in seen_lanes:
            cls = SEVERITY_CLASS.get(lane, "sev-unk")
            parts.append(f'<div class="lane-label {cls}">{_h(lane.replace("_"," "))}</div>')
            for c in by_lane[lane]:
                parts.append(_card_html(c, blocks_map, by_id, card_link_fn))
        body = "".join(parts)
    else:
        body = "".join(_card_html(c, blocks_map, by_id, card_link_fn)
                       for c in cards_in_col)

    return f'<section class="col">{head}<div class="col-body">{body}</div></section>'


CSS = """
:root {
  --bg: #f5f6f8;
  --col-bg: #ebeef3;
  --card-bg: #ffffff;
  --text: #1a2233;
  --muted: #6b7588;
  --border: #d6dbe4;
  --shadow: 0 1px 2px rgba(20,30,55,0.06), 0 1px 4px rgba(20,30,55,0.04);
  --load: #c2410c;
  --load-bg: #fff1ea;
  --cos: #475569;
  --cos-bg: #eef2f7;
  --unk: #6b7588;
  --unk-bg: #eef0f4;
  --chip-dep-bg: #fef3c7;
  --chip-dep-fg: #92400e;
  --chip-block-bg: #dbeafe;
  --chip-block-fg: #1e40af;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
  background: var(--bg);
  color: var(--text);
  font-size: 13px;
  line-height: 1.4;
}
.page { padding: 20px 24px 40px; }
header.page-head { margin-bottom: 16px; }
header.page-head h1 { margin: 0 0 4px; font-size: 18px; font-weight: 600; }
header.page-head .sub { color: var(--muted); font-size: 12px; }
header.page-head .sub code { background: #e5e9f0; padding: 1px 6px; border-radius: 3px; font-size: 12px; }
header.page-head a { color: #2563eb; text-decoration: none; }
header.page-head a:hover { text-decoration: underline; }
.board {
  display: grid;
  grid-auto-flow: column;
  grid-auto-columns: minmax(260px, 1fr);
  gap: 14px;
  overflow-x: auto;
  padding-bottom: 8px;
}
.col {
  background: var(--col-bg);
  border: 1px solid var(--border);
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  min-height: 120px;
  max-height: calc(100vh - 110px);
}
.col-head {
  padding: 10px 14px;
  border-bottom: 1px solid var(--border);
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--muted);
  background: rgba(255,255,255,0.4);
  border-radius: 8px 8px 0 0;
}
.col-name { color: #334155; }
.col-count {
  background: #cbd5e1;
  color: #1e293b;
  border-radius: 999px;
  padding: 1px 8px;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0;
}
.col-body {
  padding: 10px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.col-empty {
  padding: 20px 14px;
  color: var(--muted);
  font-style: italic;
  font-size: 12px;
  text-align: center;
}
.lane-label {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  padding: 3px 8px;
  border-radius: 4px;
  align-self: flex-start;
  margin-top: 4px;
}
.lane-label.sev-load { background: var(--load-bg); color: var(--load); }
.lane-label.sev-cos  { background: var(--cos-bg);  color: var(--cos); }
.lane-label.sev-unk  { background: var(--unk-bg);  color: var(--unk); }
.card {
  background: var(--card-bg);
  border: 1px solid var(--border);
  border-left: 3px solid var(--unk);
  border-radius: 6px;
  padding: 10px 12px;
  box-shadow: var(--shadow);
}
.card.sev-load { border-left-color: var(--load); }
.card.sev-cos  { border-left-color: var(--cos); }
a.card-link { display: block; text-decoration: none; color: inherit; }
a.card-link:hover .card { box-shadow: 0 2px 6px rgba(20,30,55,0.12), 0 4px 12px rgba(20,30,55,0.10); transform: translateY(-1px); transition: all 80ms ease-out; }
a.card-link:hover .card-subject { color: #2563eb; }
.card-clickable { cursor: pointer; }
.card-head { display: flex; gap: 8px; align-items: baseline; margin-bottom: 4px; }
.card-id {
  font-family: ui-monospace, "SF Mono", Menlo, Consolas, monospace;
  font-size: 11.5px;
  font-weight: 700;
  color: #475569;
  flex-shrink: 0;
}
.card-subject {
  font-size: 12.5px;
  font-weight: 600;
  color: var(--text);
  word-break: break-word;
}
.card-body {
  color: #475569;
  font-size: 12px;
  margin: 4px 0 6px;
}
.card-meta-row { display: flex; gap: 6px; font-size: 11px; margin-top: 4px; }
.meta-label {
  color: var(--muted);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  font-size: 10px;
  flex-shrink: 0;
  padding-top: 1px;
}
.meta-val { color: #475569; }
.edges { display: flex; flex-wrap: wrap; gap: 4px; margin-top: 6px; }
.chip {
  font-family: ui-monospace, "SF Mono", Menlo, Consolas, monospace;
  font-size: 10.5px;
  padding: 1px 7px;
  border-radius: 999px;
  font-weight: 600;
}
.chip-dep   { background: var(--chip-dep-bg);   color: var(--chip-dep-fg); }
.chip-block { background: var(--chip-block-bg); color: var(--chip-block-fg); }
.card-foot {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 8px;
  padding-top: 6px;
  border-top: 1px dashed #e5e9f0;
}
.sev-chip {
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  padding: 2px 7px;
  border-radius: 4px;
}
.sev-chip.sev-load { background: var(--load-bg); color: var(--load); }
.sev-chip.sev-cos  { background: var(--cos-bg);  color: var(--cos); }
.sev-chip.sev-unk  { background: var(--unk-bg);  color: var(--unk); }
.age {
  color: var(--muted);
  font-size: 11px;
  font-variant-numeric: tabular-nums;
  margin-left: auto;
}
"""


def render_html(cards: list[dict], *, board_name: str, source_label: str | None,
                columns: list[str] | None, lanes: bool,
                card_link_fn=None) -> str:
    blocks_map = _blocks_of(cards)
    by_id = {c.get("id", ""): c for c in cards if c.get("id")}
    by_status: dict[str, list[dict]] = {}
    for c in cards:
        by_status.setdefault(c.get("status", "?"), []).append(c)
    if columns:
        col_order = list(columns)
        for s in by_status:
            if s not in col_order:
                col_order.append(s)
    else:
        col_order = sorted(by_status.keys())

    cols_html = "".join(
        _column_html(col, by_status.get(col, []), lanes=lanes,
                     blocks_map=blocks_map, by_id=by_id,
                     card_link_fn=card_link_fn)
        for col in col_order
    )

    src_html = ""
    if source_label:
        href = f"vscode://file/{(REPO / source_label).resolve().as_posix()}"
        src_html = f' · source: <a href="{_h(href)}"><code>{_h(source_label)}</code></a>'

    title = f"{board_name} — {len(cards)} cards"

    return (
        '<!doctype html>\n'
        '<html lang="en">\n'
        '<head>\n'
        '<meta charset="utf-8">\n'
        f'<title>{_h(title)}</title>\n'
        f'<style>{CSS}</style>\n'
        '</head>\n'
        '<body>\n'
        '<div class="page">\n'
        '<header class="page-head">'
        f'<h1>{_h(title)}</h1>'
        f'<div class="sub">{len(cards)} cards across {len(col_order)} columns'
        f'{src_html}</div>'
        '</header>\n'
        f'<div class="board">{cols_html}</div>\n'
        '</div>\n'
        '</body>\n'
        '</html>\n'
    )


def main() -> int:
    """Standalone: render a directory of *.json cards (debts-style sources)."""
    args = sys.argv[1:]
    if not args:
        print("usage: python -m boards.render_html <source_dir> [--columns a,b,c] [--no-lanes] [-o page.html]")
        return 1

    import json

    src_arg = args[0]
    columns: list[str] | None = None
    lanes = True
    out_path: Path | None = None
    i = 1
    while i < len(args):
        a = args[i]
        if a == "--columns" and i + 1 < len(args):
            columns = [c.strip() for c in args[i + 1].split(",") if c.strip()]
            i += 2
        elif a == "--no-lanes":
            lanes = False
            i += 1
        elif a == "-o" and i + 1 < len(args):
            out_path = Path(args[i + 1])
            i += 2
        else:
            i += 1

    src = Path(src_arg)
    if not src.is_absolute():
        src = REPO / src
    cards: list[dict] = []
    for p in sorted(src.glob("*.json")):
        try:
            r = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if isinstance(r, dict) and "status" in r:
            cards.append(r)

    page = render_html(
        cards,
        board_name=src.name,
        source_label=str(src.relative_to(REPO)) if src.is_relative_to(REPO) else None,
        columns=columns,
        lanes=lanes,
    )
    if out_path is not None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(page, encoding="utf-8")
        sys.stderr.write(f"wrote {out_path}\n")
    else:
        sys.stdout.write(page)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
