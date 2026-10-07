import subprocess, os, sys
D = r"C:\Users\Laboratorio\Downloads\mandibula_guia"
FF = r"C:\Users\Laboratorio\Downloads\femur_vh\deps_vid\imageio_ffmpeg\binaries\ffmpeg-win-x86_64-v7.1.exe"
FONT = "arialbd.ttf"
FONTR = "arial.ttf"
T = D + r"\_tmp"
os.makedirs(T, exist_ok=True)
BG = "0x0b1626"
ENC = ["-r", "30", "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", "-an"]


def run(args):
    r = subprocess.run([FF, "-y", "-hide_banner", "-loglevel", "error"] + args, capture_output=True, text=True, cwd=T)
    if r.returncode != 0:
        print("FFERR", r.stderr[:600]); sys.exit(1)


def txt(name, s):
    p = T + "\\" + name
    open(p, "w", encoding="utf-8").write(s)
    return name


def dt(name, s, size, y, color="white", font=FONT, x="(w-text_w)/2"):
    return "drawtext=fontfile=%s:textfile=%s:fontsize=%d:fontcolor=%s:x=%s:y=%s" % (font, txt(name, s), size, color, x, y)


def card(out, lines, dur):
    """lines: [(texto, size, y, color, font)]"""
    vf = ",".join(dt("c_%s_%d.txt" % (os.path.basename(out), i), t, sz, y, col, f) for i, (t, sz, y, col, f) in enumerate(lines))
    vf += ",fade=t=in:st=0:d=0.5,fade=t=out:st=%.2f:d=0.5" % (dur - 0.5)
    run(["-f", "lavfi", "-i", "color=c=%s:s=1920x1080:d=%s:r=30" % (BG, dur), "-vf", vf] + ENC + [out])


def clip_full(src, out):
    run(["-i", src, "-vf", "pad=1920:1080:0:0:color=%s,fade=t=in:st=0:d=0.4" % BG] + ENC + [out])


def clip_sum(src, out, label, sublabel, speed=4):
    vf = ("crop=1920:872:0:0,setpts=PTS/%d,fps=30,pad=1920:1080:0:104:color=%s," % (speed, BG)
          + dt("top.txt", "Mandíbula 3D  ·  Blender  ·  Guía quirúrgica para ortodoncia", 40, 30, "white") + ","
          + dt("lab_%s.txt" % os.path.basename(out), label, 46, 984, "0x5fd0ff") + ","
          + dt("sub_%s.txt" % os.path.basename(out), sublabel, 26, 1040, "0xc9d6e6", FONTR)
          + ",fade=t=in:st=0:d=0.3")
    run(["-i", src, "-vf", vf] + ENC + [out])


WHITE, CY, GR = "white", "0x5fd0ff", "0xc9d6e6"
card(T + r"\card0.mp4", [("Modelado de mandíbula y guía quirúrgica", 72, 330, WHITE, FONT),
                           ("para ortodoncia", 72, 420, WHITE, FONT),
                           ("3D Slicer  →  Blender  →  3D Slicer", 44, 560, CY, FONT),
                           ("CBCT dental  ·  segmentación  ·  malla  ·  guía para mini-implante (TAD)", 30, 640, GR, FONTR)], 4)
card(T + r"\card1.mp4", [("Paso 2", 44, 400, CY, FONT), ("Blender: limpiar y mejorar la malla", 66, 470, WHITE, FONT)], 2.5)
card(T + r"\card2.mp4", [("Paso 3", 44, 400, CY, FONT), ("De vuelta en 3D Slicer: la guía quirúrgica", 66, 470, WHITE, FONT)], 2.5)
card(T + r"\cardEnd.mp4", [("Resultado", 60, 250, WHITE, FONT),
                             ("Mandíbula segmentada:  38.8 mL  ·  93 × 77 × 52 mm", 38, 380, CY, FONT),
                             ("Malla optimizada en Blender:  270 020  →  92 972 triángulos", 38, 450, CY, FONT),
                             ("Guía dentosoportada con manguito Ø2.2 mm para mini-implante", 38, 520, CY, FONT),
                             ("Archivos: guia_quirurgica_ortodoncia.stl  ·  mandibula_blender.stl  ·  escena .mrb", 28, 620, GR, FONTR),
                             ("Diseño demostrativo con datos de muestra. No apto para uso clínico sin validación.", 28, 700, GR, FONTR)], 6)
for n, s in (("A", "1_slicer_modelado.mp4"), ("B", "2_blender_procesado.mp4"), ("C", "3_slicer_guia.mp4")):
    clip_full(D + "\\" + s, T + "\\full_%s.mp4" % n)

lst = [T + r"\card0.mp4", T + r"\full_A.mp4", T + r"\card1.mp4", T + r"\full_B.mp4", T + r"\card2.mp4", T + r"\full_C.mp4", T + r"\cardEnd.mp4"]
open(T + r"\list_full.txt", "w").write("".join("file '%s'\n" % p.replace("\\", "/") for p in lst))
run(["-f", "concat", "-safe", "0", "-i", T + r"\list_full.txt", "-c", "copy", D + r"\VIDEO_COMPLETO_mandibula_guia.mp4"])
print("FULL OK", flush=True)

# resumen
card(T + r"\scard0.mp4", [("Mandíbula 3D → guía quirúrgica", 78, 380, WHITE, FONT),
                            ("para ortodoncia", 78, 475, WHITE, FONT),
                            ("3D Slicer  ·  Blender  ·  3D Slicer", 40, 610, CY, FONT)], 3)
clip_sum(D + r"\1_slicer_modelado.mp4", T + r"\sum_A.mp4", "1 · 3D Slicer: segmentamos la mandíbula desde un CBCT", "Umbral de hueso + crecimiento desde semillas + suavizado   (video x4)")
clip_sum(D + r"\2_blender_procesado.mp4", T + r"\sum_B.mp4", "2 · Blender: limpiamos y mejoramos la malla", "Fragmentos, huecos, suavizado Laplaciano y optimización: 270 k → 93 k triángulos   (video x4)")
clip_sum(D + r"\3_slicer_guia.mp4", T + r"\sum_C.mp4", "3 · 3D Slicer: diseñamos la guía quirúrgica", "Cáscara dentosoportada + manguito Ø2.2 mm para mini-implante (TAD)   (video x4)")
card(T + r"\scardEnd.mp4", [("Del CBCT a una guía lista para imprimir en 3D", 56, 400, WHITE, FONT),
                              ("Flujo reproducible con software abierto: 3D Slicer + Blender", 34, 500, CY, FONT),
                              ("Diseño demostrativo con datos de muestra", 28, 600, GR, FONTR)], 4)
lst = [T + r"\scard0.mp4", T + r"\sum_A.mp4", T + r"\sum_B.mp4", T + r"\sum_C.mp4", T + r"\scardEnd.mp4"]
open(T + r"\list_sum.txt", "w").write("".join("file '%s'\n" % p.replace("\\", "/") for p in lst))
run(["-f", "concat", "-safe", "0", "-i", T + r"\list_sum.txt", "-c", "copy", D + r"\VIDEO_RESUMEN_redes_mandibula_guia.mp4"])
print("SUM OK", flush=True)
