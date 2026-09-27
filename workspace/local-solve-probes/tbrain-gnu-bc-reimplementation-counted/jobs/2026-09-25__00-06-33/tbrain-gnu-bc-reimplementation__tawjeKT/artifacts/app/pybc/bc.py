#!/usr/bin/env python3
import sys
from dataclasses import dataclass

class BCError(Exception): pass
class Halt(Exception): pass
class Quit(Exception): pass
class BreakSig(Exception): pass
class ContinueSig(Exception): pass
class ReturnSig(Exception):
    def __init__(self, value=None): self.value=value

def truncdiv(a,b):
    if b==0: raise BCError()
    q=abs(a)//abs(b)
    return -q if (a<0) != (b<0) else q

@dataclass
class Num:
    c:int=0
    s:int=0
    def truth(self): return self.c != 0
    def integer(self): return truncdiv(self.c,10**self.s) if self.s else self.c
    def at(self,s):
        if s>=self.s: return Num(self.c*10**(s-self.s),s)
        return Num(truncdiv(self.c,10**(self.s-s)),s)
    def copy(self): return Num(self.c,self.s)

def add(a,b,sub=False):
    s=max(a.s,b.s); aa=a.at(s).c; bb=b.at(s).c
    return Num(aa-bb if sub else aa+bb,s)
def mul(a,b,scale):
    target=min(a.s+b.s,max(scale,a.s,b.s))
    return Num(a.c*b.c,a.s+b.s).at(target)
def div(a,b,scale):
    if b.c==0: raise BCError()
    # (a.c/10^a.s)/(b.c/10^b.s), coefficient at requested scale
    shift=scale+b.s-a.s
    if shift>=0: c=truncdiv(a.c*10**shift,b.c)
    else: c=truncdiv(a.c,b.c*10**(-shift))
    return Num(c,scale)
def mod(a,b,scale):
    if b.c==0: raise BCError()
    q=div(a,b,scale)
    target=max(scale+b.s,a.s)
    prod=Num(q.c*b.c,q.s+b.s).at(target)
    return add(a.at(target),prod,True)
def power(a,b,scale):
    e=b.integer()
    if e==0: return Num(1,0)
    if a.c==0 and e<0: raise BCError()
    if e<0:
        p=Num(pow(abs(a.c),-e),a.s*(-e))
        if a.c<0 and (-e)%2: p.c=-p.c
        return div(Num(1,0),p,scale)
    target=min(a.s*e,max(scale,a.s))
    c=pow(abs(a.c),e)
    if a.c<0 and e%2: c=-c
    return Num(c,a.s*e).at(target)

def sqrt_num(a,scale):
    if a.c<0: raise BCError()
    if a.c==0: return Num(0,0)
    if a.c==10**a.s: return Num(1,0)
    target=max(scale,a.s)
    # floor(sqrt(value)*10^target)
    import math
    exp=2*target-a.s
    n=a.c*(10**exp) if exp>=0 else a.c//(10**(-exp))
    return Num(math.isqrt(n),target)

@dataclass
class Tok:
    k:str; v:str; line:int

KEYWORDS={'if','else','while','for','break','continue','halt','quit','return','define','void','auto','print','length','scale','sqrt'}
def lex(src):
    out=[]; i=0; line=1; n=len(src)
    while i<n:
        c=src[i]
        if c in ' \t\r': i+=1; continue
        if c=='\\' and i+1<n and src[i+1]=='\n': i+=2; line+=1; continue
        if c=='\n': out.append(Tok('NL','\n',line)); line+=1; i+=1; continue
        if c=='#':
            while i<n and src[i]!='\n': i+=1
            continue
        if src.startswith('/*',i):
            i+=2
            while i<n and not src.startswith('*/',i):
                if src[i]=='\n': line+=1
                i+=1
            i=min(n,i+2); continue
        if c=='"':
            j=i+1
            while j<n and src[j]!='"':
                if src[j]=='\\' and j+1<n: j+=2
                else: j+=1
            out.append(Tok('STR',src[i+1:j],line)); i=min(n,j+1); continue
        if c.isdigit() or c.isupper() or (c=='.' and i+1<n and (src[i+1].isdigit() or src[i+1].isupper())):
            j=i
            while j<n and (src[j].isdigit() or src[j].isupper() or src[j]=='.'): j+=1
            out.append(Tok('NUM',src[i:j],line)); i=j; continue
        if c.isalpha() or c=='_':
            j=i+1
            while j<n and (src[j].isalnum() or src[j]=='_'): j+=1
            v=src[i:j]; out.append(Tok(v if v in KEYWORDS else 'ID',v,line)); i=j; continue
        matched=False
        for op in ('++','--','+=','-=','*=','/=','%=','^=','==','!=','<=','>=','&&','||'):
            if src.startswith(op,i): out.append(Tok(op,op,line)); i+=len(op); matched=True; break
        if matched: continue
        out.append(Tok(c,c,line)); i+=1
    out.append(Tok('EOF','',line)); return out

# Expressions are tuples. const, var, arr, call, unary, binary, assign, pre, post, builtin
class Parser:
    def __init__(self,toks): self.t=toks; self.i=0; self.saw_quit=False
    def cur(self): return self.t[self.i]
    def accept(self,k):
        if self.cur().k==k: x=self.cur(); self.i+=1; return x
        return None
    def need(self,k):
        x=self.accept(k)
        if not x: raise SyntaxError((k,self.cur()))
        return x
    def seps(self):
        while self.cur().k in ('NL',';'): self.i+=1
    def program(self):
        blocks=[]
        while self.cur().k!='EOF':
            self.seps()
            if self.cur().k=='EOF': break
            if self.cur().k=='define':
                fb=[self.function()]
                if self.saw_quit: fb.append(('force_quit',))
                blocks.append(fb)
                if self.saw_quit: break
                self.seps(); continue
            block=[]
            # Same top-level physical line is one execution block. Compound parser consumes internal NL.
            startline=self.cur().line
            while self.cur().k!='EOF':
                block.append(self.stmt())
                if self.accept(';'): continue
                if self.cur().k=='NL':
                    while self.accept('NL'): pass
                    break
                if self.cur().k=='EOF': break
            if self.saw_quit:
                block.append(('force_quit',)); blocks.append(block); break
            blocks.append(block)
        return blocks
    def function(self):
        self.need('define'); void=bool(self.accept('void')); name=self.need('ID').v; self.need('(')
        pars=[]
        if self.cur().k!=')':
            while True:
                ref=bool(self.accept('*')); pn=self.need('ID').v; arr=False
                if self.accept('['): self.need(']'); arr=True
                pars.append((pn,arr,ref))
                if not self.accept(','): break
        self.need(')'); self.seps(); self.need('{'); self.seps()
        autos=[]
        if self.accept('auto'):
            while True:
                an=self.need('ID').v; ar=False
                if self.accept('['): self.need(']'); ar=True
                autos.append((an,ar))
                if not self.accept(','): break
            self.accept(';'); self.seps()
        body=[]
        while self.cur().k not in ('}','EOF'):
            body.append(self.stmt()); self.seps()
        self.need('}')
        return ('define',name,void,pars,autos,body)
    def stmt(self):
        k=self.cur().k
        if k=='{':
            self.i+=1; body=[]; self.seps()
            while self.cur().k not in ('}','EOF'):
                body.append(self.stmt()); self.seps()
            self.need('}'); return ('block',body)
        if k=='if':
            self.i+=1; self.need('('); c=self.expr(); self.need(')'); self.seps(); a=self.stmt(); b=None
            # GNU allows newline before else while statement remains structurally open.
            save=self.i; self.seps()
            if self.accept('else'): self.seps(); b=self.stmt()
            else: self.i=save
            return ('if',c,a,b)
        if k=='while':
            self.i+=1; self.need('('); c=self.expr(); self.need(')'); self.seps(); return ('while',c,self.stmt())
        if k=='for':
            self.i+=1; self.need('(')
            a=None if self.cur().k==';' else self.expr(); self.need(';')
            b=None if self.cur().k==';' else self.expr(); self.need(';')
            c=None if self.cur().k==')' else self.expr(); self.need(')'); self.seps()
            return ('for',a,b,c,self.stmt())
        if k in ('break','continue','halt','quit'):
            self.i+=1
            if k=='quit': self.saw_quit=True
            return (k,)
        if k=='return':
            self.i+=1
            if self.cur().k in ('NL',';','}'): return ('return',None)
            if self.accept('('): e=self.expr(); self.need(')')
            else: e=self.expr()
            return ('return',e)
        if k=='print':
            self.i+=1; xs=[]
            while True:
                if self.cur().k=='STR': xs.append(('str',self.cur().v)); self.i+=1
                else: xs.append(('expr',self.expr()))
                if not self.accept(','): break
            return ('print',xs)
        if k=='STR': self.i+=1; return ('string',self.t[self.i-1].v)
        if k=='define': return self.function()
        e=self.expr(); return ('expr',e)
    def expr(self,minp=0):
        t=self.cur()
        if t.k in ('-','!','++','--'):
            self.i+=1; left=('pre',t.k,self.expr(90))
        elif t.k=='(':
            self.i+=1; left=('paren',self.expr()); self.need(')')
        elif t.k=='NUM': self.i+=1; left=('const',t.v)
        elif t.k in ('length','sqrt','scale') and self.t[self.i+1].k=='(':
            self.i+=1; name=t.k; self.need('('); x=self.expr(); self.need(')'); left=('builtin',name,x)
        elif t.k=='scale':
            self.i+=1; left=('var','scale')
        elif t.k=='ID':
            self.i+=1; name=t.v
            if self.accept('('):
                args=[]
                if self.cur().k!=')':
                    while True:
                        # Bare name[] is an array actual.
                        if self.cur().k=='ID' and self.t[self.i+1].k=='[' and self.t[self.i+2].k==']':
                            an=self.cur().v; self.i+=3; args.append(('arrayarg',an))
                        else: args.append(self.expr())
                        if not self.accept(','): break
                self.need(')'); left=('call',name,args)
            elif self.accept('['):
                idx=self.expr(); self.need(']'); left=('arr',name,idx)
            else: left=('var',name)
        elif t.k=='.': self.i+=1; left=('var','last')
        else: raise SyntaxError(('expression',t))
        if self.cur().k in ('++','--'):
            op=self.cur().k; self.i+=1; left=('post',op,left)
        prec={'=':10,'+=':10,'-=':10,'*=':10,'/=':10,'%=':10,'^=':10,
              '||':20,'&&':30,'==':40,'!=':40,'<':40,'>':40,'<=':40,'>=':40,
              '+':50,'-':50,'*':60,'/':60,'%':60,'^':70}
        while self.cur().k in prec and prec[self.cur().k]>=minp:
            op=self.cur().k; p=prec[op]; self.i+=1
            # assignment and exponentiation associate right-to-left
            right=self.expr(p if op in ('=','+=','-=','*=','/=','%=','^=','^') else p+1)
            left=('assign',op,left,right) if op.endswith('=') and op not in ('==','!=','<=','>=') else ('binary',op,left,right)
        return left

class Array:
    def __init__(self): self.d={}
    def clone(self):
        x=Array(); x.d={k:v.copy() for k,v in self.d.items()}; return x

class Ref:
    def __init__(self,get,set): self.get=get; self.set=set

class Runtime:
    def __init__(self):
        self.vars={}; self.arrays={}; self.funcs={}; self.scale=0; self.ibase=10; self.obase=10
        self.last=Num(); self.base_stack=[]; self.col=0
    def varget(self,n):
        if n=='scale': return Num(self.scale,0)
        if n=='ibase': return Num(self.ibase,0)
        if n=='obase': return Num(self.obase,0)
        if n in ('last','.'): return self.last.copy()
        return self.vars.get(n,Num()).copy()
    def varset(self,n,v):
        v=v.copy()
        if n=='scale': self.scale=max(0,v.integer()); return
        if n=='ibase': self.ibase=max(2,min(16,v.integer())); return
        if n=='obase': self.obase=max(2,min(999,v.integer())); return
        if n in ('last','.'): self.last=v; return
        self.vars[n]=v
    def arr(self,n):
        if n not in self.arrays: self.arrays[n]=Array()
        return self.arrays[n]
    def idx(self,v):
        if v.c<0 or (v.integer()==0 and v.c!=0): raise BCError()
        x=v.integer()
        if x<0 or x>=65536: raise BCError()
        return x
    def ref(self,e,base=None):
        if e[0]=='var':
            n=e[1]; return Ref(lambda:self.varget(n),lambda v:self.varset(n,v))
        if e[0]=='arr':
            a=self.arr(e[1]); i=self.idx(self.eval(e[2],base))
            return Ref(lambda:a.d.get(i,Num()).copy(),lambda v:a.d.__setitem__(i,v.copy()))
        raise BCError()
    def constant(self,text,base):
        b=base if base is not None else self.ibase
        neg=False
        if '.' in text: ip,fp=text.split('.',1)
        else: ip,fp=text,''
        def digit(ch): return int(ch) if ch.isdigit() else ord(ch)-55
        # single digit rule applies to integer portion
        if len(ip)==1: iv=digit(ip[0])
        else:
            iv=0
            for ch in ip or '0': iv=iv*b+min(digit(ch),b-1)
        s=len(fp)
        if not fp: return Num(iv,0)
        f=0
        for ch in fp: f=f*b+min(digit(ch),b-1)
        # truncate base fraction to exactly s decimal places
        fc=(f*10**s)//(b**s)
        return Num(iv*10**s+fc,s)
    def eval(self,e,base=None):
        k=e[0]
        if k=='const': return self.constant(e[1],base)
        if k=='paren': return self.eval(e[1],base)
        if k in ('var','arr'): return self.ref(e,base).get()
        if k=='arrayarg': raise BCError()
        if k=='pre':
            op=e[1]
            if op=='-':
                v=self.eval(e[2],base); return Num(-v.c,v.s)
            if op=='!': return Num(0 if self.eval(e[2],base).truth() else 1,0)
            r=self.ref(e[2],base); old=r.get(); v=add(old,Num(1),op=='--'); r.set(v); return v
        if k=='post':
            r=self.ref(e[2],base); old=r.get(); r.set(add(old,Num(1),e[1]=='--')); return old
        if k=='assign':
            r=self.ref(e[2],base); op=e[1]
            if op=='=': v=self.eval(e[3],base)
            else:
                a=r.get(); b=self.eval(e[3],base); o=op[0]
                v=self.arith(o,a,b)
            r.set(v); return v.copy()
        if k=='binary':
            op=e[1]; a=self.eval(e[2],base)
            if op=='&&' and not a.truth(): return Num(0,0)
            if op=='||' and a.truth(): return Num(1,0)
            b=self.eval(e[3],base)
            if op=='&&': return Num(1 if b.truth() else 0,0)
            if op=='||': return Num(1 if b.truth() else 0,0)
            if op in ('==','!=','<','>','<=','>='):
                s=max(a.s,b.s); x=a.at(s).c; y=b.at(s).c
                z={'==':x==y,'!=':x!=y,'<':x<y,'>':x>y,'<=':x<=y,'>=':x>=y}[op]
                return Num(int(z),0)
            return self.arith(op,a,b)
        if k=='builtin':
            v=self.eval(e[2],base)
            if e[1]=='scale': return Num(v.s,0)
            if e[1]=='length':
                ip=abs(v.c)//10**v.s if v.s else abs(v.c)
                if ip==0: n=v.s if v.s else 1
                else: n=len(str(ip))+v.s
                return Num(n,0)
            return sqrt_num(v,self.scale)
        if k=='call': return self.call(e[1],e[2],base)
        raise BCError()
    def arith(self,o,a,b):
        if o=='+': return add(a,b)
        if o=='-': return add(a,b,True)
        if o=='*': return mul(a,b,self.scale)
        if o=='/': return div(a,b,self.scale)
        if o=='%': return mod(a,b,self.scale)
        if o=='^': return power(a,b,self.scale)
        raise BCError()
    def call(self,name,args,base=None):
        if name not in self.funcs: raise BCError()
        f=self.funcs[name]; _,_,void,pars,autos,body=f
        if len(args)!=len(pars): raise BCError()
        callbase=self.ibase
        vals=[]
        for p,a in zip(pars,args):
            if p[1]:
                if a[0]!='arrayarg': raise BCError()
                ar=self.arr(a[1]); vals.append(ar if p[2] else ar.clone())
            else: vals.append(self.eval(a,base))
        saved=[]
        for (n,isarr,ref),v in zip(pars,vals):
            store=self.arrays if isarr else self.vars; saved.append((store,n,store.get(n,None)))
            store[n]=v.copy() if not isarr else v
        for n,isarr in autos:
            store=self.arrays if isarr else self.vars; saved.append((store,n,store.get(n,None)))
            store[n]=Array() if isarr else Num()
        val=Num()
        try:
            for st in body: self.exec_stmt(st,callbase)
        except ReturnSig as r:
            if r.value is not None: val=r.value
        finally:
            for store,n,old in reversed(saved):
                if old is None: store.pop(n,None)
                else: store[n]=old
        return None if void else val
    def emit(self,s):
        out=[]
        for ch in s:
            if self.col==68:
                out.append('\\\n'); self.col=0
            out.append(ch)
            if ch=='\n': self.col=0
            else: self.col+=1
        sys.stdout.write(''.join(out))
    def fmt(self,v):
        if v.c==0: return '0'
        neg=v.c<0; c=abs(v.c); b=self.obase
        if b==10:
            d=str(c).rjust(v.s+1,'0')
            if v.s: z=d[:-v.s]+'.'+d[-v.s:]; z=z[1:] if z.startswith('0.') else z
            else: z=d
            return ('-' if neg else '')+z
        den=10**v.s; ip=c//den; rem=c%den
        digs=[]
        zero_ip=(ip==0)
        if ip==0: digs=[0]
        while ip: digs.append(ip%b); ip//=b
        digs.reverse()
        def dg(x,first=False):
            if b<=16: return str(x) if x<10 else chr(55+x)
            w=len(str(b-1)); return ' '+str(x).zfill(w)
        z=''.join(dg(x,j==0) for j,x in enumerate(digs))
        if v.s:
            k=0; p=1
            while p<10**v.s: p*=b; k+=1
            fs=[]
            for _ in range(k): rem*=b; q=rem//den; rem%=den; fs.append(q)
            if zero_ip: z=''
            if b<=16: z+='.'+''.join(dg(x) for x in fs)
            else: z+='.'+' '.join(str(x).zfill(len(str(b-1))) for x in fs)
        return ('-' if neg else '')+z
    def string(self,s):
        mp={'n':'\n','t':'\t','r':'\r','b':'\b','f':'\f','a':'\a','\\':'\\','"':'"'}
        out=''; i=0
        while i<len(s):
            if s[i]=='\\' and i+1<len(s): out+=mp.get(s[i+1],s[i+1]); i+=2
            else: out+=s[i]; i+=1
        return out
    def exec_stmt(self,st,base=None):
        k=st[0]
        if k=='define': self.funcs[st[1]]=st; return
        if k=='block':
            for x in st[1]: self.exec_stmt(x,base)
        elif k=='expr':
            v=self.eval(st[1],base)
            if st[1][0]!='assign' and v is not None:
                self.emit(self.fmt(v)+'\n'); self.last=v.copy()
        elif k=='string': self.emit(self.string(st[1]))
        elif k=='print':
            for typ,x in st[1]:
                if typ=='str': self.emit(self.string(x))
                else:
                    v=self.eval(x,base)
                    if v is not None: self.emit(self.fmt(v)); self.last=v.copy()
        elif k=='if':
            if self.eval(st[1],base).truth(): self.exec_stmt(st[2],base)
            elif st[3] is not None: self.exec_stmt(st[3],base)
        elif k=='while':
            while self.eval(st[1],base).truth():
                try: self.exec_stmt(st[2],base)
                except BreakSig: break
        elif k=='for':
            if st[1] is not None: self.eval(st[1],base)
            while st[2] is None or self.eval(st[2],base).truth():
                try: self.exec_stmt(st[4],base)
                except ContinueSig: pass
                except BreakSig: break
                if st[3] is not None: self.eval(st[3],base)
        elif k=='break': raise BreakSig()
        elif k=='continue': raise ContinueSig()
        elif k=='return': raise ReturnSig(None if st[1] is None else self.eval(st[1],base))
        elif k=='halt': raise Halt()
        elif k=='quit': pass
        elif k=='force_quit': raise Quit()

def main(argv):
    chunks=[]
    try:
        for p in argv:
            with open(p,encoding='latin1') as f: chunks.append(f.read())
        chunks.append(sys.stdin.read())
        src=''.join(x if not x or x.endswith('\n') else x+'\n' for x in chunks)
        blocks=Parser(lex(src)).program()
    except Exception:
        return 1
    rt=Runtime()
    try:
        for block in blocks:
            try:
                for st in block: rt.exec_stmt(st)
            except BCError:
                continue
    except (Halt,Quit): pass
    except (BreakSig,ContinueSig,ReturnSig): pass
    return 0
if __name__=='__main__': sys.exit(main(sys.argv[1:]))
