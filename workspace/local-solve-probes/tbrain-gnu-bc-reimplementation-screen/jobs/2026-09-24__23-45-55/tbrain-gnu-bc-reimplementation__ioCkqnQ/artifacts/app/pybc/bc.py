"""A small, pure Python implementation of GNU bc's language."""
import sys, math

class BCError(Exception): pass
class BreakSig(Exception): pass
class ContinueSig(Exception): pass
class HaltSig(Exception): pass
class QuitSig(Exception): pass
class ReturnSig(Exception):
    def __init__(self, value): self.value=value

class Num:
    __slots__=('c','s')
    def __init__(self,c=0,s=0): self.c=int(c); self.s=int(s)
    def copy(self): return Num(self.c,self.s)
    def truth(self): return self.c != 0
    def integer(self):
        return truncdiv(self.c, 10**self.s)

def truncdiv(a,b):
    if b == 0: raise BCError('divide by zero')
    return (1 if a*b >= 0 else -1) * (abs(a)//abs(b))

def align(a,b):
    s=max(a.s,b.s)
    return a.c*10**(s-a.s), b.c*10**(s-b.s), s

def add(a,b,neg=False):
    x,y,s=align(a,b); return Num(x-y if neg else x+y,s)

def mul(a,b,scale):
    raw_s=a.s+b.s
    out=min(raw_s,max(scale,a.s,b.s))
    c=a.c*b.c
    if raw_s>out: c=truncdiv(c,10**(raw_s-out))
    elif out>raw_s: c*=10**(out-raw_s)
    return Num(c,out)

def div(a,b,scale):
    if b.c==0: raise BCError('divide by zero')
    e=scale+b.s-a.s
    c=truncdiv(a.c*(10**e),b.c) if e>=0 else truncdiv(a.c,b.c*10**(-e))
    return Num(c,scale)

def cmpnum(a,b):
    x,y,_=align(a,b); return (x>y)-(x<y)

def const_num(text,base):
    neg=False
    if '.' in text: ip,fp=text.split('.',1)
    else: ip,fp=text,''
    digs='0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    def dv(ch): return digs.index(ch)
    allcount=len(ip)+len(fp)
    # A one-digit constant is independent of ibase.
    if allcount==1 and fp=='': return Num(dv(ip),0)
    vals=[min(dv(ch),base-1) for ch in ip] if ip else []
    iv=0
    for d in vals: iv=iv*base+d
    n=len(fp)
    if not n: return Num(iv,0)
    fv=0
    for ch in fp: fv=fv*base+min(dv(ch),base-1)
    c=iv*10**n + (fv*10**n)//(base**n)
    return Num(c,n)

class Lexer:
    def __init__(self,s): self.s=s; self.i=0; self.t=[]; self.scan(); self.t.append(('EOF',''))
    def scan(self):
        s=self.s; n=len(s)
        while self.i<n:
            i=self.i; c=s[i]
            if c in ' \t\r': self.i+=1; continue
            if c=='\\' and i+1<n and s[i+1]=='\n': self.i+=2; continue
            if c=='\n': self.t.append(('NL','\n')); self.i+=1; continue
            if c=='#':
                j=s.find('\n',i); self.i=n if j<0 else j; continue
            if s.startswith('/*',i):
                j=s.find('*/',i+2); self.i=n if j<0 else j+2; continue
            if c=='"':
                j=i+1
                while j<n and s[j]!='"': j+=1
                self.t.append(('STR',s[i+1:j])); self.i=min(j+1,n); continue
            if c.islower():
                j=i+1
                while j<n and (s[j].islower() or s[j].isdigit() or s[j]=='_'): j+=1
                self.t.append(('ID',s[i:j])); self.i=j; continue
            if c.isdigit() or c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ' or (c=='.' and i+1<n and (s[i+1].isdigit() or s[i+1].isupper())):
                j=i; dots=0
                while j<n and (s[j].isdigit() or s[j].isupper() or (s[j]=='.' and dots==0)):
                    if s[j]=='.': dots+=1
                    j+=1
                self.t.append(('NUM',s[i:j])); self.i=j; continue
            found=False
            for op in ('++','--','<=','>=','==','!=','&&','||','+=','-=','*=','/=','%=','^=','=+','=-','=*','=/','=%','=^'):
                if s.startswith(op,i): self.t.append((op,op)); self.i+=len(op); found=True; break
            if found: continue
            self.t.append((c,c)); self.i+=1

class Parser:
    def __init__(self,s): self.z=Lexer(s).t; self.p=0
    def typ(self): return self.z[self.p][0]
    def val(self): return self.z[self.p][1]
    def take(self,t=None):
        x=self.z[self.p]
        if t is not None and x[0]!=t: raise BCError('syntax')
        self.p+=1; return x
    def seps(self):
        had=False
        while self.typ() in ('NL',';'): self.p+=1; had=True
        return had
    def nls(self):
        while self.typ()=='NL': self.p+=1
    def program(self):
        # A top-level newline ends an execution block; semicolons do not.
        blocks=[]; cur=[]
        while self.typ() in ('NL',';'): self.p+=1
        while self.typ()!='EOF':
            st=self.stmt(); cur.append(st)
            saw_nl=False
            while self.typ() in ('NL',';'):
                if self.typ()=='NL': saw_nl=True
                self.p+=1
            if self.hasquit(st):
                # quit acts when read, even in an unexecuted statement.  The
                # not-yet-complete block containing it is never executed.
                return blocks
            if saw_nl:
                blocks.append(cur); cur=[]
        if cur: blocks.append(cur)
        return blocks
    def hasquit(self,x):
        if isinstance(x,tuple):
            if x and x[0]=='quit': return True
            return any(self.hasquit(q) for q in x[1:])
        if isinstance(x,list): return any(self.hasquit(q) for q in x)
        return False
    def stmt(self):
        t=self.typ(); v=self.val()
        if t=='{':
            self.take(); a=[]; self.seps()
            while self.typ() not in ('}','EOF'): a.append(self.stmt()); self.seps()
            self.take('}'); return ('block',a)
        if t=='STR': return ('string',self.take()[1])
        if t=='ID' and v=='quit': self.take(); return ('quit',)
        if t=='ID' and v=='define': return self.function()
        if t=='ID' and v=='print':
            self.take(); a=[]
            while True:
                if self.typ()=='STR': a.append(('s',self.take()[1]))
                else: a.append(('e',self.expr()))
                if self.typ()!=',': break
                self.take(',')
            return ('print',a)
        if t=='ID' and v in ('if','while'):
            kind=self.take()[1]; self.nls(); self.take('('); e=self.expr(); self.take(')'); self.nls(); a=self.stmt()
            b=None; save=self.p; self.nls()
            if kind=='if' and self.typ()=='ID' and self.val()=='else': self.take(); self.nls(); b=self.stmt()
            elif kind=='if': self.p=save
            return (kind,e,a,b) if kind=='if' else (kind,e,a)
        if t=='ID' and v=='for':
            self.take(); self.nls(); self.take('(')
            a=None if self.typ()==';' else self.expr(); self.take(';')
            b=None if self.typ()==';' else self.expr(); self.take(';')
            c=None if self.typ()==')' else self.expr(); self.take(')'); self.nls()
            return ('for',a,b,c,self.stmt())
        if t=='ID' and v in ('break','continue','halt'):
            self.take(); return (v,)
        if t=='ID' and v=='return':
            self.take()
            if self.typ() in ('NL',';','}'): return ('return',None)
            if self.typ()=='(':
                self.take(); e=self.expr(); self.take(')')
            else: e=self.expr()
            return ('return',e)
        e=self.expr(); return ('expr',e,self.assignment_statement(e))
    def assignment_statement(self,e):
        # Assignment has higher precedence than comparisons and boolean ops,
        # but lexical `a=...` still makes the whole input an assignment stmt.
        if e[0]=='assign': return True
        if e[0]=='bin' and e[1] in ('<','<=','>','>=','==','!=','&&','||'):
            return self.assignment_statement(e[2])
        return False
    def function(self):
        self.take(); self.nls(); void=False
        if self.typ()=='ID' and self.val()=='void': self.take(); void=True
        name=self.take('ID')[1]; self.nls(); self.take('('); pars=[]
        if self.typ()!=')':
            while True:
                ref=False
                if self.typ()=='*': self.take(); ref=True
                pn=self.take('ID')[1]; arr=False
                if self.typ()=='[': self.take(); self.take(']'); arr=True
                pars.append((pn,arr,ref))
                if self.typ()!=',': break
                self.take(',')
        self.take(')'); self.nls(); self.take('{'); self.seps(); autos=[]
        if self.typ()=='ID' and self.val()=='auto':
            self.take()
            while True:
                an=self.take('ID')[1]; arr=False
                if self.typ()=='[': self.take(); self.take(']'); arr=True
                autos.append((an,arr))
                if self.typ()!=',': break
                self.take(',')
            self.seps()
        body=[]
        while self.typ() not in ('}','EOF'): body.append(self.stmt()); self.seps()
        self.take('}'); return ('define',name,pars,autos,body,void)
    def expr(self): return self.orx()
    def orx(self):
        x=self.andx()
        while self.typ()=='||': self.take(); x=('bin','||',x,self.andx())
        return x
    def andx(self):
        x=self.notx()
        while self.typ()=='&&': self.take(); x=('bin','&&',x,self.notx())
        return x
    def notx(self):
        if self.typ()=='!': self.take(); return ('un','!',self.notx())
        return self.rel()
    def rel(self):
        x=self.assign()
        while self.typ() in ('<','<=','>','>=','==','!='):
            op=self.take()[0]; x=('bin',op,x,self.assign())
        return x
    def assign(self):
        x=self.add()
        if self.typ() in ('=','+=','-=','*=','/=','%=','^=','=+','=-','=*','=/','=%','=^'):
            op=self.take()[0]
            if x[0] not in ('var','arr'): raise BCError('bad assignment')
            return ('assign',op,x,self.assign())
        return x
    def add(self):
        x=self.term()
        while self.typ() in ('+','-'):
            op=self.take()[0]; x=('bin',op,x,self.term())
        return x
    def term(self):
        x=self.power()
        while self.typ() in ('*','/','%'):
            op=self.take()[0]; x=('bin',op,x,self.power())
        return x
    def power(self):
        x=self.unary()
        if self.typ()=='^': self.take(); x=('bin','^',x,self.power())
        return x
    def unary(self):
        if self.typ()=='-': self.take(); return ('un','-',self.unary())
        if self.typ() in ('++','--'):
            op=self.take()[0]; x=self.unary()
            if x[0] not in ('var','arr'): raise BCError('increment')
            return ('inc',op,x,True)
        return self.post()
    def post(self):
        x=self.atom()
        if self.typ() in ('++','--'):
            op=self.take()[0]
            if x[0] not in ('var','arr'): raise BCError('increment')
            return ('inc',op,x,False)
        return x
    def atom(self):
        t=self.typ()
        if t=='NUM': return ('num',self.take()[1])
        if t=='.': self.take(); return ('var','last')
        if t=='(':
            self.take(); x=self.expr(); self.take(')'); return ('paren',x)
        if t=='ID':
            n=self.take()[1]
            if self.typ()=='(':
                self.take(); a=[]
                if self.typ()!=')':
                    while True:
                        # Array actual parameter is name[].
                        if self.typ()=='ID' and self.z[self.p+1][0]=='[' and self.z[self.p+2][0]==']':
                            q=self.take()[1]; self.take('['); self.take(']'); a.append(('arrayarg',q))
                        else: a.append(self.expr())
                        if self.typ()!=',': break
                        self.take(',')
                self.take(')'); return ('call',n,a)
            if self.typ()=='[':
                self.take(); i=self.expr(); self.take(']'); return ('arr',n,i)
            return ('var',n)
        raise BCError('expression')

class Engine:
    def __init__(self):
        self.globals={'scale':Num(0),'ibase':Num(10),'obase':Num(10),'last':Num(0)}
        self.arrays={}; self.frames=[]; self.funcs={}; self.callbases=[]; self.col=0
    def getv(self,n):
        for f in reversed(self.frames):
            if n in f[0]: return f[0][n]
        return self.globals.get(n,Num(0))
    def setv(self,n,v):
        v=v.copy()
        if n=='scale': v=Num(max(0,v.integer()))
        elif n=='ibase': v=Num(min(16,max(2,v.integer())))
        elif n=='obase': v=Num(min(999,max(2,v.integer())))
        for f in reversed(self.frames):
            if n in f[0]: f[0][n]=v; return v
        self.globals[n]=v; return v
    def geta(self,n):
        for f in reversed(self.frames):
            if n in f[1]: return f[1][n]
        return self.arrays.setdefault(n,{})
    def idx(self,x):
        v=self.ev(x)
        if v.c<0: raise BCError('bad index')
        # GNU bc truncates indexes >= 1, but rejects a positive fraction < 1.
        if v.s and 0 < v.c < 10**v.s: raise BCError('bad index')
        i=v.integer()
        if i<0 or i>=65536: raise BCError('bad index')
        return i
    def resolve(self,x):
        if x[0]=='var': return ('v',x[1])
        return ('a',self.geta(x[1]),self.idx(x[2]))
    def resolved_get(self,r):
        return self.getv(r[1]) if r[0]=='v' else r[1].get(r[2],Num(0))
    def resolved_set(self,r,v):
        if r[0]=='v': return self.setv(r[1],v)
        r[1][r[2]]=v.copy(); return v
    def refget(self,x): return self.resolved_get(self.resolve(x))
    def refset(self,x,v): return self.resolved_set(self.resolve(x),v)
    def scale(self): return self.getv('scale').integer()
    def ev(self,x):
        k=x[0]
        if k=='num': return const_num(x[1], self.callbases[-1] if self.callbases else self.getv('ibase').integer())
        if k=='paren': return self.ev(x[1])
        if k in ('var','arr'): return self.refget(x).copy()
        if k=='un':
            a=self.ev(x[2])
            if a is None: raise BCError('void value')
            return Num(-a.c,a.s) if x[1]=='-' else Num(0 if a.truth() else 1)
        if k=='inc':
            ref=self.resolve(x[2]); old=self.resolved_get(ref).copy()
            new=add(old,Num(1),x[1]=='--'); self.resolved_set(ref,new)
            return new.copy() if x[3] else old
        if k=='assign':
            ref=self.resolve(x[2])
            rhs=self.ev(x[3]); op=x[1]
            if rhs is None: raise BCError('void value')
            if op!='=':
                oper=op[0] if op[0]!='=' else op[1]
                rhs=self.binary(oper,self.resolved_get(ref).copy(),rhs)
            self.resolved_set(ref,rhs); return rhs.copy()
        if k=='bin':
            # GNU bc evaluates both boolean operands.
            a=self.ev(x[2]); b=self.ev(x[3])
            if a is None or b is None: raise BCError('void value')
            return self.binary(x[1],a,b)
        if k=='call': return self.call(x[1],x[2])
        raise BCError('evaluation')
    def binary(self,op,a,b):
        if op=='+': return add(a,b)
        if op=='-': return add(a,b,True)
        if op=='*': return mul(a,b,self.scale())
        if op=='/': return div(a,b,self.scale())
        if op=='%':
            if b.c==0: raise BCError('remainder by zero')
            q=div(a,b,self.scale()); prod=mul(q,b,max(self.scale()+b.s,a.s)); return add(a,prod,True)
        if op=='^':
            e=b.integer()
            if a.c==0 and e<0: raise BCError('zero negative power')
            if e==0: return Num(1)
            if e<0:
                p=self.powpos(a,-e); return div(Num(1),p,self.scale())
            return self.powpos(a,e)
        c=cmpnum(a,b)
        if op in ('<','<=','>','>=','==','!='):
            return Num(int({'<':c<0,'<=':c<=0,'>':c>0,'>=':c>=0,'==':c==0,'!=':c!=0}[op]))
        if op=='&&': return Num(int(a.truth() and b.truth()))
        if op=='||': return Num(int(a.truth() or b.truth()))
        raise BCError('operator')
    def powpos(self,a,e):
        target=min(a.s*e,max(self.scale(),a.s)); c=pow(a.c,e); rs=a.s*e
        if rs>target: c=truncdiv(c,10**(rs-target))
        elif target>rs: c*=10**(target-rs)
        return Num(c,target)
    def call(self,n,args):
        if n in ('length','scale','sqrt'):
            if len(args)!=1: raise BCError('parameters')
            a=self.ev(args[0])
            if a is None: raise BCError('void value')
            if n=='scale': return Num(a.s)
            if n=='length': return Num(max(a.s,len(str(abs(a.c))) if a.c else 1))
            if a.c<0: raise BCError('sqrt negative')
            if a.c in (0,10**a.s): return Num(0 if a.c==0 else 1)
            t=max(self.scale(),a.s); exp=2*t-a.s
            q=a.c*10**exp if exp>=0 else a.c//10**(-exp)
            return Num(math.isqrt(q),t)
        if n not in self.funcs: raise BCError('undefined function')
        pars,autos,body,void=self.funcs[n]
        if len(args)!=len(pars): raise BCError('parameters')
        vals={}; ars={}
        # Evaluate actuals in caller before installing frame.
        prepared=[]
        for (pn,isarr,ref),arg in zip(pars,args):
            if isarr:
                if arg[0]!='arrayarg': raise BCError('array parameter')
                ar=self.geta(arg[1]); prepared.append(ar if ref else {i:v.copy() for i,v in ar.items()})
            else:
                if arg[0]=='arrayarg': raise BCError('scalar parameter')
                prepared.append(self.ev(arg))
        for p,v in zip(pars,prepared):
            (ars if p[1] else vals)[p[0]]=v
        for an,isarr in autos: (ars if isarr else vals)[an]={} if isarr else Num(0)
        callbase=self.getv('ibase').integer()
        self.frames.append((vals,ars)); self.callbases.append(callbase)
        try:
            try: self.run(body); ret=Num(0)
            except ReturnSig as r: ret=r.value
        finally:
            self.callbases.pop(); self.frames.pop()
        if void: return None
        return ret
    def emit(self,s):
        for ch in s:
            if ch=='\n': sys.stdout.write(ch); self.col=0; continue
            if self.col==68: sys.stdout.write('\\\n'); self.col=0
            sys.stdout.write(ch); self.col+=1
        sys.stdout.flush()
    def fmt(self,a):
        if a.c==0: return '0'
        neg=a.c<0; c=abs(a.c); base=self.getv('obase').integer(); sign='-' if neg else ''
        den=10**a.s; iv=c//den; rem=c%den
        chars='0123456789ABCDEF'
        digs=[]
        if iv==0: digs=[]
        else:
            while iv: digs.append(iv%base); iv//=base
            digs.reverse()
        if base<=16: ip=''.join(chars[d] for d in digs) if digs else ''
        else:
            w=len(str(base-1)); ip=''.join(' '+str(d).zfill(w) for d in digs) if digs else ''
        fp=''
        if a.s:
            k=0; q=1
            while q<10**a.s: q*=base; k+=1
            fd=[]
            for _ in range(k): rem*=base; fd.append(rem//den); rem%=den
            if base<=16: fp='.'+''.join(chars[d] for d in fd)
            else:
                w=len(str(base-1)); fp='.'+' '.join(str(d).zfill(w) for d in fd)
        return sign+ip+fp
    def exec(self,s):
        k=s[0]
        if k=='block': return self.run(s[1])
        if k=='define': self.funcs[s[1]]=(s[2],s[3],s[4],s[5]); return
        if k=='string': self.emit(s[1]); return
        if k=='print':
            for q,v in s[1]:
                if q=='s':
                    trans={'a':'\a','b':'\b','f':'\f','n':'\n','r':'\r','q':'"','t':'\t','\\':'\\'}; out=''; i=0
                    while i<len(v):
                        if v[i]=='\\' and i+1<len(v): out+=trans.get(v[i+1],''); i+=2
                        else: out+=v[i]; i+=1
                    self.emit(out)
                else:
                    z=self.ev(v)
                    if z is None: raise BCError('void value')
                    self.setv('last',z); self.emit(self.fmt(z))
            return
        if k=='expr':
            z=self.ev(s[1])
            if z is None:
                if s[2]: raise BCError('void value')
                return
            if not s[2]: self.setv('last',z); self.emit(self.fmt(z)+'\n')
            return
        if k=='if':
            cond=self.ev(s[1])
            if cond is None: raise BCError('void value')
            branch=s[2] if cond.truth() else s[3]
            if branch is not None: self.exec(branch)
            return
        if k=='while':
            while True:
                cond=self.ev(s[1])
                if cond is None: raise BCError('void value')
                if not cond.truth(): break
                try: self.exec(s[2])
                except BreakSig: break
            return
        if k=='for':
            if s[1] is not None: self.ev(s[1])
            while True:
                if s[2] is not None:
                    cond=self.ev(s[2])
                    if cond is None: raise BCError('void value')
                    if not cond.truth(): break
                try: self.exec(s[4])
                except ContinueSig: pass
                except BreakSig: break
                if s[3] is not None: self.ev(s[3])
            return
        if k=='break': raise BreakSig()
        if k=='continue': raise ContinueSig()
        if k=='halt': raise HaltSig()
        if k=='return': raise ReturnSig(Num(0) if s[1] is None else self.ev(s[1]))
    def run(self,a):
        for s in a: self.exec(s)

def main(argv):
    chunks=[]
    try:
        for f in argv:
            with open(f,encoding='latin1') as h: chunks.append(h.read())
        chunks.append(sys.stdin.read())
    except OSError as e:
        sys.stderr.write(str(e)+'\n'); return 1
    src=''.join(chunks); eng=Engine()
    try: prog=Parser(src).program()
    except QuitSig: return 0
    except BCError as e: return 0
    try:
        # A runtime error abandons the entire newline execution block.
        for block in prog:
            try: eng.run(block)
            except BCError: continue
    except (HaltSig,QuitSig): pass
    return 0
if __name__=='__main__': sys.exit(main(sys.argv[1:]))
