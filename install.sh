#!/bin/bash
# Razer Reactive — install on a typical Linux desktop (Arch, Fedora, Debian/Ubuntu, openSUSE).
set -uo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_NAME="razer-reactive"
USER_NAME="${SUDO_USER:-${USER:-$(id -un)}}"
USER_HOME="$(getent passwd "$USER_NAME" | cut -d: -f6)"
INSTALL_DIR="$USER_HOME/.local/share/$APP_NAME"
CONFIG_DIR="$USER_HOME/.config/$APP_NAME"
BIN_DIR="$USER_HOME/.local/bin"
SKIP_PACKAGES=0
GROUPS=(openrazer plugdev input keyd)

for arg in "$@"; do
    case "$arg" in
        --skip-packages) SKIP_PACKAGES=1 ;;
        -h|--help)
            echo "Usage: sudo ./install.sh [--skip-packages]"
            echo "  --skip-packages   only copy the app (OpenRazer already installed)"
            exit 0
            ;;
    esac
done

step() { echo ""; echo "→ $*"; }
ok() { echo "   ✓ $*"; }
warn() { echo "   ! $*"; }
fail() { echo "❌ $*"; exit 1; }

as_user() {
    runuser -u "$USER_NAME" -- env HOME="$USER_HOME" USER="$USER_NAME" "$@"
}

user_runtime() {
    echo "/run/user/$(id -u "$USER_NAME")"
}

require_root() {
    [ "$(id -u)" -eq 0 ] || fail "Run: sudo ./install.sh"
}

detect_pm() {
    if command -v pacman >/dev/null 2>&1; then
        echo pacman
    elif command -v dnf >/dev/null 2>&1; then
        echo dnf
    elif command -v zypper >/dev/null 2>&1; then
        echo zypper
    elif command -v apt-get >/dev/null 2>&1; then
        echo apt
    else
        echo none
    fi
}

pkg_installed() {
    local pm="$1" pkg="$2"
    case "$pm" in
        pacman) pacman -Q "$pkg" &>/dev/null ;;
        dnf) rpm -q "$pkg" &>/dev/null ;;
        zypper) rpm -q "$pkg" &>/dev/null ;;
        apt) dpkg -s "$pkg" &>/dev/null ;;
        *) return 1 ;;
    esac
}

install_pkgs() {
    local pm="$1"
    shift
    local missing=() pkg
    [ "$#" -gt 0 ] || return 0
    for pkg in "$@"; do
        pkg_installed "$pm" "$pkg" || missing+=("$pkg")
    done
    if [ "${#missing[@]}" -eq 0 ]; then
        ok "already installed: $*"
        return 0
    fi
    case "$pm" in
        pacman) pacman -S --needed --noconfirm "${missing[@]}" ;;
        dnf) dnf install -y "${missing[@]}" ;;
        zypper) zypper --non-interactive install "${missing[@]}" ;;
        apt)
            export DEBIAN_FRONTEND=noninteractive
            apt-get update -y
            apt-get install -y "${missing[@]}"
            ;;
        *) return 1 ;;
    esac
}

install_kernel_headers() {
    local pm="$1"
    step "Kernel headers (needed by OpenRazer DKMS)"
    case "$pm" in
        pacman)
            local kver kpkg h owner
            kver="$(uname -r)"
            owner="$(pacman -Qo "/usr/lib/modules/${kver}/" 2>/dev/null | awk '{print $(NF-1)}' | head -1 || true)"
            if [ -n "$owner" ]; then
                kpkg="${owner%-headers}"
                kpkg="${kpkg%-nvidia-open}"
                kpkg="${kpkg%-nvidia}"
                h="${kpkg}-headers"
                install_pkgs pacman "$h" || warn "could not install $h"
            else
                warn "could not detect kernel package"
            fi
            ;;
        apt)
            install_pkgs apt "linux-headers-$(uname -r)" || warn "install linux-headers for your kernel"
            ;;
        dnf)
            install_pkgs dnf kernel-devel || warn "install kernel-devel"
            ;;
        zypper)
            install_pkgs zypper kernel-default-devel || warn "install kernel-default-devel"
            ;;
        *)
            warn "install kernel headers / -devel for your distro so DKMS can build OpenRazer"
            ;;
    esac
}

install_packages() {
    local pm="$1"
    step "System packages ($pm)"
    case "$pm" in
        pacman)
            install_pkgs pacman \
                python python-gobject gtk4 libadwaita python-evdev dkms \
                || fail "could not install GTK / Python dependencies"
            if ! install_pkgs pacman openrazer-daemon openrazer-driver-dkms python-openrazer; then
                warn "OpenRazer packages missing. Install: openrazer-meta  (or openrazer-daemon + driver + python-openrazer)"
            fi
            ;;
        apt)
            install_pkgs apt \
                python3 python3-gi python3-gi-cairo \
                gir1.2-gtk-4.0 gir1.2-adw-1 \
                python3-evdev dkms \
                || fail "could not install GTK / Python dependencies"
            if ! install_pkgs apt openrazer-daemon openrazer-driver-dkms python3-openrazer; then
                warn "OpenRazer is not in the default repos."
                echo "      Ubuntu / Mint:"
                echo "        sudo add-apt-repository ppa:openrazer/stable"
                echo "        sudo apt update"
                echo "        sudo apt install openrazer-meta"
                echo "      Debian: see https://openrazer.github.io/"
            fi
            ;;
        dnf)
            install_pkgs dnf \
                python3 python3-gobject gtk4 libadwaita python3-evdev dkms \
                || fail "could not install GTK / Python dependencies"
            if ! install_pkgs dnf openrazer-daemon openrazer-kernel-modules-dkms python3-openrazer; then
                warn "OpenRazer packages missing. Fedora:"
                echo "        sudo dnf install openrazer-meta"
                echo "      See https://openrazer.github.io/"
            fi
            ;;
        zypper)
            install_pkgs zypper \
                python3 python3-gobject gtk4 libadwaita python3-evdev dkms \
                || fail "could not install GTK / Python dependencies"
            if ! install_pkgs zypper openrazer-daemon openrazer-driver-dkms python3-openrazer; then
                warn "OpenRazer packages missing. See https://openrazer.github.io/"
            fi
            ;;
        none)
            warn "No supported package manager (pacman / apt / dnf / zypper)."
            echo "      Install yourself, then rerun: sudo ./install.sh --skip-packages"
            echo "      Need: Python 3, GTK4, libadwaita, PyGObject, python-evdev, OpenRazer"
            ;;
    esac
}

setup_groups() {
    step "User groups ($USER_NAME)"
    local g present=() csv
    for g in "${GROUPS[@]}"; do
        getent group "$g" >/dev/null && present+=("$g")
    done
    [ "${#present[@]}" -gt 0 ] || { warn "openrazer / input groups not created yet (install OpenRazer first)"; return 0; }
    csv="$(IFS=,; echo "${present[*]}")"
    usermod -aG "$csv" "$USER_NAME" || true
    ok "added to: ${present[*]}"
}

install_app_files() {
    step "App files → $INSTALL_DIR"
    local f
    for f in razer_reactive.py razer_reactive_gui.py i18n.py config.toml factory_profiles.json; do
        [ -f "$DIR/$f" ] || fail "Missing file: $DIR/$f"
    done

    install -d "$INSTALL_DIR"
    install -m644 "$DIR/razer_reactive.py" "$INSTALL_DIR/"
    install -m644 "$DIR/razer_reactive_gui.py" "$INSTALL_DIR/"
    install -m644 "$DIR/i18n.py" "$INSTALL_DIR/"
    install -m644 "$DIR/config.toml" "$INSTALL_DIR/"
    install -m644 "$DIR/factory_profiles.json" "$INSTALL_DIR/"
    [ -f "$DIR/exec-with-keyd.sh" ] && install -m755 "$DIR/exec-with-keyd.sh" "$INSTALL_DIR/"
    [ -f "$DIR/VERSION" ] && install -m644 "$DIR/VERSION" "$INSTALL_DIR/"
    [ -f "$DIR/LICENSE" ] && install -m644 "$DIR/LICENSE" "$INSTALL_DIR/"
    chown -R "$USER_NAME:" "$INSTALL_DIR"
    ok "copied to $INSTALL_DIR"
}

install_config() {
    step "User config"
    install -d "$CONFIG_DIR"
    if [ ! -f "$CONFIG_DIR/config.toml" ]; then
        install -m644 "$INSTALL_DIR/config.toml" "$CONFIG_DIR/config.toml"
        ok "created $CONFIG_DIR/config.toml"
    else
        ok "kept existing $CONFIG_DIR/config.toml"
    fi
    chown -R "$USER_NAME:" "$CONFIG_DIR"
}

install_launchers() {
    step "Commands in PATH"
    install -d "$BIN_DIR"

    cat >"$BIN_DIR/razer-reactive" <<EOF
#!/bin/sh
exec python3 "$INSTALL_DIR/razer_reactive.py" "\$@"
EOF
    cat >"$BIN_DIR/razer-reactive-gui" <<EOF
#!/bin/sh
exec python3 "$INSTALL_DIR/razer_reactive_gui.py" "\$@"
EOF

    chmod 755 "$BIN_DIR/razer-reactive" "$BIN_DIR/razer-reactive-gui"
    chown "$USER_NAME:" "$BIN_DIR/razer-reactive" "$BIN_DIR/razer-reactive-gui"
    ok "razer-reactive, razer-reactive-gui"
}

install_desktop() {
    step "Menu shortcut"
    local apps="$USER_HOME/.local/share/applications"
    local desktop=""
    for candidate in "$USER_HOME/Desktop" "$USER_HOME/Pulpit" "$USER_HOME/Bureau" "$USER_HOME/Escritorio"; do
        [ -d "$candidate" ] && desktop="$candidate" && break
    done

    install -d "$apps"
    if [ -f "$DIR/razer-reactive.desktop" ]; then
        sed "s|^Exec=.*|Exec=$BIN_DIR/razer-reactive-gui|" \
            "$DIR/razer-reactive.desktop" >"$apps/razer-reactive.desktop"
    else
        cat >"$apps/razer-reactive.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Razer Reactive
GenericName=Keyboard lighting
Comment=Reactive per-key lighting for OpenRazer keyboards
Exec=$BIN_DIR/razer-reactive-gui
Icon=input-keyboard-symbolic
Categories=Utility;Settings;HardwareSettings;
Terminal=false
StartupNotify=true
EOF
    fi
    chown "$USER_NAME:" "$apps/razer-reactive.desktop"
    chmod 644 "$apps/razer-reactive.desktop"

    if [ -n "$desktop" ]; then
        cp "$apps/razer-reactive.desktop" "$desktop/Razer Reactive.desktop"
        chown "$USER_NAME:" "$desktop/Razer Reactive.desktop"
        chmod +x "$desktop/Razer Reactive.desktop"
        as_user gio set "$desktop/Razer Reactive.desktop" metadata::trusted true 2>/dev/null || true
    fi
    ok "application menu"
}

install_systemd_service() {
    step "Background service (autostart)"
    local unit_dir="$USER_HOME/.config/systemd/user"
    local unit_file="$unit_dir/razer-reactive.service"
    local starter="$INSTALL_DIR/exec-with-keyd.sh"
    local exec_line

    if [ -x "$starter" ]; then
        exec_line="$starter /usr/bin/python3 $INSTALL_DIR/razer_reactive.py --daemon"
    else
        exec_line="/usr/bin/python3 $INSTALL_DIR/razer_reactive.py --daemon"
    fi

    install -d "$unit_dir"
    cat >"$unit_file" <<EOF
[Unit]
Description=Razer Reactive keyboard lighting
After=graphical-session.target openrazer-daemon.service
Wants=openrazer-daemon.service

[Service]
Type=simple
ExecStart=$exec_line
Restart=on-failure
RestartSec=3

[Install]
WantedBy=default.target
EOF
    chown "$USER_NAME:" "$unit_file"

    local rt bus
    rt="$(user_runtime)"
    bus="${rt}/bus"
    if [ -S "$bus" ]; then
        as_user XDG_RUNTIME_DIR="$rt" DBUS_SESSION_BUS_ADDRESS="unix:path=${bus}" \
            systemctl --user daemon-reload
        as_user XDG_RUNTIME_DIR="$rt" DBUS_SESSION_BUS_ADDRESS="unix:path=${bus}" \
            systemctl --user enable --now razer-reactive.service \
            || warn "could not start the service — run it after login"
        ok "razer-reactive.service"
    else
        warn "no graphical session — enable after login:"
        echo "      systemctl --user enable --now razer-reactive.service"
    fi
}

start_openrazer() {
    step "OpenRazer daemon"
    modprobe razerkbd 2>/dev/null || true

    local rt bus
    rt="$(user_runtime)"
    bus="${rt}/bus"
    if [ ! -f /usr/lib/systemd/user/openrazer-daemon.service ] \
        && [ ! -f /usr/lib/systemd/user/openrazer-daemon.service ]; then
        warn "openrazer-daemon.service not found — install OpenRazer for your distro"
        return 0
    fi
    [ -S "$bus" ] || {
        warn "will start after login"
        return 0
    }

    as_user XDG_RUNTIME_DIR="$rt" DBUS_SESSION_BUS_ADDRESS="unix:path=${bus}" \
        systemctl --user enable --now openrazer-daemon 2>/dev/null \
        || warn "could not enable openrazer-daemon"
    ok "openrazer-daemon"
}

verify_install() {
    step "Verify Python modules"
    python3 - <<'PY' || warn "some Python modules are missing — install OpenRazer + GTK4 + PyGObject"
import sys
missing = []
try:
    import gi
    gi.require_version("Gtk", "4.0")
    gi.require_version("Adw", "1")
    from gi.repository import Gtk, Adw  # noqa: F401
except Exception as exc:
    missing.append(f"GTK4/libadwaita ({exc})")
try:
    import evdev  # noqa: F401
except Exception:
    missing.append("python-evdev")
try:
    from openrazer.client import DeviceManager  # noqa: F401
except Exception:
    missing.append("python-openrazer")
if missing:
    print("   missing: " + ", ".join(missing))
    sys.exit(1)
print("   Python modules OK")
PY
}

print_summary() {
    echo ""
    echo "══════════════════════════════════════"
    echo "  Razer Reactive — install finished"
    echo "══════════════════════════════════════"
    echo ""
    echo "Launch:"
    echo "  razer-reactive-gui"
    echo ""
    echo "Service:"
    echo "  systemctl --user status razer-reactive.service"
    echo "  systemctl --user restart razer-reactive.service"
    echo ""
    echo "Factory profiles (in the GUI):"
    echo "  Startowy, Mryganie na przemian, Deszcz czerwony, Krople na klawisze"
    echo ""
    if [ ! -d "$USER_HOME/.local/bin" ] || ! echo ":$PATH:" | grep -q ":$BIN_DIR:"; then
        echo "If the command is not found, add to PATH:"
        echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
        echo ""
    fi
    echo "After the first install:"
    echo "  • log out and back in (openrazer / input / keyd groups)"
    echo "  • plug in the Razer keyboard over USB"
    echo ""
    echo "Uninstall: sudo ./uninstall.sh"
    echo ""
}

echo "══════════════════════════════════════"
echo "  Razer Reactive — Linux install"
echo "══════════════════════════════════════"

require_root
PM="$(detect_pm)"
echo "Package manager: $PM"

if [ "$SKIP_PACKAGES" -eq 0 ]; then
    install_kernel_headers "$PM"
    install_packages "$PM"
else
    warn "skipped package installation"
fi
setup_groups
install_app_files
install_config
install_launchers
install_desktop
start_openrazer
install_systemd_service
verify_install
print_summary
