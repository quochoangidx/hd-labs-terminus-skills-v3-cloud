#!/usr/bin/env python3
"""Small, pure Python implementation of the documented GNU sed subset."""
import sys, re

class SedError(Exception): pass

def escseq(s, i, regex=False):
    """Return (character or None, new index). None means preserve backslash."""
    if i >= len(s): return None, i
    c=s[i]
    simple={'a':'\a','f':'\f','n':'\n','r':'\r','t':'\t','v':'\v'}
    if c in simple: return simple[c], i+1
    bases={'d':10,'o':8,'x':16}
    if c in bases:
        base=bases[c]; lim=2 if c=='x' else 3; j=i+1
        valid='0123456789abcdefABCDEF' if base==16 else ('01234567' if base==8 else '0123456789')
        while j<len(s) and j<i+1+lim and s[j] in valid: j+=1
        if j>i+1: return chr(int(s[i+1:j],base)&255),j
    return None,i

def decode_text(s):
    out=[]; i=0
    while i<len(s):
        if s[i]=='\\':
            v,j=escseq(s,i+1)
            if v is not None: out.append(v); i=j; continue
            if i+1<len(s): out.append(s[i+1]); i+=2; continue
        out.append(s[i]); i+=1
    return ''.join(out)

POSIX_CLASSES={
 'alnum':'A-Za-z0-9','alpha':'A-Za-z','blank':' \\t','cntrl':'\\x00-\\x1f\\x7f',
 'digit':'0-9','graph':'!-~','lower':'a-z','print':' -~','punct':r'!-/:-@[-`{-~',
 'space':'\\t\\n\\v\\f\\r ','upper':'A-Z','xdigit':'A-Fa-f0-9'
}

def bracket(src,i):
    # i points after '['; return translated class and index after ']'
    neg=''
    if i<len(src) and src[i]=='^': neg='^'; i+=1
    out=[]
    if i<len(src) and src[i]==']': out.append(r'\]'); i+=1
    while i<len(src):
        if src[i]==']': return '['+neg+''.join(out)+']',i+1
        if src.startswith('[:',i):
            k=src.find(':]',i+2)
            if k>=0 and src[i+2:k] in POSIX_CLASSES:
                out.append(POSIX_CLASSES[src[i+2:k]]); i=k+2; continue
        if src.startswith('[=',i):
            k=src.find('=]',i+2)
            if k>=0:
                out.append(re.escape(src[i+2:k])); i=k+2; continue
        if src.startswith('[.',i):
            k=src.find('.]',i+2)
            if k>=0:
                out.append(re.escape(src[i+2:k])); i=k+2; continue
        c=src[i]
        if c=='\\' and i+1<len(src):
            n=src[i+1]
            if n in 'dDsSwW': out.append('\\'+n); i+=2; continue
            if n in ']-\\^': out.append('\\'+n); i+=2; continue
            out.append(re.escape(n)); i+=2; continue
        if c=='[': out.append(r'\[')
        elif c=='\\': out.append(r'\\')
        else: out.append(c)
        i+=1
    return r'\[',i

def preprocess_regex(src):
    # Section 5.8 escapes are expanded before regexp syntax is parsed.  This
    # deliberately lets, e.g., \x5e become the anchor ^ and \x5b open a class.
    out=[]; i=0
    while i<len(src):
        if src[i]=='\\' and i+1<len(src):
            v,j=escseq(src,i+1,True)
            if v is not None:
                out.append(v); i=j; continue
            out.extend(('\\',src[i+1])); i+=2; continue
        out.append(src[i]); i+=1
    return ''.join(out)

def regex_translate(src, extended=False):
    src=preprocess_regex(src)
    out=[]; i=0
    while i<len(src):
        c=src[i]
        if c=='[':
            x,i=bracket(src,i+1); out.append(x); continue
        if c=='\\':
            if i+1>=len(src): out.append(r'\\'); break
            n=src[i+1]
            if n in '123456789': out.append('\\'+n); i+=2; continue
            if n in 'bB': out.append('\\'+n); i+=2; continue
            if n=='w': out.append('[A-Za-z0-9_]'); i+=2; continue
            if n=='W': out.append('[^A-Za-z0-9_]'); i+=2; continue
            if n=='s': out.append('[\\t\\n\\v\\f\\r ]'); i+=2; continue
            if n=='S': out.append('[^\\t\\n\\v\\f\\r ]'); i+=2; continue
            if n=='<': out.append(r'(?<![A-Za-z0-9_])(?=[A-Za-z0-9_])'); i+=2; continue
            if n=='>': out.append(r'(?<=[A-Za-z0-9_])(?![A-Za-z0-9_])'); i+=2; continue
            if n=='`': out.append(r'\A'); i+=2; continue
            if n=="'": out.append(r'\Z'); i+=2; continue
            if not extended and n in '()|+?': out.append(n); i+=2; continue
            if not extended and n in '{}': out.append(n); i+=2; continue
            out.append(re.escape(n)); i+=2; continue
        if not extended and c=='^':
            special=(i==0 or (i>=2 and src[i-2:i] in ('\\(','\\|')))
            out.append('^' if special else '\\^')
        elif not extended and c=='$':
            special=(i==len(src)-1 or src[i+1:i+3] in ('\\)','\\|'))
            out.append('$' if special else '\\$')
        elif not extended and c in '()+?|{}': out.append('\\'+c)
        else: out.append(c)
        i+=1
    return ''.join(out)

class RX:
    def __init__(self,src,extended=False,mods=''):
        self.src=src; self.mods=mods
        flags=re.ASCII|re.S
        if 'I' in mods or 'i' in mods: flags|=re.I
        if 'M' in mods or 'm' in mods: flags|=re.M
        p=regex_translate(src,extended)
        if 'M' not in mods and 'm' not in mods:
            # Unescaped dollar outside brackets is translated in a small scan below.
            q=[]; bracketed=False; escaped=False
            for ch in p:
                if escaped: q.append(ch); escaped=False; continue
                if ch=='\\': q.append(ch); escaped=True; continue
                if ch=='[': bracketed=True
                elif ch==']': bracketed=False
                if ch=='$' and not bracketed: q.append('\\Z')
                else: q.append(ch)
            p=''.join(q)
        self.pattern=p; self.extended=extended
        try:
            self.re=re.compile(p,flags)
            self.end=re.compile('(?:'+p+r')(?=\Z)',flags)
            self._end_cache={}
        except re.error as e: raise SedError(str(e))
    def search(self,text,pos=0):
        # POSIX leftmost-longest.  The suffix assertion constrains the end while
        # matching against the original string, so ^, $, and \Z retain meaning.
        n=len(text)
        for st in range(pos,n+1):
            for en in range(n,st-1,-1):
                tail=n-en
                q=self._end_cache.get(tail)
                if q is None:
                    q=re.compile('(?:'+self.pattern+
                                 r')(?=[\s\S]{'+str(tail)+r'}\Z)', self.re.flags)
                    self._end_cache[tail]=q
                m=q.match(text,st)
                if m is not None: return m
        return None

class Addr:
    def __init__(self,kind,val=None): self.kind=kind; self.val=val
    def match(self,ctx,cmd):
        k=self.kind
        if k=='num': return ctx.lineno==self.val
        if k=='last': return ctx.islast
        if k=='step':
            first,step=self.val
            return ctx.lineno>=first and (ctx.lineno-first)%step==0
        if k=='rx': return self.val.search(ctx.pat) is not None
        return False

class Cmd:
    def __init__(self,op,a1=None,a2=None,bang=False,arg=None):
        self.op=op; self.a1=a1; self.a2=a2; self.bang=bang; self.arg=arg
        self.active=bool(a2 is not None and a1 is not None and a1.kind=='num' and a1.val==0)

class Parser:
    def __init__(self,s,extended=False): self.s=s; self.i=0; self.extended=extended; self.last_rx=None
    def skipws(self):
        while self.i<len(self.s) and self.s[self.i] in ' \t\r': self.i+=1
    def delimited(self,delim):
        o=[]
        while self.i<len(self.s):
            c=self.s[self.i]; self.i+=1
            if c==delim: return ''.join(o)
            if c=='\\' and self.i<len(self.s):
                n=self.s[self.i]
                if n==delim: o.extend(['\\',n]); self.i+=1
                else: o.extend(['\\',n]); self.i+=1
            else: o.append(c)
        raise SedError('unterminated expression')
    def address(self):
        self.skipws()
        if self.i>=len(self.s): return None
        c=self.s[self.i]
        if c.isdigit():
            j=self.i
            while self.i<len(self.s) and self.s[self.i].isdigit(): self.i+=1
            n=int(self.s[j:self.i])
            if self.i<len(self.s) and self.s[self.i]=='~':
                self.i+=1; j=self.i
                while self.i<len(self.s) and self.s[self.i].isdigit(): self.i+=1
                return Addr('step',(n,int(self.s[j:self.i])))
            return Addr('num',n)
        if c=='$': self.i+=1; return Addr('last')
        if c=='/':
            self.i+=1; x=self.delimited('/'); mods=''
            while self.i<len(self.s) and self.s[self.i] in 'IMim': mods+=self.s[self.i]; self.i+=1
            
            rx=self.last_rx if x=='' and self.last_rx is not None else RX(x,self.extended,mods)
            if x!='': self.last_rx=rx
            return Addr('rx',rx)
        if c=='\\' and self.i+1<len(self.s):
            d=self.s[self.i+1]; self.i+=2; x=self.delimited(d); mods=''
            while self.i<len(self.s) and self.s[self.i] in 'IMim': mods+=self.s[self.i]; self.i+=1
            
            rx=self.last_rx if x=='' and self.last_rx is not None else RX(x,self.extended,mods)
            if x!='': self.last_rx=rx
            return Addr('rx',rx)
        return None
    def textarg(self):
        # One-line extension or traditional backslash-newline form. A trailing
        # backslash continues text onto another script line and is removed.
        self.skipws()
        if self.i<len(self.s) and self.s[self.i]=='\\':
            self.i+=1
            if self.i<len(self.s) and self.s[self.i]=='\n': self.i+=1
        out=[]
        while self.i<len(self.s):
            j=self.i
            while self.i<len(self.s) and self.s[self.i]!='\n': self.i+=1
            line=self.s[j:self.i]
            if line.endswith('\\') and self.i<len(self.s):
                out.append(line[:-1]); out.append('\n'); self.i+=1; continue
            out.append(line); break
        return decode_text(''.join(out))
    def subst(self):
        if self.i>=len(self.s): raise SedError('missing delimiter')
        d=self.s[self.i]; self.i+=1
        pat=self.delimited(d); rep=self.delimited(d); flags=''; num=None
        while self.i<len(self.s) and self.s[self.i] not in ';\n}':
            c=self.s[self.i]
            if c.isdigit():
                j=self.i
                while self.i<len(self.s) and self.s[self.i].isdigit(): self.i+=1
                num=int(self.s[j:self.i]); continue
            if c in 'gpIMim': flags+=c; self.i+=1; continue
            if c in ' \t\r': self.i+=1; continue
            break
        rx=self.last_rx if pat=='' and self.last_rx is not None else RX(pat,self.extended,flags)
        if pat!='': self.last_rx=rx
        return (rx,rep,flags,num)
    def trans(self):
        d=self.s[self.i]; self.i+=1
        a=decode_text(self.delimited(d)); b=decode_text(self.delimited(d))
        return (a,b)
    def parse(self,endblock=False):
        out=[]
        while self.i<len(self.s):
            while self.i<len(self.s) and self.s[self.i] in ';\n \t\r': self.i+=1
            if self.i>=len(self.s): break
            if self.s[self.i]=='#':
                while self.i<len(self.s) and self.s[self.i]!='\n': self.i+=1
                continue
            if self.s[self.i]=='}':
                self.i+=1
                if endblock: break
                continue
            a1=self.address(); self.skipws(); a2=None
            if self.i<len(self.s) and self.s[self.i]==',':
                self.i+=1; self.skipws()
                if self.i<len(self.s) and self.s[self.i]=='+':
                    self.i+=1; j=self.i
                    while self.i<len(self.s) and self.s[self.i].isdigit(): self.i+=1
                    a2=Addr('plus',int(self.s[j:self.i]))
                elif self.i<len(self.s) and self.s[self.i]=='~':
                    self.i+=1; j=self.i
                    while self.i<len(self.s) and self.s[self.i].isdigit(): self.i+=1
                    a2=Addr('untilmod',int(self.s[j:self.i]))
                else: a2=self.address()
            self.skipws(); bang=False
            if self.i<len(self.s) and self.s[self.i]=='!': bang=True; self.i+=1; self.skipws()
            if self.i>=len(self.s): break
            op=self.s[self.i]; self.i+=1; arg=None
            if op=='{': arg=self.parse(True)
            elif op in 'aic': arg=self.textarg()
            elif op in ':btT':
                self.skipws(); j=self.i
                while self.i<len(self.s) and self.s[self.i] not in ';\n} \t\r': self.i+=1
                arg=self.s[j:self.i]
            elif op=='s': arg=self.subst()
            elif op=='y': arg=self.trans()
            elif op=='l':
                self.skipws(); j=self.i
                while self.i<len(self.s) and self.s[self.i].isdigit(): self.i+=1
                arg=int(self.s[j:self.i]) if self.i>j else 70
            elif op in 'qQ':
                self.skipws(); j=self.i
                while self.i<len(self.s) and self.s[self.i].isdigit(): self.i+=1
                arg=int(self.s[j:self.i]) if self.i>j else 0
            elif op=='=': pass
            elif op not in 'dDgGhHnNpPxz':
                raise SedError('unknown command '+op)
            out.append(Cmd(op,a1,a2,bang,arg))
        return out

def selected(c,ctx):
    if c.a1 is None:
        yes=True
    elif c.a2 is None:
        yes=c.a1.match(ctx,c)
    else:
        just=False
        if c.active:
            yes=True
        elif c.a1.match(ctx,c):
            yes=True; just=True
        else:
            yes=False
        if yes:
            end=False
            if c.active:                         # range started earlier
                if c.a2.kind=='plus': end=ctx.lineno>=c.range_end
                elif c.a2.kind=='untilmod': end=(ctx.lineno%c.a2.val)==0
                else: end=c.a2.match(ctx,c)
            elif just:
                if c.a2.kind=='plus':
                    c.range_end=ctx.lineno+c.a2.val
                    end=c.a2.val==0
                elif c.a2.kind=='untilmod': end=False
                elif c.a2.kind=='num': end=ctx.lineno>=c.a2.val
                else: end=False                  # regex tested from next line
            if end: c.active=False
            else: c.active=True
    return (not yes) if c.bang else yes

def replacement(rep,m):
    out=[]; i=0; mode=None; once=None
    def put(x):
        nonlocal once
        if once=='lower' and x: x=x[0].lower()+x[1:]; once=None
        elif once=='upper' and x: x=x[0].upper()+x[1:]; once=None
        if mode=='lower': x=x.lower()
        elif mode=='upper': x=x.upper()
        out.append(x)
    while i<len(rep):
        c=rep[i]
        if c=='&': put(m.group(0)); i+=1; continue
        if c=='\\' and i+1<len(rep):
            n=rep[i+1]; i+=2
            if n.isdigit() and n!='0':
                try: put(m.group(int(n)) or '')
                except IndexError: put('')
            elif n=='L': mode='lower'
            elif n=='U': mode='upper'
            elif n=='E': mode=None
            elif n=='l': once='lower'
            elif n=='u': once='upper'
            else:
                v,j=escseq(rep,i-1)
                if v is not None: put(v); i=j
                else: put(n)
            continue
        put(c); i+=1
    return ''.join(out)

def substitute(text,arg):
    rx,rep,flags,num=arg; matches=[]; pos=0
    while pos<=len(text):
        m=rx.search(text,pos)
        if not m: break
        matches.append(m)
        pos=m.end() if m.end()>m.start() else m.end()+1
    if not matches: return text,False
    chosen=[]
    if num is not None:
        if 1<=num<=len(matches):
            chosen=matches[num-1:] if 'g' in flags else [matches[num-1]]
    elif 'g' in flags: chosen=matches
    else: chosen=[matches[0]]
    if not chosen: return text,False
    out=[]; last=0
    for m in chosen:
        out.append(text[last:m.start()]); out.append(replacement(rep,m)); last=m.end()
    out.append(text[last:])
    return ''.join(out),True

def listline(s,width):
    parts=[]
    for ch in s:
        o=ord(ch)
        mp={'\a':r'\a','\b':r'\b','\f':r'\f','\n':r'\n','\r':r'\r','\t':r'\t','\v':r'\v','\\':r'\\'}
        if ch in mp: parts.append(mp[ch])
        elif 32<=o<127: parts.append(ch)
        else: parts.append('\\%03o'%o)
    parts.append('$')
    if not width: return ''.join(parts)+'\n'
    out=''; col=0
    for x in parts:
        if col+len(x)>width-1:
            out+='\\\n'; col=0
        out+=x; col+=len(x)
    return out+'\n'

class Context:
    pass

class Engine:
    def __init__(self,cmds,quiet,separate,records):
        self.cmds=cmds; self.quiet=quiet; self.separate=separate; self.records=records
        self.hold=''; self.out=[]; self.exit=0; self.stop=False; self.serial=0
        self.labels={}; self.flatten_labels(cmds)
    def reset_ranges(self,cs):
        for c in cs:
            c.active=bool(c.a2 is not None and c.a1 is not None and c.a1.kind=='num' and c.a1.val==0)
            if c.op=='{': self.reset_ranges(c.arg)
    def flatten_labels(self,cs):
        for i,c in enumerate(cs):
            if c.op==':': self.labels[c.arg]=(cs,i)
            if c.op=='{': self.flatten_labels(c.arg)
    def emit(self,s): self.out.append(s)
    def runlist(self,cs,ctx,start=0):
        i=start
        while i<len(cs):
            c=cs[i]; i+=1
            if not selected(c,ctx): continue
            op=c.op
            if op=='{':
                r=self.runlist(c.arg,ctx)
                if r: return r
            elif op==':': pass
            elif op=='a': ctx.queue.append(c.arg+'\n')
            elif op=='i': self.emit(c.arg+'\n')
            elif op=='c':
                # Print replacement only when range closes (or for a single address).
                if c.a2 is None or not c.active: self.emit(c.arg+'\n')
                return 'delete'
            elif op=='d': return 'delete'
            elif op=='D':
                if '\n' in ctx.pat:
                    ctx.pat=ctx.pat.split('\n',1)[1:][0]; return 'restart'
                return 'delete'
            elif op=='g': ctx.pat=self.hold
            elif op=='G': ctx.pat+='\n'+self.hold
            elif op=='h': self.hold=ctx.pat
            elif op=='H': self.hold+='\n'+ctx.pat
            elif op=='x': ctx.pat,self.hold=self.hold,ctx.pat
            elif op=='z': ctx.pat=''
            elif op=='p': self.emit(ctx.pat+'\n')
            elif op=='P': self.emit(ctx.pat.split('\n',1)[0]+'\n')
            elif op=='=': self.emit(str(ctx.lineno)+'\n')
            elif op=='l': self.emit(listline(ctx.pat,c.arg))
            elif op=='s':
                ctx.pat,ok=substitute(ctx.pat,c.arg)
                if ok:
                    ctx.subbed=True
                    if 'p' in c.arg[2]: self.emit(ctx.pat+'\n')
            elif op=='y':
                a,b=c.arg; table={ord(x):y for x,y in zip(a,b)}; ctx.pat=ctx.pat.translate(table)
            elif op in 'b tT':
                take=op=='b' or (op=='t' and ctx.subbed) or (op=='T' and not ctx.subbed)
                if op in 'tT': ctx.subbed=False
                if take:
                    if not c.arg: return 'end'
                    target=self.labels.get(c.arg)
                    if target and target[0] is cs: i=target[1]+1
                    else: return ('branch',target)
            elif op=='n':
                if not self.quiet: self.emit(ctx.pat+'\n')
                self.emit(''.join(ctx.queue)); ctx.queue=[]
                if not self.loadnext(ctx): return 'stop'
                ctx.subbed=False
            elif op=='N':
                old=ctx.pat
                if not self.loadnext(ctx): return 'stopN'
                ctx.pat=old+'\n'+ctx.pat; ctx.subbed=False
            elif op in 'qQ':
                if op=='q' and not self.quiet: self.emit(ctx.pat+'\n')
                self.emit(''.join(ctx.queue)); self.exit=c.arg; self.stop=True; return 'quit'
        return None
    def loadnext(self,ctx):
        ni=ctx.index+1
        if ni>=len(self.records): return False
        if self.separate and self.records[ni][0]!=ctx.fileid: return False
        ctx.index=ni; fid,ln,text,last=self.records[ni]
        ctx.fileid=fid; ctx.lineno=ln; ctx.pat=text; ctx.islast=last; self.serial+=1; ctx.serial=self.serial
        return True
    def run(self):
        idx=0
        while idx<len(self.records) and not self.stop:
            fid,ln,text,last=self.records[idx]
            if self.separate and (idx==0 or self.records[idx-1][0]!=fid): self.reset_ranges(self.cmds)
            ctx=Context(); ctx.index=idx; ctx.fileid=fid; ctx.lineno=ln; ctx.pat=text; ctx.islast=last
            ctx.queue=[]; ctx.subbed=False; self.serial+=1; ctx.serial=self.serial
            while True:
                r=self.runlist(self.cmds,ctx)
                if r=='restart': continue
                while isinstance(r,tuple) and r[0]=='branch' and r[1]:
                    cs,j=r[1]; r=self.runlist(cs,ctx,j+1)
                    if r=='restart': break
                if r=='restart': continue
                break
            if r not in ('delete','quit','stop'):
                if not self.quiet: self.emit(ctx.pat+'\n')
            self.emit(''.join(ctx.queue))
            idx=ctx.index+1
        return ''.join(self.out),self.exit

def read_inputs(files,separate):
    allfiles=[]; status=0
    if not files:
        data=sys.stdin.buffer.read().decode('latin1'); allfiles=[('-',data)]
    else:
        for f in files:
            try:
                if f=='-': data=sys.stdin.buffer.read().decode('latin1')
                else:
                    with open(f,'rb') as h: data=h.read().decode('latin1')
                allfiles.append((f,data))
            except OSError as e:
                sys.stderr.write('sed: cannot read %s: %s\n'%(f,e.strerror)); status=2
    rec=[]; global_lines=[]
    for fid,(name,data) in enumerate(allfiles):
        ls=data.splitlines(True); vals=[]
        for x in ls: vals.append(x[:-1] if x.endswith('\n') else x)
        if separate:
            for j,x in enumerate(vals): rec.append((fid,j+1,x,j==len(vals)-1))
        else:
            for x in vals: global_lines.append((fid,x))
    if not separate:
        for j,(fid,x) in enumerate(global_lines): rec.append((fid,j+1,x,j==len(global_lines)-1))
    return rec,status

def main(argv):
    quiet=False; ext=False; sep=False; pieces=[]; i=0
    try:
        while i<len(argv) and argv[i] in ('-n','-E','-s','-e'):
            a=argv[i]; i+=1
            if a=='-n': quiet=True
            elif a=='-E': ext=True
            elif a=='-s': sep=True
            else:
                if i>=len(argv): raise SedError('option requires argument')
                pieces.append(argv[i]); i+=1
        if not pieces:
            if i>=len(argv): raise SedError('no script')
            pieces=[argv[i]]; i+=1
        script='\n'.join(pieces)
        if script.startswith('#n'): quiet=True
        cmds=Parser(script,ext).parse()
        records,readstatus=read_inputs(argv[i:],sep)
        eng=Engine(cmds,quiet,sep,records)
        out,status=eng.run(); sys.stdout.buffer.write(out.encode('latin1','surrogateescape'))
        return readstatus or status
    except SedError as e:
        sys.stderr.write('sed: %s\n'%e); return 1

if __name__=='__main__': sys.exit(main(sys.argv[1:]))
