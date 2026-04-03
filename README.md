# DOS Machines

DOS Machines is a folder-based DOS machine workspace and DOSBox-family machine editor.

This initial scaffold provides:

- Python 3.11 project setup with setuptools
- PySide6 Qt Widgets application shell
- settings and workspace initialization under `~/.config/dos-machines/`
- layered per-game profile model stored in `.dosmachines/profile.json`
- generated managed `dosbox.conf`
- generated `.desktop` launchers with DOS Machines metadata

## Run

Install dependencies and run the app:

```bash
python -m pip install -e .[dev]
dos-machines
```

## Tests

```bash
pytest
```
