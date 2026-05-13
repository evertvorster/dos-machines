# DOS Machines Architecture

DOS Machines is a small PySide6 desktop application for managing folder-based DOSBox-family game profiles. The code is intentionally service-oriented: Qt code owns presentation and user interaction, while the application services own filesystem, profile, launcher, import, engine, and preset behavior.

## Core model

A DOS machine is represented by a game directory containing a managed `.dosmachines/` folder:

```text
<Game Directory>/
└── .dosmachines/
    ├── profile.json      # structured DOS Machines profile
    ├── dosbox.conf       # generated or imported DOSBox config
    ├── icon.*            # optional managed icon
    └── media/            # optional user-managed media/artwork folder
```

The user-facing workspace is a normal filesystem folder. Machine launchers are `.desktop` files stored in that workspace, and each launcher points back to the managed profile via DOS Machines metadata keys.

## Runtime wiring

`dos_machines.app.build_main_window()` wires the application together:

1. `SettingsService` loads config paths and persisted settings.
2. `WorkspaceService` manages the selected workspace folder.
3. `EngineRegistry` probes/caches DOSBox-family engine metadata and schemas.
4. `PresetService` loads user/system machine presets and section defaults.
5. `ProfileService` creates, updates, loads, saves, and deletes managed profiles.
6. `ImportService` analyses existing `dosbox.conf` files and turns them into profiles.
7. `LauncherService` writes and launches `.desktop` entries.
8. `MainWindow` presents the workspace and delegates behavior to the services.

## Package layout

```text
src/dos_machines/
├── app.py                  # QApplication setup and dependency wiring
├── application/            # filesystem/config/profile/import services
├── domain/                 # dataclass models and serialization
├── ui/                     # PySide6 widgets/dialogs/views
└── assets/                 # app icon and bundled system presets
```

### `domain/`

`domain.models` contains serialization-friendly dataclasses such as:

- `Settings`
- `EngineRef`, `EngineSchema`, `SchemaSection`, `SchemaOption`
- `MachineProfile`, `ProfileIdentity`, `GameTargets`, `OptionState`
- `MachinePreset`
- `WorkspaceEntry`

These classes define the persisted shape of settings, profiles, engine schemas, and workspace launcher metadata.

### `application/`

The application layer is the behavioral core:

- `settings_service.py` creates and persists `~/.config/dos-machines/settings.json` and related app directories.
- `workspace_service.py` manages the workspace path and reads `.desktop` launcher metadata, including broken-profile/icon detection.
- `engine_registry.py` registers an engine binary, probes version/capabilities, stores cached schema data, and parses a default config.
- `schema_parser.py` parses DOSBox-style config samples into editable schema sections/options.
- `config_renderer.py` renders a managed `dosbox.conf` from a `MachineProfile` and `EngineSchema`.
- `profile_service.py` creates/updates profile JSON, generated config, managed icons, and existing-profile reuse.
- `import_service.py` analyses existing `dosbox.conf` files, detects imported options/autoexec/executable, reports non-blocking unknowns, and creates profiles after review.
- `preset_service.py` persists user machine presets and engine-scoped section defaults, and exposes bundled system presets.
- `launcher_service.py` writes executable `.desktop` launchers and starts DOSBox using the launcher `Exec` and `Path` fields.

### `ui/`

The UI layer is Qt-specific and should generally delegate persistent behavior to application services:

- `main_window.py` shows the workspace, supports folder navigation, drag/drop, launcher activation, icon resizing, context actions, and host configuration.
- `create_machine_dialog.py` handles creating/configuring/importing machines, editing config sections, applying presets, icon selection, and media access.
- `host_config_dialog.py` edits engine-scoped host/default settings.
- `media.py` launches the per-machine media folder with Dolphin or `xdg-open`.

## Important workflows

### Creating or updating a machine

1. The dialog collects title, game directory, executable, engine binary, presets/defaults, icon, and config options.
2. `ProfileService.create()` registers the engine, loads the schema, creates or reuses the machine id, writes `.dosmachines/profile.json`, and writes `.dosmachines/dosbox.conf`.
3. `LauncherService.sync_launcher()` writes or renames the workspace `.desktop` launcher.

Existing profiles can be updated without changing the machine id. Managed icons are copied into `.dosmachines/` and reused across moved profiles when possible.

### Importing an existing `dosbox.conf`

1. `ImportService.analyse_config()` detects the engine binary from `PATH` and registers it.
2. The config is parsed into known schema options, raw unknown overrides, and `autoexec` text.
3. Non-blocking issues are reported for unknown sections/options so the user can review them instead of losing data.
4. Managed configs are recognized by the generated header, `.dosmachines` path, or managed autoexec pattern.
5. After review, the import is saved through `ProfileService.create()` so the result becomes a normal managed profile.

### Launching a machine

Workspace `.desktop` files contain:

- `Exec="<engine>" -conf "<game>/.dosmachines/dosbox.conf"`
- `Path=<game>/.dosmachines`
- `X-DOSMachines-ProfilePath=<game>/.dosmachines/profile.json`
- `X-DOSMachines-MachineId=<machine id>`

`LauncherService.launch_launcher()` reads the launcher and starts the command in the configured working directory.

## Persistence locations

By default:

```text
~/.config/dos-machines/
├── settings.json
├── workspace/
├── engines/
│   └── <engine-id>/
│       ├── binary-info.json
│       ├── default.conf
│       └── schema.json
└── presets/
    └── user-presets.json
```

Game-specific state lives beside the game in `.dosmachines/` rather than inside the global config directory.

## Testing

The test suite is the best behavioral specification. It covers service behavior, import/recovery paths, schema parsing, presets, launcher writing/launching, workspace broken-entry detection, and important Qt UI flows.

Run:

```bash
pytest
```

At the time this document was written, the suite passed with 74 tests.
