# Writes workspace/reports/<slug>/revision-ledger.json for the v7 return (panel PASS, difficulty run invalid).
import json
R = "workspace/reports/tbrain-gnu-sed-reimplementation"
L = "ledger-receipts-v7/"
ledger = {
    "schema_version": 1, "task_slug": "tbrain-gnu-sed-reimplementation",
    "report_path": "workspace/revision/12e6eda4-8ced-4dcd-928d-7abc22b133a9/v7/12e6eda4-8ced-4dcd-928d-7abc22b133a9.md",
    "returned_snapshot_sha256": "dda81d57b60d3b77ea3cc6c08676cf47fa8571bdfe71f3596af0bcbb5a3452e8",
    "repaired_snapshot_sha256": open(f"{R}/rev6/repaired-snapshot.txt").read().strip(),
    "note": "v7 judged rev5: QUALITY PANEL PASS and every blocking quality gate passed. The difficulty run was invalid, not failed: 8/8 agent trials (Opus 5, GPT-5.6) died with NonZeroAgentExitCodeError while oracle (3/3) and NOP passed. That is not a panel finding; it is recorded as one row so its receipts bind to both snapshots.",
    "findings": [{
        "id": "v7-difficulty-invalid-NonZeroAgentExitCodeError", "axis": "deterministic_execution", "severity": "Major", "blocking": True,
        "decision": "backed",
        "rationale": "The agent image ran `rm -f /bin/sed /usr/bin/sed` for the 'images ship without sed' premise, but the platform harness shells out to sed inside the task container (Terminus's get-asciinema-timestamp.sh: grep | tail | sed -E; Harbor's node bootstrap: node --version | sed). The platform's own hint (make [environment] public) did not apply: it already was. tbrain-press-shop-scheduling, on the same digest-pinned base and the same network settings, got 8/8 genuine runs. rev6 keeps GNU sed 4.9 in the agent image (user decision, 2026-09-26) and says so in the instruction; the program is still barred from calling it (audit hook), and the verifier still makes /bin/sed root-only in its own container. Nothing graded changed: tests/ and solution/ are byte-identical to rev5.",
        "reproduction": L + "repro-harness-returned.json",
        "closure": L + "closure-harness-repaired.json",
        "gate": {"rule": "scripts/task-policy.py agent-dockerfile:harness-binaries-kept (fails when an agent Dockerfile removes sed, grep, tail, awk, cut, tr or bash), with scripts/tests/test_task_policy.py::test_agent_image_must_keep_harness_binaries; corpus sweep: only the sed task's own history and tbrain-gnu-grep-reimplementation (removes grep) fail"},
    }],
    "previous_findings": [{"id": "v6-1..14", "status": "closed", "response": "v7 quality panel PASS with no blocking issues on rev5, which answered them"}],
}
json.dump(ledger, open(f"{R}/revision-ledger.json", "w"), indent=1)
