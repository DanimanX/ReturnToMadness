# REGRESO A LA LOCURA
### Un descenso en siete etapas al sueño de R'lyeh

> *"No fue la muerte lo que me reclamó, sino la certeza de que ya había estado aquí."*

---

## 1. Concepto

**Género:** acción-plataformas 2D lateral, pixel art, combate cuerpo a cuerpo con dash.
**Referencia de sensación:** *Blasphemous* (peso, penitencia, iconografía brutal) atravesada por el
cosmos de **H. P. Lovecraft** (insignificancia, revelación, locura como precio del conocimiento).
**Duración:** 7 etapas, ~20–40 minutos por partida.

La diferencia central con *Blasphemous*: aquí la penitencia no es la culpa, es el **conocimiento**.
Cada vez que el Testigo avanza, ve un poco más de la verdad. Y la verdad lo deshace.

---

## 2. Premisa

Eres **el Testigo**, último acólito de la **Orden del Ojo Abierto**. La Orden no adoraba a
Cthulhu: lo *vigilaba*. Siete sellos mantenían dormido al que sueña bajo el Pacífico. Alguien
los ha ido rompiendo, uno por uno, desde dentro.

Desciendes por las siete capas del sueño para volver a cerrarlos. Cada capa que atraviesas te
arranca un trozo de cordura. Al final del descenso descubres lo que la Orden nunca se atrevió a
escribir: el séptimo sello no lo rompió un traidor. Lo rompiste tú, en otra vuelta, y has estado
descendiendo la misma escalera durante siglos.

**El juego es un bucle.** Al vencer al último sello, la locura llega a 7/7 y la partida reinicia
en la etapa 1 con el mundo ya deformado (modo *REGRESO*), conservando la locura.

---

## 3. Las siete etapas

| # | Etapa | Lugar | Paleta | Guardián | Revelación |
|---|-------|-------|--------|----------|------------|
| 1 | La Costa Ahogada | Innsmouth, muelles bajo la lluvia | pizarra azul, farol enfermo | **El Sacerdote Ahogado** | "Los peces llevaban rostros. Yo no quise mirar." |
| 2 | Las Criptas de Dagon | catacumbas inundadas | verde profundo, cian bioluminiscente | **La Madre de Branquias** | "Dagon no es un dios. Es una etapa." |
| 3 | El Ala Prohibida | Biblioteca Miskatonic, Arkham | ámbar, sepia, polvo | **El Bibliotecario** | "El libro me leía a mí." |
| 4 | La Meseta de Leng | meseta helada, luna de Kadath | azul frío, violeta | **El Cazador de la Luna** | "No había cima. Solo un ojo." |
| 5 | El Abismo de Yuggoth | ciudad-máquina fúngica | magenta, verde ácido | **El Ingeniero Mi-Go** | "Mi cerebro estaba en un tarro y aun así sentía miedo." |
| 6 | El Sueño de R'lyeh | ciudad no euclidiana | verde-negro, oro | **El Yo Que No Fui** | "Me reconocí en el espejo. Él no." |
| 7 | El Trono del Durmiente | R'lyeh, la cámara del sueño | rojo, negro, verde abisal | **Cthulhu** | "Yo soy el séptimo sello." |

Cada etapa: 1 fragmento de lore al inicio, 2–3 fragmentos opcionales, un guardián al final,
y un texto de revelación al cruzar la puerta.

---

## 4. Sistema de Locura (el corazón del juego)

Hay **dos medidores** y no son lo mismo.

### Cordura (por etapa, 0–100)
Baja al recibir daño, al permanecer en la oscuridad y al estar cerca de horrores.
Si llega a 0: la pantalla se abre, el Testigo grita y **pierde un cirio** (vida).
Se recupera en los **altares** (que además son puntos de guardado) y al matar seres menores.

### Locura (permanente, 0–7)
Sube **una marea por etapa completada** y un poco por cada muerte. Nunca baja.
Es a la vez una maldición y una ventaja:

- **Daño infligido:** ×(1 + 0.13 · Locura) — ves las grietas del mundo y sabes dónde golpear.
- **Daño recibido:** ×(1 + 0.09 · Locura) — el mundo te conoce.
- **Los enemigos te detectan antes** y aparecen horrores que no existen.

### Efectos visuales por marea

| Marea | Nombre | Lo que cambia |
|-------|--------|----------------|
| 0 | Testigo | nada |
| 1 | Primer susurro | viñeta, susurros esporádicos |
| 2 | Grieta | aberración cromática leve, sombras que se mueven |
| 3 | Voz | onda de pantalla, enemigos fantasma, HUD que tiembla |
| 4 | Vórtice | balanceo de cámara, *drift* de control, ojos en el fondo |
| 5 | Coro | duplicación de siluetas, texto que habla al jugador |
| 6 | Durmiente | el ojo de Cthulhu sigue al jugador, todo respira |
| 7 | Regreso | el juego se reinicia con el mundo deformado |

---

## 5. Combate

- **Filo de cirio** (ataque): combo de 3 golpes, alcance corto, pegada pesada.
- **Dash**: breve, con invulnerabilidad; atraviesa proyectiles.
- **La Voz** (Insight): grito que aturde y empuja en área, cuesta 18 de cordura.
  A mayor Locura, más potente y más barato: la locura te enseña a gritar.
- **Parada**: mantener el ataque en el aire frenando la caída (golpe descendente con rebote).
- **Ejecución**: enemigo aturdido + interactuar = recupera cordura (y sube Locura un punto).

---

## 6. Identidad visual

Pixel art a **480×270**, escalado entero a 1440×810.
Silueta negra + luz de borde cálida. Nada de contornos suaves: formas duras, dientes, telas.
El Testigo es una capucha picuda, un farol y una espada que parece una vela derretida.

Post-proceso de pantalla único, parametrizado por Locura:
aberración cromática, onda, viñeta, grano, líneas de escaneo, tinte de sangre y un
pulso de "respiración" en los bordes. A marea 6 el propio HUD se corrompe.

---

## 7. Idiomas

Cinco lenguas: español, inglés, francés, portugués e italiano. Se eligen con **← →** en el
título o en la pausa y se recuerdan entre partidas (`user://settings.cfg`).

Reglas de traducción:
- El tono es el mismo en las cinco: frases cortas, literarias, sin épica de videojuego.
- Lo que se traduce es **todo** el texto del juego, incluidos los susurros de la locura.
- Los nombres propios de Lovecraft no se traducen (Innsmouth, Miskatonic, R'lyeh, Cthulhu).
- Si a una lengua le falta una cadena, `tools/gen_lang.py` falla y no escribe nada.

## 8. Estructura técnica

```
project.godot          autoloads: GameState, AudioDirector
data/stages.gd         las 7 etapas como mapas ASCII + lore
scripts/               lógica (jugador, enemigos, jefes, nivel, HUD, FX)
scenes/                main.tscn y raíces de escena
shaders/madness.gdshader   post-proceso de locura
assets/                sprites, tiles, fondos, ui, audio (generados)
tools/                 generadores de arte y audio
```

Los niveles se escriben como **mapas ASCII** en `data/stages.gd`: una etapa es texto, no un
archivo de 4000 nodos. Eso permite editar el juego con un editor de texto y mantiene el
proyecto legible.
