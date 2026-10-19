"""pixelart.py — toolkit mínimo de pixel art para Regreso a la Locura.

Todo se dibuja a 1x con formas duras (sin antialias) y luego se compone.
La estética: silueta casi negra + luz de borde cálida + detalles emisivos.
"""
from __future__ import annotations

import math
import random

from PIL import Image, ImageChops, ImageDraw, ImageFilter

# ---------------------------------------------------------------- paleta base
INK        = (8, 7, 12)
INK_SOFT   = (17, 16, 25)
BONE       = (198, 189, 160)
BONE_DIM   = (128, 122, 104)
BLOOD      = (110, 18, 22)
BLOOD_HI   = (168, 36, 38)
GOLD       = (226, 175, 92)
GOLD_HI    = (255, 222, 150)
CANDLE     = (255, 196, 110)
TEAL       = (34, 86, 88)
TEAL_HI    = (86, 164, 150)
VIOLET     = (86, 52, 120)
VIOLET_HI  = (156, 108, 196)
SICK       = (128, 150, 74)
STEEL      = (150, 160, 172)
STEEL_HI   = (216, 226, 232)


def new(w: int, h: int) -> Image.Image:
    return Image.new("RGBA", (w, h), (0, 0, 0, 0))


def P(pts):
    return [(int(round(x)), int(round(y))) for x, y in pts]


def poly(d: ImageDraw.ImageDraw, pts, color):
    d.polygon(P(pts), fill=color)


def rect(d, x0, y0, x1, y1, color):
    d.rectangle([int(x0), int(y0), int(x1), int(y1)], fill=color)


def px(img: Image.Image, x, y, color):
    x, y = int(x), int(y)
    if 0 <= x < img.width and 0 <= y < img.height:
        img.putpixel((x, y), color)


def line(d, pts, color, width=1):
    d.line(P(pts), fill=color, width=width, joint="curve")


def ellipse(d, cx, cy, rx, ry, color):
    d.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=color)


def edge_light(img: Image.Image, color, dx=0, dy=-1, strength=255, mask_src=None) -> Image.Image:
    """Añade un borde de 1px del color dado desplazando la silueta."""
    a = (mask_src or img).split()[3]
    shifted = ImageChops.offset(a, dx, dy)
    edge = ImageChops.subtract(a, shifted)
    if strength != 255:
        edge = edge.point(lambda v: v * strength // 255)
    layer = Image.new("RGBA", img.size, tuple(color) + (0,))
    layer.putalpha(edge)
    return Image.alpha_composite(img, layer)


def inner_shadow(img: Image.Image, color, dx=0, dy=1, strength=255, src=None) -> Image.Image:
    """Sombra interior: zona de la silueta que queda expuesta al desplazar."""
    a = (src or img).split()[3]
    shifted = ImageChops.offset(a, dx, dy)
    inner = ImageChops.subtract(a, shifted)
    if strength != 255:
        inner = inner.point(lambda v: v * strength // 255)
    layer = Image.new("RGBA", img.size, tuple(color) + (0,))
    layer.putalpha(inner)
    return Image.alpha_composite(img, layer)


def glow(img: Image.Image, cx, cy, radius, color, strength=140) -> Image.Image:
    """Halo suave (se difumina y se mezcla). Barato y suficiente a esta escala."""
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    steps = max(2, radius)
    for i in range(steps, 0, -1):
        t = i / steps
        a = int(strength * (1 - t) ** 2)
        r = radius * t
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=tuple(color) + (a,))
    layer = layer.filter(ImageFilter.GaussianBlur(1.2))
    return Image.alpha_composite(img, layer)


def dither_fill(img: Image.Image, box, top, bottom, seed=0, density=0.5):
    """Gradiente con dithering ordenado de 2 colores (look pixel art)."""
    x0, y0, x1, y1 = [int(v) for v in box]
    rnd = random.Random(seed)
    h = max(1, y1 - y0)
    for y in range(y0, y1):
        t = (y - y0) / h
        thr = t
        for x in range(x0, x1):
            # bayer 4x4
            b = BAYER4[y % 4][x % 4] / 16.0
            c = bottom if t > b else top
            if c is not None:
                img.putpixel((x, y), tuple(c) + (255,))


BAYER4 = [
    [0, 8, 2, 10],
    [12, 4, 14, 6],
    [3, 11, 1, 9],
    [15, 7, 13, 5],
]


def gradient_v(w, h, top, bottom, dither=True, seed=0):
    img = Image.new("RGBA", (w, h))
    d = ImageDraw.Draw(img)
    for y in range(h):
        t = y / max(1, h - 1)
        c = [int(top[i] + (bottom[i] - top[i]) * t) for i in range(3)]
        d.line([(0, y), (w, y)], fill=tuple(c) + (255,))
    if dither:
        # banding suave
        rnd = random.Random(seed)
        px_img = img.load()
        for y in range(h):
            for x in range(w):
                if rnd.random() < 0.06:
                    r, g, b, a = px_img[x, y]
                    k = rnd.choice((-6, 6))
                    px_img[x, y] = (clamp(r + k), clamp(g + k), clamp(b + k), a)
    return img


def clamp(v):
    return max(0, min(255, int(v)))


def noise_layer(w, h, color, density, seed=0, alpha=255):
    img = new(w, h)
    rnd = random.Random(seed)
    for y in range(h):
        for x in range(w):
            if rnd.random() < density:
                a = alpha if rnd.random() > 0.4 else alpha // 2
                img.putpixel((x, y), tuple(color) + (a,))
    return img


def value_noise(w, h, scale, seed):
    """Ruido de valor simple bilineal, reutilizable para texturas."""
    rnd = random.Random(seed)
    gw = max(2, int(w / scale) + 2)
    gh = max(2, int(h / scale) + 2)
    grid = [[rnd.random() for _ in range(gw)] for _ in range(gh)]

    def sample(x, y):
        gx, gy = x / scale, y / scale
        x0, y0 = int(gx), int(gy)
        fx, fy = gx - x0, gy - y0
        fx = fx * fx * (3 - 2 * fx)
        fy = fy * fy * (3 - 2 * fy)
        a = grid[y0][x0]
        b = grid[y0][min(gw - 1, x0 + 1)]
        c = grid[min(gh - 1, y0 + 1)][x0]
        e = grid[min(gh - 1, y0 + 1)][min(gw - 1, x0 + 1)]
        return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + e * fx) * fy

    return [[sample(x, y) for x in range(w)] for y in range(h)]


def ragged_hem(x0, x1, y, amp=2.0, freq=0.55, phase=0.0, seed=0):
    """Borde inferior irregular para telas y carne."""
    pts = []
    rnd = random.Random(seed)
    for x in range(int(x0), int(x1) + 1):
        yy = y + math.sin((x - x0) * freq + phase) * amp + rnd.uniform(-0.6, 0.6)
        pts.append((x, yy))
    return pts


def save(img: Image.Image, path: str, scale: int = 1):
    if scale != 1:
        img = img.resize((img.width * scale, img.height * scale), Image.NEAREST)
    img.save(path)


def contact_sheet(images, cols, cell_w, cell_h, bg=(24, 20, 30), scale=3, pad=4):
    rows = (len(images) + cols - 1) // cols
    sheet = Image.new("RGBA", (cols * (cell_w + pad) + pad, rows * (cell_h + pad) + pad), tuple(bg) + (255,))
    for i, im in enumerate(images):
        cx = pad + (i % cols) * (cell_w + pad)
        cy = pad + (i // cols) * (cell_h + pad)
        sheet.alpha_composite(im, (cx, cy))
    return sheet.resize((sheet.width * scale, sheet.height * scale), Image.NEAREST)
