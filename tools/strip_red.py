import struct,sys
d=bytearray(open(sys.argv[1],'rb').read())
size,hv,ver,boff,bcnt=struct.unpack_from('<IHHII',d,0)
tbl=8+boff; blocks=[]
for i in range(bcnt):
    p=tbl+i*12; t,o,s=struct.unpack_from('<4sII',d,p); blocks.append((t,p+4+o,s))
print(blocks)
keep=[b for b in blocks if b[0] not in (b'RED2',b'REDI')]
struct.pack_into('<I',d,12,len(keep))
for i,(t,a,s) in enumerate(keep):
    p=tbl+i*12; struct.pack_into('<4sII',d,p,t,a-(p+4),s)
open(sys.argv[2],'wb').write(d)
