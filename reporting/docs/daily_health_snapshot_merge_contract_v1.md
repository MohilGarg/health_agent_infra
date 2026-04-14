# daily health snapshot merge contract v1

This bounded contract freezes truthfulness behavior for `daily_health_snapshot` over the current flagship day-proof boundary.

## field ownership by canonical lane

- Garmin owns sleep, readiness, resting HR, HRV, body battery/readiness, and running rollups.
- Cronometer owns food-logging and nutrition totals, plus hydration only when canonicalized for the same target date. It remains a bridge/reference lane rather than a flagship day-proof requirement.
- wger owns gym rollups when present, but remains an exploratory non-flagship connector rather than a flagship day-proof requirement.
- Subjective fields remain reserved for the typed manual readiness or equivalent canonical subjective lane and stay unset unless that lane is ready.

## allowed lane states

- `ready`
- `missing`
- `stale`
- `blocked`

## mandatory rules

- `daily_health_snapshot` may consume only canonical lane artifacts, never raw-source receipts directly.
- if an owning lane is `missing`, `stale`, `blocked`, or date-misaligned, that lane's owned fields stay unset.
- a declared flagship-complete claim must fail closed unless Garmin and the typed manual readiness or subjective lane are both `ready` for the same target date.
- Cronometer and external gym connectors may enrich the snapshot when they are `ready`, but they do not gate truthful flagship day proof.
- truthful outcomes are limited to:
  - `snapshot_emitted_partial_truthful`
  - `snapshot_emitted_complete_for_declared_lanes`
  - `snapshot_blocked`
- snapshot provenance must use `derivation_method = cross_source_merge` and include supporting refs to upstream canonical artifacts plus explicit lane states.

## proof bundle

The bounded proof bundle for this slice lives under:

- `reporting/artifacts/protocol_layer_proof/2026-04-12-daily-health-snapshot-merge-contract-v1/`

It includes explicit blocked flagship-lane, optional-lane degraded, and fully aligned cases plus replay-stability evidence.
