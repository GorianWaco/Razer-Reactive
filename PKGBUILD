# Maintainer: GorianWaco
# https://github.com/GorianWaco/Razer-Reactive
#
# Build from a git checkout (files next to this PKGBUILD):
#   makepkg -si
#
# After you push tag v$pkgver to GitHub, switch `source` to the GitHub
# archive (see comments below) and run: updpkgsums && makepkg --printsrcinfo > .SRCINFO

pkgname=razer-reactive
pkgver=1.6
pkgrel=1
pkgdesc="Reactive per-key lighting for Razer keyboards (OpenRazer)"
arch=('any')
url="https://github.com/GorianWaco/Razer-Reactive"
license=('MIT')
depends=(
    'python'
    'python-gobject'
    'gtk4'
    'libadwaita'
    'python-evdev'
    'dkms'
    'openrazer-daemon'
    'openrazer-driver-dkms'
    'python-openrazer'
)
optdepends=(
    'keyd: if keyd grabs the keyboard, join the keyd group for press events'
)

# --- Local makepkg (default): use project files in $startdir ---
source=()
sha256sums=()

# --- AUR / remote (after tag v1.4 exists on GitHub) ---
# source=("${pkgname}-${pkgver}.tar.gz::https://github.com/gorian/razer-reactive/archive/refs/tags/v${pkgver}.tar.gz")
# sha256sums=('REPLACE_WITH_updpkgsums')

package() {
    local root
    if [[ -f "$srcdir/${pkgname}-${pkgver}/razer_reactive.py" ]]; then
        root="$srcdir/${pkgname}-${pkgver}"
    elif [[ -f "$srcdir/${pkgname}-v${pkgver}/razer_reactive.py" ]]; then
        root="$srcdir/${pkgname}-v${pkgver}"
    else
        root="$startdir"
    fi

    local inst="$pkgdir/usr/share/razer-reactive"
    install -dm755 "$inst" \
        "$pkgdir/usr/bin" \
        "$pkgdir/usr/share/applications" \
        "$pkgdir/usr/lib/systemd/user" \
        "$pkgdir/usr/share/licenses/$pkgname" \
        "$pkgdir/usr/share/doc/$pkgname"

    install -m644 \
        "$root/razer_reactive.py" \
        "$root/razer_reactive_gui.py" \
        "$root/i18n.py" \
        "$root/config.toml" \
        "$root/factory_profiles.json" \
        "$inst/"
    [[ -f "$root/exec-with-keyd.sh" ]] && install -m755 "$root/exec-with-keyd.sh" "$inst/"

    [[ -f "$root/LICENSE" ]] && install -m644 "$root/LICENSE" \
        "$pkgdir/usr/share/licenses/$pkgname/LICENSE"
    [[ -f "$root/README.md" ]] && install -m644 "$root/README.md" \
        "$pkgdir/usr/share/doc/$pkgname/README.md"
    [[ -f "$root/INSTALL.txt" ]] && install -m644 "$root/INSTALL.txt" \
        "$pkgdir/usr/share/doc/$pkgname/INSTALL.txt"
    [[ -f "$root/CHANGELOG.md" ]] && install -m644 "$root/CHANGELOG.md" \
        "$pkgdir/usr/share/doc/$pkgname/CHANGELOG.md"

    install -Dm644 "$root/razer-reactive.desktop" \
        "$pkgdir/usr/share/applications/razer-reactive.desktop"

    install -Dm755 /dev/stdin "$pkgdir/usr/bin/razer-reactive" <<'EOF'
#!/bin/sh
exec python3 /usr/share/razer-reactive/razer_reactive.py "$@"
EOF
    install -Dm755 /dev/stdin "$pkgdir/usr/bin/razer-reactive-gui" <<'EOF'
#!/bin/sh
exec python3 /usr/share/razer-reactive/razer_reactive_gui.py "$@"
EOF

    install -Dm644 /dev/stdin "$pkgdir/usr/lib/systemd/user/razer-reactive.service" <<'EOF'
[Unit]
Description=Razer Reactive keyboard lighting
After=graphical-session.target openrazer-daemon.service
Wants=openrazer-daemon.service

[Service]
Type=simple
ExecStart=/usr/bin/python3 /usr/share/razer-reactive/razer_reactive.py --daemon
Restart=on-failure
RestartSec=3

[Install]
WantedBy=default.target
EOF
}
