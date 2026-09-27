"""A small, byte-oriented GNU grep compatible command."""
import sys, os, ctypes, locale

libc = ctypes.CDLL(None)
locale.setlocale(locale.LC_ALL, 'C')
class RM(ctypes.Structure):
    _fields_ = [('so', ctypes.c_int), ('eo', ctypes.c_int)]
libc.regcomp.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int]
libc.regcomp.restype = ctypes.c_int
libc.regexec.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_size_t, ctypes.POINTER(RM), ctypes.c_int]
libc.regexec.restype = ctypes.c_int
libc.regfree.argtypes = [ctypes.c_void_p]

class Regex:
    def __init__(self, pat, extended, icase, newline=True):
        self.mem = ctypes.create_string_buffer(4096)
        flags = (1 if extended else 0) | (2 if icase else 0) | (4 if newline else 0)
        r = libc.regcomp(self.mem, pat, flags)
        if r: raise ValueError('invalid regular expression')
    def search(self, data, start=0):
        # REG_STARTEND is a GNU/POSIX extension and permits embedded NUL bytes.
        buf = ctypes.create_string_buffer(data, len(data) + 1)
        m = RM(start, len(data))
        r = libc.regexec(self.mem, buf, 1, ctypes.byref(m), 4)
        return None if r else (m.so, m.eo)
    def __del__(self):
        try: libc.regfree(self.mem)
        except Exception: pass

class Opt:
    def __init__(self):
        self.mode='G'; self.icase=False; self.invert=False; self.word=False; self.line=False
        self.count=False; self.list_yes=False; self.list_no=False; self.maxcount=-1
        self.only=False; self.quiet=False; self.silent=False; self.byte=False
        self.withname=None; self.label=b'(standard input)'; self.number=False; self.tab=False
        self.nullname=False; self.zero=False; self.before=0; self.after=0
        self.group=b'--'; self.binary='binary'; self.pats=[]; self.hadpatopt=False

def num(s):
    try:
        n=int(s)
        if n < 0: raise ValueError
        return n
    except: raise ValueError('invalid context length argument')

def parse(argv):
    o=Opt(); files=[]; i=0
    arglong={'regexp','file','max-count','label','after-context','before-context','context','group-separator','binary-files'}
    longs={
      'extended-regexp':('mode','E'),'fixed-strings':('mode','F'),'basic-regexp':('mode','G'),
      'ignore-case':('icase',True),'no-ignore-case':('icase',False),'invert-match':('invert',True),
      'word-regexp':('word',True),'line-regexp':('line',True),'count':('count',True),
      'files-with-matches':('list_yes',True),'files-without-match':('list_no',True),
      'only-matching':('only',True),'quiet':('quiet',True),'silent':('quiet',True),
      'no-messages':('silent',True),'byte-offset':('byte',True),'with-filename':('withname',True),
      'no-filename':('withname',False),'line-number':('number',True),'initial-tab':('tab',True),
      'null':('nullname',True),'null-data':('zero',True),'no-group-separator':('group',None),
      'text':('binary','text'),'binary':('binary','binary'),'without-match':('binary','without-match')}
    while i<len(argv):
        a=argv[i]
        if a=='--': i+=1; break
        if not a.startswith('-') or a=='-': break
        if a.startswith('--'):
            x=a[2:]; val=None
            if '=' in x: x,val=x.split('=',1)
            if x in arglong:
                if val is None:
                    i+=1
                    if i>=len(argv): raise ValueError('option requires an argument')
                    val=argv[i]
                vb=os.fsencode(val)
                if x=='regexp': o.pats += vb.split(b'\n'); o.hadpatopt=True
                elif x=='file': read_patterns(o, val)
                elif x=='max-count':
                    o.maxcount=int(val)
                    if o.maxcount < -1: raise ValueError('invalid max count')
                elif x=='label': o.label=vb
                elif x=='after-context': o.after=num(val)
                elif x=='before-context': o.before=num(val)
                elif x=='context': o.before=o.after=num(val)
                elif x=='group-separator': o.group=vb
                elif x=='binary-files':
                    if val not in ('binary','text','without-match'): raise ValueError('unknown binary-files type')
                    o.binary=val
            elif x in longs: setattr(o,*longs[x])
            elif x in ('help','version'): pass
            else: raise ValueError('unrecognized option --'+x)
            i+=1; continue
        # Historical -NUM context option.
        if len(a)>1 and a[1:].isdigit(): o.before=o.after=num(a[1:]); i+=1; continue
        j=1
        while j<len(a):
            c=a[j]
            noarg={'G':('mode','G'),'E':('mode','E'),'F':('mode','F'),'i':('icase',True),'y':('icase',True),
             'v':('invert',True),'w':('word',True),'x':('line',True),'c':('count',True),'l':('list_yes',True),
             'L':('list_no',True),'o':('only',True),'q':('quiet',True),'s':('silent',True),'b':('byte',True),
             'H':('withname',True),'h':('withname',False),'n':('number',True),'T':('tab',True),
             'Z':('nullname',True),'z':('zero',True),'a':('binary','text'),'I':('binary','without-match')}
            if c in noarg: setattr(o,*noarg[c]); j+=1; continue
            if c in 'efmABC':
                if j+1<len(a): val=a[j+1:]; j=len(a)
                else:
                    i+=1
                    if i>=len(argv): raise ValueError('option requires an argument -- '+c)
                    val=argv[i]; j=len(a)
                if c=='e': o.pats += os.fsencode(val).split(b'\n'); o.hadpatopt=True
                elif c=='f': read_patterns(o,val)
                elif c=='m':
                    o.maxcount=int(val)
                    if o.maxcount < -1: raise ValueError('invalid max count')
                elif c=='A': o.after=num(val)
                elif c=='B': o.before=num(val)
                else: o.before=o.after=num(val)
            else: raise ValueError('invalid option -- '+c)
        i+=1
    rest=argv[i:]
    if not o.hadpatopt:
        if not rest: raise ValueError('missing search pattern')
        o.pats += os.fsencode(rest[0]).split(b'\n'); rest=rest[1:]
    files=rest
    return o,files

def read_patterns(o, fn):
    try:
        d=sys.stdin.buffer.read() if fn=='-' else open(fn,'rb').read()
    except OSError: raise ValueError(fn+': cannot read pattern file')
    if d:
        if d.endswith(b'\n'): d=d[:-1]
        o.pats += d.split(b'\n')
    o.hadpatopt=True

class Matcher:
    def __init__(self,o):
        self.o=o; self.fixed=[]; self.regex=[]
        if o.mode=='F':
            self.fixed=[p.lower() if o.icase else p for p in o.pats]
        else:
            self.regex=[Regex(p,o.mode=='E',o.icase,not o.zero) for p in o.pats]
    @staticmethod
    def better(z,best):
        return z is not None and (best is None or z[0]<best[0] or (z[0]==best[0] and z[1]>best[1]))
    @staticmethod
    def isword(c):
        return 65<=c<=90 or 97<=c<=122 or 48<=c<=57 or c==95
    def candidates(self,d,start):
        if self.o.mode=='F':
            x=d.lower() if self.o.icase else d
            for pat in self.fixed:
                k=x.find(pat,start)
                yield None if k<0 else (k,k+len(pat)), ('f',x,pat)
        else:
            for rx in self.regex:
                yield rx.search(d,start), ('r',rx,None)
    def next_for(self,d,z,engine):
        if z is None: return None
        a,b=z; typ,obj,pat=engine
        if typ=='f':
            k=obj.find(pat,a+1)
            return None if k<0 else (k,k+len(pat))
        return obj.search(d,a+1)
    def best(self,d,start=0):
        if self.o.line:
            if start: return None
            best=None
            for z,_ in self.candidates(d,0):
                if z==(0,len(d)) and self.better(z,best): best=z
            return best
        best=None
        for z,engine in self.candidates(d,start):
            if self.o.word:
                while z is not None:
                    a,b=z
                    if (a==0 or not self.isword(d[a-1])) and (b==len(d) or not self.isword(d[b])):
                        break
                    z=self.next_for(d,z,engine)
            if self.better(z,best): best=z
        return best
    def matches(self,d): return self.best(d) is not None
    def all(self,d):
        out=[]; p=0
        while p<=len(d):
            z=self.best(d,p)
            if z is None: break
            a,b=z
            if b>a: out.append(z); p=b
            else: p=a+1
        return out

def records(data, delim):
    out=[]; p=0; n=1
    while p<len(data):
        q=data.find(delim,p)
        if q<0: out.append((n,p,data[p:])); break
        out.append((n,p,data[p:q])); p=q+1; n+=1
    return out

def name_for(fn,o): return o.label if fn=='-' else os.fsencode(fn)
def prefix(o,name,ln,off,selected,showname,width=0):
    sep=b':' if selected else b'-'; fields=[]
    if o.number: fields.append(str(ln).encode().rjust(width) if o.tab else str(ln).encode())
    if o.byte: fields.append(str(off).encode().rjust(width) if o.tab else str(off).encode())
    tail=sep.join(fields)+sep if fields else b''
    if showname:
        tail=name+(b'\0' if o.nullname else sep)+tail
    if not tail: return b''
    if o.tab:
        return tail+b'\t'
    return tail

def emit_name(name,o): return name+(b'\0' if o.nullname else b'\n')

def process(data,fn,o,m,showname):
    delim=b'\0' if o.zero else b'\n'; rs=records(data,delim); name=name_for(fn,o)
    width=len(str(len(data)))
    isbin=(not o.zero and b'\0' in data and o.binary!='text')
    selected=[]; nsel=0
    if o.maxcount==0: rs=[]
    for idx,(ln,off,line) in enumerate(rs):
        raw=m.matches(line)
        if isbin and o.binary=='without-match': raw=False
        sel=(not raw if o.invert else raw)
        if sel:
            selected.append(idx); nsel+=1
            if o.maxcount>=0 and nsel>=o.maxcount: break
    if o.quiet: return b'',bool(selected)
    if o.list_yes: return (emit_name(name,o) if selected else b''),bool(selected)
    if o.list_no: return (b'' if selected else emit_name(name,o)),not bool(selected)
    if o.count:
        pre=(name+(b'\0' if o.nullname else b':') if showname else b'')
        return pre+str(len(selected)).encode()+b'\n',bool(selected)
    if isbin and o.binary=='binary':
        return ((b'Binary file '+name+b' matches\n') if selected else b''),bool(selected)
    if not selected: return b'',False
    if o.only:
        if o.invert: return b'',True
        out=[]
        for idx in selected:
            ln,off,line=rs[idx]
            for a,b in m.all(line): out.append(prefix(o,name,ln,off+a,True,showname,width)+line[a:b]+delim)
        return b''.join(out),True
    # Merge intervals around selected records; max-count still permits trailing context.
    spans=[]
    for x in selected:
        a=max(0,x-o.before); b=min(len(rs)-1,x+o.after)
        if spans and a<=spans[-1][1]+1: spans[-1][1]=max(spans[-1][1],b)
        else: spans.append([a,b])
    out=[]; sset=set(selected)
    for si,(a,b) in enumerate(spans):
        if si and (o.before or o.after) and o.group is not None: out.append(o.group+delim)
        for x in range(a,b+1):
            ln,off,line=rs[x]; chosen=x in sset
            out.append(prefix(o,name,ln,off,chosen,showname,width)+line+delim)
    return b''.join(out),True

def main(argv):
    try: o,files=parse(argv)
    except Exception as e:
        sys.stderr.write('grep: '+str(e)+'\n'); return 2
    if not files: files=['-']
    showname=(len(files)>1) if o.withname is None else o.withname
    try: matcher=Matcher(o)
    except Exception as e:
        sys.stderr.write('grep: '+str(e)+'\n'); return 2
    anymatch=False; haderr=False; out=sys.stdout.buffer
    prior_normal_output=False
    for fn in files:
        try:
            if fn=='-':
                data=sys.stdin.buffer.read()
            else:
                with open(fn,'rb') as f: data=f.read()
        except OSError as e:
            haderr=True
            if not o.silent: sys.stderr.write('grep: %s: %s\n'%(fn,e.strerror))
            continue
        chunk,yes=process(data,fn,o,matcher,showname)
        anymatch |= yes
        if chunk:
            normal_context = (o.before or o.after) and not (o.count or o.list_yes or o.list_no or o.only or o.quiet)
            if normal_context and prior_normal_output and o.group is not None:
                out.write(o.group+(b'\0' if o.zero else b'\n'))
            out.write(chunk)
            if normal_context: prior_normal_output=True
        if o.quiet and yes: return 0
    if haderr: return 2
    return 0 if anymatch else 1
if __name__=='__main__': sys.exit(main(sys.argv[1:]))
