# Publishing Razer Reactive (GitHub + AUR)

Repo: **https://github.com/GorianWaco/Razer-Reactive**

## 1. Tag and push

```bash
cd ~/Projekty/Razer-Reactive
git add -A
git commit -m "Razer Reactive 1.6"
git tag v1.6
git push -u origin main
git push origin v1.6
```

## 2. GitHub Release

1. https://github.com/GorianWaco/Razer-Reactive/releases/new
2. Tag: `v1.6`
3. Title: `Razer Reactive 1.6`
4. Attach `dist/razer-reactive-1.6.tar.gz` from `./make-dist.sh`
5. Publish

Friends install:

```bash
git clone https://github.com/GorianWaco/Razer-Reactive.git
cd Razer-Reactive
sudo ./install.sh
```

## 3. AUR (optional)

After the tag exists:

```bash
source=("${pkgname}-${pkgver}.tar.gz::https://github.com/GorianWaco/Razer-Reactive/archive/refs/tags/v${pkgver}.tar.gz")
```

Then `updpkgsums`, `makepkg --printsrcinfo > .SRCINFO`, push the AUR package.
