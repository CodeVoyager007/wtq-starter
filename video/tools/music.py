"""Original cinematic score for the demo (royalty-free, synthesized from scratch).

Usage: python3 music.py <cues.json> <out.wav>
cues.json: {"duration": 92.4, "drop": 7.5, "hits": [7.5, 18.2, ...], "outro": 87.4}
  drop  - when the beat starts (end of the intro)
  hits  - impact + swell at each chapter card
  outro - final chord; the beat stops here and the chord rings out
"""
import json, sys, wave
import numpy as np

SR = 48000
BPM = 100
BEAT = 60 / BPM
cues = json.load(open(sys.argv[1]))
N = int(SR * cues["duration"])
L = np.zeros(N); R = np.zeros(N)
rng = np.random.default_rng(11)

def add(sig, start, gain=1.0, pan=0.0):
    i = int(start * SR)
    if i >= N: return
    sig = sig[: N - i]
    L[i:i + len(sig)] += sig * gain * (1 - max(pan, 0))
    R[i:i + len(sig)] += sig * gain * (1 + min(pan, 0))

def tt(d): return np.arange(int(d * SR)) / SR
def midi(n): return 440 * 2 ** ((n - 69) / 12)

def pad_note(f, d):
    t = tt(d); s = np.zeros_like(t)
    for h in range(1, 7):
        for det in (-0.12, 0.12):
            s += np.sin(2 * np.pi * f * h * (1 + det / 100 * h) * t) / h ** 1.6
    a = np.clip(t / 0.8, 0, 1) * np.clip((d - t) / 0.8, 0, 1)
    return s * a / 6

def pluck(f, d=0.45):
    t = tt(d); e = np.exp(-t / 0.13)
    return np.sin(2 * np.pi * f * t + 1.8 * e * np.sin(2 * np.pi * 2 * f * t)) * e

def kick():
    t = tt(0.4); f = 45 + 110 * np.exp(-t / 0.035)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.16)

def hat():
    t = tt(0.06); n = rng.standard_normal(len(t)); n = n - np.convolve(n, np.ones(4) / 4, 'same')
    return n * np.exp(-t / 0.015)

def sub(f, d):
    t = tt(d); return np.sin(2 * np.pi * f * t) * np.exp(-t / (d * 0.7)) * np.clip(t / 0.01, 0, 1)

def impact():
    t = tt(3.0); drop = 2 * np.pi * np.cumsum(30 + 50 * np.exp(-t / 0.25)) / SR
    n = np.convolve(rng.standard_normal(len(t)), np.ones(30) / 30, 'same')
    return np.sin(drop) * np.exp(-t / 0.9) + 0.5 * n * np.exp(-t / 0.08)

def swell(d=1.2):
    t = tt(d); n = rng.standard_normal(len(t))
    k = (t / d) ** 3
    lp = np.convolve(n, np.ones(12) / 12, 'same')
    return (lp * 0.6 + 0.3 * np.sin(2 * np.pi * (200 + 900 * k) * t)) * k

# A minor: Am - F - C - G, two bars each
prog = [(57, [57, 60, 64]), (53, [53, 57, 60]), (48, [55, 60, 64]), (55, [55, 59, 62])]
BAR = 4 * BEAT
drop, outro, dur = cues["drop"], cues["outro"], cues["duration"]

def saw(f, d, bright=1.6, harm=18):
    t = tt(d); s = np.zeros_like(t)
    for h in range(1, harm + 1):
        if f * h > 9000: break
        s += np.sin(2 * np.pi * f * h * t) / h ** bright
    return s

def cello(f, d):  # bowed low-string ostinato note: soft attack, dark tone, slight swell
    t = tt(d); e = np.clip(t / 0.03, 0, 1) * np.exp(-t / (d * 0.9))
    return saw(f, d, 2.0) * e

def braam(f, d=3.2):  # low brass-like swell for chapter hits
    t = tt(d); e = np.clip(t / 0.25, 0, 1) ** 2 * np.exp(-np.clip(t - 0.4, 0, None) / 1.1)
    s = sum(saw(f * m, d, 1.4) for m in (1, 1.5, 2)) + 0.6 * np.sin(2 * np.pi * f / 2 * t)
    return s * e

def tick():
    t = tt(0.03); return np.sin(2 * np.pi * 2600 * t) * np.exp(-t / 0.004)

# Intro: low drone that swells into the title slam
add(pad_note(midi(45), drop + 0.5), 0, 0.35)
add(pad_note(midi(33), drop + 0.5), 0, 0.25)

# Main bed: dark pads, eighth-note low string ostinato, soft kick on the downbeat, clock tick
t0 = drop; bar = 0
while t0 < outro:
    root, chord = prog[(bar // 2) % 4]
    if bar % 2 == 0:
        L2 = min(2 * BAR, outro - t0 + 0.8)
        add(pad_note(midi(root - 12), L2), t0, 0.20, -0.3)
        add(pad_note(midi(chord[1] - 12), L2), t0, 0.12, 0.3)
    for s8 in range(8):
        ts = t0 + s8 * BEAT / 2
        if ts >= outro: break
        accent = 1.0 if s8 % 4 == 0 else 0.7
        add(cello(midi(root - 12), BEAT / 2 * 0.95), ts, 0.16 * accent, -0.15)
        add(cello(midi(root), BEAT / 2 * 0.95), ts, 0.06 * accent, 0.15)
        if s8 % 2 == 0: add(tick(), ts, 0.05, 0.5)
    if t0 < outro: add(kick(), t0, 0.45)
    t0 += BAR; bar += 1

# Chapter hits: swell into a braam with a sub boom
for h in cues.get("hits", []):
    add(swell(), h - 1.2, 0.18)
    add(braam(midi(33)), h, 0.22)
    add(impact(), h, 0.5)

# Outro: final braam and a long dark chord
add(braam(midi(33), 4.0), outro, 0.25)
add(impact(), outro, 0.6)
for n in (33, 45, 52, 57, 60):
    add(pad_note(midi(n), dur - outro + 0.2), outro, 0.14, (n % 3 - 1) * 0.3)

# Cheap stereo reverb: convolve with decaying noise
def reverb(x, seed):
    ir_t = tt(1.6); ir = np.random.default_rng(seed).standard_normal(len(ir_t)) * np.exp(-ir_t / 0.45)
    n = len(x) + len(ir); F = 1 << (n - 1).bit_length()
    return np.fft.irfft(np.fft.rfft(x, F) * np.fft.rfft(ir, F), F)[: len(x)] * 0.012
L, R = L + reverb(L, 1), R + reverb(R, 2)
fade = np.clip((dur - np.arange(N) / SR) / 1.5, 0, 1)
L *= fade; R *= fade
peak = max(np.abs(L).max(), np.abs(R).max())
L, R = np.tanh(L / peak * 1.2) * 0.85, np.tanh(R / peak * 1.2) * 0.85
pcm = (np.stack([L, R], 1) * 32767).astype(np.int16)
with wave.open(sys.argv[2], "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
print(f"music ok: {dur:.1f}s")
