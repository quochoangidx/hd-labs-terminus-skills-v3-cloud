"""rev1: targeted cases for the platform quality-panel findings (one per rule, manual-pinned)."""
import json
N = []
def c(family, script, inp, opts=(), files=None, finding="", **kw):
    d = {"family": family, "opts": list(opts), "script": script, "input": inp}
    if files is not None: d["files"] = files
    d.update(kw); d["finding"] = finding; N.append(d)
AIC = "append_insert_change"
c(AIC, "i TEXT", "x\n", finding="1,36,53,70"); c(AIC, "c TEXT", "x\n", finding="1,36,54,68")
c(AIC, "2i  NEW", "a\nb\n", finding="53"); c(AIC, "2c  NEW", "a\nb\n", finding="54")
c(AIC, "1a hello;2d", "a\nb\n", finding="34"); c(AIC, "a hi;d", "x\n", finding="49")
c(AIC, "a X\nN;d", "a\nb\n", finding="50"); c(AIC, "a\\\nA\\\nB", "x\n", finding="51")
c(AIC, "a\\\n\\\\", "x\n", finding="52"); c(AIC, "i\\\n\\\\", "x\n", finding="52")
c(AIC, "a \\\\", "x\n", finding="72"); c(AIC, "i \\\\", "x\n", finding="74")
c(AIC, "1c\\", "x\n", extra=["-e", "CHANGED"], finding="55"); c(AIC, "1,2i X", "a\nb\n", finding="73")
SUB = "substitution_and_regex_escapes"
c(SUB, "s/a/X/i", "A\n", finding="2,46"); c(SUB, "s#/#X#", "/\n", finding="42")
c(SUB, "s/a/x\\\ny/", "a\n", finding="45"); c(SUB, "s/a?b/X/", "a?b\n", finding="63")
c(SUB, "s/a\\+b/X/", "a+b\n", ["-E"], finding="63"); c(SUB, "s/a^b/X/", "a^b\n", finding="65")
c(SUB, "s/a$b/X/", "a$b\n", finding="65"); c(SUB, "s/\\(*\\)/X/", "*\n", finding="75")
ML = "multiline_commands"
c(ML, "N;s/^b/X/m", "a\nb\n", finding="2"); c(ML, "N;s/./X/Mg", "a\nb\n", finding="47,48")
c(ML, "N;s/./X/mg", "a\nb\n", finding="47"); c(ML, "N;/^b/Mp", "a\nb\n", ["-n"], finding="61")
BR = "bracket_expressions"
c(BR, "s/[[=a=]]/X/g", "a b\n", finding="3"); c(BR, "s/[a-c]/X/", "c\n", finding="66")
c(BR, "s/[-a]/X/g", "-a.b\n", finding="20")
CC = "case_conversion"
c(CC, "s/\\(b\\?\\)-/\\u\\1x/g", "a-b-\n", finding="4"); c(CC, "s/\\(b\\?\\)-/x\\u\\1/g", "a-b-\n", finding="44")
c(CC, "s/a/\\LAb\\UCd/", "a\n", finding="43")
SF = "several_files"
c(SF, "$p", "", ["-s", "-n"], [["e", ""], ["f", "a\n"]], finding="29")
c(SF, "p", "a\n", [], [["-", None]], finding="32")
L = "l_command"
c(L, "l", "a" * 80 + "\n", ["-n"], finding="33,37,56"); c(L, "l", "a" * 71 + "\n", ["-n"], finding="37,56")
c(L, "l", "a" * 69 + "\n", ["-n"], finding="37")
CM = "comments_and_first_line"
c(CM, "  s/o/O/", "one\n", finding="35"); c(CM, "# ignored ; 2d", "a\nb\n", finding="71")
BT = "branching_and_t_flag"
c(BT, "s/a/A/;t done;:done;t skip;s/$/X/;:skip", "a\n", finding="38")
c(BT, "s/a/A/;t;s/$/X/", "a\n", finding="39"); c(BT, "T;s/$/X/", "a\n", finding="39")
c(BT, "b target ;s/x/wrong/;:target;s/x/ok/", "x\n", finding="57")
c(BT, "1{N;s/a/A/;D};t ok;b;:ok;p", "a\nb\n", ["-n"], finding="9,11")
c(BT, "1{N;s/a/A/;D};T bad;p;:bad", "a\nb\n", ["-n"], finding="11")
BK = "back_references"
c(BK, "s/\\(a\\)\\(b\\)\\(c\\)/\\3/", "abc\n", finding="40")
c(BK, "s/\\(a\\)\\(b\\)\\(c\\)\\(d\\)\\(e\\)\\(f\\)\\(g\\)\\(h\\)\\(i\\)/\\9\\8\\1/", "abcdefghi\n", finding="41")
c(BK, "s/\\(a\\)\\1/X/I", "aA\n", finding="14,21,23,28"); c(BK, "s/(a)\\1/X/i", "aA\n", ["-E"], finding="24")
c(BK, "/\\(a\\)\\1/Ip", "aA\nab\n", ["-n"], finding="16")
SA = "step_and_regex_addresses"
c(SA, "3~2p", "1\n2\n3\n4\n5\n", ["-n"], finding="58"); c(SA, "/a|b/p", "b\nc\n", ["-E", "-n"], finding="59")
c(SA, "/a\\/b/p", "a/b\nab\n", ["-n"], finding="60"); c(SA, "\\%a\\%b%p", "a%b\nab\n", ["-n"], finding="60")
c(SA, "/b/id", "b\n", ["-n"], finding="62")
c("options_and_script_argument", "s/a/b/", "a\n", script_arg=True, finding="67")
c("hold_space", "h;s/x/y/;g", "x\n", finding="69")
YZ = "y_z_and_line_numbers"
c(YZ, "13p", "".join(f"{i}\n" for i in range(1, 30)), ["-n"], finding="77")
c(YZ, "y/a/\\\n/", "a\n", finding="78"); c(YZ, "y/\\t/_/", "a\tb\n", finding="12")
c("leftmost_longest", "s/(a|aa)*b/X/", "a" * 45 + "\n", ["-E"], finding="5")
json.dump(N, open("new_cases.json", "w"), indent=0)
print(len(N))
