import cv2
import numpy as np
import customtkinter as ctk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
import os
import math
import json

LALIGA_ROJO, LALIGA_VERDE, LALIGA_BLANCO, LALIGA_NEGRO = (68, 75, 255), (0, 220, 0), (255, 255, 255), (0, 0, 0)
LALIGA_MAGENTA, LALIGA_SEC = (255, 0, 255), (255, 100, 50)

def distancia_punto_recta(pt, linea_p1, linea_p2):
    vx, vy = float(linea_p2[0] - linea_p1[0]), float(linea_p2[1] - linea_p1[1])
    mag = math.hypot(vx, vy)
    if mag == 0: return 0.0, (0.0, 0.0)
    vx, vy = vx / mag, vy / mag
    nx, ny = -vy, vx
    dist = (float(pt[0]) - float(linea_p1[0])) * nx + (float(pt[1]) - float(linea_p1[1])) * ny
    return dist, (nx, ny)

class GoalLineApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Ojo de Halcón - Goal Line PRO")
        self.geometry("1400x850")
        if os.path.exists("icono.ico"): self.iconbitmap("icono.ico")
        
        self.fase = 1
        self.linea_gol = []
        self.linea_ext = []
        self.p_centro = None
        self.radio_balon = 15.0
        self.drag_mode = None
        self.grosor_linea_cm = 12.0
        self.modo_juego = "GOL"
        self.mostrar_guias = True
        
        self.img_orig = None
        self.img_dibujada = None
        self.scale_factor = 1.0
        self.img_x_off = 0
        self.img_y_off = 0
        self.ruta_img = ""
        
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
        ctk.CTkLabel(self.frame_header, text="⚽  VAR PRO", font=ctk.CTkFont(family="Segoe UI", size=24, weight="bold"), text_color="#ffffff").pack(pady=(18, 0))
        ctk.CTkLabel(self.frame_header, text="Goal Line Technology — Hawk Eye", font=ctk.CTkFont(size=11), text_color="#6b7280").pack(pady=(0, 8))
        # Línea de acento
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
        self.lbl_fase = ctk.CTkLabel(self.frame_progreso, text="Fase 1: Borde de ADENTRO", font=ctk.CTkFont(size=14, weight="bold"), text_color="#34d399", wraplength=260)
        self.lbl_fase.pack(pady=(2, 10), padx=10)
        
        # ⚙️ Opciones
        self._section_label(self.scroll_sidebar, "⚙️  OPCIONES")
        self.frame_opt = ctk.CTkFrame(self.scroll_sidebar, fg_color="#16161c", corner_radius=12, border_width=1, border_color="#27272a")
        self.frame_opt.pack(pady=(0, 8), padx=14, fill="x")
        self.cmb_modo = ctk.CTkOptionMenu(self.frame_opt, values=["Gol / No Gol", "Fuera / Dentro"], command=self.cambiar_modo, fg_color="#27272a", button_color="#3f3f46", button_hover_color="#52525b", corner_radius=8, font=ctk.CTkFont(size=12))
        self.cmb_modo.pack(pady=(12, 6), padx=12, fill="x")
        self.cmb_modo.set("Fuera / Dentro")
        self.modo_juego = "FUERA"
        
        # 📏 Grosor Línea
        self.frame_grosor = ctk.CTkFrame(self.scroll_sidebar, fg_color="#16161c", corner_radius=12, border_width=1, border_color="#27272a")
        self.frame_grosor.pack(pady=(0, 8), padx=14, fill="x")
        self.lbl_grosor = ctk.CTkLabel(self.frame_grosor, text="Grosor Línea: 12.0 cm", font=ctk.CTkFont(size=12), text_color="#a1a1aa")
        self.lbl_grosor.pack(pady=(10, 0))
        self.slider_grosor = ctk.CTkSlider(self.frame_grosor, from_=5, to=20, number_of_steps=150, command=self.cambiar_grosor, progress_color="#3b82f6", button_color="#60a5fa", button_hover_color="#93c5fd")
        self.slider_grosor.set(12.0)
        self.slider_grosor.pack(pady=(4, 12), padx=14, fill="x")
        
        # 🎮 Controles
        self._section_label(self.scroll_sidebar, "🎮  CONTROLES")
        self.frame_btn = ctk.CTkFrame(self.scroll_sidebar, fg_color="transparent")
        self.frame_btn.pack(pady=(0, 8), padx=14, fill="x")
        ctk.CTkButton(self.frame_btn, text="⟲ Deshacer", command=self.deshacer, fg_color="#dc2626", hover_color="#b91c1c", width=140, height=36, font=ctk.CTkFont(size=13, weight="bold"), corner_radius=10).pack(side="left")
        ctk.CTkButton(self.frame_btn, text="Siguiente ▸", command=self.siguiente_fase, fg_color="#2563eb", hover_color="#1d4ed8", width=140, height=36, font=ctk.CTkFont(size=13, weight="bold"), corner_radius=10).pack(side="right")
        
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
        
        ctk.CTkButton(self.frame_export, text="📸 Exportar Imagen", command=self.guardar_imagen, fg_color="#059669", hover_color="#047857", height=34, corner_radius=10, font=ctk.CTkFont(size=12, weight="bold")).pack(pady=(10, 3), padx=12, fill="x")
        ctk.CTkButton(self.frame_export, text="🎬 Exportar Vídeo 3D", command=self.guardar_video, fg_color="#e11d48", hover_color="#be123c", height=34, corner_radius=10, font=ctk.CTkFont(size=12, weight="bold")).pack(pady=3, padx=12, fill="x")
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

        self.canvas_img.bind("<Button-1>", self.click_img)
        self.canvas_img.bind("<B1-Motion>", self.arrastrar_raton)
        self.canvas_img.bind("<ButtonRelease-1>", self.soltar_raton)
        self.canvas_img.bind("<Motion>", self.mover_raton)
        self.canvas_img.bind("<MouseWheel>", self.rueda_raton)
        self.bind("<Configure>", self.redimensionar)
        self.bind("z", lambda e: self.deshacer())
        self.bind("Z", lambda e: self.deshacer())
        self.bind("<space>", lambda e: self.siguiente_fase())
        self.bind("<Left>", self.tecla_flecha)
        self.bind("<Right>", self.tecla_flecha)
        self.bind("<Up>", self.tecla_flecha)
        self.bind("<Down>", self.tecla_flecha)
        self.bind("c", lambda e: self.reiniciar())
        self.bind("C", lambda e: self.reiniciar())
        self.bind("h", self.toggle_guias)
        self.bind("H", self.toggle_guias)
        self.bind("<Control-s>", lambda e: self.guardar_proyecto())
        self.bind("<Control-o>", lambda e: self.cargar_proyecto())

    def _section_label(self, parent, text):
        """Crea un label de sección estilizado para el sidebar."""
        ctk.CTkLabel(parent, text=text, font=ctk.CTkFont(size=10, weight="bold"), text_color="#4b5563", anchor="w").pack(pady=(12, 4), padx=16, fill="x")

    def next_frame(self):
        if hasattr(self, "video_cap") and self.video_cap and hasattr(self, "current_frame_idx"):
            if self.current_frame_idx < self.total_frames - 1:
                self.current_frame_idx += 1; self.cargar_frame_actual()

    def prev_frame(self):
        if hasattr(self, "current_frame_idx") and self.current_frame_idx > 0:
            self.current_frame_idx -= 1; self.cargar_frame_actual()

    def slider_cambio_frame(self, valor):
        nuevo = int(valor)
        if hasattr(self, "current_frame_idx") and nuevo != self.current_frame_idx:
            self.current_frame_idx = nuevo; self.cargar_frame_actual()

    def tecla_flecha(self, event):
        if self.fase >= 3 and self.p_centro:
            x, y = self.p_centro
            if event.keysym == "Left": x -= 1
            elif event.keysym == "Right": x += 1
            elif event.keysym == "Up": y -= 1
            elif event.keysym == "Down": y += 1
            self.p_centro = (x, y); self.actualizar()
        else:
            if event.keysym == "Left": self.prev_frame()
            elif event.keysym == "Right": self.next_frame()

    def toggle_guias(self, event=None):
        self.mostrar_guias = not self.mostrar_guias; self.actualizar()

    def cargar_imagen(self):
        path = filedialog.askopenfilename(filetypes=[("Media", "*.jpg;*.jpeg;*.png;*.webp;*.bmp;*.mp4;*.mkv;*.avi;*.mov")])
        if not path: return
        self.ruta_img = path
        _, ext = os.path.splitext(path.lower())
        if hasattr(self, "video_cap") and self.video_cap: self.video_cap.release(); self.video_cap = None
        if ext in ['.mp4', '.avi', '.mkv', '.mov']:
            self.video_cap = cv2.VideoCapture(path)
            self.total_frames = int(self.video_cap.get(cv2.CAP_PROP_FRAME_COUNT))
            self.slider_video.configure(from_=0, to=self.total_frames-1, number_of_steps=self.total_frames-1)
            self.frame_video.grid(); self.current_frame_idx = 0; self.cargar_frame_actual()
        else:
            self.frame_video.grid_remove(); self.img_orig = cv2.imread(path); self.reiniciar()

    def cargar_frame_actual(self):
        if not hasattr(self, "video_cap") or not self.video_cap: return
        self.video_cap.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame_idx)
        ret, frame = self.video_cap.read()
        if ret:
            self.img_orig = frame
            self.lbl_frame_info.configure(text=f"Frame: {self.current_frame_idx}/{self.total_frames}")
            self.slider_video.set(self.current_frame_idx); self.actualizar()

    def reiniciar(self):
        self.fase = 1; self.linea_gol.clear(); self.linea_ext.clear(); self.p_centro = None
        self.radio_balon = 15.0; self.drag_mode = None; self.actualizar()

    def cambiar_grosor(self, val):
        self.grosor_linea_cm = round(float(val), 1)
        self.lbl_grosor.configure(text=f"Grosor Línea: {self.grosor_linea_cm} cm"); self.actualizar()

    def deshacer(self):
        if self.fase == 4: self.fase = 3
        elif self.fase == 3 and self.p_centro: self.p_centro = None
        elif self.fase == 3: self.fase = 2; self.linea_ext = []
        elif self.fase == 2 and self.linea_ext: self.linea_ext.pop()
        elif self.fase == 1 and self.linea_gol: self.linea_gol.pop()
        self.actualizar()
        
    def siguiente_fase(self):
        if self.fase == 1 and len(self.linea_gol) == 2: self.fase = 2
        elif self.fase == 2 and len(self.linea_ext) == 2: self.fase = 3
        elif self.fase == 3 and self.p_centro: self.fase = 4
        self.actualizar()

    def click_img(self, event):
        if self.img_orig is None: return
        x = int((event.x - self.img_x_off) / self.scale_factor)
        y = int((event.y - self.img_y_off) / self.scale_factor)
        h, w = self.img_orig.shape[:2]
        if not (0 <= x < w and 0 <= y < h): return
        if self.fase == 1:
            if len(self.linea_gol) < 2:
                self.linea_gol.append((x, y))
                if len(self.linea_gol) == 2: self.fase = 2
        elif self.fase == 2:
            if len(self.linea_ext) < 2:
                self.linea_ext.append((x, y))
                if len(self.linea_ext) == 2: self.fase = 3
        elif self.fase == 3:
            self.p_centro = (x, y); self.drag_mode = "move"
        self.actualizar()

    def arrastrar_raton(self, event):
        if self.img_orig is None or self.fase < 3 or not self.p_centro or self.drag_mode != "move": return
        x = int((event.x - self.img_x_off) / self.scale_factor)
        y = int((event.y - self.img_y_off) / self.scale_factor)
        h, w = self.img_orig.shape[:2]
        self.p_centro = (max(0, min(w-1, x)), max(0, min(h-1, y)))
        self.actualizar(); self.mover_raton(event)

    def soltar_raton(self, event): self.drag_mode = None

    def cambiar_modo(self, valor):
        self.modo_juego = "GOL" if "Gol" in valor else "FUERA"; self.actualizar()

    def rueda_raton(self, event):
        if self.fase >= 3 and self.p_centro:
            if event.delta > 0: self.radio_balon += 1.0
            elif event.delta < 0: self.radio_balon = max(1.0, self.radio_balon - 1.0)
            self.actualizar()

    def dibujar_minimapa(self, radio_cm, margen_cm, es_gol, w_mini=400, h_mini=250):
        """
        Minimapa 3D. La posición del balón se deriva DIRECTAMENTE de margen_cm:
        - margen_cm > 0: balón completamente pasado la línea (FUERA/GOL)
        - margen_cm < 0: balón aún toca o está dentro (DENTRO/NO GOL)
        El borde interior del balón está a margen_cm del borde exterior de la línea.
        """
        minimapa = np.zeros((h_mini, w_mini, 3), dtype=np.uint8)
        c1, c2 = (30, 110, 30), (25, 95, 25)
        for i in range(0, w_mini, 40):
            cv2.rectangle(minimapa, (i, 0), (i+40, h_mini), c1 if (i // 40) % 2 == 0 else c2, -1)
        
        S = 1.0  # escala cm → px minimapa (1cm = 1px)
        g_px = int(6.0 * S)  # grosor línea en minimapa (6px)
        x_linea_in = w_mini // 3  # borde interior (césped)
        x_linea_out = x_linea_in + g_px  # borde exterior (fuera)
        
        # Dibujar línea blanca y límite rojo
        cv2.rectangle(minimapa, (x_linea_in, 0), (x_linea_out, h_mini), (230, 230, 230), -1)
        cv2.line(minimapa, (x_linea_out, 0), (x_linea_out, h_mini), (0, 0, 255), 2)
        
        r_px = int(radio_cm * S * 2.0)  # radio balón en minimapa (22px si radio_cm=11)
        
        # POSICIÓN DEL BALÓN: derivada de margen_cm
        # margen_cm = distancia del borde interior del balón al borde exterior de la línea
        # Borde interior del balón = centro - radio (hacia el campo)
        # Si margen = 0: borde interior justo en la línea → centro = x_linea_out + radio
        # Si margen > 0: pasado → centro = x_linea_out + radio + margen*S
        # Si margen < 0: dentro → centro = x_linea_out + radio + margen*S (con margen negativo)
        x_ball = x_linea_out + r_px + int(margen_cm * S)
        x_ball = max(r_px + 5, min(w_mini - r_px - 5, x_ball))
        y_ball = h_mini // 2
        
        # Color del balón
        if self.modo_juego == "GOL":
            c_ball = LALIGA_VERDE if es_gol else LALIGA_ROJO
        else:
            c_ball = LALIGA_ROJO if es_gol else LALIGA_VERDE
            
        cv2.circle(minimapa, (x_ball, y_ball), r_px, c_ball, -1)
        cv2.circle(minimapa, (x_ball, y_ball), r_px, (255, 255, 255), 2)
        
        txt = ("GOL" if es_gol else "NO GOL") if self.modo_juego == "GOL" else ("FUERA" if es_gol else "DENTRO")
        cv2.putText(minimapa, "VAR TECH", (10, 25), cv2.FONT_HERSHEY_DUPLEX, 0.6, (255,255,255), 1)
        cv2.putText(minimapa, txt, (10, 60), cv2.FONT_HERSHEY_DUPLEX, 1.0, c_ball, 2)
        cv2.putText(minimapa, f"Margen: {abs(margen_cm):.1f} cm", (10, h_mini-20), cv2.FONT_HERSHEY_DUPLEX, 0.7, (255,255,255), 1)
        return minimapa

    def actualizar(self):
        if self.img_orig is None: return
        self.img_dibujada = self.img_orig.copy()
        ocultar = (self.fase == 3 and (self.p_centro is None or self.drag_mode == "move"))
        lbl_dir = "Borde FUERA (Red)" if self.modo_juego == "GOL" else "Borde FUERA (Calle)"
        f_txt = ["", "Fase 1: Borde ADENTRO (Césped)", f"Fase 2: {lbl_dir}", "Fase 3: Centro Balón", "Fase 4: RESULTADO"]
        self.lbl_fase.configure(text=f_txt[min(self.fase, 4)])
        
        # Dibujar líneas infininitas
        if not ocultar:
            if len(self.linea_gol) == 2:
                vx, vy = float(self.linea_gol[1][0]-self.linea_gol[0][0]), float(self.linea_gol[1][1]-self.linea_gol[0][1])
                p1 = (int(self.linea_gol[0][0]-vx*10000), int(self.linea_gol[0][1]-vy*10000))
                p2 = (int(self.linea_gol[1][0]+vx*10000), int(self.linea_gol[1][1]+vy*10000))
                cv2.line(self.img_dibujada, p1, p2, LALIGA_BLANCO, 1, cv2.LINE_AA)
            if len(self.linea_ext) == 2:
                vx, vy = float(self.linea_ext[1][0]-self.linea_ext[0][0]), float(self.linea_ext[1][1]-self.linea_ext[0][1])
                p1 = (int(self.linea_ext[0][0]-vx*10000), int(self.linea_ext[0][1]-vy*10000))
                p2 = (int(self.linea_ext[1][0]+vx*10000), int(self.linea_ext[1][1]+vy*10000))
                cv2.line(self.img_dibujada, p1, p2, LALIGA_ROJO, 1, cv2.LINE_AA)
                
        if self.p_centro and not ocultar:
            cv2.circle(self.img_dibujada, (int(self.p_centro[0]), int(self.p_centro[1])), 3, LALIGA_SEC, -1)
            
        if len(self.linea_gol) == 2 and len(self.linea_ext) == 2 and self.p_centro:
            radio = float(self.radio_balon)
            escala = 11.0 / max(0.1, radio)  # px → cm (basado en balón = 22cm diámetro)
            
            # ========================================================
            # DISTANCIA DEL BALÓN A LA LÍNEA EXTERIOR (decisión final)
            # ========================================================
            d_ball_ext, _ = distancia_punto_recta(self.p_centro, self.linea_ext[0], self.linea_ext[1])
            # Orientar: queremos que positivo = FUERA del campo
            # El césped (linea_gol) está DENTRO, así que su distancia a linea_ext debe ser negativa
            d_grass_ext, _ = distancia_punto_recta(self.linea_gol[0], self.linea_ext[0], self.linea_ext[1])
            if d_grass_ext > 0:
                d_ball_ext = -d_ball_ext
                d_grass_ext = -d_grass_ext
            
            # ========================================================
            # DISTANCIA DEL BALÓN A LA LÍNEA INTERIOR (para minimapa)
            # ========================================================
            # ========================================================
            # DECISIÓN: margen = distancia_borde_balón al borde exterior
            # margen > 0 → completamente fuera (GOL / FUERA)
            # margen ≤ 0 → todavía toca o está dentro (NO GOL / DENTRO)
            # ========================================================
            margen_px = d_ball_ext - radio
            margen_cm = margen_px * escala
            es_gol = margen_cm > 0
            
            # Grosor de línea detectado
            thick_px = abs(d_grass_ext)
            thick_cm = thick_px * escala
            
            # Distancia del centro al borde interior en cm (para minimapa)
            # Ya no se necesita: la posición del balón se deriva de margen_cm directamente
            
            txt = ("GOL" if es_gol else "NO GOL") if self.modo_juego == "GOL" else ("FUERA" if es_gol else "DENTRO")
            col = (LALIGA_VERDE if es_gol else LALIGA_ROJO) if self.modo_juego == "GOL" else (LALIGA_ROJO if es_gol else LALIGA_VERDE)
            
            cv2.putText(self.img_dibujada, txt, (50, 80), cv2.FONT_HERSHEY_DUPLEX, 2.0, LALIGA_NEGRO, 5)
            cv2.putText(self.img_dibujada, txt, (50, 80), cv2.FONT_HERSHEY_DUPLEX, 2.0, col, 3)
            sm = f"MARGIN: {abs(margen_cm):.1f} cm"
            cv2.putText(self.img_dibujada, sm, (50, 130), cv2.FONT_HERSHEY_DUPLEX, 1.0, LALIGA_NEGRO, 3)
            cv2.putText(self.img_dibujada, sm, (50, 130), cv2.FONT_HERSHEY_DUPLEX, 1.0, LALIGA_BLANCO, 1)
            
            # Contorno del balón
            cx, cy = int(self.p_centro[0]), int(self.p_centro[1])
            cv2.circle(self.img_dibujada, (cx, cy), int(radio), (255,255,255), 1, cv2.LINE_AA)
            
            # Debug
            self.lbl_info.configure(text=f"d_ext={d_ball_ext:.1f}px r={radio:.0f}px | Grosor:{thick_cm:.1f}cm")
            
            if self.fase == 4:
                h_i, w_i = self.img_orig.shape[:2]
                w_m = int(w_i * 0.25)
                h_m = int(w_m * 0.66)
                mini = self.dibujar_minimapa(11.0, margen_cm, es_gol, w_m, h_m)
                y_s, x_s = 40, w_i - w_m - 40
                if x_s > 0 and (y_s + h_m) < h_i:
                    self.img_dibujada[y_s:y_s+h_m, x_s:x_s+w_m] = mini
                    cv2.rectangle(self.img_dibujada, (x_s, y_s), (x_s+w_m, y_s+h_m), (255,255,255), 2)
                    
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
            cv2.rectangle(self.img_dibujada, (x_start, y_start), (x_start + box_w_1, y_end), (35, 35, 35), -1)
            x_m = x_start + box_w_1
            cv2.rectangle(self.img_dibujada, (x_m, y_start), (x_m + box_w_v, y_end), LALIGA_ROJO, -1)
            x_m2 = x_m + box_w_v
            cv2.rectangle(self.img_dibujada, (x_m2, y_start), (x_m2 + box_w_2, y_end), (35, 35, 35), -1)
            
            # Franja inferior decorativa
            line_h = 3
            cv2.rectangle(self.img_dibujada, (x_start, y_end), (x_start + box_w_1, y_end + line_h), (200, 200, 200), -1)
            cv2.rectangle(self.img_dibujada, (x_m, y_end), (x_m + box_w_v, y_end + line_h), (10, 10, 10), -1)
            cv2.rectangle(self.img_dibujada, (x_m2, y_end), (x_m2 + box_w_2, y_end + line_h), (200, 200, 200), -1)
            
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
                overlay_shield(self.img_dibujada, shield1_path, x_start + pad_x, sy, s_size)
            if has_s2:
                sy = y_start + (h_box - s_size) // 2
                overlay_shield(self.img_dibujada, shield2_path, x_m2 + pad_x, sy, s_size)

            # Textos
            th_max = max(th_1, th_v, th_2)
            ty = y_start + (h_box + th_max) // 2 - 2
            
            tx_1 = x_start + pad_x + w_s1 + (box_w_1 - pad_x*2 - w_s1 - tw_1)//2
            cv2.putText(self.img_dibujada, eq1, (tx_1, ty), font, scale, LALIGA_BLANCO, thick, cv2.LINE_AA)
            tx_v = x_m + (box_w_v - tw_v) // 2
            cv2.putText(self.img_dibujada, "VS", (tx_v, ty), font, scale, LALIGA_BLANCO, thick, cv2.LINE_AA)
            tx_2 = x_m2 + pad_x + w_s2 + (box_w_2 - pad_x*2 - w_s2 - tw_2)//2
            cv2.putText(self.img_dibujada, eq2, (tx_2, ty), font, scale, LALIGA_BLANCO, thick, cv2.LINE_AA)
                            
        self.mostrar_imagen()

    def redimensionar(self, event):
        if event.widget == self:
            if not hasattr(self, "_last_size") or self._last_size != (event.width, event.height):
                self._last_size = (event.width, event.height); self.mostrar_imagen()

    def mostrar_imagen(self):
        if self.img_dibujada is None: return
        self.canvas_img.update(); cw, ch = self.canvas_img.winfo_width(), self.canvas_img.winfo_height()
        if cw <= 1 or ch <= 1: return
        h, w = self.img_dibujada.shape[:2]; self.scale_factor = min(cw/w, ch/h)
        nw, nh = int(w*self.scale_factor), int(h*self.scale_factor)
        img_res = cv2.resize(self.img_dibujada, (nw, nh), interpolation=cv2.INTER_LANCZOS4)
        self.img_tk = ImageTk.PhotoImage(image=Image.fromarray(cv2.cvtColor(img_res, cv2.COLOR_BGR2RGB)))
        self.img_x_off, self.img_y_off = (cw-nw)//2, (ch-nh)//2
        self.canvas_img.delete("all"); self.canvas_img.create_image(self.img_x_off, self.img_y_off, anchor="nw", image=self.img_tk)

    def mover_raton(self, event):
        if self.img_dibujada is None: return
        x, y = int((event.x - self.img_x_off)/self.scale_factor), int((event.y - self.img_y_off)/self.scale_factor)
        h, w = self.img_dibujada.shape[:2]
        if not (0 <= x < w and 0 <= y < h): return
        # Lupa: recorte de 40px alrededor del cursor, escalado a 200x200 (tamaño del canvas)
        r = 40
        z = 220
        padded = cv2.copyMakeBorder(self.img_dibujada, r, r, r, r, cv2.BORDER_CONSTANT, value=[0,0,0])
        px, py = x + r, y + r
        recorte = padded[py-r:py+r, px-r:px+r].copy()
        zoom = cv2.resize(recorte, (z, z), interpolation=cv2.INTER_NEAREST)
        c = z // 2
        gs = max(1, z // (2 * r))
        for i in range(0, z, gs):
            cv2.line(zoom, (i, 0), (i, z), (40, 40, 40), 1)
            cv2.line(zoom, (0, i), (z, i), (40, 40, 40), 1)
        cv2.line(zoom, (c, 0), (c, z), LALIGA_BLANCO, 1)
        cv2.line(zoom, (0, c), (z, c), LALIGA_BLANCO, 1)
        cv2.circle(zoom, (c, c), 2, LALIGA_ROJO, -1)
        self.img_tk_lupa = ImageTk.PhotoImage(image=Image.fromarray(cv2.cvtColor(zoom, cv2.COLOR_BGR2RGB)))
        self.canvas_lupa.delete("all")
        self.canvas_lupa.create_image(0, 0, anchor="nw", image=self.img_tk_lupa)

    def guardar_imagen(self):
        if self.img_dibujada is not None and self.ruta_img:
            cv2.imwrite(f"{os.path.splitext(os.path.basename(self.ruta_img))[0]}_VAR_RESULT.jpg", self.img_dibujada)
            self.lbl_info.configure(text="¡Imagen Exportada!")

    def guardar_proyecto(self):
        """Guarda el estado actual como proyecto .varproj (JSON)."""
        if self.img_orig is None or not self.ruta_img:
            self.lbl_info.configure(text="Nada que guardar"); return
        proj = {
            "ruta_img": self.ruta_img,
            "linea_gol": [list(p) for p in self.linea_gol],
            "linea_ext": [list(p) for p in self.linea_ext],
            "p_centro": list(self.p_centro) if self.p_centro else None,
            "radio_balon": float(self.radio_balon),
            "modo_juego": self.modo_juego,
            "grosor": float(self.slider_grosor.get()),
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
        """Carga un proyecto .varproj y restaura todo el estado."""
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
            self.lbl_info.configure(text=f"Imagen no encontrada: {ruta}"); return
        
        self.ruta_img = ruta
        self.img_orig = cv2.imread(ruta)
        if self.img_orig is None:
            self.lbl_info.configure(text="Error al leer imagen"); return
        
        self.linea_gol = [tuple(p) for p in proj.get("linea_gol", [])]
        self.linea_ext = [tuple(p) for p in proj.get("linea_ext", [])]
        pc = proj.get("p_centro")
        self.p_centro = tuple(pc) if pc else None
        self.radio_balon = proj.get("radio_balon", 15)
        self.modo_juego = proj.get("modo_juego", "FUERA")
        grosor = proj.get("grosor", 12.0)
        self.slider_grosor.set(grosor)
        self.lbl_grosor.configure(text=f"Grosor Línea: {grosor:.1f} cm")
        
        if self.modo_juego == "GOL":
            self.cmb_modo.set("Gol / No Gol")
        else:
            self.cmb_modo.set("Fuera / Dentro")
            
        eq1 = proj.get("equipo1", "")
        eq2 = proj.get("equipo2", "")
        self.entry_equipo1.delete(0, "end"); self.entry_equipo1.insert(0, eq1)
        self.entry_equipo2.delete(0, "end"); self.entry_equipo2.insert(0, eq2)
        
        self.fase = 5
        self.actualizar()
        self.lbl_info.configure(text=f"Proyecto cargado: {os.path.basename(path)}")

    def guardar_video(self):
        if self.img_dibujada is None or self.img_orig is None or not self.ruta_img: return
        if not (len(self.linea_gol) == 2 and len(self.linea_ext) == 2 and self.p_centro):
            self.lbl_info.configure(text="Completa las fases 1 a 4 primero"); return
        
        self.lbl_info.configure(text="Generando vídeo 3D...")
        self.update()
        
        W, H = 1280, 720
        FPS = 30
        h_orig, w_orig = self.img_orig.shape[:2]
        sx_scale, sy_scale = W / w_orig, H / h_orig
        
        # 1. DATOS DE CALIBRACIÓN
        radio = float(self.radio_balon)
        d_ball_ext, (nx, ny) = distancia_punto_recta(self.p_centro, self.linea_ext[0], self.linea_ext[1])
        d_grass_ext, _ = distancia_punto_recta(self.linea_gol[0], self.linea_ext[0], self.linea_ext[1])
        if d_grass_ext > 0:
            d_ball_ext, d_grass_ext = -d_ball_ext, -d_grass_ext
            nx, ny = -nx, -ny
            
        esc_cm = 11.0 / max(0.1, radio)
        margen_cm = (d_ball_ext - radio) * esc_cm
        
        dx_line = float(self.linea_ext[1][0] - self.linea_ext[0][0])
        dy_line = float(self.linea_ext[1][1] - self.linea_ext[0][1])
        lmx, lmy = (self.linea_ext[0][0] + self.linea_ext[1][0]) / 2.0, (self.linea_ext[0][1] + self.linea_ext[1][1]) / 2.0
        cross = dx_line * (self.p_centro[1] - lmy) - dy_line * (self.p_centro[0] - lmx)
        side = 1 if cross > 0 else -1
        start_angle = math.atan2(ny, nx)
        
        txt_res = ("NO GOL" if margen_cm > 0 else "GOL") if self.modo_juego == "GOL" else ("FUERA" if margen_cm > 0 else "DENTRO")
        col_res = (LALIGA_ROJO if margen_cm > 0 else LALIGA_VERDE) if self.modo_juego == "GOL" else (LALIGA_ROJO if margen_cm > 0 else LALIGA_VERDE)
        
        vid_path = f"{os.path.splitext(os.path.basename(self.ruta_img))[0]}_VAR3D.mp4"
        out = cv2.VideoWriter(vid_path, cv2.VideoWriter_fourcc(*'mp4v'), float(FPS), (W, H))
        img_start = cv2.resize(self.img_orig, (W, H), interpolation=cv2.INTER_LANCZOS4)

        def project(pts_3d, cam_pos, cam_target, fov=45):
            fwd = np.array(cam_target, dtype=float) - np.array(cam_pos, dtype=float)
            fwd /= (np.linalg.norm(fwd) + 1e-9)
            up_ref = np.array([0, 0, 1], dtype=float)
            if abs(np.dot(fwd, up_ref)) > 0.99: up_ref = np.array([0, 1, 0], dtype=float)
            right = np.cross(fwd, up_ref)
            right /= (np.linalg.norm(right) + 1e-9)
            up = np.cross(right, fwd)
            fl = 1.0 / max(0.01, math.tan(math.radians(fov / 2)))
            res = []
            for pt in pts_3d:
                v = np.array(pt, dtype=float) - np.array(cam_pos, dtype=float)
                zc = float(np.dot(v, fwd))
                if zc < 0.1: zc = 0.1
                xc, yc = float(np.dot(v, right)), float(np.dot(v, up))
                sx_p = int(W/2 + (xc/zc)*fl*H/2)
                sy_p = int(H/2 - (yc/zc)*fl*H/2)
                res.append((sx_p, sy_p, zc))
            return res

        def dibujar_3d_sobre(bg, alpha):
            frame = bg.copy()
            for pts, col in [(self.linea_gol, (255,255,0)), (self.linea_ext, LALIGA_ROJO)]:
                vx, vy = float(pts[1][0]-pts[0][0]), float(pts[1][1]-pts[0][1])
                p1 = (int((pts[0][0]-vx*100)*sx_scale), int((pts[0][1]-vy*100)*sy_scale))
                p2 = (int((pts[1][0]+vx*100)*sx_scale), int((pts[1][1]+vy*100)*sy_scale))
                ov = frame.copy()
                cv2.line(ov, p1, p2, col, 3, cv2.LINE_AA)
                cv2.addWeighted(ov, alpha, frame, 1-alpha, 0, frame)
            if self.p_centro:
                cx, cy = int(self.p_centro[0]*sx_scale), int(self.p_centro[1]*sy_scale)
                r_px = int(radio * sx_scale)
                ball_ov = frame.copy()
                for ri in range(r_px, 0, -1):
                    frac = ri/r_px
                    iv = int(255*(0.4+0.6*(1-frac**2)))
                    cc = tuple(max(0,min(255,int(col_res[k]*iv/255))) for k in range(3))
                    cv2.circle(ball_ov, (cx, cy), ri, cc, -1, cv2.LINE_AA)
                cv2.circle(ball_ov, (cx, cy), r_px, (255,255,255), 1, cv2.LINE_AA)
                cv2.addWeighted(ball_ov, alpha, frame, 1-alpha, 0, frame)
            cv2.putText(frame, "VAR TECH 3D", (20, 40), 1, 1.5, (255,255,255), 1, cv2.LINE_AA)
            if alpha > 0.8:
                cv2.putText(frame, txt_res, (50, 100), cv2.FONT_HERSHEY_DUPLEX, 1.8, (0,0,0), 5, cv2.LINE_AA)
                cv2.putText(frame, txt_res, (50, 100), cv2.FONT_HERSHEY_DUPLEX, 1.8, col_res, 3, cv2.LINE_AA)
            return frame

        # --- SOPORTE DE ALINEACIÓN SEAMLESS ---
        # Calculamos la rotación inicial para que coincida con la línea en la foto
        # Usamos self.linea_gol que ya tiene los puntos calibrados
        p_a, p_b = self.linea_gol[0], self.linea_gol[1]
        v_line_2d = np.array(p_b) - np.array(p_a)
        angle_foto = math.atan2(v_line_2d[1], v_line_2d[0])
        start_angle = angle_foto - math.pi/2 

        def render_3d(t_norm, fase):
            # PROPORCIONES FIJAS (1cm = 1px, Balón x2)
            ball_r3 = 22.0  # Radio 22px (Diámetro 44px)
            line_w_3d = 6.0 # Grosor 6px
            gap_3d = margen_cm # 1cm = 1px
            bx_3d = side * (line_w_3d/2.0 + gap_3d + ball_r3)
            dist_base = ball_r3 * 20.0 # Basado en el nuevo radio
            
            # Easing suave (ease-in-out cúbico)
            t_e = t_norm * t_norm * (3.0 - 2.0 * t_norm)
            
            if fase == "move":
                ang = start_angle + t_e * (math.pi*0.5 if side>0 else -math.pi*0.5)
                h = dist_base * 0.4 + t_e * dist_base * 2.6
                d = dist_base * (1.2 - t_e * 1.2)  # llega a 0 (cenital) al final
                fov = 35 - t_e * 15
                cam = [math.cos(ang)*d, math.sin(ang)*d, h]
                tgt = [bx_3d * (0.1 * (1-t_e)), 0, 0]
            else:
                # Ya estamos cenital, solo hacemos zoom descendente
                h = dist_base * 3.0 - t_e * dist_base * 1.8
                cam = [0.01, 0.01, h]
                tgt = [0, 0, 0]; fov = 20 - t_e * 8

            img = np.zeros((H, W, 3), dtype=np.uint8)
            p_test = project([(bx_3d, 0, 0)], cam, tgt, fov)[0]
            off_x, off_y = 0, 0
            if fase == "move":
                off_x = int((self.p_centro[0] - p_test[0]) * (1.0 - t_norm))
                off_y = int((self.p_centro[1] - p_test[1]) * (1.0 - t_norm))

            def project_aligned(pts):
                prjs = project(pts, cam, tgt, fov)
                return [(p[0]+off_x, p[1]+off_y, p[2]) for p in prjs]

            # 1. CÉSPED DINÁMICO
            sw = line_w_3d * 6.0; L_H = ball_r3 * 40.0
            for i in range(-5, 6):
                c = (42, 145, 42) if i % 2 == 0 else (35, 120, 35)
                p_c = [(-L_H, i*sw, -1), (L_H, i*sw, -1), (line_half:=L_H, (i+1)*sw, -1), (-L_H, (i+1)*sw, -1)]
                prj = project_aligned(p_c)
                if any(p[2]>0 for p in prj):
                    cv2.fillPoly(img, [np.array([(p[0],p[1]) for p in prj], np.int32)], c)
            
            # 2. LÍNEA BLANCA PRINCIPAL
            prj_l = project_aligned([(-line_w_3d/2, -line_half, 0), (line_w_3d/2, -line_half,0), 
                                     (line_w_3d/2, line_half, 0), (-line_w_3d/2, line_half, 0)])
            cv2.fillPoly(img, [np.array([(p[0],p[1]) for p in prj_l], np.int32)], (245,245,245))
            
            # 3. BALÓN PRO (dibujamos primero para conocer posición en pantalla)
            prj_b = project_aligned([(bx_3d, 0, 0)])
            bx_s, by_s, bz_s = prj_b[0]
            br_s = max(4, int(ball_r3 * (W/2) / max(1.0, bz_s)))

            # 4. FILL GAP 2D (Pared de Decisión en coordenadas de pantalla)
            if fase == "hold":
                # Proyectamos el borde de la línea (lado del balón) a pantalla
                prj_line_edge = project_aligned([(side * line_w_3d / 2.0, 0, 0)])
                line_sx = prj_line_edge[0][0]
                # Borde más cercano del balón en pantalla
                ball_near_sx = bx_s + (br_s if side < 0 else -br_s)
                # Determinamos x_left y x_right para el rectángulo
                x_left = min(line_sx, ball_near_sx)
                x_right = max(line_sx, ball_near_sx)
                # Dibujamos el relleno cubriendo toda la altura de la imagen
                ov_w = img.copy()
                cv2.rectangle(ov_w, (x_left, 0), (x_right, H), col_res, -1)
                cv2.addWeighted(ov_w, 0.7, img, 0.3, 0, img)
                # Borde blanco fino en el lado de la línea
                cv2.line(img, (line_sx, 0), (line_sx, H), (255,255,255), 1, cv2.LINE_AA)

            # 5. ILUMINACIÓN DE DECISIÓN (Resaltado Glow)
            if fase == "hold":
                prj_er = project_aligned([(side*line_w_3d/2, -line_half, 0.1), (side*line_w_3d/2, line_half, 0.1)])
                for g in range(12, 0, -3):
                    cv2.line(img, (prj_er[0][0], prj_er[0][1]), (prj_er[1][0], prj_er[1][1]), col_res, g, cv2.LINE_AA)
                cv2.line(img, (prj_er[0][0], prj_er[0][1]), (prj_er[1][0], prj_er[1][1]), (255,255,255), 1, cv2.LINE_AA)

            # 6. DIBUJAR BALÓN
            if fase == "hold":
                # Balón Decision Look: Borde blanco nítido
                cv2.circle(img, (bx_s, by_s), br_s+1, (255,255,255), 2, cv2.LINE_AA)
                cv2.circle(img, (bx_s, by_s), br_s-1, col_res, -1, cv2.LINE_AA)
            else:
                for ri in range(br_s, 0, -2):
                    frac = ri/br_s; iv = int(255*(0.5+0.5*(1-frac**2)))
                    cc = tuple(max(0,min(255,int(col_res[k]*iv/255))) for k in range(3))
                    cv2.circle(img, (bx_s, by_s), ri, cc, -1, cv2.LINE_AA)
                cv2.circle(img, (bx_s, by_s), br_s, (255,255,255), 1, cv2.LINE_AA)
            
            cv2.putText(img, "VAR TECH 3D", (20, 40), 1, 1.5, (255,255,255), 1, cv2.LINE_AA)
            return img

        # EJECUCIÓN (LALIGA Visual Style - Transición Seamless)
        for i in range(15): out.write(img_start) # 1. Foto Estática (0.5s)
        
        # 2. Fundido (Dissolve) suave de la Foto al 3D (1.5s -> 45 frames)
        frame_3d_start = render_3d(0.0, "move")
        n_dissolve = 45
        for i in range(n_dissolve):
            t = i / float(n_dissolve)
            alpha = t * t * (3.0 - 2.0 * t)  # ease-in-out suave
            blended = cv2.addWeighted(img_start, 1.0 - alpha, frame_3d_start, alpha, 0)
            out.write(blended)
        
        # 3. Animación de Cámara (ascenso suave) (3.0s -> 90 frames)
        n_move = 90
        for i in range(n_move):
            out.write(render_3d(i / float(n_move), "move"))
            
        # 4. Zoom de Veredicto PROGRESIVO (4.0s -> 120 frames)
        n_hold = 120
        for i in range(n_hold):
            t_hold = i / float(n_hold)
            fr = render_3d(t_hold, "hold")
            # Banner con ease-in suave (aparición gradual)
            t_banner = min(1.0, i / 30.0)
            alpha_b = t_banner * t_banner  # ease-in cuadrático
            ov = fr.copy(); bh = 170; bw = 480
            cv2.rectangle(ov, (30, H - bh - 30), (30 + bw, H - 30), (0,0,0), -1)
            cv2.addWeighted(ov, 0.7*alpha_b, fr, 1-0.7*alpha_b, 0, fr)
            if alpha_b > 0.3:
                txt_alpha = min(1.0, (alpha_b - 0.3) / 0.7)  # texto aparece después
                cv2.putText(fr, txt_res, (50, H - bh + 15), cv2.FONT_HERSHEY_DUPLEX, 2.2, (0,0,0), 6, cv2.LINE_AA)
                cv2.putText(fr, txt_res, (50, H - bh + 15), cv2.FONT_HERSHEY_DUPLEX, 2.2, col_res, 3, cv2.LINE_AA)
                cv2.putText(fr, "VAR TECH (cm)", (55, H - 85), 1, 1.2, (200,200,200), 1, cv2.LINE_AA)
                m_txt = f"Margen: {abs(margen_cm):.1f} cm"
                cv2.putText(fr, m_txt, (55, H - 50), cv2.FONT_HERSHEY_DUPLEX, 1.1, (255,255,255), 1, cv2.LINE_AA)
            out.write(fr)
            
        out.release()
        self.lbl_info.configure(text=f"Video Exportado: {os.path.basename(vid_path)}")
        messagebox.showinfo("VAR 3D", f"Video guardado:\n{vid_path}")

if __name__ == "__main__":
    ctk.set_appearance_mode("dark"); GoalLineApp().mainloop()
