import slicer, numpy as np
D=r"C:\Users\Laboratorio\Downloads\mandibula_guia"
exec(open(D+r"\chk_slices.py").read().split("import nrrd_min")[0])
v=slicer.util.loadVolume(D+r"\cbct.nrrd"); a=slicer.util.arrayFromVolume(v)
M=np.load(D+r"\M_blender.npy").astype(bool)
tiles=[]
for j in (110,125,140):
    g=np.clip(a[40:140,j,180:290]/2500*255,0,255); rgb=np.stack([g,g,g],-1)
    m=M[40:140,j,180:290]; rgb[m]=0.55*rgb[m]+0.45*np.array([0,255,0])
    tiles.append(np.kron(rgb[::-1],np.ones((4,4,1))))
png(D+r"\ex_cor.png",np.concatenate(tiles,1))
slicer.app.quit()
