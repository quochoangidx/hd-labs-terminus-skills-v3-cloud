# tbrain-gnu-ed-reimplementation — revision v3

**Returned snapshot** `68890de1633b39b51de23e82147974c5e43de42adf79d8473bcb7e9b1462229b`
(byte-identical to the rev2 archive this project shipped)
**Return** pre-difficulty gate again: 52 blocking findings, down from 64. A new axis appeared,
`coherent_contract`, and it was right.

## The headline: the errata I added in v2 became a new source of findings

Shipping `/app/docs/ed-errata.txt` stopped the panel reading the reference against the manual.
It started reading the reference against the errata instead — and three entries were wrong, so
eleven findings followed from my own text. The corrected entries:

| Entry | What v2 claimed | What ed 1.19 does |
|---|---|---|
| unset mark | resolves to address 0 | resolves to 0 only while the buffer is empty; otherwise it fails |
| a marked line that changes | the mark survives | the change clears the mark, and undo restores it |
| backslash-only first global-list line | an empty list, one print per line | a continuation; the empty segment prints, so each line prints twice and a following command joins the list |

Every entry is now derived from execution, and `evidence/errata-map.json` names a graded case
for each of the twenty-one, so an entry cannot drift from what the program does.

## What the evidence showed

| Platform claim | Raw evidence | Root-cause class | Decision |
|---|---|---|---|
| 3 contract findings: ASCII-only domain versus NUL fixtures | the instruction said ASCII text; `bin_01` and `bin_empty_01` hold NUL | contract defect I introduced in v2 | backed: the stated domain now admits NUL bytes |
| 11 reference findings tracing to wrong errata entries | GNU ed matches the reference on every script; the errata did not | documentation defect | backed: entries rewritten and pinned |
| 7 reference findings about undocumented behaviour | GNU ed matches the reference | not a defect, but undocumented | backed: errata entries added |
| 3 reference findings (6, 19, 24) | GNU ed matches the reference, and so does the manual | not a defect | disputed, with the script added as a case |
| 27, 38: the package audit and a shebang | `#!/` was in the executable-format list | my own check, too broad | backed: rule removed, witness added |
| 26 coverage findings | the returned corpus had no case for any of them | missing behavioural coverage | backed: 25 cases added |

## Validation through stb, as asked

`stb harbor` could not run this task here, and neither failure is about the task:

- `stb harbor run -a oracle` refuses the task outright: *network_mode='no-network' is not
  supported by EnvironmentType.DOCKER environment*. Weakening the declared policy to satisfy
  the local runner would change what the platform measures, so the documented fallback applies.
- `stb harbor check` fails in the checking agent: *400 bedrock error: Access to Anthropic models
  is not allowed from unsupported countries*. Retried with `-m @openai/gpt-5.6`, it fails with
  *Function tools with reasoning_effort are not supported for gpt-5.6 in /v1/chat/completions*,
  and the command refuses any agent other than `claude-code`.

Recorded in `receipts/stb-harbor-attempts.json`. Validation therefore ran through
`scripts/preflight.sh --strict --determinism`, which builds both images and enforces the
no-network phases with `docker --network none` plus a noexec `/tmp`.

## Results

| Run | Result |
|---|---|
| Differential over the whole corpus | 1770 cases, 0 differ from GNU ed 1.19 |
| Oracle / NOP / noexec, determinism | reward 1 / 0 / 1, pass |
| Wrong paths | 12 of 12 rejected on their own witness |
| Panel precheck, ledger, maps, zip review | pass, 52 answered, 21 errata + 45 findings mapped, ready |

## Final state

| Item | Value |
|---|---|
| Repaired snapshot | `59a910038fda...` |
| Upload archive | `tbrain-gnu-ed-reimplementation-rev3.zip`, sha256 `8908026e1f518786d439...`, 46 entries |
| Returned archive | untouched, sha256 `308fb5688bea58b61cf34efef885580c1e1a68b66d46857994867224c5590325` |
| Corpus | 1719 → 1770 cases, 25 platform-visible tests |

The three disputed findings need `contest-note.md` posted in `#terminus-3-submissions`.
