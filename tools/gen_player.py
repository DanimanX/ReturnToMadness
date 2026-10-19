"""Genera el sprite del Testigo (jugador).

Construcción por capas: silueta -> sombreado -> borde -> emisivos.
Canvas 48x48, pies en y=46, mirando a la derecha.
"""
from __future__ import annotations

import math
import os
import sys

from PIL import Image, ImageChops, ImageDraw

sys.path.insert(0, os.path.dirname(__file__))
from pixelart import GOLD, GOLD_HI, edge_light, glow, inner_shadow, new, poly, px  # noqa: E402

W = H = 48
FEET = 46
CX = 24.0

CLOAK_D = (14, 15, 21)
CLOAK_M = (24, 26, 37)
CLOAK_H = (46, 50, 64)
RIM_WARM = (186, 148, 98)
RIM_COLD = (56, 88, 98)
BLADE_D = (66, 74, 88)
BLADE_HI = (158, 174, 190)
EYE = (255, 150, 52)
GLOWC = (255, 168, 78)


def body(img, lean=0.0, bob=0.0, cloth_phase=0.0, cloth_amp=1.1, stride=0.0,
         arm_raise=0.0, crouch=0.0, tilt=0.0):
    d = ImageDraw.Draw(img)
    cx = CX + lean + tilt * 0.5
    sh_y = 18.0 + bob + crouch * 0.35
    hem_y = 43.0 + crouch * 0.55
    col = CLOAK_D + (255,)

    # capucha: cono de 1px en la punta a 11px en la base
    apex = (cx + tilt * 1.4 - 0.5, 2.0 + bob * 0.4)
    poly(d, [apex,
             (cx + 2.0 + tilt * 0.9, 8.0 + bob * 0.6),
             (cx + 4.6 + tilt * 0.5, 14.0 + bob * 0.8),
             (cx + 5.2, sh_y + 0.6),
             (cx - 5.4, sh_y + 0.6),
             (cx - 4.8 + tilt * 0.5, 13.8 + bob * 0.8),
             (cx - 2.6 + tilt * 0.9, 7.8 + bob * 0.6)], col)

    # manto de hombros
    poly(d, [(cx - 7.4 + lean * 0.4, sh_y), (cx + 7.6 + lean * 0.4, sh_y),
             (cx + 6.8, sh_y + 3.2), (cx - 6.6, sh_y + 3.2)], col)

    # túnica: lados casi rectos, bajo harapiento
    hem = []
    for i in range(15):
        t = i / 14.0
        x = cx - 6.6 + t * 13.2
        w = math.sin(t * 7.0 + cloth_phase) * cloth_amp
        hem.append((x, hem_y + w * (0.4 + 0.8 * abs(t - 0.5) * 2)))
    poly(d, [(cx - 6.2, sh_y + 1.0), (cx + 6.4, sh_y + 1.0),
             (cx + 7.0, hem_y - 5.0), (cx - 6.8, hem_y - 5.0)] + list(reversed(hem)), col)

    # botas
    d.line([(cx - 2.6, hem_y - 6), (cx - 2.6 - stride * 1.1, FEET)], fill=col, width=3)
    d.line([(cx + 2.8, hem_y - 6), (cx + 2.8 + stride * 1.1, FEET)], fill=col, width=3)

    # brazo trasero (farol)
    hand_l = (cx - 7.6, 31.0 + bob + arm_raise * 0.5)
    d.line([(cx - 6.0, sh_y + 1.6), (cx - 7.8, 24.5 + bob), hand_l], fill=col, width=2)

    # brazo delantero (espada)
    hand_r = (cx + 7.4 + arm_raise * 1.2, 30.0 + bob - arm_raise * 6.0)
    d.line([(cx + 6.2, sh_y + 1.6), (cx + 8.2, 24.0 + bob - arm_raise * 1.5), hand_r],
           fill=col, width=2)

    return dict(cx=cx, sh_y=sh_y, hem_y=hem_y, hand_l=hand_l, hand_r=hand_r,
                arm_raise=arm_raise, bob=bob)


def sword(img, hand, raise_amt=0.0):
    d = ImageDraw.Draw(img)
    hx, hy = hand
    # ángulo base: hoja hacia abajo-adelante; el ataque la sube en arco
    base = math.radians(82)
    sweep = math.radians(-150)
    a = base + sweep * raise_amt
    n = 13
    pts = []
    for i in range(n):
        t = i / (n - 1)
        r = t * 15.0
        bend = math.sin(t * math.pi) * 1.4
        da = a - math.radians(8) * t
        pts.append((hx + math.cos(da) * r + bend * 0.3,
                    hy + math.sin(da) * r - bend))
    d.line(pts, fill=BLADE_D + (255,), width=3, joint="curve")
    # cerca del mango, hoja ancha (recuerda a una vela derretida)
    d.line(pts[:4], fill=BLADE_D + (255,), width=4, joint="curve")
    d.line([(pts[i][0], pts[i][1] - 1) for i in range(1, len(pts))],
           fill=BLADE_HI + (255,), width=1, joint="curve")
    d.line([(pts[i][0] + 1, pts[i][1] + 1) for i in range(len(pts))],
           fill=(52, 58, 70, 255), width=1, joint="curve")
    # guarda
    gx, gy = hx, hy
    d.line([(gx - 2, gy - 1), (gx, gy + 1), (gx + 2, gy - 1)], fill=GOLD + (255,), width=1)
    px(img, gx, gy + 2, GOLD_HI + (255,))
    px(img, gx, gy + 3, GOLD + (255,))


def lantern(img, hand, lit=True):
    hx, hy = hand
    d = ImageDraw.Draw(img)
    d.line([(hx, hy), (hx, hy + 2)], fill=GOLD + (255,), width=1)
    d.rectangle([hx - 2, hy + 3, hx + 2, hy + 8], fill=(16, 12, 9, 255))
    d.rectangle([hx - 2, hy + 3, hx + 2, hy + 8], outline=GOLD + (210,))
    if lit:
        px(img, hx - 1, hy + 6, GLOWC + (255,))
        px(img, hx, hy + 5, (255, 226, 160, 255))
        px(img, hx + 1, hy + 6, GLOWC + (255,))


def shade(img, anc, cloth_phase=0.0, lit=True):
    cx = anc["cx"]
    sh_y = anc["sh_y"]
    img = inner_shadow(img, CLOAK_M, -2, 0, 95)
    img = inner_shadow(img, (4, 4, 7), 2, 0, 170)
    img = edge_light(img, RIM_WARM, -1, 0, 190)
    img = edge_light(img, RIM_COLD, 0, -1, 45)

    d = ImageDraw.Draw(img)
    # interior de la capucha: trapecio pequeño, dentro del cono
    top = sh_y - 8.5
    poly(d, [(cx - 3.4, top), (cx + 3.6, top), (cx + 3.0, sh_y - 3.0), (cx - 2.8, sh_y - 3.0)],
         (4, 4, 8, 255))
    px(img, cx - 1, top + 2, EYE + (255,))
    px(img, cx + 2, top + 2, EYE + (255,))
    px(img, cx - 1, top + 1, (255, 214, 150, 255))
    # pliegues de la túnica
    for fx, fy0, fy1 in ((cx - 3, sh_y + 6, 40), (cx + 2, sh_y + 8, 41)):
        for yy in range(int(fy0), int(fy1)):
            if yy % 3 != 2:
                px(img, fx + (1 if (yy // 3) % 2 else 0), yy, CLOAK_M + (110,))
    # hebilla / cadena
    px(img, cx, int(sh_y) + 9, GOLD + (190,))
    px(img, cx - 1, int(sh_y) + 10, (150, 112, 50, 160))
    return img


def frame(kind, i=0, n=1):
    t = i / max(1, n)
    p = dict(lean=0.0, bob=0.0, cloth_phase=0.0, cloth_amp=1.0, stride=0.0,
             arm_raise=0.0, crouch=0.0, tilt=0.0, lit=True, sword=True)
    if kind == "idle":
        p["bob"] = math.sin(t * math.tau) * 0.7
        p["cloth_phase"] = t * math.tau * 0.5
        p["cloth_amp"] = 0.9
    elif kind == "run":
        p["stride"] = math.sin(t * math.tau)
        p["bob"] = -abs(math.sin(t * math.tau)) * 1.2
        p["lean"] = 1.2
        p["cloth_phase"] = -t * math.tau * 1.3
        p["cloth_amp"] = 1.7
        p["arm_raise"] = 0.08
        p["tilt"] = 0.6
    elif kind == "jump":
        p.update(stride=1.0, cloth_amp=2.0, cloth_phase=1.2, arm_raise=0.12, tilt=-0.4)
    elif kind == "fall":
        p.update(stride=-1.0, cloth_amp=2.2, cloth_phase=3.6, arm_raise=0.04, tilt=0.5)
    elif kind == "dash":
        p.update(lean=3.2, cloth_amp=2.6, cloth_phase=4.4, arm_raise=0.28, bob=-1.0,
                 stride=0.7, tilt=1.2)
    elif kind == "attack":
        p["arm_raise"] = [0.98, 0.62, 0.18, 0.0][min(i, 3)]
        p["lean"] = [0.4, 1.8, 2.4, 0.8][min(i, 3)]
        p["cloth_phase"] = [4.0, 5.2, 5.8, 5.0][min(i, 3)]
        p["cloth_amp"] = 1.9
        p["bob"] = [0.0, 0.4, 0.6, 0.2][min(i, 3)]
        p["tilt"] = [-0.5, 0.8, 1.0, 0.3][min(i, 3)]
    elif kind == "hurt":
        p.update(lean=-2.6, cloth_amp=2.4, cloth_phase=2.2, bob=1.0, crouch=1.4, tilt=-1.4)
    elif kind == "death":
        p["crouch"] = [0.0, 3.0, 7.0, 11.0, 14.0][min(i, 4)]
        p["lean"] = -0.8 - i * 0.5
        p["cloth_amp"] = 2.2
        p["cloth_phase"] = 2.0 + i * 0.6
        p["lit"] = i < 3
        p["tilt"] = -0.4 * i
    elif kind == "voice":
        p["arm_raise"] = [0.95, 0.75, 0.45][min(i, 2)]
        p["lean"] = -0.6
        p["cloth_amp"] = 2.2
        p["cloth_phase"] = 1.5
        p["bob"] = -0.8

    img = new(W, H)
    anc = body(img, lean=p["lean"], bob=p["bob"], cloth_phase=p["cloth_phase"],
               cloth_amp=p["cloth_amp"], stride=p["stride"], arm_raise=p["arm_raise"],
               crouch=p["crouch"], tilt=p["tilt"])
    img = shade(img, anc, p["cloth_phase"], p["lit"])

    # el halo del farol lo pone el motor (Light2D), no el sprite
    lantern(img, anc["hand_l"], p["lit"])
    if p["sword"]:
        sword(img, anc["hand_r"], p["arm_raise"])
    if kind == "death" and i >= 3:
        img = img.point(lambda v: int(v * 0.8))
    return img


def main(outdir):
    os.makedirs(outdir, exist_ok=True)
    plan = [("idle", 4), ("run", 8), ("jump", 1), ("fall", 1), ("dash", 1),
            ("attack", 4), ("hurt", 1), ("death", 5), ("voice", 3)]
    frames = []
    for kind, n in plan:
        for i in range(n):
            im = frame(kind, i, n)
            im.save(os.path.join(outdir, f"testigo_{kind}_{i}.png"))
            frames.append(im)
    print(f"testigo: {len(frames)} frames")
    from pixelart import contact_sheet
    contact_sheet(frames, 10, W, H, scale=3).save("/tmp/testigo_sheet.png")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else
         os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "sprites"))
