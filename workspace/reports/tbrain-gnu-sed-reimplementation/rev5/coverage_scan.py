# Counts roster cases that exercise each coverage class the v6 panel named.
# usage: coverage_scan.py <task-dir>
import json, os, re, sys
T = sys.argv[1]
cases = []
for n in sorted(os.listdir(os.path.join(T, "tests", "cases"))):
    if n.endswith(".json") and n != "inputs.json":
        for fam, rows in json.load(open(os.path.join(T, "tests", "cases", n))).items():
            cases.extend(rows)
checks = {
    "command_after_q_or_Q": lambda c: re.search(r"(^|[;{\n])\s*\d*\$?[qQ]\s*\d*\s*;\s*[^}\s]", c["script"]),
    "taken_t_or_T_label_with_trailing_space": lambda c: re.search(r"[tT] \w+ +;", c["script"]) and re.search(r"s/", c["script"]),
    "tilde_regex_delimiter": lambda c: re.search(r"\\~|s~", c["script"]),
    "bracket_range_ending_in_escape": lambda c: re.search(r"\[[^]]*-\\[afnrtv]", c["script"]),
    "hold_space_across_files": lambda c: len(c.get("files", [])) > 1 and re.search(r"[hH]", c["script"]) and re.search(r"[gGx]", c["script"]),
    "a_then_Q": lambda c: re.search(r"(^|\n)[^\n]*a [^\n]*\n[^\n]*Q", c["script"]),
    "missing_file_before_q_code": lambda c: re.search(r"[qQ] ?\d", c["script"]) and any(t is None and n != "-" for n, t in c.get("files", [])),
}
print(json.dumps({"cases": len(cases), "exercising": {k: sum(1 for c in cases if f(c)) for k, f in checks.items()}}, indent=1))
