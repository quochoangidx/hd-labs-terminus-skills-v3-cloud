# Counts roster cases that exercise each coverage class the v4/v5 panels named.
# usage: coverage_scan.py <task-dir>   (parses scripts with that task's reference parser)
import json, os, re, sys
T = sys.argv[1]
sys.path.insert(0, os.path.join(T, "solution", "pysed"))
import sed as S
inputs = json.load(open(os.path.join(T, "tests", "cases", "inputs.json")))
cases = []
for n in sorted(os.listdir(os.path.join(T, "tests", "cases"))):
    if n.endswith(".json") and n != "inputs.json":
        for fam, rows in json.load(open(os.path.join(T, "tests", "cases", n))).items():
            cases.extend(rows)
def cmds(c):
    try:
        return S.ScriptParser(c["script"], "-E" in c["opts"]).parse()[0]
    except Exception:
        return []
def s_flags(c):
    return [x for x in re.findall(r"s(.)(?:\\.|(?!\1).)*\1(?:\\.|(?!\1).)*\1([gp0-9]*)", c["script"])]
EXCL = re.compile(r"y/|(^|[;{}\s,0-9$~+])l(\s|;|$)|/[IM]([,;{\s]|$)")
checks = {
    "ctrl_escape_in_replacement_or_regex": lambda c: re.search(r"\\[afrv]", c["script"]) and not any(x.name in "aic" for x in cmds(c)),
    "ctrl_escape_in_aic_text": lambda c: any(x.name in "aic" and re.search("[\a\f\r\v]", x.arg or "") for x in cmds(c)),
    "aic_text_reading_like_y_l_I": lambda c: any(x.name in "aic" and EXCL.search(x.arg or "") for x in cmds(c)),
    "range_on_block": lambda c: any(x.name == "{" and x.a2 is not None for x in cmds(c)),
    "s_number_g_and_p": lambda c: any(re.search(r"\d", f) and "g" in f and "p" in f for _, f in s_flags(c)),
    "s_g_before_number": lambda c: any(re.search(r"g\d", f) for _, f in s_flags(c)),
    "q_Q_multi_digit_code": lambda c: re.search(r"[qQ] ?\d\d", c["script"]),
    "T_after_n_or_N": lambda c: re.search(r"[nN];.*T", c["script"]),
    "group_4_to_8_in_replacement": lambda c: re.search(r"\\[4-8]", c["script"]),
    "group_4_to_7_in_replacement": lambda c: re.search(r"\\[4-7]", c["script"]),
    "bre_exact_interval": lambda c: "-E" not in c["opts"] and re.search(r"\\\{\d+\\\}", c["script"]),
    "regex_escape_in_address": lambda c: re.search(r"(^|[;{}\n,!])\s*/[^/]*\\[WSbB<>][^/]*/", c["script"]),
    "close_brace_then_semicolon": lambda c: "};" in c["script"],
    "digit_s_delimiter": lambda c: re.search(r"(^|[;{}\n])\s*s\d", c["script"]),
    "dollar_in_multiline_space": lambda c: "N" in c["script"] and re.search(r"\$[/|)]|\$\\\)", c["script"]),
    "zero_range_match_after_line1": lambda c: c["script"].startswith("0,/"),
    "dash_beside_a_file": lambda c: len(c.get("files", [])) + len(c.get("extra", [])) > 1 and any(n == "-" for n, _ in c.get("files", [])) or ("-" in c.get("extra", []) and c.get("files")),
    "missing_file_after_q": lambda c: re.search(r"[qQ]", c["script"]) and any(t is None and n != "-" for n, t in c.get("files", [])[1:]),
    "append_then_N_or_n_then_print": lambda c: re.search(r"(^|\n)\$?!?\d*a .*\n.*[nN].*[pP]", c["script"]),
    "input_over_32_lines": lambda c: (inputs.get(c["input"][1:], "") if str(c["input"]).startswith("@") else c["input"]).count("\n") > 32,
}
res = {k: sum(1 for c in cases if f(c)) for k, f in checks.items()}
print(json.dumps({"cases": len(cases), "exercising": res}, indent=1))
