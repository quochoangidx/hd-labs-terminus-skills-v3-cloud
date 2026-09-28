#!/usr/bin/env python3
import sys, os, re, stat

class EdError(Exception): pass
class Quit(Exception): pass
class Line(str): pass

class PosixRegex:
 def __init__(self, pattern, flags=0):
  self.pattern=pattern; self.flags=flags; self.base=re.compile(pattern,flags)
 def _at(self,text,pos):
  n=len(text)
  for end in range(n,pos-1,-1):
   try: rx=re.compile('(?:'+self.pattern+')(?=.{'+str(n-end)+'}\\Z)',self.flags)
   except re.error: return self.base.match(text,pos)
   m=rx.match(text,pos)
   if m is not None: return m
  return None
 def search(self,text,pos=0):
  for i in range(pos,len(text)+1):
   m=self._at(text,i)
   if m is not None: return m
  return None
 def finditer(self,text):
  pos=0
  while pos<=len(text):
   m=self.search(text,pos)
   if m is None: return
   yield m
   pos=m.end() if m.end()>m.start() else m.end()+1

class Editor:
 def __init__(self, argv):
  self.ext=False; self.loose=False; self.script=False; self.restricted=False
  self.prompt=None; self.prompt_on=False; self.quiet=False; self.filename=''
  i=0
  while i<len(argv) and argv[i].startswith('-') and argv[i]!='-':
   a=argv[i]
   if a=='-E': self.ext=True
   elif a=='-l': self.loose=True
   elif a=='-q': self.quiet=True
   elif a=='-r': self.restricted=True
   elif a=='-s': self.script=True
   elif a=='-p':
    i+=1
    if i>=len(argv): raise SystemExit(1)
    self.prompt=argv[i]; self.prompt_on=True
   else: raise SystemExit(1)
   i+=1
  if len(argv)-i>1: raise SystemExit(1)
  self.lines=[]; self.cur=0; self.modified=False; self.warned=False
  self.cut=[]; self.marks={}; self.undo=None; self.last_re=None; self.last_sub_re=None
  self.last_repl=None; self.last_sub_flags=''; self.bad=False; self.quit_now=False
  self.regstdin=stat.S_ISREG(os.fstat(0).st_mode); self.input=sys.stdin.buffer; self.in_global=False; self.inject=None
  if i<len(argv):
   self.filename=argv[i]
   try: self._load(argv[i], initial=True)
   except EdError:
    self.bad=True
    if self.regstdin: self.quit_now=True

 def out(self,s): sys.stdout.buffer.write(s.encode('latin1')); sys.stdout.buffer.flush()
 def err(self,msg='?'):
  self.out('?\n'); self.bad=True
  if not self.quiet: print(msg,file=sys.stderr)
  if self.regstdin: self.quit_now=True
  raise EdError(msg)
 def readline(self, prompt=True):
  if self.inject is not None:
   return self.inject.pop(0) if self.inject else None
  if prompt and self.prompt_on: self.out(self.prompt)
  b=self.input.readline()
  if b==b'': return None
  return b[:-1] if b.endswith(b'\n') else b
 def text(self,b): return b.decode('latin1')
 def bytes_count(self, ls): return sum(len(x.encode('latin1'))+1 for x in ls)
 def checkfile(self,f):
  if not f: raise EdError('No current filename')
  if f.startswith('!'): raise EdError('Shell access restricted')
  if self.restricted and (os.path.dirname(f) not in ('','.') or f in ('.','..')): raise EdError('Restricted')
 def readfile(self,f):
  self.checkfile(f)
  try:
   data=open(f,'rb').read()
  except OSError: raise EdError('Cannot open input file')
  binary=b'\0' in data
  parts=data.split(b'\n')
  if parts and parts[-1]==b'': parts.pop()
  elif data and not binary: parts[-1]+=b''
  return [Line(x.decode('latin1')) for x in parts], len(data)
 def _load(self,f,initial=False):
  self.checkfile(f)
  try: ls,n=self.readfile(f)
  except EdError:
   if initial and not self.regstdin:
    if not self.quiet: print(f+': No such file or directory',file=sys.stderr)
    self.lines=[]; self.cur=0; return
   raise
  self.lines=ls; self.cur=len(ls); self.modified=False; self.warned=False
  if not self.script: self.out(str(n)+'\n')
 def snapshot(self):
  if self.in_global: return
  self.undo=([*self.lines],self.cur,self.modified,dict(self.marks),[*self.cut])
 def restore(self):
  if self.undo is None: raise EdError('Nothing to undo')
  now=([*self.lines],self.cur,self.modified,dict(self.marks),[*self.cut])
  self.lines,self.cur,self.modified,self.marks,self.cut=self.undo; self.undo=now
 def changed(self): self.modified=True; self.warned=False

 def bre(self,p):
  if self.ext: return p
  out=''; i=0; incl=False
  while i<len(p):
   c=p[i]
   if c=='[': incl=True; out+=c; i+=1; continue
   if c==']' and incl: incl=False; out+=c; i+=1; continue
   if c=='\\' and i+1<len(p):
    d=p[i+1]; i+=2
    if incl: out+='\\'+d if d in '\\' else d; continue
    if d in '()|+?': out+=d
    elif d=='{':
     j=p.find('\\}',i)
     if j>=0: out+='{'+p[i:j]+'}'; i=j+2
     else: out+='\\{'
    elif d=='<': out+=r'(?<!\w)(?=\w)'
    elif d=='>': out+=r'(?<=\w)(?!\w)'
    elif d in ('`',): out+='^'
    elif d=="'": out+='$'
    elif d in 'bBwW' or d.isdigit(): out+='\\'+d
    else: out+=re.escape(d)
    continue
   if not incl and c in '()+?|{}': out+='\\'+c
   else: out+=c
   i+=1
  return out
 def regex(self,p,icase=False):
  if p=='':
   if self.last_re is None: raise EdError('No previous pattern')
   p=self.last_re
  else: self.last_re=p
  q=self.bre(p)
  classes={'alnum':'A-Za-z0-9','alpha':'A-Za-z','blank':' \t','cntrl':'\x00-\x1F\x7F','digit':'0-9','graph':'!-~','lower':'a-z','print':' -~','punct':r'!-/:-@[-`{-~','space':'\t\n\v\f\r ','upper':'A-Z','xdigit':'A-Fa-f0-9'}
  for k,v in classes.items(): q=q.replace('[:'+k+':]' ,v)
  try: return PosixRegex(q, re.I if icase else 0),p
  except re.error: raise EdError('Invalid pattern')
 def delim(self,s,pos,d):
  out=''; esc=False
  while pos<len(s):
   c=s[pos]
   if c==d and not esc: return out,pos+1
   if c=='\\' and not esc: esc=True; out+=c
   else: esc=False; out+=c
   pos+=1
  raise EdError('Unclosed delimiter')
 def searchaddr(self,s,pos,forward):
  d=s[pos]; p,pos=self.delim(s,pos+1,d); ic=False
  if pos<len(s) and s[pos]=='I': ic=True; pos+=1
  rx,_=self.regex(p,ic)
  n=len(self.lines)
  if not n: raise EdError('No match')
  seq=range(self.cur,n) if forward else range(self.cur-2,-1,-1)
  seq=list(seq)+(list(range(0,self.cur)) if forward else list(range(n-1,self.cur-2,-1)))
  for k in seq:
   if rx.search(self.lines[k]): return k+1,pos
  raise EdError('No match')
 def oneaddr(self,s,pos):
  while pos<len(s) and s[pos] in ' \t': pos+=1
  if pos>=len(s): return None,pos
  c=s[pos]; base=None
  if c=='.': base=self.cur; pos+=1
  elif c=='$': base=len(self.lines); pos+=1
  elif c.isdigit():
   j=pos
   while j<len(s) and s[j].isdigit(): j+=1
   base=int(s[pos:j]); pos=j
  elif c in '/?': base,pos=self.searchaddr(s,pos,c=='/')
  elif c=="'" and pos+1<len(s) and s[pos+1].islower():
   x=s[pos+1]; pos+=2
   if x not in self.marks or self.marks[x]>len(self.lines): raise EdError('Invalid mark')
   base=self.marks[x]
  elif c in '+-': base=self.cur
  else: return None,pos
  while True:
   save=pos
   while pos<len(s) and s[pos] in ' \t': pos+=1
   sign=1
   if pos<len(s) and s[pos] in '+-': sign=-1 if s[pos]=='-' else 1; pos+=1
   elif pos<len(s) and s[pos].isdigit(): sign=1
   else: pos=save; break
   j=pos
   while j<len(s) and s[j].isdigit(): j+=1
   num=int(s[pos:j]) if j>pos else 1; base+=sign*num; pos=j
  if base<0 or base>len(self.lines): raise EdError('Invalid address')
  return base,pos
 def addresses(self,s):
  vals=[]; pos=0; sep=None
  a,pos=self.oneaddr(s,pos)
  if a is not None: vals.append(a)
  while True:
   p=pos
   while p<len(s) and s[p] in ' \t': p+=1
   if p>=len(s) or s[p] not in ',;': pos=p; break
   sep=s[p]; p+=1
   if not vals: vals.append(1 if sep==',' else self.cur)
   if sep==';': self.cur=vals[-1]
   a,p2=self.oneaddr(s,p)
   vals.append(len(self.lines) if a is None else a); pos=p2
  return vals[-2:],pos,sep
 def rng(self,addrs,default,zero=False):
  if not addrs: a=b=default
  elif len(addrs)==1: a=b=addrs[0]
  else: a,b=addrs
  if a>b or a<0 or b>len(self.lines) or (not zero and a==0): raise EdError('Invalid address')
  return a,b
 def noaddr(self,a):
  if a: raise EdError('Unexpected address')
 def adjust_marks_delete(self,a,b):
  d=b-a+1
  for k,v in list(self.marks.items()):
   if a<=v<=b: del self.marks[k]
   elif v>b: self.marks[k]=v-d
 def adjust_marks_insert(self,p,n):
  for k,v in list(self.marks.items()):
   if v>p: self.marks[k]=v+n
 def input_lines(self):
  ls=[]
  while True:
   b=self.readline(False)
   if b is None or b==b'.': break
   ls.append(Line(self.text(b)))
  return ls
 def plist(self,line):
  out=''
  col=0
  for ch in line:
   o=ord(ch)
   if ch=='\\': z='\\\\'
   elif ch=='\t': z='\\t'
   elif ch=='\b': z='\\b'
   elif ch=='\a': z='\\a'
   elif ch=='\v': z='\\v'
   elif ch=='\f': z='\\f'
   elif ch=='\r': z='\\r'
   elif 32<=o<127: z=ch
   else: z='\\%03o'%o
   if col+len(z)>78: out+='\\\n'; col=0
   out+=z; col+=len(z)
  return out+'$\n'
 def prints(self,a,b,mode='p'):
  if a<1 or b>len(self.lines) or a>b: raise EdError('Invalid address')
  for i in range(a,b+1):
   prefix=('%d\t'%i) if 'n' in mode else ''
   if 'l' in mode: self.out(prefix+self.plist(self.lines[i-1]))
   else: self.out(prefix+self.lines[i-1]+'\n')
  self.cur=b
 def suffix(self,s,pos):
  modes=[]
  while pos<len(s) and s[pos] in 'pln':
   if s[pos] in modes: raise EdError('Invalid suffix')
   modes.append(s[pos]); pos+=1
  if s[pos:].strip(): raise EdError('Unexpected command suffix')
  return modes
 def do_suffix(self,modes):
  if modes: self.prints(self.cur,self.cur,''.join(modes))
 def file_suffix(self,arg):
  i=0; modes=[]
  while i<len(arg) and arg[i] in 'pln':
   if arg[i] in modes: raise EdError('Invalid suffix')
   modes.append(arg[i]); i+=1
  if i<len(arg) and arg[i] not in ' \t': raise EdError('Invalid filename syntax')
  return modes,arg[i:].strip()

 def substitute(self,a,b,rest):
  oldcur=self.cur
  if not rest or rest[0] in 'gpr0123456789':
   if self.last_sub_re is None: raise EdError('No previous substitution')
   pat=self.last_sub_re; repl=self.last_repl; flags=self.last_sub_flags
   fl=rest
   if 'r' in fl:
    if self.last_re is None: raise EdError('No previous pattern')
    pat=self.last_re
   if 'g' in fl: flags='' if 'g' in flags else 'g'
  else:
   d=rest[0]
   if d in ' \t\n': raise EdError('Invalid delimiter')
   pat,p=self.delim(rest,1,d)
   try: repl,p2=self.delim(rest,p,d); fl=rest[p2:]
   except EdError:
    repl=rest[p:]; fl='p'
   if repl=='%':
    if self.last_repl is None: raise EdError('No previous substitution')
    repl=self.last_repl
   flags=fl
   self.last_sub_re=pat if pat else self.last_re
   self.last_repl=repl; self.last_sub_flags=flags
  ic='i' in flags.lower(); rx,pat=self.regex(pat,ic); self.last_sub_re=pat
  g='g' in flags; nums=''.join(c for c in flags if c.isdigit()); nth=int(nums) if nums else 0
  pmodes=[c for c in flags if c in 'pln']
  if g and nth: raise EdError('Invalid substitution suffix')
  def expand(m):
   out=''; i=0
   while i<len(repl):
    if repl[i]=='&': out+=m.group(0); i+=1
    elif repl[i]=='\\' and i+1<len(repl):
     c=repl[i+1]; i+=2
     if c.isdigit(): out+=m.group(int(c)) or ''
     else: out+=c
    else: out+=repl[i]; i+=1
   return out
  new=[]; anyc=False; last=None; lastcut=None
  for idx in range(a-1,b):
   line=self.lines[idx]; matches=list(rx.finditer(line)); chosen=matches if g else (([matches[nth-1]] if len(matches)>=nth else []) if nth else matches[:1])
   if not chosen: new.append(line); continue
   anyc=True; out=''; q=0
   for m in chosen: out+=line[q:m.start()]+expand(m); q=m.end()
   out+=line[q:]; pieces=out.split('\n'); new.extend(Line(x) for x in pieces); last=a+len(new)-1; lastcut=Line(pieces[-1])
  if not anyc: self.cur=oldcur; raise EdError('No match')
  self.snapshot(); self.cut=[lastcut]; kept={k:v-a for k,v in self.marks.items() if a<=v<=b}; self.adjust_marks_delete(a,b); self.lines[a-1:b]=new; self.adjust_marks_insert(a-1,len(new)); [self.marks.__setitem__(k,min(a+off,a+len(new)-1)) for k,off in kept.items()]; self.cur=last; self.changed()
  for m in pmodes: self.prints(self.cur,self.cur,m)

 def global_cmd(self,a,b,rest,invert,interactive=False):
  if not rest: raise EdError('Invalid pattern')
  d=rest[0]; pat,p=self.delim(rest,1,d); ic=False
  if p<len(rest) and rest[p]=='I': ic=True; p+=1
  rx,_=self.regex(pat,ic)
  targets=[self.lines[i-1] for i in range(a,b+1) if bool(rx.search(self.lines[i-1])) != invert]
  cmd=rest[p:]
  if not interactive:
   while cmd.endswith('\\'):
    x=self.readline(False)
    if x is None: break
    cmd=cmd[:-1]+'\n'+self.text(x)
   if cmd=='': cmd='p'
  lastcmd=None
  before=([*self.lines],self.cur,self.modified,dict(self.marks),[*self.cut])
  oldundo=self.undo; self.in_global=True
  try:
   for obj in targets:
    try: self.cur=next(i+1 for i,x in enumerate(self.lines) if x is obj)
    except StopIteration: continue
    if interactive:
     self.prints(self.cur,self.cur)
     x=self.readline(False)
     if x is None: break
     z=self.text(x)
     while z.endswith('\\'):
      y=self.readline(False)
      if y is None: break
      z=z[:-1]+'\n'+self.text(y)
     if z=='': continue
     if z=='&':
      if lastcmd is None: raise EdError('No previous command')
      z=lastcmd
     else: lastcmd=z
     self.execute_list(z)
    else: self.execute_list(cmd)
  finally:
   self.in_global=False
   if self.lines != before[0] or self.modified != before[2]: self.undo=before
   else: self.undo=oldundo
 def execute_list(self,s):
  old=self.inject; self.inject=[x.encode('latin1') for x in s.split('\n')]
  try:
   while self.inject:
    x=self.text(self.inject.pop(0)); self.execute(x,inglobal=True)
  finally: self.inject=old

 def execute(self,s,inglobal=False):
  addrs,pos,sep=self.addresses(s); rest=s[pos:]; rest=rest.lstrip(' \t')
  if not rest:
   a=(addrs[-1] if addrs else self.cur+1); self.prints(a,a); return
  c=rest[0]; arg=rest[1:]
  if inglobal and c in 'gvGV': raise EdError('Cannot nest global commands')
  if c=='#':
   if sep==';' and addrs: self.cur=addrs[-1]
   return
  if c in 'aic':
   default=self.cur if c!='i' else self.cur
   a,b=self.rng(addrs,default,zero=(c=='a'))
   if c=='i': a=b=b-1
   self.snapshot(); new=self.input_lines()
   if c=='c': self.cut=self.lines[a-1:b]; self.adjust_marks_delete(a,b); p=a-1; self.lines[a-1:b]=new
   else: p=b; self.lines[p:p]=new
   self.adjust_marks_insert(p,len(new)); self.cur=p+len(new) if new else (min(a,len(self.lines)) if c=='c' else min(b,len(self.lines))); self.changed(); self.do_suffix(self.suffix(arg,0)); return
  if c=='d':
   a,b=self.rng(addrs,self.cur); modes=self.suffix(arg,0); self.snapshot(); self.cut=self.lines[a-1:b]; self.adjust_marks_delete(a,b); del self.lines[a-1:b]; self.cur=min(a,len(self.lines)); self.changed(); self.do_suffix(modes); return
  if c in 'pnl':
   a,b=self.rng(addrs,self.cur); modes=self.suffix(arg,0); self.prints(a,b,c+''.join(modes)); return
  if c=='=':
   a,b=self.rng(addrs,len(self.lines),zero=True)
   if arg.strip(): raise EdError('Invalid suffix')
   self.out(str(b)+'\n'); return
  if c=='k':
   a,b=self.rng(addrs,self.cur)
   if len(arg)!=1 or not arg.islower(): raise EdError('Invalid mark')
   self.marks[arg]=b; return
  if c=='y':
   a,b=self.rng(addrs,self.cur); modes=self.suffix(arg,0); self.cut=self.lines[a-1:b]; self.do_suffix(modes); return
  if c=='x':
   a,b=self.rng(addrs,self.cur,True); modes=self.suffix(arg,0)
   if not self.cut: raise EdError('Cut buffer is empty')
   self.snapshot(); copies=[Line(x) for x in self.cut]; self.lines[b:b]=copies; self.adjust_marks_insert(b,len(copies)); self.cur=b+len(self.cut); self.changed(); self.do_suffix(modes); return
  if c in 'mt':
   a,b=self.rng(addrs,self.cur); dest,p=self.oneaddr(arg,0)
   if dest is None: dest=self.cur
   modes=self.suffix(arg,p)
   block=self.lines[a-1:b] if c=='m' else [Line(x) for x in self.lines[a-1:b]]
   if c=='m' and a<=dest<=b: raise EdError('Invalid destination')
   self.snapshot(); moved={k:v-a for k,v in self.marks.items() if c=='m' and a<=v<=b}
   if c=='m':
    self.adjust_marks_delete(a,b); del self.lines[a-1:b]
    if dest>b: dest-=b-a+1
   self.lines[dest:dest]=block; self.adjust_marks_insert(dest,len(block))
   for k,off in moved.items(): self.marks[k]=dest+off+1
   self.cur=dest+len(block); self.changed(); self.do_suffix(modes); return
  if c=='j':
   if not addrs: a,b=self.cur,self.cur+1
   else: a,b=self.rng(addrs,self.cur)
   modes=self.suffix(arg,0)
   if b>len(self.lines): raise EdError('Invalid address')
   self.snapshot(); self.cut=self.lines[a-1:b]; z=Line(''.join(self.cut)); firstmarks=[k for k,v in self.marks.items() if v==a]; self.adjust_marks_delete(a,b); self.lines[a-1:b]=[z]
   for k in firstmarks: self.marks[k]=a
   self.cur=a; self.changed(); self.do_suffix(modes); return
  if c=='s':
   a,b=self.rng(addrs,self.cur); self.substitute(a,b,arg); return
  if c in 'gvGV':
   a,b=self.rng(addrs[0:] if addrs else [],1 if not self.lines else 1)
   if not addrs: a,b=(1,len(self.lines))
   self.global_cmd(a,b,arg,c in 'vV',c in 'GV'); return
  if c=='u':
   self.noaddr(addrs); modes=self.suffix(arg,0)
   self.restore(); self.do_suffix(modes); return
  if c=='f':
   self.noaddr(addrs)
   if arg and arg[0] not in ' \t': raise EdError('Invalid filename syntax')
   f=arg.strip()
   if f: self.checkfile(f); self.filename=f
   elif not self.filename: raise EdError('No current filename')
   else: self.out(self.filename+'\n')
   return
  if c in 'eE':
   self.noaddr(addrs); modes,f=self.file_suffix(arg); f=f or self.filename
   if c=='e' and self.modified and not self.warned: self.warned=True; raise EdError('Warning: buffer modified')
   self.checkfile(f); self.filename=f; self._load(f); self.do_suffix(modes); return
  if c=='r':
   a,b=self.rng(addrs,len(self.lines),True); modes,f=self.file_suffix(arg); f=f or self.filename
   if not self.filename and f: self.filename=f
   ls,n=self.readfile(f); self.snapshot(); self.lines[b:b]=ls; self.adjust_marks_insert(b,len(ls)); self.cur=b+len(ls) if ls else b
   if ls: self.changed()
   if not self.script: self.out(str(n)+'\n')
   self.do_suffix(modes); return
  if c in 'wW':
   append=c=='W'; q=False
   if c=='w' and arg.startswith('q'): q=True; arg=arg[1:]
   modes,f=self.file_suffix(arg); f=f or self.filename
   if not self.filename and f: self.filename=f
   self.checkfile(f)
   if addrs: a,b=self.rng(addrs,self.cur)
   else: a,b=(1,len(self.lines))
   data=(''.join(x+'\n' for x in self.lines[a-1:b])).encode('latin1')
   try:
    with open(f,'ab' if append else 'wb') as h: h.write(data)
   except OSError: raise EdError('Cannot open output file')
   if not self.script: self.out(str(len(data))+'\n')
   if not append and a==1 and b==len(self.lines): self.modified=False; self.warned=False
   if q: raise Quit()
   self.do_suffix(modes); return
  if c in 'qQ':
   self.noaddr(addrs)
   if arg.strip(): raise EdError('Invalid suffix')
   if c=='q' and self.modified and not self.warned: self.warned=True; raise EdError('Warning: buffer modified')
   raise Quit()
  if c=='P':
   self.noaddr(addrs)
   if arg.strip(): raise EdError('Invalid suffix')
   self.prompt_on=not self.prompt_on; return
  if c=='z':
   a,b=self.rng(addrs,self.cur+1); a=b; n=int(arg) if arg.strip().isdigit() else 22; self.prints(a,min(len(self.lines),a+n-1)); return
  raise EdError('Unknown command')

 def run(self):
  if self.quit_now: return 1
  while True:
   b=self.readline(True)
   if b is None:
    try:
     if self.modified and not self.warned: self.warned=True; self.out('?\n'); self.bad=True; continue
     break
    except: break
   text=self.text(b)
   while text.endswith('\\'):
    more=self.readline(False)
    if more is None: break
    text=text[:-1]+'\n'+self.text(more)
   try: self.execute(text)
   except Quit: break
   except EdError as e:
    self.out('?\n'); self.bad=True
    if not self.quiet: print(str(e),file=sys.stderr)
    if self.regstdin: break
  return 0 if (self.loose or not self.bad) else 1

def main(argv):
 try: return Editor(argv).run()
 except (EdError,OSError) as e:
  sys.stdout.write('?\n'); return 1
if __name__=='__main__': sys.exit(main(sys.argv[1:]))
