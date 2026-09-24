#!/usr/bin/env python3
"""Build complete, offline human-spoken digits from the licensed source manifest.

Requires Python 3 and FFmpeg with Rubber Band. The Average setting retains every
source sample with a single linear loudness adjustment. Faster settings process
each whole recording at a conservative, pitch-preserving tempo. No speech is
spliced, gated, faded, or cropped, and every clip receives fixed silent guards.
"""

import argparse
import array
import base64
import hashlib
import io
import json
import math
from pathlib import Path
import subprocess
import sys
import wave

RATES = {
    "average": 1,
    "moderately-fast": 1.12,
    "fast": 1.25,
    "very-fast": 1.4,
    "extremely-fast": 1.55,
    "incredibly-fast": 1.7,
    "ultra-fast": 1.85,
}
WORDS = "one two three four five six seven eight nine".split()
TARGET_RMS_DBFS = -20
PEAK_CEILING = 0.8
QUIET_GUARD_SECONDS = 0.020
DURATION_ALLOWANCE_SECONDS = 0.080


def unpack(raw, typecode="h"):
    samples = array.array(typecode)
    samples.frombytes(raw)
    if sys.byteorder != "little":
        samples.byteswap()
    return list(samples)


def pack(samples, typecode="h"):
    data = array.array(typecode, samples)
    if sys.byteorder != "little":
        data.byteswap()
    return data.tobytes()


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def measure(samples):
    if not samples or not all(math.isfinite(value) for value in samples):
        raise ValueError("Missing or invalid audio samples")
    return (
        math.sqrt(sum(value * value for value in samples) / len(samples)),
        max(abs(value) for value in samples),
    )


def read_source(manifest, digit, word):
    entry = manifest["clips"][digit]
    if entry["transcript"].lower().strip() != word:
        raise ValueError(f"Wrong source transcript for {digit}")
    raw_wav = base64.b64decode(entry["wavBase64"], validate=True)
    if digest(raw_wav) != entry["sha256"]:
        raise ValueError(f"Source WAV hash does not match for {digit}")
    with wave.open(io.BytesIO(raw_wav), "rb") as source:
        if (source.getnchannels() != 1 or source.getsampwidth() != 2
                or source.getframerate() != manifest["sampleRate"]
                or source.getcomptype() != "NONE"):
            raise ValueError(f"Source {digit} must be mono PCM16 at the manifest sample rate")
        pcm = source.readframes(source.getnframes())
        if len(pcm) != source.getnframes() * 2:
            raise ValueError(f"Incomplete source recording for {digit}")
    if entry.get("pcmSha256") and digest(pcm) != entry["pcmSha256"]:
        raise ValueError(f"Source PCM hash does not match for {digit}")
    samples = unpack(pcm)
    if len(samples) < manifest["sampleRate"] * 0.2:
        raise ValueError(f"Source recording is unexpectedly short for {digit}")
    source_rms, source_peak = measure([value / 32768 for value in samples])
    if source_rms < 0.005 or source_peak >= 32767 / 32768:
        raise ValueError(f"Source {digit} is silent or clipped")
    # One linear gain per complete recording: no gate, compressor, limiter,
    # silence trim, or envelope fade can erase a quiet initial consonant.
    gain = min(10 ** (TARGET_RMS_DBFS / 20) / source_rms,
               PEAK_CEILING / source_peak)
    normalized = [round(value * gain) for value in samples]
    output_rms, output_peak = measure([value / 32768 for value in normalized])
    return normalized, {
        "wavSha256": digest(raw_wav), "pcmSha256": digest(pcm),
        "normalizedPcmSha256": digest(pack(normalized)),
        "frames": len(samples),
        "normalization": {"gain": gain, "sourceRms": source_rms,
                          "sourcePeak": source_peak, "outputRms": output_rms,
                          "outputPeak": output_peak},
    }


def accelerate(samples, rate, sample_rate):
    if rate == 1:
        return samples[:], len(samples), {"leading": 0, "trailing": 0}
    # Flush padding protects short recordings from incomplete filter output.
    # Pass the WHOLE word to Rubber Band once and retain EVERY nonzero output
    # sample, including transform latency/tails; never assume a crop offset.
    flush_padding = round(sample_rate * 0.250)
    # One additional terminal zero keeps an exact input-block boundary from
    # triggering an early filter flush. Validate full output length below.
    trailing_padding = flush_padding + 1
    padded = [0] * flush_padding + samples + [0] * trailing_padding
    result = subprocess.run([
        "ffmpeg", "-hide_banner", "-loglevel", "error",
        "-f", "s16le", "-ar", str(sample_rate), "-ac", "1", "-i", "pipe:0",
        "-af", f"rubberband=tempo={rate}:pitch=1:transients=crisp:formant=preserved:pitchq=quality:window=short",
        "-f", "f32le", "pipe:1",
    ], input=pack(padded), stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    transformed = unpack(result.stdout, "f")
    _, peak = measure(transformed)
    # Inspect floating-point output BEFORE PCM16 quantization so a conversion
    # cannot silently saturate overshoots and hide clipping from validation.
    if peak >= 32767 / 32768:
        raise ValueError(f"Tempo {rate} creates clipped audio")
    expected_frames = len(padded) / rate
    if abs(len(transformed) - expected_frames) > 1:
        raise ValueError(f"Unexpected tempo duration at {rate}: {len(transformed)} frames")
    quantized = [round(value * 32768) for value in transformed]
    # Remove only digital silence introduced by flush padding. Limit removal
    # to the known tempo-scaled padding extent. The input is never trimmed, and
    # every nonzero sample remains even when the transform bleeds into padding.
    padding_limit = math.floor(flush_padding / rate)
    trailing_limit = math.floor(trailing_padding / rate)
    start, end = 0, len(quantized)
    while start < padding_limit and quantized[start] == 0:
        start += 1
    while len(quantized) - end < trailing_limit and quantized[end - 1] == 0:
        end -= 1
    if any(quantized[:start]) or any(quantized[end:]):
        raise ValueError("Padding removal would erase a nonzero sample")
    rendered = quantized[start:end]
    if abs(len(rendered) - len(samples) / rate) > sample_rate * DURATION_ALLOWANCE_SECONDS:
        raise ValueError(f"Unexpected retained tempo duration at {rate}: {len(rendered)} versus {len(samples) / rate} frames")
    return rendered, len(quantized), {"leading": start, "trailing": len(quantized) - end}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    root = Path(__file__).resolve().parents[1]
    parser.add_argument("--source", type=Path, default=root / "assets/number-voice/source.json")
    parser.add_argument("--output", type=Path, default=root / "number-speech-data.js")
    args = parser.parse_args()
    manifest = json.loads(args.source.read_text())
    sample_rate = manifest["sampleRate"]
    if not isinstance(sample_rate, int) or not 8000 <= sample_rate <= 96000:
        raise ValueError("Unsupported source sample rate")
    guard_frames = round(sample_rate * QUIET_GUARD_SECONDS)
    originals, sources = {}, {}
    for digit, word in enumerate(WORDS, 1):
        originals[str(digit)], sources[str(digit)] = read_source(manifest, str(digit), word)
    clips, clip_hashes, frame_counts, rendered_frames = {}, {}, {}, {}
    full_transform_frames, padding_removed_frames, schedule_tail_frames = {}, {}, {}
    duration_allowance_frames = round(sample_rate * DURATION_ALLOWANCE_SECONDS)
    prior = {digit: float("inf") for digit in originals}
    for speed, rate in RATES.items():
        clips[speed], clip_hashes[speed], frame_counts[speed] = {}, {}, {}
        rendered_frames[speed] = {}
        full_transform_frames[speed], padding_removed_frames[speed] = {}, {}
        schedule_tail_frames[speed] = {}
        for digit, source in originals.items():
            rendered, full_transform_frames[speed][digit], padding_removed_frames[speed][digit] = accelerate(source, rate, sample_rate)
            # Different tempos can leave different amounts of quiet transform
            # tail. Add only zeros to a shared duration allowance: every speed
            # becomes predictably shorter without ever cutting an audio tail.
            scheduled_length = round(len(source) / rate) + duration_allowance_frames
            tail_frames = scheduled_length - len(rendered)
            if tail_frames < 0:
                raise ValueError(f"Transform tail exceeds its allowance for {digit}: {speed}")
            if scheduled_length >= prior[digit]:
                raise ValueError(f"Non-increasing speed for {digit}: {speed}")
            prior[digit] = scheduled_length
            samples = [0] * guard_frames + rendered + [0] * (tail_frames + guard_frames)
            if any(abs(value) >= 32767 for value in samples):
                raise ValueError(f"PCM quantization clips {digit} at {speed}")
            raw = pack(samples)
            clips[speed][digit] = base64.b64encode(raw).decode("ascii")
            clip_hashes[speed][digit] = digest(raw)
            frame_counts[speed][digit] = len(samples)
            rendered_frames[speed][digit] = len(rendered)
            schedule_tail_frames[speed][digit] = tail_frames
    data = {
        "format": "pcm-s16le", "sampleRate": sample_rate,
        "voice": manifest["voice"], "version": 2,
        "provenance": manifest["provenance"],
        "sourceManifestSha256": digest(args.source.read_bytes()),
        "sourceWavSha256": {digit: source["wavSha256"] for digit, source in sources.items()},
        "sourcePcmSha256": {digit: source["pcmSha256"] for digit, source in sources.items()},
        "normalizedSourcePcmSha256": {digit: source["normalizedPcmSha256"] for digit, source in sources.items()},
        "sourceFrames": {digit: source["frames"] for digit, source in sources.items()},
        "normalization": {"targetRmsDbfs": TARGET_RMS_DBFS, "peakCeiling": PEAK_CEILING,
                          "digits": {digit: source["normalization"] for digit, source in sources.items()}},
        "processing": {"method": "whole-word-pitch-preserving", "pitch": 1,
                       "rateRange": [min(RATES.values()), max(RATES.values())],
                       "crossfades": False, "sourceTrimming": False,
                       "trimming": "padding-only-digital-silence",
                       "flushPaddingFrames": round(sample_rate * 0.250),
                       "flushTrailingPaddingFrames": round(sample_rate * 0.250) + 1,
                       "durationAllowanceFrames": duration_allowance_frames,
                       "window": "short"},
        "quietGuardFrames": guard_frames,
        "rates": RATES, "clips": clips, "clipPcmSha256": clip_hashes,
        "frames": frame_counts, "renderedFrames": rendered_frames,
        "fullTransformFrames": full_transform_frames,
        "paddingRemovedFrames": padding_removed_frames,
        "scheduleTailFrames": schedule_tail_frames,
    }
    header = """// Generated by scripts/build-number-speech.py. Do not edit waveform data.
// Complete human-spoken digits; source and attribution: NUMBER-SPEECH-ASSETS.md.
(function (root) {
  'use strict';
  const data = """
    footer = """;
  root.__numberSpeechData = data;
  if (typeof module === 'object' && module.exports) module.exports = data;
})(typeof globalThis !== 'undefined' ? globalThis : this);
"""
    args.output.write_text(header + json.dumps(data, indent=2) + footer)
    print(f"Wrote {args.output.name}: {args.output.stat().st_size:,} bytes; 63 complete clips")
    for speed in RATES:
        durations = [value / sample_rate for value in frame_counts[speed].values()]
        print(f"{speed}: {min(durations):.3f}–{max(durations):.3f} seconds")


if __name__ == "__main__":
    main()
