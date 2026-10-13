# Corregir los marcadores de un libro PDF

Esta herramienta guarda los marcadores en el mismo archivo. Antes crea una copia completa del original. Trabaja con un libro por vez.

## Flujo con subcomandos

```bash
pdf-bookmarker extraer "libro.pdf" --salida "Revision libro"
pdf-bookmarker verificar "libro.pdf" "Revision libro/plan_para_revisar.json"
# (edición manual si hace falta)
pdf-bookmarker aplicar "libro.pdf" "Revision libro/plan_para_revisar.json"
```

El subcomando `verificar` busca cada entrada numerada del plan (1., 1.1., a), b)) en el texto del PDF y corrige su página automáticamente. Las entradas de portadilla (depth 0) no se tocan.

El programa comprueba los títulos, niveles y destinos escritos contra el plan que usted ha revisado. Comprueba también que los contenidos y las dimensiones de las páginas no cambien. Puede comparar las imágenes antes y después, con Poppler instalado.

El programa no decide por sí solo si un título corresponde al libro. Esa revisión debe hacerse frente al índice y al inicio real de cada apartado. El índice impreso puede contener errores. Un número dentro de los límites del PDF no garantiza un destino correcto.

## Instalar

Necesita Python 3.10 o posterior.

```bash
python3 -m pip install pypdf
```

En macOS, para extraer el texto con su disposición y comprobar las imágenes:

```bash
brew install poppler
```

## 1. Extraer un archivo

Desde la carpeta de la herramienta:

```bash
python3 corregir_marcadores.py extraer "/ruta/Libro.pdf" --salida "/ruta/Revision Libro"
```

Se crean estos archivos:

- `plan_para_revisar.json`: los marcadores que se pueden corregir.
- `marcadores_originales.json`: el listado anterior.
- `texto_por_paginas.txt`: el texto, con un salto de página entre cada página del PDF. Los PDF que contienen solo imágenes necesitan OCR o lectura visual.

## 2. Revisar el plan

Cada entrada tiene esta forma:

```json
{
  "title": "Capítulo 1. Título del capítulo",
  "page": 15,
  "depth": 0,
  "verified": true
}
```

`page` es la página física del PDF, empezando por 1. No es necesariamente el número impreso en el libro.

`depth` comienza en 0. Una parte puede tener nivel 0, sus capítulos nivel 1 y sus apartados nivel 2. El nivel solo puede aumentar de uno en uno. El orden del plan determina qué apartado pertenece a cada capítulo.

Marque `verified` como `true` después de revisar el título y el destino. El programa rechaza entradas sin esa confirmación. Puede añadir una propiedad `note` para registrar errores del índice o páginas ausentes.

Compare cada entrada con el libro. Si el inicio de un apartado falta, no lo presente como verificado en una página distinta. Puede enlazar su continuación, indicando en el título qué páginas faltan.

El archivo incluye el número de páginas y la huella del PDF de origen. No cambie esos datos para eludir una discrepancia. Si otro programa modifica el PDF, extraiga de nuevo el plan y compruebe los destinos.

## 3. Comprobar sin modificar

```bash
python3 corregir_marcadores.py comprobar "/ruta/Libro.pdf" "/ruta/Revision Libro/plan_para_revisar.json"
```

## 4. Guardar en el mismo PDF

```bash
python3 corregir_marcadores.py aplicar "/ruta/Libro.pdf" "/ruta/Revision Libro/plan_para_revisar.json" --verificar-imagenes destinos
```

Para comparar todas las páginas, cambie `destinos` por `todas`. Esa comprobación tarda más. Sin Poppler, omita la opción. En ese caso se comprueban el contenido de las páginas y los marcadores, pero no las imágenes.

Se crea una carpeta `Respaldo de marcadores` junto al PDF. Cada ejecución conserva el original, los marcadores anteriores, el plan aplicado y un informe. Puede elegir otra ubicación:

```bash
python3 corregir_marcadores.py aplicar "/ruta/Libro.pdf" "/ruta/plan.json" --respaldo "/ruta/Respaldos" --verificar-imagenes destinos
```

Para deshacer los cambios, cierre el libro y copie el PDF de respaldo sobre el archivo corregido.

## Planes de la Colección Manresa

La carpeta `planes_verificados` contiene los planes de los 12 libros terminados al preparar esta entrega. No incluye los borradores de los demás libros ni copias de los PDF.

Estos planes están vinculados a las copias de respaldo anteriores a la corrección. Sirven como registro y como ejemplos completos de estructura. Los libros terminados ya tienen los marcadores corregidos. No hace falta volver a aplicarlos. El programa rechazará un plan si su huella no coincide con el PDF elegido.

En el libro sobre Diego Laínez, el plan señala que faltan las páginas impresas 48 y 49. El marcador dirige a la continuación en la página 50. El script no reconstruye páginas ausentes.

## Alcance de la comprobación

La comparación de contenidos detecta cambios en las instrucciones gráficas de cada página. La comparación de imágenes amplía esa comprobación a la representación de las páginas elegidas. Ninguna de ellas demuestra que el índice sea correcto. Esa verificación se hace comparando los encabezados con el libro.

La herramienta reemplaza el conjunto de marcadores por el plan. Conserva las páginas y copia la estructura del documento, pero no conserva colores, estilos o acciones especiales de los marcadores anteriores. Está pensada para libros sin formularios ni firmas digitales.
