"""Procesa un archivo por vez. Conserva los originales si hay pendientes."""
import argparse
from pathlib import Path
from types import SimpleNamespace
from corregir_marcadores import extraer, cargar_plan, aplicar
from verificar_paginas import verificar
from extraer_de_indice import generar


def listar_pdfs(ruta):
    if ruta.is_file():
        if ruta.suffix.lower() != '.pdf':
            raise ValueError('Seleccione un archivo PDF.')
        return [ruta]
    if ruta.is_dir():
        return [p for p in sorted(ruta.iterdir()) if p.is_file() and p.suffix.lower() == '.pdf']
    raise ValueError('El archivo o la carpeta no existe.')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('carpeta', type=Path)
    p.add_argument('--aplicar', action='store_true', help='Guardar solo planes sin entradas pendientes.')
    args = p.parse_args()
    try:
        pdfs = listar_pdfs(args.carpeta)
    except ValueError as exc:
        p.error(str(exc))
    if not pdfs:
        print('La carpeta no contiene archivos PDF.')
        return
    for pdf in pdfs:
        if pdf.suffix.lower() != '.pdf' or not pdf.is_file():
            continue
        out = pdf.parent / '_pdf_bookmarker_tmp' / pdf.stem
        plan = out / 'plan_para_revisar.json'
        try:
            extraer(SimpleNamespace(pdf=pdf, salida=out))
            import json
            if not json.loads((out / 'marcadores_originales.json').read_text()) and cargar_plan(plan).get('review_origin') != 'verified_local_plan':
                generar(pdf, out)
            verificar(pdf, plan)
            data = cargar_plan(plan)
            pending = sum(e.get('verified') is not True for e in data['entries'])
            if not data['entries'] or data.get('needs_structure_review'):
                print(f'{pdf.name}: no se extrajo una estructura completa. Revise el índice o el OCR.')
                continue
            if pending:
                print(f'{pdf.name}: pendiente de revisión ({pending} entradas).')
                continue
            if args.aplicar:
                aplicar(SimpleNamespace(pdf=pdf, plan=plan, respaldo=None, verificar_imagenes='destinos', motor='pypdf'))
            else:
                print(f'{pdf.name}: plan preparado. Revise antes de aplicar.')
        except Exception as exc:
            print(f'{pdf.name}: error: {exc}')


if __name__ == '__main__':
    main()
