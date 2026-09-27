#!/usr/bin/env python3
import sys, os, ctypes, locale, re
locale.setlocale(locale.LC_ALL, 'C')

# glibc POSIX regular expressions give sed's required leftmost-longest rule.
libc=ctypes.CDLL(None)
class RM(ctypes.Structure): _fields_=[('so',ctypes.c_int),('eo',ctypes.c_int)]
class RX:
 def __init__(self,pat,ere=False,icase=False,newline=False):
  self.newline=newline
  self.mem=ctypes.create_string_buffer(4096); self.pat=pat
  flags=(1 if ere else 0)|(2 if icase else 0)|(4 if getattr(self,'newline',False) else 0)
  rc=libc.regcomp(ctypes.byref(self.mem),pat,flags)
  if rc: raise ValueError('bad regexp')
 def search(self,s,start=0,n=10):
  a=(RM*n)(); a[0].so=start; a[0].eo=len(s)
  # REG_STARTEND, essential both for offsets and embedded newlines.
  rc=libc.regexec(ctypes.byref(self.mem),s,n,a,4)
  if rc: return None
  return [(a[i].so,a[i].eo) if a[i].so>=0 else (-1,-1) for i in range(n)]

class Cmd:
 def __init__(self,a1=None,a2=None,neg=False,op='',arg=None):
  self.a1,self.a2,self.neg,self.op,self.arg=a1,a2,neg,op,arg
  self.active=False; self.started=False; self.zero_done=False; self.jump=None

class Parser:
 def __init__(self,s,ere): self.s=s; self.i=0; self.ere=ere; self.cmd=[]; self.lastpat=None
 def ws(self):
  while self.i<len(self.s) and self.s[self.i] in b' \t': self.i+=1
 def delim(self,d):
  out=bytearray()
  while self.i<len(self.s):
   c=self.s[self.i]; self.i+=1
   if c==d: return bytes(out)
   if c==92 and self.i<len(self.s):
    q=self.s[self.i]; self.i+=1
    if q==d: out.append(q)
    else: out.extend((92,q))
   else: out.append(c)
  raise ValueError('unterminated')
 def addr(self):
  self.ws()
  if self.i>=len(self.s): return None
  c=self.s[self.i]
  if 48<=c<=57:
   j=self.i
   while self.i<len(self.s) and 48<=self.s[self.i]<=57:self.i+=1
   n=int(self.s[j:self.i]);
   if self.i<len(self.s) and self.s[self.i]==126:
    self.i+=1;j=self.i
    while self.i<len(self.s) and 48<=self.s[self.i]<=57:self.i+=1
    return ('step',n,int(self.s[j:self.i]))
   return ('num',n)
  if c in (43,126):
   kind='plus' if c==43 else 'tilde';self.i+=1;j=self.i
   while self.i<len(self.s) and 48<=self.s[self.i]<=57:self.i+=1
   if j==self.i: return None
   return (kind,int(self.s[j:self.i]))
  if c==36: self.i+=1; return ('last',)
  if c in (47,92):
   if c==92:
    self.i+=1
    if self.i>=len(self.s): return None
    d=self.s[self.i];self.i+=1
   else: d=c;self.i+=1
   p=self.delim(d); mods=0
   while self.i<len(self.s) and self.s[self.i] in b'IM':
    if self.s[self.i]==73:mods|=1
    else:mods|=2
    self.i+=1
   return ('re',p,mods)
  return None
 def text(self):
  # GNU accepts both aTEXT and a\ newline TEXT forms.
  if self.i<len(self.s) and self.s[self.i]==92:self.i+=1
  if self.i<len(self.s) and self.s[self.i]==10:self.i+=1
  out=bytearray()
  while self.i<len(self.s):
   j=self.s.find(b'\n',self.i)
   if j<0:j=len(self.s)
   part=self.s[self.i:j]; self.i=j+(j<len(self.s))
   if part.endswith(b'\\'):
    out.extend(part[:-1]);out.append(10);continue
   out.extend(part);break
  # GNU text-command escapes commonly used in generated scripts.
  r=bytearray();i=0
  while i<len(out):
   if out[i]==92 and i+1<len(out):
    q=out[i+1]
    if q==110:r.append(10)
    elif q==116:r.append(9)
    else:r.append(q)
    i+=2
   else:r.append(out[i]);i+=1
  return bytes(r)
 def parse(self):
  braces=[]
  while self.i<len(self.s):
   self.ws()
   if self.i>=len(self.s):break
   if self.s[self.i] in b';\n':self.i+=1;continue
   if self.s[self.i]==35:
    j=self.s.find(b'\n',self.i);self.i=len(self.s) if j<0 else j+1;continue
   a1=self.addr();a2=None
   self.ws()
   if a1 and self.i<len(self.s) and self.s[self.i]==44:
    self.i+=1;a2=self.addr()
    if a2 and a2[0]=='num' and a2[1]>=0: pass
    self.ws()
   neg=False
   if self.i<len(self.s) and self.s[self.i]==33:neg=True;self.i+=1;self.ws()
   if self.i>=len(self.s):break
   op=chr(self.s[self.i]);self.i+=1;arg=None
   if op in 'aic': arg=self.text()
   elif op=='s':
    d=self.s[self.i];self.i+=1;p=self.delim(d);r=self.delim(d)
    j=self.i
    while self.i<len(self.s) and self.s[self.i] not in b';\n':self.i+=1
    fl=self.s[j:self.i].strip(); arg=[p,r,fl,None]
   elif op=='y':
    d=self.s[self.i];self.i+=1;x=self.delim(d);y=self.delim(d);arg=(unesc(x),unesc(y))
   elif op in 'btT:':
    self.ws();j=self.i
    while self.i<len(self.s) and self.s[self.i] not in b';\n':self.i+=1
    arg=self.s[j:self.i].strip()
   elif op=='l':
    j=self.i
    while self.i<len(self.s) and 48<=self.s[self.i]<=57:self.i+=1
    arg=int(self.s[j:self.i] or b'70')
   elif op in 'qQ':
    self.ws();j=self.i
    while self.i<len(self.s) and 48<=self.s[self.i]<=57:self.i+=1
    arg=int(self.s[j:self.i] or b'0')
   c=Cmd(a1,a2,neg,op,arg);self.cmd.append(c)
   if op=='{':braces.append(len(self.cmd)-1)
   elif op=='}' and braces:
    k=braces.pop();self.cmd[k].jump=len(self.cmd)
   if op not in 'aic' and self.i<len(self.s) and self.s[self.i] in b';\n':self.i+=1
  labels={c.arg:i for i,c in enumerate(self.cmd) if c.op==':'}
  for c in self.cmd:
   if c.op in 'btT': c.jump=labels.get(c.arg,len(self.cmd))
  return self.cmd

def unesc(x):
 r=bytearray();i=0
 while i<len(x):
  if x[i]==92 and i+1<len(x):
   q=x[i+1]; mp={110:10,116:9,114:13,102:12,118:11,97:7}
   if q in mp:r.append(mp[q]);i+=2;continue
   if q in b'01234567':
    j=i+1
    while j<len(x) and j<i+4 and x[j] in b'01234567':j+=1
    r.append(int(x[i+1:j],8)&255);i=j;continue
   if q==120:
    j=i+2
    while j<len(x) and j<i+4 and chr(x[j]).lower() in '0123456789abcdef':j+=1
    if j>i+2:r.append(int(x[i+2:j],16)&255);i=j;continue
   r.append(q);i+=2
  else:r.append(x[i]);i+=1
 return bytes(r)

class Sed:
 def __init__(self,cmd,quiet,ere,sep):
  self.c=cmd;self.quiet=quiet;self.ere=ere;self.sep=sep;self.lastre=None
  self.h=b'';self.subbed=False;self.out=sys.stdout.buffer;self.status=0
 def regex(self,p,mods=0):
  if p==b'':
   if self.lastre is None: raise ValueError('no previous regexp')
   return self.lastre
  r=RX(p,self.ere,bool(mods&1),bool(mods&2));self.lastre=r;return r
 def amatch(self,a,line,no,last,c,second=False):
  if not a:return True
  k=a[0]
  if k=='num':return no>=a[1] if second else no==a[1]
  if k=='last':return last
  if k=='step':return no>=a[1] and (no-a[1])%a[2]==0
  if k=='re':return self.regex(a[1],a[2]).search(line) is not None
  if k=='plus':return no>=c.end
  if k=='tilde':return no>=c.end
  return False
 def selected(self,c,line,no,last):
  if not c.a2:v=self.amatch(c.a1,line,no,last,c)
  elif not c.active:
   zero=(c.a1[0]=='num' and c.a1[1]==0 and c.a2[0]=='re' and not c.zero_done)
   v=zero or self.amatch(c.a1,line,no,last,c)
   if v:
    c.active=True;c.started=True
    if zero:
     c.zero_done=True
     if self.amatch(c.a2,line,no,last,c,True):c.active=False
    if c.a2[0]=='plus':
     c.end=no+c.a2[1]
     if c.end<=no:c.active=False
    elif c.a2[0]=='tilde':c.end=no+(c.a2[1]-no%c.a2[1])
    # Numeric addr2 is tested immediately; regex addr2 starts next line.
    if c.a2[0]=='num' and self.amatch(c.a2,line,no,last,c,True):c.active=False
   
  else:
   v=True
   if self.amatch(c.a2,line,no,last,c,True):c.active=False
  return (not v) if c.neg else v
 def subst(self,line,arg):
  p,repl,fl,cache=arg;icase=b'i' in fl or b'I' in fl
  rx=self.regex(p,(1 if icase else 0)|(2 if (b'm' in fl or b'M' in fl) else 0));arg[3]=rx
  global_=b'g' in fl
  nums=[int(x) for x in re.findall(rb'[0-9]+',fl)]
  nth=nums[0] if nums else 0
  pos=0;prev=-1;count=0;out=bytearray();changed=False
  while pos<=len(line):
   m=rx.search(line,pos)
   if not m:break
   a,b=m[0]
   if a<pos:break
   if global_ and a==b and prev==a:
    if a>=len(line):break
    pos=a+1
    continue
   count+=1;take=(nth==0 or count>=nth) and (global_ or count==nth or (nth==0 and count==1))
   if take:
    out.extend(line[prev if prev>=0 else 0:a] if not changed else line[prev:a])
    out.extend(self.replacement(repl,line,m));prev=b;changed=True
    if not global_:break
   if b==a:
    if b>=len(line):pos=len(line)+1;break
    pos=b+1
   else:pos=b
  if changed:out.extend(line[prev:]);return bytes(out),True
  return line,False
 def replacement(self,r,s,m):
  out=bytearray();i=0;mode=None;once=None
  def put(data):
   nonlocal once
   for x in data:
    if once=='l':x=ord(chr(x).lower());once=None
    elif once=='u':x=ord(chr(x).upper());once=None
    if mode=='L':x=ord(chr(x).lower())
    elif mode=='U':x=ord(chr(x).upper())
    out.append(x)
  while i<len(r):
   if r[i]==38:put(s[m[0][0]:m[0][1]]);i+=1
   elif r[i]==92 and i+1<len(r):
    q=r[i+1];i+=2
    if 48<=q<=57:
     z=m[q-48] if q-48<len(m) else (-1,-1)
     if z[0]>=0:put(s[z[0]:z[1]])
    elif q in (76,85,69):mode={76:'L',85:'U',69:None}[q]
    elif q in (108,117):once={108:'l',117:'u'}[q]
    elif q==110:put(b'\n')
    else:put(bytes([q]))
   else:put(bytes([r[i]]));i+=1
  return bytes(out)
 def listline(self,s,n):
  z=bytearray()
  esc={7:b'\\a',8:b'\\b',9:b'\\t',10:b'\\n',11:b'\\v',12:b'\\f',13:b'\\r',92:b'\\\\'}
  for x in s:
   if x in esc:z.extend(esc[x])
   elif 32<=x<127:z.append(x)
   else:z.extend(('\\%03o'%x).encode())
  if n<=0:n=70
  while len(z)>=n:
   self.out.write(z[:n-1]+b'\\\n');z=z[n-1:]
  self.out.write(z+b'$\n')
 def run_records(self,recs):
  idx=0;hold_global=self.h
  while idx<len(recs):
   line,no,last=recs[idx];idx+=1; app=[];pc=0;deleted=False
   self.subbed=False
   while pc<len(self.c):
    c=self.c[pc];sel=self.selected(c,line,no,last)
    if c.op=='{' and not sel:pc=c.jump;continue
    if not sel:pc+=1;continue
    o=c.op
    if o in '{}:':pass
    elif o=='p':self.out.write(line+b'\n')
    elif o=='P':self.out.write(line.split(b'\n',1)[0]+b'\n')
    elif o=='=':self.out.write(str(no).encode()+b'\n')
    elif o=='l':self.listline(line,c.arg)
    elif o=='a':app.append(c.arg+b'\n')
    elif o=='i':self.out.write(c.arg+b'\n')
    elif o=='c':
     # In a range, print replacement only when entering the range.
     if not c.a2 or c.started:self.out.write(c.arg+b'\n')
     c.started=False;deleted=True;break
    elif o=='d':deleted=True;break
    elif o=='D':
     if b'\n' in line:line=line.split(b'\n',1)[1];pc=0;continue
     deleted=True;break
    elif o=='h':self.h=line
    elif o=='H':self.h+=b'\n'+line
    elif o=='g':line=self.h
    elif o=='G':line+=b'\n'+self.h
    elif o=='x':line,self.h=self.h,line
    elif o=='z':line=b''
    elif o=='y':line=line.translate(bytes.maketrans(*c.arg))
    elif o=='s':
     line,ch=self.subst(line,c.arg)
     if ch:
      self.subbed=True
      fl=c.arg[2]
      if b'p' in fl:self.out.write(line+b'\n')
      elif b'P' in fl:self.out.write(line.split(b'\n',1)[0]+b'\n')
    elif o=='b':pc=c.jump;continue
    elif o in 'tT':
     take=self.subbed if o=='t' else not self.subbed;self.subbed=False
     if take:pc=c.jump;continue
    elif o=='n':
     if not self.quiet:self.out.write(line+b'\n')
     for x in app:self.out.write(x)
     app=[]
     if idx>=len(recs):return None
     line,no,last=recs[idx];idx+=1;self.subbed=False;pc+=1;continue
    elif o=='N':
     if idx>=len(recs):
      if not self.quiet:self.out.write(line+b'\n')
      for x in app:self.out.write(x)
      return 'eof'
     q,nn,ll=recs[idx];idx+=1;line+=b'\n'+q;no=nn;last=ll;self.subbed=False
    elif o in 'qQ':
     if o=='q' and not self.quiet:self.out.write(line+b'\n')
     if o=='q':
      for x in app:self.out.write(x)
     return c.arg
    pc+=1
   if not deleted and not self.quiet:self.out.write(line+b'\n')
   for x in app:self.out.write(x)
  return None

def lines(data):
 # Inputs in the task end in LF. Split only on LF; bytes.splitlines() would
 # incorrectly treat CR, VT, FF, and other bytes as record separators.
 if data.endswith(b'\n'): data=data[:-1]
 return data.split(b'\n') if data else []

def main():
 a=sys.argv[1:];quiet=ere=sep=False;scripts=[];i=0
 while i<len(a) and a[i] in ('-n','-E','-s','-e'):
  if a[i]=='-n':quiet=True;i+=1
  elif a[i]=='-E':ere=True;i+=1
  elif a[i]=='-s':sep=True;i+=1
  else:
   if i+1>=len(a):return 1
   scripts.append(os.fsencode(a[i+1]));i+=2
 if not scripts:
  if i>=len(a):return 1
  scripts=[os.fsencode(a[i])];i+=1
 script=b'\n'.join(scripts)
 if script.startswith(b'#n'):quiet=True
 try:cmd=Parser(script,ere).parse()
 except Exception:return 1
 files=a[i:];groups=[];status=0
 if not files:
  groups=[lines(sys.stdin.buffer.read())]
 else:
  allrows=[]
  for f in files:
   try:
    rows=lines(sys.stdin.buffer.read()) if f=='-' else lines(open(f,'rb').read())
   except OSError:status=2;continue
   if sep:groups.append(rows)
   else:allrows.extend(rows)
  if not sep:groups=[allrows]
 s=Sed(cmd,quiet,ere,sep);base=0
 for rows in groups:
  for c in cmd:c.active=False;c.started=False;c.zero_done=False
  rec=[]
  for j,x in enumerate(rows):rec.append((x,j+1 if sep else base+j+1,j==len(rows)-1))
  q=s.run_records(rec)
  base+=len(rows)
  if isinstance(q,int):return q
 return status
if __name__=='__main__':sys.exit(main())
