"""Construye la banda sonora del video promocional.

Lee los tiempos de corte que imprime el arnés (promo N/9 : clase @12.34s) y
mezcla los ambientes y la música del juego para que cada sección tenga su
propio color: descenso -> duelos -> tarjeta final.
"""
from __future__ import annotations

import re
import sys
import wave

import numpy as np

SR = 44100
AUDIO = "assets/audio/"


def load(name: str) -> np.ndarray:
    with wave.open(AUDIO + name, "rb") as w:
        assert w.getframerate() == 22050, name
        data = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)
        x = data.astype(np.float32) / 32768.0
    # remuestreo lineal a 44.1 kHz
    n = int(len(x) * SR / 22050)
    return np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)


def loop_to(x: np.ndarray, n: int) -> np.ndarray:
    if len(x) >= n:
        return x[:n].copy()
    reps = int(np.ceil(n / len(x)))
    return np.tile(x, reps)[:n].copy()


def env(n: int, attack: float = 0.6, release: float = 1.2, sr: int = SR) -> np.ndarray:
    e = np.ones(n, dtype=np.float32)
    a = min(n, int(attack * sr))
    r = min(n, int(release * sr))
    if a:
        e[:a] = np.linspace(0.0, 1.0, a) ** 1.5
    if r:
        e[-r:] *= np.linspace(1.0, 0.0, r) ** 1.2
    return e


def place(track: np.ndarray, src: np.ndarray, at: float, gain: float = 1.0,
          fade_in: float = 0.3, fade_out: float = 1.0) -> None:
    start = int(at * SR)
    if start >= len(track):
        return
    seg = src[: len(track) - start].copy()
    if len(seg) == 0:
        return
    seg *= env(len(seg), fade_in, fade_out) * gain
    track[start:start + len(seg)] += seg


def parse(path: str) -> list[tuple[int, str, float]]:
    out = []
    rx = re.compile(r"promo (\d+)/9 : (\w+) @([\d.]+)s")
    try:
        text = open(path, encoding="utf-8", errors="replace").read()
    except FileNotFoundError:
        return out
    for m in rx.finditer(text):
        out.append((int(m.group(1)), m.group(2), float(m.group(3))))
    return out


def main() -> None:
    log_path = sys.argv[1] if len(sys.argv) > 1 else "/tmp/promo/beat_times.log"
    out_path = sys.argv[2] if len(sys.argv) > 2 else "/tmp/promo/soundtrack.wav"

    beats = parse(log_path)
    # duración total: último corte + 6 s de tarjeta
    if beats:
        total = beats[-1][2] + 6.5
    else:
        total = 52.0
        beats = [(1, "title", 0.0), (2, "play", 4.0), (7, "boss", 27.5),
                 (8, "boss", 34.0), (9, "card", 41.5)]
    n = int(total * SR)
    track = np.zeros(n, dtype=np.float32)

    amb = {i: load("amb_%d.wav" % i) for i in (1, 2, 3, 5, 6)}
    boss = load("mus_boss.wav")

    # --- cama continua: un descenso que se va oscureciendo ---
    order = [b for b in beats if b[1] in ("play", "boss")]
    for idx, (num, kind, t) in enumerate(beats):
        nxt = beats[idx + 1][2] if idx + 1 < len(beats) else total
        dur = max(0.5, nxt - t)
        seg = np.zeros(int(dur * SR), dtype=np.float32)
        if kind == "title":
            src = loop_to(amb[6], len(seg))
            place(track, src, t, 0.55, 1.2, 1.4)
        elif kind == "play":
            which = [1, 2, 3, 5, 6][min(idx - 1, 4)] if idx >= 1 else 1
            src = loop_to(amb[which], len(seg))
            place(track, src, t, 0.42, 0.5, 0.9)
        elif kind == "boss":
            src = loop_to(boss, len(seg))
            place(track, src, t, 0.62, 0.8, 0.8)
        elif kind == "card":
            src = loop_to(amb[6], len(seg))
            place(track, src, t, 0.6, 1.0, 2.0)

    # --- golpes puntuales: dan ritmo al montaje ---
    if len(beats) >= 2:
        for num, kind, t in beats:
            if kind == "boss":
                place(track, load("sfx_boss_roar.wav"), t, 0.55, 0.05, 0.6)
            elif kind == "card":
                place(track, load("sfx_checkpoint.wav"), t, 0.45, 0.05, 1.5)
            elif num > 1:
                place(track, load("sfx_voice.wav"), t + 0.35, 0.30, 0.05, 0.5)
    # último latido antes del cierre
    place(track, load("sfx_death.wav"), max(0.0, total - 8.0), 0.35, 0.05, 1.0)

    # --- master: normalizar, limitar y desvanecer al final ---
    peak = float(np.max(np.abs(track))) or 1.0
    track = track / peak * 0.89
    track = np.tanh(track * 1.18) * 0.92          # limita sin recortar
    tail = int(2.2 * SR)
    track[-tail:] *= np.linspace(1.0, 0.0, tail) ** 1.3
    head = int(0.5 * SR)
    track[:head] *= np.linspace(0.0, 1.0, head) ** 1.2

    pcm = np.clip(track * 32767.0, -32768, 32767).astype(np.int16)
    with wave.open(out_path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())

    rms = float(np.sqrt(np.mean(track ** 2)))
    print("banda sonora: %.1fs  peak=%.2f  rms=%.3f  -> %s"
          % (len(track) / SR, float(np.max(np.abs(track))), rms, out_path))
    for num, kind, t in beats:
        print("  corte %d %-6s @ %6.2fs" % (num, kind, t))


if __name__ == "__main__":
    main()
