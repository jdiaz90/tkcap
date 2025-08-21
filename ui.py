import tkinter as tk
from tkinter import filedialog

def seleccionar_carpeta(titulo):
    root = tk.Tk()
    root.withdraw()
    return filedialog.askdirectory(title=titulo)
