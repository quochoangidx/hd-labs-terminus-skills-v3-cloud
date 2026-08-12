# Terminus 3 category and subcategory screen

Use this screen before building a skeleton. Terminus 3 classifies the domain in
which correctness lives, not the surface activity the agent performs. Writing
code does not automatically make a task `Software`.

## Exact taxonomy

- `Science`: `Biology`, `Chemistry`, `Physics`, `Earth`, `Robotics`, `Math`, `Linguistics`
- `Software`: `Algorithms`, `Systems`, `Databases`, `Data engineering`, `Frontend`, `Languages`
- `ML`: `Training`, `Inference`, `Evaluation`, `Kernels`
- `Operations`: `Finance`, `Logistics`, `Supply chain`, `Claims`, `Compliance`, `Marketing`
- `Security`: `Cryptography`, `Reverse engineering`, `Forensics`, `AppSec`
- `Hardware`: `CAD`, `RTL`
- `Media`: `Music`, `Design`

Values are case-sensitive. Every task has exactly one category and one
subcategory.

## Decision rule

Ask: **What body of domain knowledge determines whether the submitted artifact
is correct?** Choose that domain, then the narrowest matching subcategory.

1. Identify the real-world object being reasoned about: a training run, a
   transaction log, a molecular spectrum, a route plan, an RTL design, a media
   artifact, or software behavior itself.
2. Identify the evidence the verifier uses. If success depends on domain facts,
   constraints, or native artifact validity, that domain normally owns the
   category even when the deliverable is code.
3. Use `Software` only when software itself is the subject: algorithms,
   compilers, databases, distributed systems, frontend systems, or data
   engineering.
4. Reject narrative relabeling. Changing nouns in `instruction.md` without
   changing the evidence, artifact, and verifier does not change the domain.

Examples:

- Repairing checkpoint recovery in a training loop → `ML / Training`.
- Implementing a database WAL recovery path → `Software / Databases`.
- Inferring compounds from spectra and producing a validated report →
  `Science / Chemistry`.
- Restoring a supply planning workbook from operational constraints →
  `Operations / Supply chain`.
- Reconstructing an exploit chain or vulnerable request → `Security / AppSec`.
- Repairing a parser/compiler frontend → `Software / Languages`.
- Implementing a CPU-simulated accelerator kernel → `ML / Kernels`.
- Producing a valid synthesizable module and timing artifact → `Hardware / RTL`.

## Evidence artifact

Write `workspace/reports/<slug>/category-screen.json` before the skeleton probe:

```json
{
  "status": "pass",
  "task_slug": "tbrain-example",
  "declared_category": "ML",
  "declared_subcategory": "Training",
  "domain_rationale": "Correctness depends on checkpoint and optimizer-state semantics in a training run.",
  "evidence": [
    "instruction.md: the requested outcome is deterministic training resumption",
    "tests/test_outputs.py: verification compares model and optimizer state after resume"
  ]
}
```

The evidence must cite agent-visible requirements and verifier behavior. A
passing screen is invalid when the rationale merely repeats the label.

There is no locally runnable platform category classifier. Historical
Terminus 2 classifier results may explain old submissions, but they must not
block or relabel a Terminus 3 task.
