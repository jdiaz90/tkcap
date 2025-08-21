import os, cv2
import numpy as np
from datetime import datetime

class IdentificadorPersonaje:
    def __init__(self, carpeta_referencias, umbral=0.90):
        self.carpeta_referencias = carpeta_referencias
        self.umbral = umbral
        self.referencias = {}
        self.cargar_referencias()

    def cargar_referencias(self):
        self.referencias.clear()
        os.makedirs(self.carpeta_referencias, exist_ok=True)
        for personaje in os.listdir(self.carpeta_referencias):
            ruta_pj = os.path.join(self.carpeta_referencias, personaje)
            if os.path.isdir(ruta_pj):
                self.referencias[personaje] = []
                for archivo in os.listdir(ruta_pj):
                    if archivo.lower().endswith((".png", ".jpg", ".jpeg")):
                        img = cv2.imread(os.path.join(ruta_pj, archivo))
                        if img is not None:
                            self.referencias[personaje].append(img)

    def identificar(self, recorte):
        if recorte is None or not self.referencias:
            return None, 0.0

        # 🔹 Filtro previo para descartar frames negros o uniformes
        brillo_medio = np.mean(recorte)
        varianza_pix = np.var(recorte)
        if brillo_medio < 5 or varianza_pix < 50:
            return None, 0.0

        mejor_nombre, mejor_score = None, -1
        for nombre, lista_imgs in self.referencias.items():
            for ref_bgr in lista_imgs:
                if recorte.shape != ref_bgr.shape:
                    recorte = cv2.resize(recorte, (ref_bgr.shape[1], ref_bgr.shape[0]))
                res = cv2.matchTemplate(ref_bgr, recorte, cv2.TM_CCOEFF_NORMED)
                _, max_val, _, _ = cv2.minMaxLoc(res)
                if max_val > mejor_score:
                    mejor_score, mejor_nombre = max_val, nombre

        if mejor_score >= self.umbral:
            return mejor_nombre, mejor_score
        return None, mejor_score
