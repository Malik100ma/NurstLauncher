import asyncio
import base64
import hashlib
import io
import json
import os
import queue
import re
import shutil
import subprocess
import sys
import threading
import time
import traceback
import urllib.request
import uuid
import webbrowser
import zipfile
import posixpath
import tkinter as tk
from pathlib import Path
from tkinter import font as tkfont
from tkinter import ttk, messagebox, simpledialog, filedialog, colorchooser

import minecraft_launcher_lib as mll

try:  # Discord Rich Presence (необязательно): pip install pypresence
    from pypresence import Presence
except Exception:
    Presence = None

try:  # значок в трее (необязательно): pip install pystray
    import pystray
except Exception:
    pystray = None

try:  # Pillow необязателен, но с ним иконка обрезается/масштабируется сама
    from PIL import Image, ImageDraw, ImageTk
    PIL_OK = True
except Exception:
    PIL_OK = False

APP_NAME = "Nurst Launcher"

# Встроенная иконка лаунчера (PNG 128x128). Используется, если рядом нет своей icon.png / icon.ico:
# так значок окна, панели задач и трея всегда есть, даже в одиночном exe.
ICON_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAIAAAACACAYAAADDPmHLAABPN0lEQVR42p29d6AkV3nm/XtPVXW8fe+dKGmkURbKSAiBQAaE"
    "lowBCYQFxgiWxWDWOO/axuGzWfiMMWsblmWxMcY2YEBgEFgswURjNApGCZQTiqORJt7QscJ5vz+quvtU6L7jb0Cjq3v7dlfV"
    "OeeNz/O8Uq/XFUBEUBQUEMZ/gWr6pVLxR9L/q1b/ePInfVMRIf2I7NUi04+yikrundHxB09eLtm7TX6Se50gqKavEOcedPy3"
    "ji9ZCleWvULF+V3nUWh6rc53cl/nvqv5z55+jjq/mV6Bqk7vP3uT9PJlcg3uD9LLU9z1EneJcpcozmvz9zK+HVUw04fqXvT4"
    "lzVbNJm5tOJ8yOT2JPuGMH0YMn4MOllI96Glm2H6+enHp1crMl389KeS/V14yNmTSF8ruc0k2QaUwrZ0v5hcN5L7fvn2FfdU"
    "uD9OF0ZKB2J8zeOvNP+hk3+n1znzrKXPSSTdPOr8wLlugfzia+HKx89fwIx37PiX0o1uyx8u7o1o9pnpbWjuQyQ9SZqdSPdE"
    "6/iCNL9okxM6ORv5DTL+J/favLVwVrrSGmnuXTU7NZpdeP7h6fjnkrdHVe+Ze//xQ8+d9tl/JlbXtVIzf6u42dJFGX+mOtZa"
    "3R2rxeefHi7NNo/UG3UtGjVVxzyPLVC2OdTZuJM3cRZ1sjtl+mynlknyxjBnLnXicdLPrnBHzslJX6HOpnR+7m4O15PJ9PPH"
    "vy1I/vdyGz1v3osnv8rMVzmYautRtFxS8Y6UXpdumulGnW7g/C9LYdPm7l+n62RExztGJj5UZOoCxt5g/MFTE1Q2vVMXIJMT"
    "NPVRkvN/OV+rzuI7F6wyPrn5czK1LFM3kO5qLR0ezW2E6Qkb33P6dd5Gjv3z+BlMfy45U6PO/efjANd/FC/JNZfTQzN9xypL"
    "47jjshmZxkfTJZveo8rkUE0OjHMbRp0gwQ0Y3OhEJP8Axr+Tup18kKjIZKdOzKrIZCHFWc7JBec+XyY3K649Lzzk8UcXzeb0"
    "YeZ/X3FuzImIphs+byrJQh9RcQLA0lI6cVJ6kPJ2Qyb37Fov56i4T6PS3YwDxZxZH8dS7v3lTpwbuxdjLjeQFszYj0jJsUlF"
    "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"
    "lUHEMFSiLLXyTEr7atU8lhs+29vKOdsCVmnztzc8SQI8ZbnGdW9fpmPWQOBTtzV481UHaDVMujgps4v+KOb8zQ2+/hzDsq4z"
    "UrfXP7+5GVvoePCIXeSyXQk3rQxp+GMVrxRD2AuV/31ujV95yoj/elONv75vOOltjJ9iaJXjWz67LhI2S49I04yh7Qtf2rvA"
    "664fUa+NszXPyQKkolNYoRZWcB9+bn87wtCpT9WysoW6XJDZwUaYKAHQaft85a5VnvhkyD9c2uHUpR7rA8X4IOKlDzgjY/ZG"
    "oMMQI0N21ODY4w0vOTGtqieJRz/x6EU1RrEh1BQ14xuo+dD0oe5BkyF+vcZLP7vOMAxBPX79WS06fpe1HizU4dnH+mxfCDgU"
    "JngieEA/jDm2FfAPF3hs0jX6FnzR+Qis7D/iRFkM4KF4icuujbl5JaRmPJo1n94oQkzWJhflykcTLjpmM1969CCeb7Ku5vT4"
    "1H3hgfWYrz/R4C07heEo1TMcRMpFm2NOW/S5uxvR8L3Mbbi+yBSq/LYam+l8b+oCdBrRS8aPryYjOm/lyJ4WoeMnb+lwqDei"
    "H1s6TcNP94/48t0xJ29b5KlHCzZOSHQ6REKY6taJGBIVRgmMIksUJSQ2xiek5cUs1UI21SM210OWg4gFL6JGSBKHNGuGj9/q"
    "86FdB0Hg/GPa/M8XCHY0xPM8rLVsbvl850Hl/oMhjZrP0Fq2eB5XXtjg/GZW4pWNCHjpD2ObRvt3hUtctivmx+sRJJYXP+VI"
    "RgnsWx/gGzPhYqxGyo/XfO5ZHRFMyqN5oH1koRcLP3e0oEmSWhiFzXXloUGdXfsSan5eal7mlvJ1Rg2BsYWTmQWTqkpSDoOi"
    "WoJXhbGyVDf86UuPZ0fLsN6LaDY89g4TXvuFQ/zxD2pofYmFRsqeUTevcyZ+eBlT13gGIwaLIVIhTIRhDKMYRrESJkpkTVqS"
    "jhb50HVd/Lqh7vm8+/ltOv6QGA+1aZwQMOSZOwJIUrWStgh/+8wmz1teYy1WArPR4qfXGCewWDdct77Mz/5byB29ECLLm847"
    "ggt2NrnvyVUatWDyVp4IPat8//FV/CyaV/IaAlah5sF1B2JuXavR8NLvGQOqCS85MiWqJpV4Jy1gI4ro4rJbMOR0eF3ygMyp"
    "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"
    "H8OuFfm/zlYmcXJnnbdBKM5D0spspLoMrWilQINWLLTO4WfqnDqJzqDszSK85KuUpqwvL2ilf57VVLAzAp7DAZg6VkSppC7J"
    "Ri4m15qWwqkyc2y+uKxvipq95U0uc4SXmWkFZWYfoBxwl0knssGGNtXAkaKs/8xmnlTVUrUQ+8ocE+pexKwKmRZeOy/FmsWl"
    "k40dt86KmnXuJpBSEbEwQW3W7ysbADUOJ/2zzu84CuwzR78Wq4r5Z65aoRkgs2IyU9QJPJwSrM40dbMrgG5UzIzKHmXqdOXO"
    "1jmbRzdouc5zI26dQ8ucgZkbKp8pVZZU5gR0VDapdIOajMw8lFM3VbDg+bw3x2YyG3WOqnlw80wUs2vPOq8qNu89NgrfdQOw"
    "pMzxn4eTkunGjSWp4u9v1AaX/yALqSpA1g1qHwV3JTh0/VIp2GxQjJENBBdmBVEyZ2NtVK2Tw3ABRRrVf1QLQOc0WZjTCNMN"
    "MIwwG20lGwR3h7NZivdlZjwzmRkDmcMrvBxOm1arVStmKlrqBtU//Q8z+WZ3DWVORVI3aGZpReVSZ85TKF+aznUd+ZN5OAOf"
    "pTLVnGYV8h8qKP1/jNffx/d8kDUAAAAASUVORK5CYII="
)

# --- автообновление: лаунчер смотрит последний релиз на GitHub.
# Номер версии в коде не нужен: чтобы выпустить обновление, достаточно создать на GitHub релиз
# с тегом (например v1.5) и приложить к нему "Nurst Launcher.exe". Какой релиз установлен,
# лаунчер запоминает сам (nurst_config.json, ключ installed_tag).
UPDATE_REPO = "Malik100ma/NurstLauncher"
RELEASES_PAGE = f"https://github.com/{UPDATE_REPO}/releases/latest"
UPDATE_API = f"https://api.github.com/repos/{UPDATE_REPO}/releases/latest"

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

# --- значок сборки: цвет, символ или своя картинка
BUILD_COLORS = ("#ff6a00", "#ef4444", "#eab308", "#22c55e", "#14b8a6", "#3b82f6", "#8b5cf6", "#ec4899", "#6b7280")
BUILD_GLYPHS = ("Буква", "⛏", "⚔", "🏹", "🌲", "🔥", "💎", "🧱", "🚀", "👑", "🐉", "🛡", "⭐", "🌙")
HEX_COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")

# --- экспорт сборки в ZIP: эти папки в корне сборки не упаковываются (миры — по выбору)
EXPORT_SKIP_DIRS = {"logs", "crash-reports"}

# --- аргументы JVM
DEFAULT_JAVA_TEXT = "Автоматически (Java от Mojang под каждую версию)"
RECOMMENDED_JVM = ("-XX:+UseG1GC -XX:+ParallelRefProcEnabled -XX:MaxGCPauseMillis=200 "
                   "-XX:+UnlockExperimentalVMOptions -XX:+DisableExplicitGC -XX:G1NewSizePercent=30 "
                   "-XX:G1MaxNewSizePercent=40 -XX:G1HeapRegionSize=8M -XX:G1ReservePercent=20 "
                   "-XX:G1MixedGCCountTarget=4 -XX:InitiatingHeapOccupancyPercent=15 "
                   "-XX:SurvivorRatio=32 -XX:+PerfDisableSharedMem -XX:MaxTenuringThreshold=1")
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


def parse_version(text) -> tuple:
    """"v1.4.2" -> (1, 4, 2). Пустой кортеж, если номера в строке нет."""
    return tuple(int(n) for n in re.findall(r"\d+", str(text or "")))


def is_newer(latest, current) -> bool:
    a, b = list(parse_version(latest)), list(parse_version(current))
    if not a:
        return False
    size = max(len(a), len(b))
    a += [0] * (size - len(a))
    b += [0] * (size - len(b))
    return a > b


def fetch_latest_release() -> dict:
    """Спрашивает у GitHub последний релиз: {"version": "1.4", "url": ссылка на exe или "", "page": ссылка}."""
    req = urllib.request.Request(UPDATE_API, headers={
        "User-Agent": "NurstLauncher", "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    tag = str(data.get("tag_name") or data.get("name") or "").strip()
    exes = [a for a in data.get("assets", []) if str(a.get("name", "")).lower().endswith(".exe")]
    exes.sort(key=lambda a: "nurst" not in str(a.get("name", "")).lower())
    return {
        "version": tag.lstrip("vV"),
        "url": exes[0].get("browser_download_url", "") if exes else "",
        "size": int(exes[0].get("size") or 0) if exes else 0,
        "digest": str(exes[0].get("digest") or "") if exes else "",   # "sha256:..." (GitHub отдаёт для новых файлов)
        "page": data.get("html_url") or RELEASES_PAGE,
    }


def parse_jvm_args(text) -> list:
    """'-XX:+UseG1GC -Dname="a b"' -> ['-XX:+UseG1GC', '-Dname=a b'].
    Аргументы делятся пробелами, двойные кавычки склеивают пробелы внутри, обратные слэши
    (пути Windows) не трогаются. ValueError, если кавычка не закрыта."""
    args, cur, quoted, has = [], [], False, False
    for ch in str(text or ""):
        if ch == '"':
            quoted = not quoted
            has = True
        elif ch.isspace() and not quoted:
            if cur or has:
                args.append("".join(cur))
                cur, has = [], False
        else:
            cur.append(ch)
    if quoted:
        raise ValueError('Неправильные кавычки в аргументах JVM: не закрыта «"»')
    if cur or has:
        args.append("".join(cur))
    return [a for a in args if a]


def jvm_error(text):
    """Текст ошибки для поля «Аргументы JVM» или None, если всё в порядке."""
    try:
        args = parse_jvm_args(text)
    except ValueError as e:
        return str(e)
    for a in args:
        if not a.startswith("-"):
            return f"«{a}» не похоже на аргумент JVM: он должен начинаться с «-»"
    return None


def file_sha256(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


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


class BuildBadge(tk.Canvas):
    """Значок сборки: цветной скруглённый квадрат с символом / буквой или своя картинка."""

    def __init__(self, parent, size=36):
        super().__init__(parent, width=size, height=size, bg=parent.cget("bg"),
                         highlightthickness=0, bd=0)
        self._bb_size = size
        self._bb_img = None
        self.set_build(None, None, None)

    def set_build(self, name, meta, folder):
        try:
            self.delete("all")
            self._bb_img = None
            s = self._bb_size
            if not name or meta is None:                     # сборка не выбрана
                round_rect(self, 1, 1, s - 1, s - 1, max(6, s // 4), fill=INPUT_HOVER, outline="")
                self.create_text(s // 2, s // 2, text="N", fill=FG_DIM, font=(FONT, int(s * 0.42), "bold"))
                return
            icon = meta.get("icon")
            if icon and folder and PIL_OK:
                try:
                    img = Image.open(os.path.join(folder, str(icon))).convert("RGBA")
                    w, h = img.size
                    m = min(w, h)
                    img = img.crop(((w - m) // 2, (h - m) // 2, (w - m) // 2 + m, (h - m) // 2 + m))
                    resample = getattr(getattr(Image, "Resampling", Image), "LANCZOS")
                    img = img.resize((s, s), resample)
                    mask = Image.new("L", (s * 4, s * 4), 0)
                    ImageDraw.Draw(mask).rounded_rectangle((0, 0, s * 4 - 1, s * 4 - 1), radius=s, fill=255)
                    img.putalpha(mask.resize((s, s), resample))
                    self._bb_img = ImageTk.PhotoImage(img)
                    self.create_image(s // 2, s // 2, image=self._bb_img)
                    return
                except Exception:
                    pass                                      # битая картинка: рисуем обычный значок
            color = meta.get("color")
            color = color if isinstance(color, str) and HEX_COLOR.match(color) else ACCENT
            round_rect(self, 1, 1, s - 1, s - 1, max(6, s // 4), fill=color, outline="")
            glyph = str(meta.get("glyph") or "") or (str(name)[:1].upper() or "N")
            r_, g_, b_ = _rgb(color)
            light = (0.299 * r_ + 0.587 * g_ + 0.114 * b_) > 170
            family = FONT if glyph.isascii() or glyph.isalpha() else "Segoe UI Emoji"
            self.create_text(s // 2, s // 2, text=glyph, fill="#111116" if light else "#ffffff",
                             font=(family, int(s * 0.42), "bold"))
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
        self.icon_pil = None
        self.tray = None
        self.tray_hint_shown = False
        self.all_versions = []
        self.update_info = None     # {"version", "url", "size", "page"}, когда найден более новый релиз
        self.updating = False
        self.moving = False         # идёт перенос файлов в другую папку игры
        self.task_busy = False      # идёт экспорт / импорт / копирование сборки
        self.sb_loading = False     # значения в странице «Сборка» подставляются кодом, а не пользователем
        self.settings_tab = "game"

        self.setup_style()
        self.apply_icon()
        self.create_widgets()
        self.toggle_mode()
        self.refresh_builds(self.config.get("build"))
        self.apply_build()
        self.load_versions_thread()
        self.fit_window()
        self.autologin_ms()
        self.check_updates()
        self.root.after(150, self.apply_titlebar)

        self.started_at = int(time.time())
        self.rpc_base = None
        self.rpc = DiscordPresence()
        self.rpc.set_app(self.discord_app_id())
        self.rpc_idle()

        self.fullscreen = False
        self.root.bind("<F11>", self.toggle_fullscreen)
        self.root.bind("<Escape>", self.on_escape)

        self.root.protocol("WM_DELETE_WINDOW", self.on_window_close)
        self.start_tray()

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
            self.config["tray_close"] = bool(self.tray_close_var.get())
            self.config["auto_update"] = bool(self.auto_update_var.get())
            self.config["loader"] = self.loader_combobox.get()
            self.config["build"] = self.build_combobox.get()
            self.config["jvm_args"] = self.jvm_var.get().strip()
            self.save_build_meta()
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[WARN] Не удалось сохранить настройки: {e}")

    def on_close(self):
        """Полный выход из лаунчера."""
        self.save_config()
        self.stop_tray()
        self.rpc.shutdown()
        self.root.destroy()

    def on_window_close(self):
        """Крестик окна: в трей, если так включено в настройках, иначе выход."""
        if self.moving or self.task_busy:
            messagebox.showinfo("Лаунчер", "Идёт перенос или упаковка файлов, дождитесь конца, чтобы ничего не потерялось.")
            return
        if self.tray is not None and self.tray_close_var.get():
            self.hide_to_tray()
        else:
            self.on_close()

    # --------------------------------------------------------------------- tray
    def start_tray(self):
        """Значок у часов (в трее) с меню: Открыть лаунчер / Играть / Выход."""
        if pystray is None or not PIL_OK or self.icon_pil is None:
            return
        try:
            resample = getattr(getattr(Image, "Resampling", Image), "LANCZOS")
            image = self.icon_pil.resize((64, 64), resample)
            menu = pystray.Menu(
                pystray.MenuItem("Открыть лаунчер", lambda icon, item: self.ui(self.show_window), default=True),
                pystray.MenuItem("Играть", lambda icon, item: self.ui(self.tray_play),
                                 enabled=lambda item: not self.running),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Выход", lambda icon, item: self.ui(self.on_close)),
            )
            self.tray = pystray.Icon("NurstLauncher", image, APP_NAME, menu)
            self.tray.run_detached()
        except Exception as e:
            print(f"[WARN] Не удалось создать значок в трее: {e}")
            self.tray = None

    def stop_tray(self):
        tray, self.tray = self.tray, None
        if tray is not None:
            try:
                tray.stop()
            except Exception:
                pass

    def tray_notify(self, text, only_hidden=False):
        """Всплывающее уведомление из трея (если окно спрятано, иначе и так видно)."""
        if self.tray is None:
            return
        try:
            if only_hidden and self.root.state() not in ("withdrawn", "iconic"):
                return
            self.tray.notify(text, APP_NAME)
        except Exception:
            pass

    def show_window(self):
        """«Открыть лаунчер»: показывает окно поверх остальных, даже если оно свёрнуто или спрятано."""
        self.root.deiconify()
        try:
            self.root.state("normal")
        except Exception:
            pass
        self.root.lift()
        self.root.attributes("-topmost", True)
        self.root.after(250, lambda: self.root.attributes("-topmost", False))
        self.root.focus_force()

    def hide_to_tray(self):
        self.save_config()
        self.root.withdraw()
        if not self.tray_hint_shown:
            self.tray_hint_shown = True
            self.tray_notify("Лаунчер свёрнут в трей. Значок у часов: Открыть, Играть, Выход.")

    def tray_play(self):
        """«Играть» из трея: запуск с текущими версией, сборкой и ником."""
        if self.running:
            self.tray_notify("Игра уже запускается")
            return
        self.tray_notify("Запускаю Minecraft…")
        self.start_launch_thread()

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
        folders = [CONFIG_DIR, self.minecraft_dir]
        if getattr(sys, "_MEIPASS", None):
            folders.append(sys._MEIPASS)
        folders.append(os.path.dirname(os.path.abspath(__file__)))
        for folder in dict.fromkeys(folders):
            for name in ICON_NAMES:
                path = os.path.join(folder, name)
                if os.path.isfile(path):
                    return path
        return None

    def apply_icon(self):
        """Иконка окна, панели задач, шапки и трея: из файла icon.png / icon.ico или встроенная."""
        path = self.find_icon()
        is_win = sys.platform.startswith("win")
        try:
            if PIL_OK:
                src = Image.open(path) if path else Image.open(io.BytesIO(base64.b64decode(ICON_B64)))
                img = src.convert("RGBA")
                w, h = img.size
                s = min(w, h)
                left, top = (w - s) // 2, (h - s) // 2
                img = img.crop((left, top, left + s, top + s))  # центральный квадрат
                resample = getattr(getattr(Image, "Resampling", Image), "LANCZOS")
                self.icon_pil = img

                big = img.resize((256, 256), resample)
                self.icon_img = ImageTk.PhotoImage(big)
                self.root.iconphoto(True, self.icon_img)
                self.logo_img = ImageTk.PhotoImage(round_image(img, 72))

                if is_win:
                    ico_path = os.path.join(CONFIG_DIR, "icon_generated.ico")
                    big.save(ico_path, format="ICO", sizes=[(256, 256), (64, 64), (32, 32), (16, 16)])
                    self.root.iconbitmap(ico_path)
            else:
                if path and path.lower().endswith(".ico"):
                    if is_win:
                        self.root.iconbitmap(path)
                else:
                    self.icon_img = tk.PhotoImage(file=path) if path else tk.PhotoImage(data=ICON_B64)
                    self.root.iconphoto(True, self.icon_img)
                    factor = max(1, round(self.icon_img.width() / 72))
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
        self.footer_version = tk.Label(footer, font=(FONT, 8), bg=BG, fg=FOOT)
        self.footer_version.pack(side=tk.RIGHT)
        self.refresh_version_labels()

        self.update_bar = None
        if self.update_info:
            self.show_update_bar(fit=False)

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
        self.build_badge = BuildBadge(row, size=32)
        self.build_badge.pack(side=tk.LEFT, padx=(0, 8))
        self.build_combobox = ttk.Combobox(row, font=(FONT, 11), state="readonly", values=(NO_BUILD,))
        self.build_combobox.set(NO_BUILD)
        self.build_combobox.pack(side=tk.LEFT, fill="x", expand=True)
        self.build_combobox.bind("<<ComboboxSelected>>", lambda e: self.on_build_selected())
        RoundedButton(row, "Удалить", command=self.delete_build, style="danger",
                      font=(FONT, 10), radius=8, padx=14, pady=6).pack(side=tk.LEFT, padx=(8, 0))
        row = tk.Frame(cell, bg=CARD)
        row.pack(fill="x", pady=(8, 0))
        row.columnconfigure(0, weight=1, uniform="port")
        row.columnconfigure(1, weight=1, uniform="port")
        RoundedButton(row, "⬆  Экспорт сборки (ZIP)", command=self.export_build, style="ghost",
                      font=(FONT, 10), radius=8, pady=6).grid(row=0, column=0, sticky="ew", padx=(0, 4))
        RoundedButton(row, "⬇  Импорт сборки (ZIP)", command=self.import_build, style="ghost",
                      font=(FONT, 10), radius=8, pady=6).grid(row=0, column=1, sticky="ew", padx=(4, 0))

        cell = self.make_field(grid, "СОЗДАТЬ СБОРКУ (ВЕРСИЯ И ЗАГРУЗЧИК — ВЫШЕ)", 2, 0, colspan=2)
        row = tk.Frame(cell, bg=CARD)
        row.pack(fill="x", pady=(4, 0))
        self.new_build_entry = ttk.Entry(row, font=(FONT, 11))
        self.new_build_entry.pack(side=tk.LEFT, fill="x", expand=True)
        self.new_build_entry.bind("<Return>", lambda e: self.create_build())
        RoundedButton(row, "+ Создать", command=self.create_build, style="primary",
                      font=(FONT, 10, "bold"), radius=8, padx=14, pady=6).pack(side=tk.LEFT, padx=(8, 0))

        # ===== настройки: страница в этом же окне («⚙ Настройки» -> «← Назад»), три вкладки
        self.main_column = column
        self.settings_page = tk.Frame(self.root, bg=BG)
        tk.Frame(self.settings_page, width=540, height=1, bg=BG).pack()   # та же ширина, что у главной
        st = self.make_card(self.settings_page, "НАСТРОЙКИ", action=("←  Назад", self.close_settings))
        tabs = tk.Frame(st, bg=CARD)
        tabs.pack(fill="x", pady=(0, 14))
        self.settings_tab_buttons = {}
        self.settings_tab_frames = {}
        titles = (("game", "Игра"), ("build", "Сборка"), ("launcher", "Лаунчер"))
        for i, (key, title) in enumerate(titles):
            tabs.columnconfigure(i, weight=1, uniform="stabs")
            btn = RoundedButton(tabs, title, command=lambda k=key: self.show_settings_tab(k),
                                style="tab_off", font=(FONT, 10, "bold"), radius=9, pady=7)
            btn.grid(row=0, column=i, sticky="ew", padx=(0 if i == 0 else 4, 0 if i == len(titles) - 1 else 4))
            self.settings_tab_buttons[key] = btn
            self.settings_tab_frames[key] = tk.Frame(st, bg=CARD)
        tab_game = self.settings_tab_frames["game"]
        tab_build = self.settings_tab_frames["build"]
        tab_launcher = self.settings_tab_frames["launcher"]

        # ---------- вкладка «Игра»: путь, ОЗУ, версии, Java, аргументы JVM
        tk.Label(tab_game, text="ПУТЬ ИГРЫ", font=(FONT, 8, "bold"), bg=CARD, fg=FG_DIM).pack(anchor="w")
        row = tk.Frame(tab_game, bg=CARD)
        row.pack(fill="x", pady=(4, 14))
        self.game_dir_var = tk.StringVar(value=self.minecraft_dir)
        self.game_dir_entry = ttk.Entry(row, font=(FONT, 10), textvariable=self.game_dir_var, state="readonly")
        self.game_dir_entry.pack(side=tk.LEFT, fill="x", expand=True)
        RoundedButton(row, "📁", command=self.choose_game_dir, style="primary",
                      font=(FONT, 12), radius=8, padx=12, pady=4).pack(side=tk.LEFT, padx=(8, 0))
        RoundedButton(row, "По умолчанию", command=self.reset_game_dir, style="ghost",
                      font=(FONT, 9), radius=8, padx=10, pady=7).pack(side=tk.LEFT, padx=(6, 0))
        head = tk.Frame(tab_game, bg=CARD)
        head.pack(fill="x")
        tk.Label(head, text="ОЗУ ДЛЯ ИГРЫ (У СБОРКИ МОЖЕТ БЫТЬ СВОЯ)", font=(FONT, 8, "bold"),
                 bg=CARD, fg=FG_DIM).pack(side=tk.LEFT)
        self.ram_text = tk.Label(head, font=(FONT, 10, "bold"), bg=CARD, fg=ACCENT)
        self.ram_text.pack(side=tk.RIGHT)
        self.ram_var = tk.IntVar(value=int(self.config.get("ram", 2)))
        Slider(tab_game, self.ram_var, from_=1, to=16).pack(fill="x", pady=(2, 8))
        self.ram_var.trace_add("write", self.on_ram_change)
        self.on_ram_change()

        self.show_all_var = tk.BooleanVar(value=bool(self.config.get("show_all", False)))
        row = tk.Frame(tab_game, bg=CARD)
        row.pack(fill="x")
        Switch(row, self.show_all_var, command=self.refresh_versions).pack(side=tk.LEFT)
        lbl = tk.Label(row, text="Показывать снапшоты и старые версии", font=(FONT, 10),
                       bg=CARD, fg=FG_DIM, cursor="hand2")
        lbl.pack(side=tk.LEFT, padx=(10, 0))
        lbl.bind("<Button-1>", lambda e: (self.show_all_var.set(not self.show_all_var.get()),
                                          self.refresh_versions()))

        tk.Label(tab_game, text="JAVA", font=(FONT, 8, "bold"), bg=CARD, fg=FG_DIM).pack(anchor="w", pady=(16, 0))
        row = tk.Frame(tab_game, bg=CARD)
        row.pack(fill="x", pady=(4, 0))
        saved_java = str(self.config.get("java_path") or "")
        self.java_var = tk.StringVar(value=saved_java or DEFAULT_JAVA_TEXT)
        ttk.Entry(row, font=(FONT, 10), textvariable=self.java_var, state="readonly").pack(
            side=tk.LEFT, fill="x", expand=True)
        RoundedButton(row, "📁", command=self.choose_java, style="primary",
                      font=(FONT, 12), radius=8, padx=12, pady=4).pack(side=tk.LEFT, padx=(8, 0))
        RoundedButton(row, "Авто", command=self.reset_java, style="ghost",
                      font=(FONT, 9), radius=8, padx=10, pady=7).pack(side=tk.LEFT, padx=(6, 0))
        self.java_note = tk.Label(tab_game, text="", font=(FONT, 8), bg=CARD, fg=FG_DIM, anchor="w")
        self.java_note.pack(fill="x", pady=(4, 0))

        tk.Label(tab_game, text="АРГУМЕНТЫ JVM (ЧЕРЕЗ ПРОБЕЛ)", font=(FONT, 8, "bold"),
                 bg=CARD, fg=FG_DIM).pack(anchor="w", pady=(10, 0))
        row = tk.Frame(tab_game, bg=CARD)
        row.pack(fill="x", pady=(4, 0))
        self.jvm_var = tk.StringVar(value=str(self.config.get("jvm_args") or ""))
        self.jvm_entry = ttk.Entry(row, font=(FONT, 10), textvariable=self.jvm_var)
        self.jvm_entry.pack(side=tk.LEFT, fill="x", expand=True)
        self.jvm_entry.bind("<FocusOut>", lambda e: self.save_config())
        RoundedButton(row, "Рекомендуемые", command=self.fill_recommended_jvm, style="ghost",
                      font=(FONT, 9), radius=8, padx=10, pady=7).pack(side=tk.LEFT, padx=(8, 0))
        RoundedButton(row, "Очистить", command=lambda: self.jvm_var.set(""), style="ghost",
                      font=(FONT, 9), radius=8, padx=10, pady=7).pack(side=tk.LEFT, padx=(6, 0))
        self.jvm_note = tk.Label(tab_game, text="", font=(FONT, 8), bg=CARD, fg=FG_DIM, anchor="w",
                                 wraplength=500, justify="left")
        self.jvm_note.pack(fill="x", pady=(4, 0))
        self.jvm_var.trace_add("write", self.on_jvm_change)
        self.on_jvm_change()
        self.refresh_java_note()

        # ---------- вкладка «Сборка»: управление выбранной сборкой
        row = tk.Frame(tab_build, bg=CARD)
        row.pack(fill="x")
        self.sb_badge = BuildBadge(row, size=44)
        self.sb_badge.pack(side=tk.LEFT, padx=(0, 10))
        col = tk.Frame(row, bg=CARD)
        col.pack(side=tk.LEFT, fill="x", expand=True)
        tk.Label(col, text="СБОРКА", font=(FONT, 8, "bold"), bg=CARD, fg=FG_DIM).pack(anchor="w")
        self.sb_combobox = ttk.Combobox(col, font=(FONT, 11), state="readonly", values=(NO_BUILD,))
        self.sb_combobox.set(NO_BUILD)
        self.sb_combobox.pack(fill="x", pady=(4, 0))
        self.sb_combobox.bind("<<ComboboxSelected>>", self.on_sb_selected)
        self.sb_hint = tk.Label(tab_build, text="", font=(FONT, 9), bg=CARD, fg=WARN, anchor="w")
        self.sb_hint.pack(fill="x", pady=(6, 0))

        tk.Label(tab_build, text="НАЗВАНИЕ", font=(FONT, 8, "bold"), bg=CARD, fg=FG_DIM).pack(anchor="w", pady=(8, 0))
        row = tk.Frame(tab_build, bg=CARD)
        row.pack(fill="x", pady=(4, 0))
        self.sb_name_var = tk.StringVar()
        name_entry = ttk.Entry(row, font=(FONT, 11), textvariable=self.sb_name_var)
        name_entry.pack(side=tk.LEFT, fill="x", expand=True)
        name_entry.bind("<Return>", lambda e: self.rename_build())
        RoundedButton(row, "Переименовать", command=self.rename_build, style="primary",
                      font=(FONT, 10, "bold"), radius=8, padx=12, pady=6).pack(side=tk.LEFT, padx=(8, 0))
        RoundedButton(row, "Дублировать", command=self.duplicate_build, style="ghost",
                      font=(FONT, 10), radius=8, padx=12, pady=6).pack(side=tk.LEFT, padx=(6, 0))

        tk.Label(tab_build, text="ЗНАЧОК: ЦВЕТ", font=(FONT, 8, "bold"), bg=CARD, fg=FG_DIM).pack(anchor="w", pady=(14, 0))
        row = tk.Frame(tab_build, bg=CARD)
        row.pack(fill="x", pady=(4, 0))
        for color in BUILD_COLORS:
            sw = tk.Canvas(row, width=26, height=26, bg=CARD, highlightthickness=0, bd=0, cursor="hand2")
            round_rect(sw, 2, 2, 24, 24, 7, fill=color, outline="")
            sw.bind("<Button-1>", lambda e, c=color: self.set_build_color(c))
            sw.pack(side=tk.LEFT, padx=(0, 5))
        RoundedButton(row, "Свой цвет…", command=self.pick_build_color, style="ghost",
                      font=(FONT, 9), radius=8, padx=10, pady=4).pack(side=tk.LEFT, padx=(4, 0))

        row = tk.Frame(tab_build, bg=CARD)
        row.pack(fill="x", pady=(10, 0))
        tk.Label(row, text="Символ:", font=(FONT, 10), bg=CARD, fg=FG_DIM).pack(side=tk.LEFT)
        self.sb_glyph = ttk.Combobox(row, font=(FONT, 11), state="readonly", width=7, values=BUILD_GLYPHS)
        self.sb_glyph.set(BUILD_GLYPHS[0])
        self.sb_glyph.pack(side=tk.LEFT, padx=(8, 8))
        self.sb_glyph.bind("<<ComboboxSelected>>", self.on_glyph_selected)
        RoundedButton(row, "Своя картинка…", command=self.pick_build_image, style="ghost",
                      font=(FONT, 9), radius=8, padx=10, pady=5).pack(side=tk.LEFT)
        RoundedButton(row, "Сбросить", command=self.reset_build_icon, style="ghost",
                      font=(FONT, 9), radius=8, padx=10, pady=5).pack(side=tk.LEFT, padx=(6, 0))

        head = tk.Frame(tab_build, bg=CARD)
        head.pack(fill="x", pady=(16, 0))
        self.sb_ram_on = tk.BooleanVar(value=False)
        Switch(head, self.sb_ram_on, command=self.on_sb_ram_toggle).pack(side=tk.LEFT)
        lbl = tk.Label(head, text="Своя ОЗУ для этой сборки", font=(FONT, 10), bg=CARD, fg=FG_DIM, cursor="hand2")
        lbl.pack(side=tk.LEFT, padx=(10, 0))
        lbl.bind("<Button-1>", lambda e: (self.sb_ram_on.set(not self.sb_ram_on.get()), self.on_sb_ram_toggle()))
        self.sb_ram_text = tk.Label(head, font=(FONT, 10, "bold"), bg=CARD, fg=ACCENT)
        self.sb_ram_text.pack(side=tk.RIGHT)
        self.sb_ram_var = tk.IntVar(value=int(self.config.get("ram", 2)))
        Slider(tab_build, self.sb_ram_var, from_=1, to=16).pack(fill="x", pady=(2, 0))
        self.sb_ram_var.trace_add("write", self.on_sb_ram_change)

        # ---------- вкладка «Лаунчер»: Discord, трей, тема, обновления
        self.discord_var = tk.BooleanVar(value=bool(self.config.get("discord", True)))
        row = tk.Frame(tab_launcher, bg=CARD)
        row.pack(fill="x")
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

        self.tray_close_var = tk.BooleanVar(value=bool(self.config.get("tray_close", False)))
        row = tk.Frame(tab_launcher, bg=CARD)
        row.pack(fill="x", pady=(10, 0))
        Switch(row, self.tray_close_var).pack(side=tk.LEFT)
        lbl = tk.Label(row, text="Закрытие окна сворачивает в трей", font=(FONT, 10),
                       bg=CARD, fg=FG_DIM, cursor="hand2")
        lbl.pack(side=tk.LEFT, padx=(10, 0))
        lbl.bind("<Button-1>", lambda e: self.tray_close_var.set(not self.tray_close_var.get()))
        if pystray is None:
            tk.Label(row, text="(не установлен pystray)", font=(FONT, 8), bg=CARD, fg=WARN).pack(side=tk.LEFT, padx=(8, 0))

        self.light_var = tk.BooleanVar(value=(THEME == "light"))
        row = tk.Frame(tab_launcher, bg=CARD)
        row.pack(fill="x", pady=(10, 0))
        Switch(row, self.light_var, command=self.on_theme_toggle).pack(side=tk.LEFT)
        lbl = tk.Label(row, text="Светлая тема (чёрное на белом)", font=(FONT, 10),
                       bg=CARD, fg=FG_DIM, cursor="hand2")
        lbl.pack(side=tk.LEFT, padx=(10, 0))
        lbl.bind("<Button-1>", lambda e: (self.light_var.set(not self.light_var.get()),
                                          self.on_theme_toggle()))

        row = tk.Frame(tab_launcher, bg=CARD)
        row.pack(fill="x", pady=(14, 0))
        self.version_label = tk.Label(row, font=(FONT, 10), bg=CARD, fg=FG_DIM)
        self.version_label.pack(side=tk.LEFT)
        self.refresh_version_labels()
        RoundedButton(row, "Проверить обновления", command=lambda: self.check_updates(manual=True),
                      style="ghost", font=(FONT, 9, "bold"), radius=8, padx=12, pady=5).pack(side=tk.RIGHT)
        self.update_note = tk.Label(tab_launcher, text="", font=(FONT, 9), bg=CARD, fg=FG_DIM, anchor="w")
        self.update_note.pack(fill="x", pady=(4, 0))
        self.auto_update_var = tk.BooleanVar(value=bool(self.config.get("auto_update", True)))
        row = tk.Frame(tab_launcher, bg=CARD)
        row.pack(fill="x", pady=(8, 0))
        Switch(row, self.auto_update_var).pack(side=tk.LEFT)
        lbl = tk.Label(row, text="Обновлять автоматически (при выходе нового релиза)", font=(FONT, 10),
                       bg=CARD, fg=FG_DIM, cursor="hand2")
        lbl.pack(side=tk.LEFT, padx=(10, 0))
        lbl.bind("<Button-1>", lambda e: self.auto_update_var.set(not self.auto_update_var.get()))

        self.show_settings_tab(self.settings_tab if self.settings_tab in self.settings_tab_frames else "game")
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

    GAME_FOLDER_NAME = ".nurstclient"

    def choose_game_dir(self):
        """Окно выбора папки. Внутри выбранной папки лаунчер сам создаёт .nurstclient
        (если выбрана уже сама папка .nurstclient, она используется как есть)."""
        folder = filedialog.askdirectory(parent=self.root, title="Куда поставить Minecraft",
                                         initialdir=os.path.dirname(self.minecraft_dir) or self.minecraft_dir,
                                         mustexist=False)
        if not folder:
            return
        folder = os.path.normpath(folder)
        if os.path.basename(folder).lower() != self.GAME_FOLDER_NAME:
            folder = os.path.join(folder, self.GAME_FOLDER_NAME)
        self.set_game_dir(folder)

    def reset_game_dir(self):
        self.set_game_dir(GAME_DIR)

    @staticmethod
    def _inside(child, parent) -> bool:
        child, parent = os.path.normcase(os.path.abspath(child)), os.path.normcase(os.path.abspath(parent))
        return child == parent or child.startswith(parent + os.sep)

    def movable_entries(self, old, new):
        """Что переносить из старой папки: всё, кроме файлов настроек лаунчера и самой новой папки."""
        skip = {"nurst_config.json", "icon_generated.ico"}
        if os.path.normcase(os.path.abspath(old)) == os.path.normcase(os.path.abspath(CONFIG_DIR)):
            skip |= set(ICON_NAMES)     # своя иконка остаётся там, где лаунчер её ищет
        try:
            names = os.listdir(old)
        except OSError:
            return []
        return [n for n in names if n not in skip and not self._inside(new, os.path.join(old, n))]

    @staticmethod
    def merge_move(src, dst, problems):
        """Переносит файл или папку; если папка уже есть в новом месте, содержимое сливается.
        Файл, который уже лежит в новой папке, не перезаписывается (остаётся в старой)."""
        try:
            if os.path.isdir(src) and not os.path.islink(src) and os.path.isdir(dst):
                for name in os.listdir(src):
                    NurstLauncherApp.merge_move(os.path.join(src, name), os.path.join(dst, name), problems)
                try:
                    os.rmdir(src)
                except OSError:
                    pass
                return
            if os.path.lexists(dst):
                problems.append(f"{dst} — уже есть в новой папке, оставлен в старой")
                return
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.move(src, dst)
        except Exception as e:
            problems.append(f"{src} — {e}")

    def set_game_dir(self, path):
        """Меняет папку игры. Если в старой папке есть файлы (версии, сборки, моды, миры),
        предлагает перенести их в новую."""
        path = os.path.normpath(os.path.expanduser(str(path).strip()))
        if self.running:
            messagebox.showinfo("Папка игры", "Сначала дождитесь конца загрузки, переноса или закройте игру.")
            return
        created = not os.path.isdir(path)
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

        def undo_created():
            if created:
                try:
                    os.rmdir(path)      # пустую папку, которую только что создали, не оставляем
                except OSError:
                    pass

        old = self.minecraft_dir
        if os.path.normcase(path) == os.path.normcase(old):
            return
        entries = self.movable_entries(old, path)
        move = False
        if entries:
            answer = messagebox.askyesnocancel(
                "Папка игры",
                f"Перенести файлы из старой папки в новую?\n\n{old}\n  →  {path}\n\n"
                "Это версии, Java, сборки, моды и миры. Если нажать «Нет», путь просто сменится, "
                "а Minecraft скачается в новую папку заново.\n\n"
                "Да — перенести (может занять время)\nНет — только сменить путь\nОтмена — ничего не менять")
            if answer is None:
                undo_created()
                self.game_dir_var.set(self.minecraft_dir)
                return
            move = bool(answer)
        if not move:
            self.apply_game_dir(path)
            return

        self.running = True                  # на время переноса игру запустить нельзя
        self.moving = True
        self.play_button.config(state="disabled")
        self.update_status("📦 Переношу файлы в новую папку…", WARN)
        threading.Thread(target=self.move_worker, args=(old, path, entries), daemon=True).start()

    def move_worker(self, old, new, entries):
        problems = []
        total = len(entries)
        for i, name in enumerate(entries, 1):
            self.ui(self.update_status, f"📦 Переношу ({i}/{total}): {name}", WARN)
            self.merge_move(os.path.join(old, name), os.path.join(new, name), problems)
        self.ui(self.finish_move, old, new, problems)

    def finish_move(self, old, new, problems):
        self.running = False
        self.moving = False
        self.play_button.config(state="normal")
        if os.path.normcase(os.path.abspath(old)) != os.path.normcase(os.path.abspath(CONFIG_DIR)):
            try:
                os.rmdir(old)                # пустую старую папку убираем
            except OSError:
                pass
        self.apply_game_dir(new, moved=True)
        if problems:
            shown = "\n".join(problems[:6]) + (f"\n…и ещё {len(problems) - 6}" if len(problems) > 6 else "")
            messagebox.showerror("Папка игры", f"Не всё удалось перенести ({len(problems)}):\n\n{shown}\n\n"
                                               f"Эти файлы остались в старой папке:\n{old}")

    def apply_game_dir(self, path, moved=False):
        """Запоминает новую папку игры и обновляет интерфейс."""
        self.minecraft_dir = path
        if os.path.normcase(path) == os.path.normcase(os.path.normpath(GAME_DIR)):
            self.config.pop("game_dir", None)
        else:
            self.config["game_dir"] = path
        self.game_dir_var.set(path)
        self.footer_path.config(text=path)
        self.refresh_builds(self.config.get("build"))
        self.apply_build()
        if moved:
            self.update_status("✅ Файлы перенесены, папка игры изменена", OK)
        else:
            self.update_status("Папка игры изменена. Версии и Java скачаются в неё заново", OK)
        self.save_config()

    # ------------------------------------------------------------- автообновление
    def check_updates(self, manual=False):
        threading.Thread(target=self.check_updates_worker, args=(manual,), daemon=True).start()

    def check_updates_worker(self, manual=False):
        try:
            info = fetch_latest_release()
        except Exception as e:
            print(f"[WARN] Не удалось проверить обновления: {e}")
            if manual:
                self.ui(self.set_update_note, "Не удалось проверить обновления (нет интернета?)", ERR)
            return
        try:
            needed, record = self.decide_update(info)
        except Exception as e:
            print(f"[WARN] Не удалось сравнить версии: {e}")
            return
        if record:
            self.ui(self.record_installed, record)
        if needed:
            self.ui(self.on_update_found, info, manual)
        elif manual:
            shown = info["version"] or self.installed_version()
            self.ui(self.set_update_note, f"У вас последняя версия ({shown})", OK)

    def installed_version(self) -> str:
        return str(self.config.get("installed_tag") or "")

    def refresh_version_labels(self):
        ver = self.installed_version()
        for name, text in (("footer_version", f"{'v' + ver + '  ·  ' if ver else ''}F11 — полный экран"),
                           ("version_label", f"Версия лаунчера: {ver}" if ver else "Версия лаунчера: определится после проверки")):
            label = getattr(self, name, None)
            if label is not None:
                try:
                    label.config(text=text)
                except Exception:
                    pass

    def record_installed(self, tag):
        """Запоминает, какой релиз сейчас установлен."""
        self.config["installed_tag"] = tag
        self.save_config()
        self.refresh_version_labels()

    def decide_update(self, info):
        """Нужно ли обновление и что запомнить как установленный релиз: (нужно, тег или None).

        Установленный релиз лаунчер знает по записи в настройках. Если записи ещё нет (первый запуск
        после появления автообновления), exe сравнивается с файлом релиза по sha256: совпал — это и
        есть последний релиз, не совпал — релиз новее. Если сравнить нечем, считаем, что у вас последний."""
        tag = info.get("version") or ""
        if not tag:
            return False, None
        installed = self.installed_version()
        if installed:
            if parse_version(tag) and parse_version(installed):
                return is_newer(tag, installed), None
            return tag != installed, None
        digest = (info.get("digest") or "").lower()
        digest = digest.split(":", 1)[1] if digest.startswith("sha256:") else digest
        if getattr(sys, "frozen", False) and len(digest) == 64:
            if file_sha256(sys.executable) == digest:
                return False, tag
            return True, None
        return False, tag

    def set_update_note(self, text, color=None):
        try:
            self.update_note.config(text=text, fg=color or FG_DIM)
        except Exception:
            pass

    def can_self_update(self, info) -> bool:
        """Сам заменить себя можно только собранному exe на Windows и если в релизе есть exe."""
        return bool(getattr(sys, "frozen", False) and sys.platform.startswith("win") and info.get("url"))

    def on_update_found(self, info, manual=False):
        self.update_info = info
        self.set_update_note(f"Доступна версия {info['version']}", OK)
        self.show_update_bar()
        # автообновление: ставим сами. Одну и ту же версию автоматически пробуем только раз,
        # чтобы не уйти в бесконечное обновление, если номер внутри exe забыли поднять
        if (self.auto_update_var.get() and self.can_self_update(info) and not self.running
                and not self.moving and self.config.get("update_tried") != info["version"]):
            self.start_update()

    def show_update_bar(self, fit=True):
        """Плашка под шапкой: «Доступна версия 1.4» и кнопка «Обновить»."""
        if self.update_bar is not None:
            try:
                self.update_bar.destroy()
            except Exception:
                pass
        bar = tk.Frame(self.root, bg=CARD, highlightbackground=ACCENT, highlightcolor=ACCENT,
                       highlightthickness=1)
        bar.pack(fill="x", padx=20, pady=(10, 0), after=self.header)
        inner = tk.Frame(bar, bg=CARD)
        inner.pack(fill="x", padx=14, pady=8)
        self.update_label = tk.Label(inner, text=f"⬆  Доступна версия {self.update_info['version']}",
                                     font=(FONT, 11, "bold"), bg=CARD, fg=ACCENT)
        self.update_label.pack(side=tk.LEFT)
        self.update_button = RoundedButton(inner, "Обновить", command=self.start_update, style="primary",
                                           font=(FONT, 10, "bold"), radius=8, padx=16, pady=5)
        self.update_button.pack(side=tk.RIGHT)
        self.update_later = RoundedButton(inner, "Позже", command=self.hide_update_bar, style="ghost",
                                          font=(FONT, 10), radius=8, padx=12, pady=5)
        self.update_later.pack(side=tk.RIGHT, padx=(0, 8))
        self.update_bar = bar
        if fit:
            self.fit_window(resize=False)

    def hide_update_bar(self):
        if self.updating:
            return
        if self.update_bar is not None:
            self.update_bar.destroy()
            self.update_bar = None
        self.update_info = None

    def start_update(self):
        if self.updating or not self.update_info:
            return
        info = self.update_info
        # из .py-скрипта или без exe в релизе обновиться самому нельзя: открываем страницу релиза
        if not self.can_self_update(info):
            webbrowser.open(info.get("page") or RELEASES_PAGE)
            return
        if self.running:
            messagebox.showinfo("Обновление", "Дождитесь конца загрузки или закройте игру, затем обновите лаунчер.")
            return
        self.updating = True
        self.config["update_tried"] = info["version"]
        self.save_config()
        self.update_button.config(state="disabled", text="Скачиваю…")
        self.update_later.config(state="disabled")
        threading.Thread(target=self.update_worker, args=(info,), daemon=True).start()

    def update_worker(self, info):
        exe = os.path.abspath(sys.executable)
        new_exe = exe + ".new"
        try:
            req = urllib.request.Request(info["url"], headers={"User-Agent": "NurstLauncher"})
            done = 0
            with urllib.request.urlopen(req, timeout=30) as resp, open(new_exe, "wb") as out:
                total = int(resp.headers.get("Content-Length") or info.get("size") or 0)
                while True:
                    chunk = resp.read(1024 * 256)
                    if not chunk:
                        break
                    out.write(chunk)
                    done += len(chunk)
                    if total:
                        self.ui(self.update_label.config, text=f"⬆  Скачиваю {info['version']}: {done * 100 // total}%")
            with open(new_exe, "rb") as f:
                head = f.read(2)
            if done < 1_000_000 or head != b"MZ" or (total and done != total):
                raise RuntimeError("файл скачался не полностью или повреждён")
        except Exception as e:
            print(f"[WARN] Обновление не скачалось: {e}")
            try:
                os.remove(new_exe)
            except OSError:
                pass
            self.updating = False
            self.config.pop("update_tried", None)        # не вышло: в следующий раз попробуем снова
            self.ui(self.update_label.config, text=f"⬆  Доступна версия {info['version']}")
            self.ui(self.update_button.config, state="normal", text="Обновить")
            self.ui(self.update_later.config, state="normal")
            self.ui(messagebox.showerror, "Обновление", f"Не удалось скачать обновление:\n{e}\n\n"
                                                        f"Можно скачать вручную:\n{info.get('page') or RELEASES_PAGE}")
            return
        self.ui(self.finish_update, exe, new_exe, info["version"])

    def finish_update(self, exe, new_exe, tag=None):
        """Запускает скрипт, который после закрытия лаунчера подменит exe и откроет новую версию."""
        try:
            script = self.write_updater_script(exe, new_exe)
            env = dict(os.environ, PYINSTALLER_RESET_ENVIRONMENT="1")
            flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) | getattr(subprocess, "DETACHED_PROCESS", 0)
            subprocess.Popen(["cmd", "/c", script], creationflags=flags, env=env, close_fds=True)
            if tag:
                self.config["installed_tag"] = tag  # on_close ниже сохранит; новая версия будет знать, что она последняя
        except Exception as e:
            self.updating = False
            messagebox.showerror("Обновление", f"Не удалось запустить обновление:\n{e}")
            return
        self.on_close()

    @staticmethod
    def write_updater_script(exe, new_exe) -> str:
        import tempfile
        script = os.path.join(tempfile.gettempdir(), "nurst_update.bat")
        lines = [
            "@echo off",
            "set n=0",
            ":wait",
            "set /a n+=1",
            "if %n% gtr 60 exit /b 1",
            "timeout /t 1 /nobreak >nul",
            f'move /y "{new_exe}" "{exe}" >nul 2>&1',
            "if errorlevel 1 goto wait",
            f'start "" "{exe}"',
            'del "%~f0"',
        ]
        with open(script, "w", encoding="utf-8", newline="\r\n") as f:
            f.write("\r\n".join(lines) + "\r\n")
        return script

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
        # страница настроек: берём самую большую вкладку
        if getattr(self, "settings_page", None) is not None:
            was_open, tab = self.settings_open, self.settings_tab
            self.main_column.pack_forget()
            self.settings_page.pack(expand=True, padx=20, pady=(14, 4))
            for key in self.settings_tab_frames:
                self.show_settings_tab(key)
                self.root.update_idletasks()
                req_w = max(req_w, self.root.winfo_reqwidth())
                req_h = max(req_h, self.root.winfo_reqheight())
            self.show_settings_tab(tab)
            if not was_open:
                self.settings_page.pack_forget()
                self.main_column.pack(expand=True, padx=20, pady=(14, 4))
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
        self.update_build_views()

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
        self.update_build_views()
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
        error, slug = self.build_name_error(name)
        if error:
            messagebox.showerror("Сборка", error)
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

    # ------------------------------------------------------- вкладки настроек
    def show_settings_tab(self, key):
        self.settings_tab = key
        for name, frame in self.settings_tab_frames.items():
            frame.pack_forget()
        self.settings_tab_frames[key].pack(fill="x")
        for name, btn in self.settings_tab_buttons.items():
            btn.set_style("primary" if name == key else "tab_off")

    # --------------------------------------------------------- Java и аргументы JVM
    @staticmethod
    def detect_java(path) -> str:
        """Запускает «java -version» и возвращает номер версии, иначе RuntimeError."""
        flags = 0x08000000 if sys.platform.startswith("win") else 0
        res = subprocess.run([path, "-version"], capture_output=True, text=True, timeout=10, creationflags=flags)
        text = (res.stderr or "") + (res.stdout or "")
        m = re.search(r'version "([^"]+)"', text) or re.search(r"(\d+\.\d+[\w.+\-]*)", text)
        if res.returncode != 0 or not m:
            raise RuntimeError(text.strip()[:200] or "программа не ответила")
        return m.group(1)

    def refresh_java_note(self):
        path = str(self.config.get("java_path") or "")
        if not path:
            self.java_note.config(text="Для каждой версии Minecraft берётся нужная Java от Mojang", fg=FG_DIM)
        elif not os.path.isfile(path):
            self.java_note.config(text="⚠ Файл не найден, при запуске будет Java от Mojang", fg=WARN)
        else:
            self.java_note.config(text=f"✅ Java {self.config.get('java_version', '')}".strip(), fg=OK)

    def choose_java(self):
        path = filedialog.askopenfilename(
            parent=self.root, title="Выберите java.exe или javaw.exe",
            filetypes=[("Java", "java.exe javaw.exe java"), ("Все файлы", "*.*")])
        if path:
            self.set_java_path(path)

    def set_java_path(self, path):
        path = os.path.normpath(path)
        try:
            version = self.detect_java(path)
        except Exception as e:
            messagebox.showerror("Java", f"Это не похоже на Java:\n{path}\n\n{e}")
            return
        self.config["java_path"] = path
        self.config["java_version"] = version
        self.java_var.set(path)
        self.refresh_java_note()
        self.save_config()

    def reset_java(self):
        self.config.pop("java_path", None)
        self.config.pop("java_version", None)
        self.java_var.set(DEFAULT_JAVA_TEXT)
        self.refresh_java_note()
        self.save_config()

    def fill_recommended_jvm(self):
        self.jvm_var.set(RECOMMENDED_JVM)
        self.save_config()

    def on_jvm_change(self, *args):
        error = jvm_error(self.jvm_var.get())
        if error:
            self.jvm_note.config(text=f"⚠ {error}", fg=ERR)
        else:
            self.jvm_note.config(text="Например: -XX:+UseG1GC. Свои -Xmx / -Xms заменяют ОЗУ из настроек", fg=FG_DIM)

    # ------------------------------------------------------- управление сборкой
    def current_build(self):
        """(название, папка, build.json) выбранной сборки или (None, None, None)."""
        path = self.current_build_path()
        if not path:
            return None, None, None
        return self.build_combobox.get(), path, (self.read_build_meta(path) or {})

    def write_build_meta(self, path, meta):
        with open(os.path.join(path, "build.json"), "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

    def require_build(self):
        name, path, meta = self.current_build()
        if not path:
            messagebox.showinfo("Сборка", "Сначала выберите сборку в списке.")
            return None
        return name, path, meta

    def build_name_error(self, name, ignore=None):
        """(текст ошибки или None, имя папки) для названия сборки. ignore: своя же папка (при переименовании)."""
        def same(a, b):
            return bool(b) and os.path.normcase(os.path.abspath(a)) == os.path.normcase(os.path.abspath(b))

        if not name:
            return "Введите название сборки!", ""
        slug = slugify(name)
        if not slug:
            return "В названии нужны буквы или цифры.", ""
        if slug in RESERVED_NAMES:
            return "Это имя занято служебной папкой игры, выберите другое.", slug
        taken = self.list_builds().get(name)
        target = os.path.join(self.minecraft_dir, slug)
        if (taken and not same(taken, ignore)) or (os.path.exists(target) and not same(target, ignore)):
            return "Сборка с таким названием уже есть.", slug
        return None, slug

    def unique_build(self, base):
        """Свободное название сборки: base, а если занято, «base (2)», «base (3)»…"""
        base = (base or "").strip()[:64]
        if not slugify(base):
            base = "Сборка"
        candidate = base
        n = 2
        while self.build_name_error(candidate)[0]:
            candidate = f"{base} ({n})"
            n += 1
        return candidate, slugify(candidate)

    def update_build_views(self):
        """Обновляет значки и поля управления под выбранную сборку."""
        name, path, meta = self.current_build()
        for badge in (getattr(self, "build_badge", None), getattr(self, "sb_badge", None)):
            if badge is not None:
                badge.set_build(name, meta, path)
        if not hasattr(self, "sb_combobox"):
            return
        self.sb_combobox["values"] = self.build_combobox["values"]
        self.sb_combobox.set(self.build_combobox.get())
        self.sb_loading = True
        try:
            self.sb_name_var.set(name or "")
            own = bool(meta and isinstance(meta.get("ram"), int) and meta["ram"] > 0)
            self.sb_ram_on.set(own)
            self.sb_ram_var.set(meta["ram"] if own else int(self.ram_var.get()))
            glyph = (meta or {}).get("glyph")
            self.sb_glyph.set(glyph if glyph in BUILD_GLYPHS else BUILD_GLYPHS[0])
        finally:
            self.sb_loading = False
        self.sb_hint.config(text="" if name else "Выберите сборку, чтобы ей управлять")
        self.refresh_sb_ram_label()

    def on_sb_selected(self, event=None):
        self.build_combobox.set(self.sb_combobox.get())
        self.on_build_selected()

    def rename_build(self):
        cur = self.require_build()
        if not cur:
            return
        if self.running:
            messagebox.showinfo("Сборка", "Дождитесь конца загрузки или закройте игру.")
            return
        name, path, meta = cur
        new = self.sb_name_var.get().strip()
        if new == name:
            return
        error, slug = self.build_name_error(new, ignore=path)
        if error:
            messagebox.showerror("Сборка", error)
            return
        new_path = os.path.join(self.minecraft_dir, slug)
        try:
            if os.path.normcase(new_path) != os.path.normcase(path):
                os.rename(path, new_path)
        except OSError as e:
            messagebox.showerror("Сборка", f"Не удалось переименовать (закройте игру, если она запущена):\n{e}")
            return
        meta["name"] = new
        self.write_build_meta(new_path, meta)
        self.config["build"] = new
        self.refresh_builds(new)
        self.update_status(f"✅ Сборка переименована: «{name}» → «{new}»", OK)
        self.save_config()

    def duplicate_build(self):
        cur = self.require_build()
        if not cur:
            return
        if self.running:
            messagebox.showinfo("Сборка", "Дождитесь конца загрузки или закройте игру.")
            return
        name, path, meta = cur
        new = simpledialog.askstring("Дублировать сборку", "Название копии:", parent=self.root,
                                     initialvalue=self.unique_build(f"{name} (копия)")[0])
        if not new:
            return
        new = new.strip()
        error, slug = self.build_name_error(new)
        if error:
            messagebox.showerror("Сборка", error)
            return
        self.begin_task(f"📑 Копирую сборку «{name}»…")
        threading.Thread(target=self.duplicate_worker, args=(path, new, slug), daemon=True).start()

    def duplicate_worker(self, src, new, slug):
        dest = os.path.join(self.minecraft_dir, slug)
        try:
            shutil.copytree(src, dest)
            meta = self.read_build_meta(dest) or {}
            meta["name"] = new
            self.write_build_meta(dest, meta)
        except Exception as e:
            shutil.rmtree(dest, ignore_errors=True)
            self.ui(self.finish_duplicate, None, str(e))
            return
        self.ui(self.finish_duplicate, new, None)

    def finish_duplicate(self, new, error):
        self.end_task()
        if error:
            messagebox.showerror("Сборка", f"Не удалось скопировать сборку:\n{error}")
            self.update_status("❌ Копирование не удалось", ERR)
            return
        self.refresh_builds(new)
        self.apply_build()
        self.update_status(f"✅ Копия создана: «{new}»", OK)
        self.save_config()

    def set_build_color(self, color):
        cur = self.require_build()
        if not cur:
            return
        name, path, meta = cur
        meta["color"] = color
        self.write_build_meta(path, meta)
        self.update_build_views()

    def pick_build_color(self):
        cur = self.require_build()
        if not cur:
            return
        meta = cur[2]
        result = colorchooser.askcolor(color=meta.get("color") or ACCENT, parent=self.root,
                                       title="Цвет значка сборки")
        if result and result[1]:
            self.set_build_color(str(result[1]).lower())

    def on_glyph_selected(self, event=None):
        if self.sb_loading:
            return
        cur = self.require_build()
        if not cur:
            return
        name, path, meta = cur
        glyph = self.sb_glyph.get()
        if glyph == BUILD_GLYPHS[0]:
            meta.pop("glyph", None)
        else:
            meta["glyph"] = glyph
        self.write_build_meta(path, meta)
        self.update_build_views()

    def pick_build_image(self):
        if not PIL_OK:
            messagebox.showinfo("Сборка", "Для своей картинки нужен пакет Pillow: pip install Pillow")
            return
        cur = self.require_build()
        if not cur:
            return
        name, path, meta = cur
        src = filedialog.askopenfilename(
            parent=self.root, title="Картинка для значка сборки",
            filetypes=[("Картинки", "*.png *.jpg *.jpeg *.bmp *.gif *.webp *.ico"), ("Все файлы", "*.*")])
        if not src:
            return
        try:
            img = Image.open(src).convert("RGBA")
            w, h = img.size
            m = min(w, h)
            img = img.crop(((w - m) // 2, (h - m) // 2, (w - m) // 2 + m, (h - m) // 2 + m))
            resample = getattr(getattr(Image, "Resampling", Image), "LANCZOS")
            img.resize((128, 128), resample).save(os.path.join(path, "build_icon.png"))
        except Exception as e:
            messagebox.showerror("Сборка", f"Не удалось открыть картинку:\n{e}")
            return
        meta["icon"] = "build_icon.png"
        self.write_build_meta(path, meta)
        self.update_build_views()

    def reset_build_icon(self):
        cur = self.require_build()
        if not cur:
            return
        name, path, meta = cur
        icon = meta.get("icon")
        for key in ("color", "glyph", "icon"):
            meta.pop(key, None)
        self.write_build_meta(path, meta)
        if icon:
            try:
                os.remove(os.path.join(path, str(icon)))
            except OSError:
                pass
        self.update_build_views()

    def on_sb_ram_toggle(self):
        if self.sb_loading:
            return
        cur = self.require_build()
        if not cur:
            self.sb_ram_on.set(False)
            return
        name, path, meta = cur
        if self.sb_ram_on.get():
            meta["ram"] = int(self.sb_ram_var.get())
        else:
            meta.pop("ram", None)
        self.write_build_meta(path, meta)
        self.refresh_sb_ram_label()

    def refresh_sb_ram_label(self):
        try:
            on = bool(self.sb_ram_on.get())
            self.sb_ram_text.config(text=f"{int(self.sb_ram_var.get())} ГБ" if on else "общая")
        except Exception:
            pass

    def on_sb_ram_change(self, *args):
        """Ползунок ОЗУ сборки: сдвинули, значит у сборки своя ОЗУ (и она сразу сохраняется)."""
        if self.sb_loading:
            self.refresh_sb_ram_label()
            return
        try:
            name, path, meta = self.current_build()
            if path:
                self.sb_ram_on.set(True)
                meta["ram"] = int(self.sb_ram_var.get())
                self.write_build_meta(path, meta)
        except Exception as e:
            print(f"[WARN] Не удалось сохранить ОЗУ сборки: {e}")
        self.refresh_sb_ram_label()

    # ------------------------------------------------- фоновые задачи со сборками
    def begin_task(self, text):
        self.running = True
        self.task_busy = True
        self.play_button.config(state="disabled")
        self.update_status(text, WARN)

    def end_task(self):
        self.running = False
        self.task_busy = False
        self.play_button.config(state="normal")

    # --------------------------------------------------------- экспорт / импорт ZIP
    def export_build(self):
        """Упаковывает выбранную сборку в один ZIP: моды, конфиги, настройки (миры по желанию)."""
        cur = self.require_build()
        if not cur:
            return
        if self.running:
            messagebox.showinfo("Экспорт", "Дождитесь конца загрузки или закройте игру.")
            return
        name, path, meta = cur
        target = filedialog.asksaveasfilename(
            parent=self.root, title="Экспорт сборки", defaultextension=".zip",
            initialfile=f"{slugify(name) or 'build'}.zip", filetypes=[("ZIP-архив", "*.zip")])
        if not target:
            return
        target = os.path.normpath(target)
        if not target.lower().endswith(".zip"):
            target += ".zip"
        if self._inside(target, path):
            messagebox.showerror("Экспорт", "Сохраните архив вне папки самой сборки.")
            return
        with_saves = False
        if os.path.isdir(os.path.join(path, "saves")):
            with_saves = messagebox.askyesno(
                "Экспорт сборки",
                "Добавить в архив миры (папка saves)?\n\nАрхив может стать очень большим. Если нажать «Нет», "
                "в нём будут моды, конфиги, ресурспаки и настройки.")
        self.begin_task(f"📤 Экспортирую «{name}»…")
        threading.Thread(target=self.export_worker, args=(name, path, target, with_saves), daemon=True).start()

    def export_worker(self, name, path, target, with_saves):
        skip = set(EXPORT_SKIP_DIRS)
        if not with_saves:
            skip.add("saves")
        files = []
        for root_dir, dirs, names in os.walk(path):
            if os.path.normcase(root_dir) == os.path.normcase(path):
                dirs[:] = [d for d in dirs if d not in skip]
            for n in names:
                full = os.path.join(root_dir, n)
                if not os.path.islink(full):
                    files.append(full)
        try:
            with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
                for i, full in enumerate(files, 1):
                    zf.write(full, os.path.relpath(full, path).replace(os.sep, "/"))
                    if i % 20 == 0 or i == len(files):
                        self.ui(self.update_status, f"📤 Экспорт «{name}»: {i}/{len(files)}", WARN)
        except Exception as e:
            try:
                os.remove(target)
            except OSError:
                pass
            self.ui(self.finish_export, name, target, str(e))
            return
        self.ui(self.finish_export, name, target, None)

    def finish_export(self, name, target, error):
        self.end_task()
        if error:
            messagebox.showerror("Экспорт", f"Не удалось создать архив:\n{error}")
            self.update_status("❌ Экспорт не удался", ERR)
            return
        size = os.path.getsize(target) / 1048576
        self.update_status(f"✅ Сборка «{name}» сохранена: {target} ({size:.1f} МБ)", OK)
        self.tray_notify(f"✅ Сборка «{name}» экспортирована", True)

    def import_build(self):
        """Создаёт сборку из ZIP, который сделал экспорт (в нём лежит build.json)."""
        if self.running:
            messagebox.showinfo("Импорт", "Дождитесь конца загрузки или закройте игру.")
            return
        src = filedialog.askopenfilename(
            parent=self.root, title="Импорт сборки",
            filetypes=[("ZIP-архив сборки", "*.zip"), ("Все файлы", "*.*")])
        if not src:
            return
        self.begin_task("📥 Импортирую сборку…")
        threading.Thread(target=self.import_worker, args=(src,), daemon=True).start()

    def import_worker(self, src):
        folder = None
        try:
            if not zipfile.is_zipfile(src):
                raise ValueError("Это не ZIP-архив.")
            with zipfile.ZipFile(src) as zf:
                found = sorted((n for n in zf.namelist()
                                if n == "build.json" or (n.count("/") == 1 and n.endswith("/build.json"))), key=len)
                if not found:
                    raise ValueError("В архиве нет build.json: это не сборка Nurst Launcher.")
                prefix = found[0][:-len("build.json")]
                meta = json.loads(zf.read(found[0]).decode("utf-8"))
                if not isinstance(meta, dict) or not str(meta.get("name") or "").strip():
                    raise ValueError("Повреждённый build.json в архиве.")
                meta["version"] = str(meta.get("version") or "").strip()
                if not meta["version"]:
                    raise ValueError("В архиве не указана версия Minecraft.")
                if meta.get("loader") not in LOADERS:
                    meta["loader"] = "Vanilla"
                members = [i for i in zf.infolist()
                           if not i.is_dir() and i.filename.startswith(prefix) and i.filename != found[0]]
                need = sum(i.file_size for i in members)
                free = shutil.disk_usage(self.minecraft_dir).free
                if need > free - 512 * 1048576:
                    raise OSError(f"Недостаточно места: нужно {need // 1048576} МБ, свободно {free // 1048576} МБ.")
                name, slug = self.unique_build(str(meta["name"]).strip())
                meta["name"] = name
                folder = os.path.join(self.minecraft_dir, slug)
                os.makedirs(folder)
                for i, info in enumerate(members, 1):
                    rel = posixpath.normpath(info.filename[len(prefix):].replace("\\", "/"))
                    parts = rel.split("/")
                    dest = os.path.normpath(os.path.join(folder, *parts))
                    if rel.startswith("/") or ".." in parts or ":" in parts[0] or not self._inside(dest, folder):
                        continue                          # подозрительный путь в архиве пропускаем
                    os.makedirs(os.path.dirname(dest), exist_ok=True)
                    with zf.open(info) as source, open(dest, "wb") as out:
                        shutil.copyfileobj(source, out)
                    if i % 20 == 0:
                        self.ui(self.update_status, f"📥 Импорт «{name}»: {i}/{len(members)}", WARN)
            os.makedirs(os.path.join(folder, "mods"), exist_ok=True)
            self.write_build_meta(folder, meta)
        except Exception as e:
            if folder and os.path.isdir(folder):
                shutil.rmtree(folder, ignore_errors=True)
            self.ui(self.finish_import, None, str(e))
            return
        self.ui(self.finish_import, meta["name"], None)

    def finish_import(self, name, error):
        self.end_task()
        if error:
            messagebox.showerror("Импорт", f"Не удалось импортировать сборку:\n{error}")
            self.update_status("❌ Импорт не удался", ERR)
            return
        self.refresh_builds(name)
        self.apply_build()
        self.update_status(f"✅ Сборка «{name}» импортирована", OK)
        self.save_config()

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
        ram = int(self.ram_var.get())
        _, _, build_meta = self.current_build()
        if build_meta and isinstance(build_meta.get("ram"), int) and build_meta["ram"] > 0:
            ram = build_meta["ram"]                      # у сборки своя ОЗУ
        ram = max(1, ram)
        jvm = [f"-Xmx{ram}G", f"-Xms{min(ram, 1)}G"]
        # свои аргументы идут после ОЗУ, поэтому могут её переопределить (-Xmx / -Xms)
        error = jvm_error(self.jvm_var.get())
        if error:
            raise ValueError(error)
        jvm += parse_jvm_args(self.jvm_var.get())

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
            java_path = self.resolve_java(version, callback)
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
            self.ui(self.tray_notify, "✅ Игра запущена!", True)
            self.ui(self.progress.config, value=self.progress["maximum"])

        except Exception as e:
            traceback.print_exc()
            self.ui(self.update_status, f"❌ Ошибка: {e}", ERR)
            self.ui(self.tray_notify, f"❌ Ошибка: {e}", True)
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

    def resolve_java(self, version: str, callback: dict):
        """Своя Java из настроек, а если её нет или она пропала, Java от Mojang под эту версию."""
        custom = str(self.config.get("java_path") or "")
        if custom:
            if os.path.isfile(custom):
                self.ui(self.update_status, f"☕ Java из настроек: {custom}")
                return custom
            self.ui(self.update_status, "⚠ Выбранная Java не найдена, использую Java от Mojang", WARN)
        return self.ensure_java(version, callback)

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
