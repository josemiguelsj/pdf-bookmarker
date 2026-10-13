#!/usr/bin/env python3
"""Revisa y reemplaza marcadores de un PDF a partir de un plan explícito.

Dependencia: python3 -m pip install pypdf
Opcional: Poppler (pdftotext y pdftoppm) para extraer y comparar imágenes.
Las páginas del plan empiezan en 1. Los niveles empiezan en 0.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

try:
    from pypdf import PdfReader, PdfWriter
    from pypdf.generic import NameObject
except ImportError:
    raise SystemExit('Falta pypdf. Instálelo con: python3 -m pip install pypdf')


def leer_pdf(path):
    reader = PdfReader(str(path))
    if reader.is_encrypted:
        raise ValueError('El PDF está cifrado. Se necesita una copia accesible sin contraseña.')
    return reader


def marcadores(reader):
    result = []
    def recorrer(items, depth=0):
        for item in items:
            if isinstance(item, list):
                recorrer(item, depth + 1)
            else:
                try:
                    page = reader.get_destination_page_number(item)
                    page = page + 1 if page is not None and page >= 0 else None
                except Exception:
                    page = None
                result.append({'title': str(item.title), 'page': page, 'depth': depth})
    recorrer(reader.outline)
    return result


def escribir_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def sha256(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def firmas_paginas(reader):
    result = []
    for page in reader.pages:
        contents = page.get_contents()
        result.append({
            'contenido': hashlib.sha256(contents.get_data() if contents else b'').hexdigest(),
            'media': [float(v) for v in page.mediabox],
            'crop': [float(v) for v in page.cropbox],
            'giro': int(page.get('/Rotate', 0)),
        })
    return result


def validar_plan(plan, count):
    if not isinstance(plan, list) or not plan:
        raise ValueError('El plan debe contener al menos un marcador.')
    previous = -1
    for pos, item in enumerate(plan, 1):
        if not isinstance(item, dict):
            raise ValueError(f'Marcador {pos}: se esperaba un objeto JSON.')
        title, page, depth = (item.get(k) for k in ('title', 'page', 'depth'))
        if not isinstance(title, str) or not title.strip():
            raise ValueError(f'Marcador {pos}: título vacío o inválido.')
        if any(ord(c) < 32 for c in title):
            raise ValueError(f'Marcador {pos}: título con saltos de línea o caracteres de control.')
        if type(page) is not int or not 1 <= page <= count:
            raise ValueError(f'Marcador {pos}: página fuera del PDF ({page}).')
        if type(depth) is not int or depth < 0 or depth > previous + 1:
            raise ValueError(f'Marcador {pos}: salto de nivel inválido ({depth}).')
        if item.get('verified') is not True:
            raise ValueError(f'Marcador {pos}: falta confirmar su revisión con "verified": true.')
        previous = depth


def extraer(args):
    src = args.pdf.resolve()
    reader = leer_pdf(src)
    out = args.salida.resolve()
    out.mkdir(parents=True, exist_ok=True)
    entries = marcadores(reader)
    plan = dict(
        schema=1,
        source_name=src.name,
        source_sha256=sha256(src),
        page_count=len(reader.pages),
        entries=[dict(x, verified=False) for x in entries],
    )
    escribir_json(out / 'plan_para_revisar.json', plan)
    escribir_json(out / 'marcadores_originales.json', entries)
    poppler = shutil.which('pdftotext')
    if poppler:
        subprocess.run([poppler, '-layout', str(src), str(out / 'texto_por_paginas.txt')], check=True)
    else:
        texts = [p.extract_text() or '' for p in reader.pages]
        (out / 'texto_por_paginas.txt').write_text('\f'.join(texts), encoding='utf-8')
    print(f'Extraídos {len(entries)} marcadores de {len(reader.pages)} páginas.')
    print(f'Plan pendiente de revisión: {out / "plan_para_revisar.json"}')


def cargar_plan(path):
    data = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(data, dict) or data.get('schema') != 1:
        raise ValueError('Formato desconocido. El plan debe tener schema: 1 y entries.')
    return data


def comprobar(args):
    reader = leer_pdf(args.pdf)
    data = cargar_plan(args.plan)
    validar_plan(data.get('entries'), len(reader.pages))
    if data.get('page_count') != len(reader.pages):
        raise ValueError('El número de páginas no coincide con el plan.')
    if data.get('source_sha256') and data['source_sha256'] != sha256(args.pdf):
        raise ValueError('El PDF cambió desde la revisión. Extraiga y revise un plan nuevo.')
    print(f'Plan válido: {len(data["entries"])} marcadores. La estructura y las páginas son válidas.')
    print('Esta comprobación no sustituye la comparación de los títulos con el libro.')
    return data, reader


def comparar_render(original, changed, page_numbers, directory):
    renderer = shutil.which('pdftoppm')
    if not renderer:
        raise ValueError('La comparación visual necesita pdftoppm (Poppler).')
    for n in page_numbers:
        paths = []
        for label, pdf in [('antes', original), ('despues', changed)]:
            prefix = directory / f'{label}-{n}'
            run = subprocess.run([
                renderer, '-f', str(n), '-l', str(n), '-scale-to', '1400',
                '-singlefile', '-png', str(pdf), str(prefix)
            ], capture_output=True, text=True)
            if run.returncode:
                raise ValueError(f'No se pudo representar la página {n}: {run.stderr[-1000:]}')
            paths.append(prefix.with_suffix('.png'))
        if paths[0].read_bytes() != paths[1].read_bytes():
            raise ValueError(f'La imagen de la página {n} cambió. El original no se reemplazará.')


def aplicar(args):
    if args.pdf.is_symlink():
        raise ValueError('Seleccione el archivo original en lugar de un enlace simbólico.')
    src = args.pdf.resolve()
    data, reader = comprobar(args)
    entries = data['entries']
    if reader.get_fields():
        raise ValueError('El PDF tiene campos de formulario. Este script está pensado para libros.')
    if args.verificar_imagenes and not shutil.which('pdftoppm'):
        raise ValueError('Instale Poppler para la opción --verificar-imagenes.')
    original_hash = sha256(src)
    original_signatures = firmas_paginas(reader)
    old_entries = marcadores(reader)
    backup_root = (args.respaldo or src.parent / 'Respaldo de marcadores').resolve()
    stamp = datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    backup_dir = backup_root / stamp
    backup_dir.mkdir(parents=True, exist_ok=False)
    backup = backup_dir / src.name
    shutil.copy2(src, backup)
    if sha256(backup) != original_hash:
        raise ValueError('Falló la comprobación de la copia de respaldo.')
    escribir_json(backup_dir / 'marcadores_anteriores.json', old_entries)
    escribir_json(backup_dir / 'plan_aplicado.json', data)
    writer = PdfWriter()
    writer.clone_document_from_reader(reader)
    writer.root_object.pop(NameObject('/Outlines'), None)
    parents = []
    for x in entries:
        depth = x['depth']
        parent = parents[depth - 1] if depth else None
        ref = writer.add_outline_item(x['title'], x['page'] - 1, parent=parent, is_open=False)
        parents = parents[:depth] + [ref]
    writer.page_mode = '/UseOutlines'
    fd, temp_name = tempfile.mkstemp(prefix='.marcadores-', suffix='.pdf', dir=src.parent)
    temp_path = Path(temp_name)
    try:
        with os.fdopen(fd, 'wb') as stream:
            writer.write(stream)
            stream.flush()
            os.fsync(stream.fileno())
        final = leer_pdf(temp_path)
        if firmas_paginas(final) != original_signatures:
            raise ValueError('Cambió el contenido o la geometría de las páginas. Se conserva el original.')
        expected = [{k: x[k] for k in ('title', 'page', 'depth')} for x in entries]
        if marcadores(final) != expected:
            raise ValueError('Los marcadores escritos no coinciden con el plan. Se conserva el original.')
        checked = []
        if args.verificar_imagenes:
            if args.verificar_imagenes == 'destinos':
                checked = sorted({x['page'] for x in entries})
            else:
                checked = list(range(1, len(reader.pages) + 1))
            with tempfile.TemporaryDirectory(prefix='revisar-imagenes-') as render_dir:
                comparar_render(src, temp_path, checked, Path(render_dir))
        # Evita sobrescribir cambios de otro programa durante la revisión.
        if sha256(src) != original_hash:
            raise ValueError('Otro programa modificó el original. No se reemplazará.')
        os.chmod(temp_path, src.stat().st_mode)
        os.replace(temp_path, src)
        report = {
            'archivo': str(src), 'respaldo': str(backup),
            'paginas': len(reader.pages), 'marcadores_anteriores': len(old_entries),
            'marcadores_finales': len(entries), 'contenido_y_geometria_sin_cambios': True,
            'paginas_con_imagen_identica': checked,
            'sha256_anterior': original_hash, 'sha256_final': sha256(src),
        }
        escribir_json(backup_dir / 'informe.json', report)
        print(f'Guardado en el mismo archivo: {src}')
        print(f'Marcadores: {len(old_entries)} → {len(entries)}. Páginas: {len(reader.pages)}.')
        print(f'Respaldo e informe: {backup_dir}')
    finally:
        if temp_path.exists():
            temp_path.unlink()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='comando', required=True)
    extract = commands.add_parser('extraer', help='Extrae marcadores y texto. No modifica el PDF.')
    extract.add_argument('pdf', type=Path)
    extract.add_argument('--salida', type=Path, required=True)
    extract.set_defaults(func=extraer)
    check = commands.add_parser('comprobar', help='Valida un plan revisado. No modifica el PDF.')
    check.add_argument('pdf', type=Path)
    check.add_argument('plan', type=Path)
    check.set_defaults(func=comprobar)
    apply = commands.add_parser('aplicar', help='Guarda los marcadores en el mismo PDF con respaldo.')
    apply.add_argument('pdf', type=Path)
    apply.add_argument('plan', type=Path)
    apply.add_argument('--respaldo', type=Path)
    apply.add_argument('--verificar-imagenes', choices=['destinos', 'todas'],
                       help='Compara las imágenes antes y después. Necesita Poppler.')
    apply.set_defaults(func=aplicar)
    args = parser.parse_args()
    try:
        args.func(args)
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as exc:
        print(f'Error: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
