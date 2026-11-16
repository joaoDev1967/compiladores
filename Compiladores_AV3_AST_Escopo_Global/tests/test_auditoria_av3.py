"""Regressões dos casos independentes da auditoria da AV3."""
import unittest

from tests.suporte import analisar_fragmento as analisar
from lexing.lexer import tokenizar


class TesteAuditoriaAV3(unittest.TestCase):
    def assert_sem_erros(self, resultado):
        for fase in ('erros_lexicos', 'erros_sintaticos', 'erros_semanticos'):
            self.assertEqual(resultado[fase], [])





    def test_grafias_equivalentes_em_assinatura_c(self):
        resultado = analisar('signed long int f(long); long f(long int n) { int x = 1; }', 'c')
        self.assert_sem_erros(resultado)
        self.assertEqual([s['tipo_declarado'] for s in resultado['simbolos'] if s['lexema'] == 'f'],
                         ['signed long int', 'long'])

    def test_parametros_array_e_ponteiro_equivalentes_em_c(self):
        for tipo_array, tipo_ponteiro in (('int a[]', 'int *a'), ('int *a[]', 'int **a')):
            with self.subTest(array=tipo_array):
                fonte = f'int f({tipo_array}); int f({tipo_ponteiro}) {{ int x = 1; }}'
                self.assert_sem_erros(analisar(fonte, 'c'))
        resultado = analisar('int f(int a[][]); int f(int *a) { int x = 1; }', 'c')
        self.assertIn('incompatível', resultado['erros_semanticos'][0]['mensagem'])





    def test_literal_de_texto_inicializa_caracteres_em_c(self):
        fonte = 'const char *texto = "olá"; char buf[] = "oi"; texto = buf;'
        self.assert_sem_erros(analisar(fonte, 'c'))
        resultado = analisar('int x = "olá"; char *p = L"largo";', 'c')
        self.assertEqual(len(resultado['erros_semanticos']), 2)



    def test_recuperacao_na_mesma_linha_preserva_comandos(self):
        resultado = analisar('int x = 1 int y = 2; y = 3 y = 4;', 'c')
        self.assertEqual(len(resultado['erros_sintaticos']), 2)
        self.assertEqual([s['lexema'] for s in resultado['simbolos']], ['y'])
        self.assertEqual(len(resultado['ast_comandos']), 2)
        self.assertIn('NUM (4)', resultado['ast_comandos'][1])

    def test_tabela_contem_apenas_declaracoes_na_ordem(self):
        resultado = analisar('z = 0; int a; { float a; } int z;', 'c')
        linhas = resultado['tabela_simbolos']
        self.assertEqual([s['ordem'] for s in linhas], [1, 2, 3])
        self.assertEqual([(s['lexema'], s['categoria'], s['tipo_declarado']) for s in linhas],
                         [('a', 'Variável', 'int'),
                          ('a', 'Variável', 'float'), ('z', 'Variável', 'int')])
        self.assertEqual(resultado['tokens'][0]['lexema'], 'z')
        self.assertTrue(all('token' not in s for s in linhas))
        self.assertEqual([s['lexema'] for s in resultado['simbolos']], ['a', 'a', 'z'])
        self.assertIn("'z' utilizada sem declaração", resultado['erros_semanticos'][0]['mensagem'])
