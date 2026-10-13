#!/usr/bin/env bash
# Doble-click para marcar todos los PDFs de una carpeta que elija en Finder.
# Totalmente offline. Usa pdf-bookmarker.

TARGET=$(osascript -e 'POSIX path of (choose folder with prompt "Elija la carpeta con PDFs para añadir bookmarks:")' 2>/dev/null)
if [ -z "$TARGET" ]; then
  echo "Cancelado"; exit 0
fi

echo "Procesando: $TARGET"
echo "────────────────────────────────────────────────────────"
"$HOME/bin/pdf-bookmarker" --batch "$TARGET" --log
echo "────────────────────────────────────────────────────────"
echo
echo "Listo. Pulse Return para cerrar."
read -r
