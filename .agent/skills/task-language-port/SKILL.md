---
name: task-language-port
description: Use only when the user explicitly requests a language migration of an existing Terminus task for internal reuse, compatibility testing, or replacement. Terminus 3 does not treat a language change or narrative reskin as a novel independently-submittable task.
---

# Task Language Port

Terminus 3 requires every submission to be novel. A different implementation
language, cover story, slug, or variable vocabulary does not create novelty.
The portal explicitly rejects variations and reskins of Terminal-Bench 2.1,
Terminal-Bench 3.0, prior Terminus tasks, and an author's earlier work.

Use this skill only after an explicit user request and only for one of these
purposes:

- migrate a task to a supported runtime while replacing the original artifact
- test whether a verifier is truly language-agnostic
- produce an internal teaching or compatibility artifact that will not be
  submitted as a separate Terminus 3 task

If the user wants another independently-submittable task, stop the port. Use
`task-miner` to design a genuinely new setup, definition, data, domain evidence,
and behavior contract, then build it with `task-clone`.

## Migration workflow

1. Confirm the intended use and record that the result is not a separate novel
   submission.
2. Read the source task completely: `instruction.md`, `task.toml`, environment,
   solution, tests, artifact declarations, and verifier Dockerfile.
3. Preserve observable behavior, artifact paths, exact values, and all
   preservation requirements. Translate both the broken starter and oracle fix;
   do not silently simplify the gap.
4. Update `[metadata].languages` using lowercase language names. Keep the exact
   Terminus 3 category/subcategory pair unless the domain itself changes.
5. Keep the Terminus 3 contract: top-level `artifacts`, separate verifier,
   `tests/Dockerfile`, `network_mode`, 1800–18000 second agent timeout, and no
   removed Terminus 2 fields.
6. Adapt digest-pinned images and build commands. Bake every dependency into the
   relevant image; never install verifier dependencies at trial time.
7. Re-run oracle, nop, a deliberately wrong/incomplete candidate, static checks,
   instruction sufficiency, and artifact transfer checks. Independently
   spot-check the migrated oracle against the visible contract on hard inputs. A
   successful source-language task does not prove the migrated runtime works.
8. Package only if the user requested an internal ZIP or a replacement upload.

Do not create multiple sibling ports, mandatory narrative reskins, or a
same-corpus language series. Those were Terminus 2-era workflows and conflict
with the Terminus 3 novelty requirement.
