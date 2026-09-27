#!/usr/bin/env python3
"""A small, pure Python implementation of the GNU bc language."""
import sys, math
from dataclasses import dataclass

P10=[1]
def p10(n):
    while len(P10)<=n: P10.append(P10[-1]*10)
    return P10[n]
def truncdiv(a,b):
    if b==0: raise BCRuntime()
    q=abs(a)//abs(b)
    return -q if (a<0) != (b<0) else q

@dataclass(frozen=True)
class Num:
    v:int=0; s:int=0
    def integer(self): return truncdiv(self.v,p10(self.s))
    def truth(self): return self.v!=0

def align(a,b):
    s=max(a.s,b.s); return a.v*p10(s-a.s),b.v*p10(s-b.s),s
def add(a,b):
    x,y,s=align(a,b); return Num(x+y,s)
def sub(a,b):
    x,y,s=align(a,b); return Num(x-y,s)
def neg(a): return Num(-a.v,a.s)
def mul(a,b,sc):
    raw=a.v*b.v; rs=a.s+b.s
    out=min(rs,max(sc,a.s,b.s))
    return Num(truncdiv(raw,p10(rs-out)),out)
def div(a,b,sc):
    if b.v==0: raise BCRuntime()
    # (a.v/10^as)/(b.v/10^bs), represented at sc
    shift=sc+b.s-a.s
    if shift>=0: v=truncdiv(a.v*p10(shift),b.v)
    else: v=truncdiv(a.v,b.v*p10(-shift))
    return Num(v,sc)
def rem(a,b,sc):
    if b.v==0: raise BCRuntime()
    q=div(a,b,sc)
    # GNU definition requires product scale max(sc+b.s,a.s).
    ps=max(sc+b.s,a.s)
    raw=q.v*b.v; rs=q.s+b.s
    pv=raw*p10(ps-rs) if ps>=rs else truncdiv(raw,p10(rs-ps))
    av=a.v*p10(ps-a.s)
    return Num(av-pv,ps)
def power(a,b,sc):
    n=b.integer()
    if n==0: return Num(1,0)
    if n<0:
        if a.v==0: raise BCRuntime()
        pos=power(a,Num(-n,0),sc)
        return div(Num(1,0),pos,sc)
    out=min(a.s*n,max(sc,a.s))
    raw=pow(a.v,n); rs=a.s*n
    return Num(truncdiv(raw,p10(rs-out)),out)
def sqrt_num(a,sc):
    if a.v<0: raise BCRuntime()
    if a.v==0: return Num(0,0)
    if a.v==p10(a.s): return Num(1,0)
    out=max(sc,a.s)
    # floor(sqrt(a.v / 10^a.s) * 10^out)
    shift=2*out-a.s
    if shift>=0: z=a.v*p10(shift); return Num(math.isqrt(z),out)
    # This is only relevant for exceptionally unusual negative shifts.
    return Num(math.isqrt(a.v//p10(-shift)),out)
def cmp(a,b):
    x,y,_=align(a,b); return (x>y)-(x<y)
def length_num(a):
    if a.v==0: return 1 if a.s==0 else a.s
    av=abs(a.v); integer=av//p10(a.s)
    return a.s+(len(str(integer)) if integer else 0)

class BCRuntime(Exception): pass
class Halt(Exception): pass
class Quit(Exception): pass
class ParseQuit(Exception): pass
class BreakSig(Exception): pass
class ContinueSig(Exception): pass
class ReturnSig(Exception):
    def __init__(self,v=None): self.v=v

@dataclass
class Tok:
    k:str; v:str; line:int

KEY={'define','void','auto','return','if','else','while','for','break','continue','halt','quit','print'}
class Lexer:
    def __init__(self,s): self.s=s; self.i=0; self.line=1
    def tokens(self):
        r=[]; s=self.s; n=len(s)
        while self.i<n:
            i=self.i; c=s[i]
            if c in ' \t\r': self.i+=1; continue
            if c=='\\' and i+1<n and s[i+1]=='\n': self.i+=2; self.line+=1; continue
            if c=='\n': r.append(Tok('NL','\n',self.line)); self.i+=1; self.line+=1; continue
            if c=='#':
                j=s.find('\n',i); self.i=n if j<0 else j; continue
            if s.startswith('/*',i):
                j=s.find('*/',i+2); j=n-2 if j<0 else j
                self.line+=s[i:j+2].count('\n'); self.i=j+2; continue
            if c=='"':
                j=i+1
                while j<n and s[j]!='"':
                    if s[j]=='\n': self.line+=1
                    j+=1
                r.append(Tok('STR',s[i+1:j],self.line)); self.i=min(j+1,n); continue
            if c.isdigit() or c in 'ABCDEF' or (c=='.' and i+1<n and (s[i+1].isdigit() or s[i+1] in 'ABCDEF')):
                j=i
                while j<n and (s[j].isdigit() or s[j] in 'ABCDEF' or s[j]=='.'): j+=1
                r.append(Tok('NUM',s[i:j],self.line)); self.i=j; continue
            if c.islower():
                j=i+1
                while j<n and (s[j].islower() or s[j].isdigit() or s[j]=='_'): j+=1
                v=s[i:j]; r.append(Tok(v if v in KEY else 'ID',v,self.line)); self.i=j; continue
            matched=False
            for op in ('++','--','+=','-=','*=','/=','%=','^=','=+','=-','=*','=/','=%','=^','==','!=','<=','>=','&&','||'):
                if s.startswith(op,i): r.append(Tok(op,op,self.line)); self.i+=len(op); matched=True; break
            if matched: continue
            if c in '+-*/%^=<>!()[]{};,.' : r.append(Tok(c,c,self.line)); self.i+=1; continue
            self.i+=1
        r.append(Tok('EOF','',self.line)); return r

# AST forms are compact tuples. var: ('var',name), index: ('idx',name,expr)
class Parser:
    def __init__(self,t): self.t=t; self.i=0
    def cur(self,k=None): return self.t[self.i].k if k is None else self.t[self.i].k==k
    def pop(self,k=None):
        x=self.t[self.i]
        if k is not None and x.k!=k: raise SyntaxError((k,x))
        self.i+=1; return x
    def seps(self):
        while self.cur() in ('NL',';'): self.i+=1
    def softnl(self):
        while self.cur('NL'): self.i+=1
    def program(self):
        # A newline after a complete statement ends an execution block.  A
        # runtime error abandons the rest of that block, not merely one stmt.
        out=[]; block=[]; self.seps(); self.quit_seen=False
        while not self.cur('EOF'):
            try:
                block.append(self.stmt())
            except ParseQuit:
                self.quit_seen=True
                block=[]                 # the block being compiled never runs
                break
            saw_nl=False
            while self.cur() in ('NL',';'):
                if self.pop().k=='NL': saw_nl=True
            if saw_nl:
                if block: out.append(('topblock',block)); block=[]
        if block: out.append(('topblock',block))
        return out
    def stmt(self):
        k=self.cur()
        if k=='{':
            self.pop(); z=[]; self.seps()
            while not self.cur('}') and not self.cur('EOF'):
                z.append(self.stmt()); self.seps()
            self.pop('}'); return ('block',z)
        if k=='define': return self.define()
        if k=='if':
            self.pop(); self.softnl(); self.pop('('); e=self.expr(); self.pop(')'); self.softnl(); a=self.stmt()
            save=self.i; self.seps()
            if self.cur('else'): self.pop(); self.softnl(); b=self.stmt()
            else: self.i=save; b=None
            return ('if',e,a,b)
        if k=='while':
            self.pop(); self.softnl(); self.pop('('); e=self.expr(); self.pop(')'); self.softnl(); return ('while',e,self.stmt())
        if k=='for':
            self.pop(); self.softnl(); self.pop('(')
            a=None if self.cur(';') else self.expr(); self.pop(';')
            b=None if self.cur(';') else self.expr(); self.pop(';')
            c=None if self.cur(')') else self.expr(); self.pop(')'); self.softnl()
            return ('for',a,b,c,self.stmt())
        if k=='print':
            self.pop(); z=[]
            while True:
                if self.cur('STR'): z.append(('str',self.pop().v))
                else: z.append(self.expr())
                if not self.cur(','): break
                self.pop(',')
            return ('print',z)
        if k=='STR': return ('string',self.pop().v)
        if k=='quit':
            self.pop(); raise ParseQuit()
        if k in ('break','continue','halt'):
            self.pop(); return (k,)
        if k=='return':
            self.pop()
            if self.cur('('): self.pop(); e=self.expr(); self.pop(')'); return ('return',e)
            if self.cur() not in ('NL',';','}'): return ('return',self.expr())
            return ('return',None)
        e=self.expr(); return ('expr',e,self.assignment_start(e))
    def assignment_start(self,e):
        # GNU's statement decision is lexical in effect; direct assignment root suffices
        return e[0]=='assign'
    def define(self):
        self.pop('define'); self.softnl(); void=False
        if self.cur('void'): self.pop(); void=True
        name=self.pop('ID').v; self.softnl(); self.pop('('); pars=[]
        if not self.cur(')'):
            while True:
                ref=False
                if self.cur('*'): self.pop(); ref=True
                nm=self.pop('ID').v; arr=False
                if self.cur('['): self.pop(); self.pop(']'); arr=True
                pars.append((nm,arr,ref))
                if not self.cur(','): break
                self.pop(',')
        self.pop(')'); self.softnl(); self.pop('{'); self.seps(); autos=[]
        if self.cur('auto'):
            self.pop()
            while True:
                nm=self.pop('ID').v; arr=False
                if self.cur('['): self.pop(); self.pop(']'); arr=True
                autos.append((nm,arr))
                if not self.cur(','): break
                self.pop(',')
            self.seps()
        body=[]
        while not self.cur('}') and not self.cur('EOF'):
            body.append(self.stmt()); self.seps()
        self.pop('}'); return ('define',name,pars,autos,body,void)
    def expr(self,minp=0):
        k=self.cur()
        if k in ('-','!','++','--'):
            op=self.pop().k
            # ! has its documented low prefix precedence; unary minus is high.
            rhs=self.expr(3 if op=='!' else 8)
            x=('pre',op,rhs)
        elif k=='(':
            self.pop(); x=('paren',self.expr()); self.pop(')')
        elif k=='NUM': x=('num',self.pop().v)
        elif k=='.': self.pop(); x=('var','last')
        elif k=='ID':
            nm=self.pop().v
            if self.cur('('):
                self.pop(); args=[]
                if not self.cur(')'):
                    while True:
                        if self.cur('ID') and self.t[self.i+1].k=='[' and self.t[self.i+2].k==']':
                            an=self.pop().v; self.pop('['); self.pop(']'); args.append(('arrayarg',an))
                        else: args.append(self.expr())
                        if not self.cur(','): break
                        self.pop(',')
                self.pop(')'); x=('call',nm,args)
            elif self.cur('['):
                self.pop(); ix=self.expr(); self.pop(']'); x=('idx',nm,ix)
            else: x=('var',nm)
        else: raise SyntaxError(self.t[self.i])
        while True:
            op=self.cur()
            if op in ('++','--'):
                if 9<minp: break
                self.pop(); x=('post',op,x); continue
            prec={'||':1,'&&':2,'<':3,'<=':3,'>':3,'>=':3,'==':3,'!=':3,
                  '=':4,'+=':4,'-=':4,'*=':4,'/=':4,'%=':4,'^=':4,
                  '=+':4,'=-':4,'=*':4,'=/':4,'=%':4,'=^':4,
                  '+':5,'-':5,'*':6,'/':6,'%':6,'^':7}.get(op,0)
            if prec==0 or prec<minp: break
            self.pop(); right_assoc=op in ('=','+=','-=','*=','/=','%=','^=','=+','=-','=*','=/','=%','=^','^')
            y=self.expr(prec if right_assoc else prec+1)
            oldmap={'=+':'+=','=-':'-=','=*':'*=','=/':'/=','=%':'%=','=^':'^='}
            op=oldmap.get(op,op)
            x=('assign',op,x,y) if op.endswith('=') and op not in ('==','!=','<=','>=') else ('bin',op,x,y)
        return x

@dataclass
class Function:
    pars:list; autos:list; body:list; void:bool
class Frame:
    def __init__(self): self.vars={}; self.arrs={}; self.localv=set(); self.locala=set()

class Machine:
    def __init__(self):
        self.gvars={'scale':Num(0),'ibase':Num(10),'obase':Num(10),'last':Num(0)}
        self.garr={}; self.frames=[]; self.func={}; self.literal_base=None
        self.out=[]; self.col=0; self.stopped=False
    def emit(self,s,wrap=True):
        for ch in s:
            if ch=='\n': self.out.append(ch); self.col=0; continue
            if wrap and self.col>=68:
                self.out.append('\\\n'); self.col=0
            self.out.append(ch); self.col+=1
    def getv(self,n):
        for f in reversed(self.frames):
            if n in f.localv: return f.vars.get(n,Num())
        return self.gvars.get(n,Num())
    def setv(self,n,v):
        if n in ('scale','ibase','obase'):
            q=v.integer()
            if n=='scale': q=max(0,q)
            elif n=='ibase': q=min(16,max(2,q))
            else: q=min(999,max(2,q))
            v=Num(q,0)
        for f in reversed(self.frames):
            if n in f.localv: f.vars[n]=v; return
        self.gvars[n]=v
    def geta(self,n):
        for f in reversed(self.frames):
            if n in f.locala: return f.arrs[n]
        return self.garr.setdefault(n,{})
    def index(self,v):
        if v.v<0 or (0<abs(v.v)<p10(v.s)): raise BCRuntime()
        q=v.integer()
        if q<0 or q>=65536: raise BCRuntime()
        return q
    def literal(self,text):
        base=self.literal_base if self.literal_base is not None else self.getv('ibase').integer()
        if '.' in text: ip,fp=text.split('.',1)
        else: ip,fp=text,''
        def d(c): return int(c) if c.isdigit() else ord(c)-55
        # Single digit rule applies to the integer part independently.
        if ip:
            ds=[d(c) for c in ip]
            if len(ds)>1: ds=[min(x,base-1) for x in ds]
            iv=0
            for x in ds: iv=iv*base+x
        else: iv=0
        n=len(fp)
        if not fp: return Num(iv,0)
        fv=0; den=1
        for c in fp: fv=fv*base+min(d(c),base-1); den*=base
        frac=(fv*p10(n))//den
        return Num(iv*p10(n)+frac,n)
    def ref(self,e):
        if e[0]=='var':
            return (lambda:self.getv(e[1]),lambda v:self.setv(e[1],v))
        if e[0]=='idx':
            ix=self.index(self.ev(e[2])); a=self.geta(e[1])
            return (lambda:a.get(ix,Num()),lambda v:a.__setitem__(ix,v))
        raise BCRuntime()
    def ev(self,e):
        t=e[0]
        if t=='num': return self.literal(e[1])
        if t=='paren': return self.ev(e[1])
        if t in ('var','idx'): return self.ref(e)[0]()
        if t=='pre':
            op=e[1]
            if op=='-': return neg(self.ev(e[2]))
            if op=='!': return Num(0 if self.ev(e[2]).truth() else 1)
            g,s=self.ref(e[2]); nv=add(g(),Num(1 if op=='++' else -1)); s(nv); return nv
        if t=='post':
            g,s=self.ref(e[2]); old=g(); s(add(old,Num(1 if e[1]=='++' else -1))); return old
        if t=='assign':
            g,s=self.ref(e[2]); op=e[1]
            if op=='=': v=self.ev(e[3])
            else:
                a=g(); b=self.ev(e[3]); v=self.calc(op[0],a,b)
            s(v); return v
        if t=='bin':
            op=e[1]; a=self.ev(e[2])
            if op=='&&': return Num(1 if a.truth() and self.ev(e[3]).truth() else 0)
            if op=='||': return Num(1 if a.truth() or self.ev(e[3]).truth() else 0)
            b=self.ev(e[3]); return self.calc(op,a,b)
        if t=='call':
            n=e[1]
            if n in ('length','scale','sqrt'):
                a=self.ev(e[2][0])
                if n=='length': return Num(length_num(a))
                if n=='scale': return Num(a.s)
                return sqrt_num(a,self.getv('scale').integer())
            return self.call(n,e[2])
        raise BCRuntime()
    def calc(self,op,a,b):
        sc=self.getv('scale').integer()
        if op=='+': return add(a,b)
        if op=='-': return sub(a,b)
        if op=='*': return mul(a,b,sc)
        if op=='/': return div(a,b,sc)
        if op=='%': return rem(a,b,sc)
        if op=='^': return power(a,b,sc)
        c=cmp(a,b)
        return Num(int({'<':c<0,'<=':c<=0,'>':c>0,'>=':c>=0,'==':c==0,'!=':c!=0}[op]))
    def call(self,n,args):
        if n not in self.func: raise BCRuntime()
        fn=self.func[n]
        if len(args)!=len(fn.pars): raise BCRuntime()
        vals=[]
        for arg,p in zip(args,fn.pars):
            if p[1]:
                if arg[0]!='arrayarg': raise BCRuntime()
                a=self.geta(arg[1]); vals.append(a if p[2] else dict(a))
            else:
                if arg[0]=='arrayarg': raise BCRuntime()
                vals.append(self.ev(arg))
        f=Frame()
        for (p,arr,ref),v in zip(fn.pars,vals):
            if arr: f.locala.add(p); f.arrs[p]=v
            else: f.localv.add(p); f.vars[p]=v
        for n0,arr in fn.autos:
            if arr: f.locala.add(n0); f.arrs[n0]={}
            else: f.localv.add(n0); f.vars[n0]=Num()
        oldbase=self.literal_base; self.literal_base=self.getv('ibase').integer(); self.frames.append(f)
        rv=Num()
        try:
            for st in fn.body: self.exec(st)
        except ReturnSig as x: rv=x.v if x.v is not None else Num()
        finally:
            self.frames.pop(); self.literal_base=oldbase
        return None if fn.void else rv
    def format(self,a):
        if a.v==0: return '0'
        base=self.getv('obase').integer(); negs='-' if a.v<0 else ''; av=abs(a.v)
        if base==10:
            z=str(av).rjust(a.s+1,'0')
            if a.s: z=z[:-a.s]+'.'+z[-a.s:]
            if z.startswith('0.'): z=z[1:]
            return negs+z
        den=p10(a.s); integer=av//den
        digs=[]
        if integer==0: digs=[0]
        while integer: digs.append(integer%base); integer//=base
        digs.reverse()
        chars='0123456789ABCDEF'
        if base<=16: left=''.join(chars[x] for x in digs)
        else:
            w=len(str(base-1)); left=''.join((' ' if i==0 else ' ')+str(x).zfill(w) for i,x in enumerate(digs))
        frac=''
        if a.s:
            k=0; q=1
            while q<den: q*=base; k+=1
            remv=av%den; fd=[]
            for _ in range(k): remv*=base; fd.append(remv//den); remv%=den
            if base<=16: frac='.'+''.join(chars[x] for x in fd)
            else:
                w=len(str(base-1)); frac='.'+' '.join(str(x).zfill(w) for x in fd)
        return negs+left+frac
    def printnum(self,v,newline=False):
        if v is None: return
        self.emit(self.format(v)); self.setv('last',v)
        if newline: self.emit('\n')
    def pstring(self,s,esc):
        if not esc: self.emit(s); return
        mp={'a':'\a','b':'\b','f':'\f','n':'\n','r':'\r','q':'"','t':'\t','\\':'\\'}
        z=''; i=0
        while i<len(s):
            if s[i]=='\\' and i+1<len(s): z+=mp.get(s[i+1],''); i+=2
            else: z+=s[i]; i+=1
        self.emit(z)
    def exec(self,s):
        t=s[0]
        if t in ('block','topblock'):
            for x in s[1]: self.exec(x)
        elif t=='define': self.func[s[1]]=Function(s[2],s[3],s[4],s[5])
        elif t=='expr':
            v=self.ev(s[1])
            if not s[2]: self.printnum(v,True)
        elif t=='string': self.pstring(s[1],False)
        elif t=='print':
            for x in s[1]:
                if x[0]=='str': self.pstring(x[1],True)
                else: self.printnum(self.ev(x))
        elif t=='if':
            if self.ev(s[1]).truth(): self.exec(s[2])
            elif s[3] is not None: self.exec(s[3])
        elif t=='while':
            while self.ev(s[1]).truth():
                try: self.exec(s[2])
                except BreakSig: break
        elif t=='for':
            if s[1] is not None: self.ev(s[1])
            while s[2] is None or self.ev(s[2]).truth():
                try: self.exec(s[4])
                except ContinueSig: pass
                except BreakSig: break
                if s[3] is not None: self.ev(s[3])
        elif t=='break': raise BreakSig()
        elif t=='continue': raise ContinueSig()
        elif t=='return': raise ReturnSig(None if s[1] is None else self.ev(s[1]))
        elif t=='halt': raise Halt()
    def run(self,prog):
        for st in prog:
            try: self.exec(st)
            except BCRuntime: continue
            except Halt: self.stopped=True; break

def main(argv):
    m=Machine()
    def process(src):
        try:
            parser=Parser(Lexer(src).tokens()); prog=parser.program()
        except SyntaxError:
            return False
        m.run(prog)
        if parser.quit_seen: m.stopped=True
        return True
    try:
        for fn in argv:
            if m.stopped: break
            with open(fn,encoding='utf-8') as f: process(f.read())
        if not m.stopped: process(sys.stdin.read())
    except OSError as e:
        sys.stderr.write(str(e)+'\n')
        sys.stdout.write(''.join(m.out)); return 1
    sys.stdout.write(''.join(m.out)); return 0
if __name__=='__main__': sys.exit(main(sys.argv[1:]))
