#!/usr/bin/env python3
"""Selector de un PDF o una carpeta en macOS."""
import argparse
import subprocess
import sys
from pathlib import Path

DIALOGO = '''set tipo to button returned of (display dialog "Seleccione el material para revisar sus marcadores" buttons {"Cancelar", "Carpeta", "PDF"} default button "PDF" cancel button "Cancelar")
if tipo is "Carpeta" then
    return POSIX path of (choose folder with prompt "Elija la carpeta de libros")
else
    return POSIX path of (choose file with prompt "Elija el archivo PDF")
end if'''


def elegir():
    result = subprocess.run(['osascript', '-e', DIALOGO], capture_output=True, text=True)
    if result.returncode:
        if '-128' in result.stderr:
            return None
        raise ValueError(result.stderr.strip() or 'No se pudo abrir el selector de macOS.')
    path = result.stdout.rstrip('\r\n')
    if not path:
        return None
    return Path(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--aplicar', action='store_true', help='Guardar solo los planes completamente verificados.')
    parser.add_argument('--ruta', type=Path, help='Seleccionar por ruta, sin abrir el diálogo.')
    args = parser.parse_args()
    try:
        path = args.ruta or elegir()
        if path is None:
            print('Cancelado.')
            return 0
        from procesar_carpeta import listar_pdfs
        listar_pdfs(path)
        command = [sys.executable, str(Path(__file__).with_name('procesar_carpeta.py')), str(path)]
        if args.aplicar:
            command.append('--aplicar')
        return subprocess.run(command).returncode
    except (ValueError, OSError) as exc:
        print(f'Error: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
