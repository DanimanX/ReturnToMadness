# REGRESO A LA LOCURA

**Action-platformer de horror cósmico en pixel art · Godot 4 · 7 etapas**
**por DanimanX**

[![Build](https://github.com/DanimanX/ReturnToMadness/actions/workflows/build.yml/badge.svg)](https://github.com/DanimanX/ReturnToMadness/actions/workflows/build.yml)
[![Idiomas](https://img.shields.io/badge/idiomas-ES%20%C2%B7%20EN%20%C2%B7%20FR%20%C2%B7%20PT%20%C2%B7%20IT-8a6bbf)]()

[![Video promocional](promo/poster.png)](promo/regreso-a-la-locura-promo.mp4)

▶ **[Ver el video promocional](promo/regreso-a-la-locura-promo.mp4)** (51 s, 1080p)

Descarga los binarios desde [Releases](https://github.com/DanimanX/ReturnToMadness/releases):
Linux, Windows, macOS y Web.

> *"No fue la muerte lo que me reclamó, sino la certeza de que ya había estado aquí."*

Eres **el Testigo**, último acólito de la Orden del Ojo Abierto, y desciendes por las siete
capas del sueño de Cthulhu para volver a cerrar los sellos que alguien está abriendo desde
dentro. Cada capa que cruzas te arranca un trozo de cordura, y la locura que acumulas
**no se cura nunca**: te hace pegar más fuerte, te hace ver horrores que no existen y, al
final, te devuelve al principio.

**Duración:** ~20–40 minutos por partida · **Guardado:** en los altares.

---

## Cómo jugar

```bash
# 1. Abrir el proyecto en Godot 4.7+
godot --path . --editor

# 2. O jugar directamente
godot --path .
```

Binarios ya compilados (GitHub Actions los genera para las cuatro plataformas):
[Releases](https://github.com/DanimanX/ReturnToMadness/releases).

En Linux con el binario descargado:

```bash
./Godot_v4.7.2-stable_linux.x86_64 --path /ruta/a/ReturnToMadness
```

| Tecla | Acción |
|-------|--------|
| `A` / `D` o flechas | Moverse |
| `Espacio` | Saltar (mantener = salto más alto) |
| `J` o clic izquierdo | Golpear — combo de 3 |
| `K` | Esquivar (invulnerable, atraviesa proyectiles) |
| `L` | **La Voz**: grito que aturde y empuja, cuesta cordura |
| `E` | Interactuar |
| `Esc` | Pausa / controles |
| `Enter` | Confirmar |

También funciona con mando (stick izquierdo, `A` saltar, `X` golpear, `B` esquivar, `Y` La Voz).

---

## Idiomas

El juego está en **cinco idiomas**: español, inglés, francés, portugués e italiano.

En la pantalla de título o en la pausa, cambia con **← →**. La elección se guarda en
`user://settings.cfg` y se mantiene entre partidas. Al arrancar por primera vez se intenta
usar el idioma del sistema.

Se traduce **todo**: títulos de etapa, intros, fragmentos de lore, revelaciones, nombres de
los guardianes, susurros de la locura, HUD, menús y el final.

Los textos viven en `assets/lang/{es,en,fr,pt,it}.json` y se generan desde
`tools/gen_lang.py`, que falla si a alguna lengua le falta una cadena.

---

## Video promocional

El video se genera desde el propio juego, no se edita a mano:

```bash
bash tools/gen_promo.sh
```

1. Godot graba la partida a resolución nativa (480×270, sin pérdidas) con `--write-movie`.
2. `tools/gen_promo_audio.py` alinea la banda sonora a los cortes reales del montaje.
3. `ffmpeg` escala ×4 con vecino más cercano y codifica H.264 a 1080p.

Resultado: `promo/regreso-a-la-locura-promo.mp4`.

---

## Las dos barras

**Cordura** (0–100, por etapa) baja al recibir daño, al estar cerca de horrores y en la
oscuridad. Si llega a cero, el Testigo grita, pierde un cirio y la locura sube. Se recupera
en los **altares** (que son puntos de guardado) y al matar.

**Locura** (0–7, permanente) sube al avanzar, al matar y al morir. Nunca baja:

- daño que infliges: **×(1 + 0.13 · locura)**
- daño que recibes: **×(1 + 0.09 · locura)**
- los enemigos te detectan antes y aparecen espectros que no existen

| Marea | Nombre | Qué cambia |
|-------|--------|-----------|
| 0 | Testigo | nada |
| 1 | Primer susurro | viñeta, susurros |
| 2 | Grieta | aberración cromática, alucinaciones |
| 3 | Voz | onda de pantalla, HUD que tiembla |
| 4 | Vórtice | *drift* de control, ojos en el fondo |
| 5 | Coro | siluetas duplicadas, susurros constantes |
| 6 | Durmiente | todo respira, el ojo te sigue |
| 7 | Regreso | el juego se reinicia con el mundo deformado |

---

## Las siete etapas

1. **La Costa Ahogada** — Innsmouth bajo la lluvia · *El Sacerdote Ahogado*
2. **Las Criptas de Dagon** — catacumbas inundadas · *La Madre de Branquias*
3. **El Ala Prohibida** — Biblioteca Miskatonic · *El Bibliotecario*
4. **La Meseta de Leng** — hielo y luna de Kadath · *El Cazador de la Luna*
5. **El Abismo de Yuggoth** — ciudad-máquina fúngica · *El Ingeniero Mi-Go*
6. **El Sueño de R'lyeh** — geometría imposible · *El Yo Que No Fui*
7. **El Trono del Durmiente** — la cámara del sueño · *Cthulhu*

Cada etapa tiene un altar (guardado), fragmentos de lore opcionales y un guardián de tres
fases al final. Detrás de la puerta, una revelación.

---

## Estructura del proyecto

```
project.godot              autoloads: GameState, AudioDirector
scenes/main.tscn           única escena raíz; todo lo demás se construye en código
data/stages.gd             las 7 etapas como mapas ASCII + lore (generado, editable)
scripts/
  main.gd                  flujo: título, etapas, muerte, revelación, bucle
  game_state.gd            locura, cordura, cirios, guardado
  level.gd                 parsea el mapa, autotile, colisión, props, entidades
  player.gd                movimiento, combo, esquiva, La Voz
  enemy.gd                 cinco criaturas con comportamiento propio
  boss.gd                  siete guardianes, tres fases, patrones
  tentacle.gd              tentáculo que brota y se retira
  hud.gd                   cirios, cordura, locura, barra de jefe, susurros
  madness_fx.gd            post-proceso y alucinaciones
  pixel_font.gd            tipografía 5x7 dibujada desde atlas
  smoke.gd / bot.gd        arnés de verificación (ver abajo)
shaders/madness.gdshader   aberración, onda, viñeta, grano, escaneo, tinte
assets/                    sprites, tiles, fondos, ui, audio (todo generado)
tools/                     generadores de arte, audio y niveles
```

### Los niveles son texto

Una etapa es un mapa ASCII de 17 filas en `data/stages.gd`:

```
"...................",   .  vacío        P  inicio        A  altar (guardado)
"..###.......###....",   #  sólido       X  puerta        b  fragmento de lore
"..###..^....###....",   =  plataforma   B  jefe          t  antorcha
"#########..########",   ^  pinchos      s  estatua       :  cadena
                         ~  agua         1 ahogado  2 cultista  3 pólipo
                                        4 bestia   5 Mi-Go    T tentáculo
```

Reglas que respeta el generador: ningún salto supera 4 tiles horizontales ni 3 de altura.

---

## Generar el arte, el audio y los niveles

Todo el contenido es procedural y reproducible:

```bash
python3 tools/gen_player.py     # el Testigo: 28 frames
python3 tools/gen_enemies.py    # 5 criaturas + 7 jefes + espectro
python3 tools/gen_world.py      # 6 atlas de tiles + props
python3 tools/gen_bg.py         # 7 etapas × 2 capas de parallax
python3 tools/gen_ui.py         # tipografía, cirios, ojo, logo
python3 tools/gen_audio.py      # 7 ambientes, música de jefe, 12 efectos
python3 tools/gen_stages.py     # los 7 mapas ASCII + validación
```

`gen_stages.py` **valida** cada etapa: si un salto es imposible o un marcador flota, falla y
no escribe el archivo.

---

## Verificación

El proyecto incluye un arnés que juega solo. No es una demo: es el test de regresión.

```bash
# capturas guiadas en /tmp/shots (título, etapa 1, locura 6, biblioteca, Cthulhu)
godot --path . -- --smoke

# ¿se puede recorrer la etapa N de principio a fin? (bot que salta, pega y esquiva)
godot --headless --path . -- --smoke --traverse --invuln --stage=1

# ¿el jefe muere y la puerta cierra la etapa? (duelo + ciclo completo)
godot --headless --path . -- --smoke --bosstest --stage=1
```

Resultados medidos en esta máquina (Godot 4.7.2, Linux, sin GPU dedicada):

- **Geometría**: las 7 etapas se recorren de principio a fin sin quedarse atascado.
  Tiempos del bot: 22 s, 27 s, 33 s, 32 s, 66 s, 38 s, 36 s (a ×2.5 de velocidad).
- **Combate**: los 7 guardianes mueren y la puerta completa la etapa, subiendo la locura
  de 0.8 a 7.0 a lo largo de la partida.
- **Estructura**: `gen_stages.py` valida saltos y apoyos antes de escribir `data/stages.gd`.

El modo `--invuln` existe porque el bot no es una IA de combate: sirve para medir
geometría sin que las peleas contaminen el resultado.

---

## Créditos

**Un juego de DanimanX.**

Código, arte y audio generados para este proyecto. El universo de Cthulhu es de
**H. P. Lovecraft** y es de dominio público; los nombres propios se usan como homenaje.
Inspirado en la sensación de *Blasphemous* (The Game Kitchen).

Sin licencia declarada: todos los derechos reservados por el autor. Si quieres que sea
software libre, añade un `LICENSE` (MIT, GPL-3.0 o CC-BY para el arte) — es la única
decisión de publicación que queda abierta.
