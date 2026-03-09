"""
Guitar-to-Doom Launcher Pro
Кастомный GUI: frameless, анимации, Canvas-кнопки, VU-метр
"""
import tkinter as tk
import subprocess, os, sys, math, random
import ctypes, ctypes.wintypes

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# ── Палитра ───────────────────────────────────────────────────────────────────
BG       = "#0a0a0a"
PANEL    = "#111111"
CARD     = "#161616"
CARD2    = "#1c1c1c"
BORDER   = "#252525"
BORDER2  = "#333333"

RED      = "#dd2222"
RED_HOT  = "#ff4444"
RED_DIM  = "#3d0808"
RED_MID  = "#7a1111"
ORANGE   = "#ff6600"

BLUE     = "#2277dd"
BLUE_HOT = "#44aaff"
BLUE_DIM = "#071d3d"
BLUE_MID = "#0e3a6b"

GREEN    = "#22bb44"
GREEN_DIM= "#0a2414"

GOLD     = "#ffaa00"
GOLD_DIM = "#3d2800"

TEXT     = "#f0f0f0"
TEXT_MID = "#aaaaaa"
TEXT_DIM = "#444444"

# ── Игры ─────────────────────────────────────────────────────────────────────
GAMES = [
    {"name": "DOOM II: Hell on Earth",     "short": "DOOM II",         "iwad": "iwads\\doom2.wad",    "extra": ["mods\\audio\\IDKFAv2.wad", "mods\\graphics\\NeuralUpscale2x_v1.0.pk3"]},
    {"name": "The Ultimate DOOM",           "short": "Ultimate DOOM",   "iwad": "iwads\\doom.wad",     "extra": ["mods\\audio\\IDKFAv2.wad", "mods\\graphics\\NeuralUpscale2x_v1.0.pk3"]},
    {"name": "TNT: Evilution",              "short": "TNT: Evilution",  "iwad": "iwads\\tnt.wad",      "extra": ["mods\\audio\\IDKFAv2.wad", "mods\\graphics\\NeuralUpscale2x_v1.0.pk3"]},
    {"name": "The Plutonia Experiment",     "short": "Plutonia",        "iwad": "iwads\\plutonia.wad", "extra": ["mods\\audio\\IDKFAv2.wad", "mods\\graphics\\NeuralUpscale2x_v1.0.pk3"]},
    {"name": "SIGIL by John Romero",        "short": "SIGIL",           "iwad": "iwads\\doom.wad",     "extra": ["official\\sigil.wad", "mods\\audio\\IDKFAv2.wad", "mods\\graphics\\NeuralUpscale2x_v1.0.pk3"]},
    {"name": "Master Levels for DOOM II",   "short": "Master Levels",   "iwad": "iwads\\doom2.wad",    "extra": ["official\\masterlevels.wad", "mods\\audio\\IDKFAv2.wad", "mods\\graphics\\NeuralUpscale2x_v1.0.pk3"]},
    {"name": "No Rest for the Living",      "short": "NRFTL",           "iwad": "iwads\\doom2.wad",    "extra": ["official\\nerve.wad", "mods\\audio\\IDKFAv2.wad", "mods\\graphics\\NeuralUpscale2x_v1.0.pk3"]},
    {"name": "Только контроллер",            "short": "Ctrl Only",       "iwad": None,                  "extra": []},
]

W, H = 720, 540

# ── Утилиты ───────────────────────────────────────────────────────────────────
def _blend(c1, c2, t):
    """Линейная интерполяция цветов"""
    r1,g1,b1 = int(c1[1:3],16), int(c1[3:5],16), int(c1[5:7],16)
    r2,g2,b2 = int(c2[1:3],16), int(c2[3:5],16), int(c2[5:7],16)
    r = int(r1 + (r2-r1)*t); g = int(g1 + (g2-g1)*t); b = int(b1 + (b2-b1)*t)
    return f"#{r:02x}{g:02x}{b:02x}"

def _audio_backend():
    try:
        import sounddevice  # noqa
        return "sounddevice"
    except ImportError:
        try:
            from winmm_audio import WinMMStream  # noqa
            return "WinMM"
        except ImportError:
            return "NO AUDIO"

# ── Главное окно ─────────────────────────────────────────────────────────────
class GuitarDoomLauncher(tk.Tk):

    def __init__(self):
        super().__init__()
        self._audio_backend = _audio_backend()
        self._selected_game = 0
        self._instrument    = "guitar"   # 'guitar' | 'bass'
        self._hover_launch  = False
        self._status_text   = "Готов к запуску"
        self._status_color  = TEXT_MID
        self._drag_x = self._drag_y = 0

        # VU-метр: 22 бара
        self._vu  = [random.random() * 0.2 for _ in range(22)]
        self._vut = [0.08] * 22
        self._vu_tick = 0

        # Launch-кнопка: пульсация
        self._pulse = 0.0
        self._pulse_dir = 1

        self._setup_window()
        self._build_ui()
        self._start_animate()

    # ── Окно ─────────────────────────────────────────────────────────────────

    def _setup_window(self):
        self.overrideredirect(True)
        self.configure(bg=BG)
        sw = self.winfo_screenwidth(); sh = self.winfo_screenheight()
        self.geometry(f"{W}x{H}+{(sw-W)//2}+{(sh-H)//2}")

        # DWM: скруглённые углы + тёмная тема для превью в таскбаре
        try:
            hwnd = self.winfo_id()
            v = ctypes.c_int(1)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(v), 4)
            v = ctypes.c_int(2)  # DWMWCP_ROUND
            ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 33, ctypes.byref(v), 4)
        except Exception:
            pass

    # ── Построение UI ─────────────────────────────────────────────────────────

    def _build_ui(self):
        # ── Верхняя полоска-акцент ────────────────────────────────────────────
        accent_top = tk.Canvas(self, height=3, bg=RED, highlightthickness=0)
        accent_top.pack(fill="x")

        # ── Кастомный тайтлбар ────────────────────────────────────────────────
        self._build_titlebar()

        # ── Хедер с VU-метром ─────────────────────────────────────────────────
        self._build_header()

        # ── Разделитель ───────────────────────────────────────────────────────
        tk.Frame(self, bg=BORDER, height=1).pack(fill="x")

        # ── Контент: список игр + правая колонка ──────────────────────────────
        content = tk.Frame(self, bg=BG)
        content.pack(fill="both", expand=True)

        self._build_gamelist(content)

        sep = tk.Frame(content, bg=BORDER, width=1)
        sep.pack(side="left", fill="y", padx=0)

        self._build_controls(content)

        # ── Статусбар ─────────────────────────────────────────────────────────
        tk.Frame(self, bg=BORDER, height=1).pack(fill="x")
        self._build_statusbar()

    # ── Тайтлбар ─────────────────────────────────────────────────────────────

    def _build_titlebar(self):
        tb = tk.Frame(self, bg=PANEL, height=38)
        tb.pack(fill="x")
        tb.pack_propagate(False)

        # Иконка / логотип
        tk.Label(tb, text="  ▐▌ GUITAR-TO-DOOM", font=("Consolas", 11, "bold"),
                 bg=PANEL, fg=RED).pack(side="left", padx=(8, 0))
        tk.Label(tb, text=" LAUNCHER PRO", font=("Consolas", 11),
                 bg=PANEL, fg=TEXT_MID).pack(side="left")

        # Аудио бэкенд — пилюля справа
        backend_color = BLUE if self._audio_backend == "sounddevice" else ORANGE
        pill = tk.Label(tb, text=f"  {self._audio_backend}  ",
                        font=("Consolas", 8, "bold"),
                        bg=backend_color, fg=TEXT, relief="flat", padx=4, pady=2)
        pill.pack(side="right", padx=(0, 8), pady=8)

        # Кнопки закрыть / свернуть
        for txt, cmd, color in [("✕", self.destroy, RED), ("─", self._minimize, TEXT_DIM)]:
            b = tk.Label(tb, text=txt, font=("Consolas", 12, "bold"),
                         bg=PANEL, fg=color, cursor="hand2", padx=10)
            b.pack(side="right")
            b.bind("<Button-1>", lambda e, c=cmd: c())
            b.bind("<Enter>",  lambda e, w=b, c=color: w.config(bg=CARD2))
            b.bind("<Leave>",  lambda e, w=b: w.config(bg=PANEL))

        # Перетаскивание
        tb.bind("<ButtonPress-1>",   self._drag_start)
        tb.bind("<B1-Motion>",       self._drag_move)

    def _minimize(self):
        self.overrideredirect(False)
        self.iconify()
        self.bind("<Map>", lambda e: (self.overrideredirect(True), self.bind("<Map>", "")))

    def _drag_start(self, e):
        self._drag_x = e.x_root - self.winfo_x()
        self._drag_y = e.y_root - self.winfo_y()

    def _drag_move(self, e):
        self.geometry(f"+{e.x_root - self._drag_x}+{e.y_root - self._drag_y}")

    # ── Хедер / VU-метр ──────────────────────────────────────────────────────

    def _build_header(self):
        hdr = tk.Frame(self, bg=PANEL, height=82)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)

        # Логотип — левая часть
        logo = tk.Frame(hdr, bg=PANEL)
        logo.pack(side="left", padx=(16, 0))
        tk.Label(logo, text="🎸", font=("Segoe UI Emoji", 26),
                 bg=PANEL, fg=RED).pack(anchor="w")

        info = tk.Frame(hdr, bg=PANEL)
        info.pack(side="left", padx=(10, 0))
        tk.Label(info, text="Guitar-to-Doom Controller Pro",
                 font=("Consolas", 13, "bold"), bg=PANEL, fg=TEXT).pack(anchor="w")
        tk.Label(info, text="GZDoom + аудио управление через гитару",
                 font=("Consolas", 9), bg=PANEL, fg=TEXT_DIM).pack(anchor="w")

        # VU-метр — правая часть
        self._vu_canvas = tk.Canvas(hdr, width=264, height=62,
                                     bg=PANEL, highlightthickness=0)
        self._vu_canvas.pack(side="right", padx=(0, 16), pady=10)
        self._draw_vu()

    def _draw_vu(self):
        c = self._vu_canvas
        c.delete("all")
        n  = len(self._vu)
        bw = 9; gap = 3; total_w = n*(bw+gap)-gap
        ox = (264 - total_w) // 2
        max_h = 50; oy = 56

        for i, v in enumerate(self._vu):
            x0 = ox + i*(bw+gap)
            x1 = x0 + bw
            bar_h = int(v * max_h)

            # Сегментированный бар (4 сегмента)
            seg_h = max_h // 4
            for s in range(4):
                sy0 = oy - (s+1)*seg_h + 2
                sy1 = oy - s*seg_h
                # цвет сегмента
                if s == 3:  col = RED_HOT   # top: red
                elif s == 2: col = ORANGE   # upper: orange
                else:        col = GREEN    # low: green
                dim_col = _blend(col, BG, 0.82)
                filled = bar_h > s * seg_h
                fill = col if filled else dim_col
                c.create_rectangle(x0, sy0, x1, sy1-1, fill=fill, outline="")

    # ── Список игр ────────────────────────────────────────────────────────────

    def _build_gamelist(self, parent):
        frame = tk.Frame(parent, bg=BG, width=220)
        frame.pack(side="left", fill="y")
        frame.pack_propagate(False)

        tk.Label(frame, text="  ВЫБОР ИГРЫ", font=("Consolas", 8, "bold"),
                 bg=BG, fg=TEXT_DIM).pack(fill="x", pady=(10, 4))

        self._game_canvas = tk.Canvas(frame, bg=BG, highlightthickness=0,
                                       width=220, height=330)
        self._game_canvas.pack(fill="both", expand=True)
        self._game_canvas.bind("<Button-1>",  self._on_game_click)
        self._game_canvas.bind("<Motion>",    self._on_game_hover)
        self._game_canvas.bind("<Leave>",     self._on_game_leave)
        self._hover_game = -1
        self._draw_gamelist()

    def _draw_gamelist(self, hover=-1):
        c = self._game_canvas; c.delete("all")
        iw = 220; ih = 38; pad = 4

        for i, g in enumerate(GAMES):
            y0 = pad + i * (ih + 2)
            y1 = y0 + ih
            selected = (i == self._selected_game)
            hovered  = (i == hover)

            # Фон карточки
            if selected:
                bg = RED_DIM; border = RED; fg = TEXT; sym = "▶"
            elif hovered:
                bg = CARD2; border = BORDER2; fg = TEXT_MID; sym = " "
            else:
                bg = PANEL; border = BORDER; fg = TEXT_DIM; sym = " "

            # Рисуем карточку
            c.create_rectangle(4, y0, iw-4, y1, fill=bg, outline=border)

            # Левая полоска у выбранной
            if selected:
                c.create_rectangle(4, y0, 8, y1, fill=RED, outline="")

            # Текст
            c.create_text(22, (y0+y1)//2, text=sym, fill=RED if selected else TEXT_DIM,
                          font=("Consolas", 9, "bold"), anchor="w")
            c.create_text(32, (y0+y1)//2, text=g["short"], fill=fg,
                          font=("Consolas", 10), anchor="w")

            # "NO WAD" пометка
            if g["iwad"] and not os.path.exists(os.path.join(SCRIPT_DIR, g["iwad"])):
                c.create_text(iw-10, (y0+y1)//2, text="●", fill=RED_MID,
                              font=("Consolas", 8), anchor="e")

    def _on_game_click(self, e):
        ih = 40; pad = 4
        idx = (e.y - pad) // (ih)
        if 0 <= idx < len(GAMES):
            self._selected_game = idx
            self._draw_gamelist(self._hover_game)
            self._update_launch_label()

    def _on_game_hover(self, e):
        ih = 40; pad = 4
        idx = (e.y - pad) // ih
        if idx != self._hover_game:
            self._hover_game = idx if 0 <= idx < len(GAMES) else -1
            self._draw_gamelist(self._hover_game)

    def _on_game_leave(self, e):
        self._hover_game = -1
        self._draw_gamelist(-1)

    # ── Правая колонка ────────────────────────────────────────────────────────

    def _build_controls(self, parent):
        col = tk.Frame(parent, bg=BG)
        col.pack(side="left", fill="both", expand=True, padx=16, pady=10)

        tk.Label(col, text="ИНСТРУМЕНТ", font=("Consolas", 8, "bold"),
                 bg=BG, fg=TEXT_DIM).pack(anchor="w", pady=(2, 6))

        # ── Карточки инструментов ─────────────────────────────────────────────
        cards = tk.Frame(col, bg=BG)
        cards.pack(fill="x")

        self._guitar_card = self._make_instrument_card(
            cards, "GUITAR", "🎸", "E  A  D  G  B  e",
            "Электрогитара · 6 струн", RED, RED_DIM, RED_MID,
            lambda: self._set_instrument("guitar")
        )
        self._guitar_card.pack(side="left", padx=(0, 8))

        self._bass_card = self._make_instrument_card(
            cards, "BASS", "🎵", "E     A     D     G",
            "Бас-гитара · 4 струны", BLUE, BLUE_DIM, BLUE_MID,
            lambda: self._set_instrument("bass")
        )
        self._bass_card.pack(side="left")

        self._refresh_instrument_cards()

        # ── Мини-схема управления ──────────────────────────────────────────────
        ctrl_frame = tk.Frame(col, bg=CARD, highlightthickness=1,
                              highlightbackground=BORDER)
        ctrl_frame.pack(fill="x", pady=(10, 0))

        ctrl_rows = [
            ("E/A/D/G",    "W S A D",   "Движение",          RED,      TEXT_MID),
            ("B / e",      "← →",       "Поворот (гитара)",   RED,      TEXT_MID),
            ("Удар слабый","Space",      "Использовать/открыть",GOLD,    TEXT_MID),
            ("Удар сильный","Ctrl",      "Выстрел",            ORANGE,   TEXT_MID),
            ("Palm mute",  "]",          "Следующее оружие",   BLUE_HOT, TEXT_MID),
        ]
        for i, (src, key, desc, sc, dc) in enumerate(ctrl_rows):
            row = tk.Frame(ctrl_frame, bg=CARD if i % 2 == 0 else CARD2)
            row.pack(fill="x")
            tk.Label(row, text=f"  {src}", font=("Consolas", 8), bg=row["bg"],
                     fg=sc, width=14, anchor="w").pack(side="left", pady=2)
            tk.Label(row, text="→", font=("Consolas", 8), bg=row["bg"],
                     fg=TEXT_DIM).pack(side="left")
            tk.Label(row, text=f" {key}", font=("Consolas", 8, "bold"), bg=row["bg"],
                     fg=GREEN, width=8, anchor="w").pack(side="left")
            tk.Label(row, text=desc, font=("Consolas", 8), bg=row["bg"],
                     fg=dc).pack(side="left")

        tk.Frame(col, bg=BORDER, height=1).pack(fill="x", pady=(10, 10))

        # ── Launch кнопка ─────────────────────────────────────────────────────
        self._launch_cv = tk.Canvas(col, width=460, height=52, bg=BG,
                                     highlightthickness=0)
        self._launch_cv.pack()
        self._launch_cv.bind("<Button-1>",  lambda e: self._launch())
        self._launch_cv.bind("<Enter>",     lambda e: setattr(self, "_hover_launch", True))
        self._launch_cv.bind("<Leave>",     lambda e: setattr(self, "_hover_launch", False))
        self._launch_label = "LAUNCH DOOM"
        self._draw_launch_btn()

        # ── Нижние кнопки ─────────────────────────────────────────────────────
        btns = tk.Frame(col, bg=BG)
        btns.pack(fill="x", pady=(10, 0))

        self._make_flat_btn(btns, "📚  Обучение",      GOLD,    GOLD_DIM,  self._tutorial).pack(side="left", padx=(0, 8))
        self._make_flat_btn(btns, "⚙️  Зависимости",   TEXT_MID, CARD,     self._setup).pack(side="left", padx=(0, 8))
        self._make_flat_btn(btns, "🎮  Только контроллер", TEXT_MID, CARD, self._ctrl_only).pack(side="left")

    def _make_instrument_card(self, parent, title, icon, strings, subtitle,
                               accent, bg_dim, border, cmd):
        cv = tk.Canvas(parent, width=215, height=110, bg=CARD,
                        highlightthickness=1, highlightbackground=BORDER,
                        cursor="hand2")
        cv.bind("<Button-1>", lambda e, c=cmd: c())

        def draw(selected):
            cv.delete("all")
            w, h = 215, 110
            bg = bg_dim if selected else CARD
            cv.configure(bg=bg, highlightbackground=accent if selected else BORDER)

            # Верхняя полоска
            if selected:
                cv.create_rectangle(0, 0, w, 4, fill=accent, outline="")

            # Иконка
            cv.create_text(28, 30, text=icon, font=("Segoe UI Emoji", 20), fill=accent, anchor="center")

            # Заголовок
            cv.create_text(52, 22, text=title, font=("Consolas", 13, "bold"),
                           fill=accent if selected else TEXT_DIM, anchor="w")
            cv.create_text(52, 40, text=subtitle, font=("Consolas", 8),
                           fill=TEXT_MID if selected else TEXT_DIM, anchor="w")

            # Строки — нотки
            cv.create_rectangle(8, 55, w-8, 56, fill=BORDER, outline="")
            cv.create_text(w//2, 75, text=strings,
                           font=("Consolas", 10, "bold"),
                           fill=accent if selected else TEXT_DIM, anchor="center")

            if selected:
                cv.create_text(w//2, 96, text="● ВЫБРАНО", font=("Consolas", 8, "bold"),
                               fill=accent, anchor="center")
            else:
                cv.create_text(w//2, 96, text="нажми для выбора", font=("Consolas", 8),
                               fill=TEXT_DIM, anchor="center")

        cv._draw = draw
        return cv

    def _refresh_instrument_cards(self):
        self._guitar_card._draw(self._instrument == "guitar")
        self._bass_card._draw(self._instrument == "bass")

    def _set_instrument(self, mode):
        self._instrument = mode
        self._refresh_instrument_cards()

    def _make_flat_btn(self, parent, text, fg, bg, cmd):
        b = tk.Label(parent, text=text, font=("Consolas", 9),
                     bg=bg, fg=fg, relief="flat", cursor="hand2",
                     padx=10, pady=6)
        b.bind("<Button-1>", lambda e: cmd())
        b.bind("<Enter>", lambda e: b.config(bg=_blend(bg, TEXT, 0.1)))
        b.bind("<Leave>", lambda e: b.config(bg=bg))
        return b

    # ── Launch-кнопка ────────────────────────────────────────────────────────

    def _update_launch_label(self):
        g = GAMES[self._selected_game]
        if g["iwad"] is None:
            self._launch_label = "ЗАПУСТИТЬ КОНТРОЛЛЕР"
        else:
            self._launch_label = f"▶  LAUNCH  {g['short'].upper()}"

    def _draw_launch_btn(self):
        c = self._launch_cv; c.delete("all")
        w, h = 460, 52
        p = self._pulse
        hovered = self._hover_launch

        if hovered:
            base = _blend(RED, RED_HOT, 0.5 + 0.5 * math.sin(p * math.pi))
            border = RED_HOT
        else:
            base = _blend(RED_DIM, RED_MID, 0.4 + 0.4 * math.sin(p * math.pi))
            border = RED_MID

        # Кнопка с скруглёнными "концами" через овал
        r = 8
        c.create_rectangle(r, 2, w-r, h-2, fill=base, outline="")
        c.create_oval(2, 2, r*2, h-2, fill=base, outline="")
        c.create_oval(w-r*2, 2, w-2, h-2, fill=base, outline="")
        c.create_rectangle(2, 2, w-2, h-2, outline=border, width=1)

        # Шеврон-декор
        arrow_col = _blend(RED_HOT, "#ffffff", 0.5) if hovered else _blend(RED, RED_HOT, 0.5)
        for dx in [-22, -11, 0]:
            c.create_text(w//2 - 60 + dx, h//2, text="▶",
                          font=("Consolas", 10, "bold"), fill=arrow_col, anchor="center")
        for dx in [0, 11, 22]:
            c.create_text(w//2 + 60 + dx, h//2, text="◀",
                          font=("Consolas", 10, "bold"), fill=arrow_col, anchor="center")

        # Текст
        txt_color = "#ffffff" if hovered else TEXT
        c.create_text(w//2, h//2, text=self._launch_label,
                      font=("Consolas", 14, "bold"), fill=txt_color, anchor="center")
        self._launch_cv.config(cursor="hand2")

    # ── Статусбар ─────────────────────────────────────────────────────────────

    def _build_statusbar(self):
        sb = tk.Frame(self, bg=PANEL, height=32)
        sb.pack(fill="x", side="bottom")
        sb.pack_propagate(False)

        # Бэкенд
        bc = BLUE if self._audio_backend == "sounddevice" else ORANGE
        tk.Label(sb, text=f"  🔊 {self._audio_backend}",
                 font=("Consolas", 8), bg=PANEL, fg=bc).pack(side="left", pady=6)

        # Статус
        self._status_lbl = tk.Label(sb, text=f"  ●  {self._status_text}",
                                     font=("Consolas", 9), bg=PANEL, fg=TEXT_MID)
        self._status_lbl.pack(side="left", padx=8)

        # Python версия
        v = sys.version_info
        tk.Label(sb, text=f"Python {v.major}.{v.minor}.{v.micro}  ",
                 font=("Consolas", 8), bg=PANEL, fg=TEXT_DIM).pack(side="right")

        # Разделитель вертикальный
        tk.Frame(sb, bg=BORDER, width=1).pack(side="right", fill="y", pady=6)
        tk.Label(sb, text="  v2.0  ", font=("Consolas", 8), bg=PANEL, fg=TEXT_DIM).pack(side="right")

    def _set_status(self, text, color=TEXT_MID):
        self._status_lbl.config(text=f"  ●  {text}", fg=color)

    # ── Анимация ─────────────────────────────────────────────────────────────

    def _start_animate(self):
        self._animate()

    def _animate(self):
        self._vu_tick += 1

        # Случайные всплески VU-метра
        if self._vu_tick % 12 == 0:
            i = random.randint(0, len(self._vu)-1)
            self._vut[i] = random.uniform(0.25, 0.95)

        # Дрейф к тишине
        for i in range(len(self._vut)):
            self._vut[i] *= 0.88
            self._vut[i] = max(self._vut[i], 0.04)
            self._vu[i] += (self._vut[i] - self._vu[i]) * 0.35

        self._draw_vu()

        # Пульс launch-кнопки
        self._pulse += 0.07 * self._pulse_dir
        if self._pulse >= 1.0: self._pulse = 1.0; self._pulse_dir = -1
        if self._pulse <= 0.0: self._pulse = 0.0; self._pulse_dir = 1
        self._draw_launch_btn()

        self.after(45, self._animate)

    # ── Запуск ────────────────────────────────────────────────────────────────

    def _launch(self):
        game = GAMES[self._selected_game]
        mode = self._instrument

        gzdoom = os.path.join(SCRIPT_DIR, "gzdoom.exe")
        script = os.path.join(SCRIPT_DIR, "guitar_to_doom.py")

        if not os.path.exists(script):
            self._set_status("guitar_to_doom.py не найден!", RED_HOT)
            return

        # Запуск GZDoom
        if game["iwad"]:
            iwad_path = os.path.join(SCRIPT_DIR, game["iwad"])
            if not os.path.exists(gzdoom):
                self._set_status("gzdoom.exe не найден!", RED_HOT); return
            if not os.path.exists(iwad_path):
                self._set_status(f"WAD не найден: {game['iwad']}", RED_HOT); return

            gz_cmd = [
                gzdoom,
                "-config",  os.path.join(SCRIPT_DIR, "gzdoom.ini"),
                "-savedir", os.path.join(SCRIPT_DIR, "save"),
                "-iwad",    iwad_path,
            ]
            for f in game["extra"]:
                fp = os.path.join(SCRIPT_DIR, f)
                if os.path.exists(fp):
                    gz_cmd += ["-file", fp]
            subprocess.Popen(gz_cmd, cwd=SCRIPT_DIR)

        # Запуск контроллера
        py_cmd = [sys.executable, script]
        if mode == "bass":
            py_cmd.append("--bass")
        subprocess.Popen(py_cmd, cwd=SCRIPT_DIR, creationflags=subprocess.CREATE_NEW_CONSOLE)

        instr = "Bass" if mode == "bass" else "Guitar"
        self._set_status(f"[OK] {instr} · {game['short']} запущен", GREEN)

    def _tutorial(self):
        script = os.path.join(SCRIPT_DIR, "guitar_tutorial.py")
        if not os.path.exists(script):
            self._set_status("guitar_tutorial.py не найден!", RED_HOT); return
        py_cmd = [sys.executable, script]
        if self._instrument == "bass":
            py_cmd.append("--bass")
        subprocess.Popen(py_cmd, cwd=SCRIPT_DIR, creationflags=subprocess.CREATE_NEW_CONSOLE)
        self._set_status("Обучение запущено", GOLD)

    def _setup(self):
        script = os.path.join(SCRIPT_DIR, "setup.py")
        if not os.path.exists(script):
            self._set_status("setup.py не найден!", RED_HOT); return
        subprocess.Popen([sys.executable, script], cwd=SCRIPT_DIR,
                         creationflags=subprocess.CREATE_NEW_CONSOLE)
        self._set_status("Установка зависимостей...", BLUE_HOT)

    def _ctrl_only(self):
        script = os.path.join(SCRIPT_DIR, "guitar_to_doom.py")
        if not os.path.exists(script):
            self._set_status("guitar_to_doom.py не найден!", RED_HOT); return
        py_cmd = [sys.executable, script]
        if self._instrument == "bass":
            py_cmd.append("--bass")
        subprocess.Popen(py_cmd, cwd=SCRIPT_DIR, creationflags=subprocess.CREATE_NEW_CONSOLE)
        self._set_status("Контроллер запущен без игры", TEXT_MID)


if __name__ == "__main__":
    app = GuitarDoomLauncher()
    app.mainloop()
