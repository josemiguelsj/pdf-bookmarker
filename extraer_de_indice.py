#!/usr/bin/env python3
"""Extrae el índice impreso con su página física y conserva destinos pendientes."""
import argparse
import re
from pathlib import Path
from corregir_marcadores import escribir_json, sha256
from verificar_paginas import leer_pdf_por_paginas, normtxt

HEAD = re.compile(r'^(indice(?: general)?|synopsis of contents|contenido|sumario|table of contents|contents|table des matieres|inhaltsverzeichnis)\.?$')
ENTRY = re.compile(r'^(\s*)(.{3,250}?)\s*(?:\.{2,}|\s{2,})\s*(\d{1,4}|[ivxlcdm]+)\s*$', re.I)


def clasificar_depth(title, indent, prev_depth, chapter=False):
    decimal = re.match(r'^(\d+(?:\.\d+)*)[.]?\s', title)
    if decimal:
        depth = decimal[1].count('.') + (1 if chapter else 0)
    elif re.match(r'^[a-z]\)', title):
        depth = min(prev_depth + 1, 2)
    elif re.match(r'^(capitulo|chapter|parte|prologo|introduccion|bibliografia|apendice)\b', normtxt(title)):
        depth = 0
    else:
        depth = indent // 4
    return max(0, min(depth, prev_depth + 1))


def generar(pdf, out):
    pdf = pdf.resolve()
    pages = leer_pdf_por_paginas(pdf)
    headings = []
    for n, text in enumerate(pages, 1):
        for i, line in enumerate(text.splitlines()):
            if HEAD.fullmatch(re.sub(r'\s+[ivxlcdm]+$', '', normtxt(line))):
                headings.append((n, i, line.strip()))
    general = [x for x in headings if normtxt(x[2]) in ['indice', 'indice general', 'table of contents', 'contents']]
    chosen = (general or headings)
    entries = []
    if chosen:
        start, line_index, label = chosen[0]
        entries.append(dict(title='Índice general', page=start, depth=0, verified=True, evidence=dict(method='index_heading', page=start, title='Índice general', source_sha256=sha256(pdf))))
        previous = -1
        chapter = False
        continuation = []
        for n in range(start, len(pages) + 1):
            lines = pages[n - 1].splitlines()
            if n == start:
                lines = lines[line_index + 1:]
            parsed = 0
            for line in lines:
                match = ENTRY.match(line)
                if match:
                    indent, title, printed = match.groups()
                    title = ' '.join(continuation + [title.strip(' .')])
                    continuation = []
                    depth = clasificar_depth(title, len(indent), previous, chapter)
                    previous = depth
                    if re.match(r'^(capitulo|chapter)\b', normtxt(title)):
                        chapter = True
                    entries.append(dict(title=title, page=None, printed_page=printed, depth=depth, verified=False, status='unresolved', index_page=n))
                    parsed += 1
                elif line.strip() and not HEAD.fullmatch(normtxt(line)):
                    continuation.append(line.strip())
                    continuation = continuation[-3:]
                elif not line.strip():
                    continuation = []
            if n > start and parsed == 0:
                break
    out.mkdir(parents=True, exist_ok=True)
    data = dict(schema=1, source_name=pdf.name, source_sha256=sha256(pdf), page_count=len(pages), entries=entries, needs_structure_review=len(entries) < 2)
    escribir_json(out / 'plan_para_revisar.json', data)
    (out / 'texto_por_paginas.txt').write_text('\f'.join(pages), encoding='utf-8')
    print(f'Índice: {len(entries)} entradas. Los destinos pendientes no se estiman.')
    return data


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('pdf', type=Path)
    p.add_argument('--salida', type=Path, required=True)
    args = p.parse_args()
    generar(args.pdf, args.salida)


if __name__ == '__main__':
    main()
