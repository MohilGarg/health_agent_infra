# Agent Integration

How a Claude agent (or open Claude-equivalent) installs and uses Health Agent Infra.

The package ships two things the agent consumes:

1. **A CLI called `hai`** — deterministic subcommands on the user's PATH.
2. **Five markdown skills** under `skills/` — judgment-layer instructions.

The agent reads skills, makes decisions, and invokes CLI subcommands to move structured state. The CLI validates the agent's output at the writeback boundary.

## Install

For local development:

```bash
cd /path/to/health_agent_infra
pip install -e .
hai setup-skills
```

`pip install -e .` exposes the `hai` command on the user's PATH. `hai setup-skills` copies every directory under `skills/` into `~/.claude/skills/` (or a custom path via `--dest`). If a skill of the same name already exists, `hai setup-skills` skips it unless `--force` is passed.

Verify:

```bash
hai --help
ls ~/.claude/skills/   # should list recovery-readiness, reporting, merge-human-inputs, writeback-protocol, safety
```

## Claude Code

After `hai setup-skills`, Claude Code discovers the skills automatically the next time it starts. The skills appear in its available-skills list with descriptions drawn from each `SKILL.md` frontmatter.

The agent invokes CLI subcommands via its `Bash` tool. Each `SKILL.md` scopes `allowed-tools` to the exact CLI patterns it needs — e.g., the writeback-protocol skill allows `Bash(hai writeback *)` and `Bash(hai review *)` but not other commands.

Typical agent loop in Claude Code:

1. User: "Give me today's training recommendation."
2. Agent reads `recovery-readiness` skill (loaded on user prompt or via skill discovery).
3. Agent: `hai pull --date $(date +%Y-%m-%d) --use-default-manual-readiness --user-id u_1 > /tmp/evidence.json`
4. Agent: `hai clean --evidence-json /tmp/evidence.json > /tmp/prep.json`
5. Agent reads `prep.json`, classifies state and applies policy per the skill, writes `TrainingRecommendation` JSON to `/tmp/rec.json`.
6. Agent: `hai writeback --recommendation-json /tmp/rec.json --base-dir ~/.local/share/hai/recovery_readiness_v1`
7. Agent: `hai review schedule --recommendation-json /tmp/rec.json --base-dir ~/.local/share/hai/recovery_readiness_v1`
8. Agent uses the `reporting` skill to narrate the recommendation back to the user.

## Claude Agent SDK

Two options:

1. **CLI subcommand dispatch** — the SDK agent runs `hai` subcommands via shell. This is the same flow as Claude Code. Fully agent-agnostic.
2. **Direct Python imports** — if the SDK is running in the same Python environment where `pip install -e .` happened, the agent can `from health_agent_infra.clean import clean_inputs, build_raw_summary` and call functions directly. This skips subprocess overhead but couples the agent to Python. Use only for performance-sensitive inner loops.

For the SDK, skill discovery is not automatic. Upload skills to the Anthropic Skills API (the SDK has org-level support) or reference them by file path in your agent's system prompt.

## Other Claude surfaces

- **Claude.ai** — skill upload is per-user via the UI. Upload each `skills/<skill>/SKILL.md` manually; supporting files in a skill directory are not currently supported there.
- **Web API** — use the Skills API to register skills by `skill_id` and reference them in conversation turns.

## Open Claude-equivalent agents

Any agent with:

- A shell-exec tool (for `hai` subcommands), AND
- A way to load markdown system-prompt fragments at session start (for the skills)

can drive this package. The contract between agent and runtime is the `TrainingRecommendation` JSON schema at `hai writeback` — open-source agents just need to produce a valid JSON.

## MCP

No MCP server ships yet. A future wrapper could expose the CLI subcommands as MCP tools for agents that prefer MCP over shell. Tracked in `STATUS.md` under "what's next."

## Where tools expect paths

- `hai pull` reads from `pull/data/garmin/export/daily_summary_export.csv` (packaged with the repo; override via `--export-dir` in the adapter call if needed).
- `hai writeback` requires `--base-dir` whose path ends in `recovery_readiness_v1/`. Enforced at the I/O boundary. Suggested default: `~/.local/share/health_agent_infra/recovery_readiness_v1/`.
- `hai setup-skills` defaults to `~/.claude/skills/`. Override via `--dest`.

## Where the determinism boundary is

**Schema validation at `hai writeback`.** When the agent produces a `TrainingRecommendation` JSON, the tool deserializes and validates against the dataclass shape in `src/health_agent_infra/schemas.py`. Missing required fields, wrong types, or unknown action values fail closed with a clear error, and nothing persists. This is the one place the runtime enforces the agent's output shape.

Everything upstream of that (pull, clean) is deterministic pure functions on evidence. Everything downstream (writeback, review) is idempotent persistence with locality enforcement.

## What an agent should NOT do

- Modify JSONL files directly. All state mutation goes through `hai`.
- Claim more than the evidence supports. Rationale in the recommendation must reference raw_summary numbers.
- Use diagnostic / clinical language. R2 in the recovery-readiness skill and the writeback schema check both reject it.
- Call `hai` subcommands outside its `allowed-tools` scope in the relevant skill.
