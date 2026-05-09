"""Foundation 1 — data-point shape, validator, constructor, store IO.

This module is itself 0.1 infrastructure. It does not call any LLM, does
not use random/uuid/time-as-value, and is small enough to audit in one
sitting. Collectors construct data points via `make_data_point` so that
direct `datetime` access can be banned in collector files.

Provenance block conforms to W3C PROV-DM (https://www.w3.org/TR/prov-dm/)
via PROV-JSON vocabulary (https://www.w3.org/TR/prov-json/).  The three
local names are replaced with their standard PROV-DM counterparts:

  collected_at      → prov:wasGeneratedAtTime   (advisory wall-clock)
  source_state      → prov:wasDerivedFrom        (source entity identifier)
  collector_pointer → prov:wasAttributedTo       (agent/collector pointer)

Validation uses prov-python (https://pypi.org/project/prov/) to round-trip
the provenance block through a ProvDocument, confirming it is structurally
well-formed per the spec.  The round-trip is read-only telemetry; it does
not alter the stored dict.

See: foundations/data-point.md (the bedrock this implements).
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
from pathlib import Path
from typing import Any

import prov.model as _prov

REQUIRED_FIELDS = (
    "id", "kind", "value",
    "provenance.prov:wasAttributedTo",
    "provenance.prov:wasDerivedFrom",
    "provenance.prov:wasGeneratedAtTime",
    "witness",
)

_PROV_NS = "http://www.w3.org/ns/prov#"
_EX_NS = "http://example.org/zero-four#"


def _now_iso() -> str:
    # Single localized use of wall-clock — only for the advisory
    # prov:wasGeneratedAtTime field. Never feeds value or witness derivation.
    # See Foundation 1.
    return _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")


def content_hash(value: Any) -> str:
    """Deterministic content hash over a JSON-serializable value."""
    canonical = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(canonical).hexdigest()[:16]


def _build_prov_document(
    dp_id: str,
    source_state: str,
    collector_id: str,
    generated_at: str,
) -> _prov.ProvDocument:
    """Build a minimal PROV-DM document for a single data-point emission.

    Encodes three PROV relations per W3C PROV-DM §5:
      - wasGeneratedBy  (entity ← activity, with prov:time)
      - wasDerivedFrom  (entity ← source entity)
      - wasAttributedTo (entity ← agent)
    """
    d = _prov.ProvDocument()
    d.add_namespace("ex", _EX_NS)

    entity_qn = f"ex:{dp_id}"
    source_qn = f"ex:{source_state}"
    agent_qn = f"ex:{collector_id}"
    activity_qn = f"ex:collection:{collector_id}"

    entity = d.entity(entity_qn)
    source = d.entity(source_qn)
    agent = d.agent(agent_qn)
    activity = d.activity(activity_qn)

    d.wasGeneratedBy(entity, activity, time=generated_at)
    d.wasDerivedFrom(entity, source)
    d.wasAttributedTo(entity, agent)
    return d


def _validate_prov_block(prov_block: dict) -> tuple[bool, str]:
    """Round-trip the provenance block through prov-python to confirm
    it is structurally well-formed per W3C PROV-DM.

    Extracts the three required fields, builds a ProvDocument, and
    verifies it contains exactly the expected entity, agent, and
    three PROV relations.  Returns (ok, reason).
    """
    attributed = prov_block.get("prov:wasAttributedTo")
    derived = prov_block.get("prov:wasDerivedFrom")
    generated = prov_block.get("prov:wasGeneratedAtTime")

    if not isinstance(attributed, dict) or "kind" not in attributed:
        return False, "prov_block:wasAttributedTo_not_pointer"
    if not isinstance(derived, str) or not derived:
        return False, "prov_block:wasDerivedFrom_empty"
    if not isinstance(generated, str) or not generated:
        return False, "prov_block:wasGeneratedAtTime_empty"

    collector_id = attributed.get("target", {}).get("collector_id", "unknown")
    try:
        d = _build_prov_document(
            dp_id="check", source_state=derived,
            collector_id=collector_id, generated_at=generated,
        )
        # Confirm the document has all three expected PROV relations.
        # prov-python uses: ProvGeneration (wasGeneratedBy),
        # ProvDerivation (wasDerivedFrom), ProvAttribution (wasAttributedTo).
        records = list(d.get_records())
        rel_types = {type(r).__name__ for r in records}
        required = {"ProvGeneration", "ProvDerivation", "ProvAttribution"}
        missing = required - rel_types
        if missing:
            return False, f"prov_doc_missing_relations:{sorted(missing)}"
    except Exception as exc:  # noqa: BLE001
        return False, f"prov_build_error:{exc}"
    return True, "ok"


def make_data_point(
    *,
    collector_id: str,
    kind: str,
    value: Any,
    source_state: str,
    collector_pointer: dict,
    witness: str | None = None,
) -> dict:
    """Construct a Foundation-1 conformant record with PROV-DM provenance.

    `witness` defaults to content_hash(value); collectors override only when
    they have a separate fingerprint of their *inputs* (preferred) so that
    re-derivation can be checked without re-hashing the value.

    Provenance fields use W3C PROV-DM vocabulary (PROV-JSON names):
      prov:wasAttributedTo    — the collector pointer (Foundation-3 pointer)
      prov:wasDerivedFrom     — the source_state identifier
      prov:wasGeneratedAtTime — advisory wall-clock at collection
    """
    cid = content_hash(value)
    if witness is None:
        witness = cid
    return {
        "id": f"{collector_id}:{cid}",
        "kind": kind,
        "value": value,
        "provenance": {
            "prov:wasAttributedTo": collector_pointer,
            "prov:wasDerivedFrom": source_state,
            "prov:wasGeneratedAtTime": _now_iso(),
        },
        "witness": witness,
    }


def validate(dp: dict) -> tuple[bool, str]:
    """Schema check. Returns (ok, reason). Does NOT re-derive."""
    if not isinstance(dp, dict):
        return False, "not_a_record"
    for field in ("id", "kind", "value", "provenance", "witness"):
        if field not in dp:
            return False, f"missing_field:{field}"
    prov = dp["provenance"]
    for sub in ("prov:wasAttributedTo", "prov:wasDerivedFrom", "prov:wasGeneratedAtTime"):
        if sub not in prov:
            return False, f"missing_field:provenance.{sub}"
    extras = set(dp.keys()) - {"id", "kind", "value", "provenance", "witness"}
    if extras:
        return False, f"extra_fields:{sorted(extras)}"
    if not isinstance(dp["id"], str) or ":" not in dp["id"]:
        return False, "bad_id_format"
    if not isinstance(dp["kind"], str) or not dp["kind"]:
        return False, "bad_kind"
    if not isinstance(dp["witness"], str) or not dp["witness"]:
        return False, "bad_witness"
    # Structural PROV-DM validation via prov-python.
    ok, reason = _validate_prov_block(prov)
    if not ok:
        return False, reason
    return True, "ok"


def write_jsonl(path: Path, dps: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for dp in dps:
            f.write(json.dumps(dp, sort_keys=True) + "\n")


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]
