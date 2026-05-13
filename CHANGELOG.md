# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed

- DOSBox child processes lingering as zombie (`<defunct>`) entries after exiting. The parent app never reaped the child's exit status. Fixed by spawning a daemon thread that calls `process.wait()` immediately after launching, so the exit status is collected without blocking the UI. The `Popen` object is also kept alive in `LauncherService` to prevent premature garbage collection.

## [0.2.4] - 2026-04-20

### Added

- Pentium preset profile
- Improved icon handling in the UI

## [0.2.3] - 2026-04-16

### Changed

- Repositioned the Media button in the dialog layout

## [0.2.2] - 2026-04-16

### Fixed

- Media display rendering improvements

### Added

- Hercules VGA preset

## [0.2.1] - 2026-04-07

### Added

- Host configuration options dialog
- Default preset library
- Media folder management for game directories

### Fixed

- Config file not being applied correctly
- Autoexec section being overwritten when applying system presets

### Changed

- Code clean-up and formatting improvements
- Ignored generated local artifacts

## [0.2.0] - 2026-04-05

### Added

- Import functionality for existing DOSBox `.conf` files
- Media folder support per game directory
- Previous presets shown when updating a machine
- Icon size limit in the dialog
- Help text sections (collapsed by default)
- Panel icon support
- Scroll wheel disabled for section value adjustment

### Fixed

- Autoexec import handling
- Import process reliability
- Broken machine repair when the directory structure changes
- Icon handling when adjusting machines with existing icons

### Changed

- UI clean-up and panel improvements

## [0.1.1] - 2026-04-04

### Fixed

- Icon adjustment bug when a machine already had an icon
- UI scaling for the launcher dialog

## [0.1.0] - 2026-04-04

### Added

- Core application shell with PySide6 Qt Widgets
- Folder-based DOS machine workspace management
- Per-game profile model stored in `.dosmachines/profile.json`
- Managed `dosbox.conf` generation
- `.desktop` launcher generation with DOS Machines metadata
- Initial DOSBox config system
- Section-based profile editor
- File drag-and-drop and folder operations
- Icon support for machines
- Default section templates for new machines
- UI scaling and double-click handling
- DOSBox-X configuration support (subsequently removed in 0.1.1)
