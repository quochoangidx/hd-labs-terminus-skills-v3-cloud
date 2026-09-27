# Documented exception: independence_check.py `model_in_tests` (2026-09-26 rule)

The rule targets verifiers that work out every expected answer at grading time (an end-to-end
model under tests/). This verifier has no expectation model. Its expected values are the sealed
targets in tests/targets.json (authority_text: the same numbers the agent sees). tests/check_*.py
is the published rule checker, byte-identical to the agent's environment/app/tools copy; it scores
the submitted file under the stated rules and derives no answer. Moving it to solution/ would leave
the verifier unable to grade. The search that produced the reference ships as solution/search.py
(the new solution_quality guidance), and it is not run at grading time.
Contract citation: execution-profiles.md builder_certified, "record a documented_exception ... never
quietly edit the task to satisfy a rule you think is mistaken".
