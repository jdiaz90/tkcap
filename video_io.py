import json
import os
import subprocess

import cv2


def obtener_capitulos(video_path, log):
    comando = [
        "ffprobe", "-v", "error", "-print_format", "json",
        "-show_chapters", video_path,
    ]
    resultado = subprocess.run(comando, capture_output=True, text=True)
    if resultado.returncode != 0 or not resultado.stdout.strip():
        log.error("ffprobe no devolvió datos.")
        return []

    try:
        data = json.loads(resultado.stdout)
    except json.JSONDecodeError as exc:
        log.error("ffprobe devolvió JSON no válido: %s", exc)
        return []

    return [float(c["start_time"]) for c in data.get("chapters", [])]


def extraer_frame(video_path, tiempo, salida, log=None):
    if log:
        log.debug("Extrayendo frame en %.2fs -> %s", tiempo, salida)

    comando = [
        "ffmpeg", "-y", "-ss", str(tiempo), "-i", video_path,
        "-vframes", "1", salida,
    ]
    resultado = subprocess.run(comando, capture_output=True, text=True)
    if resultado.returncode != 0:
        if log:
            log.error("FFmpeg no pudo extraer el fotograma: %s", resultado.stderr.strip())
        return False
    return os.path.isfile(salida)


def recortar_imagen(img, coords):
    """Recorta una región de una imagen BGR ya cargada en memoria."""
    if img is None:
        return None

    x1, x2, y1, y2 = map(int, coords)
    alto, ancho = img.shape[:2]
    x1, x2 = max(0, x1), min(ancho, x2)
    y1, y2 = max(0, y1), min(alto, y2)
    if x2 <= x1 or y2 <= y1:
        return None

    return img[y1:y2, x1:x2]


def recortar(img_path, coords):
    """Compatibilidad con llamadas antiguas que reciben la ruta del frame."""
    img = cv2.imread(img_path)
    return recortar_imagen(img, coords)
