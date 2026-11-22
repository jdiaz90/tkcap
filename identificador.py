import os

import cv2
import numpy as np


class IdentificadorPersonaje:
    def __init__(self, carpeta_referencias, umbral=0.90):
        self.carpeta_referencias = carpeta_referencias
        self.umbral = umbral
        self.referencias = {}
        self.cargar_referencias()

    def cargar_referencias(self):
        """Carga todas las imágenes; el nombre de la carpeta identifica al personaje."""
        referencias = {}
        os.makedirs(self.carpeta_referencias, exist_ok=True)

        with os.scandir(self.carpeta_referencias) as personajes:
            for entrada in personajes:
                if not entrada.is_dir():
                    continue

                imagenes = []
                with os.scandir(entrada.path) as archivos:
                    for archivo in archivos:
                        if archivo.is_file() and archivo.name.lower().endswith((".png", ".jpg", ".jpeg")):
                            img = cv2.imread(archivo.path)
                            if img is not None:
                                imagenes.append(img)
                referencias[entrada.name] = imagenes

        # Sustitución al final: nunca deja el banco en un estado parcialmente cargado.
        self.referencias = referencias

    def agregar_referencia(self, nombre, imagen):
        """Añade a memoria una referencia recién guardada, sin recargar el banco."""
        if imagen is None:
            return
        self.referencias.setdefault(nombre, []).append(imagen.copy())

    def identificar(self, recorte):
        if recorte is None or not self.referencias:
            return None, 0.0

        brillo_medio = float(np.mean(recorte))
        varianza_pix = float(np.var(recorte))
        if brillo_medio < 5 or varianza_pix < 50:
            return None, 0.0

        mejor_nombre, mejor_score = None, -1.0
        # El recorte original no se modifica. Si hay varios tamaños de plantilla,
        # cada variante redimensionada parte siempre de la imagen original.
        recortes_por_tamano = {}
        forma_original = recorte.shape[:2]

        for nombre, lista_imgs in self.referencias.items():
            for ref_bgr in lista_imgs:
                alto_ref, ancho_ref = ref_bgr.shape[:2]
                clave = (ancho_ref, alto_ref)

                if clave not in recortes_por_tamano:
                    if forma_original == (alto_ref, ancho_ref):
                        recortes_por_tamano[clave] = recorte
                    else:
                        recortes_por_tamano[clave] = cv2.resize(
                            recorte, clave, interpolation=cv2.INTER_LINEAR
                        )

                muestra = recortes_por_tamano[clave]
                res = cv2.matchTemplate(ref_bgr, muestra, cv2.TM_CCOEFF_NORMED)
                _, max_val, _, _ = cv2.minMaxLoc(res)
                score = float(max_val)
                if score > mejor_score:
                    mejor_score, mejor_nombre = score, nombre

        if mejor_score >= self.umbral:
            return mejor_nombre, mejor_score
        return None, mejor_score
