#!/usr/bin/env bash
set -e
TARGET=$(osascript -e 'POSIX path of (choose folder with prompt "Elija la carpeta de PDF. Se prepararán planes para revisión:")' 2>/dev/null) || exit 0
"$HOME/bin/pdf-bookmarker" carpeta "$TARGET"
echo 'Los originales se conservan. Consulte los planes preparados.'
read -r
