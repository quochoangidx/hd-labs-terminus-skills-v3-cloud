#!/usr/bin/env python3
"""Small, pure Python replacement for the tested GNU grep 3.8 interface."""
import os
import re
import sys


def err(s):
    sys.stderr.write("grep: " + s + "\n")


class Opt:
    def __init__(self):
        self.engine = None
        self.patterns = []
        self.ignore = False
        self.invert = False
        self.word = False
        self.line = False
        self.mode = 'normal'       # resolved after parsing
        self.want_count = False
        self.file_mode = None
        self.want_quiet = False
        self.pattern_source = False
        self.max_count = None
        self.only = False
        self.silent_errors = False
        self.byteoff = False
        self.with_name = None
        self.label = '(standard input)'
        self.lineno = False
        self.initial_tab = False
        self.null_name = False
        self.zero = False
        self.before = 0
        self.after = 0
        self.before_set = self.after_set = False
        self.context_seen = False
        self.group_sep = b'--'
        self.binary = 'binary'


def number(s):
    try:
        n = int(s, 10)
        if n < 0: raise ValueError
        return n
    except ValueError:
        raise RuntimeError("invalid context length argument")


def parse(argv):
    o = Opt(); operands = []; i = 0; end = False
    def engine(x):
        if o.engine is not None and o.engine != x:
            raise RuntimeError("conflicting matchers specified")
        o.engine = x
    def context_both(v):
        n = number(v); o.context_seen = True
        if not o.before_set: o.before = n
        if not o.after_set: o.after = n
    def longopt(a, following):
        nonlocal i
        if '=' in a: name, val = a[2:].split('=', 1)
        else: name, val = a[2:], None
        takes = {'regexp','file','max-count','label','after-context','before-context','context','group-separator','binary-files'}
        if name in takes and val is None:
            if following is None: raise RuntimeError("option '--%s' requires an argument" % name)
            i += 1; val = following
        if name == 'basic-regexp': engine('bre')
        elif name == 'extended-regexp': engine('ere')
        elif name == 'fixed-strings': engine('fixed')
        elif name == 'regexp': o.pattern_source = True; o.patterns.extend(split_arg(val))
        elif name == 'file': load_patterns(o, val)
        elif name == 'ignore-case': o.ignore = True
        elif name == 'no-ignore-case': o.ignore = False
        elif name == 'invert-match': o.invert = True
        elif name == 'word-regexp': o.word = True
        elif name == 'line-regexp': o.line = True
        elif name == 'count': o.want_count = True
        elif name == 'files-with-matches': o.file_mode = 'files'
        elif name == 'files-without-match': o.file_mode = 'files_without'
        elif name in ('quiet','silent'): o.want_quiet = True
        elif name == 'max-count': o.max_count = number(val)
        elif name == 'only-matching': o.only = True
        elif name == 'no-messages': o.silent_errors = True
        elif name == 'byte-offset': o.byteoff = True
        elif name == 'with-filename': o.with_name = True
        elif name == 'no-filename': o.with_name = False
        elif name == 'label': o.label = val
        elif name == 'line-number': o.lineno = True
        elif name == 'initial-tab': o.initial_tab = True
        elif name == 'null': o.null_name = True
        elif name == 'null-data': o.zero = True
        elif name == 'after-context': o.after = number(val); o.after_set = True; o.context_seen = True
        elif name == 'before-context': o.before = number(val); o.before_set = True; o.context_seen = True
        elif name == 'context': context_both(val)
        elif name == 'group-separator': o.group_sep = val.encode('latin1', 'surrogateescape')
        elif name == 'no-group-separator': o.group_sep = None
        elif name == 'text': o.binary = 'text'
        elif name == 'binary-files':
            if val not in ('binary','text','without-match'): raise RuntimeError("unknown binary-files type")
            o.binary = val
        elif name == 'version':
            sys.stdout.write('grep (GNU grep) 3.8\n'); raise SystemExit(0)
        elif name == 'help':
            sys.stdout.write('Usage: grep [OPTION]... PATTERNS [FILE]...\n'); raise SystemExit(0)
        else: raise RuntimeError("unrecognized option '--%s'" % name)
    while i < len(argv):
        a = argv[i]
        if end or not a.startswith('-') or a == '-': operands.append(a); i += 1; continue
        if a == '--': end = True; i += 1; continue
        if a.startswith('--'):
            longopt(a, argv[i+1] if i+1 < len(argv) else None); i += 1; continue
        if len(a) > 1 and a[1:].isdigit(): context_both(a[1:]); i += 1; continue
        j = 1
        while j < len(a):
            c = a[j]
            if c in 'GEF': engine({'G':'bre','E':'ere','F':'fixed'}[c]); j += 1
            elif c in 'ivwxconbsTHhZzqalsIL':
                if c == 'i': o.ignore = True
                elif c == 'v': o.invert = True
                elif c == 'w': o.word = True
                elif c == 'x': o.line = True
                elif c == 'c': o.want_count = True
                elif c == 'o': o.only = True
                elif c == 'n': o.lineno = True
                elif c == 'b': o.byteoff = True
                elif c == 's': o.silent_errors = True
                elif c == 'T': o.initial_tab = True
                elif c == 'H': o.with_name = True
                elif c == 'h': o.with_name = False
                elif c == 'Z': o.null_name = True
                elif c == 'z': o.zero = True
                elif c == 'q': o.want_quiet = True
                elif c == 'a': o.binary = 'text'
                elif c == 'I': o.binary = 'without-match'
                elif c == 'l': o.file_mode = 'files'
                elif c == 'L': o.file_mode = 'files_without'
                j += 1
            elif c in 'efmABC':
                val = a[j+1:]
                if not val:
                    i += 1
                    if i >= len(argv): raise RuntimeError("option requires an argument -- '%s'" % c)
                    val = argv[i]
                if c == 'e': o.pattern_source = True; o.patterns.extend(split_arg(val))
                elif c == 'f': o.pattern_source = True; load_patterns(o, val)
                elif c == 'm': o.max_count = number(val)
                elif c == 'A': o.after = number(val); o.after_set = True; o.context_seen = True
                elif c == 'B': o.before = number(val); o.before_set = True; o.context_seen = True
                else: context_both(val)
                j = len(a)
            else: raise RuntimeError("invalid option -- '%s'" % c)
        i += 1
    if not o.pattern_source:
        if not operands: raise RuntimeError("no pattern supplied")
        o.pattern_source = True
        o.patterns.extend(split_arg(operands.pop(0)))
    if o.want_quiet: o.mode = 'quiet'
    elif o.file_mode is not None: o.mode = o.file_mode
    elif o.want_count: o.mode = 'count'
    if o.engine is None: o.engine = 'bre'
    return o, operands


def split_arg(s):
    return [x.encode('latin1', 'surrogateescape') for x in s.split('\n')]


def load_patterns(o, fn):
    try:
        data = sys.stdin.buffer.read() if fn == '-' else open(fn, 'rb').read()
    except OSError as e: raise RuntimeError('%s: %s' % (fn, e.strerror))
    if not data:
        return
    parts = data.split(b'\n')
    if data.endswith(b'\n'): parts.pop()
    o.patterns.extend(parts)


POSIX_CLASSES = {
    'alnum':'A-Za-z0-9','alpha':'A-Za-z','blank':' \\t','cntrl':'\\x00-\\x1f\\x7f',
    'digit':'0-9','graph':'!-~','lower':'a-z','print':' -~','punct':'!-/:-@[-`{-~',
    'space':'\\t-\\r ','upper':'A-Z','xdigit':'A-Fa-f0-9','word':'A-Za-z0-9_'
}

def classes(s):
    # Replace POSIX named classes while preserving their surrounding bracket expression.
    return re.sub(r'\[:(alnum|alpha|blank|cntrl|digit|graph|lower|print|punct|space|upper|xdigit|word):\]',
                  lambda m: POSIX_CLASSES[m.group(1)], s)


def bre_to_py(s):
    out=[]; i=0; inclass=False
    while i < len(s):
        c=s[i]
        if c == '[': inclass=True; out.append(c); i+=1; continue
        if c == ']' and inclass: inclass=False; out.append(c); i+=1; continue
        if c == '\\' and i+1 < len(s):
            d=s[i+1]
            if not inclass and d in '(){}+?|': out.append(d)
            elif not inclass and d in '123456789': out.append('\\'+d)
            elif not inclass and d == '<': out.append(r'(?<![A-Za-z0-9_])(?=[A-Za-z0-9_])')
            elif not inclass and d == '>': out.append(r'(?<=[A-Za-z0-9_])(?![A-Za-z0-9_])')
            elif not inclass and d in 'bB': out.append('\\'+d)
            elif d == 's': out.append(r'[\t-\r ]')
            elif d == 'S': out.append(r'[^\t-\r ]')
            elif d == 'w': out.append(r'[A-Za-z0-9_]')
            elif d == 'W': out.append(r'[^A-Za-z0-9_]')
            else: out.append(re.escape(d))
            i+=2; continue
        if not inclass and c in '()+?|{}': out.append('\\'+c)
        else: out.append(c)
        i+=1
    return classes(''.join(out))


def ere_to_py(s):
    # Python ERE syntax is close; convert GNU special boundary escapes.
    out=[]; i=0; incl=False
    while i < len(s):
        c=s[i]
        if c == '[': incl=True
        elif c == ']' and incl: incl=False
        if c == '\\' and i+1 < len(s):
            d=s[i+1]
            if not incl and d == '<': out.append(r'(?<![A-Za-z0-9_])(?=[A-Za-z0-9_])')
            elif not incl and d == '>': out.append(r'(?<=[A-Za-z0-9_])(?![A-Za-z0-9_])')
            elif not incl and d == 's': out.append(r'[\t-\r ]')
            elif not incl and d == 'S': out.append(r'[^\t-\r ]')
            else: out.append(c+d)
            i += 2; continue
        out.append(c); i += 1
    return classes(''.join(out))


def absolute_anchors(s):
    """Make grep's record anchors independent of Python regex endpos."""
    out=[]; incl=False; i=0
    while i < len(s):
        c=s[i]
        if c == '\\' and i+1 < len(s):
            out.append(s[i:i+2]); i += 2; continue
        if c == '[': incl=True
        elif c == ']' and incl: incl=False
        if not incl and c == '^': out.append(r'\A')
        elif not incl and c == '$': out.append(r'\Z')
        else: out.append(c)
        i += 1
    return ''.join(out)


ASCII_FOLD = str.maketrans('ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz')


class Matcher:
    def __init__(self, o):
        self.o=o; self.fixed=[]; self.rx=[]; self.sources=[]; self.validators={}
        self.flags=re.ASCII | re.DOTALL | (re.IGNORECASE if o.ignore else 0)
        flags=self.flags
        for p in o.patterns:
            s=p.decode('latin1')
            if o.engine == 'fixed': self.fixed.append(s.translate(ASCII_FOLD) if o.ignore else s)
            else:
                q=bre_to_py(s) if o.engine == 'bre' else ere_to_py(s)
                q=absolute_anchors(q)
                try:
                    self.rx.append(re.compile(q, flags)); self.sources.append(q)
                except re.error as e: raise RuntimeError(str(e))
    @staticmethod
    def wordchar(c): return c is not None and (c == '_' or c.isascii() and c.isalnum())
    def bounds(self, s, a, b):
        if self.o.line and (a != 0 or b != len(s)): return False
        if self.o.word and not self.o.line:
            if a and self.wordchar(s[a-1]): return False
            if b < len(s) and self.wordchar(s[b]): return False
        return True
    def spans(self, raw):
        s=raw.decode('latin1'); cmp=s.translate(ASCII_FOLD) if self.o.ignore else s
        found=[]
        if self.o.engine == 'fixed':
            for p in self.fixed:
                if p == '':
                    for a in range(len(s)+1):
                        if self.bounds(s,a,a): found.append((a,a))
                else:
                    a=cmp.find(p)
                    while a >= 0:
                        b=a+len(p)
                        if self.bounds(s,a,b): found.append((a,b))
                        a=cmp.find(p,a+1)
        else:
            # Test each start/end pair. fullmatch gives POSIX alternative independence;
            # choosing max end below supplies leftmost-longest across all patterns.
            for a in range(len(s)+1):
                for ri,rx in enumerate(self.rx):
                    if rx.match(s,a) is None: continue
                    for b in range(len(s), a-1, -1):
                        if not self.bounds(s,a,b): continue
                        rem=len(s)-b; key=(ri,rem)
                        vrx=self.validators.get(key)
                        if vrx is None:
                            tail=r'(?=(?:[\s\S]{%d})\Z)' % rem
                            vrx=re.compile('(?:'+self.sources[ri]+')'+tail,self.flags)
                            self.validators[key]=vrx
                        if vrx.match(s,a) is not None:
                            found.append((a,b)); break
        return found
    def selected(self, raw): return bool(self.spans(raw)) != self.o.invert
    def nonoverlap(self, raw):
        spans=self.spans(raw); out=[]; pos=0; n=len(raw)
        while True:
            cand=[x for x in spans if x[0] >= pos and x[1] > x[0]]
            if not cand: break
            a=min(x[0] for x in cand); b=max(x[1] for x in cand if x[0]==a)
            out.append((a,b)); pos=b
            if pos > n: break
        return out


def records(data, zero, binary):
    if not data: return []
    sep=b'\0' if zero else b'\n'
    if binary and not zero:
        # In binary mode NUL is also a record terminator.
        chunks=[]; starts=[]; st=0
        for i,c in enumerate(data):
            if c in (0,10): chunks.append(data[st:i]); starts.append(st); st=i+1
        if st < len(data): chunks.append(data[st:]); starts.append(st)
        return list(zip(chunks,starts))
    parts=data.split(sep); out=[]; off=0
    for k,p in enumerate(parts):
        if k == len(parts)-1 and p == b'' and data.endswith(sep): break
        out.append((p,off)); off += len(p)+1
    return out


def namebytes(name): return name.encode('latin1','surrogateescape')

def prefix(o, shown_name, many, line, off, context=False):
    fields=[]
    if o.with_name is True or (o.with_name is None and many): fields.append(namebytes(shown_name))
    if o.lineno: fields.append(str(line).encode())
    if o.byteoff: fields.append(str(off).encode())
    if not fields: return b''
    delim=b'-' if context else b':'
    if o.null_name and fields and (o.with_name is True or (o.with_name is None and many)):
        first=fields[0]+b'\0'; rest=fields[1:]
        p=first + (delim.join(rest)+delim if rest else b'')
    else: p=delim.join(fields)+delim
    if o.initial_tab:
        # GNU aligns numeric prefixes to a tab stop by placing a tab before content.
        p += b'\t'
    return p


def main(argv):
    try: o, files=parse(argv); matcher=Matcher(o)
    except SystemExit as e: return int(e.code or 0)
    except RuntimeError as e: err(str(e)); return 2
    if not files: files=['-']
    many=len(files)>1
    had_error=False; any_selected=False; output=bytearray(); groups_emitted=False
    term=b'\0' if o.zero else b'\n'
    for fn in files:
        shown=o.label if fn=='-' else fn
        try: data=sys.stdin.buffer.read() if fn=='-' else open(fn,'rb').read()
        except OSError as e:
            had_error=True
            if not o.silent_errors: err('%s: %s' % (fn,e.strerror))
            continue
        isbin=(b'\0' in data and not o.zero and o.binary!='text')
        recs=records(data,o.zero,isbin)
        sels=[]
        if not (isbin and o.binary=='without-match') and o.max_count != 0:
            for idx,(raw,off) in enumerate(recs):
                if matcher.selected(raw):
                    sels.append(idx)
                    if o.max_count is not None and len(sels)>=o.max_count: break
                    if isbin and o.binary=='binary' and o.mode!='count': break
                    if o.mode in ('quiet','files'): break
        count=len(sels); matched=count>0; any_selected |= matched
        if o.mode=='quiet' and matched:
            sys.stdout.buffer.write(output); return 0
        if o.mode=='files':
            if matched: output += namebytes(shown)+(b'\0' if o.null_name else b'\n')
            continue
        if o.mode=='files_without':
            if not matched: output += namebytes(shown)+(b'\0' if o.null_name else b'\n')
            continue
        if o.mode=='count':
            p=prefix(o,shown,many,0,0)
            # count ignores line/byte fields; retain only filename decoration
            if o.with_name is True or (o.with_name is None and many):
                nb=namebytes(shown); p=nb+(b'\0' if o.null_name else b':')
            else: p=b''
            output += p+str(count).encode()+b'\n'
            continue
        if isbin and o.binary=='binary':
            if matched: output += b'Binary file '+namebytes(shown)+b' matches\n'
            continue
        if not sels: continue
        selected=set(sels)
        if o.context_seen and not o.only:
            wanted=set()
            for x in sels:
                wanted.update(range(max(0,x-o.before),min(len(recs),x+o.after+1)))
            order=sorted(wanted); runs=[]
            for x in order:
                if not runs or x != runs[-1][-1]+1: runs.append([x])
                else: runs[-1].append(x)
        else: runs=[sels]
        for run in runs:
            if groups_emitted and o.context_seen and not o.only and o.group_sep is not None: output += o.group_sep+term
            groups_emitted=True
            for idx in run:
                raw,off=recs[idx]; sel=idx in selected
                if o.only:
                    if sel and not o.invert:
                        spans=matcher.nonoverlap(raw)
                        for a,b in spans:
                            output += prefix(o,shown,many,idx+1,off+a,False)+raw[a:b]+term
                else:
                    output += prefix(o,shown,many,idx+1,off,not sel)+raw+term
    sys.stdout.buffer.write(output)
    if o.mode=='files_without': success=any_selected is False  # corrected below from actual emitted names
    if had_error: return 2
    if o.mode=='files_without':
        # At least one output name means success.
        return 0 if output else 1
    return 0 if any_selected else 1

if __name__=='__main__':
    sys.exit(main(sys.argv[1:]))
