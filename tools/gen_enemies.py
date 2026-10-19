"""Criaturas y jefes. Silueta oscura + borde + ojos emisivos."""
from __future__ import annotations

import math
import os
import random
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(__file__))
from pixelart import edge_light, glow, new, poly, px  # noqa: E402


# ------------------------------------------------------------------ helpers
def blob(d, cx, cy, rx, ry, color, wobble=0.0, seed=0, n=14):
    rnd = random.Random(seed)
    pts = []
    for i in range(n):
        t = i / n * math.tau
        r = 1.0 + (math.sin(t * 3 + seed) * wobble) + rnd.uniform(-wobble, wobble) * 0.4
        pts.append((cx + math.cos(t) * rx * r, cy + math.sin(t) * ry * r))
    poly(d, pts, color)


def limb(d, pts, widths, color):
    """Tubo de anchura variable a lo largo de una polilínea."""
    for i in range(len(pts) - 1):
        d.line([pts[i], pts[i + 1]], fill=color, width=max(1, int(round(widths[i]))))


def eye(img, x, y, color, r=1):
    for dx in range(-r, r + 1):
        for dy in range(-r, r + 1):
            if dx * dx + dy * dy <= r * r + 0.5:
                px(img, x + dx, y + dy, color + (255,))


def finish(img, rim=(120, 110, 80), strength=120, cold=None, rim_dx=1):
    img = edge_light(img, rim, rim_dx, 0, strength)
    if cold:
        img = edge_light(img, cold, -rim_dx, -1, 60)
    return img


def save_pair(name, frames, outdir):
    for i, im in enumerate(frames):
        im.save(os.path.join(outdir, f"{name}_{i}.png"))


# ------------------------------------------------------------------ enemigos
def ahogado(frame=0):
    """Pescador de Innsmouth: encorvado, lanza, branquias."""
    W, H = 30, 34
    img = new(W, H)
    d = ImageDraw.Draw(img)
    bob = 0 if frame == 0 else 1
    body_c = (22, 30, 28, 255)
    cx, cy = 16, 20 + bob
    # piernas cortas
    d.line([(13, 28 + bob), (11, 33)], fill=body_c, width=3)
    d.line([(18, 28 + bob), (20, 33)], fill=body_c, width=3)
    # torso encorvado
    blob(d, cx, cy, 8.5, 9.5, body_c, wobble=0.10, seed=3)
    # joroba
    blob(d, cx + 3, cy - 6, 6, 5, body_c, wobble=0.14, seed=7)
    # cabeza de pez adelantada
    hx, hy = cx - 4, cy - 10
    blob(d, hx, hy, 6.0, 5.2, body_c, wobble=0.12, seed=11)
    poly(d, [(hx - 5, hy + 1), (hx - 9, hy + 3), (hx - 5, hy + 4)], body_c)   # hocico
    # cresta dorsal
    for i in range(4):
        x = hx + 2 + i * 2
        poly(d, [(x, hy - 4), (x + 1, hy - 9 + i), (x + 2, hy - 4)], body_c)
    # aleta branquial
    poly(d, [(cx + 8, cy - 5), (cx + 13, cy - 1), (cx + 8, cy + 3)], body_c)
    # brazo con lanza
    d.line([(cx - 2, cy - 5), (cx - 5, cy + 1)], fill=body_c, width=2)
    # lanza
    d.line([(cx - 12, cy + 9), (cx + 4, cy - 13)], fill=(52, 44, 34, 255), width=1)
    poly(d, [(cx + 4, cy - 13), (cx + 7, cy - 15), (cx + 4, cy - 11)], (150, 148, 132, 255))
    # detalles
    eye(img, hx - 2, hy, (222, 242, 150), 1)
    px(img, hx - 3, hy - 1, (255, 255, 210, 255))
    for i in range(3):
        px(img, hx + 1 + i, hy + 2, (58, 78, 70, 255))
    img = finish(img, rim=(110, 160, 120), strength=150, cold=(60, 110, 120))
    return img


def cultista(frame=0):
    W, H = 24, 36
    img = new(W, H)
    d = ImageDraw.Draw(img)
    bob = 0 if frame == 0 else 1
    c = (26, 22, 30, 255)
    # túnica
    poly(d, [(9, 12 + bob), (15, 12 + bob), (18, 33), (6, 33)], c)
    # capucha
    poly(d, [(8, 13 + bob), (16, 13 + bob), (14, 4 + bob), (10, 4 + bob)], c)
    # daga curva
    d.line([(16, 18 + bob), (21, 14 + bob), (23, 9 + bob)], fill=(120, 124, 132, 255), width=1)
    d.line([(17, 19 + bob), (15, 22 + bob)], fill=(40, 34, 28, 255), width=1)
    # brazos
    d.line([(8, 15 + bob), (5, 21 + bob)], fill=c, width=2)
    # ojos
    px(img, 10, 9 + bob, (230, 190, 90, 255))
    px(img, 14, 9 + bob, (230, 190, 90, 255))
    # cinturón dorado
    d.line([(8, 22 + bob), (16, 22 + bob)], fill=(110, 84, 40, 255))
    img = finish(img, rim=(150, 120, 70), strength=110, cold=(70, 90, 110))
    return img


def polipo(frame=0):
    """Horror flotante: poliedro imposible con tentáculos y un ojo."""
    W, H = 34, 34
    img = new(W, H)
    d = ImageDraw.Draw(img)
    c = (22, 18, 32, 255)
    cx, cy = 17, 12
    wob = frame * 1.2
    # masa imposible: dos volúmenes que no encajan
    poly(d, [(cx - 10, cy - 4), (cx - 3, cy - 11), (cx + 7, cy - 8), (cx + 11, cy + 1),
             (cx + 4, cy + 7), (cx - 7, cy + 6)], c)
    poly(d, [(cx - 3, cy - 11), (cx + 7, cy - 8), (cx + 5, cy - 2), (cx - 4, cy - 3)], (40, 34, 56, 255))
    poly(d, [(cx + 4, cy + 7), (cx + 11, cy + 1), (cx + 9, cy + 8)], (14, 12, 20, 255))
    # tentáculos gruesos colgantes
    for i in range(4):
        x0 = cx - 8 + i * 5
        pts = []
        for k in range(6):
            t = k / 5.0
            pts.append((x0 + math.sin(t * 3 + i + wob) * 3.0, cy + 5 + t * 15))
        limb(d, pts, [3, 3, 2, 2, 1, 1], c)
    eye(img, cx + 1, cy - 2, (206, 128, 230), 2)
    px(img, cx, cy - 3, (245, 215, 255, 255))
    img = finish(img, rim=(140, 100, 180), strength=160)
    return img


def bestia_lunar(frame=0):
    """Cuadrúpedo pálido, sin ojos, cuello largo."""
    W, H = 40, 30
    img = new(W, H)
    d = ImageDraw.Draw(img)
    c = (76, 78, 84, 255)
    dark = (40, 42, 50, 255)
    sway = frame * 1.5
    # patas
    for i, x in enumerate((9, 15, 26, 32)):
        d.line([(x, 20), (x + (2 if i % 2 else -2), 29)], fill=dark, width=2)
    # cuerpo
    blob(d, 21, 16, 11, 6.5, c, wobble=0.10, seed=5)
    # cuello y cabeza
    neck = [(30, 13), (34, 8), (35 + math.sin(sway) * 1.2, 3)]
    limb(d, neck, [5, 4, 3], c)
    blob(d, 35 + math.sin(sway) * 1.2, 2, 4.5, 3.0, c, wobble=0.12, seed=9)
    # boca vertical
    d.line([(35, 3), (36, 6)], fill=(20, 18, 22, 255))
    # costillas
    for i in range(4):
        d.line([(14 + i * 4, 12), (13 + i * 4, 20)], fill=(54, 56, 64, 255))
    img = finish(img, rim=(170, 180, 196), strength=150, cold=(120, 160, 180))
    return img


def migo(frame=0):
    """Cangrejo fúngico alado que flota."""
    W, H = 32, 30
    img = new(W, H)
    d = ImageDraw.Draw(img)
    c = (44, 26, 50, 255)
    cx, cy = 16, 15
    flap = 3 if frame == 0 else -2
    # alas
    poly(d, [(cx - 2, cy - 5), (cx - 16, cy - 12 + flap), (cx - 8, cy + 1)], (58, 34, 62, 180))
    poly(d, [(cx + 2, cy - 5), (cx + 16, cy - 12 - flap), (cx + 8, cy + 1)], (58, 34, 62, 180))
    # cuerpo
    blob(d, cx, cy, 6, 7, c, wobble=0.14, seed=4)
    # cabeza fúngica
    blob(d, cx, cy - 8, 5.5, 4.5, c, wobble=0.16, seed=6)
    for i in range(5):
        px(img, cx - 4 + i * 2, cy - 11, (150, 90, 120, 220))
    # pinzas
    for s in (-1, 1):
        d.line([(cx + s * 6, cy - 2), (cx + s * 10, cy + 4)], fill=c, width=2)
        d.line([(cx + s * 10, cy + 4), (cx + s * 9, cy + 8)], fill=c, width=2)
        d.line([(cx + s * 10, cy + 4), (cx + s * 12, cy + 6)], fill=c, width=1)
    eye(img, cx - 2, cy - 8, (200, 240, 190))
    eye(img, cx + 2, cy - 8, (200, 240, 190))
    img = finish(img, rim=(150, 90, 130), strength=120)
    return img


def espectro():
    """Alucinación: silueta del propio Testigo, ojos blancos."""
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "sprites", "testigo_idle_0.png")
    base = Image.open(p).convert("RGBA")
    a = base.split()[3]
    black = Image.new("RGBA", base.size, (4, 4, 8, 0))
    black.putalpha(a)
    d = ImageDraw.Draw(black)
    # ojos blancos, vacíos
    px(black, 23, 12, (236, 240, 255, 255))
    px(black, 26, 12, (236, 240, 255, 255))
    px(black, 23, 13, (180, 190, 220, 255))
    px(black, 26, 13, (180, 190, 220, 255))
    black = edge_light(black, (170, 190, 210), -1, 0, 150)
    return black


# ------------------------------------------------------------------ jefes
def sacerdote(frame=0):
    """Jefe 1: El Sacerdote Ahogado. Mitra, panza, cara de tentáculos."""
    W, H = 60, 74
    img = new(W, H)
    d = ImageDraw.Draw(img)
    c = (24, 32, 34, 255)
    sway = frame * 1.1
    cx = 30
    # túnica ancha
    poly(d, [(cx - 12, 24), (cx + 12, 24), (cx + 22, 73), (cx - 22, 73)], c)
    # panza
    blob(d, cx + 2, 48, 13, 16, c, wobble=0.08, seed=2)
    # estola
    poly(d, [(cx - 6, 24), (cx - 1, 24), (cx - 3, 60), (cx - 8, 60)], (46, 58, 44, 255))
    poly(d, [(cx + 2, 24), (cx + 7, 24), (cx + 9, 60), (cx + 4, 60)], (46, 58, 44, 255))
    # mitra
    poly(d, [(cx - 9, 24), (cx + 9, 24), (cx + 6, 6), (cx, 1), (cx - 6, 6)], c)
    poly(d, [(cx - 6, 23), (cx + 6, 23), (cx + 4, 12), (cx, 9), (cx - 4, 12)], (10, 12, 14, 255))
    # tentáculos de la cara
    for i in range(5):
        x0 = cx - 6 + i * 3
        pts = [(x0, 24), (x0 + math.sin(i + sway) * 2, 30), (x0 + math.sin(i * 2 + sway) * 3, 37)]
        limb(d, pts, [2, 2, 1], (34, 46, 44, 255))
    # ojos
    eye(img, cx - 4, 16, (220, 238, 130))
    eye(img, cx + 4, 16, (220, 238, 130))
    # incensario colgando
    d.line([(cx + 20, 34), (cx + 25, 50), (cx + 27, 58)], fill=(70, 64, 50, 255), width=1)
    blob(d, cx + 27, 61, 4, 4, (40, 36, 32, 255), wobble=0.2, seed=8)
    px(img, cx + 27, 60, (255, 140, 60, 255))
    img = finish(img, rim=(110, 150, 120), strength=120, cold=(70, 110, 120))
    return img


def madre(frame=0):
    """Jefe 2: La Madre de Branquias. Masa agachada, fauces, huevos."""
    W, H = 78, 60
    img = new(W, H)
    d = ImageDraw.Draw(img)
    c = (26, 34, 30, 255)
    cx, cy = 39, 40
    blob(d, cx, cy, 32, 19, c, wobble=0.06, seed=3)
    # boca vertical
    poly(d, [(cx - 9, 16), (cx + 9, 16), (cx + 4, 46), (cx - 4, 46)], (6, 6, 8, 255))
    for i in range(6):
        y = 20 + i * 4
        d.line([(cx - 7, y), (cx - 2, y + 3)], fill=(178, 166, 128, 255))
        d.line([(cx + 7, y), (cx + 2, y + 3)], fill=(178, 166, 128, 255))
    # brazos múltiples
    for i in range(4):
        s = -1 if i % 2 == 0 else 1
        x0 = cx + s * (14 + i * 3)
        y0 = cy - 6 + i * 4
        pts = [(x0, y0), (x0 + s * 9, y0 + 4), (x0 + s * 7, y0 + 12)]
        limb(d, pts, [3, 2, 1], c)
    # sacos de huevos
    for i in range(5):
        ex = cx - 20 + i * 10
        ey = cy + 12 + (i % 2) * 3
        blob(d, ex, ey, 4.0, 4.5, (62, 74, 44, 255), wobble=0.2, seed=i)
        px(img, ex, ey - 1, (170, 205, 110, 255))
        px(img, ex + 1, ey + 1, (120, 150, 80, 255))
    eye(img, cx - 10, 24, (220, 240, 120))
    eye(img, cx + 10, 24, (220, 240, 120))
    img = finish(img, rim=(130, 180, 120), strength=150, cold=(70, 120, 110))
    return img


def bibliotecario(frame=0):
    """Jefe 3: El Bibliotecario. Alto, delgado, con un tomo abierto."""
    W, H = 52, 78
    img = new(W, H)
    d = ImageDraw.Draw(img)
    c = (34, 28, 24, 255)
    cx = 26
    # abrigo largo
    poly(d, [(cx - 9, 22), (cx + 9, 22), (cx + 15, 77), (cx - 15, 77)], c)
    # hombros y cuello largo
    d.line([(cx, 22), (cx, 12)], fill=c, width=4)
    blob(d, cx, 9, 6, 7, c, wobble=0.10, seed=2)
    # sin ojos: costura
    d.line([(cx - 4, 9), (cx + 4, 9)], fill=(14, 12, 12, 255))
    # pelos/tentáculos
    for i in range(4):
        d.line([(cx - 5 + i * 3, 3), (cx - 7 + i * 4, -1)], fill=c, width=1)
    # tomo flotante
    poly(d, [(cx - 17, 30), (cx, 36), (cx + 17, 30), (cx + 17, 44), (cx, 50), (cx - 17, 44)], (74, 56, 38, 255))
    poly(d, [(cx - 14, 33), (cx, 38), (cx + 14, 33), (cx + 14, 42), (cx, 47), (cx - 14, 42)], (214, 196, 152, 255))
    for i in range(5):
        d.line([(cx - 11, 36 + i), (cx - 3, 39 + i)], fill=(120, 104, 78, 255))
        d.line([(cx + 3, 39 + i), (cx + 11, 36 + i)], fill=(120, 104, 78, 255))
    # libros flotantes
    for bx, by in ((cx - 20, 24), (cx + 19, 27)):
        d.rectangle([bx - 3, by, bx + 3, by + 4], fill=(150, 130, 92, 255))
        d.line([(bx - 3, by + 2), (bx + 3, by + 2)], fill=(90, 76, 54, 255))
    # brazos
    d.line([(cx - 9, 26), (cx - 15, 36)], fill=c, width=3)
    d.line([(cx + 9, 26), (cx + 15, 36)], fill=c, width=3)
    # luz del libro
    img = glow(img, cx, 40, 16, (240, 200, 120), 90)
    img = finish(img, rim=(170, 140, 90), strength=110)
    return img


def cazador(frame=0):
    """Jefe 4: El Cazador de la Luna. Arácnido con guadaña."""
    W, H = 68, 58
    img = new(W, H)
    d = ImageDraw.Draw(img)
    c = (52, 58, 74, 255)
    cx, cy = 34, 30
    # patas
    for i in range(4):
        s = -1 if i % 2 == 0 else 1
        x0 = cx + s * (6 + i * 3)
        pts = [(x0, cy + 6), (x0 + s * 10, cy + 14), (x0 + s * 6, 57)]
        limb(d, pts, [3, 2, 2], c)
    blob(d, cx, cy, 13, 9, c, wobble=0.10, seed=4)
    # cabeza enmascarada
    blob(d, cx - 6, cy - 11, 7, 6, c, wobble=0.12, seed=6)
    poly(d, [(cx - 13, cy - 12), (cx - 17, cy - 8), (cx - 12, cy - 6)], (196, 200, 210, 255))
    eye(img, cx - 9, cy - 12, (230, 240, 255))
    # guadaña
    d.line([(cx + 10, cy + 4), (cx + 22, cy - 14)], fill=(70, 72, 80, 255), width=2)
    d.arc([cx + 8, cy - 30, cx + 32, cy - 8], 200, 340, fill=(206, 214, 226, 255))
    d.arc([cx + 9, cy - 29, cx + 31, cy - 9], 200, 340, fill=(240, 244, 255, 255))
    img = finish(img, rim=(150, 180, 210), strength=140, cold=(110, 150, 190))
    return img


def ingeniero(frame=0):
    """Jefe 5: El Ingeniero Mi-Go. Cerebro en tarro con brazos mecánicos."""
    W, H = 68, 56
    img = new(W, H)
    d = ImageDraw.Draw(img)
    cx, cy = 34, 26
    # brazos mecánicos
    for s in (-1, 1):
        pts = [(cx + s * 10, cy), (cx + s * 22, cy - 8), (cx + s * 26, cy + 8), (cx + s * 20, cy + 18)]
        limb(d, pts, [4, 3, 2, 2], (58, 54, 60, 255))
        d.line([(cx + s * 20, cy + 18), (cx + s * 16, cy + 24)], fill=(88, 80, 70, 255), width=2)
    # tarro
    d.rectangle([cx - 12, cy - 12, cx + 12, cy + 12], fill=(30, 40, 44, 255), outline=(70, 90, 96, 255))
    d.rectangle([cx - 10, cy - 10, cx + 10, cy + 10], fill=(20, 60, 60, 255))
    # cerebro
    blob(d, cx, cy, 8, 7, (150, 100, 110, 255), wobble=0.2, seed=3)
    for i in range(6):
        d.line([(cx - 6 + i * 2, cy - 5), (cx - 5 + i * 2, cy + 5)], fill=(180, 130, 140, 255))
    # alas
    poly(d, [(cx - 12, cy - 12), (cx - 26, cy - 22), (cx - 14, cy - 2)], (44, 30, 56, 210))
    poly(d, [(cx + 12, cy - 12), (cx + 26, cy - 22), (cx + 14, cy - 2)], (44, 30, 56, 210))
    # tubos
    for i in range(3):
        d.line([(cx - 8 + i * 6, cy + 12), (cx - 10 + i * 6, cy + 22)], fill=(90, 70, 60, 255))
    img = glow(img, cx, cy, 12, (120, 240, 200), 60)
    img = finish(img, rim=(150, 110, 150), strength=120)
    return img


def espejo(frame=0):
    """Jefe 6: El Yo Que No Fui."""
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "sprites", "testigo_idle_0.png")
    base = Image.open(p).convert("RGBA")
    a = base.split()[3]
    img = Image.new("RGBA", base.size, (6, 2, 10, 0))
    img.putalpha(a)
    d = ImageDraw.Draw(img)
    px(img, 23, 12, (255, 255, 255, 255))
    px(img, 26, 12, (255, 255, 255, 255))
    px(img, 23, 13, (200, 210, 255, 255))
    px(img, 26, 13, (200, 210, 255, 255))
    # corona de llamas negras
    for i in range(5):
        x = 21 + i * 2
        d.line([(x, 3), (x - 1, -3 + (i % 2))], fill=(60, 20, 70, 255), width=1)
    img = edge_light(img, (180, 120, 255), -1, 0, 170)
    img = glow(img, 24, 12, 10, (150, 90, 220), 50)
    return img


def cthulhu(frame=0):
    """Jefe final: masa alada con cara de tentáculos."""
    W, H = 132, 156
    img = new(W, H)
    d = ImageDraw.Draw(img)
    c = (16, 40, 36, 255)
    dark = (8, 20, 20, 255)
    cx, cy = 66, 62
    sway = frame * 0.8
    # alas desplegadas
    for s in (-1, 1):
        pts = [(cx + s * 10, cy - 30), (cx + s * 62, cy - 66), (cx + s * 66, cy - 20),
               (cx + s * 52, cy + 2), (cx + s * 40, cy - 6)]
        poly(d, pts, (12, 30, 30, 255))
        for i in range(5):
            d.line([(cx + s * 12, cy - 28), (cx + s * (58 - i * 4), cy - (58 - i * 9))],
                   fill=(24, 56, 50, 255))
    # cuerpo/torso
    blob(d, cx, cy + 34, 30, 40, c, wobble=0.06, seed=2)
    # hombros
    blob(d, cx, cy - 2, 26, 16, c, wobble=0.08, seed=5)
    # cabeza
    blob(d, cx, cy - 22, 19, 18, c, wobble=0.08, seed=7)
    # tentáculos de la boca
    for i in range(9):
        x0 = cx - 18 + i * 4.5
        pts = []
        for k in range(7):
            t = k / 6.0
            pts.append((x0 + math.sin(t * 4 + i + sway) * (2 + t * 4),
                        cy - 8 + t * (30 + (i % 3) * 5)))
        limb(d, pts, [3, 3, 2, 2, 2, 1, 1], (22, 52, 46, 255))
    # ojos enormes
    for ex in (cx - 9, cx + 9):
        eye(img, ex, cy - 28, (150, 255, 170), 2)
        px(img, ex, cy - 29, (230, 255, 230, 255))
    # garras
    for s in (-1, 1):
        limb(d, [(cx + s * 24, cy + 16), (cx + s * 40, cy + 34), (cx + s * 34, cy + 46)],
             [5, 3, 2], c)
    img = finish(img, rim=(80, 180, 120), strength=130, cold=(60, 140, 140))
    img = glow(img, cx, cy - 28, 26, (90, 220, 140), 50)
    return img


def main(outdir):
    os.makedirs(outdir, exist_ok=True)
    save_pair("en_ahogado", [ahogado(0), ahogado(1)], outdir)
    save_pair("en_cultista", [cultista(0), cultista(1)], outdir)
    save_pair("en_polipo", [polipo(0), polipo(1)], outdir)
    save_pair("en_bestia", [bestia_lunar(0), bestia_lunar(1)], outdir)
    save_pair("en_migo", [migo(0), migo(1)], outdir)
    espectro().save(os.path.join(outdir, "en_espectro.png"))
    save_pair("boss_sacerdote", [sacerdote(0), sacerdote(1)], outdir)
    save_pair("boss_madre", [madre(0), madre(1)], outdir)
    save_pair("boss_bibliotecario", [bibliotecario(0), bibliotecario(1)], outdir)
    save_pair("boss_cazador", [cazador(0), cazador(1)], outdir)
    save_pair("boss_ingeniero", [ingeniero(0), ingeniero(1)], outdir)
    espejo().save(os.path.join(outdir, "boss_espejo.png"))
    save_pair("boss_cthulhu", [cthulhu(0), cthulhu(1)], outdir)
    print("criaturas listas")


if __name__ == "__main__":
    main(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "sprites"))
