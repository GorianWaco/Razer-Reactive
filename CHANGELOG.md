# Changelog

## 1.6

- Factory lighting profiles shipped with the app: Startowy, Mryganie na przemian, Deszcz czerwony, Krople na klawisze
- Caps Lock indicator: the Caps key stays lit (configurable color) while Caps is on
- Background mode `blink_alternate`: neighboring keys blink in opposite phase
- Background mode `rain_hits`: raindrops land on individual keys instead of sliding down the matrix
- `install.sh` works on Arch, Fedora, Debian/Ubuntu and openSUSE (not only CachyOS)
- Factory profiles cannot be deleted; user saves still override them

## 1.5

- Background mode `blink_alternate`: neighboring keys blink in opposite phase
- Background mode `rain_hits`: raindrops land on individual keys instead of sliding down the matrix
- Caps Lock indicator: the Caps key stays lit (configurable color) while Caps is on

## 1.4

- Multi-select on the keyboard map (Ctrl+click, Shift+rectangle)
- Edit / fill / clear styles for a group of keys
- Fix: key edit dialog failed to open (translation `key=` conflict; GestureClick vs Button)
- Packaging: README, LICENSE (MIT), updated PKGBUILD for GitHub/AUR

## 1.3

- Custom large color picker (no cramped system dialog)
- Keyboard map scale and BlackWidow V4 X layout (numpad, Enter, labels)
- English / Polish UI language switch

## 1.2

- Separate modes for background, custom-key keys, and press reaction
- Ripple-from-key press effect

## 1.1

- Per-key effects and dual colors

## 1.0

- Initial reactive lighting daemon and GTK4 GUI
