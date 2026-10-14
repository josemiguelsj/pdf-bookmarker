import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import seleccionar
from procesar_carpeta import listar_pdfs

class Selector(unittest.TestCase):
    def test_archivo_seleccionado_no_incluye_sus_vecinos(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            chosen = root / "Libro con 'comillas'.PDF"
            chosen.touch()
            (root / 'Otro.pdf').touch()
            self.assertEqual(listar_pdfs(chosen), [chosen])
            self.assertEqual(len(listar_pdfs(root)), 2)
    def test_cancelar(self):
        with patch('seleccionar.subprocess.run', return_value=subprocess.CompletedProcess([], 1, '', 'User canceled. (-128)')):
            self.assertIsNone(seleccionar.elegir())
    def test_ruta_con_espacios(self):
        path = "/tmp/Una carpeta/Libro 'uno'.pdf"
        with patch('seleccionar.subprocess.run', return_value=subprocess.CompletedProcess([], 0, path+'\n', '')):
            self.assertEqual(seleccionar.elegir(), Path(path))
    def test_error_visible(self):
        with patch('seleccionar.subprocess.run', return_value=subprocess.CompletedProcess([], 1, '', 'error del selector')):
            with self.assertRaises(ValueError):
                seleccionar.elegir()
    def test_extension_incorrecta(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'libro.txt'
            path.touch()
            with self.assertRaises(ValueError):
                listar_pdfs(path)
if __name__ == '__main__':
    unittest.main()
