# Status

## Architecture (post-reshape, 2026-04-17)

Health Agent Infra is a **tools-plus-skills package** an agent installs:

- **Python tools** — `src/health_agent_infra/` exposes a `hai` CLI with subcommands for pull, clean, writeback, review, and setup-skills. All deterministic. The runtime holds no classification, no policy, no recommendation logic.
- **Markdown skills** — `skills/` ships five skills: `recovery-readiness`, `reporting`, `merge-human-inputs`, `writeback-protocol`, `safety`. An agent reads these to decide what to do with the evidence.
- **Determinism boundary** — `hai writeback` validates the agent's recommendation JSON against `TrainingRecommendation` before persisting. Malformed recommendations fail closed.

## What's proven

The flagship loop runs end-to-end with an agent doing the judgment:

```
hai pull (Garmin CSV)
    └─► hai clean
            └─► agent reads CleanedEvidence + RawSummary + recovery-readiness skill
                    └─► agent produces TrainingRecommendation JSON
                            └─► hai writeback (schema-validated + idempotent)
                                    └─► hai review schedule
                                            └─► hai review record (next day)
```

- 14 deterministic + contract tests passing in `safety/tests/test_recovery_readiness_v1.py`.
- Two proof bundles preserved as inputs-and-outputs examples:
  - `reporting/artifacts/flagship_loop_proof/2026-04-16-recovery-readiness-v1/` — 8 synthetic scenarios (from the pre-reshape era). Bundle contents describe what the agent-plus-skills can be expected to produce on those inputs.
  - `reporting/artifacts/flagship_loop_proof/2026-04-16-garmin-real-slice/` — the real Garmin CSV slice.
  - Note: the captured JSONs were produced by the pre-reshape Python runtime. Regenerating them under the new skills-driven flow is a follow-on.

## Install and run

```bash
pip install -e .
hai setup-skills
hai --help
```

See [README.md](README.md) for the full subcommand list and [reporting/docs/agent_integration.md](reporting/docs/agent_integration.md) for Claude Code and Claude Agent SDK integration notes.

## Doctrine

The controlling doctrine is [`reporting/docs/canonical_doctrine.md`](reporting/docs/canonical_doctrine.md). Non-goals are frozen in [`reporting/docs/explicit_non_goals.md`](reporting/docs/explicit_non_goals.md). The reshape itself is recorded in [`reporting/docs/phase_timeline.md`](reporting/docs/phase_timeline.md).

## What this is not

- Not a clinical product or medical device.
- Not hosted or multi-user.
- Not a polished install flow for general users.
- Not a learning loop — no ML model in the runtime.
- Not a multi-source platform — Garmin plus typed manual readiness only. Broader source fusion is out of scope.
- Not a replacement for a coach, clinician, or informed user judgment.

## Tools + skills at a glance

| Layer | Surface | Location |
|---|---|---|
| Data acquisition | `hai pull` + Garmin adapter | `src/health_agent_infra/pull/` |
| Normalization / raw aggregation | `hai clean` | `src/health_agent_infra/clean/` |
| Schema-validated writeback | `hai writeback` | `src/health_agent_infra/writeback/` |
| Review scheduling + outcomes | `hai review` | `src/health_agent_infra/review/` |
| State classification + policy + recommendation | recovery-readiness skill | `skills/recovery-readiness/SKILL.md` |
| User-facing narration | reporting skill | `skills/reporting/SKILL.md` |
| Raw human input partitioning | merge-human-inputs skill | `skills/merge-human-inputs/SKILL.md` |
| Writeback invocation protocol | writeback-protocol skill | `skills/writeback-protocol/SKILL.md` |
| Fail-closed boundaries | safety skill | `skills/safety/SKILL.md` |

## What's next

No active roadmap beyond the reshape. Candidate directions — to be picked deliberately, not executed by default:

- Regenerate the 2026-04-16 proof bundles with a real agent driving the skills-driven flow, so the captured JSONs match what the runtime actually produces now (not just what the pre-reshape Python produced).
- Add a second source adapter conforming to `FlagshipPullAdapter` (e.g., a typed manual readiness intake adapter distinct from the neutral default).
- Publish to PyPI once the install story is validated by a real user run.
- MCP server wrapper for agents that prefer MCP over CLI subcommands.
