import cv2
import numpy as np
import tkinter as tk
from tkinter import filedialog
import sys
import os

# --- VARIABLES GLOBALES - MODO MULTIJUGADOR ---
fase = 0  # 0: Fuga, 1: Defensas, 2: Ataque, 3: Limites
pts_fuga = []
pts_def = []
pts_att = []
pts_lim = []

punto_fuga = None
imagen_original = None
imagen_base_dibujada = None

# Estados de la App
ataca_derecha = True  
mostrar_lineas_fuga = True 

# Rastreo continuo del ratón
mouse_x, mouse_y = 0, 0 

def seleccionar_imagen():
    """Abre un diálogo de Windows para seleccionar una foto"""
    root = tk.Tk()
    root.withdraw() 
    file_path = filedialog.askopenfilename(
        title="VAR Multijugador - Selecciona la captura del partido",
        filetypes=[
            ("Imágenes", "*.jpg;*.jpeg;*.png;*.bmp;*.webp"),
            ("Todos los archivos", "*.*")
        ]
    )
    root.destroy()
    if not file_path:
        print("No se seleccionó ninguna imagen. Saliendo.")
        sys.exit()
    return file_path

def calcular_interseccion(p1, p2, p3, p4):
    x1, y1 = p1; x2, y2 = p2
    x3, y3 = p3; x4, y4 = p4
    a1 = y2 - y1; b1 = x1 - x2; c1 = a1 * x1 + b1 * y1
    a2 = y4 - y3; b2 = x3 - x4; c2 = a2 * x3 + b2 * y3
    determinante = a1 * b2 - a2 * b1
    if determinante == 0: return None 
    x = (b2 * c1 - b1 * c2) / determinante
    y = (a1 * c2 - a2 * c1) / determinante
    return (int(x), int(y))

def crear_linea_infinita(p1, p2):
    x1, y1 = p1; x2, y2 = p2
    if x1 == x2: return (x1, -10000), (x1, 10000)
    m = (y2 - y1) / (x2 - x1)
    b = y1 - m * x1
    return (-10000, int(m * -10000 + b)), (10000, int(m * 10000 + b))

def x_en_fondo(p_fuga, p_suelo, y_fondo):
    if p_fuga[0] == p_suelo[0]: return p_fuga[0]
    m = (p_suelo[1] - p_fuga[1]) / (p_suelo[0] - p_fuga[0])
    b = p_fuga[1] - m * p_fuga[0]
    return (y_fondo - b) / m

def dibujar_linea_infinita(img, pt1, pt2, color, grosor):
    p1_inf, p2_inf = crear_linea_infinita(pt1, pt2)
    cv2.line(img, p1_inf, p2_inf, color, grosor, cv2.LINE_AA)
    return img

def sombrear_zona_fuera_juego(img, p_fuga, p_def_suelo, ataca_derecha, color, puntos_limite):
    h, w = img.shape[:2]
    x_fondo = x_en_fondo(p_fuga, p_def_suelo, h*10)
    
    if ataca_derecha:
        esquina_inf = (w*10, h*10)
        esquina_sup = (w*10, -h*10)
    else:
        esquina_inf = (-w*10, h*10)
        esquina_sup = (-w*10, -h*10)
        
    poligono_offside = np.array([p_fuga, (int(x_fondo), int(h*10)), esquina_inf, esquina_sup], dtype=np.int32)
    
    capa_sombra = np.zeros_like(img)
    cv2.fillPoly(capa_sombra, [poligono_offside], color)
    
    if len(puntos_limite) >= 3:
        mask_campo = np.zeros(img.shape[:2], dtype=np.uint8)
        pts_campo = np.array(puntos_limite, dtype=np.int32)
        cv2.fillPoly(mask_campo, [pts_campo], 255) 
        sombra_final = cv2.bitwise_and(capa_sombra, capa_sombra, mask=mask_campo)
    else:
        sombra_final = capa_sombra

    return cv2.addWeighted(img, 1.0, sombra_final, 0.4, 0) 

def actualizar_dibujos():
    global imagen_base_dibujada, punto_fuga
    imagen_base_dibujada = imagen_original.copy()
    punto_fuga = None 
    h_img = imagen_base_dibujada.shape[0]
    
    # Textos informativos de interfaz
    dir_texto = "DERECHA" if ataca_derecha else "IZQUIERDA"
    textos_fase = {
        0: "Fase 1: Calibracion (4 puntos azules)",
        1: "Fase 2: Defensores (Pulsar ESPACIO al terminar)",
        2: "Fase 3: Atacantes (Pulsar ESPACIO al terminar)",
        3: "Fase 4: Limites del Campo (Sombra Cyan)"
    }
    
    if mostrar_lineas_fuga:
        cv2.putText(imagen_base_dibujada, f"Ataque: {dir_texto}", (30, 250), cv2.FONT_HERSHEY_DUPLEX, 0.8, (0, 0, 0), 3, cv2.LINE_AA)
        cv2.putText(imagen_base_dibujada, f"Ataque: {dir_texto}", (30, 250), cv2.FONT_HERSHEY_DUPLEX, 0.8, (255, 255, 255), 1, cv2.LINE_AA)
        cv2.putText(imagen_base_dibujada, textos_fase[fase], (30, 290), cv2.FONT_HERSHEY_DUPLEX, 0.7, (0, 0, 0), 3, cv2.LINE_AA)
        cv2.putText(imagen_base_dibujada, textos_fase[fase], (30, 290), cv2.FONT_HERSHEY_DUPLEX, 0.7, (0, 255, 255), 1, cv2.LINE_AA)

    # 1. CALIBRACIÓN
    if len(pts_fuga) >= 4:
        punto_fuga = calcular_interseccion(pts_fuga[0], pts_fuga[1], pts_fuga[2], pts_fuga[3])

    if mostrar_lineas_fuga:
        if len(pts_fuga) >= 2:
            p1, p2 = crear_linea_infinita(pts_fuga[0], pts_fuga[1])
            cv2.line(imagen_base_dibujada, p1, p2, (255, 0, 0), 1, cv2.LINE_AA)
        if len(pts_fuga) >= 4:
            p1, p2 = crear_linea_infinita(pts_fuga[2], pts_fuga[3])
            cv2.line(imagen_base_dibujada, p1, p2, (255, 0, 0), 1, cv2.LINE_AA)

    # 2. EVALUAR DEFENSORES Y ENCONTRAR AL ÚLTIMO
    mejor_def_proyectado = None
    mejor_x_fondo = None
    
    if punto_fuga is not None and len(pts_def) >= 2:
        for i in range(0, len(pts_def) - 1, 2):
            hombro = pts_def[i]
            pie = pts_def[i+1]
            p_proyectado = (hombro[0], pie[1])
            xf = x_en_fondo(punto_fuga, p_proyectado, h_img)
            
            # Buscar el que está más cerca de su propia portería
            if mejor_x_fondo is None:
                mejor_x_fondo = xf
                mejor_def_proyectado = p_proyectado
            else:
                if ataca_derecha and xf > mejor_x_fondo:
                    mejor_x_fondo = xf
                    mejor_def_proyectado = p_proyectado
                elif not ataca_derecha and xf < mejor_x_fondo:
                    mejor_x_fondo = xf
                    mejor_def_proyectado = p_proyectado

        # Pintar todos los defensores
        for i in range(0, len(pts_def) - 1, 2):
            hombro = pts_def[i]
            pie = pts_def[i+1]
            p_proyectado = (hombro[0], pie[1])
            
            if mostrar_lineas_fuga:
                cv2.line(imagen_base_dibujada, hombro, p_proyectado, (255, 255, 0), 1, cv2.LINE_AA)
                cv2.line(imagen_base_dibujada, (pie[0]-5, pie[1]), (pie[0]+5, pie[1]), (255, 255, 0), 1)
                
            if p_proyectado == mejor_def_proyectado:
                # Solo dibujamos la sombra cyan si ya hemos pasado a la Fase 3 (Límites)
                if fase >= 3:
                    imagen_base_dibujada = sombrear_zona_fuera_juego(imagen_base_dibujada, punto_fuga, p_proyectado, ataca_derecha, (255, 255, 0), pts_lim)
                # La línea amarilla gruesa sí la dejamos siempre visible para guiarte
                imagen_base_dibujada = dibujar_linea_infinita(imagen_base_dibujada, punto_fuga, p_proyectado, (255, 255, 0), 2)
            elif mostrar_lineas_fuga:
                # Los demás se llevan una línea finita secundaria para referencia
                imagen_base_dibujada = dibujar_linea_infinita(imagen_base_dibujada, punto_fuga, p_proyectado, (150, 150, 0), 1)

    # 3. EVALUAR ATACANTES Y VEREDICTO
    atacantes_fuera_juego = 0
    if punto_fuga is not None and mejor_x_fondo is not None and len(pts_att) >= 2:
        for i in range(0, len(pts_att) - 1, 2):
            hombro = pts_att[i]
            pie = pts_att[i+1]
            p_proyectado = (hombro[0], pie[1])
            xf = x_en_fondo(punto_fuga, p_proyectado, h_img)
            
            esta_adelantado = False
            if ataca_derecha and xf > mejor_x_fondo: esta_adelantado = True
            elif not ataca_derecha and xf < mejor_x_fondo: esta_adelantado = True
            
            # Dinamismo de color: Rojo si está en Offside, Verde si está Correcto
            if esta_adelantado:
                atacantes_fuera_juego += 1
                color = (0, 0, 255) # Rojo
            else:
                color = (0, 255, 0) # Verde
                
            if mostrar_lineas_fuga:
                cv2.line(imagen_base_dibujada, hombro, p_proyectado, color, 1, cv2.LINE_AA)
                cv2.line(imagen_base_dibujada, (pie[0]-5, pie[1]), (pie[0]+5, pie[1]), color, 1)
                
            imagen_base_dibujada = dibujar_linea_infinita(imagen_base_dibujada, punto_fuga, p_proyectado, color, 2)
            
        # Veredicto global
        if atacantes_fuera_juego > 0:
            texto_veredicto = "FUERA DE JUEGO"
            color_texto = (0, 0, 255)
        else:
            texto_veredicto = "POSICION CORRECTA"
            color_texto = (0, 255, 0)
            
        cv2.putText(imagen_base_dibujada, texto_veredicto, (30, h_img - 30), cv2.FONT_HERSHEY_DUPLEX, 1.2, (0,0,0), 4, cv2.LINE_AA)
        cv2.putText(imagen_base_dibujada, texto_veredicto, (30, h_img - 30), cv2.FONT_HERSHEY_DUPLEX, 1.2, color_texto, 2, cv2.LINE_AA)

    # 4. LÍMITES Y PUNTOS RESIDUALES
    if mostrar_lineas_fuga:
        for i in range(len(pts_lim)):
            cv2.circle(imagen_base_dibujada, pts_lim[i], 3, (255, 0, 255), -1) 
            if i > 0:
                cv2.line(imagen_base_dibujada, pts_lim[i-1], pts_lim[i], (255, 0, 255), 1, cv2.LINE_AA)
        if len(pts_lim) >= 3:
             cv2.line(imagen_base_dibujada, pts_lim[-1], pts_lim[0], (255, 0, 255), 1, cv2.LINE_AA)

    # Mostrar puntitos de calibración
    if mostrar_lineas_fuga:
        for p in pts_fuga: cv2.circle(imagen_base_dibujada, p, 2, (0, 0, 255), -1)
        # Mostrar puntos impares (clics a medias)
        if len(pts_def) % 2 != 0: cv2.circle(imagen_base_dibujada, pts_def[-1], 2, (255, 255, 0), -1)
        if len(pts_att) % 2 != 0: cv2.circle(imagen_base_dibujada, pts_att[-1], 2, (0, 0, 255), -1)


def actualizar_interfaz():
    if imagen_base_dibujada is None:
        return
        
    imagen_mostrar = imagen_base_dibujada.copy()
    h, w = imagen_mostrar.shape[:2]
    
    r = 25 
    img_acolchada = cv2.copyMakeBorder(imagen_base_dibujada, r, r, r, r, cv2.BORDER_CONSTANT, value=[0,0,0])
    y_p, x_p = mouse_y + r, mouse_x + r
    recorte = img_acolchada[y_p-r : y_p+r, x_p-r : x_p+r].copy()
    
    if recorte.shape[0] > 0 and recorte.shape[1] > 0:
        lupa = cv2.resize(recorte, (200, 200), interpolation=cv2.INTER_NEAREST)
        cv2.line(lupa, (100, 0), (100, 200), (255, 255, 255), 1)
        cv2.line(lupa, (0, 100), (200, 100), (255, 255, 255), 1)
        
        if w > 220 and h > 220:
            x_ini, y_ini = 10, 10
            imagen_mostrar[y_ini:y_ini+200, x_ini:x_ini+200] = lupa
            cv2.rectangle(imagen_mostrar, (x_ini, y_ini), (x_ini+200, y_ini+200), (255, 255, 255), 2)
            
    cv2.imshow('VAR Nivel Dios', imagen_mostrar)

def registrar_clic(evento, x, y, flags, param):
    global mouse_x, mouse_y, fase
    if evento in [cv2.EVENT_MOUSEMOVE, cv2.EVENT_LBUTTONDOWN]:
        mouse_x, mouse_y = x, y
        if evento == cv2.EVENT_LBUTTONDOWN:
            if fase == 0:
                pts_fuga.append((x, y))
                if len(pts_fuga) == 4: fase = 1 # Salto automático a defensores
            elif fase == 1:
                pts_def.append((x, y))
            elif fase == 2:
                pts_att.append((x, y))
            elif fase == 3:
                pts_lim.append((x, y))
            actualizar_dibujos()
        actualizar_interfaz()

# --- INICIO ---
ruta_imagen = seleccionar_imagen()
imagen_original = cv2.imread(ruta_imagen)

if imagen_original is None:
    print("¡ERROR! No se pudo leer la imagen.")
else:
    actualizar_dibujos()
    
    cv2.namedWindow('VAR Nivel Dios', cv2.WINDOW_NORMAL)
    actualizar_interfaz()
    cv2.setWindowProperty('VAR Nivel Dios', cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
    cv2.setMouseCallback('VAR Nivel Dios', registrar_clic)
    
    print("\n--- INSTRUCCIONES VAR MODO MULTIJUGADOR ---")
    print("FASE 1: Haz 4 clics para calibrar las líneas de fuga.")
    print("FASE 2: Haz clic (Hombro-Pie) en TODOS los defensores que quieras.")
    print("        -> Cuando termines con los defensas, pulsa la barra ESPACIADORA.")
    print("FASE 3: Haz clic (Hombro-Pie) en TODOS los atacantes que quieras.")
    print("        -> Cuando termines, pulsa la barra ESPACIADORA.")
    print("FASE 4: Marca los límites de la sombra del césped.\n")
    print("CONTROLES:")
    print("  'ESPACIO' -> Confirmar y pasar a la siguiente fase (Jugadores).")
    print("  'Z' -> Deshacer el último clic (inteligente, retrocede fases si es necesario).")
    print("  'L' -> Ocultar/Mostrar líneas de construcción para guardar foto limpia.")
    print("  'I'/'D' -> Cambiar dirección de ataque.")
    print("  'G' -> Guardar / 'ESC' -> Salir.")
    print("---------------------------------------------------\n")
    
    while True:
        tecla = cv2.waitKey(1) & 0xFF
        if tecla == 27: # ESC
            break
        elif tecla == ord(' '):
            # Lógica para avanzar de fase con la barra espaciadora
            if fase == 1 and len(pts_def) >= 2 and len(pts_def) % 2 == 0:
                fase = 2
            elif fase == 2 and len(pts_att) >= 2 and len(pts_att) % 2 == 0:
                fase = 3
            actualizar_dibujos()
            actualizar_interfaz()
        elif tecla == ord('z') or tecla == ord('Z'):
            # Deshacer inteligente por fases
            if fase == 3:
                if len(pts_lim) > 0: pts_lim.pop()
                else: fase = 2
            elif fase == 2:
                if len(pts_att) > 0: pts_att.pop()
                else: fase = 1
            elif fase == 1:
                if len(pts_def) > 0: pts_def.pop()
                else: fase = 0
            elif fase == 0:
                if len(pts_fuga) > 0: pts_fuga.pop()
            actualizar_dibujos()
            actualizar_interfaz()
        elif tecla == ord('i') or tecla == ord('I'):
            ataca_derecha = False 
            actualizar_dibujos()
            actualizar_interfaz()
        elif tecla == ord('d') or tecla == ord('D'):
            ataca_derecha = True 
            actualizar_dibujos()
            actualizar_interfaz()
        elif tecla == ord('l') or tecla == ord('L'):
            mostrar_lineas_fuga = not mostrar_lineas_fuga 
            actualizar_dibujos()
            actualizar_interfaz()
        elif tecla == ord('g') or tecla == ord('G'):
            if imagen_base_dibujada is not None:
                nombre_base = os.path.splitext(os.path.basename(ruta_imagen))[0]
                contador = 1
                nombre_archivo = f"{nombre_base}_VAR_{contador}.jpg"
                while os.path.exists(nombre_archivo):
                    contador += 1
                    nombre_archivo = f"{nombre_base}_VAR_{contador}.jpg"
                cv2.imwrite(nombre_archivo, imagen_base_dibujada)
                print(f"¡Análisis guardado con éxito como: {nombre_archivo}!")
            
    cv2.destroyAllWindows()