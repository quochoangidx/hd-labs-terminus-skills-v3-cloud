# Claude Code entry point

`AGENTS.md` is the sole durable policy and team-memory source for this
repository. Do not copy its rules into this file.

Before working on a Terminus task:

1. Read `AGENTS.md` sections 1 and 2 (the condensed current rules).
2. Load the matching skill from `.claude/skills/`.
3. Read only the additional `AGENTS.md` sections and skill references cited by
   that workflow. Read the full file only when the task spans the whole
   authoring pipeline or a cited rule cannot be located safely.
4. Record each new durable finding as a short rule (1–3 sentences plus a
   pointer) in the matching `AGENTS.md` §2 theme, or repair the rule it changes
   in place, keeping the file consistent and conflict-free. Put long evidence in
   the relevant skill reference or a dated file under `docs/history/`.

Shared skills live under `.agent/skills/`. `.claude/skills/` is a symlink to
that directory; never create a second Claude-specific copy of a shared skill.
Claude-only execution profiles may live under `.claude/agents/` when the same
runtime control cannot be expressed in a shared `SKILL.md`.
