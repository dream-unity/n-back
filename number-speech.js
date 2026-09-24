'use strict';

(function exposeNumberSpeech(root, factory) {
  const api = factory();
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  if (root) root.__numberSpeechAudio = api;
})(typeof window !== 'undefined' ? window : globalThis, () => {
  const RATES = Object.freeze({ average: 1, 'moderately-fast': 1.12, fast: 1.25, 'very-fast': 1.4, 'extremely-fast': 1.55, 'incredibly-fast': 1.7, 'ultra-fast': 1.85 });
  const GAPS = Object.freeze({ average: 300, 'moderately-fast': 200, fast: 120, 'very-fast': 80, 'extremely-fast': 40, 'incredibly-fast': 15, 'ultra-fast': 0 });
  // The lead-in is never accelerated. It gives a resumed audio output time to
  // open before the first consonant, including one-number, fastest-speed trials.
  const LEAD_SECONDS = .35, TAIL_SECONDS = .1;
  const decoded = new WeakMap();

  function decodeClip(data, rate, digit) {
    let cache = decoded.get(data);
    if (!cache) { cache = new Map(); decoded.set(data, cache); }
    const key = rate + ':' + digit;
    if (cache.has(key)) return cache.get(key);
    const encoded = data.clips?.[rate]?.[digit];
    if (typeof encoded !== 'string' || !encoded.length) throw new Error('Number audio is incomplete.');
    const binary = atob(encoded);
    if (binary.length % 2) throw new Error('Invalid number audio samples.');
    const samples = new Float32Array(binary.length / 2);
    for (let i = 0; i < samples.length; i++) {
      const value = binary.charCodeAt(i * 2) | (binary.charCodeAt(i * 2 + 1) << 8);
      samples[i] = (value >= 32768 ? value - 65536 : value) / 32768;
    }
    cache.set(key, samples);
    return samples;
  }

  function buildSequence(values, settings, data) {
    if (!Array.isArray(values) || !values.length || values.length > 3 ||
        !Array.from(values).every(value => Number.isInteger(value) && value >= 1 && value <= 9)) {
      throw new Error('A sequence must contain one to three digits from 1 to 9.');
    }
    if (!data || !Number.isInteger(data.sampleRate) || data.sampleRate < 8000 || data.sampleRate > 96000) throw new Error('Invalid number audio sample rate.');
    const rate = Object.hasOwn(RATES, settings.rate) ? settings.rate : 'average';
    const spacing = Object.hasOwn(GAPS, settings.spacing) ? settings.spacing : 'average';
    const clips = values.map(digit => decodeClip(data, rate, digit));
    const sampleRate = data.sampleRate, lead = Math.ceil(LEAD_SECONDS * sampleRate), tail = Math.ceil(TAIL_SECONDS * sampleRate);
    const gap = Math.round(GAPS[spacing] * sampleRate / 1000);
    const length = lead + tail + clips.reduce((total, clip) => total + clip.length, 0) + gap * (clips.length - 1);
    const samples = new Float32Array(length), segments = [];
    let cursor = lead;
    clips.forEach((clip, index) => {
      samples.set(clip, cursor);
      segments.push({ digit: values[index], start: cursor, end: cursor + clip.length });
      cursor += clip.length + gap;
    });
    return { samples, sampleRate, segments, duration: length / sampleRate, rate, spacing };
  }

  function createPlayer(environment, data = environment.__numberSpeechData) {
    let context = null, preparation = null, keepAlive = null, active = null, disposed = false;
    const later = (callback, delay) => environment.setTimeout(callback, delay);
    const clear = handle => environment.clearTimeout(handle);
    const available = () => !disposed && !!(environment.AudioContext || environment.webkitAudioContext) && !!data?.clips;

    function cancel() {
      const previous = active;
      if (previous) previous.finish(false);
    }

    function prepare() {
      if (!available()) return Promise.resolve(false);
      if (preparation) return preparation;
      try {
        if (!context || context.state === 'closed') {
          const AudioContext = environment.AudioContext || environment.webkitAudioContext;
          context = new AudioContext({ latencyHint: 'playback' });
          keepAlive = context.createBufferSource();
          keepAlive.buffer = context.createBuffer(1, 128, context.sampleRate);
          keepAlive.loop = true;
          keepAlive.connect(context.destination);
          keepAlive.start();
        }
        // Invoke resume synchronously inside Start/Test/Resume's user gesture.
        const preparedContext = context;
        const resume = preparedContext.state === 'running' ? Promise.resolve() : preparedContext.resume();
        let timeout;
        const pending = Promise.race([
          Promise.resolve(resume).then(() => !disposed && context === preparedContext && preparedContext.state === 'running', () => false),
          new Promise(resolve => { timeout = later(() => resolve(false), 2500); })
        ]).finally(() => { clear(timeout); if (preparation === pending) preparation = null; });
        preparation = pending;
        return pending;
      } catch (_) { return Promise.resolve(false); }
    }

    function play(values, settings) {
      cancel();
      const volume = Math.max(0, Math.min(1, Number(settings.volume)));
      if (!settings.speak || !Number.isFinite(volume) || volume <= 0 || !available()) return Promise.resolve(false);
      return new Promise(resolve => {
        let finished = false, source = null, gain = null, watchdog = null, drain = null;
        const item = { finish(ok) {
          if (finished) return;
          finished = true;
          if (active === item) active = null;
          clear(watchdog); clear(drain);
          if (source) {
            source.onended = null;
            if (!ok) { try { source.stop(); } catch (_) {} }
            try { source.disconnect(); } catch (_) {}
          }
          try { gain?.disconnect(); } catch (_) {}
          resolve(ok);
        }};
        active = item;
        prepare().then(ready => {
          if (finished || active !== item) return;
          if (!ready) { item.finish(false); return; }
          try {
            const sequence = buildSequence(values, settings, data);
            const buffer = context.createBuffer(1, sequence.samples.length, sequence.sampleRate);
            buffer.getChannelData(0).set(sequence.samples);
            source = context.createBufferSource();
            source.buffer = buffer;
            source.playbackRate.value = 1; // Tempo is rendered; never speed up the protective lead-in or raise voice pitch.
            gain = context.createGain(); gain.gain.value = volume;
            source.connect(gain); gain.connect(context.destination);
            source.onended = () => {
              if (finished || active !== item || drain !== null) return;
              // onended describes the audio graph; output devices can still have
              // queued samples. Do not open the response timer before they drain.
              const latency = Math.max(0, Number(context.baseLatency) || 0) + Math.max(0, Number(context.outputLatency) || 0);
              drain = later(() => item.finish(true), Math.max(60, latency * 1000));
            };
            // This is a failure watchdog, never a per-number cutoff. All digits
            // and gaps have already been copied into the same complete buffer.
            watchdog = later(() => item.finish(false), sequence.duration * 1000 + 10000);
            source.start();
          } catch (_) { item.finish(false); }
        }, () => item.finish(false));
      });
    }

    function release() {
      cancel();
      const retiring = context;
      context = null; preparation = null;
      try { keepAlive?.stop(); keepAlive?.disconnect(); } catch (_) {}
      keepAlive = null;
      try { Promise.resolve(retiring?.close()).catch(() => {}); } catch (_) {}
    }
    function dispose() { disposed = true; release(); }
    return { play, cancel, prepare, available, release, dispose };
  }

  return Object.freeze({ createPlayer, buildSequence, decodeClip, RATES, GAPS, LEAD_SECONDS, TAIL_SECONDS });
});
