"""Regressões dos casos independentes da auditoria da AV3."""
import unittest

from tests.suporte import analisar_fragmento as analisar
from lexing.lexer import tokenizar


class TesteAuditoriaAV3(unittest.TestCase):
    def assert_sem_erros(self, resultado):
        for fase in ('erros_lexicos', 'erros_sintaticos', 'erros_semanticos'):
            self.assertEqual(resultado[fase], [])

    def test_comentario_c_continuado_preserva_posicoes(self):
        for quebra in ('\n', '\r\n', '\r'):
            with self.subTest(quebra=quebra):
                fonte = quebra.join(('// comentário \\', 'fantasma = 9; \\',
                                     'outro = 10;', 'int valido = 1;'))
                resultado = analisar(fonte, 'c')
                self.assert_sem_erros(resultado)
                self.assertEqual([t['lexema'] for t in resultado['tokens']],
                                 ['int', 'valido', '=', '1', ';'])
                self.assertEqual([(t['linha'], t['coluna']) for t in resultado['tokens']],
                                 [(4, 1), (4, 5), (4, 12), (4, 14), (4, 15)])
        tokens_java, erros_java = tokenizar('// fim \\\nint valido = 1;', 'java')
        self.assertFalse(erros_java)
        self.assertEqual(tokens_java[0].linha, 2)

    def test_digrafos_do_c_geram_tokens_e_escopos_corretos(self):
        resultado = analisar('%:define K 1\nint main(void) <% int v<:2:>; return 0; %>', 'c')
        self.assert_sem_erros(resultado)
        self.assertEqual(resultado['tokens'][0]['tipo'], 'PREPROCESSADOR')
        tipos = {t['lexema']: t['tipo'] for t in resultado['tokens']}
        self.assertEqual([tipos[op] for op in ('<%', '%>', '<:', ':>')],
                         ['LBRACE', 'RBRACE', 'LBRACKET', 'RBRACKET'])
        tokens_c, _ = tokenizar('a %:%: b', 'c')
        self.assertEqual((tokens_c[1].lexema, tokens_c[1].tipo), ('%:%:', 'TOKEN_PASTE'))
        tokens_java, _ = tokenizar('<%', 'java')
        self.assertEqual([t.tipo for t in tokens_java], ['LT', 'MOD'])

    def test_bloco_de_texto_java_invalido_e_recuperacao(self):
        resultado = analisar('String texto = """\n  a\\q\n  """; int ok = 1;', 'java')
        self.assertEqual(len(resultado['erros_lexicos']), 1)
        self.assertIn('Escape inválido', resultado['erros_lexicos'][0]['mensagem'])
        self.assertEqual([s['lexema'] for s in resultado['simbolos']], ['ok'])

    def test_bloco_de_texto_java_aceita_escapes_validos(self):
        fonte = 'String texto = """\n  a\\s' + '\\' + '\r\n  b\\\\q\n  """;'
        self.assert_sem_erros(analisar(fonte, 'java'))

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

    def test_metodo_java_acessa_campo_posterior_e_preserva_ordem(self):
        fonte = 'class Main { void f(int p) { int x = total; total = x + p; } int total = 1; }'
        resultado = analisar(fonte, 'java')
        self.assert_sem_erros(resultado)
        self.assertEqual([s['lexema'] for s in resultado['simbolos']],
                         ['Main', 'f', 'p', 'x', 'total'])
        self.assertIn('ID (x)', resultado['ast_comandos'][0])
        self.assertIn('ID (total)', resultado['ast_comandos'][-1])

    def test_java_campo_e_metodo_com_mesmo_nome(self):
        for membros in ('int total = 1; int total() { int valor = total; }',
                        'int total() { int valor = total; } int total = 1;'):
            with self.subTest(membros=membros):
                resultado = analisar(f'class Main {{ {membros} }}', 'java')
                self.assert_sem_erros(resultado)
                self.assertCountEqual([s['categoria'] for s in resultado['simbolos']
                                       if s['lexema'] == 'total'], ['Variável', 'Função'])
        resultado = analisar('class Main { int total; int total; }', 'java')
        self.assertIn('duplicada', resultado['erros_semanticos'][0]['mensagem'])

    def test_array_c_rejeita_atribuicao_e_parametro_ajusta_tipo(self):
        resultado = analisar('int a[2]; int b[2]; a = b;', 'c')
        self.assertEqual(len(resultado['erros_semanticos']), 1)
        self.assertIn('Arrays em C', resultado['erros_semanticos'][0]['mensagem'])
        resultado = analisar('int f(int a[]) { int b[2]; a = b; }', 'c')
        self.assert_sem_erros(resultado)
        self.assert_sem_erros(analisar('int[] a = null; int[] b = null; a = b;', 'java'))

    def test_modulo_distingue_reais_c_e_java(self):
        fonte = 'double x = 5.0 % 2.0; int y = 5 % 2;'
        resultado = analisar(fonte, 'c')
        self.assertEqual(len(resultado['erros_semanticos']), 1)
        self.assertIn("Operação '%' inválida", resultado['erros_semanticos'][0]['mensagem'])
        self.assert_sem_erros(analisar(fonte, 'java'))

    def test_literal_de_texto_inicializa_caracteres_em_c(self):
        fonte = 'const char *texto = "olá"; char buf[] = "oi"; texto = buf;'
        self.assert_sem_erros(analisar(fonte, 'c'))
        resultado = analisar('int x = "olá"; char *p = L"largo";', 'c')
        self.assertEqual(len(resultado['erros_semanticos']), 2)

    def test_final_java_local_parametro_e_campo_inicializado(self):
        fonte = ('class Main { void f(final int p) { final int x = 1; x = 2; '
                 'p = 3; campo = 4; } final int campo = 5; }')
        resultado = analisar(fonte, 'java')
        erros = resultado['erros_semanticos']
        self.assertEqual(len(erros), 3)
        for erro, nome in zip(erros, ('x', 'p', 'campo')):
            self.assertIn(f"final '{nome}'", erro['mensagem'])

    def test_final_java_sem_inicializador_aceita_um_valor_por_ramo(self):
        fonte = 'boolean cond = true; final int x; if (cond) x = 1; else x = 2;'
        self.assert_sem_erros(analisar(fonte, 'java'))
        for caso in (fonte + ' x = 3;', 'final int x; x = 1; x = 3;'):
            resultado = analisar(caso, 'java')
            self.assertEqual(len(resultado['erros_semanticos']), 1)
            self.assertIn("final 'x'", resultado['erros_semanticos'][0]['mensagem'])

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
