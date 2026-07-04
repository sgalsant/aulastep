#!/usr/bin/env bash
# Genera la skill 'aulastep-authoring' como artefacto del repositorio:
# SKILL.md + referencias (copiadas de docs/) + wheel autocontenido.
set -euo pipefail
cd "$(dirname "$0")/.."

OUT="${1:-dist/aulastep-authoring.skill}"
STAGE="$(mktemp -d)/aulastep-authoring"

uv build --wheel >/dev/null
mkdir -p "$STAGE/assets" "$STAGE/references"
cp skill/aulastep-authoring/SKILL.md "$STAGE/"
# Las referencias se toman SIEMPRE de docs/ (única fuente de verdad).
cp docs/formato-actividad.md "$STAGE/references/formato.md"
cp docs/directivas.md "$STAGE/references/directivas.md"
cp dist/aulastep-*.whl "$STAGE/assets/"

mkdir -p "$(dirname "$OUT")"
rm -f "$OUT"
(cd "$(dirname "$STAGE")" && zip -rq - "$(basename "$STAGE")") > "$OUT"
echo "Skill generada en $OUT"
unzip -l "$OUT"
