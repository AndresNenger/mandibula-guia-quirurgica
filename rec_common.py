import ctypes, subprocess, os, time
FFMPEG = r"C:\Users\Laboratorio\Downloads\femur_vh\deps_vid\imageio_ffmpeg\binaries\ffmpeg-win-x86_64-v7.1.exe"
D = r"C:\Users\Laboratorio\Downloads\mandibula_guia"
FPS = 30
class RECT(ctypes.Structure):
    _fields_ = [("l", ctypes.c_long), ("t", ctypes.c_long), ("r", ctypes.c_long), ("b", ctypes.c_long)]
class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]
def start_rec(hwnd, out):
    u = ctypes.windll.user32
    u.ShowWindow(hwnd, 3); u.SetForegroundWindow(hwnd)
    return u
def region(hwnd):
    u = ctypes.windll.user32
    rc = RECT(); u.GetClientRect(hwnd, ctypes.byref(rc))
    pt = POINT(0, 0); u.ClientToScreen(hwnd, ctypes.byref(pt))
    return pt.x, pt.y, (rc.r - rc.l)//2*2, (rc.b - rc.t)//2*2
def launch_ffmpeg(hwnd, out):
    x, y, w, h = region(hwnd)
    print("REGION", x, y, w, h, flush=True)
    cmd = [FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-f", "gdigrab", "-framerate", str(FPS),
           "-draw_mouse", "0", "-offset_x", str(x), "-offset_y", str(y), "-video_size", "%dx%d" % (w, h),
           "-i", "desktop", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", out]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    time.sleep(1.5)
    if p.poll() is not None:
        print("FFMPEG_FAIL", p.stderr.read().decode(errors="ignore")[:400], flush=True)
        return None
    print("FFMPEG_OK", flush=True)
    return p
def stop_ffmpeg(p):
    try:
        p.stdin.write(b"q"); p.stdin.flush(); p.wait(timeout=60)
    except Exception as e:
        print("ffmpeg cierre", e, flush=True); p.kill()
