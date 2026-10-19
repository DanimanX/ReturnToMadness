"""Fondos de parallax: 7 etapas x 2 capas (lejos / cerca), 1600x270.

Regla de arte: todo el fondo por debajo de valor 60 salvo la fuente de luz.
La capa cercana es casi negra: enmarca y da profundidad sin competir con el juego.
"""
from __future__ import annotations

import math
import os
import random
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(__file__))
from pixelart import BAYER4, clamp, value_noise  # noqa: E402

W, H = 1600, 270


def canvas():
    return Image.new("RGBA", (W, H), (0, 0, 0, 255))


def draw(img, fn):
    """Dibuja en una capa RGBA y la compone (mezcla real de alfa)."""
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer, "RGBA")
    fn(d, layer)
    img.alpha_composite(layer)


def sky(top, bottom, seed=0, glow=None):
    img = canvas()
    d = ImageDraw.Draw(img, "RGBA")
    for y in range(H):
        t = (y / (H - 1)) ** 0.9
        c = [int(top[i] + (bottom[i] - top[i]) * t) for i in range(3)]
        d.line([(0, y), (W, y)], fill=tuple(c) + (255,))
    if glow:
        gx, gy, gr, gc, ga = glow
        draw(img, lambda dd, ll: [dd.ellipse([gx - gr * k / 6, gy - gr * k / 3,
                                              gx + gr * k / 6, gy + gr * k / 3],
                                             fill=tuple(gc) + (int(ga * (1 - k / 7)),))
                                 for k in range(1, 7)])
    # dither fino
    rnd = random.Random(seed)
    p = img.load()
    for y in range(H):
        for x in range(W):
            if BAYER4[y % 4][x % 4] / 16.0 < 0.5:
                continue
            r, g, b, a = p[x, y]
            k = 2 if rnd.random() < 0.5 else -2
            p[x, y] = (clamp(r + k), clamp(g + k), clamp(b + k), 255)
    return img


def haze(img, y0, y1, color, peak=60, seed=3, density=0.45):
    """Bruma sutil: solo un poco, cerca del horizonte."""
    n = value_noise(W, H, 70, seed)
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    p = layer.load()
    for y in range(max(0, y0), min(H, y1)):
        t = (y - y0) / max(1, y1 - y0)
        a = int(peak * math.sin(t * math.pi) ** 1.5)
        for x in range(W):
            if n[y][x] > density:
                p[x, y] = tuple(color) + (a,)
    img.alpha_composite(layer)


def moon(d, cx, cy, r, col=(206, 210, 196), halo=(120, 150, 140), halo_a=26):
    if True:
        for k in range(5, 0, -1):
            rr = r * (1 + k * 0.7)
            d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr],
                      fill=tuple(halo) + (int(halo_a * (1 - k / 6)),))
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=tuple(col) + (255,))
        rnd = random.Random(int(cx + cy))
        for _ in range(6):
            ex = cx + rnd.uniform(-r * .6, r * .6)
            ey = cy + rnd.uniform(-r * .6, r * .6)
            er = rnd.uniform(1, r * .25)
            d.ellipse([ex - er, ey - er, ex + er, ey + er],
                      fill=(clamp(col[0] - 16), clamp(col[1] - 16), clamp(col[2] - 14), 255))


def ridge(d, base_y, amp, step, color, seed=0, rough=1.0):
    rnd = random.Random(seed)
    pts = [(0, H), (0, base_y)]
    x = 0
    while x <= W:
        pts.append((x, base_y - rnd.uniform(0, amp) * rough))
        x += step
    pts += [(W, base_y), (W, H)]
    d.polygon(pts, fill=tuple(color) + (255,))


def towers(d, count, base_y, hmin, hmax, color, seed=0, wmin=12, wmax=34, lights=0.35):
    rnd = random.Random(seed)
    if True:
        for _ in range(count):
            x = rnd.randrange(-60, W)
            w = rnd.randrange(wmin, wmax)
            h = rnd.randrange(hmin, hmax)
            lean = rnd.uniform(-0.08, 0.08) * h
            top = base_y - h
            d.polygon([(x, base_y), (x + w, base_y), (x + w + lean, top), (x + lean, top)],
                      fill=tuple(color) + (255,))
            if rnd.random() < 0.7:
                d.polygon([(x + lean - 4, top), (x + w + lean + 4, top),
                           (x + w / 2 + lean, top - rnd.randrange(8, 26))],
                          fill=tuple(color) + (255,))
            if rnd.random() < lights:
                for _ in range(rnd.randrange(1, 3)):
                    wx = int(x + rnd.randrange(3, max(4, w - 4)))
                    wy = int(top + rnd.randrange(6, max(8, h - 8)))
                    d.rectangle([wx, wy, wx + 1, wy + 1], fill=(150, 116, 58, 230))


def tentacle(d, x, base_y, height, width, color, sway=0.0, seg=16):
    pts = []
    ws = []
    for i in range(seg):
        t = i / (seg - 1)
        pts.append((x + math.sin(t * 2.6 + sway) * width * 1.1, base_y - t * height))
        ws.append(max(1, width * (1 - t * 0.85)))
    for i in range(len(pts) - 1):
        d.line([pts[i], pts[i + 1]], fill=tuple(color) + (255,), width=int(round(ws[i])))


# ------------------------------------------------------------------ etapas
def stage1():
    """Innsmouth: costa bajo la lluvia."""
    far = sky((6, 10, 15), (14, 24, 30), 1, glow=(1180, 150, 260, (30, 48, 54), 90))
    D = ImageDraw.Draw(far, "RGBA")
    moon(D, 1180, 58, 15, (178, 186, 176), (70, 96, 96), 20)

    def clouds(d, _):
        n = value_noise(W, H, 46, 21)
        for y in range(8, 120):
            band = 1 - abs((y - 64) / 64.0)
            for x in range(W):
                if n[y][x] * band > 0.52:
                    d.point((x, y), fill=(12, 20, 26, 150))
    draw(far, clouds)
    towers(D, 22, 214, 26, 86, (9, 16, 20), 11, 10, 30, 0.4)
    # mar
    def sea(d, _):
        d.rectangle([0, 216, W, H], fill=(7, 14, 18, 255))
        rnd = random.Random(31)
        for _ in range(200):
            x, y = rnd.randrange(W), rnd.randrange(220, H)
            d.line([(x, y), (x + rnd.randrange(3, 12), y)], fill=(26, 46, 52, 140))
        # reflejo de luna
        for y in range(220, H, 3):
            w = 10 + (y - 220) // 4
            d.line([(1180 - w // 2, y), (1180 + w // 2, y)], fill=(70, 92, 86, 90))
    draw(far, sea)
    haze(far, 170, 250, (34, 54, 58), 70, 7)

    near = canvas()
    near.putalpha(0)
    def nearc(d, _):
        towers(d, 6, 276, 110, 210, (4, 7, 9), 41, 34, 70, 0.25)
        for x in range(60, W, 300):
            d.rectangle([x, 188, x + 3, 270], fill=(3, 5, 7, 255))
            d.rectangle([x - 9, 190, x + 12, 194], fill=(3, 5, 7, 255))
            d.rectangle([x + 3, 192, x + 10, 195], fill=(120, 92, 44, 200))
    draw(near, nearc)
    return far, near


def stage2():
    """Criptas de Dagon."""
    far = sky((5, 11, 12), (12, 26, 26), 2, glow=(800, 250, 400, (16, 44, 42), 80))
    D = ImageDraw.Draw(far, "RGBA")

    def arch(d, _):
        step = 200
        for i in range(W // step + 1):
            x = i * step
            d.rectangle([x, 96, x + 16, 270], fill=(8, 19, 19, 255))
            d.rectangle([x + 168, 96, x + 184, 270], fill=(8, 19, 19, 255))
            for k in range(84):
                rr = 84 - k
                d.arc([x + 92 - rr, 96 - rr, x + 92 + rr, 96 + rr], 180, 360,
                      fill=(8, 19, 19, 255), width=1)
            d.rectangle([x, 20, x + 184, 30], fill=(7, 16, 16, 255))
            # luz en el intradós
            d.arc([x + 92 - 76, 96 - 76, x + 92 + 76, 96 + 76], 190, 350,
                  fill=(26, 60, 56, 120), width=1)
    draw(far, arch)

    def detrás(d, _):
        for i in range(6):
            tentacle(d, 120 + i * 280, 270, 170, 5, (9, 24, 24), i * 0.8)
        for x in range(40, W, 210):
            for y in range(0, 70, 5):
                d.ellipse([x - 2, y, x + 2, y + 3], outline=(7, 16, 16, 255))
    draw(far, detrás)
    haze(far, 150, 270, (18, 52, 50), 70, 5)

    near = canvas()
    near.putalpha(0)
    def nearc(d, _):
        for i in range(6):
            x = i * 300 + 30
            d.rectangle([x, 108, x + 34, 270], fill=(3, 7, 8, 255))
            d.rectangle([x - 8, 96, x + 42, 112], fill=(4, 9, 10, 255))
            d.rectangle([x - 8, 96, x + 42, 99], fill=(18, 40, 38, 255))
        rnd = random.Random(3)
        for _ in range(150):
            x, y = rnd.randrange(W), rnd.randrange(196, 270)
            d.ellipse([x, y, x + rnd.randrange(1, 4), y + rnd.randrange(1, 3)],
                      fill=(9, 22, 22, 220))
    draw(near, nearc)
    return far, near


def stage3():
    """Biblioteca Miskatonic."""
    far = sky((10, 8, 7), (24, 18, 12), 3)
    D = ImageDraw.Draw(far, "RGBA")

    def windows(d, _):
        for i in range(4):
            x = 210 + i * 400
            d.rectangle([x, 24, x + 96, 176], fill=(34, 30, 22, 255))
            d.rectangle([x + 9, 33, x + 87, 167], fill=(16, 24, 32, 255))
            for k in range(1, 4):
                d.line([(x + 9, 33 + k * 33), (x + 87, 33 + k * 33)], fill=(34, 30, 22, 255), width=2)
            d.line([(x + 48, 33), (x + 48, 167)], fill=(34, 30, 22, 255), width=2)
            # luz fría de la luna
            d.rectangle([x + 9, 33, x + 87, 167], fill=(24, 34, 40, 120))
    draw(far, windows)

    def shelves(d, _):
        for row, y in enumerate(range(48, 270, 52)):
            d.rectangle([0, y, W, y + 40], fill=(11, 8, 6, 255))
            x = 4
            while x < W:
                w = 5
                hh = 22 + (x * 7 + row * 13) % 10
                shade = (15 + (x // 7) % 7, 11 + (x // 5) % 5, 7)
                d.rectangle([x, y + 40 - hh, x + w, y + 40], fill=tuple(shade) + (255,))
                x += w + 2
            d.rectangle([0, y + 40, W, y + 43], fill=(9, 7, 5, 255))
            # un candelabro cada tanto
            if row % 2 == 0:
                for cx in range(140 + row * 40, W, 520):
                    d.rectangle([cx, y + 8, cx + 2, y + 26], fill=(40, 32, 22, 255))
                    d.point((cx + 1, y + 6), fill=(210, 160, 80, 255))
    draw(far, shelves)
    haze(far, 0, 270, (40, 30, 18), 20, 5, 0.55)
    # sombra profunda en la parte baja
    def grad(d, _):
        for y in range(120, 270):
            a = int((y - 120) / 150 * 150)
            d.line([(0, y), (W, y)], fill=(0, 0, 0, a))
    draw(far, grad)

    near = canvas()
    near.putalpha(0)
    def nearc(d, _):
        for i in range(4):
            x = i * 430 - 20
            d.rectangle([x, 0, x + 46, 270], fill=(4, 3, 3, 255))
            d.rectangle([x - 10, 0, x + 56, 18], fill=(5, 4, 3, 255))
            d.line([(x, 0), (x, 270)], fill=(16, 13, 9, 255))
        rnd = random.Random(12)
        for _ in range(16):
            x, y = rnd.randrange(W), rnd.randrange(244, 268)
            w, h = rnd.randrange(8, 20), rnd.randrange(2, 6)
            d.rectangle([x, y, x + w, y + h], fill=(12, 9, 6, 255))
    draw(near, nearc)
    return far, near


def stage4():
    """Meseta de Leng."""
    far = sky((10, 12, 26), (26, 26, 44), 4)
    D = ImageDraw.Draw(far, "RGBA")
    moon(D, 340, 58, 36, (214, 220, 232), (110, 120, 175), 46)
    ridge(D, 196, 96, 96, (26, 31, 54), 8, 1.0)
    ridge(D, 222, 62, 64, (17, 21, 40), 9, 1.1)
    ridge(D, 246, 34, 48, (9, 11, 22), 10, 1.2)
    haze(far, 180, 270, (58, 66, 96), 80, 10)

    def nieve(d, _):
        rnd = random.Random(4)
        for _ in range(240):
            x, y = rnd.randrange(W), rnd.randrange(H)
            d.point((x, y), fill=(150, 160, 190, rnd.choice((30, 50, 70))))
    draw(far, nieve)

    near = canvas()
    near.putalpha(0)
    def nearc(d, _):
        for x, hh, lean in ((160, 160, 10), (700, 210, -14), (1180, 130, 8)):
            d.polygon([(x, 270), (x + 40, 270), (x + 40 + lean, 270 - hh),
                       (x + lean, 270 - hh)], fill=(6, 7, 14, 255))
            d.line([(x + lean, 270 - hh), (x + 40 + lean, 270 - hh)], fill=(74, 84, 116, 220))
            d.line([(x + lean, 270 - hh), (x + lean, 270 - hh + 60)], fill=(24, 28, 46, 200))
        for x in range(0, W, 34):
            d.ellipse([x, 256, x + 40, 272], fill=(7, 9, 18, 255))
    draw(near, nearc)
    return far, near


def stage5():
    """Yuggoth: ciudad-máquina fúngica."""
    far = sky((9, 5, 16), (26, 12, 32), 5, glow=(1300, 90, 300, (60, 20, 60), 70))
    D = ImageDraw.Draw(far, "RGBA")
    # anillos
    def rings(d, _):
        for r in (140, 200, 260):
            d.arc([1300 - r, 90 - r // 3, 1300 + r, 90 + r // 3], 200, 340,
                  fill=(58, 24, 60, 90), width=1)
            d.arc([1300 - r, 90 - r // 3, 1300 + r, 90 + r // 3], 340, 380,
                  fill=(58, 24, 60, 60), width=1)
    draw(far, rings)

    def towers_f(d, _):
        rnd = random.Random(5)
        for i in range(12):
            x = rnd.randrange(W)
            hh = rnd.randrange(70, 200)
            w = rnd.randrange(16, 40)
            d.polygon([(x, 270), (x + w, 270), (x + w - 4, 270 - hh),
                       (x + 6, 270 - hh)], fill=(17, 8, 23, 255))
            d.ellipse([x - 14, 270 - hh - 22, x + w + 14, 270 - hh + 14], fill=(24, 11, 30, 255))
            d.arc([x - 14, 270 - hh - 22, x + w + 14, 270 - hh + 14], 200, 340,
                  fill=(92, 38, 100, 200), width=1)
            for _ in range(5):
                d.point((x + rnd.randrange(max(1, w)), 270 - hh - 14 + rnd.randrange(12)),
                        fill=(196, 88, 210, 230))
    draw(far, towers_f)
    haze(far, 110, 270, (56, 18, 56), 70, 11)

    near = canvas()
    near.putalpha(0)
    def nearc(d, _):
        for i in range(5):
            x = 70 + i * 320
            d.rectangle([x, 130, x + 30, 270], fill=(6, 3, 9, 255))
            d.ellipse([x - 26, 100, x + 56, 148], fill=(7, 4, 11, 255))
            for k in range(6):
                d.point((x + 8 + k * 4, 120), fill=(180, 70, 200, 220))
            d.arc([x - 26, 100, x + 56, 148], 200, 340, fill=(90, 36, 100, 190), width=1)
        rnd = random.Random(17)
        for _ in range(110):
            d.point((rnd.randrange(W), rnd.randrange(H)),
                    fill=(180, 80, 180, rnd.choice((40, 70, 100))))
    draw(near, nearc)
    return far, near


def stage6():
    """R'lyeh: el ojo y la geometría imposible."""
    far = sky((7, 15, 14), (18, 34, 30), 6, glow=(820, 120, 340, (30, 62, 50), 90))
    D = ImageDraw.Draw(far, "RGBA")

    def ojo(d, _):
        cxx, cyy = 820, 118
        d.ellipse([cxx - 190, cyy - 96, cxx + 190, cyy + 96], fill=(12, 28, 25, 255))
        d.ellipse([cxx - 176, cyy - 84, cxx + 176, cyy + 84], fill=(22, 46, 38, 255))
        d.ellipse([cxx - 62, cyy - 62, cxx + 62, cyy + 62], fill=(96, 128, 66, 200))
        d.ellipse([cxx - 22, cyy - 22, cxx + 22, cyy + 22], fill=(4, 7, 6, 255))
        d.point((cxx - 26, cyy - 16), fill=(210, 230, 170, 220))
    draw(far, ojo)

    def slabs(d, _):
        for x, y, w, h in ((110, 54, 190, 96), (400, 150, 120, 190), (1200, 30, 160, 80),
                           (1420, 150, 130, 180), (620, 24, 96, 64)):
            d.polygon([(x, y), (x + w, y - 12), (x + w + 12, y + h), (x - 8, y + h + 10)],
                      fill=(11, 26, 22, 255))
            d.line([(x, y), (x + w, y - 12)], fill=(52, 96, 74, 140))
    draw(far, slabs)

    def ciudad(d, _):
        rnd = random.Random(8)
        for _ in range(12):
            x = rnd.randrange(W)
            w = rnd.randrange(24, 62)
            hh = rnd.randrange(30, 90)
            d.rectangle([x, 270 - hh, x + w, 270], fill=(8, 19, 17, 255))
            d.polygon([(x, 270 - hh), (x + w // 2, 270 - hh - 30), (x + w, 270 - hh)],
                      fill=(8, 19, 17, 255))
    draw(far, ciudad)
    haze(far, 130, 270, (34, 74, 58), 72, 13)

    near = canvas()
    near.putalpha(0)
    def nearc(d, _):
        for i in range(4):
            x = 60 + i * 400
            for k in range(20):
                t = k / 19
                d.rectangle([x + math.sin(t * 2.2) * 10, 270 - t * 230,
                             x + 26 + math.sin(t * 2.2) * 10, 270 - t * 230 + 12],
                            fill=(3, 8, 7, 255))
        for i in range(8):
            tentacle(d, 40 + i * 210, 278, 120, 7, (3, 8, 7), i * 0.9)
    draw(near, nearc)
    return far, near


def stage7():
    """Trono del Durmiente."""
    far = sky((26, 9, 11), (6, 12, 12), 7, glow=(800, 200, 500, (86, 24, 24), 110))
    D = ImageDraw.Draw(far, "RGBA")

    def coloso(d, _):
        # silueta gigantesca apenas visible contra el resplandor
        d.polygon([(800, 30), (874, 86), (1030, 48), (1070, 150), (1004, 268),
                   (596, 268), (530, 150), (570, 48), (726, 86)], fill=(5, 10, 10, 255))
        d.line([(800, 30), (874, 86), (1030, 48)], fill=(96, 44, 40, 200))
        d.line([(800, 30), (726, 86), (570, 48)], fill=(96, 44, 40, 200))
        for i in range(9):
            tentacle(d, 646 + i * 40, 266, 200, 8, (6, 12, 12), i * 0.7)
        d.ellipse([770, 84, 786, 96], fill=(120, 220, 140, 200))
        d.ellipse([816, 84, 832, 96], fill=(120, 220, 140, 200))
        # alas
        d.polygon([(770, 60), (560, 4), (700, 130)], fill=(6, 12, 12, 255))
        d.polygon([(832, 60), (1040, 4), (900, 130)], fill=(6, 12, 12, 255))
    draw(far, coloso)

    def cols(d, _):
        for i in range(6):
            x = 80 + i * 290
            d.rectangle([x, 20, x + 38, 270], fill=(8, 8, 10, 255))
            d.rectangle([x - 8, 12, x + 46, 30], fill=(10, 10, 12, 255))
            d.line([(x, 20), (x, 270)], fill=(20, 18, 20, 255))
    draw(far, cols)

    near = canvas()
    near.putalpha(0)
    def nearc(d, _):
        for i in range(8):
            tentacle(d, 70 + i * 210, 282, 200, 13, (3, 6, 6), i * 1.1)
        for i in range(3):
            x = i * 520 + 120
            d.rectangle([x, 0, x + 50, 270], fill=(3, 4, 5, 255))
            for k in range(7):
                d.rectangle([x + 10, 30 + k * 34, x + 42, 38 + k * 34], fill=(9, 9, 11, 255))
    draw(near, nearc)
    return far, near


STAGES = [stage1, stage2, stage3, stage4, stage5, stage6, stage7]


def lift(img, gain, tint=(0, 0, 0)):
    """Sube el valor sin tocar el alfa: la capa cercana debe leerse, no ser un vacío."""
    px = img.load()
    for y in range(img.height):
        for x in range(img.width):
            r, g, b, a = px[x, y]
            if a == 0:
                continue
            px[x, y] = (clamp(r * gain + tint[0]), clamp(g * gain + tint[1]),
                        clamp(b * gain + tint[2]), a)
    return img


def main(outdir):
    os.makedirs(outdir, exist_ok=True)
    for i, fn in enumerate(STAGES, start=1):
        far, near = fn()
        lift(far, 1.18)
        lift(near, 3.4, (2, 4, 6))
        far.save(os.path.join(outdir, f"bg_{i}_far.png"))
        near.save(os.path.join(outdir, f"bg_{i}_near.png"))
    print("fondos: 7 etapas x 2 capas")
    # hoja a tamaño real (recorte central 480x270, sin escalar)
    sheet = Image.new("RGBA", (480 * 2, 270 * 7), (0, 0, 0, 255))
    for i in range(1, 8):
        far = Image.open(os.path.join(outdir, f"bg_{i}_far.png"))
        near = Image.open(os.path.join(outdir, f"bg_{i}_near.png"))
        comp = Image.alpha_composite(far, near).crop((560, 0, 1040, 270))
        sheet.alpha_composite(comp, (0, (i - 1) * 270))
    sheet.save("/tmp/bg_sheet.png")


if __name__ == "__main__":
    main(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "bg"))
