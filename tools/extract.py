import os
import sys,json,re,struct
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from scan import F,get,strings
NAMES=[n for n in F if re.match(r'^(E\d\d\d|T\d\d\d|CLAS|ROOM|SMP\d|LOAD|P000)$',n)]
def lvl(ch):
    b=ch.encode('shift_jis')
    if len(b)==1: return 'a'
    c=b[0]<<8|b[1]
    if c<0x8890: return 'sym'
    if c<=0x9872: return 'k1'
    return 'k2'
def plausible(t, referenced):
    try: s=t.decode('shift_jis')
    except: return False
    body=s.replace('\r','').replace('@','')
    if any(ord(ch)<0x80 and not (referenced and ch in ' ;') for ch in body): return False
    if any(lvl(ch)=='k2' for ch in body): return False
    kana=sum(1 for ch in body if '\u3040'<=ch<='\u30ff')
    kan=sum(1 for ch in body if lvl(ch)=='k1')
    if kana+kan==0: return False
    if len(body)<2 and not referenced: return False
    if len(body)<3 and kana==0 and not referenced: return False
    return True
def ptrs(b,base=0x200000):
    P={}
    for k in range(0,len(b)-3,2):
        v=struct.unpack('>I',b[k:k+4])[0]-base
        if 0<=v<len(b): P.setdefault(v,[]).append(k)
    return P
if __name__=='__main__':
    out=[]
    for n in NAMES:
        b=get(n);P=ptrs(b)
        for s,e in strings(b):
            ref=s in P
            if plausible(b[s:e],ref):
                out.append(dict(f=n,s=s,e=e,ref=ref,jp=b[s:e].decode('shift_jis')))
    json.dump(out,open('strings.json','w',encoding='utf-8'),ensure_ascii=False,indent=0)
    u={}
    for o in out: u.setdefault(o['jp'],0); u[o['jp']]+=1
    print(len(out),len(u),sum(len(k) for k in u))
    rej=[]
    for n in NAMES:
        b=get(n);P=ptrs(b)
        for s,e in strings(b):
            if not plausible(b[s:e],s in P) and n[0] in 'ETC': rej.append(b[s:e].decode('shift_jis','replace'))
    print(len(rej)); print(rej[:200])
