#!/usr/bin/env python3
"""GTK4 interface for Razer Reactive lighting."""

from __future__ import annotations

import sys
import threading
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("Gdk", "4.0")

from gi.repository import Adw, Gdk, GLib, Gtk

sys.path.insert(0, str(Path(__file__).resolve().parent))

from i18n import (
    background_mode_labels,
    custom_key_mode_labels,
    key_effect_mode_labels,
    mode_label,
    press_mode_labels,
    tr,
)
from razer_reactive import (
    APP_ID,
    BACKGROUND_MODES,
    CUSTOM_KEY_MODES,
    KEY_EFFECT_MODES,
    KEY_MAPPING,
    MODES_WITH_COLOR_2,
    PRESS_MODES,
    UI_LANGUAGES,
    Config,
    DaemonClient,
    can_access_keyd_socket,
    clamp,
    clamp_byte,
    config_from_dict,
    default_config_path,
    delete_profile,
    get_profile,
    is_factory_profile,
    is_keyd_running,
    iter_gui_keys,
    key_label,
    load_config,
    load_profiles,
    normalize_ui_language,
    rgb_to_hex,
    save_config,
    save_profile,
    user_in_group,
)

# Sized so a full 6×22 map fits a typical maximized window without H-scroll.
KEYBOARD_MAP_SCALE = 1.28
_KEY_BTN_WIDTH = int(34 * KEYBOARD_MAP_SCALE)
_KEY_BTN_HEIGHT = int(30 * KEYBOARD_MAP_SCALE)
_KEY_BTN_FONT_REM = round(0.68 * KEYBOARD_MAP_SCALE, 2)
_KEYBOARD_GRID_PADDING = int(6 * KEYBOARD_MAP_SCALE)
_KEYBOARD_MIN_HEIGHT = int(6 * (_KEY_BTN_HEIGHT + 4) + 2 * _KEYBOARD_GRID_PADDING + 8)
_KEYBOARD_MIN_WIDTH = int(22 * (_KEY_BTN_WIDTH + 4) + 2 * _KEYBOARD_GRID_PADDING + 8)

APP_CSS = f"""
.preview-swatch {{
    min-width: 56px;
    min-height: 56px;
    border-radius: 12px;
    border: 2px solid alpha(@window_fg_color, 0.15);
}}

.status-pill {{
    border-radius: 999px;
    padding: 4px 12px;
    font-weight: 600;
}}

.status-running {{
    background: alpha(@success_color, 0.18);
    color: @success_color;
}}

.status-stopped {{
    background: alpha(@window_fg_color, 0.08);
    color: alpha(@window_fg_color, 0.7);
}}

.status-offline {{
    background: alpha(@warning_color, 0.18);
    color: @warning_color;
}}

.status-off {{
    background: alpha(@error_color, 0.14);
    color: @error_color;
}}

.action-button {{
    min-height: 42px;
}}

.key-btn {{
    min-width: {_KEY_BTN_WIDTH}px;
    min-height: {_KEY_BTN_HEIGHT}px;
    padding: {max(1, int(2 * KEYBOARD_MAP_SCALE))}px {max(2, int(3 * KEYBOARD_MAP_SCALE))}px;
    font-size: {_KEY_BTN_FONT_REM}rem;
    font-weight: 600;
    border: 2px solid transparent;
    box-shadow: none;
}}

.key-btn-selected {{
    border: 2px solid @accent_color;
    box-shadow: 0 0 0 1px alpha(@accent_color, 0.55);
}}

.key-btn-empty {{
    min-width: {_KEY_BTN_WIDTH}px;
    min-height: {_KEY_BTN_HEIGHT}px;
    opacity: 0;
}}

.keyboard-grid {{
    padding: {_KEYBOARD_GRID_PADDING}px;
}}

.color-chooser-wrap {{
    min-width: 420px;
    min-height: 360px;
}}
"""


def rgba_from_rgb(color: tuple[int, int, int]) -> Gdk.RGBA:
    rgba = Gdk.RGBA()
    rgba.red = color[0] / 255.0
    rgba.green = color[1] / 255.0
    rgba.blue = color[2] / 255.0
    rgba.alpha = 1.0
    return rgba


def rgb_from_rgba(rgba: Gdk.RGBA) -> tuple[int, int, int]:
    return (
        clamp_byte(rgba.red * 255),
        clamp_byte(rgba.green * 255),
        clamp_byte(rgba.blue * 255),
    )


class ColorPickDialog(Adw.Window):
    """Large color chooser without scrollbars."""

    def __init__(
        self,
        parent: Gtk.Window | None,
        color: tuple[int, int, int],
        on_pick,
        lang: str = "en",
    ) -> None:
        super().__init__(transient_for=parent, modal=True)
        self._on_pick = on_pick
        self.set_title(tr(lang, "color_pick_title"))
        self.set_default_size(480, 520)
        self.set_resizable(True)

        toolbar = Adw.ToolbarView()
        header = Adw.HeaderBar()
        cancel_btn = Gtk.Button(label=tr(lang, "cancel"))
        cancel_btn.connect("clicked", lambda *_: self.close())
        ok_btn = Gtk.Button(label=tr(lang, "choose"))
        ok_btn.add_css_class("suggested-action")
        ok_btn.connect("clicked", self._on_ok)
        header.pack_start(cancel_btn)
        header.pack_end(ok_btn)
        toolbar.add_top_bar(header)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_margin_top(12)
        box.set_margin_bottom(16)
        box.set_margin_start(16)
        box.set_margin_end(16)
        box.add_css_class("color-chooser-wrap")

        self.chooser = Gtk.ColorChooserWidget()
        self.chooser.set_use_alpha(False)
        self.chooser.set_rgba(rgba_from_rgb(color))
        self.chooser.set_vexpand(True)
        self.chooser.set_hexpand(True)
        box.append(self.chooser)

        toolbar.set_content(box)
        self.set_content(toolbar)

    def _on_ok(self, *_args) -> None:
        self._on_pick(rgb_from_rgba(self.chooser.get_rgba()))
        self.close()


class ColorPickButton(Gtk.Button):
    """Opens a full-size color dialog instead of the cramped system picker."""

    def __init__(
        self,
        color: tuple[int, int, int],
        on_change,
        parent_window: Gtk.Window | None = None,
        lang: str = "en",
    ) -> None:
        super().__init__()
        self._color = color
        self._on_change = on_change
        self._parent_window = parent_window
        self._lang = lang
        self._swatch = Gtk.DrawingArea()
        self._swatch.set_size_request(36, 24)
        self._swatch.set_draw_func(self._draw)
        self.set_child(self._swatch)
        self.connect("clicked", self._open)

    def _draw(self, _area, context, width, height) -> None:
        context.set_source_rgb(
            self._color[0] / 255.0,
            self._color[1] / 255.0,
            self._color[2] / 255.0,
        )
        context.rectangle(0, 0, width, height)
        context.fill()

    def _open(self, *_args) -> None:
        parent = self._parent_window
        if parent is None:
            root = self.get_root()
            parent = root if isinstance(root, Gtk.Window) else None
        dialog = ColorPickDialog(parent, self._color, self._on_picked, self._lang)
        dialog.present()

    def _on_picked(self, color: tuple[int, int, int]) -> None:
        self.set_color(color)
        self._on_change(color)

    def get_color(self) -> tuple[int, int, int]:
        return self._color

    def set_color(self, color: tuple[int, int, int]) -> None:
        self._color = color
        self._swatch.queue_draw()

    def set_lang(self, lang: str) -> None:
        self._lang = lang


class ColorRow(Gtk.Box):
    def __init__(
        self,
        title: str,
        subtitle: str,
        color: tuple[int, int, int],
        on_change,
        parent_window: Gtk.Window | None = None,
        lang: str = "en",
    ) -> None:
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        self.add_css_class("linked")

        self._on_change = on_change
        self._updating = False

        text_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        text_box.set_hexpand(True)
        text_box.set_valign(Gtk.Align.CENTER)

        self.title_label = Gtk.Label(label=title, xalign=0)
        self.title_label.add_css_class("title-4")
        self.subtitle_label = Gtk.Label(label=subtitle, xalign=0)
        self.subtitle_label.add_css_class("dim-label")

        text_box.append(self.title_label)
        text_box.append(self.subtitle_label)

        self.preview = Gtk.DrawingArea()
        self.preview.set_size_request(56, 56)
        self.preview.add_css_class("preview-swatch")
        self.preview.set_draw_func(self._draw_preview)
        self._color = color

        self.picker = ColorPickButton(color, self._on_color_set, parent_window, lang)

        self.value_label = Gtk.Label(xalign=1)
        self.value_label.add_css_class("monospace")
        self._update_value_label()

        self.append(text_box)
        self.append(self.preview)
        self.append(self.picker)
        self.append(self.value_label)

    def _draw_preview(self, _area, context, width, height) -> None:
        context.set_source_rgb(
            self._color[0] / 255.0,
            self._color[1] / 255.0,
            self._color[2] / 255.0,
        )
        context.rectangle(0, 0, width, height)
        context.fill()

    def _update_value_label(self) -> None:
        self.value_label.set_text(rgb_to_hex(self._color))

    def _on_color_set(self, color: tuple[int, int, int]) -> None:
        if self._updating:
            return
        self._color = color
        self.preview.queue_draw()
        self._update_value_label()
        self._on_change(self._color)

    def get_color(self) -> tuple[int, int, int]:
        return self._color

    def set_color(self, color: tuple[int, int, int]) -> None:
        self._updating = True
        self._color = color
        self.picker.set_color(color)
        self.preview.queue_draw()
        self._update_value_label()
        self._updating = False

    def set_labels(self, title: str, subtitle: str) -> None:
        self.title_label.set_text(title)
        self.subtitle_label.set_text(subtitle)

    def set_lang(self, lang: str) -> None:
        self.picker.set_lang(lang)


class KeyStyleDialog(Adw.Window):
    def __init__(
        self,
        parent: Gtk.Window | None,
        key_names: list[str],
        color: tuple[int, int, int],
        color_2: tuple[int, int, int],
        effect: str | None,
        on_apply,
        lang: str = "en",
    ) -> None:
        super().__init__()
        if parent is not None:
            self.set_transient_for(parent)
        self.set_modal(True)
        self._key_names = list(key_names)
        self._on_apply = on_apply
        self._color = color
        self._color_2 = color_2
        self._effect = effect
        self._lang = lang
        if len(self._key_names) == 1:
            self.set_title(
                tr(lang, "key_dialog_title", name=key_label(self._key_names[0]))
            )
        else:
            self.set_title(tr(lang, "key_dialog_title_multi", n=len(self._key_names)))
        self.set_default_size(460, 420)
        self.set_hide_on_close(True)

        toolbar = Adw.ToolbarView()
        header = Adw.HeaderBar()
        cancel_btn = Gtk.Button(label=tr(lang, "cancel"))
        cancel_btn.connect("clicked", lambda *_: self.close())
        apply_btn = Gtk.Button(label=tr(lang, "apply"))
        apply_btn.add_css_class("suggested-action")
        apply_btn.connect("clicked", self._on_apply_clicked)
        header.pack_start(cancel_btn)
        header.pack_end(apply_btn)
        toolbar.add_top_bar(header)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        group = Adw.PreferencesGroup()
        group.set_margin_top(12)
        group.set_margin_bottom(12)
        group.set_margin_start(12)
        group.set_margin_end(12)

        self.effect_row = Adw.ComboRow()
        self.effect_row.set_title(tr(lang, "key_effect"))
        self.effect_row.set_subtitle(tr(lang, "key_effect_sub"))
        effect_labels = [tr(lang, "key_effect_default")] + key_effect_mode_labels(lang)
        self.effect_row.set_model(Gtk.StringList.new(effect_labels))
        if effect and effect in KEY_EFFECT_MODES:
            self.effect_row.set_selected(KEY_EFFECT_MODES.index(effect) + 1)
        else:
            self.effect_row.set_selected(0)
        self.effect_row.connect("notify::selected", self._on_effect_changed)
        group.add(self.effect_row)

        self.color_row = ColorRow(
            tr(lang, "color_1"),
            tr(lang, "color_1_sub"),
            color,
            self._on_color_changed,
            self,
            lang,
        )
        self.color_2_row = ColorRow(
            tr(lang, "color_2"),
            tr(lang, "color_2_sub"),
            color_2,
            self._on_color_2_changed,
            self,
            lang,
        )
        group.add(self.color_row)
        group.add(self.color_2_row)
        content.append(group)
        toolbar.set_content(content)
        self.set_content(toolbar)
        self._update_color_2_visibility()

    def _selected_effect(self) -> str | None:
        index = self.effect_row.get_selected()
        if index <= 0:
            return None
        return KEY_EFFECT_MODES[index - 1]

    def _on_effect_changed(self, *_args) -> None:
        self._update_color_2_visibility()

    def _update_color_2_visibility(self) -> None:
        effect = self._selected_effect()
        needs_color_2 = effect is None or effect in MODES_WITH_COLOR_2
        self.color_2_row.set_visible(needs_color_2)

    def _on_color_changed(self, color: tuple[int, int, int]) -> None:
        self._color = color

    def _on_color_2_changed(self, color: tuple[int, int, int]) -> None:
        self._color_2 = color

    def _on_apply_clicked(self, _button) -> None:
        self._on_apply(
            self._key_names,
            self._color,
            self._color_2,
            self._selected_effect(),
        )
        self.close()


class KeyboardColorEditor(Gtk.Box):
    """Keyboard map for per-key color/effect assignment with multi-select."""

    def __init__(self, config: Config, on_change, parent_window: Gtk.Window, lang: str) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self._on_change = on_change
        self._parent_window = parent_window
        self._lang = lang
        self._layout = config.keyboard_layout
        self._base_color = config.base_color
        self._base_color_2 = config.base_color_2
        self._brush_color = config.base_color
        self._brush_color_2 = config.base_color_2
        self._brush_effect: str | None = None
        self._key_colors: dict[str, tuple[int, int, int]] = dict(config.key_colors)
        self._key_colors_2: dict[str, tuple[int, int, int]] = dict(config.key_colors_2)
        self._key_effects: dict[str, str] = dict(config.key_effects)
        self._buttons: dict[str, Gtk.Button] = {}
        self._key_cells: dict[str, tuple[int, int, int, int]] = {}
        self._selected: set[str] = set()
        self._anchor_key: str | None = None

        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        header.set_valign(Gtk.Align.CENTER)

        title_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        title_box.set_hexpand(True)
        self.title_label = Gtk.Label(label=tr(lang, "map_title"), xalign=0)
        self.title_label.add_css_class("title-4")
        self.subtitle_label = Gtk.Label(
            label=tr(lang, "map_subtitle"),
            xalign=0,
            wrap=True,
        )
        self.subtitle_label.add_css_class("dim-label")
        self.selection_label = Gtk.Label(xalign=0)
        self.selection_label.add_css_class("accent")
        self.selection_label.set_visible(False)
        title_box.append(self.title_label)
        title_box.append(self.subtitle_label)
        title_box.append(self.selection_label)
        header.append(title_box)

        brush_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        brush_box.set_halign(Gtk.Align.END)

        brush_colors = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.brush_picker = ColorPickButton(
            self._brush_color, self._on_brush_changed, parent_window, lang
        )
        self.brush_picker.set_tooltip_text(tr(lang, "brush_color_1"))
        self.brush_picker_2 = ColorPickButton(
            self._brush_color_2, self._on_brush_2_changed, parent_window, lang
        )
        self.brush_picker_2.set_tooltip_text(tr(lang, "brush_color_2"))
        brush_colors.append(self.brush_picker)
        brush_colors.append(self.brush_picker_2)

        brush_effect_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        brush_effect_label = Gtk.Label(label=tr(lang, "brush_effect"), xalign=0)
        brush_effect_label.add_css_class("caption")
        self._brush_effect_label = brush_effect_label
        brush_effect_labels = [tr(lang, "brush_default")] + key_effect_mode_labels(lang)
        self._brush_effect_model = Gtk.StringList.new(brush_effect_labels)
        # DropDown (not Adw.ComboRow) — ComboRow outside PreferencesGroup can steal clicks.
        self.brush_effect_dropdown = Gtk.DropDown(model=self._brush_effect_model)
        self.brush_effect_dropdown.set_selected(0)
        self.brush_effect_dropdown.connect("notify::selected", self._on_brush_effect_changed)
        brush_effect_box.append(brush_effect_label)
        brush_effect_box.append(self.brush_effect_dropdown)

        brush_box.append(brush_colors)
        brush_box.append(brush_effect_box)
        header.append(brush_box)
        self.append(header)

        max_row = max(pos[0] for pos in KEY_MAPPING.values())
        max_col = max(pos[1] for pos in KEY_MAPPING.values())
        for _name, row, col, colspan, rowspan in iter_gui_keys(self._layout):
            max_row = max(max_row, row + rowspan - 1)
            max_col = max(max_col, col + colspan - 1)

        grid = Gtk.Grid()
        grid.set_row_spacing(3)
        grid.set_column_spacing(3)
        grid.add_css_class("keyboard-grid")
        grid.set_halign(Gtk.Align.CENTER)
        grid.set_valign(Gtk.Align.START)
        grid.set_can_focus(True)

        placements = {
            (grid_row, grid_col): (key_name, span_cols, span_rows)
            for key_name, grid_row, grid_col, span_cols, span_rows in iter_gui_keys(self._layout)
        }
        occupied: set[tuple[int, int]] = set()
        for row in range(max_row + 1):
            for col in range(max_col + 1):
                if (row, col) in occupied:
                    continue
                placement = placements.get((row, col))
                if placement is None:
                    spacer = Gtk.Box()
                    spacer.add_css_class("key-btn-empty")
                    spacer.set_can_target(False)
                    spacer.set_focusable(False)
                    grid.attach(spacer, col, row, 1, 1)
                    continue

                key_name, colspan, rowspan = placement
                color = self._key_colors.get(key_name, config.base_color)
                btn = Gtk.Button(label=key_label(key_name))
                btn.add_css_class("key-btn")
                btn.set_can_target(True)
                btn.set_focusable(True)
                if colspan > 1:
                    btn.set_hexpand(True)
                if rowspan > 1:
                    btn.set_vexpand(True)
                self._apply_button_style(key_name, btn, color)

                # Use Button.clicked (reliable). Extra GestureClick(button=1) fights
                # Gtk.Button's own gesture and silently drops real mouse clicks.
                btn.connect("clicked", self._on_key_clicked, key_name)

                right_click = Gtk.GestureClick()
                right_click.set_button(3)
                right_click.connect("pressed", self._on_key_right_click, key_name)
                btn.add_controller(right_click)

                self._buttons[key_name] = btn
                self._key_cells[key_name] = (row, col, colspan, rowspan)
                grid.attach(btn, col, row, colspan, rowspan)
                for grid_row in range(row, row + rowspan):
                    for grid_col in range(col, col + colspan):
                        occupied.add((grid_row, grid_col))

        # Escape clears selection when the map has focus.
        key_controller = Gtk.EventControllerKey()
        key_controller.connect("key-pressed", self._on_map_key_pressed)
        grid.add_controller(key_controller)

        # Direct child (no nested ScrolledWindow) so clicks reach buttons reliably.
        self._grid = grid
        self.append(grid)

        actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        actions.set_halign(Gtk.Align.END)

        self.edit_selection_btn = Gtk.Button(label=tr(lang, "edit_selection"))
        self.edit_selection_btn.add_css_class("suggested-action")
        self.edit_selection_btn.connect("clicked", self._on_edit_selection)
        self.edit_selection_btn.set_sensitive(False)

        self.deselect_btn = Gtk.Button(label=tr(lang, "deselect"))
        self.deselect_btn.connect("clicked", self._on_deselect)
        self.deselect_btn.set_sensitive(False)

        self.fill_btn = Gtk.Button(label=tr(lang, "fill_all"))
        self.fill_btn.connect("clicked", self._on_fill_clicked)
        self.clear_btn = Gtk.Button(label=tr(lang, "clear_map"))
        self.clear_btn.connect("clicked", self._on_clear_clicked)

        actions.append(self.edit_selection_btn)
        actions.append(self.deselect_btn)
        actions.append(self.fill_btn)
        actions.append(self.clear_btn)

        self.append(actions)

    def _key_tooltip(self, key_name: str, color: tuple[int, int, int]) -> str:
        effect = self._key_effects.get(key_name)
        if effect:
            effect_label = mode_label(self._lang, effect)
            return f"{key_name} · {effect_label} · {rgb_to_hex(color)}"
        if key_name in self._key_colors:
            return f"{key_name} · {rgb_to_hex(color)}"
        return key_name

    def _apply_button_style(self, key_name: str, button: Gtk.Button, color: tuple[int, int, int]) -> None:
        button.set_tooltip_text(self._key_tooltip(key_name, color))
        selected = key_name in self._selected
        if selected:
            button.add_css_class("key-btn-selected")
        else:
            button.remove_css_class("key-btn-selected")
        css = f".key-btn {{ background-color: {rgb_to_hex(color)}; color: white; }}"
        provider = Gtk.CssProvider()
        provider.load_from_data(css)
        style = button.get_style_context()
        for old in getattr(button, "_color_providers", []):
            style.remove_provider(old)
        style.add_provider(provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        button._color_providers = [provider]  # type: ignore[attr-defined]

    def _refresh_button(self, key_name: str) -> None:
        button = self._buttons[key_name]
        color = self._key_colors.get(key_name, self._base_color)
        self._apply_button_style(key_name, button, color)

    def _refresh_selection_ui(self) -> None:
        count = len(self._selected)
        has_sel = count > 0
        self.selection_label.set_visible(has_sel)
        if has_sel:
            self.selection_label.set_text(tr(self._lang, "selection_count", n=count))
        self.edit_selection_btn.set_sensitive(has_sel)
        self.deselect_btn.set_sensitive(has_sel)
        if has_sel:
            self.fill_btn.set_label(tr(self._lang, "fill_selection"))
            self.clear_btn.set_label(tr(self._lang, "clear_selection"))
        else:
            self.fill_btn.set_label(tr(self._lang, "fill_all"))
            self.clear_btn.set_label(tr(self._lang, "clear_map"))

    def _set_selected(self, keys: set[str], *, anchor: str | None = None) -> None:
        previous = self._selected
        self._selected = set(keys)
        if anchor is not None:
            self._anchor_key = anchor
        elif not self._selected:
            self._anchor_key = None
        for key_name in previous | self._selected:
            if key_name in self._buttons:
                self._refresh_button(key_name)
        self._refresh_selection_ui()

    def _keys_in_rect(self, a: str, b: str) -> set[str]:
        if a not in self._key_cells or b not in self._key_cells:
            return {b}
        ar, ac, aw, ah = self._key_cells[a]
        br, bc, bw, bh = self._key_cells[b]
        r0 = min(ar, br)
        r1 = max(ar + ah - 1, br + bh - 1)
        c0 = min(ac, bc)
        c1 = max(ac + aw - 1, bc + bw - 1)
        result: set[str] = set()
        for key_name, (row, col, colspan, rowspan) in self._key_cells.items():
            # Include key if its footprint intersects the rectangle.
            if row + rowspan - 1 < r0 or row > r1:
                continue
            if col + colspan - 1 < c0 or col > c1:
                continue
            result.add(key_name)
        return result

    def _notify_change(self) -> None:
        self._on_change(self.get_key_styles())

    def _on_brush_changed(self, color: tuple[int, int, int]) -> None:
        self._brush_color = color

    def _on_brush_2_changed(self, color: tuple[int, int, int]) -> None:
        self._brush_color_2 = color

    def _on_brush_effect_changed(self, _dropdown, _pspec) -> None:
        index = self.brush_effect_dropdown.get_selected()
        self._brush_effect = None if index <= 0 else KEY_EFFECT_MODES[index - 1]

    def _on_map_key_pressed(self, _controller, keyval: int, _keycode: int, _state) -> bool:
        if keyval == Gdk.KEY_Escape and self._selected:
            self._set_selected(set())
            return True
        return False

    def _current_modifiers(self) -> Gdk.ModifierType:
        """Read Ctrl/Shift at click time (keyboard or pointer device)."""
        display = self.get_display()
        if display is None:
            return Gdk.ModifierType(0)
        seat = display.get_default_seat()
        if seat is None:
            return Gdk.ModifierType(0)
        for getter in (seat.get_keyboard, seat.get_pointer):
            device = getter()
            if device is None:
                continue
            try:
                return Gdk.ModifierType(device.get_modifier_state())
            except Exception:
                continue
        return Gdk.ModifierType(0)

    def _on_key_clicked(self, _button, key_name: str) -> None:
        state = self._current_modifiers()
        ctrl = bool(state & Gdk.ModifierType.CONTROL_MASK)
        shift = bool(state & Gdk.ModifierType.SHIFT_MASK)

        if ctrl:
            selected = set(self._selected)
            if key_name in selected:
                selected.discard(key_name)
            else:
                selected.add(key_name)
            self._set_selected(selected, anchor=key_name)
            return

        if shift and self._anchor_key:
            self._set_selected(self._keys_in_rect(self._anchor_key, key_name))
            return

        # Plain click: if multi-selection includes this key, edit the group;
        # otherwise open a single-key dialog.
        if len(self._selected) > 1 and key_name in self._selected:
            self._open_style_dialog(sorted(self._selected))
            return

        self._set_selected({key_name}, anchor=key_name)
        self._open_style_dialog([key_name])

    def _on_key_right_click(
        self,
        _gesture,
        _n_press: int,
        _x: float,
        _y: float,
        key_name: str,
    ) -> None:
        if len(self._selected) > 1 and key_name in self._selected:
            targets = list(self._selected)
        else:
            targets = [key_name]
        for name in targets:
            self._key_colors.pop(name, None)
            self._key_colors_2.pop(name, None)
            self._key_effects.pop(name, None)
            self._refresh_button(name)
        self._notify_change()

    def _style_seed(self, key_names: list[str]) -> tuple[
        tuple[int, int, int],
        tuple[int, int, int],
        str | None,
    ]:
        """Initial dialog values from the first key (or common values when all match)."""
        first = key_names[0]
        color = self._key_colors.get(first, self._base_color)
        color_2 = self._key_colors_2.get(first, self._base_color_2)
        effect = self._key_effects.get(first)
        if len(key_names) > 1:
            colors = {self._key_colors.get(k, self._base_color) for k in key_names}
            colors_2 = {self._key_colors_2.get(k, self._base_color_2) for k in key_names}
            effects = {self._key_effects.get(k) for k in key_names}
            if len(colors) == 1:
                color = next(iter(colors))
            if len(colors_2) == 1:
                color_2 = next(iter(colors_2))
            if len(effects) == 1:
                effect = next(iter(effects))
        return color, color_2, effect

    def _open_style_dialog(self, key_names: list[str]) -> None:
        if not key_names:
            return
        parent = self._parent_window
        if parent is None:
            root = self.get_root()
            parent = root if isinstance(root, Gtk.Window) else None
        color, color_2, effect = self._style_seed(key_names)
        dialog = KeyStyleDialog(
            parent,
            key_names,
            color,
            color_2,
            effect,
            self._on_key_style_applied,
            self._lang,
        )
        dialog.set_hide_on_close(True)
        dialog.present()

    def _on_edit_selection(self, _button) -> None:
        if self._selected:
            self._open_style_dialog(sorted(self._selected))

    def _on_deselect(self, _button) -> None:
        self._set_selected(set())

    def _on_key_style_applied(
        self,
        key_names: list[str],
        color: tuple[int, int, int],
        color_2: tuple[int, int, int],
        effect: str | None,
    ) -> None:
        for key_name in key_names:
            self._key_colors[key_name] = color
            if color_2 != self._base_color_2 or effect:
                self._key_colors_2[key_name] = color_2
            else:
                self._key_colors_2.pop(key_name, None)
            if effect:
                self._key_effects[key_name] = effect
            else:
                self._key_effects.pop(key_name, None)
            self._refresh_button(key_name)
        self._notify_change()

    def _apply_brush_to(self, key_names: list[str] | None = None) -> None:
        targets = key_names if key_names is not None else list(self._buttons)
        for key_name in targets:
            self._key_colors[key_name] = self._brush_color
            if self._brush_color_2 != self._base_color_2 or self._brush_effect:
                self._key_colors_2[key_name] = self._brush_color_2
            else:
                self._key_colors_2.pop(key_name, None)
            if self._brush_effect:
                self._key_effects[key_name] = self._brush_effect
            else:
                self._key_effects.pop(key_name, None)
            self._refresh_button(key_name)
        self._notify_change()

    def _clear_styles(self, key_names: list[str] | None = None) -> None:
        if key_names is None:
            self._key_colors.clear()
            self._key_colors_2.clear()
            self._key_effects.clear()
            for key_name in self._buttons:
                self._refresh_button(key_name)
        else:
            for key_name in key_names:
                self._key_colors.pop(key_name, None)
                self._key_colors_2.pop(key_name, None)
                self._key_effects.pop(key_name, None)
                self._refresh_button(key_name)
        self._notify_change()

    def _on_fill_clicked(self, _button) -> None:
        if self._selected:
            self._apply_brush_to(sorted(self._selected))
        else:
            self._apply_brush_to(None)

    def _on_clear_clicked(self, _button) -> None:
        if self._selected:
            self._clear_styles(sorted(self._selected))
        else:
            self._clear_styles(None)

    def get_key_colors(self) -> dict[str, tuple[int, int, int]]:
        return dict(self._key_colors)

    def get_key_colors_2(self) -> dict[str, tuple[int, int, int]]:
        return dict(self._key_colors_2)

    def get_key_effects(self) -> dict[str, str]:
        return dict(self._key_effects)

    def get_key_styles(self) -> tuple[
        dict[str, tuple[int, int, int]],
        dict[str, tuple[int, int, int]],
        dict[str, str],
    ]:
        return self.get_key_colors(), self.get_key_colors_2(), self.get_key_effects()

    def set_key_styles(
        self,
        key_colors: dict[str, tuple[int, int, int]],
        key_colors_2: dict[str, tuple[int, int, int]],
        key_effects: dict[str, str],
        base_color: tuple[int, int, int],
        base_color_2: tuple[int, int, int],
    ) -> None:
        self._base_color = base_color
        self._base_color_2 = base_color_2
        self._key_colors = dict(key_colors)
        self._key_colors_2 = dict(key_colors_2)
        self._key_effects = dict(key_effects)
        for key_name in self._buttons:
            self._refresh_button(key_name)

    def set_lang(self, lang: str) -> None:
        self._lang = lang
        self.title_label.set_text(tr(lang, "map_title"))
        self.subtitle_label.set_text(tr(lang, "map_subtitle"))
        self.brush_picker.set_tooltip_text(tr(lang, "brush_color_1"))
        self.brush_picker_2.set_tooltip_text(tr(lang, "brush_color_2"))
        self.brush_picker.set_lang(lang)
        self.brush_picker_2.set_lang(lang)
        self._brush_effect_label.set_text(tr(lang, "brush_effect"))
        selected = self.brush_effect_dropdown.get_selected()
        labels = [tr(lang, "brush_default")] + key_effect_mode_labels(lang)
        self._brush_effect_model = Gtk.StringList.new(labels)
        self.brush_effect_dropdown.set_model(self._brush_effect_model)
        self.brush_effect_dropdown.set_selected(min(max(selected, 0), len(labels) - 1))
        self.edit_selection_btn.set_label(tr(lang, "edit_selection"))
        self.deselect_btn.set_label(tr(lang, "deselect"))
        self._refresh_selection_ui()
        for key_name in self._buttons:
            self._refresh_button(key_name)


class ScaleRow(Gtk.Box):
    def __init__(
        self,
        title: str,
        subtitle: str,
        value: float,
        minimum: float,
        maximum: float,
        step: float,
        digits: int,
        suffix: str,
        on_change,
    ) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self._digits = digits
        self._suffix = suffix
        self._on_change = on_change
        self._updating = False

        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        text_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        text_box.set_hexpand(True)
        self.title_label = Gtk.Label(label=title, xalign=0)
        self.title_label.add_css_class("title-4")
        self.subtitle_label = Gtk.Label(label=subtitle, xalign=0)
        self.subtitle_label.add_css_class("dim-label")
        text_box.append(self.title_label)
        text_box.append(self.subtitle_label)

        self.value_label = Gtk.Label(xalign=1)
        self.value_label.add_css_class("monospace")
        header.append(text_box)
        header.append(self.value_label)

        self.scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, minimum, maximum, step)
        self.scale.set_draw_value(False)
        self.scale.set_hexpand(True)
        self.scale.set_value(value)
        self.scale.connect("value-changed", self._on_value_changed)
        self._update_value_label(value)

        self.append(header)
        self.append(self.scale)

    def _update_value_label(self, value: float) -> None:
        if self._digits <= 0:
            text = f"{int(round(value))}{self._suffix}"
        else:
            text = f"{value:.{self._digits}f}{self._suffix}"
        self.value_label.set_text(text)

    def _on_value_changed(self, scale: Gtk.Scale) -> None:
        value = scale.get_value()
        self._update_value_label(value)
        if not self._updating:
            self._on_change(value)

    def get_value(self) -> float:
        return self.scale.get_value()

    def set_value(self, value: float) -> None:
        self._updating = True
        self.scale.set_value(value)
        self._update_value_label(value)
        self._updating = False

    def set_labels(self, title: str, subtitle: str) -> None:
        self.title_label.set_text(title)
        self.subtitle_label.set_text(subtitle)


class MainWindow(Adw.ApplicationWindow):
    def __init__(self, app: Adw.Application, config: Config) -> None:
        super().__init__(application=app, title="Razer Reactive")
        self.set_default_size(1280, 920)
        self.config = config
        self._lang = normalize_ui_language(config.ui_language)
        self.client = DaemonClient()
        self._daemon_available = False
        self._daemon_synced = False
        self._applying_config = False
        self._status_timer_id: int | None = None
        self._apply_timeout_id: int | None = None
        self._background_mode_handler_id: int | None = None
        self._press_mode_handler_id: int | None = None
        self._custom_key_mode_handler_id: int | None = None
        self._language_handler_id: int | None = None
        self._status_state = "offline"

        self.connect("realize", self._on_realize)

        self.toast_overlay = Adw.ToastOverlay()
        self.set_content(self.toast_overlay)

        toolbar_view = Adw.ToolbarView()
        self.toast_overlay.set_child(toolbar_view)

        header = Adw.HeaderBar()
        self.start_button = Gtk.Button(label=tr(self._lang, "start"))
        self.start_button.add_css_class("suggested-action")
        self.start_button.connect("clicked", self._on_toggle_clicked)

        self.save_button = Gtk.Button(label=tr(self._lang, "save"))
        self.save_button.connect("clicked", self._on_save_clicked)

        header.pack_start(self.save_button)
        header.pack_end(self.start_button)
        toolbar_view.add_top_bar(header)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        toolbar_view.set_content(scrolled)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18)
        content.set_margin_top(18)
        content.set_margin_bottom(24)
        content.set_margin_start(20)
        content.set_margin_end(20)
        scrolled.set_child(content)

        hero = Adw.Bin()
        hero_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        hero_card.add_css_class("card")
        hero_card.set_margin_start(18)
        hero_card.set_margin_end(18)
        hero_card.set_margin_top(18)
        hero_card.set_margin_bottom(18)
        hero_card.set_spacing(10)

        self.hero_title = Gtk.Label(label=tr(self._lang, "hero_title"), xalign=0)
        self.hero_title.add_css_class("title-1")
        self.hero_desc = Gtk.Label(
            label=tr(self._lang, "hero_desc"),
            xalign=0,
            wrap=True,
        )
        self.hero_desc.add_css_class("dim-label")

        status_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        self.status_label = Gtk.Label(label=tr(self._lang, "status_connecting"), xalign=0)
        self.status_label.add_css_class("status-pill")
        self.status_label.add_css_class("status-offline")
        self.device_label = Gtk.Label(xalign=0)
        self.device_label.add_css_class("dim-label")
        self.daemon_warning = Gtk.Label(xalign=0, wrap=True)
        self.daemon_warning.add_css_class("warning")
        self.daemon_warning.set_visible(False)
        self.keyd_warning = Gtk.Label(xalign=0, wrap=True)
        self.keyd_warning.add_css_class("warning")
        self.keyd_warning.set_visible(False)
        status_row.append(self.status_label)
        status_row.append(self.device_label)

        hero_card.append(self.hero_title)
        hero_card.append(self.hero_desc)
        hero_card.append(status_row)
        hero_card.append(self.daemon_warning)
        hero_card.append(self.keyd_warning)
        hero.set_child(hero_card)
        content.append(hero)

        # Language
        lang_group = Adw.PreferencesGroup(title=tr(self._lang, "language"))
        self.language_row = Adw.ComboRow()
        self.language_row.set_title(tr(self._lang, "language"))
        self.language_row.set_subtitle(tr(self._lang, "language_subtitle"))
        self.language_row.set_model(
            Gtk.StringList.new([tr(self._lang, "lang_en"), tr(self._lang, "lang_pl")])
        )
        self.language_row.set_selected(0 if self._lang == "en" else 1)
        self._language_handler_id = self.language_row.connect(
            "notify::selected", self._on_language_changed
        )
        lang_group.add(self.language_row)
        content.append(lang_group)

        # Profiles
        self.profiles_group = Adw.PreferencesGroup(
            title=tr(self._lang, "profiles_title"),
            description=tr(self._lang, "profiles_desc"),
        )
        self.profile_name_row = Adw.EntryRow()
        self.profile_name_row.set_title(tr(self._lang, "profile_name"))
        self.profiles_group.add(self.profile_name_row)

        self.profile_combo_row = Adw.ComboRow()
        self.profile_combo_row.set_title(tr(self._lang, "saved_profiles"))
        self._profile_model = Gtk.StringList()
        self.profile_combo_row.set_model(self._profile_model)
        self.profiles_group.add(self.profile_combo_row)

        self.profile_actions_row = Adw.ActionRow()
        self.profile_actions_row.set_title(tr(self._lang, "manage_profiles"))
        self.profile_actions_row.set_subtitle(tr(self._lang, "manage_profiles_sub"))

        profile_btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        profile_btn_box.set_valign(Gtk.Align.CENTER)

        self.save_profile_btn = Gtk.Button(label=tr(self._lang, "save"))
        self.save_profile_btn.add_css_class("suggested-action")
        self.save_profile_btn.connect("clicked", self._on_save_profile_clicked)
        profile_btn_box.append(self.save_profile_btn)

        self.load_profile_btn = Gtk.Button(label=tr(self._lang, "load"))
        self.load_profile_btn.connect("clicked", self._on_load_profile_clicked)
        profile_btn_box.append(self.load_profile_btn)

        self.delete_profile_btn = Gtk.Button(label=tr(self._lang, "delete"))
        self.delete_profile_btn.add_css_class("destructive-action")
        self.delete_profile_btn.connect("clicked", self._on_delete_profile_clicked)
        profile_btn_box.append(self.delete_profile_btn)

        self.profile_actions_row.add_suffix(profile_btn_box)
        self.profiles_group.add(self.profile_actions_row)
        content.append(self.profiles_group)
        self._refresh_profile_list()

        # Background
        self.background_group = Adw.PreferencesGroup(
            title=tr(self._lang, "background_title"),
            description=tr(self._lang, "background_desc"),
        )
        self.background_mode_row = Adw.ComboRow()
        self.background_mode_row.set_title(tr(self._lang, "bg_mode"))
        self.background_mode_row.set_subtitle(tr(self._lang, "bg_mode_sub"))
        self.background_mode_row.set_model(
            Gtk.StringList.new(background_mode_labels(self._lang))
        )
        try:
            mode_index = BACKGROUND_MODES.index(config.background_mode)
        except ValueError:
            mode_index = 0
        self.background_mode_row.set_selected(mode_index)
        self._background_mode_handler_id = self.background_mode_row.connect(
            "notify::selected",
            self._on_background_mode_changed,
        )
        self.background_group.add(self.background_mode_row)

        self.base_color_row = ColorRow(
            tr(self._lang, "base_color_1"),
            tr(self._lang, "base_color_1_sub"),
            config.base_color,
            self._on_config_changed,
            self,
            self._lang,
        )
        self.base_color_2_row = ColorRow(
            tr(self._lang, "base_color_2"),
            tr(self._lang, "base_color_2_sub"),
            config.base_color_2,
            self._on_config_changed,
            self,
            self._lang,
        )
        self.background_speed_row = ScaleRow(
            tr(self._lang, "anim_speed"),
            tr(self._lang, "anim_speed_sub"),
            config.background_speed,
            0.05,
            5.0,
            0.05,
            2,
            "×",
            self._on_config_changed,
        )
        self.background_group.add(self.base_color_row)
        self.background_group.add(self.base_color_2_row)
        self.background_group.add(self.background_speed_row)
        content.append(self.background_group)

        # Custom keys + map
        self.key_editor_group = Adw.PreferencesGroup(
            title=tr(self._lang, "custom_keys_title"),
            description=tr(self._lang, "custom_keys_desc"),
        )
        self.custom_key_mode_row = Adw.ComboRow()
        self.custom_key_mode_row.set_title(tr(self._lang, "custom_key_mode"))
        self.custom_key_mode_row.set_subtitle(tr(self._lang, "custom_key_mode_sub"))
        self.custom_key_mode_row.set_model(
            Gtk.StringList.new(custom_key_mode_labels(self._lang))
        )
        try:
            custom_mode_index = CUSTOM_KEY_MODES.index(config.custom_key_mode)
        except ValueError:
            custom_mode_index = 0
        self.custom_key_mode_row.set_selected(custom_mode_index)
        self._custom_key_mode_handler_id = self.custom_key_mode_row.connect(
            "notify::selected",
            self._on_custom_key_mode_changed,
        )
        self.key_editor_group.add(self.custom_key_mode_row)
        content.append(self.key_editor_group)

        # Map outside PreferencesGroup — Adw list styling can block clicks on custom children.
        self.keyboard_editor = KeyboardColorEditor(
            config, self._on_key_colors_changed, self, self._lang
        )
        map_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        map_card.add_css_class("card")
        map_card.set_margin_start(0)
        map_card.set_margin_end(0)
        map_inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        map_inner.set_margin_top(12)
        map_inner.set_margin_bottom(12)
        map_inner.set_margin_start(12)
        map_inner.set_margin_end(12)
        map_inner.append(self.keyboard_editor)
        map_card.append(map_inner)
        content.append(map_card)

        # Press
        self.colors_group = Adw.PreferencesGroup(
            title=tr(self._lang, "press_title"),
            description=tr(self._lang, "press_desc"),
        )
        self.press_mode_row = Adw.ComboRow()
        self.press_mode_row.set_title(tr(self._lang, "press_mode"))
        self.press_mode_row.set_subtitle(tr(self._lang, "press_mode_sub"))
        self.press_mode_row.set_model(Gtk.StringList.new(press_mode_labels(self._lang)))
        try:
            press_mode_index = PRESS_MODES.index(config.press_mode)
        except ValueError:
            press_mode_index = 0
        self.press_mode_row.set_selected(press_mode_index)
        self._press_mode_handler_id = self.press_mode_row.connect(
            "notify::selected",
            self._on_press_mode_changed,
        )
        self.colors_group.add(self.press_mode_row)

        self.press_color_row = ColorRow(
            tr(self._lang, "press_color_1"),
            tr(self._lang, "press_color_1_sub"),
            config.press_color,
            self._on_config_changed,
            self,
            self._lang,
        )
        self.press_color_2_row = ColorRow(
            tr(self._lang, "press_color_2"),
            tr(self._lang, "press_color_2_sub"),
            config.press_color_2,
            self._on_config_changed,
            self,
            self._lang,
        )
        self.colors_group.add(self.press_color_row)
        self.colors_group.add(self.press_color_2_row)
        content.append(self.colors_group)

        # Timing
        self.timing_group = Adw.PreferencesGroup(
            title=tr(self._lang, "timing_title"),
            description=tr(self._lang, "timing_desc"),
        )
        self.hold_row = ScaleRow(
            tr(self._lang, "hold"),
            tr(self._lang, "hold_sub"),
            config.hold_seconds,
            0.0,
            10.0,
            0.1,
            1,
            " s",
            self._on_config_changed,
        )
        self.fade_row = ScaleRow(
            tr(self._lang, "fade"),
            tr(self._lang, "fade_sub"),
            config.fade_seconds,
            0.0,
            5.0,
            0.1,
            1,
            " s",
            self._on_config_changed,
        )
        self.timing_group.add(self.hold_row)
        self.timing_group.add(self.fade_row)
        content.append(self.timing_group)

        # Lock indicators
        self.indicators_group = Adw.PreferencesGroup(
            title=tr(self._lang, "indicators_title"),
            description=tr(self._lang, "indicators_desc"),
        )
        self.caps_lock_row = Adw.SwitchRow()
        self.caps_lock_row.set_title(tr(self._lang, "caps_lock"))
        self.caps_lock_row.set_subtitle(tr(self._lang, "caps_lock_sub"))
        self.caps_lock_row.set_active(config.caps_lock_indicator)
        self.caps_lock_row.connect("notify::active", lambda *_args: self._on_config_changed(None))
        self.indicators_group.add(self.caps_lock_row)
        self.caps_lock_color_row = ColorRow(
            tr(self._lang, "caps_lock_color"),
            tr(self._lang, "caps_lock_color_sub"),
            config.caps_lock_color,
            self._on_config_changed,
            self,
            self._lang,
        )
        self.indicators_group.add(self.caps_lock_color_row)
        content.append(self.indicators_group)

        # Display
        self.display_group = Adw.PreferencesGroup(title=tr(self._lang, "display_title"))
        self.brightness_row = ScaleRow(
            tr(self._lang, "brightness"),
            tr(self._lang, "brightness_sub"),
            config.brightness,
            0,
            100,
            1,
            0,
            "%",
            self._on_config_changed,
        )
        self.fps_row = ScaleRow(
            tr(self._lang, "fps"),
            tr(self._lang, "fps_sub"),
            config.fps,
            10,
            60,
            1,
            0,
            " FPS",
            self._on_config_changed,
        )
        self.display_group.add(self.brightness_row)
        self.display_group.add(self.fps_row)
        content.append(self.display_group)

        # Actions
        self.actions_group = Adw.PreferencesGroup(
            title=tr(self._lang, "actions_title"),
            description=tr(self._lang, "actions_desc"),
        )
        actions_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.turn_off_button = Gtk.Button(label=tr(self._lang, "turn_off"))
        self.turn_off_button.add_css_class("destructive-action")
        self.turn_off_button.add_css_class("action-button")
        self.turn_off_button.connect("clicked", self._on_turn_off_clicked)
        self.reset_button = Gtk.Button(label=tr(self._lang, "reset_settings"))
        self.reset_button.add_css_class("action-button")
        self.reset_button.connect("clicked", self._on_reset_clicked)
        actions_box.append(self.turn_off_button)
        actions_box.append(self.reset_button)
        self.actions_group.add(actions_box)
        content.append(self.actions_group)

        self.connect("close-request", self._on_close_request)
        self._update_background_mode_visibility()
        self._update_press_mode_visibility()
        self._connect_daemon()
        self._update_keyd_warning()

    def _t(self, key: str, **kwargs) -> str:
        return tr(self._lang, key, **kwargs)

    def _show_toast(self, text: str) -> None:
        self.toast_overlay.add_toast(Adw.Toast.new(text))

    def _on_language_changed(self, _row, _pspec) -> None:
        if self._applying_config:
            return
        idx = self.language_row.get_selected()
        lang = "en" if idx <= 0 else "pl"
        if lang == self._lang:
            return
        self._lang = lang
        self._apply_language()
        self._on_config_changed(None)

    def _apply_language(self) -> None:
        lang = self._lang
        self.set_title(tr(lang, "app_title"))
        self.save_button.set_label(tr(lang, "save"))
        self.hero_title.set_text(tr(lang, "hero_title"))
        self.hero_desc.set_text(tr(lang, "hero_desc"))

        if self._language_handler_id is not None:
            self.language_row.handler_block(self._language_handler_id)
        self.language_row.set_title(tr(lang, "language"))
        self.language_row.set_subtitle(tr(lang, "language_subtitle"))
        selected = self.language_row.get_selected()
        self.language_row.set_model(
            Gtk.StringList.new([tr(lang, "lang_en"), tr(lang, "lang_pl")])
        )
        self.language_row.set_selected(selected)
        if self._language_handler_id is not None:
            self.language_row.handler_unblock(self._language_handler_id)

        self.profiles_group.set_title(tr(lang, "profiles_title"))
        self.profiles_group.set_description(tr(lang, "profiles_desc"))
        self.profile_name_row.set_title(tr(lang, "profile_name"))
        self.profile_combo_row.set_title(tr(lang, "saved_profiles"))
        self.profile_actions_row.set_title(tr(lang, "manage_profiles"))
        self.profile_actions_row.set_subtitle(tr(lang, "manage_profiles_sub"))
        self.save_profile_btn.set_label(tr(lang, "save"))
        self.load_profile_btn.set_label(tr(lang, "load"))
        self.delete_profile_btn.set_label(tr(lang, "delete"))

        self.background_group.set_title(tr(lang, "background_title"))
        self.background_group.set_description(tr(lang, "background_desc"))
        self._retranslate_mode_row(
            self.background_mode_row,
            BACKGROUND_MODES,
            background_mode_labels(lang),
            tr(lang, "bg_mode"),
            tr(lang, "bg_mode_sub"),
            self._background_mode_handler_id,
        )
        self.base_color_row.set_labels(tr(lang, "base_color_1"), tr(lang, "base_color_1_sub"))
        self.base_color_row.set_lang(lang)
        self.base_color_2_row.set_labels(tr(lang, "base_color_2"), tr(lang, "base_color_2_sub"))
        self.base_color_2_row.set_lang(lang)
        self.background_speed_row.set_labels(tr(lang, "anim_speed"), tr(lang, "anim_speed_sub"))

        self.key_editor_group.set_title(tr(lang, "custom_keys_title"))
        self.key_editor_group.set_description(tr(lang, "custom_keys_desc"))
        self._retranslate_mode_row(
            self.custom_key_mode_row,
            CUSTOM_KEY_MODES,
            custom_key_mode_labels(lang),
            tr(lang, "custom_key_mode"),
            tr(lang, "custom_key_mode_sub"),
            self._custom_key_mode_handler_id,
        )
        self.keyboard_editor.set_lang(lang)

        self.colors_group.set_title(tr(lang, "press_title"))
        self.colors_group.set_description(tr(lang, "press_desc"))
        self._retranslate_mode_row(
            self.press_mode_row,
            PRESS_MODES,
            press_mode_labels(lang),
            tr(lang, "press_mode"),
            tr(lang, "press_mode_sub"),
            self._press_mode_handler_id,
        )
        self.press_color_row.set_labels(tr(lang, "press_color_1"), tr(lang, "press_color_1_sub"))
        self.press_color_row.set_lang(lang)
        self.press_color_2_row.set_labels(tr(lang, "press_color_2"), tr(lang, "press_color_2_sub"))
        self.press_color_2_row.set_lang(lang)

        self.timing_group.set_title(tr(lang, "timing_title"))
        self.timing_group.set_description(tr(lang, "timing_desc"))
        self.hold_row.set_labels(tr(lang, "hold"), tr(lang, "hold_sub"))
        self.fade_row.set_labels(tr(lang, "fade"), tr(lang, "fade_sub"))

        self.indicators_group.set_title(tr(lang, "indicators_title"))
        self.indicators_group.set_description(tr(lang, "indicators_desc"))
        self.caps_lock_row.set_title(tr(lang, "caps_lock"))
        self.caps_lock_row.set_subtitle(tr(lang, "caps_lock_sub"))
        self.caps_lock_color_row.set_labels(tr(lang, "caps_lock_color"), tr(lang, "caps_lock_color_sub"))
        self.caps_lock_color_row.set_lang(lang)

        self.display_group.set_title(tr(lang, "display_title"))
        self.brightness_row.set_labels(tr(lang, "brightness"), tr(lang, "brightness_sub"))
        self.fps_row.set_labels(tr(lang, "fps"), tr(lang, "fps_sub"))

        self.actions_group.set_title(tr(lang, "actions_title"))
        self.actions_group.set_description(tr(lang, "actions_desc"))
        self.turn_off_button.set_label(tr(lang, "turn_off"))
        self.reset_button.set_label(tr(lang, "reset_settings"))

        self._set_status_ui(self._status_state)
        self._update_keyd_warning()

    def _retranslate_mode_row(
        self,
        row: Adw.ComboRow,
        modes: tuple[str, ...],
        labels: list[str],
        title: str,
        subtitle: str,
        handler_id: int | None,
    ) -> None:
        selected = row.get_selected()
        if handler_id is not None:
            row.handler_block(handler_id)
        row.set_title(title)
        row.set_subtitle(subtitle)
        row.set_model(Gtk.StringList.new(labels))
        if 0 <= selected < len(modes):
            row.set_selected(selected)
        if handler_id is not None:
            row.handler_unblock(handler_id)

    def _refresh_profile_list(self, select_name: str | None = None) -> None:
        names = sorted(load_profiles().keys())
        self._profile_model.splice(0, self._profile_model.get_n_items())
        for name in names:
            self._profile_model.append(name)
        if select_name and select_name in names:
            self.profile_combo_row.set_selected(names.index(select_name))
        elif names:
            self.profile_combo_row.set_selected(0)

    def _on_save_profile_clicked(self, _button) -> None:
        name = self.profile_name_row.get_text().strip()
        if not name:
            self._show_toast(self._t("toast_profile_name"))
            return
        try:
            save_profile(name, self._current_config())
            self._refresh_profile_list(select_name=name)
            self._show_toast(self._t("toast_profile_saved", name=name))
        except Exception as exc:
            self._show_toast(self._t("toast_profile_save_fail", err=exc))

    def _on_load_profile_clicked(self, _button) -> None:
        idx = self.profile_combo_row.get_selected()
        if idx < 0 or idx >= self._profile_model.get_n_items():
            self._show_toast(self._t("toast_pick_profile"))
            return
        name = self._profile_model.get_string(idx)
        config = get_profile(name, keyboard_name=self.config.keyboard_name)
        if config is None:
            self._show_toast(self._t("toast_profile_missing", name=name))
            self._refresh_profile_list()
            return

        self._daemon_synced = False
        self.config = config
        self._load_config_into_ui(config)
        self.profile_name_row.set_text(name)
        self._daemon_synced = True
        self._schedule_apply()
        self._show_toast(self._t("toast_profile_loaded", name=name))

    def _on_delete_profile_clicked(self, _button) -> None:
        idx = self.profile_combo_row.get_selected()
        if idx < 0 or idx >= self._profile_model.get_n_items():
            self._show_toast(self._t("toast_pick_delete"))
            return
        name = self._profile_model.get_string(idx)
        if is_factory_profile(name):
            self._show_toast(self._t("toast_factory_profile", name=name))
            return

        dialog = Adw.MessageDialog(
            transient_for=self,
            heading=self._t("delete_profile_heading", name=name),
            body=self._t("delete_profile_body"),
        )
        dialog.add_response("cancel", self._t("cancel"))
        dialog.add_response("delete", self._t("delete"))
        dialog.set_response_appearance("delete", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_default_response("cancel")
        dialog.set_close_response("cancel")
        dialog.connect("response", self._on_delete_profile_response, name)
        dialog.present()

    def _on_delete_profile_response(self, _dialog, response: str, name: str) -> None:
        if response != "delete":
            return
        result = delete_profile(name)
        self._refresh_profile_list()
        if result == "deleted":
            self._show_toast(self._t("toast_profile_deleted", name=name))
        elif result == "restored":
            self._show_toast(self._t("toast_factory_restored", name=name))
        elif result == "factory":
            self._show_toast(self._t("toast_factory_profile", name=name))
        else:
            self._show_toast(self._t("toast_profile_missing", name=name))

    def _connect_daemon(self) -> None:
        def worker() -> None:
            try:
                if not self.client.is_available():
                    GLib.idle_add(self._on_daemon_offline)
                    return

                status = self.client.status()
                config = self.client.get_config()
                GLib.idle_add(self._on_daemon_ready, status, config)
            except Exception as exc:
                GLib.idle_add(self._on_daemon_error, str(exc))

        threading.Thread(target=worker, name="connect-daemon", daemon=True).start()

    def _on_daemon_offline(self) -> None:
        self._daemon_available = False
        self._set_status_ui("offline")
        self.device_label.set_text("")
        self.daemon_warning.set_text(self._t("daemon_offline"))
        self.daemon_warning.set_visible(True)
        self._set_actions_sensitive(False)

    def _on_daemon_error(self, message: str) -> None:
        self._daemon_available = False
        self._set_status_ui("offline")
        self.device_label.set_text("")
        self.daemon_warning.set_text(self._t("daemon_error", err=message))
        self.daemon_warning.set_visible(True)
        self._set_actions_sensitive(False)

    def _set_actions_sensitive(self, enabled: bool) -> None:
        self.start_button.set_sensitive(enabled)
        self.turn_off_button.set_sensitive(enabled)
        self.reset_button.set_sensitive(enabled)

    def _on_daemon_ready(self, status: dict, config: Config) -> None:
        self._daemon_available = True
        self._daemon_synced = False
        self.config = config
        self._load_config_into_ui(config)
        self._daemon_synced = True
        self._apply_status(status)
        keyboard = status.get("keyboard", "")
        source = status.get("input_source", "")
        if keyboard and source:
            self.device_label.set_text(f"{keyboard} · {source}")
        elif keyboard:
            self.device_label.set_text(keyboard)
        else:
            self.device_label.set_text(self._t("device_openrazer"))
        self.daemon_warning.set_visible(False)
        self._set_actions_sensitive(True)
        self._start_status_polling()

    def _load_config_into_ui(self, config: Config) -> None:
        self._applying_config = True
        if self._apply_timeout_id is not None:
            GLib.source_remove(self._apply_timeout_id)
            self._apply_timeout_id = None

        if self._background_mode_handler_id is not None:
            self.background_mode_row.handler_block(self._background_mode_handler_id)
        if self._press_mode_handler_id is not None:
            self.press_mode_row.handler_block(self._press_mode_handler_id)
        if self._custom_key_mode_handler_id is not None:
            self.custom_key_mode_row.handler_block(self._custom_key_mode_handler_id)
        if self._language_handler_id is not None:
            self.language_row.handler_block(self._language_handler_id)
        try:
            self._lang = normalize_ui_language(config.ui_language)
            self.language_row.set_selected(0 if self._lang == "en" else 1)
            self._apply_language()

            self.base_color_row.set_color(config.base_color)
            self.base_color_2_row.set_color(config.base_color_2)
            self.press_color_row.set_color(config.press_color)
            self.press_color_2_row.set_color(config.press_color_2)
            self.hold_row.set_value(config.hold_seconds)
            self.fade_row.set_value(config.fade_seconds)
            self.caps_lock_row.set_active(config.caps_lock_indicator)
            self.caps_lock_color_row.set_color(config.caps_lock_color)
            self.brightness_row.set_value(config.brightness)
            self.fps_row.set_value(config.fps)
            self.background_speed_row.set_value(config.background_speed)
            self.keyboard_editor.set_key_styles(
                config.key_colors,
                config.key_colors_2,
                config.key_effects,
                config.base_color,
                config.base_color_2,
            )
            try:
                mode_index = BACKGROUND_MODES.index(config.background_mode)
            except ValueError:
                mode_index = 0
            self.background_mode_row.set_selected(mode_index)
            try:
                press_mode_index = PRESS_MODES.index(config.press_mode)
            except ValueError:
                press_mode_index = 0
            self.press_mode_row.set_selected(press_mode_index)
            try:
                custom_mode_index = CUSTOM_KEY_MODES.index(config.custom_key_mode)
            except ValueError:
                custom_mode_index = 0
            self.custom_key_mode_row.set_selected(custom_mode_index)
            self._update_background_mode_visibility()
            self._update_press_mode_visibility()
        finally:
            if self._background_mode_handler_id is not None:
                self.background_mode_row.handler_unblock(self._background_mode_handler_id)
            if self._press_mode_handler_id is not None:
                self.press_mode_row.handler_unblock(self._press_mode_handler_id)
            if self._custom_key_mode_handler_id is not None:
                self.custom_key_mode_row.handler_unblock(self._custom_key_mode_handler_id)
            if self._language_handler_id is not None:
                self.language_row.handler_unblock(self._language_handler_id)
            self._applying_config = False

    def _start_status_polling(self) -> None:
        if self._status_timer_id is not None:
            return

        def poll() -> bool:
            if not self._daemon_available:
                return False
            try:
                status = self.client.status()
                self._apply_status(status)
                keyboard = status.get("keyboard", "")
                source = status.get("input_source", "")
                if keyboard and source:
                    self.device_label.set_text(f"{keyboard} · {source}")
            except Exception:
                self._daemon_available = False
                self._set_status_ui("offline")
                self.daemon_warning.set_text(self._t("daemon_lost"))
                self.daemon_warning.set_visible(True)
                self._set_actions_sensitive(False)
                return False
            return True

        self._status_timer_id = GLib.timeout_add_seconds(2, poll)

    def _update_keyd_warning(self) -> None:
        if not is_keyd_running():
            self.keyd_warning.set_visible(False)
            return

        if can_access_keyd_socket() or user_in_group("keyd"):
            self.keyd_warning.set_visible(False)
            return

        self.keyd_warning.set_text(self._t("keyd_help"))
        self.keyd_warning.set_visible(True)

    def _selected_mode(self, row: Adw.ComboRow, modes: tuple[str, ...]) -> str:
        index = row.get_selected()
        if index < 0 or index >= len(modes):
            return "static"
        return modes[index]

    def _current_config(self) -> Config:
        return Config(
            base_color=self.base_color_row.get_color(),
            base_color_2=self.base_color_2_row.get_color(),
            press_color=self.press_color_row.get_color(),
            press_color_2=self.press_color_2_row.get_color(),
            hold_seconds=self.hold_row.get_value(),
            fade_seconds=self.fade_row.get_value(),
            brightness=int(self.brightness_row.get_value()),
            fps=int(self.fps_row.get_value()),
            keyboard_name=self.config.keyboard_name,
            background_mode=self._selected_mode(self.background_mode_row, BACKGROUND_MODES),
            background_speed=self.background_speed_row.get_value(),
            press_mode=self._selected_mode(self.press_mode_row, PRESS_MODES),
            custom_key_mode=self._selected_mode(self.custom_key_mode_row, CUSTOM_KEY_MODES),
            keyboard_layout=self.config.keyboard_layout,
            ui_language=self._lang,
            key_colors=self.keyboard_editor.get_key_colors(),
            key_colors_2=self.keyboard_editor.get_key_colors_2(),
            key_effects=self.keyboard_editor.get_key_effects(),
            caps_lock_indicator=self.caps_lock_row.get_active(),
            caps_lock_color=self.caps_lock_color_row.get_color(),
        )

    def _schedule_apply(self) -> None:
        if self._applying_config or not self._daemon_synced or not self._daemon_available:
            return

        if self._apply_timeout_id is not None:
            GLib.source_remove(self._apply_timeout_id)

        self._apply_timeout_id = GLib.timeout_add(400, self._apply_config_now)

    def _apply_config_now(self) -> bool:
        self._apply_timeout_id = None
        if not self._daemon_synced or not self._daemon_available:
            return False

        self.config = self._current_config()

        def worker() -> None:
            try:
                response = self.client.update_config(self.config)
                if not response.get("ok"):
                    GLib.idle_add(
                        self._show_toast,
                        response.get("error", self._t("toast_update_error")),
                    )
            except Exception as exc:
                GLib.idle_add(self._show_toast, self._t("toast_error", err=exc))

        threading.Thread(target=worker, name="apply-config", daemon=True).start()
        return False

    def _on_background_mode_changed(self, _row, _pspec) -> None:
        self._update_background_mode_visibility()
        self._on_config_changed(None)

    def _on_press_mode_changed(self, _row, _pspec) -> None:
        self._update_press_mode_visibility()
        self._on_config_changed(None)

    def _on_custom_key_mode_changed(self, _row, _pspec) -> None:
        self._on_config_changed(None)

    def _update_background_mode_visibility(self) -> None:
        mode = self._selected_mode(self.background_mode_row, BACKGROUND_MODES)
        self.base_color_2_row.set_visible(mode in MODES_WITH_COLOR_2)

    def _update_press_mode_visibility(self) -> None:
        mode = self._selected_mode(self.press_mode_row, PRESS_MODES)
        self.press_color_2_row.set_visible(mode in MODES_WITH_COLOR_2)

    def _on_key_colors_changed(self, _colors) -> None:
        self._on_config_changed(None)

    def _on_config_changed(self, _value) -> None:
        self.keyboard_editor.set_key_styles(
            self.keyboard_editor.get_key_colors(),
            self.keyboard_editor.get_key_colors_2(),
            self.keyboard_editor.get_key_effects(),
            self.base_color_row.get_color(),
            self.base_color_2_row.get_color(),
        )
        self._schedule_apply()

    def _apply_status(self, status: dict) -> None:
        if status.get("running"):
            self._set_status_ui("running")
        elif status.get("turned_off"):
            self._set_status_ui("off")
        else:
            self._set_status_ui("stopped")

    def _set_status_ui(self, state: str) -> None:
        self._status_state = state
        self.status_label.remove_css_class("status-running")
        self.status_label.remove_css_class("status-stopped")
        self.status_label.remove_css_class("status-offline")
        self.status_label.remove_css_class("status-off")

        if state == "running":
            self.status_label.set_text(self._t("status_running"))
            self.status_label.add_css_class("status-running")
            self.start_button.set_label(self._t("stop"))
            self.start_button.remove_css_class("suggested-action")
            self.start_button.add_css_class("destructive-action")
        elif state == "off":
            self.status_label.set_text(self._t("status_off"))
            self.status_label.add_css_class("status-off")
            self.start_button.set_label(self._t("start"))
            self.start_button.remove_css_class("destructive-action")
            self.start_button.add_css_class("suggested-action")
        elif state == "stopped":
            self.status_label.set_text(self._t("status_stopped"))
            self.status_label.add_css_class("status-stopped")
            self.start_button.set_label(self._t("start"))
            self.start_button.remove_css_class("destructive-action")
            self.start_button.add_css_class("suggested-action")
        else:
            self.status_label.set_text(self._t("status_offline"))
            self.status_label.add_css_class("status-offline")
            self.start_button.set_label(self._t("start"))
            self.start_button.remove_css_class("destructive-action")
            self.start_button.add_css_class("suggested-action")

    def _on_toggle_clicked(self, _button) -> None:
        if not self._daemon_available:
            self._show_toast(self._t("toast_daemon_down"))
            return

        self.config = self._current_config()

        def worker() -> None:
            try:
                status = self.client.status()
                if status.get("running"):
                    response = self.client.stop_lighting()
                    message = self._t("toast_stopped")
                    running = False
                else:
                    self.client.update_config(self.config)
                    response = self.client.start_lighting()
                    message = self._t("toast_started")
                    running = True

                if not response.get("ok"):
                    GLib.idle_add(
                        self._show_toast,
                        response.get("error", self._t("toast_op_failed")),
                    )
                    return

                GLib.idle_add(self._on_toggle_done, running, message)
            except Exception as exc:
                GLib.idle_add(self._show_toast, self._t("toast_failed", err=exc))

        threading.Thread(target=worker, name="toggle-lighting", daemon=True).start()

    def _on_toggle_done(self, running: bool, message: str) -> None:
        self._set_status_ui("running" if running else "stopped")
        self._show_toast(message)

    def _on_turn_off_clicked(self, _button) -> None:
        if not self._daemon_available:
            self._show_toast(self._t("toast_daemon_down"))
            return

        def worker() -> None:
            try:
                response = self.client.turn_off_lighting()
                if not response.get("ok"):
                    GLib.idle_add(
                        self._show_toast,
                        response.get("error", self._t("toast_turn_off_fail")),
                    )
                    return
                GLib.idle_add(self._on_turn_off_done)
            except Exception as exc:
                GLib.idle_add(self._show_toast, self._t("toast_failed", err=exc))

        threading.Thread(target=worker, name="turn-off-lighting", daemon=True).start()

    def _on_turn_off_done(self) -> None:
        self._set_status_ui("off")
        self._show_toast(self._t("toast_turned_off"))

    def _on_reset_clicked(self, _button) -> None:
        if not self._daemon_available:
            self._show_toast(self._t("toast_daemon_down"))
            return

        dialog = Adw.MessageDialog(
            transient_for=self,
            heading=self._t("reset_heading"),
            body=self._t("reset_body"),
        )
        dialog.add_response("cancel", self._t("cancel"))
        dialog.add_response("reset", self._t("reset"))
        dialog.set_response_appearance("reset", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_default_response("cancel")
        dialog.set_close_response("cancel")
        dialog.connect("response", self._on_reset_dialog_response)
        dialog.present()

    def _on_reset_dialog_response(self, dialog, response: str) -> None:
        if response != "reset" or not self._daemon_available:
            return

        self._daemon_synced = False

        def worker() -> None:
            try:
                result = self.client.reset_config()
                if not result.get("ok"):
                    GLib.idle_add(
                        self._show_toast,
                        result.get("error", self._t("toast_reset_fail")),
                    )
                    GLib.idle_add(setattr, self, "_daemon_synced", True)
                    return

                config = config_from_dict(result["config"])
                GLib.idle_add(self._on_reset_done, config)
            except Exception as exc:
                GLib.idle_add(self._show_toast, self._t("toast_failed", err=exc))
                GLib.idle_add(setattr, self, "_daemon_synced", True)

        threading.Thread(target=worker, name="reset-config", daemon=True).start()

    def _on_reset_done(self, config: Config) -> None:
        self.config = config
        self._load_config_into_ui(config)
        self._daemon_synced = True
        try:
            self._apply_status(self.client.status())
        except Exception:
            self._set_status_ui("stopped")
        self._show_toast(self._t("toast_reset_done"))

    def _on_save_clicked(self, _button) -> None:
        self.config = self._current_config()
        path = save_config(self.config)

        if self._daemon_available:
            def worker() -> None:
                try:
                    self.client.set_config(self.config)
                    GLib.idle_add(
                        self._show_toast,
                        self._t("toast_saved_applied", path=path),
                    )
                except Exception as exc:
                    GLib.idle_add(
                        self._show_toast,
                        self._t("toast_saved_ipc", err=exc),
                    )

            threading.Thread(target=worker, name="save-config", daemon=True).start()
        else:
            self._show_toast(self._t("toast_saved", path=path))

    def _on_realize(self, _widget) -> None:
        self.maximize()

    def _on_close_request(self, _window) -> bool:
        self._show_toast(self._t("toast_still_running"))
        return False


class RazerReactiveApplication(Adw.Application):
    def __init__(self) -> None:
        super().__init__(application_id=APP_ID)
        self.window: MainWindow | None = None

        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(APP_CSS)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

    def do_activate(self) -> None:
        if self.window is not None:
            self.window.present()
            return

        config_path = default_config_path()
        try:
            config = load_config(config_path)
        except FileNotFoundError:
            config = load_config(Path(__file__).with_name("config.toml"))

        self.window = MainWindow(self, config)
        self.window.connect("destroy", self._on_window_destroy)
        self.window.present()

    def _on_window_destroy(self, _window) -> None:
        self.window = None


def run_gui(argv: list[str] | None = None) -> int:
    app = RazerReactiveApplication()
    return app.run(argv if argv is not None else [sys.argv[0]])


if __name__ == "__main__":
    raise SystemExit(run_gui())
