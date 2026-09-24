'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const crypto = require('node:crypto');
const root = path.resolve(__dirname, '..');
const trainer = require(path.join(root, 'extra-training-runtime.js'));
const speech = require(path.join(root, 'number-speech.js'));
let checks = 0;
function check(condition, message) { assert.ok(condition, message); checks++; }
let seed = 123456789;
function random() { seed = (Math.imul(seed, 1664525) + 1013904223) >>> 0; return seed / 4294967296; }

const source = JSON.parse(fs.readFileSync(path.join(root, 'SOURCE.json')));
for (const [name, item] of Object.entries(source.files)) {
  const bytes = fs.readFileSync(path.join(root, name === 'extra-training.html' ? 'source/extra-training.html' : name));
  const hash = crypto.createHash('sha1').update('blob ' + bytes.length + '\0').update(bytes).digest('hex');
  check(hash === item.git_blob_sha, 'Byte-for-byte source copy: ' + name);
}
assert.deepEqual(trainer.sameSlots([2, 3, 1], [1, 2, 3]), []); checks++;
assert.deepEqual(trainer.sameSlots([8, 2, 7], [1, 2, 3]), [1]); checks++;
assert.deepEqual(trainer.sameSlots([1, 2, 3], [1, 2, 3]), [0, 1, 2]); checks++;
assert.deepEqual(trainer.sameSlots([1], null), []); checks++;
let probabilistic = 0, matches = 0, generated = 0;
for (let n = 1; n <= 20; n++) for (let count = 1; count <= 3; count++) {
  for (const interference of [0, 25, 50, 75, 100]) for (const prob of [0, .35, 1]) {
    const settings = { n, count, interference, prob };
    const history = [];
    for (let i = 0; i < n + 120; i++) {
      const trial = trainer.makeTrial(history, settings, random);
      const expected = i >= n ? history[i - n].values : null;
      assert.deepEqual(trial.target, expected); checks++;
      check(trial.values.length === count && trial.values.every(v => Number.isInteger(v) && v >= 1 && v <= 9), 'Valid ordered digits');
      check(trial.scored === (i >= n), 'Only trials after N memory-fill trials are scored');
      check(trial.match === !!expected?.some((v, j) => v === trial.values[j]), 'Same-position match truth');
      if (expected && prob !== .35) check(trial.match === Boolean(prob), 'Requested forced match/nonmatch');
      if (expected && prob === .35) { probabilistic++; if (trial.match) matches++; }
      history.push(trial); generated++;
    }
  }
}
check(Math.abs(matches / probabilistic - .35) < .015, 'Configured 35% match rate is respected');
const defaults = trainer.normaliseSettings({});
check(defaults.n === 2 && defaults.count === 3 && defaults.response === 3, 'Source defaults preserved');
check(trainer.normaliseSettings({n: 100, count: 100}).n === 20, 'N maximum 20');
check(trainer.normaliseSettings({n: 0, count: 0}).count === 1, 'Count minimum 1');
check(trainer.normaliseSettings({session: 'open'}).session === 'open', 'Open-ended sessions');
check(trainer.dPrime({hits:0, misses:0, falseAlarms:0, correctRejects:0}) === null, 'No invented d-prime without observations');
check(Number.isFinite(trainer.dPrime({hits:10, misses:0, falseAlarms:0, correctRejects:10})), 'Perfect d-prime stays finite');
check(trainer.dPrime({hits:10, misses:0, falseAlarms:0, correctRejects:10}) > 0, 'Positive signal sensitivity');

const context = vm.createContext({window: {}, module: {exports: {}}, console});
vm.runInContext(fs.readFileSync(path.join(root, 'number-speech-data.js'), 'utf8'), context);
const data = context.window.__numberSpeechData || context.__numberSpeechData || context.module.exports;
check(Boolean(data?.clips), 'Bundled human speech data is present');
let audioSequences = 0;
for (const rate of Object.keys(speech.RATES)) {
  for (let digit = 1; digit <= 9; digit++) {
    const samples = speech.decodeClip(data, rate, digit);
    check(samples.length > 0 && samples.every(v => Number.isFinite(v) && Math.abs(v) <= 1), 'Complete, valid embedded audio clip');
  }
  for (const spacing of Object.keys(speech.GAPS)) for (const values of [[1], [2, 8], [6, 8, 9]]) {
    const sequence = speech.buildSequence(values, {rate, spacing}, data);
    check(sequence.segments.length === values.length, 'All spoken digits included');
    check(sequence.duration > 0 && Number.isFinite(sequence.duration), 'Finite speech duration');
    check(sequence.segments[0].start >= Math.ceil(speech.LEAD_SECONDS * data.sampleRate), 'Lead-in preserved');
    check(sequence.samples.slice(0, sequence.segments[0].start).every(v => v === 0), 'Silent speech lead-in');
    for (let i = 1; i < sequence.segments.length; i++) {
      check(sequence.segments[i].start - sequence.segments[i-1].end === Math.round(speech.GAPS[spacing] * data.sampleRate / 1000), 'Exact selected inter-number spacing');
    }
    audioSequences++;
  }
}
const html = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
check(html === fs.readFileSync(path.join(root, 'N-Back-Offline.html'), 'utf8'), 'Download and repository app are identical');
check(html === fs.readFileSync(path.join(root, 'Sentience-N-Back-Offline.html'), 'utf8'), 'Branded download and repository app are identical');
check(html === fs.readFileSync(path.join(root, 'extra-training.html'), 'utf8'), 'Legacy training entry point carries the same brand');
check(html.includes('<title>Sentience n-back — Dream Unity</title>'), 'Browser title uses Sentience n-back');
check(html.includes('<h1 id="menu-title">Sentience n-back</h1>'), 'Menu title uses Sentience n-back');
check(html.includes('<h1 id="training-title" tabindex="-1">Sentience n-back</h1>'), 'Training title uses Sentience n-back');
check(html.includes('Open Sentience n-back'), 'Portal uses Sentience n-back');
check(html.includes('property="og:title" content="Sentience n-back — Dream Unity"'), 'Share metadata uses Sentience n-back');
check(!/Extra Training|Ordered Number N-back|Open ordered/i.test(html), 'No previous product names in the playable app');

check(!/<script\b[^>]*\bsrc\s*=/i.test(html), 'No external JavaScript');
check(!/<link\b[^>]*\brel=["']stylesheet/i.test(html), 'No external stylesheets');
check(!/<(?:iframe|img|audio|video)\b[^>]*\bsrc\s*=/i.test(html), 'No external runtime media');
check(!/\b(?:fetch\s*\(|XMLHttpRequest|WebSocket\s*\(|import\s*\()/.test(html), 'No runtime networking');
check(html.includes('id="open-training"') && html.includes('id="back-to-menu"'), 'Both screens and internal navigation included');
check(html.includes('CAMSOWN') && html.includes('CC BY 3.0'), 'Voice attribution included offline');
const scripts = [...html.matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/gi)];
check(scripts.length === 4, 'Three original modules plus internal navigation');
for (const script of scripts) { new vm.Script(script[1]); checks++; }
const result = {
  passed: true, assertions: checks, generatedTrials: generated,
  testedNLevels: [1,20], numberCounts: [1,2,3], interferenceLevels: 5,
  embeddedVoiceClips: 63, audioSequences,
  observedMatchRate: matches / probabilistic,
  htmlBytes: Buffer.byteLength(html),
  htmlSha256: crypto.createHash('sha256').update(html).digest('hex')
};
fs.mkdirSync(path.join(root, 'validation'), {recursive:true});
fs.writeFileSync(path.join(root, 'validation', 'unit-tests.json'), JSON.stringify(result, null, 2) + '\n');
console.log(JSON.stringify(result, null, 2));
