#!/usr/bin/env python3
import sys, os, ctypes, locale
locale.setlocale(locale.LC_ALL, 'C')

# glibc POSIX regex gives the required leftmost-longest behavior.
libc=ctypes.CDLL(None)
class RM(ctypes.Structure): _fields_=[('so',ctypes.c_int),('eo',ctypes.c_int)]
libc.regcomp.argtypes=[ctypes.c_void_p,ctypes.c_char_p,ctypes.c_int]
libc.regexec.argtypes=[ctypes.c_void_p,ctypes.c_char_p,ctypes.c_size_t,ctypes.POINTER(RM),ctypes.c_int]
libc.regfree.argtypes=[ctypes.c_void_p]
REG_EXTENDED=1; REG_ICASE=2; REG_NEWLINE=4

class RX:
 def __init__(self,s,ext=False,icase=False,multi=False):
  raw=s;s=b'';i=0
  while i<len(raw):
   if raw[i]==92 and i+1<len(raw) and raw[i+1] in (ord('x'),ord('o')):
    x,i=escaped_char(raw,i+1);s+=x
   else:s+=bytes([raw[i]]);i+=1
  self.s=s;self.ext=ext;self.mem=ctypes.create_string_buffer(1024)
  flags=(REG_EXTENDED if ext else 0)|(REG_ICASE if icase else 0)|(REG_NEWLINE if multi else 0)
  r=libc.regcomp(self.mem,s,flags)
  if r: raise ValueError('bad regexp')
 def search(self,s,pos=0,n=100):
  # REG_NOTBOL when starting after zero; regexec offsets are relative to suffix.
  m=(RM*n)(); r=libc.regexec(self.mem,s[pos:],n,m,1 if pos else 0)
  if r: return None
  return [(x.so+pos,x.eo+pos) if x.so>=0 else (-1,-1) for x in m]
 def __del__(self):
  try: libc.regfree(self.mem)
  except: pass

class Addr:
 def __init__(self,k,v=None): self.k=k; self.v=v
 def hit(self,E):
  k,v=self.k,self.v
  if k=='num': return E.lineno==v
  if k=='last': return E.islast
  if k=='step': return E.lineno==v[0] if v[1]==0 else E.lineno>=v[0] and (E.lineno-v[0])%v[1]==0
  if k=='rx': return v.search(E.pat) is not None
  return False
class Cmd:
 def __init__(self,op,a1=None,a2=None,neg=False,arg=None):
  self.op,self.a1,self.a2,self.neg,self.arg=op,a1,a2,neg,arg; self.active=False
 def selected(self,E):
  if not self.a1: z=True
  elif not self.a2: z=self.a1.hit(E)
  elif self.a1.k=='zero' and not hasattr(self,'zero_started'):
   self.zero_started=True;z=True;self.active=True
   if self.a2.hit(E):self.active=False
  elif self.active:
   z=True
   if self.a2.k=='plus':
    if E.lineno>=self.end: self.active=False
   elif self.a2.k=='tilde':
    if E.lineno%self.a2.v==0: self.active=False
   elif self.a2.hit(E): self.active=False
  elif self.a1.hit(E):
   z=True; self.active=True
   if self.a2.k=='plus':
    self.end=E.lineno+self.a2.v
    if self.a2.v==0:self.active=False
   elif self.a2.k=='num' and self.a2.v<=E.lineno:self.active=False
   elif self.a2.k=='tilde':
    pass
   elif self.a2.k=='rx' and self.a1.k!='zero': pass # range regex starts checking next line
   elif self.a2.hit(E): self.active=False
  else: z=False
  return not z if self.neg else z

def escaped_char(s,i):
 c=s[i]
 mp={ord('n'):10,ord('t'):9,ord('r'):13,ord('f'):12,ord('v'):11,ord('a'):7,ord('b'):8}
 if c in mp:return bytes([mp[c]]),i+1
 if c in (ord('x'),ord('o')):
  base=16 if c==ord('x') else 8;j=i+1
  valid='0123456789abcdef' if base==16 else '01234567';limit=i+(3 if base==16 else 4)
  while j<len(s) and j<limit and chr(s[j]).lower() in valid:j+=1
  if j>i+1:return bytes([int(s[i+1:j],base)&255]),j
 if 48<=c<=55:
  j=i
  while j<len(s) and j<i+3 and 48<=s[j]<=55:j+=1
  return bytes([int(s[i:j],8)&255]),j
 return bytes([c]),i+1

def unescape(s):
 out=b'';i=0
 while i<len(s):
  if s[i]==92 and i+1<len(s): x,i=escaped_char(s,i+1);out+=x
  else:out+=bytes([s[i]]);i+=1
 return out

class Parser:
 def __init__(self,s,ext): self.s=s;self.i=0;self.ext=ext;self.labels={};self.fix=[];self.last_rx=None
 def ws(self):
  while self.i<len(self.s) and self.s[self.i] in b' \t\r':self.i+=1
 def delim(self,d):
  o=b''
  while self.i<len(self.s):
   c=self.s[self.i];self.i+=1
   if c==d:return o
   if c==92 and self.i<len(self.s):
    n=self.s[self.i];self.i+=1
    if n==d:o+=bytes([d])
    else:o+=b'\\'+bytes([n])
   else:o+=bytes([c])
  raise ValueError('unterminated')
 def addr(self):
  self.ws()
  if self.i>=len(self.s):return None
  c=self.s[self.i]
  if 48<=c<=57:
   j=self.i
   while self.i<len(self.s) and chr(self.s[self.i]).isdigit():self.i+=1
   n=int(self.s[j:self.i])
   if self.i<len(self.s) and self.s[self.i]==126:
    self.i+=1;j=self.i
    while self.i<len(self.s) and chr(self.s[self.i]).isdigit():self.i+=1
    return Addr('step',(n,int(self.s[j:self.i])))
   return Addr('zero' if n==0 else 'num',n)
  if c==36:self.i+=1;return Addr('last')
  if c in (47,92):
   if c==92:self.i+=1;d=self.s[self.i]
   else:d=47
   self.i+=1; x=self.delim(d)
   ic=mu=False
   while self.i<len(self.s) and self.s[self.i] in b'IM':
    if self.s[self.i]==ord('I'):ic=True
    else:mu=True
    self.i+=1
   if x:self.last_rx=RX(x,self.ext,ic,mu)
   elif self.last_rx is not None and (ic or mu):self.last_rx=RX(self.last_rx.s,self.ext,ic,mu)
   if self.last_rx is None: raise ValueError('no previous regexp')
   return Addr('rx',self.last_rx)
  return None
 def parse(self,stopbrace=False):
  out=[]
  while self.i<len(self.s):
   self.ws()
   while self.i<len(self.s) and self.s[self.i] in b';\n':self.i+=1;self.ws()
   if self.i>=len(self.s):break
   if self.s[self.i]==35:
    while self.i<len(self.s) and self.s[self.i]!=10:self.i+=1
    continue
   if self.s[self.i]==125:
    self.i+=1
    if stopbrace:return out
    continue
   a1=self.addr();a2=None
   if a1:
    self.ws()
    if self.i<len(self.s) and self.s[self.i]==44:
     self.i+=1;self.ws()
     if self.i<len(self.s) and self.s[self.i] in (43,126):
      k='plus' if self.s[self.i]==43 else 'tilde';self.i+=1;j=self.i
      while self.i<len(self.s) and chr(self.s[self.i]).isdigit():self.i+=1
      a2=Addr(k,int(self.s[j:self.i]))
     else:a2=self.addr()
   self.ws();neg=False
   while self.i<len(self.s) and self.s[self.i]==33:neg=not neg;self.i+=1;self.ws()
   if self.i>=len(self.s):break
   op=chr(self.s[self.i]);self.i+=1; arg=None
   if op=='{': arg=self.parse(True)
   elif op in 'aic':
    self.ws()
    if self.i<len(self.s) and self.s[self.i]==92 and self.i+1<len(self.s) and self.s[self.i+1]==10:
     self.i+=2;parts=[]
     while True:
      j=self.i
      while self.i<len(self.s) and self.s[self.i]!=10:self.i+=1
      line=self.s[j:self.i]
      cont=line.endswith(b'\\')
      if cont:line=line[:-1]
      parts.append(line)
      if self.i<len(self.s):self.i+=1
      if not cont:break
     arg=b'\n'.join(parts)
    else:
     j=self.i
     while self.i<len(self.s) and self.s[self.i]!=10:self.i+=1
     arg=unescape(self.s[j:self.i])
   elif op in ':btT':
    self.ws();j=self.i
    while self.i<len(self.s) and self.s[self.i] not in b';\n}':self.i+=1
    arg=self.s[j:self.i].strip()
   elif op=='s':
    d=self.s[self.i];self.i+=1; pat=self.delim(d); rep=self.delim(d)
    j=self.i
    while self.i<len(self.s) and self.s[self.i] not in b';\n}':self.i+=1
    fl=self.s[j:self.i].strip()
    ic=bool(set(fl)&set(b'Ii'));mu=bool(set(fl)&set(b'Mm'))
    if pat:self.last_rx=RX(pat,self.ext,ic,mu)
    elif self.last_rx is not None and (ic or mu):self.last_rx=RX(self.last_rx.s,self.ext,ic,mu)
    if self.last_rx is None:raise ValueError('no previous regexp')
    arg=(self.last_rx,rep,fl)
   elif op=='y':
    d=self.s[self.i];self.i+=1;x=unescape(self.delim(d));y=unescape(self.delim(d));arg=bytes.maketrans(x,y)
   elif op=='l':
    j=self.i
    while self.i<len(self.s) and chr(self.s[self.i]).isdigit():self.i+=1
    arg=int(self.s[j:self.i]) if self.i>j else 70
   elif op=='q' or op=='Q':
    self.ws();j=self.i
    while self.i<len(self.s) and chr(self.s[self.i]).isdigit():self.i+=1
    arg=int(self.s[j:self.i]) if self.i>j else 0
   C=Cmd(op,a1,a2,neg,arg);out.append(C)
  return out

def replacement(rep,src,m):
 out=b'';i=0;mode=None;once=None
 def cv(x):
  nonlocal once
  if not x:return x
  if once:
   x=(x[:1].upper() if once=='u' else x[:1].lower())+x[1:];once=None
  if mode=='U':x=x.upper()
  elif mode=='L':x=x.lower()
  return x
 while i<len(rep):
  c=rep[i]
  if c==38:x=src[m[0][0]:m[0][1]];i+=1
  elif c==92 and i+1<len(rep):
   n=rep[i+1];i+=2
   if 48<=n<=57:
    a,b=m[n-48];x=src[a:b] if a>=0 else b''
   elif n in b'LUEul':
    if n==ord('E'):mode=None
    elif n in b'LU':mode=chr(n)
    else:once=chr(n)
    x=b''
   elif n==ord('n'):x=b'\n'
   elif n in (ord('x'),ord('o')):x,i=escaped_char(rep,i-1)
   else:x=bytes([n])
  else:x=bytes([c]);i+=1
  out+=cv(x)
 return out

def subst(p,arg):
 rx,rep,fl=arg; globalflag=b'g' in fl; printflag=b'p' in fl
 import re
 nums=[int(x) for x in re.findall(rb'\d+',fl)]
 nth=nums[0] if nums else None
 out=b'';pos=0;count=0;changed=False;last_nonempty_end=-1
 while pos<=len(p):
  m=rx.search(p,pos)
  if not m:break
  a,b=m[0]
  # GNU sed ignores an empty match immediately following an accepted nonempty one.
  if a==b and a==last_nonempty_end:
   if a<len(p):out+=p[pos:a+1];pos=a+1;continue
   break
  count+=1; take=(nth is None or count>=nth) and (globalflag or not changed)
  if take:
   out+=p[pos:a]+replacement(rep,p,m);changed=True
   if b>a:last_nonempty_end=b
  else:out+=p[pos:b]
  if b==a:
   if b<len(p):out+=p[b:b+1];pos=b+1
   else:pos=b;break
  else:pos=b
  if changed and not globalflag:break
 out+=p[pos:]
 return out,changed,printflag

def listed(p,N):
 units=[]
 mp={7:b'\\a',8:b'\\b',9:b'\\t',10:b'\\n',11:b'\\v',12:b'\\f',13:b'\\r',92:b'\\\\'}
 for c in p:units.append(mp.get(c,bytes([c]) if 32<=c<127 else ('\\%03o'%c).encode()))
 width=max(0,N-1);lines=[];cur=b''
 for u in units:
  if len(cur)+len(u)>width:
   lines.append(cur+b'\\');cur=b''
  cur+=u
 lines.append(cur+b'$')
 return b'\n'.join(lines)+b'\n'

class Engine:
 def __init__(self,cmds,quiet,separate,records):
  self.cmds=cmds;self.quiet=quiet;self.sep=separate;self.recs=records;self.pat=b'';self.hold=b'';self.lineno=0;self.islast=False;self.append=[];self.status=0;self.subbed=False
  self.labels={};self.parents={};self.index_labels(cmds)
 def index_labels(self,cs):
  for i,c in enumerate(cs):
   if c.op==':':self.labels[c.arg]=(cs,i)
   if c.op=='{':
    self.parents[id(c.arg)]=(cs,i)
    self.index_labels(c.arg)
 def wr(self,x):sys.stdout.buffer.write(x)
 def nextrec(self):
  if not self.recs:return None
  data,newfile,last=self.recs.pop(0)
  if self.sep and newfile:
   self.lineno=0;self.hold=b''
   def reset(cs):
    for c in cs:c.active=False; reset(c.arg) if c.op=='{' else None
   reset(self.cmds)
  self.lineno+=1;self.islast=last;return data
 def runlist(self,cs,start=0):
  i=start
  while i<len(cs):
   c=cs[i];i+=1
   if not c.selected(self):continue
   o=c.op
   if o=='{':
    z=self.runlist(c.arg)
    if z:return z
   elif o=='p':self.wr(self.pat+b'\n')
   elif o=='P':self.wr(self.pat.split(b'\n',1)[0]+b'\n')
   elif o=='=':self.wr(str(self.lineno).encode()+b'\n')
   elif o=='l':self.wr(listed(self.pat,c.arg))
   elif o=='d':return 'delete'
   elif o=='D':
    if b'\n' in self.pat:self.pat=self.pat.split(b'\n',1)[1];return 'restart'
    return 'delete'
   elif o=='n':
    if not self.quiet:self.wr(self.pat+b'\n')
    for x in self.append:self.wr(x+b'\n')
    self.append=[];z=self.nextrec()
    if z is None:return 'quit'
    self.pat=z;self.subbed=False
   elif o=='N':
    if self.sep and self.recs and self.recs[0][1]:return 'end'
    z=self.nextrec()
    if z is None:return 'end'
    self.pat+=b'\n'+z
   elif o=='h':self.hold=self.pat
   elif o=='H':self.hold+=b'\n'+self.pat
   elif o=='g':self.pat=self.hold
   elif o=='G':self.pat+=b'\n'+self.hold
   elif o=='x':self.pat,self.hold=self.hold,self.pat
   elif o=='z':self.pat=b''
   elif o=='y':self.pat=self.pat.translate(c.arg)
   elif o=='s':
    self.pat,ch,pp=subst(self.pat,c.arg);self.subbed|=ch
    if ch and pp:self.wr(self.pat+b'\n')
   elif o=='a':self.append.append(c.arg)
   elif o=='i':self.wr(c.arg+b'\n')
   elif o=='c':
    if not c.a2 or not c.active or self.islast:self.wr(c.arg+b'\n')
    return 'delete'
   elif o in ('q','Q'):
    if o=='q' and not self.quiet:self.wr(self.pat+b'\n')
    for x in self.append:self.wr(x+b'\n')
    self.status=c.arg;return 'quit'
   elif o in ('b','t','T'):
    take=o=='b' or (o=='t' and self.subbed) or (o=='T' and not self.subbed)
    if o in ('t','T'):self.subbed=False
    if take:
     if not c.arg:return 'end'
     target=self.labels.get(c.arg)
     if target and target[0] is cs:i=target[1]+1
     elif target:return ('jump',target)
   # ':' and comments are no-ops
  return None
 def resume(self,cs,start):
  r=self.runlist(cs,start)
  while r is None and id(cs) in self.parents:
   cs,i=self.parents[id(cs)]
   r=self.runlist(cs,i+1)
  return r
 def run(self):
  while True:
   z=self.nextrec()
   if z is None:break
   self.pat=z;self.append=[];self.subbed=False
   while True:
    r=self.runlist(self.cmds)
    if r=='restart':continue
    while isinstance(r,tuple) and r[0]=='jump':
     cs,j=r[1];r=self.resume(cs,j+1)
     if r=='restart':break
    if r=='restart':continue
    break
   if r=='quit':break
   if r != 'delete' and not self.quiet:self.wr(self.pat+b'\n')
   for x in self.append:self.wr(x+b'\n')
   if r=='endN':break
  return self.status

def main():
 argv=sys.argv[1:];quiet=False;ext=False;sep=False;pieces=[];i=0
 while i<len(argv) and argv[i] in ('-n','-E','-s','-e'):
  if argv[i]=='-n':quiet=True;i+=1
  elif argv[i]=='-E':ext=True;i+=1
  elif argv[i]=='-s':sep=True;i+=1
  else:
   if i+1>=len(argv):return 1
   pieces.append(os.fsencode(argv[i+1]));i+=2
 if not pieces:
  if i>=len(argv):return 1
  pieces=[os.fsencode(argv[i])];i+=1
 script=b'\n'.join(pieces)
 if script.startswith(b'#n'):quiet=True
 try:cmds=Parser(script,ext).parse()
 except Exception as e:
  print('sed.py:',e,file=sys.stderr);return 1
 files=argv[i:];records=[];status=0
 if not files:
  raw=sys.stdin.buffer.read();lines=raw.splitlines(True)
  for j,x in enumerate(lines):records.append((x[:-1] if x.endswith(b'\n') else x,j==0,j==len(lines)-1))
 else:
  allfiles=[]
  for fn in files:
   try:
    with open(fn,'rb') as f:raw=f.read()
   except OSError as e:print('sed.py:',e,file=sys.stderr);status=2;continue
   ls=raw.splitlines(True);allfiles.append(ls)
  flat=[]
  for ls in allfiles:
   for j,x in enumerate(ls):flat.append([x[:-1] if x.endswith(b'\n') else x,j==0,False])
  for j,x in enumerate(flat):x[2]=(j==len(flat)-1) or (sep and (j+1==len(flat) or flat[j+1][1]));records.append(tuple(x))
 E=Engine(cmds,quiet,sep,records);r=E.run();return r or status
if __name__=='__main__':raise SystemExit(main())
