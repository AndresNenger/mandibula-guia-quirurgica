import slicer, SampleData, numpy as np
D=r"C:\Users\Laboratorio\Downloads\mandibula_guia"
v=SampleData.downloadSample("CBCTDentalSurgery")
print("NODE",v.GetName(),v.GetImageData().GetDimensions(),v.GetSpacing(),v.GetOrigin(),flush=True)
a=slicer.util.arrayFromVolume(v)
print("RANGE",a.min(),a.max(),np.percentile(a,[50,90,99]),flush=True)
slicer.util.saveNode(v,D.replace("\\","/")+"/cbct.nrrd")
slicer.app.quit()
