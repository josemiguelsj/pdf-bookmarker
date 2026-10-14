import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pypdf import PdfReader, PdfWriter
from pypdf.generic import NameObject, DictionaryObject, DecodedStreamObject
from corregir_marcadores import aplicar, marcadores, firmas_paginas, sha256, escribir_json
from verificar_paginas import verificar
from extraer_de_indice import generar
from memoria import main as aprender


def pdf_texto(path, texts):
    writer = PdfWriter()
    font = DictionaryObject({NameObject('/Type'): NameObject('/Font'), NameObject('/Subtype'): NameObject('/Type1'), NameObject('/BaseFont'): NameObject('/Helvetica')})
    ref = writer._add_object(font)
    for text in texts:
        page = writer.add_blank_page(width=400, height=600)
        page[NameObject('/Resources')] = DictionaryObject({NameObject('/Font'): DictionaryObject({NameObject('/F1'): ref})})
        stream = DecodedStreamObject()
        lines = ['BT /F1 12 Tf 40 550 Td']
        for line in text.splitlines():
            line = line.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')
            lines += [f'({line}) Tj', '0 -18 Td']
        lines.append('ET')
        stream.set_data('\n'.join(lines).encode('ascii'))
        page[NameObject('/Contents')] = writer._add_object(stream)
    with path.open('wb') as f:
        writer.write(f)


class Regresiones(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.env = patch.dict(os.environ, {'PDF_BOOKMARKER_CACHE': str(self.root / 'cache'), 'PDF_BOOKMARKER_MEMORY': str(self.root / 'memoria.json')})
        self.env.start()
        self.pdf = self.root / "Libro con 'comillas'.pdf"
        self.plan = self.root / 'plan.json'
        pdf_texto(self.pdf, ['1. Vida y obra\nTexto del capitulo.', '2. Familia y escuela\nTexto.', 'INDICE GENERAL\n1. Vida y obra ...... 1\n2. Familia y escuela ...... 2'])

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()

    def crear_plan(self, entries):
        data = dict(schema=1, source_sha256=sha256(self.pdf), page_count=3, entries=entries)
        escribir_json(self.plan, data)
        return data

    def entry(self, title, page, depth=0, verified=False):
        return dict(title=title, page=page, depth=depth, verified=verified)

    def test_resuelve_raiz_y_no_impone_monotonia(self):
        self.crear_plan([self.entry('Indice general', 3, verified=True), self.entry('1. Vida y obra', 2)])
        verificar(self.pdf, self.plan)
        data = json.loads(self.plan.read_text())
        self.assertEqual([e['page'] for e in data['entries']], [3, 1])
        self.assertTrue(data['entries'][1]['verified'])

    def test_titulo_no_encontrado_no_se_aprueba(self):
        self.crear_plan([self.entry('1. Otro titulo', 2)])
        verificar(self.pdf, self.plan)
        entry = json.loads(self.plan.read_text())['entries'][0]
        self.assertFalse(entry['verified'])
        self.assertEqual(entry['page'], 2)

    def test_rechaza_pdf_distinto_sin_reatar_hash(self):
        self.crear_plan([self.entry('1. Vida y obra', 2)])
        original = self.plan.read_bytes()
        pdf_texto(self.pdf, ['Otro libro'])
        with self.assertRaises(ValueError):
            verificar(self.pdf, self.plan)
        self.assertEqual(self.plan.read_bytes(), original)

    def test_coincidencia_ambigua_permanece_pendiente(self):
        pdf_texto(self.pdf, ['1. Vida y obra', '1. Vida y obra', 'INDICE GENERAL'])
        self.crear_plan([self.entry('1. Vida y obra', 2)])
        verificar(self.pdf, self.plan)
        entry = json.loads(self.plan.read_text())['entries'][0]
        self.assertEqual(entry['candidates'], [1, 2])
        self.assertFalse(entry['verified'])

    def test_encabezado_en_varias_lineas(self):
        pdf_texto(self.pdf, ['1. Vida\ny obra', 'Otro texto', 'INDICE GENERAL'])
        self.crear_plan([self.entry('1. Vida y obra', 2)])
        verificar(self.pdf, self.plan)
        self.assertEqual(json.loads(self.plan.read_text())['entries'][0]['page'], 1)

    def test_indice_tiene_destino_fisico_y_no_estimado(self):
        data = generar(self.pdf, self.root / 'indice')
        self.assertEqual(data['entries'][0]['page'], 3)
        self.assertTrue(data['entries'][0]['verified'])
        self.assertIsNone(data['entries'][1]['page'])

    def test_aprobar_no_elude_revision(self):
        self.crear_plan([self.entry('1. Otro titulo', 2)])
        before = self.plan.read_bytes()
        result = subprocess.run([sys.executable, str(Path(__file__).resolve().parents[1] / 'aprobar_plan.py'), str(self.plan)], capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(before, self.plan.read_bytes())

    def test_memoria_reutiliza_correccion_con_contexto(self):
        self.crear_plan([self.entry('Titulo revisado', 2)])
        with patch.object(sys, 'argv', ['aprender', str(self.pdf), str(self.plan), '--entrada', '1', '--pagina', '1', '--evidencia', 'Encabezado visible en la pagina 1']):
            aprender()
        self.crear_plan([self.entry('Titulo revisado', 2)])
        verificar(self.pdf, self.plan)
        self.assertEqual(json.loads(self.plan.read_text())['entries'][0]['page'], 1)
        self.crear_plan([self.entry('Otra parte', 2), self.entry('Titulo revisado', 2, 1)])
        verificar(self.pdf, self.plan)
        self.assertFalse(json.loads(self.plan.read_text())['entries'][1]['verified'])

    def test_ambos_motores_conservan_paginas_y_destinos(self):
        for motor in ['pypdf', 'pikepdf']:
            with self.subTest(motor=motor):
                before = firmas_paginas(PdfReader(self.pdf))
                entries = [self.entry('Indice general', 3, verified=True), self.entry('1. Vida y obra', 1, verified=True), self.entry('Detalle', 1, 1, True)]
                self.crear_plan(entries)
                aplicar(SimpleNamespace(pdf=self.pdf, plan=self.plan, respaldo=None, verificar_imagenes='destinos', motor=motor))
                reader = PdfReader(self.pdf)
                self.assertEqual(firmas_paginas(reader), before)
                self.assertEqual(marcadores(reader), [{k: x[k] for k in ['title', 'page', 'depth']} for x in entries])
                self.assertTrue(list((self.root / 'Respaldo de marcadores').glob('*/informe.json')))

    def test_aplicar_rechaza_hash_ausente(self):
        data = self.crear_plan([self.entry('Titulo', 1, verified=True)])
        del data['source_sha256']
        escribir_json(self.plan, data)
        before = self.pdf.read_bytes()
        with self.assertRaises(ValueError):
            aplicar(SimpleNamespace(pdf=self.pdf, plan=self.plan, respaldo=None, verificar_imagenes=None))
        self.assertEqual(self.pdf.read_bytes(), before)

    def test_detecta_fuente_modificada_sin_cambiar_instrucciones(self):
        reader = PdfReader(self.pdf)
        before = firmas_paginas(reader)
        reader.pages[0]['/Resources']['/Font']['/F1'][NameObject('/BaseFont')] = NameObject('/Courier')
        self.assertNotEqual(before, firmas_paginas(reader))

    def test_revision_editada_invalida_evidencia_anterior(self):
        self.crear_plan([self.entry('1. Vida y obra', 2)])
        verificar(self.pdf, self.plan)
        data = json.loads(self.plan.read_text())
        data['entries'][0]['title'] = 'Encabezado inexistente'
        escribir_json(self.plan, data)
        verificar(self.pdf, self.plan)
        self.assertFalse(json.loads(self.plan.read_text())['entries'][0]['verified'])

    def test_revision_sobrevive_a_aplicacion_correcta(self):
        entries = [self.entry('Titulo revisado manualmente', 1, verified=True)]
        self.crear_plan(entries)
        aplicar(SimpleNamespace(pdf=self.pdf, plan=self.plan, respaldo=None, verificar_imagenes=None, motor='pypdf'))
        self.crear_plan([self.entry('Titulo revisado manualmente', 2)])
        verificar(self.pdf, self.plan)
        entry = json.loads(self.plan.read_text())['entries'][0]
        self.assertEqual(entry['page'], 1)
        self.assertTrue(entry['verified'])

    def test_carpeta_prepara_sin_modificar_pdf(self):
        from procesar_carpeta import main
        before = self.pdf.read_bytes()
        with patch.object(sys, 'argv', ['carpeta', str(self.root)]):
            main()
        self.assertEqual(self.pdf.read_bytes(), before)
        plan = self.root / '_pdf_bookmarker_tmp' / self.pdf.stem / 'plan_para_revisar.json'
        self.assertEqual(len(json.loads(plan.read_text())['entries']), 3)

    def test_plan_conocido_exige_huella_exacta(self):
        from corregir_marcadores import plan_conocido
        directory = self.root / 'planes_conocidos'
        data = self.crear_plan([self.entry('1. Vida y obra', 1, verified=True)])
        escribir_json(directory / 'ejemplo.json', data)
        self.assertIsNotNone(plan_conocido(sha256(self.pdf), 3, directory))
        self.assertIsNone(plan_conocido('0' * 64, 3, directory))
        self.assertIsNone(plan_conocido(sha256(self.pdf), 4, directory))


if __name__ == '__main__':
    unittest.main()
