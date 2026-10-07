import slicer, qt, ctk, vtk, numpy as np, os, time, traceback, shutil, math
exec(open(r"C:\Users\Laboratorio\Downloads\mandibula_guia\rec_common.py", encoding="utf-8").read())
REC = os.environ.get("REC", "1") == "1"
SCALE = 1.0 if REC else 0.15
OUT = D + r"\3_slicer_guia.mp4"
S = {"proc": None}
CAP = {"w": None}
mw = slicer.util.mainWindow()


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


def cyl_mask(shape, p0, p1, r):
    """Cilindro (con tapas planas) entre p0 y p1 (mm, marco de índices * 0.5) como máscara [k,j,i]."""
    p0 = np.array(p0, float); p1 = np.array(p1, float)
    lo = np.floor((np.minimum(p0, p1) - r - 1) / 0.5).astype(int); hi = np.ceil((np.maximum(p0, p1) + r + 1) / 0.5).astype(int)
    lo = np.maximum(lo, 0); hi = np.minimum(hi, np.array([shape[2], shape[1], shape[0]]) - 1)
    ii, jj, kk = np.meshgrid(np.arange(lo[0], hi[0] + 1), np.arange(lo[1], hi[1] + 1), np.arange(lo[2], hi[2] + 1), indexing="ij")
    P = np.stack([ii, jj, kk], -1) * 0.5
    ax = p1 - p0; L = np.linalg.norm(ax); ax = ax / L
    t = (P - p0) @ ax
    rad = np.linalg.norm((P - p0) - t[..., None] * ax, axis=-1)
    ins = (t >= 0) & (t <= L) & (rad <= r)
    m = np.zeros(shape, bool)
    m[lo[2]:hi[2] + 1, lo[1]:hi[1] + 1, lo[0]:hi[0] + 1] = np.transpose(ins, (2, 1, 0))
    return m


FOC_MAND = (-90.7, -78.2, 39.5)


def cam_set(theta, elev=10, dist=230, focal=None):
    focal = focal or FOC_MAND
    lmn = slicer.app.layoutManager()
    t = math.radians(theta); e = math.radians(elev)
    pos = (focal[0] + dist * math.cos(e) * math.cos(t), focal[1] + dist * math.cos(e) * math.sin(t), focal[2] + dist * math.sin(e))
    vn = lmn.threeDWidget(0).mrmlViewNode()
    cam = slicer.modules.cameras.logic().GetViewActiveCameraNode(vn)
    cam.SetFocalPoint(*focal); cam.SetPosition(*pos); cam.SetViewUp(0, 0, 1)
    lmn.threeDWidget(0).threeDView().renderWindow().GetRenderers().GetFirstRenderer().ResetCameraClippingRange()
    lmn.threeDWidget(0).threeDView().forceRender()


def orbit(theta0, deg, frames, **kw):
    for f in range(frames):
        cam_set(theta0 + deg * f / float(frames), **kw)
        yield 0.1


def shot(n):
    try:
        sn = slicer.util.getNode('Guia_Ortodoncia'); dd = sn.GetDisplayNode()
        print('DBG', n, 'vis', dd.GetVisibility(), dd.GetVisibility3D(), 'closed', sn.GetSegmentation().ContainsRepresentation('Closed surface'), 'master', sn.GetSegmentation().GetMasterRepresentationName(), [(sn.GetSegmentation().GetNthSegmentID(i), dd.GetSegmentVisibility3D(sn.GetSegmentation().GetNthSegmentID(i)), dd.GetSegmentOpacity3D(sn.GetSegmentation().GetNthSegmentID(i))) for i in range(sn.GetSegmentation().GetNumberOfSegments())], flush=True)
        slicer.app.processEvents()
        slicer.app.layoutManager().threeDWidget(0).threeDView().grab().save(D + '\dbg_' + n + '.png')
    except Exception as ex:
        print('SHOTFAIL', ex, flush=True)


def refresh(seg):
    seg.RemoveClosedSurfaceRepresentation()
    seg.CreateClosedSurfaceRepresentation()
    slicer.app.processEvents()


def idx2ras(u):  # u en mm del marco de índices (i,j,k)*0.5
    return (-u[0], -u[1], u[2])


def seq():
    mw.showMaximized()
    yield 2.0
    hwnd = int(mw.winId())
    start_rec(hwnd, OUT)
    yield 1.5
    if REC:
        S["proc"] = launch_ffmpeg(hwnd, OUT)
        if not S["proc"]:
            slicer.app.exit(1)
            return
    lm = slicer.app.layoutManager()
    caption("Regreso a 3D Slicer  ·  Paso 3 de 3: guía quirúrgica para ortodoncia", "Con la malla mejorada en Blender diseñamos una guía de mini-implante (TAD) sobre los dientes")
    yield 3.0
    # ---- 1. cargar CBCT + modelo de Blender
    caption("Cargamos el CBCT y el modelo mejorado en Blender", "mandibula_blender.stl se alinea con el volumen original")
    lm.setLayout(slicer.vtkMRMLLayoutNode.SlicerLayoutFourUpView)
    v = slicer.util.loadVolume(D + r"\cbct.nrrd")
    dn = v.GetDisplayNode(); dn.AutoWindowLevelOff(); dn.SetWindowLevel(2400, 1250)
    slicer.util.setSliceViewerLayers(background=v, fit=True)
    mn = slicer.util.loadModel(D + r"\mandibula_blender.stl")
    mn.SetName("Mandibula_Blender")
    md = mn.GetDisplayNode(); md.SetColor(0.95, 0.9, 0.78); md.SetSliceIntersectionThickness(3); md.SetSliceIntersectionVisibility(True)
    yield 1.0
    for nm, a, b in (("Red", 20, 60), ("Green", -80, -50), ("Yellow", -115, -65)):
        lm.sliceWidget(nm).sliceLogic().SetSliceOffset((a + b) / 2.0)
    tv = lm.threeDWidget(0).threeDView()
    vn = lm.threeDWidget(0).mrmlViewNode()
    vn.SetBoxVisible(False)
    vn.SetAxisLabelsVisible(False)
    vn.SetBackgroundColor(0.04, 0.06, 0.1)
    vn.SetBackgroundColor2(0.2, 0.28, 0.4)
    cam_set(90)
    yield 3.5
    for k in range(40):
        for nm, a, b in (("Red", 25, 55), ("Green", -85, -45)):
            lm.sliceWidget(nm).sliceLogic().SetSliceOffset(a + (b - a) * k / 39.0)
        yield 0.1
    lm.setLayout(slicer.vtkMRMLLayoutNode.SlicerLayoutOneUp3DView)
    cam_set(90)
    yield from orbit(90, 100, 35)
    # ---- 2. modelo -> segmentación
    caption("Convertimos el modelo en segmentación", "Segmentations: la malla pasa a ser un segmento editable")
    seg = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentationNode", "Guia_Ortodoncia")
    seg.CreateDefaultDisplayNodes()
    seg.SetReferenceImageGeometryParameterFromVolumeNode(v)
    slicer.modules.segmentations.logic().ImportModelToSegmentationNode(mn, seg)
    sg = seg.GetSegmentation()
    id_m = sg.GetNthSegmentID(0)
    sg.GetSegment(id_m).SetName("Mandibula")
    sg.GetSegment(id_m).SetColor(0.93, 0.88, 0.76)
    mn.GetDisplayNode().SetVisibility(False)
    dsp = seg.GetDisplayNode()
    seg.CreateClosedSurfaceRepresentation()
    yield 2.5
    # ---- 3. editor
    lm.setLayout(slicer.vtkMRMLLayoutNode.SlicerLayoutFourUpView)
    slicer.util.selectModule("SegmentEditor")
    yield 1.5
    ew = slicer.modules.segmenteditor.widgetRepresentation().self().editor
    ew.setSegmentationNode(seg)
    ew.setSourceVolumeNode(v)
    sen = ew.mrmlSegmentEditorNode()
    sen.SetOverwriteMode(slicer.vtkMRMLSegmentEditorNode.OverwriteNone)
    sen.SetMaskMode(slicer.vtkMRMLSegmentationNode.EditAllowedEverywhere)
    M = slicer.util.arrayFromSegmentBinaryLabelmap(seg, id_m, v).astype(bool)
    shape = M.shape
    Z, Y, X = np.indices(shape)
    plane = 97 + 0.243 * (Y - 90)

    # ---- 4. región coronal
    caption("Paso A: aislar las coronas dentarias", "Corte bajo el plano oclusal (≈ 11 mm) y por delante del 1.er molar")
    crown = M & (Z > plane - 22) & (Y < 168)
    id_c = sg.AddEmptySegment("Coronas", "Coronas", (0.2, 0.55, 0.95))
    slicer.util.updateSegmentBinaryLabelmapFromArray(crown.astype(np.uint8), seg, id_c, v)
    dsp.SetSegmentOpacity3D(id_m, 0.45)
    ew.setCurrentSegmentID(id_c)
    refresh(seg)
    yield 3.5
    print("CROWN_VOX", int(crown.sum()), flush=True)

    # ---- 5. planificación del mini-implante
    caption("Paso B: planificar el mini-implante (TAD)", "Zona vestibular posterior izquierda · eje a 45° respecto al plano oclusal")
    j0, z0 = 128, 70
    ib = np.argwhere(M[z0, j0, :]).max()
    E = np.array([ib * 0.5, j0 * 0.5, z0 * 0.5])
    d = np.array([-math.cos(math.radians(45)), 0.0, -math.sin(math.radians(45))])
    print("TAD_E_idx", ib, j0, z0, flush=True)
    lineN = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsLineNode", "Eje_perforacion")
    pa = idx2ras(E - 14 * d); pb = idx2ras(E + 10 * d)
    lineN.AddControlPointWorld(vtk.vtkVector3d(*pa)); lineN.AddControlPointWorld(vtk.vtkVector3d(*pb))
    lineN.GetDisplayNode().SetColor(1, 0.9, 0.1); lineN.GetDisplayNode().SetSelectedColor(1, 0.9, 0.1)
    lineN.GetDisplayNode().SetLineThickness(0.4)
    lineN.GetDisplayNode().SetPropertiesLabelVisibility(False)
    lineN.GetDisplayNode().SetPointLabelsVisibility(False)
    lineN.GetDisplayNode().SetGlyphScale(2.0)
    id_t = sg.AddEmptySegment("TAD_planificado", "TAD_planificado", (0.95, 0.15, 0.15))
    slicer.util.updateSegmentBinaryLabelmapFromArray(cyl_mask(shape, E - 1.0 * d, E + 9.0 * d, 0.8).astype(np.uint8), seg, id_t, v)
    refresh(seg)
    # centrar cortes en el sitio
    ras = idx2ras(E)
    slicer.modules.markups.logic().JumpSlicesToLocation(ras[0], ras[1], ras[2], True)
    yield 4.0
    # vista 3D lateral
    lm.setLayout(slicer.vtkMRMLLayoutNode.SlicerLayoutOneUp3DView)
    cam_set(180, 8, 120, idx2ras(E))
    yield 2.5
    shot('tad')

    # ---- 6. cáscara de la guía
    caption("Paso C: cáscara de la guía alrededor de las coronas", "Margin (+2.5 mm) − holgura de ajuste (0.5 mm)")
    lm.setLayout(slicer.vtkMRMLLayoutNode.SlicerLayoutFourUpView)
    yield 1.0
    id_h = sg.AddEmptySegment("Holgura", "Holgura", (0.7, 0.7, 0.2))
    id_g = sg.AddEmptySegment("Guia", "Guia", (0.1, 0.85, 0.75))
    for tgt in (id_h, id_g):
        ew.setCurrentSegmentID(tgt)
        ew.setActiveEffectByName("Logical operators")
        e = ew.activeEffect()
        e.setParameter("Operation", "COPY")
        e.setParameter("ModifierSegmentID", id_c)
        e.self().onApply()
        yield 0.8
    ew.setCurrentSegmentID(id_h)
    ew.setActiveEffectByName("Margin")
    e = ew.activeEffect(); e.setParameter("MarginSizeMm", "0.5"); e.setParameter("Operation", "Grow")
    yield 0.8
    e.self().onApply()
    yield 1.5
    ew.setCurrentSegmentID(id_g)
    e = ew.activeEffect(); e.setParameter("MarginSizeMm", "2.5"); e.setParameter("Operation", "Grow")
    yield 0.8
    e.self().onApply()
    yield 2.0
    ew.setActiveEffectByName("Logical operators")
    e = ew.activeEffect(); e.setParameter("Operation", "SUBTRACT"); e.setParameter("ModifierSegmentID", id_h)
    yield 0.8
    e.self().onApply()
    ew.setActiveEffectByName(None)
    refresh(seg)
    dsp.SetSegmentVisibility3D(id_h, False)
    dsp.SetSegmentVisibility(id_h, False)
    dsp.SetSegmentOpacity3D(id_c, 0.0)
    dsp.SetSegmentVisibility(id_c, False)
    yield 2.5
    lm.setLayout(slicer.vtkMRMLLayoutNode.SlicerLayoutOneUp3DView)
    cam_set(180, 12, 150, idx2ras(E))
    yield 1.5
    shot('shell')
    yield from orbit(180, 50, 30, elev=12, dist=150, focal=idx2ras(E))

    # ---- 7. manguito + conector
    caption("Paso D: manguito guía y brazo de conexión", "Cilindro Ø5.6 mm sobre el eje del TAD + brazo hacia la cáscara dentaria")
    Cm = crown
    kz = 88
    iw = np.argwhere(Cm[kz, j0, :]).max()
    W = np.array([iw * 0.5 + 1.2, j0 * 0.5, kz * 0.5])
    Stop = E - 6.0 * d
    sleeve = cyl_mask(shape, E - 7.5 * d, E + 0.5 * d, 2.8)
    arm = cyl_mask(shape, W, Stop, 2.2)
    id_s = sg.AddEmptySegment("Manguito_Conector", "Manguito_Conector", (0.1, 0.85, 0.75))
    slicer.util.updateSegmentBinaryLabelmapFromArray((sleeve | arm).astype(np.uint8), seg, id_s, v)
    refresh(seg)
    ew.setCurrentSegmentID(id_g)
    lm.setLayout(slicer.vtkMRMLLayoutNode.SlicerLayoutOneUp3DView)
    gfoc = idx2ras((E + W) / 2.0)
    cam_set(185, 15, 80, gfoc)
    yield 1.5
    yield from orbit(185, 40, 15, elev=15, dist=80, focal=gfoc)
    ew.setActiveEffectByName("Logical operators")
    e = ew.activeEffect(); e.setParameter("Operation", "UNION"); e.setParameter("ModifierSegmentID", id_s)
    yield 0.8
    e.self().onApply()
    sg.RemoveSegment(id_s)
    refresh(seg)
    yield 2.5
    shot('sleeve')
    # ---- 8. perforación
    caption("Paso E: canal de perforación Ø2.2 mm", "El eje del mini-implante queda definido por el manguito (resta booleana)")
    bore = cyl_mask(shape, E - 16 * d, E + 6 * d, 1.1)
    id_b = sg.AddEmptySegment("Perforacion", "Perforacion", (1, 0.4, 0.1))
    slicer.util.updateSegmentBinaryLabelmapFromArray(bore.astype(np.uint8), seg, id_b, v)
    refresh(seg)
    cam_set(185, 15, 70, idx2ras((E + W) / 2.0))
    yield 2.5
    ew.setCurrentSegmentID(id_g)
    ew.setActiveEffectByName("Logical operators")
    e = ew.activeEffect(); e.setParameter("Operation", "SUBTRACT"); e.setParameter("ModifierSegmentID", id_b)
    yield 0.8
    e.self().onApply()
    ew.setActiveEffectByName(None)
    sg.RemoveSegment(id_b)
    refresh(seg)
    yield 2.5
    shot('bore')
    # ---- 9. resultado
    caption("Guía quirúrgica terminada", "Cáscara dentosoportada + manguito de perforación · TAD planificado en rojo")
    dsp.SetSegmentVisibility(id_c, False)
    dsp.SetSegmentVisibility3D(id_c, False)
    lineN.GetDisplayNode().SetVisibility(True)
    dsp.SetSegmentOpacity3D(id_m, 0.55)
    lm.setLayout(slicer.vtkMRMLLayoutNode.SlicerLayoutOneUp3DView)
    slicer.util.selectModule("Data")
    gfoc = idx2ras((E + W) / 2.0)
    cam_set(180, 12, 95, gfoc)
    yield 1.5
    shot('final1')
    yield from orbit(180, 130, 60, elev=15, dist=95, focal=gfoc)
    shot('final2')
    cam_set(90, 25, 190)
    yield from orbit(90, 110, 40, elev=25, dist=190)
    # ---- 10. exportar
    out_dir = D + r"\_exp_guia"
    os.makedirs(out_dir, exist_ok=True)
    for f in os.listdir(out_dir):
        os.remove(os.path.join(out_dir, f))
    arr = vtk.vtkStringArray()
    arr.InsertNextValue(id_g)
    slicer.modules.segmentations.logic().ExportSegmentsClosedSurfaceRepresentationToFiles(out_dir, seg, arr, "STL", True, 1.0, False)
    for f in os.listdir(out_dir):
        if f.lower().endswith(".stl"):
            shutil.copy(os.path.join(out_dir, f), D + r"\guia_quirurgica_ortodoncia.stl")
    arr2 = vtk.vtkStringArray(); arr2.InsertNextValue(id_t)
    slicer.modules.segmentations.logic().ExportSegmentsClosedSurfaceRepresentationToFiles(out_dir, seg, arr2, "STL", True, 1.0, False)
    for f in os.listdir(out_dir):
        if f.lower().endswith(".stl") and "TAD" in f:
            shutil.copy(os.path.join(out_dir, f), D + r"\TAD_planificado.stl")
    slicer.util.saveScene(D + r"\escena_guia_ortodoncia.mrb")
    print("GUIA_STL", os.path.getsize(D + r"\guia_quirurgica_ortodoncia.stl"), flush=True)
    caption("Exportado: guia_quirurgica_ortodoncia.stl", "Listo para impresión 3D · diseño demostrativo, requiere validación clínica")
    yield 4.5
    if REC:
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
            if REC:
                stop_ffmpeg(S["proc"])
        except Exception:
            pass
        slicer.app.exit(2)
        return
    qt.QTimer.singleShot(max(1, int(dt * 1000 * SCALE)), drive)


qt.QTimer.singleShot(1500, drive)
