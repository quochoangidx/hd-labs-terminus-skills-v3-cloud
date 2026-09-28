"""pym4: a GNU m4 1.4.19 replacement in pure Python.

Usage: python3 /app/pym4/m4.py [FILE]...
"""

import math
import os
import re
import sys
import threading

SPACES = ' \t\n\v\f\r'
DIGITS = '0123456789'
LOWER = 'abcdefghijklmnopqrstuvwxyz'
UPPER = LOWER.upper()
ALPHA = LOWER + UPPER
WORD_START = frozenset(ALPHA + '_')
WORD_CHARS = frozenset(ALPHA + DIGITS + '_')
WORD_RUN_RE = re.compile(r'[A-Za-z0-9_]*')

T_EOF, T_STRING, T_WORD, T_OPEN, T_COMMA, T_CLOSE, T_SIMPLE, T_MACDEF = range(8)
K_STR, K_FILE, K_MACRO = range(3)


class _MacroChar(object):
    pass


MACRO_CH = _MacroChar()


class M4Fatal(Exception):
    pass


class M4Exit(Exception):
    def __init__(self, code):
        Exception.__init__(self, code)
        self.code = code


class Builtin(object):
    __slots__ = ('name', 'func', 'groks', 'blind')

    def __init__(self, name, func, groks, blind):
        self.name = name
        self.func = func
        self.groks = groks
        self.blind = blind


class Def(object):
    __slots__ = ('text', 'bi')

    def __init__(self, text, bi=None):
        self.text = text
        self.bi = bi


class Block(object):
    __slots__ = ('kind', 'text', 'pos', 'file', 'line', 'advance', 'bi')

    def __init__(self, kind, text, file, line, bi=None):
        self.kind = kind
        self.text = text
        self.pos = 0
        self.file = file
        self.line = line
        self.advance = False
        self.bi = bi


def w32(v):
    return ((v + 0x80000000) & 0xFFFFFFFF) - 0x80000000


def w64(v):
    return ((v + 0x8000000000000000) & 0xFFFFFFFFFFFFFFFF) - 0x8000000000000000


def strtol(s):
    """Emulate C strtol base 10.  Returns (value, endindex)."""
    n = len(s)
    i = 0
    while i < n and s[i] in SPACES:
        i += 1
    j = i
    neg = False
    if j < n and s[j] in '+-':
        neg = s[j] == '-'
        j += 1
    k = j
    while k < n and s[k] in DIGITS:
        k += 1
    if k == j:
        return 0, 0
    v = int(s[j:k])
    if neg:
        v = -v
    if v > 0x7FFFFFFFFFFFFFFF:
        v = 0x7FFFFFFFFFFFFFFF
    elif v < -0x8000000000000000:
        v = -0x8000000000000000
    return v, k


_DEC_FLOAT_RE = re.compile(r'(?:[0-9]+\.?[0-9]*|\.[0-9]+)(?:[eE][+-]?[0-9]+)?')
_HEX_FLOAT_RE = re.compile(
    r'0[xX](?:[0-9a-fA-F]+\.?[0-9a-fA-F]*|\.[0-9a-fA-F]+)(?:[pP][+-]?[0-9]+)?')


def strtod(s):
    """Emulate C strtod.  Returns (value, endindex)."""
    n = len(s)
    i = 0
    while i < n and s[i] in SPACES:
        i += 1
    j = i
    sign = 1.0
    if j < n and s[j] in '+-':
        if s[j] == '-':
            sign = -1.0
        j += 1
    low = s[j:j + 8].lower()
    if low.startswith('infinity'):
        return sign * float('inf'), j + 8
    if low.startswith('inf'):
        return sign * float('inf'), j + 3
    if low.startswith('nan'):
        k = j + 3
        if k < n and s[k] == '(':
            m = k + 1
            while m < n and (s[m] in WORD_CHARS):
                m += 1
            if m < n and s[m] == ')':
                k = m + 1
        return math.copysign(float('nan'), sign), k
    m = _HEX_FLOAT_RE.match(s, j)
    if m:
        txt = m.group()
        try:
            v = float.fromhex(txt)
        except OverflowError:
            v = float('inf')
        return sign * v, m.end()
    m = _DEC_FLOAT_RE.match(s, j)
    if m:
        return sign * float(m.group()), m.end()
    return 0.0, 0


class M4(object):
    def __init__(self):
        self.symtab = {}
        self.lquote = '`'
        self.rquote = "'"
        self.bcomm = '#'
        self.ecomm = '\n'
        self.stack = []
        self.cur_file = ''
        self.cur_line = 0
        self.input_change = False
        self.sol = False
        self.wrap = []
        self.divs = {}
        self.cur_div = 0
        self.out0 = []
        self.retcode = 0
        self.stdin_used = False
        self._syntax_changed()
        self.builtins = {}
        self._regex_cache = {}
        self._init_builtins()

    # ------------------------------------------------------------------
    # diagnostics

    def warn(self, msg):
        try:
            if self.cur_line:
                sys.stderr.write('m4:%s:%d: %s\n' % (self.cur_file, self.cur_line, msg))
            else:
                sys.stderr.write('m4: %s\n' % msg)
        except Exception:
            pass

    def fatal(self, msg):
        self.warn(msg)
        raise M4Fatal(msg)

    # ------------------------------------------------------------------
    # syntax helpers

    def _syntax_changed(self):
        excl = set(ALPHA + '_')
        if self.lquote:
            excl.add(self.lquote[0])
        if self.bcomm:
            excl.add(self.bcomm[0])
        cls = ''.join(re.escape(c) for c in sorted(excl))
        self.plain_re = re.compile('[^' + cls + ']+')
        excl2 = set(excl)
        excl2.update('(),')
        cls2 = ''.join(re.escape(c) for c in sorted(excl2))
        self.arg_plain_re = re.compile('[^' + cls2 + ']+')
        if self.lquote:
            qc = set([self.lquote[0], self.rquote[0]])
            self.quote_body_re = re.compile(
                '[^' + ''.join(re.escape(c) for c in sorted(qc)) + ']*')
        else:
            self.quote_body_re = None
        if self.bcomm:
            self.comm_body_re = re.compile('[^' + re.escape(self.ecomm[0]) + ']*')
        else:
            self.comm_body_re = None

    # ------------------------------------------------------------------
    # input stack

    def push_file(self, text, name):
        b = Block(K_FILE, text, name, 1)
        b.advance = self.sol
        self.sol = False
        self.stack.append(b)
        self.input_change = True

    def push_string(self, text, file, line):
        if text:
            self.stack.append(Block(K_STR, text, file, line))
            self.input_change = True

    def push_macro(self, bi):
        self.stack.append(Block(K_MACRO, '', self.cur_file, self.cur_line, bi))
        self.input_change = True

    def pop_input(self):
        b = self.stack.pop()
        if b.kind == K_FILE:
            self.sol = b.advance
        self.input_change = True

    def next_char(self):
        stack = self.stack
        while stack:
            b = stack[-1]
            if self.input_change:
                self.cur_file = b.file
                self.cur_line = b.line
                self.input_change = False
            if b.kind == K_STR:
                if b.pos < len(b.text):
                    c = b.text[b.pos]
                    b.pos += 1
                    return c
            elif b.kind == K_FILE:
                if self.sol:
                    self.sol = False
                    b.line += 1
                    self.cur_line = b.line
                if b.pos < len(b.text):
                    c = b.text[b.pos]
                    b.pos += 1
                    if c == '\n':
                        self.sol = True
                    return c
            self.pop_input()
        self.cur_file = ''
        self.cur_line = 0
        return None

    def peek_char(self):
        for b in reversed(self.stack):
            if b.kind == K_MACRO:
                return MACRO_CH
            if b.pos < len(b.text):
                return b.text[b.pos]
        return None

    def peek_str(self, n):
        res = []
        need = n
        for b in reversed(self.stack):
            if b.kind == K_MACRO:
                break
            chunk = b.text[b.pos:b.pos + need]
            if chunk:
                res.append(chunk)
                need -= len(chunk)
                if need <= 0:
                    break
        return ''.join(res)

    def lookahead(self, s, consume=True):
        """Check whether the input continues with S[1:] (S[0] already read)."""
        rest = s[1:]
        if not rest:
            return True
        if self.peek_str(len(rest)) == rest:
            if consume:
                for _ in range(len(rest)):
                    self.next_char()
            return True
        return False

    def read_run(self, regex):
        """Consume a run matching REGEX from the top block only."""
        stack = self.stack
        if not stack:
            return ''
        b = stack[-1]
        if b.kind == K_MACRO:
            return ''
        m = regex.match(b.text, b.pos)
        if not m:
            return ''
        chunk = m.group()
        if not chunk:
            return ''
        if self.input_change:
            self.cur_file = b.file
            self.cur_line = b.line
            self.input_change = False
        if b.kind == K_FILE:
            if self.sol:
                self.sol = False
                b.line += 1
            nl = chunk.count('\n')
            if nl:
                if chunk[-1] == '\n':
                    b.line += nl - 1
                    self.sol = True
                else:
                    b.line += nl
            self.cur_line = b.line
        b.pos = m.end()
        return chunk

    # ------------------------------------------------------------------
    # tokenizer

    def peek_token(self):
        ch = self.peek_char()
        if ch is None:
            return T_EOF
        if ch is MACRO_CH:
            return T_MACDEF
        bc = self.bcomm
        if bc and ch == bc[0] and self.peek_str(len(bc)) == bc:
            return T_STRING
        if ch in WORD_START:
            return T_WORD
        lq = self.lquote
        if lq and ch == lq[0] and self.peek_str(len(lq)) == lq:
            return T_STRING
        if ch == '(':
            return T_OPEN
        if ch == ',':
            return T_COMMA
        if ch == ')':
            return T_CLOSE
        return T_SIMPLE

    def next_token(self):
        ch = self.peek_char()
        if ch is None:
            return T_EOF, None
        if ch is MACRO_CH:
            while self.stack[-1].kind != K_MACRO:
                self.pop_input()
            b = self.stack[-1]
            if self.input_change:
                self.cur_file = b.file
                self.cur_line = b.line
                self.input_change = False
            self.pop_input()
            return T_MACDEF, b.bi
        c = self.next_char()
        bc = self.bcomm
        if bc and c == bc[0] and self.lookahead(bc):
            ec = self.ecomm
            parts = [bc]
            e0 = ec[0]
            body = self.comm_body_re
            while True:
                chunk = self.read_run(body)
                if chunk:
                    parts.append(chunk)
                c = self.next_char()
                if c is None:
                    self.fatal('ERROR: end of file in comment')
                if c == e0 and self.lookahead(ec):
                    parts.append(ec)
                    break
                parts.append(c)
            return T_STRING, ''.join(parts)
        if c in WORD_START:
            parts = [c]
            while True:
                chunk = self.read_run(WORD_RUN_RE)
                if chunk:
                    parts.append(chunk)
                nc = self.peek_char()
                if nc is None or nc is MACRO_CH or nc not in WORD_CHARS:
                    break
                parts.append(self.next_char())
            return T_WORD, ''.join(parts)
        lq = self.lquote
        if lq and c == lq[0] and self.lookahead(lq):
            rq = self.rquote
            l0 = lq[0]
            r0 = rq[0]
            depth = 1
            parts = []
            body = self.quote_body_re
            while True:
                chunk = self.read_run(body)
                if chunk:
                    parts.append(chunk)
                c = self.next_char()
                if c is None:
                    self.fatal('ERROR: end of file in string')
                if c == r0 and self.lookahead(rq):
                    depth -= 1
                    if depth == 0:
                        break
                    parts.append(rq)
                elif c == l0 and self.lookahead(lq):
                    depth += 1
                    parts.append(lq)
                else:
                    parts.append(c)
            return T_STRING, ''.join(parts)
        if c == '(':
            return T_OPEN, c
        if c == ',':
            return T_COMMA, c
        if c == ')':
            return T_CLOSE, c
        return T_SIMPLE, c

    # ------------------------------------------------------------------
    # output

    def output(self, text):
        d = self.cur_div
        if d == 0:
            self.out0.append(text)
        elif d > 0:
            lst = self.divs.get(d)
            if lst is None:
                self.divs[d] = [text]
            else:
                lst.append(text)

    def insert_diversion(self, n):
        if n < 0 or n == self.cur_div:
            return
        lst = self.divs.pop(n, None)
        if lst:
            self.output(''.join(lst))

    def undivert_all(self):
        for n in sorted(self.divs.keys()):
            if n != self.cur_div:
                self.insert_diversion(n)

    # ------------------------------------------------------------------
    # symbols

    def lookup(self, name):
        st = self.symtab.get(name)
        if st:
            return st[-1]
        return None

    def define(self, name, d, push=False):
        st = self.symtab.get(name)
        if st:
            if push:
                st.append(d)
            else:
                st[-1] = d
        else:
            self.symtab[name] = [d]

    # ------------------------------------------------------------------
    # expansion

    def expand_input(self):
        while True:
            stack = self.stack
            if stack:
                b = stack[-1]
                if b.kind != K_MACRO and b.pos < len(b.text):
                    run = self.read_run(self.plain_re)
                    if run:
                        self.output(run)
            t, v = self.next_token()
            if t == T_EOF:
                return
            if t == T_WORD:
                self.expand_word(None, v)
            elif t == T_MACDEF:
                pass
            else:
                self.output(v)

    def expand_word(self, obs, name):
        d = self.lookup(name)
        if d is None or (d.bi is not None and d.bi.blind
                         and self.peek_token() != T_OPEN):
            if obs is None:
                self.output(name)
            else:
                obs.append(name)
        else:
            self.expand_macro(name, d)

    def expand_macro(self, name, d):
        open_f = self.cur_file
        open_l = self.cur_line
        argv = self.collect_arguments(name, d)
        close_f = self.cur_file
        close_l = self.cur_line
        self.cur_file = open_f
        self.cur_line = open_l
        out = []
        self.call_macro(d, argv, out)
        text = ''.join(out)
        if text:
            self.push_string(text, open_f, open_l)
        self.cur_file = close_f
        self.cur_line = close_l

    def collect_arguments(self, name, d):
        argv = [name]
        groks = d.bi is not None and d.bi.groks
        if self.peek_token() == T_OPEN:
            self.next_token()
            while True:
                more, arg = self.expand_argument()
                if not groks and not isinstance(arg, str):
                    arg = ''
                argv.append(arg)
                if not more:
                    break
        return argv

    def expand_argument(self):
        obs = []
        func = None
        t, v = self.next_token()
        while t == T_SIMPLE and v in SPACES:
            t, v = self.next_token()
        paren = 0
        while True:
            if t == T_COMMA or t == T_CLOSE:
                if paren == 0:
                    if func is not None:
                        return t == T_COMMA, func
                    return t == T_COMMA, ''.join(obs)
                if t == T_CLOSE:
                    paren -= 1
                obs.append(v)
            elif t == T_OPEN:
                paren += 1
                obs.append(v)
            elif t == T_SIMPLE or t == T_STRING:
                obs.append(v)
            elif t == T_WORD:
                self.expand_word(obs, v)
            elif t == T_EOF:
                self.fatal('ERROR: end of file in argument list')
            elif t == T_MACDEF:
                if not any(obs):
                    func = v
            stack = self.stack
            if stack:
                b = stack[-1]
                if b.kind != K_MACRO and b.pos < len(b.text):
                    run = self.read_run(self.arg_plain_re)
                    if run:
                        obs.append(run)
            t, v = self.next_token()

    def call_macro(self, d, argv, out):
        if d.bi is not None:
            d.bi.func(argv, out)
        else:
            self.expand_user(d.text, argv, out)

    def expand_user(self, text, argv, out):
        i = 0
        n = len(text)
        argc = len(argv)
        while True:
            j = text.find('$', i)
            if j < 0:
                out.append(text[i:])
                return
            out.append(text[i:j])
            k = j + 1
            c = text[k] if k < n else ''
            if c and c in DIGITS:
                m = k
                while m < n and text[m] in DIGITS:
                    m += 1
                idx = int(text[k:m])
                if idx < argc:
                    a = argv[idx]
                    if isinstance(a, str):
                        out.append(a)
                i = m
            elif c == '#':
                out.append(str(argc - 1))
                i = k + 1
            elif c == '*' or c == '@':
                self.dump_args(out, argv, ',', c == '@')
                i = k + 1
            else:
                out.append('$')
                i = k

    def dump_args(self, out, argv, sep, quoted):
        first = True
        for a in argv[1:]:
            if not first:
                out.append(sep)
            first = False
            if not isinstance(a, str):
                a = ''
            if quoted:
                out.append(self.lquote)
                out.append(a)
                out.append(self.rquote)
            else:
                out.append(a)

    # ------------------------------------------------------------------
    # driver

    def read_file(self, name):
        if name == '' or os.path.isdir(name):
            return None
        try:
            with open(name, 'rb') as f:
                return f.read().decode('latin-1')
        except (IOError, OSError):
            return None

    def run(self, files):
        code = 0
        try:
            try:
                if not files:
                    files = ['-']
                for f in files:
                    if f == '-':
                        if self.stdin_used:
                            text = ''
                        else:
                            self.stdin_used = True
                            try:
                                text = sys.stdin.buffer.read().decode('latin-1')
                            except Exception:
                                text = ''
                        self.push_file(text, 'stdin')
                    else:
                        text = self.read_file(f)
                        if text is None:
                            sys.stderr.write("m4: cannot open `%s': No such file or directory\n" % f)
                            self.retcode = 1
                            continue
                        self.push_file(text, f)
                    self.expand_input()
                while self.wrap:
                    blocks = self.wrap
                    self.wrap = []
                    self.stack = blocks
                    self.input_change = True
                    self.expand_input()
                self.cur_div = 0
                self.undivert_all()
                code = self.retcode
            except M4Exit as e:
                code = e.code
            except M4Fatal:
                code = 1
        finally:
            data = ''.join(self.out0).encode('latin-1', 'replace')
            try:
                sys.stdout.buffer.write(data)
                sys.stdout.buffer.flush()
            except Exception:
                code = 1
        return code

    # ------------------------------------------------------------------
    # builtin helpers

    def _init_builtins(self):
        B = self.builtins
        table = [
            # name, method, groks, blind
            ('__file__', self.b_file, False, False),
            ('__line__', self.b_line, False, False),
            ('__program__', self.b_program, False, False),
            ('builtin', self.b_builtin, True, True),
            ('changecom', self.b_changecom, False, False),
            ('changequote', self.b_changequote, False, False),
            ('debugfile', self.b_void, False, False),
            ('debugmode', self.b_void, False, False),
            ('decr', self.b_decr, False, True),
            ('define', self.b_define, True, True),
            ('defn', self.b_defn, False, True),
            ('divert', self.b_divert, False, False),
            ('divnum', self.b_divnum, False, False),
            ('dnl', self.b_dnl, False, False),
            ('dumpdef', self.b_void, False, False),
            ('errprint', self.b_errprint, False, True),
            ('esyscmd', self.b_void, False, True),
            ('eval', self.b_eval, False, True),
            ('format', self.b_format, False, True),
            ('ifdef', self.b_ifdef, False, True),
            ('ifelse', self.b_ifelse, False, True),
            ('include', self.b_include, False, True),
            ('incr', self.b_incr, False, True),
            ('index', self.b_index, False, True),
            ('indir', self.b_indir, True, True),
            ('len', self.b_len, False, True),
            ('m4exit', self.b_m4exit, False, False),
            ('m4wrap', self.b_m4wrap, False, True),
            ('maketemp', self.b_void, False, True),
            ('mkstemp', self.b_void, False, True),
            ('patsubst', self.b_patsubst, False, True),
            ('popdef', self.b_popdef, False, True),
            ('pushdef', self.b_pushdef, True, True),
            ('regexp', self.b_regexp, False, True),
            ('shift', self.b_shift, False, True),
            ('sinclude', self.b_sinclude, False, True),
            ('substr', self.b_substr, False, True),
            ('syscmd', self.b_void, False, True),
            ('sysval', self.b_sysval, False, False),
            ('traceoff', self.b_void, False, False),
            ('traceon', self.b_void, False, False),
            ('translit', self.b_translit, False, True),
            ('undefine', self.b_undefine, False, True),
            ('undivert', self.b_undivert, False, False),
        ]
        for name, fn, groks, blind in table:
            bi = Builtin(name, fn, groks, blind)
            B[name] = bi
            self.symtab[name] = [Def(None, bi)]
        self.symtab['__gnu__'] = [Def('')]
        self.symtab['__unix__'] = [Def('')]

    def bad_argc(self, argv, mn, mx):
        argc = len(argv)
        if mn > 0 and argc < mn:
            self.warn("Warning: too few arguments to builtin `%s'" % argv[0])
            return True
        if mx > 0 and argc > mx:
            self.warn("Warning: excess arguments to builtin `%s' ignored" % argv[0])
        return False

    @staticmethod
    def arg(argv, i):
        if i < len(argv):
            a = argv[i]
            if isinstance(a, str):
                return a
        return ''

    def numeric_arg(self, name, s):
        if s == '':
            self.warn("empty string treated as 0 in builtin `%s'" % name)
            return True, 0
        v, end = strtol(s)
        if end != len(s):
            self.warn("non-numeric argument to builtin `%s'" % name)
            return False, 0
        return True, w32(v)

    # ------------------------------------------------------------------
    # builtins

    def b_void(self, argv, out):
        pass

    def b_sysval(self, argv, out):
        out.append('0')

    def b_file(self, argv, out):
        self.bad_argc(argv, 1, 1)
        out.append(self.lquote + self.cur_file + self.rquote)

    def b_line(self, argv, out):
        self.bad_argc(argv, 1, 1)
        out.append(str(self.cur_line))

    def b_program(self, argv, out):
        self.bad_argc(argv, 1, 1)
        out.append(self.lquote + 'm4' + self.rquote)

    def _define(self, argv, push):
        if self.bad_argc(argv, 2, 3):
            return
        name = argv[1]
        if not isinstance(name, str):
            self.warn('Warning: %s: invalid macro name ignored' % argv[0])
            return
        if len(argv) == 2:
            self.define(name, Def(''), push)
            return
        val = argv[2]
        if isinstance(val, str):
            self.define(name, Def(val), push)
        else:
            self.define(name, Def(None, val), push)

    def b_define(self, argv, out):
        self._define(argv, False)

    def b_pushdef(self, argv, out):
        self._define(argv, True)

    def b_undefine(self, argv, out):
        if self.bad_argc(argv, 2, -1):
            return
        for a in argv[1:]:
            self.symtab.pop(a, None)

    def b_popdef(self, argv, out):
        if self.bad_argc(argv, 2, -1):
            return
        for a in argv[1:]:
            st = self.symtab.get(a)
            if st:
                st.pop()
                if not st:
                    del self.symtab[a]

    def b_defn(self, argv, out):
        if self.bad_argc(argv, 2, -1):
            return
        argc = len(argv)
        for a in argv[1:]:
            d = self.lookup(a)
            if d is None:
                continue
            if d.bi is None:
                out.append(self.lquote + d.text + self.rquote)
            elif argc != 2:
                self.warn("Warning: cannot concatenate builtin `%s'" % a)
            else:
                self.push_macro(d.bi)

    def b_indir(self, argv, out):
        if self.bad_argc(argv, 2, -1):
            return
        name = argv[1]
        if not isinstance(name, str):
            self.warn('Warning: indir: invalid macro name ignored')
            return
        d = self.lookup(name)
        if d is None:
            self.warn("undefined macro `%s'" % name)
            return
        args = list(argv[1:])
        if not (d.bi is not None and d.bi.groks):
            for i in range(1, len(args)):
                if not isinstance(args[i], str):
                    args[i] = ''
        self.call_macro(d, args, out)

    def b_builtin(self, argv, out):
        if self.bad_argc(argv, 2, -1):
            return
        name = argv[1]
        if not isinstance(name, str):
            self.warn('Warning: builtin: invalid macro name ignored')
            return
        bi = self.builtins.get(name)
        if bi is None:
            self.warn("undefined builtin `%s'" % name)
            return
        args = list(argv[1:])
        if not bi.groks:
            for i in range(1, len(args)):
                if not isinstance(args[i], str):
                    args[i] = ''
        bi.func(args, out)

    def b_ifdef(self, argv, out):
        if self.bad_argc(argv, 3, 4):
            return
        d = self.lookup(self.arg(argv, 1))
        if d is not None:
            out.append(self.arg(argv, 2))
        elif len(argv) >= 4:
            out.append(self.arg(argv, 3))

    def b_ifelse(self, argv, out):
        argc = len(argv)
        if argc == 2:
            return
        if self.bad_argc(argv, 4, -1):
            return
        if argc % 3 == 0:
            self.bad_argc(argv, 0, argc - 2)
        args = [a if isinstance(a, str) else '' for a in argv[1:]]
        n = len(args)
        i = 0
        while True:
            if args[i] == args[i + 1]:
                out.append(args[i + 2])
                return
            rem = n - i
            if rem == 3:
                return
            if rem in (4, 5):
                out.append(args[i + 3])
                return
            i += 3

    def b_shift(self, argv, out):
        if self.bad_argc(argv, 2, -1):
            return
        self.dump_args(out, argv[1:], ',', True)

    def b_changequote(self, argv, out):
        if self.bad_argc(argv, 1, 3):
            return
        argc = len(argv)
        lq = self.arg(argv, 1) if argc >= 2 else None
        rq = self.arg(argv, 2) if argc >= 3 else None
        if lq is None:
            lq, rq = '`', "'"
        elif rq is None or (lq and not rq):
            rq = "'"
        self.lquote = lq
        self.rquote = rq
        self._syntax_changed()

    def b_changecom(self, argv, out):
        if self.bad_argc(argv, 1, 3):
            return
        argc = len(argv)
        if argc == 1:
            bc, ec = '', ''
        else:
            bc = self.arg(argv, 1)
            ec = self.arg(argv, 2) if argc >= 3 else None
            if ec is None or (bc and not ec):
                ec = '\n'
        self.bcomm = bc
        self.ecomm = ec
        self._syntax_changed()

    def b_dnl(self, argv, out):
        self.bad_argc(argv, 1, 1)
        while True:
            c = self.next_char()
            if c is None:
                self.warn('Warning: end of file treated as newline')
                return
            if c == '\n':
                return

    def b_m4wrap(self, argv, out):
        if self.bad_argc(argv, 2, -1):
            return
        parts = []
        self.dump_args(parts, argv, ' ', False)
        self.wrap.append(Block(K_STR, ''.join(parts), self.cur_file, self.cur_line))

    def _include(self, argv, silent):
        if self.bad_argc(argv, 2, 2):
            return
        name = self.arg(argv, 1)
        text = self.read_file(name)
        if text is None:
            if not silent:
                self.warn("cannot open `%s': No such file or directory" % name)
                self.retcode = 1
            return
        self.push_file(text, name)

    def b_include(self, argv, out):
        self._include(argv, False)

    def b_sinclude(self, argv, out):
        self._include(argv, True)

    def b_divert(self, argv, out):
        if self.bad_argc(argv, 1, 2):
            return
        n = 0
        if len(argv) >= 2:
            ok, n = self.numeric_arg(argv[0], self.arg(argv, 1))
            if not ok:
                return
        self.cur_div = n

    def b_undivert(self, argv, out):
        if len(argv) == 1:
            self.undivert_all()
            return
        for i in range(1, len(argv)):
            a = self.arg(argv, i)
            v, end = strtol(a)
            if end == len(a) and not (a and a[0] in SPACES):
                self.insert_diversion(w32(v))
            else:
                text = self.read_file(a)
                if text is None:
                    self.warn("cannot undivert `%s': No such file or directory" % a)
                else:
                    self.output(text)

    def b_divnum(self, argv, out):
        self.bad_argc(argv, 1, 1)
        out.append(str(self.cur_div))

    def b_len(self, argv, out):
        if self.bad_argc(argv, 2, 2):
            return
        out.append(str(len(self.arg(argv, 1))))

    def b_index(self, argv, out):
        if self.bad_argc(argv, 3, 3):
            if len(argv) == 2:
                out.append('0')
            return
        out.append(str(self.arg(argv, 1).find(self.arg(argv, 2))))

    def b_substr(self, argv, out):
        if self.bad_argc(argv, 3, 4):
            if len(argv) == 2:
                out.append(self.arg(argv, 1))
            return
        s = self.arg(argv, 1)
        avail = len(s)
        length = avail
        ok, start = self.numeric_arg(argv[0], self.arg(argv, 2))
        if not ok:
            return
        if len(argv) >= 4:
            ok, length = self.numeric_arg(argv[0], self.arg(argv, 3))
            if not ok:
                return
        if start < 0 or length <= 0 or start >= avail:
            return
        if start + length > avail:
            length = avail - start
        out.append(s[start:start + length])

    @staticmethod
    def expand_ranges(s):
        res = []
        frm = None
        i = 0
        n = len(s)
        while i < n:
            c = s[i]
            if c == '-' and frm is not None:
                i += 1
                if i >= n:
                    res.append('-')
                    break
                to = s[i]
                a = ord(frm)
                b = ord(to)
                if a <= b:
                    for x in range(a + 1, b + 1):
                        res.append(chr(x))
                else:
                    for x in range(a - 1, b - 1, -1):
                        res.append(chr(x))
                frm = to
                i += 1
            else:
                res.append(c)
                frm = c
                i += 1
        return ''.join(res)

    def b_translit(self, argv, out):
        if self.bad_argc(argv, 3, 4):
            if len(argv) == 2:
                out.append(self.arg(argv, 1))
            return
        frm = self.arg(argv, 2)
        if '-' in frm:
            frm = self.expand_ranges(frm)
        if len(argv) >= 4:
            to = self.arg(argv, 3)
            if '-' in to:
                to = self.expand_ranges(to)
        else:
            to = ''
        mp = {}
        for i, c in enumerate(frm):
            if c not in mp:
                mp[c] = to[i] if i < len(to) else None
        res = []
        for c in self.arg(argv, 1):
            if c in mp:
                r = mp[c]
                if r is not None:
                    res.append(r)
            else:
                res.append(c)
        out.append(''.join(res))

    def b_incr(self, argv, out):
        if self.bad_argc(argv, 2, 2):
            return
        ok, v = self.numeric_arg(argv[0], self.arg(argv, 1))
        if ok:
            out.append(str(w32(v + 1)))

    def b_decr(self, argv, out):
        if self.bad_argc(argv, 2, 2):
            return
        ok, v = self.numeric_arg(argv[0], self.arg(argv, 1))
        if ok:
            out.append(str(w32(v - 1)))

    def b_errprint(self, argv, out):
        if self.bad_argc(argv, 2, -1):
            return
        parts = []
        self.dump_args(parts, argv, ' ', False)
        try:
            sys.stderr.write(''.join(parts))
            sys.stderr.flush()
        except Exception:
            pass

    def b_m4exit(self, argv, out):
        self.bad_argc(argv, 1, 2)
        code = 0
        if len(argv) >= 2:
            ok, code = self.numeric_arg(argv[0], self.arg(argv, 1))
            if not ok:
                code = 1
        if code < 0 or code > 255:
            self.warn('exit status out of range')
            code = 1
        if code == 0 and self.retcode != 0:
            code = self.retcode
        raise M4Exit(code)

    # ---- eval

    def b_eval(self, argv, out):
        if self.bad_argc(argv, 2, 4):
            return
        radix = 10
        a2 = self.arg(argv, 2)
        if a2:
            ok, radix = self.numeric_arg(argv[0], a2)
            if not ok:
                return
        if radix < 1 or radix > 36:
            self.warn("radix %d in builtin `%s' out of range" % (radix, argv[0]))
            return
        mn = 1
        if len(argv) >= 4:
            ok, mn = self.numeric_arg(argv[0], self.arg(argv, 3))
            if not ok:
                return
        if mn < 0:
            self.warn("negative width to builtin `%s'" % argv[0])
            return
        expr = self.arg(argv, 1)
        value = 0
        if not expr:
            self.warn("empty string treated as 0 in builtin `%s'" % argv[0])
        else:
            err, value = Evaluator(expr, self).evaluate()
            if err:
                msgs = {
                    1: 'divide by zero in eval: %s',
                    2: 'modulo by zero in eval: %s',
                    3: 'negative exponent in eval: %s',
                    4: 'bad expression in eval: %s',
                    5: 'bad expression in eval (missing right parenthesis): %s',
                    6: 'bad input in eval: %s',
                    7: 'excess input in eval: %s',
                    8: 'invalid operator in eval: %s',
                }
                self.warn(msgs[err] % expr)
                if err == 8:
                    self.retcode = 1
                return
        if radix == 1:
            res = []
            if value < 0:
                res.append('-')
                value = -value
            if mn - value > 0:
                res.append('0' * (mn - value))
            res.append('1' * value)
            out.append(''.join(res))
            return
        neg = value < 0
        v = -value if neg else value
        digs = '0123456789abcdefghijklmnopqrstuvwxyz'
        s = []
        while True:
            s.append(digs[v % radix])
            v //= radix
            if v == 0:
                break
        s = ''.join(reversed(s))
        if neg:
            out.append('-')
        if mn > len(s):
            out.append('0' * (mn - len(s)))
        out.append(s)

    # ---- format

    def b_format(self, argv, out):
        if self.bad_argc(argv, 2, -1):
            return
        fmt = self.arg(argv, 1)
        args = [a if isinstance(a, str) else '' for a in argv[2:]]
        state = [0]

        def next_arg():
            if state[0] < len(args):
                a = args[state[0]]
                state[0] += 1
                return a
            return None

        def arg_int(bits=32):
            a = next_arg()
            if a is None:
                return 0
            if a == '':
                self.warn('empty string treated as 0')
                return 0
            v, end = strtol(a)
            if end != len(a):
                self.warn('non-numeric argument %s' % a)
            return w32(v) if bits == 32 else v

        def arg_double():
            a = next_arg()
            if a is None:
                return 0.0
            if a == '':
                self.warn('empty string treated as 0')
                return 0.0
            v, end = strtod(a)
            if end != len(a):
                self.warn('non-numeric argument %s' % a)
            return v

        i = 0
        n = len(fmt)
        while True:
            j = fmt.find('%', i)
            if j < 0:
                out.append(fmt[i:])
                return
            out.append(fmt[i:j])
            i = j + 1
            if i < n and fmt[i] == '%':
                out.append('%')
                i += 1
                continue
            ok = set('aAcdeEfFgGiosuxX')
            flags = set()
            while i < n and fmt[i] in "'+ 0#-":
                c = fmt[i]
                if c == "'":
                    ok -= set('aAceEosxX')
                elif c == '+' or c == ' ':
                    ok -= set('cosuxX')
                elif c == '0':
                    ok -= set('cs')
                elif c == '#':
                    ok -= set('cdisu')
                flags.add(c)
                i += 1
            width = 0
            if i < n and fmt[i] == '*':
                width = arg_int()
                i += 1
            else:
                while i < n and fmt[i] in DIGITS:
                    width = width * 10 + ord(fmt[i]) - 48
                    i += 1
            prec = -1
            if i < n and fmt[i] == '.':
                ok.discard('c')
                i += 1
                if i < n and fmt[i] == '*':
                    prec = arg_int()
                    i += 1
                else:
                    prec = 0
                    while i < n and fmt[i] in DIGITS:
                        prec = prec * 10 + ord(fmt[i]) - 48
                        i += 1
            lmod = ''
            if i < n and fmt[i] == 'l':
                lmod = 'l'
                i += 1
                ok -= set('cs')
            elif i < n and fmt[i] == 'h':
                lmod = 'h'
                i += 1
                if i < n and fmt[i] == 'h':
                    lmod = 'hh'
                    i += 1
                ok -= set('aAceEfFgGs')
            if i < n:
                c = fmt[i]
                i += 1
            else:
                c = ''
            if c not in ok or c == '':
                self.warn("Warning: unrecognized specifier in `%s'" % fmt)
                continue
            if width < 0:
                flags.add('-')
                width = -width
            if prec < 0:
                prec = -1
            if c == 'c':
                v = arg_int()
                s = pad_str(chr(v & 0xFF), width, flags)
                k = s.find('\0')
                if k >= 0:
                    s = s[:k]
                out.append(s)
            elif c == 's':
                a = next_arg()
                if a is None:
                    a = ''
                if prec >= 0:
                    a = a[:prec]
                out.append(pad_str(a, width, flags))
            elif c in 'dioxXu':
                v = arg_int(64 if lmod == 'l' else 32)
                out.append(fmt_int(v, c, flags, width, prec, lmod))
            else:
                v = arg_double()
                out.append(fmt_float(v, c, flags, width, prec))

    # ---- regular expressions

    def compile_regex(self, pat):
        r = self._regex_cache.get(pat)
        if r is None:
            try:
                r = Regex(pat)
            except RegexError as e:
                self.warn("bad regular expression: `%s': %s" % (pat, e))
                return None
            self._regex_cache[pat] = r
        return r

    def substitute(self, out, victim, repl, m):
        i = 0
        n = len(repl)
        nsub = len(m) // 2 - 1
        while True:
            j = repl.find('\\', i)
            if j < 0:
                out.append(repl[i:])
                return
            out.append(repl[i:j])
            if j + 1 >= n:
                self.warn('Warning: trailing \\ ignored in replacement')
                return
            c = repl[j + 1]
            if c == '0' or c == '&':
                out.append(victim[m[0]:m[1]])
            elif c in '123456789':
                k = ord(c) - 48
                if k > nsub:
                    self.warn('Warning: sub-expression %d not present' % k)
                elif m[2 * k + 1] > 0 and m[2 * k] >= 0:
                    out.append(victim[m[2 * k]:m[2 * k + 1]])
            else:
                out.append(c)
            i = j + 2

    def b_regexp(self, argv, out):
        if self.bad_argc(argv, 3, 4):
            if len(argv) == 2:
                out.append('0')
            return
        victim = self.arg(argv, 1)
        rx = self.compile_regex(self.arg(argv, 2))
        if rx is None:
            return
        m = rx.search(victim, 0)
        if len(argv) == 3:
            out.append(str(m[0] if m else -1))
        elif m:
            self.substitute(out, victim, self.arg(argv, 3), m)

    def b_patsubst(self, argv, out):
        if self.bad_argc(argv, 3, 4):
            if len(argv) == 2:
                out.append(self.arg(argv, 1))
            return
        rx = self.compile_regex(self.arg(argv, 2))
        if rx is None:
            return
        victim = self.arg(argv, 1)
        repl = self.arg(argv, 3)
        length = len(victim)
        offset = 0
        res = []
        while offset <= length:
            m = rx.search(victim, offset)
            if not m:
                if offset < length:
                    res.append(victim[offset:])
                break
            if m[0] > offset:
                res.append(victim[offset:m[0]])
            self.substitute(res, victim, repl, m)
            offset = m[1]
            if m[0] == m[1]:
                if offset < length:
                    res.append(victim[offset])
                offset += 1
        out.append(''.join(res))


# ----------------------------------------------------------------------
# printf emulation

def pad_str(s, width, flags):
    if len(s) >= width:
        return s
    if '-' in flags:
        return s + ' ' * (width - len(s))
    return ' ' * (width - len(s)) + s


def fmt_int(v, conv, flags, width, prec, lmod):
    bits = {'': 32, 'l': 64, 'h': 16, 'hh': 8}[lmod]
    mask = (1 << bits) - 1
    if conv in 'di':
        v &= mask
        if v >= (1 << (bits - 1)):
            v -= (1 << bits)
    else:
        v &= mask
    neg = v < 0
    a = -v if neg else v
    if conv in 'diu':
        digits = str(a)
    elif conv == 'o':
        digits = '%o' % a
    elif conv == 'x':
        digits = '%x' % a
    else:
        digits = '%X' % a
    if prec >= 0:
        if prec == 0 and a == 0:
            digits = ''
        if len(digits) < prec:
            digits = '0' * (prec - len(digits)) + digits
    prefix = ''
    if conv in 'di':
        if neg:
            prefix = '-'
        elif '+' in flags:
            prefix = '+'
        elif ' ' in flags:
            prefix = ' '
    if '#' in flags:
        if conv == 'o' and not digits.startswith('0'):
            digits = '0' + digits
        elif conv in 'xX' and a != 0:
            prefix = '0' + conv
    total = len(prefix) + len(digits)
    if total >= width:
        return prefix + digits
    if '-' in flags:
        return prefix + digits + ' ' * (width - total)
    if '0' in flags and prec < 0:
        return prefix + '0' * (width - total) + digits
    return ' ' * (width - total) + prefix + digits


def _hexfloat(x, prec, upper, alt):
    """Format non-negative finite x like glibc %a (without sign)."""
    if x == 0.0:
        lead = 0
        frac = ''
        exp = 0
        if prec > 0:
            frac = '0' * prec
    else:
        h = float.hex(x)  # 0x1.xxxxp+e
        m = re.match(r'0x([01])\.?([0-9a-f]*)p([+-]\d+)', h)
        lead = int(m.group(1))
        frac = m.group(2)
        exp = int(m.group(3))
        frac = frac.ljust(13, '0')
        if prec < 0:
            frac = frac.rstrip('0')
        elif prec < 13:
            val = int(lead * (16 ** 13) + int(frac, 16))
            drop = 13 - prec
            q, r = divmod(val, 16 ** drop)
            half = 16 ** drop // 2
            if r > half or (r == half and (q & 1)):
                q += 1
            lead = q // (16 ** prec)
            fr = q % (16 ** prec)
            frac = ('%0*x' % (prec, fr)) if prec > 0 else ''
        else:
            frac = frac + '0' * (prec - 13)
    s = '0x%d' % lead
    if frac or alt:
        s += '.' + frac
    s += 'p%+d' % exp
    if upper:
        s = s.upper()
    return s


def fmt_float(v, conv, flags, width, prec):
    upper = conv in 'AEFG'
    neg = math.copysign(1.0, v) < 0
    if neg:
        sign = '-'
    elif '+' in flags:
        sign = '+'
    elif ' ' in flags:
        sign = ' '
    else:
        sign = ''
    if math.isinf(v) or math.isnan(v):
        body = 'inf' if math.isinf(v) else 'nan'
        if upper:
            body = body.upper()
        return pad_str(sign + body, width, flags)
    a = abs(v)
    if conv in 'aA':
        body = _hexfloat(a, prec, upper, '#' in flags)
        prefix = body[:2]
        rest = body[2:]
        total = len(sign) + len(body)
        if total >= width:
            return sign + body
        if '-' in flags:
            return sign + body + ' ' * (width - total)
        if '0' in flags:
            return sign + prefix + '0' * (width - total) + rest
        return ' ' * (width - total) + sign + body
    spec = '%' + ('#' if '#' in flags else '')
    if prec >= 0:
        spec += '.' + str(prec)
    spec += conv
    body = spec % a
    total = len(sign) + len(body)
    if total >= width:
        return sign + body
    if '-' in flags:
        return sign + body + ' ' * (width - total)
    if '0' in flags:
        return sign + '0' * (width - total) + body
    return ' ' * (width - total) + sign + body


# ----------------------------------------------------------------------
# eval

(EV_EOTEXT, EV_ERROR, EV_BADOP, EV_PLUS, EV_MINUS, EV_TIMES, EV_DIVIDE,
 EV_MODULO, EV_EXPONENT, EV_ASSIGN, EV_EQ, EV_NOTEQ, EV_GT, EV_GTEQ, EV_LS,
 EV_LSEQ, EV_LSHIFT, EV_RSHIFT, EV_LNOT, EV_NOT, EV_AND, EV_OR, EV_XOR,
 EV_LAND, EV_LOR, EV_LEFTP, EV_RIGHTP, EV_NUMBER) = range(28)

E_NO, E_DIV, E_MOD, E_NEGEXP, E_SYNTAX, E_MISSING, E_UNKNOWN, E_EXCESS, E_BADOP = range(9)


class _EvalErr(Exception):
    def __init__(self, code):
        Exception.__init__(self, code)
        self.code = code


def _cdiv(a, b):
    q = abs(a) // abs(b)
    return -q if (a < 0) != (b < 0) else q


class Evaluator(object):
    def __init__(self, text, m4):
        self.text = text
        self.pos = 0
        self.m4 = m4
        self.et = EV_EOTEXT
        self.val = 0

    def lex(self):
        t = self.text
        n = len(t)
        p = self.pos
        while p < n and t[p] in SPACES:
            p += 1
        if p >= n:
            self.pos = p
            self.et = EV_EOTEXT
            return
        c = t[p]
        if c in DIGITS:
            if c == '0':
                p += 1
                c2 = t[p] if p < n else ''
                if c2 in ('x', 'X'):
                    base = 16
                    p += 1
                elif c2 in ('b', 'B'):
                    base = 2
                    p += 1
                elif c2 in ('r', 'R'):
                    base = 0
                    p += 1
                    while p < n and t[p] in DIGITS and base <= 36:
                        base = 10 * base + ord(t[p]) - 48
                        p += 1
                    if base == 0 or base > 36 or p >= n or t[p] != ':':
                        self.pos = p
                        self.et = EV_ERROR
                        return
                    p += 1
                else:
                    base = 8
            else:
                base = 10
            val = 0
            while p < n:
                ch = t[p]
                if ch in DIGITS:
                    digit = ord(ch) - 48
                elif ch in LOWER:
                    digit = ord(ch) - 97 + 10
                elif ch in UPPER:
                    digit = ord(ch) - 65 + 10
                else:
                    break
                if base == 1:
                    if digit == 1:
                        val = w32(val + 1)
                    elif digit == 0 and val == 0:
                        p += 1
                        continue
                    else:
                        break
                elif digit >= base:
                    break
                else:
                    val = w32(val * base + digit)
                p += 1
            self.pos = p
            self.val = val
            self.et = EV_NUMBER
            return
        p += 1
        nx = t[p] if p < n else ''
        et = EV_ERROR
        if c == '+':
            et = EV_BADOP if nx in ('+', '=') and nx else EV_PLUS
        elif c == '-':
            et = EV_BADOP if nx in ('-', '=') and nx else EV_MINUS
        elif c == '*':
            if nx == '*':
                p += 1
                nx2 = t[p] if p < n else ''
                et = EV_BADOP if nx2 == '=' else EV_EXPONENT
            elif nx == '=':
                et = EV_BADOP
            else:
                et = EV_TIMES
        elif c == '/':
            et = EV_BADOP if nx == '=' else EV_DIVIDE
        elif c == '%':
            et = EV_BADOP if nx == '=' else EV_MODULO
        elif c == '=':
            if nx == '=':
                p += 1
                et = EV_EQ
            else:
                et = EV_ASSIGN
        elif c == '!':
            if nx == '=':
                p += 1
                et = EV_NOTEQ
            else:
                et = EV_LNOT
        elif c == '>':
            if nx == '=':
                p += 1
                et = EV_GTEQ
            elif nx == '>':
                p += 1
                nx2 = t[p] if p < n else ''
                et = EV_BADOP if nx2 == '=' else EV_RSHIFT
            else:
                et = EV_GT
        elif c == '<':
            if nx == '=':
                p += 1
                et = EV_LSEQ
            elif nx == '<':
                p += 1
                nx2 = t[p] if p < n else ''
                et = EV_BADOP if nx2 == '=' else EV_LSHIFT
            else:
                et = EV_LS
        elif c == '^':
            et = EV_BADOP if nx == '=' else EV_XOR
        elif c == '~':
            et = EV_NOT
        elif c == '&':
            if nx == '&':
                p += 1
                et = EV_LAND
            elif nx == '=':
                et = EV_BADOP
            else:
                et = EV_AND
        elif c == '|':
            if nx == '|':
                p += 1
                et = EV_LOR
            elif nx == '=':
                et = EV_BADOP
            else:
                et = EV_OR
        elif c == '(':
            et = EV_LEFTP
        elif c == ')':
            et = EV_RIGHTP
        self.pos = p
        self.et = et

    def lex_checked(self):
        self.lex()
        if self.et == EV_ERROR:
            raise _EvalErr(E_UNKNOWN)

    def evaluate(self):
        try:
            self.lex()
            v = self.logical_or()
            if self.et != EV_EOTEXT:
                if self.et == EV_BADOP:
                    return E_BADOP, 0
                return E_EXCESS, 0
            return E_NO, v
        except _EvalErr as e:
            return e.code, 0

    def logical_or(self):
        v1 = self.logical_and()
        while self.et == EV_LOR:
            self.lex_checked()
            try:
                v2 = self.logical_and()
                v1 = 1 if (v1 or v2) else 0
            except _EvalErr as e:
                if v1 != 0 and e.code < E_SYNTAX:
                    v1 = 1
                else:
                    raise
        return v1

    def logical_and(self):
        v1 = self.or_term()
        while self.et == EV_LAND:
            self.lex_checked()
            try:
                v2 = self.or_term()
                v1 = 1 if (v1 and v2) else 0
            except _EvalErr as e:
                if v1 == 0 and e.code < E_SYNTAX:
                    v1 = 0
                else:
                    raise
        return v1

    def or_term(self):
        v1 = self.xor_term()
        while self.et == EV_OR:
            self.lex_checked()
            v1 = w32(v1 | self.xor_term())
        return v1

    def xor_term(self):
        v1 = self.and_term()
        while self.et == EV_XOR:
            self.lex_checked()
            v1 = w32(v1 ^ self.and_term())
        return v1

    def and_term(self):
        v1 = self.equality_term()
        while self.et == EV_AND:
            self.lex_checked()
            v1 = w32(v1 & self.equality_term())
        return v1

    def equality_term(self):
        v1 = self.cmp_term()
        while self.et in (EV_EQ, EV_NOTEQ, EV_ASSIGN):
            op = self.et
            if op == EV_ASSIGN:
                self.m4.warn('Warning: recommend ==, not =, for equality operator')
            self.lex_checked()
            v2 = self.cmp_term()
            if op == EV_NOTEQ:
                v1 = 1 if v1 != v2 else 0
            else:
                v1 = 1 if v1 == v2 else 0
        return v1

    def cmp_term(self):
        v1 = self.shift_term()
        while self.et in (EV_GT, EV_GTEQ, EV_LS, EV_LSEQ):
            op = self.et
            self.lex_checked()
            v2 = self.shift_term()
            if op == EV_GT:
                v1 = int(v1 > v2)
            elif op == EV_GTEQ:
                v1 = int(v1 >= v2)
            elif op == EV_LS:
                v1 = int(v1 < v2)
            else:
                v1 = int(v1 <= v2)
        return v1

    def shift_term(self):
        v1 = self.add_term()
        while self.et in (EV_LSHIFT, EV_RSHIFT):
            op = self.et
            self.lex_checked()
            v2 = self.add_term()
            sh = v2 & 0x1F
            if op == EV_LSHIFT:
                v1 = w32(v1 << sh)
            else:
                v1 = v1 >> sh
        return v1

    def add_term(self):
        v1 = self.mult_term()
        while self.et in (EV_PLUS, EV_MINUS):
            op = self.et
            self.lex_checked()
            v2 = self.mult_term()
            v1 = w32(v1 + v2 if op == EV_PLUS else v1 - v2)
        return v1

    def mult_term(self):
        v1 = self.exp_term()
        while self.et in (EV_TIMES, EV_DIVIDE, EV_MODULO):
            op = self.et
            self.lex_checked()
            v2 = self.exp_term()
            if op == EV_TIMES:
                v1 = w32(v1 * v2)
            elif op == EV_DIVIDE:
                if v2 == 0:
                    raise _EvalErr(E_DIV)
                if v2 == -1:
                    v1 = w32(-v1)
                else:
                    v1 = w32(_cdiv(v1, v2))
            else:
                if v2 == 0:
                    raise _EvalErr(E_MOD)
                if v2 == -1:
                    v1 = 0
                else:
                    v1 = w32(v1 - v2 * _cdiv(v1, v2))
        return v1

    def exp_term(self):
        v1 = self.unary_term()
        while self.et == EV_EXPONENT:
            self.lex_checked()
            v2 = self.exp_term()
            if v2 < 0:
                raise _EvalErr(E_NEGEXP)
            if v1 == 0 and v2 == 0:
                raise _EvalErr(E_DIV)
            v1 = w32(pow(v1, v2, 1 << 32))
        return v1

    def unary_term(self):
        op = self.et
        if op in (EV_PLUS, EV_MINUS, EV_NOT, EV_LNOT):
            self.lex_checked()
            v1 = self.unary_term()
            if op == EV_MINUS:
                v1 = w32(-v1)
            elif op == EV_NOT:
                v1 = w32(~v1)
            elif op == EV_LNOT:
                v1 = 1 if v1 == 0 else 0
            return v1
        return self.simple_term()

    def simple_term(self):
        et = self.et
        if et == EV_LEFTP:
            self.lex_checked()
            v1 = self.logical_or()
            if self.et == EV_ERROR:
                raise _EvalErr(E_UNKNOWN)
            if self.et != EV_RIGHTP:
                raise _EvalErr(E_MISSING)
        elif et == EV_NUMBER:
            v1 = self.val
        elif et == EV_BADOP:
            raise _EvalErr(E_BADOP)
        elif et == EV_ERROR:
            raise _EvalErr(E_UNKNOWN)
        else:
            raise _EvalErr(E_SYNTAX)
        self.lex()
        return v1


# ----------------------------------------------------------------------
# GNU (Emacs syntax) regular expressions with POSIX leftmost-longest matching

class RegexError(Exception):
    pass


_CLASSES = {
    'alpha': ALPHA,
    'upper': UPPER,
    'lower': LOWER,
    'digit': DIGITS,
    'xdigit': DIGITS + 'abcdefABCDEF',
    'alnum': ALPHA + DIGITS,
    'space': SPACES,
    'blank': ' \t',
    'punct': ''.join(chr(c) for c in range(33, 127) if not chr(c).isalnum()),
    'print': ''.join(chr(c) for c in range(32, 127)),
    'graph': ''.join(chr(c) for c in range(33, 127)),
    'cntrl': ''.join(chr(c) for c in range(0, 32)) + chr(127),
}
_WORDSET = frozenset(ALPHA + DIGITS + '_')
_ALLCHARS = frozenset(chr(c) for c in range(256))


class _RegexParser(object):
    def __init__(self, pat):
        self.p = pat
        self.i = 0
        self.ngroups = 0
        self.completed = set()

    def at(self, s):
        return self.p.startswith(s, self.i)

    def parse(self):
        node = self.parse_alt()
        if self.i < len(self.p):
            raise RegexError('Unmatched ) or \\)')
        return node

    def parse_alt(self):
        branches = [self.parse_branch()]
        while self.at('\\|'):
            self.i += 2
            branches.append(self.parse_branch())
        if len(branches) == 1:
            return branches[0]
        return ('alt', branches)

    def parse_branch(self):
        items = []
        start_i = self.i
        expr_start = True
        p = self.p
        n = len(p)
        while self.i < n and not self.at('\\|') and not self.at('\\)'):
            atom, is_anchor = self.parse_atom(start_i, expr_start)
            if is_anchor:
                items.append(atom)
                expr_start = True
                continue
            expr_start = False
            while self.i < n:
                c = p[self.i]
                if c == '*':
                    self.i += 1
                    atom = ('rep', atom, 0, None)
                elif c == '+':
                    self.i += 1
                    atom = ('rep', atom, 1, None)
                elif c == '?':
                    self.i += 1
                    atom = ('rep', atom, 0, 1)
                elif self.at('\\{'):
                    self.i += 2
                    mn, mx = self.parse_interval()
                    atom = ('rep', atom, mn, mx)
                else:
                    break
            items.append(atom)
        if len(items) == 1:
            return items[0]
        return ('cat', items)

    def parse_interval(self):
        p = self.p
        n = len(p)
        j = self.i
        while j < n and p[j] in DIGITS:
            j += 1
        mn = int(p[self.i:j]) if j > self.i else None
        self.i = j
        if self.i < n and p[self.i] == ',':
            self.i += 1
            j = self.i
            while j < n and p[j] in DIGITS:
                j += 1
            mx = int(p[self.i:j]) if j > self.i else None
            self.i = j
            if mn is None:
                mn = 0
        else:
            if mn is None:
                raise RegexError('Invalid content of \\{\\}')
            mx = mn
        if not self.at('\\}'):
            raise RegexError('Unmatched \\{')
        self.i += 2
        if mx is not None and mx < mn:
            raise RegexError('Invalid content of \\{\\}')
        if mn > 32767 or (mx is not None and mx > 32767):
            raise RegexError('Regular expression too big')
        return mn, mx

    def parse_atom(self, branch_start, expr_start):
        p = self.p
        n = len(p)
        c = p[self.i]
        if c == '\\':
            if self.i + 1 >= n:
                raise RegexError('Trailing backslash')
            d = p[self.i + 1]
            self.i += 2
            if d == '(':
                self.ngroups += 1
                g = self.ngroups
                inner = self.parse_alt()
                if not self.at('\\)'):
                    raise RegexError('Unmatched ( or \\(')
                self.i += 2
                self.completed.add(g)
                return ('group', g, inner), False
            if d in '123456789':
                k = ord(d) - 48
                if k not in self.completed:
                    raise RegexError('Invalid back reference')
                return ('backref', k), False
            if d == '<':
                return ('wstart',), True
            if d == '>':
                return ('wend',), True
            if d == 'b':
                return ('wbound',), True
            if d == 'B':
                return ('nwbound',), True
            if d == '`':
                return ('bufstart',), True
            if d == "'":
                return ('bufend',), True
            if d == 'w':
                return ('set', _WORDSET), False
            if d == 'W':
                return ('set', _ALLCHARS - _WORDSET), False
            if d == 's':
                return ('set', frozenset(SPACES)), False
            if d == 'S':
                return ('set', _ALLCHARS - frozenset(SPACES)), False
            return ('char', d), False
        if c == '[':
            self.i += 1
            return self.parse_bracket(), False
        if c == '.':
            self.i += 1
            return ('set', _ALLCHARS - frozenset('\n')), False
        if c == '^':
            q = self.i
            self.i += 1
            if q == 0 or (q >= 2 and p[q - 2:q] in ('\\(', '\\|')):
                return ('bol',), True
            return ('char', '^'), False
        if c == '$':
            self.i += 1
            if self.i >= n or self.at('\\)') or self.at('\\|'):
                return ('eol',), True
            return ('char', '$'), False
        self.i += 1
        return ('char', c), False

    def parse_bracket(self):
        p = self.p
        n = len(p)
        neg = False
        chars = set()
        if self.i < n and p[self.i] == '^':
            neg = True
            self.i += 1
        first = True
        while True:
            if self.i >= n:
                raise RegexError('Unmatched [, [^, [:, [., or [=')
            c = p[self.i]
            if c == ']' and not first:
                self.i += 1
                break
            first = False
            start = None
            if c == '[' and self.i + 1 < n and p[self.i + 1] in ':=.':
                kind = p[self.i + 1]
                end = p.find(kind + ']', self.i + 2)
                if end < 0:
                    raise RegexError('Unmatched [, [^, [:, [., or [=')
                name = p[self.i + 2:end]
                self.i = end + 2
                if kind == ':':
                    if name not in _CLASSES:
                        raise RegexError('Invalid character class name')
                    chars.update(_CLASSES[name])
                    continue
                if len(name) != 1:
                    raise RegexError('Invalid collation character')
                start = name
            else:
                start = c
                self.i += 1
            if self.i + 1 < n and p[self.i] == '-' and p[self.i + 1] != ']':
                self.i += 1
                e = p[self.i]
                if e == '[' and self.i + 1 < n and p[self.i + 1] in '.=':
                    kind = p[self.i + 1]
                    end = p.find(kind + ']', self.i + 2)
                    if end < 0:
                        raise RegexError('Unmatched [, [^, [:, [., or [=')
                    e = p[self.i + 2:end]
                    if len(e) != 1:
                        raise RegexError('Invalid collation character')
                    self.i = end + 2
                else:
                    self.i += 1
                for x in range(ord(start), ord(e) + 1):
                    chars.add(chr(x))
            else:
                chars.add(start)
        fs = frozenset(chars)
        if neg:
            fs = _ALLCHARS - fs
        return ('set', fs)


class Regex(object):
    def __init__(self, pat):
        parser = _RegexParser(pat)
        tree = parser.parse()
        self.ngroups = parser.ngroups
        self.matcher = self._compile(tree)

    def _compile(self, node):
        kind = node[0]
        if kind == 'char':
            ch = node[1]

            def f(s, i, caps, k):
                return i < len(s) and s[i] == ch and k(i + 1, caps)
            return f
        if kind == 'set':
            st = node[1]

            def f(s, i, caps, k):
                return i < len(s) and s[i] in st and k(i + 1, caps)
            return f
        if kind == 'cat':
            fs = [self._compile(x) for x in node[1]]

            def build(idx):
                if idx == len(fs):
                    return lambda s, i, caps, k: k(i, caps)
                first = fs[idx]
                rest = build(idx + 1)

                def f(s, i, caps, k):
                    return first(s, i, caps, lambda j, c: rest(s, j, c, k))
                return f
            return build(0)
        if kind == 'alt':
            fs = [self._compile(x) for x in node[1]]

            def f(s, i, caps, k):
                for g in fs:
                    if g(s, i, caps, k):
                        return True
                return False
            return f
        if kind == 'group':
            g = node[1]
            inner = self._compile(node[2])

            def f(s, i, caps, k):
                def k2(j, c):
                    c2 = list(c)
                    c2[2 * g] = i
                    c2[2 * g + 1] = j
                    return k(j, tuple(c2))
                return inner(s, i, caps, k2)
            return f
        if kind == 'rep':
            inner = self._compile(node[1])
            mn = node[2]
            mx = node[3]

            def rep(s, i, caps, k, count):
                if mx is None or count < mx:
                    def k2(j, c):
                        if j == i and count >= mn:
                            return False
                        return rep(s, j, c, k, count + 1)
                    if inner(s, i, caps, k2):
                        return True
                if count >= mn:
                    return k(i, caps)
                return False

            def f(s, i, caps, k):
                return rep(s, i, caps, k, 0)
            return f
        if kind == 'backref':
            g = node[1]

            def f(s, i, caps, k):
                a = caps[2 * g]
                b = caps[2 * g + 1]
                if a < 0 or b < 0:
                    return False
                sub = s[a:b]
                if s.startswith(sub, i):
                    return k(i + len(sub), caps)
                return False
            return f

        def isw(s, i):
            return 0 <= i < len(s) and s[i] in _WORDSET
        if kind == 'bol':
            return lambda s, i, caps, k: (i == 0 or s[i - 1] == '\n') and k(i, caps)
        if kind == 'eol':
            return lambda s, i, caps, k: (i == len(s) or s[i] == '\n') and k(i, caps)
        if kind == 'bufstart':
            return lambda s, i, caps, k: i == 0 and k(i, caps)
        if kind == 'bufend':
            return lambda s, i, caps, k: i == len(s) and k(i, caps)
        if kind == 'wstart':
            return lambda s, i, caps, k: (isw(s, i) and not isw(s, i - 1)) and k(i, caps)
        if kind == 'wend':
            return lambda s, i, caps, k: (isw(s, i - 1) and not isw(s, i)) and k(i, caps)
        if kind == 'wbound':
            return lambda s, i, caps, k: (isw(s, i - 1) != isw(s, i)) and k(i, caps)
        if kind == 'nwbound':
            return lambda s, i, caps, k: (isw(s, i - 1) == isw(s, i)) and k(i, caps)
        raise RegexError('internal error')

    def search(self, s, start):
        """Return a flat list [start0, end0, start1, end1, ...] or None."""
        n = len(s)
        init = tuple([-1] * (2 * (self.ngroups + 1)))
        best = [None, None]
        matcher = self.matcher
        for pos in range(start, n + 1):
            best[0] = -1

            def final(j, caps):
                if j > best[0]:
                    best[0] = j
                    best[1] = caps
                return j == n
            matcher(s, pos, init, final)
            if best[0] >= 0:
                res = list(best[1])
                res[0] = pos
                res[1] = best[0]
                return res
        return None


def main(argv):
    return M4().run(argv)


def _thread_main(argv, result):
    try:
        result.append(main(argv))
    except BaseException:
        import traceback
        traceback.print_exc()
        result.append(1)


if __name__ == "__main__":
    sys.setrecursionlimit(2000000)
    threading.stack_size(1024 * 1024 * 1024)
    res = []
    t = threading.Thread(target=_thread_main, args=(sys.argv[1:], res))
    t.start()
    t.join()
    try:
        sys.stdout.flush()
    except Exception:
        pass
    os._exit(res[0] if res else 1)
