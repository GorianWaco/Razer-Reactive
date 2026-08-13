# Razer Reactive

Reactive per-key lighting for Razer keyboards on Linux (OpenRazer).

**Polski** · [English](#english)

---

## Polski

Reaktywne podświetlenie klawiszy: tło, własne kolory i efekty per klawisz (oraz grupa klawiszy), reakcja na naciśnięcie (m.in. fala od klawisza), wskaźnik Caps Lock. Działa w tle jako usługa użytkownika — zamknięcie okna nie wyłącza efektu.

W programie są **profile fabryczne**: Startowy, Mryganie na przemian, Deszcz czerwony, Krople na klawisze.

### Wymagania

- Linux z systemd (Arch, Fedora, Debian/Ubuntu, openSUSE, CachyOS, …)
- Klawiatura Razer z **podświetleniem per-klawisz** (macierz LED w OpenRazer)
- OpenRazer (daemon + sterownik DKMS)
- Grupy: `openrazer` (oraz zwykle `input` / `plugdev`)

### Szybka instalacja

```bash
git clone https://github.com/GorianWaco/Razer-Reactive.git
cd Razer-Reactive
sudo ./install.sh
```

Albo z archiwum:

```bash
tar -xzf razer-reactive-1.6.tar.gz
cd razer-reactive-1.6
sudo ./install.sh
```

Następnie **wyloguj się i zaloguj** (grupa `openrazer`), podłącz klawiaturę i uruchom:

```bash
razer-reactive-gui
```

Jeśli OpenRazer jest już zainstalowany:

```bash
sudo ./install.sh --skip-packages
```

### Instalacja z AUR (Arch / CachyOS)

```bash
yay -S razer-reactive
# lub
paru -S razer-reactive
```

```bash
systemctl --user enable --now openrazer-daemon
systemctl --user enable --now razer-reactive.service
sudo usermod -aG openrazer,input "$USER"
```

### Użycie

| Polecenie | Opis |
|-----------|------|
| `razer-reactive-gui` | Okno ustawień |
| `systemctl --user status razer-reactive.service` | Status usługi |
| `systemctl --user restart razer-reactive.service` | Restart po zmianach |

**Mapa klawiszy**

- Klik — edycja klawisza
- **Ctrl+klik** — dodaj/usuń z zaznaczenia
- **Shift+klik** — zaznacz prostokąt
- Prawy przycisk — usuń własne ustawienia
- Język UI: English / Polski w oknie programu

### Odinstalowanie

```bash
sudo ./uninstall.sh
```

Konfiguracja w `~/.config/razer-reactive/` jest zachowywana.

### Licencja

MIT — zobacz [LICENSE](LICENSE).

---

## English

Reactive per-key RGB lighting for Razer keyboards on Linux via OpenRazer.

### Features

- Background effects (static, waves, rainbow, rain, drops-on-keys, …)
- Per-key colors and effects; multi-select (Ctrl / Shift)
- Press reaction (including ripple from key)
- Caps Lock indicator
- Factory lighting profiles
- User systemd service (keeps running after closing the GUI)
- English / Polish UI

### Requirements

- Linux with systemd
- Razer keyboard with **per-key** matrix support
- OpenRazer (daemon + DKMS driver)
- Membership in the `openrazer` group

### Install

```bash
git clone https://github.com/GorianWaco/Razer-Reactive.git
cd Razer-Reactive
sudo ./install.sh
```

Log out and back in, then run `razer-reactive-gui`.

`install.sh` talks to **pacman**, **apt**, **dnf** or **zypper**. OpenRazer still has to be available for your distro — the script installs it when the packages exist, otherwise it prints the usual OpenRazer instructions.

### Links

- Source: https://github.com/GorianWaco/Razer-Reactive
- Issues: https://github.com/GorianWaco/Razer-Reactive/issues
- OpenRazer: https://openrazer.github.io/
