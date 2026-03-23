import cv2
import numpy as np
import customtkinter as ctk
from tkinter import filedialog
from PIL import Image, ImageTk
import os

# --- COLORES LALIGA (Formato BGR para OpenCV) ---
LALIGA_ROJO    = (68, 75, 255)
LALIGA_AZUL    = (255, 0, 0)
LALIGA_SEC     = (255, 100, 50)
LALIGA_VERDE   = (0, 220, 0)
LALIGA_BLANCO  = (255, 255, 255)
LALIGA_NEGRO   = (0, 0, 0)
LALIGA_MAGENTA = (255, 0, 255)

# --- MATEMÁTICA Y LÓGICA DE DIBUJO (Vía Intersección) ---
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

def x_at_y(p_fuga, p_suelo, y_eval):
    if p_fuga[1] == p_suelo[1]: return p_suelo[0]
    return p_fuga[0] + (y_eval - p_fuga[1]) * (p_suelo[0] - p_fuga[0]) / (p_suelo[1] - p_fuga[1])

def obtener_punto_mas_adelantado(hombro, pie, punto_fuga, y_eval, ataca_derecha):
    p_hombro_suelo = (hombro[0], pie[1])
    p_pie_suelo = (pie[0], pie[1])
    xf_hombro = x_at_y(punto_fuga, p_hombro_suelo, y_eval)
    xf_pie = x_at_y(punto_fuga, p_pie_suelo, y_eval)
    if ataca_derecha:
        return (p_pie_suelo, xf_pie) if xf_pie > xf_hombro else (p_hombro_suelo, xf_hombro)
    else:
        return (p_pie_suelo, xf_pie) if xf_pie < xf_hombro else (p_hombro_suelo, xf_hombro)

def crear_linea_infinita(p1, p2):
    x1, y1 = p1; x2, y2 = p2
    if x1 == x2: return (x1, -10000), (x1, 10000)
    m = (y2 - y1) / (x2 - x1)
    b = y1 - m * x1
    return (-10000, int(m * -10000 + b)), (10000, int(m * 10000 + b))

def dibujar_linea_infinita(img, pt1, pt2, color, grosor):
    p1_inf, p2_inf = crear_linea_infinita(pt1, pt2)
    cv2.line(img, p1_inf, p2_inf, color, grosor, cv2.LINE_AA)
    return img

def sombrear_zona_fuera_juego(img, p_fuga, p_def_suelo, ataca_derecha, color, puntos_limite):
    h, w = img.shape[:2]
    x_fondo = x_at_y(p_fuga, p_def_suelo, h*10)
    if ataca_derecha:
        esquina_inf, esquina_sup = (w*10, h*10), (w*10, -h*10)
    else:
        esquina_inf, esquina_sup = (-w*10, h*10), (-w*10, -h*10)
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

# --- GUI CLASE PRINCIPAL ---
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class VarProInterseccionApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("VAR Pro - Intersection Edition (Líneas)")
        self.geometry("1400x850")
        if os.path.exists("icono.ico"):
            self.iconbitmap("icono.ico")
        
        # Estados
        self.fase = 0
        self.pts_fuga = []
        self.pts_def = []
        self.pts_att = []
        self.pts_lim = []
        
        self.punto_fuga = None
        self.imagen_original = None
        self.imagen_base_dibujada = None
        self.scale_factor = 1.0
        self.img_x_offset = 0
        self.img_y_offset = 0
        
        self.ataca_derecha = True
        self.mostrar_lineas_fuga = True
        self.mouse_x, self.mouse_y = 0, 0
        self.ruta_imagen = ""

        # UI Layout
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Panel Izquierdo (Controles)
        self.panel_izq = ctk.CTkFrame(self, width=300, corner_radius=0)
        self.panel_izq.grid(row=0, column=0, sticky="nsew")
        self.panel_izq.grid_rowconfigure(10, weight=1) # Spacer

        self.lbl_titulo = ctk.CTkLabel(self.panel_izq, text="VAR PRO (Líneas)", font=ctk.CTkFont(size=24, weight="bold"))
        self.lbl_titulo.grid(row=0, column=0, padx=20, pady=(20, 10))

        self.btn_cargar = ctk.CTkButton(self.panel_izq, text="Cargar Imagen", command=self.cargar_imagen)
        self.btn_cargar.grid(row=1, column=0, padx=20, pady=10)

        # Estado Principal
        self.lbl_fase = ctk.CTkLabel(self.panel_izq, text="Fase 1: Calibración", font=ctk.CTkFont(size=16), text_color="#FF4B44")
        self.lbl_fase.grid(row=2, column=0, padx=20, pady=10)

        self.btn_siguiente = ctk.CTkButton(self.panel_izq, text="Siguiente Fase (Espacio)", command=self.avanzar_fase)
        self.btn_siguiente.grid(row=3, column=0, padx=20, pady=5)

        self.btn_deshacer = ctk.CTkButton(self.panel_izq, text="Deshacer Punto (Z)", command=self.deshacer, fg_color="transparent", border_width=2, text_color=("gray10", "#DCE4EE"))
        self.btn_deshacer.grid(row=4, column=0, padx=20, pady=5)

        # Switches
        self.switch_ataque = ctk.CTkSwitch(self.panel_izq, text="Ataca Derecha", command=self.toggle_ataque)
        self.switch_ataque.select()
        self.switch_ataque.grid(row=5, column=0, padx=20, pady=(20,5), sticky="w")

        self.switch_lineas = ctk.CTkSwitch(self.panel_izq, text="Mostrar Líneas Guía", command=self.toggle_lineas)
        self.switch_lineas.select()
        self.switch_lineas.grid(row=6, column=0, padx=20, pady=5, sticky="w")

        # Equipos
        self.lbl_equipos = ctk.CTkLabel(self.panel_izq, text="Marcador Equipos:", font=ctk.CTkFont(size=12, weight="bold"))
        self.lbl_equipos.grid(row=7, column=0, padx=20, pady=(15, 0), sticky="w")
        
        self.frame_equipos = ctk.CTkFrame(self.panel_izq, fg_color="transparent")
        self.frame_equipos.grid(row=8, column=0, padx=20, pady=5, sticky="ew")
        self.frame_equipos.grid_columnconfigure(0, weight=1)
        self.frame_equipos.grid_columnconfigure(1, weight=1)
        self.entry_equipo1 = ctk.CTkEntry(self.frame_equipos, placeholder_text="Local", width=110)
        self.entry_equipo1.grid(row=0, column=0, padx=(0, 5))
        self.entry_equipo2 = ctk.CTkEntry(self.frame_equipos, placeholder_text="Visit.", width=110)
        self.entry_equipo2.grid(row=0, column=1, padx=(5, 0))
        
        self.entry_equipo1.bind("<FocusOut>", lambda e: self.actualizar_dibujos())
        self.entry_equipo2.bind("<FocusOut>", lambda e: self.actualizar_dibujos())
        self.entry_equipo1.bind("<Return>", lambda e: self.actualizar_dibujos())
        self.entry_equipo2.bind("<Return>", lambda e: self.actualizar_dibujos())

        # Lupa Panel Dedicated
        self.lbl_lupa_title = ctk.CTkLabel(self.panel_izq, text="Lupa de Precisión", font=ctk.CTkFont(size=14, weight="bold"))
        self.lbl_lupa_title.grid(row=9, column=0, padx=20, pady=(15, 0))
        
        self.canvas_lupa = ctk.CTkCanvas(self.panel_izq, width=240, height=240, bg="black", highlightthickness=0)
        self.canvas_lupa.grid(row=10, column=0, padx=20, pady=5, sticky="n")

        self.btn_guardar = ctk.CTkButton(self.panel_izq, text="Exportar Análisis", command=self.guardar_imagen, fg_color="green", hover_color="darkgreen")
        self.btn_guardar.grid(row=11, column=0, padx=20, pady=20)

        # Panel Central (Imagen)
        self.panel_central = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.panel_central.grid(row=0, column=1, sticky="nsew")
        self.panel_central.grid_rowconfigure(0, weight=1)
        self.panel_central.grid_columnconfigure(0, weight=1)

        self.canvas_img = ctk.CTkCanvas(self.panel_central, bg="#1a1a1a", highlightthickness=0)
        self.canvas_img.grid(row=0, column=0, sticky="nsew")
        
        # Controles de Vídeo Nav
        self.frame_video = ctk.CTkFrame(self.panel_central)
        self.frame_video.grid(row=1, column=0, sticky="ew", padx=10, pady=5)
        
        self.btn_prev = ctk.CTkButton(self.frame_video, text="< Ant. Frame", width=120, command=self.prev_frame)
        self.btn_prev.pack(side="left", padx=10, pady=10)
        
        self.slider_video = ctk.CTkSlider(self.frame_video, command=self.slider_cambio_frame)
        self.slider_video.pack(side="left", fill="x", expand=True, padx=10, pady=10)
        
        self.btn_next = ctk.CTkButton(self.frame_video, text="Sig. Frame >", width=120, command=self.next_frame)
        self.btn_next.pack(side="left", padx=10, pady=10)
        
        self.lbl_frame_info = ctk.CTkLabel(self.frame_video, text="Frame: 0 / 0")
        self.lbl_frame_info.pack(side="right", padx=20, pady=10)
        
        self.frame_video.grid_remove() # Oculto al inicio
        
        self.canvas_img.bind("<Button-1>", self.click_imagen)
        self.canvas_img.bind("<Motion>", self.mover_raton)
        self.bind("<Configure>", self.redimensionar_ventana)
        self.bind("<space>", lambda e: self.avanzar_fase())
        self.bind("z", lambda e: self.deshacer())
        self.bind("Z", lambda e: self.deshacer())
        self.bind("<Left>", self.safe_prev_frame)
        self.bind("<Right>", self.safe_next_frame)

    def safe_prev_frame(self, event):
        w = self.focus_get()
        if w and "entry" in str(type(w)).lower(): return
        self.prev_frame()

    def safe_next_frame(self, event):
        w = self.focus_get()
        if w and "entry" in str(type(w)).lower(): return
        self.next_frame()

    def cargar_imagen(self):
        path = filedialog.askopenfilename(filetypes=[("Media", "*.jpg;*.jpeg;*.png;*.bmp;*.webp;*.mp4;*.avi;*.mkv;*.mov")])
        if not path: return
        self.ruta_imagen = path
        _, ext = os.path.splitext(path.lower())
        
        if hasattr(self, "video_cap") and self.video_cap:
            self.video_cap.release()
            self.video_cap = None
            
        if ext in ['.mp4', '.avi', '.mkv', '.mov']:
            self.video_cap = cv2.VideoCapture(path)
            self.total_frames = int(self.video_cap.get(cv2.CAP_PROP_FRAME_COUNT))
            max_idx = max(1, self.total_frames - 1)
            self.slider_video.configure(from_=0, to=max_idx, number_of_steps=max_idx)
            self.frame_video.grid()
            self.current_frame_idx = 0
            self.cargar_frame_actual()
        else:
            self.frame_video.grid_remove()
            self.imagen_original = cv2.imread(path)
            self.reiniciar_fases()

    def reiniciar_fases(self):
        self.fase = 0
        self.pts_fuga.clear()
        self.pts_def.clear()
        self.pts_att.clear()
        self.pts_lim.clear()
        self.punto_fuga = None
        if hasattr(self, 'matriz_homografia'): self.matriz_homografia = None
        self.actualizar_dibujos()

    def cargar_frame_actual(self):
        if not hasattr(self, "video_cap") or not self.video_cap: return
        self.video_cap.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame_idx)
        ret, frame = self.video_cap.read()
        if ret:
            self.imagen_original = frame
            self.lbl_frame_info.configure(text=f"Frame: {self.current_frame_idx} / {self.total_frames}")
            self.slider_video.set(self.current_frame_idx)
            self.reiniciar_fases()
            
    def slider_cambio_frame(self, valor):
        nuevo_frame = int(valor)
        if hasattr(self, "current_frame_idx") and nuevo_frame != self.current_frame_idx:
            self.current_frame_idx = nuevo_frame
            self.cargar_frame_actual()
            
    def prev_frame(self):
        if hasattr(self, "current_frame_idx") and self.current_frame_idx > 0:
            self.current_frame_idx -= 1
            self.cargar_frame_actual()
            
    def next_frame(self):
        if hasattr(self, "video_cap") and self.video_cap and hasattr(self, "current_frame_idx") and self.current_frame_idx < self.total_frames - 1:
            self.current_frame_idx += 1
            self.cargar_frame_actual()

    def avanzar_fase(self):
        if self.fase == 1 and len(self.pts_def) >= 2 and len(self.pts_def) % 2 == 0:
            self.fase = 2
        elif self.fase == 2 and len(self.pts_att) >= 2 and len(self.pts_att) % 2 == 0:
            self.fase = 3
        self.actualizar_dibujos()

    def deshacer(self):
        if self.fase == 3:
            if len(self.pts_lim) > 0: self.pts_lim.pop()
            else: self.fase = 2
        elif self.fase == 2:
            if len(self.pts_att) > 0: self.pts_att.pop()
            else: self.fase = 1
        elif self.fase == 1:
            if len(self.pts_def) > 0: self.pts_def.pop()
            else: self.fase = 0
        elif self.fase == 0:
            if len(self.pts_fuga) > 0: self.pts_fuga.pop()
        self.actualizar_dibujos()

    def toggle_ataque(self):
        self.ataca_derecha = self.switch_ataque.get()
        self.actualizar_dibujos()
        
    def toggle_lineas(self):
        self.mostrar_lineas_fuga = self.switch_lineas.get()
        self.actualizar_dibujos()

    def click_imagen(self, event):
        if self.imagen_original is None: return
        x_orig = int((event.x - self.img_x_offset) / self.scale_factor)
        y_orig = int((event.y - self.img_y_offset) / self.scale_factor)
        
        h, w = self.imagen_original.shape[:2]
        if not (0 <= x_orig < w and 0 <= y_orig < h): return
        
        if self.fase == 0:
            self.pts_fuga.append((x_orig, y_orig))
            if len(self.pts_fuga) == 4: self.fase = 1
        elif self.fase == 1: self.pts_def.append((x_orig, y_orig))
        elif self.fase == 2: self.pts_att.append((x_orig, y_orig))
        elif self.fase == 3: self.pts_lim.append((x_orig, y_orig))
        
        self.actualizar_dibujos()

    def mover_raton(self, event):
        if self.imagen_base_dibujada is None: return
        x_orig = int((event.x - self.img_x_offset) / self.scale_factor)
        y_orig = int((event.y - self.img_y_offset) / self.scale_factor)
        self.mouse_x, self.mouse_y = x_orig, y_orig
        
        h, w = self.imagen_base_dibujada.shape[:2]
        if not (0 <= x_orig < w and 0 <= y_orig < h): return
        
        r = 30
        img_acolchada = cv2.copyMakeBorder(self.imagen_base_dibujada, r, r, r, r, cv2.BORDER_CONSTANT, value=[0,0,0])
        y_p, x_p = y_orig + r, x_orig + r
        recorte = img_acolchada[y_p-r : y_p+r, x_p-r : x_p+r].copy()
        
        if recorte.shape[0] > 0 and recorte.shape[1] > 0:
            zoom_size = 240
            lupa = cv2.resize(recorte, (zoom_size, zoom_size), interpolation=cv2.INTER_CUBIC)
            
            centro = zoom_size // 2
            cv2.line(lupa, (centro, centro - 20), (centro, centro + 20), LALIGA_BLANCO, 1, cv2.LINE_AA)
            cv2.line(lupa, (centro - 20, centro), (centro + 20, centro), LALIGA_BLANCO, 1, cv2.LINE_AA)
            cv2.circle(lupa, (centro, centro), 2, LALIGA_ROJO, -1)
            
            lupa_rgb = cv2.cvtColor(lupa, cv2.COLOR_BGR2RGB)
            self.img_tk_lupa = ImageTk.PhotoImage(image=Image.fromarray(lupa_rgb))
            self.canvas_lupa.create_image(0, 0, anchor="nw", image=self.img_tk_lupa)

    def redimensionar_ventana(self, event):
        if event.widget == self and self.imagen_base_dibujada is not None:
            self.mostrar_imagen()

    def actualizar_dibujos(self):
        if self.imagen_original is None: return
        self.imagen_base_dibujada = self.imagen_original.copy()
        h_img, w_img = self.imagen_base_dibujada.shape[:2]
        
        fases_text = ["Fase 1: Calibrar Fugas", "Fase 2: Defensores", "Fase 3: Atacantes", "Fase 4: Límites del Campo"]
        self.lbl_fase.configure(text=fases_text[self.fase])
        
        if len(self.pts_fuga) >= 4:
            self.punto_fuga = calcular_interseccion(self.pts_fuga[0], self.pts_fuga[1], self.pts_fuga[2], self.pts_fuga[3])

        if self.mostrar_lineas_fuga:
            if len(self.pts_fuga) >= 2:
                p1, p2 = crear_linea_infinita(self.pts_fuga[0], self.pts_fuga[1])
                cv2.line(self.imagen_base_dibujada, p1, p2, LALIGA_BLANCO, 1, cv2.LINE_AA)
            if len(self.pts_fuga) >= 4:
                p1, p2 = crear_linea_infinita(self.pts_fuga[2], self.pts_fuga[3])
                cv2.line(self.imagen_base_dibujada, p1, p2, LALIGA_BLANCO, 1, cv2.LINE_AA)

        mejor_def_proyectado = None
        mejor_x_fondo = None

        if self.punto_fuga is not None and len(self.pts_def) >= 2:
            y_eval = self.pts_def[1][1]  # Altura fija para evitar el cruce de rayos
            
            for i in range(0, len(self.pts_def) - 1, 2):
                p_proyectado, xf = obtener_punto_mas_adelantado(self.pts_def[i], self.pts_def[i+1], self.punto_fuga, y_eval, self.ataca_derecha)
                if mejor_x_fondo is None:
                    mejor_x_fondo = xf
                    mejor_def_proyectado = p_proyectado
                else:
                    if self.ataca_derecha and xf > mejor_x_fondo:
                        mejor_x_fondo, mejor_def_proyectado = xf, p_proyectado
                    elif not self.ataca_derecha and xf < mejor_x_fondo:
                        mejor_x_fondo, mejor_def_proyectado = xf, p_proyectado

            for i in range(0, len(self.pts_def) - 1, 2):
                hombro, pie = self.pts_def[i], self.pts_def[i+1]
                p_proyectado, _ = obtener_punto_mas_adelantado(hombro, pie, self.punto_fuga, y_eval, self.ataca_derecha)
                cv2.line(self.imagen_base_dibujada, hombro, p_proyectado, LALIGA_AZUL, 1, cv2.LINE_AA)
                cv2.line(self.imagen_base_dibujada, (pie[0]-5, pie[1]), (pie[0]+5, pie[1]), LALIGA_AZUL, 1)
                    
                if p_proyectado == mejor_def_proyectado:
                    if self.fase >= 3:
                        self.imagen_base_dibujada = sombrear_zona_fuera_juego(self.imagen_base_dibujada, self.punto_fuga, p_proyectado, self.ataca_derecha, LALIGA_SEC, self.pts_lim)
                    self.imagen_base_dibujada = dibujar_linea_infinita(self.imagen_base_dibujada, self.punto_fuga, p_proyectado, LALIGA_AZUL, 2)
                elif self.mostrar_lineas_fuga:
                    self.imagen_base_dibujada = dibujar_linea_infinita(self.imagen_base_dibujada, self.punto_fuga, p_proyectado, LALIGA_SEC, 1)

        atacantes_fuera_juego = 0
        if self.punto_fuga is not None and mejor_def_proyectado is not None and len(self.pts_att) >= 2:
            y_eval = self.pts_def[1][1]
            for i in range(0, len(self.pts_att) - 1, 2):
                hombro, pie = self.pts_att[i], self.pts_att[i+1]
                p_proyectado, xf = obtener_punto_mas_adelantado(hombro, pie, self.punto_fuga, y_eval, self.ataca_derecha)
                
                esta_adelantado = False
                if self.ataca_derecha and xf > mejor_x_fondo: esta_adelantado = True
                elif not self.ataca_derecha and xf < mejor_x_fondo: esta_adelantado = True
                
                if esta_adelantado:
                    atacantes_fuera_juego += 1
                    color = LALIGA_ROJO
                else:
                    color = LALIGA_VERDE
                    
                cv2.line(self.imagen_base_dibujada, hombro, p_proyectado, color, 1, cv2.LINE_AA)
                cv2.line(self.imagen_base_dibujada, (pie[0]-5, pie[1]), (pie[0]+5, pie[1]), color, 1)
                self.imagen_base_dibujada = dibujar_linea_infinita(self.imagen_base_dibujada, self.punto_fuga, p_proyectado, color, 2)

            if atacantes_fuera_juego > 0:
                ruta_img = "offside.png"
                texto_fallback = "FUERA DE JUEGO"
                color_fallback = LALIGA_ROJO
            else:
                ruta_img = "no_offside.png"
                texto_fallback = "POSICION CORRECTA"
                color_fallback = LALIGA_VERDE
                
            dibujado_img = False
            if os.path.exists(ruta_img):
                overlay = cv2.imread(ruta_img, cv2.IMREAD_UNCHANGED)
                if overlay is not None:
                    target_w = int(w_img * 0.25)
                    if target_w < 300: target_w = 300
                    if target_w > 900: target_w = 900
                    
                    aspect = overlay.shape[1] / overlay.shape[0]
                    target_h = int(target_w / aspect)
                    overlay = cv2.resize(overlay, (target_w, target_h), interpolation=cv2.INTER_LANCZOS4)
                    
                    x_off = 30
                    y_off = h_img - target_h - 30
                    
                    if y_off >= 0 and x_off + target_w <= w_img:
                        if len(overlay.shape) == 3 and overlay.shape[2] == 4:
                            alpha_s = overlay[:, :, 3] / 255.0
                            alpha_l = 1.0 - alpha_s
                            for c in range(3):
                                self.imagen_base_dibujada[y_off:y_off+target_h, x_off:x_off+target_w, c] = (
                                    alpha_s * overlay[:, :, c] +
                                    alpha_l * self.imagen_base_dibujada[y_off:y_off+target_h, x_off:x_off+target_w, c]
                                )
                        else:
                            overlay_bgr = overlay[:,:,:3] if len(overlay.shape)==3 and overlay.shape[2]>=3 else overlay
                            self.imagen_base_dibujada[y_off:y_off+target_h, x_off:x_off+target_w] = overlay_bgr
                        dibujado_img = True
            
            if not dibujado_img:
                cv2.putText(self.imagen_base_dibujada, texto_fallback, (30, h_img - 30), cv2.FONT_HERSHEY_DUPLEX, 1.2, LALIGA_NEGRO, 4, cv2.LINE_AA)
                cv2.putText(self.imagen_base_dibujada, texto_fallback, (30, h_img - 30), cv2.FONT_HERSHEY_DUPLEX, 1.2, color_fallback, 2, cv2.LINE_AA)

        if self.mostrar_lineas_fuga:
            for i in range(len(self.pts_lim)):
                cv2.circle(self.imagen_base_dibujada, self.pts_lim[i], 3, LALIGA_MAGENTA, -1) 
                if i > 0:
                    cv2.line(self.imagen_base_dibujada, self.pts_lim[i-1], self.pts_lim[i], LALIGA_MAGENTA, 1, cv2.LINE_AA)
            if len(self.pts_lim) >= 3:
                 cv2.line(self.imagen_base_dibujada, self.pts_lim[-1], self.pts_lim[0], LALIGA_MAGENTA, 1, cv2.LINE_AA)
            for p in self.pts_fuga: cv2.circle(self.imagen_base_dibujada, p, 2, LALIGA_BLANCO, -1)
            if len(self.pts_def) % 2 != 0: cv2.circle(self.imagen_base_dibujada, self.pts_def[-1], 2, LALIGA_AZUL, -1)
            if len(self.pts_att) % 2 != 0: cv2.circle(self.imagen_base_dibujada, self.pts_att[-1], 2, LALIGA_ROJO, -1)
        
        eq1 = self.entry_equipo1.get().strip().upper()
        eq2 = self.entry_equipo2.get().strip().upper()
        
        if eq1 or eq2:
            if not eq1: eq1 = "LOCAL"
            if not eq2: eq2 = "VISIT."
            texto_marcador = f"{eq1} VS {eq2}"
            
            (text_w, text_h), _ = cv2.getTextSize(texto_marcador, cv2.FONT_HERSHEY_DUPLEX, 1.2, 2)
            margin_x = 20
            margin_y = 15
            x_centro = w_img // 2
            x_inicio = x_centro - (text_w // 2)
            y_base = text_h + 30
            
            cv2.rectangle(self.imagen_base_dibujada, (x_inicio - margin_x, y_base - text_h - margin_y), (x_inicio + text_w + margin_x, y_base + margin_y), LALIGA_NEGRO, -1)
            cv2.rectangle(self.imagen_base_dibujada, (x_inicio - margin_x, y_base - text_h - margin_y), (x_inicio + text_w + margin_x, y_base + margin_y), LALIGA_BLANCO, 2)
            cv2.putText(self.imagen_base_dibujada, texto_marcador, (x_inicio, y_base), cv2.FONT_HERSHEY_DUPLEX, 1.2, LALIGA_BLANCO, 2, cv2.LINE_AA)
            
        self.mostrar_imagen()

    def mostrar_imagen(self):
        if self.imagen_base_dibujada is None: return
        self.canvas_img.update()
        c_width = self.canvas_img.winfo_width()
        c_height = self.canvas_img.winfo_height()
        if c_width <= 1 or c_height <= 1: return
        
        h_orig, w_orig = self.imagen_base_dibujada.shape[:2]
        scale = min(c_width / w_orig, c_height / h_orig)
        self.scale_factor = scale
        new_w, new_h = int(w_orig * scale), int(h_orig * scale)
        
        img_resized = cv2.resize(self.imagen_base_dibujada, (new_w, new_h), interpolation=cv2.INTER_LANCZOS4)
        img_rgb = cv2.cvtColor(img_resized, cv2.COLOR_BGR2RGB)
        self.img_tk = ImageTk.PhotoImage(image=Image.fromarray(img_rgb))
        
        self.img_x_offset = (c_width - new_w) // 2
        self.img_y_offset = (c_height - new_h) // 2
        
        self.canvas_img.delete("all")
        self.canvas_img.create_image(self.img_x_offset, self.img_y_offset, anchor="nw", image=self.img_tk)

    def guardar_imagen(self):
        if self.imagen_base_dibujada is not None and self.ruta_imagen:
            base = os.path.splitext(os.path.basename(self.ruta_imagen))[0]
            count = 1
            out_path = f"{base}_VAR_PRO_LINEAS_{count}.jpg"
            while os.path.exists(out_path):
                count += 1
                out_path = f"{base}_VAR_PRO_LINEAS_{count}.jpg"
            cv2.imwrite(out_path, self.imagen_base_dibujada)
            print(f"Exportado: {out_path}")

if __name__ == "__main__":
    app = VarProInterseccionApp()
    app.mainloop()
