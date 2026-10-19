#!/usr/bin/env bash
# Exporta el build web y lo empaqueta listo para usar.
#   bash tools/gen_web_bundle.sh
# Resultado: build/regreso-a-la-locura-web.zip
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
GODOT="${GODOT:-godot}"
OUT_DIR="$ROOT/build/web"
ZIP="$ROOT/build/regreso-a-la-locura-web.zip"

rm -rf "$OUT_DIR"
mkdir -p "$OUT_DIR" "$(dirname "$ZIP")"

echo "== exportando"
"$GODOT" --headless --path "$ROOT" --import >/dev/null 2>&1 || true
"$GODOT" --headless --path "$ROOT" --export-release "Web" "$OUT_DIR/index.html"

for f in index.html index.js index.wasm index.pck; do
  test -s "$OUT_DIR/$f" || { echo "falta $f en la exportación"; exit 1; }
done

# arranque en un clic, instrucciones y notas
cp "$ROOT/web/serve.py" "$OUT_DIR/serve.py"
cp "$ROOT/web/START-HERE.txt" "$OUT_DIR/START-HERE.txt"
chmod +x "$OUT_DIR/serve.py"

# 404 para que un servidor estático no muestre su propia página de error
cat > "$OUT_DIR/404.html" <<'HTML'
<!doctype html><meta charset="utf-8"><title>404</title>
<body style="background:#0b0a0f;color:#cfc8b4;font-family:monospace;padding:2rem">
<p>404 — no encontrado / not found</p>
<p><a style="color:#e2af5c" href="./">volver al juego / back to the game</a></p>
</body>
HTML

echo "== midiendo"
python3 - "$OUT_DIR" <<'PY'
import os, sys
d = sys.argv[1]
total = sum(os.path.getsize(os.path.join(d, f)) for f in os.listdir(d))
print("   %.1f MB en %d archivos" % (total / 1048576, len(os.listdir(d))))
PY

echo "== comprimiendo"
rm -f "$ZIP"
(cd "$OUT_DIR" && zip -q -9 -r "$ZIP" .)
echo "listo: $ZIP ($(du -h "$ZIP" | cut -f1))"
