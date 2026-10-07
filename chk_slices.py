import numpy as np, zlib, struct, sys
sys.path.insert(0,r"C:\Users\Laboratorio\Downloads\mandibula_guia")
D=r"C:\Users\Laboratorio\Downloads\mandibula_guia"
def png(path,img):
    img=np.clip(img,0,255).astype(np.uint8); h,w=img.shape[:2]
    raw=b"".join(b"\x00"+img[i].tobytes() for i in range(h))
    def ch(t,d): c=struct.pack(">I",len(d))+t+d; return c+struct.pack(">I",zlib.crc32(t+d)&0xffffffff)
    open(path,"wb").write(b"\x89PNG\r\n\x1a\n"+ch(b"IHDR",struct.pack(">IIBBBBB",w,h,8,2,0,0,0))+ch(b"IDAT",zlib.compress(raw))+ch(b"IEND",b""))
import nrrd_min
