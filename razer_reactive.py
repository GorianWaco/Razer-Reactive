#!/usr/bin/env python3
"""Reactive per-key lighting for OpenRazer keyboards."""

from __future__ import annotations

import argparse
import fcntl
import glob
import grp
import json
import math
import os
import random
import re
import select
import signal
import socket
import struct
import subprocess
import sys
import threading
import time
import tomllib
from dataclasses import dataclass, field, replace
from pathlib import Path

from evdev import InputDevice, ecodes
from openrazer.client import DeviceManager

EVENT_FORMAT = "@llHHI"
EVENT_SIZE = struct.calcsize(EVENT_FORMAT)
EV_KEY = 0x01
KEYD_SOCKET = Path("/var/run/keyd.socket")
KEYD_VIRTUAL_KEYBOARD = "keyd virtual keyboard"
KEYD_GROUP = "keyd"
KEYD_PERMISSION_HELP = (
    "keyd przechwytuje klawiaturę, ale brak dostępu do jego urządzenia. "
    "Uruchom: sudo usermod -aG keyd $USER , wyloguj się i zaloguj ponownie."
)

KEY_MAPPING: dict[str, tuple[int, int]] = {
    "M6": (0, 0),
    "ESC": (0, 1),
    "F1": (0, 3),
    "F2": (0, 4),
    "F3": (0, 5),
    "F4": (0, 6),
    "F5": (0, 7),
    "F6": (0, 8),
    "F7": (0, 9),
    "F8": (0, 10),
    "F9": (0, 11),
    "F10": (0, 12),
    "F11": (0, 13),
    "F12": (0, 14),
    "PRTSCR": (0, 15),
    "SCRLK": (0, 16),
    "PAUSE": (0, 17),
    "LOGO": (0, 20),
    "M1": (1, 0),
    "BACKTICK": (1, 1),
    "1": (1, 2),
    "2": (1, 3),
    "3": (1, 4),
    "4": (1, 5),
    "5": (1, 6),
    "6": (1, 7),
    "7": (1, 8),
    "8": (1, 9),
    "9": (1, 10),
    "0": (1, 11),
    "DASH": (1, 12),
    "EQUALS": (1, 13),
    "BACKSPACE": (1, 14),
    "INS": (1, 15),
    "HOME": (1, 16),
    "PAGEUP": (1, 17),
    "NUMLK": (1, 18),
    "NPFORWARDSLASH": (1, 19),
    "NPASTERISK": (1, 20),
    "NPDASH": (1, 21),
    "M2": (2, 0),
    "TAB": (2, 1),
    "Q": (2, 2),
    "W": (2, 3),
    "E": (2, 4),
    "R": (2, 5),
    "T": (2, 6),
    "Y": (2, 7),
    "U": (2, 8),
    "I": (2, 9),
    "O": (2, 10),
    "P": (2, 11),
    "LEFTSQUAREBRACKET": (2, 12),
    "RIGHTSQUAREBRACKET": (2, 13),
    "DELETE": (2, 15),
    "END": (2, 16),
    "PAGEDOWN": (2, 17),
    "NP7": (2, 18),
    "NP8": (2, 19),
    "NP9": (2, 20),
    "NPPLUS": (2, 21),
    "M3": (3, 0),
    "CAPSLK": (3, 1),
    "A": (3, 2),
    "S": (3, 3),
    "D": (3, 4),
    "F": (3, 5),
    "G": (3, 6),
    "H": (3, 7),
    "J": (3, 8),
    "K": (3, 9),
    "L": (3, 10),
    "SEMICOLON": (3, 11),
    "APOSTROPHE": (3, 12),
    "POUNDSIGN": (3, 13),
    "RETURN": (3, 14),
    "NP4": (3, 18),
    "NP5": (3, 19),
    "NP6": (3, 20),
    "M4": (4, 0),
    "LEFTSHIFT": (4, 1),
    "BACKSLASH": (4, 2),
    "Z": (4, 3),
    "X": (4, 4),
    "C": (4, 5),
    "V": (4, 6),
    "B": (4, 7),
    "N": (4, 8),
    "M": (4, 9),
    "COMMA": (4, 10),
    "PERIOD": (4, 11),
    "FORWARDSLASH": (4, 12),
    "RIGHTSHIFT": (4, 14),
    "UPARROW": (4, 16),
    "NP1": (4, 18),
    "NP2": (4, 19),
    "NP3": (4, 20),
    "ENTER": (4, 21),
    "M5": (5, 0),
    "LEFTCTRL": (5, 1),
    "SUPER": (5, 2),
    "LEFTALT": (5, 3),
    "SPACE": (5, 7),
    "RIGHTALT": (5, 11),
    "FN": (5, 12),
    "CTXMENU": (5, 13),
    "RIGHTCTRL": (5, 14),
    "LEFTARROW": (5, 15),
    "DOWNARROW": (5, 16),
    "RIGHTARROW": (5, 17),
    "NP0": (5, 19),
    "NPPERIOD": (5, 20),
    "MUTE": (0, 3),
    "VOL_DOWN": (0, 4),
    "VOL_UP": (0, 5),
    "MEDIA_BACK": (0, 7),
    "MEDIA_PLAY": (0, 8),
    "MEDIA_FORWARD": (0, 9),
    "BRIGHTNESSDOWN": (0, 13),
    "BRIGHTNESSUP": (0, 14),
}

EVENT_MAPPING: dict[int, str] = {
    1: "ESC",
    2: "1",
    3: "2",
    4: "3",
    5: "4",
    6: "5",
    7: "6",
    8: "7",
    9: "8",
    10: "9",
    11: "0",
    12: "DASH",
    13: "EQUALS",
    14: "BACKSPACE",
    15: "TAB",
    16: "Q",
    17: "W",
    18: "E",
    19: "R",
    20: "T",
    21: "Y",
    22: "U",
    23: "I",
    24: "O",
    25: "P",
    26: "LEFTSQUAREBRACKET",
    27: "RIGHTSQUAREBRACKET",
    28: "RETURN",
    29: "LEFTCTRL",
    30: "A",
    31: "S",
    32: "D",
    33: "F",
    34: "G",
    35: "H",
    36: "J",
    37: "K",
    38: "L",
    39: "SEMICOLON",
    40: "APOSTROPHE",
    41: "BACKTICK",
    42: "LEFTSHIFT",
    43: "POUNDSIGN",
    44: "Z",
    45: "X",
    46: "C",
    47: "V",
    48: "B",
    49: "N",
    50: "M",
    51: "COMMA",
    52: "PERIOD",
    53: "FORWARDSLASH",
    54: "RIGHTSHIFT",
    55: "NPASTERISK",
    56: "LEFTALT",
    57: "SPACE",
    58: "CAPSLK",
    59: "F1",
    60: "F2",
    61: "F3",
    62: "F4",
    63: "F5",
    64: "F6",
    65: "F7",
    66: "F8",
    67: "F9",
    68: "F10",
    69: "NUMLK",
    70: "SCRLK",
    71: "NP7",
    72: "NP8",
    73: "NP9",
    74: "NPDASH",
    75: "NP4",
    76: "NP5",
    77: "NP6",
    78: "NPPLUS",
    79: "NP1",
    80: "NP2",
    81: "NP3",
    82: "NP0",
    83: "NPPERIOD",
    86: "BACKSLASH",
    87: "F11",
    88: "F12",
    96: "ENTER",
    97: "RIGHTCTRL",
    98: "NPFORWARDSLASH",
    99: "PRTSCR",
    100: "RIGHTALT",
    102: "HOME",
    103: "UPARROW",
    104: "PAGEUP",
    105: "LEFTARROW",
    106: "RIGHTARROW",
    107: "END",
    108: "DOWNARROW",
    109: "PAGEDOWN",
    110: "INS",
    111: "DELETE",
    113: "MUTE",
    114: "VOL_DOWN",
    115: "VOL_UP",
    119: "PAUSE",
    125: "SUPER",
    127: "CTXMENU",
    183: "M1",
    184: "M2",
    185: "M3",
    186: "M4",
    187: "M5",
    188: "M6",
    0x2AD: "MACROMODE",
    0x2AC: "GAMEMODE",
    0x2AB: "BRIGHTNESSDOWN",
    0x2AA: "BRIGHTNESSUP",
}

RGB = tuple[int, int, int]
APP_ID = "com.gorian.razer-reactive"
BUNDLED_CONFIG = Path(__file__).with_name("config.toml")
SCRIPT_PATH = Path(__file__).resolve()
BACKGROUND_MODES = (
    "static",
    "breathe",
    "gradient_horizontal",
    "gradient_vertical",
    "gradient_flow",
    "gradient_flow_reverse",
    "diagonal",
    "checkerboard",
    "cycle",
    "rainbow",
    "wave",
    "wave_vertical",
    "wave_flow",
    "pulse_radial",
    "meteor",
    "strobe",
    "blink_alternate",
    "rain",
    "rain_hits",
    "per_key",
)
BACKGROUND_MODE_LABELS = {
    "static": "Stały kolor",
    "breathe": "Pulsowanie",
    "gradient_horizontal": "Gradient poziomy",
    "gradient_vertical": "Gradient pionowy",
    "gradient_flow": "Płynący gradient",
    "gradient_flow_reverse": "Płynący gradient (w lewo)",
    "diagonal": "Gradient po przekątnej",
    "checkerboard": "Szachownica",
    "cycle": "Rotacja odcienia",
    "rainbow": "Tęcza",
    "wave": "Fala pozioma",
    "wave_vertical": "Fala pionowa",
    "wave_flow": "Fala płynąca",
    "pulse_radial": "Puls od środka",
    "meteor": "Meteor",
    "strobe": "Stroboskop",
    "blink_alternate": "Mryganie na przemian",
    "rain": "Deszcz",
    "rain_hits": "Krople na klawisze",
    "per_key": "Własne kolory klawiszy",
}

POSITION_TO_KEY: dict[tuple[int, int], str] = {}
for _key_name, _position in KEY_MAPPING.items():
    POSITION_TO_KEY.setdefault(_position, _key_name)

KEYBOARD_LAYOUTS = ("ansi", "iso")
ANSI_HIDDEN_KEYS = frozenset({"POUNDSIGN"})
ANSI_RETURN_ALIASES = ((3, 13),)
KEY_EFFECT_MODES = tuple(
    mode for mode in BACKGROUND_MODES if mode not in ("per_key", "rain", "rain_hits")
)
KEY_EFFECT_MODE_LABELS = {
    mode: BACKGROUND_MODE_LABELS[mode] for mode in KEY_EFFECT_MODES
}
# Te same efekty co dla pojedynczego klawisza — osobne tryby globalne.
# „ripple” tylko dla naciśnięcia: fala rozchodzi się od klawisza po całej matrycy.
PRESS_MODES = KEY_EFFECT_MODES + ("ripple",)
PRESS_MODE_LABELS = {
    **KEY_EFFECT_MODE_LABELS,
    "ripple": "Fala od klawisza",
}
CUSTOM_KEY_MODES = KEY_EFFECT_MODES
CUSTOM_KEY_MODE_LABELS = KEY_EFFECT_MODE_LABELS
MODES_WITH_COLOR_2 = frozenset({
    "breathe", "gradient_horizontal", "gradient_vertical", "gradient_flow",
    "gradient_flow_reverse", "diagonal", "checkerboard", "cycle", "rainbow",
    "wave", "wave_vertical", "wave_flow",
    "pulse_radial", "meteor", "strobe", "blink_alternate", "rain", "rain_hits", "ripple",
})

KEY_LABELS: dict[str, str] = {
    "ESC": "Esc",
    "BACKTICK": "`",
    "DASH": "-",
    "EQUALS": "=",
    "BACKSPACE": "⌫",
    "TAB": "Tab",
    "CAPSLK": "Caps",
    "RETURN": "Enter",
    "LEFTSHIFT": "Shift",
    "RIGHTSHIFT": "Shift",
    "LEFTCTRL": "Ctrl",
    "RIGHTCTRL": "Ctrl",
    "LEFTALT": "Alt",
    "RIGHTALT": "Alt",
    "SPACE": "Space",
    "BACKSLASH": "\\",
    "POUNDSIGN": "#",
    "SEMICOLON": ";",
    "APOSTROPHE": "'",
    "COMMA": ",",
    "PERIOD": ".",
    "FORWARDSLASH": "/",
    "LEFTSQUAREBRACKET": "[",
    "RIGHTSQUAREBRACKET": "]",
    "UPARROW": "↑",
    "DOWNARROW": "↓",
    "LEFTARROW": "←",
    "RIGHTARROW": "→",
    "SUPER": "Win",
    "CTXMENU": "Menu",
    "PRTSCR": "PrtSc",
    "SCRLK": "ScrLk",
    "PAUSE": "Pause",
    "INS": "Ins",
    "HOME": "Home",
    "END": "End",
    "PAGEUP": "PgUp",
    "PAGEDOWN": "PgDn",
    "DELETE": "Del",
    "NUMLK": "Num",
    "LOGO": "Razer",
    "NPFORWARDSLASH": "/",
    "NPASTERISK": "*",
    "NPDASH": "−",
    "NPPLUS": "+",
    "NPPERIOD": ".",
    "ENTER": "Enter",
    "NP0": "0",
    "NP1": "1",
    "NP2": "2",
    "NP3": "3",
    "NP4": "4",
    "NP5": "5",
    "NP6": "6",
    "NP7": "7",
    "NP8": "8",
    "NP9": "9",
    "FN": "Fn",
}

# GUI-only geometry: (row, col, colspan, rowspan). LED matrix stays in KEY_MAPPING.
# Tuned for full-size Razer (BlackWidow V4 X style) numpad and wide modifiers.
GUI_KEY_GEOMETRY: dict[str, tuple[int, int, int, int]] = {
    "TAB": (2, 1, 1, 1),
    "CAPSLK": (3, 1, 1, 1),
    "LEFTSHIFT": (4, 1, 1, 1),
    "RIGHTSHIFT": (4, 14, 1, 1),
    "SPACE": (5, 4, 7, 1),
    # Numpad: + and Enter are tall; 0 is double-wide (standard layout).
    "NPPLUS": (2, 21, 1, 2),
    "ENTER": (4, 21, 1, 2),
    "NP0": (5, 18, 2, 1),
}


@dataclass
class Config:
    base_color: RGB
    base_color_2: RGB
    press_color: RGB
    press_color_2: RGB
    hold_seconds: float
    fade_seconds: float
    brightness: int
    fps: int
    keyboard_name: str
    background_mode: str
    background_speed: float
    press_mode: str = "static"
    custom_key_mode: str = "static"
    keyboard_layout: str = "ansi"
    ui_language: str = "en"
    key_colors: dict[str, RGB] = field(default_factory=dict)
    key_colors_2: dict[str, RGB] = field(default_factory=dict)
    key_effects: dict[str, str] = field(default_factory=dict)
    caps_lock_indicator: bool = True
    caps_lock_color: RGB = (255, 220, 40)


UI_LANGUAGES = ("en", "pl")


def normalize_ui_language(value: object) -> str:
    lang = str(value).strip().lower()
    return lang if lang in UI_LANGUAGES else "en"


@dataclass
class ActiveKey:
    phase: str
    phase_end: float


@dataclass
class RainStreak:
    col: int
    row: float
    speed: float


@dataclass
class RainHit:
    """Pojedyncza kropla uderzająca w klawisz od góry."""
    row: int
    col: int
    start: float
    duration: float
    intensity: float


@dataclass
class PressRipple:
    """Fala rozchodząca się od naciśniętego klawisza po całej klawiaturze."""
    row: float
    col: float
    start: float
    color_a: RGB
    color_b: RGB


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def clamp_byte(value: float) -> int:
    return int(clamp(value, 0, 255))


def parse_rgb(value: object, fallback: RGB) -> RGB:
    if isinstance(value, (list, tuple)) and len(value) >= 3:
        return (clamp_byte(value[0]), clamp_byte(value[1]), clamp_byte(value[2]))
    return fallback


def parse_color(value: str) -> RGB:
    value = value.strip()
    if value.startswith("#"):
        raw = value[1:]
        if len(raw) != 6:
            raise ValueError(f"Nieprawidłowy kolor hex: {value}")
        return (
            int(raw[0:2], 16),
            int(raw[2:4], 16),
            int(raw[4:6], 16),
        )
    parts = [int(part.strip()) for part in value.split(",")]
    if len(parts) != 3:
        raise ValueError(f"Oczekiwano R,G,B lub #RRGGBB, otrzymano: {value}")
    return tuple(clamp_byte(part) for part in parts)


def rgb_to_hex(color: RGB) -> str:
    return "#{:02x}{:02x}{:02x}".format(*color)


def config_dir() -> Path:
    return Path.home() / ".config" / "razer-reactive"


def default_config_path() -> Path:
    user_config = config_dir() / "config.toml"
    if user_config.exists():
        return user_config
    return BUNDLED_CONFIG


def default_config() -> Config:
    return load_config(BUNDLED_CONFIG)


def load_config(path: Path | None = None) -> Config:
    config_path = path or default_config_path()
    with config_path.open("rb") as handle:
        data = tomllib.load(handle)

    colors = data.get("colors", {})
    timing = data.get("timing", {})
    display = data.get("display", {})
    device = data.get("device", {})

    background = data.get("background", {})

    base = colors.get("base", [0, 40, 80])
    base_2 = colors.get("base_2", [0, 80, 160])
    press = colors.get("press", [255, 120, 0])
    press_2 = colors.get("press_2", [255, 200, 50])
    background_mode = str(background.get("mode", "static")).strip().lower()
    if background_mode not in BACKGROUND_MODES:
        background_mode = "static"

    press_section = data.get("press", {})
    if not isinstance(press_section, dict):
        press_section = {}
    custom_keys = data.get("custom_keys", {})
    if not isinstance(custom_keys, dict):
        custom_keys = {}

    press_mode = str(press_section.get("mode", "static")).strip().lower()
    if press_mode not in PRESS_MODES:
        press_mode = "static"

    custom_key_mode = str(custom_keys.get("mode", "static")).strip().lower()
    if custom_key_mode not in CUSTOM_KEY_MODES:
        custom_key_mode = "static"

    ui_section = data.get("ui", {})
    if not isinstance(ui_section, dict):
        ui_section = {}
    ui_language = normalize_ui_language(ui_section.get("language", "en"))

    indicators = data.get("indicators", {})
    if not isinstance(indicators, dict):
        indicators = {}
    caps_lock_indicator = bool(indicators.get("caps_lock", True))
    caps_lock_raw = indicators.get("caps_lock_color", colors.get("caps_lock", [255, 220, 40]))

    return normalize_config(Config(
        base_color=(clamp_byte(base[0]), clamp_byte(base[1]), clamp_byte(base[2])),
        base_color_2=(clamp_byte(base_2[0]), clamp_byte(base_2[1]), clamp_byte(base_2[2])),
        press_color=(clamp_byte(press[0]), clamp_byte(press[1]), clamp_byte(press[2])),
        press_color_2=(clamp_byte(press_2[0]), clamp_byte(press_2[1]), clamp_byte(press_2[2])),
        hold_seconds=float(timing.get("hold_seconds", 2.0)),
        fade_seconds=float(timing.get("fade_seconds", 1.0)),
        brightness=int(clamp(display.get("brightness", 100), 0, 100)),
        fps=int(clamp(display.get("fps", 30), 1, 120)),
        keyboard_name=str(device.get("keyboard_name", "")).strip(),
        background_mode=background_mode,
        background_speed=float(clamp(background.get("speed", 0.5), 0.05, 5.0)),
        press_mode=press_mode,
        custom_key_mode=custom_key_mode,
        keyboard_layout=normalize_keyboard_layout(device.get("keyboard_layout", "ansi")),
        ui_language=ui_language,
        key_colors=parse_key_colors(data.get("key_colors", {})),
        key_colors_2=parse_key_colors(data.get("key_colors_2", {})),
        key_effects=parse_key_effects(data.get("key_effects", {})),
        caps_lock_indicator=caps_lock_indicator,
        caps_lock_color=parse_rgb(caps_lock_raw, (255, 220, 40)),
    ))


def save_config(config: Config, path: Path | None = None) -> Path:
    config_path = path or (config_dir() / "config.toml")
    config_path.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "[colors]",
        f"base = [{config.base_color[0]}, {config.base_color[1]}, {config.base_color[2]}]",
        f"base_2 = [{config.base_color_2[0]}, {config.base_color_2[1]}, {config.base_color_2[2]}]",
        f"press = [{config.press_color[0]}, {config.press_color[1]}, {config.press_color[2]}]",
        f"press_2 = [{config.press_color_2[0]}, {config.press_color_2[1]}, {config.press_color_2[2]}]",
        "",
        "[background]",
        f'mode = "{config.background_mode}"',
        f"speed = {config.background_speed}",
        "",
        "[press]",
        f'mode = "{config.press_mode}"',
        "",
        "[custom_keys]",
        f'mode = "{config.custom_key_mode}"',
        "",
        "[timing]",
        f"hold_seconds = {config.hold_seconds}",
        f"fade_seconds = {config.fade_seconds}",
        "",
        "[display]",
        f"brightness = {config.brightness}",
        f"fps = {config.fps}",
        "",
        "[device]",
        f'keyboard_name = "{config.keyboard_name}"',
        f'keyboard_layout = "{config.keyboard_layout}"',
        "",
        "[ui]",
        f'language = "{config.ui_language}"',
        "",
        "[indicators]",
        f"caps_lock = {str(config.caps_lock_indicator).lower()}",
        f"caps_lock_color = [{config.caps_lock_color[0]}, {config.caps_lock_color[1]}, {config.caps_lock_color[2]}]",
        "",
    ]
    if config.key_colors:
        lines.append("[key_colors]")
        for name in sorted(config.key_colors):
            color = config.key_colors[name]
            lines.append(f"{name} = [{color[0]}, {color[1]}, {color[2]}]")
        lines.append("")
    if config.key_colors_2:
        lines.append("[key_colors_2]")
        for name in sorted(config.key_colors_2):
            color = config.key_colors_2[name]
            lines.append(f"{name} = [{color[0]}, {color[1]}, {color[2]}]")
        lines.append("")
    if config.key_effects:
        lines.append("[key_effects]")
        for name in sorted(config.key_effects):
            lines.append(f'{name} = "{config.key_effects[name]}"')
        lines.append("")
    config_path.write_text("\n".join(lines), encoding="utf-8")
    return config_path


def profiles_path() -> Path:
    return config_dir() / "profiles.json"


def factory_profiles_path() -> Path:
    return Path(__file__).with_name("factory_profiles.json")


def _read_profiles_file(path: Path) -> dict[str, dict]:
    if not path.exists():
        return {}
    try:
        with path.open(encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return {}
    profiles = data.get("profiles", {})
    return profiles if isinstance(profiles, dict) else {}


def load_factory_profiles() -> dict[str, dict]:
    return _read_profiles_file(factory_profiles_path())


def load_user_profiles() -> dict[str, dict]:
    return _read_profiles_file(profiles_path())


def is_factory_profile(name: str) -> bool:
    return name in load_factory_profiles()


def load_profiles() -> dict[str, dict]:
    """Factory presets plus user profiles. A user save of the same name wins."""
    merged = dict(load_factory_profiles())
    merged.update(load_user_profiles())
    return merged


def save_profiles(profiles: dict[str, dict]) -> Path:
    """Write only user-owned profiles (never overwrite factory JSON)."""
    factory_names = set(load_factory_profiles())
    user_only = {
        name: data
        for name, data in profiles.items()
        if name not in factory_names or name in load_user_profiles()
    }
    path = profiles_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump({"profiles": user_only}, handle, indent=2, ensure_ascii=False)
    return path


def save_user_profiles(profiles: dict[str, dict]) -> Path:
    path = profiles_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump({"profiles": profiles}, handle, indent=2, ensure_ascii=False)
    return path


def config_to_profile(config: Config) -> dict:
    data = config_to_dict(config)
    data.pop("keyboard_name", None)
    return data


def config_from_profile(data: dict, keyboard_name: str = "") -> Config:
    merged = dict(data)
    merged["keyboard_name"] = keyboard_name
    return config_from_dict(merged)


def save_profile(name: str, config: Config) -> Path:
    name = name.strip()
    if not name:
        raise ValueError("Nazwa profilu nie może być pusta.")
    profiles = load_user_profiles()
    profiles[name] = config_to_profile(config)
    return save_user_profiles(profiles)


def delete_profile(name: str) -> str:
    """Delete a user profile.

    Returns:
        deleted  — user profile removed
        restored — user override removed, factory preset remains
        factory  — name is factory-only and cannot be deleted
        missing  — no such profile
    """
    user = load_user_profiles()
    factory = is_factory_profile(name)
    if name in user:
        del user[name]
        save_user_profiles(user)
        return "restored" if factory else "deleted"
    if factory:
        return "factory"
    return "missing"


def get_profile(name: str, keyboard_name: str = "") -> Config | None:
    profiles = load_profiles()
    data = profiles.get(name)
    if not data:
        return None
    return config_from_profile(data, keyboard_name=keyboard_name)


def blend_color(start: RGB, end: RGB, amount: float) -> RGB:
    amount = clamp(amount, 0.0, 1.0)
    return (
        clamp_byte(start[0] + (end[0] - start[0]) * amount),
        clamp_byte(start[1] + (end[1] - start[1]) * amount),
        clamp_byte(start[2] + (end[2] - start[2]) * amount),
    )


def rgb_to_hsv(color: RGB) -> tuple[float, float, float]:
    red, green, blue = color[0] / 255.0, color[1] / 255.0, color[2] / 255.0
    max_c = max(red, green, blue)
    min_c = min(red, green, blue)
    delta = max_c - min_c

    if delta == 0:
        hue = 0.0
    elif max_c == red:
        hue = 60.0 * (((green - blue) / delta) % 6.0)
    elif max_c == green:
        hue = 60.0 * (((blue - red) / delta) + 2.0)
    else:
        hue = 60.0 * (((red - green) / delta) + 4.0)

    saturation = 0.0 if max_c == 0 else delta / max_c
    value = max_c
    return hue, saturation, value


def hsv_to_rgb(hue: float, saturation: float, value: float) -> RGB:
    hue = hue % 360.0
    chroma = value * saturation
    secondary = chroma * (1.0 - abs((hue / 60.0) % 2.0 - 1.0))
    match = value - chroma

    if hue < 60.0:
        red, green, blue = chroma, secondary, 0.0
    elif hue < 120.0:
        red, green, blue = secondary, chroma, 0.0
    elif hue < 180.0:
        red, green, blue = 0.0, chroma, secondary
    elif hue < 240.0:
        red, green, blue = 0.0, secondary, chroma
    elif hue < 300.0:
        red, green, blue = secondary, 0.0, chroma
    else:
        red, green, blue = chroma, 0.0, secondary

    return (
        clamp_byte((red + match) * 255.0),
        clamp_byte((green + match) * 255.0),
        clamp_byte((blue + match) * 255.0),
    )


def apply_effect_mode(
    mode: str,
    row: int,
    col: int,
    rows: int,
    cols: int,
    color_a: RGB,
    color_b: RGB,
    speed: float,
    now: float,
) -> RGB:
    if mode == "static":
        return color_a

    if mode == "breathe":
        pulse = (math.sin(now * speed * math.tau) + 1.0) * 0.5
        return blend_color(color_a, color_b, pulse)

    if mode == "gradient_horizontal":
        amount = col / max(cols - 1, 1)
        return blend_color(color_a, color_b, amount)

    if mode == "gradient_vertical":
        amount = row / max(rows - 1, 1)
        return blend_color(color_a, color_b, amount)

    if mode == "gradient_flow":
        amount = (col / max(cols - 1, 1) + now * speed * 0.35) % 1.0
        return blend_color(color_a, color_b, amount)

    if mode == "gradient_flow_reverse":
        amount = (col / max(cols - 1, 1) - now * speed * 0.35) % 1.0
        return blend_color(color_a, color_b, amount)

    if mode == "diagonal":
        amount = (
            (row / max(rows - 1, 1)) + (col / max(cols - 1, 1))
        ) * 0.5
        return blend_color(color_a, color_b, amount)

    if mode == "checkerboard":
        return color_a if (row + col) % 2 == 0 else color_b

    if mode == "cycle":
        hue, saturation, value = rgb_to_hsv(color_a)
        hue = (hue + now * speed * 90.0) % 360.0
        return hsv_to_rgb(hue, saturation, value)

    if mode == "rainbow":
        hue = (
            (col / max(cols, 1)) * 300.0
            + (row / max(rows, 1)) * 60.0
            + now * speed * 120.0
        ) % 360.0
        _, saturation, value = rgb_to_hsv(color_a)
        return hsv_to_rgb(hue, max(saturation, 0.75), value)

    if mode == "wave":
        phase = (col / max(cols, 1) + now * speed) % 1.0
        amount = (math.sin(phase * math.tau) + 1.0) * 0.5
        return blend_color(color_a, color_b, amount)

    if mode == "wave_vertical":
        phase = (row / max(rows, 1) + now * speed) % 1.0
        amount = (math.sin(phase * math.tau) + 1.0) * 0.5
        return blend_color(color_a, color_b, amount)

    if mode == "wave_flow":
        phase = ((col / max(cols, 1) + row / max(rows, 1)) * 0.5 + now * speed) % 1.0
        amount = (math.sin(phase * math.tau) + 1.0) * 0.5
        return blend_color(color_a, color_b, amount)

    if mode == "pulse_radial":
        center_row = (rows - 1) / 2.0
        center_col = (cols - 1) / 2.0
        distance = math.hypot(row - center_row, col - center_col)
        max_distance = math.hypot(center_row, center_col) or 1.0
        phase = (distance / max_distance + now * speed) % 1.0
        amount = (math.sin(phase * math.tau) + 1.0) * 0.5
        return blend_color(color_a, color_b, amount)

    if mode == "meteor":
        meteor_pos = (now * speed * 3.0) % (cols + 4) - 2.0
        distance = abs(col - meteor_pos)
        if distance < 1.8:
            amount = 1.0 - distance / 1.8
            return blend_color(color_a, color_b, amount)
        return color_a

    if mode == "strobe":
        return color_a if math.sin(now * speed * math.tau * 6.0) > 0 else color_b

    if mode == "blink_alternate":
        # Sąsiednie klawisze w przeciwnej fazie — szachownica, która się odwraca.
        flip = math.sin(now * speed * math.tau * 3.0) > 0
        even = (row + col) % 2 == 0
        if flip:
            return color_a if even else color_b
        return color_b if even else color_a

    # Fala od naciśnięcia malowana osobno na całej matrycy — sam klawisz świeci kolorem A.
    if mode == "ripple":
        return color_a

    if mode in ("per_key", "rain", "rain_hits"):
        return color_a

    return color_a


def compute_background_color(
    row: int,
    col: int,
    rows: int,
    cols: int,
    config: Config,
    now: float,
) -> RGB:
    key_name = get_key_at_position(row, col, config.keyboard_layout)
    speed = config.background_speed

    # 1) Efekt ustawiony indywidualnie na klawiszu
    if key_name and key_name in config.key_effects:
        mode = config.key_effects[key_name]
        color_a = config.key_colors.get(key_name, config.base_color)
        color_b = config.key_colors_2.get(key_name, config.base_color_2)
        return apply_effect_mode(mode, row, col, rows, cols, color_a, color_b, speed, now)

    # 2) Klawisze z własnym kolorem — osobny tryb globalny
    if key_name and key_name in config.key_colors:
        mode = config.custom_key_mode
        color_a = config.key_colors[key_name]
        color_b = config.key_colors_2.get(key_name, config.base_color_2)
        return apply_effect_mode(mode, row, col, rows, cols, color_a, color_b, speed, now)

    # 3) Reszta klawiatury — tryb tła
    return apply_effect_mode(
        config.background_mode,
        row,
        col,
        rows,
        cols,
        config.base_color,
        config.base_color_2,
        speed,
        now,
    )


def compute_press_color(
    row: int,
    col: int,
    rows: int,
    cols: int,
    config: Config,
    now: float,
) -> RGB:
    """Kolor reakcji na naciśnięcie — własny tryb efektu (niezależny od tła)."""
    return apply_effect_mode(
        config.press_mode,
        row,
        col,
        rows,
        cols,
        config.press_color,
        config.press_color_2,
        config.background_speed,
        now,
    )


def parse_key_colors(raw: object) -> dict[str, RGB]:
    if not isinstance(raw, dict):
        return {}
    colors: dict[str, RGB] = {}
    for name, value in raw.items():
        if not isinstance(value, list) or len(value) < 3:
            continue
        colors[str(name).upper()] = (
            clamp_byte(value[0]),
            clamp_byte(value[1]),
            clamp_byte(value[2]),
        )
    return colors


def key_label(name: str) -> str:
    return KEY_LABELS.get(name, name)


def normalize_keyboard_layout(value: object) -> str:
    layout = str(value).strip().lower()
    return layout if layout in KEYBOARD_LAYOUTS else "ansi"


def get_key_at_position(row: int, col: int, layout: str = "ansi") -> str | None:
    if layout == "ansi" and (row, col) in ANSI_RETURN_ALIASES:
        return "RETURN"
    return POSITION_TO_KEY.get((row, col))


def iter_gui_keys(layout: str = "ansi"):
    """Yield (key_name, row, col, colspan, rowspan) for the keyboard map widget."""
    hidden = ANSI_HIDDEN_KEYS if layout == "ansi" else frozenset()
    # Media aliases share LED cells with F-keys — hide them on the map.
    media_aliases = frozenset({
        "MUTE", "VOL_DOWN", "VOL_UP", "MEDIA_BACK", "MEDIA_PLAY", "MEDIA_FORWARD",
        "BRIGHTNESSDOWN", "BRIGHTNESSUP",
    })
    occupied: set[tuple[int, int]] = set()

    def place(key_name: str, row: int, col: int, colspan: int, rowspan: int):
        for grid_row in range(row, row + rowspan):
            for grid_col in range(col, col + colspan):
                occupied.add((grid_row, grid_col))
        return key_name, row, col, colspan, rowspan

    # Stable visual order: row, then column, then name.
    for key_name in sorted(
        KEY_MAPPING,
        key=lambda name: (*KEY_MAPPING[name], name),
    ):
        if key_name in media_aliases:
            continue

        # ISO-only key: hide on ANSI, but do not block RETURN placement (same cell).
        if key_name in hidden:
            continue

        if key_name in GUI_KEY_GEOMETRY:
            row, col, colspan, rowspan = GUI_KEY_GEOMETRY[key_name]
        else:
            row, col = KEY_MAPPING[key_name]
            colspan, rowspan = 1, 1
            if layout == "ansi" and key_name == "RETURN":
                # Visual Enter spans #/pound cell + Enter LED cell.
                row, col = 3, 13
                colspan = 2

        if any(
            (r, c) in occupied
            for r in range(row, row + rowspan)
            for c in range(col, col + colspan)
        ):
            continue

        yield place(key_name, row, col, colspan, rowspan)


def normalize_config(config: Config) -> Config:
    layout = normalize_keyboard_layout(config.keyboard_layout)
    if layout != "ansi":
        return replace(config, keyboard_layout=layout)

    key_colors = dict(config.key_colors)
    key_colors_2 = dict(config.key_colors_2)
    key_effects = dict(config.key_effects)

    for field_name, target in (
        ("POUNDSIGN", "RETURN"),
    ):
        if field_name in key_colors and target not in key_colors:
            key_colors[target] = key_colors[field_name]
        if field_name in key_colors_2 and target not in key_colors_2:
            key_colors_2[target] = key_colors_2[field_name]
        if field_name in key_effects and target not in key_effects:
            key_effects[target] = key_effects[field_name]
        key_colors.pop(field_name, None)
        key_colors_2.pop(field_name, None)
        key_effects.pop(field_name, None)

    return replace(
        config,
        keyboard_layout=layout,
        key_colors=key_colors,
        key_colors_2=key_colors_2,
        key_effects=key_effects,
    )


def parse_key_effects(raw: object) -> dict[str, str]:
    if not isinstance(raw, dict):
        return {}
    effects: dict[str, str] = {}
    for name, value in raw.items():
        mode = str(value).strip().lower()
        if mode in KEY_EFFECT_MODES:
            effects[str(name).upper()] = mode
    return effects


def config_to_dict(config: Config) -> dict:
    return {
        "base_color": list(config.base_color),
        "base_color_2": list(config.base_color_2),
        "press_color": list(config.press_color),
        "press_color_2": list(config.press_color_2),
        "hold_seconds": config.hold_seconds,
        "fade_seconds": config.fade_seconds,
        "brightness": config.brightness,
        "fps": config.fps,
        "keyboard_name": config.keyboard_name,
        "background_mode": config.background_mode,
        "background_speed": config.background_speed,
        "press_mode": config.press_mode,
        "custom_key_mode": config.custom_key_mode,
        "keyboard_layout": config.keyboard_layout,
        "ui_language": config.ui_language,
        "key_colors": {name: list(color) for name, color in config.key_colors.items()},
        "key_colors_2": {name: list(color) for name, color in config.key_colors_2.items()},
        "key_effects": dict(config.key_effects),
        "caps_lock_indicator": config.caps_lock_indicator,
        "caps_lock_color": list(config.caps_lock_color),
    }


def config_from_dict(data: dict) -> Config:
    background_mode = str(data.get("background_mode", "static")).strip().lower()
    if background_mode not in BACKGROUND_MODES:
        background_mode = "static"

    press_mode = str(data.get("press_mode", "static")).strip().lower()
    if press_mode not in PRESS_MODES:
        press_mode = "static"

    custom_key_mode = str(data.get("custom_key_mode", "static")).strip().lower()
    if custom_key_mode not in CUSTOM_KEY_MODES:
        custom_key_mode = "static"

    return normalize_config(Config(
        base_color=tuple(clamp_byte(value) for value in data.get("base_color", [0, 40, 80])),
        base_color_2=tuple(clamp_byte(value) for value in data.get("base_color_2", [0, 80, 160])),
        press_color=tuple(clamp_byte(value) for value in data.get("press_color", [255, 120, 0])),
        press_color_2=tuple(clamp_byte(value) for value in data.get("press_color_2", [255, 200, 50])),
        hold_seconds=float(data.get("hold_seconds", 2.0)),
        fade_seconds=float(data.get("fade_seconds", 1.0)),
        brightness=int(clamp(data.get("brightness", 100), 0, 100)),
        fps=int(clamp(data.get("fps", 30), 1, 120)),
        keyboard_name=str(data.get("keyboard_name", "")).strip(),
        background_mode=background_mode,
        background_speed=float(clamp(data.get("background_speed", 0.5), 0.05, 5.0)),
        press_mode=press_mode,
        custom_key_mode=custom_key_mode,
        keyboard_layout=normalize_keyboard_layout(data.get("keyboard_layout", "ansi")),
        ui_language=normalize_ui_language(data.get("ui_language", "en")),
        key_colors=parse_key_colors(data.get("key_colors", {})),
        key_colors_2=parse_key_colors(data.get("key_colors_2", {})),
        key_effects=parse_key_effects(data.get("key_effects", {})),
        caps_lock_indicator=bool(data.get("caps_lock_indicator", True)),
        caps_lock_color=parse_rgb(data.get("caps_lock_color", [255, 220, 40]), (255, 220, 40)),
    ))


def daemon_socket_path() -> Path:
    runtime = os.environ.get("XDG_RUNTIME_DIR")
    if runtime:
        return Path(runtime) / "razer-reactive.sock"
    return Path(f"/tmp/razer-reactive-{os.getuid()}.sock")


class DaemonClient:
    """IPC client for the background razer-reactive daemon."""

    def __init__(self, timeout: float = 2.0) -> None:
        self.timeout = timeout

    @property
    def socket_path(self) -> Path:
        return daemon_socket_path()

    def is_available(self) -> bool:
        return self.socket_path.exists()

    def request(self, command: str, **payload) -> dict:
        if not self.is_available():
            raise RuntimeError("Usługa w tle nie działa. Uruchom: razer_reactive.py --daemon")

        message = {"cmd": command, **payload}
        encoded = (json.dumps(message) + "\n").encode("utf-8")

        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as conn:
            conn.settimeout(self.timeout)
            conn.connect(str(self.socket_path))
            conn.sendall(encoded)

            data = b""
            while b"\n" not in data:
                chunk = conn.recv(4096)
                if not chunk:
                    break
                data += chunk

        if not data:
            raise RuntimeError("Brak odpowiedzi od usługi w tle.")

        return json.loads(data.decode("utf-8"))

    def status(self) -> dict:
        return self.request("status")

    def start_lighting(self) -> dict:
        return self.request("start")

    def stop_lighting(self) -> dict:
        return self.request("stop")

    def turn_off_lighting(self) -> dict:
        return self.request("turn_off")

    def reset_config(self) -> dict:
        return self.request("reset_config")

    def get_config(self) -> Config:
        response = self.request("get_config")
        return config_from_dict(response["config"])

    def update_config(self, config: Config) -> dict:
        return self.request("update_config", config=config_to_dict(config))

    def set_config(self, config: Config) -> dict:
        return self.request("set_config", config=config_to_dict(config))

    def reload_config(self) -> dict:
        return self.request("reload")


def find_keyboard(config: Config):
    manager = DeviceManager()
    manager.sync_effects = False

    keyboards = [device for device in manager.devices if device.type == "keyboard"]
    if not keyboards:
        raise RuntimeError("Nie znaleziono klawiatury OpenRazer.")

    if config.keyboard_name:
        matches = [
            device
            for device in keyboards
            if config.keyboard_name.lower() in device.name.lower()
        ]
        if not matches:
            names = ", ".join(device.name for device in keyboards)
            raise RuntimeError(
                f"Nie znaleziono klawiatury pasującej do '{config.keyboard_name}'. "
                f"Dostępne: {names}"
            )
        keyboard = matches[0]
    else:
        keyboard = keyboards[0]

    if keyboard.fx.advanced is None:
        raise RuntimeError(
            f"{keyboard.name} nie obsługuje macierzy LED (custom per-key lighting)."
        )

    return manager, keyboard


def _keyboard_path_needle(keyboard_name: str) -> str:
    return keyboard_name.replace(" ", "_")


def is_keyd_running() -> bool:
    return KEYD_SOCKET.exists()


def user_in_group(group_name: str) -> bool:
    try:
        group_id = grp.getgrnam(group_name).gr_gid
    except KeyError:
        return False
    return group_id in os.getgroups()


def can_access_event(path: str) -> bool:
    try:
        handle = open(path, "rb")
        handle.close()
        return True
    except OSError:
        return False


def can_access_keyd_socket() -> bool:
    return can_access_event(str(KEYD_SOCKET))


def parse_input_devices() -> dict[str, list[str]]:
    devices: dict[str, list[str]] = {}
    proc_path = Path("/proc/bus/input/devices")
    if not proc_path.exists():
        return devices

    for block in proc_path.read_text(encoding="utf-8", errors="replace").split("\n\n"):
        name = None
        handlers: list[str] = []
        for line in block.splitlines():
            if line.startswith('N: Name="'):
                name = line.split('"')[1]
            elif line.startswith("H: Handlers="):
                handlers = line.split()[1:]

        if not name:
            continue

        event_paths = [f"/dev/input/{handler}" for handler in handlers if handler.startswith("event")]
        if event_paths:
            devices[name] = event_paths

    return devices


def find_physical_event_files(keyboard_name: str) -> list[str]:
    search_dir = Path("/dev/input/by-id")
    if not search_dir.exists():
        return []

    needle = _keyboard_path_needle(keyboard_name)
    pattern = re.compile(
        rf".*{re.escape(needle)}(-if\d+)?-event-kbd$",
        re.IGNORECASE,
    )

    paths: list[str] = []
    seen: set[str] = set()
    for entry in sorted(search_dir.iterdir()):
        if not pattern.match(entry.name):
            continue
        real = str(entry.resolve())
        if real in seen:
            continue
        seen.add(real)
        paths.append(str(entry))

    return paths


def find_keyd_virtual_event_files() -> list[str]:
    return parse_input_devices().get(KEYD_VIRTUAL_KEYBOARD, [])


def find_event_files(keyboard_name: str) -> list[str]:
    return find_key_event_sources(keyboard_name)


def find_key_event_sources(keyboard_name: str) -> list[str]:
    paths: list[str] = []
    seen: set[str] = set()

    def add(new_paths: list[str]) -> None:
        for path in new_paths:
            real = str(Path(path).resolve())
            if real in seen:
                continue
            seen.add(real)
            paths.append(path)

    if is_keyd_running():
        add(find_keyd_virtual_event_files())

    add(find_physical_event_files(keyboard_name))
    return paths


def read_caps_lock_led(event_paths: list[str]) -> bool | None:
    """Read Caps Lock LED from evdev. None if no device reports the LED."""
    led_capsl = int(getattr(ecodes, "LED_CAPSL", 1))
    ev_led = getattr(ecodes, "EV_LED", None)
    seen_capable = False
    any_on = False
    for path in event_paths:
        try:
            device = InputDevice(path)
        except (OSError, FileNotFoundError):
            continue
        try:
            capabilities = device.capabilities()
            leds = capabilities.get(ev_led, []) if ev_led is not None else []
            if led_capsl not in leds and not leds:
                continue
            seen_capable = True
            if led_capsl in device.leds():
                any_on = True
        except OSError:
            continue
        finally:
            try:
                device.close()
            except OSError:
                pass
    if not seen_capable:
        return None
    return any_on


def keyd_key_name_to_code(key_name: str) -> int | None:
    normalized = key_name.strip().lower()
    aliases = {
        "ret": "enter",
        "return": "enter",
        "esc": "escape",
        "bspc": "backspace",
        "del": "delete",
        "ins": "insert",
        "pgup": "pageup",
        "pgdn": "pagedown",
        "leftmeta": "leftmeta",
        "rightmeta": "rightmeta",
        "leftalt": "leftalt",
        "rightalt": "rightalt",
        "leftctrl": "leftctrl",
        "rightctrl": "rightctrl",
        "leftshift": "leftshift",
        "rightshift": "rightshift",
    }
    normalized = aliases.get(normalized, normalized)

    for candidate in (normalized, normalized.upper()):
        if hasattr(ecodes, f"KEY_{candidate.upper()}"):
            return int(getattr(ecodes, f"KEY_{candidate.upper()}"))

    return None


def validate_key_input_access(keyboard_name: str) -> None:
    if not is_keyd_running():
        paths = find_physical_event_files(keyboard_name)
        if not paths:
            raise RuntimeError(f"Nie znaleziono urządzenia wejściowego dla {keyboard_name}.")
        inaccessible = [path for path in paths if not can_access_event(path)]
        if inaccessible:
            raise RuntimeError(
                "Brak dostępu do urządzenia klawiatury. Dodaj użytkownika do grupy input: "
                "sudo usermod -aG input $USER"
            )
        return

    if can_access_keyd_socket():
        return

    virtual_paths = find_keyd_virtual_event_files()
    if any(can_access_event(path) for path in virtual_paths):
        return

    if user_in_group(KEYD_GROUP):
        raise RuntimeError(
            "Jesteś w grupie keyd, ale nadal brak dostępu. Wyloguj się i zaloguj ponownie."
        )

    raise RuntimeError(KEYD_PERMISSION_HELP)


def create_key_reader(keyboard_name: str, on_key_press):
    if is_keyd_running() and can_access_keyd_socket():
        return KeydMonitorReader(on_key_press)

    if is_keyd_running():
        virtual_paths = find_keyd_virtual_event_files()
        accessible_virtual = [path for path in virtual_paths if can_access_event(path)]
        if accessible_virtual:
            return RawKeyReader(accessible_virtual, on_key_press)
        validate_key_input_access(keyboard_name)

    physical_paths = find_physical_event_files(keyboard_name)
    if not physical_paths:
        raise RuntimeError(f"Nie znaleziono urządzenia wejściowego dla {keyboard_name}.")

    accessible_physical = [path for path in physical_paths if can_access_event(path)]
    if not accessible_physical:
        raise RuntimeError(
            "Brak dostępu do urządzenia klawiatury. Dodaj użytkownika do grupy input: "
            "sudo usermod -aG input $USER"
        )

    return RawKeyReader(accessible_physical, on_key_press)


class KeydMonitorReader:
    """Reads key presses from the keyd IPC monitor stream."""

    def __init__(self, on_key_press) -> None:
        self._on_key_press = on_key_press
        self._running = False
        self._process: subprocess.Popen[str] | None = None
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._running:
            return

        self._running = True
        self._process = subprocess.Popen(
            ["keyd", "monitor"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
        self._thread = threading.Thread(target=self._loop, name="keyd-monitor", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._process is not None:
            self._process.terminate()
            try:
                self._process.wait(timeout=1.0)
            except subprocess.TimeoutExpired:
                self._process.kill()
            self._process = None
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None

    def _loop(self) -> None:
        if self._process is None or self._process.stdout is None:
            return

        for line in self._process.stdout:
            if not self._running:
                break

            line = line.strip()
            if not line.endswith(" down"):
                continue

            parts = line.split("\t")
            if len(parts) < 3:
                continue

            key_token = parts[2].rsplit(" ", 1)[0]
            key_code = keyd_key_name_to_code(key_token)
            if key_code is not None:
                self._on_key_press(key_code)


class RawKeyReader:
    """Low-level input reader matching the OpenRazer daemon approach."""

    def __init__(self, event_paths: list[str], on_key_press) -> None:
        self._event_paths = event_paths
        self._on_key_press = on_key_press
        self._running = False
        self._handles: list[object] = []
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._running:
            return

        self._handles = []
        for path in self._event_paths:
            handle = open(path, "rb")
            flags = fcntl.fcntl(handle.fileno(), fcntl.F_GETFL)
            fcntl.fcntl(handle.fileno(), fcntl.F_SETFL, flags | os.O_NONBLOCK)
            self._handles.append(handle)

        self._running = True
        self._thread = threading.Thread(target=self._loop, name="raw-key-reader", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        for handle in self._handles:
            try:
                handle.close()
            except OSError:
                pass
        self._handles.clear()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None

    def _loop(self) -> None:
        fd_map = {handle.fileno(): handle for handle in self._handles}
        poll = select.epoll()
        for fd in fd_map:
            poll.register(fd, select.EPOLLIN | select.EPOLLPRI)

        try:
            while self._running:
                for fd, _mask in poll.poll(0.05):
                    handle = fd_map[fd]
                    while self._running:
                        data = handle.read(EVENT_SIZE)
                        if not data:
                            break
                        if len(data) < EVENT_SIZE:
                            continue
                        key_code = self._parse_press(data)
                        if key_code is not None:
                            self._on_key_press(key_code)
        finally:
            poll.close()

    @staticmethod
    def _parse_press(data: bytes) -> int | None:
        _sec, _usec, ev_type, ev_code, ev_value = struct.unpack(EVENT_FORMAT, data)
        if ev_type != EV_KEY or ev_value != 1:
            return None
        return ev_code


class ReactiveLighting:
    def __init__(
        self,
        config: Config,
        manager=None,
        keyboard=None,
    ) -> None:
        self.config = config
        self._running = False
        self._lock = threading.Lock()
        self._active: dict[tuple[int, int], ActiveKey] = {}
        self._recent_presses: dict[tuple[int, int], float] = {}
        self._rain_streaks: list[RainStreak] = []
        self._rain_hits: list[RainHit] = []
        self._rain_last_tick = time.monotonic()
        self._caps_lock_on = False
        self._caps_lock_paths: list[str] = []
        self._caps_lock_last_poll = 0.0
        self._ripples: list[PressRipple] = []
        self._threads: list[threading.Thread] = []
        self._key_reader: RawKeyReader | KeydMonitorReader | None = None
        self._event_files: list[str] = []
        self._input_source = ""

        if manager is None or keyboard is None:
            self.manager, self.keyboard = find_keyboard(config)
        else:
            self.manager = manager
            self.keyboard = keyboard
            self.manager.sync_effects = False

        self.rows = self.keyboard.fx.advanced.rows
        self.cols = self.keyboard.fx.advanced.cols

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def keyboard_name(self) -> str:
        return self.keyboard.name

    @property
    def input_source(self) -> str:
        return self._input_source

    def update_config(self, config: Config, *, reset_state: bool = False) -> None:
        with self._lock:
            self.config = replace(config)
        if self._running:
            self.keyboard.brightness = config.brightness
            if reset_state:
                self.reset_visual_state()

    def reset_visual_state(self) -> None:
        with self._lock:
            self._active.clear()
            self._recent_presses.clear()
            self._rain_streaks.clear()
            self._rain_hits.clear()
            self._ripples.clear()
            self._rain_last_tick = time.monotonic()
        self._prime_matrix()

    def start(self) -> None:
        if self._running:
            return

        if self._threads:
            for thread in self._threads:
                thread.join(timeout=2.0)
            self._threads.clear()

        validate_key_input_access(self.keyboard.name)
        self._event_files = find_key_event_sources(self.keyboard.name)
        self._caps_lock_paths = list(self._event_files)
        led_state = read_caps_lock_led(self._caps_lock_paths)
        if led_state is not None:
            self._caps_lock_on = led_state
        self._caps_lock_last_poll = time.monotonic()

        self.keyboard.brightness = self.config.brightness
        self._prime_matrix()
        self._running = True

        self._key_reader = create_key_reader(self.keyboard.name, self.on_key_code)
        self._input_source = (
            "keyd monitor"
            if isinstance(self._key_reader, KeydMonitorReader)
            else ", ".join(self._key_reader._event_paths)
        )
        self._key_reader.start()

        render_thread = threading.Thread(target=self._render_loop, name="render-loop", daemon=True)
        self._threads = [render_thread]
        render_thread.start()

    def run_blocking(self) -> None:
        self.start()
        print(f"Klawiatura: {self.keyboard.name}")
        print(f"Urządzenia wejściowe: {', '.join(self._event_files)}")
        print(
            "Kolory: baza "
            f"{self.config.base_color} | naciśnięcie {self.config.press_color} | "
            f"czas {self.config.hold_seconds}s | wygaszanie {self.config.fade_seconds}s"
        )
        print("Naciśnij Ctrl+C aby zakończyć.")
        try:
            while self._running:
                time.sleep(0.2)
        finally:
            self.stop()

    def _shutdown_threads(self) -> None:
        if not self._running and not self._threads and self._key_reader is None:
            return

        self._running = False

        if self._key_reader is not None:
            self._key_reader.stop()
            self._key_reader = None

        for thread in self._threads:
            thread.join(timeout=3.0)
        self._threads.clear()

        with self._lock:
            self._active.clear()
            self._recent_presses.clear()
            self._rain_streaks.clear()
            self._rain_hits.clear()
            self._ripples.clear()

    def _tick_rain(self, config: Config, now: float) -> None:
        dt = max(0.0, now - self._rain_last_tick)
        self._rain_last_tick = now
        if dt <= 0.0:
            return

        spawn_chance = config.background_speed * 1.8 * dt
        if random.random() < spawn_chance:
            self._rain_streaks.append(
                RainStreak(
                    col=random.randrange(self.cols),
                    row=-1.0,
                    speed=4.0 + config.background_speed * 6.0,
                )
            )

        active_columns = {streak.col for streak in self._rain_streaks}
        if random.random() < spawn_chance * 0.6:
            free_cols = [col for col in range(self.cols) if col not in active_columns]
            if free_cols:
                self._rain_streaks.append(
                    RainStreak(
                        col=random.choice(free_cols),
                        row=-1.0,
                        speed=4.0 + config.background_speed * 6.0,
                    )
                )

        updated: list[RainStreak] = []
        for streak in self._rain_streaks:
            streak.row += streak.speed * dt
            if streak.row <= self.rows + 2:
                updated.append(streak)
        self._rain_streaks = updated

    def _occupied_key_cells(self, layout: str) -> list[tuple[int, int]]:
        cells = [
            (row, col)
            for row in range(self.rows)
            for col in range(self.cols)
            if get_key_at_position(row, col, layout)
        ]
        if cells:
            return cells
        return [
            (row, col)
            for row in range(self.rows)
            for col in range(self.cols)
        ]

    def _tick_rain_hits(self, config: Config, now: float) -> None:
        dt = max(0.0, now - self._rain_last_tick)
        self._rain_last_tick = now
        if dt <= 0.0:
            return

        cells = self._occupied_key_cells(config.keyboard_layout)
        busy = {(hit.row, hit.col) for hit in self._rain_hits}
        spawn = config.background_speed * 9.0 * dt
        attempts = max(1, int(spawn) + 1)
        for _ in range(attempts):
            if random.random() >= min(1.0, spawn):
                continue
            free = [cell for cell in cells if cell not in busy]
            if not free:
                break
            row, col = random.choice(free)
            busy.add((row, col))
            self._rain_hits.append(
                RainHit(
                    row=row,
                    col=col,
                    start=now,
                    duration=0.45 + random.random() * 0.4,
                    intensity=0.78 + random.random() * 0.16,
                )
            )

        self._rain_hits = [
            hit for hit in self._rain_hits if now - hit.start < hit.duration
        ]

    def _paint_rain_hits(self, matrix, config: Config, now: float) -> None:
        bright = config.base_color_2
        flash = (
            min(255, bright[0] + 40),
            min(255, bright[1] + 70),
            min(255, bright[2] + 55),
        )
        for hit in self._rain_hits:
            life = (now - hit.start) / max(hit.duration, 0.001)
            if life >= 1.0:
                continue
            if life < 0.1:
                pop = 1.0 - life / 0.1
                color = blend_color(bright, flash, pop * 0.55)
                amount = hit.intensity
            else:
                fade = (1.0 - (life - 0.1) / 0.9) ** 0.85
                color = bright
                amount = clamp(fade * hit.intensity, 0.0, 1.0)
            matrix[hit.row, hit.col] = blend_color(
                matrix[hit.row, hit.col],
                color,
                amount,
            )
            splash = amount * 0.22
            if splash <= 0.05:
                continue
            for d_row, d_col in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                row = hit.row + d_row
                col = hit.col + d_col
                if 0 <= row < self.rows and 0 <= col < self.cols:
                    matrix[row, col] = blend_color(
                        matrix[row, col],
                        bright,
                        splash,
                    )

    def _paint_rain(self, matrix, config: Config) -> None:
        for streak in self._rain_streaks:
            head = int(streak.row)
            for trail in range(5):
                row = head - trail
                if row < 0 or row >= self.rows:
                    continue
                key_name = get_key_at_position(row, streak.col, config.keyboard_layout)
                dark = (
                    config.key_colors[key_name]
                    if key_name and key_name in config.key_colors
                    else config.base_color
                )
                amount = max(0.0, 1.0 - trail * 0.22)
                matrix[row, streak.col] = blend_color(dark, config.base_color_2, amount)

    def stop(self) -> None:
        self._shutdown_threads()
        try:
            self.keyboard.fx.advanced.restore()
        except Exception:
            pass

    def turn_off(self) -> None:
        self._shutdown_threads()
        try:
            matrix = self.keyboard.fx.advanced.matrix
            for row in range(self.rows):
                for col in range(self.cols):
                    matrix[row, col] = (0, 0, 0)
            self.keyboard.fx.advanced.draw()
            self.keyboard.brightness = 0
        except Exception:
            pass

    def _prime_matrix(self) -> None:
        matrix = self.keyboard.fx.advanced.matrix
        now = time.monotonic()
        with self._lock:
            config = replace(self.config)
            for row in range(self.rows):
                for col in range(self.cols):
                    matrix[row, col] = compute_background_color(
                        row, col, self.rows, self.cols, config, now
                    )
        self.keyboard.fx.advanced.draw()

    def _register_press(self, row: int, col: int, now: float, config: Config) -> None:
        last = self._recent_presses.get((row, col), 0.0)
        if now - last < 0.03:
            return
        self._recent_presses[(row, col)] = now

        self._active[(row, col)] = ActiveKey(
            phase="hold",
            phase_end=now + config.hold_seconds,
        )

        if config.press_mode == "ripple":
            self._ripples.append(
                PressRipple(
                    row=float(row),
                    col=float(col),
                    start=now,
                    color_a=config.press_color,
                    color_b=config.press_color_2,
                )
            )

    def _poll_caps_lock(self, now: float, *, force: bool = False) -> None:
        if not force and now < self._caps_lock_last_poll:
            return
        self._caps_lock_last_poll = now + 0.12
        state = read_caps_lock_led(self._caps_lock_paths)
        if state is not None:
            self._caps_lock_on = state

    def _paint_caps_lock(self, matrix, config: Config, now: float) -> None:
        if not config.caps_lock_indicator or not self._caps_lock_on:
            return
        position = KEY_MAPPING.get("CAPSLK")
        if position is None:
            return
        row, col = position
        if row >= self.rows or col >= self.cols:
            return
        wave = (math.sin(now * math.tau * 1.15) + 1.0) * 0.5
        matrix[row, col] = blend_color(
            config.caps_lock_color,
            (255, 255, 255),
            0.16 * wave,
        )

    def _paint_ripples(self, matrix, config: Config, now: float) -> None:
        """Rysuje pierścienie fali od naciśnięć (tryb press = ripple)."""
        if not self._ripples:
            return

        max_dist = math.hypot(self.rows - 1, self.cols - 1) + 2.0
        # Szybkość ekspansji w „klawiszach na sekundę” (skalowana prędkością animacji).
        expand_speed = 5.0 + config.background_speed * 12.0
        band = 1.55
        trail_len = 3.2

        alive: list[PressRipple] = []
        for ripple in self._ripples:
            age = now - ripple.start
            if age < 0:
                continue
            radius = age * expand_speed
            if radius - trail_len > max_dist:
                continue
            alive.append(ripple)

            # Delikatne wygaszanie fali w miarę oddalania się od źródła.
            life = max(0.0, 1.0 - (radius / max(max_dist, 0.001)) * 0.55)

            for row in range(self.rows):
                for col in range(self.cols):
                    dist = math.hypot(row - ripple.row, col - ripple.col)
                    front = abs(dist - radius)
                    if front <= band:
                        amount = (1.0 - front / band) * life
                    else:
                        # Krótki ogon za czołem fali.
                        behind = radius - dist
                        if 0.0 < behind <= trail_len:
                            amount = (1.0 - behind / trail_len) * 0.45 * life
                        else:
                            continue

                    if amount <= 0.02:
                        continue

                    # Lekki gradient kolorów na pierścieniu w czasie.
                    mix = (math.sin(age * 4.0 + dist * 0.35) + 1.0) * 0.5
                    wave_color = blend_color(ripple.color_a, ripple.color_b, mix)
                    background = matrix[row, col]
                    matrix[row, col] = blend_color(background, wave_color, clamp(amount, 0.0, 1.0))

        self._ripples = alive

    def on_key_code(self, code: int) -> None:
        key_name = EVENT_MAPPING.get(code)
        if key_name is None:
            return
        position = KEY_MAPPING.get(key_name)
        if position is None:
            return

        now = time.monotonic()
        with self._lock:
            self._register_press(position[0], position[1], now, self.config)
            if key_name == "CAPSLK":
                # LED bywa zaktualizowany chwilę po evencie — przełącz od razu, poll poprawi.
                self._caps_lock_on = not self._caps_lock_on
                self._caps_lock_last_poll = now + 0.08

    def _render_loop(self) -> None:
        matrix = self.keyboard.fx.advanced.matrix

        while self._running:
            started = time.monotonic()
            now = started

            with self._lock:
                config = replace(self.config)
                frame_interval = 1.0 / config.fps

                for row in range(self.rows):
                    for col in range(self.cols):
                        matrix[row, col] = compute_background_color(
                            row, col, self.rows, self.cols, config, now
                        )

                if config.background_mode == "rain":
                    self._rain_hits.clear()
                    self._tick_rain(config, now)
                    self._paint_rain(matrix, config)
                elif config.background_mode == "rain_hits":
                    self._rain_streaks.clear()
                    self._tick_rain_hits(config, now)
                    self._paint_rain_hits(matrix, config, now)

                # Fala od naciśnięcia — na całej klawiaturze, pod lokalnym hold/fade klawisza.
                if config.press_mode == "ripple":
                    self._paint_ripples(matrix, config, now)

                expired: list[tuple[int, int]] = []
                for position, active in self._active.items():
                    row, col = position
                    background = matrix[row, col]
                    press_color = compute_press_color(
                        row, col, self.rows, self.cols, config, now
                    )
                    if active.phase == "hold":
                        color = press_color
                        if now >= active.phase_end:
                            active.phase = "fade"
                            active.phase_end = now + config.fade_seconds
                    else:
                        remaining = active.phase_end - now
                        if remaining <= 0:
                            expired.append(position)
                            continue
                        progress = 1.0 - (remaining / max(config.fade_seconds, 0.001))
                        color = blend_color(
                            background,
                            press_color,
                            1.0 - progress,
                        )

                    matrix[row, col] = color

                for position in expired:
                    self._active.pop(position, None)

                self._poll_caps_lock(now)
                self._paint_caps_lock(matrix, config, now)

            self.keyboard.fx.advanced.draw()

            elapsed = time.monotonic() - started
            time.sleep(max(0.0, frame_interval - elapsed))


class DaemonServer:
    def __init__(self, daemon: "ReactiveDaemon") -> None:
        self._daemon = daemon
        self._socket: socket.socket | None = None
        self._thread: threading.Thread | None = None
        self._running = False

    def start(self) -> None:
        path = daemon_socket_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            path.unlink()

        self._socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._socket.bind(str(path))
        self._socket.listen(8)
        self._running = True
        self._thread = threading.Thread(target=self._accept_loop, name="daemon-ipc", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._socket is not None:
            try:
                self._socket.close()
            except OSError:
                pass
            self._socket = None

        path = daemon_socket_path()
        if path.exists():
            try:
                path.unlink()
            except OSError:
                pass

        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None

    def _accept_loop(self) -> None:
        if self._socket is None:
            return

        while self._running:
            try:
                self._socket.settimeout(0.5)
                conn, _addr = self._socket.accept()
            except socket.timeout:
                continue
            except OSError:
                break

            threading.Thread(
                target=self._handle_client,
                args=(conn,),
                name="daemon-client",
                daemon=True,
            ).start()

    def _handle_client(self, conn: socket.socket) -> None:
        try:
            conn.settimeout(2.0)
            data = b""
            while b"\n" not in data:
                chunk = conn.recv(4096)
                if not chunk:
                    return
                data += chunk

            request = json.loads(data.decode("utf-8"))
            response = self._dispatch(request)
            conn.sendall((json.dumps(response) + "\n").encode("utf-8"))
        except Exception as exc:
            response = {"ok": False, "error": str(exc)}
            try:
                conn.sendall((json.dumps(response) + "\n").encode("utf-8"))
            except OSError:
                pass
        finally:
            conn.close()

    def _dispatch(self, request: dict) -> dict:
        command = request.get("cmd")
        if command == "status":
            return self._daemon.get_status()
        if command == "start":
            return self._daemon.start_lighting()
        if command == "stop":
            return self._daemon.stop_lighting()
        if command == "turn_off":
            return self._daemon.turn_off_lighting()
        if command == "reset_config":
            return self._daemon.reset_config()
        if command == "get_config":
            return {"ok": True, "config": config_to_dict(self._daemon.config)}
        if command == "update_config":
            return self._daemon.update_config(config_from_dict(request["config"]))
        if command == "set_config":
            return self._daemon.set_config(config_from_dict(request["config"]))
        if command == "reload":
            return self._daemon.reload_config()
        if command == "quit":
            self._daemon.shutdown()
            return {"ok": True}
        return {"ok": False, "error": f"Nieznane polecenie: {command}"}


class ReactiveDaemon:
    def __init__(self, config_path: Path | None = None) -> None:
        self.config_path = config_path or default_config_path()
        self.config = load_config(self.config_path)
        self._running = False
        self._shutdown_requested = False
        self._lock = threading.Lock()
        self._server = DaemonServer(self)
        self.lighting: ReactiveLighting | None = None
        self.manager = None
        self.keyboard = None
        self._last_error = ""
        self._lighting_turned_off = False

    def run(self, auto_start: bool = True) -> int:
        self._running = True
        self._server.start()

        if auto_start:
            result = self.start_lighting()
            if not result.get("ok"):
                self._last_error = result.get("error", "Nieznany błąd")

        def handle_signal(_signum, _frame) -> None:
            self.shutdown()

        signal.signal(signal.SIGINT, handle_signal)
        signal.signal(signal.SIGTERM, handle_signal)

        try:
            while self._running:
                time.sleep(0.2)
        finally:
            self._cleanup()
        return 0 if not self._last_error else 1

    def shutdown(self) -> None:
        self._shutdown_requested = True
        self._running = False

    def _cleanup(self) -> None:
        self.stop_lighting()
        self._server.stop()

    def get_status(self) -> dict:
        with self._lock:
            running = self.lighting is not None and self.lighting.is_running
            keyboard_name = self.keyboard.name if self.keyboard is not None else ""
            input_source = self.lighting.input_source if self.lighting is not None else ""
            error = self._last_error
            turned_off = self._lighting_turned_off and not running
        return {
            "ok": True,
            "running": running,
            "turned_off": turned_off,
            "keyboard": keyboard_name,
            "input_source": input_source,
            "error": error,
        }

    def _ensure_keyboard(self) -> None:
        if self.manager is None or self.keyboard is None:
            self.manager, self.keyboard = find_keyboard(self.config)

    def start_lighting(self) -> dict:
        with self._lock:
            try:
                self._ensure_keyboard()
                if self.lighting is None:
                    self.lighting = ReactiveLighting(
                        self.config,
                        manager=self.manager,
                        keyboard=self.keyboard,
                    )
                else:
                    self.lighting.update_config(self.config)

                self.lighting.start()
                self._lighting_turned_off = False
                self._last_error = ""
                return {"ok": True}
            except Exception as exc:
                self._last_error = str(exc)
                return {"ok": False, "error": str(exc)}

    def stop_lighting(self) -> dict:
        with self._lock:
            if self.lighting is not None and self.lighting.is_running:
                self.lighting.stop()
            self._lighting_turned_off = False
            return {"ok": True}

    def turn_off_lighting(self) -> dict:
        with self._lock:
            try:
                self._ensure_keyboard()
                if self.lighting is None:
                    self.lighting = ReactiveLighting(
                        self.config,
                        manager=self.manager,
                        keyboard=self.keyboard,
                    )
                self.lighting.turn_off()
                self._lighting_turned_off = True
                self._last_error = ""
                return {"ok": True}
            except Exception as exc:
                self._last_error = str(exc)
                return {"ok": False, "error": str(exc)}

    def reset_config(self) -> dict:
        with self._lock:
            was_running = self.lighting is not None and self.lighting.is_running
            self._lighting_turned_off = False
            keyboard_name = self.config.keyboard_name
            self.config = default_config()
            self.config = replace(self.config, keyboard_name=keyboard_name)
            save_config(self.config, self.config_path)

            if self.lighting is not None:
                if self.lighting.is_running:
                    self.lighting.stop()
                self.lighting.update_config(self.config)

            config_dict = config_to_dict(self.config)

        if was_running:
            result = self.start_lighting()
            if not result.get("ok"):
                return result

        return {"ok": True, "config": config_dict}

    def update_config(self, config: Config) -> dict:
        with self._lock:
            old_mode = self.config.background_mode
            self.config = replace(config)
            if self.lighting is not None and self.lighting.is_running:
                self.lighting.update_config(
                    self.config,
                    reset_state=config.background_mode != old_mode,
                )
            return {"ok": True}

    def set_config(self, config: Config) -> dict:
        with self._lock:
            self.config = replace(config)
            save_config(self.config, self.config_path)
            if self.lighting is not None and self.lighting.is_running:
                self.lighting.update_config(self.config, reset_state=True)
            return {"ok": True}

    def reload_config(self) -> dict:
        with self._lock:
            self.config = load_config(self.config_path)
            if self.lighting is not None and self.lighting.is_running:
                self.lighting.update_config(self.config, reset_state=True)
            return {"ok": True, "config": config_to_dict(self.config)}


def systemd_user_unit_path() -> Path:
    return Path.home() / ".config" / "systemd" / "user" / "razer-reactive.service"


def install_systemd_service() -> Path:
    unit_path = systemd_user_unit_path()
    unit_path.parent.mkdir(parents=True, exist_ok=True)

    unit = f"""[Unit]
Description=Razer Reactive keyboard lighting
After=graphical-session.target openrazer-daemon.service
Wants=openrazer-daemon.service

[Service]
Type=simple
ExecStart=/usr/bin/python3 {SCRIPT_PATH} --daemon
Restart=on-failure
RestartSec=3

[Install]
WantedBy=default.target
"""
    unit_path.write_text(unit, encoding="utf-8")

    subprocess.run(
        ["systemctl", "--user", "daemon-reload"],
        check=True,
    )
    subprocess.run(
        ["systemctl", "--user", "enable", "--now", "razer-reactive.service"],
        check=True,
    )
    return unit_path


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Reaktywne podświetlenie klawiszy OpenRazer z kolorem bazowym i wygaszaniem."
    )
    parser.add_argument(
        "-c",
        "--config",
        type=Path,
        default=None,
        help="Plik konfiguracyjny TOML",
    )
    parser.add_argument("--gui", action="store_true", help="Uruchom interfejs GTK")
    parser.add_argument(
        "--daemon",
        action="store_true",
        help="Uruchom usługę w tle (bez okien, z IPC)",
    )
    parser.add_argument(
        "--install-service",
        action="store_true",
        help="Zainstaluj i włącz autostart usługi systemd (user)",
    )
    parser.add_argument(
        "--install",
        action="store_true",
        help="Uruchom skrypt instalacyjny (wymaga sudo)",
    )
    parser.add_argument("--base-color", type=parse_color, help="Kolor bazowy: R,G,B lub #RRGGBB")
    parser.add_argument("--press-color", type=parse_color, help="Kolor po naciśnięciu: R,G,B lub #RRGGBB")
    parser.add_argument("--hold", type=float, help="Czas pełnego podświetlenia po naciśnięciu (sekundy)")
    parser.add_argument("--fade", type=float, help="Czas wygaszania do koloru bazowego (sekundy)")
    parser.add_argument("--brightness", type=int, help="Jasność 0-100")
    parser.add_argument("--fps", type=int, help="Częstotliwość odświeżania macierzy LED")
    parser.add_argument("--keyboard", type=str, help="Fragment nazwy klawiatury OpenRazer")
    return parser


def main() -> int:
    parser = build_arg_parser()
    args = parser.parse_args()

    if args.install:
        install_script = SCRIPT_PATH.with_name("install.sh")
        if not install_script.exists():
            print(f"Brak skryptu instalacyjnego: {install_script}", file=sys.stderr)
            print("Uruchom: sudo ./install.sh", file=sys.stderr)
            return 1
        if os.geteuid() != 0:
            print("Instalacja wymaga uprawnień root.", file=sys.stderr)
            print(f"Uruchom: sudo {install_script}", file=sys.stderr)
            return 1
        os.execvp("bash", ["bash", str(install_script)])

    if args.install_service:
        try:
            path = install_systemd_service()
            print(f"Zainstalowano usługę: {path}")
            print("Usługa uruchomiona i włączona przy logowaniu.")
            return 0
        except subprocess.CalledProcessError as exc:
            print(f"Błąd instalacji usługi: {exc}", file=sys.stderr)
            return 1

    if args.gui:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from razer_reactive_gui import run_gui

        return run_gui()

    if args.daemon:
        config_path = args.config or default_config_path()
        if not config_path.exists():
            print(f"Brak pliku konfiguracyjnego: {config_path}", file=sys.stderr)
            return 1

        socket_path = daemon_socket_path()
        if socket_path.exists():
            try:
                DaemonClient(timeout=1.0).status()
                print("Usługa w tle już działa.", file=sys.stderr)
                return 1
            except Exception:
                try:
                    socket_path.unlink()
                except OSError:
                    pass

        daemon = ReactiveDaemon(config_path)
        return daemon.run(auto_start=True)

    if daemon_socket_path().exists():
        try:
            DaemonClient(timeout=1.0).status()
            print(
                "Usługa w tle już działa. Użyj GUI lub: systemctl --user restart razer-reactive.service",
                file=sys.stderr,
            )
            return 1
        except Exception:
            pass

    config_path = args.config or default_config_path()
    if not config_path.exists():
        print(f"Brak pliku konfiguracyjnego: {config_path}", file=sys.stderr)
        return 1

    config = load_config(config_path)

    if args.base_color is not None:
        config.base_color = args.base_color
    if args.press_color is not None:
        config.press_color = args.press_color
    if args.hold is not None:
        config.hold_seconds = max(0.0, args.hold)
    if args.fade is not None:
        config.fade_seconds = max(0.0, args.fade)
    if args.brightness is not None:
        config.brightness = int(clamp(args.brightness, 0, 100))
    if args.fps is not None:
        config.fps = int(clamp(args.fps, 1, 120))
    if args.keyboard is not None:
        config.keyboard_name = args.keyboard.strip()

    app = ReactiveLighting(config)

    def handle_signal(_signum, _frame) -> None:
        app.stop()

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    try:
        app.run_blocking()
    except Exception as exc:
        print(f"Błąd: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())