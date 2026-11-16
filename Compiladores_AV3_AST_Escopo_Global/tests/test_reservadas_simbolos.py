"""Regressões da separação entre palavras reservadas e símbolos declarados."""
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from compilador import categoria_exibicao, mostrar
from tests.suporte import analisar_fragmento as analisar
from lexing.lexer import tokenizar
from lexing.tokens import RESERVADAS, RESERVADAS_C, RESERVADAS_JAVA
from semantica.analisador import TabelaSimbolos


class TesteReservadasForaDaTabela(unittest.TestCase):
    def test_todas_as_reservadas_ficam_fora_da_tabela(self):
        for linguagem, reservadas in ((None, RESERVADAS), ('c', RESERVADAS_C),
                                     ('java', RESERVADAS_JAVA)):
            with self.subTest(linguagem=linguagem):
                tokens, erros = tokenizar(' '.join(sorted(reservadas)), linguagem)
                self.assertFalse(erros)
                tabela = TabelaSimbolos(tokens)
                self.assertEqual(tabela.listar_tabela(), [])
                self.assertEqual(tabela.listar(), [])
                self.assertEqual(len(tabela.listar_reservadas()), len(reservadas))
                self.assertTrue(all(categoria_exibicao(t) == 'KEYWORD' for t in tokens))

    def test_analise_c_e_java_preserva_apenas_declaracoes(self):
        casos = [
            ('c', 'int main(void) { int contador=1; if (contador) { '
             'contador=contador+1; } return contador; }', ['main', 'contador']),
            ('java', 'public class Exemplo { public static void main(String[] args) { '
             'boolean ativo=true; int contador=1; if (ativo) { '
             'contador=contador+1; } return; } }',
             ['Exemplo', 'main', 'args', 'ativo', 'contador']),
            (None, 'int contador=1; float media=2.0f;', ['contador', 'media']),
        ]
        for linguagem, fonte, nomes in casos:
            with self.subTest(linguagem=linguagem):
                resultado = analisar(fonte, linguagem)
                self.assertFalse(resultado['erros_lexicos'])
                self.assertFalse(resultado['erros_sintaticos'])
                self.assertFalse(resultado['erros_semanticos'])
                linhas = resultado['tabela_simbolos']
                self.assertEqual([s['lexema'] for s in linhas], nomes)
                self.assertEqual([s['ordem'] for s in linhas], list(range(1, len(nomes) + 1)))
                self.assertEqual(linhas, [{k: v for k, v in s.items() if k != 'token'}
                                          for s in resultado['simbolos']])
                self.assertTrue(all(s['token'] == 'IDENTIFIER' for s in resultado['simbolos']))

    def test_frequencias_lexicas_permanecem_separadas(self):
        resultado = analisar('int a;\nint b; float c;', 'c')
        self.assertEqual([s['lexema'] for s in resultado['tabela_simbolos']], ['a', 'b', 'c'])
        self.assertEqual([(p['lexema'], p['ocorrencias'], p['linha'], p['coluna'])
                          for p in resultado['palavras_reservadas']],
                         [('int', 2, 1, 1), ('float', 1, 2, 8)])

    def test_identificadores_parecidos_e_reservadas_de_outra_linguagem(self):
        for linguagem, nomes in (
            ('c', ['ifx', 'returnValue', 'integer', 'IF', 'class', 'true']),
            ('java', ['ifx', 'returnValue', 'integer', 'IF', 'auto', 'restrict']),
        ):
            with self.subTest(linguagem=linguagem):
                resultado = analisar(' '.join('int ' + nome + ';' for nome in nomes), linguagem)
                self.assertFalse(resultado['erros_sintaticos'])
                self.assertEqual([s['lexema'] for s in resultado['tabela_simbolos']], nomes)

    def test_reservada_como_nome_invalido_nao_vira_simbolo(self):
        for linguagem in ('c', 'java'):
            with self.subTest(linguagem=linguagem):
                resultado = analisar('int if = 1; int valido = 2;', linguagem)
                self.assertTrue(resultado['erros_sintaticos'])
                self.assertEqual([s['lexema'] for s in resultado['tabela_simbolos']], ['valido'])

    def test_apenas_reservadas_produz_tabela_vazia_no_terminal(self):
        resultado = analisar('return;', 'c')
        self.assertEqual(resultado['tabela_simbolos'], [])
        self.assertEqual(resultado['simbolos'], [])
        saida = StringIO()
        with redirect_stdout(saida):
            mostrar(resultado, 'entrada.c', somente_ascii=True)
        self.assertIn('- return -> KEYWORD', saida.getvalue())
        self.assertIn('Nenhuma declaração registrada.', saida.getvalue())
        self.assertIn('Entradas na tabela: 0', saida.getvalue())


if __name__ == '__main__':
    unittest.main()
