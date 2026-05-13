# DOS Machines

DOS Machines is a folder-based DOS machine workspace and DOSBox-family machine editor.

This initial scaffold provides:

- Python 3.11 project setup with setuptools
- PySide6 Qt Widgets application shell
- settings and workspace initialization under `~/.config/dos-machines/`
- layered per-game profile model stored in `.dosmachines/profile.json`
- generated managed `dosbox.conf`
- generated `.desktop` launchers with DOS Machines metadata

## Arch Linux

Build and install with the included `PKGBUILD`:

```bash
makepkg -si
```

The package installs:

- the Python application into the system Python environment
- the desktop launcher into `/usr/share/applications`
- the app icon into `/usr/share/icons/hicolor/scalable/apps`
- the default DOSBox Staging config into `/usr/share/dos-machines`

`dosbox-staging` is a runtime dependency of the package.

## Architecture

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the core model, service layout, persistence locations, and main workflows.

## Development

Install dependencies and run the app:

```bash
python -m pip install -e .[dev]
dos-machines
```

## Tests

```bash
pytest
```
