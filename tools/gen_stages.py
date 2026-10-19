"""Genera data/stages.gd: las 7 etapas como mapas ASCII jugables.

Reglas de construcción:
  - 17 filas (270 px), 16 px por tile.
  - Salto del jugador: ~4 tiles de hueco, ~3 tiles de altura. Nunca más.
  - Cada etapa: entrada segura, arena, trampa, altar, tramo de riesgo,
    antecámara y arena de jefe con puerta.
  - Los marcadores se colocan en la fila libre sobre el suelo.
"""
from __future__ import annotations

import os
import random

ROWS = 17
T = 16

SOLID, PLAT, SPIKE, WATER = "#", "=", "^", "~"


class Stage:
    def __init__(self, width: int, ground: int):
        self.w = width
        self.rows = [["." for _ in range(width)] for _ in range(ROWS)]
        self.top = [ground] * width      # fila del primer sólido de cada columna
        self.gap = set()
        self.marks: list[tuple[int, int, str]] = []

    # ---------------------------------------------------------- terreno
    def solid_fill(self) -> None:
        for x in range(self.w):
            if x in self.gap:
                continue
            for y in range(self.top[x], ROWS):
                self.rows[y][x] = SOLID

    def set_top(self, x0: int, x1: int, h: int) -> None:
        for x in range(max(0, x0), min(self.w, x1)):
            self.top[x] = h

    def ramp(self, x0: int, x1: int, h0: int, h1: int) -> None:
        n = max(1, x1 - x0)
        for x in range(max(0, x0), min(self.w, x1)):
            t = (x - x0) / n
            self.top[x] = int(round(h0 + (h1 - h0) * t))

    def carve(self, x0: int, x1: int) -> None:
        for x in range(max(0, x0), min(self.w, x1)):
            self.gap.add(x)

    def platform(self, x0: int, x1: int, row: int) -> None:
        for x in range(max(0, x0), min(self.w, x1)):
            if self.rows[row][x] == ".":
                self.rows[row][x] = PLAT

    def spikes(self, x0: int, x1: int) -> None:
        for x in range(max(0, x0), min(self.w, x1)):
            if x in self.gap:
                continue
            r = self.top[x] - 1
            if r >= 0:
                self.rows[r][x] = SPIKE

    def water(self, x0: int, x1: int, depth_from: int = 13) -> None:
        for x in range(max(0, x0), min(self.w, x1)):
            for y in range(depth_from, ROWS):
                if self.rows[y][x] == ".":
                    self.rows[y][x] = WATER

    # ---------------------------------------------------------- objetos
    def put(self, x: int, row: int, ch: str) -> None:
        if 0 <= x < self.w and 0 <= row < ROWS and self.rows[row][x] == ".":
            self.rows[row][x] = ch

    def _valid_spot(self, x: int, dy: int, strict: bool, flat: bool) -> bool:
        if x in self.gap or not (1 <= x < self.w - 1):
            return False
        row = self.top[x] + dy
        if row < 0 or row >= ROWS or self.rows[row][x] != ".":
            return False
        if self.top[x] >= ROWS:
            return False
        if flat:
            if x - 1 in self.gap or x + 1 in self.gap:
                return False
            if not (self.top[x - 1] == self.top[x] == self.top[x + 1]):
                return False
        if strict:
            for dx in (-2, -1, 0, 1, 2):
                xx = x + dx
                if 0 <= xx < self.w and self.rows[row][xx] == SPIKE:
                    return False
                if 0 <= xx < self.w and self.rows[row + 1][xx] == SPIKE:
                    return False
        return True

    def on_ground(self, x: int, ch: str, dy: int = -1) -> int:
        """Coloca en el suelo; si el punto no sirve, busca uno cercano válido."""
        strict = ch in "At"
        flat = ch in "PABXbts"
        order = [0]
        for d in range(1, 10):
            order += [d, -d]
        for d in order:
            if self._valid_spot(x + d, dy, strict, flat):
                self.put(x + d, self.top[x + d] + dy, ch)
                return x + d
        return -1

    def ceiling_vines(self, x0: int, x1: int, ch: str = ":") -> None:
        for x in range(max(0, x0), min(self.w, x1)):
            if x % 7 == 0:
                self.put(x, 0, ch)

    # ---------------------------------------------------------- salida
    def audit_markers(self) -> list[str]:
        """Cada marcador debe apoyarse en suelo sólido y estar en una fila libre."""
        errors = []
        for yo, row in enumerate(self.rows):
            for x, ch in enumerate(row):
                if ch not in "PABXbts:T12345":
                    continue
                if yo + 1 >= ROWS:
                    errors.append(f"marcador {ch} en el borde inferior x={x}")
                    continue
                below = self.rows[yo + 1][x]
                if ch in "PABXbts" and below not in (SOLID, PLAT):
                    errors.append(f"marcador {ch} flotando en x={x}, y={yo} (abajo '{below}')")
                if ch in "1245T":
                    # 1,2,4 son terrestres; T sale del suelo. 3 y 5 vuelan.
                    if ch != "5" and below not in (SOLID, PLAT):
                        errors.append(f"enemigo {ch} flotando en x={x}, y={yo}")
                if ch in "35" and below in (SOLID, PLAT) and ch == "3":
                    pass
        # el altar no debe estar sobre pinchos
        for x in range(self.w):
            for yo in range(ROWS):
                if self.rows[yo][x] == "A":
                    for dx in (-1, 0, 1):
                        if 0 <= x + dx < self.w and self.rows[yo][x + dx] == SPIKE:
                            errors.append(f"altar junto a pinchos en x={x}")
        return errors

    def render(self) -> list[str]:
        return ["".join(r) for r in self.rows]

    def is_playable(self) -> list[str]:
        """Verifica que cada tramo sea saltable: hueco <=4 tiles, subida <=3.

        Una columna cuenta como apoyo si tiene suelo sólido o una plataforma.
        """
        errors = []
        support: list[int | None] = []
        for x in range(self.w):
            if x not in self.gap:
                support.append(self.top[x])
                continue
            row = None
            for y in range(ROWS):
                if self.rows[y][x] == PLAT:
                    row = y
                    break
            support.append(row)
        # recorre el recorrido jugable
        last_x = -1
        last_y = None
        for x in range(2, self.w - 2):
            sy = support[x]
            if sy is None:
                continue
            if last_x >= 0:
                dx = x - last_x
                if dx > 4:
                    errors.append(f"hueco de {dx} tiles en x={last_x}->{x}")
                if last_y is not None and last_y - sy > 3:
                    errors.append(f"subida de {last_y - sy} tiles en x={x}")
            last_x, last_y = x, sy
        return errors


# ------------------------------------------------------------------ utilidades
def flat(s: Stage, x0: int, x1: int, h: int, **_) -> None:
    s.set_top(x0, x1, h)


def gap(s: Stage, x0: int, x1: int, **_) -> None:
    s.carve(x0, x1)


def platforms(s: Stage, x0: int, x1: int, h: int, rows_down=(3, 5), **_) -> None:
    """Abismo cruzado por islotes de piedra al mismo nivel.

    Cada hueco mide 2 tiles y cada islote 3: margen de sobra para el salto.
    Las plataformas flotantes se añaden solo como decoración alcanzable.
    """
    x = x0
    while x < x1:
        pit_w = min(2, x1 - x)
        s.carve(x, x + pit_w)
        x += pit_w
        if x >= x1:
            break
        isl_w = min(3, x1 - x)
        s.set_top(x, x + isl_w, h)
        x += isl_w
    # plataformas decorativas dos filas por encima del borde (alcanzables)
    mid = (x0 + x1) // 2
    if x1 - x0 >= 7:
        s.platform(mid, mid + 2, h - 2)


def spikes_pit(s: Stage, x0: int, x1: int, h: int, **_) -> None:
    s.set_top(x0, x1, h + 1)
    s.spikes(x0 + 1, x1 - 1)


def water_pit(s: Stage, x0: int, x1: int, h: int, **_) -> None:
    s.set_top(x0, x1, h + 1)
    s.water(x0, x1, h + 1)


def stairs(s: Stage, x0: int, x1: int, h0: int, h1: int, **_) -> None:
    s.ramp(x0, x1, h0, h1)


def tunnel(s: Stage, x0: int, x1: int, h: int, **_) -> None:
    s.set_top(x0, x1, h)


SEGMENTS = {
    "flat": flat, "gap": gap, "platforms": platforms, "spikes": spikes_pit,
    "water": water_pit, "stairs": stairs, "tunnel": tunnel,
}


def carve_with_walk(s: Stage, segs: list, start_h: int) -> list[tuple[int, int, int, str]]:
    """Recorre segmentos y devuelve tramos jugables (x0, x1, altura, tipo)."""
    x = 2
    h = start_h
    spans = []
    for seg in segs:
        kind = seg[0]
        n = seg[1]
        if kind == "flat":
            h = seg[2] if len(seg) > 2 else h
            flat(s, x, x + n, h)
        elif kind == "gap":
            gap(s, x, x + n)
        elif kind == "platforms":
            platforms(s, x, x + n, h)
        elif kind == "spikes":
            spikes_pit(s, x, x + n, h)
            h = h + 1
        elif kind == "water":
            water_pit(s, x, x + n, h)
            h = h + 1
        elif kind == "stairs":
            h2 = seg[2]
            stairs(s, x, x + n, h, h2)
            h = h2
        elif kind == "tunnel":
            tunnel(s, x, x + n, h)
        spans.append((x, x + n, h, kind))
        x += n
    s.solid_fill()
    return spans


# ------------------------------------------------------------------ etapas
def stage_1():
    """La Costa Ahogada — tutorial: caminar, saltar, primer altar, primer jefe."""
    s = Stage(150, 13)
    segs = [
        ("flat", 16, 13), ("gap", 2), ("flat", 10, 13),
        ("platforms", 6), ("flat", 12, 13),
        ("spikes", 4), ("flat", 8, 13),
        ("stairs", 4, 12), ("flat", 10, 12),
        ("gap", 2), ("flat", 18, 12),
        ("spikes", 4), ("flat", 6, 12),
        ("gap", 2), ("flat", 14, 13),
        ("flat", 46, 13),
    ]
    carve_with_walk(s, segs, 13)
    # entrada
    s.on_ground(3, "P")
    s.on_ground(9, "t")
    s.on_ground(13, "1")
    s.on_ground(24, "1")
    s.on_ground(33, "b")       # primer fragmento, fácil de ver
    s.on_ground(39, "t")
    s.on_ground(48, "1")
    s.on_ground(52, "A")       # altar / checkpoint
    s.on_ground(58, "2")
    s.on_ground(68, "b")
    s.on_ground(74, "1")
    s.on_ground(80, "2")
    s.on_ground(88, "t")
    s.on_ground(94, "b")
    s.on_ground(100, "1")
    s.on_ground(106, "2")
    s.on_ground(112, "t")
    # arena del jefe
    s.on_ground(126, "s")
    s.on_ground(132, "B")
    s.on_ground(144, "X")
    s.ceiling_vines(0, 40)
    return s


def stage_2():
    """Las Criptas de Dagon — agua, techos bajos, tentáculos."""
    s = Stage(158, 13)
    segs = [
        ("flat", 12, 13), ("water", 4), ("flat", 8, 13),
        ("platforms", 7), ("flat", 9, 13),
        ("water", 5), ("flat", 7, 13),
        ("stairs", 4, 11), ("tunnel", 10, 11),
        ("gap", 2), ("flat", 10, 11),
        ("spikes", 5), ("flat", 8, 11),
        ("water", 4), ("flat", 12, 12),
        ("platforms", 6), ("flat", 10, 12),
        ("water", 5), ("flat", 16, 12),
        ("flat", 40, 12),
    ]
    carve_with_walk(s, segs, 13)
    s.on_ground(3, "P")
    s.on_ground(8, "t")
    s.on_ground(18, "1")
    s.on_ground(27, "3", dy=-3)
    s.on_ground(34, "b")
    s.on_ground(41, "1")
    s.on_ground(47, "T")
    s.on_ground(56, "A")
    s.on_ground(60, "2")
    s.on_ground(70, "T")
    s.on_ground(78, "1")
    s.on_ground(84, "b")
    s.on_ground(88, "3", dy=-4)
    s.on_ground(96, "2")
    s.on_ground(104, "T")
    s.on_ground(112, "b")
    s.on_ground(118, "1")
    s.on_ground(124, "t")
    s.on_ground(134, "s")
    s.on_ground(140, "B")
    s.on_ground(152, "X")
    s.ceiling_vines(20, 90)
    s.ceiling_vines(100, 140)
    return s


def stage_3():
    """El Ala Prohibida — verticalidad, plataformas, cultistas."""
    s = Stage(166, 13)
    segs = [
        ("flat", 14, 13), ("stairs", 4, 10), ("flat", 8, 10),
        ("gap", 2), ("flat", 8, 10), ("stairs", 3, 13),
        ("flat", 10, 13), ("platforms", 8), ("flat", 10, 13),
        ("stairs", 4, 9), ("flat", 6, 9), ("gap", 2), ("flat", 8, 9),
        ("stairs", 3, 12), ("flat", 9, 12),
        ("spikes", 4), ("flat", 9, 12),
        ("platforms", 7), ("flat", 12, 12),
        ("stairs", 4, 9), ("flat", 8, 9),
        ("gap", 2), ("flat", 12, 11),
        ("flat", 40, 11),
    ]
    carve_with_walk(s, segs, 13)
    s.on_ground(4, "P")
    s.on_ground(10, "t")
    s.on_ground(20, "2")
    s.on_ground(26, "b")
    s.on_ground(34, "2")
    s.on_ground(40, "1")
    s.on_ground(48, "t")
    s.on_ground(54, "2")
    s.on_ground(62, "b")
    s.on_ground(66, "3", dy=-4)
    s.on_ground(72, "A")
    s.on_ground(80, "2")
    s.on_ground(86, "b")
    s.on_ground(92, "1")
    s.on_ground(100, "2")
    s.on_ground(108, "3", dy=-4)
    s.on_ground(112, "b")
    s.on_ground(118, "2")
    s.on_ground(126, "t")
    s.on_ground(134, "s")
    s.on_ground(140, "B")
    s.on_ground(158, "X")
    s.ceiling_vines(0, 60)
    return s


def stage_4():
    """La Meseta de Leng — hielo resbaladizo, bestias, viento."""
    s = Stage(172, 13)
    segs = [
        ("flat", 12, 13), ("gap", 2), ("flat", 8, 13),
        ("spikes", 4), ("flat", 8, 13),
        ("platforms", 8), ("flat", 10, 13),
        ("stairs", 4, 10), ("flat", 8, 10), ("gap", 2), ("flat", 8, 10),
        ("stairs", 4, 13), ("flat", 10, 13),
        ("gap", 2), ("flat", 8, 13),
        ("spikes", 6), ("flat", 10, 13),
        ("platforms", 8), ("flat", 12, 12),
        ("stairs", 3, 9), ("flat", 10, 9),
        ("gap", 2), ("flat", 14, 12),
        ("flat", 42, 12),
    ]
    carve_with_walk(s, segs, 13)
    s.on_ground(3, "P")
    s.on_ground(8, "t")
    s.on_ground(18, "4")
    s.on_ground(26, "b")
    s.on_ground(34, "1")
    s.on_ground(42, "4")
    s.on_ground(50, "b")
    s.on_ground(56, "A")
    s.on_ground(64, "4")
    s.on_ground(70, "3", dy=-4)
    s.on_ground(76, "b")
    s.on_ground(84, "1")
    s.on_ground(92, "4")
    s.on_ground(100, "b")
    s.on_ground(108, "2")
    s.on_ground(116, "4")
    s.on_ground(124, "t")
    s.on_ground(132, "b")
    s.on_ground(140, "s")
    s.on_ground(146, "B")
    s.on_ground(164, "X")
    s.ceiling_vines(30, 100)
    return s


def stage_5():
    """El Abismo de Yuggoth — vuelo, proyectiles, caída."""
    s = Stage(178, 12)
    segs = [
        ("flat", 14, 12), ("platforms", 8), ("flat", 10, 12),
        ("water", 5), ("flat", 10, 12),
        ("platforms", 9), ("flat", 10, 12),
        ("gap", 2), ("flat", 8, 12),
        ("spikes", 6), ("flat", 10, 12),
        ("stairs", 4, 9), ("flat", 8, 9), ("gap", 2), ("flat", 10, 10),
        ("platforms", 8), ("flat", 12, 10),
        ("water", 5), ("flat", 12, 11),
        ("gap", 2), ("flat", 14, 12),
        ("flat", 44, 12),
    ]
    carve_with_walk(s, segs, 12)
    s.on_ground(3, "P")
    s.on_ground(8, "t")
    s.on_ground(20, "5", dy=-5)
    s.on_ground(28, "b")
    s.on_ground(36, "5", dy=-4)
    s.on_ground(44, "1")
    s.on_ground(52, "5", dy=-5)
    s.on_ground(58, "b")
    s.on_ground(66, "A")
    s.on_ground(72, "5", dy=-4)
    s.on_ground(80, "2")
    s.on_ground(88, "5", dy=-5)
    s.on_ground(94, "b")
    s.on_ground(102, "4")
    s.on_ground(110, "5", dy=-4)
    s.on_ground(118, "b")
    s.on_ground(126, "2")
    s.on_ground(134, "5", dy=-5)
    s.on_ground(142, "t")
    s.on_ground(150, "s")
    s.on_ground(156, "B")
    s.on_ground(170, "X")
    s.ceiling_vines(0, 70)
    return s


def stage_6():
    """El Sueño de R'lyeh — geometría rota, todo hostil."""
    s = Stage(182, 12)
    segs = [
        ("flat", 12, 12), ("gap", 2), ("flat", 8, 12),
        ("platforms", 9), ("flat", 10, 11),
        ("spikes", 5), ("flat", 9, 11),
        ("gap", 2), ("flat", 8, 11),
        ("water", 4), ("flat", 8, 11),
        ("platforms", 8), ("flat", 10, 11),
        ("stairs", 4, 9), ("flat", 8, 9), ("gap", 2), ("flat", 10, 10),
        ("spikes", 6), ("flat", 10, 10),
        ("gap", 2), ("flat", 10, 11),
        ("platforms", 8), ("flat", 14, 11),
        ("flat", 44, 12),
    ]
    carve_with_walk(s, segs, 12)
    s.on_ground(3, "P")
    s.on_ground(7, "t")
    s.on_ground(18, "3", dy=-4)
    s.on_ground(24, "b")
    s.on_ground(32, "1")
    s.on_ground(40, "4")
    s.on_ground(46, "T")
    s.on_ground(52, "b")
    s.on_ground(58, "A")
    s.on_ground(64, "3", dy=-4)
    s.on_ground(70, "5", dy=-5)
    s.on_ground(78, "b")
    s.on_ground(84, "4")
    s.on_ground(92, "T")
    s.on_ground(98, "2")
    s.on_ground(106, "3", dy=-4)
    s.on_ground(112, "b")
    s.on_ground(120, "5", dy=-5)
    s.on_ground(128, "4")
    s.on_ground(136, "T")
    s.on_ground(144, "b")
    s.on_ground(150, "t")
    s.on_ground(158, "s")
    s.on_ground(164, "B")
    s.on_ground(174, "X")
    s.ceiling_vines(0, 90)
    s.ceiling_vines(100, 160)
    return s


def stage_7():
    """El Trono del Durmiente — el descenso final."""
    s = Stage(190, 12)
    segs = [
        ("flat", 14, 12), ("gap", 2), ("flat", 9, 12),
        ("spikes", 6), ("flat", 9, 12),
        ("platforms", 9), ("flat", 10, 11),
        ("water", 5), ("flat", 9, 11),
        ("gap", 2), ("flat", 9, 11),
        ("stairs", 4, 8), ("flat", 8, 8), ("gap", 2), ("flat", 10, 10),
        ("spikes", 6), ("flat", 10, 10),
        ("platforms", 9), ("flat", 12, 10),
        ("water", 5), ("flat", 12, 11),
        ("gap", 2), ("flat", 12, 11),
        ("flat", 48, 12),
    ]
    carve_with_walk(s, segs, 12)
    s.on_ground(3, "P")
    s.on_ground(8, "t")
    s.on_ground(20, "1")
    s.on_ground(26, "4")
    s.on_ground(34, "b")
    s.on_ground(42, "5", dy=-5)
    s.on_ground(50, "T")
    s.on_ground(56, "b")
    s.on_ground(62, "A")
    s.on_ground(68, "4")
    s.on_ground(74, "2")
    s.on_ground(82, "T")
    s.on_ground(90, "b")
    s.on_ground(96, "5", dy=-5)
    s.on_ground(104, "4")
    s.on_ground(112, "3", dy=-4)
    s.on_ground(120, "b")
    s.on_ground(128, "T")
    s.on_ground(136, "2")
    s.on_ground(144, "4")
    s.on_ground(150, "b")
    s.on_ground(158, "t")
    s.on_ground(166, "s")
    s.on_ground(172, "B")
    s.on_ground(184, "X")
    s.ceiling_vines(0, 100)
    s.ceiling_vines(110, 170)
    return s


# El texto (nombres, intro, fragmentos, revelación) vive en assets/lang/*.json.
# Aquí solo queda la estructura: clave, material y mapa.
STAGES = [
    dict(key="costa", builder=stage_1, material="rock"),
    dict(key="criptas", builder=stage_2, material="brick"),
    dict(key="biblioteca", builder=stage_3, material="brick"),
    dict(key="meseta", builder=stage_4, material="ice"),
    dict(key="yuggoth", builder=stage_5, material="fungus"),
    dict(key="rlyeh", builder=stage_6, material="dream"),
    dict(key="trono", builder=stage_7, material="flesh"),
]


# ------------------------------------------------------------------ salida
def gd_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace('"', '\\"')


def emit(stages) -> str:
    out = []
    out.append('extends RefCounted')
    out.append('class_name StageData')
    out.append('')
    out.append('## Las siete etapas del descenso.')
    out.append('## Generado por tools/gen_stages.py — los mapas son editables a mano.')
    out.append('##')
    out.append('## Los textos NO están aquí: viven en assets/lang/{es,en,fr,pt,it}.json')
    out.append('## con las claves stage.<key>.name, .subtitle, .intro, .revelation y .frag.N')
    out.append('')
    out.append('const COUNT := %d' % len(stages))
    out.append('')
    out.append('const STAGES := [')
    for spec in stages:
        s = spec["builder"]()
        errors = s.is_playable() + s.audit_markers()
        if errors:
            raise SystemExit("etapa %s no jugable:\n  %s" % (spec["key"], "\n  ".join(errors)))
        rows = s.render()
        out.append('\t{')
        out.append('\t\t"key": "%s",' % spec["key"])
        out.append('\t\t"material": "%s",' % spec["material"])
        out.append('\t\t"map": [')
        for r in rows:
            out.append('\t\t\t"%s",' % r)
        out.append('\t\t],')
        out.append('\t},')
        print("etapa %d %-12s %3d x %d  sólidos=%d" %
              (stages.index(spec) + 1, spec["key"], len(rows[0]), len(rows),
               sum(r.count("#") for r in rows)))
    out.append(']')
    return "\n".join(out) + "\n"


def preview(stages, outdir):
    import sys
    sys.path.insert(0, os.path.dirname(__file__))
    from PIL import Image
    W = max(len(s["builder"]().render()[0]) for s in stages)
    img = Image.new("RGBA", (W * 4, ROWS * 4 * len(stages)), (10, 10, 14, 255))
    for i, spec in enumerate(stages):
        s = spec["builder"]()
        for y, row in enumerate(s.render()):
            for x, ch in enumerate(row):
                if ch == ".":
                    continue
                c = {
                    "#": (70, 74, 82), "=": (110, 96, 60), "^": (200, 70, 60),
                    "~": (40, 90, 110), "P": (255, 230, 120), "B": (255, 60, 60),
                    "X": (160, 220, 160), "A": (255, 180, 80), "b": (220, 200, 120),
                    "t": (255, 150, 60), "s": (120, 120, 140), ":": (60, 60, 60),
                    "T": (170, 60, 100),
                }.get(ch, (80, 200, 200) if ch.isdigit() else (150, 150, 150))
                img.putpixel((x * 4, i * ROWS * 4 + y * 4), c + (255,))
                img.putpixel((x * 4 + 1, i * ROWS * 4 + y * 4), c + (255,))
                img.putpixel((x * 4, i * ROWS * 4 + y * 4 + 1), c + (255,))
                img.putpixel((x * 4 + 1, i * ROWS * 4 + y * 4 + 1), c + (255,))
    img.save(os.path.join(outdir, "stages_preview.png"))
    print("preview:", img.size)


if __name__ == "__main__":
    root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
    src = emit(STAGES)
    path = os.path.join(root, "data", "stages.gd")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(src)
    print("escrito", path, len(src), "bytes")
    preview(STAGES, "/tmp")
