#!/usr/bin/env python3
"""Genera un plan JSON para un PDF SIN marcadores previos.

Lee el ÍNDICE / CONTENIDO / TABLE OF CONTENTS en las primeras 50 páginas
y en las últimas 50 páginas, parsea las entradas (título ... página) y
construye un plan con jerarquía por numeración decimal o indentación.

Las páginas quedan como estimación inicial (basadas en el número que
aparece en el índice). Después hay que correr `pdf-bookmarker verificar`
para resolverlas por contenido.

Uso:
  extraer_de_indice.py <pdf> --salida <carpeta>
"""
from __future__ import annotations
import argparse, json, re, subprocess, unicodedata, hashlib
from pathlib import Path
import pypdf

TOC_HEAD = re.compile(
    r'^\s*(ÍNDICE(\s+GENERAL)?|CONTENIDO|SUMARIO|INDICE|TABLA\s+DE\s+CONTENIDO|'
    r'TABLE(\s+DES\s+MATIÈRES|\s+OF\s+CONTENTS)?|CONTENTS|'
    r'DES\s+PRINCIPAUX\s+SUJETS\s+CONTENUS|'
    r'INHALT|INHALTSVERZEICHNIS)\s*\.?\s*$', re.IGNORECASE)

ENT_DOTS = re.compile(r'^(\s*)(.{3,180}?)\s*\.{3,}\s*(\d{1,4})\s*$')
ENT_GAP = re.compile(r'^(\s*)(.{3,180}?)\s{2,}(\d{1,4})\s*$')
ENT_DEC = re.compile(r'^(\s*)(\d+(?:\.\d+)*\.?\s+.{3,180}?)\s+(\d{1,4})\s*$')


def sha256(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda: f.read(1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()


def norm_header(s):
    s = re.sub(r'\b([A-ZÁÉÍÓÚÑ])\s(?=[A-ZÁÉÍÓÚÑ]\b)', r'\1', s)
    s = re.sub(r'\b(\w) (?=\w\b)', r'\1', s)
    return s


def leer_rango(pdf, inicio, fin):
    r = subprocess.run(['pdftotext', '-f', str(inicio), '-l', str(fin),
                        '-layout', str(pdf), '-'],
                       capture_output=True, text=True)
    return [norm_header(ln) for ln in r.stdout.split('\n')]


def localizar_toc(pdf, total):
    """Devuelve lista de (start_page, lines) donde empieza el TOC."""
    for inicio, fin in [(1, min(50, total)),
                        (max(1, total - 50), total)]:
        lines = leer_rango(pdf, inicio, fin)
        for i, ln in enumerate(lines):
            if TOC_HEAD.match(ln.strip()):
                return inicio, i, lines
    return None, None, None


def extraer_entradas(lines, start_idx):
    """Extrae entradas de índice desde lines[start_idx+1:].
    Devuelve lista de (indent, title, book_page)."""
    out = []
    empty = 0
    for raw in lines[start_idx + 1: start_idx + 500]:
        if not raw.strip():
            empty += 1
            if empty > 30:
                break
            continue
        empty = 0
        m = ENT_DEC.match(raw) or ENT_DOTS.match(raw) or ENT_GAP.match(raw)
        if m:
            indent = len(m.group(1).expandtabs(4))
            t = m.group(2).strip(' .\t·')
            p = int(m.group(3))
            if t and 1 <= p < 5000 and len(t) >= 2:
                out.append((indent, t, p))
    return out


def clasificar_depth(title, indent, prev_depth):
    """Depth plano estilo plan verificado:
    0 = Partes, capítulos, preliminares, bibliografía.
    1 = numeración decimal (1., 1.1., 1.1.1.).
    2 = sub-letras a), b).
    """
    t = title.strip()
    if re.match(r'^(portada|índice|índice general|presentación|prólogo|'
                r'prologo|abreviaturas|índice de abreviaturas|'
                r'bibliografía|bibliography|conclusiones|anexo|'
                r'apéndice|appendix|epílogo|preface|introduction|'
                r'contents?)\b', t, re.IGNORECASE):
        d = 0
    elif re.match(r'^(primera|segunda|tercera|cuarta|quinta|sexta|'
                  r'séptima|octava|part(e)?)\s+\w', t, re.IGNORECASE):
        d = 0
    elif re.match(r'^(cap[íi]tulo|CAPITULO|chapter|chap\.)\s+[IVXLC\d]+',
                  t, re.IGNORECASE):
        d = 0
    elif re.match(r'^\s*\d+(?:\.\d+)*\.?\s+', t):
        d = 1
    elif re.match(r'^\s*[a-h]\)', t):
        d = 2
    else:
        d = max(1, indent // 4)
    # Nunca saltar más de un nivel
    if d > prev_depth + 1:
        d = prev_depth + 1
    return d


def main():
    ap = argparse.ArgumentParser(prog='extraer-de-indice',
                                 description='Genera plan desde el ÍNDICE del libro, no desde bookmarks.')
    ap.add_argument('pdf', type=Path)
    ap.add_argument('--salida', type=Path, required=True)
    args = ap.parse_args()

    pdf = args.pdf.resolve()
    out = args.salida.resolve()
    out.mkdir(parents=True, exist_ok=True)

    reader = pypdf.PdfReader(str(pdf))
    total = len(reader.pages)

    toc_inicio_pdf, toc_idx, lines = localizar_toc(pdf, total)
    entradas = []
    if toc_idx is not None:
        entradas = extraer_entradas(lines, toc_idx)

    plan_entries = []
    prev_d = -1
    for indent, title, book_page in entradas:
        d = clasificar_depth(title, indent, prev_d)
        prev_d = d
        clean = re.sub(r'[\x00-\x1f]+', ' ', title).strip()
        page = min(max(book_page, 1), total)
        plan_entries.append({
            "title": clean[:200],
            "page": page,
            "depth": d,
            "verified": False,
            "note": "estimación desde índice del libro"
        })

    # Guardar plan y texto por páginas (como extraer original)
    plan = {
        "schema": 1,
        "source_name": pdf.name,
        "source_sha256": sha256(pdf),
        "page_count": total,
        "entries": plan_entries,
    }
    (out / 'plan_para_revisar.json').write_text(
        json.dumps(plan, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    # Texto por páginas para que verificar/aprobar puedan trabajar
    txt = subprocess.run(['pdftotext', '-layout', str(pdf), '-'],
                         capture_output=True, text=True).stdout
    (out / 'texto_por_paginas.txt').write_text(txt, encoding='utf-8')

    print(f'Extraídas {len(plan_entries)} entradas del índice del libro.')
    print(f'Plan: {out / "plan_para_revisar.json"}')
    if len(plan_entries) == 0:
        print('No se encontró ÍNDICE / CONTENIDO en el PDF.')


if __name__ == '__main__':
    main()
