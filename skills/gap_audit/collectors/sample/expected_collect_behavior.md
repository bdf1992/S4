# Sample — claim_without_probe collector

## Synthetic input

[`synthetic_md_link_input.jsonl`](synthetic_md_link_input.jsonl) — three synthetic `md_link` records mirroring the shape `skills/claim_audit/collectors/markdown_claims.py` emits:

| id suffix | receipt | should produce a gap data point? |
| --- | --- | --- |
| `aaaa…` | `anchor_unverified` | yes (`looked_for=["resolve:repo_path_section_anchored"]`) |
| `bbbb…` | `live` | no (claim has a probe — claim_audit's resolver) |
| `cccc…` | `external` | no (claim is out-of-scope by construction) |

## Expected output of `collect()`

Given the synthetic input above placed at `INPUTS[0]` and a `source_state` argument, `collect()` should return a list of length **1** containing one `claim_without_probe` data point whose:

- `kind == "claim_without_probe"`
- `value.claim_pointer.target.data_point_id == "markdown_claims:aaaaaaaaaaaaaaaa"`
- `value.looked_for == ["resolve:repo_path_section_anchored"]`
- `provenance.collector.target.collector_id == "claim_without_probe"`

## Running

The current Foundation-2 collector reads from a hardcoded `INPUTS[0]` path. Running this sample directly requires either (a) temporarily redirecting `INPUTS[0]` to point at `synthetic_md_link_input.jsonl`, or (b) introducing a sample-runner harness. Both have design implications flagged in `audits/2026-04-30-overnight.md` for operator review.

Until the harness exists, this sample functions as a *declarative* demonstration of the input → output relationship. The collector's actual run against the live `skills/claim_audit/datasets/markdown_claims.jsonl` is the operational sample for this iteration.
