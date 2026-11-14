"""Synthesise the film's score in code: no samples, no generative audio.

Every sound is built from oscillators, filtered noise and Karplus-Strong strings,
placed at the picture's event times. 120 BPM in D minor; the groove's beat 0 is t = 1.0 s.
The random source is seeded, so every run writes the same file.

Writes build/score-raw.wav; `make film-score` loudness-normalises it into assets/audio/."""

import sys
from pathlib import Path

import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, fftconvolve, lfilter, sosfilt

SR = 48000
DUR = 30.0
N = int(SR * DUR)
rng = np.random.default_rng(151)
BEAT = 0.5
G0 = 1.0  # groove start


def t_axis(n):
    return np.arange(n) / SR


def midi(m):
    return 440.0 * 2 ** ((m - 69) / 12)


class Bus:
    def __init__(self):
        self.l = np.zeros(N)
        self.r = np.zeros(N)

    def add(self, sig, at, gain=1.0, pan=0.0):
        i = int(round(at * SR))
        if i >= N:
            return
        sig = sig[: N - i]
        gl = gain * np.cos((pan + 1) * np.pi / 4)
        gr = gain * np.sin((pan + 1) * np.pi / 4)
        self.l[i : i + len(sig)] += sig * gl
        self.r[i : i + len(sig)] += sig * gr


dry, wet = Bus(), Bus()


def env_exp(n, decay, attack=0.002):
    t = t_axis(n)
    a = np.clip(t / attack, 0, 1)
    return a * np.exp(-t * decay)


def pluck(freq, dur=1.2, decay=0.996, bright=0.6):
    """Karplus-Strong string via an IIR comb (lfilter keeps it fast)."""
    n = int(dur * SR)
    p = max(2, int(round(SR / freq)))
    x = np.zeros(n)
    burst = rng.uniform(-1, 1, p)
    burst = sosfilt(butter(1, 1500 + 7000 * bright, fs=SR, output="sos"), burst)
    x[:p] = burst
    a = np.zeros(p + 2)
    a[0] = 1
    a[p] = -decay * 0.5
    a[p + 1] = -decay * 0.5
    y = lfilter([1.0], a, x)
    y *= np.minimum(1, (n - np.arange(n)) / (0.05 * SR))  # tail fade
    return y / (np.max(np.abs(y)) + 1e-9)


def kick(dur=0.45, punch=1.0):
    n = int(dur * SR)
    t = t_axis(n)
    f = 46 + 110 * np.exp(-t * 32)
    ph = 2 * np.pi * np.cumsum(f) / SR
    body = np.sin(ph) * np.exp(-t * 7.5)
    click = rng.uniform(-1, 1, n) * np.exp(-t * 900) * 0.35 * punch
    return np.tanh((body + click) * 1.6)


def hat(dur=0.06, tone=7500):
    n = int(dur * SR)
    x = rng.uniform(-1, 1, n)
    x = sosfilt(butter(2, tone, btype="high", fs=SR, output="sos"), x)
    return x * env_exp(n, 70, 0.0008)


def saw(freq, n, detune=0.0):
    t = t_axis(n)
    return 2 * ((t * freq * (1 + detune)) % 1.0) - 1


def bass_note(freq, dur):
    n = int(dur * SR)
    x = 0.6 * saw(freq, n) + 0.8 * np.sin(2 * np.pi * freq * t_axis(n))
    x = sosfilt(butter(2, 420, fs=SR, output="sos"), x)
    e = np.minimum(1, t_axis(n) / 0.004) * np.exp(-t_axis(n) * 5.0)
    e *= np.minimum(1, (n - np.arange(n)) / (0.01 * SR))
    return x * e


def pad_chord(notes, dur, cutoff=1400, attack=0.8, release=1.2):
    n = int(dur * SR)
    x = np.zeros(n)
    for m in notes:
        for d in (-0.004, 0.0, 0.0045):
            x += saw(midi(m), n, d)
    x = sosfilt(butter(2, cutoff, fs=SR, output="sos"), x) / (len(notes) * 3)
    t = t_axis(n)
    e = np.minimum(1, t / attack) * np.minimum(1, (dur - t) / release)
    return x * np.clip(e, 0, 1)


def swept_noise(dur, f0, f1, q=1.2, shape=None):
    """noise through a band-pass whose centre glides f0 -> f1 (block-wise, state carried)"""
    n = int(dur * SR)
    x = rng.uniform(-1, 1, n)
    y = np.zeros(n)
    blk = 256
    zi = None
    for b in range(0, n, blk):
        c = f0 * (f1 / f0) ** (b / n)
        lo, hi = c / (1 + 1 / q), min(c * (1 + 1 / q), SR / 2 - 100)
        sos = butter(2, [lo, hi], btype="band", fs=SR, output="sos")
        if zi is None:
            zi = np.zeros((sos.shape[0], 2))
        y[b : b + blk], zi = sosfilt(sos, x[b : b + blk], zi=zi)
    if shape is not None:
        y *= shape(np.linspace(0, 1, n))
    return y / (np.max(np.abs(y)) + 1e-9)


def whoosh(peak_at, dur=0.6, up=False, gain=0.32, pan=0.0):
    f0, f1 = (500, 4200) if up else (4200, 420)
    pk = 0.55
    shape = lambda u: np.where(u < pk, (u / pk) ** 2.2, np.exp(-(u - pk) * 9))
    w = swept_noise(dur, f0, f1, q=1.6, shape=shape)
    dry.add(w, peak_at - pk * dur, gain, pan)
    wet.add(w, peak_at - pk * dur, gain * 0.5, pan)


def impact(at, gain=1.0):
    n = int(2.4 * SR)
    t = t_axis(n)
    sub = np.sin(2 * np.pi * (38 + 30 * np.exp(-t * 8)) * t) * np.exp(-t * 1.6)
    noise = sosfilt(butter(2, 900, fs=SR, output="sos"), rng.uniform(-1, 1, n)) * np.exp(-t * 6)
    dry.add(kick(0.6, 1.4), at, 0.9 * gain)
    dry.add(sub, at, 0.75 * gain)
    dry.add(noise, at, 0.5 * gain)
    wet.add(noise, at, 0.7 * gain)


# ---------------- harmony ----------------
# D minor: Dm - Bb - F - C, one chord per bar (2 s)
CHORDS = [(50, [62, 65, 69]), (46, [62, 65, 70]), (53, [60, 65, 69]), (48, [60, 64, 67])]


def chord_at(t):
    bar = int((t - G0) // 2) % 4
    return CHORDS[bar]


# the B's 14 outline layers peel toward the camera one at a time (BS.drawPeel); a rising pluck on each
PEEL_STARTS = [0, 0.07, 0.12, 0.18, 0.22, 0.26, 0.29, 0.32, 0.35, 0.38, 0.4, 0.42, 0.44, 0.46]
PEEL_NOTES = [69, 72, 74, 76, 79, 81, 84, 86, 88, 91, 93, 96, 98, 100]


def peel(t0, k=1.0, gain=0.07, pan=-0.6, pan_step=0.09):
    for j, (dt, m) in enumerate(zip(PEEL_STARTS, PEEL_NOTES)):
        s_ = pluck(midi(m), 0.45, 0.99, 0.85)
        dry.add(s_, t0 + dt * k, gain + 0.003 * j, pan + j * pan_step)
        wet.add(s_, t0 + dt * k, 0.05)


# ---------------- 0-1 s: frame 0 hits; the code flies into both logos ----------------
dry.add(kick(0.5, 1.2), 0.0, 0.7)
hit = sosfilt(butter(2, 2500, fs=SR, output="sos"), rng.uniform(-1, 1, int(0.5 * SR))) * env_exp(int(0.5 * SR), 9)
dry.add(hit, 0.0, 0.3)
wet.add(hit, 0.0, 0.4)
pent = [62, 65, 67, 69, 72, 74, 77, 79, 81, 84, 86, 89]  # D minor pentatonic, rising with the glyph flight
for j, m in enumerate(pent):
    s_ = pluck(midi(m), 0.9, 0.995, 0.75)
    dry.add(s_, 0.02 + 0.072 * j, 0.17, -0.6 + j / 9)
    wet.add(s_, 0.02 + 0.072 * j, 0.09)
rise = swept_noise(0.95, 400, 6000, q=2.0, shape=lambda u: u ** 2.2)
dry.add(rise, 0.05, 0.16)
wet.add(rise, 0.05, 0.1)
dry.add(pad_chord([38, 45, 50], 1.4, cutoff=700, attack=0.3, release=0.4), 0.0, 0.4)
impact(1.0, 0.9)                                   # logos lock to the official artwork; groove starts
dry.add(pluck(midi(38), 2.0, 0.998, 0.3), 1.0, 0.45)

# ---------------- groove ----------------
END_GROOVE = 25.0
# kick, hats and bass drop out under a riser: the frame flies through the B (10-11 s), and the
# line-up holds still for half a bar (24-25 s) before the end card lands on the downbeat
DROPS = [(10.0, 11.0), (24.0, 25.0)]


def dropped(t):
    return any(a <= t < b for a, b in DROPS)


HATS_FROM = 2.5
beats = int((END_GROOVE - G0) / BEAT)
for b in range(beats):
    t = G0 + b * BEAT
    in_drop = dropped(t)
    if not in_drop:
        dry.add(kick(), t, 0.85)
    if t >= HATS_FROM and not in_drop:
        dry.add(hat(), t + BEAT / 2, 0.16, 0.25)
        if b % 2:
            dry.add(hat(0.03, 9500), t + BEAT * 0.75, 0.07, -0.25)
for k in range(int((END_GROOVE - G0) / (BEAT / 2))):
    t = G0 + k * BEAT / 2
    if dropped(t):
        continue
    root, _ = chord_at(t)
    accent = 1.0 if k % 2 == 0 else 0.65
    dry.add(bass_note(midi(root - 12), 0.22), t, 0.42 * accent)
for k in range(int((END_GROOVE - G0) / (BEAT / 4))):
    t = G0 + k * BEAT / 4
    root, tones = chord_at(t)
    seq = tones + [m + 12 for m in tones]
    order = [0, 2, 4, 1, 3, 5, 2, 4]
    m = seq[order[k % 8]]
    bright = min(1.0, 0.35 + (t - G0) / 20)
    g = 0.15 if dropped(t) else 0.12
    s_ = pluck(midi(m), 0.5, 0.992, bright)
    dry.add(s_, t, g, -0.35 if k % 2 else 0.35)
    wet.add(s_, t, g * 0.5)
for bar in range(int((END_GROOVE - G0) / 2)):
    t = G0 + bar * 2
    root, tones = chord_at(t + 0.01)
    dry.add(pad_chord([root] + tones, 2.3, cutoff=1100, attack=0.3, release=0.4), t, 0.16)
rise2 = swept_noise(1.3, 300, 7000, q=2.2, shape=lambda u: u ** 2.4)
dry.add(rise2, 9.6, 0.22)
wet.add(rise2, 9.6, 0.14)

# ---------------- effects on visible actions ----------------
whoosh(2.15, 0.5, up=True, gain=0.24)            # logos burst into glyphs
impact(2.5, 0.85)                                # the glyphs pour into the B
dry.add(pluck(midi(74), 1.4, 0.996, 0.6), 2.5, 0.22)
dry.add(pluck(midi(81), 1.2, 0.996, 0.7), 3.0, 0.14)   # the line decodes
whoosh(3.9, 0.8, up=False, gain=0.2)             # B swings and unfolds into the building
dry.add(pluck(midi(86), 1.2, 0.996, 0.7), 4.75, 0.18)  # FIRST UP
impact(4.75, 0.35)
dry.add(pluck(midi(84), 1.0, 0.996, 0.7), 7.0, 0.14)
dry.add(pluck(midi(89), 1.0, 0.996, 0.7), 8.75, 0.14)
whoosh(10.0, 0.4, up=False, gain=0.18)           # the building folds back into the B
whoosh(10.8, 0.55, up=True, gain=0.32)           # through the B
peel(10.16)                                      # geo.html: drawPeel T0 10.16
impact(11.0, 0.8)                                # ink: the speakers
sparkle = [86, 89, 91, 93, 96]
for i in range(5):
    w = 11.0 + 2.5 * i
    if i:
        whoosh(w + 0.15, 0.55, up=bool(i % 2), gain=0.28, pan=0.3 if i % 2 else -0.3)   # glyphs fly to the next face
    for j in range(5):                                                                   # the face resolves into the photo
        s_ = pluck(midi(sparkle[j] - (i % 2) * 2), 0.6, 0.993, 0.9)
        dry.add(s_, w + 0.85 + 0.075 * j, 0.09, -0.5 + j / 4)
        wet.add(s_, w + 0.85 + 0.075 * j, 0.07)
    dry.add(pluck(midi([74, 77, 81, 79, 86][i]), 0.9, 0.995, 0.7), w + 0.3, 0.12, 0.2)
# line-up: the camera pulls back from the fifth face and the other four are standing there
whoosh(23.4, 0.7, up=False, gain=0.26)           # pull-back
for j, m in enumerate([86, 84, 81, 79]):         # slots 4, 3, 2, 1 tile in, nearest first
    s_ = pluck(midi(m), 0.7, 0.994, 0.85)
    dry.add(s_, 23.16 + 0.07 * j, 0.13, 0.5 - j * 0.33)
    wet.add(s_, 23.16 + 0.07 * j, 0.09)
impact(24.0, 0.95)                               # all five lock; the groove stops
for m in (50, 62, 69, 74):                       # open fifth rings through the hold
    s_ = pluck(midi(m), 1.6, 0.998, 0.55)
    dry.add(s_, 24.0, 0.16)
    wet.add(s_, 24.0, 0.1)
rise3 = swept_noise(0.95, 300, 7000, q=2.2, shape=lambda u: u ** 2.6)
dry.add(rise3, 24.05, 0.2)
wet.add(rise3, 24.05, 0.13)
whoosh(24.8, 0.6, up=True, gain=0.3)             # five faces pour into the B
peel(24.74, k=0.62, gain=0.06, pan=0.6, pan_step=-0.09)  # speakers.html: drawPeel T0 X0 + 0.34, k 0.62
impact(25.0, 1.0)
# end card: Dm chord rings out under the poster
dry.add(pad_chord([38, 50, 57, 62, 65, 69], 5.0, cutoff=1600, attack=0.05, release=3.0), 25.0, 0.35)
for j, m in enumerate([62, 65, 69, 74]):
    dry.add(pluck(midi(m), 3.5, 0.998, 0.6), 25.3 + 0.09 * j, 0.18, -0.4 + j * 0.27)
    wet.add(pluck(midi(m), 3.5, 0.998, 0.6), 25.3 + 0.09 * j, 0.12)

# ---------------- reverb (generated impulse) and master ----------------
ir_n = int(2.4 * SR)
irt = t_axis(ir_n)
ir_l = rng.normal(0, 1, ir_n) * np.exp(-irt * 2.6)
ir_r = rng.normal(0, 1, ir_n) * np.exp(-irt * 2.6)
lp = butter(1, 5000, fs=SR, output="sos")
ir_l, ir_r = sosfilt(lp, ir_l), sosfilt(lp, ir_r)
ir_l /= np.sqrt(np.sum(ir_l ** 2))
ir_r /= np.sqrt(np.sum(ir_r ** 2))
L = dry.l + fftconvolve(wet.l, ir_l)[:N] * 0.9
R = dry.r + fftconvolve(wet.r, ir_r)[:N] * 0.9
mix = np.stack([L, R], axis=1)
mix = sosfilt(butter(2, 28, btype="high", fs=SR, output="sos"), mix, axis=0)
# fade the tail into the last frame
fade = np.ones(N)
fs = int(28.6 * SR)
fade[fs:] = np.linspace(1, 0, N - fs) ** 1.5
mix *= fade[:, None]
mix = np.tanh(mix * 0.9) / 0.9
mix /= np.max(np.abs(mix)) / 0.89
out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[1] / "build/score-raw.wav"
out.parent.mkdir(parents=True, exist_ok=True)
wavfile.write(out, SR, (mix * 32767).astype(np.int16))
print("wrote", out)
