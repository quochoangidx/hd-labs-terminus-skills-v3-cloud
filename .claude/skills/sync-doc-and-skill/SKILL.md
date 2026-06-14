---
name: sync-doc-and-skill
description: Sync Terminus docs from the Snorkel portal and update dependent Terminus skills to match. Run periodically or when you suspect docs have changed. Fetches the live JS bundle from the portal SPA, extracts doc content, diffs against local docs/, patches local files, then audits Terminus skills for discrepancies and auto-fixes them.
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
    ├── JS bundle contains all doc content as embedded strings
    │
    ▼
Step 1: Fetch & Extract docs from JS bundle
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

## Step 1 — Fetch Docs from Portal

The Snorkel portal at `https://snorkel-ai.github.io/Terminus-EC-Training-stateful/` is a single-page app (SPA). All doc content is embedded in the JS bundle. WebFetch/curl only gets the HTML shell — content must be extracted from the JS.

### 1a. Download the JS bundle

```bash
# Get the main page to find the bundle filename (it has a hash)
PORTAL_URL="https://snorkel-ai.github.io/Terminus-EC-Training-stateful/"
BUNDLE_PATH=$(curl -sL "$PORTAL_URL" | grep -oE 'src="/Terminus-EC-Training-stateful/assets/index-[^"]+\.js"' | sed 's/src="//;s/"//')
BUNDLE_URL="https://snorkel-ai.github.io${BUNDLE_PATH}"

curl -sL "$BUNDLE_URL" > /tmp/terminus_bundle.js
echo "Bundle size: $(wc -c < /tmp/terminus_bundle.js) bytes"
```

### 1b. Extract navigation structure

```bash
# Extract all doc page slugs and titles
grep -oE 'slug:"[^"]+",title:"[^"]+"' /tmp/terminus_bundle.js | \
  sed 's/slug:"//;s/",title:"/ → /;s/"//' | sort
```

Compare with existing local docs:
```bash
find docs/ -name "*.md" | sed 's|docs/||; s|\.md$||' | sort
```

Flag any pages in online that are missing locally, or local pages not in online.

### 1c. Extract doc content

The bundle contains doc content as JSX strings. Extract key sections:

```bash
# Extract checklist items
grep -oE '"checklist-item",children:"[^"]*"' /tmp/terminus_bundle.js

# Extract table cell content
grep -oE 'children:"[^"]{20,200}"' /tmp/terminus_bundle.js | head -50

# Extract specific doc sections by searching for key terms
grep -oP '.{0,200}(test_deps_in_image|verifier depend|tests/wheels).{0,200}' /tmp/terminus_bundle.js
grep -oP '.{0,200}sanctioned.{0,200}' /tmp/terminus_bundle.js
grep -oP '.{0,200}allow_internet.{0,200}' /tmp/terminus_bundle.js
grep -oP '.{0,200}codebase_size.{0,200}' /tmp/terminus_bundle.js
grep -oP '.{0,200}tmux.{0,200}' /tmp/terminus_bundle.js
grep -oP '.{0,200}rubric.{0,200}' /tmp/terminus_bundle.js
grep -oP '.{0,200}canary.{0,200}' /tmp/terminus_bundle.js
```

### 1d. Known extraction patterns

Since the SPA embeds content as JSX, use these patterns to extract structured data:

| What | Pattern |
|------|---------|
| Navigation | `slug:"...",title:"..."` |
| Checklist items | `"checklist-item",children:"..."` |
| Table cells | `l.jsx("td",{children:"..."})` |
| CI check names | `l.jsx("code",{children:"..."})` |
| Info boxes | `"info-box",children:[...]` |
| Section headers | `l.jsx("h2",{children:"..."})` |

## Step 2 — Diff Against Local Docs

For each key rule area, compare online content with local docs:

### Critical rules to check (these cause CI failures and rejections):

| Rule Area | Local Doc File | Online Search Term |
|-----------|---------------|-------------------|
| Verifier dependency placement | `creating-tasks/writing-tests.md` | `test_deps_in_image`, `verifier dependencies`, `tests/wheels` |
| Sanctioned bases | `creating-tasks/dockerfile-best-practices.md` | `sanctioned` |
| test.sh canonical form | `creating-tasks/writing-tests.md` | `reward.txt` |
| codebase_size bands | `understanding-tasks/task-requirements.md` | `codebase_size` |
| Difficulty thresholds | `understanding-tasks/difficulty-guidelines.md` | `accuracy` |
| Diversity gates | `understanding-tasks/diversity-requirements.md` | `blocked` |
| Instruction styling | `understanding-tasks/prompt-styling.md` | `canary` |
| Rubric format | `understanding-tasks/rubrics.md` | `rubric` |
| tmux/asciinema | `creating-tasks/dockerfile-best-practices.md` | `tmux` |
| allow_internet | `understanding-tasks/task-requirements.md` | `allow_internet` |
| Docker-compose flags | `reviewing-tasks/reviewer-checklist.md` | `docker_compose` |

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
4. **New page in online nav** → create new local doc file with placeholder, flag for content extraction

**Always preserve local additions** (e.g., empirical notes, Go-specific guidance) that don't contradict online docs.

## Step 4 — Audit Skills Against Updated Docs

After docs are synced, audit these skills:

```
.claude/skills/task-miner/SKILL.md
.claude/skills/task-clone/SKILL.md
.claude/skills/task-zip-validator/SKILL.md
.claude/skills/task-client-feedback-review/SKILL.md
```

### Audit checklist (check each rule in each skill):

| Rule | task-miner | task-clone | task-zip-validator |
|------|-----------|------------|-------------------|
| test.sh canonical form | — | template | check |
| verifier dependency placement | — | guidance | check |
| Sanctioned base images | — | Docker Rules | check |
| tmux/asciinema required | runtime risk | Docker Rules | check |
| allow_internet = false | — | metadata defaults | check |
| codebase_size bands | — | metadata defaults | check |
| Difficulty thresholds | scoring mapping | validation | check |
| Python must be hard | hardness filter | metadata | check |
| Rubric requirements | — | rubric section | reminder |
| docker-compose flags | — | Docker Rules | check |
| Canary string | — | instruction style | check |
| AI scaffolding files | — | cleanup | check |
| Env spec anti-bypass | — | — | check |
| Instruction styling | prompt template | instruction style | check |
| Build context size | — | quality preflight | check |

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
| task-miner | Python hard rule missing | added to hardness filter | ✅ fixed |
| ... | ... | ... | ... |

New online pages not in local: 0
Docs with changes: 1
Skill fixes applied: 3
Manual review needed: 0
```

## Appendix: Bundle Hash Tracking

Store the last-synced bundle filename to detect changes:

```bash
# Save current bundle hash
echo "index-C9l2BqvB.js" > docs/.last-sync-bundle
```

On next run, compare:
```bash
LAST=$(cat docs/.last-sync-bundle 2>/dev/null)
CURRENT=$(curl -sL "$PORTAL_URL" | grep -oE 'index-[^"]+\.js')
if [ "$LAST" = "$CURRENT" ]; then
    echo "No bundle change — docs likely unchanged. Use --force to sync anyway."
fi
```

## Appendix: Key Terms to Monitor

These terms in the online bundle indicate rule changes that affect skills:

```
test_deps_in_image
sanctioned
allow_internet
codebase_size
minimal
tmux
asciinema
canary
rubric
custom_docker_compose
is_multi_container
difficulty
hard
medium
easy
blocked
reward.txt
set -uo pipefail
CLAUDE.md
cursorrules
```

If any of these appear in a different context than expected, flag for investigation.
