# Internal Docs Audit - post-v0.1.15

**Date:** 2026-05-03  
**Trigger:** v0.1.15 was published, then the maintainer flagged that
the internal docs felt weaker than the code/audit discipline.
**Scope:** current-state and operator-facing docs: root overview docs,
`reporting/docs/`, planning indexes, v0.1.16/v0.1.17 workspace READMEs,
and tactical roadmap surfaces. Frozen historical audit artifacts were
read for provenance but not rewritten.

## Verdict

The audit trail is strong; the operating docs were weaker. The main
problem was not missing evidence, but routing: readers had to walk
release artifacts and audit responses to reconstruct current truth.
Several current-state surfaces still described v0.1.14.1 / schema 023
or the pre-publish W-2U-GATE sequencing after v0.1.15 had shipped.

This pass adds a current-truth document and updates the drifted
summary surfaces. Historical references in frozen cycle artifacts are
left intact.

## Findings and fixes

| Finding | Severity | Disposition |
|---|---|---|
| F-DOC-01 current-version drift | high | Fixed root README, ROADMAP, reporting index, planning index, tactical plan, and current-state references to show v0.1.15 as shipped, not pending. |
| F-DOC-02 schema-head drift | high | Fixed state-model, architecture, memory-model, and docs index references from migration 023/v0.1.14.1 to migration 025/v0.1.15. |
| F-DOC-03 publish-first pivot drift | high | Fixed v0.1.16 README, tactical §5B/§5C, ROADMAP dependency chain, and current-state wording so W-2U-GATE is post-publish empirical validation feeding v0.1.16, not a pre-publish ship gate. |
| F-DOC-04 current truth buried in audit history | medium | Added `reporting/docs/current_system_state.md` as the first stop for "what is true now?" and linked it from the docs/plans/reporting maps. |
| F-DOC-05 brittle exact mirrors | medium | Kept generated CLI detail in `agent_cli_contract.md`; summary docs now point to generated sources and only carry small counts. |

## Residual risks

- `verification/tests/test_doc_freshness_assertions.py` still only catches
  a narrow class of stale "current version" claims. It does not yet verify
  schema head, command count, or next-cycle sequencing across docs.
- Long tactical/strategic docs still mix active plan rows with historical
  provenance. They are usable, but a future docs cycle should consider
  splitting tactical history from the next-cycle authoring surface.
- Line-number citations remain useful in audit responses but should not
  be copied into durable orientation docs unless a test pins them.

## Recommendation

No separate release is needed for this docs pass unless the maintainer
wants a packaged docs-only version. Keep the changes as post-v0.1.15
documentation cleanup, then run v0.1.16 from the new current-state map
plus the v0.1.16 workspace README once Mohil's transcript exists.
