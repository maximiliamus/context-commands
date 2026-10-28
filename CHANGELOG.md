# Changelog

## [0.2.1] - 2026-10-29

### Added

- A link to update instructions in the installed commands file.

## [0.2.0] - 2026-10-29

### Added

- `;;;` to check the operator's understanding.
- Benchmark selection by command marker, including related combinations and
  follow-up scenarios.

### Changed

- Installation and updates compare only version values. Matching versions leave
  the installed file untouched, including local edits and modification time.
- An installed file without a version is updated while preserving its custom
  commands.
- Install and update messages explain the result, next steps, and common errors.
- Context commands put the chat back in discussion mode until an explicit
  action request or confirmation of a specific proposed action.

## [0.1.0] - 2026-10-28

### Added

- Fifteen context commands for chats with AI agents, with compact help and
  examples of combined commands.
- Custom commands, aliases, and overrides in `CONTEXT_COMMANDS.md`.
- PowerShell and Bash install and update scripts in `scripts/`, with custom
  definitions preserved during updates.
- A benchmark for command interpretation and reporting.
- Regression tests for installation, updates, and the benchmark harness.
- MIT license.
