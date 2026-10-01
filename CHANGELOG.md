# Changelog

## 1.8

- Language, the active lighting profile, and the rest of the settings are saved automatically
- After a reboot the daemon restores that saved look instead of the factory default
- Loading a lighting profile keeps the interface language you already chose

## 1.7

- GUI starts the background lighting service itself (no `sudo ./install.sh` when the app is already installed)
- “Start service” banner when the daemon is down; Start in the header also launches it
- Clearer errors: missing OpenRazer, stopped daemon, journal excerpt
- Daemon keeps running and retries the keyboard if OpenRazer is not ready yet
- systemd unit: higher start limit, unbuffered logs, reset-failed on install

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
