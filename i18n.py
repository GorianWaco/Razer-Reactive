"""UI strings for Razer Reactive (English / Polish)."""

from __future__ import annotations

from razer_reactive import (
    BACKGROUND_MODES,
    CUSTOM_KEY_MODES,
    KEY_EFFECT_MODES,
    PRESS_MODES,
)

# Effect mode labels per language
_MODE_LABELS_EN = {
    "static": "Static color",
    "breathe": "Breathing",
    "gradient_horizontal": "Horizontal gradient",
    "gradient_vertical": "Vertical gradient",
    "gradient_flow": "Flowing gradient",
    "gradient_flow_reverse": "Flowing gradient (left)",
    "diagonal": "Diagonal gradient",
    "checkerboard": "Checkerboard",
    "cycle": "Hue cycle",
    "rainbow": "Rainbow",
    "wave": "Horizontal wave",
    "wave_vertical": "Vertical wave",
    "wave_flow": "Flowing wave",
    "pulse_radial": "Radial pulse",
    "meteor": "Meteor",
    "strobe": "Strobe",
    "blink_alternate": "Alternate blink",
    "rain": "Rain",
    "rain_hits": "Drops on keys",
    "per_key": "Custom key colors",
    "ripple": "Ripple from key",
}

_MODE_LABELS_PL = {
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
    "ripple": "Fala od klawisza",
}

STRINGS: dict[str, dict[str, str]] = {
    "en": {
        "app_title": "Razer Reactive",
        "save": "Save",
        "start": "Start",
        "stop": "Stop",
        "cancel": "Cancel",
        "apply": "Apply",
        "choose": "Choose",
        "delete": "Delete",
        "load": "Load",
        "reset": "Reset",
        "hero_title": "Reactive key lighting",
        "hero_desc": (
            "Lighting runs in the background as a system service. "
            "This window is for configuration only — closing it does not turn the effect off."
        ),
        "status_connecting": "Connecting…",
        "status_running": "Active",
        "status_stopped": "Stopped",
        "status_off": "Off",
        "status_offline": "Service unavailable",
        "device_openrazer": "OpenRazer keyboard",
        "language": "Language",
        "language_subtitle": "Interface language",
        "lang_en": "English",
        "lang_pl": "Polski",
        "profiles_title": "Setting profiles",
        "profiles_desc": "Save and load complete sets of colors, background modes and timings. Built-in factory looks cannot be deleted.",
        "profile_name": "Profile name",
        "saved_profiles": "Saved profiles",
        "manage_profiles": "Manage profiles",
        "manage_profiles_sub": "Save current settings or load a selected profile",
        "background_title": "Keyboard background",
        "background_desc": "Animation or gradient for the base lighting.",
        "bg_mode": "Background mode",
        "bg_mode_sub": "Lighting effect for the whole keyboard",
        "base_color_1": "Background color 1",
        "base_color_1_sub": "Primary background color or gradient start",
        "base_color_2": "Background color 2",
        "base_color_2_sub": "Second color (gradient, breathing, wave)",
        "anim_speed": "Animation speed",
        "anim_speed_sub": "Speed of breathing, waves or hue rotation",
        "custom_keys_title": "Keys with custom color",
        "custom_keys_desc": (
            "Default effect for all keys with an assigned color. "
            "On the map you can override a single key’s effect."
        ),
        "custom_key_mode": "Custom-key mode",
        "custom_key_mode_sub": "Lighting effect for recolored keys",
        "map_title": "Keyboard map",
        "map_subtitle": (
            "Click a key to edit. Ctrl+click: add/remove from selection. "
            "Shift+click: select a rectangle. Right-click: clear custom settings."
        ),
        "brush_color_1": "Brush color 1",
        "brush_color_2": "Brush color 2",
        "brush_effect": "Brush effect",
        "brush_default": "Default",
        "fill_all": "Fill all",
        "fill_selection": "Fill selection",
        "clear_map": "Clear map",
        "clear_selection": "Clear selection styles",
        "edit_selection": "Edit selection",
        "deselect": "Deselect",
        "selection_count": "{n} keys selected",
        "press_title": "Key press reaction",
        "press_desc": "Effect and color after a key press — independent of the background.",
        "press_mode": "Press mode",
        "press_mode_sub": "Pressed-key effect — “Ripple from key” spreads across the matrix",
        "press_color_1": "Press color 1",
        "press_color_1_sub": "Primary active-key color or gradient start",
        "press_color_2": "Press color 2",
        "press_color_2_sub": "Second color (breathing, gradient, wave, etc.)",
        "timing_title": "Timing",
        "timing_desc": "How long a key stays lit and how quickly it returns to the background.",
        "hold": "Hold time",
        "hold_sub": "Full brightness after press",
        "fade": "Fade time",
        "fade_sub": "Smooth return to the current background",
        "indicators_title": "Lock indicators",
        "indicators_desc": "Highlight lock keys while they are on — independent of rain and other effects.",
        "caps_lock": "Caps Lock",
        "caps_lock_sub": "Light up the Caps Lock key while Caps is enabled",
        "caps_lock_color": "Caps Lock color",
        "caps_lock_color_sub": "Color of the Caps Lock key while the lock is on",
        "display_title": "Display",
        "brightness": "Brightness",
        "brightness_sub": "Keyboard backlight brightness",
        "fps": "Refresh rate",
        "fps_sub": "Effect update frequency",
        "actions_title": "Actions",
        "actions_desc": "Turn lighting off completely or restore program defaults.",
        "turn_off": "Turn lighting off completely",
        "reset_settings": "Reset settings to defaults",
        "color_pick_title": "Choose color",
        "key_dialog_title": "Key {name}",
        "key_dialog_title_multi": "{n} keys",
        "key_effect": "Key effect",
        "key_effect_sub": "Custom effect, or default for recolored keys / background",
        "key_effect_default": "Default (global)",
        "color_1": "Color 1",
        "color_1_sub": "Primary key color or gradient start",
        "color_2": "Color 2",
        "color_2_sub": "Second color (breathing, gradient, wave, etc.)",
        "toast_profile_name": "Enter a profile name.",
        "toast_profile_saved": "Saved profile: {name}",
        "toast_profile_save_fail": "Could not save profile: {err}",
        "toast_pick_profile": "Select a profile from the list.",
        "toast_profile_missing": "Profile “{name}” does not exist.",
        "toast_profile_loaded": "Loaded profile: {name}",
        "toast_pick_delete": "Select a profile to delete.",
        "toast_profile_deleted": "Deleted profile: {name}",
        "toast_factory_profile": "“{name}” is a factory profile and cannot be deleted.",
        "toast_factory_restored": "Restored factory profile: {name}",
        "delete_profile_heading": "Delete profile “{name}”?",
        "delete_profile_body": "This cannot be undone.",
        "daemon_offline": (
            "Background service is not running. On a fresh system run:\n"
            "sudo ./install.sh"
        ),
        "daemon_error": "Could not connect to service: {err}",
        "daemon_lost": "Lost connection to the background service.",
        "toast_update_error": "Update error.",
        "toast_error": "Error: {err}",
        "toast_daemon_down": "Background service is not running.",
        "toast_stopped": "Lighting stopped.",
        "toast_started": "Lighting started.",
        "toast_op_failed": "Operation failed.",
        "toast_failed": "Failed: {err}",
        "toast_turn_off_fail": "Could not turn off.",
        "toast_turned_off": "Lighting fully off (brightness 0).",
        "reset_heading": "Reset settings?",
        "reset_body": (
            "Restores default colors, timings, brightness and background mode. "
            "Keyboard name is kept."
        ),
        "toast_reset_fail": "Reset failed.",
        "toast_reset_done": "Defaults restored.",
        "toast_saved_applied": "Saved and applied: {path}",
        "toast_saved_ipc": "Saved locally, but IPC error: {err}",
        "toast_saved": "Settings saved: {path}",
        "toast_still_running": "Lighting still runs in the background.",
        "keyd_help": (
            "keyd is capturing the keyboard, but this app cannot access it. "
            "Run: sudo usermod -aG keyd $USER , then log out and back in."
        ),
    },
    "pl": {
        "app_title": "Razer Reactive",
        "save": "Zapisz",
        "start": "Uruchom",
        "stop": "Zatrzymaj",
        "cancel": "Anuluj",
        "apply": "Zastosuj",
        "choose": "Wybierz",
        "delete": "Usuń",
        "load": "Wczytaj",
        "reset": "Resetuj",
        "hero_title": "Reaktywne podświetlenie klawiszy",
        "hero_desc": (
            "Podświetlenie działa w tle jako usługa systemowa. "
            "To okno służy tylko do konfiguracji — zamknięcie nie wyłącza efektu."
        ),
        "status_connecting": "Łączenie…",
        "status_running": "Aktywne",
        "status_stopped": "Zatrzymane",
        "status_off": "Wyłączone",
        "status_offline": "Usługa niedostępna",
        "device_openrazer": "Klawiatura OpenRazer",
        "language": "Język",
        "language_subtitle": "Język interfejsu",
        "lang_en": "English",
        "lang_pl": "Polski",
        "profiles_title": "Profile ustawień",
        "profiles_desc": "Zapisuj i wczytuj gotowe zestawy kolorów, trybów tła i czasów reakcji. Wbudowanych profili fabrycznych nie można usunąć.",
        "profile_name": "Nazwa profilu",
        "saved_profiles": "Zapisane profile",
        "manage_profiles": "Zarządzaj profilami",
        "manage_profiles_sub": "Zapisz bieżące ustawienia lub wczytaj wybrany profil",
        "background_title": "Tło klawiatury",
        "background_desc": "Tryb animacji lub gradientu podświetlenia bazowego.",
        "bg_mode": "Tryb tła",
        "bg_mode_sub": "Efekt podświetlenia całej klawiatury",
        "base_color_1": "Kolor tła 1",
        "base_color_1_sub": "Pierwszy kolor tła lub początek gradientu",
        "base_color_2": "Kolor tła 2",
        "base_color_2_sub": "Drugi kolor (gradient, pulsowanie, fala)",
        "anim_speed": "Prędkość animacji",
        "anim_speed_sub": "Szybkość pulsowania, fali lub rotacji odcienia",
        "custom_keys_title": "Klawisze z własnym kolorem",
        "custom_keys_desc": (
            "Domyślny efekt dla wszystkich klawiszy z przypisanym kolorem. "
            "Na mapie możesz nadpisać efekt pojedynczego klawisza."
        ),
        "custom_key_mode": "Tryb klawiszy z kolorem",
        "custom_key_mode_sub": "Efekt podświetlenia klawiszy, którym zmieniono kolor",
        "map_title": "Mapa klawiszy",
        "map_subtitle": (
            "Kliknij klawisz, aby edytować. Ctrl+klik: dodaj/usuń z zaznaczenia. "
            "Shift+klik: zaznacz prostokąt. Prawy przycisk: usuń własne ustawienia."
        ),
        "brush_color_1": "Kolor 1 pędzla",
        "brush_color_2": "Kolor 2 pędzla",
        "brush_effect": "Efekt pędzla",
        "brush_default": "Domyślny",
        "fill_all": "Wypełnij wszystkie",
        "fill_selection": "Wypełnij zaznaczenie",
        "clear_map": "Wyczyść mapę",
        "clear_selection": "Wyczyść style zaznaczenia",
        "edit_selection": "Edytuj zaznaczenie",
        "deselect": "Odznacz",
        "selection_count": "Zaznaczono klawiszy: {n}",
        "press_title": "Reakcja na naciśnięcie",
        "press_desc": "Rodzaj i kolor podświetlenia po wciśnięciu klawisza — niezależnie od tła.",
        "press_mode": "Tryb po naciśnięciu",
        "press_mode_sub": "Efekt naciśniętego klawisza — „Fala od klawisza” rozchodzi się po całej matrycy",
        "press_color_1": "Kolor po naciśnięciu 1",
        "press_color_1_sub": "Główny kolor aktywnego klawisza lub początek gradientu",
        "press_color_2": "Kolor po naciśnięciu 2",
        "press_color_2_sub": "Drugi kolor (pulsowanie, gradient, fala itd.)",
        "timing_title": "Czas",
        "timing_desc": "Jak długo klawisz świeci i jak szybko wraca do tła.",
        "hold": "Czas podświetlenia",
        "hold_sub": "Pełna jasność po naciśnięciu",
        "fade": "Czas wygaszania",
        "fade_sub": "Płynne przejście z powrotem do aktualnego tła",
        "indicators_title": "Wskaźniki blokad",
        "indicators_desc": "Podświetl klawisze blokad, gdy są włączone — niezależnie od deszczu i innych efektów.",
        "caps_lock": "Caps Lock",
        "caps_lock_sub": "Świeć klawiszem Caps Lock, gdy blokada wielkich liter jest włączona",
        "caps_lock_color": "Kolor Caps Lock",
        "caps_lock_color_sub": "Kolor klawisza Caps Lock przy włączonej blokadzie",
        "display_title": "Wyświetlanie",
        "brightness": "Jasność",
        "brightness_sub": "Jasność podświetlenia klawiatury",
        "fps": "Odświeżanie",
        "fps_sub": "Częstotliwość aktualizacji efektu",
        "actions_title": "Akcje",
        "actions_desc": "Wyłącz podświetlenie całkowicie lub przywróć domyślne ustawienia programu.",
        "turn_off": "Wyłącz podświetlenie całkowicie",
        "reset_settings": "Resetuj ustawienia do domyślnych",
        "color_pick_title": "Wybór koloru",
        "key_dialog_title": "Klawisz {name}",
        "key_dialog_title_multi": "Klawisze: {n}",
        "key_effect": "Efekt klawisza",
        "key_effect_sub": "Własny efekt albo domyślny dla klawiszy z kolorem / tło",
        "key_effect_default": "Domyślny (globalny)",
        "color_1": "Kolor 1",
        "color_1_sub": "Główny kolor klawisza lub początek gradientu",
        "color_2": "Kolor 2",
        "color_2_sub": "Drugi kolor (pulsowanie, gradient, fala itd.)",
        "toast_profile_name": "Podaj nazwę profilu.",
        "toast_profile_saved": "Zapisano profil: {name}",
        "toast_profile_save_fail": "Nie udało się zapisać profilu: {err}",
        "toast_pick_profile": "Wybierz profil z listy.",
        "toast_profile_missing": "Profil „{name}” nie istnieje.",
        "toast_profile_loaded": "Wczytano profil: {name}",
        "toast_pick_delete": "Wybierz profil do usunięcia.",
        "toast_profile_deleted": "Usunięto profil: {name}",
        "toast_factory_profile": "„{name}” to profil fabryczny — nie można go usunąć.",
        "toast_factory_restored": "Przywrócono profil fabryczny: {name}",
        "delete_profile_heading": "Usunąć profil „{name}”?",
        "delete_profile_body": "Tej operacji nie można cofnąć.",
        "daemon_offline": (
            "Usługa w tle nie działa. Na świeżym systemie uruchom:\n"
            "sudo ./install.sh"
        ),
        "daemon_error": "Nie udało się połączyć z usługą: {err}",
        "daemon_lost": "Utracono połączenie z usługą w tle.",
        "toast_update_error": "Błąd aktualizacji.",
        "toast_error": "Błąd: {err}",
        "toast_daemon_down": "Usługa w tle nie działa.",
        "toast_stopped": "Podświetlenie zatrzymane.",
        "toast_started": "Podświetlenie uruchomione.",
        "toast_op_failed": "Operacja nie powiodła się.",
        "toast_failed": "Nie udało się: {err}",
        "toast_turn_off_fail": "Nie udało się wyłączyć.",
        "toast_turned_off": "Podświetlenie wyłączone całkowicie (jasność 0).",
        "reset_heading": "Resetować ustawienia?",
        "reset_body": (
            "Przywróci domyślne kolory, czasy, jasność i tryb tła. "
            "Nazwa klawiatury zostanie zachowana."
        ),
        "toast_reset_fail": "Reset nie powiódł się.",
        "toast_reset_done": "Przywrócono domyślne ustawienia.",
        "toast_saved_applied": "Zapisano i zastosowano: {path}",
        "toast_saved_ipc": "Zapisano lokalnie, ale błąd IPC: {err}",
        "toast_saved": "Zapisano ustawienia: {path}",
        "toast_still_running": "Podświetlenie nadal działa w tle.",
        "keyd_help": (
            "keyd przechwytuje klawiaturę, ale brak dostępu do jego urządzenia. "
            "Uruchom: sudo usermod -aG keyd $USER , wyloguj się i zaloguj ponownie."
        ),
    },
}


def tr(lang: str, msg_id: str, **kwargs) -> str:
    """Translate msg_id. Format kwargs must not reuse names that collide with params."""
    table = STRINGS.get(lang) or STRINGS["en"]
    text = table.get(msg_id) or STRINGS["en"].get(msg_id, msg_id)
    if kwargs:
        try:
            return text.format(**kwargs)
        except (KeyError, ValueError):
            return text
    return text


def mode_label(lang: str, mode: str) -> str:
    labels = _MODE_LABELS_EN if lang != "pl" else _MODE_LABELS_PL
    return labels.get(mode, mode)


def mode_labels_list(lang: str, modes: tuple[str, ...]) -> list[str]:
    return [mode_label(lang, mode) for mode in modes]


def background_mode_labels(lang: str) -> list[str]:
    return mode_labels_list(lang, BACKGROUND_MODES)


def press_mode_labels(lang: str) -> list[str]:
    return mode_labels_list(lang, PRESS_MODES)


def custom_key_mode_labels(lang: str) -> list[str]:
    return mode_labels_list(lang, CUSTOM_KEY_MODES)


def key_effect_mode_labels(lang: str) -> list[str]:
    return mode_labels_list(lang, KEY_EFFECT_MODES)
