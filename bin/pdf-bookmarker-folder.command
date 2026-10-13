#!/usr/bin/env bash
# Doble-click para marcar los PDFs de una carpeta elegida en Finder.
# Flujo por cada PDF: extraer → verificar → aplicar.
# Muestra progreso en vivo. Totalmente offline.

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

echo "╔════════════════════════════════════════════════════════╗"
echo "║  pdf-bookmarker — procesando $PDF_COUNT PDF(s)"
echo "║  Carpeta: $TARGET"
echo "╚════════════════════════════════════════════════════════╝"
echo

OK=0
FAIL=0
I=0
for pdf in "${PDFS[@]}"; do
  I=$((I+1))
  name=$(basename "$pdf")
  echo "────[$I/$PDF_COUNT]──────────────────────────────────────────"
  echo "📘 $name"
  salida="$WORK/$(basename "$pdf" .pdf)"
  if "$HOME/bin/pdf-bookmarker" extraer "$pdf" --salida "$salida" >/dev/null 2>&1; then
    echo "   ✓ extraído"
  else
    echo "   ✗ falló al extraer. Saltando."
    FAIL=$((FAIL+1)); continue
  fi
  if "$HOME/bin/pdf-bookmarker" verificar "$pdf" "$salida/plan_para_revisar.json" >/dev/null 2>&1; then
    echo "   ✓ páginas verificadas"
  fi
  if "$HOME/bin/pdf-bookmarker" aplicar "$pdf" "$salida/plan_para_revisar.json" 2>&1 | tail -1; then
    OK=$((OK+1))
  else
    FAIL=$((FAIL+1))
  fi
done

echo
echo "╔════════════════════════════════════════════════════════╗"
echo "║  RESUMEN: $OK aplicados, $FAIL fallidos de $PDF_COUNT"
echo "║  Respaldos en: $TARGET/Respaldo de marcadores/"
echo "║  Archivos de trabajo: $WORK (puede borrarlos)"
echo "╚════════════════════════════════════════════════════════╝"
echo
echo "Listo. Pulse Return para cerrar."
read -r
