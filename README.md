# VAR Pro - LaLiga Edition 🖥️⚽

Aplicación de análisis volumétrico y trazado de líneas de fuera de juego (VAR) de nivel profesional, diseñada con una interfaz gráfica moderna, precisión matemática en perspectiva 3D, y compatibilidad nativa con fotogramas de vídeo para análisis en tiempo real. 

**Hecho por [@albertitocalata](https://twitter.com/albertitocalata)**.

---

## ✨ Novedades y Características Principales

* **Interfaz Gráfica Moderna (GUI)** 🎨: Interfaz oscura, estilizada y profesional manejada íntegramente con ratón desde un panel lateral unificado, gracias a `CustomTkinter`. Despídete de la consola de MS-DOS.
* **Lupa de Precisión Quirúrgica** 🔍: Un panel dedicado a una lupa dinámica ampliada mediante interpolación bicúbica (`INTER_CUBIC`), con un punto de mira central rojo coral diseñado bajo la paleta gráfica oficial de LaLiga.
* **Análisis Directo desde Vídeos** 🎥:
  * Ya no necesitas capturar la pantalla. Carga tu archivo `.mp4`, `.mov` o `.avi` estandar.
  * Una barra de reproducción deslizante interactiva te permite avanzar o retroceder milisegundo a milisegundo para **cazar el fotograma exacto del instante del pase**.
* **Geometría Dinámica Antifallos** 🤖: 
  * Se evalúan las proyecciones visuales al 100% sobre el mismo eje `Y` del césped de los jugadores (`x_at_y`). Esto previene físicamente que un falso de perspectiva o un enfoque de cámara raro emita veredictos equivocados.
* **Física Corporal Humana (Hombro / Pie)** 🦶: Al hacer clic en el hombro y en el pie del jugador, el motor matemático evalúa y extrapola ambos puntos para verificar **automáticamente** cuál de los dos miembros está más adelantado a favor o en contra del gol.
* **Sombreado Direccional Automático** 🟩🟥: Calcula cuál es el "último defensor", cruza las referencias, traza líneas rojas o verdes absolutas hasta el infinito, y sombrea la zona "Offside" del área dinámicamente si aplicas la fase de límites.
* **Marcador Oficial y Watermark** ✒️: Tu marca y firma analítica quedan integradas en la imagen procesada exportada al pulsarse el botón de un clic.

## 🚀 Requisitos de Instalación (Código)

La aplicación requiere la instalación de las dependencias informáticas de visión artificial e interfaz gráfica:

```bash
pip install opencv-python numpy customtkinter Pillow
```

## 🎮 Guía de Uso (Flujo de Trabajo)

La aplicación está distribuida en dos variantes geométricas dependiendo de qué referencias tengas en la imagen:

* **Modo Intersección** (`python gui_app_var.py`): Se basa en cruzar líneas libres infinitas del césped formadas por 4 marcas que hagas a mano en el campo.
* **Modo Homografía** (`python gui_var.py`): Se basa en reconstruir las distancias usando los 4 vértices del área de penalti (grande o pequeña) para además devolverte la distancia en **centímetros exactos** del fuera de juego.

### Cómo Analizar

1. **Carga** la foto o vídeo. Si usas vídeo, utiliza la ruleta y los botones inferiores para encontrar la estampa exacta de la posible infracción.
2. Sigue el **Indicador de Fase** de color rojo fuego de la izquierda en la pantalla. Usa el Espaciador del teclado o presiona el botón "Siguiente Fase".
3. **Fase 1 (Calibración)**: Haz tus 4 clics en el campo para enseñarle a la app dónde están el cielo y el suelo geolocalizando el campo.
4. **Fase 2 (Defensas)**: Arriba, Abajo (Hombro, Pie). Selecciona el último hombre que habilita la jugada.
5. **Fase 3 (Atacantes)**: Selecciona a los que rematan a puerta. Un texto dictará instantáneamente `POSICIÓN CORRECTA` o `FUERA DE JUEGO`.
6. Haz clic en **Exportar**. ¡Se generará un `.jpg` final a máxima resolución con tu firma!