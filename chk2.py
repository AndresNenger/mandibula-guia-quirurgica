import slicer, numpy as np, zlib, struct
D=r"C:\Users\Laboratorio\Downloads\mandibula_guia"
exec(open(D+r"\chk_slices.py").read().split("import nrrd_min")[0])
v=slicer.util.loadVolume(D+r"\cbct.nrrd"); a=slicer.util.arrayFromVolume(v)
m=np.load(D+r"\mand_grow.npy").astype(bool)
def ov(sl_a,sl_m):
    g=np.clip(sl_a/2500*255,0,255); rgb=np.stack([g,g,g],-1)
    rgb[sl_m]=0.5*rgb[sl_m]+0.5*np.array([0,255,0]); return rgb[::-1]
png(D+r"\o_cor150.png",ov(a[:,150,:],m[:,150,:])[:, :, :])
png(D+r"\o_cor120.png",ov(a[:,120,:],m[:,120,:]))
png(D+r"\o_sag150.png",ov(a[:,:,150],m[:,:,150]))
png(D+r"\o_sag200.png",ov(a[:,:,200],m[:,:,200]))
slicer.app.quit()
