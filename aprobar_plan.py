#!/usr/bin/env python3
"""Marca `verified: true` en todas las entradas del plan.

Diseñado para flujos batch donde la revisión humana es diferida (el usuario
confirma al correr el .command). Si el plan está vacío, exits con código 2.

Uso:  aprobar_plan.py <plan.json>  [--nota TEXTO]
"""
import argparse, json, sys
from pathlib import Path

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('plan', type=Path)
    ap.add_argument('--nota', default='aprobado en batch',
                    help='Texto para el campo note (default: "aprobado en batch").')
    args = ap.parse_args()
    data = json.loads(args.plan.read_text(encoding='utf-8'))
    entries = data.get('entries', [])
    if not entries:
        sys.stderr.write(f'ERROR: plan vacío. No hay marcadores que aprobar: {args.plan}\n')
        sys.exit(2)
    n = 0
    for e in entries:
        if not e.get('verified'):
            e['verified'] = True
            if not e.get('note'):
                e['note'] = args.nota
            n += 1
    args.plan.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n',
                         encoding='utf-8')
    print(f'Aprobadas {n}/{len(entries)} entradas en {args.plan.name}')

if __name__ == '__main__':
    main()
