#!/usr/bin/env python3
import sys, math
sys.setrecursionlimit(100000)
if hasattr(sys, 'set_int_max_str_digits'): sys.set_int_max_str_digits(0)
from dataclasses import dataclass

@dataclass(frozen=True)
class Num:
    c: int = 0
    s: int = 0
    def trunc(self, s):
        if s >= self.s: return Num(self.c * 10 ** (s-self.s), s)
        return Num(tdiv(self.c, 10 ** (self.s-s)), s)
    def truth(self): return self.c != 0

def tdiv(a,b):
    if b == 0: raise RuntimeError()
    q=abs(a)//abs(b)
    return -q if (a<0) != (b<0) else q

def align(a,b):
    s=max(a.s,b.s)
    return a.c*10**(s-a.s), b.c*10**(s-b.s), s

def add(a,b,neg=False):
    x,y,s=align(a,b); return Num(x-y if neg else x+y,s)

def mul(a,b,scale):
    rs=min(a.s+b.s,max(scale,a.s,b.s))
    c=a.c*b.c
    if a.s+b.s>rs: c=tdiv(c,10**(a.s+b.s-rs))
    elif a.s+b.s<rs: c*=10**(rs-a.s-b.s)
    return Num(c,rs)

def divide(a,b,scale):
    if b.c==0: raise RuntimeError()
    e=scale+b.s-a.s
    if e>=0: c=tdiv(a.c*10**e,b.c)
    else: c=tdiv(a.c,b.c*10**(-e))
    return Num(c,scale)

def modulo(a,b,scale):
    if b.c==0: raise RuntimeError()
    q=divide(a,b,scale)
    target=max(scale+b.s,a.s)
    # Exact q*b, then truncate both terms to the prescribed result scale.
    p=Num(q.c*b.c,q.s+b.s).trunc(target)
    return add(a.trunc(target),p,True)

def power(a,b,scale):
    n=tdiv(b.c,10**b.s)
    if n==0: return Num(1,0)
    if n<0:
        if a.c==0: raise RuntimeError()
        p=power(a,Num(-n,0),scale)
        return divide(Num(1,0),p,scale)
    rs=min(a.s*n,max(scale,a.s))
    c=pow(a.c,n); raw=a.s*n
    if raw>rs: c=tdiv(c,10**(raw-rs))
    elif raw<rs: c*=10**(rs-raw)
    return Num(c,rs)

def sqrt_num(a,scale):
    if a.c<0: raise RuntimeError()
    if a.c in (0,10**a.s): return Num(0 if a.c==0 else 1,0)
    rs=max(scale,a.s); e=2*rs-a.s
    if e>=0: n=a.c*10**e
    else: n=a.c//10**(-e)
    return Num(math.isqrt(n),rs)

@dataclass
class Tok:
    k: str
    v: str
    line: int

KEYS={'if','else','while','for','break','continue','halt','quit','return','print','define','void','auto','length','scale','sqrt'}
class Lexer:
    def __init__(self,s): self.s=s; self.i=0; self.line=1
    def run(self):
        out=[]; s=self.s; n=len(s)
        while self.i<n:
            i=self.i; ch=s[i]
            if ch in ' \t\r\f': self.i+=1; continue
            if ch=='\\' and i+1<n and s[i+1]=='\n': self.i+=2; self.line+=1; continue
            if ch=='\n': out.append(Tok('NL','\n',self.line)); self.i+=1; self.line+=1; continue
            if ch=='#':
                j=s.find('\n',i); self.i=n if j<0 else j; continue
            if s.startswith('/*',i):
                j=s.find('*/',i+2)
                if j<0: self.i=n; continue
                self.line+=s[i:j+2].count('\n'); self.i=j+2; continue
            if ch=='"':
                j=i+1
                while j<n and s[j]!='"': j+=1
                val=s[i+1:j]; self.line+=val.count('\n'); out.append(Tok('STR',val,self.line-val.count('\n'))); self.i=min(j+1,n); continue
            if ch.islower():
                j=i+1
                while j<n and (s[j].islower() or s[j].isdigit() or s[j]=='_'): j+=1
                v=s[i:j]; out.append(Tok(v if v in KEYS else 'ID',v,self.line)); self.i=j; continue
            if ch.isdigit() or ch in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ' or (ch=='.' and i+1<n and (s[i+1].isdigit() or s[i+1] in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ')):
                j=i
                if s[j]=='.': j+=1
                while j<n and (s[j].isdigit() or s[j] in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'): j+=1
                if j<n and s[j]=='.':
                    j+=1
                    while j<n and (s[j].isdigit() or s[j] in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'): j+=1
                out.append(Tok('NUM',s[i:j],self.line)); self.i=j; continue
            found=False
            for op in ('++','--','+=','-=','*=','/=','%=','^=','=+','=-','=*','=/','=%','=^','==','!=','<=','>=','&&','||'):
                if s.startswith(op,i): out.append(Tok(op,op,self.line)); self.i+=2; found=True; break
            if found: continue
            if ch in '+-*/%^=<>!(){}[],;.': out.append(Tok(ch,ch,self.line)); self.i+=1; continue
            self.i+=1
        out.append(Tok('EOF','',self.line)); return out

class QuitParse(Exception): pass
class ParseError(Exception): pass
class Parser:
    def __init__(self,t): self.t=t; self.i=0
    def peek(self,k=None): return self.t[self.i].k if k is None else self.t[self.i].k==k
    def pop(self,k=None):
        x=self.t[self.i]
        if k is not None and x.k!=k: raise ParseError((k,x.k,x.line))
        self.i+=1; return x
    def seps(self):
        while self.peek('NL') or self.peek(';'): self.i+=1
    def program(self):
        blocks=[]; cur=[]
        while self.peek('NL') or self.peek(';'): self.i+=1
        try:
            while not self.peek('EOF'):
                cur.append(self.stmt())
                saw_nl=False
                while self.peek('NL') or self.peek(';'):
                    if self.peek('NL'): saw_nl=True
                    self.i+=1
                if saw_nl:
                    blocks.append(('topblock',cur)); cur=[]
        except QuitParse:
            pass
        if cur: blocks.append(('topblock',cur))
        return blocks
    def stmt(self):
        k=self.peek()
        if k=='quit': self.pop(); raise QuitParse()
        if k=='{':
            self.pop(); z=[]; self.seps()
            while not self.peek('}') and not self.peek('EOF'):
                z.append(self.stmt()); self.seps()
            self.pop('}'); return ('block',z)
        if k=='if':
            self.pop(); self.pop('('); e=self.expr(); self.pop(')'); self.seps(); a=self.stmt(); self.seps(); b=None
            if self.peek('else'): self.pop(); self.seps(); b=self.stmt()
            return ('if',e,a,b)
        if k=='while':
            self.pop(); self.pop('('); e=self.expr(); self.pop(')'); self.seps(); return ('while',e,self.stmt())
        if k=='for':
            self.pop(); self.pop('(')
            a=None if self.peek(';') else self.expr(); self.pop(';')
            b=None if self.peek(';') else self.expr(); self.pop(';')
            c=None if self.peek(')') else self.expr(); self.pop(')'); self.seps()
            return ('for',a,b,c,self.stmt())
        if k in ('break','continue','halt'):
            self.pop(); return (k,)
        if k=='return':
            self.pop()
            if self.peek('('): self.pop(); e=self.expr(); self.pop(')'); return ('return',e)
            if self.peek() in ('NL',';','}'): return ('return',None)
            return ('return',self.expr())
        if k=='print':
            self.pop(); q=[]
            while True:
                if self.peek('STR'): q.append(('str',self.pop().v))
                else: q.append(('expr',self.expr()))
                if not self.peek(','): break
                self.pop()
            return ('print',q)
        if k=='STR': return ('string',self.pop().v)
        if k=='define': return self.function()
        e=self.expr(); return ('expr',e,e[0]=='assign')
    def function(self):
        self.pop('define'); void=False
        if self.peek('void'): self.pop(); void=True
        name=self.pop('ID').v; self.pop('('); params=[]
        if not self.peek(')'):
            while True:
                ref=False
                if self.peek('*'): self.pop(); ref=True
                nm=self.pop('ID').v; arr=False
                if self.peek('['): self.pop(); self.pop(']'); arr=True
                params.append((nm,arr,ref))
                if not self.peek(','): break
                self.pop()
        self.pop(')'); self.seps(); self.pop('{'); self.seps(); autos=[]
        if self.peek('auto'):
            self.pop()
            while True:
                nm=self.pop('ID').v; arr=False
                if self.peek('['): self.pop(); self.pop(']'); arr=True
                autos.append((nm,arr))
                if not self.peek(','): break
                self.pop()
            if self.peek(';'): self.pop()
            self.seps()
        body=[]
        while not self.peek('}') and not self.peek('EOF'):
            body.append(self.stmt()); self.seps()
        self.pop('}'); return ('define',name,params,autos,body,void)
    def expr(self,minp=0):
        k=self.peek()
        if k in ('-','!','++','--'):
            self.pop(); bp=9 if k=='-' else (3 if k=='!' else 10); left=('un',k,self.expr(bp))
        elif k=='(':
            self.pop(); left=('paren',self.expr()); self.pop(')')
        elif k=='NUM': left=('num',self.pop().v)
        elif k=='.': self.pop(); left=('var','last')
        elif k in ('length','sqrt') or (k=='scale' and self.i+1<len(self.t) and self.t[self.i+1].k=='('):
            name=self.pop().k; self.pop('('); e=self.expr(); self.pop(')'); left=('builtin',name,e)
        elif k=='scale':
            self.pop(); left=('var','scale')
        elif k=='ID':
            name=self.pop().v
            if self.peek('('):
                self.pop(); args=[]
                if not self.peek(')'):
                    while True:
                        if self.peek('ID') and self.i+2<len(self.t) and self.t[self.i+1].k=='[' and self.t[self.i+2].k==']':
                            nm=self.pop().v; self.pop('['); self.pop(']'); args.append(('arrayarg',nm))
                        else: args.append(self.expr())
                        if not self.peek(','): break
                        self.pop()
                self.pop(')'); left=('call',name,args)
            elif self.peek('['):
                self.pop(); ix=self.expr(); self.pop(']'); left=('arr',name,ix)
            else: left=('var',name)
        else: raise ParseError(('expression',k,self.t[self.i].line))
        while True:
            op=self.peek()
            if op in ('++','--'):
                if 10<minp: break
                self.pop(); left=('post',op,left); continue
            prec={'||':1,'&&':2,'<':4,'<=':4,'>':4,'>=':4,'==':4,'!=':4,
                  '=':5,'+=':5,'-=':5,'*=':5,'/=':5,'%=':5,'^=':5,'=+':5,'=-':5,'=*':5,'=/':5,'=%':5,'=^':5,
                  '+':6,'-':6,'*':7,'/':7,'%':7,'^':8}.get(op,-1)
            if prec<minp: break
            self.pop(); right=self.expr(prec if op in ('=','+=','-=','*=','/=','%=','^=','=+','=-','=*','=/','=%','=^','^') else prec+1)
            left=('assign',op,left,right) if op in ('=','+=','-=','*=','/=','%=','^=','=+','=-','=*','=/','=%','=^') else ('bin',op,left,right)
        return left

class Flow(Exception):
    def __init__(self,k,v=None): self.k=k; self.v=v
class Halt(Exception): pass

class Writer:
    def __init__(self): self.parts=[]; self.col=0
    def put(self,s):
        for ch in s:
            if ch=='\n': self.parts.append(ch); self.col=0; continue
            if self.col==68: self.parts.append('\\\n'); self.col=0
            self.parts.append(ch); self.col+=1
    def text(self): return ''.join(self.parts)

class Engine:
    def __init__(self):
        self.vals={'scale':Num(0,0),'ibase':Num(10,0),'obase':Num(10,0),'last':Num(0,0)}
        self.arrs={}; self.funcs={}; self.w=Writer(); self.call_ibases=[]
    def ivar(self,n): return self.vals.get(n,Num())
    def integer(self,n): return tdiv(n.c,10**n.s)
    def setvar(self,n,v):
        if n=='scale': self.vals[n]=Num(max(0,self.integer(v)),0)
        elif n=='ibase': self.vals[n]=Num(min(16,max(2,self.integer(v))),0)
        elif n=='obase': self.vals[n]=Num(min(999,max(2,self.integer(v))),0)
        else: self.vals[n]=v
    def scale(self): return self.integer(self.ivar('scale'))
    def parseconst(self,s):
        base=self.call_ibases[-1] if self.call_ibases else self.integer(self.ivar('ibase'))
        if '.' in s: a,b=s.split('.',1)
        else: a,b=s,''
        def dig(ch): return ord(ch)-48 if ch<='9' else ord(ch)-55
        def clamp(ch,single=False):
            d=dig(ch)
            return d if single else min(d,base-1)
        # A single digit retains its digit value even when >= ibase.
        single=(len(a+b)==1)
        ip=0
        for ch in a: ip=ip*base+clamp(ch,single)
        if not b: return Num(ip,0)
        num=0
        for ch in b: num=num*base+clamp(ch,single)
        den=base**len(b); frac=(num*10**len(b))//den
        return Num(ip*10**len(b)+frac,len(b))
    def ref(self,e):
        if e[0]=='var':
            n=e[1]; return (lambda:self.ivar(n),lambda v:self.setvar(n,v))
        if e[0]=='arr':
            n=e[1]; x=self.eval(e[2]);
            if x.c<0 or (0<abs(x.c)<10**x.s): raise RuntimeError()
            ix=self.integer(x)
            if ix<0 or ix>=65536: raise RuntimeError()
            ar=self.arrs.setdefault(n,{})
            return (lambda:ar.get(ix,Num()),lambda v:ar.__setitem__(ix,v))
        raise RuntimeError()
    def op(self,op,a,b):
        if op=='+': return add(a,b)
        if op=='-': return add(a,b,True)
        if op=='*': return mul(a,b,self.scale())
        if op=='/': return divide(a,b,self.scale())
        if op=='%': return modulo(a,b,self.scale())
        if op=='^': return power(a,b,self.scale())
        x,y,_=align(a,b)
        if op in ('<','<=','>','>=','==','!='):
            return Num(int({'<':x<y,'<=':x<=y,'>':x>y,'>=':x>=y,'==':x==y,'!=':x!=y}[op]),0)
        if op=='&&': return Num(int(a.truth() and b.truth()),0)
        if op=='||': return Num(int(a.truth() or b.truth()),0)
        raise RuntimeError()
    def eval(self,e):
        k=e[0]
        if k=='num': return self.parseconst(e[1])
        if k=='paren': return self.eval(e[1])
        if k in ('var','arr'): return self.ref(e)[0]()
        if k=='un':
            op=e[1]
            if op in ('++','--'):
                g,s=self.ref(e[2]); old=g(); v=add(old,Num(1),op=='--'); s(v); return v
            a=self.eval(e[2]); return Num(-a.c,a.s) if op=='-' else Num(int(not a.truth()),0)
        if k=='post':
            g,s=self.ref(e[2]); old=g(); s(add(old,Num(1),e[1]=='--')); return old
        if k=='bin':
            a=self.eval(e[2]); b=self.eval(e[3]); return self.op(e[1],a,b)
        if k=='assign':
            g,s=self.ref(e[2]); b=self.eval(e[3]); op=e[1]
            
            if op=='=': v=b
            else:
                bop = op[0] if op[0] != '=' else op[1]
                v=self.op(bop,g(),b)
            s(v); return v
        if k=='builtin':
            a=self.eval(e[2])
            if e[1]=='scale': return Num(a.s,0)
            if e[1]=='length': return Num(max(len(str(abs(a.c))) if a.c else 1,a.s),0)
            return sqrt_num(a,self.scale())
        if k=='call':
            if e[1] in self.funcs and self.funcs[e[1]][3]: raise RuntimeError()
            return self.call(e[1],e[2])
        raise RuntimeError()
    def format(self,a):
        base=self.integer(self.ivar('obase')); neg=a.c<0; c=abs(a.c); den=10**a.s
        ip=c//den; rem=c%den
        digs=[]
        if ip==0: digs=[0]
        else:
            while ip: digs.append(ip%base); ip//=base
            digs.reverse()
        width=len(str(base-1))
        def dstr(d,first=False):
            if base<=16: return '0123456789ABCDEF'[d]
            return (' ' if first else ' ')+str(d).zfill(width)
        if c < den and a.s:
            ints=''
        elif base<=16: ints=''.join(dstr(x) for x in digs)
        else: ints=''.join(dstr(x,True) for x in digs)
        if a.s:
            k=0; p=1
            while p<10**a.s: p*=base; k+=1
            fd=[]
            for _ in range(k): rem*=base; fd.append(rem//den); rem%=den
            if base<=16: frac=''.join(dstr(x) for x in fd)
            else: frac=' '.join(str(x).zfill(width) for x in fd)
            out=ints+'.'+frac
        else: out=ints
        if c==0: out='0'
        elif base==10 and a.s:
            q=str(c).zfill(a.s+1); out=q[:-a.s]+'.'+q[-a.s:]
            if out.startswith('0.'): out=out[1:]
        if neg and c: out='-'+out
        return out
    def printnum(self,v,newline=False):
        self.vals['last']=v; self.w.put(self.format(v));
        if newline: self.w.put('\n')
    def unescape(self,s):
        m={'a':'\a','b':'\b','f':'\f','n':'\n','r':'\r','q':'"','t':'\t','\\':'\\'}; z=''; i=0
        while i<len(s):
            if s[i]=='\\' and i+1<len(s): z+=m.get(s[i+1],''); i+=2
            else: z+=s[i]; i+=1
        return z
    def stmt(self,s):
        k=s[0]
        if k in ('block','topblock'):
            if k=='topblock':
                for x in s[1]:
                    if x[0]=='define': self.stmt(x)
            for x in s[1]:
                if not (k=='topblock' and x[0]=='define'): self.execstmt(x)
        elif k=='expr':
            isvoid = s[1][0]=='call' and s[1][1] in self.funcs and self.funcs[s[1][1]][3]
            if isvoid:
                self.call(s[1][1],s[1][2])
            else:
                v=self.eval(s[1])
                if not s[2]: self.printnum(v,True)
        elif k=='string': self.w.put(s[1])
        elif k=='print':
            for typ,x in s[1]: self.w.put(self.unescape(x)) if typ=='str' else self.printnum(self.eval(x))
        elif k=='if':
            branch=s[2] if self.eval(s[1]).truth() else s[3]
            if branch is not None: self.stmt(branch)
        elif k=='while':
            while self.eval(s[1]).truth():
                try: self.stmt(s[2])
                except Flow as f:
                    if f.k=='break': break
                    raise
        elif k=='for':
            if s[1]: self.eval(s[1])
            while s[2] is None or self.eval(s[2]).truth():
                try: self.stmt(s[4])
                except Flow as f:
                    if f.k=='break': break
                    if f.k!='continue': raise
                if s[3]: self.eval(s[3])
        elif k in ('break','continue'): raise Flow(k)
        elif k=='halt': raise Halt()
        elif k=='return': raise Flow('return',Num() if s[1] is None else self.eval(s[1]))
        elif k=='define': self.funcs[s[1]]=(s[2],s[3],s[4],s[5])
    def execstmt(self,s):
        # Keep if separate to evaluate its condition exactly once.
        if s[0]=='if':
            branch=s[2] if self.eval(s[1]).truth() else s[3]
            if branch is not None: self.stmt(branch)
        else: self.stmt(s)
    def call(self,name,args):
        if name not in self.funcs: raise RuntimeError()
        params,autos,body,void=self.funcs[name]
        if len(params)!=len(args): raise RuntimeError()
        saves=[]; prepared=[]
        for (nm,arr,ref),arg in zip(params,args):
            if arr:
                if arg[0]!='arrayarg': raise RuntimeError()
                src=self.arrs.setdefault(arg[1],{})
                prepared.append((nm,True,src if ref else dict(src)))
            else:
                if arg[0]=='arrayarg': raise RuntimeError()
                prepared.append((nm,False,self.eval(arg)))
        callbase=self.integer(self.ivar('ibase'))
        for nm,arr,v in prepared:
            d=self.arrs if arr else self.vals; saves.append((d,nm,nm in d,d.get(nm))); d[nm]=v
        for nm,arr in autos:
            d=self.arrs if arr else self.vals; saves.append((d,nm,nm in d,d.get(nm))); d[nm]={} if arr else Num()
        self.call_ibases.append(callbase)
        ret=Num()
        try:
            for x in body: self.execstmt(x)
        except Flow as f:
            if f.k=='return': ret=f.v
            else: raise
        finally:
            self.call_ibases.pop()
            for d,nm,had,old in reversed(saves):
                if had: d[nm]=old
                else: d.pop(nm,None)
        return ret

def main(argv):
    chunks=[]
    try:
        for fn in argv:
            with open(fn,encoding='latin1') as f: chunks.append(f.read())
    except OSError as e:
        sys.stderr.write(str(e)+'\n'); return 1
    chunks.append(sys.stdin.read())
    src=''.join(chunks)
    eng=Engine()
    try: ast=Parser(Lexer(src).run()).program()
    except Exception as e:
        return 1
    try:
        for st in ast:
            try: eng.execstmt(st)
            except RuntimeError: continue
    except Halt: pass
    sys.stdout.write(eng.w.text()); return 0
if __name__=='__main__': sys.exit(main(sys.argv[1:]))
