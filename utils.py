import os, logging, re
from datetime import datetime

def setup_logger():
    logs_dir = "logs"
    os.makedirs(logs_dir, exist_ok=True)
    log_filename = os.path.join(logs_dir, f"log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
    logging.basicConfig(
        level=logging.DEBUG,
        format='[%(asctime)s] %(message)s',
        datefmt='%H:%M:%S',
        handlers=[
            logging.FileHandler(log_filename, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

def limpiar_nombre(texto):
    texto_limpio = re.sub(r'[^A-Za-z0-9_\- ]+', '_', texto)
    return texto_limpio.strip().replace(' ', '_')[:30]

def a_mmss(segundos):
    minutos = int(segundos // 60)
    segs = int(segundos % 60)
    return f"{minutos:02d}:{segs:02d}"

def tiempo_a_segundos(linea):
    mm, ss = linea.split(" ", 1)[0].split(":")
    return int(mm) * 60 + int(ss)

def asegurar_directorio(ruta):
    os.makedirs(ruta, exist_ok=True)

def formatear_resultados_cronologicamente(lista_lineas):
    return sorted(lista_lineas, key=tiempo_a_segundos)
