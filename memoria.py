"""Memoria local de correcciones explícitas, vinculada al PDF y al título."""
import argparse
import json
import os
from pathlib import Path
from corregir_marcadores import cargar_plan, leer_pdf, sha256, escribir_json


def ruta():
    return Path(os.environ.get('PDF_BOOKMARKER_MEMORY', Path.home() / '.local/share/pdf-bookmarker/memoria.json'))


def clave(fingerprint, entry):
    return json.dumps([fingerprint, entry.get('_memory_id'), entry['title'], entry['depth']], ensure_ascii=False)


def identificar(entries):
    parents = []
    seen = {}
    for entry in entries:
        depth = entry['depth']
        parents = parents[:depth]
        context = tuple(parents + [entry['title']])
        seen[context] = seen.get(context, 0) + 1
        entry['_memory_id'] = [list(context), seen[context]]
        parents.append(entry['title'])


def consultar(fingerprint, entry, memory=None):
    if memory is None:
        path = ruta()
        memory = json.loads(path.read_text()) if path.exists() else {}
    return memory.get(clave(fingerprint, entry))


def main():
    p = argparse.ArgumentParser(description='Registrar una corrección revisada contra el libro.')
    p.add_argument('pdf', type=Path)
    p.add_argument('plan', type=Path)
    p.add_argument('--entrada', type=int, required=True, help='Posición del marcador, desde 1.')
    p.add_argument('--pagina', type=int, required=True)
    p.add_argument('--evidencia', required=True, help='Encabezado observado y motivo de la corrección.')
    args = p.parse_args()
    data = cargar_plan(args.plan)
    fingerprint = sha256(args.pdf)
    if data.get('source_sha256') != fingerprint:
        p.error('La huella no coincide.')
    count = len(leer_pdf(args.pdf).pages)
    if data.get('page_count') != count or not 1 <= args.pagina <= count or not 1 <= args.entrada <= len(data['entries']):
        p.error('Entrada o página inválida.')
    if not args.evidencia.strip():
        p.error('La evidencia no puede quedar vacía.')
    identificar(data['entries'])
    entry = data['entries'][args.entrada - 1]
    correction = dict(page=args.pagina, verified=True, status='reviewed', evidence=dict(method='manual_review', title=entry['title'], page=args.pagina, source_sha256=fingerprint, detail=args.evidencia))
    path = ruta()
    memory = json.loads(path.read_text()) if path.exists() else {}
    memory[clave(fingerprint, entry)] = correction
    escribir_json(path, memory)
    entry.update(correction)
    escribir_json(args.plan, data)
    print('Corrección registrada. Se reutilizará solo para este contenido y título.')


if __name__ == '__main__':
    main()


def recordar_aplicacion(data, final_sha256):
    entries = [dict(e) for e in data['entries']]
    identificar(entries)
    path = ruta()
    memory = json.loads(path.read_text()) if path.exists() else {}
    for fingerprint in [data['source_sha256'], final_sha256]:
        for entry in entries:
            if entry.get('verified') is not True:
                continue
            evidence = dict(entry.get('evidence') or {})
            evidence.update(method='inherited_review', source_sha256=fingerprint, title=entry['title'], page=entry['page'], original_source_sha256=data['source_sha256'])
            memory[clave(fingerprint, entry)] = dict(page=entry['page'], verified=True, status='reviewed', evidence=evidence)
    escribir_json(path, memory)
