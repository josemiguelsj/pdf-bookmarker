"""Procesa un archivo por vez. Conserva los originales si hay pendientes."""
import argparse
from pathlib import Path
from types import SimpleNamespace
from corregir_marcadores import extraer, cargar_plan, aplicar
from verificar_paginas import verificar
from extraer_de_indice import generar


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('carpeta', type=Path)
    p.add_argument('--aplicar', action='store_true', help='Guardar solo planes sin entradas pendientes.')
    args = p.parse_args()
    for pdf in sorted(args.carpeta.iterdir()):
        if pdf.suffix.lower() != '.pdf' or not pdf.is_file():
            continue
        out = args.carpeta / '_pdf_bookmarker_tmp' / pdf.stem
        plan = out / 'plan_para_revisar.json'
        try:
            extraer(SimpleNamespace(pdf=pdf, salida=out))
            import json
            if not json.loads((out / 'marcadores_originales.json').read_text()) and cargar_plan(plan).get('review_origin') != 'verified_local_plan':
                generar(pdf, out)
            verificar(pdf, plan)
            data = cargar_plan(plan)
            pending = sum(e.get('verified') is not True for e in data['entries'])
            if not data['entries'] or pending or data.get('needs_structure_review'):
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
