# 🥋 TKCAP - Character Capture & Recognition

TKCAP es una herramienta en Python para **capturar fotogramas de partidas de juegos de lucha** y reconocer automáticamente el personaje que aparece en cada lado de la pantalla.

Usa técnicas de **template matching** con OpenCV y referencias de imágenes preetiquetadas para identificar personajes, y permite una **validación manual** mediante interfaz gráfica en Tkinter.

-----

## 🚀 Características

  - **Procesamiento de vídeo**: extracción de frames en puntos clave.
  - **Recorte automático** de las zonas de interés (izquierda/derecha) según configuración.
  - **Comparación con plantillas** (template matching) usando OpenCV.
  - **Interfaz gráfica** para confirmación o corrección manual del personaje detectado.
  - **Filtro anti-falsos positivos** para descartar frames vacíos o negros.
  - **Configuraciones por juego**: perfiles y coordenadas ajustadas a distintas entregas de juegos de lucha.

-----

## 📂 Estructura del proyecto

```
TKCAP/
│
├── config/
│   ├── JuegoDeLucha*/config.json  # Configuración específica por juego*
│   └── JuegoDeLucha*/personajes_ref  # Imágenes de referencia
│
├── debug/  # Recortes temporales para validación (ignorado en Git)
├── frames/  # Frames extraídos (ignorado en Git)
├── logs/  # Registros de ejecución (ignorado en Git)
└── venv/  # Entorno virtual Python (ignorado en Git)
│
├── main.py  # Entrada principal del programa
├── config_loader.py  # Carga de archivos de configuración
├── identificador.py  # Lógica de identificación de personajes
├── interfaz_alias.py  # Interfaz gráfica de validación
├── ui.py  # Utilidades de UI (selección de carpetas)
├── utils.py  # Funciones auxiliares y helpers
├── video_io.py  # Entrada/salida de vídeo y recortes
├── requirements.txt  # Dependencias del proyecto
└── tkchars.bat  # Lanzador rápido en Windows
```

-----

## 🛠 Instalación

1.  Clona este repositorio:

    ```bash
    git clone https://github.com/usuario/tkcap.git
    cd tkcap
    ```

2.  Crea y activa un entorno virtual:

    ```bash
    python -m venv venv
    .\venv\Scripts\activate   # En Windows
    # o source venv/bin/activate  # En Linux/Mac
    ```

3.  Instala las dependencias:

    ```bash
    pip install -r requirements.txt
    ```

4.  (Opcional) Instala **Tesseract OCR** si quieres hacer reconocimiento de texto.

      * [Instrucciones de instalación](https://github.com/tesseract-ocr/tesseract/wiki)

-----

## ▶️ Uso

Hay dos formas de ejecutar el programa:

1.  **Usando el archivo `main.py`**
      * Asegúrate de haber activado el entorno virtual.
      * Ejecuta el script principal:
        ```bash
        python main.py
        ```
2.  **Usando el lanzador `tkchars.bat`** (solo en Windows)
      * Simplemente ejecuta el archivo .bat. Este script se encargará de activar el entorno virtual y lanzar el programa.

En ambos casos:

  * El programa te pedirá que **selecciones el juego** de la lista de perfiles disponibles.
  * A continuación, se abrirá una ventana para que **selecciones la carpeta que contiene los vídeos**.
  * Finalmente, selecciona la carpeta donde se **guardarán los resultados**.

El programa procesará automáticamente los vídeos encontrados y, si es necesario, abrirá una interfaz gráfica para la validación manual de personajes.

-----

## ⚙️ Configuración

Cada juego tiene su `config.json` dentro de `config/` con:

  * Resolución objetivo
  * Coordenadas de recorte para izquierda/derecha
  * Rutas de carpetas de referencias

Puedes añadir o actualizar imágenes en `personajes_ref` para mejorar la precisión.

-----

## 📦 Dependencias principales

  * `numpy`
  * `opencv-python`
  * `pillow`
  * `pytesseract`
  * `fuzzywuzzy`
  * `rapidfuzz`
  * `python-Levenshtein`
  * `packaging`

Todas instalables vía:

```bash
pip install -r requirements.txt
```

-----

## 📄 Licencia

Este proyecto está bajo la **Licencia MIT**. Puedes ver el texto completo en el archivo [`LICENSE.md`](./LICENSE)
