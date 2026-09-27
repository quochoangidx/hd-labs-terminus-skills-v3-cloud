"""Systematic sweep over documented syntax dimensions; each case tagged with its family and the manual rule."""
import json
C = []
def c(fam, rule, script, inp, opts=(), **kw):
    d = {"family": fam, "rule": rule, "opts": list(opts), "script": script, "input": inp}; d.update(kw); C.append(d)
MIX = "aZ9 _-.,;:!?\t{}[]()\\/|*+^$@#%&~'\"\n"
# 1 every POSIX class, in s and in an address
for cl in "alpha digit alnum upper lower space blank punct print graph cntrl xdigit".split():
    c("bracket_expressions", f"[:{cl}:]", f"s/[[:{cl}:]]/X/g", MIX)
    c("bracket_expressions", f"[^[:{cl}:]]", f"s/[^[:{cl}:]]/X/g", "aZ9 _-.\t\n")
# bracket specials
for s, i in [("s/[]a]/X/g", "a]b\n"), ("s/[^]a]/X/g", "a]b\n"), ("s/[a-]/X/g", "-ab\n"), ("s/[.*]/X/g", "a.*b\n"),
             ("s/[\\n]/X/g", "anb\\\n"), ("s/[\\t]/X/g", "a\tt\\\n"), ("s/[[.-.]]/X/g", "a-b\n"), ("s/[[=b=]c]/X/g", "abc\n"),
             ("s/[a-cx-z]/X/g", "abcdwxyz\n"), ("s/[$^]/X/g", "a$^b\n")]:
    c("bracket_expressions", "bracket list rule", s, i)
# 2 escapes in regex, replacement, y, multiline a/i/c text
ESC = [("\\t", "a\tb"), ("\\x41", "aAb"), ("\\x4", None), ("\\o101", "aAb"), ("\\o7", None), ("\\d065", "aAb"), ("\\d9", None), ("\\cA", None)]
for e, text in ESC:
    if text: c("substitution_and_regex_escapes", f"regex escape {e}", f"s/{e}/X/g", text + "\n")
    c("substitution_and_regex_escapes", f"replacement escape {e}", f"s/b/<{e}>/", "abc\n")
    c("y_z_and_line_numbers", f"y escape {e}", f"y/b/{e}/", "abc\n")
    c("y_z_and_line_numbers", f"y source escape {e}", f"y/{e}b/QR/", "a\tb\x01\x04\x07A\n".replace("\x01", "") )
    for cmd in "aic":
        c("append_insert_change", f"{cmd} text escape {e}", f"{cmd}\\\nL{e}R", "x\n")
c("substitution_and_regex_escapes", "replacement \\n", "s/b/<\\n>/", "abc\n")
for cmd in "aic":
    c("append_insert_change", f"{cmd} \\\\ and \\n", f"{cmd}\\\nA\\\\B\\nC", "x\n")
    c("append_insert_change", f"{cmd} continuation then command", f"1{cmd}\\\nA\\\nB\ns/x/y/", "x\nx\n")
    c("append_insert_change", f"{cmd} one-line ; is text", f"{cmd} T;d", "x\n")
    c("append_insert_change", f"{cmd} one-line tab lead", f"{cmd}\tT", "x\n")
    c("append_insert_change", f"{cmd} one-line then -e command", f"1{cmd} T", "x\ny\n", extra=["-e", "s/y/Y/"])
    c("append_insert_change", f"{cmd} range", f"2,3{cmd} T", "a\nb\nc\nd\n")
    c("append_insert_change", f"{cmd} negated", f"2!{cmd} T", "a\nb\nc\n")
# 3 whitespace
for s in ["\tp", " \t p", "1 p", "1\tp", "1,2 !p", "1!\tp", "{ p }", "{\tp\t}", "1 { p ; p }", "$ p", "/b/ p", "p ; p", "p;\tp"]:
    c("comments_and_first_line", "whitespace", s, "a\nb\n", ["-n"])
# 4 delimiters
for d in "#|,;:@!%xX1_":
    if d in "x1":
        continue
    c("substitution_and_regex_escapes", f"s delimiter {d}", f"s{d}b{d}<\\{d}>{d}", "abc\n")
    c("substitution_and_regex_escapes", f"s escaped delimiter in regex {d}", f"s{d}\\{d}{d}X{d}g", f"a{d}b{d}\n")
    c("step_and_regex_addresses", f"address delimiter {d}", f"\\{d}b{d}p", "abc\nd\n", ["-n"])
    c("step_and_regex_addresses", f"address escaped delimiter {d}", f"\\{d}a\\{d}{d}p", f"a{d}b\nab\n", ["-n"])
    c("y_z_and_line_numbers", f"y delimiter {d}", f"y{d}ab{d}xy{d}", "abc\n")
    c("y_z_and_line_numbers", f"y escaped delimiter {d}", f"y{d}a\\{d}{d}\\{d}a{d}", f"a{d}b\n")
c("substitution_and_regex_escapes", "backslash delimiter", "s\\a\\b\\", "abc\n")
c("y_z_and_line_numbers", "y backslash delimiter", "y\\ab\\xy\\", "abc\n")
c("substitution_and_regex_escapes", "slash in bracket with other delimiter", "s,[/],X,g", "a/b\n")
# 5 M mode
for s in ["N;s/^/>/Mg", "N;s/$/</Mg", "N;s/./X/Mg", "N;s/\\`/>/Mg", "N;s/\\'/</Mg", "N;s/a.b/X/M", "N;s/a$/X/M", "N;s/^b/X/M"]:
    c("multiline_commands", "M in s", s, "a\nb\n")
for s in ["N;/a.b/Mp", "N;/a$/Mp", "N;/^b/Mp", "N;/\\`b/Mp", "N;/a\\'/Mp", "N;/b$/Mp"]:
    c("multiline_commands", "M in address", s, "a\nb\n", ["-n"])
# 6 escaped operators
for s, i, o in [("s/a\\?b/X/", "a?b ab\n", ["-E"]), ("s/a\\+b/X/", "a+b aab\n", ["-E"]), ("s/a\\|b/X/g", "a|b\n", ["-E"]),
                ("s/\\(a\\)/X/", "(a) a\n", ["-E"]), ("s/a\\{2\\}/X/", "a{2} aa\n", ["-E"]), ("s/a{2}/X/", "a{2} aa\n", []),
                ("s/a?b/X/", "a?b ab\n", []), ("s/a+b/X/", "a+b aab\n", []), ("s/a|b/X/g", "a|b\n", []), ("s/(a)/X/", "(a) a\n", []),
                ("s/a\\?b/X/g", "ab b\n", []), ("s/a\\+b/X/g", "aab b\n", []), ("s/a\\|b/X/g", "a|b\n", []),
                ("s/a*b/X/g", "aab b\n", ["-E"]), ("s/\\.\\*/X/g", "a.*b\n", ["-E"]), ("s/\\./X/g", "a.b\n", [])]:
    c("substitution_and_regex_escapes", "BRE/ERE operator", s, i, o)
# 7 anchors in groups and alternation
for s, o in [("s/\\(^a\\)/X/", []), ("s/\\(a$\\)/X/", []), ("s/(^a)/X/", ["-E"]), ("s/(a$)/X/", ["-E"]), ("s/b|^a/X/g", ["-E"]),
             ("s/a$|b/X/g", ["-E"]), ("s/\\(b\\|^a\\)/X/g", []), ("s/x^/X/", []), ("s/$x/X/", []), ("s/^*a/X/", []), ("s/a\\(^b\\)/X/", [])]:
    c("substitution_and_regex_escapes", "anchor position", s, "ab a\nba\n", o)
# 8 case conversion
for s in ["s/\\(b\\?\\)-/\\l\\1X/g", "s/\\(b\\?\\)-/\\u\\1x/g", "s/\\w\\+/\\u&/g", "s/\\w\\+/\\l&/g", "s/.*/\\U&/", "s/.*/\\L&/",
          "s/\\(a\\)\\(b\\)/\\U\\1\\E\\2/", "s/\\(\\w*\\) \\(\\w*\\)/\\U\\1\\L \\2/", "s/a/\\u\\LAB/", "s/a/\\l\\UAB/", "s/a/\\UA\\lBC/", "s/.*/\\L\\u&/"]:
    c("case_conversion", "case conversion", s, "ab Cd a--b-\n")
# 9 l wrapping
for w in (5, 6, 7, 8, 11, 12, 20):
    c("l_command", f"l {w} escapes", f"l {w}", "\\\\\\\\\\\\\\ab\tcd\\ef\t\tgh\\\n", ["-n"])
    c("l_command", f"l {w} plain", f"l {w}", "abcdefghijklmnopqrstuvwxyz\n", ["-n"])
c("l_command", "l 0 escapes", "l 0", "\\" * 40 + "\t" * 20 + "\n", ["-n"])
c("l_command", "default l escapes", "l", "\\" * 40 + "\t" * 20 + "\n", ["-n"])
# 10 labels
for s in ["b x;: x ;s/a/C/", ":x ;s/a/b/;tx", "b x ; s/a/B/;:x", "t x ;s/a/b/;:x", ":a;N;$!ba;s/\\n/,/g", "s/a/b/;T x ;s/$/!/;:x", "b;s/a/Z/"]:
    c("branching_and_t_flag", "labels", s, "a\na\n")
# 11 empty regex reuse
for s, o in [("/a/s//X/", []), ("s/a/X/;s//Y/", []), ("/b/!s//Z/;s/c//", []), ("/a/{s//X/g}", []), ("s/b/X/;//d", [])]:
    c("substitution_and_regex_escapes", "empty regex reuses last", s, "abc\nbab\ncc\n", o)
json.dump(C, open("sweep.json", "w"), indent=0)
print(len(C))
