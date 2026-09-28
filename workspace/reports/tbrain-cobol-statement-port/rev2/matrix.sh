#!/bin/bash
# Grade every mutant on the returned and on the repaired verifier.
set -u
cd "$(dirname "$0")"
RUN=../rev1/run_verifier.sh
REPAIRED=/Users/quochoangdev/HDTechLS/hd-labs-terminus-skills-v3/workspace/revision/8eaa9cda-42c4-4d68-80a5-6bd99aa99c15/v2/tbrain-cobol-statement-port
for m in reference m1_python_worker m2_payin_100_cap m3_restore_site_packages; do
  echo "returned $m: $(bash $RUN returned rev2-returned mut/$m.py repro/$m)"
done
for m in reference m1_python_worker m2_payin_100_cap m3_restore_site_packages m4_shell_delegation m5_loader_delegation; do
  echo "repaired $m: $(bash $RUN $REPAIRED rev2-repaired mut/$m.py closure/$m)"
done
