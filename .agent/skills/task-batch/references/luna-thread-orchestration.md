# Luna Review-Thread Orchestration

Use this workflow for the two fairness reviewers and the consolidated auditor.
They are independent Codex tasks, not collaboration subagents. The builder and
blind solvers remain `gpt-5.6-sol` collaboration subagents.

## Authorization and availability

Invoking `task-batch N` authorizes the visible role tasks required by this
workflow. They appear in the Codex sidebar. Before spending a builder turn:

1. Confirm that `list_projects`, `create_thread`, `wait_threads`, `read_thread`,
   and `send_message_to_thread` are available.
2. Call `list_projects` and resolve the current repository's exact project ID.
3. Confirm that `create_thread` advertises `gpt-5.6-luna` with `high` and `max`.

Fail closed if any capability or profile is unavailable. Do not substitute a
model, use the parent task as a reviewer, or claim that changing
`~/.codex/config.toml` unlocks a missing thread profile.

## Snapshot and prompt isolation

Create a hash-bound fairness packet containing only `instruction.md` plus the
agent-visible environment/evidence. Exclude `solution/`, `tests/`, rubrics,
reports, intended mechanisms, builder notes, and prior probe results. Give each
fairness task only the packet path, its SHA-256, the review contract, and the
required output schema. Require read-only behavior and an explicit attestation
that no excluded surface was inspected.

Create the auditor task only after the semantic draft and deterministic gates
are complete. Give it the exact task snapshot and only the receipts needed for
semantic realism, folder/manual review, and task-tree style judgment. Do not
give it builder dispositions or intended answers. Require read-only behavior;
the orchestrator writes returned reports into the canonical report directory.

Use a project worktree created from `working-tree` so each role sees the exact
uncommitted snapshot without mutating the builder checkout. A role task must
not edit task files, commit, push, or create a PR.

## Launch and collection

Launch the fairness pair asynchronously with separate `create_thread` calls:

- model `gpt-5.6-luna`, thinking `high`;
- titles `<slug> fairness 1` and `<slug> fairness 2`;
- distinct thread IDs and the same hash-bound fairness packet.

Wait on both in one bounded `wait_threads` call and carry each returned cursor
forward. Use `read_thread` only to capture the completed turn and transcript.
Do not wake on commentary or repeatedly reread unchanged state. If a task asks
for information, provide only an operational clarification already present in
its packet; never reveal builder or verifier-only context.

Launch one auditor task with model `gpt-5.6-luna`, thinking `max`, title
`<slug> consolidated auditor`, then collect it the same way. Reuse this exact
thread after probes with `send_message_to_thread`; omit model changes or set the
same Luna/max profile explicitly. The follow-up is a new counted turn but the
auditor session identity remains the original thread ID.

For one permitted remediation cycle, send the revised hash-bound packet to the
same reviewer or auditor threads. Do not create replacement identities. Reject
the candidate if the same gate fails again.

## Provenance

For every Luna review/audit turn, record:

```json
{
  "execution_surface": "codex_thread",
  "runtime": "codex-thread",
  "model": "gpt-5.6-luna",
  "reasoning_effort": "high",
  "session_id": "<actual threadId>",
  "thread_id": "<same actual threadId>",
  "host_id": "<actual hostId>"
}
```

Use `max` for the auditor. Save the exact returned final text as the transcript,
plus its SHA-256. A task title, client-generated pending ID, or invented label
is not a session ID. Do not record a turn as complete until `wait_threads`
reports completion and `read_thread` provides the corresponding final output.
