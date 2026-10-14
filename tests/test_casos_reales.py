import unittest
from verificar_paginas import candidatos,indexar_encabezados

class CasosReales(unittest.TestCase):
    def test_marcador_del_indice_no_se_excluye(self):
        self.assertEqual(candidatos('TABLE OF CONTENTS',['TABLE OF CONTENTS\nChapter One ..... 1']),[1])
    def test_indice_no_verifica_un_capitulo(self):
        self.assertEqual(candidatos('Chapter One',['TABLE OF CONTENTS\nChapter One']),[])
    def test_errata_corto(self):
        self.assertEqual(candidatos('ERRATA',['ERRATA\nCorrections']),[1])
    def test_numeracion_omitida_en_encabezado(self):
        pages=['CONTENTS\nII. THE RATIO AND THE CLASSICAL INVESTIGATION 8','Chapter Two\nTHE RATIO AND THE CLASSICAL\nINVESTIGATION']
        self.assertEqual(candidatos('II. THE RATIO AND THE CLASSICAL INVESTIGATION',pages),[2])
    def test_numero_de_nota_adherido(self):
        self.assertEqual(candidatos('RULES OF THE PROFESSOR OF CASES OF CONSCIENCE',['RULES OF THE PROFESSOR OF\nCASES OF CONSCIENCE41']),[1])
    def test_numero_de_nota_no_elimina_anno(self):
        self.assertEqual(candidatos('The Ratio of 1599',['The Ratio of 1599']),[1])
    def test_duplicado_sigue_ambiguo(self):
        self.assertEqual(candidatos('II. Heading for a chapter',['Heading for a chapter','Heading for a chapter']),[1,2])

if __name__ == '__main__':
    unittest.main()
