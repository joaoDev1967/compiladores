"""Regressões específicas dos dez defeitos do documento Erros_a_Corrigir.

Os testes antigos continuam em test_compilador.py; estes validam a nova rodada.
"""
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


def mensagens(resultado, etapa):
    return ' '.join(x['mensagem'] for x in resultado['erros_' + etapa])


class Teste01Controle(unittest.TestCase):
    def test_if_atribuicao_na_condicao_preserva_corpo(self):
        r = analisar('int x; int y; if (x = 1) y = 2;')
        self.assertFalse(r['erros_sintaticos'])
        self.assertEqual(len(r['ast_comandos']), 3)
        self.assertIn('Atribuicao', r['ast_comandos'][-1])
        self.assertIn('ID (y)', r['ast_comandos'][-1])

    def test_while_com_atribuicao_na_condicao_preserva_bloco(self):
        r = analisar('int x=3; while (x = x - 1) { x = 2; }')
        self.assertEqual(len(r['ast_comandos']), 2)
        self.assertEqual(r['erros_sintaticos'], [])

    def test_for_condicao_e_incremento_nao_apagam_corpo(self):
        r = analisar('int x=1; for (int i=0; i<2; i++) x=3;')
        self.assertEqual(len(r['ast_comandos']), 3)
        self.assertEqual(r['erros_sintaticos'], [])

    def test_if_else_sem_chaves_preserva_ambos(self):
        r = analisar('int x; if (x=1) x=2; else x=3;')
        self.assertEqual(len(r['ast_comandos']), 3)
        self.assertEqual(r['erros_sintaticos'], [])


class Teste02EscopoFor(unittest.TestCase):
    def test_i_nao_vaza_apos_chaves(self):
        r = analisar('for (int i=0; i<3; i++) { int z=i; } i=9;')
        self.assertIn("'i'", mensagens(r, 'semanticos'))
        self.assertEqual(r['erros_sintaticos'], [])

    def test_i_nao_vaza_apos_comando_simples(self):
        r = analisar('int x; for (int i=0;i<3;i++) x=i; i=9;')
        self.assertEqual(len(r['erros_semanticos']), 1)
        self.assertEqual(len(r['ast_comandos']), 4)

    def test_pode_redeclarar_i_apos_laco(self):
        r = analisar('for (int i=0;i<3;i++) {} int i=9;')
        self.assertEqual(r['erros_semanticos'], [])
        itens = [x for x in r['simbolos'] if x['lexema'] == 'i']
        self.assertEqual(len(itens), 2)
        self.assertNotEqual(itens[0]['escopo'], itens[1]['escopo'])


class Teste03TiposCompostos(unittest.TestCase):
    def test_array_nao_recebe_escalar(self):
        r = analisar('int xs[]; xs = 1;')
        self.assertEqual(r['erros_sintaticos'], [])
        self.assertIn('int[]', mensagens(r, 'semanticos'))

    def test_java_array_declarado(self):
        r = analisar('String[] args; args="t";')
        self.assertIn('String[]', mensagens(r, 'semanticos'))
        sym = next(x for x in r['simbolos'] if x['lexema'] == 'args')
        self.assertEqual(sym['tipo_declarado'], 'String[]')

    def test_parametro_ponteiro_nao_finge_int(self):
        r = analisar('int f(int *a) { int x = a; }')
        self.assertIn('int*', mensagens(r, 'semanticos'))
        self.assertFalse(r['erros_sintaticos'])

    def test_parametro_java_array_nao_finge_string(self):
        r = analisar('void main(String[] args){ args="t"; }')
        self.assertIn('String[]', mensagens(r, 'semanticos'))

    def test_ponteiro_em_variavel_normal(self):
        r = analisar('int *p; int x=p;')
        self.assertIn('int*', mensagens(r, 'semanticos'))


class Teste04Reais(unittest.TestCase):
    def test_real_sem_sufixo_double(self):
        for n in ['1.5', '3e2', '2.0D', '1d']:
            with self.subTest(n=n):
                r = analisar('float a=' + n + ';')
                self.assertIn('double a float', mensagens(r, 'semanticos'))

    def test_float_somente_com_f(self):
        for n in ['1f', '2.0F', '3e2f']:
            with self.subTest(n=n):
                r = analisar('float a=' + n + ';')
                self.assertFalse(r['erros_lexicos'])
                self.assertFalse(r['erros_semanticos'])

    def test_double_aceita_reais_sem_f(self):
        r = analisar('double d=1.5; float w=1.5f;')
        self.assertEqual(r['erros_semanticos'], [])


class Teste05TiposC(unittest.TestCase):
    def test_const_ordem_variavel(self):
        r = analisar('const int y=2; int const x=1;')
        self.assertEqual(r['erros_sintaticos'], [])
        self.assertEqual(r['erros_semanticos'], [])

    def test_long_long_e_int_explicitado(self):
        r = analisar('long long x=1; long int y=2; short int z=3;')
        self.assertEqual(len(r['ast_comandos']), 3)
        self.assertEqual(r['erros_sintaticos'], [])
        sym = next(x for x in r['simbolos'] if x['lexema'] == 'x')
        self.assertEqual(sym['tipo_declarado'], 'long long')

    def test_unsigned_e_signed_implicam_int(self):
        r = analisar('unsigned x=1; signed y=2; unsigned long z=3;')
        self.assertEqual(r['erros_sintaticos'], [])
        self.assertEqual(r['erros_semanticos'], [])
        self.assertEqual(len(r['ast_comandos']), 3)


class Teste06Alias(unittest.TestCase):
    def test_typedef_define_tipo_e_nao_variavel(self):
        r = analisar('typedef int Inteiro; Inteiro x=1;')
        self.assertEqual(r['erros_semanticos'], [])
        self.assertEqual(len(r['ast_comandos']), 1)
        alias = next(x for x in r['simbolos'] if x['lexema'] == 'Inteiro')
        self.assertEqual(alias['categoria'], 'Tipo')

    def test_typedef_nao_declara_variavel_inteiro(self):
        r = analisar('typedef int Inteiro; Inteiro=2;')
        self.assertTrue(r['erros_semanticos'])
        self.assertIn('não é uma variável', mensagens(r, 'semanticos'))


class Teste07Inicializacao(unittest.TestCase):
    def test_auto_referencia_rejeitada(self):
        r = analisar('int x=x+1;')
        self.assertIn('próprio inicializador', mensagens(r, 'semanticos'))

    def test_nome_declarado_antes_pode_ser_usado(self):
        r = analisar('int x=1; int y=x+1;')
        self.assertEqual(r['erros_semanticos'], [])

    def test_declarador_anterior_na_mesma_lista(self):
        r = analisar('int x=1, y=x+1;')
        self.assertEqual(r['erros_semanticos'], [])


class Teste08Simbolos(unittest.TestCase):
    def test_sombra_mantem_duas_declaracoes(self):
        r = analisar('int a=1; { float a=2.5f; }')
        simbolos_a = [x for x in r['simbolos'] if x['lexema'] == 'a']
        self.assertEqual(len(simbolos_a), 2)
        self.assertNotEqual(simbolos_a[0]['escopo'], simbolos_a[1]['escopo'])

    def test_funcao_variavel_mesmo_escopo_rejeitado(self):
        r = analisar('int x=1; int x(int a){return a;}')
        self.assertIn('já declarada', mensagens(r, 'semanticos'))
        s = next(x for x in r['simbolos'] if x['lexema'] == 'x')
        self.assertNotEqual(s['categoria'], 'Função')

    def test_parametros_mesmo_nome_em_funcoes_diferentes(self):
        r = analisar('int f(int a){return a;} int g(float a){return 1;}')
        simbolos_a = [x for x in r['simbolos'] if x['lexema'] == 'a']
        self.assertEqual(len(simbolos_a), 2)
        self.assertNotEqual(simbolos_a[0]['escopo'], simbolos_a[1]['escopo'])


class Teste09Lexico(unittest.TestCase):
    def test_literal_long_e_unsigned_atomicos(self):
        ts, erros = tokenizar('10L 25U 30UL 100LL 0xFF 0b101')
        self.assertEqual(erros, [])
        self.assertEqual([t.lexema for t in ts], ['10L', '25U', '30UL', '100LL', '0xFF', '0b101'])
        self.assertTrue(all(t.tipo == 'NUMBER' for t in ts))

    def test_hexadecimal_incompleto_nao_vira_zero_e_nome(self):
        ts, erros = tokenizar('int x=0x; int y=1;')
        self.assertEqual(len(erros), 1)
        self.assertIn('0x', [t.lexema for t in ts])
        self.assertEqual([t.lexema for t in ts].count('x'), 1)

    def test_java_numeros_com_underscore(self):
        ts, erros = tokenizar('int x=1_000;')
        self.assertFalse(erros)
        self.assertIn('1_000', [t.lexema for t in ts])

    def test_anotacao_java(self):
        ts, erros = tokenizar('@Override')
        self.assertEqual(erros, [])
        self.assertEqual([t.tipo for t in ts], ['AT', 'IDENTIFIER'])

    def test_identificador_dolar_java(self):
        ts, erros = tokenizar('int $preco=1;', linguagem='java')
        self.assertEqual(erros, [])
        self.assertIn('$preco', [t.lexema for t in ts])

    def test_identificador_dolar_em_c_erro_lexico_sem_perder_nome(self):
        ts, erros = tokenizar('int $preco=1;', linguagem='c')
        self.assertEqual(len(erros), 1)
        self.assertIn('$preco', [t.lexema for t in ts])

    def test_null_em_string_mas_nao_int(self):
        r = analisar('String s=null; int n=null;')
        self.assertEqual(r['erros_sintaticos'], [])
        self.assertEqual(len(r['erros_semanticos']), 1)


class Teste10Recuperacao(unittest.TestCase):
    def test_string_aberta_preserva_comando_na_linha_seguinte(self):
        r = analisar('String s="aberto;\nint x=2;')
        self.assertEqual(len(r['erros_lexicos']), 1)
        self.assertEqual(len(r['ast_comandos']), 1)
        self.assertIn('ID (x)', r['ast_comandos'][0])
        self.assertNotIn('s', [x['lexema'] for x in r['simbolos']])

    def test_char_errado_preserva_comando_na_mesma_linha(self):
        r = analisar("char c='ab'; int x=1;")
        self.assertEqual(len(r['ast_comandos']), 1)
        self.assertIn('ID (x)', r['ast_comandos'][0])
        self.assertEqual(len(r['erros_lexicos']), 1)

    def test_agregado_fora_gramatica_nao_produz_chave_espuria(self):
        r = analisar('int xs[]={1,2}; int y=3;')
        self.assertEqual(len(r['erros_sintaticos']), 1)
        self.assertNotIn('sem abertura', mensagens(r, 'sintaticos'))
        self.assertEqual(len(r['ast_comandos']), 1)
        self.assertIn('ID (y)', r['ast_comandos'][0])

    def test_inicializador_parcial_nao_registra_nome(self):
        r = analisar('int x=1+; int y=2; x=2;')
        self.assertEqual(len(r['ast_comandos']), 2)
        self.assertIn("'x'", mensagens(r, 'semanticos'))
        self.assertNotIn('x', [x['lexema'] for x in r['simbolos']])


class TesteFimAFim(unittest.TestCase):
    def test_json_inclui_escopos_e_aceita_cli_java(self):
        with tempfile.TemporaryDirectory() as pasta:
            entrada = Path(pasta) / 'Demo.java'
            saida = Path(pasta) / 'resultado.json'
            entrada.write_text('class Demo { void main(String[] args) { int $preco=1; } }', encoding='utf-8')
            env = os.environ.copy()
            env['PYTHONIOENCODING'] = 'utf-8'
            p = subprocess.run([sys.executable, str(ROOT / 'compilador.py'), str(entrada),
                                '--sem-tokens', '--json', str(saida)],
                                capture_output=True, text=True, encoding='utf-8', cwd=str(ROOT),
                                env=env)
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
            obj = json.loads(saida.read_text(encoding='utf-8'))
            nome = next(x for x in obj['simbolos'] if x['lexema'] == '$preco')
            self.assertEqual((nome['tipo_declarado'], nome['token']), ('int', 'IDENTIFIER'))
            self.assertIn('/funcao', nome['escopo'])

    def test_c_sinaliza_dolar_em_cli(self):
        with tempfile.TemporaryDirectory() as pasta:
            entrada = Path(pasta) / 'Demo.c'
            entrada.write_text('int $preco=1;', encoding='utf-8')
            env = os.environ.copy()
            env['PYTHONIOENCODING'] = 'utf-8'
            p = subprocess.run([sys.executable, str(ROOT / 'compilador.py'), str(entrada),
                                '--sem-tokens'], capture_output=True, text=True,
                                encoding='utf-8', cwd=str(ROOT), env=env)
            self.assertEqual(p.returncode, 1)
            self.assertIn('[ERRO LÉXICO]', p.stdout)


if __name__ == '__main__':
    unittest.main()
