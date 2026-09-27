#!/usr/bin/env python3
"""Small, byte-oriented GNU grep 3.8 compatible implementation."""
import sys, os, re

B=lambda s: os.fsencode(s)
WORD=set(b'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_')

def ci(c):
    return c+32 if 65<=c<=90 else c

def cls_named(name):
    sets={
      b'alnum': set(range(48,58))|set(range(65,91))|set(range(97,123)),
      b'alpha': set(range(65,91))|set(range(97,123)), b'blank':{9,32},
      b'cntrl':set(range(32))|{127}, b'digit':set(range(48,58)),
      b'graph':set(range(33,127)), b'lower':set(range(97,123)),
      b'print':set(range(32,127)), b'punct':set(range(33,48))|set(range(58,65))|set(range(91,97))|set(range(123,127)),
      b'space':{9,10,11,12,13,32}, b'upper':set(range(65,91)), b'xdigit':set(b'0123456789abcdefABCDEF'),
      b'word':WORD,
    }
    return sets.get(name,set())

class Parser:
 def __init__(self,p,ere=False,icase=False): self.p=p; self.i=0; self.ere=ere; self.icase=icase
 def special(self,ch):
  if self.i>=len(self.p): return False
  if self.ere: return self.p[self.i]==ch
  return self.i+1<len(self.p) and self.p[self.i]==92 and self.p[self.i+1]==ch
 def take_special(self,ch):
  if not self.special(ch): return False
  self.i += 1 if self.ere else 2; return True
 def parse(self, stop=False):
  alts=[self.seq(stop)]
  while self.take_special(124): alts.append(self.seq(stop))
  return ('alt',alts) if len(alts)>1 else alts[0]
 def seq(self,stop):
  a=[]
  while self.i<len(self.p):
   if self.special(124) or (stop and self.special(41)): break
   x=self.atom()
   if self.i<len(self.p) and self.p[self.i]==42: self.i+=1; x=('rep',x,0,None)
   elif self.ere and self.i<len(self.p) and self.p[self.i] in (43,63):
    q=self.p[self.i]; self.i+=1; x=('rep',x,1,None) if q==43 else ('rep',x,0,1)
   elif (not self.ere) and self.i+1<len(self.p) and self.p[self.i]==92 and self.p[self.i+1] in (43,63):
    q=self.p[self.i+1]; self.i+=2; x=('rep',x,1,None) if q==43 else ('rep',x,0,1)
   else:
    save=self.i
    if self.take_special(123):
     j=self.i
     while self.i<len(self.p) and 48<=self.p[self.i]<=57:self.i+=1
     if self.i==j: self.i=save
     else:
      lo=int(self.p[j:self.i]); hi=lo
      if self.i<len(self.p) and self.p[self.i]==44:
       self.i+=1; j=self.i
       while self.i<len(self.p) and 48<=self.p[self.i]<=57:self.i+=1
       hi=int(self.p[j:self.i]) if self.i>j else None
      if not self.take_special(125): self.i=save
      else: x=('rep',x,lo,hi)
   a.append(x)
  return ('seq',a)
 def atom(self):
  if self.take_special(40):
   x=self.parse(True)
   if not self.take_special(41): raise ValueError('unmatched parenthesis')
   return x
  c=self.p[self.i]; self.i+=1
  if c==46:return ('dot',)
  if c==94:return ('bol',)
  if c==36:return ('eol',)
  if c==91:return self.bracket()
  if c==92:
   if self.i>=len(self.p): return ('lit',92)
   c=self.p[self.i]; self.i+=1
   # GNU extensions commonly documented by grep.
   if c in (98,60,62): return ({98:'wb',60:'bow',62:'eow'}[c],)
   if c in (66,96,39): return ({66:'nwb',96:'bol',39:'eol'}[c],)
  return ('lit',c)
 def bracket(self):
  neg=False
  if self.i<len(self.p) and self.p[self.i]==94: neg=True; self.i+=1
  s=set(); first=True; prev=None
  if self.i<len(self.p) and self.p[self.i]==93: s.add(93); self.i+=1
  while self.i<len(self.p) and self.p[self.i]!=93:
   if self.p[self.i:self.i+2]==b'[:':
    k=self.p.find(b':]',self.i+2)
    if k>=0: s |= cls_named(self.p[self.i+2:k]); self.i=k+2; prev=None; continue
   c=self.p[self.i]; self.i+=1
   if c==92 and self.i<len(self.p): c=self.p[self.i]; self.i+=1
   if c==45 and prev is not None and self.i<len(self.p) and self.p[self.i]!=93:
    d=self.p[self.i]; self.i+=1
    if d==92 and self.i<len(self.p): d=self.p[self.i]; self.i+=1
    s |= set(range(min(prev,d),max(prev,d)+1)); prev=None
   else: s.add(c); prev=c
  if self.i>=len(self.p): return ('lit',91)
  self.i+=1
  return ('class',s,neg)

def ends(node,data,pos,icase,memo):
 key=(id(node),pos)
 if key in memo:return memo[key]
 t=node[0]; out=set()
 if t=='lit':
  if pos<len(data) and (ci(data[pos])==ci(node[1]) if icase else data[pos]==node[1]):out.add(pos+1)
 elif t=='dot':
  if pos<len(data):out.add(pos+1)
 elif t=='class':
  if pos<len(data):
   c=data[pos]; hit=c in node[1]
   if icase: hit=hit or ci(c) in {ci(x) for x in node[1]}
   if hit != node[2]:out.add(pos+1)
 elif t=='bol':
  if pos==0:out.add(pos)
 elif t=='eol':
  if pos==len(data):out.add(pos)
 elif t in ('wb','nwb','bow','eow'):
  l=pos>0 and data[pos-1] in WORD; r=pos<len(data) and data[pos] in WORD
  ok={'wb':l!=r,'nwb':l==r,'bow':(not l and r),'eow':(l and not r)}[t]
  if ok:out.add(pos)
 elif t=='alt':
  for x in node[1]:out |= ends(x,data,pos,icase,memo)
 elif t=='seq':
  out={pos}
  for x in node[1]:
   out={q for p in out for q in ends(x,data,p,icase,memo)}
   if not out:break
 elif t=='rep':
  x,lo,hi=node[1:]; cur={pos}; levels=[cur]
  limit=hi if hi is not None else len(data)+1
  for _ in range(limit):
   nxt={q for p in cur for q in ends(x,data,p,icase,memo) if q!=p}
   if not nxt:break
   levels.append(nxt); cur=nxt
  for k in range(lo,min(len(levels), (hi+1 if hi is not None else len(levels)))):out |= levels[k]
 memo[key]=out; return out

class Opt:
 def __init__(self):
  self.mode=None; self.pats=[]; self.icase=False; self.inv=False; self.word=False; self.line=False
  self.out=None; self.only=False; self.quiet=False; self.silent=False; self.byte=False; self.fname=None; self.label=None
  self.num=False; self.tab=False; self.zero_name=False; self.zero=False; self.max=None
  self.after=None; self.before=None; self.common=0; self.context_given=False; self.sep=b'--'; self.use_sep=True; self.binary='binary'

def need(argv,i,val):
 if val!='':return val,i
 if i+1>=len(argv):raise ValueError('missing option argument')
 return argv[i+1],i+1

def parse(argv):
 o=Opt(); files=[]; operand=None; i=0; explicit=False
 while i<len(argv):
  a=argv[i]
  if a=='--': i+=1; break
  if not a.startswith('-') or a=='-': break
  if a.startswith('--'):
   x=a[2:]; name,eq,val=x.partition('=')
   noarg={'extended-regexp':'E','fixed-strings':'F','basic-regexp':'G','ignore-case':'i','no-ignore-case':'J','invert-match':'v','word-regexp':'w','line-regexp':'x','count':'c','files-with-matches':'l','files-without-match':'L','quiet':'q','silent':'q','only-matching':'o','no-messages':'s','byte-offset':'b','with-filename':'H','no-filename':'h','line-number':'n','initial-tab':'T','null':'Z','null-data':'z','text':'a'}
   argmap={'regexp':'e','file':'f','max-count':'m','label':'Y','after-context':'A','before-context':'B','context':'C','group-separator':'S','binary-files':'D'}
   if name=='no-group-separator':o.use_sep=False; i+=1;continue
   if name in noarg: chars=noarg[name]
   elif name in argmap:
    val,i=need(argv,i,val if eq else ''); chars=argmap[name]+val
   else: raise ValueError('unknown option')
  else: chars=a[1:]
  j=0
  if chars.isdigit(): o.common=int(chars); o.context_given=True; i+=1; continue
  while j<len(chars):
   c=chars[j]; j+=1
   if c in 'GEF':
    if o.mode and o.mode!=c:raise ValueError('conflicting matchers')
    o.mode=c
   elif c=='i':o.icase=True
   elif c=='J':o.icase=False
   elif c=='v':o.inv=True
   elif c=='w':o.word=True
   elif c=='x':o.line=True
   elif c=='c':
    if o.out not in ('l','L'):o.out='c'
   elif c in 'lL':o.out=c
   elif c=='q':o.quiet=True
   elif c=='o':o.only=True
   elif c=='s':o.silent=True
   elif c=='b':o.byte=True
   elif c=='H':o.fname=True
   elif c=='h':o.fname=False
   elif c=='n':o.num=True
   elif c=='T':o.tab=True
   elif c=='Z':o.zero_name=True
   elif c=='z':o.zero=True
   elif c=='a':o.binary='text'
   elif c=='I':o.binary='without-match'
   elif c=='I':o.binary='without-match'
   elif c in 'efmYABCS D'.replace(' ',''):
    val,i=need(argv,i,chars[j:]); j=len(chars)
    if c=='e': o.pats += [(B(x),None) for x in val.split('\n')]; explicit=True
    elif c=='f':
     try:
      d=sys.stdin.buffer.read() if val=='-' else open(val,'rb').read()
      pp=[] if d==b'' else d.split(b'\n'); pp=pp[:-1] if d.endswith(b'\n') else pp
      o.pats += [(x,None) for x in pp]; explicit=True
     except OSError: raise ValueError('pattern file')
    elif c=='m':o.max=int(val)
    elif c=='Y':o.label=B(val)
    elif c=='A':o.after=int(val);o.context_given=True
    elif c=='B':o.before=int(val);o.context_given=True
    elif c=='C':o.common=int(val);o.context_given=True
    elif c=='S':o.sep=B(val);o.use_sep=True
    elif c=='D':
     if val not in ('binary','text','without-match'):raise ValueError('bad binary mode')
     o.binary=val
   else:raise ValueError('unknown option')
  i+=1
 if not explicit:
  if i>=len(argv):raise ValueError('no pattern')
  o.pats=[(B(x),None) for x in argv[i].split('\n')];i+=1
 files=argv[i:]
 if o.after is None:o.after=o.common
 if o.before is None:o.before=o.common
 return o,files

class BackrefPattern:
 def __init__(self, pattern, ere, icase):
  self.regex=re.compile(translate_regex(pattern,ere), re.I if icase else 0)

def translate_regex(p,ere):
 """Translate the documented ASCII BRE/ERE syntax to Python bytes regex."""
 out=bytearray(); i=0
 while i<len(p):
  c=p[i]
  if c==91:                       # copy bracket expression, expanding POSIX classes
   j=i+1; buf=bytearray(b'[')
   if j<len(p) and p[j]==94:buf.append(94);j+=1
   if j<len(p) and p[j]==93:buf.append(93);j+=1
   while j<len(p) and p[j]!=93:
    if p[j:j+2]==b'[:':
     k=p.find(b':]',j+2)
     if k>=0:
      name=p[j+2:k]; chars=sorted(cls_named(name))
      for x in chars:
       if x in (92,93,45,94):buf.append(92)
       buf.append(x)
      j=k+2;continue
    buf.append(p[j]);j+=1
   if j<len(p):buf.append(93);j+=1
   out.extend(buf);i=j;continue
  if c==92 and i+1<len(p):
   d=p[i+1];i+=2
   if 49<=d<=57:out.extend((92,d));continue
   if not ere and d in b'()|+?{}':out.append(d);continue
   if d==60:out.extend(b'(?<![A-Za-z0-9_])(?=[A-Za-z0-9_])');continue
   if d==62:out.extend(b'(?<=[A-Za-z0-9_])(?![A-Za-z0-9_])');continue
   if d==98:out.extend(b'\\b');continue
   if d==66:out.extend(b'\\B');continue
   out.extend((92,d));continue
  i+=1
  if not ere and c in b'()+?|{}':out.extend((92,c))
  else:out.append(c)
 return bytes(out)

def compile_pats(o):
 out=[]
 for p,_ in o.pats:
  if o.mode=='F':out.append(p)
  else:
   if re.search(br'\\[1-9]',p):
    out.append(BackrefPattern(p,o.mode=='E',o.icase));continue
   z=Parser(p,o.mode=='E',o.icase).parse()
   out.append(z)
 return out

def one_matches(data,pats,o,start=0):
 best=None
 for s in range(start,len(data)+1):
  for p in pats:
   if o.mode=='F':
    if p==b'': e=s
    else:
     q=data.lower().find(p.lower(),s) if o.icase else data.find(p,s)
     if q<0:continue
     if q!=s:continue
     e=s+len(p)
    es={e}
   elif isinstance(p,BackrefPattern):
    es=set()
    for ee in range(len(data),s-1,-1):
     mm=p.regex.match(data,s,ee)
     if mm is not None and mm.start()==s and mm.end()==ee:
      es={ee};break
   else:es=ends(p,data,s,o.icase,{})
   for e in es:
    if o.line and not (s==0 and e==len(data)):continue
    if o.word and not ((s==0 or data[s-1] not in WORD) and (e==len(data) or data[e] not in WORD)):continue
    if best is None or e>best:best=e
  if best is not None:return s,best
 return None

def records(d,delim):
 out=[]; start=0
 delims=delim if isinstance(delim,tuple) else (delim,)
 for i,c in enumerate(d):
  if c in delims:out.append((d[start:i],start,True));start=i+1
 if start<len(d):out.append((d[start:],start,False))
 return out

def prefix(o,name,multi,n,off,context=False):
 sep=b'-' if context else b':'
 use_name=o.fname is True or (o.fname is None and multi)
 fields=[]
 if use_name: fields.append(name)
 if o.num:
  z=str(n).encode()
  if o.tab: z=z.rjust(getattr(o,'nwidth',len(z)))
  fields.append(z)
 if o.byte:
  z=str(off).encode()
  if o.tab: z=z.rjust(getattr(o,'bwidth',len(z)))
  fields.append(z)
 if not fields:return b''
 # -Z replaces only the separator immediately following a filename.
 if use_name and o.zero_name:
  r=fields[0]+b'\0'
  if len(fields)>1:r+=sep.join(fields[1:])+sep
 else:r=sep.join(fields)+sep
 if o.tab:r+=b'\t'
 return r

def main(argv):
 try:o,files=parse(argv); pats=compile_pats(o)
 except Exception as e:
  sys.stderr.write('grep: '+str(e)+'\n');return 2
 if not files:files=['-']
 multi=len(files)>1; had=False; err=False; output=[]; last_group=False
 for fn in files:
  name=o.label or b'(standard input)' if fn=='-' else B(fn)
  try:d=sys.stdin.buffer.read() if fn=='-' else open(fn,'rb').read()
  except OSError as e:
   err=True
   if not o.silent:sys.stderr.write('grep: %s: %s\n'%(fn,e.strerror))
   continue
  binary=(b'\0' in d and not o.zero and o.binary!='text')
  rs=records(d,0 if o.zero else ((0,10) if binary else 10))
  o.nwidth=len(str(max(1,len(rs))))
  o.bwidth=len(str(max(0,len(d))))
  selected=[]; matches=[]
  if not (binary and o.binary=='without-match') and o.max!=0:
   for idx,(line,off,term) in enumerate(rs):
    m=one_matches(line,pats,o); yes=(m is not None)^o.inv
    if yes:
     selected.append(idx); matches.append(m)
     if o.max is not None and len(selected)>=o.max:break
     if binary and o.binary=='binary' and o.out!='c':break
  count=len(selected)
  if o.out!='L': had |= count>0
  if o.quiet and count:return 0
  if o.quiet:continue
  if o.out in ('l','L'):
   yes=count>0 if o.out=='l' else count==0
   if yes:
    output.append(name+(b'\0' if o.zero_name else b'\n'))
    had=True
   continue
  if o.out=='c':
   use_name=o.fname is True or (o.fname is None and multi)
   shown=(name+(b'\0' if o.zero_name else b':')) if use_name else b''
   output.append(shown+str(count).encode()+b'\n');continue
  if not count:continue
  if binary and o.binary=='binary':
   output.append(b'Binary file '+name+b' matches\n');continue
  selset=set(selected)
  show=set()
  for x in selected:
   if o.only: show.add(x)
   else: show.update(range(max(0,x-o.before),min(len(rs),x+o.after+1)))
  groups=[]
  for x in sorted(show):
   if not groups or x>groups[-1][-1]+1:groups.append([x])
   else:groups[-1].append(x)
  for gi,g in enumerate(groups):
   if o.context_given and not o.only and (last_group or gi) and o.use_sep:output.append(o.sep+b'\n')
   for x in g:
    line,off,term=rs[x]; chosen=x in selset
    if chosen and o.out is None and not o.inv and getattr(o,'only',False):pass
    if chosen and hasattr(o,'only') and o.only and not o.inv:
     pos=0
     while True:
      m=one_matches(line,pats,o,pos)
      if not m:break
      s,e=m
      if e>s: output.append(prefix(o,name,multi,x+1,off+s)+line[s:e]+(b'\0' if o.zero else b'\n'))
      pos=e if e>s else s+1
    elif not (o.only and o.inv):
     output.append(prefix(o,name,multi,x+1,off,not chosen)+line+(b'\0' if o.zero else b'\n'))
   last_group=True
 if output:sys.stdout.buffer.write(b''.join(output))
 return 2 if err else (0 if had else 1)

if __name__=='__main__':sys.exit(main(sys.argv[1:]))
