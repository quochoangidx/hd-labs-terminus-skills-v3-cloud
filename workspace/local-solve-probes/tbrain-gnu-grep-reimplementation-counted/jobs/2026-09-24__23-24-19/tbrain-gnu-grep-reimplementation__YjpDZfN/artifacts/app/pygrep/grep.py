#!/usr/bin/env python3
"""Small, byte-oriented GNU grep 3.8 replacement."""
import sys, os, ctypes, ctypes.util, locale
locale.setlocale(locale.LC_ALL, 'C')

libc = ctypes.CDLL(ctypes.util.find_library('c') or 'libc.so.6')
libc.regcomp.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int]
libc.regcomp.restype = ctypes.c_int
libc.regexec.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_size_t, ctypes.c_void_p, ctypes.c_int]
libc.regexec.restype = ctypes.c_int
libc.regfree.argtypes = [ctypes.c_void_p]
REG_EXTENDED, REG_ICASE, REG_NEWLINE = 1, 2, 4
REG_NOTBOL, REG_NOTEOL, REG_STARTEND = 1, 2, 4

class RM(ctypes.Structure):
    _fields_ = [('so', ctypes.c_int), ('eo', ctypes.c_int)]

class Rx:
    def __init__(self, p, extended, icase):
        self.mem = ctypes.create_string_buffer(4096)
        self.compiled = False
        flags = (REG_EXTENDED if extended else 0) | (REG_ICASE if icase else 0)
        if libc.regcomp(self.mem, p, flags):
            raise ValueError('invalid regular expression')
        self.compiled = True
    def search(self, s, start=0):
        # REG_STARTEND permits embedded NUL bytes.
        buf = ctypes.create_string_buffer(s + b'\0')
        m = (RM * 1)(); m[0].so = start; m[0].eo = len(s)
        ef = REG_STARTEND | (REG_NOTBOL if start else 0)
        if libc.regexec(self.mem, buf, 1, m, ef): return None
        return m[0].so, m[0].eo
    def exact(self, s, a, b):
        buf = ctypes.create_string_buffer(s + b'\0')
        m = (RM * 1)(); m[0].so = a; m[0].eo = b
        ef = REG_STARTEND | (REG_NOTBOL if a else 0) | (REG_NOTEOL if b < len(s) else 0)
        if libc.regexec(self.mem, buf, 1, m, ef): return False
        return m[0].so == a and m[0].eo == b
    def __del__(self):
        try:
            if self.compiled: libc.regfree(self.mem)
        except Exception: pass

def split_patterns(b, from_file=False):
    if from_file and not b:
        return []
    a = b.split(b'\n')
    if from_file and b.endswith(b'\n'): a.pop()
    return a

def num(s, allow_minus_one=False):
    try:
        n = int(s)
        if n < 0 and not (allow_minus_one and n == -1): raise ValueError
        return n
    except Exception: raise ValueError('invalid number')

def parse(av):
    o = dict(mode='G', ignore=False, invert=False, word=False, line=False,
      count=False, listmode=None, max=-1, only=False, quiet=False, silent=False,
      byte=False, fname=None, label=b'(standard input)', lineno=False, tab=False,
      nullname=False, zero=False, binary='binary', before=0, after=0,
      b_explicit=False, a_explicit=False, sep=b'--', sep_on=True, pats=[], pfiles=[])
    files=[]; i=0; operand=None; engine_seen=None
    def engine(x):
        nonlocal engine_seen
        if engine_seen is not None and engine_seen != x: raise ValueError('conflicting matchers')
        engine_seen=x; o['mode']=x
    long_noarg = {
      'basic-regexp':lambda:engine('G'),'extended-regexp':lambda:engine('E'),
      'fixed-strings':lambda:engine('F'),'ignore-case':lambda:o.update(ignore=True),
      'no-ignore-case':lambda:o.update(ignore=False),'invert-match':lambda:o.update(invert=True),
      'word-regexp':lambda:o.update(word=True),'line-regexp':lambda:o.update(line=True),
      'count':lambda:o.update(count=True),'files-with-matches':lambda:o.update(listmode='l'),
      'files-without-match':lambda:o.update(listmode='L'),'only-matching':lambda:o.update(only=True),
      'quiet':lambda:o.update(quiet=True),'silent':lambda:o.update(quiet=True),
      'no-messages':lambda:o.update(silent=True),'byte-offset':lambda:o.update(byte=True),
      'with-filename':lambda:o.update(fname=True),'no-filename':lambda:o.update(fname=False),
      'line-number':lambda:o.update(lineno=True),'initial-tab':lambda:o.update(tab=True),
      'null':lambda:o.update(nullname=True),'null-data':lambda:o.update(zero=True),
      'text':lambda:o.update(binary='text'),'binary':lambda:o.update(binary='without'),
      'no-group-separator':lambda:o.update(sep_on=False)}
    while i < len(av):
        a=av[i]
        if a=='--': i+=1; break
        if not a.startswith('-') or a=='-': break
        if a.startswith('--'):
            x=a[2:]; val=None
            if '=' in x: x,val=x.split('=',1)
            needs={'regexp','file','max-count','label','after-context','before-context','context','group-separator','binary-files'}
            if x in needs and val is None:
                i+=1
                if i>=len(av): raise ValueError('missing option argument')
                val=av[i]
            if x=='regexp': o['pats'] += split_patterns(os.fsencode(val))
            elif x=='file': o['pfiles'].append(val)
            elif x=='max-count': o['max']=num(val, True)
            elif x=='label': o['label']=os.fsencode(val)
            elif x=='after-context': o['after']=num(val); o['a_explicit']=True
            elif x=='before-context': o['before']=num(val); o['b_explicit']=True
            elif x=='context':
                n=num(val)
                if not o['a_explicit']: o['after']=n
                if not o['b_explicit']: o['before']=n
            elif x=='group-separator': o['sep']=os.fsencode(val); o['sep_on']=True
            elif x=='binary-files':
                if val not in ('binary','text','without-match'): raise ValueError('bad binary type')
                o['binary']='without' if val=='without-match' else val
            elif x in long_noarg and val is None: long_noarg[x]()
            else: raise ValueError('unknown option')
            i+=1; continue
        # GNU -NUM context shorthand
        if len(a)>1 and a[1:].isdigit():
            n=num(a[1:])
            if not o['a_explicit']: o['after']=n
            if not o['b_explicit']: o['before']=n
            i+=1; continue
        j=1
        while j<len(a):
            c=a[j]; arg=None
            if c.isdigit():
                k=j
                while k<len(a) and a[k].isdigit(): k+=1
                n=num(a[j:k])
                if not o['a_explicit']: o['after']=n
                if not o['b_explicit']: o['before']=n
                j=k
                continue
            if c in 'efmABC':
                if j+1<len(a): arg=a[j+1:]; j=len(a)
                else:
                    i+=1
                    if i>=len(av): raise ValueError('missing option argument')
                    arg=av[i]; j=len(a)
            else: j+=1
            if c=='G': engine('G')
            elif c=='E': engine('E')
            elif c=='F': engine('F')
            elif c=='e': o['pats'] += split_patterns(os.fsencode(arg))
            elif c=='f': o['pfiles'].append(arg)
            elif c in 'iy': o['ignore']=True
            elif c=='v': o['invert']=True
            elif c=='w': o['word']=True
            elif c=='x': o['line']=True
            elif c=='c': o['count']=True
            elif c=='l': o['listmode']='l'
            elif c=='L': o['listmode']='L'
            elif c=='m': o['max']=num(arg, True)
            elif c=='o': o['only']=True
            elif c=='q': o['quiet']=True
            elif c=='s': o['silent']=True
            elif c=='b': o['byte']=True
            elif c=='H': o['fname']=True
            elif c=='h': o['fname']=False
            elif c=='n': o['lineno']=True
            elif c=='T': o['tab']=True
            elif c=='Z': o['nullname']=True
            elif c=='z': o['zero']=True
            elif c=='a': o['binary']='text'
            elif c=='I': o['binary']='without'
            elif c=='A': o['after']=num(arg); o['a_explicit']=True
            elif c=='B': o['before']=num(arg); o['b_explicit']=True
            elif c=='C':
                n=num(arg)
                if not o['a_explicit']: o['after']=n
                if not o['b_explicit']: o['before']=n
            else: raise ValueError('unknown option')
        i+=1
    rest=av[i:]
    for pf in o['pfiles']:
        try:
            data=sys.stdin.buffer.read() if pf=='-' else open(pf,'rb').read()
        except OSError: raise ValueError('pattern file error')
        o['pats'] += split_patterns(data, True)
    if not o['pats'] and not o['pfiles']:
        if not rest: raise ValueError('no pattern')
        o['pats']=split_patterns(os.fsencode(rest[0])); rest=rest[1:]
    files=rest or ['-']
    if o['zero']: o['binary']='text'
    return o,files

class Matcher:
    def __init__(self,o):
        self.o=o; self.ps=o['pats']; self.rx=[]
        if o['mode']!='F':
            for p in self.ps: self.rx.append(Rx(p,o['mode']=='E',o['ignore']))
    @staticmethod
    def wordbyte(c): return c==95 or 48<=c<=57 or 65<=c<=90 or 97<=c<=122
    def valid(self,s,a,b):
        if self.o['line'] and (a!=0 or b!=len(s)): return False
        if self.o['word'] and not self.o['line']:
            if a and self.wordbyte(s[a-1]): return False
            if b<len(s) and self.wordbyte(s[b]): return False
        return True
    def search(self,s,start=0):
        best=None
        if self.o['mode']=='F':
            hay=s.lower() if self.o['ignore'] else s
            for p0 in self.ps:
                p=p0.lower() if self.o['ignore'] else p0
                pos=start
                while pos<=len(s):
                    a=hay.find(p,pos)
                    if a<0: break
                    b=a+len(p)
                    if self.valid(s,a,b):
                        q=(a,b)
                        if best is None or a<best[0] or (a==best[0] and b>best[1]): best=q
                        break
                    pos=a+1
        else:
            for r in self.rx:
                pos=start
                while pos<=len(s):
                    q=r.search(s,pos)
                    if q is None: break
                    a,b=q
                    if self.valid(s,a,b):
                        if best is None or a<best[0] or (a==best[0] and b>best[1]): best=q
                        break
                    # With -w, a shorter alternative at this same leftmost
                    # start can have valid word boundaries.
                    found=None
                    if self.o['word'] and not self.o['line']:
                        for e in range(b-1, a-1, -1):
                            if self.valid(s,a,e) and r.exact(s,a,e):
                                found=(a,e); break
                    if found is not None:
                        if best is None or a<best[0] or (a==best[0] and found[1]>best[1]): best=found
                        break
                    pos=a+1 if a<len(s) else len(s)+1
        return best

def records(data, delim, binary_split=False):
    out=[]; start=0; n=1
    seps={delim}
    if binary_split: seps={0,10}
    for i,c in enumerate(data):
        if c in seps:
            out.append((data[start:i],start,n)); start=i+1; n+=1
    if start<len(data): out.append((data[start:],start,n))
    return out

def main(av):
    try: o,files=parse(av); mat=Matcher(o)
    except Exception as e:
        sys.stderr.write('grep: '+str(e)+'\n'); return 2
    multi=len(files)>1
    showname = multi if o['fname'] is None else o['fname']
    delim=0 if o['zero'] else 10; odelim=bytes([delim]); output=bytearray()
    anysel=False; any_list_output=False; haderr=False; previous_group=False
    for fn in files:
        name=o['label'] if fn=='-' else os.fsencode(fn)
        try: data=sys.stdin.buffer.read() if fn=='-' else open(fn,'rb').read()
        except OSError as e:
            haderr=True
            if not o['silent']: sys.stderr.write('grep: %s: %s\n'%(fn,e.strerror))
            continue
        isbin=(not o['zero'] and b'\0' in data and o['binary']!='text')
        recs=records(data,delim,isbin and o['binary']=='binary')
        selected=[]; matches={}; count=0
        if o['max']!=0 and not (isbin and o['binary']=='without'):
            for idx,(line,off,ln) in enumerate(recs):
                q=mat.search(line); sel=(q is not None) ^ o['invert']
                if sel:
                    count+=1; selected.append(idx)
                    if q is not None: matches[idx]=q
                    if o['quiet']:
                        return 0
                    if isbin and o['binary']=='binary' and not o['count']: break
                    if o['max']>=0 and count>=o['max']: break
        if count: anysel=True
        # Filename-list and count modes.
        if o['quiet']: continue
        if o['listmode']:
            emit=(o['listmode']=='l' and count>0) or (o['listmode']=='L' and count==0)
            if emit:
                any_list_output=True
                output += name + (b'\0' if o['nullname'] else b'\n')
            continue
        if o['count']:
            if showname: output += name + (b'\0' if o['nullname'] else b':')
            output += str(count).encode()+b'\n'; continue
        if not selected: continue
        if isbin and o['binary']=='binary':
            output += b'Binary file '+name+b' matches\n'; continue
        def prefix(line_no,off,context=False):
            sep=b'-' if context else b':'
            z=bytearray()
            if showname: z += name + (b'\0' if o['nullname'] else sep)
            if o['lineno']: z += str(line_no).encode()+sep
            if o['byte']: z += str(off).encode()+sep
            if o['tab'] and z: z += b'\t'
            return z
        if o['only']:
            if o['invert']:
                continue
            for idx in selected:
                line,off,ln=recs[idx]; pos=0
                while pos<=len(line):
                    q=mat.search(line,pos)
                    if q is None: break
                    a,b=q
                    if b>a:
                        output += prefix(ln,off+a)+line[a:b]+odelim
                    pos=b if b>a else a+1
            continue
        wanted=set()
        for idx in selected:
            wanted.update(range(max(0,idx-o['before']),min(len(recs),idx+o['after']+1)))
        groups=[]
        for idx in sorted(wanted):
            if not groups or idx>groups[-1][-1]+1: groups.append([idx])
            else: groups[-1].append(idx)
        for g in groups:
            if previous_group and o['sep_on'] and (o['before'] or o['after']): output += o['sep']+b'\n'
            previous_group=True
            for idx in g:
                line,off,ln=recs[idx]
                output += prefix(ln,off,idx not in selected)+line+odelim
    sys.stdout.buffer.write(output)
    if haderr: return 2
    if o['listmode']:
        return 0 if any_list_output else 1
    return 0 if anysel else 1

if __name__=='__main__':
    sys.exit(main(sys.argv[1:]))
