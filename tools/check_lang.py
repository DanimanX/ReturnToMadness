"""Comprueba que todas las claves usadas en el código existan en los 5 idiomas.

Detecta las llamadas literales (I18n.t("x")) y las familias dinámicas conocidas
(stage.%s.name, boss.%d, whisper.%d...). Falla con código 1 si algo falta.
"""
from __future__ import annotations

import glob
import json
import os
import re
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
LANGS = ["es", "en", "fr", "pt", "it"]

# familias que se construyen en tiempo de ejecución
FAMILIES = [
    "stage.{key}.name", "stage.{key}.subtitle", "stage.{key}.intro",
    "stage.{key}.revelation", "stage.{key}.frag.0", "stage.{key}.frag.1",
    "stage.{key}.frag.2",
]
STAGE_KEYS = ["costa", "criptas", "biblioteca", "meseta", "yuggoth", "rlyeh", "trono"]


def load(lang: str) -> dict:
    path = os.path.join(ROOT, "assets", "lang", "%s.json" % lang)
    with open(path, encoding="utf-8") as f:
        return json.load(f)["strings"]


def used_keys() -> set[str]:
    keys: set[str] = set()
    for path in glob.glob(os.path.join(ROOT, "scripts", "*.gd")):
        src = open(path, encoding="utf-8").read()
        keys.update(re.findall(r'I18n\.t\(\s*"([^"]+)"', src))
    for fam in FAMILIES:
        for k in STAGE_KEYS:
            keys.add(fam.format(key=k))
    for i in range(7):
        keys.add("boss.%d" % i)
    for i in range(12):
        keys.add("whisper.%d" % i)
    # las claves con formato se resuelven aparte
    return {k for k in keys if "%" not in k and "%d" not in k}


def main() -> int:
    tables = {lang: load(lang) for lang in LANGS}
    keys = sorted(used_keys())
    problems = 0
    for key in keys:
        missing = [lang for lang in LANGS if key not in tables[lang] or not tables[lang][key]]
        if missing:
            print("FALTA %-28s en %s" % (key, ", ".join(missing)))
            problems += 1
    # claves presentes pero sin usar (aviso, no error)
    all_keys = set(tables["es"])
    unused = sorted(all_keys - set(keys))
    print("\nclaves usadas: %d | en los JSON: %d" % (len(keys), len(all_keys)))
    if unused:
        print("sin usar: %s" % ", ".join(unused))
    if problems:
        print("\n%d claves incompletas" % problems)
        return 1
    # coherencia entre idiomas
    for lang in LANGS[1:]:
        if set(tables[lang]) != set(tables["es"]):
            diff = set(tables["es"]) ^ set(tables[lang])
            print("desajuste de claves en %s: %s" % (lang, sorted(diff)))
            return 1
    print("OK: las 5 lenguas tienen las mismas %d claves" % len(all_keys))
    return 0


if __name__ == "__main__":
    sys.exit(main())
