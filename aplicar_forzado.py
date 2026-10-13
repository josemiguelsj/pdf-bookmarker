#!/usr/bin/env python3
"""Aplica un plan usando pikepdf (más tolerante que pypdf con PDFs frágiles).

Para PDFs donde `pdf-bookmarker aplicar` reporta "Cambió el contenido o la
geometría de las páginas". pikepdf no reescribe las páginas, solo manipula
el outline; respeta la estructura PDF original.

Siempre crea respaldo antes de modificar.

Uso:
  aplicar_forzado.py <pdf> <plan.json>  [--respaldo <carpeta>]
"""
from __future__ import annotations
import argparse, json, shutil, hashlib, sys
from datetime import datetime
from pathlib import Path

try:
    import pikepdf
except ImportError:
    raise SystemExit('Falta pikepdf. Instalar con: pip3 install --user --break-system-packages pikepdf')


def sha256(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda: f.read(1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()


def validar_plan(entries, count):
    if not entries:
        raise ValueError('El plan debe contener al menos un marcador.')
    prev = -1
    for pos, item in enumerate(entries, 1):
        title = item.get('title', '')
        page = item.get('page')
        depth = item.get('depth')
        if not isinstance(title, str) or not title.strip():
            raise ValueError(f'Marcador {pos}: título vacío.')
        if type(page) is not int or not 1 <= page <= count:
            raise ValueError(f'Marcador {pos}: página fuera del PDF ({page}).')
        if type(depth) is not int or depth < 0 or depth > prev + 1:
            raise ValueError(f'Marcador {pos}: salto de nivel inválido ({depth}).')
        if item.get('verified') is not True:
            raise ValueError(f'Marcador {pos}: falta "verified": true.')
        prev = depth


def main():
    ap = argparse.ArgumentParser(prog='aplicar-forzado',
                                 description='Aplica un plan con pikepdf (para PDFs que pypdf rechaza).')
    ap.add_argument('pdf', type=Path)
    ap.add_argument('plan', type=Path)
    ap.add_argument('--respaldo', type=Path)
    args = ap.parse_args()

    src = args.pdf.resolve()
    data = json.loads(args.plan.read_text(encoding='utf-8'))
    entries = data.get('entries', [])

    with pikepdf.open(str(src)) as pdf_pre:
        total = len(pdf_pre.pages)

    validar_plan(entries, total)

    if data.get('source_sha256') and data['source_sha256'] != sha256(src):
        raise SystemExit('ERROR: el PDF cambió desde la revisión del plan.')

    # Respaldo
    backup_root = (args.respaldo or src.parent / 'Respaldo de marcadores').resolve()
    stamp = datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    backup_dir = backup_root / stamp
    backup_dir.mkdir(parents=True, exist_ok=False)
    backup = backup_dir / src.name
    shutil.copy2(src, backup)
    if sha256(backup) != sha256(src):
        raise SystemExit('ERROR: falló la comprobación del respaldo.')
    (backup_dir / 'plan_aplicado.json').write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    # Modificar outline in-place con pikepdf
    with pikepdf.open(str(src), allow_overwriting_input=True) as pdf:
        pages = pdf.pages
        # Borrar outlines existentes
        if '/Outlines' in pdf.Root:
            del pdf.Root['/Outlines']

        with pdf.open_outline() as outline:
            outline.root.clear()
            stack = []  # (depth, pikepdf.OutlineItem)
            for e in entries:
                depth = e['depth']
                page_idx = e['page'] - 1
                oi = pikepdf.OutlineItem(
                    e['title'][:200],
                    page_idx,
                    page_location=pikepdf.PageLocation.Fit,
                )
                # Encontrar nivel padre
                while stack and stack[-1][0] >= depth:
                    stack.pop()
                if stack:
                    stack[-1][1].children.append(oi)
                else:
                    outline.root.append(oi)
                stack.append((depth, oi))
        pdf.save(str(src))

    print(f'Guardado en el mismo archivo: {src}')
    print(f'Marcadores: {len(entries)}. Páginas: {total}.')
    print(f'Respaldo: {backup_dir}')


if __name__ == '__main__':
    try:
        main()
    except (SystemExit, Exception) as e:
        if isinstance(e, SystemExit) and (e.code or 0) == 0:
            sys.exit(0)
        sys.stderr.write(f'Error: {e}\n')
        sys.exit(1)
