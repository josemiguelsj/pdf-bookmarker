#!/usr/bin/env python3
"""Verifica las páginas de un plan contra el texto real del PDF.

Para cada entrada que empieza con decimal (1., 1.1., …) o letra (a), b), …),
busca en el texto la línea donde aparece como ENCABEZADO (al inicio de línea,
permitiendo artículos "La/El/Los" entre el anchor y las palabras del título).

- Si encuentra la página real, actualiza `page` y añade nota.
- Si no encuentra, deja la entrada intacta.
- Mantiene monotonía: una entrada posterior no apunta a una página anterior.
- No toca entradas con depth 0 (portadillas, se asumen verificadas manualmente).

Uso:
  verificar_paginas.py <pdf> <plan.json> [--ventana N]
"""
from __future__ import annotations
import argparse, json, re, subprocess, unicodedata, hashlib
from pathlib import Path


def normtxt(s):
    s = unicodedata.normalize('NFD', s)
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return re.sub(r'\s+', ' ', s.lower()).strip()


def sha256(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda: f.read(1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()


def leer_pdf_por_paginas(pdf):
    r = subprocess.run(['pdftotext', '-layout', str(pdf), '-'],
                       capture_output=True, text=True)
    return r.stdout.split('\f')


def construir_patron(title):
    """Devuelve el regex compilado o None si el título no tiene anchor numérico."""
    m = re.match(r'^\s*(\d+(?:\.\d+)*)\.|^\s*([a-h])\)', title)
    if not m:
        return None
    tn_no_num = normtxt(re.sub(r'^(\d+(\.\d+)*\.?|[a-h]\))\s*', '', title))
    words = [w for w in tn_no_num.split() if len(w) >= 4][:2]
    if not words:
        return None
    if m.group(1):
        anchor = r'^\s*' + re.escape(m.group(1)) + r'\.\s+'
    else:
        anchor = r'^\s*' + re.escape(m.group(2)) + r'\)\s+'
    # Permite "La ", "El ", "Los ", artículos y conectores antes de las palabras
    conectores = r'(?:[a-z]+\s+){0,3}'
    cuerpo = r'.{0,30}'.join(re.escape(w) for w in words)
    return re.compile(anchor + conectores + cuerpo, re.IGNORECASE)


def buscar_pagina_real(pat, pages, lo, hi):
    """Busca línea que matchee el patrón en pages[lo:hi]. Retorna 1-indexed."""
    for i in range(max(0, lo), min(len(pages), hi)):
        for line in pages[i].split('\n'):
            if pat.match(normtxt(line)):
                return i + 1
    return None


def verificar(pdf, plan_path, ventana=25, dry=False):
    pages = leer_pdf_por_paginas(pdf)
    data = json.loads(plan_path.read_text(encoding='utf-8'))
    cambios = []
    for e in data['entries']:
        if e.get('depth', 0) == 0:
            continue  # portadillas no se tocan automáticamente
        pat = construir_patron(e['title'])
        if not pat:
            continue
        pg = e['page']
        real = buscar_pagina_real(pat, pages, pg - 6, pg + ventana)
        if real and real != pg:
            cambios.append((e['title'][:60], pg, real))
            e['page'] = real
            e['note'] = f"verificado {pg}→{real}"
    # Monotonía
    prev = 0
    for e in data['entries']:
        if e['page'] < prev:
            e['page'] = prev
            e['note'] = (e.get('note') or '') + ' | monot'
        prev = e['page']
    # Actualizar hash
    data['source_sha256'] = sha256(pdf)
    if not dry:
        plan_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n',
                             encoding='utf-8')
    return cambios


def main():
    ap = argparse.ArgumentParser(prog='verificar_paginas',
                                 description='Corrige páginas de un plan buscando los títulos en el texto del PDF.')
    ap.add_argument('pdf', type=Path)
    ap.add_argument('plan', type=Path)
    ap.add_argument('--ventana', type=int, default=25,
                    help='Páginas adelante del hint donde buscar (default 25).')
    ap.add_argument('--dry', action='store_true',
                    help='Reporta cambios sin modificar el plan.')
    args = ap.parse_args()
    cambios = verificar(args.pdf.resolve(), args.plan.resolve(),
                        ventana=args.ventana, dry=args.dry)
    print(f'Correcciones: {len(cambios)}')
    for t, old, new in cambios:
        print(f'  {old:>3} → {new:<3}  {t}')


if __name__ == '__main__':
    main()
