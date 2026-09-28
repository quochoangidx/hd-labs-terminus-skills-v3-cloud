#!/usr/bin/env python3
"""Small, byte-oriented GNU sed 4.9 compatible interpreter."""
import sys, os, ctypes

libc = ctypes.CDLL(None)
class RM(ctypes.Structure):
    _fields_ = [('so', ctypes.c_int), ('eo', ctypes.c_int)]
libc.regcomp.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int]
libc.regcomp.restype = ctypes.c_int
libc.regexec.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_size_t, ctypes.POINTER(RM), ctypes.c_int]
libc.regexec.restype = ctypes.c_int
libc.regfree.argtypes = [ctypes.c_void_p]
REG_EXTENDED, REG_ICASE, REG_NEWLINE = 1, 2, 4

def sed_escapes(s, context='regex'):
    """Expand GNU sed character escapes, preserving context syntax."""
    out=bytearray(); i=0
    simple={97:7,102:12,110:10,114:13,116:9,118:11}
    while i<len(s):
        if s[i]!=92 or i+1>=len(s):
            out.append(s[i]); i+=1; continue
        z=s[i+1]
        if z in simple:
            out.append(simple[z]); i+=2; continue
        if z==99 and i+2<len(s):
            q=s[i+2]
            if 97<=q<=122:q-=32
            out.append(q ^ 64); i+=3; continue
        if z in (100,111,120):
            base={100:10,111:8,120:16}[z]; lim=2 if z==120 else 3
            j=i+2
            while j<len(s) and j<i+2+lim:
                c=s[j]
                v=(c-48 if 48<=c<=57 else c-87 if 97<=c<=102 else c-55 if 65<=c<=70 else 99)
                if v>=base:break
                j+=1
            if j>i+2:
                out.append(int(s[i+2:j],base)&255);i=j;continue
        # Regex and replacement contexts retain grammar backslashes;
        # text/transliteration contexts use backslash to quote the byte.
        if context=='text':out.append(z)
        else:out.extend((92,z))
        i+=2
    return bytes(out)

def numesc(s):
    return sed_escapes(s, 'regex')

class RX:
    def __init__(self, pat, ext=False, icase=False, multi=False):
        self.pat=numesc(pat); self.buf=ctypes.create_string_buffer(4096)
        flags=(REG_EXTENDED if ext else 0)|(REG_ICASE if icase else 0)|(REG_NEWLINE if multi else 0)
        rc=libc.regcomp(self.buf, self.pat, flags)
        if rc: raise ValueError('bad regexp')
    def find(self, data, start=0, n=10):
        # REG_STARTEND makes embedded newlines and a nonzero starting point safe.
        a=(RM*n)(); a[0].so=start; a[0].eo=len(data)
        db=ctypes.create_string_buffer(data+b'\0')
        if libc.regexec(self.buf, db, n, a, 4): return None
        return [(x.so,x.eo) if x.so>=0 else None for x in a]
    def __del__(self):
        try: libc.regfree(self.buf)
        except: pass

def scan_delim(s,i,d):
    out=bytearray()
    while i<len(s):
        c=s[i]
        if c==d: return bytes(out),i+1
        if c==92 and i+1<len(s):
            # A backslash quoting the delimiter is removed; other regex
            # backslashes remain significant.
            if s[i+1]==d: out.append(d)
            else: out.extend(s[i:i+2])
            i+=2
        else: out.append(c); i+=1
    raise ValueError('unterminated')

def unescape_text(x):
    return sed_escapes(x, 'text')

class Addr:
    def __init__(self,k,v=None,mods=b''): self.k,self.v,self.mods=k,v,mods
class Cmd:
    def __init__(self,a1=None,a2=None,neg=False,op=None,arg=None):
        self.a1,self.a2,self.neg,self.op,self.arg=a1,a2,neg,op,arg; self.active=False; self.end=None

class Parser:
    def __init__(self,s,ext=False): self.s=s; self.i=0; self.ext=ext; self.cmd=[]; self.stack=[]
    def ws(self):
        while self.i<len(self.s) and self.s[self.i] in b' \t\r': self.i+=1
    def addr(self):
        self.ws(); i=self.i
        if i>=len(self.s): return None
        if self.s[i:i+1].isdigit():
            j=i
            while j<len(self.s) and self.s[j:j+1].isdigit():j+=1
            n=int(self.s[i:j]); self.i=j
            if j<len(self.s) and self.s[j]==126:
                j+=1;k=j
                while j<len(self.s) and self.s[j:j+1].isdigit():j+=1
                self.i=j; return Addr('step',(n,int(self.s[k:j])))
            return Addr('num',n)
        if self.s[i]==36:self.i+=1;return Addr('last')
        if self.s[i] in (47,92):
            if self.s[i]==92:
                if i+1>=len(self.s): return None
                d=self.s[i+1]; i+=2
            else:d=47;i+=1
            p,i=scan_delim(self.s,i,d); j=i
            while j<len(self.s) and self.s[j] in b'IM':j+=1
            self.i=j; return Addr('re',p,self.s[i:j])
        return None
    def parse(self):
        while self.i<len(self.s):
            self.ws()
            if self.i>=len(self.s):break
            if self.s[self.i] in b';\n': self.i+=1;continue
            if self.s[self.i]==35:
                while self.i<len(self.s) and self.s[self.i]!=10:self.i+=1
                continue
            a1=self.addr(); a2=None
            self.ws()
            if a1 and self.i<len(self.s) and self.s[self.i]==44:
                self.i+=1; self.ws()
                if self.s[self.i:self.i+1]==b'+':
                    self.i+=1;j=self.i
                    while self.i<len(self.s) and self.s[self.i:self.i+1].isdigit():self.i+=1
                    a2=Addr('plus',int(self.s[j:self.i]))
                elif self.s[self.i:self.i+1]==b'~':
                    self.i+=1;j=self.i
                    while self.i<len(self.s) and self.s[self.i:self.i+1].isdigit():self.i+=1
                    a2=Addr('tilde',int(self.s[j:self.i]))
                else:a2=self.addr()
            self.ws(); neg=False
            while self.i<len(self.s) and self.s[self.i]==33:neg=not neg;self.i+=1;self.ws()
            if self.i>=len(self.s):break
            op=chr(self.s[self.i]);self.i+=1; c=Cmd(a1,a2,neg,op)
            if op=='{':
                self.cmd.append(c);self.stack.append(len(self.cmd)-1);continue
            if op=='}':
                if self.stack:self.cmd[self.stack.pop()].end=len(self.cmd)
                self.cmd.append(c);continue
            if op in ':btT':
                self.ws();j=self.i
                while self.i<len(self.s) and self.s[self.i] not in b';\n':self.i+=1
                c.arg=self.s[j:self.i].strip()
            elif op in 'ai c'.replace(' ',''):
                # Optional backslash/newline form; consume through physical line.
                if self.i<len(self.s) and self.s[self.i] in b' \t':
                    while self.i<len(self.s) and self.s[self.i] in b' \t':self.i+=1
                    j=self.i
                    while self.i<len(self.s) and self.s[self.i]!=10:self.i+=1
                    c.arg=unescape_text(self.s[j:self.i])
                else:
                    if self.i<len(self.s) and self.s[self.i]==92:self.i+=1
                    if self.i<len(self.s) and self.s[self.i]==10:self.i+=1
                    parts=[]
                    while True:
                        j=self.i
                        while self.i<len(self.s) and self.s[self.i]!=10:self.i+=1
                        x=self.s[j:self.i]
                        if x.endswith(b'\\'):
                            parts.append(x[:-1]);self.i+=self.i<len(self.s);continue
                        parts.append(x);break
                    c.arg=b'\n'.join(parts)
            elif op=='s':
                d=self.s[self.i];self.i+=1;p,self.i=scan_delim(self.s,self.i,d);r,self.i=scan_delim(self.s,self.i,d)
                j=self.i
                while self.i<len(self.s) and self.s[self.i] not in b';\n \t':self.i+=1
                fl=self.s[j:self.i]; c.arg=(p,r,fl)
            elif op=='y':
                d=self.s[self.i];self.i+=1;x,self.i=scan_delim(self.s,self.i,d);y,self.i=scan_delim(self.s,self.i,d);c.arg=(sed_escapes(x,'text'),sed_escapes(y,'text'))
            elif op=='l':
                self.ws();j=self.i
                while self.i<len(self.s) and self.s[self.i:self.i+1].isdigit():self.i+=1
                c.arg=int(self.s[j:self.i] or b'70')
            elif op in 'qQ':
                self.ws();j=self.i
                while self.i<len(self.s) and self.s[self.i:self.i+1].isdigit():self.i+=1
                c.arg=int(self.s[j:self.i] or b'0')
            self.cmd.append(c)
        labels={c.arg:i for i,c in enumerate(self.cmd) if c.op==':'}
        for c in self.cmd:
            if c.op in 'btT':c.arg=labels.get(c.arg,len(self.cmd))
        return self.cmd

def repl_expand(rep,data,m):
    out=bytearray(); mode=None; one=None; i=0
    def emit(x):
        nonlocal one
        for q in x:
            ch=bytes([q]); conv=one or mode
            if conv=='L':ch=ch.lower()
            elif conv=='U':ch=ch.upper()
            out.extend(ch);one=None
    while i<len(rep):
        c=rep[i]
        if c==38:
            emit(data[m[0][0]:m[0][1]]);i+=1;continue
        if c==92 and i+1<len(rep):
            z=rep[i+1];i+=2
            if 48<=z<=57:
                n=z-48
                if n<len(m) and m[n]:emit(data[m[n][0]:m[n][1]])
            elif z in (76,85):mode=chr(z)
            elif z==69:mode=None
            elif z in (108,117):one='L' if z==108 else 'U'
            elif z==110:emit(b'\n')
            else:emit(bytes([z]))
            continue
        emit(bytes([c]));i+=1
    return bytes(out)

def escaped_l(data,width):
    mp={7:b'\\a',8:b'\\b',9:b'\\t',10:b'\\n',11:b'\\v',12:b'\\f',13:b'\\r',36:b'\\$',92:b'\\\\'}
    toks=[]
    for c in data:
        if c in mp:toks.append(mp[c])
        elif 32<=c<127:toks.append(bytes([c]))
        else:toks.append(('\\%03o'%c).encode())
    if not width:return b''.join(toks)+b'$\n'
    out=bytearray();col=0
    for t in toks:
        if col+len(t)>width-1:out.extend(b'\\\n');col=0
        out.extend(t);col+=len(t)
    out.extend(b'$\n');return bytes(out)

class Engine:
    def __init__(self,cmd,ext,quiet,separate,records):
        self.c=cmd;self.ext=ext;self.quiet=quiet;self.sep=separate;self.r=records;self.h=b'';self.last_rx=None;self.last_pat=None;self.out=sys.stdout.buffer;self.exit=0
    def rx(self,p,mods=b''):
        if p==b'':
            p=self.last_pat
            if p is None:return self.last_rx
        else:self.last_pat=p
        x=RX(p,self.ext,b'I' in mods,b'M' in mods);self.last_rx=x;return x
    def amatch(self,a,ps,num,idx,startnum):
        if not a:return True
        if a.k=='num':return num==a.v
        if a.k=='last':return idx==len(self.r)-1 or (self.sep and (idx+1==len(self.r) or self.r[idx+1][0]!=self.r[idx][0]))
        if a.k=='step':
            first,step=a.v;return num>=first and (num-first)%step==0
        if a.k=='re':return self.rx(a.v,a.mods).find(ps) is not None
        if a.k=='plus':return num<=startnum+a.v
        if a.k=='tilde':return num%a.v!=0
        return False
    def selected(self,c,ps,num,idx):
        if not c.a1:ok=True
        elif not c.a2:ok=self.amatch(c.a1,ps,num,idx,num)
        elif not c.active:
            # GNU's special zero address starts a 0,/re/ range before the
            # first input line, allowing its end regexp to match line one.
            ok=(c.a1.k=='num' and c.a1.v==0 and num==1) or self.amatch(c.a1,ps,num,idx,num)
            if ok:
                c.active=True;c._start=num
                if c.a2.k=='re' and not (c.a1.k=='num' and c.a1.v==0): c._defer=True
                else:c._defer=False
        else:ok=True
        if c.a2 and c.active:
            end=False
            if getattr(c,'_defer',False):c._defer=False
            elif c.a2.k=='plus':end=num>=c._start+c.a2.v
            elif c.a2.k=='tilde':end=num>c._start and num%c.a2.v==0
            elif c.a2.k=='num':end=num>=c.a2.v
            else:end=self.amatch(c.a2,ps,num,idx,c._start)
            if end:c.active=False
        return not ok if c.neg else ok
    def substitute(self,ps,arg):
        p,r,fl=arg; r=sed_escapes(r,'replacement'); mods=bytes(x for x in fl if x in b'IM');rx=self.rx(p,mods)
        g=b'g' in fl; want=0
        digs=bytes(x for x in fl if 48<=x<=57)
        if digs:want=int(digs)
        out=bytearray();pos=0;count=0;changed=False;last_nonempty_end=-1
        while pos<=len(ps):
            m=rx.find(ps,pos)
            if not m:break
            a,b=m[0]
            if a==b and a==last_nonempty_end:
                if pos<len(ps):out.extend(ps[pos:pos+1]);pos+=1;last_nonempty_end=-1;continue
                break
            count+=1;take=(want==0 and (g or count==1)) or count==want or (want and g and count>=want)
            if take:
                out.extend(ps[pos:a]);out.extend(repl_expand(r,ps,m));pos=b;changed=True
                if b>a:last_nonempty_end=b
            else:
                out.extend(ps[pos:b]);pos=b
            if b==a:
                if pos<len(ps):out.extend(ps[pos:pos+1]);pos+=1
                else:break
            if not g and (not want or count>=want):break
        out.extend(ps[pos:]);return bytes(out),changed,(b'p' in fl)
    def run(self):
        idx=0;globalnum=0;prevfid=None
        while idx<len(self.r):
            fid,ps=self.r[idx]
            if self.sep and fid!=prevfid:
                globalnum=0
                for z in self.c: z.active=False
            prevfid=fid;globalnum+=1;num=globalnum;pc=0;deleted=False;append=[];subst=False
            while pc<len(self.c):
                c=self.c[pc]
                if c.op=='}':pc+=1;continue
                sel=self.selected(c,ps,num,idx)
                if c.op=='{' and not sel:pc=(c.end or pc)+1;continue
                if c.op=='{' or not sel:pc+=1;continue
                o=c.op
                if o=='p':self.out.write(ps+b'\n')
                elif o=='P':self.out.write(ps.split(b'\n',1)[0]+b'\n')
                elif o=='=':self.out.write(str(num).encode()+b'\n')
                elif o=='l':self.out.write(escaped_l(ps,c.arg))
                elif o=='a':append.append(c.arg+b'\n')
                elif o=='i':self.out.write(c.arg+b'\n')
                elif o=='c':
                    # GNU emits once, at range end (or immediately for a single address).
                    if not c.a2 or not c.active:self.out.write(c.arg+b'\n')
                    deleted=True;break
                elif o=='d':deleted=True;break
                elif o=='D':
                    if b'\n' in ps:ps=ps.split(b'\n',1)[1];pc=0;continue
                    deleted=True;break
                elif o=='h':self.h=ps
                elif o=='H':self.h+=b'\n'+ps
                elif o=='g':ps=self.h
                elif o=='G':ps+=b'\n'+self.h
                elif o=='x':ps,self.h=self.h,ps
                elif o=='z':ps=b''
                elif o=='y':ps=ps.translate(bytes.maketrans(*c.arg))
                elif o=='s':
                    ps,ch,pp=self.substitute(ps,c.arg);subst|=ch
                    if ch and pp:self.out.write(ps+b'\n')
                elif o=='n':
                    if not self.quiet:self.out.write(ps+b'\n')
                    for x in append:self.out.write(x)
                    append=[]
                    if idx+1>=len(self.r) or (self.sep and self.r[idx+1][0]!=fid):deleted=True;break
                    idx+=1
                    fid,ps=self.r[idx];globalnum+=1;prevfid=fid;num=globalnum;subst=False
                elif o=='N':
                    if idx+1>=len(self.r) or (self.sep and self.r[idx+1][0]!=fid):
                        # GNU mode ends the script here, but unlike POSIX mode
                        # the current pattern space still receives auto-print.
                        if not self.quiet:self.out.write(ps+b'\n')
                        for x in append:self.out.write(x)
                        return self.exit
                    idx+=1;globalnum+=1;num=globalnum;ps+=b'\n'+self.r[idx][1]
                elif o in ('b','t','T'):
                    jump=o=='b' or (o=='t' and subst) or (o=='T' and not subst)
                    if o in 'tT':subst=False
                    if jump:pc=c.arg;continue
                elif o=='q':
                    if not self.quiet:self.out.write(ps+b'\n')
                    for x in append:self.out.write(x)
                    return c.arg
                elif o=='Q':return c.arg
                pc+=1
            if not deleted and not self.quiet:self.out.write(ps+b'\n')
            for x in append:self.out.write(x)
            idx+=1
        return self.exit

def main(argv):
    quiet=ext=sep=False;scripts=[];i=0
    while i<len(argv):
        a=argv[i]
        if a=='-n':quiet=True
        elif a=='-E':ext=True
        elif a=='-s':sep=True
        elif a=='-e':
            i+=1
            if i>=len(argv):return 1
            scripts.append(os.fsencode(argv[i]))
        else:break
        i+=1
    if not scripts:
        if i>=len(argv):return 1
        scripts=[os.fsencode(argv[i])];i+=1
    script=b'\n'.join(scripts)
    if script.startswith(b'#n'):quiet=True
    try:cmd=Parser(script,ext).parse()
    except Exception as e:
        sys.stderr.write('sed: '+str(e)+'\n');return 1
    files=argv[i:];records=[];status=0
    if not files:
        data=sys.stdin.buffer.read();records=[(0,x) for x in data.split(b'\n')[:-1]]
    else:
        for fi,name in enumerate(files):
            try:
                if name=='-':data=sys.stdin.buffer.read()
                else:
                    with open(name,'rb') as f:data=f.read()
                records += [(fi,x) for x in data.split(b'\n')[:-1]]
            except OSError as e:
                sys.stderr.write('sed: '+name+': '+e.strerror+'\n');status=2
    try:r=Engine(cmd,ext,quiet,sep,records).run()
    except BrokenPipeError:return 0
    return r or status
if __name__=='__main__':sys.exit(main(sys.argv[1:]))
