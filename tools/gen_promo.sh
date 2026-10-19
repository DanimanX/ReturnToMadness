#!/usr/bin/env bash
# Graba y monta el video promocional.
#   bash tools/gen_promo.sh
# Requisitos: Godot 4.7 (GODOT=/ruta/al/binario), ffmpeg, python3.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
GODOT="${GODOT:-/tmp/godot/Godot_v4.7.2-stable_linux.x86_64}"
WORK="${WORK:-/tmp/promo}"
OUT="$ROOT/promo/regreso-a-la-locura-promo.mp4"

mkdir -p "$WORK/frames" "$(dirname "$OUT")"
rm -f "$WORK"/frames/*.png "$WORK"/beat_*.log

# --- 1. grabar a resolución nativa (480x270), sin pérdidas -------------------
cp "$ROOT/project.godot" "$WORK/project.godot.bak"
trap 'cp "$WORK/project.godot.bak" "$ROOT/project.godot"' EXIT
sed -i -E 's|^(window/size/window_width_override)=.*|\1=0|;
           s|^(window/size/window_height_override)=.*|\1=0|' "$ROOT/project.godot"

"$GODOT" --path "$ROOT" --write-movie "$WORK/frames/f.png" --fixed-fps 30 \
         -- --smoke --promo 2>&1 | tee "$WORK/beat_times.log" | grep -E "promo|frames" || true

cp "$WORK/project.godot.bak" "$ROOT/project.godot"
trap - EXIT

# --- 2. banda sonora alineada a los cortes -----------------------------------
python3 "$ROOT/tools/gen_promo_audio.py" "$WORK/beat_times.log" "$WORK/soundtrack.wav"

# --- 3. montaje: 4x nearest, H.264, audio --------------------------------
ffmpeg -y -v error -framerate 30 -start_number 0 -i "$WORK/frames/f%08d.png" \
       -i "$WORK/soundtrack.wav" \
       -vf "scale=1920:1080:flags=neighbor,format=yuv420p" \
       -c:v libx264 -preset slow -crf 20 -tune animation \
       -c:a aac -b:a 192k -shortest -movflags +faststart \
       "$OUT"

echo "video: $OUT"
ffprobe -v error -show_entries format=duration,size -of default=nw=1 "$OUT"
