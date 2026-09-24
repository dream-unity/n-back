# Sentience n-back — Dream Unity

**Sentience n-back** is Dream Unity’s offline number-memory trainer. Practise ordered sequences with adjustable difficulty, interference, timing and recorded Australian-English number audio. All game code and voice recordings are included in one downloadable HTML file.

## Play offline

Download **[Sentience-N-Back-Offline.html](Sentience-N-Back-Offline.html)**, save it on your computer, and open it in a current desktop browser. Select **Open Sentience n-back**, adjust your settings, and press **Start**. The complete application, styles, game code, recorded digits and voice license are inside this single HTML file. No internet, account, server or installation is required to play. `index.html` is the identical self-contained application. Existing `N-Back-Offline.html` and `extra-training.html` links remain compatible and open the same newly branded application.

## Included

- N-back levels 1–20; 1–3 ordered digits per trial, using digits 1–9.
- The original same-position matching rule: at least one digit must match the same position exactly N trials earlier. Transposed digits are interference, not matches.
- All five interference settings, six match-probability settings, seven response times, and timed or open-ended sessions.
- All seven speech speeds and seven spacing settings; volume, spoken stimuli and audio-only mode.
- Embedded human recordings for all nine digits at every speech speed. No online voice service or installed speech-synthesis voice is needed.
- Start, pause/resume, stop, test speech, keyboard controls, supported-device haptics, feedback, explanations, trial totals, hits, accuracy and d-prime.
- A local training-menu screen and return button; no link or runtime dependency on the source application.

The first N trials are unscored memory-fill trials. The full spoken sequence finishes before the response timer starts. F/J = Match, D/K = No Match, and Escape = Stop. Haptics require browser/device vibration support. Settings are locked while a session is running, as in the original trainer. Returning to the menu stops the current session.

## Source and preservation

Source repository: `mike-stack1982364/Ontological-Worlds`.
Pinned source commit: `f34066d0b7466f7477f9d077cff72cbb27a9e47e`.

`SOURCE.json` records the exact imported files and Git blob hashes. The original standalone page is preserved byte-for-byte in `source/extra-training.html` for provenance and rebuilds, not as a promoted app entry point. The game engine, speech engine, embedded speech data, voice source recordings, voice build script and attribution are unchanged. The generated application adds Sentience n-back branding, an internal menu, keyboard help, embedded dependencies/credits and matching browser/share metadata. Ontological/relational training and unrelated source modules are deliberately not included. The source repository is not modified.

## Rebuild and validate

After the initial import, these commands use only checked-in files:

```sh
python3 scripts/build-offline.py
node tests/offline.test.cjs
python3 tests/browser-offline.py
```

The workflow imports the pinned source only when `SOURCE.json` is absent. Later builds use the independent repository copy, not live files from Ontological Worlds. Validation reports are stored in `validation/unit-tests.json` and `validation/browser-tests.json`. Browser testing requires Playwright and Chromium; playing the downloaded application does not. All published app entry points and the downloadable HTML are rebuilt from the same source.

## Recorded voice

Voice: **Cameron**, recorded by **CAMSOWN**, adapted from Asterisk Core Sounds Australian English 1.6.1. The recordings and their adaptations are licensed under **CC BY 3.0**. Attribution, modifications, original credits and the full voice license are included in the application and in `NUMBER-SPEECH-ASSETS.md` and `assets/number-voice/`. No endorsement is claimed. This voice license does not relicense unrelated application code.
