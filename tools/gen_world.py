"""Tiles, props y elementos de mundo. Un atlas de 16 tiles por material."""
from __future__ import annotations

import math
import os
import random
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(__file__))
from pixelart import (  # noqa: E402
    BAYER4, GOLD, GOLD_HI, INK, edge_light, glow, new, poly, px, rect,
)

T = 16
COLS, ROWS = 8, 2

# cada material: (base, base2, luz, sombra, acento, acento2)
MATERIALS = {
    "rock":  dict(base=(23, 27, 33), base2=(30, 35, 43), hi=(96, 112, 114), lo=(12, 14, 18), ac=(52, 96, 78), ac2=(116, 146, 88)),
    "brick": dict(base=(36, 28, 25), base2=(46, 36, 31), hi=(140, 108, 78), lo=(18, 14, 13), ac=(140, 106, 58), ac2=(192, 150, 76)),
    "flesh": dict(base=(38, 20, 30), base2=(48, 26, 38), hi=(150, 74, 84), lo=(20, 9, 16), ac=(104, 34, 50), ac2=(176, 70, 76)),
    "ice":   dict(base=(30, 40, 54), base2=(38, 50, 66), hi=(136, 164, 190), lo=(16, 22, 32), ac=(96, 124, 158), ac2=(206, 228, 244)),
    "fungus":dict(base=(30, 22, 40), base2=(40, 28, 52), hi=(128, 82, 148), lo=(15, 10, 22), ac=(118, 48, 132), ac2=(176, 108, 74)),
    "dream": dict(base=(18, 30, 28), base2=(24, 40, 36), hi=(96, 148, 122), lo=(8, 14, 14), ac=(116, 100, 48), ac2=(214, 184, 96)),
}


def base_tile(m, rnd):
    """Bloque sólido con textura de ruido y grietas."""
    img = new(T, T)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, T - 1, T - 1], fill=tuple(m["base"]) + (255,))
    # variación de valor con dither
    for y in range(T):
        for x in range(T):
            n = rnd.random()
            if n < 0.10:
                img.putpixel((x, y), tuple(m["base2"]) + (255,))
            elif n < 0.14:
                img.putpixel((x, y), tuple(m["lo"]) + (255,))
    # grietas
    for _ in range(2):
        cx, cy = rnd.randrange(2, 14), rnd.randrange(2, 14)
        for k in range(rnd.randrange(3, 7)):
            px(img, cx + k // 2, cy + k, m["lo"] + (255,))
    return img


def top_lip(img, m, moss=True):
    """Borde superior iluminado + musgo/algas."""
    d = ImageDraw.Draw(img)
    d.line([(0, 0), (T - 1, 0)], fill=tuple(min(255, c + 26) for c in m["hi"]) + (255,))
    d.line([(0, 1), (T - 1, 1)], fill=tuple(m["hi"]) + (150,))
    d.line([(0, 2), (T - 1, 2)], fill=tuple(m["hi"]) + (60,))
    if moss:
        rnd = random.Random(img.getpixel((0, 0))[0] * 7 + 3)
        for x in range(T):
            if rnd.random() < 0.42:
                px(img, x, 1, m["ac"] + (255,))
            if rnd.random() < 0.18:
                px(img, x, 2, m["ac2"] + (180,))
            if rnd.random() < 0.12:
                px(img, x, 3, m["ac"] + (120,))


def tile_solid(m, rnd, top=False, left=False, right=False, bottom=False):
    img = base_tile(m, rnd)
    d = ImageDraw.Draw(img)
    if top:
        top_lip(img, m)
    if left:
        d.line([(0, 0), (0, T - 1)], fill=tuple(m["lo"]) + (255,))
        d.line([(1, 0), (1, T - 1)], fill=tuple(m["base2"]) + (170,))
    if right:
        d.line([(T - 1, 0), (T - 1, T - 1)], fill=tuple(m["lo"]) + (255,))
        d.line([(T - 2, 0), (T - 2, T - 1)], fill=tuple(m["lo"]) + (120,))
    if bottom:
        d.line([(0, T - 1), (T - 1, T - 1)], fill=tuple(m["lo"]) + (255,))
    return img


def atlas(mat_name):
    m = MATERIALS[mat_name]
    rnd = random.Random(hash(mat_name) & 0xFFFF)
    sheet = new(T * COLS, T * ROWS)

    def put(idx, im):
        sheet.alpha_composite(im, ((idx % COLS) * T, (idx // COLS) * T))

    put(0, tile_solid(m, rnd))                                    # interior
    put(1, tile_solid(m, rnd, top=True))                          # superficie
    put(2, tile_solid(m, rnd, top=True, left=True))               # esquina sup izq
    put(3, tile_solid(m, rnd, top=True, right=True))              # esquina sup der
    put(4, tile_solid(m, rnd, left=True))                         # borde izq
    put(5, tile_solid(m, rnd, right=True))                        # borde der
    put(6, tile_solid(m, rnd, bottom=True))                       # borde inferior
    put(7, tile_solid(m, rnd, top=True, left=True, right=True, bottom=True))  # bloque suelto

    # 8: plataforma de un solo sentido (losa fina)
    p = new(T, T)
    d = ImageDraw.Draw(p)
    d.rectangle([0, 0, T - 1, 5], fill=tuple(m["base2"]) + (255,))
    d.line([(0, 0), (T - 1, 0)], fill=tuple(m["hi"]) + (255,))
    d.line([(0, 1), (T - 1, 1)], fill=tuple(m["hi"]) + (90,))
    d.line([(0, 5), (T - 1, 5)], fill=tuple(m["lo"]) + (255,))
    for _ in range(4):
        px(p, rnd.randrange(T), rnd.randrange(5), m["lo"] + (200,))
    put(8, p)

    # 9: pinchos (huesos afilados)
    s = new(T, T)
    d = ImageDraw.Draw(s)
    for i in range(3):
        bx = 2 + i * 5
        poly(d, [(bx, T - 1), (bx + 2, 3 + (i % 2) * 3), (bx + 4, T - 1)], (18, 18, 22, 255))
        poly(d, [(bx + 1, T - 1), (bx + 2, 4 + (i % 2) * 3), (bx + 3, T - 1)], (150, 146, 132, 255))
        d.line([(bx + 2, 5 + (i % 2) * 3), (bx + 2, T - 6)], fill=(200, 196, 180, 255))
    d.rectangle([0, T - 3, T - 1, T - 1], fill=(40, 30, 28, 255))
    put(9, s)

    # 10: superficie de agua
    w = new(T, T)
    d = ImageDraw.Draw(w)
    d.rectangle([0, 4, T - 1, T - 1], fill=(16, 44, 52, 210))
    for x in range(T):
        yy = 4 + int(round(math.sin(x * 0.9) * 0.8))
        px(w, x, yy, (120, 190, 190, 200))
        px(w, x, yy + 1, (52, 104, 112, 160))
    for _ in range(6):
        px(w, rnd.randrange(T), rnd.randrange(7, T), (70, 140, 140, 110))
    put(10, w)

    # 11: cuerpo de agua
    wb = new(T, T)
    d = ImageDraw.Draw(wb)
    d.rectangle([0, 0, T - 1, T - 1], fill=(13, 36, 44, 200))
    for _ in range(7):
        px(wb, rnd.randrange(T), rnd.randrange(T), (34, 78, 88, 120))
    put(11, wb)

    # 12: ladrillo detallado (muro decorativo)
    br = new(T, T)
    d = ImageDraw.Draw(br)
    d.rectangle([0, 0, T - 1, T - 1], fill=tuple(m["lo"]) + (255,))
    for row in range(4):
        off = 4 if row % 2 else 0
        for col in range(-1, 3):
            x0 = col * 8 + off
            d.rectangle([x0 + 1, row * 4 + 1, x0 + 7, row * 4 + 3], fill=tuple(m["base"]) + (255,))
            d.line([(x0 + 1, row * 4 + 1), (x0 + 7, row * 4 + 1)], fill=tuple(m["hi"]) + (70,))
    put(12, br)

    # 13: fuste de columna
    pil = new(T, T)
    d = ImageDraw.Draw(pil)
    d.rectangle([0, 0, T - 1, T - 1], fill=tuple(m["base2"]) + (255,))
    d.rectangle([3, 0, 12, T - 1], fill=tuple(m["base"]) + (255,))
    d.line([(3, 0), (3, T - 1)], fill=tuple(m["hi"]) + (150,))
    d.line([(4, 0), (4, T - 1)], fill=tuple(m["hi"]) + (60,))
    d.line([(12, 0), (12, T - 1)], fill=tuple(m["lo"]) + (220,))
    put(13, pil)

    # 14: capitel
    cap = new(T, T)
    d = ImageDraw.Draw(cap)
    d.rectangle([0, 8, T - 1, T - 1], fill=tuple(m["base2"]) + (255,))
    d.rectangle([1, 4, T - 2, 9], fill=tuple(m["base"]) + (255,))
    d.line([(1, 4), (T - 2, 4)], fill=tuple(m["hi"]) + (220,))
    d.line([(0, 10), (T - 1, 10)], fill=tuple(m["lo"]) + (255,))
    d.line([(2, 12), (T - 3, 12)], fill=tuple(m["hi"]) + (70,))
    put(14, cap)

    # 15: vacío decorativo (transparente)
    return sheet


def save_atlases(outdir):
    os.makedirs(outdir, exist_ok=True)
    for name in MATERIALS:
        atlas(name).save(os.path.join(outdir, f"tiles_{name}.png"))
    print("tiles:", ", ".join(MATERIALS))


# ------------------------------------------------------------------ props
def altar():
    img = new(36, 44)
    d = ImageDraw.Draw(img)
    # base escalonada
    d.rectangle([2, 38, 33, 43], fill=(30, 27, 28, 255))
    d.rectangle([4, 34, 31, 37], fill=(40, 36, 36, 255))
    d.rectangle([7, 12, 28, 34], fill=(34, 31, 32, 255))
    d.line([(7, 12), (7, 34)], fill=(92, 82, 64, 255))
    d.line([(28, 12), (28, 34)], fill=(12, 11, 12, 255))
    # mesa
    d.rectangle([3, 8, 32, 13], fill=(48, 42, 40, 255))
    d.line([(3, 8), (32, 8)], fill=(126, 108, 78, 255))
    # vela
    d.rectangle([16, 3, 19, 9], fill=(206, 196, 168, 255))
    px(img, 17, 1, (255, 214, 140, 255))
    px(img, 18, 2, (255, 170, 70, 255))
    # velas pequeñas
    for x, h in ((8, 4), (26, 5)):
        d.rectangle([x, 9 - h, x + 1, 9], fill=(190, 180, 152, 255))
        px(img, x, 8 - h, (255, 200, 120, 255))
    # símbolo del ojo abierto
    poly(d, [(12, 22), (17, 19), (23, 22), (17, 26)], (82, 70, 44, 255))
    px(img, 17, 22, (236, 196, 110, 255))
    px(img, 17, 23, (150, 110, 50, 255))
    img = edge_light(img, (120, 100, 62), 0, -1, 90)
    return img


def torch():
    img = new(12, 26)
    d = ImageDraw.Draw(img)
    d.rectangle([5, 12, 6, 25], fill=(38, 30, 26, 255))
    d.rectangle([3, 10, 8, 13], fill=(62, 48, 36, 255))
    d.rectangle([4, 6, 7, 10], fill=(20, 18, 18, 255))
    px(img, 5, 4, (255, 226, 160, 255))
    px(img, 6, 3, (255, 180, 80, 255))
    px(img, 5, 2, (255, 140, 50, 255))
    px(img, 6, 5, (255, 200, 110, 255))
    return img


def gate():
    img = new(40, 64)
    d = ImageDraw.Draw(img)
    # marco de piedra
    d.rectangle([0, 0, 39, 63], fill=(24, 22, 26, 255))
    d.rectangle([4, 6, 35, 63], fill=(6, 6, 10, 255))
    d.arc([4, 2, 35, 30], 180, 360, fill=(52, 46, 44, 255))
    for x in (4, 35):
        d.line([(x, 4), (x, 63)], fill=(74, 64, 54, 255))
    # runas
    for i in range(5):
        y = 14 + i * 8
        px(img, 2, y, (150, 120, 60, 200))
        px(img, 37, y, (150, 120, 60, 200))
    # velo
    for y in range(8, 63, 3):
        d.line([(6, y), (33, y)], fill=(16, 22, 26, 160))
    return img


def book():
    img = new(18, 18)
    d = ImageDraw.Draw(img)
    # tapas inclinadas, como un libro flotando
    poly(d, [(2, 5), (16, 3), (16, 14), (2, 16)], (62, 34, 38, 255))
    poly(d, [(3, 6), (9, 5), (9, 15), (3, 16)], (150, 138, 108, 255))
    poly(d, [(9, 5), (15, 4), (15, 14), (9, 15)], (128, 118, 92, 255))
    # renglones
    for i in range(4):
        d.line([(4, 8 + i * 2), (8, 7 + i * 2)], fill=(120, 104, 76, 255))
        d.line([(10, 7 + i * 2), (14, 6 + i * 2)], fill=(112, 96, 70, 255))
    # runa encendida
    px(img, 6, 9, (255, 214, 120, 255))
    px(img, 12, 7, (255, 200, 100, 230))
    d.line([(1, 5), (16, 3)], fill=(126, 90, 60, 255))
    return img


def statue():
    img = new(28, 52)
    d = ImageDraw.Draw(img)
    d.rectangle([2, 44, 25, 51], fill=(32, 30, 30, 255))
    d.rectangle([6, 40, 21, 45], fill=(40, 37, 36, 255))
    # cuerpo encapuchado
    poly(d, [(9, 40), (9, 16), (13, 8), (18, 12), (19, 40)], (30, 30, 36, 255))
    poly(d, [(12, 9), (18, 14), (15, 20), (12, 17)], (6, 6, 9, 255))
    px(img, 14, 14, (120, 190, 180, 255))
    px(img, 16, 14, (120, 190, 180, 255))
    # tentáculos que salen de la base
    for i in range(3):
        d.line([(10 + i * 4, 40), (9 + i * 5, 34), (11 + i * 4, 30)],
               fill=(36, 34, 40, 255), width=2)
    img = edge_light(img, (74, 80, 78), 1, 0, 90)
    return img


def tentacle_hazard():
    """Tentáculo que brota del suelo: 3 frames."""
    out = []
    for f in range(3):
        img = new(20, 40)
        d = ImageDraw.Draw(img)
        pts = []
        for i in range(9):
            t = i / 8.0
            x = 10 + math.sin(t * 2.2 + f * 1.1) * (4 + t * 3)
            y = 40 - t * (34 + f * 2)
            pts.append((x, y, 5 - t * 4))
        for i in range(len(pts) - 1):
            d.line([(pts[i][0], pts[i][1]), (pts[i + 1][0], pts[i + 1][1])],
                   fill=(44, 26, 40, 255), width=max(1, int(pts[i][2])))
        for i in range(len(pts) - 1):
            px(img, pts[i][0] - 1, pts[i][1], (96, 52, 70, 255))
        px(img, pts[-1][0], pts[-1][1], (150, 90, 110, 255))
        # ventosas
        for i in range(1, len(pts) - 1, 2):
            px(img, pts[i][0] + 1, pts[i][1], (120, 70, 84, 200))
        out.append(img)
    return out


def chain():
    img = new(6, 32)
    d = ImageDraw.Draw(img)
    for y in range(0, 32, 4):
        d.ellipse([1, y, 4, y + 3], outline=(58, 56, 54, 255))
    return img


def save_props(outdir):
    os.makedirs(outdir, exist_ok=True)
    altar().save(os.path.join(outdir, "prop_altar.png"))
    torch().save(os.path.join(outdir, "prop_torch.png"))
    gate().save(os.path.join(outdir, "prop_gate.png"))
    book().save(os.path.join(outdir, "prop_book.png"))
    statue().save(os.path.join(outdir, "prop_statue.png"))
    chain().save(os.path.join(outdir, "prop_chain.png"))
    for i, im in enumerate(tentacle_hazard()):
        im.save(os.path.join(outdir, f"prop_tentacle_{i}.png"))
    print("props: altar torch gate book statue chain tentacle(3)")


if __name__ == "__main__":
    root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets")
    save_atlases(os.path.join(root, "tiles"))
    save_props(os.path.join(root, "sprites"))
