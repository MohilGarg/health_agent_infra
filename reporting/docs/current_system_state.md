# Current system state

**Status:** current truth as of the v0.1.15 publish on 2026-05-03.

This file is the short operational answer to "what is true now?"
Use it before reading cycle-level audit history. Release artifacts
(`PLAN.md`, `RELEASE_PROOF.md`, `REPORT.md`, Codex responses) remain
the provenance trail; this file is the current-state map.

## Shipped baseline

| Surface | Current value | Source of truth |
|---|---|---|
| Package version | `0.1.15` | `pyproject.toml`, `CHANGELOG.md` |
| Published posture | PyPI package published; second-user empirical validation pending | `reporting/plans/v0_1_15/RELEASE_PROOF.md` |
| Schema head | `25` | `src/health_agent_infra/core/state/migrations/` |
| CLI commands | 60 annotated `hai` commands | `hai capabilities --json` |
| Test gate at release | 2630 passed, 3 skipped | `reporting/plans/v0_1_15/RELEASE_PROOF.md` |
| Domains | recovery, running, sleep, stress, strength, nutrition | `src/health_agent_infra/domains/` |
| Runtime state | local SQLite by default; no package telemetry | `reporting/docs/privacy.md`, `SECURITY.md` |

## Product claim

Health Agent Infra is a local governed runtime for a personal-health
agent. The maintainer dogfoods it daily. v0.1.15 made the package
installable from PyPI for a non-maintainer and closed the candidate
package bugs found before publish.

The stronger claim, "a non-maintainer completed the full flow under
recorded observation," is **not yet proven**. Mohil's recorded session
against `health-agent-infra==0.1.15` is post-publish empirical
validation; findings feed v0.1.16.

## v0.1.15 shipped

- `gym_set.set_id` now includes exercise slug; migration 024 rewrites
  old-format ids while preserving custom correction rows.
- CSV fixtures default-deny against the canonical state DB on both
  `hai pull` and `hai daily`; explicit opt-in or demo/non-canonical
  destination required.
- `hai intake gaps` emits a `present` block, `is_partial_day`, and
  `target_status` for nutrition target availability.
- `hai target nutrition` writes four atomic macro target rows using
  the existing `target` table; migration 025 extends `target_type`
  with `carbs_g` and `fat_g`.
- Nutrition classification suppresses partial-day/no-target cases to
  `nutrition_status='insufficient_data'`.
- `merge-human-inputs` consumes the W-A presence block for recap vs
  forward-march framing.

## Next cycles

| Cycle | Role |
|---|---|
| v0.1.16 | Empirical fixes from Mohil's recorded session plus `hai explain` foreign-user pass. PLAN.md authors after the transcript exists. |
| v0.1.17 | Maintainability + eval consolidation: W-29 cli.py split, W-30 regression prep, eval substrate, persona residuals, `hai sync purge`, body-comp intake, W-D arm-2, and W-C-EQP. |
| v0.2.0 | Weekly review (W52) + deterministic factuality (W58D) + Path A doc adjuncts. |

## How to update this file

Update this file after any release that changes package version,
schema head, command count, test gate, product claim, or next-cycle
role. Do not mirror detailed CLI command metadata here; regenerate
`reporting/docs/agent_cli_contract.md` from
`hai capabilities --markdown` instead.
