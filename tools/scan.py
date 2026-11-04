import json,struct,re,collections
d=open('track1.iso','rb').read()
F={n:(l,s) for n,l,s in json.load(open('files.json'))}
def get(n): l,s=F[n];return d[l*2048:l*2048+s]
def is_lead(c): return 0x81<=c<=0x9f or 0xe0<=c<=0xef
def strings(b):
    # 0x00-terminated runs consisting of sjis chars and 0x0d, starting after 0x00
    res=[];k=0;n=len(b)
    while k<n:
        if (k==0 or b[k-1]==0 or (k>=4 and b[k-4]==0 and b[k-3] in (0x20,0xff)) or b[k-2:k]==bytes([255,255]) or (k>=2 and b[k-2]==0x80 and b[k-1] in (5,6))) and is_lead(b[k]):
            j=k;ok=True;chars=0
            while j<n and b[j]!=0:
                if b[j]==0x0d: j+=1;continue
                if is_lead(b[j]) and j+1<n:
                    try: b[j:j+2].decode('shift_jis')
                    except: ok=False;break
                    j+=2;chars+=1
                elif 0x20<=b[j]<0x7f: j+=1
                else: ok=False;break
            if ok and j<n and b[j]==0 and chars>=1:
                res.append((k,j));k=j+1;continue
        k+=1
    return res
if __name__=='__main__':
    names=[n for n in F if re.match(r'^(E\d\d\d|T\d\d\d|CLAS|ROOM|SMP\d|LOAD|P000|OPDB|S2DA|LSD\d)$',n)]
    for n in names:
        b=get(n);S=strings(b)
        best=None
        for base in (0x200000,0,0xff0000,0x20000,0x10000,0x220000,0x240000,0x40000,0x80000,0x8000,0xFF8000):
            refs=0
            ptrs=set()
            for k in range(0,len(b)-3,2):
                v=struct.unpack('>I',b[k:k+4])[0]-base
                if 0<=v<len(b): ptrs.add(v)
            r=sum(1 for s,e in S if s in ptrs)
            if not best or r>best[1]: best=(base,r)
        print(n,len(b),'strings',len(S),'chars',sum(e-s for s,e in S),'best base',hex(best[0]),best[1])
