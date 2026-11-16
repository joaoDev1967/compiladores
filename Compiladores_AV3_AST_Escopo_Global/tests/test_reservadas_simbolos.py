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
from lexing.tokens import RESERVADAS, RESERVADAS_C
from semantica.analisador import TabelaSimbolos


class TesteReservadasForaDaTabela(unittest.TestCase):


    def test_frequencias_lexicas_permanecem_separadas(self):
        resultado = analisar('int a;\nint b; float c;', 'c')
        self.assertEqual([s['lexema'] for s in resultado['tabela_simbolos']], ['a', 'b', 'c'])
        self.assertEqual([(p['lexema'], p['ocorrencias'], p['linha'], p['coluna'])
                          for p in resultado['palavras_reservadas']],
                         [('int', 2, 1, 1), ('float', 1, 2, 8)])



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
