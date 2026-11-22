
import os, sys
import cv2
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
from video_io import obtener_capitulos, extraer_frame, recortar, recortar_imagen
from ui import seleccionar_carpeta
from interfaz_alias import lanzar_interfaz

log = setup_logger()
lock_ui = threading.Lock()

# === MENÚ DE JUEGO ===
config_dir = "config"
juegos_disponibles = [
    d for d in os.listdir(config_dir)
    if os.path.isdir(os.path.join(config_dir, d))
]

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
def identificar_personaje(
    coords, idx, lado, frame_path, nombre_base, start_time,
    video_path, recorte_precalculado=None,
    reconocimiento_ya_realizado=False
):
    recorte = (
        recorte_precalculado
        if recorte_precalculado is not None
        else recortar(frame_path, coords)
    )

    ruta_debug_img = os.path.join(
        CARPETA_DEBUG, f"{idx}_{lado}.png"
    )
    asegurar_directorio(CARPETA_DEBUG)

    if recorte is not None:
        cv2.imwrite(ruta_debug_img, recorte)

    if reconocimiento_ya_realizado:
        nombre, score = None, 0.0
    else:
        nombre, score = identificador.identificar(recorte)

    log.info(
        "[CAPÍTULO %s][MANUAL] %s: %s (score=%.3f)",
        idx, lado, nombre if nombre else "DESCONOCIDO", score
    )

    if nombre:
        return nombre

    with lock_ui:
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

    if (
        isinstance(alias_confirmado, str)
        and alias_confirmado.startswith("__CAPITULO_ESPECIAL__:")
    ):
        return alias_confirmado

    if alias_confirmado and alias_confirmado not in (
        "DESCONOCIDO", "__OMITIR__"
    ):
        if guardar:
            destino_dir = os.path.join(CARPETA_REF, alias_confirmado)
            asegurar_directorio(destino_dir)

            destino_path = os.path.join(
                destino_dir,
                f"{limpiar_nombre(nombre_base)}_{idx}_{lado}.png"
            )

            recorte_guardar = cv2.imread(ruta_debug_img)

            if recorte_guardar is None:
                recorte_guardar = recorte

            if (
                recorte_guardar is not None
                and cv2.imwrite(destino_path, recorte_guardar)
            ):
                identificador.agregar_referencia(
                    alias_confirmado, recorte_guardar
                )

        log.info(
            "[CAPÍTULO %s][MANUAL] %s confirmado como %s",
            idx, lado, alias_confirmado
        )
        return alias_confirmado

    log.info(
        "[CAPÍTULO %s][MANUAL] %s queda como DESCONOCIDO",
        idx, lado
    )
    return "DESCONOCIDO"


# === PROCESAR UN CAPÍTULO COMPLETO ===
def procesar_capitulo(idx, start_time, video_path, nombre_base):
    mmss = a_mmss(start_time)
    t_captura = start_time + OFFSET_SEGUNDOS
    frame_path = os.path.join(
        CARPETA_FRAMES, f"frame_{idx}.png"
    )

    if not extraer_frame(video_path, t_captura, frame_path, log):
        return None

    if modo_personajes == "4p":
        nombre_inf_izq = identificar_personaje(
            COORDENADAS["izquierda_inferior"], idx, "izq_inf",
            frame_path, nombre_base, t_captura, video_path
        )

        if (
            isinstance(nombre_inf_izq, str)
            and nombre_inf_izq.startswith("__CAPITULO_ESPECIAL__:")
        ):
            return f"{mmss} {nombre_inf_izq.split(':', 1)[1]}"

        nombre_sup_izq = identificar_personaje(
            COORDENADAS["izquierda_superior"], idx, "izq_sup",
            frame_path, nombre_base, t_captura, video_path
        )

        nombre_inf_der = identificar_personaje(
            COORDENADAS["derecha_inferior"], idx, "der_inf",
            frame_path, nombre_base, t_captura, video_path
        )

        nombre_sup_der = identificar_personaje(
            COORDENADAS["derecha_superior"], idx, "der_sup",
            frame_path, nombre_base, t_captura, video_path
        )

        return (
            f"{mmss} {nombre_sup_izq} / {nombre_inf_izq} Vs. "
            f"{nombre_sup_der} / {nombre_inf_der}"
        )

    nombre_izq = identificar_personaje(
        COORDENADAS["izquierda"], idx, "izquierda",
        frame_path, nombre_base, t_captura, video_path
    )

    if (
        isinstance(nombre_izq, str)
        and nombre_izq.startswith("__CAPITULO_ESPECIAL__:")
    ):
        return f"{mmss} {nombre_izq.split(':', 1)[1]}"

    nombre_der = identificar_personaje(
        COORDENADAS["derecha"], idx, "derecha",
        frame_path, nombre_base, t_captura, video_path
    )

    if (
        isinstance(nombre_der, str)
        and nombre_der.startswith("__CAPITULO_ESPECIAL__:")
    ):
        return f"{mmss} {nombre_der.split(':', 1)[1]}"

    return f"{mmss} {nombre_izq} Vs. {nombre_der}"


# === RECONOCIMIENTO AUTOMÁTICO DE UN CAPÍTULO ===
def procesar_capitulo_automatico(
    idx, start_time, video_path, nombre_base
):
    mmss = a_mmss(start_time)
    t_captura = start_time + OFFSET_SEGUNDOS
    frame_path = os.path.join(
        CARPETA_FRAMES, f"frame_{idx}.png"
    )

    log.info(
        "[CAPÍTULO %s][AUTO] Iniciando reconocimiento en %s",
        idx, mmss
    )

    if not extraer_frame(video_path, t_captura, frame_path, log):
        log.error(
            "[CAPÍTULO %s][AUTO] No se pudo extraer el fotograma",
            idx
        )
        return None

    frame = cv2.imread(frame_path)

    if frame is None:
        log.error(
            "[CAPÍTULO %s][AUTO] No se pudo leer el fotograma: %s",
            idx, frame_path
        )
        return None

    if modo_personajes == "4p":
        claves = [
            ("izquierda_inferior", "izq_inf"),
            ("izquierda_superior", "izq_sup"),
            ("derecha_inferior", "der_inf"),
            ("derecha_superior", "der_sup"),
        ]
    else:
        claves = [
            ("izquierda", "izquierda"),
            ("derecha", "derecha"),
        ]

    nombres = {}

    for clave, lado in claves:
        recorte = recortar_imagen(frame, COORDENADAS[clave])
        nombre, score = identificador.identificar(recorte)

        aceptado = bool(
            nombre and score >= identificador.umbral
        )

        if aceptado:
            nombres[clave] = nombre
            estado = nombre
        else:
            estado = "DESCONOCIDO"

        log.info(
            "[CAPÍTULO %s][AUTO] %s: %s (score=%.3f, umbral=%.2f)",
            idx, lado, estado, score, identificador.umbral
        )

    if len(nombres) == len(claves):
        log.info(
            "[CAPÍTULO %s][AUTO] Todas las posiciones reconocidas",
            idx
        )

        if modo_personajes == "4p":
            return (
                f"{mmss} {nombres['izquierda_superior']} / "
                f"{nombres['izquierda_inferior']} Vs. "
                f"{nombres['derecha_superior']} / "
                f"{nombres['derecha_inferior']}"
            )

        return (
            f"{mmss} {nombres['izquierda']} Vs. "
            f"{nombres['derecha']}"
        )

    pendientes = [
        lado
        for clave, lado in claves
        if clave not in nombres
    ]

    log.info(
        "[CAPÍTULO %s][AUTO] Pendiente de revisión manual: %s",
        idx, ", ".join(pendientes)
    )

    return (
        "manual", idx, start_time, frame_path,
        nombre_base, video_path, nombres
    )


# === PROCESAR VÍDEO CON HILOS ===
def procesar_video(video_path):
    asegurar_directorio(CARPETA_FRAMES)

    capitulos = obtener_capitulos(video_path, log)

    if not capitulos:
        return []

    nombre_base = os.path.splitext(
        os.path.basename(video_path)
    )[0]

    resultados = []
    pendientes_manuales = []

    # --- Procesado automático en paralelo ---
    workers_por_defecto = min(4, os.cpu_count() or 1)

    try:
        max_workers = max(
            1,
            int(os.environ.get(
                "TKCAP_MAX_WORKERS", workers_por_defecto
            ))
        )
    except ValueError:
        log.warning(
            "TKCAP_MAX_WORKERS no es válido; se usarán %s procesos.",
            workers_por_defecto
        )
        max_workers = workers_por_defecto

    log.info(
        "Procesamiento automático: %s capítulos, %s trabajadores",
        len(capitulos), max_workers
    )

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(
                procesar_capitulo_automatico,
                idx, st, video_path, nombre_base
            )
            for idx, st in enumerate(capitulos, start=1)
        ]

        for f in futures:
            res = f.result()

            if res:
                if isinstance(res, tuple) and res[0] == "manual":
                    pendientes_manuales.append(res[1:])
                else:
                    resultados.append(res)

    log.info(
        "Reconocimiento automático terminado. "
        "%s capítulos pendientes de revisión manual.",
        len(pendientes_manuales)
    )

    # --- BLOQUE DE REVISIÓN MANUAL ---
    for (
        idx, start_time, frame_path, nombre_base,
        video_path, nombres_previos
    ) in pendientes_manuales:

        mmss = a_mmss(start_time)

        log.info(
            "[CAPÍTULO %s][MANUAL] Comenzando revisión de %s",
            idx, mmss
        )

        frame = cv2.imread(frame_path)

        if frame is None:
            log.error(
                "[CAPÍTULO %s][MANUAL] No se pudo leer el fotograma: %s",
                idx, frame_path
            )
            continue

        if modo_personajes == "4p":
            claves = [
                ("izquierda_inferior", "izq_inf"),
                ("izquierda_superior", "izq_sup"),
                ("derecha_inferior", "der_inf"),
                ("derecha_superior", "der_sup"),
            ]

            nombres = dict(nombres_previos)
            fallos_ya_comprobados = (
                {clave for clave, _ in claves} - set(nombres)
            )
            especial = None

            while True:
                reiniciar = False

                for clave, lado in claves:
                    if clave in nombres:
                        log.info(
                            "[CAPÍTULO %s][MANUAL] %s ya reconocido "
                            "automáticamente como %s; se conserva",
                            idx, lado, nombres[clave]
                        )
                        continue

                    recorte = recortar_imagen(
                        frame, COORDENADAS[clave]
                    )

                    if clave not in fallos_ya_comprobados:
                        nombre_auto, score_auto = (
                            identificador.identificar(recorte)
                        )

                        log.info(
                            "[CAPÍTULO %s][MANUAL] "
                            "Nueva comprobación %s: %s (score=%.3f)",
                            idx, lado,
                            nombre_auto or "DESCONOCIDO",
                            score_auto
                        )

                        if (
                            nombre_auto
                            and score_auto >= identificador.umbral
                        ):
                            nombres[clave] = nombre_auto
                            continue

                    log.info(
                        "[CAPÍTULO %s][MANUAL] Abriendo interfaz "
                        "para %s",
                        idx, lado
                    )

                    mtime_antes = (
                        os.path.getmtime(frame_path)
                        if os.path.exists(frame_path) else None
                    )

                    nombre = identificar_personaje(
                        COORDENADAS[clave], idx, lado,
                        frame_path, nombre_base,
                        start_time + OFFSET_SEGUNDOS,
                        video_path,
                        recorte_precalculado=recorte,
                        reconocimiento_ya_realizado=True
                    )

                    mtime_despues = (
                        os.path.getmtime(frame_path)
                        if os.path.exists(frame_path) else None
                    )

                    if (
                        isinstance(nombre, str)
                        and nombre.startswith("__CAPITULO_ESPECIAL__:")
                    ):
                        especial = nombre.split(":", 1)[1]
                        break

                    if (
                        mtime_antes is not None
                        and mtime_despues != mtime_antes
                    ):
                        log.info(
                            "[CAPÍTULO %s][MANUAL] "
                            "El instante del fotograma ha cambiado. "
                            "Se recalcularán las posiciones.",
                            idx
                        )

                        frame_actualizado = cv2.imread(frame_path)

                        if frame_actualizado is not None:
                            frame = frame_actualizado

                        nombres = {clave: nombre}
                        fallos_ya_comprobados = set()
                        reiniciar = True
                        break

                    nombres[clave] = nombre

                if especial is not None or not reiniciar:
                    break

            if especial is not None:
                resultados.append(f"{mmss} {especial}")
            else:
                resultado = (
                    f"{mmss} "
                    f"{nombres.get('izquierda_superior', 'DESCONOCIDO')} / "
                    f"{nombres.get('izquierda_inferior', 'DESCONOCIDO')} Vs. "
                    f"{nombres.get('derecha_superior', 'DESCONOCIDO')} / "
                    f"{nombres.get('derecha_inferior', 'DESCONOCIDO')}"
                )
                resultados.append(resultado)

                log.info(
                    "[CAPÍTULO %s][MANUAL] Resultado final: %s",
                    idx, resultado
                )

        else:
            # --- MODO 2P ---
            claves = ("izquierda", "derecha")
            nombres = dict(nombres_previos)
            fallos_ya_comprobados = set(claves) - set(nombres)
            especial = None

            while True:
                reiniciar = False

                for clave in claves:
                    if clave in nombres:
                        log.info(
                            "[CAPÍTULO %s][MANUAL] %s ya reconocido "
                            "automáticamente como %s; se conserva",
                            idx, clave, nombres[clave]
                        )
                        continue

                    recorte = recortar_imagen(
                        frame, COORDENADAS[clave]
                    )

                    if clave not in fallos_ya_comprobados:
                        nombre_auto, score_auto = (
                            identificador.identificar(recorte)
                        )

                        log.info(
                            "[CAPÍTULO %s][MANUAL] "
                            "Nueva comprobación %s: %s (score=%.3f)",
                            idx, clave,
                            nombre_auto or "DESCONOCIDO",
                            score_auto
                        )

                        if (
                            nombre_auto
                            and score_auto >= identificador.umbral
                        ):
                            nombres[clave] = nombre_auto
                            continue

                    log.info(
                        "[CAPÍTULO %s][MANUAL] Abriendo interfaz "
                        "para %s",
                        idx, clave
                    )

                    mtime_antes = (
                        os.path.getmtime(frame_path)
                        if os.path.exists(frame_path) else None
                    )

                    nombre = identificar_personaje(
                        COORDENADAS[clave], idx, clave,
                        frame_path, nombre_base,
                        start_time + OFFSET_SEGUNDOS,
                        video_path,
                        recorte_precalculado=recorte,
                        reconocimiento_ya_realizado=True
                    )

                    mtime_despues = (
                        os.path.getmtime(frame_path)
                        if os.path.exists(frame_path) else None
                    )

                    if (
                        isinstance(nombre, str)
                        and nombre.startswith("__CAPITULO_ESPECIAL__:")
                    ):
                        especial = nombre.split(":", 1)[1]
                        break

                    if (
                        mtime_antes is not None
                        and mtime_despues != mtime_antes
                    ):
                        log.info(
                            "[CAPÍTULO %s][MANUAL] "
                            "El instante del fotograma ha cambiado. "
                            "Se recalcularán las posiciones.",
                            idx
                        )

                        frame_actualizado = cv2.imread(frame_path)

                        if frame_actualizado is not None:
                            frame = frame_actualizado

                        nombres = {clave: nombre}
                        fallos_ya_comprobados = set()
                        reiniciar = True
                        break

                    nombres[clave] = nombre

                if especial is not None or not reiniciar:
                    break

            if especial is not None:
                resultados.append(f"{mmss} {especial}")
            else:
                resultado = (
                    f"{mmss} "
                    f"{nombres.get('izquierda', 'DESCONOCIDO')} Vs. "
                    f"{nombres.get('derecha', 'DESCONOCIDO')}"
                )
                resultados.append(resultado)

                log.info(
                    "[CAPÍTULO %s][MANUAL] Resultado final: %s",
                    idx, resultado
                )

    # --- ORDEN CRONOLÓGICO FINAL ---
    resultados = formatear_resultados_cronologicamente(resultados)

    log.info(
        "Vídeo terminado. Resultados obtenidos: %s",
        len(resultados)
    )

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
        nombre_base = os.path.splitext(
            os.path.basename(video_path)
        )[0]

        log.info(f"=== Comenzando vídeo: {nombre_base} ===")

        salida = procesar_video(video_path)

        if salida:
            ruta_salida = os.path.join(
                CARPETA_RESULTADOS,
                f"{limpiar_nombre(nombre_base)}_resultados.txt"
            )

            with open(ruta_salida, "w", encoding="utf-8") as out:
                out.write("\n".join(salida))

            log.info(
                f"[OK] Resultados guardados en '{ruta_salida}'"
            )
        else:
            log.warning(
                f"No se generaron resultados para {nombre_base}"
            )
