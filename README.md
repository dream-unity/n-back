# N-back — Dream Unity

An independent copy of **Extra Training — Ordered Number N-back** from `mike-stack1982364/Ontological-Worlds`, including the original game engine, options, scoring and recorded Australian-English number voice.

## Play offline

Download **N-Back-Offline.html**, save it on your computer, and open it in a current desktop browser. Select **Open Ordered Number N-back**, adjust your settings, and press **Start**. The complete application, styles, game code, recorded digits and voice license are inside this single HTML file. No internet, account, server or installation is required to play. `index.html` is the identical self-contained application.

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

`SOURCE.json` records the exact imported files and Git blob hashes. The original standalone page, game engine, speech engine, embedded speech data, voice source recordings, voice build script and attribution are copied without edits. Only the generated single-file page adds an internal menu, keyboard help and embedded dependencies/credits. Ontological/relational training and unrelated source modules are deliberately not included. The source repository is not modified.

## Rebuild and validate

After the initial import, these commands use only checked-in files:

```sh
python3 scripts/build-offline.py
node tests/offline.test.cjs
```

The workflow imports the pinned source only when `SOURCE.json` is absent. Later builds use the independent repository copy, not live files from Ontological Worlds. The validation report is stored in `validation/unit-tests.json`.

## Recorded voice

Voice: **Cameron**, recorded by **CAMSOWN**, adapted from Asterisk Core Sounds Australian English 1.6.1. The recordings and their adaptations are licensed under **CC BY 3.0**. Attribution, modifications, original credits and the full voice license are included in the application and in `NUMBER-SPEECH-ASSETS.md` and `assets/number-voice/`. No endorsement is claimed. This voice license does not relicense unrelated application code.
