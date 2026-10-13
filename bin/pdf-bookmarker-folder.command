#!/usr/bin/env bash
# Doble-click para marcar los PDFs de una carpeta elegida en Finder.
# Flujo adaptativo por cada PDF:
#   1. extraer (si tiene marcadores) o extraer-de-indice (si no los tiene).
#   2. verificar (corrige páginas por contenido).
#   3. aprobar (marca verified:true en masa).
#   4. aplicar (con pypdf). Si falla por geometría, aplicar-forzado (pikepdf).
# Totalmente offline. Progreso en vivo.

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
OK_IDX=0
OK_PK=0
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

  # 1. extraer de marcadores previos
  if ! "$BIN" extraer "$pdf" --salida "$salida" >/dev/null 2>&1; then
    echo "   ✗ extraer falló"; FAIL=$((FAIL+1)); continue
  fi
  n=$(python3 -c "import json; d=json.load(open('$plan')); print(len(d.get('entries',[])))" 2>/dev/null)

  # 2. Si plan vacío, intentar desde ÍNDICE del libro
  if [ "$n" = "0" ] || [ -z "$n" ]; then
    echo "   ↻ sin marcadores previos, probando desde índice del libro…"
    if "$BIN" extraer-de-indice "$pdf" --salida "$salida" >/dev/null 2>&1; then
      n=$(python3 -c "import json; d=json.load(open('$plan')); print(len(d.get('entries',[])))" 2>/dev/null)
    fi
    if [ "$n" = "0" ] || [ -z "$n" ]; then
      echo "   ⊘ sin índice detectable (requiere revisión manual)"
      SKIP=$((SKIP+1)); continue
    fi
    echo "   ✓ extraído desde índice ($n entradas)"
    FROM_IDX=1
  else
    echo "   ✓ extraído de marcadores previos ($n)"
    FROM_IDX=0
  fi

  "$BIN" verificar "$pdf" "$plan" >/dev/null 2>&1 && echo "   ✓ páginas verificadas"
  "$BIN" aprobar   "$plan"       >/dev/null 2>&1 && echo "   ✓ aprobado para aplicar"

  # 3. aplicar con pypdf. Si falla, probar con pikepdf.
  if "$BIN" aplicar "$pdf" "$plan" >/dev/null 2>&1; then
    echo "   ✅ aplicado"
    OK=$((OK+1))
    [ "$FROM_IDX" = "1" ] && OK_IDX=$((OK_IDX+1))
  elif "$BIN" aplicar-forzado "$pdf" "$plan" >/dev/null 2>&1; then
    echo "   ✅ aplicado (modo forzado con pikepdf)"
    OK=$((OK+1))
    OK_PK=$((OK_PK+1))
    [ "$FROM_IDX" = "1" ] && OK_IDX=$((OK_IDX+1))
  else
    echo "   ✗ aplicar falló (pypdf y pikepdf)"
    FAIL=$((FAIL+1))
  fi
done

echo
echo "╔════════════════════════════════════════════════════════╗"
echo "║  RESUMEN: $OK aplicados · $SKIP omitidos · $FAIL fallidos (total $PDF_COUNT)"
if [ "$OK_IDX" -gt 0 ] || [ "$OK_PK" -gt 0 ]; then
  echo "║  De los aplicados: $OK_IDX reconstruidos desde índice · $OK_PK en modo forzado"
fi
echo "║  Respaldos: $TARGET/Respaldo de marcadores/"
echo "║  Planes:    $WORK (puede borrarlo cuando confirme)"
echo "╚════════════════════════════════════════════════════════╝"
echo
echo "Pulse Return para cerrar."
read -r
