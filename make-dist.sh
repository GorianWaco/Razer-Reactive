#!/bin/bash
# Builds a friend-ready install archive (and a source tree for checksums).
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VERSION="$(tr -d '[:space:]' < "$DIR/VERSION")"
NAME="razer-reactive-${VERSION}"
OUT_DIR="$DIR/dist"
ARCHIVE="$OUT_DIR/${NAME}.tar.gz"

FILES=(
    VERSION
    LICENSE
    README.md
    CHANGELOG.md
    INSTALL.txt
    install.sh
    uninstall.sh
    razer_reactive.py
    razer_reactive_gui.py
    i18n.py
    config.toml
    factory_profiles.json
    exec-with-keyd.sh
    razer-reactive.desktop
    PKGBUILD
)

echo "→ Packaging $NAME"
rm -rf "$OUT_DIR/$NAME" "$ARCHIVE"
mkdir -p "$OUT_DIR/$NAME"

for f in "${FILES[@]}"; do
    if [ -f "$DIR/$f" ]; then
        cp "$DIR/$f" "$OUT_DIR/$NAME/"
    else
        echo "  ! missing: $f" >&2
        exit 1
    fi
done

chmod +x "$OUT_DIR/$NAME/install.sh" "$OUT_DIR/$NAME/uninstall.sh"

tar -C "$OUT_DIR" -czf "$ARCHIVE" "$NAME"
rm -rf "$OUT_DIR/$NAME"

SUM="$(sha256sum "$ARCHIVE" | awk '{print $1}')"
echo "✓ Archive: $ARCHIVE"
echo "  sha256:  $SUM"
echo ""
echo "For friends: send the .tar.gz — INSTALL.txt is inside."
echo "For AUR PKGBUILD sha256sums after GitHub tag v${VERSION} exists:"
echo "  curl -sL https://github.com/GorianWaco/Razer-Reactive/archive/refs/tags/v${VERSION}.tar.gz | sha256sum"
