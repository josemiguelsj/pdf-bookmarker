#!/usr/bin/env bash
# Doble-click para marcar los PDFs de una carpeta elegida en Finder.
# Flujo por cada PDF: extraer → verificar → aprobar → aplicar.
# Totalmente offline. Muestra progreso y resumen correcto.

TARGET=$(osascript -e 'POSIX path of (choose folder with prompt "Elija la carpeta con PDFs para añadir marcadores:")' 2>/dev/null)
if [ -z "$TARGET" ]; then
  echo "Cancelado"; exit 0
fi

TARGET="${TARGET%/}"
PDFS=("$TARGET"/*.pdf)
if [ ! -e "${PDFS[0]}" ]; then
  echo "Sin PDFs en: $TARGET"
  echo "Pulse Return para cerrar."
  read -r
  exit 0
fi

PDF_COUNT=${#PDFS[@]}
WORK="$TARGET/_pdf_bookmarker_tmp"
mkdir -p "$WORK"
BIN="$HOME/bin/pdf-bookmarker"

echo "╔════════════════════════════════════════════════════════╗"
echo "║  pdf-bookmarker — procesando $PDF_COUNT PDF(s)"
echo "║  Carpeta: $TARGET"
echo "╚════════════════════════════════════════════════════════╝"
echo "Al elegir esta carpeta usted autoriza la aplicación automática"
echo "de los marcadores verificados contra el texto del PDF."
echo

OK=0
SKIP=0
FAIL=0
I=0
for pdf in "${PDFS[@]}"; do
  I=$((I+1))
  name=$(basename "$pdf")
  salida="$WORK/$(basename "$pdf" .pdf)"
  plan="$salida/plan_para_revisar.json"
  echo "────[$I/$PDF_COUNT]──────────────────────────────────────────"
  echo "📘 $name"

  if ! "$BIN" extraer "$pdf" --salida "$salida" >/dev/null 2>&1; then
    echo "   ✗ extraer falló"; FAIL=$((FAIL+1)); continue
  fi

  # ¿Plan vacío? (PDF sin bookmarks previos)
  n=$(python3 -c "import json; d=json.load(open('$plan')); print(len(d.get('entries',[])))" 2>/dev/null)
  if [ "$n" = "0" ] || [ -z "$n" ]; then
    echo "   ⊘ sin marcadores previos (revisar manualmente)"
    SKIP=$((SKIP+1)); continue
  fi
  echo "   ✓ extraído ($n marcadores)"

  "$BIN" verificar "$pdf" "$plan" >/dev/null 2>&1 && echo "   ✓ páginas verificadas"
  "$BIN" aprobar "$plan" >/dev/null 2>&1 && echo "   ✓ aprobado para aplicar"

  if "$BIN" aplicar "$pdf" "$plan" >/dev/null 2>&1; then
    echo "   ✅ aplicado"
    OK=$((OK+1))
  else
    echo "   ✗ aplicar falló"
    FAIL=$((FAIL+1))
  fi
done

echo
echo "╔════════════════════════════════════════════════════════╗"
echo "║  RESUMEN: $OK aplicados · $SKIP omitidos · $FAIL fallidos (total $PDF_COUNT)"
echo "║  Respaldos: $TARGET/Respaldo de marcadores/"
echo "║  Planes:    $WORK (puede borrarlo cuando confirme)"
echo "╚════════════════════════════════════════════════════════╝"
echo
echo "Pulse Return para cerrar."
read -r
