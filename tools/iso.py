import sys,struct
def sectors(binf,n):
    f=open(binf,'rb')
    for i in range(n):
        f.seek(i*2352+16); yield f.read(2048)
def main():
    binf,out,n=sys.argv[1],sys.argv[2],int(sys.argv[3])
    with open(out,'wb') as o:
        for s in sectors(binf,n): o.write(s)
if __name__=='__main__':main()
