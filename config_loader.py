import json, os, sys

def cargar_config(ruta_perfil, log):
    ruta_cfg = os.path.join(ruta_perfil, "config.json")
    with open(ruta_cfg, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    coord = cfg.get("coordenadas", {})
    if all(k in coord for k in ["izquierda", "derecha"]):
        modo = "2p"
    elif all(k in coord for k in [
        "izquierda_superior", "izquierda_inferior",
        "derecha_superior", "derecha_inferior"
    ]):
        modo = "4p"
    else:
        log.error("Coordenadas no válidas en config.json")
        sys.exit(1)

    return cfg, modo
