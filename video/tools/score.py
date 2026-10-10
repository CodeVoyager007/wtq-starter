"""Orchestral trailer score built from FluidR3 GM instrument samples (CC BY 3.0).

Usage: python3 score.py <samples_dir> <cues.json> <out.wav>
Samples: <inst>-<Note><Octave>.mp3 from github.com/gleitz/midi-js-soundfonts (FluidR3_GM).
cues.json: {"duration", "drop", "hits": [...], "outro"} as written by assemble.py.
"""
import json, os, subprocess, sys
import numpy as np

SR = 44100
SD, CUES, OUT = sys.argv[1:4]
cues = json.load(open(CUES))
DUR = cues["duration"]; N = int(SR * DUR)
L = np.zeros(N); R = np.zeros(N)
NAMES = ['C', 'Db', 'D', 'Eb', 'E', 'F', 'Gb', 'G', 'Ab', 'A', 'Bb', 'B']
_cache = {}

def note_name(m): return f"{NAMES[m % 12]}{m // 12 - 1}"

def sample(inst, m):
    key = (inst, m)
    if key not in _cache:
        path = os.path.join(SD, f"{inst}-{note_name(m)}.mp3")
        if not os.path.exists(path):
            _cache[key] = None
        else:
            raw = subprocess.check_output(['ffmpeg', '-v', 'error', '-i', path, '-f', 's16le', '-ac', '1', '-ar', str(SR), '-'])
            _cache[key] = np.frombuffer(raw, np.int16).astype(np.float64) / 32768
    return _cache[key]

def put(sig, t, gain, pan):
    i = int(t * SR)
    if i >= N or i + len(sig) <= 0: return
    if i < 0: sig = sig[-i:]; i = 0
    sig = sig[: N - i]
    L[i:i + len(sig)] += sig * gain * (1 - max(pan, 0))
    R[i:i + len(sig)] += sig * gain * (1 + min(pan, 0))

def play(inst, m, t, dur=None, gain=1.0, pan=0.0, attack=0.0):
    if sample(inst, m) is None: return
    if dur is not None and dur > 2.6:  # sustain by overlapping re-triggers
        k = 0.0
        while k < dur:
            one(inst, m, t + k, min(2.9, dur - k + 0.4), gain, pan, 0.35 if k > 0 else attack)
            k += 2.2
        return
    one(inst, m, t, dur, gain, pan, attack)

def one(inst, m, t, dur, gain, pan, attack):
    s = sample(inst, m).copy()
    if dur is not None:
        n = min(len(s), int(dur * SR)); s = s[:n]
        rel = min(int(0.12 * SR), n); s[-rel:] *= np.linspace(1, 0, rel)
    if attack > 0:
        a = min(int(attack * SR), len(s)); s[:a] *= np.linspace(0, 1, a)
    put(s, t, gain, pan)

def chord(inst, ms, t, dur, gain, spread=0.5, attack=0.0):
    for j, m in enumerate(ms):
        play(inst, m, t, dur, gain, (j / max(1, len(ms) - 1) - 0.5) * spread, attack)

BPM = 96; BEAT = 60 / BPM; BAR = 4 * BEAT
drop, outro, hits = cues["drop"], cues["outro"], cues.get("hits", [])
A1, A2, A3 = 33, 45, 57

# ---------------- Intro: flip montage -> slam -> hero theme ----------------
flips = []; s, d = 0.35, 0.34
for _ in range(18): flips.append(s); s += d; d = max(0.075, d * 0.84)
flip_end = s; SLAM = 4.75
play('contrabass', A1, 0.0, SLAM, 0.5, attack=1.2)
play('string_ensemble_1', A2, 0.0, SLAM, 0.35, attack=1.5)
for i, ft in enumerate(flips):
    play('taiko_drum', 36 if i % 2 else 45, ft, 1.2, 0.35 + 0.5 * i / len(flips), 0.3 if i % 2 else -0.3)
    if i % 2 == 0: play('string_ensemble_1', A2 + (0 if i < 10 else 12), ft, 0.22, 0.4)
k = flip_end; g = 0.15
while k < SLAM:  # timpani roll crescendo
    play('timpani', A1, k, 0.3, g); k += 0.07; g = min(0.9, g + 0.05)
for j, m in enumerate([45, 47, 48, 50, 52, 53, 55, 56]):  # brass climb
    t = flip_end - 0.4 + j * (SLAM - flip_end + 0.4) / 8
    play('brass_section', m, t, 0.35, 0.35 + j * 0.05)
# SLAM
play('orchestra_hit', A2, SLAM, None, 1.0); play('orchestra_hit', A3, SLAM, None, 0.8)
play('timpani', A1, SLAM, None, 1.0); play('taiko_drum', 36, SLAM, None, 1.0)
chord('brass_section', [A2, 48, 52, A3], SLAM, drop - SLAM + 0.5, 0.45)
chord('choir_aahs', [A3, 60, 64], SLAM + 0.3, drop - SLAM + 0.3, 0.32, attack=0.8)
play('contrabass', A1, SLAM, drop - SLAM + 0.5, 0.6)
HERO = [(0, 57, 1), (1, 64, 1.5), (2.5, 62, .5), (3, 60, 1), (4, 59, .5), (4.5, 60, .5), (5, 57, 2)]  # beats, midi, len
def hero(t0, inst, gain, shift=0):
    for b, m, ln in HERO: play(inst, m + shift, t0 + b * BEAT, ln * BEAT + 0.15, gain, 0.1)
hero(SLAM + 0.9, 'french_horn', 0.55)

# ---------------- Body: ostinato, taiko groove, build per chapter ----------------
PROG = [(45, [57, 60, 64]), (41, [53, 57, 60]), (48, [55, 60, 64]), (43, [55, 59, 62])]  # Am F C G
def intensity(t):
    return 0.55 + 0.45 * sum(1 for h in hits if h <= t) / max(1, len(hits))
t0 = drop; bar = 0
while t0 < outro - 0.05:
    root, ch = PROG[(bar // 2) % 4]; I = intensity(t0)
    if bar % 2 == 0:
        L2 = min(2 * BAR, outro - t0 + 0.6)
        play('contrabass', root - 12, t0, L2, 0.5 * I)
        chord('french_horn', ch, t0, L2, 0.16 * I, attack=0.4)
        if I > 0.75: chord('choir_aahs', [c + 12 for c in ch], t0, L2, 0.10 * I, attack=0.8)
        play('timpani', root - 12 if root - 12 >= 33 else root, t0, None, 0.45 * I)
    pat = [0, 0, 7, 0, 12, 0, 7, 0]
    for e in range(8):
        ts = t0 + e * BEAT / 2
        if ts >= outro: break
        play('string_ensemble_1', root + pat[e], ts, BEAT / 2 * 0.9, (0.30 if e % 4 == 0 else 0.22) * I, -0.2)
        if I > 0.8: play('string_ensemble_1', root + 12 + pat[e], ts, BEAT / 2 * 0.9, 0.12 * I, 0.25)
    for b, gg in ((0, 0.55), (2.5, 0.35), (3, 0.45)):  # boom .. ba-boom
        if t0 + b * BEAT < outro: play('taiko_drum', 36, t0 + b * BEAT, 1.0, gg * I, 0.0)
    t0 += BAR; bar += 1

# Chapter hits: swell, stab, hero theme
for n, h in enumerate(hits):
    k = h - 0.9; g = 0.1
    while k < h: play('timpani', A1, k, 0.25, g); k += 0.08; g = min(0.7, g + 0.06)
    play('orchestra_hit', A2, h, None, 0.85); play('timpani', A1, h, None, 0.9); play('taiko_drum', 36, h, None, 0.8)
    chord('brass_section', [A2, 52, A3], h, 1.0, 0.4)
    if h + 8 * BEAT < outro:
        hero(h + 1.0, 'trumpet' if n >= len(hits) // 2 else 'french_horn', 0.40, 12 if n >= len(hits) // 2 else 0)

# ---------------- Outro: heroic A major, ring out ----------------
k = outro - 1.2; g = 0.1
while k < outro: play('timpani', A1, k, 0.25, g); k += 0.06; g = min(0.9, g + 0.05)
play('orchestra_hit', A2, outro, None, 1.0); play('timpani', A1, outro, None, 1.0); play('taiko_drum', 36, outro, None, 1.0)
end = DUR - outro
chord('brass_section', [A2, 49, 52, A3, 61], outro, end, 0.45)
chord('choir_aahs', [A3, 61, 64, 69], outro + 0.2, end, 0.3, attack=0.6)
chord('string_ensemble_1', [A2, 57, 64, 69], outro, end, 0.3, attack=0.3)
play('contrabass', A1, outro, end, 0.6)
hero(outro + 0.3, 'trumpet', 0.45, 12)

# ---------------- Mix: hall reverb, fade, master ----------------
def reverb(x, seed):
    t = np.arange(int(2.4 * SR)) / SR
    ir = np.random.default_rng(seed).standard_normal(len(t)) * np.exp(-t / 0.7)
    n = len(x) + len(ir); F = 1 << (n - 1).bit_length()
    return np.fft.irfft(np.fft.rfft(x, F) * np.fft.rfft(ir, F), F)[: len(x)]
wl, wr = reverb(L, 1), reverb(R, 2)
wl *= 0.25 * np.abs(L).max() / (np.abs(wl).max() + 1e-9); wr *= 0.25 * np.abs(R).max() / (np.abs(wr).max() + 1e-9)
L, R = L + wl, R + wr
fade = np.clip((DUR - np.arange(N) / SR) / 2.0, 0, 1); L *= fade; R *= fade
peak = max(np.abs(L).max(), np.abs(R).max())
L, R = np.tanh(L / peak * 1.4) * 0.89, np.tanh(R / peak * 1.4) * 0.89
pcm = (np.stack([L, R], 1) * 32767).astype(np.int16)
import wave
with wave.open(OUT, 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
print(f"score ok: {DUR:.1f}s, samples used {sum(v is not None for v in _cache.values())}")
