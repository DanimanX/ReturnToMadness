#!/usr/bin/env python3
"""Procedural audio generator for Return to Madness (Lovecraftian cosmic horror).

Everything is synthesised with NumPy only: no scipy, no samples, no network,
no ffmpeg.  Output is mono 22.05 kHz 16-bit PCM WAV, peak normalised to
-3 dBFS, DC-free, click-free.

    python3 tools/gen_audio.py

Ambience beds and the boss loop are built so that they loop seamlessly:
  * drone / LFO frequencies are quantised to an integer number of cycles per
    loop (f = round(f * duration) / duration),
  * noise beds are generated slightly longer than the loop and the tail is
    equal-power crossfaded into the head,
  * one-shot events (bells, drips, drums...) are placed with wrap-around and
    circular FFT reverb, so their tails reappear correctly at the loop start.
"""

from __future__ import annotations

import math
import time
import wave
from pathlib import Path

import numpy as np

SR = 22050
TWO_PI = 2.0 * math.pi
PEAK_DBFS = -3.0
ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "assets" / "audio"


# ---------------------------------------------------------------------------
# basic helpers
# ---------------------------------------------------------------------------
def n_samples(seconds: float) -> int:
    return int(seconds * SR + 0.5)


def tline(n: int) -> np.ndarray:
    return np.arange(n, dtype=np.float64) / SR


def rng(seed: int) -> np.random.Generator:
    return np.random.default_rng(seed)


def white(n: int, r: np.random.Generator) -> np.ndarray:
    return r.standard_normal(n)


def norm(x: np.ndarray) -> np.ndarray:
    """Peak normalise to 1.0 (guards against silence)."""
    x = np.asarray(x, dtype=np.float64)
    p = float(np.max(np.abs(x))) if x.size else 0.0
    return x / p if p > 1e-12 else x


def qf(freq: float, dur: float) -> float:
    """Quantise a frequency so it completes an integer number of cycles in dur."""
    k = max(1, int(round(freq * dur)))
    return k / dur


def lfo(n: int, rate: float, phase: float = 0.0, lo: float = 0.0,
        hi: float = 1.0, shape: str = "sine") -> np.ndarray:
    """Loop-safe low-frequency oscillator between lo and hi."""
    u = np.arange(n, dtype=np.float64) / SR
    s = np.sin(TWO_PI * rate * u + phase)
    if shape == "tri":
        s = 2.0 / math.pi * np.arcsin(np.clip(s, -1.0, 1.0))
    elif shape == "pulse":
        s = (0.5 + 0.5 * s) ** 2 * 2.0 - 1.0
    return lo + (hi - lo) * (0.5 + 0.5 * s)


def sine(freq: float, n: int, phase: float = 0.0, amp: float = 1.0) -> np.ndarray:
    return amp * np.sin(TWO_PI * freq * tline(n) + phase)


def phase_curve(freq: np.ndarray, phase0: float = 0.0) -> np.ndarray:
    return TWO_PI * np.cumsum(np.asarray(freq, dtype=np.float64)) / SR + phase0


def saw_add(ph: np.ndarray, nh: int = 24, rolloff: float = 0.0) -> np.ndarray:
    """Band-limited sawtooth from an instantaneous phase array (radians)."""
    out = np.zeros_like(ph)
    for k in range(1, nh + 1):
        a = 1.0 / k
        if rolloff:
            a /= (1.0 + rolloff * k * k)
        out += a * np.sin(k * ph)
    return out * (2.0 / math.pi)


def fade_edges(x: np.ndarray, ms: float = 4.0) -> np.ndarray:
    """Taper both ends to zero to guarantee no clicks."""
    x = np.asarray(x, dtype=np.float64).copy()
    n = len(x)
    if n < 4:
        return x
    k = min(max(1, int(SR * ms / 1000.0)), max(1, n // 2))
    x[:k] *= np.linspace(0.0, 1.0, k)
    x[-k:] *= np.linspace(1.0, 0.0, k)
    return x


def env_exp(n: int, attack: float = 0.004, tau: float = 0.1) -> np.ndarray:
    t = tline(n)
    a = np.clip(t / max(attack, 1e-6), 0.0, 1.0) if attack > 0 else np.ones(n)
    return a * np.exp(-t / max(tau, 1e-6))


def swell(n: int, attack: float, release: float) -> np.ndarray:
    """Trapezoid envelope with linear attack/release (implicit hold)."""
    t = tline(n)
    end = t[-1] if n > 1 else 0.0
    a = np.clip(t / max(attack, 1e-6), 0.0, 1.0)
    r = np.clip((end - t) / max(release, 1e-6), 0.0, 1.0)
    return np.minimum(a, r)


def place(buf: np.ndarray, t0: float, sig: np.ndarray) -> None:
    """Add sig into buf at time t0, wrapping the tail around the loop."""
    n = len(buf)
    sig = np.asarray(sig, dtype=np.float64)
    if sig.size == 0:
        return
    start = int(round(t0 * SR)) % n
    idx = (start + np.arange(sig.size)) % n
    buf += np.bincount(idx, weights=sig, minlength=n)[:n]


def fit(sig: np.ndarray, n: int) -> np.ndarray:
    sig = np.asarray(sig, dtype=np.float64)
    if sig.size >= n:
        return sig[:n]
    return np.concatenate([sig, np.zeros(n - sig.size)])


# ---------------------------------------------------------------------------
# filters (FFT magnitude shaping + STFT band sweep)
# ---------------------------------------------------------------------------
def g_lowpass(cut: float, order: int = 2):
    def g(f):
        return 1.0 / np.sqrt(1.0 + (f / max(cut, 1e-9)) ** (2 * order))
    return g


def g_highpass(cut: float, order: int = 2):
    def g(f):
        ff = np.maximum(f, 1e-6)
        return 1.0 / np.sqrt(1.0 + (cut / ff) ** (2 * order))
    return g


def g_bandpass(lo: float, hi: float, order: int = 2):
    a, b = g_highpass(lo, order), g_lowpass(hi, order)
    return lambda f: a(f) * b(f)


def g_peak(center: float, width_oct: float, gain: float = 4.0):
    def g(f):
        lf = np.log2(np.maximum(f, 15.0) / center)
        return 1.0 + (gain - 1.0) * np.exp(-0.5 * (lf / width_oct) ** 2)
    return g


def spectral_filter(x: np.ndarray, gain, pad: int = 0) -> np.ndarray:
    """Apply a smooth magnitude response. pad=0 -> circular (loop safe)."""
    x = np.asarray(x, dtype=np.float64)
    n = len(x)
    xp = np.concatenate([x, np.zeros(pad)]) if pad > 0 else x
    spec = np.fft.rfft(xp)
    f = np.fft.rfftfreq(len(xp), 1.0 / SR)
    y = np.fft.irfft(spec * np.asarray(gain(f), dtype=np.float64), len(xp))
    return y[:n]


def stft_band(x: np.ndarray, fc_func, bw_oct: float = 1.0,
              frame: int = 512, hop: int = 128) -> np.ndarray:
    """Time-varying gaussian band filter (log-frequency), overlap-add."""
    x = np.asarray(x, dtype=np.float64)
    n = len(x)
    win = np.hanning(frame)
    out = np.zeros(n + frame)
    wsum = np.zeros(n + frame)
    freqs = np.fft.rfftfreq(frame, 1.0 / SR)
    logf = np.log2(np.maximum(freqs, 15.0))
    for start in range(0, n, hop):
        seg = x[start:start + frame]
        if len(seg) < frame:
            seg = np.pad(seg, (0, frame - len(seg)))
        spec = np.fft.rfft(seg * win)
        fc = max(15.0, float(fc_func(start + frame // 2)))
        g = np.exp(-0.5 * ((logf - math.log2(fc)) / max(bw_oct, 0.05)) ** 2)
        out[start:start + frame] += np.fft.irfft(spec * g, frame) * win
        wsum[start:start + frame] += win ** 2
    out /= np.maximum(wsum, 0.05)
    return out[:n]


def formant_filter(x: np.ndarray, formants, bw: float = 0.32,
                   pad: int = 0) -> np.ndarray:
    """Vowel-like bank of gaussian resonances (formants = [(Hz, gain), ...])."""
    def g(f):
        lf = np.log2(np.maximum(f, 15.0))
        acc = np.zeros_like(f)
        for F, a in formants:
            acc += a * np.exp(-0.5 * ((lf - math.log2(F)) / bw) ** 2)
        return acc
    return spectral_filter(x, g, pad=pad)


# ---------------------------------------------------------------------------
# reverb: synthetic impulse response + FFT convolution
# ---------------------------------------------------------------------------
def make_ir(seconds: float, decay: float, cutoff: float, seed: int,
            early=((0.011, 0.55), (0.019, 0.36), (0.029, 0.24),
                   (0.041, 0.16), (0.057, 0.10))) -> np.ndarray:
    n = n_samples(seconds)
    r = rng(seed)
    t = tline(n)
    ir = white(n, r) * np.exp(-t / max(decay, 1e-4))
    ir = spectral_filter(ir, g_lowpass(cutoff, 2), pad=0)
    ir = spectral_filter(ir, g_highpass(70.0, 1), pad=0)
    for d, g in early:
        i = int(d * SR)
        if i < n:
            ir[i] += g
    ir = np.concatenate([np.zeros(int(0.007 * SR)), ir])
    ir = norm(ir)
    tail = min(int(0.05 * SR), len(ir))
    ir[-tail:] *= np.linspace(1.0, 0.0, tail)
    return ir


def reverb_loop(x: np.ndarray, ir: np.ndarray) -> np.ndarray:
    """Circular convolution: keeps a loop perfectly periodic."""
    n = len(x)
    if len(ir) > n:
        ir = ir[:n]
    h = np.fft.rfft(np.pad(ir, (0, n - len(ir))), n)
    return np.fft.irfft(np.fft.rfft(x, n) * h, n)


def reverb_once(x: np.ndarray, ir: np.ndarray) -> np.ndarray:
    n = len(x)
    L = n + len(ir) - 1
    Lp = 1 << (L - 1).bit_length()
    y = np.fft.irfft(np.fft.rfft(x, Lp) * np.fft.rfft(ir, Lp), Lp)
    return y[:n]


def reverb(x: np.ndarray, ir: np.ndarray, wet: float = 0.4,
           circular: bool = True) -> np.ndarray:
    w = reverb_loop(x, ir) if circular else reverb_once(x, ir)
    peak = float(np.max(np.abs(x))) if x.size else 0.0
    return x + wet * norm(w) * peak


def loop_noise(n: int, gain, r: np.random.Generator, xfade: float = 0.8,
               lfo: np.ndarray | None = None) -> np.ndarray:
    """Seamless noise bed: filter, then equal-power crossfade tail -> head."""
    xf = max(16, int(xfade * SR))
    raw = spectral_filter(white(n + xf, r), gain, pad=0)
    out = raw[:n].copy()
    u = np.linspace(0.0, 1.0, xf, endpoint=False)
    rise = np.sin(0.5 * math.pi * u)
    fall = np.cos(0.5 * math.pi * u)
    out[:xf] = raw[:xf] * rise + raw[n:n + xf] * fall
    if lfo is not None:
        out *= lfo
    return out


# ---------------------------------------------------------------------------
# instruments / primitives
# ---------------------------------------------------------------------------
def choir_voice(f0: float, n: int, formants, dur: float,
                r: np.random.Generator, vib_hz: float = 0.25,
                vib_depth: float = 0.004, nh: int = 24,
                breath: float = 0.03) -> np.ndarray:
    """Additive vowel/choral tone; loop-safe when vib_hz divides the loop."""
    fq = qf(f0, dur)
    t = tline(n)
    vib = 1.0 + vib_depth * np.sin(TWO_PI * vib_hz * t + r.uniform(0.0, TWO_PI))
    ph = phase_curve(np.full(n, fq) * vib)
    out = np.zeros(n)
    for k in range(1, nh + 1):
        fk = fq * k
        if fk > 8000.0:
            break
        g = sum(math.exp(-0.5 * ((fk - F) / (0.30 * F)) ** 2) for F in formants)
        out += (g / (k ** 0.7)) * np.sin(k * ph + r.uniform(0.0, TWO_PI))
    if breath > 0:
        out += breath * spectral_filter(white(n, r), g_bandpass(300, 3000, 2), pad=0)
    return norm(out)


def bell(f0: float, seconds: float, decay: float, seed: int,
         partials=((1.0, 1.0), (2.76, 0.55), (5.40, 0.32),
                   (8.93, 0.18), (13.34, 0.09))) -> np.ndarray:
    n = n_samples(seconds)
    t = tline(n)
    r = rng(seed)
    out = np.zeros(n)
    for i, (ratio, amp) in enumerate(partials):
        tau = decay / (1.0 + 0.55 * i)
        out += amp * np.sin(TWO_PI * f0 * ratio * t + r.uniform(0.0, TWO_PI)) * np.exp(-t / tau)
    out *= np.clip(t / 0.003, 0.0, 1.0)
    return norm(out)


def drip(r: np.random.Generator) -> np.ndarray:
    dur = 0.18
    n = n_samples(dur)
    t = tline(n)
    f0 = r.uniform(700.0, 1600.0)
    f = f0 * np.exp(-t * r.uniform(9.0, 18.0)) + 180.0
    sig = np.sin(phase_curve(f)) * np.exp(-t / 0.045)
    sig += 0.35 * spectral_filter(white(n, r), g_bandpass(1800, 7000, 2), pad=0) \
        * np.exp(-t / 0.010)
    return fade_edges(norm(sig), 2.0)


def bubble(r: np.random.Generator) -> np.ndarray:
    dur = r.uniform(0.04, 0.11)
    n = n_samples(dur)
    f0 = r.uniform(85.0, 230.0)
    f1 = f0 * r.uniform(1.4, 2.8)
    sig = np.sin(phase_curve(np.linspace(f0, f1, n))) * np.hanning(n)
    return fade_edges(sig, 1.5)


def frame_drum(r: np.random.Generator, vel: float = 1.0) -> np.ndarray:
    dur = 0.55
    n = n_samples(dur)
    t = tline(n)
    f = 48.0 + 95.0 * np.exp(-t / 0.05)
    body = np.sin(phase_curve(f)) * np.exp(-t / 0.16)
    body += 0.40 * np.sin(0.5 * phase_curve(f)) * np.exp(-t / 0.28)
    thump = spectral_filter(white(n, r), g_lowpass(380, 2), pad=SR // 4)
    sig = body + 0.55 * norm(thump) * np.exp(-t / 0.035)
    return fade_edges(vel * norm(sig), 3.0)


def bone_clack(r: np.random.Generator, vel: float = 0.5) -> np.ndarray:
    dur = 0.12
    n = n_samples(dur)
    t = tline(n)
    sig = spectral_filter(white(n, r), g_bandpass(1800, 6500, 2), pad=SR // 4)
    sig = norm(sig) * np.exp(-t / 0.014)
    sig += 0.35 * np.sin(TWO_PI * r.uniform(2400, 3900) * t) * np.exp(-t / 0.009)
    return fade_edges(vel * norm(sig), 1.5)


def string_drone(f: float, n: int, dur: float, r: np.random.Generator,
                 nh: int = 18) -> np.ndarray:
    t = tline(n)
    vib = (1.0 + 0.0030 * np.sin(TWO_PI * 5.0 * t + r.uniform(0.0, TWO_PI))
           + 0.0022 * np.sin(TWO_PI * 0.25 * t + r.uniform(0.0, TWO_PI)))
    ph = phase_curve(np.full(n, qf(f, dur)) * vib)
    sig = saw_add(ph, nh)
    sig = spectral_filter(sig, g_lowpass(1900, 2))
    sig = spectral_filter(sig, g_highpass(45, 2))
    return norm(sig)


def brass_swell(seconds: float, seed: int) -> np.ndarray:
    n = n_samples(seconds)
    r = rng(seed)
    t = tline(n)
    out = np.zeros(n)
    for f, a in ((110.0, 1.0), (165.0, 0.55), (220.0, 0.5), (277.75, 0.32)):
        vib = 1.0 + 0.004 * np.sin(TWO_PI * 4.5 * t + r.uniform(0.0, TWO_PI))
        out += a * saw_add(phase_curve(np.full(n, f) * vib), 14)
    out = spectral_filter(out, g_peak(950.0, 0.9, 1.6), pad=SR // 4)
    out = spectral_filter(out, g_lowpass(2600, 2), pad=SR // 4)
    env = swell(n, 1.1, 0.9)
    return fade_edges(norm(out * env), 8.0)


def metal_chirp(r: np.random.Generator) -> np.ndarray:
    dur = r.uniform(0.015, 0.045)
    n = n_samples(dur)
    t = tline(n)
    fc = r.uniform(2200.0, 5200.0)
    idx = r.uniform(0.6, 2.2)
    mod = np.sin(TWO_PI * fc * r.uniform(1.2, 1.7) * t)
    sig = np.sin(TWO_PI * fc * t + idx * mod) * np.exp(-t / (dur * 0.35))
    return fade_edges(sig, 1.0)


def crackle(r: np.random.Generator) -> np.ndarray:
    dur = r.uniform(0.002, 0.006)
    n = max(12, n_samples(dur))
    sig = spectral_filter(white(n, r), g_highpass(3200, 1), pad=0)
    sig *= np.exp(-tline(n) / 0.0025)
    return fade_edges(norm(sig), 0.4)


def whisper_utterance(r: np.random.Generator, dur: float) -> np.ndarray:
    n = n_samples(dur)
    t = tline(n)
    env = np.zeros(n)
    for _ in range(int(r.integers(3, 7))):
        c = r.uniform(0.05, max(0.06, dur - 0.05))
        w = r.uniform(0.035, 0.11)
        env += r.uniform(0.35, 1.0) * np.exp(-0.5 * ((t - c) / w) ** 2)
    env = norm(env)
    src = white(n, r)
    v = formant_filter(src, [(r.uniform(400, 700), 1.0),
                             (r.uniform(1000, 1800), 0.85),
                             (r.uniform(2300, 3500), 0.45)],
                      bw=0.33, pad=SR // 4)
    v = spectral_filter(v, g_bandpass(280, 6500, 2), pad=SR // 4)
    return fade_edges(norm(v * env), 3.0)


def reversed_swell(r: np.random.Generator, dur: float,
                   f_lo: float = 220.0, f_hi: float = 4200.0) -> np.ndarray:
    n = n_samples(dur)
    t = tline(n)
    src = white(n, r)
    fc = lambda i: f_lo * (f_hi / f_lo) ** ((min(i, n) / n) ** 1.7)
    y = stft_band(src, fc, bw_oct=1.1, frame=1024, hop=256)
    env = (t / t[-1]) ** 2.2
    env *= np.clip((t[-1] - t) / 0.09, 0.0, 1.0)
    return y * env


# ---------------------------------------------------------------------------
# ambience beds (24.0 s seamless loops)
# ---------------------------------------------------------------------------
def amb_1_drowned_coast() -> np.ndarray:
    """Drowned coast at night: sea rumble, rain hiss, distant bell, choir."""
    dur = 24.0
    n = n_samples(dur)
    r = rng(1101)
    out = np.zeros(n)

    rum = loop_noise(n, g_lowpass(150, 3), r, 0.9)
    rum *= lfo(n, 1 / 24, 0.0, 0.55, 1.0) * lfo(n, 3 / 24, 1.7, 0.60, 1.0)
    rum += 0.55 * loop_noise(n, g_bandpass(70, 240, 2), r, 0.9,
                             lfo=lfo(n, 2 / 24, 2.3, 0.5, 1.0))
    out += 0.80 * norm(rum)

    for f, a, ph in ((36.0, 0.20, 0.0), (42.0, 0.13, 1.3), (54.0, 0.08, 2.1)):
        out += a * np.sin(TWO_PI * qf(f, dur) * tline(n) + ph) \
            * lfo(n, 1 / 24, ph, 0.55, 1.0)

    rain = loop_noise(n, g_bandpass(1800, 9000, 2), r, 0.9,
                      lfo=lfo(n, 1 / 24, 0.4, 0.50, 1.0) * lfo(n, 6 / 24, 1.0, 0.6, 1.0))
    rain = spectral_filter(rain, g_peak(5200, 1.2, 2.0), pad=0)
    out += 0.26 * norm(rain)

    # sparse raindrop ticks
    for _ in range(70):
        m = n_samples(r.uniform(0.004, 0.012))
        drop = spectral_filter(white(m, r), g_bandpass(3500, 9000, 2), pad=0)
        place(out, float(r.uniform(0.0, dur)), 0.05 * fade_edges(norm(drop), 0.3))

    for t0, amp in ((0.8, 0.10), (6.4, 0.08), (12.9, 0.11), (19.3, 0.075)):
        m = n_samples(4.5)
        w = spectral_filter(white(m, r), g_bandpass(250, 1700, 2), pad=SR // 2)
        w = norm(w) * swell(m, 1.7, 2.1)
        place(out, t0, amp * w)

    ir = make_ir(3.2, 1.15, 2900, 71)
    bell_bus = np.zeros(n)
    b = bell(196.0, 6.0, 2.1, 72)
    place(bell_bus, 5.2, 0.110 * b)
    place(bell_bus, 17.4, 0.080 * b)
    out += reverb(bell_bus, ir, 0.75, circular=True)

    ch = choir_voice(73.42, n, (360.0, 760.0, 1180.0, 2350.0), dur, r,
                     vib_hz=1 / 24, vib_depth=0.005, breath=0.05)
    out += 0.100 * ch * lfo(n, 1 / 24, 0.9, 0.55, 1.0)
    out += 0.055 * choir_voice(110.0, n, (500.0, 900.0, 1500.0), dur, r,
                               vib_hz=2 / 24, vib_depth=0.004) \
        * lfo(n, 3 / 24, 2.0, 0.3, 1.0)

    out = spectral_filter(out, g_highpass(22, 2), pad=0)
    return norm(out)


def amb_2_flooded_catacombs() -> np.ndarray:
    """Flooded catacombs: drips, sub drone, bubbling, stone reverb."""
    dur = 24.0
    n = n_samples(dur)
    r = rng(2202)
    out = np.zeros(n)

    for f, a, ph in ((28.0, 0.22, 0.0), (41.5, 0.11, 1.9), (56.0, 0.09, 3.1),
                     (83.0, 0.05, 0.7)):
        out += a * np.sin(TWO_PI * qf(f, dur) * tline(n) + ph) \
            * lfo(n, 1 / 24, ph, 0.5, 1.0) * lfo(n, 5 / 24, ph * 0.5, 0.7, 1.0)

    bed = loop_noise(n, g_lowpass(300, 2), r, 0.9,
                     lfo=lfo(n, 2 / 24, 0.6, 0.55, 1.0) * lfo(n, 7 / 24, 1.4, 0.7, 1.0))
    bed = spectral_filter(bed, g_peak(180.0, 0.9, 2.4), pad=0)
    out += 0.28 * norm(bed)

    wet = np.zeros(n)
    for _ in range(30):
        sig = drip(r)
        place(wet, float(r.uniform(0.0, dur)), sig * r.uniform(0.25, 0.9))
    for _ in range(40):
        sig = bubble(r)
        place(out, float(r.uniform(0.0, dur)), sig * r.uniform(0.05, 0.14))

    ir = make_ir(3.0, 1.0, 2100, 73)
    out += reverb(wet, ir, 0.95, circular=True) * 0.55

    rumble = loop_noise(n, g_bandpass(60, 180, 2), r, 0.9,
                        lfo=lfo(n, 1 / 24, 2.7, 0.4, 1.0))
    out += 0.12 * norm(rumble)

    out = spectral_filter(out, g_highpass(20, 2), pad=0)
    return norm(out)


def amb_3_forbidden_library() -> np.ndarray:
    """Forbidden library: dust, creaking wood, page turns, oppressive hum."""
    dur = 24.0
    n = n_samples(dur)
    r = rng(3303)
    out = np.zeros(n)

    # oppressive low hum: detuned drone stack + soft lowpassed saw
    hum = np.zeros(n)
    for f, a in ((55.0, 0.20), (55.05, 0.15), (110.0, 0.10), (165.0, 0.05)):
        hum += a * np.sin(TWO_PI * qf(f, dur) * tline(n) + r.uniform(0.0, TWO_PI))
    hum += 0.10 * spectral_filter(saw_add(phase_curve(np.full(n, qf(55.0, dur))), 12),
                                  g_lowpass(420, 2), pad=0)
    hum *= lfo(n, 1 / 24, 0.0, 0.65, 1.0) * lfo(n, 4 / 24, 2.2, 0.8, 1.0)
    out += hum

    dust = loop_noise(n, g_highpass(4200, 2), r, 0.9,
                      lfo=lfo(n, 4 / 24, 0.3, 0.35, 1.0) * lfo(n, 9 / 24, 2.0, 0.6, 1.0))
    dust = spectral_filter(dust, g_lowpass(10500, 2), pad=0)
    out += 0.085 * norm(dust)

    # creaking wood: pitch-gliding band-limited saw with wobble
    def creak(seed: int) -> np.ndarray:
        pr = rng(seed)
        m = n_samples(0.95)
        tt = tline(m)
        f = np.linspace(pr.uniform(78, 105), pr.uniform(130, 175), m)
        f *= 1.0 + 0.035 * np.sin(TWO_PI * 7.0 * tt + pr.uniform(0.0, TWO_PI))
        s = saw_add(phase_curve(f), 18)
        s = spectral_filter(s, g_bandpass(180, 2400, 2), pad=SR // 4)
        env = swell(m, 0.07, 0.35) * (0.55 + 0.45 * np.sin(TWO_PI * 11.0 * tt) ** 2)
        return fade_edges(norm(s * env), 5.0)

    place(out, 3.1, 0.160 * creak(31))
    place(out, 9.7, 0.130 * creak(32))
    place(out, 18.4, 0.170 * creak(33))

    # distant page turns
    page_bus = np.zeros(n)
    for t0, seed in ((4.6, 41), (11.3, 42), (19.9, 43)):
        m = n_samples(0.32)
        pr = rng(seed)
        src = white(m, pr)
        p = stft_band(src, lambda i: 1000.0 + 3200.0 * math.sin(math.pi * min(i, m) / m) ** 1.5,
                      bw_oct=1.2, frame=256, hop=64)
        p = norm(p) * swell(m, 0.05, 0.13) \
            * (0.6 + 0.4 * np.abs(np.sin(TWO_PI * 23 * tline(m))))
        place(page_bus, t0, 0.18 * fade_edges(p, 4.0))
    out += reverb(page_bus, make_ir(2.4, 0.8, 2600, 74), 0.6, circular=True)

    room = loop_noise(n, g_lowpass(220, 2), r, 0.9,
                      lfo=lfo(n, 1 / 24, 1.3, 0.6, 1.0))
    out += 0.12 * norm(room)
    out = spectral_filter(out, g_highpass(22, 2), pad=0)
    return norm(out)


def amb_4_frozen_plateau() -> np.ndarray:
    """Frozen plateau: howling wind, thin whistle, ice cracks, hollow drone."""
    dur = 24.0
    n = n_samples(dur)
    r = rng(4404)
    out = np.zeros(n)
    t = tline(n)

    # wind: three moving bands with independent slow swells
    wind = np.zeros(n)
    for lo, hi, rate, ph, a in ((180, 620, 1 / 24, 0.0, 0.9),
                                (500, 1500, 3 / 24, 1.1, 0.8),
                                (1400, 4200, 5 / 24, 2.3, 0.55)):
        band = loop_noise(n, g_bandpass(lo, hi, 2), r, 0.9,
                          lfo=lfo(n, rate, ph, 0.20, 1.0) ** 1.7)
        wind += a * norm(band)
    out += 0.34 * norm(wind)

    # thin high whistle with slow pitch drift
    for f, a, depth in ((2630.0, 0.050, 22.0), (3170.0, 0.026, 13.0)):
        drift = 1.0 + depth / f * np.sin(TWO_PI * (2 / 24) * t + r.uniform(0.0, TWO_PI))
        wh = np.sin(phase_curve(np.full(n, qf(f, dur)) * drift))
        wh *= lfo(n, 3 / 24, r.uniform(0.0, TWO_PI), 0.15, 1.0) ** 2
        out += a * wh

    # hollow drone
    for f, a in ((98.0, 0.14), (147.0, 0.08), (196.0, 0.045), (293.5, 0.02)):
        out += a * np.sin(TWO_PI * qf(f, dur) * t + r.uniform(0.0, TWO_PI)) \
            * lfo(n, 1 / 24, 0.8, 0.55, 1.0)

    # ice cracks
    ice_bus = np.zeros(n)
    for t0, seed in ((2.4, 51), (7.9, 52), (13.2, 53), (18.1, 54), (22.6, 55)):
        pr = rng(seed)
        m = n_samples(pr.uniform(0.03, 0.075))
        c = spectral_filter(white(m, pr), g_highpass(1800, 2), pad=SR // 8)
        c = norm(c) * np.exp(-tline(m) / (m / SR * 0.30))
        c += 0.4 * np.sin(TWO_PI * pr.uniform(2200, 4200) * tline(m)) \
            * np.exp(-tline(m) / 0.012)
        place(ice_bus, t0, 0.30 * fade_edges(norm(c), 2.0))
    out += reverb(ice_bus, make_ir(2.8, 1.05, 5200, 75), 0.55, circular=True)

    out = spectral_filter(out, g_highpass(24, 2), pad=0)
    return norm(out)


def amb_5_fungal_machine_city() -> np.ndarray:
    """Alien fungal machine city: organic pulses, metal insects, crackle, dissonance."""
    dur = 24.0
    n = n_samples(dur)
    r = rng(5505)
    out = np.zeros(n)
    t = tline(n)

    # pulsing organic hum
    pulse_a = 0.5 + 0.5 * np.sin(TWO_PI * (36 / 24) * t)
    pulse_b = 0.5 + 0.5 * np.sin(TWO_PI * (26 / 24) * t + 0.7)
    hum = np.zeros(n)
    for f, a, pl in ((55.0, 0.22, pulse_a), (82.5, 0.13, pulse_b),
                     (110.0, 0.07, pulse_a), (137.5, 0.04, pulse_b)):
        hum += a * np.sin(TWO_PI * qf(f, dur) * t + r.uniform(0.0, TWO_PI)) \
            * (0.35 + 0.65 * pl ** 2)
    hum += 0.12 * spectral_filter(
        saw_add(phase_curve(np.full(n, qf(55.0, dur))), 14),
        g_lowpass(700, 2), pad=0) * (0.4 + 0.6 * pulse_a)
    out += norm(hum) * 0.55

    # dissonant interval (minor second + tritone) with slow beating
    diss = np.zeros(n)
    for f, a in ((220.0, 0.12), (231.0, 0.10), (311.0, 0.085), (440.0, 0.040)):
        diss += a * np.sin(TWO_PI * qf(f, dur) * t + r.uniform(0.0, TWO_PI))
    diss *= lfo(n, 3 / 24, 0.9, 0.45, 1.0)
    out += diss

    # metallic insects
    insect_bus = np.zeros(n)
    for _ in range(90):
        t0 = float(r.uniform(0.0, dur))
        g = metal_chirp(r)
        place(insect_bus, t0, g * r.uniform(0.05, 0.18))
    insect_bus = spectral_filter(insect_bus, g_bandpass(1600, 8500, 2), pad=0)
    out += 0.95 * norm(insect_bus)

    # electric crackle
    for _ in range(110):
        place(out, float(r.uniform(0.0, dur)), crackle(r) * r.uniform(0.03, 0.12))

    # machinery thuds
    thud_bus = np.zeros(n)
    for k in range(24):
        m = n_samples(0.35)
        tt = tline(m)
        f = 70.0 + 45.0 * np.exp(-tt / 0.03)
        s = np.sin(phase_curve(f)) * np.exp(-tt / 0.09)
        s += 0.3 * spectral_filter(white(m, r), g_lowpass(500, 2), pad=SR // 8) \
            * np.exp(-tt / 0.02)
        place(thud_bus, k * 1.0 + 0.25, 0.10 * fade_edges(norm(s), 2.0))
    out += reverb(thud_bus, make_ir(1.8, 0.55, 3000, 76), 0.4, circular=True)

    out = spectral_filter(out, g_highpass(25, 2), pad=0)
    return norm(out)


def amb_6_dream_of_rlyeh() -> np.ndarray:
    """Dream of R'lyeh: beating detuned drones, reversed swells, whispers."""
    dur = 24.0
    n = n_samples(dur)
    r = rng(6606)
    t = tline(n)
    out = np.zeros(n)

    # slow detuned drone pairs -> long uneven beating
    for f, det, a, rate in ((55.0, 0.25, 0.16, 1 / 24),
                            (55.0, 0.5, 0.12, 2 / 24),
                            (82.5, 0.375, 0.10, 1 / 24),
                            (110.0, 0.75, 0.07, 3 / 24),
                            (146.875, 0.5, 0.05, 2 / 24)):
        for sign in (-1.0, 1.0):
            fq = qf(f + sign * det / 2.0, dur)
            out += a * np.sin(TWO_PI * fq * t + r.uniform(0.0, TWO_PI)) \
                * lfo(n, rate, r.uniform(0.0, TWO_PI), 0.55, 1.0)

    # low saw haze
    haze = np.zeros(n)
    for f, a in ((55.0, 0.10), (82.5, 0.06), (110.0, 0.04)):
        haze += a * spectral_filter(saw_add(phase_curve(np.full(n, qf(f, dur))), 12),
                                    g_lowpass(320, 2), pad=0)
    out += haze * lfo(n, 1 / 24, 1.4, 0.4, 1.0)

    # reversed-sounding swells (rise in level and brightness, abrupt stop)
    for t0, seed, amp in ((3.0, 61, 0.16), (8.4, 62, 0.13),
                          (14.1, 63, 0.17), (20.2, 64, 0.12)):
        place(out, t0, amp * reversed_swell(rng(seed), 3.8))

    # whispers
    for t0, seed in ((1.6, 71), (6.2, 72), (11.8, 73), (17.3, 74), (21.9, 75)):
        place(out, t0, 0.110 * whisper_utterance(rng(seed), 1.5))

    # sub pressure swells
    out += 0.10 * np.sin(TWO_PI * qf(30.0, dur) * t) * lfo(n, 1 / 24, 0.5, 0.1, 1.0) ** 2

    out += reverb(out.copy(), make_ir(3.4, 1.4, 3200, 77), 0.22, circular=True)
    out = spectral_filter(out, g_highpass(22, 2), pad=0)
    return norm(out)


def amb_7_throne_of_cthulhu() -> np.ndarray:
    """Throne of Cthulhu: sub pressure, colossal breathing, choir of the deep."""
    dur = 24.0
    n = n_samples(dur)
    r = rng(7707)
    t = tline(n)
    out = np.zeros(n)

    # immense sub pressure
    for f, a, ph in ((27.5, 0.26, 0.0), (41.25, 0.17, 1.2), (55.0, 0.10, 2.4)):
        out += a * np.sin(TWO_PI * qf(f, dur) * t + ph) \
            * lfo(n, 1 / 24, ph, 0.65, 1.0) * lfo(n, 1 / 24, ph * 2, 0.55, 1.0)

    # colossal breathing: 4 breath cycles in 24 s
    breath_env = (0.5 + 0.5 * np.sin(TWO_PI * (4 / 24) * t - math.pi / 2)) ** 1.6
    breath_env *= 0.75 + 0.25 * np.sin(TWO_PI * (12 / 24) * t)
    breath = loop_noise(n, g_bandpass(160, 950, 2), r, 0.9)
    breath = spectral_filter(breath, g_peak(420.0, 1.0, 2.0), pad=0)
    out += 0.38 * norm(breath) * breath_env

    # choir of the deep: detuned minor cluster, deep formants
    choir = np.zeros(n)
    for f, a in ((55.0, 0.13), (65.375, 0.10), (82.5, 0.09), (110.0, 0.05)):
        choir += a * choir_voice(f, n, (330.0, 700.0, 1150.0, 2200.0), dur, r,
                                 vib_hz=1 / 24, vib_depth=0.008, breath=0.06)
    choir *= lfo(n, 2 / 24, 0.0, 0.55, 1.0) * lfo(n, 1 / 24, 1.5, 0.7, 1.0)
    out += 0.46 * choir

    # instability: slow amplitude flutter
    out *= 1.0 + 0.08 * lfo(n, 3 / 24, 2.1, -1.0, 1.0)
    out += 0.04 * np.sin(TWO_PI * qf(220.0, dur) * t
                         * (1.0 + 0.004 * np.sin(TWO_PI * (2 / 24) * t)))

    out += reverb(out.copy(), make_ir(4.0, 1.8, 1800, 78), 0.30, circular=True)
    out = spectral_filter(out, g_highpass(20, 2), pad=0)
    return norm(out)


# ---------------------------------------------------------------------------
# music: 32 s seamless boss loop, 75 BPM (= 40 beats / 32 s, ~72 BPM)
# ---------------------------------------------------------------------------
def mus_boss() -> np.ndarray:
    dur = 32.0
    n = n_samples(dur)
    r = rng(8808)
    out = np.zeros(n)
    beat = 0.8                 # 75 BPM -> exactly 40 beats in 32 s
    eighth = beat / 2.0

    # ritual percussion -----------------------------------------------------
    drum_pat = (0, 3, 6)       # eighth-note grid inside a 4/4 bar (8 steps)
    clack_pat = (2, 5, 7)
    for bar in range(10):
        bar_t = bar * 4 * beat
        for s in drum_pat:
            vel = 1.0 if s == 0 else 0.68
            if bar % 4 == 3 and s == 6:
                vel *= 1.12
            place(out, bar_t + s * eighth, 0.46 * frame_drum(r, vel))
        for s in clack_pat:
            vel = 0.45 + 0.12 * r.uniform(0.0, 1.0)
            if s == 5:
                vel *= 1.25
            place(out, bar_t + s * eighth, vel * bone_clack(r))
        # extra low hit on the "and" of beat 3 every other bar
        if bar % 2 == 1:
            place(out, bar_t + 7 * eighth, 0.30 * frame_drum(r, 0.55))

    # dissonant string cluster ----------------------------------------------
    for f, a, rate in ((110.0, 0.22, 1 / 32), (116.875, 0.18, 2 / 32),
                       (155.5, 0.16, 1 / 32), (220.0, 0.08, 3 / 32),
                       (233.0, 0.06, 2 / 32)):
        s = string_drone(f, n, dur, r)
        out += a * s * lfo(n, rate, r.uniform(0.0, TWO_PI), 0.55, 1.0)

    # brass-ish swells -------------------------------------------------------
    for t0, seed, amp in ((8.0, 81, 0.45), (22.4, 82, 0.40)):
        place(out, t0, amp * brass_swell(3.0, seed))

    # sub pulse under the drums ---------------------------------------------
    sub = np.sin(TWO_PI * qf(55.0, dur) * tline(n))
    sub *= 0.45 + 0.55 * (0.5 + 0.5 * np.sin(TWO_PI * (20 / 32) * tline(n))) ** 4
    out += 0.10 * sub

    out += reverb(out.copy(), make_ir(2.2, 0.75, 2600, 83), 0.18, circular=True)
    out = spectral_filter(out, g_highpass(25, 2), pad=0)
    return norm(out)


# ---------------------------------------------------------------------------
# one-shot SFX
# ---------------------------------------------------------------------------
def sfx_swing() -> np.ndarray:
    n = n_samples(0.22)
    r = rng(9101)
    t = tline(n)
    src = white(n, r)
    sig = stft_band(src, lambda i: 2900.0 * math.exp(-2.4 * i / n) + 260.0,
                    bw_oct=1.0, frame=256, hop=64)
    sig += 0.25 * stft_band(white(n, r),
                            lambda i: 800.0 * math.exp(-1.6 * i / n) + 120.0,
                            bw_oct=1.3, frame=256, hop=64)
    sig *= swell(n, 0.015, 0.075) * np.exp(-t / 0.075)
    return fade_edges(norm(sig), 5.0)


def sfx_hit() -> np.ndarray:
    n = n_samples(0.16)
    r = rng(9102)
    t = tline(n)
    crack = spectral_filter(white(n, r), g_highpass(1400, 2), pad=SR // 8)
    crack = norm(crack) * np.exp(-t / 0.012)
    thud = np.sin(phase_curve(48.0 + 80.0 * np.exp(-t / 0.03))) * np.exp(-t / 0.055)
    squelch = stft_band(white(n, r), lambda i: 1400.0 * math.exp(-1.9 * i / n) + 260.0,
                        bw_oct=0.85, frame=256, hop=64)
    squelch = norm(squelch) * np.exp(-t / 0.045)
    sig = np.tanh(1.4 * (1.30 * crack + 0.80 * thud + 0.90 * squelch))
    return fade_edges(norm(sig), 4.0)


def sfx_hurt() -> np.ndarray:
    n = n_samples(0.34)
    r = rng(9103)
    t = tline(n)
    thud = np.sin(phase_curve(45.0 + 55.0 * np.exp(-t / 0.05))) * np.exp(-t / 0.12)
    thud += 0.4 * spectral_filter(white(n, r), g_lowpass(300, 2), pad=SR // 8) \
        * np.exp(-t / 0.05)
    sting = np.zeros(n)
    for f in (392.0, 415.3, 587.0):
        sting += saw_add(phase_curve(np.full(n, f)), 14)
    sting = spectral_filter(sting, g_bandpass(500, 3800, 2), pad=SR // 8)
    sting = norm(sting) * np.exp(-t / 0.11) * np.clip(t / 0.006, 0.0, 1.0)
    sting = np.tanh(2.0 * sting)
    sig = 0.85 * thud + 0.55 * sting
    return fade_edges(norm(sig), 6.0)


def sfx_dash() -> np.ndarray:
    n = n_samples(0.26)
    r = rng(9104)
    body = stft_band(white(n, r), lambda i: 3400.0 * (i / n) ** 0.8 + 260.0,
                     bw_oct=0.95, frame=256, hop=64)
    body *= swell(n, 0.05, 0.10)
    air = stft_band(white(n, r), lambda i: 700.0 + 900.0 * (i / n),
                    bw_oct=1.4, frame=256, hop=64) * swell(n, 0.03, 0.12) * 0.5
    sig = body + air
    return fade_edges(norm(sig), 6.0)


def sfx_voice() -> np.ndarray:
    """The Insight scream: distorted formant scream, layered detuned voices."""
    dur = 0.90
    n = n_samples(dur)
    r = rng(9105)
    t = tline(n)
    base = (150.0
            + 95.0 * np.exp(-0.5 * ((t - 0.22) / 0.16) ** 2)
            + 55.0 * np.exp(-0.5 * ((t - 0.55) / 0.28) ** 2))
    wobble = spectral_filter(white(n, r), g_lowpass(14, 2), pad=SR // 4)
    f0 = base + 7.0 * norm(wobble) + 4.0 * np.sin(TWO_PI * 5.5 * t) \
        + 1.5 * np.sin(TWO_PI * 13.0 * t)
    f0 = np.clip(f0, 70.0, 420.0)

    sig = np.zeros(n)
    for det, delay, amp in ((0.94, 0.000, 1.0), (1.00, 0.008, 1.0), (1.065, 0.017, 0.8)):
        ph = phase_curve(f0 * det, r.uniform(0.0, TWO_PI))
        v = saw_add(ph, 26)
        v = formant_filter(v, ((700.0, 1.0), (1220.0, 0.75),
                               (2600.0, 0.55), (3450.0, 0.35)),
                           bw=0.28, pad=SR // 4)
        v = np.tanh(3.0 * norm(v))
        v = spectral_filter(v, g_lowpass(6800, 2), pad=SR // 4)
        k = int(delay * SR)
        if k:
            v = np.concatenate([np.zeros(k), v[:-k]])
        sig += amp * v

    breath = spectral_filter(white(n, r), g_bandpass(500, 5200, 2), pad=SR // 4)
    breath = formant_filter(breath, ((800.0, 1.0), (1700.0, 0.6), (3100.0, 0.4)),
                            bw=0.4, pad=SR // 4)
    rasp = 0.72 + 0.28 * np.abs(np.sin(TWO_PI * 24.0 * t))
    sig = sig * rasp + 0.22 * norm(breath) * rasp

    sig *= swell(n, 0.012, 0.26)
    sig = spectral_filter(sig, g_highpass(90, 2), pad=SR // 4)
    return fade_edges(norm(sig), 6.0)


def _heartbeat(r: np.random.Generator, vel: float) -> np.ndarray:
    m = n_samples(0.22)
    tt = tline(m)
    f = 34.0 + 46.0 * np.exp(-tt / 0.035)
    s = np.sin(phase_curve(f)) * np.exp(-tt / 0.075)
    s += 0.35 * spectral_filter(white(m, r), g_lowpass(220, 2), pad=SR // 8) \
        * np.exp(-tt / 0.025)
    return fade_edges(vel * norm(s), 2.0)


def sfx_death() -> np.ndarray:
    dur = 1.40
    n = n_samples(dur)
    r = rng(9106)
    t = tline(n)

    # descending doom drone
    f = 145.0 * np.exp(-t / 0.75) + 30.0
    drone = 0.6 * saw_add(phase_curve(f), 22)
    drone += 0.8 * np.sin(phase_curve(f * 0.5))
    drone = spectral_filter(drone, g_lowpass(1500, 2), pad=SR // 2)
    drone *= swell(n, 0.02, 0.45) * np.exp(-t / 0.9)

    # heartbeat slowing, then stopping
    beats = np.zeros(n)
    for t0, vel in ((0.06, 0.95), (0.40, 0.80), (0.78, 0.60), (1.06, 0.30)):
        raw = _heartbeat(r, vel)
        start = int(t0 * SR)
        m = min(len(raw), n - start)
        if m > 0:
            beats[start:start + m] += raw[:m]

    sig = np.tanh(1.3 * (0.85 * drone + 0.9 * beats))
    return fade_edges(norm(sig), 8.0)


def sfx_checkpoint() -> np.ndarray:
    dur = 1.20
    n = n_samples(dur)
    r = rng(9107)
    t = tline(n)

    flare_n = n_samples(0.42)
    flare = stft_band(white(flare_n, r),
                      lambda i: 600.0 + 3800.0 * (i / flare_n) ** 0.7,
                      bw_oct=1.2, frame=256, hop=64)
    flare = norm(flare) * swell(flare_n, 0.05, 0.18) * 0.30
    sig = fit(flare, n)

    b = bell(523.25, 0.95, 0.38, 91,
             partials=((1.0, 1.0), (2.0, 0.5), (2.98, 0.35), (4.16, 0.2), (6.1, 0.1)))
    sig += 0.55 * fit(b, n)

    pad = np.zeros(n)
    for f, a in ((220.0, 0.10), (261.63, 0.08), (329.63, 0.07), (440.0, 0.035)):
        v = np.sin(TWO_PI * f * t + r.uniform(0.0, TWO_PI))
        v += 0.35 * np.sin(2 * TWO_PI * f * t + r.uniform(0.0, TWO_PI))
        pad += a * v
    pad = spectral_filter(pad, g_lowpass(2400, 2), pad=SR // 4)
    pad *= swell(n, 0.22, 0.45)
    sig += 0.55 * norm(pad)
    return fade_edges(norm(sig), 8.0)


def sfx_pickup() -> np.ndarray:
    dur = 0.45
    n = n_samples(dur)
    r = rng(9108)

    m = n_samples(0.20)
    paper = spectral_filter(white(m, r), g_highpass(2400, 2), pad=SR // 8)
    flutter = np.abs(np.sin(TWO_PI * 31.0 * tline(m))) ** 3
    paper = norm(paper) * flutter * swell(m, 0.01, 0.06)
    paper = formant_filter(paper, ((1800.0, 1.0), (3000.0, 0.6)), bw=0.5, pad=SR // 8)
    sig = 0.30 * fit(paper, n)

    sig += 0.22 * fit(whisper_utterance(r, 0.30), n)

    b = bell(1318.5, 0.40, 0.14, 92,
             partials=((1.0, 1.0), (2.0, 0.45), (2.9, 0.25), (4.1, 0.12)))
    sig += 0.50 * fit(b, n)
    return fade_edges(norm(sig), 6.0)


def sfx_whisper() -> np.ndarray:
    dur = 1.60
    n = n_samples(dur)
    r = rng(9109)
    sig = np.zeros(n)
    for seed, t0, amp in ((101, 0.02, 1.0), (102, 0.32, 0.8),
                          (103, 0.70, 0.9), (104, 1.06, 0.7)):
        utt = whisper_utterance(rng(seed), 0.62)
        sig += amp * fit(np.pad(utt, (int(t0 * SR), 0)), n)
    sig += 0.06 * spectral_filter(white(n, r), g_bandpass(400, 6000, 2), pad=SR // 4) \
        * swell(n, 0.2, 0.4)
    sig += reverb(sig * 0.4, make_ir(1.4, 0.5, 3500, 93), 0.35, circular=False)
    return fade_edges(norm(sig), 8.0)


def sfx_boss_roar() -> np.ndarray:
    dur = 1.60
    n = n_samples(dur)
    r = rng(9110)
    t = tline(n)

    f0 = 48.0 + 13.0 * np.sin(TWO_PI * 0.9 * t) + 8.0 * np.exp(-t / 0.55)
    mod = np.sin(phase_curve(f0 * 1.41))
    idx = 6.5 * np.exp(-t / 0.8) + 2.0
    growl = np.sin(phase_curve(f0) + idx * mod)
    sub = np.sin(phase_curve(f0 * 0.5))
    noise = formant_filter(white(n, r), ((380.0, 1.0), (900.0, 0.8), (1900.0, 0.5)),
                           bw=0.4, pad=SR // 4)
    noise = norm(noise) * (0.55 + 0.45 * np.abs(np.sin(TWO_PI * 33.0 * t)))
    sig = 0.65 * growl + 0.55 * sub + 0.50 * noise
    sig = np.tanh(2.2 * norm(sig))
    sig = spectral_filter(sig, g_lowpass(4200, 2), pad=SR // 4)
    sig *= swell(n, 0.09, 0.55) * (0.8 + 0.2 * np.exp(-t / 0.4))
    return fade_edges(norm(sig), 8.0)


def sfx_land() -> np.ndarray:
    n = n_samples(0.12)
    r = rng(9111)
    t = tline(n)
    thud = np.sin(phase_curve(42.0 + 60.0 * np.exp(-t / 0.012))) * np.exp(-t / 0.035)
    grit = spectral_filter(white(n, r), g_bandpass(700, 3200, 2), pad=SR // 8)
    grit = norm(grit) * np.exp(-t / 0.012)
    sig = 0.90 * thud + 0.80 * grit
    return fade_edges(norm(sig), 3.0)


def sfx_menu() -> np.ndarray:
    n = n_samples(0.35)
    r = rng(9112)
    t = tline(n)
    sig = np.zeros(n)
    f0 = 196.0
    for ratio, amp, tau in ((1.0, 1.0, 0.10), (2.0, 0.5, 0.075),
                            (2.98, 0.30, 0.05), (4.16, 0.15, 0.035)):
        sig += amp * np.sin(TWO_PI * f0 * ratio * t + r.uniform(0.0, TWO_PI)) \
            * np.exp(-t / tau)
    sig *= np.clip(t / 0.004, 0.0, 1.0)
    sig = spectral_filter(sig, g_lowpass(3200, 2), pad=SR // 8)
    return fade_edges(norm(sig), 5.0)


# ---------------------------------------------------------------------------
# output / verification
# ---------------------------------------------------------------------------
def finalize(x: np.ndarray, gain_db: float = PEAK_DBFS,
             taper: bool = False) -> np.ndarray:
    x = np.asarray(x, dtype=np.float64).copy()
    x -= float(np.mean(x))
    if taper:
        # Zero the ends and fold out the small DC the taper introduces; each
        # pass shrinks the residual by the tapered fraction of the file.
        for _ in range(3):
            x = fade_edges(x, 3.0)
            x -= float(np.mean(x))
        x = fade_edges(x, 3.0)
    p = float(np.max(np.abs(x)))
    assert p > 1e-9, "generated silence"
    x *= (10.0 ** (gain_db / 20.0)) / p
    return x


def write_wav(path: Path, samples: np.ndarray) -> None:
    x = np.asarray(samples, dtype=np.float64).ravel()
    assert x.size > 0, f"{path}: empty"
    assert np.all(np.isfinite(x)), f"{path}: non-finite samples"
    peak = float(np.max(np.abs(x)))
    assert peak <= 0.99, f"{path}: peak {peak:.4f} would clip"
    assert abs(float(np.mean(x))) < 1e-3, f"{path}: DC offset {np.mean(x):.5f}"
    data = np.clip(np.round(x * 32767.0), -32767, 32767).astype(np.int16)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(data.tobytes())


def verify_file(path: Path) -> dict:
    with wave.open(str(path), "rb") as w:
        ch, sw, fr, frames = (w.getnchannels(), w.getsampwidth(),
                              w.getframerate(), w.getnframes())
        raw = w.readframes(frames)
    assert ch == 1, f"{path}: channels={ch}"
    assert sw == 2, f"{path}: sampwidth={sw}"
    assert fr == SR, f"{path}: rate={fr}"
    data = np.frombuffer(raw, dtype="<i2").astype(np.float64) / 32768.0
    peak = float(np.max(np.abs(data)))
    rms = float(np.sqrt(np.mean(data * data)))
    return {
        "frames": frames,
        "seconds": frames / SR,
        "peak": peak,
        "peak_db": 20.0 * math.log10(max(peak, 1e-12)),
        "rms": rms,
        "rms_db": 20.0 * math.log10(max(rms, 1e-12)),
        "dc": float(np.mean(data)),
        "seam": float(abs(data[0] - data[-1])),
        "maxstep": float(np.max(np.abs(np.diff(data)))),
        "step": float(np.sqrt(np.mean(np.diff(data) ** 2))),
    }


def main() -> None:
    t_start = time.time()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    jobs = [
        ("amb_1.wav", 24.0, amb_1_drowned_coast),
        ("amb_2.wav", 24.0, amb_2_flooded_catacombs),
        ("amb_3.wav", 24.0, amb_3_forbidden_library),
        ("amb_4.wav", 24.0, amb_4_frozen_plateau),
        ("amb_5.wav", 24.0, amb_5_fungal_machine_city),
        ("amb_6.wav", 24.0, amb_6_dream_of_rlyeh),
        ("amb_7.wav", 24.0, amb_7_throne_of_cthulhu),
        ("mus_boss.wav", 32.0, mus_boss),
        ("sfx_swing.wav", 0.22, sfx_swing),
        ("sfx_hit.wav", 0.16, sfx_hit),
        ("sfx_hurt.wav", 0.34, sfx_hurt),
        ("sfx_dash.wav", 0.26, sfx_dash),
        ("sfx_voice.wav", 0.90, sfx_voice),
        ("sfx_death.wav", 1.40, sfx_death),
        ("sfx_checkpoint.wav", 1.20, sfx_checkpoint),
        ("sfx_pickup.wav", 0.45, sfx_pickup),
        ("sfx_whisper.wav", 1.60, sfx_whisper),
        ("sfx_boss_roar.wav", 1.60, sfx_boss_roar),
        ("sfx_land.wav", 0.12, sfx_land),
        ("sfx_menu.wav", 0.35, sfx_menu),
    ]

    rows = []
    total_bytes = 0
    for name, spec_seconds, fn in jobs:
        path = OUT_DIR / name
        sig = finalize(fn(), taper=(spec_seconds < 20.0))
        expected = n_samples(spec_seconds)
        assert len(sig) == expected, f"{name}: length {len(sig)} != {expected} samples"
        write_wav(path, sig)
        info = verify_file(path)
        assert abs(info["seconds"] - spec_seconds) <= 1.0 / SR, \
            f"{name}: {info['seconds']:.6f}s != {spec_seconds}s"
        assert info["peak"] <= 0.99
        assert abs(info["dc"]) < 1e-3
        assert info["rms_db"] > -40.0, f"{name}: suspiciously quiet"
        if spec_seconds >= 20.0:
            # a seamless loop must not jump further than the waveform's own
            # steepest legitimate sample-to-sample move
            assert info["seam"] <= info["maxstep"], \
                f"{name}: loop seam {info['seam']:.4f} > max step {info['maxstep']:.4f}"
        size = path.stat().st_size
        total_bytes += size
        rows.append((name, info, size))

    print()
    print(f"{'path':30s} {'sec':>6s} {'peak dBFS':>10s} {'rms dBFS':>9s} "
          f"{'frames':>8s} {'KiB':>8s} {'seam/max':>9s}")
    print("-" * 88)
    for name, info, size in rows:
        ratio = info["seam"] / info["maxstep"] if info["maxstep"] > 0 else 0.0
        rel = str(Path("assets") / "audio" / name)
        print(f"{rel:30s} {info['seconds']:6.2f} {info['peak_db']:10.2f} "
              f"{info['rms_db']:9.2f} {info['frames']:8d} {size / 1024.0:8.1f} "
              f"{ratio:9.2f}")

    total_mb = total_bytes / (1024.0 * 1024.0)
    elapsed = time.time() - t_start
    print("-" * 78)
    print(f"{len(rows)} files, {total_mb:.2f} MiB total, "
          f"all mono 22050 Hz 16-bit, peak {PEAK_DBFS:.1f} dBFS")
    print(f"generated in {elapsed:.1f}s")

    assert total_bytes < 25 * 1024 * 1024, "output exceeds 25 MiB"
    if elapsed > 60.0:
        print(f"WARNING: generation took {elapsed:.1f}s (> 60s budget)")
    print("\nregenerate with: python3 tools/gen_audio.py")


if __name__ == "__main__":
    main()
