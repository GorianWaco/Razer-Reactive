#!/bin/bash
# Razer Reactive — odinstalowanie.
set -uo pipefail

APP_NAME="razer-reactive"
USER_NAME="${SUDO_USER:-${USER:-$(id -un)}}"
USER_HOME="$(getent passwd "$USER_NAME" | cut -d: -f6)"
INSTALL_DIR="$USER_HOME/.local/share/$APP_NAME"
BIN_DIR="$USER_HOME/.local/bin"

step() { echo ""; echo "→ $*"; }
ok() { echo "   ✓ $*"; }

as_user() {
    runuser -u "$USER_NAME" -- env HOME="$USER_HOME" USER="$USER_NAME" "$@"
}

user_runtime() {
    echo "/run/user/$(id -u "$USER_NAME")"
}

[ "$(id -u)" -eq 0 ] || { echo "Uruchom: sudo ./uninstall.sh"; exit 1; }

echo "══════════════════════════════════════"
echo "  Razer Reactive — odinstalowanie"
echo "══════════════════════════════════════"

step "Zatrzymanie usługi"
rt="$(user_runtime)"
bus="${rt}/bus"
if [ -S "$bus" ]; then
    as_user XDG_RUNTIME_DIR="$rt" DBUS_SESSION_BUS_ADDRESS="unix:path=${bus}" \
        systemctl --user disable --now razer-reactive.service 2>/dev/null || true
    as_user XDG_RUNTIME_DIR="$rt" DBUS_SESSION_BUS_ADDRESS="unix:path=${bus}" \
        systemctl --user daemon-reload 2>/dev/null || true
fi
rm -f "$USER_HOME/.config/systemd/user/razer-reactive.service"
ok "razer-reactive.service"

step "Usuwanie plików programu"
rm -f "$BIN_DIR/razer-reactive" "$BIN_DIR/razer-reactive-gui"
rm -rf "$INSTALL_DIR"
rm -f "$USER_HOME/.local/share/applications/razer-reactive.desktop"
for desktop in "$USER_HOME/Pulpit/Razer Reactive.desktop" "$USER_HOME/Desktop/Razer Reactive.desktop"; do
    rm -f "$desktop"
done
ok "program i skróty"

echo ""
echo "✓ Odinstalowano Razer Reactive."
echo "  Konfiguracja zachowana: $USER_HOME/.config/$APP_NAME/"
echo "  (usuń ręcznie, jeśli nie potrzebujesz)"
echo ""