"""Regressões descobertas na revisão da tabela e do fluxo do barema."""
from contextlib import redirect_stdout
from io import StringIO
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if not (ROOT / "compilador.py").is_file():
    raise ModuleNotFoundError(
        "compilador.py nao encontrado em %s. "
        "Entre na pasta Compiladores_AV3_Revisado (onde esta o compilador.py) "
        "e rode: python -m unittest discover -s tests -t . -v"
        % ROOT
    )
from compilador import mostrar
from tests.suporte import analisar_fragmento as analisar
from lexing.lexer import tokenizar


def simbolos(resultado):
    return {s['lexema']: s for s in resultado['simbolos']}


def ambiente_utf8():
    env = os.environ.copy()
    env['PYTHONIOENCODING'] = 'utf-8'
    return env


class TesteTabelaRevisada(unittest.TestCase):

    def test_identificador_invalido_nao_vira_simbolo(self):
        r = analisar('int $indevido; int valido=1;', 'c')
        self.assertEqual(len(r['erros_lexicos']), 1)
        self.assertNotIn('$indevido', simbolos(r))
        self.assertEqual(simbolos(r)['valido']['tipo_declarado'], 'int')

    def test_historico_em_ordem_no_terminal(self):
        r = analisar('int a; int b; { float b; char a; }', 'c')
        stdout = StringIO()
        with redirect_stdout(stdout):
            mostrar(r, 'entrada.c', sem_tokens=True)
        texto = stdout.getvalue().split('[2]')[1].split('[3]')[0]
        linhas = [linha.split() for linha in texto.splitlines() if linha.lstrip()[:1].isdigit()]
        self.assertEqual([(int(l[0]), l[1]) for l in linhas],
                         [(1, 'a'), (2, 'b'), (3, 'b'), (4, 'a')])
        self.assertEqual([(l[1], l[3]) for l in linhas if l[2] == 'Variável'],
                         [('a', 'int'), ('b', 'int'), ('b', 'float'), ('a', 'char')])

    def test_categoria_e_tipo_do_typedef_sobrevivem_a_sombra(self):
        r = analisar('typedef int T; { float T = 1.0f; T = 2.0f; } T fora = 3;', 'c')
        self.assertFalse(r['erros_sintaticos'] or r['erros_semanticos'])
        t = r['simbolos']
        declaracoes_t = [s for s in t if s['lexema'] == 'T']
        self.assertEqual([(s['categoria'], s['tipo_declarado']) for s in declaracoes_t],
                         [('Tipo', 'int'), ('Variável', 'float')])
        self.assertNotEqual(declaracoes_t[0]['escopo'], declaracoes_t[1]['escopo'])
        self.assertEqual(simbolos(r)['fora']['tipo_declarado'], 'int')

    def test_typedef_local_nao_vaza(self):
        r = analisar('{ typedef int T; T dentro = 1; } T fora; int ok=2;', 'c')
        self.assertEqual(len(r['erros_sintaticos']), 1)
        t = simbolos(r)
        self.assertEqual(t['dentro']['tipo_declarado'], 'int')
        self.assertNotIn('fora', t)
        self.assertEqual(t['ok']['tipo_declarado'], 'int')

    def test_parametros_preservam_tipo_e_dimensoes(self):
        r = analisar('int f(unsigned long n, int a[5][6], int *p) { unsigned long z = n+1; }', 'c')
        self.assertFalse(r['erros_sintaticos'] or r['erros_semanticos'])
        t = simbolos(r)
        self.assertEqual([t[n]['tipo_declarado'] for n in ('n', 'a', 'p')],
                         ['unsigned long', 'int[][]', 'int*'])

    def test_prototipo_e_definicao_compativeis(self):
        r = analisar('int f(int anterior); int f(int valor) { int x=valor; } anterior=3;', 'c')
        t = r['simbolos']
        self.assertEqual(len([s for s in t if s['lexema'] == 'f']), 2)
        anterior = next(s for s in t if s['lexema'] == 'anterior')
        valor = next(s for s in t if s['lexema'] == 'valor')
        self.assertIn('/prototipo', anterior['escopo'])
        self.assertIn('/funcao', valor['escopo'])
        self.assertEqual(len(r['erros_semanticos']), 1)
        self.assertIn("'anterior'", r['erros_semanticos'][0]['mensagem'])

    def test_prototipo_incompativel_e_definicao_duplicada(self):
        for codigo, esperado in (
            ('int f(int n); float f(int n) { int z=1; }', 'incompatível'),
            ('int f(int n) { int z=1; } int f(int n) { int y=2; }', 'duplicada'),
        ):
            with self.subTest(codigo=codigo):
                r = analisar(codigo, 'c')
                self.assertEqual(len([s for s in r['simbolos'] if s['lexema'] == 'f']), 1)
                self.assertIn(esperado, r['erros_semanticos'][0]['mensagem'])

    def test_assinatura_invalida_nao_cadastra_funcao_ou_parametro(self):
        r = analisar('int f(int x)\nint ok=1;\nint g(int n, ) { }', 'c')
        self.assertEqual(len(r['erros_sintaticos']), 2)
        t = simbolos(r)
        self.assertTrue(all(n not in t for n in ('f', 'g', 'x', 'n')))
        self.assertEqual(t['ok']['tipo_declarado'], 'int')



class TesteLexicoRevisado(unittest.TestCase):


    def test_diretiva_continuada_e_posicao_com_crlf_e_cr(self):
        codigo = '#define SOMA 1 + ' + chr(92) + '\r\n 2\r\n\tint x;\rint y;'
        tokens, erros = tokenizar(codigo, 'c')
        self.assertFalse(erros)
        self.assertEqual(tokens[0].lexema, codigo[:codigo.index('\r\n\t')])
        self.assertEqual([(t.linha, t.coluna) for t in tokens if t.lexema == 'int'], [(3, 2), (4, 1)])

    def test_numericos_hex_mais_adicao_e_expoente(self):
        tokens, erros = tokenizar('0xFE+1 0x1.fp-2 1e+; 08; 1.0LL;', 'c')
        self.assertEqual([t.lexema for t in tokens[:4]], ['0xFE', '+', '1', '0x1.fp-2'])
        self.assertEqual([t.lexema for t in tokens if t.tipo == 'INVALID_NUMBER'], ['1e+', '08', '1.0LL'])
        self.assertEqual(len(erros), 3)


    def test_escapes_invalidos_e_char_octal(self):
        tokens, erros = tokenizar(r"""'\141' "\q"; int x;""", 'c')
        self.assertEqual((tokens[0].tipo, tokens[1].tipo), ('CHAR_LITERAL', 'INVALID_LITERAL'))
        self.assertEqual(len(erros), 1)
        self.assertEqual(tokens[-2].lexema, 'x')


class TesteFluxoRevisado(unittest.TestCase):
    def test_falta_ponto_virgula_preserva_declaracao_seguinte(self):
        r = analisar('int falhou = 1\nint valido = 2;\nvalido = valido + 1;', 'c')
        self.assertEqual(len(r['erros_sintaticos']), 1)
        self.assertEqual(len(r['ast_comandos']), 2)
        self.assertNotIn('falhou', simbolos(r))

    def test_for_incompleto_nao_cadastra_variavel_do_cabecalho(self):
        r = analisar('int n=0; for (int i=0; i<4) { n=1; } int z=2;', 'c')
        self.assertEqual(len(r['erros_sintaticos']), 1)
        self.assertNotIn('i', simbolos(r))
        self.assertEqual(simbolos(r)['z']['tipo_declarado'], 'int')



    def test_tokens_detalhados_sem_truncar_e_erro_lexico_visivel(self):
        with tempfile.TemporaryDirectory() as pasta:
            caminho = Path(pasta) / 'fonte com espaços.c'
            nome = 'identificador_com_mais_de_26_caracteres'
            caminho.write_text(f'int {nome}=1e+;', encoding='utf-8')
            p = subprocess.run([sys.executable, str(ROOT / 'compilador.py'), str(caminho),
                                '--apenas-tokens', '--tokens-detalhados'],
                               capture_output=True, text=True, encoding='utf-8',
                               env=ambiente_utf8())
            self.assertEqual(p.returncode, 1)
            self.assertIn(nome, p.stdout)
            self.assertIn('1e+', p.stderr)

    def test_cli_le_fonte_em_codificacoes_de_windows(self):
        with tempfile.TemporaryDirectory() as pasta:
            caminho = Path(pasta) / 'fonte com acentos.c'
            for encoding in ('utf-8-sig', 'utf-16', 'cp1252'):
                with self.subTest(encoding=encoding):
                    caminho.write_bytes('/* oração */ int valor=1;'.encode(encoding))
                    p = subprocess.run([sys.executable, str(ROOT / 'compilador.py'), str(caminho)],
                                       capture_output=True, text=True, encoding='utf-8',
                                       env=ambiente_utf8())
                    self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
                    self.assertIn('valor → ID', p.stdout)

    def test_exportacao_preserva_arquivo_fonte(self):
        with tempfile.TemporaryDirectory() as pasta:
            caminho = Path(pasta) / 'fonte.c'
            codigo = 'int x=1;'
            caminho.write_text(codigo, encoding='utf-8')
            p = subprocess.run([sys.executable, str(ROOT / 'compilador.py'), str(caminho),
                                '--json', str(caminho)],
                               capture_output=True, text=True, encoding='utf-8',
                               env=ambiente_utf8())
            self.assertEqual(p.returncode, 2)
            self.assertEqual(caminho.read_text(encoding='utf-8'), codigo)


if __name__ == '__main__':
    unittest.main()
