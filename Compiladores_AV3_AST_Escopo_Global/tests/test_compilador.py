"""Testes unitários e integração dos critérios da AV3."""
import json
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
from tests.suporte import analisar_fragmento as analisar
from lexing.lexer import tokenizar


class TesteLexico(unittest.TestCase):
    def test_palavras_reservadas_e_identificadores(self):
        ts, es = tokenizar('int total = 10; if (total > 1) return total;')
        self.assertFalse(es)
        self.assertEqual([t.tipo for t in ts[:4]], ['INT', 'IDENTIFIER', 'ASSIGN', 'NUMBER'])
        self.assertIn('IF', [t.tipo for t in ts])
        self.assertIn('RETURN', [t.tipo for t in ts])

    def test_lexema_numero_nao_convertido(self):
        ts, _ = tokenizar('int x = 0007; float y = 1.25e+2;')
        self.assertIn('0007', [t.lexema for t in ts])
        self.assertIn('1.25e+2', [t.lexema for t in ts])

    def test_operadores_multicaracter(self):
        ts, es = tokenizar('x <<= 2; if (x >= 2 && x != 3) x++;')
        self.assertFalse(es)
        for op in ['LSHIFT_ASSIGN', 'GE', 'AND', 'NE', 'INCREMENT']:
            self.assertIn(op, [t.tipo for t in ts])

    def test_comentarios_ignorados_e_linhas(self):
        ts, es = tokenizar('int a; // comentario\n/* duas\nlinhas */ int b;')
        self.assertFalse(es)
        self.assertEqual([t.lexema for t in ts], ['int','a',';','int','b',';'])
        self.assertEqual(ts[3].linha, 3)

    def test_strings_e_caracteres_com_escape(self):
        ts, es = tokenizar('char c = \'\\n\'; String s = "a\\"b";')
        self.assertFalse(es)
        self.assertEqual([t.tipo for t in ts].count('CHAR_LITERAL'), 1)
        self.assertIn('"a\\"b"', [t.lexema for t in ts])

    def test_preprocessador_c(self):
        ts, es = tokenizar('#include <stdio.h>\nint a;')
        self.assertFalse(es)
        self.assertEqual([t.tipo for t in ts[:3]], ['PUNCTUATOR', 'KEYWORD', 'HEADER_NAME'])
        self.assertEqual(ts[3].linha, 2)

    def test_caractere_ilegal(self):
        _, es = tokenizar('int a = 4 @ 5;')
        self.assertEqual(len(es), 1)
        self.assertIn('@', es[0].mensagem)

    def test_string_nao_fechada(self):
        _, es = tokenizar('String s = "aberto;\nint x = 2;')
        self.assertEqual(len(es), 1)
        self.assertEqual(es[0].linha, 1)

    def test_comentario_nao_fechado(self):
        _, es = tokenizar('int a; /* nao terminou')
        self.assertEqual(len(es), 1)
        self.assertIn('Comentário', es[0].mensagem)

    def test_lexer_nao_vaza_numero_de_linha(self):
        t1, _ = tokenizar('int a;\nint b;')
        t2, _ = tokenizar('int c;')
        self.assertEqual(t1[-1].linha, 2)
        self.assertEqual(t2[0].linha, 1)


    def test_crlf_linhas(self):
        ts, es = tokenizar('int a;\r\nint b;')
        self.assertFalse(es)
        self.assertEqual(ts[3].linha, 2)



class TesteSimbolos(unittest.TestCase):
    def test_simbolos_ordem_e_tipos(self):
        r = analisar('int x = 1; float y = 2; x = 3;')
        nomes = [s['lexema'] for s in r['simbolos']]
        self.assertEqual(nomes, ['x','y'])
        x = next(s for s in r['simbolos'] if s['lexema']=='x')
        self.assertEqual((x['ordem'], x['tipo_declarado'], x['escopo']), (1, 'int', 'global'))
        self.assertEqual([p['lexema'] for p in r['palavras_reservadas']], ['int', 'float'])

    def test_palavras_reservadas_tabela(self):
        r = analisar('int x=2; return 0;')
        retorno = next(p for p in r['palavras_reservadas'] if p['lexema'] == 'return')
        self.assertEqual(retorno['token'], 'RETURN')
        self.assertNotIn('return', [s['lexema'] for s in r['simbolos']])

    def test_repeticao_nao_duplica_identificador(self):
        r = analisar('int a=1; a=a+2;')
        self.assertEqual(len([s for s in r['simbolos'] if s['lexema']=='a']),1)
        ocorrencias = [t for t in r['tokens'] if t['tipo'] == 'IDENTIFIER' and t['lexema'] == 'a']
        self.assertEqual(len(ocorrencias), 3)

    def test_parametros_constam_da_tabela(self):
        r = analisar('int soma(int a, int b) { int c = a+b; return c; }')
        self.assertEqual(r['erros_semanticos'], [])
        self.assertEqual(next(s for s in r['simbolos'] if s['lexema']=='b')['tipo_declarado'],'int')


class TesteSintatico(unittest.TestCase):
    def test_ast_atribuicao_exigida_no_barema(self):
        r = analisar('int x; int a=5; x = a + 5;')
        arvore = r['ast_comandos'][-1]
        for trecho in ['Atribuicao', 'ID (x)', 'OP_ATRIB (=)', 'Expressao (+)', 'ID (a)', 'NUM (5)']:
            self.assertIn(trecho, arvore)
        self.assertFalse(r['erros_sintaticos'])

    def test_precedencia_aritmetica(self):
        r = analisar('int x=1+2*3;')
        self.assertIn('Expressao (+)', r['ast_comandos'][0])
        self.assertIn('Expressao (*)', r['ast_comandos'][0])
        self.assertLess(r['ast_comandos'][0].index('Expressao (+)'),r['ast_comandos'][0].index('Expressao (*)'))

    def test_parenteses(self):
        r = analisar('int x=(1+2)*3;')
        self.assertLess(r['ast_comandos'][0].index('Expressao (*)'),r['ast_comandos'][0].index('Expressao (+)'))

    def test_unarios(self):
        r = analisar('int x=-3+2;')
        self.assertFalse(r['erros_sintaticos'])
        self.assertIn('Expressao unaria (-)',r['ast_comandos'][0])

    def test_declaracao_sem_inicializador(self):
        r = analisar('int x; x=3;')
        self.assertEqual(len(r['ast_comandos']),2)
        self.assertFalse(r['erros_sintaticos'])

    def test_multiplas_declaracoes(self):
        r = analisar('int a=1, b=2, c; c=a+b;')
        self.assertEqual(len(r['ast_comandos']),4)
        self.assertFalse(r['erros_sintaticos'])

    def test_erro_termo_faltante(self):
        r = analisar('int x=1; x = 2 + ;')
        self.assertEqual(len(r['erros_sintaticos']),1)
        self.assertIn('Esperado',r['erros_sintaticos'][0]['mensagem'])

    def test_erro_atribuicao_vazia(self):
        r = analisar('int x; x = ;')
        self.assertTrue(r['erros_sintaticos'])

    def test_erro_sem_ponto_virgula(self):
        r = analisar('int x=4}')
        self.assertTrue(r['erros_sintaticos'])
        self.assertIn("Falta ';'",r['erros_sintaticos'][0]['mensagem'])

    def test_erro_parentese(self):
        r = analisar('int x=(3+2;')
        self.assertTrue(r['erros_sintaticos'])
        self.assertIn('Falta',r['erros_sintaticos'][0]['mensagem'])

    def test_recuperacao_apos_erro(self):
        r = analisar('int x=3; x = ; x = 4;')
        self.assertEqual(len(r['erros_sintaticos']),1)
        self.assertEqual(len(r['ast_comandos']),2)

    def test_chave_fechamento_extra(self):
        r = analisar('int x=1; }')
        self.assertTrue(any('sem abertura' in e['mensagem'] for e in r['erros_sintaticos']))

    def test_chave_abertura_nao_fechada(self):
        r = analisar('int main() { int x=1;')
        self.assertTrue(any('Faltam' in e['mensagem'] for e in r['erros_sintaticos']))


    def test_scanner_arquivo_original(self):
        r = analisar((ROOT/'hello.c').read_text(encoding='utf8'))
        self.assertEqual(len(r['ast_comandos']),2)
        self.assertFalse(r['erros_sintaticos'])
        self.assertFalse(r['erros_semanticos'])



class TesteSemantico(unittest.TestCase):
    def test_int_recebendo_string(self):
        r=analisar('int resultado = "texto";')
        self.assertEqual(len(r['erros_semanticos']),1)
        self.assertIn('String a int',r['erros_semanticos'][0]['mensagem'])

    def test_nao_declarada_esquerda(self):
        r=analisar('total = 10;')
        self.assertIn("'total'",r['erros_semanticos'][0]['mensagem'])

    def test_nao_declarada_direita(self):
        r=analisar('int x = a + 5;')
        self.assertEqual(len(r['erros_semanticos']),1)
        self.assertIn("'a'",r['erros_semanticos'][0]['mensagem'])

    def test_float_recebe_int(self):
        r=analisar('float x = 5;')
        self.assertFalse(r['erros_semanticos'])

    def test_int_nao_recebe_float(self):
        r=analisar('int x = 1.5;')
        self.assertEqual(len(r['erros_semanticos']),1)




    def test_char_aceita_caractere(self):
        r=analisar("char letra = 'A';")
        self.assertFalse(r['erros_semanticos'])

    def test_declaracao_duplicada_mesmo_escopo(self):
        r=analisar('int a=2; float a=4;')
        self.assertTrue(any('já declarada' in e['mensagem'] for e in r['erros_semanticos']))

    def test_escopo_nao_vaza(self):
        r=analisar('int main(){ { int interno=1; } interno=2; }')
        self.assertTrue(any('sem declaração' in e['mensagem'] for e in r['erros_semanticos']))

    def test_shadowing_escopo_permitido(self):
        r=analisar('int main(){int a=1; { float a=2.5f; a=3; } a=4;}')
        self.assertFalse(r['erros_semanticos'])

    def test_declaracao_usada_antes_de_existir(self):
        r = analisar('x = 1; int x;')
        self.assertEqual(len(r['erros_semanticos']), 1)
        self.assertIn('declaração prévia', r['erros_semanticos'][0]['mensagem'])

    def test_erro_tipos_na_linha_original(self):
        r = analisar('int main() {\n int x=2;\n x = "texto";\n }')
        self.assertEqual(r['erros_semanticos'][0]['linha'],3)

    def test_erro_operacao_texto_numero(self):
        r=analisar('int x = "a" + 3;')
        self.assertTrue(any('Operação' in e['mensagem'] for e in r['erros_semanticos']))


class TesteCLI(unittest.TestCase):
    def executar(self, *args):
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'
        return subprocess.run([sys.executable, str(ROOT/'compilador.py'), *map(str,args)],
                              encoding='utf8', capture_output=True, cwd=ROOT, env=env)

    def test_cli_padrao(self):
        p=self.executar('--sem-tokens')
        self.assertEqual(p.returncode,0,p.stderr+p.stdout)
        self.assertIn('TABELA DE SÍMBOLOS',p.stdout)
        self.assertIn('AST',p.stdout)

    def test_cli_erro_semantico_exit_code(self):
        p=self.executar(ROOT/'exemplos'/'erro_tipos.c','--sem-tokens')
        self.assertEqual(p.returncode,1)
        self.assertIn('[ERRO SEMÂNTICO]',p.stdout)


    def test_cli_arquivo_inexistente(self):
        p=self.executar(ROOT/'nao_existe.c')
        self.assertEqual(p.returncode,2)
        self.assertIn('falha ao ler',p.stderr)


    def test_cli_erros_lexicos_exit_code(self):
        with tempfile.TemporaryDirectory() as tmp:
            src=Path(tmp)/'invalido.c'
            src.write_text('int x = 1 @ 2;',encoding='utf8')
            p=self.executar(src,'--sem-tokens')
            self.assertEqual(p.returncode,1)
            self.assertIn('[ERRO LÉXICO]',p.stdout)



class TesteCompatibilidadePython(unittest.TestCase):
    def test_todos_os_arquivos_compilam_com_sintaxe_python_37(self):
        """Previne SyntaxError em versões antigas (3.7+) do interpretador."""
        import ast
        for arquivo in ROOT.rglob('*.py'):
            if '__pycache__' not in arquivo.parts and '.venv' not in arquivo.parts:
                with self.subTest(arquivo=str(arquivo.relative_to(ROOT))):
                    codigo = arquivo.read_text(encoding='utf-8')
                    if sys.version_info < (3, 8):
                        # Python 3.7 já utiliza sua própria gramática.
                        ast.parse(codigo, filename=str(arquivo))
                    else:
                        ast.parse(codigo, filename=str(arquivo), feature_version=(3, 7))



class TesteRegressoesAdicionais(unittest.TestCase):
    def test_hexadecimal_com_letra_f_permanece_inteiro(self):
        for literal in ('0xFF', '0xDEAD', '0x1F', '0xF0', '0xABC'):
            with self.subTest(literal=literal):
                r = analisar('int numero = ' + literal + ';')
                self.assertEqual(r['erros_lexicos'], [])
                self.assertEqual(r['erros_sintaticos'], [])
                self.assertEqual(r['erros_semanticos'], [])
                self.assertEqual(r['tokens'][3]['lexema'], literal)

    def test_real_decimal_continua_incompativel_com_int(self):
        for literal in ('1.5', '3e2', '2.0f'):
            with self.subTest(literal=literal):
                r = analisar('int numero = ' + literal + ';')
                self.assertEqual(len(r['erros_semanticos']), 1)
                self.assertIn('Incompatibilidade de tipos', r['erros_semanticos'][0]['mensagem'])

    def test_ast_em_modo_ascii(self):
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'
        p = subprocess.run([sys.executable, str(ROOT/'compilador.py'),
                            str(ROOT/'exemplos'/'correto.c'), '--ascii', '--sem-tokens'],
                           capture_output=True, encoding='utf-8', cwd=ROOT, env=env)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn('+-- ID (', p.stdout)
        self.assertNotIn('├──', p.stdout)

    def test_ast_no_terminal_cp1252_sem_erro_de_codificacao(self):
        import os
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'cp1252:strict'
        p = subprocess.run([sys.executable, str(ROOT/'compilador.py'),
                            str(ROOT/'exemplos'/'correto.c'), '--sem-tokens'],
                           capture_output=True, cwd=ROOT, env=env)
        self.assertEqual(p.returncode, 0, p.stderr.decode('utf-8', errors='replace'))
        texto = p.stdout.decode('cp1252')
        self.assertIn('Atribuicao', texto)
        self.assertIn('+-- ID (', texto)


if __name__=='__main__':
    unittest.main()
