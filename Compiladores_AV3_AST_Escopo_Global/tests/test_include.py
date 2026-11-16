"""Classificação contextual dos tokens de #include, sem perder a AST."""
from pathlib import Path
import json
import subprocess
import sys
import tempfile
import unittest

from compilador import analisar, categoria_exibicao, preparar_linha_token
from lexing.lexer import tokenizar


class TesteTokensInclude(unittest.TestCase):
    def test_tres_tokens_exatos_solicitados(self):
        for linguagem in ('c', None):
            with self.subTest(linguagem=linguagem):
                tokens, erros = tokenizar('#include <stdio.h>', linguagem)
                self.assertFalse(erros)
                self.assertEqual([(t.lexema, t.tipo) for t in tokens],
                                 [('#', 'PUNCTUATOR'), ('include', 'KEYWORD'), ('<stdio.h>', 'HEADER_NAME')])
                self.assertEqual([(t.linha, t.coluna, t.ordem) for t in tokens],
                                 [(1, 1, 1), (1, 2, 2), (1, 10, 3)])

    def test_terminal_tem_as_mesmas_classes(self):
        tokens, _ = tokenizar('#include <stdio.h>', 'c')
        self.assertEqual([preparar_linha_token(t, somente_ascii=True) for t in tokens],
                         ['- # -> PUNCTUATOR', '- include -> KEYWORD', '- <stdio.h> -> HEADER_NAME'])

    def test_cabecalho_local_entre_aspas(self):
        tokens, erros = tokenizar('#include "pasta/meu.h"', 'c')
        self.assertFalse(erros)
        self.assertEqual((tokens[2].lexema, tokens[2].tipo), ('"pasta/meu.h"', 'HEADER_NAME'))

    def test_espacos_comentarios_e_posicoes_sao_preservados(self):
        fonte = ' \t# /*antes*/ include /*nome*/ <stdio.h> /*depois*/\n  int x;'
        tokens, erros = tokenizar(fonte, 'c')
        self.assertFalse(erros)
        self.assertEqual([t.tipo for t in tokens[:3]], ['PUNCTUATOR', 'KEYWORD', 'HEADER_NAME'])
        self.assertEqual(tokens[0].coluna, 3)
        self.assertEqual(tokens[1].coluna, fonte.index('include') + 1)
        self.assertEqual(tokens[3].lexema, 'int')
        self.assertEqual((tokens[3].linha, tokens[3].coluna), (2, 3))

    def test_comentario_de_linha_apos_cabecalho_nao_vira_token(self):
        tokens, erros = tokenizar('#include<stdio.h> // comentario', 'c')
        self.assertFalse(erros)
        self.assertEqual(len(tokens), 3)

    def test_include_em_comentario_e_ignorado(self):
        tokens, erros = tokenizar('/* #include <stdio.h> */\nint x;', 'c')
        self.assertFalse(erros)
        self.assertEqual([t.lexema for t in tokens], ['int', 'x', ';'])

    def test_include_como_identificador_comum_nao_e_reservado_globalmente(self):
        r = analisar('#include <stdio.h>\nint include=0; void f(){include=1;}', 'c')
        self.assertFalse(r['erros_sintaticos'])
        self.assertFalse(r['erros_semanticos'])
        inclusoes = [t['tipo'] for t in r['tokens'] if t['lexema'] == 'include']
        self.assertEqual(inclusoes, ['KEYWORD', 'IDENTIFIER', 'IDENTIFIER'])
        self.assertEqual([s['lexema'] for s in r['simbolos']], ['include', 'f'])
        self.assertEqual(next(p for p in r['palavras_reservadas'] if p['lexema'] == 'include')['ocorrencias'], 1)


    def test_comparacoes_e_strings_fora_da_diretiva_mantem_suas_classes(self):
        tokens, erros = tokenizar('a < b > c; "<stdio.h>";', 'c')
        self.assertFalse(erros)
        self.assertNotIn('HEADER_NAME', [t.tipo for t in tokens])
        self.assertIn('STRING', [t.tipo for t in tokens])

    def test_continuacao_de_linha_e_formatos_de_quebra(self):
        for quebra in ('\n', '\r\n', '\r'):
            with self.subTest(quebra=repr(quebra)):
                fonte = '#include ' + chr(92) + quebra + '  <stdio.h>' + quebra + 'int x;'
                tokens, erros = tokenizar(fonte, 'c')
                self.assertFalse(erros)
                self.assertEqual((tokens[2].tipo, tokens[2].linha, tokens[2].coluna), ('HEADER_NAME', 2, 3))
                self.assertEqual((tokens[3].lexema, tokens[3].linha), ('int', 3))

    def test_digrafo_de_hash_preserva_lexema(self):
        tokens, erros = tokenizar('%:include <stdio.h>', 'c')
        self.assertFalse(erros)
        self.assertEqual([(t.lexema, categoria_exibicao(t)) for t in tokens],
                         [('%:', 'PUNCTUATOR'), ('include', 'KEYWORD'), ('<stdio.h>', 'HEADER_NAME')])

    def test_macro_como_argumento_e_outras_diretivas_continuam_aceitas(self):
        r = analisar('#define H <stdio.h>\n#include H\nint main(){return 0;}', 'c')
        self.assertFalse(r['erros_lexicos'])
        self.assertFalse(r['erros_sintaticos'])
        self.assertEqual(r['tokens'][0]['tipo'], 'PREPROCESSADOR')
        self.assertEqual([s['lexema'] for s in r['simbolos']], ['main'])

    def test_diretivas_parecidas_nao_sao_cortadas_como_include(self):
        tokens, erros = tokenizar('#include_next <stdio.h>', 'c')
        self.assertFalse(erros)
        self.assertEqual(len(tokens), 1)
        self.assertEqual(tokens[0].tipo, 'PREPROCESSADOR')

    def test_cabecalho_invalido_nao_engole_declaracao_seguinte(self):
        for diretiva in ('#include <stdio.h', '#include "meu.h', '#include <>', '#include ""', '#include'):
            with self.subTest(diretiva=diretiva):
                r = analisar(diretiva + '\nint valido=1;', 'c')
                self.assertTrue(r['erros_lexicos'])
                self.assertEqual([s['lexema'] for s in r['simbolos']], ['valido'])

    def test_tokens_extras_apos_cabecalho_sao_diagnosticados(self):
        r = analisar('#include <stdio.h> inesperado\nint main(){return 0;}', 'c')
        self.assertTrue(r['erros_lexicos'])
        self.assertIn('main', [s['lexema'] for s in r['simbolos']])

    def test_parser_mantem_include_e_funcao_na_ast(self):
        r = analisar('#include <stdio.h>\nint main(){int c=0;while(c<2)c++;return c;}', 'c')
        self.assertFalse(r['erros_sintaticos'])
        raiz = r['ast_estruturada']
        self.assertEqual([n['classe'] for n in raiz['filhos']], ['PREPROCESSADOR', 'FUNCAO'])
        self.assertEqual([n['classe'] for n in raiz['filhos'][0]['filhos']],
                         ['PUNCTUATOR', 'KEYWORD', 'HEADER_NAME'])

    def test_cli_e_json_exportam_a_classificacao_solicitada(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as pasta:
            fonte, saida = Path(pasta)/'include.c', Path(pasta)/'resultado.json'
            fonte.write_text('#include <stdio.h>\n', encoding='utf-8')
            p = subprocess.run([sys.executable, str(root/'compilador.py'), str(fonte),
                                '--apenas-tokens', '--ascii', '--json', str(saida)],
                               capture_output=True, text=True, encoding='utf-8')
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
            self.assertEqual(p.stdout.splitlines(),
                             ['- # -> PUNCTUATOR', '- include -> KEYWORD', '- <stdio.h> -> HEADER_NAME'])
            r = json.loads(saida.read_text(encoding='utf-8'))
        self.assertEqual([t['tipo'] for t in r['tokens']], ['PUNCTUATOR', 'KEYWORD', 'HEADER_NAME'])
        self.assertEqual(r['tabela_simbolos'], [])


if __name__ == '__main__':
    unittest.main()
