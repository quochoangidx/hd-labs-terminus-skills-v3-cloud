# Bad Example Tasks

Learn from these bad example tasks that demonstrate sub-optimal quality standards and various task types.



## Anti-Examples: Tasks to Avoid

### ❌ Too Easy

**File: `instruction.md`**

```markdown
Write a function that reverses a string.
```

**Problem:** One-liner in most languages, agents solve instantly.

### ❌ Too Vague

**File: `instruction.md`**

```markdown
Build a web scraper.
```

**Problem:** No specific requirements, impossible to verify.

### ❌ Requires Secrets or Unverifiable External State

**File: `instruction.md`**

```markdown
Query the Twitter API to get today's trending topics.
```

**Problem:** Two issues — it needs private API **credentials/secrets** (which can't be bundled or committed), and its output is **nondeterministic** (trending topics change constantly), so no stable verifier can grade it. Needing internet **by itself** is *not* a problem — a task that genuinely requires the network is acceptable with `allow_internet = true`. The real issues here are the secret credentials and the unverifiable, ever-changing result.

### ❌ Ambiguous Success Criteria

**File: `instruction.md`**

```markdown
Make this code better.
```

**Problem:** "Better" is subjective without specific metrics.

---

## Task Inspiration

Looking for ideas? Consider tasks involving:

- **Concurrency bugs** — Race conditions, deadlocks
- **Algorithm implementation** — With specific constraints
- **Code refactoring** — With measurable improvement goals
- **Security vulnerabilities** — Find and fix issues
- **Performance optimization** — With benchmarks

---

## Next Steps

- [Learn difficulty guidelines](/portal/docs/understanding-tasks/difficulty-guidelines)
- [Start creating your task](/portal/docs/creating-tasks/videos/creating-task)
