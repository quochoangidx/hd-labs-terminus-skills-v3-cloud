---
name: sync-doc-and-skill
description: Sync Terminus docs from the Snorkel portal and update dependent Terminus skills to match. Run periodically or when you suspect docs have changed. Fetch each document's markdown file directly from its portal docs path, diff it against local docs, patch local files, then audit Terminus skills for discrepancies and auto-fix them. Do not scrape the JS bundle for content because it is only the SPA shell and can carry stale hardcoded strings.
---

# Sync Docs and Skills

Automatically update local Terminus docs from the Snorkel portal, then cascade
changes to the Terminus skills that reference those docs.

## When to Use

- Before starting a new batch of tasks
- When CI rejects with a rule you haven't seen before
- When a reviewer cites a doc requirement your skill doesn't cover
- Periodically (e.g., weekly) to stay current

## Inputs

No arguments required. Optionally:
- `--docs-only` — sync docs but skip skill updates
- `--skills-only` — skip doc fetch, just re-audit skills against current local docs
- `--dry-run` — report what would change without writing files

## Architecture

```
Snorkel Portal (SPA)
    │
    ├── doc content served as plain markdown at /docs/<slug>.md (SPA fetches at runtime)
    │
    ▼
Step 1: Fetch each doc's .md file DIRECTLY (NOT from the JS bundle)
    │
    ▼
Step 2: Diff against local docs/
    │
    ▼
Step 3: Update local docs/ files
    │
    ▼
Step 4: Audit skills against updated docs
    │
    ▼
Step 5: Auto-fix skills
    │
    ▼
Step 6: Report changes
```

## Step 1 — Fetch Docs from Portal (direct `.md`, NOT the bundle)

The portal at `https://snorkel-ai.github.io/Terminus-EC-Training-stateful/` is an
SPA, but **doc content is served as plain markdown** that the app fetches at
runtime from `…/docs/<slug>.md` (content-type `text/markdown`). Fetch those
`.md` files DIRECTLY.

> ⚠️ Do NOT grep the JS bundle for doc content. The bundle is only the React
> shell; it carries stale hardcoded strings (confirmed 2026-06-14: the bundle
> still showed stale model names while the live `.md` had already changed).
> Also, the bundle has a content-hashed filename, so an
> UNCHANGED bundle name does NOT mean docs are unchanged — doc `.md` files change
> independently. The only reliable change-detector is diffing the fetched `.md`.

### 1a. Build the slug list (and detect new/removed pages)

The slug set normally matches local `docs/`. To catch newly-added pages, also
read the nav from the bundle (the bundle is still fine for the slug list):

```bash
PORTAL="https://snorkel-ai.github.io/Terminus-EC-Training-stateful"
BUNDLE=$(curl -sL "$PORTAL/" | grep -oE '/Terminus-EC-Training-stateful/assets/index-[^"]+\.js' | head -1)
curl -sL "https://snorkel-ai.github.io$BUNDLE" | grep -oE 'slug:"[^"]+"' | sed 's/slug:"//;s/"//' | sort -u > /tmp/portal_slugs.txt
find docs -name '*.md' | sed 's|docs/||;s|\.md$||' | sort > /tmp/local_slugs.txt
echo "== new pages in portal (create locally) =="; comm -23 /tmp/portal_slugs.txt /tmp/local_slugs.txt
echo "== local pages not in portal (flag) =="; comm -13 /tmp/portal_slugs.txt /tmp/local_slugs.txt
```

### 1b. Fetch each doc's markdown DIRECTLY (authoritative)

```bash
mkdir -p /tmp/livemd
cat /tmp/local_slugs.txt /tmp/portal_slugs.txt | sort -u | while IFS= read -r slug; do
  out="/tmp/livemd/$(echo "$slug" | tr '/' '_').md"
  code=$(curl -sL -H 'Cache-Control: no-store' -o "$out" -w '%{http_code}' "$PORTAL/docs/$slug.md?z=$RANDOM")
  [ "$code" = 200 ] && [ -s "$out" ] || echo "  [HTTP $code] fetch failed: $slug"
done
```

The directly-fetched `.md` is the source of truth even when curl gets a stale
cached bundle from the GitHub Pages CDN.

## Step 2 — Diff Against Local Docs

For each key rule area, compare online content with local docs:

### Critical rules to check (these cause CI failures and rejections):

| Rule Area | Local Doc File | Online Search Term |
|-----------|---------------|-------------------|
| Verifier dependency placement | `creating-tasks/writing-tests.md` | `test_deps_in_image`, `verifier dependencies`, `tests/wheels` |
| Separate verifier + artifacts | `creating-tasks/writing-tests.md` | `tests/Dockerfile`, `environment_mode`, `artifacts` |
| Sanctioned bases | `creating-tasks/dockerfile-best-practices.md` | `sanctioned` |
| test.sh canonical form | `creating-tasks/writing-tests.md` | `reward.txt` |
| Difficulty thresholds | `understanding-tasks/difficulty-guidelines.md` | `accuracy` |
| Inference vs under-specification | `understanding-tasks/what-makes-a-good-task.md`, `testing-and-validation/running-real-agents.md` | `specification must be inferred`, `hidden requirements`, `could not possibly obtain` |
| Category taxonomy | `understanding-tasks/task-taxonomy.md` | `subcategory` |
| Instruction styling | `understanding-tasks/prompt-styling.md` | `canary` |
| Category/policy live status | `reference/category-status.md` | `Terminus 3`, `subcategory`, `network_mode` |
| Rubric format | `understanding-tasks/rubrics.md` | `rubric` |
| tmux/asciinema | `creating-tasks/dockerfile-best-practices.md` | `tmux` |
| Per-phase network mode | `understanding-tasks/task-requirements.md` | `[environment]`, `[agent]`, `[verifier]`, `network_mode` |
| Docker-compose flags | `reviewing-tasks/reviewer-checklist.md` | `docker_compose` |
| Verifier integrity | `creating-tasks/writing-tests.md`, `reviewing-tasks/reviewer-checklist.md` | `complete expected artifact`, `dynamically`, `config` |
| CLI installation and credentials | `getting-started/quick-start.md`, `testing-and-validation/running-real-agents.md` | `snorkelai-stb`, `stb login`, `keys refresh` |
| Difficulty trial schedule | `understanding-tasks/difficulty-guidelines.md` | `4 runs`, `8 runs`, `GPT-5.6`, `Claude Opus 5` |
| Live category availability | `reference/category-status.md`, `reference/changelog.md` | `seven categories`, `milestones are removed` |
| Internet-enabled reproducibility | `creating-tasks/dockerfile-best-practices.md` | per-phase `network_mode`, `digest`, `stable invariants` |
| Cloud image-builder syntax | `creating-tasks/dockerfile-best-practices.md`, `testing-and-validation/ci-checks-reference.md` | `check_modal_dockerfile_compat`, `COPY --chown`, `COPY --from` |
| Hardware/CAD geometry verification | `creating-tasks/cad-task-guidelines.md` | `direct measurement`, `sampling`, `recompute`, `built geometry` |

### Diff format

For each rule area, report:
```
=== verifier dependency placement ===
ONLINE: "Verifier dependencies should be installed before test.sh runs."
   ALT: "Dependency wheels under tests/ are not allowed by current client feedback."
LOCAL:  "Bake verifier dependencies into the Docker image with exact pins; tests/test.sh must not install packages."
STATUS: ✅ ALIGNED (after last sync)
```

## Step 3 — Update Local Docs

For each discrepancy found:

1. **Online added new content** → append to local doc file
2. **Online changed a rule** → update local doc file with online version
3. **Online removed content** → flag for manual review (don't auto-delete)
4. **New page in online nav** → create the local file from the directly fetched Markdown

**Always preserve local additions** (e.g., empirical notes, Go-specific guidance) that don't contradict online docs.

## Step 4 — Audit Skills Against Updated Docs

After docs are synced, audit the doctrine-coupled set:

```
.agent/skills/task-miner/SKILL.md (+ category_rules.md)
.agent/skills/task-clone/SKILL.md
.agent/skills/task-batch/SKILL.md
.agent/skills/task-zip-validator/SKILL.md
.agent/skills/task-zip-submit/SKILL.md
.agent/skills/task-client-feedback-review/SKILL.md
.agent/skills/task-language-port/SKILL.md
.agent/skills/terminus-regular-task-authoring/SKILL.md
.agent/skills/task-harbor-runner/SKILL.md
.agent/skills/task-llm-style-audit/SKILL.md
.agent/skills/task-revise-flag-remediation/SKILL.md
.agent/skills/terminus-hard-python-verifier/SKILL.md
.agent/skills/terminus-rust-task-authoring/SKILL.md
```

### Audit checklist (check each rule in each skill):

| Rule | task-miner | task-clone | task-zip-validator |
|------|-----------|------------|-------------------|
| test.sh canonical form | — | template | check |
| verifier dependency placement | — | guidance | check |
| Sanctioned base images | — | Docker Rules | check |
| tmux/asciinema required | runtime risk | Docker Rules | check |
| Separate verifier + artifacts | candidate shape | layout/metadata | check |
| network_mode | candidate viability | metadata defaults | check |
| Terminus 3 taxonomy | candidate category | metadata defaults | check |
| Difficulty thresholds | scoring mapping | validation | check |
| Language-independent tiers | scoring mapping | metadata | check |
| Rubric requirements | — | rubric section | reminder |
| docker-compose flags | — | Docker Rules | check |
| Canary string | — | instruction style | check |
| AI scaffolding files | — | cleanup | check |
| Env spec anti-bypass | — | — | check |
| Instruction styling | prompt template | instruction style | check |
| Build context size | — | quality preflight | check |
| No end-to-end solver in `tests/` | — | verifier architecture | check |
| Config values read dynamically when the task requires config input | — | verifier architecture | check |
| Snorkel CLI credential flow | — | agent-run commands | check |
| One-model platform-Hard early exit | scoring mapping | validation | check |
| Net-new category availability | candidate filter | category gate | check |
| Internet-enabled source pinning | viability | Docker/verifier review | check |
| Clear goal vs inferred domain model | evidence graph | prompt/evidence gate | V3 schema check |
| Held-out generalization vs hidden arbitrary policy | candidate shape | verifier design | review |
| Cloud-compatible COPY syntax | — | Docker Rules | blocking check |
| CAD geometry and parametric recompute | candidate feasibility | verifier design | CAD review |

### Terminus 3 epistemic consistency check

Do not resolve generic phrases such as "fully specified" or "all tested
behavior" by forcing every semantic invariant into `instruction.md`. Reconcile
them with the Terminus 3-specific guidance:

- the goal, artifact/interface, and arbitrary exact conventions must be clear;
- the domain model may be inferred from agent-visible evidence, system state,
  realistic specs, or conventions;
- hidden instances/combinations are valid when they exercise that same model;
- unobtainable facts and oracle-only policies are invalid.

Flag any skill that requires one visible sentence/source per test, forbids all
hidden feature values, or requires fairness reviewers to reproduce the exact
oracle. Those are legacy contract-transcription rules, not the Terminus 3
fairness model.

For each cell, verify the skill's text matches the current docs. Report discrepancies.

## Step 5 — Auto-fix Skills

For each discrepancy found in Step 4:

1. Read the relevant section of the skill file
2. Draft the fix based on the updated doc content
3. Apply the edit
4. Verify the fix doesn't break other sections

**Rules for auto-fix:**
- Only fix factual discrepancies (rules, thresholds, lists)
- Do NOT rewrite skill structure or add new sections without user approval
- Preserve empirical notes and Go-specific guidance
- Flag ambiguous changes for manual review

## Step 6 — Report

Print a summary:

```
=== Sync Doc & Skill Report ===

Docs synced: 2026-06-03
Bundle hash: index-C9l2BqvB.js
Online pages: 42
Local pages: 42

=== Doc Changes ===
| Doc File | Change | Status |
|----------|--------|--------|
| writing-tests.md | test_deps rule updated | ✅ synced |
| task-requirements.md | no change | ✅ current |
| ... | ... | ... |

=== Skill Fixes ===
| Skill | Finding | Fix | Status |
|-------|---------|-----|--------|
| task-clone | test.sh template had rc=$? | canonical form | ✅ fixed |
| task-miner | Terminus 3 taxonomy missing | added exact category/subcategory screen | ✅ fixed |
| ... | ... | ... | ... |

New online pages not in local: 0
Docs with changes: 1
Skill fixes applied: 3
Manual review needed: 0
```

## Appendix: Change Detection (do NOT rely on bundle hash)

⚠️ The bundle filename hash is NOT a reliable change-detector. Doc `.md` files are
served and updated independently of the SPA shell bundle, so docs can change while
the bundle name stays the same (confirmed 2026-06-14: bundle `index-Bbhn77A_.js`
unchanged while `difficulty-guidelines.md` changed model names). The GitHub
Pages CDN can also serve curl a stale bundle while
serving fresh `.md`.

**Reliable detection = diff the directly-fetched `.md` files** (Step 1b + Step 2).
The `docs/.last-sync-bundle` marker is kept only as a coarse hint; never conclude
"docs unchanged" from an unchanged bundle name — always fetch and diff the `.md`.

## Appendix: Key Terms to Monitor

These terms in the online bundle indicate rule changes that affect skills:

```
test_deps_in_image
sanctioned
tests/Dockerfile
environment_mode
artifacts
network_mode
tmux
asciinema
canary
rubric
is_multi_container
difficulty
frontier
advanced
core
base
reward.txt
set -uo pipefail
CLAUDE.md
cursorrules
check_modal_dockerfile_compat
COPY --chown
COPY --from
CAD Task Guidelines
recompute
```

If any of these appear in a different context than expected, flag for investigation.
