#!/usr/bin/env python3
"""A small, pure-Python-driver implementation of GNU grep's documented interface."""
import sys, os, ctypes, locale
locale.setlocale(locale.LC_ALL, "C")

# POSIX regex support from the C library gives the required leftmost-longest rules.
_libc = ctypes.CDLL(None)
class RM(ctypes.Structure):
    _fields_ = [('rm_so', ctypes.c_int), ('rm_eo', ctypes.c_int)]
_libc.regcomp.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int]
_libc.regcomp.restype = ctypes.c_int
_libc.regexec.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_size_t,
                          ctypes.POINTER(RM), ctypes.c_int]
_libc.regexec.restype = ctypes.c_int
_libc.regfree.argtypes = [ctypes.c_void_p]
REG_EXTENDED, REG_ICASE, REG_NEWLINE = 1, 2, 4
REG_NOTBOL, REG_NOTEOL, REG_STARTEND = 1, 2, 4

class BadOption(Exception): pass

class Rx:
    def __init__(self, pat, extended, icase, word=False, whole=False):
        self.mem = (ctypes.c_long * 512)()
        self.word, self.whole = word, whole
        flags = REG_NEWLINE | (REG_EXTENDED if extended else 0) | (REG_ICASE if icase else 0)
        rc = _libc.regcomp(ctypes.byref(self.mem), pat, flags)
        if rc:
            raise BadOption('invalid regular expression')
    @staticmethod
    def wc(c):
        return c == 95 or 48 <= c <= 57 or 65 <= c <= 90 or 97 <= c <= 122
    def search(self, data, start=0):
        buf = ctypes.create_string_buffer(data)
        pos = start
        while pos <= len(data):
            m = (RM * 1)()
            m[0].rm_so, m[0].rm_eo = pos, len(data)
            flags = REG_STARTEND | (REG_NOTBOL if pos else 0)
            rc = _libc.regexec(ctypes.byref(self.mem), ctypes.cast(buf, ctypes.c_char_p),
                               1, m, flags)
            if rc:
                return None
            a, b = m[0].rm_so, m[0].rm_eo
            if self.whole:
                return (a, b) if a == 0 and b == len(data) else None
            if not self.word or ((a == 0 or not self.wc(data[a-1])) and
                                 (b == len(data) or not self.wc(data[b])) and
                                 (b > a or
                                  (a < len(data) and self.wc(data[a])) or
                                  (a > 0 and self.wc(data[a-1])))):
                return a, b
            # Look for a later possible start. Advancing one byte preserves
            # overlapping candidates needed when a rejected match was longest.
            pos = a + 1
        return None
    def __del__(self):
        try: _libc.regfree(ctypes.byref(self.mem))
        except Exception: pass

class Fixed:
    def __init__(self, pat, icase, word=False, whole=False):
        self.pat = pat.lower() if icase else pat
        self.icase, self.word, self.whole = icase, word, whole
    @staticmethod
    def wc(c): return c == 95 or 48 <= c <= 57 or 65 <= c <= 90 or 97 <= c <= 122
    def search(self, data, start=0):
        hay = data.lower() if self.icase else data
        p = self.pat
        if self.whole:
            return (0, len(data)) if start == 0 and hay == p else None
        at = start
        while True:
            i = hay.find(p, at)
            if i < 0: return None
            j = i + len(p)
            if not self.word or ((i == 0 or not self.wc(data[i-1])) and
                                 (j == len(data) or not self.wc(data[j]))):
                return i, j
            at = i + 1

def split_patterns(p):
    # A newline in a pattern list separates patterns; retain an empty final pattern.
    return p.split(b'\n')

def parse(argv):
    o = dict(mode='G', icase=False, invert=False, word=False, whole=False,
             count=False, files_with=None, maxcount=None, only=False, quiet=False,
             silent=False, byte=False, filename=None, line=False, tab=False,
             nulname=False, null_data=False, before=0, after=0, group=b'--',
             binary='binary', label=b'(standard input)', haspat=False, context=False)
    pats, files = [], []
    needpat = True
    i = 0
    valued = {'e','f','m','A','B','C','d','D'}
    while i < len(argv):
        a = argv[i]
        if a == '--': i += 1; break
        if a.startswith('--'):
            name, eq, val = a[2:].partition('=')
            aliases = {'extended-regexp':'E','fixed-strings':'F','basic-regexp':'G',
              'regexp':'e','file':'f','ignore-case':'i','no-ignore-case':'no-i',
              'invert-match':'v','word-regexp':'w','line-regexp':'x','count':'c',
              'files-with-matches':'l','files-without-match':'L','max-count':'m',
              'only-matching':'o','quiet':'q','silent':'q','no-messages':'s',
              'byte-offset':'b','with-filename':'H','no-filename':'h','line-number':'n',
              'initial-tab':'T','null':'Z','null-data':'z','after-context':'A',
              'before-context':'B','context':'C','text':'a','binary-files':'binary-files',
              'label':'label','group-separator':'group','no-group-separator':'nogroup',
              'text':'a','binary':'I'}
            if name not in aliases: raise BadOption('unrecognized option')
            key = aliases[name]
            if key in ('e','f','m','A','B','C','binary-files','label','group'):
                if not eq:
                    i += 1
                    if i >= len(argv): raise BadOption('option requires an argument')
                    val = argv[i]
            handle(o, pats, key, val)
            i += 1; continue
        if len(a) > 1 and a[0] == '-':
            s, k = a[1:], 0
            while k < len(s):
                ch = s[k]
                if ch.isdigit():
                    j = k
                    while j < len(s) and s[j].isdigit(): j += 1
                    o['before'] = o['after'] = int(s[k:j]); o['context'] = True; k = j; continue
                if ch in valued:
                    val = s[k+1:]
                    if not val:
                        i += 1
                        if i >= len(argv): raise BadOption('option requires an argument')
                        val = argv[i]
                    handle(o, pats, ch, val); k = len(s)
                else:
                    handle(o, pats, ch, None); k += 1
            i += 1; continue
        break
    rest = argv[i:]
    if not o['haspat']:
        if not rest: raise BadOption('missing pattern')
        pats += split_patterns(os.fsencode(rest.pop(0)))
    files = rest
    return o, pats, files

def num(v):
    try:
        n = int(v)
        if n < 0: raise ValueError
        return n
    except ValueError: raise BadOption('invalid context length')

def handle(o, pats, ch, val):
    if ch in ('E','F','G'): o['mode'] = ch
    elif ch == 'i': o['icase'] = True
    elif ch == 'no-i': o['icase'] = False
    elif ch == 'v': o['invert'] = True
    elif ch == 'w': o['word'] = True
    elif ch == 'x': o['whole'] = True
    elif ch == 'c': o['count'] = True
    elif ch == 'l': o['files_with'] = True
    elif ch == 'L': o['files_with'] = False
    elif ch == 'm':
        try:
            n = int(val)
            if n < -1: raise ValueError
            o['maxcount'] = None if n == -1 else n
        except ValueError: raise BadOption('invalid max count')
    elif ch == 'o': o['only'] = True
    elif ch == 'q': o['quiet'] = True
    elif ch == 's': o['silent'] = True
    elif ch == 'b': o['byte'] = True
    elif ch == 'H': o['filename'] = True
    elif ch == 'h': o['filename'] = False
    elif ch == 'n': o['line'] = True
    elif ch == 'T': o['tab'] = True
    elif ch == 'Z': o['nulname'] = True
    elif ch == 'z': o['null_data'] = True
    elif ch in ('A','B','C'):
        n = num(val)
        o['context'] = True
        if ch in ('A','C'): o['after'] = n
        if ch in ('B','C'): o['before'] = n
    elif ch == 'a': o['binary'] = 'text'
    elif ch == 'I': o['binary'] = 'without-match'
    elif ch == 'binary-files':
        if val not in ('binary','text','without-match'): raise BadOption('unknown binary-files type')
        o['binary'] = val
    elif ch == 'label': o['label'] = os.fsencode(val)
    elif ch == 'group': o['group'] = os.fsencode(val)
    elif ch == 'nogroup': o['group'] = None
    elif ch == 'e':
        o['haspat'] = True
        pats.extend(split_patterns(os.fsencode(val)))
    elif ch == 'f':
        o['haspat'] = True
        try:
            data = sys.stdin.buffer.read() if val == '-' else open(val, 'rb').read()
        except OSError: raise BadOption('pattern file error')
        if data:
            if data.endswith(b'\n'): data = data[:-1]
            pats.extend(data.split(b'\n'))
    elif ch in ('d','D'): pass
    else: raise BadOption('invalid option -- '+str(ch))

def all_matches(matchers, rec):
    pos = 0
    while pos <= len(rec):
        best = None
        for m in matchers:
            z = m.search(rec, pos)
            if z is not None and (best is None or z[0] < best[0] or
                                  (z[0] == best[0] and z[1] > best[1])):
                best = z
        if best is None: break
        yield best
        pos = best[1] if best[1] > best[0] else best[0] + 1

def records(data, sep):
    out, st = [], 0
    for part in data.split(sep)[:-1]:
        out.append((part, st, True)); st += len(part)+1
    if st < len(data): out.append((data[st:], st, False))
    return out

def prefix(o, name, lineno, off, selected, showname):
    delim = b':' if selected else b'-'
    parts = []
    if showname:
        # -Z replaces the separator following a file name with NUL.
        p = name + (b'\0' if o['nulname'] else delim)
        if o['line']:
            v = str(lineno).encode()
            if o['tab']: v = v.rjust(o.get('_nw', len(v)))
            p += v + delim
        if o['byte']:
            v = str(off).encode()
            if o['tab']: v = v.rjust(o.get('_bw', len(v)))
            p += v + delim
    else:
        if o['line']:
            v = str(lineno).encode()
            parts.append(v.rjust(o.get('_nw', len(v))) if o['tab'] else v)
        if o['byte']:
            v = str(off).encode()
            parts.append(v.rjust(o.get('_bw', len(v))) if o['tab'] else v)
        if not parts: return b''
        p = delim.join(parts) + delim
    if o['tab']: p += b'\t'
    return p

def emit_normal(o, name, recs, selected, matches, showname, outsep):
    before, after = o['before'], o['after']
    if o['only']:
        if not o['invert']:
            for i in selected:
                rec, off, _ = recs[i]
                for a,b in matches[i]:
                    # GNU grep does not print empty matches with -o.
                    if b > a:
                        sys.stdout.buffer.write(prefix(o,name,i+1,off+a,True,showname)+rec[a:b]+outsep)
        return
    wanted = set()
    for i in selected:
        wanted.update(range(max(0,i-before), min(len(recs),i+after+1)))
    last = None
    for i in sorted(wanted):
        if o['context'] and last is not None and i > last+1 and o['group'] is not None:
            sys.stdout.buffer.write(o['group']+outsep)
        rec, off, _ = recs[i]
        sys.stdout.buffer.write(prefix(o,name,i+1,off,i in selected,showname)+rec+outsep)
        last = i

def main(argv):
    try: o, pats, files = parse(argv)
    except BadOption as e:
        sys.stderr.write('grep: '+str(e)+'\n'); return 2
    try:
        if o['mode'] == 'F':
            ms = [Fixed(p,o['icase'],o['word'],o['whole']) for p in pats]
        else:
            ms = [Rx(p,o['mode']=='E',o['icase'],o['word'],o['whole']) for p in pats]
    except BadOption as e:
        sys.stderr.write('grep: '+str(e)+'\n'); return 2
    if not files: files = ['-']
    show_default = len(files) > 1
    anymatch, haderr, any_without, prior_group = False, False, False, False
    sep = b'\0' if o['null_data'] else b'\n'
    for fn in files:
        name = o['label'] if fn == '-' else os.fsencode(fn)
        try: data = sys.stdin.buffer.read() if fn == '-' else open(fn,'rb').read()
        except OSError as e:
            haderr = True
            if not o['silent']: sys.stderr.write('grep: %s: %s\n' % (fn,e.strerror))
            continue
        binary = (not o['null_data'] and b'\0' in data and o['binary'] != 'text')
        if binary and o['binary'] == 'without-match': recs=[]
        else: recs = records(data, sep)
        # GNU uses the potential input ranges to align -T numeric fields.
        o['_nw'] = len(str(max(1, len(recs))))
        o['_bw'] = len(str(max(0, len(data) - 1)))
        selected, mm = [], {}
        limit = o['maxcount']
        scanrecs = [] if limit == 0 else recs
        for idx,(rec,off,term) in enumerate(scanrecs):
            found = next(all_matches(ms,rec),None) is not None
            yes = not found if o['invert'] else found
            if yes:
                selected.append(idx)
                if o['only'] and not o['invert']: mm[idx] = list(all_matches(ms,rec))
                if limit is not None and len(selected) >= limit: break
        hit = bool(selected)
        if hit: anymatch = True
        else: any_without = True
        if o['quiet'] and hit: return 0
        outname = name + (b'\0' if o['nulname'] else b'\n')
        if o['files_with'] is True:
            if hit: sys.stdout.buffer.write(outname)
            continue
        if o['files_with'] is False:
            if not hit: sys.stdout.buffer.write(outname)
            continue
        showname = show_default if o['filename'] is None else o['filename']
        if o['count']:
            p = (name + (b'\0' if o['nulname'] else b':')) if showname else b''
            sys.stdout.buffer.write(p+str(len(selected)).encode()+b'\n'); continue
        if binary and o['binary'] == 'binary':
            # GNU's diagnostic is on stderr, which is intentionally not compared.
            if hit and not o['silent']:
                sys.stderr.buffer.write(b'grep: '+name+b': binary file matches\n')
            continue
        if selected and o['context'] and not o['only'] and prior_group and o['group'] is not None:
            sys.stdout.buffer.write(o['group']+sep)
        emit_normal(o,name,recs,selected,mm,showname,sep)
        if selected: prior_group = True
    success = any_without if o['files_with'] is False else anymatch
    return 2 if haderr else (0 if success else 1)

if __name__ == '__main__':
    try: sys.exit(main(sys.argv[1:]))
    except BrokenPipeError: sys.exit(2)
