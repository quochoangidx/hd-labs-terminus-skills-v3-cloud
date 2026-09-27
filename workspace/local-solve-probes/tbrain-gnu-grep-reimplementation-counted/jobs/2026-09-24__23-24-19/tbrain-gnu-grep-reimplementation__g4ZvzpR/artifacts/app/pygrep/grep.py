#!/usr/bin/env python3
"""Small, byte-oriented GNU grep 3.8 compatible implementation."""
import os
import re
import sys


def err(s):
    sys.stderr.write("grep: " + s + "\n")


def split_patterns(s, file_source=False):
    if file_source and s == '': return []
    a = s.split('\n')
    if file_source and s.endswith('\n'):
        a.pop()
    return a


def translate_class(c):
    classes = {
        '[:alnum:]': 'A-Za-z0-9', '[:alpha:]': 'A-Za-z',
        '[:blank:]': ' \\t', '[:cntrl:]': '\\x00-\\x1f\\x7f',
        '[:digit:]': '0-9', '[:graph:]': '\\x21-\\x7e',
        '[:lower:]': 'a-z', '[:print:]': '\\x20-\\x7e',
        '[:punct:]': r'!-/:-@\[-`{-~', '[:space:]': '\\t-\\r ',
        '[:upper:]': 'A-Z', '[:xdigit:]': 'A-Fa-f0-9'
    }
    for k, v in classes.items():
        c = c.replace(k, v)
    return c


def trans_regex(p, mode):
    """Translate common GNU/POSIX ERE or BRE syntax to Python's ASCII re."""
    out = []
    i = 0
    inclass = False
    while i < len(p):
        ch = p[i]
        if ch == '[' and not inclass:
            j = i + 1
            if j < len(p) and p[j] == '^': j += 1
            if j < len(p) and p[j] == ']': j += 1
            while j < len(p):
                if p[j:j+2] == '[:':
                    q=p.find(':]',j+2)
                    if q >= 0: j=q+2; continue
                if p[j] == ']': break
                j += 1
            if j < len(p):
                out.append('[' + translate_class(p[i+1:j]) + ']')
                i = j + 1
                continue
        if ch == '\\' and i + 1 < len(p):
            n = p[i+1]
            if n == '<': out.append(r'(?<![A-Za-z0-9_])')
            elif n == '>': out.append(r'(?![A-Za-z0-9_])')
            elif n == 'b': out.append(r'(?:(?<![A-Za-z0-9_])(?=[A-Za-z0-9_])|(?<=[A-Za-z0-9_])(?![A-Za-z0-9_]))')
            elif n == 'B': out.append(r'(?:(?<=[A-Za-z0-9_])(?=[A-Za-z0-9_])|(?<![A-Za-z0-9_])(?![A-Za-z0-9_]))')
            elif n == 'w': out.append(r'[A-Za-z0-9_]')
            elif n == 'W': out.append(r'[^A-Za-z0-9_]')
            elif mode == 'bre' and n in '(){}+?|': out.append(n)
            elif n.isdigit(): out.append('\\' + n)
            elif n in '.^$*+?{}[]()|\\': out.append('\\' + n if mode == 'ere' else '\\' + n)
            else: out.append(re.escape(n))
            i += 2
            continue
        if mode == 'bre' and ch in '+?{}()|':
            out.append('\\' + ch)
        else:
            out.append(ch)
        i += 1
    return ''.join(out)


class Opt:
    def __init__(self):
        self.mode = None; self.patterns = []; self.hadpat = False
        self.icase = False; self.inv = False; self.word = False; self.line = False
        self.count = False; self.listmode = None; self.maxcount = -1
        self.only = False; self.quiet = False; self.silent = False
        self.byte = False; self.name = None; self.label = '(standard input)'
        self.number = False; self.tab = False; self.nulname = False; self.zero = False
        self.before_c = 0; self.after_c = 0; self.ab_explicit = [False, False]
        self.sep = '--'; self.binary = 'binary'


def number(s, what):
    try:
        n = int(s, 10)
        if n < 0 and not (what == 'max-count' and n == -1): raise ValueError
        return n
    except ValueError:
        raise RuntimeError("invalid %s: %s" % (what, s))


def parse(argv):
    o = Opt(); files = []; i = 0
    def setmode(m):
        if o.mode is not None and o.mode != m: raise RuntimeError('conflicting matchers specified')
        o.mode = m
    def addpat(s, fs=False): o.patterns.extend(split_patterns(s, fs)); setattr(o, 'hadpat', True)
    def argval(attached, name):
        nonlocal i
        if attached != '': return attached
        i += 1
        if i >= len(argv): raise RuntimeError('option requires an argument -- ' + name)
        return argv[i]
    while i < len(argv):
        a = argv[i]
        if a == '--': i += 1; break
        if not a.startswith('-') or a == '-': break
        if a.startswith('--'):
            z = a[2:]; key, eq, val = z.partition('=')
            noarg = {
                'basic-regexp':lambda:setmode('bre'), 'extended-regexp':lambda:setmode('ere'),
                'fixed-strings':lambda:setmode('fixed'), 'ignore-case':lambda:setattr(o,'icase',True),
                'no-ignore-case':lambda:setattr(o,'icase',False), 'invert-match':lambda:setattr(o,'inv',True),
                'word-regexp':lambda:setattr(o,'word',True), 'line-regexp':lambda:setattr(o,'line',True),
                'count':lambda:setattr(o,'count',True), 'files-with-matches':lambda:setattr(o,'listmode','l'),
                'files-without-match':lambda:setattr(o,'listmode','L'), 'only-matching':lambda:setattr(o,'only',True),
                'quiet':lambda:setattr(o,'quiet',True), 'silent':lambda:setattr(o,'silent',True),
                'byte-offset':lambda:setattr(o,'byte',True), 'with-filename':lambda:setattr(o,'name',True),
                'no-filename':lambda:setattr(o,'name',False), 'line-number':lambda:setattr(o,'number',True),
                'initial-tab':lambda:setattr(o,'tab',True), 'null':lambda:setattr(o,'nulname',True),
                'null-data':lambda:setattr(o,'zero',True), 'text':lambda:setattr(o,'binary','text'),
                'binary':lambda:setattr(o,'binary','text'), 'no-group-separator':lambda:setattr(o,'sep',None)
            }
            witharg = {'regexp','file','max-count','label','after-context','before-context','context','group-separator','binary-files'}
            if key in noarg:
                if eq: raise RuntimeError('option does not allow an argument -- '+key)
                noarg[key]()
            elif key in witharg:
                v = val if eq else argval('', key)
                if key == 'regexp': addpat(v)
                elif key == 'file':
                    try:
                        data = sys.stdin.buffer.read() if v == '-' else open(v.encode('latin1'),'rb').read()
                        addpat(data.decode('latin1'), True)
                    except OSError as e: raise RuntimeError('%s: %s' % (v, e.strerror))
                elif key == 'max-count': o.maxcount = number(v,key)
                elif key == 'label': o.label = v
                elif key == 'after-context': o.after_c=number(v,key); o.ab_explicit[1]=True
                elif key == 'before-context': o.before_c=number(v,key); o.ab_explicit[0]=True
                elif key == 'context':
                    n=number(v,key)
                    if not o.ab_explicit[0]: o.before_c=n
                    if not o.ab_explicit[1]: o.after_c=n
                elif key == 'group-separator': o.sep=v
                elif key == 'binary-files':
                    if v not in ('binary','text','without-match'): raise RuntimeError('unknown binary-files type')
                    o.binary=v
            else: raise RuntimeError('unrecognized option -- '+key)
            i += 1; continue
        # -NUM context
        if len(a) > 1 and a[1:].isdigit():
            n=int(a[1:])
            if not o.ab_explicit[0]: o.before_c=n
            if not o.ab_explicit[1]: o.after_c=n
            i += 1; continue
        j=1
        while j < len(a):
            c=a[j]
            if c in 'GEF': setmode({'G':'bre','E':'ere','F':'fixed'}[c]); j+=1
            elif c in 'iy': o.icase=True; j+=1
            elif c=='v': o.inv=True; j+=1
            elif c=='w': o.word=True; j+=1
            elif c=='x': o.line=True; j+=1
            elif c=='c': o.count=True; j+=1
            elif c=='l': o.listmode='l'; j+=1
            elif c=='L': o.listmode='L'; j+=1
            elif c=='o': o.only=True; j+=1
            elif c=='q': o.quiet=True; j+=1
            elif c=='s': o.silent=True; j+=1
            elif c=='b': o.byte=True; j+=1
            elif c=='H': o.name=True; j+=1
            elif c=='h': o.name=False; j+=1
            elif c=='n': o.number=True; j+=1
            elif c=='T': o.tab=True; j+=1
            elif c=='Z': o.nulname=True; j+=1
            elif c=='z': o.zero=True; j+=1
            elif c=='a': o.binary='text'; j+=1
            elif c=='I': o.binary='without-match'; j+=1
            elif c in 'efmABC':
                v=argval(a[j+1:], c); j=len(a)
                if c=='e': addpat(v)
                elif c=='f':
                    try:
                        d=sys.stdin.buffer.read() if v=='-' else open(v.encode('latin1'),'rb').read()
                        addpat(d.decode('latin1'),True)
                    except OSError as e: raise RuntimeError('%s: %s'%(v,e.strerror))
                elif c=='m': o.maxcount=number(v,'max-count')
                elif c=='A': o.after_c=number(v,'context length'); o.ab_explicit[1]=True
                elif c=='B': o.before_c=number(v,'context length'); o.ab_explicit[0]=True
                else:
                    n=number(v,'context length')
                    if not o.ab_explicit[0]: o.before_c=n
                    if not o.ab_explicit[1]: o.after_c=n
            else: raise RuntimeError('invalid option -- '+c)
        i += 1
    rest=argv[i:]
    if not o.hadpat:
        if not rest: raise RuntimeError('missing pattern')
        addpat(rest.pop(0))
    files=rest
    if o.mode is None: o.mode='bre'
    return o, files


def ascii_fold(s):
    return s.translate(str.maketrans('ABCDEFGHIJKLMNOPQRSTUVWXYZ',
                                     'abcdefghijklmnopqrstuvwxyz'))

class Matcher:
    def __init__(self,o):
        self.o=o; self.fixed=[]; self.regex=[]; self.exact_cache={}
        flags=re.ASCII | (re.IGNORECASE if o.icase else 0) | (re.DOTALL if o.zero else 0)
        for p in o.patterns:
            if o.mode=='fixed': self.fixed.append(ascii_fold(p) if o.icase else p)
            else:
                try: self.regex.append(re.compile(trans_regex(p,o.mode),flags))
                except re.error as e: raise RuntimeError(str(e))
    def span(self,s,start=0):
        """Return the POSIX leftmost-longest match satisfying -w/-x."""
        cmp=ascii_fold(s) if self.o.icase else s
        for pos in range(start,len(s)+1):
            ends=[]
            for p in self.fixed:
                if cmp.startswith(p,pos): ends.append(pos+len(p))
            for ri,r in enumerate(self.regex):
                for e in range(len(s),pos-1,-1):
                    rem=len(s)-e; key=(ri,rem)
                    q=self.exact_cache.get(key)
                    if q is None:
                        q=re.compile('(?:'+r.pattern+r')(?:[\s\S]{'+str(rem)+r'})\Z', r.flags)
                        self.exact_cache[key]=q
                    m=q.match(s,pos)
                    if m is not None and m.end()==len(s): ends.append(e)
            valid=[]
            for e in ends:
                if self.o.line and not (pos==0 and e==len(s)): continue
                if self.o.word and not self.o.line:
                    left = pos and s[pos-1].isascii() and (s[pos-1].isalnum() or s[pos-1]=='_')
                    right = e<len(s) and s[e].isascii() and (s[e].isalnum() or s[e]=='_')
                    if left or right: continue
                valid.append(e)
            if valid: return (pos,max(valid))
        return None
    def matches(self,s): return self.span(s) is not None
    def allspans(self,s):
        ans=[]; p=0
        while p<=len(s):
            x=self.span(s,p)
            if x is None: break
            a,b=x
            if b>a: ans.append(x); p=b
            else: p=a+1
        return ans


def records(data, binary, zero):
    sep=b'\0' if zero else b'\n'
    # Per task specification, NUL is also a record delimiter in binary mode.
    delimiters={sep[0]}
    if binary and not zero: delimiters.add(0)
    out=[]; start=0
    for i,c in enumerate(data):
        if c in delimiters:
            out.append((data[start:i].decode('latin1'),start,bytes([c]))); start=i+1
    if start<len(data): out.append((data[start:].decode('latin1'),start,b''))
    return out


def prefix(o,name,lineno,offset,selected,showname,width=0):
    d=b':' if selected else b'-'; z=b''; fields=[]
    if showname:
        z=name.encode('latin1','surrogateescape')+(b'\0' if o.nulname else d)
    if o.number: fields.append(str(lineno).rjust(width).encode() if width else str(lineno).encode())
    if o.byte: fields.append(str(offset).rjust(width).encode() if width else str(offset).encode())
    if fields: z += d.join(fields)+d
    if not z: return b''
    if o.tab: z += b'\t'
    return z


def main(argv):
    argv=[os.fsencode(a).decode('latin1') for a in argv]
    try: o,files=parse(argv); matcher=Matcher(o)
    except RuntimeError as e: err(str(e)); return 2
    if not files: files=['-']
    showname = o.name if o.name is not None else len(files)>1
    had_error=False; any_selected=False; output_started=False
    context_active=(o.before_c or o.after_c) and not (o.count or o.listmode or o.quiet or o.only)
    stdin_data=None
    for fn in files:
        name=o.label if fn=='-' else fn
        try:
            if fn=='-':
                if stdin_data is None: stdin_data=sys.stdin.buffer.read()
                data=stdin_data; stdin_data=b''
            else:
                with open(fn.encode('latin1'),'rb') as f: data=f.read()
        except OSError as e:
            had_error=True
            if not o.silent: err('%s: %s'%(fn,e.strerror))
            continue
        isbin=(b'\0' in data and not o.zero and o.binary!='text')
        recs=records(data,isbin,o.zero)
        tabwidth=0
        if o.tab:
            vals=[]
            if o.number: vals.append(len(str(max(1,len(recs)))))
            if o.byte: vals.append(len(str(max(0,len(data)-1))))
            tabwidth=max(vals) if vals else 0
        selected=[]; count=0
        if o.maxcount != 0 and not (isbin and o.binary=='without-match'):
            for k,(line,off,term) in enumerate(recs):
                yes=matcher.matches(line)
                if o.inv: yes=not yes
                if yes:
                    selected.append(k); count+=1
                    if o.maxcount>=0 and count>=o.maxcount: break
                    if isbin and o.binary=='binary' and not o.count: break
                    if o.listmode=='l' or o.quiet: break
        has=count>0
        if o.listmode != 'L': any_selected |= has
        if o.quiet and has: return 0
        if o.listmode:
            emit = has if o.listmode=='l' else not has
            if emit:
                any_selected=True
                sys.stdout.buffer.write(name.encode('latin1','surrogateescape')+(b'\0' if o.nulname else b'\n'))
            continue
        if o.count:
            p=(name.encode('latin1','surrogateescape')+(b'\0' if o.nulname else b':')) if showname else b''
            sys.stdout.buffer.write(p+str(count).encode()+b'\n'); continue
        if isbin and o.binary=='binary':
            if has: sys.stdout.buffer.write(('Binary file %s matches\n'%name).encode('latin1','surrogateescape'))
            continue
        if not selected: continue
        chosen=set(selected)
        if context_active:
            ranges=[]
            for k in selected:
                a=max(0,k-o.before_c); b=min(len(recs)-1,k+o.after_c)
                if ranges and a<=ranges[-1][1]+1: ranges[-1][1]=max(ranges[-1][1],b)
                else: ranges.append([a,b])
            for a,b in ranges:
                if output_started and o.sep is not None: sys.stdout.buffer.write(o.sep.encode('latin1')+b'\n')
                output_started=True
                for k in range(a,b+1):
                    line,off,term=recs[k]; sel=k in chosen
                    sys.stdout.buffer.write(prefix(o,name,k+1,off,sel,showname,tabwidth)+line.encode('latin1')+(b'\0' if o.zero else b'\n'))
        else:
            for k in selected:
                line,off,term=recs[k]
                if o.only:
                    if not o.inv:
                        for a,b in matcher.allspans(line):
                            sys.stdout.buffer.write(prefix(o,name,k+1,off+a,True,showname,tabwidth)+line[a:b].encode('latin1')+(b'\0' if o.zero else b'\n'))
                else:
                    sys.stdout.buffer.write(prefix(o,name,k+1,off,True,showname,tabwidth)+line.encode('latin1')+(b'\0' if o.zero else b'\n'))
    if had_error: return 2
    return 0 if any_selected else 1

if __name__=='__main__': sys.exit(main(sys.argv[1:]))
