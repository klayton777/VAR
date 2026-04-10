import cv2
import numpy as np
import customtkinter as ctk
from tkinter import filedialog
from PIL import Image, ImageTk
import os
import json

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

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # ━━━ SIDEBAR PREMIUM ━━━
        self.panel_izq = ctk.CTkFrame(self, width=330, corner_radius=0, fg_color="#0d0d11")
        self.panel_izq.grid(row=0, column=0, sticky="nsew")
        self.panel_izq.grid_propagate(False)

        # ── Header con branding ──
        self.frame_header = ctk.CTkFrame(self.panel_izq, fg_color="#14141a", corner_radius=0, height=80)
        self.frame_header.pack(fill="x")
        self.frame_header.pack_propagate(False)
        ctk.CTkLabel(self.frame_header, text="🏟️  VAR PRO", font=ctk.CTkFont(family="Segoe UI", size=24, weight="bold"), text_color="#ffffff").pack(pady=(18, 0))
        ctk.CTkLabel(self.frame_header, text="Offside Analysis — Intersection Mode", font=ctk.CTkFont(size=11), text_color="#6b7280").pack(pady=(0, 8))
        ctk.CTkFrame(self.panel_izq, fg_color="#3b82f6", height=2, corner_radius=0).pack(fill="x")

        # ── Scrollable content ──
        self.scroll_sidebar = ctk.CTkScrollableFrame(self.panel_izq, fg_color="#0d0d11", scrollbar_button_color="#27272a", scrollbar_button_hover_color="#3f3f46")
        self.scroll_sidebar.pack(fill="both", expand=True, padx=0, pady=0)

        # 📁 Archivo
        self._section_label(self.scroll_sidebar, "📁  ARCHIVO")
        self.frame_file = ctk.CTkFrame(self.scroll_sidebar, fg_color="#16161c", corner_radius=12, border_width=1, border_color="#27272a")
        self.frame_file.pack(pady=(0, 8), padx=14, fill="x")
        ctk.CTkButton(self.frame_file, text="Cargar Imagen / Vídeo", command=self.cargar_imagen, fg_color="#3f3f46", hover_color="#52525b", font=ctk.CTkFont(size=13, weight="bold"), height=38, corner_radius=10).pack(pady=12, padx=12, fill="x")

        # 🎯 Estado
        self._section_label(self.scroll_sidebar, "🎯  ESTADO")
        self.frame_progreso = ctk.CTkFrame(self.scroll_sidebar, fg_color="#16161c", corner_radius=12, border_width=1, border_color="#27272a")
        self.frame_progreso.pack(pady=(0, 8), padx=14, fill="x")
        ctk.CTkLabel(self.frame_progreso, text="Fase Actual", font=ctk.CTkFont(size=11), text_color="#6b7280").pack(pady=(10, 0))
        self.lbl_fase = ctk.CTkLabel(self.frame_progreso, text="Fase 1: Calibración", font=ctk.CTkFont(size=14, weight="bold"), text_color="#34d399", wraplength=260)
        self.lbl_fase.pack(pady=(2, 10), padx=10)

        # 🎮 Controles
        self._section_label(self.scroll_sidebar, "🎮  CONTROLES")
        self.frame_btn = ctk.CTkFrame(self.scroll_sidebar, fg_color="transparent")
        self.frame_btn.pack(pady=(0, 8), padx=14, fill="x")
        self.btn_deshacer = ctk.CTkButton(self.frame_btn, text="⟲ Deshacer", command=self.deshacer, fg_color="#dc2626", hover_color="#b91c1c", width=140, height=36, font=ctk.CTkFont(size=13, weight="bold"), corner_radius=10)
        self.btn_deshacer.pack(side="left")
        self.btn_siguiente = ctk.CTkButton(self.frame_btn, text="Siguiente ▸", command=self.avanzar_fase, fg_color="#2563eb", hover_color="#1d4ed8", width=140, height=36, font=ctk.CTkFont(size=13, weight="bold"), corner_radius=10)
        self.btn_siguiente.pack(side="right")

        # ⚙️ Opciones
        self._section_label(self.scroll_sidebar, "⚙️  OPCIONES")
        self.frame_opt = ctk.CTkFrame(self.scroll_sidebar, fg_color="#16161c", corner_radius=12, border_width=1, border_color="#27272a")
        self.frame_opt.pack(pady=(0, 8), padx=14, fill="x")
        
        self.switch_ataque = ctk.CTkSwitch(self.frame_opt, text="Ataca Derecha", command=self.toggle_ataque, progress_color="#3b82f6", button_color="#60a5fa", button_hover_color="#93c5fd")
        self.switch_ataque.select()
        self.switch_ataque.pack(pady=(12, 6), padx=12, anchor="w")

        self.switch_lineas = ctk.CTkSwitch(self.frame_opt, text="Mostrar Líneas Guía", command=self.toggle_lineas, progress_color="#3b82f6", button_color="#60a5fa", button_hover_color="#93c5fd")
        self.switch_lineas.select()
        self.switch_lineas.pack(pady=(6, 12), padx=12, anchor="w")

        # ⚽ Equipos
        self._section_label(self.scroll_sidebar, "⚽  EQUIPOS")
        self.frame_equipos_card = ctk.CTkFrame(self.scroll_sidebar, fg_color="#16161c", corner_radius=12, border_width=1, border_color="#27272a")
        self.frame_equipos_card.pack(pady=(0, 8), padx=14, fill="x")
        
        self.frame_equipos = ctk.CTkFrame(self.frame_equipos_card, fg_color="transparent")
        self.frame_equipos.pack(pady=10, padx=12, fill="x")
        
        self.entry_equipo1 = ctk.CTkEntry(self.frame_equipos, placeholder_text="Local", width=120, fg_color="#27272a", border_color="#3f3f46", corner_radius=8)
        self.entry_equipo1.pack(side="left", expand=True, padx=(0, 5))
        self.entry_equipo2 = ctk.CTkEntry(self.frame_equipos, placeholder_text="Visit.", width=120, fg_color="#27272a", border_color="#3f3f46", corner_radius=8)
        self.entry_equipo2.pack(side="left", expand=True, padx=(5, 0))
        
        self.entry_equipo1.bind("<FocusOut>", lambda e: self.actualizar_dibujos())
        self.entry_equipo2.bind("<FocusOut>", lambda e: self.actualizar_dibujos())
        self.entry_equipo1.bind("<Return>", lambda e: self.actualizar_dibujos())
        self.entry_equipo2.bind("<Return>", lambda e: self.actualizar_dibujos())

        # 🔍 Lupa
        self._section_label(self.scroll_sidebar, "🔍  LUPA ×8")
        self.frame_lupa = ctk.CTkFrame(self.scroll_sidebar, fg_color="#16161c", corner_radius=12, border_width=1, border_color="#27272a")
        self.frame_lupa.pack(pady=(0, 8), padx=14, fill="x")
        self.canvas_lupa = ctk.CTkCanvas(self.frame_lupa, width=220, height=220, bg="#050507", highlightthickness=1, highlightbackground="#27272a")
        self.canvas_lupa.pack(pady=12, padx=12)

        # ── Export Footer (fijo abajo) ──
        self.frame_export = ctk.CTkFrame(self.panel_izq, fg_color="#14141a", corner_radius=0, border_width=0)
        self.frame_export.pack(side="bottom", fill="x")
        ctk.CTkFrame(self.panel_izq, fg_color="#27272a", height=1, corner_radius=0).pack(side="bottom", fill="x")
        
        self.btn_guardar = ctk.CTkButton(self.frame_export, text="📸 Exportar Imagen", command=self.guardar_imagen, fg_color="#059669", hover_color="#047857", height=34, corner_radius=10, font=ctk.CTkFont(size=12, weight="bold"))
        self.btn_guardar.pack(pady=(10, 3), padx=12, fill="x")
        
        self.btn_video = ctk.CTkButton(self.frame_export, text="🎬 Exportar Vídeo", command=self.guardar_video, fg_color="#e11d48", hover_color="#be123c", height=34, corner_radius=10, font=ctk.CTkFont(size=12, weight="bold"))
        self.btn_video.pack(pady=3, padx=12, fill="x")
        ctk.CTkButton(self.frame_export, text="💾 Guardar Proyecto", command=self.guardar_proyecto, fg_color="#4f46e5", hover_color="#4338ca", height=34, corner_radius=10, font=ctk.CTkFont(size=12, weight="bold")).pack(pady=3, padx=12, fill="x")
        ctk.CTkButton(self.frame_export, text="📂 Cargar Proyecto", command=self.cargar_proyecto, fg_color="#7c3aed", hover_color="#6d28d9", height=34, corner_radius=10, font=ctk.CTkFont(size=12, weight="bold")).pack(pady=(3, 6), padx=12, fill="x")

        self.lbl_info = ctk.CTkLabel(self.frame_export, text="", text_color="#6b7280", font=ctk.CTkFont(size=10))
        self.lbl_info.pack(pady=(0, 2))
        ctk.CTkLabel(self.frame_export, text="VAR TECH™ v2.0", font=ctk.CTkFont(size=9), text_color="#3f3f46").pack(pady=(0, 8))

        # ━━━ PANEL CENTRAL ━━━
        self.panel_central = ctk.CTkFrame(self, corner_radius=0, fg_color="#050507")
        self.panel_central.grid(row=0, column=1, sticky="nsew")
        self.panel_central.grid_rowconfigure(0, weight=1)
        self.panel_central.grid_columnconfigure(0, weight=1)

        self.canvas_img = ctk.CTkCanvas(self.panel_central, bg="#050507", highlightthickness=0)
        self.canvas_img.grid(row=0, column=0, sticky="nsew")
        
        # Controles de Vídeo Nav
        self.frame_video = ctk.CTkFrame(self.panel_central, fg_color="#14141a", corner_radius=10, border_width=1, border_color="#27272a")
        self.frame_video.grid(row=1, column=0, sticky="ew", padx=20, pady=10)
        
        self.btn_prev = ctk.CTkButton(self.frame_video, text="◂ Anterior", width=110, command=self.prev_frame, fg_color="#3f3f46", hover_color="#52525b", corner_radius=8, height=32)
        self.btn_prev.pack(side="left", padx=10, pady=10)
        
        self.slider_video = ctk.CTkSlider(self.frame_video, command=self.slider_cambio_frame, button_color="#3b82f6", button_hover_color="#60a5fa", progress_color="#3b82f6")
        self.slider_video.pack(side="left", fill="x", expand=True, padx=10, pady=10)
        
        self.btn_next = ctk.CTkButton(self.frame_video, text="Siguiente ▸", width=110, command=self.next_frame, fg_color="#3f3f46", hover_color="#52525b", corner_radius=8, height=32)
        self.btn_next.pack(side="left", padx=10, pady=10)
        
        self.lbl_frame_info = ctk.CTkLabel(self.frame_video, text="Frame: 0 / 0", text_color="#6b7280", font=ctk.CTkFont(size=12, weight="bold"))
        self.lbl_frame_info.pack(side="right", padx=20, pady=10)
        
        self.frame_video.grid_remove()
        
        self.canvas_img.bind("<Button-1>", self.click_imagen)
        self.canvas_img.bind("<Motion>", self.mover_raton)
        self.bind("<Configure>", self.redimensionar_ventana)
        self.bind("<space>", lambda e: self.avanzar_fase())
        self.bind("z", lambda e: self.deshacer())
        self.bind("Z", lambda e: self.deshacer())
        self.bind("<Left>", self.safe_prev_frame)
        self.bind("<Right>", self.safe_next_frame)
        self.bind("<Control-s>", lambda e: self.guardar_proyecto())
        self.bind("<Control-o>", lambda e: self.cargar_proyecto())

    def _section_label(self, parent, text):
        ctk.CTkLabel(parent, text=text, font=ctk.CTkFont(size=10, weight="bold"), text_color="#4b5563", anchor="w").pack(pady=(12, 4), padx=16, fill="x")


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
        self.lbl_fase.configure(text=fases_text[min(self.fase, 3)])
        
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
                        self.imagen_base_dibujada = sombrear_zona_fuera_juego(self.imagen_base_dibujada, self.punto_fuga, p_proyectado, self.ataca_derecha, (255, 255, 0), self.pts_lim)
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
            
            font = cv2.FONT_HERSHEY_DUPLEX
            scale = 0.35
            thick = 1
            
            (tw_1, th_1), _ = cv2.getTextSize(eq1, font, scale, thick)
            (tw_v, th_v), _ = cv2.getTextSize("VS", font, scale, thick)
            (tw_2, th_2), _ = cv2.getTextSize(eq2, font, scale, thick)
            
            pad_x = 8
            pad_y = 6
            
            def find_shield(eq_name):
                base = os.path.join("escudos", eq_name.lower())
                for ext in [".png", ".webp", ".jpg", ".jpeg"]:
                    if os.path.exists(base + ext): return base + ext
                return None
            
            shield1_path = find_shield(eq1)
            shield2_path = find_shield(eq2)
            has_s1 = shield1_path is not None
            has_s2 = shield2_path is not None
            
            s_size = 14
            s_pad = 5
            w_s1 = (s_size + s_pad) if has_s1 else 0
            w_s2 = (s_size + s_pad) if has_s2 else 0

            box_w_1 = tw_1 + pad_x * 2 + w_s1
            box_w_v = tw_v + pad_x * 2
            box_w_2 = tw_2 + pad_x * 2 + w_s2
            h_box = max(th_1, th_v, th_2) + pad_y * 2
            
            x_start = 30
            y_start = 30
            y_end = y_start + h_box
            
            # Dibujar fondo cajas principales (Gris muy oscuro y Rojo LaLiga en medio)
            cv2.rectangle(self.imagen_base_dibujada, (x_start, y_start), (x_start + box_w_1, y_end), (35, 35, 35), -1)
            x_m = x_start + box_w_1
            cv2.rectangle(self.imagen_base_dibujada, (x_m, y_start), (x_m + box_w_v, y_end), LALIGA_ROJO, -1)
            x_m2 = x_m + box_w_v
            cv2.rectangle(self.imagen_base_dibujada, (x_m2, y_start), (x_m2 + box_w_2, y_end), (35, 35, 35), -1)
            
            # Franja inferior decorativa
            line_h = 3
            cv2.rectangle(self.imagen_base_dibujada, (x_start, y_end), (x_start + box_w_1, y_end + line_h), (200, 200, 200), -1)
            cv2.rectangle(self.imagen_base_dibujada, (x_m, y_end), (x_m + box_w_v, y_end + line_h), (10, 10, 10), -1)
            cv2.rectangle(self.imagen_base_dibujada, (x_m2, y_end), (x_m2 + box_w_2, y_end + line_h), (200, 200, 200), -1)
            
            def overlay_shield(img, path, sx, sy, size):
                shield = cv2.imread(path, cv2.IMREAD_UNCHANGED)
                if shield is not None:
                    shield = cv2.resize(shield, (size, size), interpolation=cv2.INTER_LANCZOS4)
                    if len(shield.shape) == 3 and shield.shape[2] == 4:
                        alpha_s = shield[:, :, 3] / 255.0
                        alpha_l = 1.0 - alpha_s
                        try:
                            for c in range(3):
                                img[sy:sy+size, sx:sx+size, c] = (alpha_s * shield[:, :, c] + alpha_l * img[sy:sy+size, sx:sx+size, c])
                        except Exception: pass
                    else:
                        shield_bgr = shield[:,:,:3] if len(shield.shape)==3 and shield.shape[2]>=3 else shield
                        try: img[sy:sy+size, sx:sx+size] = shield_bgr
                        except: pass

            if has_s1:
                sy = y_start + (h_box - s_size) // 2
                overlay_shield(self.imagen_base_dibujada, shield1_path, x_start + pad_x, sy, s_size)
            if has_s2:
                sy = y_start + (h_box - s_size) // 2
                overlay_shield(self.imagen_base_dibujada, shield2_path, x_m2 + pad_x, sy, s_size)

            # Textos
            th_max = max(th_1, th_v, th_2)
            ty = y_start + (h_box + th_max) // 2 - 2
            
            tx_1 = x_start + pad_x + w_s1 + (box_w_1 - pad_x*2 - w_s1 - tw_1)//2
            cv2.putText(self.imagen_base_dibujada, eq1, (tx_1, ty), font, scale, LALIGA_BLANCO, thick, cv2.LINE_AA)
            tx_v = x_m + (box_w_v - tw_v) // 2
            cv2.putText(self.imagen_base_dibujada, "VS", (tx_v, ty), font, scale, LALIGA_BLANCO, thick, cv2.LINE_AA)
            tx_2 = x_m2 + pad_x + w_s2 + (box_w_2 - pad_x*2 - w_s2 - tw_2)//2
            cv2.putText(self.imagen_base_dibujada, eq2, (tx_2, ty), font, scale, LALIGA_BLANCO, thick, cv2.LINE_AA)
            
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
            self.lbl_info.configure(text=f"Exportado: {os.path.basename(out_path)}")
            print(f"Exportado: {out_path}")

    def guardar_video(self):
        if self.imagen_base_dibujada is None or self.imagen_original is None: return
        if not self.ruta_imagen: return
        
        base = os.path.splitext(os.path.basename(self.ruta_imagen))[0]
        count = 1
        out_path = f"{base}_VAR_ANIM_{count}.mp4"
        while os.path.exists(out_path):
            count += 1
            out_path = f"{base}_VAR_ANIM_{count}.mp4"
            
        h, w = self.imagen_original.shape[:2]
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(out_path, fourcc, 30.0, (w, h))
        
        fps = 30
        frame0 = self.imagen_original.copy()
        
        pf = calcular_interseccion(self.pts_fuga[0], self.pts_fuga[1], self.pts_fuga[2], self.pts_fuga[3])
        y_eval = self.pts_def[1][1]
        m_x, m_def, def_sh = None, None, None
        for i in range(0, len(self.pts_def) - 1, 2):
            p, xf = obtener_punto_mas_adelantado(self.pts_def[i], self.pts_def[i+1], pf, y_eval, self.ataca_derecha)
            if m_x is None or (self.ataca_derecha and xf > m_x) or (not self.ataca_derecha and xf < m_x):
                m_x, m_def, def_sh = xf, p, self.pts_def[i]
                
        att_lines = []
        for i in range(0, len(self.pts_att) - 1, 2):
            p, xf = obtener_punto_mas_adelantado(self.pts_att[i], self.pts_att[i+1], pf, y_eval, self.ataca_derecha)
            adelantado = (xf > m_x) if self.ataca_derecha else (xf < m_x)
            color = LALIGA_ROJO if adelantado else LALIGA_VERDE
            att_lines.append((p, self.pts_att[i], color))

        max_w = w * 1.5
        def draw_growing_line(img, p_fuga, p_center, color, prog):
            x1, y1 = p_fuga; x2, y2 = p_center
            if x1 == x2:
                yt, yb = int(y2 - max_w * prog), int(y2 + max_w * prog)
                cv2.line(img, (x1, yt), (x1, yb), color, 2, cv2.LINE_AA)
            else:
                m = (y2 - y1) / (x2 - x1 + 0.0001)
                b = y1 - m * x1
                xl, xr = int(x2 - max_w * prog), int(x2 + max_w * prog)
                yl, yr = int(m * xl + b), int(m * xr + b)
                cv2.line(img, p_center, (xl, yl), color, 2, cv2.LINE_AA)
                cv2.line(img, p_center, (xr, yr), color, 2, cv2.LINE_AA)

        frames_clean = int(fps * 1.5)
        frames_def = int(fps * 2.0)
        frames_att = int(fps * 2.0)
        frames_shadow = int(fps * 2.0)
        frames_end = int(fps * 4.0)

        for _ in range(frames_clean): out.write(frame0)
        
        frame1 = frame0.copy()
        if m_def is not None: cv2.line(frame1, def_sh, m_def, LALIGA_AZUL, 1, cv2.LINE_AA)
        
        for i in range(frames_def):
            f_anim = frame1.copy()
            if m_def is not None: draw_growing_line(f_anim, pf, m_def, LALIGA_AZUL, (i+1)/frames_def)
            out.write(f_anim)
            
        if m_def is not None: frame1 = dibujar_linea_infinita(frame1, pf, m_def, LALIGA_AZUL, 2)
        
        for att_p, att_sh, att_col in att_lines:
            cv2.line(frame1, att_sh, att_p, att_col, 1, cv2.LINE_AA)
            
        for i in range(frames_att):
            f_anim = frame1.copy()
            for att_p, att_sh, att_col in att_lines: draw_growing_line(f_anim, pf, att_p, att_col, (i+1)/frames_att)
            out.write(f_anim)
            
        frame2 = frame1.copy()
        for att_p, _, att_col in att_lines:
            frame2 = dibujar_linea_infinita(frame2, pf, att_p, att_col, 2)
            
        frame3_fully_shaded = frame2.copy()
        if m_def is not None and len(self.pts_att) >= 2:
            frame3_fully_shaded = sombrear_zona_fuera_juego(frame3_fully_shaded, pf, m_def, self.ataca_derecha, (255, 255, 0), self.pts_lim)
            
        for i in range(frames_shadow):
            prog = (i + 1) / frames_shadow
            f_anim = cv2.addWeighted(frame3_fully_shaded, prog, frame2, 1.0 - prog, 0)
            out.write(f_anim)
            
        for _ in range(frames_end): out.write(self.imagen_base_dibujada)
            
        out.release()
        self.lbl_info.configure(text=f"Vídeo: {os.path.basename(out_path)}")
        print(f"Vídeo Exportado: {out_path}")

    def guardar_proyecto(self):
        if self.imagen_original is None or not self.ruta_imagen:
            self.lbl_info.configure(text="Nada que guardar"); return
        proj = {
            "ruta_img": self.ruta_imagen,
            "pts_fuga": [list(p) for p in self.pts_fuga],
            "pts_def": [list(p) for p in self.pts_def],
            "pts_att": [list(p) for p in self.pts_att],
            "pts_lim": [list(p) for p in self.pts_lim],
            "fase": self.fase,
            "ataca_derecha": self.ataca_derecha,
            "equipo1": self.entry_equipo1.get(),
            "equipo2": self.entry_equipo2.get(),
        }
        path = filedialog.asksaveasfilename(defaultextension=".varproj",
                                            filetypes=[("VAR Proyecto", "*.varproj")],
                                            title="Guardar Proyecto")
        if not path: return
        with open(path, "w", encoding="utf-8") as f:
            json.dump(proj, f, indent=2)
        self.lbl_info.configure(text=f"Proyecto: {os.path.basename(path)}")

    def cargar_proyecto(self):
        path = filedialog.askopenfilename(filetypes=[("VAR Proyecto", "*.varproj"), ("Todos", "*.*")],
                                          title="Cargar Proyecto")
        if not path: return
        try:
            with open(path, "r", encoding="utf-8") as f:
                proj = json.load(f)
        except Exception as e:
            self.lbl_info.configure(text=f"Error: {e}"); return
        
        ruta = proj.get("ruta_img", "")
        if not os.path.exists(ruta):
            self.lbl_info.configure(text=f"Imagen no encontrada"); return
        
        self.ruta_imagen = ruta
        self.imagen_original = cv2.imread(ruta)
        if self.imagen_original is None:
            self.lbl_info.configure(text="Error al leer imagen"); return
        
        self.pts_fuga = [tuple(p) for p in proj.get("pts_fuga", [])]
        self.pts_def = [tuple(p) for p in proj.get("pts_def", [])]
        self.pts_att = [tuple(p) for p in proj.get("pts_att", [])]
        self.pts_lim = [tuple(p) for p in proj.get("pts_lim", [])]
        self.fase = proj.get("fase", 0)
        self.ataca_derecha = proj.get("ataca_derecha", True)
        
        if self.ataca_derecha: self.switch_ataque.select()
        else: self.switch_ataque.deselect()
        
        eq1 = proj.get("equipo1", "")
        eq2 = proj.get("equipo2", "")
        self.entry_equipo1.delete(0, "end"); self.entry_equipo1.insert(0, eq1)
        self.entry_equipo2.delete(0, "end"); self.entry_equipo2.insert(0, eq2)
        
        self.actualizar_dibujos()
        self.lbl_info.configure(text=f"Proyecto cargado: {os.path.basename(path)}")

if __name__ == "__main__":
    app = VarProInterseccionApp()
    app.mainloop()
