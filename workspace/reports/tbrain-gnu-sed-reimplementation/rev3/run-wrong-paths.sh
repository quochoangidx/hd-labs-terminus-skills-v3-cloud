#!/bin/bash
# Run every rev3 wrong path through the separate verifier (score.sh) and write receipts.
ROOT=/Users/quochoangdev/HDTechLS/hd-labs-terminus-skills-v3
R=$ROOT/workspace/reports/tbrain-gnu-sed-reimplementation
T=$ROOT/workspace/tasks/tbrain-gnu-sed-reimplementation
S=$ROOT/.agent/skills/terminus-regular-task-authoring/scripts
find "$T" -name .DS_Store -delete
cd "$ROOT"
python3 - <<'PY' > "$R/rev3/wp-list.txt"
import json
w = {"tilde-ends-at-multiple":"test_multiple_ranges","hash-n-needs-newline":"test_comments_and_first_line","leftmost-first-regex":"test_leftmost_longest_matching","t-flag-survives-reads":"test_branching_and_t_flag","separate-ranges-span-files":"test_several_files","bracket-backslash-n-literal":"test_bracket_expressions","delegate-to-system-sed":"test_multiple_ranges","ic-one-line-text-dropped":"test_append_insert_change","d-restart-clears-t-flag":"test_branching_and_t_flag","exponential-backtracking-regex":"test_leftmost_longest_matching","aic-text-escapes-left-literal":"test_append_insert_change","xdigit-class-missing":"test_bracket_expressions","tab-not-whitespace-before-command":"test_comments_and_first_line","replacement-escaped-delimiter-kept":"test_substitution_and_regex_escapes","ere-escaped-question-is-quantifier":"test_substitution_and_regex_escapes","correct-but-six-seconds-on-pathological-regex":"test_leftmost_longest_matching","ctypes-into-libc":"test_editing_is_done_in_python"}
for k, v in w.items(): print(k, v)
PY
while read -r id witness; do
  find "$T" -name .DS_Store -delete
  cp "$R/rev3/mut/$id.patch" "$R/wrong-paths/$id.patch"
  export CTRF_OUT="$R/rev3/wp-$id.ctrf.json"
  python3 "$S/wrong_path_runner.py" "$T" --id "$id" --patch "$R/wrong-paths/$id.patch" \
    --expect-failing "test_outputs.py::$witness" --verifier "$ROOT/workspace/tools/score.sh" \
    --ctrf "$CTRF_OUT" --receipt "$R/wrong-paths/$id.json" > "$R/rev3/wp-$id.log" 2>&1
  echo "$id exit=$? $(tail -1 "$R/rev3/wp-$id.log")"
done < "$R/rev3/wp-list.txt"
echo ALL-DONE
