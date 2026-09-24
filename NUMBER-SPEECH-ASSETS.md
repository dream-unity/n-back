# Bundled spoken numbers

The number trainer uses human recordings of **one** through **nine** spoken by
**Cameron in Australian English**, recorded by **CAMSOWN** for the Asterisk Core
Sounds project. These replace the previous Flite synthetic voice. The source is
mono 16 kHz, signed 16-bit little-endian PCM; playback uses bundled audio and does
not require the device's speech-synthesis service or a speech-provider request.

## Source and attribution

Adapted from **Asterisk Core Sounds, Australian English, version 1.6.1**.
Voice: Cameron. Recorded by CAMSOWN. Copyright (C) 2010–2013 CAMSOWN.com.

- [Original versioned archive](https://downloads.asterisk.org/pub/telephony/sounds/releases/asterisk-core-sounds-en_AU-sln16-1.6.1.tar.gz)
- [Asterisk sound archive index](https://downloads.asterisk.org/pub/telephony/sounds/)
- [Creator's URL as supplied in the original credits](http://voiceover.camsown.com)
- [Creative Commons Attribution 3.0 Unported license](https://creativecommons.org/licenses/by/3.0/)
- [Complete original license and copyright notice](assets/number-voice/LICENSE.txt)
- [Original credits](assets/number-voice/CREDITS.txt)

The source recordings and the adapted audio in `number-speech-data.js` are
distributed under **CC BY 3.0**. Keep the attribution, copyright notice, license
link and indication of modifications when redistributing them. The recordings'
license does not change the license of unrelated application code. No endorsement
by Cameron, CAMSOWN or the Asterisk project is claimed.

`assets/number-voice/source.json` contains each complete original
`digits/1.sln16` through `digits/9.sln16` recording inside a standard PCM WAV
header, encoded as base64. The PCM payload is unchanged. Each entry records its
expected transcript, original archive filename, sample count, WAV SHA-256 and
original PCM SHA-256. The manifest also pins the source archive's SHA-256 and
SHA-1. Original durations are 0.38–0.76 seconds. No Free Spoken Digit Dataset
recordings or synthetic voices are included in this replacement.

## Rebuild and modifications

Run from the repository root:

```sh
python3 scripts/build-number-speech.py
```

The build works offline from the checked-in source manifest, using Python 3 and
FFmpeg with Rubber Band. It verifies the original WAV and PCM hashes before
processing. The following modifications are applied:

- A single constant gain for each complete digit targets RMS loudness of -20 dBFS,
  capped at a peak of 0.8. The same normalized source is used for every speed.
  No gate, compressor, limiter, speech fade or source trimming is applied.
- Average retains every normalized original sample. Faster variants apply
  whole-word, pitch-preserving Rubber Band processing with its short window.
  Words are never split into phoneme regions or joined with crossfades.
- Faster variants receive 250 ms of input flush silence on each side, plus one
  terminal zero sample to avoid an incomplete flush on exact input-block
  boundaries. Full transform duration is checked against the input duration
  and requested tempo, to within one sample.
- After transformation, only exactly zero PCM samples within the known flush
  padding are removed. Every nonzero transformed sample, including quiet tails,
  remains intact. The original input recordings are never trimmed.
- An 80 ms duration allowance accommodates transform tails at every speed,
  including Average. Additional zeros fill unused allowance, making every
  faster setting predictably shorter without cutting a word ending. Each
  complete clip also has a fixed 20 ms silent guard before and after it.

| Setting | Whole-word tempo | Complete clip duration |
| --- | ---: | ---: |
| Average | 1.00× | 0.500–0.880 s |
| Moderately fast | 1.12× | 0.459–0.799 s |
| Fast | 1.25× | 0.424–0.728 s |
| Very fast | 1.40× | 0.391–0.663 s |
| Extremely fast | 1.55× | 0.365–0.610 s |
| Incredibly fast | 1.70× | 0.344–0.567 s |
| Ultra fast | 1.85× | 0.325–0.531 s |

Complete clip durations include both quiet guards and the duration allowance.
The player additionally adds its existing 350 ms sequence lead-in, the selected
spacing between complete clips and 100 ms sequence tail. Volume is controlled
separately. All 63 derived clips include hashes and processing frame counts in
the generated asset. The build fails on clipping, incomplete transformed
output, non-increasing speed or a tail exceeding its duration allowance.

Source hashes and playback-waveform checks verify that the application preserves
the supplied recordings. They do not reconstruct any audio removed by the
original recording publisher or establish a listener's perception of very fast
speech or their physical speaker/headphone output.
