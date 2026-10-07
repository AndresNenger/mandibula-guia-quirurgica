import slicer, numpy as np, zlib, struct, vtk
D=r"C:\Users\Laboratorio\Downloads\mandibula_guia"
exec(open(D+r"\chk_slices.py").read().split("import nrrd_min")[0])
v=slicer.util.loadVolume(D+r"\cbct.nrrd")
mn=slicer.util.loadModel(D+r"\mandibula_blender.stl")
b=[0]*6; mn.GetBounds(b); print("MODEL RAS bounds",[round(x,1) for x in b],flush=True)
seg=slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentationNode","S"); seg.CreateDefaultDisplayNodes(); seg.SetReferenceImageGeometryParameterFromVolumeNode(v)
slicer.modules.segmentations.logic().ImportModelToSegmentationNode(mn,seg)
sid=seg.GetSegmentation().GetNthSegmentID(0)
M=slicer.util.arrayFromSegmentBinaryLabelmap(seg,sid,v).astype(bool)
print("MASK",M.sum(),np.argwhere(M).min(0),np.argwhere(M).max(0),flush=True)
np.save(D+r"\M_blender.npy",M.astype(np.uint8))
a=slicer.util.arrayFromVolume(v)
Z,Y,X=np.indices(M.shape)
plane=97+0.243*(Y-90)
crown=M&(Z>plane-24)&(Y<200)
print("CROWN",crown.sum(),np.argwhere(crown).min(0),np.argwhere(crown).max(0),flush=True)
# top view heightmap
h=np.where(crown,Z,0).max(axis=0).astype(float)
img=np.stack([h/h.max()*255]*3,-1)
png(D+r"\ex_top.png",np.kron(img,np.ones((3,3,1))))
# axial slice at plane - 14 vox
for zz in (60,75,90):
    s=np.where(M[zz],255,0)
    png(D+r"\ex_ax%d.png"%zz,np.stack([s]*3,-1))
slicer.app.quit()
