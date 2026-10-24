# AE-0547 — Prompt suggestions in the publish cover dialog; AE-0508 follow-up nits

Status: In Development
Tier: T1
Priority: Low
Type: Feature
Area: Frontend + Backend tests
Owner: Claude Code (claude-opus-5-5)
Branch: feat/ae-0547-cover-dialog-suggestions
Created: 2026-10-24
Updated: 2026-10-24

## Goal

The publish step's "Gerar capa com Grok" prompt offers the same prompt suggestions as the create wizard
(AE-0509): the curated catalogue for the carousel's topic and palette, then AI ideas on "Mais ideias".
Tapping one fills the prompt, which stays editable. It also closes three review nits left from AE-0508.

## Problem

- AE-0509 (#273) put the suggestions only under the wizard's slide-1 photo prompt; the cover generation
  dialog from AE-0508 (#270) had an empty prompt field with a `children` slot waiting for them.
- AE-0508 review nits: the dialog description said "Grok makes a new cover" (the engine is OpenAI on the
  Grok Bot side); the backend scenario "A confirmed generation sends the photo bytes and stores a private
  cover" no longer matches (photos are links since the last AE-0508 round); a docstring line in
  `cover_generation_runner.py` was over 88 characters.

## Scope

- Editorial: the suggestion logic of AE-0509's `CoverPromptField` moves into `CoverPromptSuggestions`
  (`topic`, `palette`, `onPick`), exported from `@/modules/editorial`; the wizard field renders it
  unchanged.
- Publishing: `CoverPickerSection` / `CoverGeneratePanel` take an optional
  `renderPromptSuggestions(fill)` and render it inside the prompt field's slot; the module imports
  nothing from editorial.
- Publish page: `PublishCoverPicker` composes `CoverPromptSuggestions` with the carousel's `topic` and
  palette (`findThemePalette` over the palette catalog, as the wizard does).
- Copy: the dialog description is neutral in en and pt ("A new cover is made from them").
- Backend tests: the scenario is renamed "A confirmed generation links the photos and stores a private
  cover" in the feature and every docstring that references it; the runner docstring is wrapped.

## Non-Goals

- No backend behaviour change, no API change, no schema change.
- No change to the suggestion catalogue, the AI ideas endpoint or the wizard.

Classification (CLAUDE.md AE-0153): the suggestions in the dialog are a user-visible behaviour change, so
they ship a `.feature` (`frontend/tests/features/cover-dialog-suggestions-ae0547.feature`). The copy,
scenario rename and docstring wrap change no behaviour.

## Acceptance Criteria

- [x] Given the publish page of a Ponto de Vista carousel with library photos, Then the "Gerar capa com
      Grok" prompt shows suggestions for the carousel's topic and palette.
- [x] When the owner taps a suggestion, Then the prompt holds it and stays editable.
- [x] The wizard's slide-1 prompt suggestions behave as before.
- [x] The dialog description no longer says Grok makes the cover (en and pt).
- [x] The backend scenario and its references describe links, not photo bytes; the runner docstring fits
      the line limit.

## Gherkin Scenarios

See `frontend/tests/features/cover-dialog-suggestions-ae0547.feature`.

## Affected Areas

- [x] Frontend (`cover-prompt-suggestions.tsx`, `cover-prompt-field.tsx`, `cover-generate-panel.tsx`,
      `cover-picker-section.tsx`, `publish-cover-picker.tsx`, `publish-artifact-tools.tsx`, i18n)
- [x] Backend tests only (feature + docstrings); `cover_generation_runner.py` docstring
- API: no change. Database: no change.

## Dependencies

AE-0508 (#270) and AE-0509 (#273), both merged.

## Progress Log

### 2026-10-24

Branched off main after #270 merged. PB's AE-0509 had no follow-up wiring the suggestions into the cover
dialog, so this ticket does it.

## Files Touched

See `.agent/reports/AE-0547.dev-summary.md`.

## Test Evidence

See `.agent/reports/AE-0547.dev-summary.md`.

## QA Report

See `.agent/reports/AE-0547.qa.md`.

## Blockers

None.
