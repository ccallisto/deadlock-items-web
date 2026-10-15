import struct, sys, os, re
def read_cstr(f):
    b=bytearray()
    while (c:=f.read(1))!=b'\0': b+=c
    return b.decode('utf-8','replace')
def entries(dirpath):
    with open(dirpath,'rb') as f:
        sig,ver,tree=struct.unpack('<III',f.read(12))
        assert sig==0x55aa1234
        hdr=12+(16 if ver==2 else 0); f.seek(hdr)
        while (ext:=read_cstr(f)):
            while (path:=read_cstr(f)):
                while (name:=read_cstr(f)):
                    crc,pre,arc,off,ln,term=struct.unpack('<IHHIIH',f.read(18))
                    predata=f.read(pre)
                    p=('' if path==' ' else path+'/')+name+'.'+ext
                    yield p,arc,off,ln,predata,hdr+tree
def extract(dirpath,pattern,out):
    base=dirpath[:-len('_dir.vpk')]; rx=re.compile(pattern); n=0
    for p,arc,off,ln,pre,dataoff in entries(dirpath):
        if not rx.search(p): continue
        if out is None: print(p); continue
        dst=os.path.join(out,p); os.makedirs(os.path.dirname(dst),exist_ok=True)
        data=pre
        if ln:
            if arc==0x7fff: fn,o=dirpath,dataoff+off
            else: fn,o=f"{base}_{arc:03d}.vpk",off
            with open(fn,'rb') as a: a.seek(o); data+=a.read(ln)
        open(dst,'wb').write(data); n+=1
    if out: print("extracted",n)
if __name__=='__main__':
    extract(sys.argv[1],sys.argv[2],sys.argv[3] if len(sys.argv)>3 else None)
