import json, random
C = []
def c(group, src, args=None, files=None, stdin=None):
    C.append({"group": group, "src": src, "args": args if args is not None else ["in.m4"], "files": files or {}, "stdin": stdin or ""})
Q = "`"
# 1 lexical
for s in ["define(`a', `b')a a1 _a a_b A (a) `a' ``a'' a`'a\n",
          "# a comment with a `quote and define(x)\ndefine(`x',`X')x # x\nx#x\n",
          "define(`foo',`bar')foo(1)foo (1) foo\n`foo'foo`'foo\n",
          "``nested `quotes'''\n`unbalanced ``' quote'\n",
          "define(`x',`#')x x\ndefine(`y',`# not a comment')y y\n",
          "dnl a whole line\ntext dnl rest\nmore dnl(\n)dnl\nend\n",
          "define(`a1b',`AB')a1b a1 1a a1b2\n123abc\n",
          "`'dnl\n`#'not comment\n\\`foo'\n",
          "define(`e',`')e()e(x)[e]\n"]:
    c("lexical_rules", s)
# 2 invocation and args
for s in ["define(`f',`[$1|$2|$3]')f( a , b ,c )\nf(  `  a',(b,c),d)\nf((a,b),`c,d')\nf\nf()\n",
          "define(`f',`$#:$*:$@')f\nf()\nf(a)\nf(a,b)\nf(,)\nf(`a,b',c)\n",
          "define(`f',`$0')f f(x)\ndefine(`g',`$1$2$3$4$5$6$7$8$9$10$11')g(1,2,3,4,5,6,7,8,9,A,B)\n",
          "define(`f',`<$1>')f(\n  x\n)\nf(x\n)\nf(\tx)\n",
          "define(`f',`($1)')f(f(f(x)))\nf(`f(x)')\nf(``f(x)'')\n",
          "define(`q',`$@')define(`s',`$*')q(`a',`b,c') s(`a',`b,c')\n[q(`define(`z',`Z')')] z\n",
          "define(`f',`$1$1')f(`$1')\ndefine(`g',`$$1 $ $a $#1')g(x)\n",
          "define(`f', `[$1]')f(\n(a,\nb))\nf(`)')f(()\n)\n"]:
    c("invocation_and_arguments", s)
# 3 rescanning
for s in ["define(`x',`y')define(`y',`z')x `x' ``x''\n",
          "define(`a',`b')define(`b',`c')define(`c',`done')a\ndefine(`d',``a'')d\ndefine(`e',```a''')e\n",
          "define(`paren',`(')define(`f',`<$1>')f paren`'x)\n",
          "define(`cat',`$1$2')cat(`def',`ine')(`w',`W')w\n",
          "define(`half',`define')half(`h',`H')h\n",
          "define(`f',`g')define(`g(x)',`no')define(`g',`G($1)')f(1)\n",
          "define(`x',`X')define(`q',`x`x'x')q `q'\n",
          "define(`c',`,')define(`f',`[$1][$2]')f(a c b)\nf(a`,'b)\n"]:
    c("rescanning", s)
# 4 definitions
for s in ["define(`a')a|define(`b',)b|define(`c',`x',`y')c|\n",
          "define(`a',`1')pushdef(`a',`2')a popdef(`a')a popdef(`a')a|\n",
          "pushdef(`a',`1')pushdef(`a',`2')define(`a',`3')a popdef(`a')a\n",
          "define(`a',`A')undefine(`a')a undefine(`nosuch')|\n",
          "define(`a',`A')define(`b',`B')defn(`a',`b') defn(`a')defn(`b')|defn(`nosuch')|\n",
          "define(`mydef',defn(`define'))mydef(`x',`X')x\n",
          "define(`x',`$1')define(`y',defn(`x'))y(`arg')\n",
          "define(`odd name',`ON')indir(`odd name') odd name\nindir(`define',`n',`N')n\n",
          "builtin(`define',`b',`B')b builtin(`len',`abc') builtin(`nosuch')|\n",
          "define(`len',`mine')len(`abc') builtin(`len',`abc')\nundefine(`len')len(`abc')\n",
          "define(`d',`defn')d(`d')\ndefine(`dd',defn(`defn'))dd(`dd')|\n",
          "define(`f',defn(`ifelse'))f(a,a,yes,no)\n"]:
    c("definitions", s)
# 5 conditionals, shift, loops
for s in ["ifdef(`foo',`yes',`no') define(`foo')ifdef(`foo',`yes',`no') ifdef(`foo',`only')|\n",
          "ifelse(`some comment')|ifelse(a,a)|ifelse(a,b,c)|ifelse(a,a,yes,no)|ifelse(a,b,yes,no)|\n",
          "ifelse(a,b,1,c,c,2,3)|ifelse(a,b,1,c,d,2,3)|ifelse(a,b,1,c,d,2)|ifelse(a,b,1,c,d)|\n",
          "shift|shift(a)|shift(a,b,c)|shift(`a',`b,c',d)|shift(shift(a,b,c))\n",
          "define(`reverse', `ifelse(`$#', `0', , `$#', `1', ``$1'',\n`reverse(shift($@)), `$1'')')reverse reverse(a) reverse(a,b,c)\n",
          "define(`forloop', `pushdef(`$1', `$2')_forloop($@)popdef(`$1')')\ndefine(`_forloop',\n`$4`'ifelse($1, `$3', `', `define(`$1', incr($1))$0($@)')')\nforloop(`i', `1', `8', `i ')\n",
          "define(`foreach', `pushdef(`$1')_foreach($@)popdef(`$1')')\ndefine(`_arg1', `$1')\ndefine(`_foreach', `ifelse(`$2', `()', `',\n`define(`$1', _arg1$2)$3`'$0(`$1', (shift$2), `$3')')')\nforeach(`x', (foo, bar, `foobar'), `Word was: x\n')\n",
          "define(`cnt',`ifelse($1,0,,`$1 cnt(decr($1))')')cnt(5)\n",
          "define(`fact',`ifelse(eval($1<=1),1,1,`eval($1*fact(decr($1)))')')fact(10)\n",
          "ifelse(`a',`a',`define(`z',`Z')')z ifelse(,,empty)\n"]:
    c("conditionals_and_loops", s)
# 6 quotes and comments changes
for s in ["changequote([,])define([a],[b])a [a] `a'\nchangequote`'define(`c',`d')c\n",
          "changequote(<<,>>)define(<<x>>,<<X>>)x <<x>> <<<<x>>>>\nchangequote\nx `x'\n",
          "changequote([)define([a],[b)a [a] changequote`'\n",
          "changequote(,)define(`a',`b')a `a'\nchangequote(`,')`a'\n",
          "changecom(`/*',`*/')define(`x',`X')x /* x */ x # x\nchangecom\nx # x\n",
          "changecom(`@')define(`x',`X')@ x\nx\nchangecom(`')# x\n",
          "define(`x',`X')changequote(`[',`]')[x] [[x]] changequote(`q',`Q')qxQ x\n",
          "changecom(`#',`')# x x\nx\n",
          "changequote({,})define({f},{[$1]})f({a,b})f({{a}})\n"]:
    c("quotes_and_comments", s)
# 7 m4wrap, include, diversions
F = {"inc.m4": "define(`fromfile',`FF')included text __file__:__line__\n", "noeol.m4": "no eol", "div.m4": "in div file\n"}
for s in ["m4wrap(`wrapped one\n')m4wrap(`wrapped two\n')text\n",
          "define(`f',`recursed')m4wrap(`f\n')m4wrap(`m4wrap(`nested\n')')body\n",
          "include(`inc.m4')fromfile\nsinclude(`missing.m4')|include(`noeol.m4')|\n",
          "include(`missing.m4')after\n",
          "divert(1)one\ndivert(2)two\ndivert(0)zero\nundivert(2)divnum\n",
          "divert(-1)define(`x',`X')discarded\ndivert`'x\n",
          "divert(3)three\ndivert(1)one\ndivert(2)two\ndivert\nmain\n",
          "divert(1)a\ndivert(2)b\nundivert(1)divert(0)undivert\nend\n",
          "divert(1)in one\nundivert(1)divert(0)x\nundivert(1)|\n",
          "undivert(`div.m4')|divert(1)undivert(`div.m4')divert|\n",
          "divert(1)A\ndivert(2)B\ndivert(-1)undivert(1)divert(0)undivert\n",
          "m4wrap(`divert(1)late\n')divert(1)early\ndivert\n",
          "divnum divert(4)divnum divert(0)divnum undivert(4)\n"]:
    c("wrap_include_divert", s, files=F)
# 8 text builtins
for s in ["len(`')len(`abc')len(abc)len(`a,b')\n",
          "index(`gnus, gnats, and armadillos', `nat')index(`abc',`')index(`abc',`d')index(`',`')\n",
          "regexp(`GNUs not Unix', `\\<[a-z]\\w+')|regexp(`GNUs not Unix', `\\<Q\\w*')|regexp(`GNUs not Unix', `\\w\\(\\w+\\)$', `*** \\& *** \\1 ***')|\n",
          "regexp(`abc',`b',`[\\&]')|regexp(`abc',`\\(b\\)\\(c\\)',`\\2\\1\\\\')|regexp(`abc',`')|regexp(`abc',`x*',`[\\&]')|\n",
          "substr(`gnus, gnats, and armadillos', `11')|substr(`gnus, gnats, and armadillos', `11', `5')|substr(`abc',`-1')|substr(`abc',`1',`-1')|substr(`abc',`5')|substr(`abc')|\n",
          "translit(`GNUs not Unix', `A-Z')|translit(`GNUs not Unix', `a-z', `A-Z')|translit(`GNUs not Unix', `A-Z', `z-a')|translit(`+,-12345', `+--1-5', `<;>a-c-a')|translit(`abc',`abc',`x')|\n",
          "patsubst(`GNUs not Unix', `^', `OBS: ')|patsubst(`GNUs not Unix', `\\<', `OBS: ')|patsubst(`GNUs not Unix', `\\w*', `(\\&)')|patsubst(`GNUs not Unix', `\\w+', `(\\&)')|patsubst(`GNUs not Unix', `[A-Z][a-z]+')|\n",
          "patsubst(`aaa',`a*',`x')|patsubst(`abc',`',`-')|patsubst(`a.b.c',`\\.',`\\\\')|patsubst(`hello world',`\\(\\w+\\) \\(\\w+\\)',`\\2 \\1')|\n",
          "define(`upcase', `translit(`$*', `a-z', `A-Z')')upcase(`hi there')\npatsubst(`a+b',`+',`P')|regexp(`a+b',`a+')|patsubst(`xAAy',`A\\{2\\}',`2')|patsubst(`x|y',`x\\|y',`Z')|\n",
          "regexp(`abcabc',`\\(a\\|ab\\)\\(c\\|bcd\\)',`[\\1,\\2]')|patsubst(`abab',`\\(ab\\)*',`<\\1>')|\n",
          "format(`Result is %d', `42')|format(`%5d|%-5d|%05d', 7, 7, 7)|format(`%x %X %o %c', 255, 255, 8, 65)|format(`%s and %.3s', `hello', `abcdef')|\n",
          "format(`%.2f %e %g %g', `3.14159', `12345.678', `0.0001', `1e10')|format(`%%|%*d|%-*d|', 4, 5, 3, 6)|format(`%d', `12abc')|format(`plain')|\n"]:
    c("text_builtins", s)
# 9 arithmetic
for s in ["eval(`1+2*3')|eval(`(1+2)*3')|eval(`-3/2')|eval(`-3%2')|eval(`7/-2')|eval(`2**10')|eval(`2**0')|eval(`-2**2')|\n",
          "eval(`1<2')|eval(`2<=2')|eval(`3==3')|eval(`3!=3')|eval(`!0')|eval(`~0')|eval(`1&&0')|eval(`0||2')|eval(`1?2:3')|\n",
          "eval(`1<<4')|eval(`256>>4')|eval(`-1>>1')|eval(`5&3')|eval(`5|3')|eval(`5^3')|eval(`0x1F')|eval(`010')|eval(`0b101')|eval(`0r36:zz')|\n",
          "eval(`255',`16')|eval(`255',`2',`12')|eval(`-255',`16',`4')|eval(`10',`36')|eval(`5',`10',`3')|eval(`0',`16',`0')|eval(`100',`1')|\n",
          "eval(`1/0')|after\n", "eval(`1 +')|after\n", "eval(`2147483647+1')|eval(`-2147483648/-1')|eval(`0x7fffffff*2')|\n",
          "incr(`5')|decr(`5')|incr(`-1')|incr(`0x10')|incr(` 7')|\n",
          "eval(`  4 * ( 2 + 1 ) ')|eval(`1 == 1 == 1')|eval(`2 ** 3 ** 2')|eval(`-(-3)')|eval(`+5')|eval(`!!5')|\n",
          "eval(`10 % 0')|next\n", "eval(`a')|next\n", "eval(`1,2')|eval(`(1')|next\n", "eval(`2**-1')|next\n"]:
    c("arithmetic", s)
# 10 misc
for s in ["__file__ __line__\n__line__ __program__\nifdef(`__gnu__',`gnu')ifdef(`__unix__',`unix')__gnu__|__unix__|\n",
          "errprint(`to stderr\n')after\n", "before\nm4exit(`3')after\n", "m4wrap(`wrapped\n')text\nm4exit\n",
          "define(`x',`X')m4exit(`0')x\n", "m4exit(`2')", "divert(1)kept\ndivert\nm4exit(`1')\n",
          "indir(`nosuch')after\n", "`unterminated quote\n", "define(`f',`x')f(unterminated\n", "# comment without newline",
          "define(`x')x(1,2)dnl\n", "undefine(`define')define(`a',`b')a\n"]:
    c("misc_and_errors", s)
# 11 files and stdin
c("files_and_stdin", "", args=["a.m4", "b.m4"], files={"a.m4": "define(`x',`X')a:__file__:__line__\n", "b.m4": "x b:__file__:__line__\n"})
c("files_and_stdin", "", args=["a.m4", "-", "b.m4"], files={"a.m4": "define(`y',`Y')A\n", "b.m4": "y B __file__\n"}, stdin="y stdin __file__ __line__\n")
c("files_and_stdin", "", args=[], stdin="define(`s',`S')s __file__\n")
c("files_and_stdin", "", args=["a.m4", "b.m4"], files={"a.m4": "`open quote\n", "b.m4": "never\n"})
c("files_and_stdin", "", args=["a.m4", "missing.m4", "b.m4"], files={"a.m4": "A\n", "b.m4": "B\n"})
c("files_and_stdin", "", args=["a.m4", "b.m4"], files={"a.m4": "define(`f',`($1)')f(", "b.m4": "arg)\n"})
c("files_and_stdin", "", args=["a.m4", "b.m4"], files={"a.m4": "divert(1)from a\ndivert\n", "b.m4": "b\nm4wrap(`wrap\n')"})
# random mixed programs
rng = random.Random(3)
WORDS = ["foo", "bar", "baz", "x", "y1", "_z", "q"]
def atom(depth):
    r = rng.random()
    if depth <= 0 or r < 0.25:
        return rng.choice(WORDS + ["hello world", "a,b", "(x)", "", "12", "-3", "abc123"])
    k = rng.randrange(13)
    a = lambda: arg(depth - 1)
    if k == 0: return f"len({a()})"
    if k == 1: return f"index({a()},{rng.choice(['`o', '`a', '`', '`1'])}')"
    if k == 2: return f"substr({a()},{rng.randint(-1, 4)}{',' + str(rng.randint(-1, 5)) if rng.random() < .6 else ''})"
    if k == 3: return f"translit({a()},{rng.choice(['`a-z', '`o', '`abc', '`z-a'])}',{rng.choice(['`A-Z', '`', '`xy', '`0-9'])}')"
    if k == 4: return f"eval({rng.randint(-9, 9)}{rng.choice(['+', '*', '-', '/', '%', '**', '<', '==', '&', '|', '<<'])}{rng.randint(1, 5)}{',' + str(rng.choice([2, 8, 16, 36])) if rng.random() < .3 else ''})"
    if k == 5: return f"ifelse({a()},{a()},{a()},{a()})"
    if k == 6: return f"patsubst({a()},{rng.choice(['`o', '`[a-z]+', '`\\w', '`^', '`\\(.\\)\\(.\\)'])}',{rng.choice(['`<\\&>', '`', '`\\2\\1', '`_'])}')"
    if k == 7: return f"regexp({a()},{rng.choice(['`o+', '`[0-9]', '`\\b', '`\\(.\\)$'])}'{rng.choice([',`[\\&]', ',`\\1\\1', ''])}')"
    if k == 8: return f"format({rng.choice(['`%s-%s', '`%5s|', '`%d', '`%x', '`%-3s.'])}',{a()},{a()})"
    if k == 9: return f"m{rng.randint(1, 4)}({a()},{a()})"
    if k == 10: return f"shift({a()},{a()},{a()})"
    if k == 11: return f"incr({rng.randint(-5, 50)})"
    return rng.choice(WORDS)
def arg(depth):
    s = atom(depth)
    r = rng.random()
    if r < 0.45: return "`" + s + "'"
    if r < 0.55: return "``" + s + "''"
    if r < 0.65: return " " + s
    return s
BODIES = ["[$1|$2]", "$2$1", "`$1'-`$2'", "$#:$*", "$@", "ifelse(`$1',,empty,`<$1>')", "len(`$1$2')", "`$0'($1)", "translit(`$1',`a-z',`A-Z')", "$1`'$1", "``$1''", "define(`last',`$1')", "substr(`$1',1)", "eval($#*10)"]
for i in range(140):
    lines = []
    if rng.random() < 0.2: lines.append("changequote([,])" if False else "")
    for m in range(1, 5):
        lines.append(f"define(`m{m}',`{rng.choice(BODIES)}')dnl")
    for w in WORDS[:rng.randint(1, 4)]:
        lines.append(f"define(`{w}',`{rng.choice(['W', 'foo', 'x y', '$1!', 'bar', '(', ','])}')dnl")
    if rng.random() < 0.3: lines.append(f"pushdef(`foo',`pushed')dnl")
    if rng.random() < 0.2: lines.append("divert(1)dnl")
    for _ in range(rng.randint(3, 7)):
        lines.append(atom(3) + rng.choice(["", " ", " foo", " x", "|"]))
    if rng.random() < 0.3: lines.append("popdef(`foo')foo last")
    if rng.random() < 0.2: lines.append("divert`'undivert(1)dnl")
    c(f"mixed_{i % 4 + 1}", "\n".join(l for l in lines if l is not None) + "\n")
json.dump(C, open("cases_raw.json", "w")); print(len(C))
