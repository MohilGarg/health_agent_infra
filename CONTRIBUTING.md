# Contributing

Thanks for looking at Health Agent Infra.

## Mental model

The project has two surfaces. Everything you contribute lands in one of them:

- **Python tools** under `src/health_agent_infra/` — deterministic data acquisition, normalization, validation, writeback, tests.
- **Markdown skills** under `skills/` — the agent's judgment layer. Classification, policy, recommendation, reporting, safety.

If it involves an if/else making a domain call, it's a skill, not code. If it moves bytes between well-defined schemas or enforces an invariant at an I/O boundary, it's a tool.

## How to add a tool

1. Decide which subpackage under `src/health_agent_infra/` it belongs to (`pull/`, `clean/`, `writeback/`, `review/`, or something new with an explicit reason).
2. Add a function or class with typed signatures. No hidden state, no global mutation, no judgment. Input in, output out.
3. Wire it into `src/health_agent_infra/cli.py` as a subcommand if the agent needs to invoke it.
4. Add a deterministic test under `safety/tests/` that fixes input → output.
5. If the tool produces structured output the agent consumes, add a dataclass to `src/health_agent_infra/schemas.py` and a round-trip test.

Never:
- Import from `skills/` inside Python code. Skills are for the agent, not the runtime.
- Add a threshold (e.g., "if X > 0.8") in Python. That's judgment — it belongs in a skill.
- Break the writeback-locality invariant (`base_dir` must contain `recovery_readiness_v1`).

## How to add a skill

1. Create a directory under `skills/<skill-name>/`.
2. Add a `SKILL.md` with standard YAML frontmatter (`name`, `description`, `allowed-tools`, `disable-model-invocation`). See the existing five skills for examples.
3. Keep the skill body under ~500 lines. If it grows, split into a `reference.md` and link from `SKILL.md`.
4. If the skill references a tool (e.g., `hai writeback`), add the tool pattern to `allowed-tools` so agents auto-approve it.
5. If the skill names a schema field, keep it in sync with `src/health_agent_infra/schemas.py`. There's no automated drift check yet — this is a manual discipline.

Never:
- Duplicate logic between two skills. If two skills need the same decision table, extract a shared reference file and both link to it.
- Use diagnosis-shaped language in any skill (`diagnosis`, `disease`, `syndrome`, etc.). The writeback tool's R2 policy rejects recommendations that contain those tokens; skills that produce them fail closed.
- Make a skill that tells the agent to call a tool the agent doesn't have access to. Scope `allowed-tools` tightly.

## Before opening a PR

1. `uv run --with pytest pytest safety/tests/` — must pass.
2. If you touched a tool: the tool has a deterministic test. Idempotency and locality invariants are preserved.
3. If you touched a skill: the frontmatter is valid, the content is actionable (decision tables, not prose alone), and `allowed-tools` is scoped.
4. If you touched schemas: every existing tool that produces/consumes the affected type is updated in the same commit.
5. If you touched docs: `README.md`, `STATUS.md`, and `reporting/docs/tour.md` agree.

## Good first changes

- Add a second adapter conforming to `FlagshipPullAdapter` (e.g., a typed manual readiness adapter with a real intake surface).
- Strengthen a contract test in `safety/tests/` — e.g., malformed recommendation JSON variants the writeback tool should reject.
- Expand a skill's decision tables with examples the agent can pattern-match against.
- Fix a documentation path that drifted.

## Not in scope

- UI, dashboard, or frontend.
- Multi-user or hosted-service features.
- A second health source (Apple Health, Oura, Strava, Whoop) — frozen by explicit non-goals.
- A learning loop / ML calibration of confidence deltas.
- Manual gym session schemas or nutrition pipelines — these were deliberately swept in the 2026-04-17 reshape. If the flagship scope needs to expand, open a plan doc first.

## If you're not sure

Read [`reporting/docs/tour.md`](reporting/docs/tour.md) (10-minute cold-read walkthrough), then [`reporting/docs/canonical_doctrine.md`](reporting/docs/canonical_doctrine.md) for the controlling thesis. Most contribution questions resolve there.
