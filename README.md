# pdf-bookmarker

Revisa marcadores de PDF con herramientas locales. Los programas no llaman a modelos ni consumen tokens de una API. El agente de Claude sí consume tokens cuando interviene.

El proceso conserva una copia del original, comprueba las páginas y sus recursos, verifica los marcadores escritos y reemplaza el PDF solo cuando las comprobaciones pasan. El motor alternativo aplica las mismas comprobaciones.

## Uso

Para elegir un PDF o una carpeta mediante un diálogo de macOS:

```bash
~/bin/pdf-bookmarker trabajar
```

El selector prepara los planes. Añada `--aplicar` para guardar solo planes completamente verificados.

```bash
pdf-bookmarker extraer "libro.pdf" --salida "Revision libro"
pdf-bookmarker verificar "libro.pdf" "Revision libro/plan_para_revisar.json"
pdf-bookmarker comprobar "libro.pdf" "Revision libro/plan_para_revisar.json"
pdf-bookmarker aplicar "libro.pdf" "Revision libro/plan_para_revisar.json" --verificar-imagenes destinos
```

Si faltan marcadores, genere el plan desde el índice impreso:

```bash
pdf-bookmarker extraer-de-indice "libro.pdf" --salida "Revision libro"
```

El índice general tiene su propia página física. Las entradas extraídas conservan el número impreso en `printed_page`. Su destino queda pendiente hasta encontrar un encabezado o registrar una revisión. El programa no trata los números impresos como páginas físicas.

`verificar` busca títulos completos en todo el libro, incluidos encabezados que ocupan varias líneas. Verifica automáticamente una coincidencia única. Si aparecen varias coincidencias o ninguna, deja la entrada pendiente. No cambia destinos para imponer un orden creciente. El índice puede aparecer antes de capítulos situados en páginas anteriores.

La búsqueda exacta no reconstruye OCR defectuoso ni resuelve toda jerarquía editorial. En esos casos hace falta revisar el índice y las páginas candidatas. El programa registra los pendientes en `informe_verificacion.json`.

## Correcciones y memoria

Registre una corrección después de comprobarla contra el libro:

```bash
pdf-bookmarker aprender "libro.pdf" "Revision libro/plan_para_revisar.json" \
  --entrada 7 --pagina 82 --evidencia "El encabezado de la carta comienza en la página física 82"
```

`--entrada` es la posición del marcador en el plan, desde 1. La memoria guarda el título, su contexto, la evidencia y la huella del PDF. Se conserva en `~/.local/share/pdf-bookmarker/memoria.json`. Cada aplicación correcta transfiere las revisiones al PDF resultante, cuyas páginas ya se comprobaron. Así se pueden reutilizar en una ejecución posterior.

Las correcciones de un libro no se trasladan automáticamente a otra edición. Una página correcta en un ejemplar puede ser incorrecta en otro. La memoria conserva revisiones comprobadas. No entrena un modelo ni modifica el código por su cuenta.

La extracción de texto se guarda en `~/.cache/pdf-bookmarker`, identificada por la huella del PDF. Puede borrar esa carpeta. El programa volverá a extraer el texto. Para cambiar estas rutas, defina `PDF_BOOKMARKER_MEMORY` y `PDF_BOOKMARKER_CACHE`.

Los 12 planes de `planes_verificados` se conservan como ejemplos y registros de revisión. Están vinculados a sus PDF originales. La extracción los recupera cuando coinciden exactamente la huella y el número de páginas. No se aplican a otros archivos por parecido de nombre.

## Carpetas

```bash
pdf-bookmarker carpeta "/ruta/de/libros"
```

Prepara planes archivo por archivo. El acceso por doble clic hace lo mismo. Los originales se conservan.

Para guardar automáticamente los planes que tengan todas sus entradas revisadas:

```bash
pdf-bookmarker carpeta "/ruta/de/libros" --aplicar
```

Si una entrada queda pendiente, ese PDF no se modifica. Un error no activa un modo que eluda las comprobaciones. Los mensajes muestran el archivo afectado y el motivo.

`aprobar` queda como comprobación de compatibilidad. Nunca convierte pendientes en verificados. `aplicar-forzado` conserva su nombre anterior, pero ahora escribe mediante un archivo temporal y comprueba el resultado antes de reemplazar el original.

## Instalación y pruebas

Necesita Python 3.10 o posterior y `pypdf`. El motor alternativo necesita `pikepdf`. Poppler aporta `pdftotext` y `pdftoppm`. La comparación visual necesita `pdftoppm`.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install pypdf pikepdf
brew install poppler
./install.sh
PDF_BOOKMARKER_PYTHON="$PWD/.venv/bin/python" pdf-bookmarker --help
python3 -m unittest discover -s tests -v
```

Cada error corregido debe incorporar una prueba que reproduzca el fallo. Las pruebas trabajan con PDF pequeños de ejemplo, no con la biblioteca del usuario.
