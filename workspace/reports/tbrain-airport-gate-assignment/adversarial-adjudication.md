# Adversarial verifier pass (step 5b) - GPT-5.6 medium via stb codex exec; saw instruction, environment, tests; not solution/manifest/reports
15 wrong + 2 valid submissions (adversarial_report.md). Two findings, both upheld:
1. NaN in an ignored top-level field accepted (Python json accepts NaN): fixed. Checkers (tool + verifier copy) now load candidate files through load_plan(): UTF-8, standard JSON, parse_constant rejects NaN/Infinity.
2. Unstated 2,000,000-byte limit: narrowed the promise. The limit is now stated in the rules and enforced by the same loader in the tool and the verifier; valid-huge-whitespace (>2 MB) is a contract-invalid file under the revised rules.
Rerun receipt: adversarial-rerun.txt (every wrong submission fails its validity test; valid-unusual-order passes).
The same loader and stated limit were applied to the roster and ad-layout tasks.
