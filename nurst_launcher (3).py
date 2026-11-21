import asyncio
import hashlib
import json
import os
import queue
import shutil
import subprocess
import sys
import threading
import time
import traceback
import uuid
import webbrowser
import tkinter as tk
from pathlib import Path
from tkinter import font as tkfont
from tkinter import ttk, messagebox, simpledialog, filedialog

import minecraft_launcher_lib as mll

try:  # Discord Rich Presence (необязательно): pip install pypresence
    from pypresence import Presence
except Exception:
    Presence = None

try:  # Pillow необязателен, но с ним иконка обрезается/масштабируется сама
    from PIL import Image, ImageDraw, ImageTk
    PIL_OK = True
except Exception:
    PIL_OK = False

APP_NAME = "Nurst Launcher"

# --- Discord Rich Presence: статус «Играет в Nurst Launcher»
# Application ID создаётся на https://discord.com/developers/applications
# (приложение с названием "Nurst Launcher") и вписывается ТОЛЬКО здесь, в коде.
# В самом лаунчере остаётся лишь переключатель «Статус в Discord» вкл/выкл.
DISCORD_APP_ID = "1569231893902397554"
DISCORD_BUTTON_LABEL = "Telegram"
DISCORD_BUTTON_URL = ""  # ссылка кнопки под статусом (необязательно)
DEFAULT_VERSION = "1.16.5"
LOADERS = ("Vanilla", "Fabric", "Quilt", "Forge")

# Сборки: у каждой своя папка прямо в .nurstclient\<название> (моды, сохранения, настройки)
NO_BUILD = "— Без сборки —"
# Имена, которые нельзя использовать для сборки (служебные папки игры)
RESERVED_NAMES = {
    "versions", "assets", "libraries", "runtime", "mods", "logs", "saves",
    "resourcepacks", "shaderpacks", "config", "screenshots", "crash-reports",
}

_TRANSLIT = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e", "ж": "zh",
    "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m", "н": "n", "о": "o",
    "п": "p", "р": "r", "с": "s", "т": "t", "у": "u", "ф": "f", "х": "h", "ц": "c",
    "ч": "ch", "ш": "sh", "щ": "sch", "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu",
    "я": "ya", "і": "i", "ї": "yi", "є": "ye", "ґ": "g",
}
FALLBACK_VERSIONS = ("1.16.5", "1.12.2", "1.18.2", "1.19.4", "1.20.1", "1.20.4", "1.21")

# Официальный client_id лаунчера Mojang (используется для входа через Microsoft)
MS_CLIENT_ID = "00000000402b5328"
MS_REDIRECT_URI = "https://login.live.com/oauth20_desktop.srf"

# Папка игры: C:\Users\<Юзер>\.nurstclient (версии, сохранения, настройки, иконка)
# Это папка по умолчанию; в настройках её можно сменить. Файл настроек лаунчера и иконка
# всегда лежат здесь, чтобы лаунчер находил их, какую бы папку игры ни выбрали.
GAME_DIR = str(Path.home() / ".nurstclient")
CONFIG_DIR = GAME_DIR

ICON_NAMES = ("icon.ico", "icon.png", "icon.jpg", "icon.jpeg", "logo.png", "logo.jpg")

FONT = "Segoe UI"
HEADER_H = 112

BG = "#0b0b0e"            # фон окна
CARD = "#14141a"          # карточки
CARD_BORDER = "#25252e"   # рамка карточек
INPUT = "#1c1c24"         # поля ввода, неактивные кнопки
INPUT_HOVER = "#272733"
FG = "#f4f4f6"
FG_DIM = "#9393a3"
ACCENT = "#ff6a00"        # фирменный оранжевый
ACCENT_HOVER = "#ff8533"
ACCENT_DARK = "#c95200"
OK = "#2ee6a6"
WARN = "#ffb84d"
ERR = "#ff5c5c"


def offline_uuid(username: str) -> str:
    """Тот же UUID, который генерирует сервер с online-mode=false
    (md5 от 'OfflinePlayer:<ник>'). Благодаря этому инвентарь, права и
    привязки на пиратском сервере не слетают при каждом входе."""
    digest = bytearray(hashlib.md5(f"OfflinePlayer:{username}".encode("utf-8")).digest())
    digest[6] = (digest[6] & 0x0F) | 0x30
    digest[8] = (digest[8] & 0x3F) | 0x80
    return str(uuid.UUID(bytes=bytes(digest)))


def slugify(name: str) -> str:
    """Название сборки -> безопасное имя папки (кириллица транслитерируется,
    потому что Java 8 на Windows плохо дружит с не-ASCII путями)."""
    out = []
    for ch in name.strip().lower():
        if ch in _TRANSLIT:
            out.append(_TRANSLIT[ch])
        elif ch.isascii() and (ch.isalnum() or ch in "-_"):
            out.append(ch)
        elif ch in " .":
            out.append("_")
    return "".join(out).strip("_")[:40]


# ===================================================================== оформление
# Свои виджеты: скруглённые кнопки, ползунок, переключатель, прогресс-бар.
# Стандартный Tkinter так не умеет, поэтому всё рисуется на Canvas.

def _rgb(color: str):
    color = color.lstrip("#")
    return tuple(int(color[i:i + 2], 16) for i in (0, 2, 4))


def _hex(rgb) -> str:
    return "#%02x%02x%02x" % tuple(max(0, min(255, int(v))) for v in rgb)


def lerp_color(c1: str, c2: str, t: float) -> str:
    a, b = _rgb(c1), _rgb(c2)
    return _hex([a[i] + (b[i] - a[i]) * t for i in range(3)])


def round_rect(cv, x1, y1, x2, y2, r, **kw):
    """Скруглённый прямоугольник (при r = высота/2 получается «таблетка»)."""
    r = max(0, min(r, (x2 - x1) / 2, (y2 - y1) / 2))
    pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
           x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
    return cv.create_polygon(pts, smooth=True, **kw)


def round_image(img, size: int):
    """Обрезает картинку в круг со сглаженным краем (нужен Pillow)."""
    scale = 4
    base = img.resize((size, size), Image.LANCZOS)
    mask = Image.new("L", (size * scale, size * scale), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size * scale - 1, size * scale - 1), fill=255)
    base.putalpha(mask.resize((size, size), Image.LANCZOS))
    return base


# стиль кнопки: (фон, фон при наведении, фон при нажатии, цвет текста)
BTN_STYLES = {
    "primary": (ACCENT, ACCENT_HOVER, ACCENT_DARK, "#ffffff"),
    "ghost": (INPUT, INPUT_HOVER, "#33333f", FG),
    "tab_off": (INPUT, INPUT_HOVER, "#33333f", FG_DIM),
    "danger": (INPUT, "#3b1c1f", "#4d2428", ERR),
}
BTN_DISABLED = ("#26262e", "#6d6d7a")

# Цвета, зависящие от темы. set_theme() подменяет их все разом (интерфейс после этого пересобирается).
SWITCH_OFF = "#35353f"    # выключенный переключатель
FOOT = "#5d5d6b"          # серый текст подвала
HEADER_TOP = "#2c1506"    # верх градиента в шапке
DARK_BAR = True           # тёмный заголовок окна Windows

THEMES = {
    "dark": dict(
        BG="#0b0b0e", CARD="#14141a", CARD_BORDER="#25252e", INPUT="#1c1c24", INPUT_HOVER="#272733",
        FG="#f4f4f6", FG_DIM="#9393a3", ACCENT="#ff6a00", ACCENT_HOVER="#ff8533", ACCENT_DARK="#c95200",
        OK="#2ee6a6", WARN="#ffb84d", ERR="#ff5c5c",
        PRESS="#33333f", DANGER_HOVER="#3b1c1f", DANGER_PRESS="#4d2428",
        DISABLED_BG="#26262e", DISABLED_FG="#6d6d7a",
        SWITCH_OFF="#35353f", FOOT="#5d5d6b", HEADER_TOP="#2c1506", DARK_BAR=True,
    ),
    "light": dict(  # чёрное на белом
        BG="#f2f2f5", CARD="#ffffff", CARD_BORDER="#d9d9e1", INPUT="#eeeef2", INPUT_HOVER="#e2e2e9",
        FG="#111116", FG_DIM="#5f5f6c", ACCENT="#ff6a00", ACCENT_HOVER="#ff8533", ACCENT_DARK="#c95200",
        OK="#0c9a6b", WARN="#c77700", ERR="#d62f2f",
        PRESS="#d3d3dc", DANGER_HOVER="#fadcdc", DANGER_PRESS="#f3c4c4",
        DISABLED_BG="#e6e6ec", DISABLED_FG="#a0a0ac",
        SWITCH_OFF="#c4c4ce", FOOT="#8a8a97", HEADER_TOP="#ffd8bd", DARK_BAR=False,
    ),
}


def set_theme(name: str):
    """Переключает палитру ("dark" / "light"). Виджеты берут цвета при создании,
    поэтому после смены темы интерфейс нужно пересобрать."""
    global BG, CARD, CARD_BORDER, INPUT, INPUT_HOVER, FG, FG_DIM, ACCENT, ACCENT_HOVER, ACCENT_DARK
    global OK, WARN, ERR, SWITCH_OFF, FOOT, HEADER_TOP, DARK_BAR, BTN_DISABLED, THEME
    t = THEMES.get(name) or THEMES["dark"]
    THEME = name if name in THEMES else "dark"
    BG, CARD, CARD_BORDER, INPUT, INPUT_HOVER = t["BG"], t["CARD"], t["CARD_BORDER"], t["INPUT"], t["INPUT_HOVER"]
    FG, FG_DIM = t["FG"], t["FG_DIM"]
    ACCENT, ACCENT_HOVER, ACCENT_DARK = t["ACCENT"], t["ACCENT_HOVER"], t["ACCENT_DARK"]
    OK, WARN, ERR = t["OK"], t["WARN"], t["ERR"]
    SWITCH_OFF, FOOT, HEADER_TOP, DARK_BAR = t["SWITCH_OFF"], t["FOOT"], t["HEADER_TOP"], t["DARK_BAR"]
    BTN_DISABLED = (t["DISABLED_BG"], t["DISABLED_FG"])
    BTN_STYLES.clear()
    BTN_STYLES.update({
        "primary": (ACCENT, ACCENT_HOVER, ACCENT_DARK, "#ffffff"),
        "ghost": (INPUT, INPUT_HOVER, t["PRESS"], FG),
        "tab_off": (INPUT, INPUT_HOVER, t["PRESS"], FG_DIM),
        "danger": (INPUT, t["DANGER_HOVER"], t["DANGER_PRESS"], ERR),
    })


THEME = "dark"


class RoundedButton(tk.Canvas):
    """Скруглённая кнопка с плавной подсветкой при наведении.
    Поддерживает .config(state="disabled"/"normal", text=..., command=...)."""

    def __init__(self, parent, text, command=None, style="primary",
                 font=(FONT, 11, "bold"), radius=10, padx=18, pady=9):
        self._rb_font = tkfont.Font(font=font)
        self._rb_text = text
        self._rb_cmd = command
        self._rb_radius = radius
        self._rb_state = "normal"
        self._rb_colors = BTN_STYLES[style]
        width = self._rb_font.measure(text) + 2 * padx
        height = self._rb_font.metrics("linespace") + 2 * pady
        super().__init__(parent, width=width, height=height, bg=parent.cget("bg"),
                         highlightthickness=0, bd=0, cursor="hand2")
        self._rb_cur = self._rb_colors[0]
        self._rb_goal = self._rb_cur
        self._rb_anim = None
        self._rb_shape = None
        self._rb_label = None
        self.bind("<Configure>", lambda e: self._rb_draw())
        self.bind("<Enter>", self._rb_enter)
        self.bind("<Leave>", self._rb_leave)
        self.bind("<ButtonPress-1>", self._rb_press)
        self.bind("<ButtonRelease-1>", self._rb_release)

    # --- цвета
    def _rb_fg(self):
        return BTN_DISABLED[1] if self._rb_state == "disabled" else self._rb_colors[3]

    def _rb_rest(self):
        return BTN_DISABLED[0] if self._rb_state == "disabled" else self._rb_colors[0]

    # --- рисование
    def _rb_draw(self):
        w, h = self.winfo_width(), self.winfo_height()
        if w < 4 or h < 4:
            w, h = self.winfo_reqwidth(), self.winfo_reqheight()
        self.delete("all")
        self._rb_shape = round_rect(self, 1, 1, w - 1, h - 1, self._rb_radius,
                                    fill=self._rb_cur, outline="")
        self._rb_label = self.create_text(w / 2, h / 2, text=self._rb_text,
                                          fill=self._rb_fg(), font=self._rb_font)

    def _rb_paint(self):
        try:
            if self._rb_shape is not None:
                self.itemconfigure(self._rb_shape, fill=self._rb_cur)
        except tk.TclError:
            pass

    def _rb_go(self, color, instant=False):
        self._rb_goal = color
        if instant:
            self._rb_cur = color
            self._rb_paint()
        elif self._rb_anim is None:
            self._rb_step()

    def _rb_step(self):
        self._rb_anim = None
        cur, goal = _rgb(self._rb_cur), _rgb(self._rb_goal)
        if cur == goal:
            return
        nxt = [g if abs(g - c) <= 3 else c + (g - c) * 0.4 for c, g in zip(cur, goal)]
        self._rb_cur = _hex(nxt)
        self._rb_paint()
        self._rb_anim = self.after(16, self._rb_step)

    # --- события мыши
    def _rb_enter(self, e):
        if self._rb_state == "normal":
            self._rb_go(self._rb_colors[1])

    def _rb_leave(self, e):
        if self._rb_state == "normal":
            self._rb_go(self._rb_colors[0])

    def _rb_press(self, e):
        if self._rb_state == "normal":
            self._rb_go(self._rb_colors[2], instant=True)

    def _rb_release(self, e):
        if self._rb_state != "normal":
            return
        inside = 0 <= e.x <= self.winfo_width() and 0 <= e.y <= self.winfo_height()
        self._rb_go(self._rb_colors[1] if inside else self._rb_colors[0])
        if inside and self._rb_cmd:
            self._rb_cmd()

    # --- публичный интерфейс
    def set_style(self, style):
        self._rb_colors = BTN_STYLES[style]
        self._rb_go(self._rb_rest())
        if self._rb_label is not None:
            self.itemconfigure(self._rb_label, fill=self._rb_fg())

    def configure(self, cnf=None, **kw):
        if cnf:
            kw = {**cnf, **kw}
        if "command" in kw:
            self._rb_cmd = kw.pop("command")
        if "text" in kw:
            self._rb_text = kw.pop("text")
            if self._rb_label is not None:
                self.itemconfigure(self._rb_label, text=self._rb_text)
        if "state" in kw:
            disabled = kw.pop("state") == "disabled"
            self._rb_state = "disabled" if disabled else "normal"
            super().configure(cursor="arrow" if disabled else "hand2")
            self._rb_go(self._rb_rest())
            if self._rb_label is not None:
                self.itemconfigure(self._rb_label, fill=self._rb_fg())
        if kw:
            super().configure(**kw)

    config = configure


class SlimProgress(tk.Canvas):
    """Тонкий скруглённый прогресс-бар. Совместим с .config(value=, maximum=)."""

    def __init__(self, parent, width=540, height=8):
        self._pb_h = height
        self._pb_value = 0
        self._pb_max = 100
        super().__init__(parent, width=width, height=height, bg=parent.cget("bg"),
                         highlightthickness=0, bd=0)
        self.bind("<Configure>", lambda e: self._pb_draw())

    def _pb_draw(self):
        w = self.winfo_width()
        if w < 4:
            w = self.winfo_reqwidth()
        h = self._pb_h
        self.delete("all")
        round_rect(self, 0, 0, w, h, h / 2, fill=INPUT, outline="")
        frac = max(0.0, min(1.0, self._pb_value / max(self._pb_max, 1)))
        if frac > 0:
            fill_w = max(h, w * frac)
            round_rect(self, 0, 0, fill_w, h, h / 2, fill=ACCENT, outline="")
            round_rect(self, 0, 0, fill_w, h / 2 + 1, h / 2, fill=ACCENT_HOVER, outline="")

    def configure(self, cnf=None, **kw):
        if cnf:
            kw = {**cnf, **kw}
        redraw = False
        if "value" in kw:
            self._pb_value = kw.pop("value")
            redraw = True
        if "maximum" in kw:
            self._pb_max = kw.pop("maximum")
            redraw = True
        if kw:
            super().configure(**kw)
        if redraw:
            self._pb_draw()

    config = configure

    def cget(self, key):
        if key == "value":
            return self._pb_value
        if key == "maximum":
            return self._pb_max
        return super().cget(key)

    __getitem__ = cget


class Slider(tk.Canvas):
    """Ползунок со значением в целых числах, привязан к IntVar."""
    PAD = 12

    def __init__(self, parent, variable, from_=1, to=16, width=300, height=30):
        self._sl_var = variable
        self._sl_lo = from_
        self._sl_hi = to
        super().__init__(parent, width=width, height=height, bg=parent.cget("bg"),
                         highlightthickness=0, bd=0, cursor="hand2")
        self.bind("<Configure>", lambda e: self._sl_draw())
        self.bind("<Button-1>", self._sl_mouse)
        self.bind("<B1-Motion>", self._sl_mouse)
        variable.trace_add("write", lambda *a: self._sl_draw())

    def _sl_value(self):
        try:
            return max(self._sl_lo, min(self._sl_hi, int(self._sl_var.get())))
        except Exception:
            return self._sl_lo

    def _sl_mouse(self, e):
        w = self.winfo_width()
        span = max(1, w - 2 * self.PAD)
        t = max(0.0, min(1.0, (e.x - self.PAD) / span))
        self._sl_var.set(round(self._sl_lo + t * (self._sl_hi - self._sl_lo)))

    def _sl_draw(self):
        try:
            w, h = self.winfo_width(), self.winfo_height()
            if w < 4 or h < 4:
                w, h = self.winfo_reqwidth(), self.winfo_reqheight()
            self.delete("all")
            pad, cy = self.PAD, h / 2
            t = (self._sl_value() - self._sl_lo) / max(1, self._sl_hi - self._sl_lo)
            x = pad + (w - 2 * pad) * t
            round_rect(self, pad, cy - 3, w - pad, cy + 3, 3, fill=INPUT_HOVER, outline="")
            if x > pad:
                round_rect(self, pad, cy - 3, x, cy + 3, 3, fill=ACCENT, outline="")
            self.create_oval(x - 10, cy - 10, x + 10, cy + 10, fill=ACCENT, outline="")
            self.create_oval(x - 6, cy - 6, x + 6, cy + 6, fill="#ffffff", outline="")
        except tk.TclError:
            pass


class Switch(tk.Canvas):
    """Переключатель (вкл/выкл), привязан к BooleanVar."""

    def __init__(self, parent, variable, command=None):
        self._sw_var = variable
        self._sw_cmd = command
        super().__init__(parent, width=40, height=22, bg=parent.cget("bg"),
                         highlightthickness=0, bd=0, cursor="hand2")
        self.bind("<Button-1>", self.toggle)
        variable.trace_add("write", lambda *a: self._sw_draw())
        self._sw_draw()

    def toggle(self, event=None):
        self._sw_var.set(not self._sw_var.get())
        if self._sw_cmd:
            self._sw_cmd()

    def _sw_draw(self):
        try:
            on = bool(self._sw_var.get())
        except Exception:
            on = False
        try:
            self.delete("all")
            round_rect(self, 1, 1, 39, 21, 10, fill=ACCENT if on else SWITCH_OFF, outline="")
            x = 29 if on else 11
            self.create_oval(x - 8, 3, x + 8, 19, fill="#ffffff", outline="")
        except tk.TclError:
            pass


class DiscordPresence:
    """Discord Rich Presence. Всё общение с Discord идёт в отдельном потоке.
    Если Discord закрыт или pypresence не установлен, молча ничего не делает;
    когда Discord появится, подключается сам (проверка раз в RETRY_SECONDS)."""

    RETRY_SECONDS = 20

    def __init__(self):
        self._q = queue.Queue()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    @property
    def available(self) -> bool:
        return Presence is not None

    def set_app(self, app_id):
        self._q.put(("app", str(app_id or "").strip()))

    def update(self, **fields):
        self._q.put(("update", fields))

    def clear(self):
        self._q.put(("clear", None))

    def shutdown(self):
        self._q.put(("quit", None))
        self._thread.join(timeout=1.5)

    def _run(self):
        if Presence is None:
            return
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        rpc = None
        app_id = ""
        fields = None

        def drop(clear=False):
            nonlocal rpc
            if rpc is not None:
                try:
                    if clear:
                        rpc.clear()
                    rpc.close()
                except Exception:
                    pass
            rpc = None

        while True:
            try:
                kind, data = self._q.get(timeout=self.RETRY_SECONDS)
            except queue.Empty:
                kind, data = "tick", None

            if kind == "quit":
                drop(clear=True)
                try:
                    loop.close()
                except Exception:
                    pass
                return
            if kind == "app":
                drop()
                app_id = data
            elif kind == "update":
                fields = data
            elif kind == "clear":
                fields = None
            elif kind == "tick" and (rpc is not None or fields is None):
                continue

            if not app_id:
                continue
            try:
                if fields is None:
                    if rpc is not None:
                        rpc.clear()
                    continue
                if rpc is None:
                    rpc = Presence(app_id, loop=loop)
                    rpc.connect()
                rpc.update(**fields)
            except Exception:
                drop()


class NurstLauncherApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        os.makedirs(CONFIG_DIR, exist_ok=True)
        self.config_path = os.path.join(CONFIG_DIR, "nurst_config.json")
        self.config = self.load_config()
        self.minecraft_dir = self.pick_game_dir(self.config.get("game_dir"))
        set_theme(self.config.get("theme", "dark"))

        self.root.title(APP_NAME)
        self.root.configure(bg=BG)
        self.root.resizable(True, True)

        self.auth_data = None
        self.max_progress = 0
        self.running = False
        self.icon_img = None
        self.logo_img = None
        self.all_versions = []

        self.setup_style()
        self.apply_icon()
        self.create_widgets()
        self.toggle_mode()
        self.refresh_builds(self.config.get("build"))
        self.apply_build()
        self.load_versions_thread()
        self.fit_window()
        self.autologin_ms()
        self.root.after(150, self.apply_titlebar)

        self.started_at = int(time.time())
        self.rpc_base = None
        self.rpc = DiscordPresence()
        self.rpc.set_app(self.discord_app_id())
        self.rpc_idle()

        self.fullscreen = False
        self.root.bind("<F11>", self.toggle_fullscreen)
        self.root.bind("<Escape>", self.on_escape)

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    # ------------------------------------------------------------------ config
    def load_config(self) -> dict:
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    @staticmethod
    def pick_game_dir(saved) -> str:
        """Папка игры из настроек; если её нет и создать нельзя (например, отключён диск) — по умолчанию."""
        if isinstance(saved, str) and saved.strip():
            path = os.path.normpath(os.path.expanduser(saved.strip()))
            try:
                os.makedirs(path, exist_ok=True)
                return path
            except OSError:
                pass
        os.makedirs(GAME_DIR, exist_ok=True)
        return GAME_DIR

    def save_config(self):
        try:
            self.config["nickname"] = self.nickname_entry.get().strip()
            self.config["version"] = self.version_combobox.get().strip()
            self.config["ram"] = self.ram_var.get()
            self.config["mode"] = self.login_mode.get()
            self.config["show_all"] = self.show_all_var.get()
            self.config["discord"] = self.discord_var.get()
            self.config["theme"] = "light" if self.light_var.get() else "dark"
            self.config["loader"] = self.loader_combobox.get()
            self.config["build"] = self.build_combobox.get()
            self.save_build_meta()
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[WARN] Не удалось сохранить настройки: {e}")

    def on_close(self):
        self.save_config()
        self.rpc.shutdown()
        self.root.destroy()

    # ----------------------------------------------------------------- discord
    def discord_app_id(self) -> str:
        return str(DISCORD_APP_ID or "").strip()

    def rpc_fields(self, details, state, start):
        fields = {"details": details, "state": state, "large_image": "logo",
                  "large_text": APP_NAME, "start": start}
        url = str(DISCORD_BUTTON_URL or "").strip()
        if url.startswith(("http://", "https://")):
            label = str(DISCORD_BUTTON_LABEL or "Ссылка").strip()
            fields["buttons"] = [{"label": label[:32] or "Ссылка", "url": url}]
        return fields

    def rpc_push(self):
        if self.rpc_base and self.discord_var.get():
            self.rpc.update(**self.rpc_fields(*self.rpc_base))

    def rpc_idle(self):
        self.rpc_base = ("В лаунчере", "Выбирает версию", self.started_at)
        self.rpc_push()

    def rpc_playing(self, version, loader, username):
        extra = f" · {loader}" if loader and loader != "Vanilla" else ""
        self.rpc_base = (f"Играет: {version}{extra}", f"Игрок: {username}", int(time.time()))
        self.rpc_push()

    def watch_game(self, proc):
        """Ждём закрытия игры и возвращаем статус «В лаунчере»."""
        try:
            proc.wait()
        except Exception:
            return
        self.ui(self.rpc_idle)

    def on_discord_toggle(self):
        if self.discord_var.get():
            self.rpc_push()
        else:
            self.rpc.clear()

    # -------------------------------------------------------------------- icon
    def find_icon(self):
        for folder in dict.fromkeys((CONFIG_DIR, self.minecraft_dir)):
            for name in ICON_NAMES:
                path = os.path.join(folder, name)
                if os.path.isfile(path):
                    return path
        return None

    def apply_icon(self):
        """Берёт иконку из папки игры (icon.png / icon.ico / icon.jpg)."""
        path = self.find_icon()
        if not path:
            return
        is_win = sys.platform.startswith("win")
        try:
            if PIL_OK:
                img = Image.open(path).convert("RGBA")
                w, h = img.size
                s = min(w, h)
                left, top = (w - s) // 2, (h - s) // 2
                img = img.crop((left, top, left + s, top + s))  # центральный квадрат
                resample = getattr(getattr(Image, "Resampling", Image), "LANCZOS")

                big = img.resize((256, 256), resample)
                self.icon_img = ImageTk.PhotoImage(big)
                self.root.iconphoto(True, self.icon_img)
                self.logo_img = ImageTk.PhotoImage(round_image(img, 72))

                if is_win:
                    ico_path = os.path.join(CONFIG_DIR, "icon_generated.ico")
                    big.save(ico_path, format="ICO", sizes=[(256, 256), (64, 64), (32, 32), (16, 16)])
                    self.root.iconbitmap(ico_path)
            else:
                if path.lower().endswith(".ico"):
                    if is_win:
                        self.root.iconbitmap(path)
                else:
                    self.icon_img = tk.PhotoImage(file=path)  # без Pillow — только PNG
                    self.root.iconphoto(True, self.icon_img)
                    factor = max(1, self.icon_img.width() // 72)
                    self.logo_img = self.icon_img.subsample(factor, factor)
        except Exception as e:
            print(f"[WARN] Не удалось загрузить иконку: {e}")

    # ------------------------------------------------------------------- style
    def setup_style(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure(
            "TEntry", fieldbackground=INPUT, foreground=FG, insertcolor=FG,
            bordercolor=CARD_BORDER, lightcolor=INPUT, darkcolor=INPUT,
            padding=(10, 7), relief="flat",
        )
        style.map(
            "TEntry",
            bordercolor=[("focus", ACCENT)], lightcolor=[("focus", ACCENT)],
            darkcolor=[("focus", ACCENT)],
            fieldbackground=[("readonly", INPUT)], foreground=[("readonly", FG)],
        )
        style.configure(
            "TCombobox", fieldbackground=INPUT, background=INPUT_HOVER, foreground=FG,
            arrowcolor=ACCENT, bordercolor=CARD_BORDER, lightcolor=INPUT, darkcolor=INPUT,
            arrowsize=16, padding=(8, 6), selectbackground=INPUT, selectforeground=FG,
        )
        style.map(
            "TCombobox",
            fieldbackground=[("readonly", INPUT), ("focus", INPUT)],
            foreground=[("readonly", FG), ("focus", FG)],
            selectbackground=[("readonly", INPUT), ("focus", INPUT)],
            selectforeground=[("readonly", FG), ("focus", FG)],
            bordercolor=[("focus", ACCENT), ("active", ACCENT_DARK)],
            lightcolor=[("focus", ACCENT)], darkcolor=[("focus", ACCENT)],
            arrowcolor=[("active", ACCENT_HOVER)],
            background=[("active", INPUT_HOVER)],
        )

        # выпадающий список версий/загрузчиков/сборок
        opt = self.root.option_add
        opt("*TCombobox*Listbox.background", INPUT)
        opt("*TCombobox*Listbox.foreground", FG)
        opt("*TCombobox*Listbox.selectBackground", ACCENT)
        opt("*TCombobox*Listbox.selectForeground", "#ffffff")
        opt("*TCombobox*Listbox.font", (FONT, 11))
        opt("*TCombobox*Listbox.borderWidth", 0)
        opt("*TCombobox*Listbox.highlightThickness", 0)

    def apply_titlebar(self, window=None):
        """Тёмный заголовок окна с оранжевой рамкой (Windows 10/11, на остальных ничего не делает)."""
        if not sys.platform.startswith("win"):
            return
        try:
            import ctypes
            target = window or self.root
            target.update_idletasks()
            hwnd = ctypes.windll.user32.GetParent(target.winfo_id())
            dwm = ctypes.windll.dwmapi.DwmSetWindowAttribute

            def put(attr, value):
                v = ctypes.c_int(value)
                dwm(hwnd, attr, ctypes.byref(v), ctypes.sizeof(v))

            def bgr(color):       # "#rrggbb" -> 0x00BBGGRR
                r, g, b = _rgb(color)
                return r | (g << 8) | (b << 16)

            put(20, 1 if DARK_BAR else 0)   # тёмный режим заголовка (Win 11 / Win 10 20H1+)
            put(19, 1 if DARK_BAR else 0)   # то же для более старых сборок Win 10
            put(35, bgr(BG))                # цвет заголовка = фон лаунчера
            put(36, bgr(FG))                # цвет текста заголовка
            put(34, 0x00006AFF)   # цвет рамки окна = оранжевый акцент
        except Exception:
            pass

    # ----------------------------------------------------------------- widgets
    def make_card(self, parent, title, action=None):
        """Карточка с рамкой и заголовком. Возвращает внутренний фрейм.
        action=(текст, команда) добавляет маленькую кнопку справа от заголовка
        (она доступна как inner.action_button)."""
        outer = tk.Frame(parent, bg=CARD, highlightbackground=CARD_BORDER,
                         highlightcolor=CARD_BORDER, highlightthickness=1)
        outer.pack(fill="x", pady=(0, 10))
        inner = tk.Frame(outer, bg=CARD)
        inner.pack(fill="x", padx=16, pady=(12, 14))
        head = tk.Frame(inner, bg=CARD)
        head.pack(fill="x", pady=(0, 10))
        tk.Label(head, text=title, font=(FONT, 9, "bold"), bg=CARD, fg=ACCENT).pack(side=tk.LEFT)
        if action:
            text, command = action
            inner.action_button = RoundedButton(head, text, command=command, style="ghost",
                                                font=(FONT, 9, "bold"), radius=8, padx=12, pady=4)
            inner.action_button.pack(side=tk.RIGHT)
        return inner

    def make_field(self, grid, label, row, col, colspan=1, padx=(0, 0)):
        """Ячейка сетки: маленькая подпись сверху, виджет кладётся внутрь."""
        cell = tk.Frame(grid, bg=CARD)
        cell.grid(row=row, column=col, columnspan=colspan, sticky="ew", padx=padx, pady=(0, 10))
        tk.Label(cell, text=label, font=(FONT, 8, "bold"), bg=CARD, fg=FG_DIM).pack(anchor="w")
        return cell

    def create_widgets(self):
        # --- шапка: градиент, логотип, название
        self.header = tk.Canvas(self.root, height=HEADER_H, bg=BG, highlightthickness=0, bd=0)
        self.header.pack(fill="x")
        self.header.bind("<Configure>", lambda e: self.draw_header())

        # --- подвал (создаём до основной колонки, чтобы его не вытеснило)
        footer = tk.Frame(self.root, bg=BG)
        footer.pack(side=tk.BOTTOM, fill="x", padx=16, pady=(0, 8))
        self.footer_path = tk.Label(footer, text=self.minecraft_dir, font=(FONT, 8), bg=BG, fg=FOOT)
        self.footer_path.pack(side=tk.LEFT)
        tk.Label(footer, text="F11 — полный экран", font=(FONT, 8), bg=BG, fg=FOOT).pack(side=tk.RIGHT)

        # --- основная колонка по центру окна
        column = tk.Frame(self.root, bg=BG)
        column.pack(expand=True, padx=20, pady=(14, 4))

        # ===== карточка «Аккаунт»
        acc = self.make_card(column, "АККАУНТ")

        self.login_mode = tk.StringVar(value=self.config.get("mode", "offline"))
        seg = tk.Frame(acc, bg=CARD)
        seg.pack(fill="x")
        seg.columnconfigure(0, weight=1, uniform="seg")
        seg.columnconfigure(1, weight=1, uniform="seg")
        self.mode_buttons = {}
        for i, (text, value) in enumerate((("Пиратка (оффлайн)", "offline"),
                                           ("Лицензия (Microsoft)", "microsoft"))):
            btn = RoundedButton(seg, text, command=lambda v=value: self.set_mode(v),
                                style="tab_off", font=(FONT, 10, "bold"), radius=9, pady=8)
            btn.grid(row=0, column=i, sticky="ew", padx=(0, 5) if i == 0 else (5, 0))
            self.mode_buttons[value] = btn

        self.login_container = tk.Frame(acc, bg=CARD)
        self.login_container.pack(fill="x", pady=(14, 0))

        # оффлайн: ник
        self.offline_frame = tk.Frame(self.login_container, bg=CARD)
        tk.Label(self.offline_frame, text="НИКНЕЙМ", font=(FONT, 8, "bold"), bg=CARD, fg=FG_DIM).pack(anchor="w")
        row = tk.Frame(self.offline_frame, bg=CARD)
        row.pack(fill="x", pady=(4, 0))
        self.nickname_entry = ttk.Combobox(row, font=(FONT, 12), values=tuple(self.saved_nicks()))
        self.nickname_entry.set(self.config.get("nickname", "NurstPlayer"))
        self.nickname_entry.pack(side=tk.LEFT, fill="x", expand=True)
        self.nickname_entry.bind("<<ComboboxSelected>>", self.on_nick_selected)
        RoundedButton(row, "+", command=self.save_nick, style="primary",
                      font=(FONT, 12, "bold"), radius=8, padx=14, pady=4).pack(side=tk.LEFT, padx=(8, 0))
        RoundedButton(row, "−", command=self.remove_nick, style="danger",
                      font=(FONT, 12, "bold"), radius=8, padx=14, pady=4).pack(side=tk.LEFT, padx=(6, 0))
        tk.Label(self.offline_frame, text="«+» сохраняет ник, список — выбрать сохранённый, «−» убирает из списка",
                 font=(FONT, 8), bg=CARD, fg=FG_DIM).pack(anchor="w", pady=(6, 0))

        # microsoft
        self.ms_frame = tk.Frame(self.login_container, bg=CARD)
        tk.Label(self.ms_frame, text="СОХРАНЁННЫЕ АККАУНТЫ", font=(FONT, 8, "bold"),
                 bg=CARD, fg=FG_DIM).pack(anchor="w")
        row = tk.Frame(self.ms_frame, bg=CARD)
        row.pack(fill="x", pady=(4, 10))
        names = self.ms_account_names()
        self.ms_account_combobox = ttk.Combobox(row, font=(FONT, 11), state="readonly", values=names)
        last = self.config.get("ms_last", "")
        self.ms_account_combobox.set(last if last in names else "")
        self.ms_account_combobox.pack(side=tk.LEFT, fill="x", expand=True)
        self.ms_account_combobox.bind("<<ComboboxSelected>>", self.on_ms_account_selected)
        RoundedButton(row, "+", command=self.save_ms_account, style="primary",
                      font=(FONT, 12, "bold"), radius=8, padx=14, pady=4).pack(side=tk.LEFT, padx=(8, 0))
        RoundedButton(row, "−", command=self.remove_ms_account, style="danger",
                      font=(FONT, 12, "bold"), radius=8, padx=14, pady=4).pack(side=tk.LEFT, padx=(6, 0))
        self.ms_login_button = RoundedButton(
            self.ms_frame, "Войти через Microsoft", command=self.login_microsoft_thread,
            style="primary", font=(FONT, 11, "bold"), radius=10, pady=9)
        self.ms_login_button.pack(fill="x")
        self.ms_status_label = tk.Label(
            self.ms_frame, text="Статус: не вошли в аккаунт", font=(FONT, 10), bg=CARD, fg=WARN)
        self.ms_status_label.pack(anchor="w", pady=(8, 0))

        # ===== карточка «Игра»: версия, загрузчик и сборки (выбор, удаление, создание)
        game = self.make_card(column, "ИГРА", action=("⚙  Настройки", self.open_settings))
        grid = tk.Frame(game, bg=CARD)
        grid.pack(fill="x")
        grid.columnconfigure(0, weight=1, uniform="game")
        grid.columnconfigure(1, weight=1, uniform="game")

        cell = self.make_field(grid, "ВЕРСИЯ", 0, 0, padx=(0, 6))
        self.version_combobox = ttk.Combobox(cell, font=(FONT, 11))
        self.version_combobox["values"] = FALLBACK_VERSIONS  # пока не загрузился полный список
        self.version_combobox.set(self.config.get("version", DEFAULT_VERSION))
        self.version_combobox.pack(fill="x", pady=(4, 0))
        self.version_combobox.bind("<<ComboboxSelected>>", self.on_profile_changed)
        self.version_combobox.bind("<Return>", self.on_profile_changed)
        self.version_combobox.bind("<FocusOut>", self.on_profile_changed)

        cell = self.make_field(grid, "ЗАГРУЗЧИК", 0, 1, padx=(6, 0))
        self.loader_combobox = ttk.Combobox(cell, font=(FONT, 11), state="readonly", values=LOADERS)
        saved_loader = self.config.get("loader", "Vanilla")
        self.loader_combobox.set(saved_loader if saved_loader in LOADERS else "Vanilla")
        self.loader_combobox.pack(fill="x", pady=(4, 0))
        self.loader_combobox.bind("<<ComboboxSelected>>", self.on_profile_changed)

        cell = self.make_field(grid, "СБОРКА", 1, 0, colspan=2)
        row = tk.Frame(cell, bg=CARD)
        row.pack(fill="x", pady=(4, 0))
        self.build_combobox = ttk.Combobox(row, font=(FONT, 11), state="readonly", values=(NO_BUILD,))
        self.build_combobox.set(NO_BUILD)
        self.build_combobox.pack(side=tk.LEFT, fill="x", expand=True)
        self.build_combobox.bind("<<ComboboxSelected>>", lambda e: self.on_build_selected())
        RoundedButton(row, "Удалить", command=self.delete_build, style="danger",
                      font=(FONT, 10), radius=8, padx=14, pady=6).pack(side=tk.LEFT, padx=(8, 0))

        cell = self.make_field(grid, "СОЗДАТЬ СБОРКУ (ВЕРСИЯ И ЗАГРУЗЧИК — ВЫШЕ)", 2, 0, colspan=2)
        row = tk.Frame(cell, bg=CARD)
        row.pack(fill="x", pady=(4, 0))
        self.new_build_entry = ttk.Entry(row, font=(FONT, 11))
        self.new_build_entry.pack(side=tk.LEFT, fill="x", expand=True)
        self.new_build_entry.bind("<Return>", lambda e: self.create_build())
        RoundedButton(row, "+ Создать", command=self.create_build, style="primary",
                      font=(FONT, 10, "bold"), radius=8, padx=14, pady=6).pack(side=tk.LEFT, padx=(8, 0))

        # ===== настройки: страница в этом же окне («⚙ Настройки» -> «← Назад»)
        self.main_column = column
        self.settings_page = tk.Frame(self.root, bg=BG)
        tk.Frame(self.settings_page, width=540, height=1, bg=BG).pack()   # та же ширина, что у главной
        st = self.make_card(self.settings_page, "НАСТРОЙКИ", action=("←  Назад", self.close_settings))
        tk.Label(st, text="ПУТЬ ИГРЫ", font=(FONT, 8, "bold"), bg=CARD, fg=FG_DIM).pack(anchor="w")
        row = tk.Frame(st, bg=CARD)
        row.pack(fill="x", pady=(4, 14))
        self.game_dir_var = tk.StringVar(value=self.minecraft_dir)
        self.game_dir_entry = ttk.Entry(row, font=(FONT, 10), textvariable=self.game_dir_var, state="readonly")
        self.game_dir_entry.pack(side=tk.LEFT, fill="x", expand=True)
        RoundedButton(row, "📁", command=self.choose_game_dir, style="primary",
                      font=(FONT, 12), radius=8, padx=12, pady=4).pack(side=tk.LEFT, padx=(8, 0))
        RoundedButton(row, "По умолчанию", command=self.reset_game_dir, style="ghost",
                      font=(FONT, 9), radius=8, padx=10, pady=7).pack(side=tk.LEFT, padx=(6, 0))
        head = tk.Frame(st, bg=CARD)
        head.pack(fill="x")
        tk.Label(head, text="ОЗУ ДЛЯ ИГРЫ", font=(FONT, 8, "bold"), bg=CARD, fg=FG_DIM).pack(side=tk.LEFT)
        self.ram_text = tk.Label(head, font=(FONT, 10, "bold"), bg=CARD, fg=ACCENT)
        self.ram_text.pack(side=tk.RIGHT)
        self.ram_var = tk.IntVar(value=int(self.config.get("ram", 2)))
        Slider(st, self.ram_var, from_=1, to=16).pack(fill="x", pady=(2, 8))
        self.ram_var.trace_add("write", self.on_ram_change)
        self.on_ram_change()

        self.show_all_var = tk.BooleanVar(value=bool(self.config.get("show_all", False)))
        row = tk.Frame(st, bg=CARD)
        row.pack(fill="x")
        Switch(row, self.show_all_var, command=self.refresh_versions).pack(side=tk.LEFT)
        lbl = tk.Label(row, text="Показывать снапшоты и старые версии", font=(FONT, 10),
                       bg=CARD, fg=FG_DIM, cursor="hand2")
        lbl.pack(side=tk.LEFT, padx=(10, 0))
        lbl.bind("<Button-1>", lambda e: (self.show_all_var.set(not self.show_all_var.get()),
                                          self.refresh_versions()))

        self.discord_var = tk.BooleanVar(value=bool(self.config.get("discord", True)))
        row = tk.Frame(st, bg=CARD)
        row.pack(fill="x", pady=(10, 0))
        Switch(row, self.discord_var, command=self.on_discord_toggle).pack(side=tk.LEFT)
        lbl = tk.Label(row, text="Статус в Discord (Rich Presence)", font=(FONT, 10),
                       bg=CARD, fg=FG_DIM, cursor="hand2")
        lbl.pack(side=tk.LEFT, padx=(10, 0))
        lbl.bind("<Button-1>", lambda e: (self.discord_var.set(not self.discord_var.get()),
                                          self.on_discord_toggle()))
        if Presence is None:
            note = "не установлен pypresence"
        elif not self.discord_app_id():
            note = "не задан DISCORD_APP_ID в коде"
        else:
            note = ""
        if note:
            tk.Label(row, text=f"({note})", font=(FONT, 8), bg=CARD, fg=WARN).pack(side=tk.LEFT, padx=(8, 0))

        self.light_var = tk.BooleanVar(value=(THEME == "light"))
        row = tk.Frame(st, bg=CARD)
        row.pack(fill="x", pady=(10, 0))
        Switch(row, self.light_var, command=self.on_theme_toggle).pack(side=tk.LEFT)
        lbl = tk.Label(row, text="Светлая тема (чёрное на белом)", font=(FONT, 10),
                       bg=CARD, fg=FG_DIM, cursor="hand2")
        lbl.pack(side=tk.LEFT, padx=(10, 0))
        lbl.bind("<Button-1>", lambda e: (self.light_var.set(not self.light_var.get()),
                                          self.on_theme_toggle()))

        self.settings_open = False

        # ===== запуск
        self.play_button = RoundedButton(
            column, "ИГРАТЬ", command=self.start_launch_thread, style="primary",
            font=(FONT, 17, "bold"), radius=14, pady=13)
        self.play_button.pack(fill="x", pady=(6, 8))

        links = tk.Frame(column, bg=BG)
        links.pack(fill="x")
        links.columnconfigure(0, weight=1, uniform="links")
        links.columnconfigure(1, weight=1, uniform="links")
        RoundedButton(links, "Открыть папку игры", command=self.open_game_folder, style="ghost",
                      font=(FONT, 10), radius=9, pady=7).grid(row=0, column=0, sticky="ew", padx=(0, 4))
        RoundedButton(links, "Открыть папку модов", command=self.open_mods_folder, style="ghost",
                      font=(FONT, 10), radius=9, pady=7).grid(row=0, column=1, sticky="ew", padx=(4, 0))

        # --- прогресс и статус
        self.progress = SlimProgress(column, width=540, height=8)
        self.progress.pack(fill="x", pady=(16, 6))

        self.status_label = tk.Label(
            column, text="Готов к запуску", font=(FONT, 10), bg=BG, fg=FG_DIM,
            wraplength=540, justify="center")
        self.status_label.pack(pady=(0, 4))

    def open_settings(self):
        """Настройки открываются в этом же окне: главный экран заменяется страницей настроек."""
        self.main_column.pack_forget()
        self.settings_page.pack(expand=True, padx=20, pady=(14, 4))
        self.settings_open = True

    def close_settings(self):
        """Назад на главный экран (настройки при этом сохраняются)."""
        self.settings_page.pack_forget()
        self.main_column.pack(expand=True, padx=20, pady=(14, 4))
        self.settings_open = False
        self.save_config()

    def choose_game_dir(self):
        """Открывает окно выбора папки, куда будет скачиваться и где будет лежать Minecraft."""
        folder = filedialog.askdirectory(parent=self.root, title="Папка для Minecraft",
                                         initialdir=self.minecraft_dir, mustexist=False)
        if folder:
            self.set_game_dir(folder)

    def reset_game_dir(self):
        self.set_game_dir(GAME_DIR)

    def set_game_dir(self, path):
        """Переносит лаунчер на другую папку игры: версии, Java, сборки и миры берутся оттуда.
        Старые файлы не копируются и не удаляются, в новой папке всё скачается заново."""
        path = os.path.normpath(os.path.expanduser(str(path).strip()))
        if self.running:
            messagebox.showinfo("Папка игры", "Сначала дождитесь конца загрузки или закройте игру.")
            return
        try:
            os.makedirs(path, exist_ok=True)
            probe = os.path.join(path, ".nurst_write_test")
            with open(probe, "w", encoding="utf-8") as f:
                f.write("ok")
            os.remove(probe)
        except OSError as e:
            messagebox.showerror("Папка игры", f"В эту папку нельзя писать:\n{path}\n\n{e}")
            self.game_dir_var.set(self.minecraft_dir)
            return
        if path == self.minecraft_dir:
            return
        self.minecraft_dir = path
        if path == os.path.normpath(GAME_DIR):
            self.config.pop("game_dir", None)
        else:
            self.config["game_dir"] = path
        self.game_dir_var.set(path)
        self.footer_path.config(text=path)
        self.refresh_builds(self.config.get("build"))
        self.apply_build()
        self.update_status("Папка игры изменена. Версии и Java скачаются в неё заново", OK)
        self.save_config()

    def on_theme_toggle(self):
        # пересобираем интерфейс чуть позже, не изнутри нажатого виджета
        self.root.after(30, self.rebuild_ui)

    def rebuild_ui(self):
        """Применяет выбранную тему: сохраняет введённое, пересоздаёт все виджеты и возвращает экран."""
        reopen = self.settings_open
        self.save_config()
        set_theme(self.config.get("theme", "dark"))
        for child in self.root.winfo_children():
            child.destroy()
        self.root.configure(bg=BG)
        self.setup_style()
        self.create_widgets()
        self.toggle_mode()
        self.refresh_builds(self.config.get("build"))
        self.apply_build()
        self.refresh_versions()
        self.fit_window(resize=False)
        if self.auth_data:
            self.ms_status_label.config(text=f"✅ Вошли как {self.auth_data.get('name', 'Игрок')}", fg=OK)
        if reopen:
            self.open_settings()
        self.root.after(50, self.apply_titlebar)

    def on_ram_change(self, *args):
        try:
            self.ram_text.config(text=f"{int(self.ram_var.get())} ГБ")
        except Exception:
            pass

    def on_profile_changed(self, event=None):
        """Версию или загрузчик изменили: сразу запоминаем в выбранной сборке."""
        try:
            self.save_build_meta()
        except Exception as e:
            print(f"[WARN] Не удалось сохранить сборку: {e}")

    def draw_header(self):
        """Шапка: тёплый градиент, круглый логотип со свечением, название, акцентная линия."""
        cv = self.header
        w = cv.winfo_width()
        if w < 4:
            w = cv.winfo_reqwidth()
        h = HEADER_H
        cv.delete("all")

        top = HEADER_TOP
        for y in range(0, h, 2):
            cv.create_line(0, y, w, y, fill=lerp_color(top, BG, (y / h) ** 0.8), width=2)

        title_font = tkfont.Font(font=(FONT, 27, "bold"))
        part1, part2 = "NURST ", "LAUNCHER"
        text_w = title_font.measure(part1) + title_font.measure(part2)
        logo_w, gap = 76, 18
        x0 = (w - (logo_w + gap + text_w)) / 2
        cx, cy = x0 + logo_w / 2, (h - 3) / 2

        # свечение за логотипом
        for r, t in ((51, 0.04), (46, 0.07), (42, 0.11)):
            cv.create_oval(cx - r, cy - r, cx + r, cy + r,
                           fill=lerp_color(lerp_color(top, BG, 0.5), ACCENT, t), outline="")
        if self.logo_img:
            cv.create_oval(cx - 39, cy - 39, cx + 39, cy + 39, outline=ACCENT, width=2)
            cv.create_image(cx, cy, image=self.logo_img)
        else:
            round_rect(cv, cx - 34, cy - 34, cx + 34, cy + 34, 16, fill=ACCENT, outline="")
            cv.create_text(cx, cy, text="N", fill="#ffffff", font=(FONT, 30, "bold"))

        tx = x0 + logo_w + gap
        cv.create_text(tx, cy - 9, text=part1, anchor="w", fill=ACCENT, font=title_font)
        cv.create_text(tx + title_font.measure(part1), cy - 9, text=part2, anchor="w",
                       fill=FG, font=title_font)
        cv.create_text(tx + 2, cy + 22, text="Minecraft  ·  Fabric  ·  Forge  ·  Quilt",
                       anchor="w", fill=FG_DIM, font=(FONT, 10))

        # акцентная линия внизу: ярче всего по центру
        step = 6
        for x in range(0, w, step):
            t = max(0.0, 1 - abs((x + step / 2) / w - 0.5) * 2) ** 1.4
            cv.create_line(x, h - 2, x + step + 1, h - 2,
                           fill=lerp_color(BG, ACCENT, t), width=2)

    def fit_window(self, resize=True):
        """Подбирает размер окна под содержимое (учитывая оба режима входа)
        и запрещает делать окно меньше, чтобы ничего не обрезалось."""
        current = self.login_mode.get()
        req_w = req_h = 0
        for mode in ("microsoft", "offline"):
            self.login_mode.set(mode)
            self.toggle_mode()
            self.root.update_idletasks()
            req_w = max(req_w, self.root.winfo_reqwidth())
            req_h = max(req_h, self.root.winfo_reqheight())
        self.login_mode.set(current)
        self.toggle_mode()
        self.root.minsize(req_w, req_h)
        if resize:
            self.root.geometry(f"{max(req_w, 680)}x{req_h + 20}")

    def set_mode(self, value):
        self.login_mode.set(value)
        self.toggle_mode()


    # ------------------------------------------------------------------ helpers
    def toggle_fullscreen(self, event=None):
        self.fullscreen = not self.fullscreen
        self.root.attributes("-fullscreen", self.fullscreen)

    def exit_fullscreen(self, event=None):
        if self.fullscreen:
            self.fullscreen = False
            self.root.attributes("-fullscreen", False)

    def on_escape(self, event=None):
        if self.settings_open:
            self.close_settings()
        else:
            self.exit_fullscreen()

    def ui(self, func, *args, **kwargs):
        """Безопасно выполнить действие в потоке интерфейса."""
        self.root.after(0, lambda: func(*args, **kwargs))

    # ------------------------------------------------------------------ builds
    def read_build_meta(self, path: str):
        try:
            with open(os.path.join(path, "build.json"), "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    def list_builds(self) -> dict:
        """{название сборки: путь к её папке}"""
        result = {}
        if not os.path.isdir(self.minecraft_dir):
            return result
        for folder in sorted(os.listdir(self.minecraft_dir)):
            path = os.path.join(self.minecraft_dir, folder)
            meta = self.read_build_meta(path) if os.path.isdir(path) else None
            if meta:
                result[meta.get("name", folder)] = path
        return result

    def current_build_path(self):
        name = self.build_combobox.get()
        if name == NO_BUILD:
            return None
        return self.list_builds().get(name)

    def current_game_dir(self) -> str:
        """Папка, в которой игра хранит моды/сохранения: папка сборки или общая."""
        return self.current_build_path() or self.minecraft_dir

    def refresh_builds(self, select=None):
        names = [NO_BUILD] + list(self.list_builds().keys())
        self.build_combobox["values"] = names
        self.build_combobox.set(select if select in names else NO_BUILD)

    def apply_build(self):
        """Подставляет версию и загрузчик выбранной сборки."""
        path = self.current_build_path()
        meta = self.read_build_meta(path) if path else None
        if not meta:
            return
        if meta.get("version"):
            self.version_combobox.set(meta["version"])
        if meta.get("loader") in LOADERS:
            self.loader_combobox.set(meta["loader"])

    def save_build_meta(self):
        """Запоминает в сборке выбранные сейчас версию и загрузчик."""
        path = self.current_build_path()
        if not path:
            return
        meta = self.read_build_meta(path) or {}
        meta.setdefault("name", self.build_combobox.get())
        meta["version"] = self.version_combobox.get().strip()
        meta["loader"] = self.loader_combobox.get()
        with open(os.path.join(path, "build.json"), "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

    def on_build_selected(self):
        self.apply_build()
        name = self.build_combobox.get()
        if name == NO_BUILD:
            self.update_status("Сборка не выбрана: используется общая папка", FG_DIM)
        else:
            self.update_status(f"Сборка «{name}»: {self.current_game_dir()}", FG_DIM)

    def create_build(self):
        """Создаёт сборку: название из поля + версия и загрузчик, выбранные выше."""
        name = self.new_build_entry.get().strip()
        version = self.version_combobox.get().strip()
        loader = self.loader_combobox.get()
        if not name:
            messagebox.showerror("Сборка", "Введите название сборки!")
            return
        if not version:
            messagebox.showerror("Сборка", "Выберите версию!")
            return
        slug = slugify(name)
        if not slug:
            messagebox.showerror("Сборка", "В названии нужны буквы или цифры.")
            return
        if slug in RESERVED_NAMES:
            messagebox.showerror("Сборка", "Это имя занято служебной папкой игры, выберите другое.")
            return
        if name in self.list_builds() or os.path.exists(os.path.join(self.minecraft_dir, slug)):
            messagebox.showerror("Сборка", "Сборка с таким названием уже есть.")
            return
        folder = os.path.join(self.minecraft_dir, slug)
        try:
            os.makedirs(os.path.join(folder, "mods"), exist_ok=True)
            with open(os.path.join(folder, "build.json"), "w", encoding="utf-8") as f:
                json.dump({"name": name, "version": version, "loader": loader},
                          f, ensure_ascii=False, indent=2)
        except Exception as e:
            messagebox.showerror("Сборка", str(e))
            return
        self.refresh_builds(name)
        self.apply_build()
        self.new_build_entry.delete(0, "end")
        self.update_status(f"✅ Сборка «{name}» создана: {folder}", OK)

    def delete_build(self):
        path = self.current_build_path()
        if not path:
            messagebox.showinfo("Сборки", "Сначала выберите сборку в списке.")
            return
        name = self.build_combobox.get()
        if not messagebox.askyesno(
            "Удалить сборку",
            f"Удалить сборку «{name}» вместе с её модами, сохранениями и настройками?\n"
            "Это действие нельзя отменить.",
        ):
            return
        try:
            shutil.rmtree(path)
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))
            return
        self.refresh_builds()
        self.apply_build()
        self.update_status(f"Сборка «{name}» удалена", FG_DIM)

    # ---------------------------------------------------------------- versions
    def load_versions_thread(self):
        threading.Thread(target=self.load_versions, daemon=True).start()

    def load_versions(self):
        """Скачивает полный список версий Mojang (нужен интернет)."""
        try:
            self.all_versions = mll.utils.get_version_list()
        except Exception as e:
            print(f"[WARN] Не удалось получить список версий: {e}")
            self.all_versions = []
        self.ui(self.refresh_versions)

    def refresh_versions(self):
        show_all = self.show_all_var.get()
        ids = []
        # сначала уже установленные версии (в т.ч. Fabric/Forge)
        try:
            for v in mll.utils.get_installed_versions(self.minecraft_dir):
                if v["id"] not in ids:
                    ids.append(v["id"])
        except Exception:
            pass
        for v in self.all_versions:
            if (show_all or v.get("type") == "release") and v["id"] not in ids:
                ids.append(v["id"])
        if not ids:
            ids = list(FALLBACK_VERSIONS)
        current = self.version_combobox.get().strip()
        self.version_combobox["values"] = ids
        if current:
            self.version_combobox.set(current)

    def toggle_mode(self):
        mode = self.login_mode.get()
        self.offline_frame.pack_forget()
        self.ms_frame.pack_forget()
        (self.offline_frame if mode == "offline" else self.ms_frame).pack(fill="x")
        for value, btn in self.mode_buttons.items():
            btn.set_style("primary" if value == mode else "tab_off")

    def update_status(self, text, color=None):
        self.status_label.config(text=text, fg=color or WARN)

    def open_game_folder(self):
        self.open_folder(self.current_game_dir())

    def open_mods_folder(self):
        mods_dir = os.path.join(self.current_game_dir(), "mods")
        os.makedirs(mods_dir, exist_ok=True)
        self.open_folder(mods_dir)

    def open_folder(self, path):
        try:
            if sys.platform.startswith("win"):
                os.startfile(path)  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))

    # ------------------------------------------------------- saved nicks / accounts
    @staticmethod
    def nick_error(name: str):
        if not name:
            return "Введите никнейм!"
        if not (3 <= len(name) <= 16) or not all(c.isalnum() or c == "_" for c in name):
            return "Ник: 3–16 символов, только латиница, цифры и _"
        return None

    def saved_nicks(self) -> list:
        nicks = self.config.get("nicks", [])
        return [n for n in nicks if isinstance(n, str)] if isinstance(nicks, list) else []

    def save_nick(self):
        """«+»: добавляет ник из поля в сохранённые."""
        name = self.nickname_entry.get().strip()
        error = self.nick_error(name)
        if error:
            self.update_status(error, ERR)
            return
        nicks = self.saved_nicks()
        if name in nicks:
            self.update_status(f"Ник «{name}» уже сохранён", FG_DIM)
            return
        nicks.append(name)
        self.config["nicks"] = nicks[-30:]
        self.nickname_entry["values"] = tuple(self.config["nicks"])
        self.update_status(f"✅ Ник «{name}» сохранён", OK)
        self.save_config()

    def remove_nick(self):
        """«−»: убирает ник из сохранённых (поле ввода не трогает)."""
        name = self.nickname_entry.get().strip()
        nicks = self.saved_nicks()
        if name not in nicks:
            self.update_status(f"Ника «{name}» нет в сохранённых", FG_DIM)
            return
        nicks.remove(name)
        self.config["nicks"] = nicks
        self.nickname_entry["values"] = tuple(nicks)
        self.update_status(f"Ник «{name}» убран из сохранённых", FG_DIM)
        self.save_config()

    def on_nick_selected(self, event=None):
        """Выбрали ник из списка: он сразу становится текущим."""
        name = self.nickname_entry.get().strip()
        if name:
            self.update_status(f"Выбран ник «{name}»", FG_DIM)
            self.save_config()

    def ms_accounts(self) -> list:
        accounts = self.config.get("ms_accounts", [])
        if not isinstance(accounts, list):
            return []
        return [a for a in accounts if isinstance(a, dict) and a.get("name") and a.get("refresh_token")]

    def ms_account_names(self) -> tuple:
        return tuple(a["name"] for a in self.ms_accounts())

    def save_ms_account(self):
        """«+»: сохраняет аккаунт Microsoft, в который сейчас вошли."""
        data = self.auth_data
        if not data or not data.get("refresh_token"):
            self.ms_status_label.config(text="Сначала войдите через Microsoft, потом нажмите «+»", fg=WARN)
            return
        accounts = [a for a in self.ms_accounts() if a.get("id") != data.get("id")]
        accounts.append({"name": data["name"], "id": data["id"], "refresh_token": data["refresh_token"]})
        self.config["ms_accounts"] = accounts[-10:]
        self.config["ms_last"] = data["name"]
        self.ms_account_combobox["values"] = self.ms_account_names()
        self.ms_account_combobox.set(data["name"])
        self.ms_status_label.config(text=f"✅ Вошли как {data['name']} · аккаунт сохранён", fg=OK)
        self.save_config()

    def remove_ms_account(self):
        """«−»: убирает выбранный аккаунт из сохранённых (текущий вход не сбрасывается)."""
        name = self.ms_account_combobox.get()
        accounts = [a for a in self.ms_accounts() if a.get("name") != name]
        if len(accounts) == len(self.ms_accounts()):
            self.ms_status_label.config(text="Выберите сохранённый аккаунт в списке", fg=WARN)
            return
        self.config["ms_accounts"] = accounts
        if self.config.get("ms_last") == name:
            self.config.pop("ms_last", None)
        self.ms_account_combobox["values"] = self.ms_account_names()
        self.ms_account_combobox.set("")
        self.ms_status_label.config(text=f"Аккаунт {name} убран из сохранённых", fg=FG_DIM)
        self.save_config()

    def update_saved_token(self, data):
        """Если этот аккаунт уже сохранён, обновляем его refresh_token."""
        token = (data or {}).get("refresh_token")
        if not token:
            return
        changed = False
        for acc in self.config.get("ms_accounts", []):
            if isinstance(acc, dict) and acc.get("id") == data.get("id"):
                acc["refresh_token"] = token
                changed = True
        if changed:
            self.save_config()

    def on_ms_account_selected(self, event=None):
        """Выбрали сохранённый аккаунт: входим в него сами, без браузера."""
        name = self.ms_account_combobox.get()
        acc = next((a for a in self.ms_accounts() if a["name"] == name), None)
        if not acc:
            return
        self.config["ms_last"] = name
        threading.Thread(target=self.ms_silent_login, args=(acc,), daemon=True).start()

    def autologin_ms(self):
        """При запуске в режиме «Лицензия» входим в последний выбранный аккаунт."""
        if self.login_mode.get() != "microsoft" or self.auth_data:
            return
        name = self.config.get("ms_last")
        acc = next((a for a in self.ms_accounts() if a["name"] == name), None)
        if acc:
            threading.Thread(target=self.ms_silent_login, args=(acc,), daemon=True).start()

    def ms_silent_login(self, acc):
        try:
            self.ui(self.ms_status_label.config, text=f"🔄 Вхожу как {acc['name']}...", fg=WARN)
            data = mll.microsoft_account.complete_refresh(
                MS_CLIENT_ID, None, MS_REDIRECT_URI, acc["refresh_token"])
            self.auth_data = data
            self.ui(self.update_saved_token, data)
            self.ui(self.ms_status_label.config, text=f"✅ Вошли как {data.get('name', acc['name'])}", fg=OK)
        except Exception as e:
            print(f"[WARN] Не удалось войти в сохранённый аккаунт: {e}")
            self.auth_data = None
            self.ui(self.ms_status_label.config,
                    text="❌ Сессия аккаунта истекла — нажмите «Войти через Microsoft»", fg=ERR)

    # --------------------------------------------------------------- microsoft
    def login_microsoft_thread(self):
        threading.Thread(target=self.login_microsoft, daemon=True).start()

    def login_microsoft(self):
        try:
            self.ui(self.ms_status_label.config, text="🔄 Открываю браузер...", fg=WARN)
            login_url, state, code_verifier = mll.microsoft_account.get_secure_login_data(
                MS_CLIENT_ID, MS_REDIRECT_URI
            )
            webbrowser.open(login_url)

            result = {}
            done = threading.Event()

            def ask():
                result["url"] = simpledialog.askstring(
                    "Авторизация Microsoft",
                    "1. Войдите в аккаунт в браузере.\n"
                    "2. Скопируйте ПОЛНУЮ ссылку из адресной строки после входа и вставьте сюда:",
                    parent=self.root,
                )
                done.set()

            self.ui(ask)
            done.wait()

            redirect_url = result.get("url")
            if not redirect_url:
                self.ui(self.ms_status_label.config, text="❌ Отменено", fg=ERR)
                return

            self.ui(self.ms_status_label.config, text="🔄 Получаю профиль...", fg=WARN)
            auth_code = mll.microsoft_account.parse_auth_code_url(redirect_url, state)
            self.auth_data = mll.microsoft_account.complete_login(
                MS_CLIENT_ID, None, MS_REDIRECT_URI, auth_code, code_verifier
            )
            name = self.auth_data.get("name", "Игрок")
            self.ui(self.ms_status_label.config, text=f"✅ Вошли как {name}", fg=OK)
            self.ui(self.update_saved_token, self.auth_data)

        except Exception as e:
            traceback.print_exc()
            self.ui(self.ms_status_label.config, text="❌ Ошибка входа", fg=ERR)
            self.ui(messagebox.showerror, "Ошибка Microsoft Auth", str(e))

    # ------------------------------------------------------------------ launch
    def start_launch_thread(self):
        if self.running:
            return
        threading.Thread(target=self.launch_minecraft, daemon=True).start()

    def auto_fix_folders(self, version: str):
        """Если папка версии лежит в корне — переносим её в /versions/."""
        versions_dir = os.path.join(self.minecraft_dir, "versions")
        os.makedirs(versions_dir, exist_ok=True)

        misplaced = os.path.join(self.minecraft_dir, version)
        correct = os.path.join(versions_dir, version)
        if os.path.isdir(misplaced) and not os.path.exists(correct):
            try:
                shutil.move(misplaced, correct)
                print(f"[INFO] Папка {version} перенесена в /versions/")
            except Exception as e:
                print(f"[ERROR] Не удалось перенести папку: {e}")

    def build_options(self):
        ram = max(1, int(self.ram_var.get()))
        jvm = [f"-Xmx{ram}G", f"-Xms{min(ram, 1)}G"]

        if self.login_mode.get() == "offline":
            username = self.nickname_entry.get().strip()
            error = self.nick_error(username)
            if error:
                raise ValueError(error)
            # Отключаем проверку сессии Mojang, иначе в 1.16.5 с фейковым токеном
            # кнопка Multiplayer блокируется ("Multiplayer is disabled")
            jvm += [
                "-Dminecraft.api.env=custom",
                "-Dminecraft.api.auth.host=https://invalid.invalid",
                "-Dminecraft.api.account.host=https://invalid.invalid",
                "-Dminecraft.api.session.host=https://invalid.invalid",
                "-Dminecraft.api.services.host=https://invalid.invalid",
            ]
            return {
                "username": username,
                "uuid": offline_uuid(username),
                "token": "0",
                "userType": "legacy",
                "jvmArguments": jvm,
                "launcherName": "NurstLauncher",
                "launcherVersion": "1.0",
            }

        if not self.auth_data:
            raise ValueError("Сначала войдите через Microsoft!")
        return {
            "username": self.auth_data["name"],
            "uuid": self.auth_data["id"],
            "token": self.auth_data["access_token"],
            "userType": "msa",
            "jvmArguments": jvm,
            "launcherName": "NurstLauncher",
            "launcherVersion": "1.0",
        }

    def launch_minecraft(self):
        version = self.version_combobox.get().strip()
        loader = self.loader_combobox.get()
        game_dir = self.current_game_dir()
        if not version:
            self.ui(messagebox.showerror, "Ошибка", "Выберите версию!")
            return

        try:
            options = self.build_options()
        except ValueError as e:
            self.ui(messagebox.showerror, "Ошибка", str(e))
            return

        self.running = True
        self.ui(self.play_button.config, state="disabled")
        self.ui(self.save_config)
        self.ui(self.progress.config, value=0)

        callback = {
            "setStatus": lambda s: self.ui(self.update_status, f"📥 {s}"),
            "setMax": self.set_max,
            "setProgress": self.set_progress,
        }

        try:
            self.auto_fix_folders(version)

            # 1. Ставим саму версию (клиент, библиотеки, ресурсы) в .nurstclient
            self.ui(self.update_status, f"🔄 Проверка файлов версии {version}...")
            mll.install.install_minecraft_version(version, self.minecraft_dir, callback=callback)

            # 2. Ставим нужную Java от Mojang (для 1.16.5 это Java 8),
            #    чтобы не зависеть от Java, установленной в системе
            java_path = self.ensure_java(version, callback)
            if java_path:
                options["executablePath"] = java_path

            # 3. Ставим загрузчик модов (Fabric / Quilt / Forge), если выбран
            launch_id = self.install_loader(loader, version, java_path, callback)

            # 4. Собираем команду и запускаем. gameDirectory = .nurstclient,
            #    значит сохранения, моды, ресурспаки и версии лежат там же.
            os.makedirs(game_dir, exist_ok=True)
            options["gameDirectory"] = game_dir
            self.ui(self.update_status, "🚀 Запуск Minecraft...", OK)
            command = mll.command.get_minecraft_command(launch_id, self.minecraft_dir, options)

            kwargs = {"cwd": game_dir}
            if sys.platform.startswith("win"):
                kwargs["creationflags"] = 0x08000000  # CREATE_NO_WINDOW
            proc = subprocess.Popen(command, **kwargs)
            self.ui(self.rpc_playing, version, loader, options["username"])
            threading.Thread(target=self.watch_game, args=(proc,), daemon=True).start()

            self.ui(self.update_status, "✅ Игра запущена!", OK)
            self.ui(self.progress.config, value=self.progress["maximum"])

        except Exception as e:
            traceback.print_exc()
            self.ui(self.update_status, f"❌ Ошибка: {e}", ERR)
        finally:
            self.running = False
            self.ui(self.play_button.config, state="normal")

    def install_loader(self, loader: str, version: str, java_path, callback: dict) -> str:
        """Ставит загрузчик модов и возвращает id версии, которую нужно запускать."""
        if loader == "Vanilla":
            return version

        try:
            installed = {v["id"] for v in mll.utils.get_installed_versions(self.minecraft_dir)}
        except Exception:
            installed = set()

        if loader in ("Fabric", "Quilt"):
            lib = mll.fabric if loader == "Fabric" else mll.quilt
            prefix = "fabric-loader" if loader == "Fabric" else "quilt-loader"
            if not lib.is_minecraft_version_supported(version):
                raise RuntimeError(f"{loader} не поддерживает Minecraft {version}")
            loader_version = lib.get_latest_loader_version()
            launch_id = f"{prefix}-{loader_version}-{version}"
            if launch_id not in installed:
                self.ui(self.update_status, f"🧩 Установка {loader} {loader_version}...")
                if loader == "Fabric":
                    mll.fabric.install_fabric(
                        version, self.minecraft_dir, loader_version=loader_version,
                        callback=callback, java=java_path)
                else:
                    mll.quilt.install_quilt(
                        version, self.minecraft_dir, loader_version=loader_version,
                        callback=callback, java=java_path)
            return launch_id

        if loader == "Forge":
            forge_version = mll.forge.find_forge_version(version)
            if not forge_version:
                raise RuntimeError(f"Для Minecraft {version} нет Forge")
            launch_id = mll.forge.forge_to_installed_version(forge_version)
            if launch_id not in installed:
                self.ui(self.update_status, f"🧩 Установка Forge {forge_version}...")
                if mll.forge.supports_automatic_install(forge_version):
                    mll.forge.install_forge_version(
                        forge_version, self.minecraft_dir, callback=callback, java=java_path)
                else:
                    mll.forge.run_forge_installer(forge_version, java=java_path)
            return launch_id

        return version

    def ensure_java(self, version: str, callback: dict):
        """Возвращает путь к java из рантайма Mojang, либо None (тогда берётся системная)."""
        try:
            info = mll.runtime.get_version_runtime_information(version, self.minecraft_dir)
            if not info:
                return None
            name = info["name"]
            self.ui(self.update_status, f"☕ Проверка Java ({name})...")
            mll.runtime.install_jvm_runtime(name, self.minecraft_dir, callback=callback)
            path = mll.runtime.get_executable_path(name, self.minecraft_dir)
            if path and os.path.exists(path):
                return path
        except Exception as e:
            print(f"[WARN] Не удалось подготовить Java от Mojang, используем системную: {e}")
        return None

    def set_max(self, value):
        self.max_progress = value or 0
        self.ui(self.progress.config, maximum=max(self.max_progress, 1), value=0)

    def set_progress(self, value):
        self.ui(self.progress.config, value=value)


if __name__ == "__main__":
    root = tk.Tk()
    app = NurstLauncherApp(root)
    root.mainloop()
