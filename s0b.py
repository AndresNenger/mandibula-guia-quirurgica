import slicer, numpy as np, zlib, struct
D=r"C:\Users\Laboratorio\Downloads\mandibula_guia"
v=slicer.util.loadVolume(D+r"\cbct.nrrd")
a=slicer.util.arrayFromVolume(v).astype(np.float32)  # z,y,x
def png(path,img):
    img=np.clip(img,0,255).astype(np.uint8); h,w=img.shape
    raw=b"".join(b"\x00"+img[i].tobytes() for i in range(h))
    def ch(t,d): c=struct.pack(">I",len(d))+t+d; return c+struct.pack(">I",zlib.crc32(t+d)&0xffffffff)
    open(path,"wb").write(b"\x89PNG\r\n\x1a\n"+ch(b"IHDR",struct.pack(">IIBBBBB",w,h,8,0,0,0,0))+ch(b"IDAT",zlib.compress(raw))+ch(b"IEND",b""))
b=(a>1000)
def norm(m): return 255*m/m.max()
png(D+r"\mip_cor.png",norm(a.max(axis=1))[::-1] if False else norm(np.clip(a,0,2500).max(axis=1))[::-1])
png(D+r"\mip_sag.png",norm(np.clip(a,0,2500).max(axis=2))[::-1])
png(D+r"\mip_axi.png",norm(np.clip(a,0,2500).max(axis=0)))
print("BONE frac",b.mean(),flush=True)
slicer.app.quit()
