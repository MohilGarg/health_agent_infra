# daily health snapshot merge contract v1

This bounded contract freezes truthfulness behavior for `daily_health_snapshot` over the v1 trio.

## field ownership by canonical lane

- Garmin owns sleep, readiness, resting HR, HRV, body battery/readiness, and running rollups.
- Cronometer owns food-logging and nutrition totals, plus hydration only when canonicalized for the same target date.
- wger owns gym rollups.
- Subjective fields remain reserved for a separate canonical subjective lane and stay unset unless that lane is ready.

## allowed lane states

- `ready`
- `missing`
- `stale`
- `blocked`

## mandatory rules

- `daily_health_snapshot` may consume only canonical lane artifacts, never raw-source receipts directly.
- if an owning lane is `missing`, `stale`, `blocked`, or date-misaligned, that lane's owned fields stay unset.
- a declared trio-complete claim must fail closed unless Garmin, Cronometer, and wger are all `ready` for the same target date.
- truthful outcomes are limited to:
  - `snapshot_emitted_partial_truthful`
  - `snapshot_emitted_complete_for_declared_lanes`
  - `snapshot_blocked`
- snapshot provenance must use `derivation_method = cross_source_merge` and include supporting refs to upstream canonical artifacts plus explicit lane states.

## proof bundle

The bounded proof bundle for this slice lives under:

- `reporting/artifacts/protocol_layer_proof/2026-04-12-daily-health-snapshot-merge-contract-v1/`

It includes explicit blocked, date-misaligned, and fully aligned cases plus replay-stability evidence.
