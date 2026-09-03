# Builder Lifecycle Hooks

The builder budget has two enforcement layers. Repository-local lifecycle hooks
block invalid mutations inside Codex and Claude. The task-batch orchestrator
still owns deadlines and must interrupt a builder that is thinking without
calling tools; hooks cannot preempt an in-flight model request.

## Agent-specific setup

Bootstrap both runtimes before mining. The command is idempotent: it installs
the shared `.agents/skills`, `.codex/skills`, and `.claude/skills` links,
records project trust in the Codex and Claude user configs, validates the
committed hook files, and runs no-lease smoke checks:

```bash
python3 .agent/skills/task-batch/scripts/setup_agent_hooks.py \
  --install --trust --self-test
```

Both configurations call the same policy engine, but pass a different
`--runtime`. The lease binds on `SubagentStart` only when `agent_type` matches
the builder pattern. Reviewers, auditors, blind solvers, and ordinary repo
sessions therefore remain outside the gate.

## Stage A: candidate gate

Create a hash-bound context packet before launching a builder. Do not paste the
full files into the prompt; name the packet and let the informed builder read
only its recorded inputs.

```bash
python3 .agent/skills/task-batch/scripts/builder_context_packet.py \
  --stage candidate_gate --candidate tbrain-example \
  --input durable_memory=AGENTS.md \
  --input pattern_catalog=.agent/skills/task-miner/frontier_task_design_patterns.md \
  --input batch_portfolio=workspace/reports/batches/BATCH.json \
  --output workspace/reports/tbrain-example/context-candidate-gate.json

python3 .agent/skills/task-batch/scripts/builder_stage_guard.py start \
  --runtime codex --batch-id BATCH --candidate tbrain-example \
  --stage candidate_gate --agent-type-pattern '(^|/)batch_builder$' \
  --context-receipt workspace/reports/tbrain-example/context-candidate-gate.json
```

Use `--runtime claude` for a Claude builder. Name the subagent
`batch_builder`, or change the explicit pattern to its exact agent type. Stage
A may mine only this candidate and must finish with a canonical source smoke.
The smoke plan uses a digest-pinned image and an argv array:

```json
{
  "schema_version": 1,
  "candidate_slug": "tbrain-example",
  "source_dir": "workspace/sources/example",
  "source_revision": "<commit>",
  "image": "<registry>/<image>@sha256:<64 hex>",
  "command": ["cargo", "check", "--locked"],
  "timeout_seconds": 900
}
```

Run it through the single canonical entry point. It copies the source into a
disposable build tree, disables network access, records output and the source
tree hash, and removes the build tree afterward.

```bash
python3 .agent/skills/task-batch/scripts/canonical_source_smoke.py \
  workspace/reports/tbrain-example/source-smoke-plan.json \
  --output workspace/reports/tbrain-example/source-smoke.json
```

On mining rejection or smoke failure, close the lease immediately and end the
builder turn. Never mine another candidate in that turn:

```bash
python3 .agent/skills/task-batch/scripts/builder_stage_guard.py close \
  --outcome rejected --reason 'canonical source smoke failed'
```

Each infrastructure repair must be recorded with `repair`. Repairs have no
internal count limit; close the candidate only when the source/environment is
fundamentally unusable or repeated evidence shows no meaningful progress.

## Stage B and later turns

After Stage A passes, prepare the stage-specific context packet and transition
the same lease. A transition preserves the builder identity but clears the
bound turn ID, so work can continue only in a new counted follow-up:

```bash
python3 .agent/skills/task-batch/scripts/builder_context_packet.py \
  --stage scaffold --candidate tbrain-example \
  --input mined_candidate=workspace/reports/tbrain-example/mined-candidate.json \
  --input source_smoke_receipt=workspace/reports/tbrain-example/source-smoke.json \
  --input clone_skill=.agent/skills/task-clone/SKILL.md \
  --output workspace/reports/tbrain-example/context-scaffold.json

python3 .agent/skills/task-batch/scripts/builder_stage_guard.py transition \
  --stage scaffold \
  --context-receipt workspace/reports/tbrain-example/context-scaffold.json \
  --source-smoke-receipt workspace/reports/tbrain-example/source-smoke.json
```

Use separate counted follow-ups for `scaffold`, `oracle_verifier`, and a
permitted `remediation`. The default deadlines are 25, 30, 40, and 25 minutes.
While a builder is running, wait in intervals no longer than 60 seconds, call
`builder_stage_guard.py check`, and interrupt the exact builder when the
deadline expires. A hook catches the next mutation but is not a timer daemon.

The guard blocks obvious cross-candidate mutations, early task scaffolding,
direct Stage-A Docker builds that bypass the canonical smoke, stale source
receipts, a second model turn without transition, and edits to the hook/lease
files. It is workflow enforcement, not a hostile-code sandbox; Docker
isolation and the existing anti-cheat gates remain mandatory.
