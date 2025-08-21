import subprocess, cv2, os, json

def obtener_capitulos(video_path, log):
    comando = ["ffprobe", "-v", "error", "-print_format", "json", "-show_chapters", video_path]
    resultado = subprocess.run(comando, capture_output=True, text=True)
    if resultado.returncode != 0 or not resultado.stdout.strip():
        log.error("ffprobe no devolvió datos.")
        return []
    data = json.loads(resultado.stdout)
    return [float(c["start_time"]) for c in data.get("chapters", [])]

def extraer_frame(video_path, tiempo, salida, log=None):
    if log:  # Solo si tenemos logger
        log.debug(f"Extrayendo frame en {tiempo:.2f}s -> {salida}")
    comando = [
        "ffmpeg", "-y",
        "-ss", str(tiempo),
        "-i", video_path,
        "-vframes", "1",
        salida
    ]
    subprocess.run(comando, capture_output=True, text=True)
    return os.path.exists(salida)

def recortar(img_path, coords):
    img = cv2.imread(img_path)
    if img is None:
        return None
    x1, x2, y1, y2 = coords
    return img[y1:y2, x1:x2]
