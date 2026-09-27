#!/bin/bash
# Reproductions on the returned snapshot, then closures on the repaired one, one at a time.
cd /Users/quochoangdev/HDTechLS/hd-labs-terminus-skills-v3
R=workspace/reports/tbrain-gnu-ed-reimplementation
WP=.agent/skills/terminus-regular-task-authoring/scripts/wrong_path_runner.py
RET=workspace/revision/fc57838e-86e3-431c-a65c-b8776a1f307e/v6/tbrain-gnu-ed-reimplementation
REP=workspace/tasks/tbrain-gnu-ed-reimplementation
mkdir -p $R/revision-v6/work/ctrf $R/revision-v6/receipts/returned
one() { # snapshot-dir id witness receipt
  export CTRF_OUT="$PWD/$R/revision-v6/work/ctrf/$(basename $4 .json).ctrf.json"; rm -f "$CTRF_OUT"
  python3 $WP $1 --id $2 --patch $R/wrong-paths/$2.patch --expect-failing "test_outputs.py::$3" \
    --verifier "$PWD/workspace/tools/score.sh" --ctrf "$CTRF_OUT" --receipt $4 > $R/revision-v6/work/$(basename $4 .json).log 2>&1
  python3 -c "import json; r=json.load(open('$4')); print('$2', r['status'], 'reward', r['reward'], 'failed', len(r['failed_test_ids']))" 2>/dev/null || { echo "$2 ERROR"; tail -3 $R/revision-v6/work/$(basename $4 .json).log; }
}
if [ "${1:-all}" != "repaired" ]; then
for pair in addressed-undo-accepted:test_addresses zero-lower-bound-rejected:test_regex append-suffix-ignored:test_append_insert_change \
  tab-separator-rejected:test_files_and_write join-keeps-mark:test_addresses open-s-prints-first-line:test_substitute \
  repeat-form-accepts-n:test_substitute E-count-ignores-s:test_files_and_write fork-exec-helper-delegation:test_regex_extended; do
  id=${pair%%:*}; w=${pair##*:}
  one $RET $id $w $R/revision-v6/receipts/returned/$id.json
done
fi
if [ "${1:-all}" != "returned" ]; then
for pair in addressed-undo-accepted:test_addresses zero-lower-bound-rejected:test_regex append-suffix-ignored:test_append_insert_change \
  tab-separator-rejected:test_files_and_write join-keeps-mark:test_addresses open-s-prints-first-line:test_substitute \
  repeat-form-accepts-n:test_substitute E-count-ignores-s:test_files_and_write leading-hyphen-starts-range:test_regex \
  global-s-without-match-fails:test_global_commands fork-exec-helper-delegation:test_regex_extended \
  delegate-to-system-ed:test_regex_extended empty-append-keeps-undo:test_append_insert_change eof-quits-quietly:test_errors_and_exit \
  global-keeps-touched-lines:test_global_commands leftmost-first-regex:test_substitute loose-exit-ignored:test_errors_and_exit \
  pipe-stops-on-error:test_errors_and_exit ranged-s-current-last-addressed:test_substitute reversed-range-rejected-for-a:test_append_insert_change \
  semicolon-keeps-current:test_addresses short-initial-load:test_files_and_write \
  undo-not-undoable:test_undo unescaped-brace-rejected:test_regex w-for-W:test_files_and_write; do
  id=${pair%%:*}; w=${pair##*:}
  one $REP $id $w $R/wrong-paths/$id.json
done
fi
echo DONE
