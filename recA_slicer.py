import slicer, qt, ctk, vtk, numpy as np, os, time, traceback, shutil, math
import SampleData
exec(open(r"C:\Users\Laboratorio\Downloads\mandibula_guia\rec_common.py", encoding="utf-8").read())
OUT = D + r"\1_slicer_modelado.mp4"
S = {"proc": None}
mw = slicer.util.mainWindow()
CAP = {"w": None}


def caption(t, sub=""):
    old = CAP["w"]
    if old is not None:
        old.hide()
        old.deleteLater()
    cap = qt.QLabel()
    cap.setWindowFlags(qt.Qt.Tool | qt.Qt.FramelessWindowHint | qt.Qt.WindowStaysOnTopHint | qt.Qt.WindowTransparentForInput)
    cap.setAttribute(qt.Qt.WA_ShowWithoutActivating)
    cap.setText("<div style='font-size:22px;font-weight:bold;color:white'>%s</div><div style='font-size:15px;color:#9fd3ff'>%s</div>" % (t, sub))
    cap.setStyleSheet("background-color: rgba(8,18,32,225); padding:10px 18px; border-radius:8px;")
    cap.setFixedWidth(1150)
    cap.setWordWrap(True)
    cap.adjustSize()
    g = mw.mapToGlobal(qt.QPoint(24, mw.height - cap.height - 28))
    cap.move(g)
    cap.show()
    cap.raise_()
    CAP["w"] = cap
    slicer.app.processEvents()


FOC_HEAD = (-90.0, -85.0, 55.0)
FOC_MAND = (-90.7, -78.2, 39.5)


def cam_set(theta, elev=10, dist=230, focal=None):
    focal = focal or FOC_MAND
    lmn = slicer.app.layoutManager()
    t = math.radians(theta); e = math.radians(elev)
    pos = (focal[0] + dist * math.cos(e) * math.cos(t), focal[1] + dist * math.cos(e) * math.sin(t), focal[2] + dist * math.sin(e))
    vn = lmn.threeDWidget(0).mrmlViewNode()
    vn.SetBoxVisible(False)
    vn.SetAxisLabelsVisible(False)
    vn.SetBackgroundColor(0.04, 0.06, 0.1)
    vn.SetBackgroundColor2(0.2, 0.28, 0.4)
    cam = slicer.modules.cameras.logic().GetViewActiveCameraNode(vn)
    cam.SetFocalPoint(*focal); cam.SetPosition(*pos); cam.SetViewUp(0, 0, 1)
    lmn.threeDWidget(0).threeDView().renderWindow().GetRenderers().GetFirstRenderer().ResetCameraClippingRange()
    lmn.threeDWidget(0).threeDView().forceRender()


def orbit(theta0, deg, frames, **kw):
    for f in range(frames):
        cam_set(theta0 + deg * f / float(frames), **kw)
        yield 0.1


def seq():
    mw.showMaximized()
    yield 2.0
    hwnd = int(mw.winId())
    start_rec(hwnd, OUT)
    yield 1.5
    S["proc"] = launch_ffmpeg(hwnd, OUT)
    if not S["proc"]:
        slicer.app.exit(1)
        return
    lm = slicer.app.layoutManager()
    caption("3D Slicer 5.12  ·  Modelado de mandíbula desde un CBCT dental", "Paso 1 de 3 del flujo: Slicer → Blender → Slicer")
    yield 3.0
    # ---- 1. cargar CBCT
    caption("Cargamos el CBCT dental (Sample Data de Slicer)", "360 × 360 × 330 voxeles · 0.5 mm · paciente con ortodoncia fija")
    lm.setLayout(slicer.vtkMRMLLayoutNode.SlicerLayoutFourUpView)
    v = SampleData.downloadSample("CBCTDentalSurgery")
    S["v"] = v
    dn = v.GetDisplayNode()
    dn.AutoWindowLevelOff()
    dn.SetWindowLevel(2400, 1250)
    slicer.util.setSliceViewerLayers(background=v, fit=True)
    yield 2.5
    for k in range(0, 60):
        for nm, a, b in (("Red", 15, 75), ("Green", -90, -20), ("Yellow", -120, -60)):
            lg = lm.sliceWidget(nm).sliceLogic()
            lg.SetSliceOffset(a + (b - a) * k / 59.0)
        yield 0.1
    # ---- 2. volume rendering
    caption("Reconstrucción 3D del volumen (Volume Rendering)", "Se observan cráneo, mandíbula, dientes y brackets metálicos")
    vl = slicer.modules.volumerendering.logic()
    vd = vl.CreateDefaultVolumeRenderingNodes(v)
    vd.SetVisibility(True)
    prop = vd.GetVolumePropertyNode().GetVolumeProperty()
    op = vtk.vtkPiecewiseFunction()
    for x, y in ((0, 0), (450, 0), (700, 0.55), (1400, 0.9), (3900, 1)):
        op.AddPoint(x, y)
    co = vtk.vtkColorTransferFunction()
    for x, r, g, b in ((0, 0, 0, 0), (500, .75, .62, .5), (900, .93, .88, .78), (3900, 1, 1, 1)):
        co.AddRGBPoint(x, r, g, b)
    prop.SetScalarOpacity(op)
    prop.SetColor(co)
    prop.ShadeOn()
    vd.GetVolumePropertyNode().Modified()
    lm.setLayout(slicer.vtkMRMLLayoutNode.SlicerLayoutOneUp3DView)
    cam_set(90, 5, 420, FOC_HEAD)
    yield 2.0
    yield from orbit(90, 200, 60, elev=5, dist=420, focal=FOC_HEAD)
    vd.SetVisibility(False)
    # ---- 3. Segment Editor
    caption("Módulo Segment Editor", "Segmentación semiautomática: umbral de hueso + crecimiento desde semillas")
    lm.setLayout(slicer.vtkMRMLLayoutNode.SlicerLayoutFourUpView)
    slicer.util.selectModule("SegmentEditor")
    yield 2.0
    seg = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentationNode", "Segmentacion_Mandibula")
    seg.CreateDefaultDisplayNodes()
    seg.SetReferenceImageGeometryParameterFromVolumeNode(v)
    S["seg"] = seg
    sg = seg.GetSegmentation()
    cols = {"Hueso": (0.9, 0.85, 0.3), "Mandibula": (0.2, 0.8, 0.4), "Craneo": (0.9, 0.25, 0.25)}
    ids = {}
    for n in ("Hueso", "Mandibula", "Craneo"):
        ids[n] = sg.AddEmptySegment(n, n, cols[n])
    ew = slicer.modules.segmenteditor.widgetRepresentation().self().editor
    ew.setSegmentationNode(seg)
    ew.setSourceVolumeNode(v)
    sen = ew.mrmlSegmentEditorNode()
    yield 1.5
    caption("Umbral (Threshold): seleccionar todo el tejido duro", "Intensidad > 550  →  hueso y dientes")
    ew.setCurrentSegmentID(ids["Hueso"])
    ew.setActiveEffectByName("Threshold")
    yield 1.0
    e = ew.activeEffect()
    e.setParameter("MinimumThreshold", "550")
    e.setParameter("MaximumThreshold", "4000")
    yield 1.5
    e.self().onApply()
    ew.setActiveEffectByName(None)
    yield 3.0
    caption("Semillas: verde = mandíbula · rojo = cráneo y columna", "Se marcan por debajo y por encima del plano oclusal")
    sen.SetMasterVolumeIntensityMask(False)
    a = slicer.util.arrayFromVolume(v)
    Z, Y, X = np.indices(a.shape)
    bone = a > 550
    plane = 97 + 0.243 * (Y - 90)
    mand = bone & (Z < plane - 14) & (Y < 215) & (Z > 40)
    rest = bone & ((Z > plane + 14) | (Y > 262))
    slicer.util.updateSegmentBinaryLabelmapFromArray(mand.astype(np.uint8), seg, ids["Mandibula"], v)
    slicer.util.updateSegmentBinaryLabelmapFromArray(rest.astype(np.uint8), seg, ids["Craneo"], v)
    seg.GetDisplayNode().SetSegmentVisibility(ids["Hueso"], False)
    seg.CreateClosedSurfaceRepresentation()
    yield 4.0
    caption("Grow from seeds: el algoritmo expande las semillas dentro del hueso", "Separa la mandíbula del maxilar y de las vértebras")
    sen.SetMasterVolumeIntensityMask(True)
    sen.SetMasterVolumeIntensityMaskRange(550, 10000)
    ew.setCurrentSegmentID(ids["Mandibula"])
    ew.setActiveEffectByName("Grow from seeds")
    yield 1.5
    e = ew.activeEffect()
    e.self().onPreview()
    yield 2.0
    e.self().onApply()
    ew.setActiveEffectByName(None)
    sen.SetMasterVolumeIntensityMask(False)
    yield 2.0
    caption("Suavizado y limpieza", "Filtro de mediana 1.5 mm + conservar solo la isla más grande")
    ew.setCurrentSegmentID(ids["Mandibula"])
    ew.setActiveEffectByName("Smoothing")
    yield 1.0
    e = ew.activeEffect()
    e.setParameter("SmoothingMethod", "MEDIAN")
    e.setParameter("KernelSizeMm", "1.5")
    yield 1.0
    e.self().onApply()
    yield 1.5
    ew.setActiveEffectByName("Islands")
    yield 1.0
    e = ew.activeEffect()
    e.setParameter("Operation", "KEEP_LARGEST_ISLAND")
    e.setParameter("MinimumSize", "1000")
    yield 1.0
    e.self().onApply()
    ew.setActiveEffectByName(None)
    yield 1.5
    sg.RemoveSegment(ids["Craneo"])
    sg.RemoveSegment(ids["Hueso"])
    seg.RemoveClosedSurfaceRepresentation()
    seg.CreateClosedSurfaceRepresentation()
    mm = slicer.util.arrayFromSegmentBinaryLabelmap(seg, ids["Mandibula"], v)
    vol_ml = float(mm.sum()) * 0.125 / 1000.0
    print("VOL_ML", vol_ml, flush=True)
    # ---- 4. vista 3D del resultado
    caption("Mandíbula segmentada", "Volumen: %.1f mL · modelo 3D de superficie listo" % vol_ml)
    lm.setLayout(slicer.vtkMRMLLayoutNode.SlicerLayoutOneUp3DView)
    cam_set(90, 15, 230)
    yield 1.0
    yield from orbit(90, 270, 75, elev=15, dist=230)
    # ---- 5. exportar
    tmp = D + r"\_exp"
    os.makedirs(tmp, exist_ok=True)
    slicer.modules.segmentations.logic().ExportSegmentsClosedSurfaceRepresentationToFiles(tmp, seg, None, "STL", True, 1.0, False)
    for f in os.listdir(tmp):
        if f.lower().endswith(".stl"):
            shutil.copy(os.path.join(tmp, f), D + r"\mandibula_slicer.stl")
    print("STL", os.path.getsize(D + r"\mandibula_slicer.stl"), flush=True)
    caption("Exportado: mandibula_slicer.stl", "Siguiente paso: limpiar y mejorar la malla en Blender")
    yield 4.0
    stop_ffmpeg(S["proc"])
    print("REC_DONE", flush=True)
    CAP["w"].hide()
    slicer.app.exit(0)


gen = seq()


def drive():
    try:
        dt = next(gen)
    except StopIteration:
        return
    except Exception:
        print("ERROR", traceback.format_exc(), flush=True)
        try:
            stop_ffmpeg(S["proc"])
        except Exception:
            pass
        slicer.app.exit(2)
        return
    qt.QTimer.singleShot(int(dt * 1000), drive)


qt.QTimer.singleShot(1500, drive)
