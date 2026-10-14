#!/usr/bin/env python3
"""Motor alternativo con respaldo, archivo temporal y las mismas comprobaciones."""
import sys


def escribir_pikepdf(source, stream, entries):
    try:
        import pikepdf
    except ImportError as exc:
        raise ValueError('Falta pikepdf para el motor alternativo.') from exc
    with pikepdf.open(source) as pdf:
        with pdf.open_outline() as outline:
            outline.root.clear()
            parents = []
            for entry in entries:
                item = pikepdf.OutlineItem(entry['title'], entry['page'] - 1)
                depth = entry['depth']
                if depth:
                    parents[depth - 1].children.append(item)
                else:
                    outline.root.append(item)
                parents = parents[:depth] + [item]
        pdf.Root.PageMode = pikepdf.Name('/UseOutlines')
        pdf.save(stream)


if __name__ == '__main__':
    from corregir_marcadores import main
    sys.argv = [sys.argv[0], 'aplicar', *sys.argv[1:], '--motor', 'pikepdf']
    sys.exit(main())
