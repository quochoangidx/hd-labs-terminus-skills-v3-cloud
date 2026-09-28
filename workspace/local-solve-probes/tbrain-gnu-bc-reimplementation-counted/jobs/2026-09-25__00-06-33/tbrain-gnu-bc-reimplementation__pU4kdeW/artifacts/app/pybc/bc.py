#!/usr/bin/env python3
import sys
from math import isqrt

class Num:
    __slots__=('v','s')
    def __init__(self,v=0,s=0): self.v=int(v); self.s=max(0,int(s))
    def copy(self): return Num(self.v,self.s)
    def integer(self):
        return truncdiv(self.v,10**self.s)
    def truth(self): return self.v != 0

def truncdiv(a,b):
    if b==0: raise RunError()
    return (abs(a)//abs(b)) * (-1 if (a<0)^(b<0) else 1)
def rescale(x,s):
    if s>=x.s: return Num(x.v*10**(s-x.s),s)
    return Num(truncdiv(x.v,10**(x.s-s)),s)
def add(a,b,sub=False):
    s=max(a.s,b.s); return Num(rescale(a,s).v + (-1 if sub else 1)*rescale(b,s).v,s)
def mul(a,b,glob):
    s=min(a.s+b.s,max(glob,a.s,b.s)); return rescale(Num(a.v*b.v,a.s+b.s),s)
def divide(a,b,s):
    if b.v==0: raise RunError()
    # (a.v/10^a.s)/(b.v/10^b.s), represented at scale s
    p=a.v*10**(b.s+s); q=b.v*10**a.s
    return Num(truncdiv(p,q),s)
def rem(a,b,glob):
    if b.v==0: raise RunError()
    q=divide(a,b,glob); return add(a,mul(q,b,max(glob+b.s,a.s)),True)
def power(a,b,glob):
    n=b.integer()
    if n<0:
        if a.v==0: raise RunError()
        raw=Num(pow(a.v,-n),a.s*(-n)); return divide(Num(1,0),raw,glob)
    if n==0: return Num(1,0)
    raw=Num(pow(a.v,n),a.s*n)
    return rescale(raw,min(a.s*n,max(glob,a.s)))
def cmp(a,b):
    s=max(a.s,b.s); av=rescale(a,s).v; bv=rescale(b,s).v
    return (av>bv)-(av<bv)

class RunError(Exception): pass
class BreakSig(Exception): pass
class ContinueSig(Exception): pass
class ReturnSig(Exception):
    def __init__(self,v): self.v=v
class HaltSig(Exception): pass
class QuitSig(Exception): pass

class Token:
    __slots__=('k','v')
    def __init__(self,k,v=None): self.k=k; self.v=v if v is not None else k
    def __repr__(self): return f'{self.k}:{self.v}'

def lex(src):
    out=[]; i=0; n=len(src)
    while i<n:
        c=src[i]
        if c=='\\' and i+1<n and src[i+1]=='\n': i+=2; continue
        if c in ' \t\r\f': i+=1; continue
        if c=='\n': out.append(Token('NL')); i+=1; continue
        if c=='#':
            while i<n and src[i]!='\n': i+=1
            continue
        if src.startswith('/*',i):
            j=src.find('*/',i+2); i=n if j<0 else j+2
            continue
        if c=='"':
            i+=1; z=[]
            while i<n and src[i]!='"':
                z.append(src[i]); i+=1
            i+=1; out.append(Token('STR',''.join(z))); continue
        if c.isdigit() or c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ' or (c=='.' and i+1<n and (src[i+1].isdigit() or src[i+1].isupper())):
            j=i
            while j<n and (src[j].isdigit() or src[j].isupper() or src[j]=='.'): j+=1
            out.append(Token('NUM',src[i:j])); i=j; continue
        if c.islower() or c=='_':
            j=i+1
            while j<n and (src[j].islower() or src[j].isdigit() or src[j]=='_'): j+=1
            out.append(Token('ID',src[i:j])); i=j; continue
        found=False
        for op in ('++','--','+=','-=','*=','/=','%=','^=','==','!=','<=','>=','&&','||'):
            if src.startswith(op,i): out.append(Token(op)); i+=len(op); found=True; break
        if found: continue
        if c=='.': out.append(Token('ID','last'))
        else: out.append(Token(c))
        i+=1
    out.append(Token('EOF')); return out

# AST expressions: ('num',text), ('var',name), ('idx',name,e), ('call',name,args),
# ('un',op,e), ('bin',op,a,b), ('as',op,l,r), ('pre/post',op,l), ('builtin',name,e)
class Parser:
    def __init__(self,t): self.t=t; self.i=0
    def cur(self): return self.t[self.i]
    def at(self,k,v=None): return self.cur().k==k and (v is None or self.cur().v==v)
    def pop(self,k=None):
        x=self.cur()
        if k is not None and x.k!=k: raise SyntaxError((k,x))
        self.i+=1; return x
    def isn(self,name): return self.at('ID',name)
    def skipnl(self):
        while self.at('NL'): self.i+=1
    def program(self):
        blocks=[]; cur=[]
        while not self.at('EOF'):
            while self.at(';') or self.at('NL'):
                if self.at('NL') and cur: blocks.append(cur); cur=[]
                self.i+=1
            if self.at('EOF'): break
            cur.append(self.stmt())
            if self.at('NL'):
                blocks.append(cur); cur=[]; self.skipnl()
            elif self.at(';'): self.pop(';')
        if cur: blocks.append(cur)
        return blocks
    def stmt(self):
        if self.at('{'):
            self.pop(); a=[]; self.skipnl()
            while not self.at('}'):
                if self.at(';') or self.at('NL'): self.i+=1; continue
                a.append(self.stmt())
                if self.at(';'): self.pop()
                self.skipnl()
            self.pop('}'); return ('block',a)
        if self.isn('define'): return self.func()
        if self.isn('if'):
            self.pop(); self.skipnl(); self.pop('('); e=self.expr(); self.pop(')'); self.skipnl(); a=self.stmt(); self.skipnl()
            b=None
            if self.isn('else'):
                self.pop(); self.skipnl(); b=self.stmt()
            return ('if',e,a,b)
        if self.isn('while'):
            self.pop(); self.skipnl(); self.pop('('); e=self.expr(); self.pop(')'); self.skipnl(); return ('while',e,self.stmt())
        if self.isn('for'):
            self.pop(); self.skipnl(); self.pop('(')
            a=None if self.at(';') else self.expr(); self.pop(';')
            b=None if self.at(';') else self.expr(); self.pop(';')
            c=None if self.at(')') else self.expr(); self.pop(')'); self.skipnl()
            return ('for',a,b,c,self.stmt())
        if self.isn('break'): self.pop(); return ('break',)
        if self.isn('continue'): self.pop(); return ('continue',)
        if self.isn('halt'): self.pop(); return ('halt',)
        if self.isn('quit'): self.pop(); return ('quit',)
        if self.isn('return'):
            self.pop()
            if self.at('('): self.pop(); e=self.expr(); self.pop(')'); return ('return',e)
            if self.at(';') or self.at('NL') or self.at('}'): return ('return',None)
            return ('return',self.expr())
        if self.isn('print'):
            self.pop(); a=[]
            while True:
                if self.at('STR'): a.append(('str',self.pop().v))
                else: a.append(('expr',self.expr()))
                if not self.at(','): break
                self.pop()
            return ('print',a)
        if self.at('STR'): return ('string',self.pop().v)
        return ('expr',self.expr())
    def func(self):
        self.pop(); self.skipnl(); void=False
        if self.isn('void'): self.pop(); void=True
        name=self.pop('ID').v; self.pop('('); pars=[]
        while not self.at(')'):
            ref=False
            if self.at('*'): self.pop(); ref=True
            nm=self.pop('ID').v; arr=False
            if self.at('['): self.pop(); self.pop(']'); arr=True
            pars.append((nm,arr,ref))
            if not self.at(','): break
            self.pop()
        self.pop(')'); self.skipnl(); self.pop('{'); self.skipnl(); autos=[]; body=[]
        while not self.at('}'):
            if self.isn('auto'):
                self.pop()
                while True:
                    nm=self.pop('ID').v; arr=False
                    if self.at('['): self.pop(); self.pop(']'); arr=True
                    autos.append((nm,arr))
                    if not self.at(','): break
                    self.pop()
            else: body.append(self.stmt())
            if self.at(';'): self.pop()
            self.skipnl()
        self.pop('}'); return ('define',name,pars,autos,body,void)
    def expr(self,minp=0):
        x=self.prefix()
        # precedence low to high; assignment right associative, exponent right associative
        prec={'=':1,'+=':1,'-=':1,'*=':1,'/=':1,'%=':1,'^=':1,'||':2,'&&':3,
              '==':4,'!=':4,'<':4,'>':4,'<=':4,'>=':4,'+':5,'-':5,'*':6,'/':6,'%':6,'^':8}
        while self.cur().k in prec and prec[self.cur().k]>=minp:
            op=self.pop().k; p=prec[op]; y=self.expr(p if op in ('=','+=','-=','*=','/=','%=','^=','^') else p+1)
            x=('as',op,x,y) if op in ('=','+=','-=','*=','/=','%=','^=') else ('bin',op,x,y)
        return x
    def prefix(self):
        if self.at('-') or self.at('+') or self.at('!'):
            op=self.pop().k; return ('un',op,self.expr(7))
        if self.at('++') or self.at('--'):
            op=self.pop().k; return ('pre',op,self.prefix())
        if self.at('('): self.pop(); x=self.expr(); self.pop(')')
        elif self.at('NUM'): x=('num',self.pop().v)
        elif self.at('ID'):
            nm=self.pop().v
            if nm in ('length','scale','sqrt') and self.at('('):
                self.pop(); e=self.expr(); self.pop(')'); x=('builtin',nm,e)
            elif self.at('('):
                self.pop(); a=[]
                while not self.at(')'):
                    # bare array argument
                    if self.at('ID') and self.t[self.i+1].k=='[' and self.t[self.i+2].k==']':
                        z=self.pop().v; self.pop(); self.pop(); a.append(('array',z))
                    else: a.append(self.expr())
                    if not self.at(','): break
                    self.pop()
                self.pop(')'); x=('call',nm,a)
            elif self.at('['):
                self.pop(); e=self.expr(); self.pop(']'); x=('idx',nm,e)
            else: x=('var',nm)
        else: raise SyntaxError(self.cur())
        if self.at('++') or self.at('--'): x=('post',self.pop().k,x)
        return x

class Env:
    def __init__(self,parent=None): self.parent=parent; self.vars={}; self.arrays={}
    def varenv(self,n):
        e=self; last=self
        while e:
            last=e
            if n in e.vars: return e
            e=e.parent
        return last
    def arrenv(self,n):
        e=self; last=self
        while e:
            last=e
            if n in e.arrays: return e
            e=e.parent
        return last


class Machine:
    def __init__(self):
        self.g=Env(); self.env=self.g; self.funcs={}; self.scale=0; self.ibase=10; self.obase=10; self.last=Num(); self.col=0; self.callbase=None
    def rawout(self,s):
        for c in s:
            if self.col==68:
                sys.stdout.write('\\\n'); self.col=0
            sys.stdout.write(c)
            if c=='\n': self.col=0
            else: self.col+=1
    def getvar(self,n):
        if n=='scale': return Num(self.scale)
        if n=='ibase': return Num(self.ibase)
        if n=='obase': return Num(self.obase)
        if n=='last': return self.last.copy()
        e=self.env.varenv(n); return e.vars.get(n,Num()).copy()
    def setvar(self,n,x):
        x=x.copy()
        if n=='scale': self.scale=max(0,x.integer()); return
        if n=='ibase': self.ibase=max(2,min(16,x.integer())); return
        if n=='obase': self.obase=max(2,min(999,x.integer())); return
        if n=='last': self.last=x; return
        self.env.varenv(n).vars[n]=x
    def idx(self,x):
        # forbidden negative and strictly fractional (0,1)
        if x.v<0 or (0<x.v<10**x.s): raise RunError()
        return x.integer()
    def lget(self,e):
        if e[0]=='var': return self.getvar(e[1])
        if e[0]=='idx':
            i=self.idx(self.eval(e[2])); en=self.env.arrenv(e[1]); return en.arrays.get(e[1],{}).get(i,Num()).copy()
        raise RunError()
    def lset(self,e,x):
        if e[0]=='var': self.setvar(e[1],x); return
        if e[0]=='idx':
            i=self.idx(self.eval(e[2])); en=self.env.arrenv(e[1]); en.arrays.setdefault(e[1],{})[i]=x.copy(); return
        raise RunError()
    def const(self,s):
        base=self.callbase if self.callbase is not None else self.ibase
        ip,_,fp=s.partition('.'); nd=len(fp); ip=ip or '0'
        def dv(c): return ord(c)-48 if c<='9' else ord(c)-55
        single=len(ip)==1
        iv=0
        for c in ip:
            d=dv(c); iv=iv*base+(d if single else min(d,base-1))
        if not fp: return Num(iv,0)
        num=0
        for c in fp: num=num*base+min(dv(c),base-1)
        den=base**nd
        fv=(num*10**nd)//den
        return Num(iv*10**nd+fv,nd)
    def eval(self,e):
        k=e[0]
        if k=='num': return self.const(e[1])
        if k in ('var','idx'): return self.lget(e)
        if k=='un':
            a=self.eval(e[2]); return Num(-a.v,a.s) if e[1]=='-' else (a if e[1]=='+' else Num(0 if a.truth() else 1))
        if k in ('pre','post'):
            lhs=e[2]
            if lhs[0]=='idx':
                i=self.idx(self.eval(lhs[2])); en=self.env.arrenv(lhs[1]); ar=en.arrays.setdefault(lhs[1],{})
                old=ar.get(i,Num()).copy(); new=add(old,Num(1),e[1]=='--'); ar[i]=new.copy()
            else:
                old=self.lget(lhs); new=add(old,Num(1),e[1]=='--'); self.lset(lhs,new)
            return new if k=='pre' else old
        if k=='as':
            op=e[1]
            # evaluate array index once
            lhs=e[2]
            if lhs[0]=='idx':
                ii=self.idx(self.eval(lhs[2])); lhs=('idxv',lhs[1],ii)
                en=self.env.arrenv(lhs[1]); old=en.arrays.get(lhs[1],{}).get(ii,Num()).copy()
            else: old=self.lget(lhs)
            b=self.eval(e[3])
            if op=='=': z=b
            else: z=self.calc(op[0],old,b)
            if lhs[0]=='idxv': self.env.arrenv(lhs[1]).arrays.setdefault(lhs[1],{})[lhs[2]]=z.copy()
            else: self.lset(lhs,z)
            return z
        if k=='bin':
            a=self.eval(e[2]); op=e[1]
            if op=='&&' and not a.truth(): return Num(0)
            if op=='||' and a.truth(): return Num(1)
            return self.calc(op,a,self.eval(e[3]))
        if k=='builtin':
            a=self.eval(e[2])
            if e[1]=='scale': return Num(a.s)
            if e[1]=='length':
                if a.v==0: return Num(max(1,a.s))
                integer=abs(a.v)//10**a.s
                return Num((len(str(integer)) if integer else 0)+a.s)
            if a.v<0: raise RunError()
            if a.v in (0,1) and a.s==0: return a.copy()
            s=max(self.scale,a.s); # floor sqrt(value*10^(2s))
            shift=2*s-a.s
            q=isqrt(a.v*(10**shift)) if shift>=0 else isqrt(a.v//10**(-shift))
            return Num(q,s)
        if k=='call': return self.call(e[1],e[2])
        raise RunError()
    def calc(self,op,a,b):
        if op=='+': return add(a,b)
        if op=='-': return add(a,b,True)
        if op=='*': return mul(a,b,self.scale)
        if op=='/': return divide(a,b,self.scale)
        if op=='%': return rem(a,b,self.scale)
        if op=='^': return power(a,b,self.scale)
        c=cmp(a,b)
        return Num(int({'==':c==0,'!=':c!=0,'<':c<0,'>':c>0,'<=':c<=0,'>=':c>=0,'&&':a.truth() and b.truth(),'||':a.truth() or b.truth()}[op]))
    def call(self,n,args):
        if n not in self.funcs: raise RunError()
        pars,autos,body,void=self.funcs[n]
        vals=[]
        for a in args:
            if a[0]=='array': vals.append(('array',self.env.arrenv(a[1]).arrays.setdefault(a[1],{})))
            else: vals.append(('num',self.eval(a)))
        oldenv=self.env; oldbase=self.callbase; callbase=self.ibase
        en=Env(oldenv)
        for (pn,arr,ref),val in zip(pars,vals):
            if arr:
                if val[0]!='array': raise RunError()
                en.arrays[pn]=val[1] if ref else {i:x.copy() for i,x in val[1].items()}
            else: en.vars[pn]=val[1].copy()
        for an,arr in autos:
            if arr: en.arrays[an]={}
            else: en.vars[an]=Num()
        self.env=en; self.callbase=callbase
        try:
            for s in body: self.exec(s)
            ret=Num()
        except ReturnSig as r: ret=r.v
        finally: self.env=oldenv; self.callbase=oldbase
        return ret
    def format(self,x):
        b=self.obase
        if x.v==0: return '0'
        neg=x.v<0; av=abs(x.v); den=10**x.s; ip=av//den; frac=av%den
        digs='0123456789ABCDEF'
        ids=[]
        if ip==0: ints=''
        else:
            while ip: ids.append(ip%b); ip//=b
            ids.reverse()
            if b<=16: ints=''.join(digs[d] for d in ids)
            else:
                w=len(str(b-1)); ints=''.join(' '+str(d).zfill(w) for d in ids)
        fs=[]
        if x.s:
            k=0; p=1
            while p<10**x.s: p*=b; k+=1
            for _ in range(k): frac*=b; d=frac//den; frac%=den; fs.append(d)
        if b<=16: fstr=''.join(digs[d] for d in fs)
        else:
            w=len(str(b-1)); fstr=' '.join(str(d).zfill(w) for d in fs)
        z=ints+('.'+fstr if fs else '')
        return ('-' if neg else '')+z
    def printnum(self,x,nl=True):
        self.last=x.copy(); self.rawout(self.format(x)+ ('\n' if nl else ''))
    def printstr(self,s):
        mp={'a':'\a','b':'\b','f':'\f','n':'\n','r':'\r','q':'"','t':'\t','\\':'\\'}
        out=[]; i=0
        while i<len(s):
            if s[i]=='\\' and i+1<len(s):
                out.append(mp.get(s[i+1],s[i+1])); i+=2
            else: out.append(s[i]); i+=1
        self.rawout(''.join(out))
    def exec(self,s):
        k=s[0]
        if k=='block':
            for z in s[1]: self.exec(z)
        elif k=='expr':
            v=self.eval(s[1]);
            # assignments do not print; void calls do not print
            if s[1][0]!='as' and not (s[1][0]=='call' and self.funcs.get(s[1][1],(None,None,None,False))[3]): self.printnum(v)
        elif k=='string': self.rawout(s[1])
        elif k=='print':
            for typ,z in s[1]:
                if typ=='str': self.printstr(z)
                else: self.printnum(self.eval(z),False)
        elif k=='if':
            if self.eval(s[1]).truth(): self.exec(s[2])
            elif s[3] is not None: self.exec(s[3])
        elif k=='while':
            while self.eval(s[1]).truth():
                try: self.exec(s[2])
                except BreakSig: break
        elif k=='for':
            if s[1] is not None: self.eval(s[1])
            while s[2] is None or self.eval(s[2]).truth():
                try: self.exec(s[4])
                except ContinueSig: pass
                except BreakSig: break
                if s[3] is not None: self.eval(s[3])
        elif k=='break': raise BreakSig()
        elif k=='continue': raise ContinueSig()
        elif k=='return': raise ReturnSig(Num() if s[1] is None else self.eval(s[1]))
        elif k=='halt': raise HaltSig()
        elif k=='quit': raise QuitSig()
        elif k=='define': self.funcs[s[1]]=(s[2],s[3],s[4],s[5])

def main(argv):
    chunks=[]
    try:
        for f in argv:
            with open(f) as h: chunks.append(h.read())
    except OSError as e: return 1
    chunks.append(sys.stdin.read())
    m=Machine()
    try:
        # Parse together so definitions and multiline constructs may span normal input.
        toks=lex(''.join(chunks))
        # quit acts while input is read. Keep only execution blocks completed
        # before the block containing it; that block has not reached its
        # terminating top-level newline yet.
        brace=paren=0; safe=0; cut=None
        for qi,t in enumerate(toks):
            if t.k=='ID' and t.v=='quit': cut=safe; break
            if t.k=='{': brace+=1
            elif t.k=='}': brace=max(0,brace-1)
            elif t.k=='(': paren+=1
            elif t.k==')': paren=max(0,paren-1)
            elif t.k=='NL' and brace==0 and paren==0: safe=qi+1
        if cut is not None: toks=toks[:cut]+[Token('EOF')]
        blocks=Parser(toks).program()
        for block in blocks:
            try:
                for st in block: m.exec(st)
            except RunError: pass
    except (HaltSig,QuitSig): pass
    except (SyntaxError, BreakSig, ContinueSig, ReturnSig): pass
    return 0
if __name__=='__main__': sys.exit(main(sys.argv[1:]))
