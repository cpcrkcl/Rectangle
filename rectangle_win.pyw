"""RectangleWin: a small Windows window manager inspired by Rectangle."""

from __future__ import annotations

import argparse
import ctypes
import json
import os
import queue
import sys
import threading
import time
import tkinter as tk
from dataclasses import dataclass
from tkinter import messagebox, ttk
import winreg


APP_NAME = "RectangleWin"
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
CONFIG_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), APP_NAME)
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)


MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008

WM_HOTKEY = 0x0312
WM_QUIT = 0x0012

SW_RESTORE = 9
SW_MAXIMIZE = 3

MONITOR_DEFAULTTONEAREST = 2

SWP_NOZORDER = 0x0004
SWP_SHOWWINDOW = 0x0040


class RECT(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long),
    ]

    @property
    def width(self) -> int:
        return self.right - self.left

    @property
    def height(self) -> int:
        return self.bottom - self.top


class MONITORINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", ctypes.c_ulong),
        ("rcMonitor", RECT),
        ("rcWork", RECT),
        ("dwFlags", ctypes.c_ulong),
    ]


class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


class MSG(ctypes.Structure):
    _fields_ = [
        ("hwnd", ctypes.c_void_p),
        ("message", ctypes.c_uint),
        ("wParam", ctypes.c_size_t),
        ("lParam", ctypes.c_ssize_t),
        ("time", ctypes.c_ulong),
        ("pt", POINT),
    ]


@dataclass(frozen=True)
class ActionDef:
    action: str
    label: str
    default_shortcut: str


@dataclass(frozen=True)
class Hotkey:
    id: int
    name: str
    modifiers: int
    virtual_key: int
    action: str


@dataclass
class AppConfig:
    shortcuts: dict[str, str]


ACTIONS = [
    ActionDef("left_half", "Left half", "Ctrl+Alt+Left"),
    ActionDef("right_half", "Right half", "Ctrl+Alt+Right"),
    ActionDef("maximize", "Maximize", "Ctrl+Alt+Up"),
    ActionDef("center", "Center", "Ctrl+Alt+Down"),
    ActionDef("previous_display", "Previous display", "Ctrl+Alt+Shift+Left"),
    ActionDef("next_display", "Next display", "Ctrl+Alt+Shift+Right"),
    ActionDef("top_half", "Top half", "Ctrl+Alt+Shift+Up"),
    ActionDef("bottom_half", "Bottom half", "Ctrl+Alt+Shift+Down"),
    ActionDef("top_left", "Top left quarter", "Ctrl+Alt+U"),
    ActionDef("top_right", "Top right quarter", "Ctrl+Alt+I"),
    ActionDef("bottom_left", "Bottom left quarter", "Ctrl+Alt+J"),
    ActionDef("bottom_right", "Bottom right quarter", "Ctrl+Alt+K"),
    ActionDef("left_third", "Left third", "Ctrl+Alt+1"),
    ActionDef("center_third", "Center third", "Ctrl+Alt+2"),
    ActionDef("right_third", "Right third", "Ctrl+Alt+3"),
    ActionDef("first_two_thirds", "First two thirds", "Ctrl+Alt+Shift+1"),
    ActionDef("last_two_thirds", "Last two thirds", "Ctrl+Alt+Shift+3"),
    ActionDef("show_panel", "Show control panel", "Ctrl+Alt+Shift+R"),
]

ACTION_BY_ID = {action.action: action for action in ACTIONS}

KEY_NAME_TO_VK = {
    **{chr(code): code for code in range(ord("A"), ord("Z") + 1)},
    **{str(number): ord(str(number)) for number in range(10)},
    **{f"F{number}": 0x6F + number for number in range(1, 25)},
    "Left": 0x25,
    "Up": 0x26,
    "Right": 0x27,
    "Down": 0x28,
    "Space": 0x20,
    "Tab": 0x09,
    "Enter": 0x0D,
    "Escape": 0x1B,
    "Backspace": 0x08,
    "Insert": 0x2D,
    "Delete": 0x2E,
    "Home": 0x24,
    "End": 0x23,
    "PageUp": 0x21,
    "PageDown": 0x22,
    "Minus": 0xBD,
    "Equals": 0xBB,
    "Comma": 0xBC,
    "Period": 0xBE,
    "Slash": 0xBF,
    "Backslash": 0xDC,
    "Semicolon": 0xBA,
    "Quote": 0xDE,
    "LeftBracket": 0xDB,
    "RightBracket": 0xDD,
}

SHORTCUT_KEYS = list(KEY_NAME_TO_VK.keys())


MonitorEnumProc = ctypes.WINFUNCTYPE(
    ctypes.c_bool,
    ctypes.c_void_p,
    ctypes.c_void_p,
    ctypes.POINTER(RECT),
    ctypes.c_void_p,
)

kernel32.GetCurrentThreadId.argtypes = []
kernel32.GetCurrentThreadId.restype = ctypes.c_ulong

user32.GetForegroundWindow.argtypes = []
user32.GetForegroundWindow.restype = ctypes.c_void_p
user32.GetShellWindow.argtypes = []
user32.GetShellWindow.restype = ctypes.c_void_p
user32.IsWindow.argtypes = [ctypes.c_void_p]
user32.IsWindow.restype = ctypes.c_bool
user32.IsWindowVisible.argtypes = [ctypes.c_void_p]
user32.IsWindowVisible.restype = ctypes.c_bool
user32.GetWindowRect.argtypes = [ctypes.c_void_p, ctypes.POINTER(RECT)]
user32.GetWindowRect.restype = ctypes.c_bool
user32.MonitorFromWindow.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
user32.MonitorFromWindow.restype = ctypes.c_void_p
user32.GetMonitorInfoW.argtypes = [ctypes.c_void_p, ctypes.POINTER(MONITORINFO)]
user32.GetMonitorInfoW.restype = ctypes.c_bool
user32.EnumDisplayMonitors.argtypes = [ctypes.c_void_p, ctypes.c_void_p, MonitorEnumProc, ctypes.c_void_p]
user32.EnumDisplayMonitors.restype = ctypes.c_bool
user32.ShowWindow.argtypes = [ctypes.c_void_p, ctypes.c_int]
user32.ShowWindow.restype = ctypes.c_bool
user32.SetWindowPos.argtypes = [
    ctypes.c_void_p,
    ctypes.c_void_p,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_uint,
]
user32.SetWindowPos.restype = ctypes.c_bool
user32.RegisterHotKey.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_uint, ctypes.c_uint]
user32.RegisterHotKey.restype = ctypes.c_bool
user32.UnregisterHotKey.argtypes = [ctypes.c_void_p, ctypes.c_int]
user32.UnregisterHotKey.restype = ctypes.c_bool
user32.GetMessageW.argtypes = [ctypes.POINTER(MSG), ctypes.c_void_p, ctypes.c_uint, ctypes.c_uint]
user32.GetMessageW.restype = ctypes.c_int
user32.PostThreadMessageW.argtypes = [ctypes.c_ulong, ctypes.c_uint, ctypes.c_size_t, ctypes.c_ssize_t]
user32.PostThreadMessageW.restype = ctypes.c_bool


def _last_error() -> int:
    return ctypes.get_last_error()


def _quote(value: str) -> str:
    return f'"{value}"'


def default_shortcuts() -> dict[str, str]:
    return {action.action: action.default_shortcut for action in ACTIONS}


def load_config() -> AppConfig:
    shortcuts = default_shortcuts()
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as config_file:
            data = json.load(config_file)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return AppConfig(shortcuts=shortcuts)

    saved = data.get("shortcuts", {})
    if isinstance(saved, dict):
        for action, shortcut in saved.items():
            if action in shortcuts and isinstance(shortcut, str):
                shortcuts[action] = normalize_shortcut_text(shortcut)
    return AppConfig(shortcuts=shortcuts)


def save_config(config: AppConfig) -> None:
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as config_file:
        json.dump({"shortcuts": config.shortcuts}, config_file, indent=2)


def normalize_shortcut_text(shortcut: str) -> str:
    shortcut = shortcut.strip()
    if not shortcut:
        return ""
    parsed = parse_shortcut(shortcut)
    return format_shortcut(*parsed) if parsed else shortcut


def parse_shortcut(shortcut: str) -> tuple[int, int, str] | None:
    parts = [part.strip() for part in shortcut.split("+") if part.strip()]
    if not parts:
        return None

    modifiers = 0
    key_parts: list[str] = []
    for part in parts:
        normalized = part.lower()
        if normalized in {"ctrl", "control"}:
            modifiers |= MOD_CONTROL
        elif normalized == "alt":
            modifiers |= MOD_ALT
        elif normalized == "shift":
            modifiers |= MOD_SHIFT
        elif normalized in {"win", "windows", "super"}:
            modifiers |= MOD_WIN
        else:
            key_parts.append(part)

    if len(key_parts) != 1:
        return None

    key = normalize_key_name(key_parts[0])
    virtual_key = KEY_NAME_TO_VK.get(key)
    if virtual_key is None:
        return None
    return modifiers, virtual_key, key


def normalize_key_name(key: str) -> str:
    lookup = {
        "pgup": "PageUp",
        "page up": "PageUp",
        "pgdn": "PageDown",
        "page down": "PageDown",
        "esc": "Escape",
        "spacebar": "Space",
        "return": "Enter",
        "-": "Minus",
        "=": "Equals",
        ",": "Comma",
        ".": "Period",
        "/": "Slash",
        "\\": "Backslash",
        ";": "Semicolon",
        "'": "Quote",
        "[": "LeftBracket",
        "]": "RightBracket",
    }
    stripped = key.strip()
    if len(stripped) == 1 and stripped.isalpha():
        return stripped.upper()
    if len(stripped) == 1 and stripped.isdigit():
        return stripped
    return lookup.get(stripped.lower(), stripped[:1].upper() + stripped[1:])


def format_shortcut(modifiers: int, _virtual_key: int, key: str) -> str:
    parts: list[str] = []
    if modifiers & MOD_CONTROL:
        parts.append("Ctrl")
    if modifiers & MOD_ALT:
        parts.append("Alt")
    if modifiers & MOD_SHIFT:
        parts.append("Shift")
    if modifiers & MOD_WIN:
        parts.append("Win")
    parts.append(key)
    return "+".join(parts)


def config_to_hotkeys(config: AppConfig) -> tuple[list[Hotkey], dict[str, str]]:
    hotkeys: list[Hotkey] = []
    invalid: dict[str, str] = {}
    for index, action in enumerate(ACTIONS, start=101):
        shortcut = config.shortcuts.get(action.action, "")
        if not shortcut:
            continue
        parsed = parse_shortcut(shortcut)
        if parsed is None:
            invalid[action.action] = shortcut
            continue
        modifiers, virtual_key, key = parsed
        hotkeys.append(Hotkey(index, format_shortcut(modifiers, virtual_key, key), modifiers, virtual_key, action.action))
    return hotkeys, invalid


def app_command(minimized: bool = True) -> str:
    exe = sys.executable
    folder = os.path.dirname(exe)
    pythonw = os.path.join(folder, "pythonw.exe")
    if os.path.exists(pythonw):
        exe = pythonw

    script = os.path.abspath(__file__)
    args = [_quote(exe), _quote(script)]
    if minimized:
        args.append("--minimized")
    return " ".join(args)


def install_startup() -> str:
    command = app_command(minimized=True)
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
        winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, command)
    return command


def remove_startup() -> bool:
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
        try:
            winreg.DeleteValue(key, APP_NAME)
            return True
        except FileNotFoundError:
            return False


def startup_command() -> str | None:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_READ) as key:
            return winreg.QueryValueEx(key, APP_NAME)[0]
    except FileNotFoundError:
        return None


def is_window_manageable(hwnd: int) -> bool:
    if not hwnd or not user32.IsWindow(hwnd) or not user32.IsWindowVisible(hwnd):
        return False
    if user32.GetShellWindow() == hwnd:
        return False
    return True


def foreground_window() -> int | None:
    hwnd = user32.GetForegroundWindow()
    return hwnd if is_window_manageable(hwnd) else None


def window_rect(hwnd: int) -> RECT:
    rect = RECT()
    if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
        raise OSError(_last_error(), "GetWindowRect failed")
    return rect


def monitor_info_for_window(hwnd: int) -> MONITORINFO:
    monitor = user32.MonitorFromWindow(hwnd, MONITOR_DEFAULTTONEAREST)
    info = MONITORINFO()
    info.cbSize = ctypes.sizeof(MONITORINFO)
    if not user32.GetMonitorInfoW(monitor, ctypes.byref(info)):
        raise OSError(_last_error(), "GetMonitorInfoW failed")
    return info


def enum_work_areas() -> list[RECT]:
    monitors: list[RECT] = []

    def callback(hmonitor, _hdc, _rect, _data):
        info = MONITORINFO()
        info.cbSize = ctypes.sizeof(MONITORINFO)
        if user32.GetMonitorInfoW(hmonitor, ctypes.byref(info)):
            monitors.append(info.rcWork)
        return True

    user32.EnumDisplayMonitors(None, None, MonitorEnumProc(callback), None)
    monitors.sort(key=lambda rect: (rect.left, rect.top))
    return monitors


def active_work_area(hwnd: int) -> RECT:
    return monitor_info_for_window(hwnd).rcWork


def set_bounds(hwnd: int, left: int, top: int, width: int, height: int) -> None:
    user32.ShowWindow(hwnd, SW_RESTORE)
    time.sleep(0.025)
    ok = user32.SetWindowPos(
        hwnd,
        None,
        int(left),
        int(top),
        int(width),
        int(height),
        SWP_NOZORDER | SWP_SHOWWINDOW,
    )
    if not ok:
        raise OSError(_last_error(), "SetWindowPos failed")


def apply_layout(action: str) -> None:
    hwnd = foreground_window()
    if hwnd is None:
        return

    work = active_work_area(hwnd)
    half_width = work.width // 2
    half_height = work.height // 2
    third_width = work.width // 3
    two_thirds = third_width * 2

    layouts = {
        "left_half": (work.left, work.top, half_width, work.height),
        "right_half": (work.left + half_width, work.top, work.width - half_width, work.height),
        "top_half": (work.left, work.top, work.width, half_height),
        "bottom_half": (work.left, work.top + half_height, work.width, work.height - half_height),
        "top_left": (work.left, work.top, half_width, half_height),
        "top_right": (work.left + half_width, work.top, work.width - half_width, half_height),
        "bottom_left": (work.left, work.top + half_height, half_width, work.height - half_height),
        "bottom_right": (
            work.left + half_width,
            work.top + half_height,
            work.width - half_width,
            work.height - half_height,
        ),
        "left_third": (work.left, work.top, third_width, work.height),
        "center_third": (work.left + third_width, work.top, third_width, work.height),
        "right_third": (work.left + two_thirds, work.top, work.width - two_thirds, work.height),
        "first_two_thirds": (work.left, work.top, two_thirds, work.height),
        "last_two_thirds": (work.left + third_width, work.top, work.width - third_width, work.height),
    }

    if action == "maximize":
        user32.ShowWindow(hwnd, SW_MAXIMIZE)
    elif action == "center":
        width = int(work.width * 0.72)
        height = int(work.height * 0.78)
        left = work.left + ((work.width - width) // 2)
        top = work.top + ((work.height - height) // 2)
        set_bounds(hwnd, left, top, width, height)
    elif action in {"next_display", "previous_display"}:
        move_to_adjacent_display(hwnd, direction=1 if action == "next_display" else -1)
    elif action in layouts:
        set_bounds(hwnd, *layouts[action])


def move_to_adjacent_display(hwnd: int, direction: int) -> None:
    monitors = enum_work_areas()
    if len(monitors) < 2:
        return

    current = active_work_area(hwnd)
    current_index = 0
    for index, monitor in enumerate(monitors):
        if (
            monitor.left == current.left
            and monitor.top == current.top
            and monitor.right == current.right
            and monitor.bottom == current.bottom
        ):
            current_index = index
            break

    target = monitors[(current_index + direction) % len(monitors)]
    rect = window_rect(hwnd)
    rel_left = (rect.left - current.left) / max(current.width, 1)
    rel_top = (rect.top - current.top) / max(current.height, 1)
    rel_width = rect.width / max(current.width, 1)
    rel_height = rect.height / max(current.height, 1)

    set_bounds(
        hwnd,
        target.left + int(target.width * rel_left),
        target.top + int(target.height * rel_top),
        max(120, int(target.width * rel_width)),
        max(80, int(target.height * rel_height)),
    )


class HotkeyThread(threading.Thread):
    def __init__(self, hotkeys: list[Hotkey], callback, log):
        super().__init__(daemon=True)
        self.hotkeys = hotkeys
        self.hotkey_by_id = {hotkey.id: hotkey for hotkey in hotkeys}
        self.callback = callback
        self.log = log
        self.thread_id = 0
        self.ready = threading.Event()
        self.registered: set[str] = set()
        self.failed: dict[str, str] = {}

    def run(self) -> None:
        self.thread_id = kernel32.GetCurrentThreadId()
        for hotkey in self.hotkeys:
            ok = user32.RegisterHotKey(None, hotkey.id, hotkey.modifiers, hotkey.virtual_key)
            if ok:
                self.registered.add(hotkey.action)
            else:
                self.failed[hotkey.action] = hotkey.name
                self.log(f"Shortcut unavailable: {hotkey.name} ({ACTION_BY_ID[hotkey.action].label})")
        self.ready.set()

        msg = MSG()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
            if msg.message == WM_HOTKEY:
                hotkey = self.hotkey_by_id.get(int(msg.wParam))
                if hotkey is not None:
                    self.callback(hotkey.action, hotkey.name)

        for hotkey in self.hotkeys:
            if hotkey.action in self.registered:
                user32.UnregisterHotKey(None, hotkey.id)

    def stop(self) -> None:
        if self.thread_id:
            user32.PostThreadMessageW(self.thread_id, WM_QUIT, 0, 0)


class RectangleWinApp:
    def __init__(self, minimized: bool = False):
        self.root = tk.Tk()
        self.root.title(APP_NAME)
        self.root.geometry("760x660")
        self.root.minsize(620, 480)
        self.root.protocol("WM_DELETE_WINDOW", self.hide)

        self.ui_queue: queue.Queue = queue.Queue()
        self.config = load_config()
        self.invalid_shortcuts: dict[str, str] = {}
        self.hotkeys: HotkeyThread | None = None
        self.tree: ttk.Treeview | None = None
        self.log_text: tk.Text | None = None

        self.status = tk.StringVar(value="Starting shortcuts...")
        self.startup_status = tk.StringVar(value=self._startup_label())
        self.config_status = tk.StringVar(value=f"Settings: {CONFIG_PATH}")

        self._build_ui()
        self.start_hotkeys()
        self.root.after(50, self.drain_queue)
        self.root.after(250, self.refresh_status)

        if minimized:
            self.root.after(100, self.hide)

    def _build_ui(self) -> None:
        self.root.configure(bg="#f6f7f8")
        style = ttk.Style()
        style.configure("TFrame", background="#f6f7f8")
        style.configure("TLabel", background="#f6f7f8", font=("Segoe UI", 10))
        style.configure("Header.TLabel", background="#f6f7f8", font=("Segoe UI", 18, "bold"))
        style.configure("Status.TLabel", background="#f6f7f8", font=("Segoe UI", 10, "bold"))

        frame = ttk.Frame(self.root, padding=18)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="RectangleWin", style="Header.TLabel").pack(anchor="w")
        ttk.Label(frame, textvariable=self.status, style="Status.TLabel").pack(anchor="w", pady=(4, 8))
        ttk.Label(frame, textvariable=self.startup_status).pack(anchor="w")
        ttk.Label(frame, textvariable=self.config_status).pack(anchor="w", pady=(0, 12))

        actions = ttk.Frame(frame)
        actions.pack(fill="x", pady=(0, 12))
        ttk.Button(actions, text="Install Startup", command=self.install_startup_from_ui).pack(side="left")
        ttk.Button(actions, text="Remove Startup", command=self.remove_startup_from_ui).pack(side="left", padx=8)
        ttk.Button(actions, text="Restore Defaults", command=self.restore_defaults).pack(side="left")
        ttk.Button(actions, text="Hide", command=self.hide).pack(side="right")
        ttk.Button(actions, text="Quit", command=self.quit).pack(side="right", padx=8)

        table_frame = ttk.Frame(frame)
        table_frame.pack(fill="both", expand=True, pady=(0, 10))
        columns = ("action", "shortcut", "status")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="browse", height=14)
        self.tree.heading("action", text="Command")
        self.tree.heading("shortcut", text="Shortcut")
        self.tree.heading("status", text="Status")
        self.tree.column("action", width=220, anchor="w")
        self.tree.column("shortcut", width=190, anchor="w")
        self.tree.column("status", width=160, anchor="w")
        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.tree.bind("<Double-1>", lambda _event: self.change_selected_shortcut())

        shortcut_actions = ttk.Frame(frame)
        shortcut_actions.pack(fill="x", pady=(0, 12))
        ttk.Button(shortcut_actions, text="Change Selected", command=self.change_selected_shortcut).pack(side="left")
        ttk.Button(shortcut_actions, text="Disable Selected", command=self.disable_selected_shortcut).pack(side="left", padx=8)
        ttk.Button(shortcut_actions, text="Apply Current Settings", command=self.apply_shortcuts).pack(side="left")

        self.log_text = tk.Text(frame, height=7, wrap="word", relief="solid", borderwidth=1)
        self.log_text.pack(fill="x")
        self.rebuild_tree()
        self.log("Ready.")

    def _startup_label(self) -> str:
        command = startup_command()
        if command:
            return f"Startup is enabled: {command}"
        return "Startup is not enabled."

    def start_hotkeys(self) -> None:
        if self.hotkeys is not None:
            self.hotkeys.stop()
            self.hotkeys.join(timeout=1)

        hotkeys, invalid = config_to_hotkeys(self.config)
        self.invalid_shortcuts = invalid
        self.hotkeys = HotkeyThread(hotkeys, self.queue_hotkey, self.queue_log)
        self.hotkeys.start()
        if invalid:
            for action, shortcut in invalid.items():
                self.log(f"Invalid shortcut ignored: {shortcut} ({ACTION_BY_ID[action].label})")

    def apply_shortcuts(self) -> None:
        save_config(self.config)
        self.start_hotkeys()
        self.refresh_status()
        self.log("Shortcuts saved and reloaded.")

    def refresh_status(self) -> None:
        if self.hotkeys and self.hotkeys.ready.is_set():
            registered = len(self.hotkeys.registered)
            total = len(self.hotkeys.hotkeys)
            self.status.set(f"Running. {registered} of {total} enabled shortcut(s) registered.")
            self.rebuild_tree()
            return
        self.root.after(250, self.refresh_status)

    def drain_queue(self) -> None:
        while True:
            try:
                item = self.ui_queue.get_nowait()
            except queue.Empty:
                break
            kind = item[0]
            if kind == "log":
                self.log(item[1])
            elif kind == "hotkey":
                self.handle_hotkey(item[1], item[2])
        self.root.after(50, self.drain_queue)

    def queue_log(self, text: str) -> None:
        self.ui_queue.put(("log", text))

    def queue_hotkey(self, action: str, name: str) -> None:
        self.ui_queue.put(("hotkey", action, name))

    def handle_hotkey(self, action: str, name: str) -> None:
        if action == "show_panel":
            self.show()
            return
        try:
            apply_layout(action)
            self.log(f"{name}: applied {ACTION_BY_ID[action].label}")
        except Exception as exc:
            self.log(f"{name}: {exc}")

    def rebuild_tree(self) -> None:
        if self.tree is None:
            return
        selected = self.selected_action()
        self.tree.delete(*self.tree.get_children())
        for action in ACTIONS:
            shortcut = self.config.shortcuts.get(action.action, "")
            status = "Disabled"
            if action.action in self.invalid_shortcuts:
                status = "Invalid"
            elif self.hotkeys and self.hotkeys.ready.is_set():
                if action.action in self.hotkeys.registered:
                    status = "Registered"
                elif shortcut:
                    status = "Unavailable"
            elif shortcut:
                status = "Pending"

            self.tree.insert("", "end", iid=action.action, values=(action.label, shortcut or "-", status))
        if selected and self.tree.exists(selected):
            self.tree.selection_set(selected)

    def selected_action(self) -> str | None:
        if self.tree is None:
            return None
        selection = self.tree.selection()
        return selection[0] if selection else None

    def change_selected_shortcut(self) -> None:
        action = self.selected_action()
        if not action:
            messagebox.showinfo(APP_NAME, "Select a command first.")
            return
        self.open_shortcut_editor(action)

    def disable_selected_shortcut(self) -> None:
        action = self.selected_action()
        if not action:
            messagebox.showinfo(APP_NAME, "Select a command first.")
            return
        self.config.shortcuts[action] = ""
        self.apply_shortcuts()

    def restore_defaults(self) -> None:
        if not messagebox.askyesno(APP_NAME, "Restore all shortcuts to their defaults?"):
            return
        self.config.shortcuts = default_shortcuts()
        self.apply_shortcuts()

    def open_shortcut_editor(self, action: str) -> None:
        action_def = ACTION_BY_ID[action]
        current = self.config.shortcuts.get(action, "")
        parsed = parse_shortcut(current) if current else None
        current_modifiers = parsed[0] if parsed else 0
        current_key = parsed[2] if parsed else "R"

        dialog = tk.Toplevel(self.root)
        dialog.title(f"Change {action_def.label}")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()

        frame = ttk.Frame(dialog, padding=18)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text=action_def.label, style="Status.TLabel").pack(anchor="w", pady=(0, 12))

        ctrl_var = tk.BooleanVar(value=bool(current_modifiers & MOD_CONTROL))
        alt_var = tk.BooleanVar(value=bool(current_modifiers & MOD_ALT))
        shift_var = tk.BooleanVar(value=bool(current_modifiers & MOD_SHIFT))
        win_var = tk.BooleanVar(value=bool(current_modifiers & MOD_WIN))
        key_var = tk.StringVar(value=current_key if current_key in SHORTCUT_KEYS else "R")

        mods = ttk.Frame(frame)
        mods.pack(fill="x", pady=(0, 12))
        ttk.Checkbutton(mods, text="Ctrl", variable=ctrl_var).pack(side="left")
        ttk.Checkbutton(mods, text="Alt", variable=alt_var).pack(side="left", padx=8)
        ttk.Checkbutton(mods, text="Shift", variable=shift_var).pack(side="left")
        ttk.Checkbutton(mods, text="Win", variable=win_var).pack(side="left", padx=8)

        key_row = ttk.Frame(frame)
        key_row.pack(fill="x", pady=(0, 14))
        ttk.Label(key_row, text="Key", width=8).pack(side="left")
        key_box = ttk.Combobox(key_row, textvariable=key_var, values=SHORTCUT_KEYS, state="readonly", width=20)
        key_box.pack(side="left")

        preview = tk.StringVar()

        def selected_shortcut() -> str:
            modifiers = 0
            if ctrl_var.get():
                modifiers |= MOD_CONTROL
            if alt_var.get():
                modifiers |= MOD_ALT
            if shift_var.get():
                modifiers |= MOD_SHIFT
            if win_var.get():
                modifiers |= MOD_WIN
            key = key_var.get()
            return format_shortcut(modifiers, KEY_NAME_TO_VK[key], key)

        def update_preview(*_args) -> None:
            preview.set(f"Shortcut: {selected_shortcut()}")

        for var in (ctrl_var, alt_var, shift_var, win_var, key_var):
            var.trace_add("write", update_preview)
        ttk.Label(frame, textvariable=preview).pack(anchor="w", pady=(0, 14))

        buttons = ttk.Frame(frame)
        buttons.pack(fill="x")

        def save() -> None:
            shortcut = selected_shortcut()
            self.config.shortcuts[action] = shortcut
            dialog.destroy()
            self.apply_shortcuts()

        def clear() -> None:
            self.config.shortcuts[action] = ""
            dialog.destroy()
            self.apply_shortcuts()

        ttk.Button(buttons, text="Save", command=save).pack(side="left")
        ttk.Button(buttons, text="Disable", command=clear).pack(side="left", padx=8)
        ttk.Button(buttons, text="Cancel", command=dialog.destroy).pack(side="right")

        update_preview()
        key_box.focus_set()
        dialog.wait_window()

    def install_startup_from_ui(self) -> None:
        command = install_startup()
        self.startup_status.set(self._startup_label())
        self.log(f"Startup installed: {command}")

    def remove_startup_from_ui(self) -> None:
        removed = remove_startup()
        self.startup_status.set(self._startup_label())
        self.log("Startup removed." if removed else "Startup was already disabled.")

    def log(self, text: str) -> None:
        if self.log_text is None:
            return
        self.log_text.configure(state="normal")
        self.log_text.insert("end", text + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def show(self) -> None:
        self.root.deiconify()
        self.root.state("normal")
        self.root.lift()
        self.root.focus_force()

    def hide(self) -> None:
        self.root.withdraw()

    def quit(self) -> None:
        if self.hotkeys is not None:
            self.hotkeys.stop()
        self.root.after(100, self.root.destroy)

    def run(self) -> None:
        self.root.mainloop()


def run_self_test() -> None:
    config = load_config()
    hotkeys, invalid = config_to_hotkeys(config)
    assert ACTION_BY_ID["show_panel"].default_shortcut == "Ctrl+Alt+Shift+R"
    assert not invalid
    assert len(hotkeys) == len([shortcut for shortcut in config.shortcuts.values() if shortcut])
    for shortcut in default_shortcuts().values():
        assert parse_shortcut(shortcut) is not None
    print(f"{APP_NAME} self-test passed with {len(hotkeys)} configured shortcuts.")


def main() -> int:
    parser = argparse.ArgumentParser(description=APP_NAME)
    parser.add_argument("--minimized", action="store_true", help="start with the control panel hidden")
    parser.add_argument("--install-startup", action="store_true", help="install this app for current-user startup")
    parser.add_argument("--remove-startup", action="store_true", help="remove this app from current-user startup")
    parser.add_argument("--self-test", action="store_true", help="run non-interactive checks")
    args = parser.parse_args()

    if args.self_test:
        run_self_test()
        return 0
    if args.install_startup:
        print(install_startup())
        return 0
    if args.remove_startup:
        print("removed" if remove_startup() else "not installed")
        return 0

    app = RectangleWinApp(minimized=args.minimized)
    app.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
