#!/bin/bash
# Run every rev6 wrong path through the separate verifier (score.sh), four at a time, and write receipts.
ROOT=/Users/quochoangdev/HDTechLS/hd-labs-terminus-skills-v3
R=$ROOT/workspace/reports/tbrain-gnu-sed-reimplementation
T=$ROOT/workspace/tasks/tbrain-gnu-sed-reimplementation
S=$ROOT/.agent/skills/terminus-regular-task-authoring/scripts
export ROOT R T S
find "$T" -name .DS_Store -delete
cd "$ROOT"
cat > "$R/rev6/wp-list.txt" <<'LIST'
tilde-ends-at-multiple test_multiple_ranges
hash-n-needs-newline test_comments_and_first_line
leftmost-first-regex test_leftmost_longest_matching
t-flag-survives-reads test_branching_and_t_flag
separate-ranges-span-files test_several_files
bracket-backslash-n-literal test_bracket_expressions
delegate-to-system-sed test_multiple_ranges
ic-one-line-text-dropped test_append_insert_change
d-restart-clears-t-flag test_branching_and_t_flag
exponential-backtracking-regex test_leftmost_longest_matching
aic-text-escapes-left-literal test_append_insert_change
xdigit-class-missing test_bracket_expressions
tab-not-whitespace-before-command test_comments_and_first_line
replacement-escaped-delimiter-kept test_substitution_and_regex_escapes
ere-escaped-question-is-quantifier test_substitution_and_regex_escapes
correct-but-six-seconds-on-pathological-regex test_leftmost_longest_matching
ctypes-into-libc test_editing_is_done_in_python
files-opened-before-the-run test_matrix_quit
q-exit-code-one-digit test_matrix_quit
control-escape-r-left-literal test_matrix_escapes
s-number-after-g-ignored test_matrix_s_flags
block-range-first-line-only test_matrix_blocks
bracket-range-end-newline-literal test_matrix_brackets
imports-verifier-package test_matrix_intervals
LIST
# build the scoring image once so parallel runs do not race on it
bash "$ROOT/workspace/tools/score.sh" "$T" "$R/rev6/wp-mut/tilde-ends-at-multiple/app" >/dev/null 2>&1
one() {
  id=$1; witness=$2
  cp "$R/rev6/wp-mut/$id.patch" "$R/wrong-paths/$id.patch"
  CTRF_OUT="$R/rev6/wp-$id.ctrf.json" python3 "$S/wrong_path_runner.py" "$T" --id "$id" --patch "$R/wrong-paths/$id.patch" \
    --expect-failing "test_outputs.py::$witness" --verifier "$ROOT/workspace/tools/score.sh" \
    --ctrf "$R/rev6/wp-$id.ctrf.json" --receipt "$R/wrong-paths/$id.json" > "$R/rev6/wp-$id.log" 2>&1
  echo "$id exit=$? $(tail -1 "$R/rev6/wp-$id.log")"
}
export -f one
xargs -P 4 -L 1 bash -c 'one "$0" "$1"' < "$R/rev6/wp-list.txt"
echo ALL-DONE
