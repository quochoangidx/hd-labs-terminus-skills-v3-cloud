# Changelog

## 2026-07-25

### Added

- Added an instruction-sufficiency manifest and validator that map every graded behavior to an agent-visible contract source before difficulty probing.
- Added a shared task policy checker for open categories, lowercase language slugs, and canonical verifier runner requirements.
- Added evidence-backed batch handover validation for preflight, oracle, NOP, probe, review, style, and package artifacts.
- Added a canonical `tests/test.sh` template with fail-safe reward handling and isolated pytest execution.

### Changed

- Limited net-new task creation to `machine-learning`, `games`, and `system-administration`, matching the July 24 platform policy.
- Standardized blind solve probes on `gpt-5.5` with medium reasoning in Codex and Claude Opus 4.8 with medium reasoning in Claude Code.
- Made preflight strict and fail-closed, with JSON evidence, task-policy checks, artifact hashes, and ZIP emission only after all required gates pass.
- Updated task scaffolding, batch, cloning, validation, and review skills to use the shared policy, canonical verifier template, canary-first validation, and evidence-backed handover.
- Synced local documentation with the current Snorkel CLI authentication flow, verifier-integrity guidance, difficulty evaluation behavior, and category availability.

### Fixed

- Prevented manual task factories from drifting on category names, language casing, verifier shell behavior, and reward-file handling.
- Prevented task delivery when required validation evidence is missing, stale, mismatched, or failed.
- Added review blockers for unavailable categories and missing or invalid instruction-sufficiency evidence.
- Added an explicit revision-queue exception flag so category checks do not reject eligible pre-existing tasks.
