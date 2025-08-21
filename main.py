import os, sys
from concurrent.futures import ThreadPoolExecutor
import threading
from utils import (
    setup_logger,
    limpiar_nombre,
    a_mmss,
    asegurar_directorio,
    formatear_resultados_cronologicamente
)
from config_loader import cargar_config
from identificador import IdentificadorPersonaje
from video_io import obtener_capitulos, extraer_frame, recortar
from ui import seleccionar_carpeta
from interfaz_alias import lanzar_interfaz

log = setup_logger()
lock_ui = threading.Lock()  # Solo un hilo abre interfaz a la vez

# === MENÚ DE JUEGO ===
config_dir = "config"
juegos_disponibles = [d for d in os.listdir(config_dir) if os.path.isdir(os.path.join(config_dir, d))]
if not juegos_disponibles:
    log.error(f"No hay perfiles en '{config_dir}'")
    sys.exit(1)

print("=== Selecciona juego ===")
for idx, nombre in enumerate(juegos_disponibles, 1):
    print(f"{idx}. {nombre}")

opcion = input("Número de juego: ").strip()
try:
    JUEGO = juegos_disponibles[int(opcion) - 1]
except (ValueError, IndexError):
    log.error("Selección inválida.")
    sys.exit(1)

# === CARGA DE CONFIGURACIÓN Y MODO ===
RUTA_PERFIL = os.path.join(config_dir, JUEGO)
CFG, modo_personajes = cargar_config(RUTA_PERFIL, log)
COORDENADAS = CFG["coordenadas"]

CARPETA_FRAMES = CFG["carpeta_frames"]
CARPETA_DEBUG = CFG["carpeta_debug"]
OFFSET_SEGUNDOS = float(CFG["offset_segundos"])
CARPETA_REF = os.path.join(RUTA_PERFIL, "personajes_ref")

identificador = IdentificadorPersonaje(CARPETA_REF, umbral=0.75)

# === SELECCIÓN DE CARPETAS ===
CARPETA_VIDEOS = seleccionar_carpeta("Selecciona la carpeta de vídeos")
CARPETA_RESULTADOS = seleccionar_carpeta("Selecciona la carpeta de resultados")
if not CARPETA_VIDEOS or not CARPETA_RESULTADOS:
    log.error("Carpetas no seleccionadas.")
    sys.exit(1)

# === IDENTIFICAR PERSONAJE ===
def identificar_personaje(coords, idx, lado, frame_path, nombre_base, start_time, video_path):
    recorte = recortar(frame_path, coords)
    ruta_debug_img = os.path.join(CARPETA_DEBUG, f"{idx}_{lado}.png")
    asegurar_directorio(CARPETA_DEBUG)
    if recorte is not None:
        import cv2
        cv2.imwrite(ruta_debug_img, recorte)

    nombre, score = identificador.identificar(recorte)
    log.info(f"{lado}: {nombre if nombre else 'DESCONOCIDO'} (score={score:.3f})")

    if nombre:
        return nombre  # flujo automático normal

    with lock_ui:  # Solo un hilo puede abrir interfaz
        alias_confirmado, guardar = lanzar_interfaz(
            "Sin coincidencia automática",
            "?",
            frame_path,
            ruta_debug_img,
            video_nombre=nombre_base,
            capitulo_idx=idx,
            ruta_perfil=RUTA_PERFIL,
            start_time=start_time,
            video_path=video_path,
            coords=coords,
            identificador=identificador
        )

    if isinstance(alias_confirmado, str) and alias_confirmado.startswith("__CAPITULO_ESPECIAL__:"):
        return alias_confirmado

    if alias_confirmado and alias_confirmado not in ("DESCONOCIDO", "__OMITIR__"):
        if guardar:
            import cv2
            destino_dir = os.path.join(CARPETA_REF, alias_confirmado)
            asegurar_directorio(destino_dir)
            destino_path = os.path.join(
                destino_dir,
                f"{limpiar_nombre(nombre_base)}_{idx}_{lado}.png"
            )
            cv2.imwrite(destino_path, recorte)
            identificador.cargar_referencias()
        return alias_confirmado

    return "DESCONOCIDO"

# === PROCESAR UN CAPÍTULO COMPLETO ===
def procesar_capitulo(idx, start_time, video_path, nombre_base):
    mmss = a_mmss(start_time)  # Marca real del capítulo
    t_captura = start_time + OFFSET_SEGUNDOS
    frame_path = os.path.join(CARPETA_FRAMES, f"frame_{idx}.png")

    if not extraer_frame(video_path, t_captura, frame_path, log):
        return None

    if modo_personajes == "4p":
        nombre_inf_izq = identificar_personaje(
            COORDENADAS["izquierda_inferior"], idx, "izq_inf",
            frame_path, nombre_base, start_time + OFFSET_SEGUNDOS, video_path
        )
        if isinstance(nombre_inf_izq, str) and nombre_inf_izq.startswith("__CAPITULO_ESPECIAL__:"):
            return f"{mmss} {nombre_inf_izq.split(':', 1)[1]}"

        nombre_sup_izq = identificar_personaje(
            COORDENADAS["izquierda_superior"], idx, "izq_sup",
            frame_path, nombre_base, start_time + OFFSET_SEGUNDOS, video_path
        )
        nombre_inf_der = identificar_personaje(
            COORDENADAS["derecha_inferior"], idx, "der_inf",
            frame_path, nombre_base, start_time + OFFSET_SEGUNDOS, video_path
        )
        nombre_sup_der = identificar_personaje(
            COORDENADAS["derecha_superior"], idx, "der_sup",
            frame_path, nombre_base, start_time + OFFSET_SEGUNDOS, video_path
        )
        return f"{mmss} {nombre_sup_izq} / {nombre_inf_izq} Vs. {nombre_sup_der} / {nombre_inf_der}"

    else:
        nombre_izq = identificar_personaje(
            COORDENADAS["izquierda"], idx, "izquierda",
            frame_path, nombre_base, start_time + OFFSET_SEGUNDOS, video_path
        )
        if isinstance(nombre_izq, str) and nombre_izq.startswith("__CAPITULO_ESPECIAL__:"):
            return f"{mmss} {nombre_izq.split(':', 1)[1]}"

        nombre_der = identificar_personaje(
            COORDENADAS["derecha"], idx, "derecha",
            frame_path, nombre_base, start_time + OFFSET_SEGUNDOS, video_path
        )
        if isinstance(nombre_der, str) and nombre_der.startswith("__CAPITULO_ESPECIAL__:"):
            return f"{mmss} {nombre_der.split(':', 1)[1]}"

        return f"{mmss} {nombre_izq} Vs. {nombre_der}"

def procesar_capitulo_automatico(idx, start_time, video_path, nombre_base):
    mmss = a_mmss(start_time)
    t_captura = start_time + OFFSET_SEGUNDOS
    frame_path = os.path.join(CARPETA_FRAMES, f"frame_{idx}.png")

    if not extraer_frame(video_path, t_captura, frame_path, log):
        return None

    if modo_personajes == "4p":
        todo_ok = True
        nombres = []
        for clave in ["izquierda_inferior", "izquierda_superior", "derecha_inferior", "derecha_superior"]:
            recorte = recortar(frame_path, COORDENADAS[clave])
            nombre, score = identificador.identificar(recorte)
            if not nombre or score < 0.75:
                todo_ok = False
                break
            nombres.append(nombre)
        if todo_ok:
            return f"{mmss} {nombres[1]} / {nombres[0]} Vs. {nombres[3]} / {nombres[2]}"
    else:
        recorte_izq = recortar(frame_path, COORDENADAS["izquierda"])
        nombre_izq, score_izq = identificador.identificar(recorte_izq)
        recorte_der = recortar(frame_path, COORDENADAS["derecha"])
        nombre_der, score_der = identificador.identificar(recorte_der)
        if nombre_izq and score_izq >= 0.75 and nombre_der and score_der >= 0.75:
            return f"{mmss} {nombre_izq} Vs. {nombre_der}"

    # Si no pudo ser automático, devolvemos TODO lo necesario para el manual
    return ("manual", idx, start_time, frame_path, nombre_base, video_path)

# === PROCESAR VÍDEO CON HILOS ===
def procesar_video(video_path):
    asegurar_directorio(CARPETA_FRAMES)
    capitulos = obtener_capitulos(video_path, log)
    if not capitulos:
        return []

    nombre_base = os.path.splitext(os.path.basename(video_path))[0]
    resultados = []
    pendientes_manuales = []

    # --- Procesado automático en paralelo ---
    with ThreadPoolExecutor(max_workers=os.cpu_count() or 4) as executor:
        futures = [
            executor.submit(procesar_capitulo_automatico, idx, st, video_path, nombre_base)
            for idx, st in enumerate(capitulos, start=1)
        ]
        for f in futures:
            res = f.result()
            if res:
                if isinstance(res, tuple) and res[0] == "manual":
                    # Guardamos datos para el manual: idx, start_time, frame_path, nombre_base, video_path
                    pendientes_manuales.append(res[1:])
                else:
                    resultados.append(res)

    # --- Bloque de revisión manual (secuencial) ---
    for idx, start_time, frame_path, nombre_base, video_path in pendientes_manuales:
        mmss = a_mmss(start_time)

        if modo_personajes == "4p":
            nombre_inf_izq = identificar_personaje(
                COORDENADAS["izquierda_inferior"], idx, "izq_inf",
                frame_path, nombre_base, start_time + OFFSET_SEGUNDOS, video_path
            )
            if isinstance(nombre_inf_izq, str) and nombre_inf_izq.startswith("__CAPITULO_ESPECIAL__:"):
                resultados.append(f"{mmss} {nombre_inf_izq.split(':', 1)[1]}")
                continue

            nombre_sup_izq = identificar_personaje(
                COORDENADAS["izquierda_superior"], idx, "izq_sup",
                frame_path, nombre_base, start_time + OFFSET_SEGUNDOS, video_path
            )
            nombre_inf_der = identificar_personaje(
                COORDENADAS["derecha_inferior"], idx, "der_inf",
                frame_path, nombre_base, start_time + OFFSET_SEGUNDOS, video_path
            )
            nombre_sup_der = identificar_personaje(
                COORDENADAS["derecha_superior"], idx, "der_sup",
                frame_path, nombre_base, start_time + OFFSET_SEGUNDOS, video_path
            )

            resultados.append(f"{mmss} {nombre_sup_izq} / {nombre_inf_izq} Vs. {nombre_sup_der} / {nombre_inf_der}")

        else:  # modo 2p
            nombre_izq = identificar_personaje(
                COORDENADAS["izquierda"], idx, "izquierda",
                frame_path, nombre_base, start_time + OFFSET_SEGUNDOS, video_path
            )
            if isinstance(nombre_izq, str) and nombre_izq.startswith("__CAPITULO_ESPECIAL__:"):
                resultados.append(f"{mmss} {nombre_izq.split(':', 1)[1]}")
                continue

            nombre_der = identificar_personaje(
                COORDENADAS["derecha"], idx, "derecha",
                frame_path, nombre_base, start_time + OFFSET_SEGUNDOS, video_path
            )
            if isinstance(nombre_der, str) and nombre_der.startswith("__CAPITULO_ESPECIAL__:"):
                resultados.append(f"{mmss} {nombre_der.split(':', 1)[1]}")
                continue

            resultados.append(f"{mmss} {nombre_izq} Vs. {nombre_der}")

    # --- Orden cronológico final ---
    resultados = formatear_resultados_cronologicamente(resultados)
    return resultados

# === BUCLE PRINCIPAL ===
if __name__ == "__main__":
    video_files = [
        os.path.join(CARPETA_VIDEOS, v)
        for v in sorted(os.listdir(CARPETA_VIDEOS))
        if v.lower().endswith((".mp4", ".mkv", ".avi", ".mov"))
    ]
    if not video_files:
        log.error("No se han encontrado vídeos.")
        sys.exit(1)

    for video_path in video_files:
        nombre_base = os.path.splitext(os.path.basename(video_path))[0]
        log.info(f"=== Comenzando vídeo: {nombre_base} ===")
        salida = procesar_video(video_path)
        if salida:
            ruta_salida = os.path.join(CARPETA_RESULTADOS, f"{limpiar_nombre(nombre_base)}_resultados.txt")
            with open(ruta_salida, "w", encoding="utf-8") as out:
                out.write("\n".join(salida))
            log.info(f"[OK] Resultados guardados en '{ruta_salida}'")
        else:
            log.warning(f"No se generaron resultados para {nombre_base}")
