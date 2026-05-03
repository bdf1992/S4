"""Substitution-template resolver for heartbeat configs.

Closes GAP-15 from hand-play 002. The runner uses this to render a step's
`args` and `fan_out` against prior steps' structured output before dispatch.

Supported syntax (intentionally narrow — see foundations/zero-four.md
"What this pattern is not"):

  {{ steps.<step_id>.<dotted.path>[<index_or_slice>]?(.<more.dotted>)? }}

  {{ steps.scrum.window.until_iso }}        # plain dotted access
  {{ steps.scrum.next_targets[0] }}         # integer index
  {{ steps.scrum.next_targets[0].skills }}  # mixed index + dotted
  {{ steps.scrum.next_targets[:10] }}       # slice
  {{ steps.scrum.next_targets[3:] }}        # slice with start
  {{ steps.scrum.next_targets[1:5] }}       # slice with start+stop
  {{ item }}                                # fan_out element binding
  {{ item.skill }}                          # dotted access on fan_out item

Not supported (deliberately): wildcards [*], filters [?cond], jq pipes.
If a use case wants more, the right move is a new ritual that emits the
already-shaped output, not a richer template DSL.
"""
from __future__ import annotations

import re

_TEMPLATE_RE = re.compile(r"\{\{\s*(.+?)\s*\}\}")
_SEGMENT_RE = re.compile(r"([^\.\[]+)|\[(-?\d*):(-?\d*)\]|\[(-?\d+)\]")


class TemplateError(ValueError):
    """Raised when a template cannot be resolved against the bindings."""


def _parse_path(expr: str) -> list:
    """Parse 'steps.scrum.next_targets[0].skills' into segment list.

    Returns a list where each element is either:
      - a string (attribute/key name)
      - an int (index)
      - a (start, stop) tuple of int|None (slice)
    """
    segs = []
    pos = 0
    for m in _SEGMENT_RE.finditer(expr):
        if m.start() != pos and expr[pos] != ".":
            raise TemplateError(
                f"unparseable template segment at offset {pos}: {expr!r}")
        name, sl_a, sl_b, idx = m.group(1), m.group(2), m.group(3), m.group(4)
        if name is not None:
            segs.append(name)
        elif idx is not None:
            segs.append(int(idx))
        else:
            start = int(sl_a) if sl_a not in (None, "") else None
            stop = int(sl_b) if sl_b not in (None, "") else None
            segs.append((start, stop))
        pos = m.end()
        if pos < len(expr) and expr[pos] == ".":
            pos += 1
    if pos != len(expr):
        raise TemplateError(f"trailing chars in template: {expr!r}")
    return segs


def _walk(value, segments: list, expr: str):
    cur = value
    for seg in segments:
        if isinstance(seg, str):
            if isinstance(cur, dict):
                if seg not in cur:
                    raise TemplateError(
                        f"key {seg!r} missing in {expr!r}")
                cur = cur[seg]
            else:
                raise TemplateError(
                    f"cannot read attribute {seg!r} from non-dict in {expr!r}")
        elif isinstance(seg, int):
            if not isinstance(cur, list):
                raise TemplateError(
                    f"cannot index non-list with [{seg}] in {expr!r}")
            try:
                cur = cur[seg]
            except IndexError:
                raise TemplateError(
                    f"index [{seg}] out of range in {expr!r}")
        elif isinstance(seg, tuple):
            start, stop = seg
            if not isinstance(cur, list):
                raise TemplateError(
                    f"cannot slice non-list in {expr!r}")
            cur = cur[start:stop]
        else:
            raise TemplateError(f"unknown segment type in {expr!r}")
    return cur


def resolve(expr: str, bindings: dict):
    """Resolve a single template expression (without surrounding {{ }}).

    bindings: dict with keys like 'steps' (mapping step_id → output) and
    optionally 'item' (for fan_out element binding).
    """
    segments = _parse_path(expr)
    if not segments:
        raise TemplateError(f"empty template: {expr!r}")
    head = segments[0]
    if head not in bindings:
        raise TemplateError(
            f"template root {head!r} not in bindings (have: "
            f"{sorted(bindings)})")
    return _walk(bindings[head], segments[1:], expr)


def render(template, bindings: dict):
    """Render a value (str, dict, list, or scalar) by resolving any
    {{ ... }} expressions. Whole-string templates ('{{ ... }}') return
    the raw resolved value; templates embedded in larger strings are
    str()-coerced and substituted in place.

    Dicts and lists are walked recursively.
    """
    if isinstance(template, str):
        m_full = _TEMPLATE_RE.fullmatch(template)
        if m_full:
            return resolve(m_full.group(1), bindings)

        def _sub(match: re.Match) -> str:
            return str(resolve(match.group(1), bindings))
        return _TEMPLATE_RE.sub(_sub, template)
    if isinstance(template, dict):
        return {k: render(v, bindings) for k, v in template.items()}
    if isinstance(template, list):
        return [render(v, bindings) for v in template]
    return template


__all__ = ["resolve", "render", "TemplateError"]
