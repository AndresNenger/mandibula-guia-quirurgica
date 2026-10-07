import numpy as np, zlib, struct
D=r"C:\Users\Laboratorio\Downloads\mandibula_guia"
def png(path,img):
    img=np.clip(img,0,255).astype(np.uint8); h,w=img.shape[:2]
    raw=b"".join(b"\x00"+img[i].tobytes() for i in range(h))
    def ch(t,d): c=struct.pack(">I",len(d))+t+d; return c+struct.pack(">I",zlib.crc32(t+d)&0xffffffff)
    open(path,"wb").write(b"\x89PNG\r\n\x1a\n"+ch(b"IHDR",struct.pack(">IIBBBBB",w,h,8,2,0,0,0))+ch(b"IDAT",zlib.compress(raw))+ch(b"IEND",b""))
m=np.load(D+r"\mand_grow.npy").astype(bool)
for name,ax in (("sag",2),("cor",1),("axi",0)):
    p=m.sum(axis=ax).astype(float); p=255*p/p.max()
    if ax!=0: p=p[::-1]
    png(D+r"\m_%s.png"%name,np.stack([p,p,p],-1))
