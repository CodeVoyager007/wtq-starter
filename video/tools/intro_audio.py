"""Synthesize the intro soundtrack (original, royalty-free): flip ticks, riser, slam boom, drone."""
import numpy as np, wave, sys
SR = 48000; DUR = 7.5
t = np.arange(int(SR * DUR)) / SR
out = np.zeros_like(t)
rng = np.random.default_rng(3)

def env_exp(start, decay):
    e = np.where(t >= start, np.exp(-(t - start) / decay), 0.0); return e

def lowpass(x, a):  # one-pole
    y = np.empty_like(x); acc = 0.0
    for i, v in enumerate(x): acc += a * (v - acc); y[i] = acc
    return y

noise = rng.standard_normal(len(t))
# Flip schedule (mirror of intro.html)
flips = []; s, d = 0.35, 0.34
for i in range(18): flips.append(s); s += d; d = max(0.075, d * 0.84)
flip_end = s
# Sub rumble under the montage
out += 0.25 * np.sin(2 * np.pi * 38 * t) * np.clip(t / 1.5, 0, 1) * (t < 4.75)
# Flip ticks: bright noise snaps + a pitched click
hp = noise - lowpass(noise, 0.2)
for i, fs in enumerate(flips):
    e = env_exp(fs, 0.035) * (t < fs + 0.25)
    out += 0.55 * hp * e + 0.25 * np.sin(2 * np.pi * (900 + 40 * i) * t) * env_exp(fs, 0.012)
# Riser into the slam
r0, r1 = flip_end - 0.6, 4.75
k = np.clip((t - r0) / (r1 - r0), 0, 1) * (t < r1)
freq = 90 + 600 * k ** 2
phase = 2 * np.pi * np.cumsum(freq) / SR
out += (0.35 * np.sin(phase) + 0.25 * hp) * k ** 2
# Boom: sub drop + body + transient + tail
T0 = 4.75
drop = 2 * np.pi * np.cumsum(np.where(t >= T0, 55 * np.exp(-(t - T0) / 1.5) + 32, 0)) / SR
out += 1.0 * np.sin(drop) * env_exp(T0, 1.4)
out += 0.45 * np.sin(2 * np.pi * 110 * t) * env_exp(T0, 0.5)
out += 0.9 * lowpass(noise, 0.15) * env_exp(T0, 0.12)
# Second hit (ta-DUM feel), lower and longer
T1 = T0 + 0.42
out += 0.8 * np.sin(2 * np.pi * 41 * t) * env_exp(T1, 1.8)
out += 0.3 * np.sin(2 * np.pi * 82 * t) * env_exp(T1, 1.0)
# Warm drone chord under the title
pad = sum(np.sin(2 * np.pi * f * t + p) for f, p in [(110, 0), (164.8, 1), (220, 2), (261.6, .5)])
out += 0.06 * pad * np.clip((t - T1) / 0.5, 0, 1) * np.clip((DUR - t) / 1.2, 0, 1) * (t > T1)
out *= np.clip((DUR - t) / 0.4, 0, 1)
out = np.tanh(out * 1.1); out /= np.max(np.abs(out)) * 1.12
pcm = (out * 32767).astype(np.int16)
with wave.open(sys.argv[1], 'wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
print('audio ok')
