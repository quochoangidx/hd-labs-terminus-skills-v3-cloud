# Builds tests/cases/matrix.json: one family per contract clause, each clause enumerated
# systematically (every escape in every position, every s-flag order, every group number, ...).
import itertools, json, sys
out = {}
def add(fam, script, inp="", opts=None, files=None, extra=None):
    row = {"opts": list(opts or []), "script": script, "input": inp}
    if files is not None: row["files"] = files
    if extra is not None: row["extra"] = extra
    out.setdefault(fam, []).append(row)

ESC = {"a": "\a", "f": "\f", "n": "\n", "r": "\r", "t": "\t", "v": "\v"}
LINES40 = "".join(f"line {i:02d} {'ab'[i % 2]}\n" for i in range(1, 41))

# section 5.8 escapes: replacement, regex, bracket, address, a/i/c text in both forms
for e, ch in ESC.items():
    add("matrix_escapes", f"s/x/<\\{e}>/", "axb\nxx\n")
    add("matrix_escapes", f"s/x/\\{e}/g", "axbx\n")
    for ere in ([], ["-E"]):
        if e == "n":
            add("matrix_escapes", "N;s/\\n/X/", "a\nb\nc\n", ere)
            add("matrix_escapes", "N;s/[\\n]/X/", "a\nb\n", ere)
            add("matrix_escapes", "$!N;/a\\nb/d", "a\nb\nc\nd\n", ere)
        else:
            add("matrix_escapes", f"s/\\{e}/X/g", f"a{ch}b{ch}\nplain\n", ere)
            add("matrix_escapes", f"s/[\\{e}]/X/", f"a{ch}b\n{e}\\\n", ere)
            add("matrix_escapes", f"/\\{e}/d", f"a{ch}b\nplain\n", ere)
            add("matrix_escapes", f"s/[^\\{e}]/Y/g", f"a{ch}b\n", ere)
    for cmd in "aic":
        add("matrix_escapes", f"2{cmd}\\\nL\\{e}R", "x\ny\nz\n")
        add("matrix_escapes", f"2{cmd} L\\{e}R", "x\ny\nz\n")
        add("matrix_escapes", f"${cmd}\\\nA\\{e}\\\nB\\{e}C", "x\ny\n")

# regex escapes \w \W \s \S \b \B \< \> in s and in addresses, BRE and ERE
WORDS = "foo bar_1 x-y\n  \t\nfoobar\n-a-\nab cd\n"
for esc in ("\\w", "\\W", "\\s", "\\S", "\\b", "\\B", "\\<", "\\>"):
    for ere in ([], ["-E"]):
        add("matrix_regex_escapes", f"s/{esc}/X/g", WORDS, ere)
        add("matrix_regex_escapes", f"s/{esc}/X/2", WORDS, ere)
        add("matrix_regex_escapes", f"/{esc}a/d", WORDS, ere)
        add("matrix_regex_escapes", f"/foo{esc}/!d", WORDS, ere)
        add("matrix_regex_escapes", f"/{esc}/,/{esc}c/s/^/>/", WORDS, ere)
add("matrix_regex_escapes", "s/\\bfoo\\b/X/g", "foo foobar barfoo foo\n")
add("matrix_regex_escapes", "s/\\<b/X/g;s/r\\>/Y/g", "bar rab barb\n")
add("matrix_regex_escapes", "/^\\S\\+\\s\\S\\+$/p", "ab cd\nab  cd\nab\n", ["-n"])
add("matrix_regex_escapes", "/^\\w+\\W\\w+$/p", "ab-cd\nab--cd\nab_cd\n", ["-n", "-E"])

# s flags: every order of g, p and a number, with and without -n
INP = "aaa\nbab\nccc\naaaaa\n"
for k in (1, 2):
    for combo in itertools.permutations(["g", "p", "N"], k + 1):
        for num in ("2", "3"):
            flags = "".join(num if f == "N" else f for f in combo)
            for q in ([], ["-n"]):
                add("matrix_s_flags", f"s/a/X/{flags}", INP, q)
for flags in ("g", "p", "2", "12", "12g", "g12", "1", "1g", "4p"):
    add("matrix_s_flags", f"s/a/X/{flags}", "aaaaaaaaaaaaaa\naa\n", ["-n"] if "p" in flags else [])
add("matrix_s_flags", "s/a*/X/2g", "baaac\n")
add("matrix_s_flags", "s/b*/X/g3", "abc\n")

# groups \1 to \9 and &, BRE and ERE
for k in range(1, 10):
    add("matrix_groups", "s/" + "\\(.\\)" * 9 + f"/[\\{k}]/", "abcdefghij\n")
    add("matrix_groups", "s/" + "(.)" * 9 + f"/<\\{k}\\{k}>/", "abcdefghij\n", ["-E"])
    add("matrix_groups", "s/\\(a\\)\\(b*\\)" + "\\(c\\)" * 7 + f"/&-\\{k}-\\&/", "xabbccccccccx\n")
add("matrix_groups", "s/\\(x\\)*y/[\\1]/", "y\nxxy\n")
add("matrix_groups", "s/(a|(b))+/[\\1\\2]/", "abab\n", ["-E"])

# repetition intervals in BRE and ERE
for rep in ("2", "2,", "1,3", "0,1", "0", "3,3"):
    add("matrix_intervals", f"s/a\\{{{rep}\\}}/X/g", "a aa aaa aaaa\n")
    add("matrix_intervals", f"s/a{{{rep}}}/X/g", "a aa aaa aaaa\n", ["-E"])
    add("matrix_intervals", f"s/\\(ab\\)\\{{{rep}\\}}/X/", "abababab\n")
    add("matrix_intervals", f"s/(ab){{{rep}}}/X/", "abababab\n", ["-E"])

# q and Q with their exit codes, including files that are never reached
for code in ("", "0", "1", "5", "42", "100", "255"):
    for cmd in "qQ":
        add("matrix_quit", f"2{cmd}{code}", "a\nb\nc\n")
        add("matrix_quit", f"/b/{cmd} {code}".rstrip(), "a\nb\nc\n", ["-n"])
        add("matrix_quit", f"{cmd}{code}", "", files=[["f", "x\ny\n"], ["m", None]])
add("matrix_quit", "$q42", "", files=[["f", "x\n"], ["g", "y\n"]])
add("matrix_quit", "2q42", "", files=[["f", "x\n"], ["m", None], ["g", "y\n"]])
add("matrix_quit", "q7", "", files=[["m", None], ["f", "x\n"]])
add("matrix_quit", "N;q9", "", files=[["f", "x\ny\nz\n"], ["m", None]])
add("matrix_quit", "a X\nq3", "a\nb\n")
add("matrix_quit", "a X\nQ3", "a\nb\n")
add("matrix_quit", "2{p;q12}", "a\nb\nc\n", ["-n"])
add("matrix_quit", "$!N;q21", "a\nb\nc\n")

# t and T around n, N, D and each other
for rd in ("n", "N"):
    add("matrix_t_flag", f"s/a/A/;{rd};T ok;s/$/BAD/;:ok", "a\nb\nc\nd\n")
    add("matrix_t_flag", f"s/a/A/;{rd};t ok;s/$/NONE/;:ok", "a\nb\nc\nd\n")
    add("matrix_t_flag", f"s/a/A/;{rd};s/b/B/;T ok;s/$/GOOD/;:ok", "a\nb\nc\nd\n")
    add("matrix_t_flag", f"s/a/A/;{rd};s/b/B/;t ok;s/$/NOT/;:ok", "a\nb\nc\nd\n")
add("matrix_t_flag", "s/x/X/;t;s/$/ no-x/", "x\ny\n")
add("matrix_t_flag", "s/x/X/;T;s/$/ had-x/", "x\ny\n")
add("matrix_t_flag", ":a;s/aa/a/;ta", "aaaaab\n")
add("matrix_t_flag", "s/a/b/;t x;:x;t y;s/$/ reset/;b;:y;s/$/ kept/", "a\nc\n")
add("matrix_t_flag", "$!N;s/\\n/-/;P;D", "a\nb\nc\n")

# addresses selecting blocks, and } followed by more commands
for addr in ("2,3", "/b/,/d/", "2,+1", "0~2,3", "2,~4", "0,/b/", "$", "3,$", "/c/,+2", "1~3", "2!", "2,3!"):
    add("matrix_blocks", f"{addr}{{s/./X/;p}}", "a\nb\nc\nd\ne\n", ["-n"])
    add("matrix_blocks", f"{addr}{{=;p}};p", "a\nb\nc\nd\ne\n", ["-n"])
add("matrix_blocks", "2{p};p", "a\nb\n", ["-n"])
add("matrix_blocks", "{p};{p}", "a\n", ["-n"])
add("matrix_blocks", "/a/{s/a/b/};{p}", "a\nc\n", ["-n"])
add("matrix_blocks", "1,3{/b/,/c/{s/^/>/}}", "a\nb\nc\nd\n")
add("matrix_blocks", "2{p}\n3{p};$p", "a\nb\nc\nd\n", ["-n"])

# - among named files, with and without -s (a file named "-" with no text is standard input)
F = {"f": "b\nc\n", "g": "d\n"}
for names, opt in ((["-", "f"], []), (["f", "-", "g"], []), (["f", "-"], ["-s"]), (["-", "f", "g"], ["-s"])):
    for script, q in (("p", []), ("$p", ["-n"]), ("=", []), ("1d", [])):
        add("matrix_files", script, "a\n", opt + q, files=[[n, F.get(n)] for n in names])

# the append queue is written when n or N reads, then at the end of the cycle
for script in ("a X\nN;P;d", "a X\nn;p", "i X\nN;P;D", "a X\nN;N;P;D", "$!a X\nN;P;D", "a X\nn;n;s/^/>/", "2a X\n$!N;P;D", "a X\na Y\nN;P;D"):
    add("matrix_append", script, "a\nb\nc\nd\n")
    add("matrix_append", script, "a\nb\nc\nd\n", ["-n"])

# longer inputs
for script, q in (("=", []), ("$=", ["-n"]), ("N;N;s/\\n/+/g", []), ("35,$p", ["-n"]), ("0~7p", ["-n"]),
                  ("$!N;P;D", []), ("/a$/,/a$/d", []), ("h;G;$!d", []), ("1~13,+2d", []), ("$,~9p", ["-n"])):
    add("matrix_long_input", script, LINES40, q)

# $ and ^ in a pattern space holding several lines, and anchors in ERE groups and alternatives
for script, ere in (("N;s/$/E/g", []), ("N;s/a$/X/", []), ("N;s/^b/X/", []), ("N;/a$/d", []), ("N;s/^/>/g", []),
                    ("N;s/b|^a/X/g", ["-E"]), ("N;s/a$|b/X/g", ["-E"]), ("N;s/(^|x)b/X/g", ["-E"]),
                    ("N;s/a(x|$)/X/g", ["-E"]), ("N;s/\\(^\\|x\\)b/X/g", []), ("N;s/a\\(x\\|$\\)/X/g", [])):
    add("matrix_anchors", script, "a\nb\nab\nba\n", ere)

# 0,/re/ and 1,/re/ with the first match on and after line 1; N on the last line
for script in ("0,/c/d", "1,/c/d", "0,/a/d", "1,/a/d", "0,/c/s/^/>/", "0,/b/{p}", "0,/x/d"):
    add("matrix_ranges", script, "a\nb\nc\nd\n")
for script, q in (("N", []), ("$!N", []), ("N;P;D", []), ("N;N", []), ("N;s/\\n/-/", ["-n"]), ("N;p", ["-n"])):
    add("matrix_ranges", script, "a\nb\nc\n", q)

for script, q in (("N;s/\\n/+/", []), ("N;p", ["-n"]), ("$!N;P;D", [])):
    add("matrix_ranges", script, "", ["-s"] + q, files=[["f", "a\n"], ["g", "b\nc\nd\n"]])
    add("matrix_ranges", script, "", q, files=[["f", "a\nb\nc\n"], ["g", "d\ne\n"]])

# delimiters of s and of addresses, and an escaped delimiter inside a bracket expression
for script in ("s1a1X1", "s,a,b,g", "s|a|b|g", "sxaxbx", "s:a\\:b:X:", "s#a#\\##g", "s;a;b;g", "s a b g",
               "\\%a%d", "\\,b,p", "\\|a\\|b|d", "s/[\\/]/X/g", "s,[\\,],X,g", "\\;[\\;];d", "s/a\\/b/X/"):
    add("matrix_delimiters", script, "a/b\na,b\nb;a\n#a#\na:b\n")

# bracket expressions
for br in ("[\\t]", "[a-]", "[-a]", "[]a]", "[^]a]", "[[:alpha:]-]", "[\\w]", "[\\]]", "[a\\]", "[[:digit:][:upper:]]", "[^[:space:]]", "[.]", "[*]"):
    add("matrix_brackets", f"s/{br}/X/g", "a-b]c\\d w\t.*Z9\n")
    add("matrix_brackets", f"s/{br}+/X/g", "a-b]c\\d w\t.*Z9\n", ["-E"])

# rev5 (v6 panel): commands after q/Q, labels followed by spaces, more delimiters,
# \n as a range endpoint, hold space across files, a missing file before a q code
for script, q in (("q;p", []), ("Q;p", []), ("2q;p", []), ("$q;=", []), ("2{p;q};p", ["-n"]), ("/b/Q;p", []),
                  ("a X\nQ", []), ("i X\nQ", []), ("2{a X\nQ5\n}", [])):
    add("matrix_quit", script, "a\nb\nc\n", q)
add("matrix_quit", "q42", "", files=[["m", None], ["f", "x\ny\n"]])
add("matrix_quit", "2Q42", "", files=[["f", "x\n"], ["m", None], ["g", "y\nz\n"]])
for script in ("s/a/A/;t x ;s/$/BAD/;:x", "s/a/A/;T x ;s/$/NOSUB/;:x", "b x ;s/$/BAD/;:x", "s/a/A/;t x\ns/$/BAD/\n:x",
               "s/a/A/;t  x  ;s/$/BAD/;: x\ns/$/!/", "/b/b end ;s/$/+/;:end"):
    add("matrix_t_flag", script, "a\nb\n")
for script in ("\\~a~p", "s~a~X~g", "\\=a=p", "s=a=X=g", "\\^a^p", "s^a^X^g", "\\.a.p", "s.a.X.g", "\\&a&p", "s&a&X&g"):
    add("matrix_delimiters", script, "a~=^.&\nb\n", ["-n"] if script.endswith("p") else [])
for br in ("[\\t-\\n]", "[\\n-\\n]", "[\\a-\\r]", "[^\\t-\\r]", "[\\a-\\t]", "[\\v-a]"):
    add("matrix_brackets", f"s/{br}/X/g", "A\t\r\a z\n")
    add("matrix_brackets", f"N;s/{br}/X/g", "a\tb\nc\v\n")
F2 = [["f", "a\nb\n"], ["g", "c\nd\n"]]
for script, q in (("/a/h;2g", []), ("1h;$G", []), ("H;$!d;x", []), ("x;1d", []), ("/c/{g;p}", ["-n"])):
    add("matrix_files", script, "", ["-s"] + q, files=F2)
    add("matrix_files", script, "", q, files=F2)

json.dump(out, open(sys.argv[1], "w"), indent=0, ensure_ascii=False)
print({k: len(v) for k, v in out.items()}, sum(len(v) for v in out.values()))
