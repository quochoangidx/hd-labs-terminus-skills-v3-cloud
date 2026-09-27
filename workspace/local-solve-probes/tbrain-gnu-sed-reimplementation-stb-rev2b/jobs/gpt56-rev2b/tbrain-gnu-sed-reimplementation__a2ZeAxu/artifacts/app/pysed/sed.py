#!/usr/bin/env python3
"""Small, pure Python implementation of the documented GNU sed 4.9 language."""
import sys, re

class SedError(Exception): pass

def escval(s, i, maxdigits=None):
    """Decode GNU numeric/simple escape beginning after backslash."""
    if i >= len(s): return '\\', i
    c=s[i]
    simple={'n':'\n','t':'\t','r':'\r','f':'\f','v':'\v','a':'\a','b':'\b'}
    if c in simple: return simple[c],i+1
    if c=='c' and i+1<len(s):
        x=s[i+1]
        if 'a'<=x<='z': x=x.upper()
        return chr(ord(x)^64),i+2
    bases={'d':10,'o':8,'x':16}
    if c in bases:
        base=bases[c]; j=i+1; lim=3 if c!='x' else 2
        good='0123456789abcdefABCDEF' if base==16 else ('01234567' if base==8 else '0123456789')
        while j<len(s) and j<i+1+lim and s[j] in good: j+=1
        if j>i+1: return chr(int(s[i+1:j],base)&255),j
    return c,i+1

def decode_chars(s):
    out=''; i=0
    while i<len(s):
        if s[i]=='\\': c,i=escval(s,i+1); out+=c
        else: out+=s[i]; i+=1
    return out

def numeric_escapes(p):
    out=''; i=0
    while i<len(p):
        if p[i]=='\\' and i+1<len(p) and p[i+1] in 'dox':
            v,j=escval(p,i+1); out+=v; i=j
        else: out+=p[i]; i+=1
    return out

def bre_to_py(p):
    p=numeric_escapes(p)
    """Translate GNU BRE syntax and its commonly documented extensions."""
    o=''; i=0; incls=False
    while i<len(p):
        c=p[i]
        if c=='[':
            # Parse bracket ourselves enough to normalize GNU classes/equivalence.
            j=i+1
            if j<len(p) and p[j]=='^': j+=1
            if j<len(p) and p[j]==']': j+=1
            while j<len(p):
                if p[j]=='[' and j+1<len(p) and p[j+1] in ':=.':
                    typ=p[j+1]; k=p.find(typ+']',j+2)
                    if k>=0: j=k+2; continue
                if p[j]==']': break
                j+=1
            if j>=len(p): o+='\\['; i+=1; continue
            z=p[i:j+1]
            classes={'alnum':'A-Za-z0-9','alpha':'A-Za-z','blank':' \\t','cntrl':'\\x00-\\x1f\\x7f',
             'digit':'0-9','graph':'!-~','lower':'a-z','print':' -~','punct':'!-/:-@[-`{-~',
             'space':'\\t\\n\\v\\f\\r ','upper':'A-Z','xdigit':'A-Fa-f0-9'}
            for n,v in classes.items(): z=z.replace('[:'+n+':]',v)
            z=re.sub(r'\[=([^]]+)=\]',lambda m: re.escape(m.group(1)),z)
            z=z.replace('[.','').replace('.]','')
            o+=z; i=j+1; continue
        if c=='\\' and i+1<len(p):
            n=p[i+1]
            if n in '(){}+?|': o+=n; i+=2; continue
            if n in '123456789': o+='\\'+n; i+=2; continue
            if n in '<>': o+=r'\b'; i+=2; continue
            if n=='b': o+=r'\b'; i+=2; continue
            if n=='B': o+=r'\B'; i+=2; continue
            if n=='w': o+=r'[A-Za-z0-9_]'; i+=2; continue
            if n=='W': o+=r'[^A-Za-z0-9_]'; i+=2; continue
            if n=='s': o+=r'[\t\n\v\f\r ]'; i+=2; continue
            if n=='S': o+=r'[^\t\n\v\f\r ]'; i+=2; continue
            if n in '`\'': o+=('\\A' if n=='`' else '\\Z'); i+=2; continue
            if n in 'dox':
                v,k=escval(p,i+1); o+=v; i=k; continue
            if n in 'ntrfvac':
                v,k=escval(p,i+1); o+=v; i=k; continue
            o+=re.escape(n); i+=2; continue
        if c in '+?(){}|': o+='\\'+c
        elif c=='*': o+='*'
        elif c=='^':
            prev=p[:i]
            special=(i==0 or prev.endswith('\\(') or prev.endswith('\\|'))
            o+=('^' if special else '\\^')
        elif c=='$':
            special=(i==len(p)-1 or p.startswith('\\)',i+1) or p.startswith('\\|',i+1))
            o+=('$' if special else '\\$')
        else: o+=c
        i+=1
    return o

def ere_to_py(p):
    p=numeric_escapes(p)
    o=''; i=0
    # BRE converter's bracket handling is useful, but ERE operators remain active.
    while i<len(p):
        if p[i]=='[':
            j=i+1
            if j<len(p) and p[j]=='^': j+=1
            if j<len(p) and p[j]==']': j+=1
            while j<len(p):
                if p[j]=='[' and j+1<len(p) and p[j+1] in ':=.':
                    t=p[j+1]; k=p.find(t+']',j+2)
                    if k>=0: j=k+2; continue
                if p[j]==']': break
                j+=1
            z=p[i:j+1] if j<len(p) else '\\['
            classes={'alnum':'A-Za-z0-9','alpha':'A-Za-z','blank':' \\t','cntrl':'\\x00-\\x1f\\x7f','digit':'0-9','graph':'!-~','lower':'a-z','print':' -~','punct':'!-/:-@[-`{-~','space':'\\t\\n\\v\\f\\r ','upper':'A-Z','xdigit':'A-Fa-f0-9'}
            for n,v in classes.items(): z=z.replace('[:'+n+':]',v)
            z=re.sub(r'\[=([^]]+)=\]',lambda m:re.escape(m.group(1)),z)
            o+=z; i=(j+1 if j<len(p) else i+1); continue
        if p[i]=='\\' and i+1<len(p):
            n=p[i+1]
            if n in '123456789': o+='\\'+n; i+=2; continue
            if n in '<>b': o+=r'\b'; i+=2; continue
            if n=='B': o+=r'\B'; i+=2; continue
            if n=='w': o+=r'[A-Za-z0-9_]'; i+=2; continue
            if n=='W': o+=r'[^A-Za-z0-9_]'; i+=2; continue
            if n=='s': o+=r'[\t\n\v\f\r ]'; i+=2; continue
            if n=='S': o+=r'[^\t\n\v\f\r ]'; i+=2; continue
            if n in '`\'': o+=('\\A' if n=='`' else '\\Z'); i+=2; continue
            if n in 'doxntrfvac': v,k=escval(p,i+1); o+=v; i=k; continue
            o+=re.escape(n); i+=2; continue
        o+=p[i]; i+=1
    return o

class RX:
    def __init__(self,p,ext=False,flags=''):
        self.src=p; self.py=(ere_to_py(p) if ext else bre_to_py(p)); self.cache={}; self.fl=re.ASCII|(re.I if 'I' in flags or 'i' in flags else 0)|(re.M if 'M' in flags or 'm' in flags else 0)
    def search(self,s,start=0):
        # Determine leftmost start, then longest end. Lookahead pins the endpoint
        # without changing ^/$ and boundary context as slicing would.
        for a in range(start,len(s)+1):
            for b in range(len(s),a-1,-1):
                try:
                    rem=len(s)-b
                    if rem not in self.cache: self.cache[rem]=re.compile('(?:'+self.py+')(?=[\\s\\S]{'+str(rem)+'}\\Z)',self.fl)
                    m=self.cache[rem].match(s,a)
                except re.error as e: raise SedError(str(e))
                if m and m.end()==b: return m
        return None

class Addr:
    def __init__(self,kind,val=None,mod=''): self.kind,self.val,self.mod=kind,val,mod
    def hit(self,ed):
        n=ed.lineno
        if self.kind=='num': return n==self.val
        if self.kind=='last': return ed.islast
        if self.kind=='step': a,b=self.val; return n>=a and (n-a)%b==0
        if self.kind=='rx': return ed.matchrx(self.val,self.mod) is not None
        return False

class Cmd:
    def __init__(self,op,a1=None,a2=None,neg=False,arg=None):
        self.op,self.a1,self.a2,self.neg,self.arg=op,a1,a2,neg,arg; self.active=(a1 is not None and a2 is not None and a1.kind=='num' and a1.val==0); self.range_first=False; self.range_last=False

class Parser:
    def __init__(self,s,ext=False): self.s=s; self.i=0; self.ext=ext; self.cmd=[]; self.labels={}; self.fix=[]
    def skip(self):
        while self.i<len(self.s) and self.s[self.i] in ' \t;\n': self.i+=1
    def regex_delim(self,d):
        out=''; bracket=False
        while self.i<len(self.s):
            c=self.s[self.i]; self.i+=1
            if c=='\\' and self.i<len(self.s): out+=c+self.s[self.i]; self.i+=1; continue
            if c=='[': bracket=True
            if c==']': bracket=False
            if c==d and not bracket: return out
            out+=c
        raise SedError('unterminated regexp')
    def addr(self):
        if self.i>=len(self.s): return None
        c=self.s[self.i]
        if c.isdigit():
            j=self.i
            while self.i<len(self.s) and self.s[self.i].isdigit(): self.i+=1
            a=int(self.s[j:self.i])
            if self.i<len(self.s) and self.s[self.i]=='~':
                self.i+=1; j=self.i
                while self.i<len(self.s) and self.s[self.i].isdigit(): self.i+=1
                return Addr('step',(a,int(self.s[j:self.i])))
            return Addr('num',a)
        if c=='$': self.i+=1; return Addr('last')
        if c=='/' or c=='\\':
            if c=='\\':
                self.i+=1
                if self.i>=len(self.s): return None
                d=self.s[self.i]; self.i+=1
            else: d='/'; self.i+=1
            p=self.regex_delim(d); j=self.i
            while self.i<len(self.s) and self.s[self.i] in 'IMim': self.i+=1
            return Addr('rx',p,self.s[j:self.i])
        return None
    def textarg(self):
        while self.i<len(self.s) and self.s[self.i] in ' \t': self.i+=1
        if self.i<len(self.s) and self.s[self.i]=='\\':
            self.i+=1
            if self.i<len(self.s) and self.s[self.i]=='\n': self.i+=1
        out=''
        while self.i<len(self.s):
            c=self.s[self.i]; self.i+=1
            if c=='\\' and self.i<len(self.s) and self.s[self.i]=='\n': out+='\n'; self.i+=1; continue
            if c=='\n': break
            out+=c
        return out
    def parse(self):
        while self.i<len(self.s):
            self.skip()
            if self.i>=len(self.s): break
            if self.s[self.i]=='#':
                while self.i<len(self.s) and self.s[self.i]!='\n': self.i+=1
                continue
            a1=self.addr(); a2=None
            while self.i<len(self.s) and self.s[self.i] in ' \t': self.i+=1
            if a1 and self.i<len(self.s) and self.s[self.i]==',':
                self.i+=1
                while self.i<len(self.s) and self.s[self.i] in ' \t': self.i+=1
                if self.i<len(self.s) and self.s[self.i]=='+':
                    self.i+=1; j=self.i
                    while self.i<len(self.s) and self.s[self.i].isdigit(): self.i+=1
                    a2=Addr('plus',int(self.s[j:self.i]))
                elif self.i<len(self.s) and self.s[self.i]=='~':
                    self.i+=1; j=self.i
                    while self.i<len(self.s) and self.s[self.i].isdigit(): self.i+=1
                    a2=Addr('tilde',int(self.s[j:self.i]))
                else: a2=self.addr()
            while self.i<len(self.s) and self.s[self.i] in ' \t': self.i+=1
            neg=False
            if self.i<len(self.s) and self.s[self.i]=='!': neg=True; self.i+=1
            while self.i<len(self.s) and self.s[self.i] in ' \t': self.i+=1
            if self.i>=len(self.s): break
            op=self.s[self.i]; self.i+=1; arg=None
            if op in 'aic': arg=self.textarg()
            elif op=='s':
                if self.i>=len(self.s): raise SedError('bad s')
                d=self.s[self.i]; self.i+=1; pat=self.regex_delim(d); rep=self.regex_delim(d)
                j=self.i
                while self.i<len(self.s) and self.s[self.i] not in ';\n \t': self.i+=1
                arg=(pat,rep,self.s[j:self.i])
            elif op=='y':
                d=self.s[self.i]; self.i+=1; x=self.regex_delim(d); y=self.regex_delim(d); arg=(decode_chars(x),decode_chars(y))
            elif op in 'btT:':
                while self.i<len(self.s) and self.s[self.i] in ' \t': self.i+=1
                j=self.i
                while self.i<len(self.s) and self.s[self.i] not in ';\n': self.i+=1
                arg=self.s[j:self.i].strip()
            elif op in 'qQ':
                while self.i<len(self.s) and self.s[self.i] in ' \t': self.i+=1
                j=self.i
                while self.i<len(self.s) and self.s[self.i].isdigit(): self.i+=1
                arg=int(self.s[j:self.i] or '0')
            elif op=='l':
                j=self.i
                while self.i<len(self.s) and self.s[self.i].isdigit(): self.i+=1
                arg=int(self.s[j:self.i] or '70')
            elif op=='{': pass
            elif op=='}': pass
            elif op not in '=dDgGhHlnNpPqQxz': raise SedError('unknown command '+op)
            c=Cmd(op,a1,a2,neg,arg); self.cmd.append(c)
            if op==':': self.labels[arg]=len(self.cmd)
            if op in 'btT': self.fix.append(c)
        for c in self.fix: c.arg=(self.labels.get(c.arg,len(self.cmd)) if c.arg else len(self.cmd))
        # Resolve braces into conditional jumps.
        st=[]
        for k,c in enumerate(self.cmd):
            if c.op=='{': st.append(k)
            elif c.op=='}' and st:
                q=st.pop(); self.cmd[q].arg=k+1
        return self.cmd

class Editor:
    def __init__(self,cmd,quiet=False,ext=False,sep=False):
        self.cmd=cmd; self.quiet=quiet; self.ext=ext; self.sep=sep; self.hold=''; self.out=[]; self.lastpat=''; self.lineno=0; self.islast=False; self.ps=''; self.subbed=False; self.queue=[]; self.exitcode=None; self.rxcache={}
    def emit(self,s): self.out.append(s)
    def rx(self,p,mods=''):
        if p=='': p=self.lastpat
        else: self.lastpat=p
        key=(p,mods)
        if key not in self.rxcache: self.rxcache[key]=RX(p,self.ext,mods)
        return self.rxcache[key]
    def matchrx(self,p,mods=''): return self.rx(p,mods).search(self.ps)
    def selected(self,c):
        c.range_first=False; c.range_last=False
        if not c.a1: hit=True
        elif not c.a2: hit=c.a1.hit(self)
        elif c.active:
            hit=True
            if c.a2.kind=='plus': end=(self.lineno>=c._end)
            elif c.a2.kind=='tilde': end=(self.lineno % c.a2.val == 0)
            else: end=c.a2.hit(self)
            if end: c.active=False; c.range_last=True
        else:
            hit=c.a1.hit(self)
            if hit:
                c.range_first=True; c.active=True
                if c.a2.kind=='plus':
                    c._end=self.lineno+c.a2.val
                    end=(c.a2.val==0)
                elif c.a2.kind=='tilde': end=(self.lineno % c.a2.val == 0)
                elif c.a2.kind=='rx': end=False
                elif c.a2.kind=='num': end=(c.a2.val<=self.lineno)
                else: end=c.a2.hit(self)
                if end: c.active=False; c.range_last=True
        return (not hit) if c.neg else hit

    def replacement(self,rep,m):
        out=''; i=0; persistent=None; one=None
        def apply(z):
            nonlocal one
            if not z: return z
            if persistent=='low': z=z.lower()
            elif persistent=='up': z=z.upper()
            if one=='low': z=z[:1].lower()+z[1:]; one=None
            elif one=='up': z=z[:1].upper()+z[1:]; one=None
            return z
        while i<len(rep):
            c=rep[i]
            if c=='&': z=m.group(0); i+=1
            elif c=='\\' and i+1<len(rep):
                n=rep[i+1]; i+=2
                if n.isdigit() and n!='0':
                    try: z=m.group(int(n)) or ''
                    except IndexError: z=''
                elif n=='L': persistent='low'; z=''
                elif n=='U': persistent='up'; z=''
                elif n=='E': persistent=None; z=''
                elif n=='l': one='low'; z=''
                elif n=='u': one='up'; z=''
                elif n in 'ntrfvadoxc':
                    z,k=escval(rep,i-1); i=k
                else: z=n
            else: z=c; i+=1
            out+=apply(z)
        return out

    def subst(self,arg):
        pat,rep,fl=arg; rx=self.rx(pat,fl); glob='g' in fl; nums=re.findall(r'\d+',fl); nth=int(nums[-1]) if nums else 1
        pos=0; count=0; out=''; changed=False; nonempty_end=-1
        while pos<=len(self.ps):
            m=rx.search(self.ps,pos)
            if not m: break
            count+=1
            if glob and m.start()==m.end()==nonempty_end:
                if pos<len(self.ps): out+=self.ps[pos]; pos+=1; nonempty_end=-1; continue
                break
            do=(count>=nth if glob else count==nth)
            if do:
                out+=self.ps[pos:m.start()]+self.replacement(rep,m); changed=True; pos=m.end()
                if m.end()>m.start(): nonempty_end=m.end()
            else: out+=self.ps[pos:m.end()]; pos=m.end()
            if m.end()==m.start():
                if pos<len(self.ps): out+=self.ps[pos]; pos+=1
                else: break
            if changed and not glob: break
        if changed:
            out+=self.ps[pos:]; self.ps=out; self.subbed=True
            if 'p' in fl: self.emit(self.ps+'\n')
            if 'P' in fl: self.emit(self.ps.split('\n',1)[0]+'\n')
    def listed(self,n):
        mp={'\a':'\\a','\b':'\\b','\f':'\\f','\n':'\\n','\r':'\\r','\t':'\\t','\v':'\\v','\\':'\\\\'}; units=[]
        for c in self.ps:
            if c in mp: units.append(mp[c])
            elif ord(c)<32 or ord(c)>=127: units.append('\\%03o'%ord(c))
            else: units.append(c)
        if n==0: return ''.join(units)+'$\n'
        lines=[]; cur=''
        for z in units:
            if len(cur)+len(z)>n-1: lines.append(cur+'\\'); cur=''
            cur+=z
        lines.append(cur+'$'); return '\n'.join(lines)+'\n'
    def cycle(self,line,reader):
        self.ps=line; self.subbed=False; self.queue=[]; pc=0; deleted=False; quitall=False
        while pc<len(self.cmd):
            c=self.cmd[pc]; pc+=1
            if c.op=='}': continue
            sel=self.selected(c)
            if c.op=='{' and not sel: pc=c.arg; continue
            if c.op=='{' or not sel: continue
            o=c.op
            if o=='s': self.subst(c.arg)
            elif o=='y': self.ps=self.ps.translate(str.maketrans(c.arg[0],c.arg[1]))
            elif o=='p': self.emit(self.ps+'\n')
            elif o=='P': self.emit(self.ps.split('\n',1)[0]+'\n')
            elif o=='=': self.emit(str(self.lineno)+'\n')
            elif o=='l': self.emit(self.listed(c.arg))
            elif o=='a': self.queue.append(c.arg+'\n')
            elif o=='i': self.emit(c.arg+'\n')
            elif o=='c':
                self.ps=c.arg
                if not c.a2 or c.neg or c.range_last: self.emit(self.ps+'\n')
                deleted=True; break
            elif o=='d': deleted=True; break
            elif o=='D':
                if '\n' in self.ps: self.ps=self.ps.split('\n',1)[1]; pc=0
                else: deleted=True; break
            elif o=='h': self.hold=self.ps
            elif o=='H': self.hold+='\n'+self.ps
            elif o=='g': self.ps=self.hold
            elif o=='G': self.ps+='\n'+self.hold
            elif o=='x': self.ps,self.hold=self.hold,self.ps
            elif o=='z': self.ps=''
            elif o in 'b': pc=c.arg
            elif o=='t':
                if self.subbed: self.subbed=False; pc=c.arg
            elif o=='T':
                if not self.subbed: pc=c.arg
                self.subbed=False
            elif o in 'qQ':
                if o=='Q': deleted=True
                self.exitcode=c.arg
                quitall=True; break
            elif o=='n':
                if not self.quiet: self.emit(self.ps+'\n')
                self.emit(''.join(self.queue)); self.queue=[]
                z=reader()
                if z is None: deleted=True; quitall=True; break
                self.ps=z; self.lineno+=1; self.subbed=False
            elif o=='N':
                z=reader()
                if z is None: quitall=True; break
                self.ps+='\n'+z; self.lineno+=1; self.subbed=False
        if not deleted and not self.quiet: self.emit(self.ps+'\n')
        self.emit(''.join(self.queue))
        return quitall

def main(argv):
    quiet=ext=sep=False; pieces=[]; files=[]; i=0
    while i<len(argv):
        a=argv[i]
        if a=='-n': quiet=True
        elif a=='-E': ext=True
        elif a=='-s': sep=True
        elif a=='-e':
            i+=1
            if i>=len(argv): return 1
            pieces.append(argv[i])
        else:
            if not pieces: pieces.append(a)
            else: files=argv[i:]; break
        i+=1
    if not pieces: return 1
    script='\n'.join(pieces)
    if script.startswith('#n'): quiet=True
    try: cmd=Parser(script,ext).parse()
    except Exception as e: sys.stderr.write('sed: '+str(e)+'\n'); return 1
    ed=Editor(cmd,quiet,ext,sep); status=0
    sources=[]
    if files:
        for f in files:
            try:
                with open(f,'rb') as h: sources.append((f,h.read().decode('latin1').split('\n')[:-1]))
            except OSError as e: sys.stderr.write('sed: '+str(e)+'\n'); status=2
    else: sources=[('-',sys.stdin.buffer.read().decode('latin1').split('\n')[:-1])]
    if not sep and len(sources)>1:
        all_lines=[]
        for _,ls in sources: all_lines.extend(ls)
        sources=[('',all_lines)]
    stop=False
    for si,(name,lines) in enumerate(sources):
        if sep:
            ed.lineno=0
            for c in cmd:
                c.active=(c.a1 is not None and c.a2 is not None and c.a1.kind=='num' and c.a1.val==0)
        idx=0
        def reader():
            nonlocal idx
            if idx>=len(lines): return None
            z=lines[idx]; idx+=1; ed.islast=(idx==len(lines)); return z
        while idx<len(lines):
            z=reader(); ed.lineno+=1
            if ed.cycle(z,reader): stop=True; break
        if stop: break
    sys.stdout.buffer.write(''.join(ed.out).encode('latin1'))
    return ed.exitcode if ed.exitcode is not None else status
if __name__=='__main__':
    try: sys.exit(main(sys.argv[1:]))
    except BrokenPipeError: sys.exit(0)
