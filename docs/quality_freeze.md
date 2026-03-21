# Quality Freeze Policy

As of March 21, 2026, the quality-plan backlog is considered closed and the repository is under a quality-freeze policy for release-critical flows.

## Goal

The quality freeze exists to keep release behavior stable once the P0 and documentation backlogs are closed.

## Freeze rules

- No release-critical behavior should change without:
  - targeted tests
  - updated documentation when user-visible behavior changes
  - passing CI and smoke checks
- Shared flows must remain preferred over duplicated logic.
- Changes affecting CLI, dependency installation, IDE/classic parity, or release workflows require smoke validation before release.

## Blocking bug policy

A bug is considered blocking when it breaks one of these validated flows:

- launching the application from the documented CLI entrypoints
- running the documented smoke commands
- opening the classic or IDE-like GUI
- launching BCASL or Engines standalone modes
- completing the tool-installation preflight flow

## Current blocking bug status

Validated by the current smoke-check plan:

- CLI smoke: validated
- IDE/classic parity checkpoints: validated by documented parity review
- dependency analyzer hardening: validated by targeted tests
- tool-installation sequencing and Linux system-Python pip flag coverage: validated by targeted tests

Current status: no known blocking bug remains open in the quality plan after smoke validation.

## Exit criteria for the freeze

The freeze should only be relaxed when a new phase is explicitly opened in `TODO.md` or when a documented release-critical regression is confirmed and tracked.
