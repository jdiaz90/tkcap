from pathlib import Path

path = Path(__file__).with_name("main.py")
source = path.read_text(encoding="utf-8")

old_log = '    log.info(f"{lado}: {nombre if nombre else \'DESCONOCIDO\'} (score={score:.3f})")'
new_log = """    log.info(
        f"[CAPÍTULO {idx}][MANUAL] {lado}: "
        f"{nombre if nombre else 'DESCONOCIDO'} (score={score:.3f})"
    )"""
if old_log not in source:
    raise SystemExit("No encuentro la línea de registro manual esperada; no se ha modificado main.py.")
source = source.replace(old_log, new_log, 1)

start = source.find("def procesar_capitulo_automatico(")
end = source.find("# === PROCESAR VÍDEO CON HILOS ===", start)
if start < 0 or end < 0:
    raise SystemExit("No encuentro los límites de procesar_capitulo_automatico; no se ha modificado main.py.")

replacement = """def procesar_capitulo_automatico(idx, start_time, video_path, nombre_base):
    mmss = a_mmss(start_time)
    t_captura = start_time + OFFSET_SEGUNDOS
    frame_path = os.path.join(CARPETA_FRAMES, f"frame_{idx}.png")

    log.info(
        f"[CAPÍTULO {idx}] Reconocimiento automático iniciado "
        f"(vídeo={mmss}, captura={t_captura:.2f}s)"
    )

    if not extraer_frame(video_path, t_captura, frame_path, log):
        log.warning(f"[CAPÍTULO {idx}] No se pudo extraer el frame")
        return None

    if modo_personajes == "4p":
        todo_ok = True
        nombres = []
        posiciones = [
            ("izquierda_inferior", "izq_inf"),
            ("izquierda_superior", "izq_sup"),
            ("derecha_inferior", "der_inf"),
            ("derecha_superior", "der_sup"),
        ]
        pendientes = []

        for clave, lado in posiciones:
            recorte = recortar(frame_path, COORDENADAS[clave])
            nombre, score = identificador.identificar(recorte)
            log.info(
                f"[CAPÍTULO {idx}][AUTO] {lado}: "
                f"{nombre if nombre else 'DESCONOCIDO'} (score={score:.3f})"
            )
            if not nombre or score < identificador.umbral:
                todo_ok = False
                pendientes.append(lado)
            nombres.append(nombre)

        if todo_ok:
            log.info(f"[CAPÍTULO {idx}] Reconocimiento automático completado")
            return f"{mmss} {nombres[1]} / {nombres[0]} Vs. {nombres[3]} / {nombres[2]}"

        log.info(
            f"[CAPÍTULO {idx}] Pendiente de revisión manual: "
            f"{', '.join(pendientes)}"
        )
    else:
        recorte_izq = recortar(frame_path, COORDENADAS["izquierda"])
        nombre_izq, score_izq = identificador.identificar(recorte_izq)
        log.info(
            f"[CAPÍTULO {idx}][AUTO] izquierda: "
            f"{nombre_izq if nombre_izq else 'DESCONOCIDO'} "
            f"(score={score_izq:.3f})"
        )

        recorte_der = recortar(frame_path, COORDENADAS["derecha"])
        nombre_der, score_der = identificador.identificar(recorte_der)
        log.info(
            f"[CAPÍTULO {idx}][AUTO] derecha: "
            f"{nombre_der if nombre_der else 'DESCONOCIDO'} "
            f"(score={score_der:.3f})"
        )

        if (nombre_izq and score_izq >= identificador.umbral
                and nombre_der and score_der >= identificador.umbral):
            log.info(f"[CAPÍTULO {idx}] Reconocimiento automático completado")
            return f"{mmss} {nombre_izq} Vs. {nombre_der}"

        pendientes = []
        if not nombre_izq or score_izq < identificador.umbral:
            pendientes.append("izquierda")
        if not nombre_der or score_der < identificador.umbral:
            pendientes.append("derecha")
        log.info(
            f"[CAPÍTULO {idx}] Pendiente de revisión manual: "
            f"{', '.join(pendientes)}"
        )

    # Si no pudo ser automático, devolvemos TODO lo necesario para el manual
    return ("manual", idx, start_time, frame_path, nombre_base, video_path)

"""
source = source[:start] + replacement + source[end:]

# Insertar el aviso del bloque manual sin depender del tipo de salto de línea.
lineas = source.splitlines(keepends=True)
objetivo = "for idx, start_time, frame_path, nombre_base, video_path in pendientes_manuales:"
for i, linea in enumerate(lineas):
    if linea.strip() == objetivo:
        if i + 1 < len(lineas) and "Comenzando revisión manual" in lineas[i + 1]:
            break
        salto = "\\n" if linea.endswith("\\n") else ""
        lineas.insert(i + 1, '        log.info(f"[CAPÍTULO {idx}] Comenzando revisión manual")' + salto)
        break
else:
    raise SystemExit("No encuentro el bucle de revisión manual; no se ha modificado main.py.")

source = "".join(lineas)

backup = path.with_name("main.py.bak")
if not backup.exists():
    backup.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
path.write_text(source, encoding="utf-8")
print("Cambios aplicados a main.py. Copia original guardada en main.py.bak.")