"""Cobertura da exibicao solicitada: lexema -> classe amigavel."""
from contextlib import redirect_stdout
from io import StringIO
import json
from pathlib import Path
import os
import re
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
from compilador import (categoria_exibicao, mostrar, mostrar_tokens,
                        preparar_linha_token)
from tests.suporte import analisar_fragmento as analisar
from lexing.lexer import tokenizar


class TesteFormatacaoTokens(unittest.TestCase):
    def test_exemplo_exatamente_como_imagem(self):
        tokens, erros = tokenizar('if else while contador')
        self.assertFalse(erros)
        linhas = [preparar_linha_token(t) for t in tokens]
        self.assertEqual(linhas, [
            '• if → KEYWORD',
            '• else → KEYWORD',
            '• while → KEYWORD',
            '• contador → ID',
        ])

    def test_tipos_internos_continuam_preservados(self):
        tokens, _ = tokenizar('if else while contador')
        self.assertEqual([t.tipo for t in tokens],
                         ['IF', 'ELSE', 'WHILE', 'IDENTIFIER'])

    def test_numeros_operadores_e_delimitadores(self):
        tokens, _ = tokenizar('int contador = 5;')
        self.assertEqual([categoria_exibicao(t) for t in tokens],
                         ['KEYWORD', 'ID', 'OPERATOR', 'NUMBER', 'DELIMITER'])

    def test_string_caractere_e_preprocessador(self):
        tokens, _ = tokenizar('#include <stdio.h>\nchar c = \'x\'; "teste"')
        self.assertEqual([categoria_exibicao(t) for t in tokens],
                         ['PUNCTUATOR', 'KEYWORD', 'HEADER_NAME', 'KEYWORD', 'ID', 'OPERATOR',
                          'CHAR', 'DELIMITER', 'STRING'])

    def test_palavras_reservadas_c_e_java(self):
        tokens, _ = tokenizar('public class Exemplo { int total = 1; }')
        self.assertEqual([categoria_exibicao(t) for t in tokens][:3],
                         ['KEYWORD', 'KEYWORD', 'ID'])

    def test_fallback_cp1252(self):
        tok, _ = tokenizar('if contador')
        self.assertEqual(preparar_linha_token(tok[0], codificacao='cp1252'),
                         '- if -> KEYWORD')
        self.assertEqual(preparar_linha_token(tok[1], somente_ascii=True),
                         '- contador -> ID')

    def test_mostrar_tokens_simples_e_detalhados(self):
        dados = analisar('int contador = 1;')
        stdout = StringIO()
        with redirect_stdout(stdout):
            mostrar_tokens(dados['tokens'])
        self.assertIn('• contador → ID', stdout.getvalue())
        self.assertNotIn('Ordem', stdout.getvalue())
        stdout = StringIO()
        with redirect_stdout(stdout):
            mostrar_tokens(dados['tokens'], detalhados=True)
        self.assertIn('Ordem', stdout.getvalue())
        self.assertIn('IDENTIFIER', stdout.getvalue())
        self.assertIn('Linha', stdout.getvalue())

    def test_saida_integral_mantem_tabela_ast_e_semantica(self):
        r = analisar('int contador=1; contador=contador+2;')
        stdout = StringIO()
        with redirect_stdout(stdout):
            mostrar(r, 'teste.c')
        saida = stdout.getvalue()
        self.assertIn('• contador → ID', saida)
        self.assertIn('TABELA DE SÍMBOLOS', saida)
        self.assertIn('ANÁLISE SINTÁTICA', saida)
        self.assertIn('ANÁLISE SEMÂNTICA', saida)

    def _cli(self, *args, encoding='utf-8'):
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = encoding
        return subprocess.run([sys.executable, str(ROOT/'compilador.py'), *map(str,args)],
                              cwd=ROOT, capture_output=True, text=True, encoding=encoding,
                              errors='replace', env=env)

    def test_cli_apenas_tokens(self):
        p = self._cli('exemplos/demonstracao_tokens.c', '--apenas-tokens')
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn('• if → KEYWORD', p.stdout)
        self.assertIn('• else → KEYWORD', p.stdout)
        self.assertIn('• while → KEYWORD', p.stdout)
        self.assertIn('• contador → ID', p.stdout)
        self.assertNotIn('TABELA DE SÍMBOLOS', p.stdout)

    def test_cli_conteudo_e_diagnosticos_por_secao(self):
        codigo = ('int main(void) {\n int x = 1;\n int invalido = 0x;\n'
                  ' x = 2 + ;\n ausente = 1;\n return x;\n}\n')
        with tempfile.TemporaryDirectory() as pasta:
            fonte = Path(pasta) / 'entrada.c'
            saida_json = Path(pasta) / 'resultado.json'
            fonte.write_text(codigo, encoding='utf-8')
            p = self._cli(fonte, '--json', saida_json)
            self.assertTrue(saida_json.is_file())
            dados = json.loads(saida_json.read_text(encoding='utf-8'))
        self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
        partes = re.split(r'^\[(\d+)\] ', p.stdout, flags=re.MULTILINE)
        secoes = dict(zip(partes[1::2], partes[2::2]))
        self.assertEqual(list(secoes), [str(i) for i in range(1, 9)])
        self.assertIn('• ausente → ID', secoes['1'])
        self.assertNotIn('ausente', secoes['2'])
        self.assertNotIn('invalido', secoes['2'])
        self.assertNotIn('IDENTIFIER', secoes['2'])
        self.assertNotIn('Palavra reservada', secoes['2'])
        self.assertEqual([s['lexema'] for s in dados['tabela_simbolos']], ['main', 'x'])
        self.assertEqual(re.findall(r'^\s+\d+  (\S+)', secoes['2'], re.MULTILINE),
                         ['main', 'x'])
        self.assertIn('Declaracao', secoes['3'])
        for numero, fase in [('4', 'LÉXICO'), ('5', 'SINTÁTICO'), ('6', 'SEMÂNTICO')]:
            self.assertEqual(re.findall(r'\[ERRO (.*?)\]', secoes[numero]), [fase])
        for numero in ('1', '2', '3', '7', '8'):
            self.assertNotIn('[ERRO ', secoes[numero])
        self.assertIn('Erros: 3', secoes['7'])
        self.assertIn('Entradas na tabela: 2', secoes['7'])
        self.assertNotIn('resultado.json', secoes['7'])
        self.assertIn('resultado.json', secoes['8'])

    def test_cli_apenas_tokens_com_json_preserva_saida_lexica(self):
        with tempfile.TemporaryDirectory() as pasta:
            fonte = Path(pasta) / 'entrada.c'
            saida_json = Path(pasta) / 'resultado.json'
            fonte.write_text('int invalido = 0x;\nausente = 1;\n', encoding='utf-8')
            tokens = self._cli(fonte, '--apenas-tokens')
            exportacao = self._cli(fonte, '--apenas-tokens', '--json', saida_json)
            dados = json.loads(saida_json.read_text(encoding='utf-8'))
        self.assertEqual(tokens.returncode, 1)
        self.assertEqual(exportacao.returncode, tokens.returncode)
        self.assertEqual(exportacao.stdout, tokens.stdout)
        self.assertEqual(exportacao.stderr, tokens.stderr)
        self.assertIn('[ERRO LÉXICO]', exportacao.stderr)
        self.assertNotIn('[ERRO SEMÂNTICO]', exportacao.stderr)
        self.assertEqual(len(dados['erros_lexicos']), 1)
        self.assertEqual(len(dados['erros_semanticos']), 1)

    def test_cli_detalhado_e_sem_tokens(self):
        p = self._cli('exemplos/correto.c', '--tokens-detalhados')
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn('Ordem  Tipo', p.stdout)
        p = self._cli('exemplos/correto.c', '--sem-tokens')
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertNotIn('• int → KEYWORD', p.stdout)
        self.assertIn('TABELA DE SÍMBOLOS', p.stdout)

    def test_cli_cp1252_usa_ascii(self):
        p = self._cli('exemplos/demonstracao_tokens.c', '--apenas-tokens', encoding='cp1252')
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn('- if -> KEYWORD', p.stdout)
        self.assertIn('- contador -> ID', p.stdout)
        self.assertNotIn('Traceback', p.stderr)


if __name__ == '__main__':
    unittest.main()
