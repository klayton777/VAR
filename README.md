# VAR Tech Suite - LaLiga Edition 🖥️⚽

Suite profesional de herramientas de análisis volumétrico, trazado de líneas de fuera de juego y tecnología de línea de gol (**VAR**). Diseñada con una interfaz gráfica premium, precisión matemática en perspectiva 3D y compatibilidad nativa con vídeo para análisis en tiempo real.

**Hecho por [@albertitocalata](https://twitter.com/albertitocalata)**.

---

## 🛠️ La Trilogía de Herramientas

Esta suite se divide en tres aplicaciones especializadas según el tipo de jugada a analizar:

1.  **VAR Pro (Intersección)** `gui_app_var.py`: Basado en el cruce de líneas libres infinitas. Ideal para cualquier zona del campo usando 4 puntos de referencia manuales.
2.  **VAR Precision (Homografía)** `gui_var.py`: Utiliza la geometría del área de penalti para reconstruir distancias reales y devolver el fuera de juego en **centímetros exactos**.
3.  **Goal Line Tech (Ojo de Halcón)** `gui_goal.py`: Herramienta dedicada para jugadas de línea de gol y "balón fuera/dentro" con **minimapa 3D explicativo**.

---

## ✨ Novedades y Características Principales

*   **Interfaz Premium (VOR Styled)** 🎨: Nueva interfaz oscura profesional con sidebar unificado, scrollable y controles táctiles/ratón mediante `CustomTkinter`.
*   **Gestión de Proyectos (.varproj)** 💾: Guarda tus calibraciones y análisis para retomarlos más tarde o compartirlos.
*   **Marcador y Escudos Dinámicos** ⚽: Personaliza los nombres de los equipos y sus escudos oficiales directamente en el análisis.
*   **Lupa de Precisión ×8** 🔍: Panel dinámico con interpolación bicúbica y punto de mira central diseñado bajo la paleta gráfica de LaLiga.
*   **Análisis de Vídeo Nativo** 🎥: Carga archivos `.mp4`, `.mov` o `.avi`. Usa la barra de reproducción para cazar el fotograma exacto milisegundo a milisegundo.
*   **Exportación Pro** 📸: Genera imágenes `.jpg` a máxima resolución o clips de vídeo con las líneas procesadas y tu firma/watermark.

---

## 🎨 Personalización de Escudos

Puedes añadir tus propios escudos para que aparezcan en el marcador:
1. Crea una carpeta llamada `escudos` en el directorio raíz.
2. Añade imágenes `.png` o `.jpg` (ej: `madrid.png`, `barca.png`).
3. En la aplicación, escribe el nombre del equipo y el sistema buscará automáticamente el archivo correspondiente.

---

## 🚀 Instalación y Uso

### Ejecutables (Recomendado)
Descarga la última versión desde la sección de **Releases** y ejecuta el archivo `.exe` correspondiente. No requiere instalación de Python.

### Entorno de Desarrollo
Si prefieres ejecutar el código fuente, instala las dependencias:

```bash
pip install opencv-python numpy customtkinter Pillow
```

Luego ejecuta cualquiera de los módulos:
```bash
python gui_goal.py
```

---

## 🎮 Guía de Flujo de Trabajo

1.  **Carga**: Importa la foto o vídeo. Busca el momento exacto del pase o del gol.
2.  **Fase 1 (Calibración)**: Haz 4 clics en el césped para enseñar a la app la perspectiva del campo.
3.  **Fase 2 (Referencias)**: Marca a los defensas/atacantes (hombro y pie). El motor matemático evaluará automáticamente qué parte del cuerpo está más adelantada.
4.  **Fase 3 (Resultado)**: La aplicación dictará instantáneamente el veredicto: `POSICIÓN CORRECTA`, `FUERA DE JUEGO` o `GOL`.
5.  **Exportar**: Genera el resultado final con un clic para compartir en redes sociales o retransmisiones.

---

**¿Te gusta el proyecto?** ¡Deja una ⭐ en el repositorio!