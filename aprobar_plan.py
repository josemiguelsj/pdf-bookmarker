#!/usr/bin/env python3
"""Comprueba la revisión existente. Nunca convierte pendientes en verificados."""
import argparse
from pathlib import Path
from corregir_marcadores import cargar_plan, validar_plan


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('plan', type=Path)
    p.add_argument('--nota', help='Compatibilidad. No modifica el plan.')
    args = p.parse_args()
    data = cargar_plan(args.plan)
    try:
        validar_plan(data.get('entries'), data.get('page_count'))
    except ValueError as exc:
        p.exit(1, f'Error: {exc}\n')
    print('Todas las entradas ya están revisadas. El plan no se modificó.')


if __name__ == '__main__':
    main()
