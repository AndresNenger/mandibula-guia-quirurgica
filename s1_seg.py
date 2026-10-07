import slicer, numpy as np, vtk, time
D=r"C:\Users\Laboratorio\Downloads\mandibula_guia"
v=slicer.util.loadVolume(D+r"\cbct.nrrd")
m=vtk.vtkMatrix4x4(); v.GetIJKToRASMatrix(m)
print("IJK2RAS",[[m.GetElement(i,j) for j in range(4)] for i in range(3)],flush=True)
a=slicer.util.arrayFromVolume(v)
seg=slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentationNode","Seg"); seg.CreateDefaultDisplayNodes(); seg.SetReferenceImageGeometryParameterFromVolumeNode(v)
for n in ("Mandibula","Resto"): seg.GetSegmentation().AddEmptySegment(n,n)
Z,Y,X=np.indices(a.shape)
bone=a>550
plane=97+0.243*(Y-90)
mand_seed=bone&(Z<plane-14)&(Y<215)&(Z>40)
rest_seed=bone&(((Z>plane+14))|(Y>262))
w=slicer.qMRMLSegmentEditorWidget(); w.setMRMLScene(slicer.mrmlScene)
sen=slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentEditorNode"); w.setMRMLSegmentEditorNode(sen)
w.setSegmentationNode(seg); w.setSourceVolumeNode(v); sen.SetMasterVolumeIntensityMask(True); sen.SetMasterVolumeIntensityMaskRange(550,10000)
ids=seg.GetSegmentation().GetSegmentIDs()
def setmask(sid,mk):
    slicer.util.updateSegmentBinaryLabelmapFromArray(mk.astype(np.uint8),seg,sid,v)
setmask("Mandibula",mand_seed); setmask("Resto",rest_seed)
w.setActiveEffectByName("Grow from seeds")
e=w.activeEffect(); 
e.self().onPreview(); 
e.self().onApply()
print("grown",flush=True)
mm=slicer.util.arrayFromSegmentBinaryLabelmap(seg,"Mandibula",v)
print("MAND vox",int(mm.sum()),flush=True)
np.save(D+r"\mand_grow.npy",mm.astype(np.uint8))

slicer.app.quit()
