#!/usr/bin/env python3
import sys, re, math

class Num:
    __slots__=('v','s')
    def __init__(self,v=0,s=0): self.v=int(v); self.s=max(0,int(s))
    def copy(self): return Num(self.v,self.s)
    def trunc(self,s):
        s=max(0,int(s))
        if s>=self.s: return Num(self.v*10**(s-self.s),s)
        return Num(tdiv(self.v,10**(self.s-s)),s)
    def integer(self): return tdiv(self.v,10**self.s)
    def nz(self): return self.v!=0

def tdiv(a,b):
    if b==0: raise RunError()
    q=abs(a)//abs(b)
    return -q if (a<0) != (b<0) else q

def align(a,b):
    s=max(a.s,b.s); return a.v*10**(s-a.s),b.v*10**(s-b.s),s

def add(a,b,neg=False):
    x,y,s=align(a,b); return Num(x-y if neg else x+y,s)
def mul(a,b,sc):
    rs=min(a.s+b.s,max(sc,a.s,b.s)); return Num(tdiv(a.v*b.v,10**(a.s+b.s-rs)),rs)
def divn(a,b,sc):
    if b.v==0: raise RunError()
    return Num(tdiv(a.v*10**(b.s+sc),b.v*10**a.s),sc)
def remn(a,b,sc):
    if b.v==0: raise RunError()
    q=divn(a,b,sc); p=mul(q,b,max(sc+b.s,a.s)); return add(a,p,True).trunc(max(sc+b.s,a.s))
def cmpn(a,b):
    x,y,_=align(a,b); return (x>y)-(x<y)

def pown(a,b,sc):
    n=b.integer()
    if n==0:return Num(1,0)
    if a.v==0 and n<0: raise RunError()
    if n>0:
        rs=min(a.s*n,max(sc,a.s)); raw=pow(a.v,n)
        return Num(tdiv(raw,10**(a.s*n-rs)),rs)
    rs=sc
    den=pow(abs(a.v),-n); num=10**(a.s*(-n)+rs)
    v=tdiv(num,den); v=-v if a.v<0 and (-n)%2 else v
    return Num(v,rs)

class RunError(Exception): pass
class Halt(Exception): pass
class VoidResult: pass
VOID=VoidResult()
class Flow(Exception):
    def __init__(self,k,v=None): self.k=k; self.v=v

# token: kind/value. Newlines are syntactically meaningful separators.
pat=re.compile(r'''(?P<WS>[ \t\r]+)|(?P<NL>\n)|(?P<BC>/\*.*?\*/)|(?P<LC>\#[^\n]*)|(?P<STR>"(?:\\.|[^"\\])*")|(?P<NUM>(?:[0-9A-F]+(?:\.[0-9A-F]*)?|\.[0-9A-F]+))|(?P<ID>[a-z][a-z0-9_]*)|(?P<OP>\+\+|--|\+=|-=|\*=|/=|%=|\^=|==|!=|<=|>=|&&|\|\||.)''',re.S)

def lex(src):
    # Outside strings, backslash-newline is whitespace. Valid test input does
    # not rely on this transformation inside a string.
    src=src.replace('\\\n',' ')
    out=[]; p=0
    while p<len(src):
        m=pat.match(src,p)
        if not m: p+=1; continue
        p=m.end(); k=m.lastgroup; v=m.group()
        if k in ('WS','LC'): continue
        if k=='BC':
            # A block comment, including any newlines in it, is one space.
            continue
        if k=='STR': out.append(('STR',v[1:-1]))
        elif k=='NUM': out.append(('NUM',v))
        elif k=='ID': out.append(('ID',v))
        elif k=='NL': out.append(('NL',v))
        else: out.append((v,v))
    out.append(('EOF','EOF')); return out

class Parser:
    def __init__(self,s): self.t=lex(s); self.i=0
    def pk(self,v=None):
        z=self.t[self.i]; return z[1]==v if v is not None else z
    def pop(self,v=None):
        z=self.t[self.i]
        if v is not None and z[1]!=v: raise SyntaxError((v,z))
        self.i+=1; return z
    def seps(self):
        while self.pk('\n') or self.pk(';'): self.i+=1
    def softnl(self):
        while self.pk('\n'): self.i+=1
    def program(self,end=None):
        a=[]; self.seps()
        while not self.pk('EOF') and not (end and self.pk(end)):
            a.append(self.stmt()); self.seps()
        return a
    def stmt(self):
        if self.pk('{'):
            self.pop(); a=self.program('}'); self.pop('}'); return ('block',a)
        if self.pk()[0]=='ID':
            w=self.pk()[1]
            if w=='define': return self.func()
            if w=='if':
                self.pop(); self.softnl(); self.pop('('); e=self.expr(); self.pop(')'); self.softnl(); a=self.stmt()
                save=self.i; self.seps()
                if self.pk()[0]=='ID' and self.pk()[1]=='else': self.pop(); self.softnl(); b=self.stmt()
                else: self.i=save; b=None
                return ('if',e,a,b)
            if w=='while':
                self.pop(); self.softnl(); self.pop('('); e=self.expr(); self.pop(')'); self.softnl(); return ('while',e,self.stmt())
            if w=='for':
                self.pop(); self.softnl(); self.pop('(')
                a=None if self.pk(';') else self.expr(); self.pop(';')
                b=None if self.pk(';') else self.expr(); self.pop(';')
                c=None if self.pk(')') else self.expr(); self.pop(')'); self.softnl()
                return ('for',a,b,c,self.stmt())
            if w in ('break','continue','halt','quit'):
                self.pop(); return (w,)
            if w=='return':
                self.pop()
                if self.pk('('): self.pop(); e=self.expr(); self.pop(')'); return ('return',e)
                return ('return',None)
            if w=='print':
                self.pop(); xs=[]
                while True:
                    if self.pk()[0]=='STR': xs.append(('str',self.pop()[1]))
                    else: xs.append(('num',self.expr()))
                    if not self.pk(','): break
                    self.pop()
                return ('print',xs)
            if w=='auto':
                self.pop(); xs=[]
                while True:
                    n=self.pop()[1]; arr=False
                    if self.pk('['): self.pop(); self.pop(']'); arr=True
                    xs.append((n,arr))
                    if not self.pk(','): break
                    self.pop()
                return ('auto',xs)
        if self.pk()[0]=='STR': return ('string',self.pop()[1])
        e=self.expr(); return ('expr',e)
    def func(self):
        self.pop(); void=False
        if self.pk()[0]=='ID' and self.pk()[1]=='void': self.pop(); void=True
        name=self.pop()[1]; self.pop('('); ps=[]
        if not self.pk(')'):
            while True:
                ref=False
                if self.pk('*'): self.pop(); ref=True
                n=self.pop()[1]; arr=False
                if self.pk('['): self.pop(); self.pop(']'); arr=True
                ps.append((n,arr,ref))
                if not self.pk(','): break
                self.pop()
        self.pop(')'); self.softnl(); self.pop('{'); body=self.program('}'); self.pop('}')
        return ('define',name,ps,body,void)
    # Pratt parser, binding powers match GNU bc's documented unusual order.
    def expr(self,minp=0):
        if self.pk('-'):
            self.pop(); x=('neg',self.expr(9))
        elif self.pk('!'):
            self.pop(); x=('not',self.expr(3))
        elif self.pk('++') or self.pk('--'):
            op=self.pop()[1]; x=('pre',op,self.expr(10))
        elif self.pk('('):
            self.pop(); x=('paren',self.expr()); self.pop(')')
        elif self.pk()[0]=='NUM': x=('const',self.pop()[1])
        elif self.pk('.'):
            self.pop(); x=('var','last')
        elif self.pk()[0]=='ID':
            n=self.pop()[1]
            if self.pk('('):
                self.pop(); aa=[]
                if not self.pk(')'):
                    while True:
                        if self.pk()[0]=='ID' and self.t[self.i+1][1]=='[' and self.t[self.i+2][1]==']':
                            q=self.pop()[1]; self.pop('['); self.pop(']'); aa.append(('arrarg',q))
                        else: aa.append(self.expr())
                        if not self.pk(','): break
                        self.pop()
                self.pop(')'); x=('call',n,aa)
            elif self.pk('['):
                self.pop(); q=self.expr(); self.pop(']'); x=('array',n,q)
            else: x=('var',n)
        else: raise SyntaxError(self.pk())
        while True:
            op=self.pk()[1]
            if op in ('++','--'):
                if 10<minp: break
                self.pop(); x=('post',op,x); continue
            prec={'||':1,'&&':2,'<':4,'<=':4,'>':4,'>=':4,'==':4,'!=':4,
                  '=':5,'+=':5,'-=':5,'*=':5,'/=':5,'%=':5,'^=':5,
                  '+':6,'-':6,'*':7,'/':7,'%':7,'^':8}.get(op,-1)
            if prec<minp: break
            self.pop(); right=self.expr(prec if op in ('=','+=','-=','*=','/=','%=','^=','^') else prec+1)
            x=('assign',op,x,right) if '=' in op and op not in ('==','!=','<=','>=') else ('bin',op,x,right)
        return x

class Env:
    def __init__(self):
        self.g={}; self.ga={}; self.frames=[]; self.funcs={}
        self.special={'scale':Num(0),'ibase':Num(10),'obase':Num(10),'last':Num(0)}
    def scalar_frame(self,n):
        for f in reversed(self.frames):
            if n in f[0]: return f
        return None
    def array_frame(self,n):
        for f in reversed(self.frames):
            if n in f[1]: return f
        return None
    def geta(self,n):
        f=self.array_frame(n)
        return f[1][n] if f else self.ga.setdefault(n,{})
    def get(self,n):
        if n in self.special:return self.special[n]
        f=self.scalar_frame(n)
        return f[0][n] if f else self.g.setdefault(n,Num())
    def set(self,n,v):
        if n in self.special:
            if n in ('scale','ibase','obase'):
                q=v.integer()
                if n=='scale': q=max(0,q)
                elif n=='ibase': q=max(2,min(16,q))
                else: q=max(2,min(999,q))
                self.special[n]=Num(q)
            else:self.special[n]=v.copy()
        else:
            f=self.scalar_frame(n)
            if f: f[0][n]=v.copy()
            else: self.g[n]=v.copy()

class VM:
    def __init__(self): self.e=Env(); self.col=0; self.stopped=False; self.callbases=[]
    def out(self,s):
        for ch in s:
            if ch=='\n': sys.stdout.write(ch); self.col=0; continue
            if self.col==68: sys.stdout.write('\\\n'); self.col=0
            sys.stdout.write(ch); self.col+=1
        sys.stdout.flush()
    def string(self,s):
        mp={'a':'\a','n':'\n','t':'\t','r':'\r','b':'\b','f':'\f','\\':'\\','q':'"'}; o=''; i=0
        while i<len(s):
            if s[i]=='\\' and i+1<len(s): o+=mp.get(s[i+1],s[i+1]); i+=2
            else:o+=s[i]; i+=1
        return o
    def const(self,z):
        neg=False; parts=z.split('.'); ip=parts[0] or '0'; fp=parts[1] if len(parts)>1 else ''; base=(self.callbases[-1] if self.callbases else self.e.get('ibase').integer())
        def d(c): return ord(c)-48 if c<='9' else ord(c)-55
        # Single digit integer part retains its own value.
        iv=0
        if len(ip)==1: iv=d(ip)
        else:
            for c in ip: iv=iv*base+min(d(c),base-1)
        s=len(fp)
        if not fp:return Num(iv,0)
        num=0
        for c in fp:num=num*base+min(d(c),base-1)
        den=base**len(fp)
        frac=tdiv(num*10**s,den)
        return Num(iv*10**s+frac,s)
    def ref(self,x):
        if x[0]=='var':
            n=x[1]; return (lambda:self.e.get(n),lambda v:self.e.set(n,v))
        if x[0]=='array':
            idx=self.ev(x[2])
            if idx.v<0 or (idx.v>0 and idx.integer()==0): raise RunError()
            i=idx.integer()
            if i>=65536: raise RunError()
            a=self.e.geta(x[1])
            return (lambda:a.setdefault(i,Num()),lambda v:a.__setitem__(i,v.copy()))
        raise RunError()
    def ev(self,x):
        k=x[0]
        if k=='const':return self.const(x[1])
        if k=='paren':return self.ev(x[1])
        if k in ('var','array'):return self.ref(x)[0]().copy()
        if k=='neg': q=self.ev(x[1]); return Num(-q.v,q.s)
        if k=='not':return Num(0 if self.ev(x[1]).nz() else 1)
        if k in ('pre','post'):
            g,s=self.ref(x[2]); old=g().copy(); nv=add(old,Num(1),x[1]=='--'); s(nv); return nv if k=='pre' else old
        if k=='assign':
            g,s=self.ref(x[2]); op=x[1]
            # The lvalue (including its old value for a compound assignment)
            # is evaluated before the right operand.
            old=g().copy() if op!='=' else None
            b=self.ev(x[3])
            v=b if op=='=' else self.calc(op[0],old,b)
            s(v); return v.copy()
        if k=='bin':
            op=x[1]; a=self.ev(x[2])
            if op=='&&': return Num(1 if a.nz() and self.ev(x[3]).nz() else 0)
            if op=='||': return Num(1 if a.nz() or self.ev(x[3]).nz() else 0)
            b=self.ev(x[3]); return self.calc(op,a,b)
        if k=='call': return self.call(x[1],x[2])
        raise RunError()
    def calc(self,op,a,b):
        sc=self.e.get('scale').integer()
        if op=='+':return add(a,b)
        if op=='-':return add(a,b,True)
        if op=='*':return mul(a,b,sc)
        if op=='/':return divn(a,b,sc)
        if op=='%':return remn(a,b,sc)
        if op=='^':return pown(a,b,sc)
        c=cmpn(a,b)
        return Num(int({'<':c<0,'<=':c<=0,'>':c>0,'>=':c>=0,'==':c==0,'!=':c!=0}[op]))
    def call(self,n,args):
        if n=='length':
            a=self.ev(args[0]); ip=abs(a.integer())
            if a.v==0:return Num(max(1,a.s))
            il=len(str(ip)) if ip else 0
            return Num(il+a.s)
        if n=='scale':return Num(self.ev(args[0]).s)
        if n=='sqrt':
            a=self.ev(args[0])
            if a.v<0:raise RunError()
            if a.v in (0,10**a.s) and a.integer() in (0,1):return Num(a.integer())
            rs=max(self.e.get('scale').integer(),a.s)
            # floor(sqrt(value)*10^rs) using integer square root.
            exp=2*rs-a.s
            if exp>=0:v=math.isqrt(a.v*10**exp)
            else:v=math.isqrt(a.v//10**(-exp))
            return Num(v,rs)
        if n not in self.e.funcs:
            # Function arguments are evaluated left-to-right before the call
            # itself fails. Array arguments have no evaluating expression.
            for arg in args:
                if arg[0]!='arrarg': self.ev(arg)
            raise RunError()
        ps,body,void=self.e.funcs[n]
        if len(ps)!=len(args):raise RunError()
        vals=[]
        for (pn,arr,ref),arg in zip(ps,args):
            if arr:
                if arg[0]!='arrarg':raise RunError()
                ar=self.e.geta(arg[1]); vals.append(ar if ref else {i:v.copy() for i,v in ar.items()})
            else: vals.append(self.ev(arg))
        scal={}; arrays={}
        for (pn,arr,ref),v in zip(ps,vals): (arrays if arr else scal).__setitem__(pn,v)
        self.e.frames.append((scal,arrays))
        self.callbases.append(self.e.get('ibase').integer())
        rv=Num()
        try:self.execs(body)
        except Flow as f:
            if f.k=='return':rv=f.v or Num()
            else: self.e.frames.pop(); raise
        finally:
            if self.e.frames and self.e.frames[-1][0] is scal:self.e.frames.pop()
            self.callbases.pop()
        return VOID if void else rv
    def fmt(self,a):
        if a.v==0:return '0'
        base=self.e.get('obase').integer(); neg=a.v<0; av=abs(a.v)
        if base==10:
            q=str(av).rjust(a.s+1,'0')
            z=(q[:-a.s]+'.'+q[-a.s:]) if a.s else q
            if a.s and q[:-a.s]=='0':z=z[1:]
            return ('-' if neg else '')+z
        den=10**a.s; integer=av//den; rem=av%den
        digs=[]
        if integer==0:digs=[0]
        while integer:digs.append(integer%base);integer//=base
        digs=digs[::-1]
        width=len(str(base-1))
        def fd(d,first=False):
            if base<=10:return str(d)
            if base<=16:return '0123456789ABCDEF'[d]
            return ' '+str(d).zfill(width)
        ip=''.join(fd(d,i==0) for i,d in enumerate(digs))
        if base>16 and digs: ip=''.join(fd(d) for d in digs)
        frac=''
        if a.s:
            # minimum k with base^k >= 10^scale
            k=0;p=1
            while p<den:k+=1;p*=base
            ds=[]
            for _ in range(k): rem*=base; ds.append(rem//den); rem%=den
            if base>16: frac='.'+str(ds[0]).zfill(width)+''.join(' '+str(d).zfill(width) for d in ds[1:])
            else:frac='.'+''.join(fd(d,True) for d in ds)
        return ('-' if neg else '')+ip+frac
    def execs(self,ss):
        for s in ss:self.stmt(s)
    def stmt(self,s):
        k=s[0]
        if k=='block':self.execs(s[1])
        elif k=='define':self.e.funcs[s[1]]=(s[2],s[3],s[4])
        elif k=='expr':
            v=self.ev(s[1])
            if s[1][0]!='assign' and v is not VOID:self.out(self.fmt(v)+'\n');self.e.set('last',v)
        elif k=='string':self.out(s[1])
        elif k=='print':
            for typ,x in s[1]:
                if typ=='str':self.out(self.string(x))
                else:
                    v=self.ev(x);self.out(self.fmt(v));self.e.set('last',v)
        elif k=='if':
            if self.ev(s[1]).nz():self.stmt(s[2])
            elif s[3]:self.stmt(s[3])
        elif k=='while':
            while self.ev(s[1]).nz():
                try:self.stmt(s[2])
                except Flow as f:
                    if f.k=='break':break
                    raise
        elif k=='for':
            if s[1]:self.ev(s[1])
            while True:
                if s[2] and not self.ev(s[2]).nz():break
                try:self.stmt(s[4])
                except Flow as f:
                    if f.k=='break':break
                    if f.k!='continue':raise
                if s[3]:self.ev(s[3])
        elif k in ('break','continue'):raise Flow(k)
        elif k=='return':raise Flow('return',self.ev(s[1]) if s[1] else Num())
        elif k=='halt' or k=='quit':raise Halt()
        elif k=='auto':
            if not self.e.frames:return
            for n,a in s[1]:
                if a:self.e.frames[-1][1][n]={}
                else:self.e.frames[-1][0][n]=Num()

def has_quit(x):
    if isinstance(x,tuple):
        if x and x[0]=='quit': return True
        return any(has_quit(y) for y in x[1:])
    if isinstance(x,list): return any(has_quit(y) for y in x)
    return False

def run_source(vm,src):
    try:p=Parser(src); ss=p.program()
    except SyntaxError:return
    for st in ss:
        # GNU bc's quit is acted on by the reader, even in a false branch or
        # function body. Earlier complete top-level statements have run.
        if has_quit(st): raise Halt()
        try:vm.stmt(st)
        except RunError:continue
        except Flow:continue

def main(argv):
    vm=VM()
    try:
        for fn in argv:
            with open(fn,encoding='latin1') as f:run_source(vm,f.read())
        if not vm.stopped:run_source(vm,sys.stdin.read())
    except Halt:pass
    except (OSError,KeyboardInterrupt):return 1
    return 0
if __name__=='__main__':sys.exit(main(sys.argv[1:]))
