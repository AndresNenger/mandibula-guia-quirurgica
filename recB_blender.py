import bpy, bmesh, blf, math, os, subprocess, ctypes, time, sys
from mathutils import Euler

D = r"C:\Users\Laboratorio\Downloads\mandibula_guia"
exec(open(D + r"\rec_common.py", encoding="utf-8").read())
SRC = D + r"\mandibula_slicer.stl"
OUTSTL = D + r"\mandibula_blender.stl"
OUTMP4 = D + r"\2_blender_procesado.mp4"

state = {"caption": "", "sub": "", "proc": None}


def find_hwnd():
    pid = os.getpid()
    out = subprocess.run(["powershell", "-NoProfile", "-Command",
                          "(Get-Process -Id %d).MainWindowTitle; (Get-Process -Id %d).MainWindowHandle" % (pid, pid)],
                         capture_output=True, text=True).stdout.strip().splitlines()
    if len(out) >= 2 and out[0].strip() and out[1].strip() not in ("", "0"):
        return int(out[1].strip()), out[0].strip()
    return None, None


def view3d():
    for win in bpy.context.window_manager.windows:
        for area in win.screen.areas:
            if area.type == 'VIEW_3D':
                region = [r for r in area.regions if r.type == 'WINDOW'][0]
                return win, area, region, area.spaces.active
    return None, None, None, None


def draw_caption():
    if not state["caption"]:
        return
    blf.enable(0, blf.SHADOW)
    blf.shadow(0, 5, 0.0, 0.0, 0.0, 1.0)
    blf.shadow_offset(0, 2, -2)
    blf.color(0, 1, 1, 1, 1)
    blf.size(0, 30)
    blf.position(0, 140, 70, 0)
    blf.draw(0, state["caption"])
    blf.color(0, 0.8, 0.88, 1.0, 1)
    blf.size(0, 21)
    blf.position(0, 140, 36, 0)
    blf.draw(0, state["sub"])


handler = bpy.types.SpaceView3D.draw_handler_add(draw_caption, (), 'WINDOW', 'POST_PIXEL')


def redraw():
    win, area, region, space = view3d()
    if area:
        area.tag_redraw()


def set_caption(a, b=""):
    state["caption"], state["sub"] = a, b
    redraw()


def orbit_steps(seconds, deg_total):
    n = int(seconds * FPS)
    for _ in range(n):
        win, area, region, space = view3d()
        r3d = space.region_3d
        q = Euler((0, 0, math.radians(deg_total / n)), 'XYZ').to_quaternion()
        r3d.view_rotation = q @ r3d.view_rotation
        area.tag_redraw()
        yield 1.0 / FPS


def hold(seconds):
    for _ in range(int(seconds * FPS)):
        redraw()
        yield 1.0 / FPS


def frame_selected():
    win, area, region, space = view3d()
    with bpy.context.temp_override(window=win, area=area, region=region):
        bpy.ops.view3d.view_selected()
    r3d = space.region_3d
    r3d.view_rotation = Euler((math.radians(90), 0, 0), 'XYZ').to_quaternion()
    r3d.view_distance *= 1.1
    area.tag_redraw()


def stats(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    nm = len([e for e in bm.edges if not e.is_manifold])
    vol = abs(bm.calc_volume())
    nt = len(bm.faces)
    bm.free()
    return nm, vol, nt


def apply_mod(obj, mod):
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=mod.name)


def sequence():
    yield 1.0
    hwnd, title = find_hwnd()
    user32 = ctypes.windll.user32
    if hwnd:
        user32.ShowWindow(hwnd, 3)
        user32.SetForegroundWindow(hwnd)
    yield 2.0
    hwnd, title = find_hwnd()
    state["proc"] = launch_ffmpeg(hwnd, OUTMP4)
    if not state["proc"]:
        bpy.ops.wm.quit_blender()
        return
    yield 0.5
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    win, area, region, space = view3d()
    with bpy.context.temp_override(window=win, area=area, region=region):
        bpy.ops.screen.screen_full_area()
    win, area, region, space = view3d()
    space.overlay.show_stats = True
    space.shading.type = 'SOLID'
    space.shading.light = 'STUDIO'
    space.shading.color_type = 'OBJECT'
    space.shading.background_type = 'VIEWPORT'
    space.shading.background_color = (0.07, 0.09, 0.13)
    space.show_gizmo = False
    space.overlay.show_floor = False
    space.overlay.show_axis_x = False
    space.overlay.show_axis_y = False
    set_caption("Blender 5.2  ·  Paso 2 de 3: mejorar la malla de la mandíbula", "Escena vacía")
    yield from hold(3.0)

    # --- 1. importar
    set_caption("Importamos mandibula_slicer.stl (salida de 3D Slicer)", "Malla cruda: escalones del voxel, ruido y posibles fragmentos")
    bpy.ops.wm.stl_import(filepath=SRC)
    obj = bpy.context.selected_objects[0]
    obj.name = "Mandibula"
    obj.color = (0.93, 0.88, 0.76, 1.0)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.shade_flat()
    frame_selected()
    nm0, vol0, nt0 = stats(obj)
    dims = obj.dimensions
    print("IMPORT", nt0, nm0, round(vol0), [round(x, 1) for x in dims], flush=True)
    set_caption("Malla cruda importada: %d triángulos" % nt0,
                "Ancho %.0f mm · alto %.0f mm · profundidad %.0f mm" % (dims.x, dims.z, dims.y))
    yield from orbit_steps(5.0, 200)

    # --- 2. wireframe
    space.overlay.show_wireframes = True
    space.overlay.wireframe_threshold = 1.0
    set_caption("Revisamos la topología (wireframe)", "Triángulos muy densos y superficie con escalones de segmentación")
    yield from orbit_steps(4.0, 120)
    space.overlay.show_wireframes = False

    # --- 3. fragmentos sueltos
    set_caption("Paso 1: detectar fragmentos sueltos", "Separar por partes desconectadas")
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.separate(type='LOOSE')
    bpy.ops.object.mode_set(mode='OBJECT')
    meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    meshes.sort(key=lambda o: len(o.data.polygons), reverse=True)
    big, small = meshes[0], meshes[1:]
    for o in small:
        o.color = (1.0, 0.1, 0.1, 1.0)
    print("PIEZAS", len(meshes), [len(o.data.polygons) for o in meshes][:12], flush=True)
    set_caption("Fragmentos sueltos en rojo", "%d piezas desconectadas: 1 mandíbula + %d fragmentos" % (len(meshes), len(small)))
    yield from orbit_steps(3.0, 90)
    for o in meshes:
        o.select_set(False)
    for o in small:
        o.select_set(True)
    bpy.context.view_layer.objects.active = big
    bpy.ops.object.delete()
    big.select_set(True)
    bpy.context.view_layer.objects.active = big
    obj = big
    obj.name = "Mandibula"
    set_caption("Paso 1 listo: fragmentos eliminados", "Nos quedamos solo con la mandíbula")
    yield from orbit_steps(2.0, 60)

    # --- 4. cerrar huecos y normales
    set_caption("Paso 2: cerrar huecos y recalcular normales", "Mesh → Fill holes + Recalculate Outside")
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.remove_doubles(threshold=0.001)
    bpy.ops.mesh.fill_holes(sides=0)
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode='OBJECT')
    nm1, vol1, nt1 = stats(obj)
    print("TRAS_CIERRE", nt1, nm1, round(vol1), flush=True)
    yield from orbit_steps(3.0, 80)

    # --- 5. suavizado
    set_caption("Paso 3: suavizado Laplaciano con conservación de volumen", "Elimina el efecto escalera del voxel sin encoger la pieza")
    lap = obj.modifiers.new("Suavizado", 'LAPLACIANSMOOTH')
    lap.iterations = 12
    lap.lambda_factor = 0.6
    lap.lambda_border = 0.0
    lap.use_volume_preserve = True
    lap.use_normalized = True
    yield from orbit_steps(2.0, 60)
    apply_mod(obj, lap)
    bpy.ops.object.shade_smooth()
    nm2, vol2, nt2 = stats(obj)
    set_caption("Superficie suavizada", "Volumen: %d mm³ → %d mm³ (%.1f%% de cambio)" % (round(vol1), round(vol2), 100 * (vol2 - vol1) / vol1))
    print("TRAS_SUAVE", nt2, nm2, round(vol2), flush=True)
    yield from orbit_steps(4.0, 120)

    # --- 6. decimar
    set_caption("Paso 4: optimizar la malla (Decimate)", "Menos triángulos, misma forma: archivo más liviano para el siguiente paso")
    dec = obj.modifiers.new("Decimar", 'DECIMATE')
    dec.ratio = 0.35
    yield from orbit_steps(1.5, 40)
    apply_mod(obj, dec)
    bpy.ops.object.shade_smooth()
    nm3, vol3, nt3 = stats(obj)
    print("TRAS_DECIMAR", nt3, nm3, round(vol3), flush=True)
    set_caption("Malla optimizada: %d → %d triángulos" % (nt0, nt3), "Volumen %d mm³ · aristas abiertas: %d" % (round(vol3), nm3))
    yield from orbit_steps(3.0, 90)
    space.overlay.show_wireframes = True
    set_caption("Malla final (wireframe)", "Distribución uniforme y superficie continua")
    yield from orbit_steps(4.0, 100)
    space.overlay.show_wireframes = False

    # --- 7. exportar
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.wm.stl_export(filepath=OUTSTL, export_selected_objects=True)
    print("EXPORT", os.path.getsize(OUTSTL), flush=True)
    set_caption("Exportado: mandibula_blender.stl", "Siguiente paso: volver a 3D Slicer y diseñar la guía quirúrgica")
    yield from orbit_steps(4.0, 120)
    yield from hold(1.0)
    try:
        stop_ffmpeg(state["proc"])
    except Exception as e:
        print("ffmpeg cierre", e, flush=True)
    print("REC_DONE", flush=True)
    bpy.ops.wm.quit_blender()


gen = sequence()


def step():
    try:
        return next(gen)
    except StopIteration:
        return None
    except Exception:
        import traceback
        print("ERROR", traceback.format_exc(), flush=True)
        try:
            stop_ffmpeg(state["proc"])
        except Exception:
            pass
        return None


bpy.app.timers.register(step, first_interval=3.0)
