#!/usr/bin/env bash
# Instala pdf-bookmarker en el sistema (enlaces simbólicos).
set -e
REPO="$(cd "$(dirname "$0")" && pwd)"
mkdir -p ~/bin ~/.claude/agents
ln -sf "$REPO/bin/pdf-bookmarker" ~/bin/pdf-bookmarker
ln -sf "$REPO/bin/pdf-bookmarker-folder.command" ~/bin/pdf-bookmarker-folder.command
ln -sf "$REPO/agent/pdf-bookmarker.md" ~/.claude/agents/pdf-bookmarker.md
chmod +x "$REPO/bin/pdf-bookmarker" "$REPO/bin/pdf-bookmarker-folder.command"
chmod +x "$REPO/corregir_marcadores.py" "$REPO/verificar_paginas.py"
echo "Instalación completada:"
echo "  Launcher:    ~/bin/pdf-bookmarker"
echo "  Doble click: ~/bin/pdf-bookmarker-folder.command"
echo "  Agente:      ~/.claude/agents/pdf-bookmarker.md"
echo "Añade a tu PATH: export PATH=\"\$HOME/bin:\$PATH\" en ~/.zshrc"
