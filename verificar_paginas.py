#!/usr/bin/env python3
"""Resuelve encabezados sin aprobar coincidencias ambiguas ni cambiar la huella."""
import argparse
import re
import unicodedata
from pathlib import Path
from corregir_marcadores import cargar_plan, leer_pdf, sha256, escribir_json
from memoria import consultar, identificar


def normtxt(s):
    s = ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')
    return re.sub(r'\s+', ' ', s.casefold()).strip()


def leer_pdf_por_paginas(pdf):
    import shutil
    import subprocess
    reader = leer_pdf(pdf)
    import os
    cache = Path(os.environ.get('PDF_BOOKMARKER_CACHE', Path.home() / '.cache/pdf-bookmarker')) / (sha256(pdf) + '.json')
    import json
    if cache.exists():
        try:
            cached = json.loads(cache.read_text())
        except (ValueError, OSError):
            cached = None
        if isinstance(cached, list) and len(cached) == len(reader.pages) and all(isinstance(x, str) for x in cached):
            return cached
    if shutil.which('pdftotext'):
        run = subprocess.run(['pdftotext', '-layout', str(pdf), '-'], capture_output=True, text=True, check=True)
        pages = run.stdout.split('\f')
        if len(pages) == len(reader.pages) + 1 and not pages[-1].strip():
            pages.pop()
    else:
        pages = [p.extract_text() or '' for p in reader.pages]
    if len(pages) != len(reader.pages):
        raise ValueError('La extracción no conserva el número de páginas.')
    escribir_json(cache, pages)
    return pages


def es_indice(text):
    return bool(re.search(r'(?mi)^\s*(indice(?: general)?|contenido|sumario|table of contents|contents)\s*[.:]?\s*$', norm_lines(text)))


def norm_lines(text):
    return '\n'.join(normtxt(line) for line in text.splitlines())


def indexar_encabezados(pages):
    index = {}
    for page, text in enumerate(pages, 1):
        if es_indice(text):
            continue
        lines = [normtxt(x) for x in text.splitlines() if x.strip()]
        for i in range(len(lines)):
            for count in range(1, 5):
                heading = ' '.join(lines[i:i + count]).strip(' .')
                if 8 <= len(heading) <= 500:
                    index.setdefault(heading, set()).add(page)
    return index


def candidatos(title, pages, index=None):
    target = normtxt(title).strip(' .')
    if len(target) < 8:
        return []
    index = index if index is not None else indexar_encabezados(pages)
    return sorted(index.get(target, []))


def verificar(pdf, plan_path, ventana=25, dry=False):
    data = cargar_plan(plan_path)
    fingerprint = sha256(pdf)
    if data.get('source_sha256') != fingerprint:
        raise ValueError('La huella del PDF no coincide. El plan no se modificó.')
    pages = leer_pdf_por_paginas(pdf)
    if data.get('page_count') != len(pages):
        raise ValueError('El número de páginas no coincide.')
    changes = []
    headings = indexar_encabezados(pages)
    memory_path = __import__('memoria').ruta()
    import json
    memory = json.loads(memory_path.read_text()) if memory_path.exists() else {}
    identificar(data['entries'])
    for entry in data['entries']:
        evidence = entry.get('evidence')
        if evidence and (evidence.get('title') != entry['title'] or evidence.get('page') != entry.get('page') or evidence.get('source_sha256') != fingerprint):
            entry['verified'] = False
        if entry.get('verified') is True:
            continue
        learned = consultar(fingerprint, entry, memory)
        if learned and 1 <= learned.get('page', 0) <= len(pages) and learned.get('evidence', {}).get('source_sha256') == fingerprint and learned.get('evidence', {}).get('title') == entry['title']:
            entry.update(learned)
            continue
        hits = candidatos(entry['title'], pages, headings)
        if len(hits) == 1:
            old = entry.get('page')
            entry['page'] = hits[0]
            entry['verified'] = True
            entry['evidence'] = {'method': 'exact_heading', 'page': hits[0], 'source_sha256': fingerprint, 'title': entry['title']}
            entry['status'] = 'verified'
            if old != hits[0]:
                changes.append((entry['title'], old, hits[0]))
        else:
            entry['verified'] = False
            entry['status'] = 'ambiguous' if hits else 'unresolved'
            entry['candidates'] = hits
    if not dry:
        escribir_json(plan_path, data)
        escribir_json(plan_path.with_name('informe_verificacion.json'), dict(source_sha256=fingerprint, verified=sum(e.get('verified') is True for e in data['entries']), pending=[dict(title=e['title'], status=e.get('status', 'unresolved'), candidates=e.get('candidates', [])) for e in data['entries'] if e.get('verified') is not True]))
    return changes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('pdf', type=Path)
    parser.add_argument('plan', type=Path)
    parser.add_argument('--ventana', type=int, default=25, help='Compatibilidad. La búsqueda comprueba todo el libro.')
    parser.add_argument('--dry', action='store_true')
    args = parser.parse_args()
    try:
        changes = verificar(args.pdf, args.plan, args.ventana, args.dry)
        print(f'Destinos corregidos: {len(changes)}. Las entradas pendientes requieren revisión.')
    except (ValueError, OSError) as exc:
        parser.exit(1, f'Error: {exc}\n')


if __name__ == '__main__':
    main()
