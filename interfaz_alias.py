import os
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
from video_io import extraer_frame, recortar

def lanzar_interfaz(detalle_detectado, sugerencia, frame_path, img_debug_path,
                    video_nombre, capitulo_idx, ruta_perfil,
                    start_time, video_path, coords, identificador):
    """
    Interfaz para confirmar/editar el personaje detectado.
    Permite ajustar la captura ±0.5 segundos, actualiza frame y debug,
    y realiza reconocimiento automático si se mueve el tiempo.
    """
    resultado = {"alias": None, "guardar": True}
    tiempo_actual = [start_time]  # mutable para closures

    def refrescar_imagenes():
        # Reextraer frame y recorte debug
        extraer_frame(video_path, tiempo_actual[0], frame_path, log=None)
        recorte = recortar(frame_path, coords)
        if recorte is not None:
            import cv2
            cv2.imwrite(img_debug_path, recorte)
        # Frame completo
        if os.path.exists(frame_path):
            img_frame = Image.open(frame_path)
            img_frame.thumbnail((400, 225))
            label_frame.image = ImageTk.PhotoImage(img_frame)
            label_frame.configure(image=label_frame.image)
        # Recorte debug
        if os.path.exists(img_debug_path):
            img_crop = Image.open(img_debug_path)
            img_crop.thumbnail((200, 200))
            label_crop.image = ImageTk.PhotoImage(img_crop)
            label_crop.configure(image=label_crop.image)
        # Tiempo
        label_tiempo.configure(
            text=f"⏱ Tiempo captura: {int(tiempo_actual[0]//60):02d}:{int(tiempo_actual[0]%60):02d}"
        )

    def mover_segundos(delta):
        tiempo_actual[0] = max(0, tiempo_actual[0] + delta)
        refrescar_imagenes()
        # Intento de identificación automática
        recorte_nuevo = recortar(frame_path, coords)
        if recorte_nuevo is not None:
            nombre, score = identificador.identificar(recorte_nuevo)
            if nombre and score >= 0.75:  # umbral configurable
                resultado["alias"] = nombre
                resultado["guardar"] = False
                root.quit()
                root.destroy()

    def confirmar():
        alias = entrada_alias.get().strip()
        if alias:
            resultado["alias"] = alias
            root.quit()
            root.destroy()
        else:
            messagebox.showwarning(
                "Aviso", "Debes escribir un nombre o usar Omitir/Capítulo especial."
            )

    def omitir():
        resultado["alias"] = "DESCONOCIDO"
        root.quit()
        root.destroy()

    def capitulo_especial():
        alias = entrada_alias.get().strip()
        if alias:
            resultado["alias"] = f"__CAPITULO_ESPECIAL__:{alias}"
            root.quit()
            root.destroy()
        else:
            messagebox.showwarning(
                "Aviso", "Escribe una descripción para el capítulo especial."
            )

    # --- Construcción de la ventana ---
    root = tk.Toplevel()
    root.title(f"Confirmar personaje — {video_nombre} (Capítulo {capitulo_idx})")
    root.geometry("950x580")
    root.bind("<Return>", lambda e=None: confirmar())

    label_tiempo = tk.Label(root, font=("Arial", 12), fg="green")
    label_tiempo.pack()

    tk.Label(root, text=f"Detección automática: {detalle_detectado}", font=("Arial", 14)).pack(pady=5)
    tk.Label(root, text=f"Sugerencia: {sugerencia}", font=("Arial", 12), fg="blue").pack()

    frame_imgs = tk.Frame(root)
    frame_imgs.pack(pady=10)
    label_frame = tk.Label(frame_imgs)
    label_frame.grid(row=0, column=0, padx=5)
    label_crop = tk.Label(frame_imgs)
    label_crop.grid(row=0, column=1, padx=5)

    tk.Label(root, text="Nombre final:", font=("Arial", 12)).pack(pady=5)
    entrada_alias = tk.Entry(root, font=("Arial", 14))
    entrada_alias.pack()
    entrada_alias.insert(0, sugerencia)

    # Botones de acción
    frame_accion = tk.Frame(root)
    frame_accion.pack(pady=10)
    tk.Button(frame_accion, text="✅ Confirmar", font=("Arial", 12),
              command=confirmar).pack(side="left", padx=10)
    tk.Button(frame_accion, text="⏭ Omitir", font=("Arial", 12),
              command=omitir).pack(side="left", padx=10)
    tk.Button(frame_accion, text="🎬 Capítulo especial", font=("Arial", 12),
              command=capitulo_especial).pack(side="left", padx=10)

    # Botones de tiempo debajo
    frame_tiempo = tk.Frame(root)
    frame_tiempo.pack(pady=5)
    tk.Button(frame_tiempo, text="⏪ -0.5s", font=("Arial", 12),
              command=lambda: mover_segundos(-0.5)).pack(side="left", padx=5)
    tk.Button(frame_tiempo, text="⏩ +0.5s", font=("Arial", 12),
              command=lambda: mover_segundos(0.5)).pack(side="left", padx=5)

    refrescar_imagenes()
    root.mainloop()
    return resultado["alias"], resultado["guardar"]
