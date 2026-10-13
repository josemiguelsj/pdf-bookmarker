# pdf-bookmarker

Corrige marcadores (bookmarks) de PDFs. Flujo offline en cuatro pasos: extraer → verificar → comprobar → aplicar. El contenido real del texto manda, nunca cálculos con offsets.

## Instalación

```bash
git clone https://github.com/josemiguelsj/pdf-bookmarker.git ~/.local/share/pdf-bookmarker
cd ~/.local/share/pdf-bookmarker
./install.sh
```

Dependencias:

```bash
python3 -m pip install pypdf
brew install poppler        # pdftotext, pdftoppm
```

Añadir al `~/.zshrc` si no está:

```bash
export PATH="$HOME/bin:$PATH"
```

## Uso

```bash
pdf-bookmarker extraer   "libro.pdf" --salida "Revision libro"
pdf-bookmarker verificar "libro.pdf" "Revision libro/plan_para_revisar.json"
# (opcional: editar plan manualmente)
pdf-bookmarker aplicar   "libro.pdf" "Revision libro/plan_para_revisar.json"
```

También por doble click en Finder: abrir `~/bin/pdf-bookmarker-folder.command`.

## Estructura

- `corregir_marcadores.py` motor de extraer/comprobar/aplicar (código base de ChatGPT, intacto).
- `verificar_paginas.py` busca cada entrada numerada del plan en el texto y corrige su página.
- `bin/pdf-bookmarker` launcher con subcomandos.
- `bin/pdf-bookmarker-folder.command` doble click para carpetas (macOS).
- `agent/pdf-bookmarker.md` subagente para Claude Code.
- `planes_verificados/` planes JSON de libros ya revisados, atados por SHA256.
- `LEAME.md` manual original.

## Regla de oro

Cada entrada del plan apunta a la página PDF donde el título aparece como encabezado real en el texto. Si no aparece como encabezado visible, apunta a la misma página que su hermano previo del índice. Nunca se calculan páginas con offsets ni se asume correspondencia constante libro↔PDF.

## Licencia

MIT. El motor `corregir_marcadores.py` es obra de ChatGPT, reutilizado con atribución.
