"""Regressões do pedido atual: AST completa e instruções fora de funções.

Usa a API pública e a CLI sem o adaptador dos testes históricos de fragmentos.
"""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from compilador import analisar


def percorrer(no):
    yield no
    for filho in no['filhos']:
        yield from percorrer(filho)


class TesteEscopoGlobal(unittest.TestCase):
    def test_exemplo_do_usuario_gera_um_erro_em_cada_atribuicao(self):
        for linguagem in (None, 'c', 'java'):
            with self.subTest(linguagem=linguagem):
                r = analisar('int c = 0;\nc = 1;\nc = 2;\n', linguagem)
                self.assertEqual(r['erros_lexicos'], [])
                self.assertEqual(r['erros_semanticos'], [])
                self.assertEqual([(e['linha'], e['coluna']) for e in r['erros_sintaticos']], [(2, 1), (3, 1)])
                self.assertTrue(all('fora de função' in e['mensagem'] for e in r['erros_sintaticos']))
                self.assertEqual([s['lexema'] for s in r['simbolos']], ['c'])
                self.assertEqual(r['simbolos'][0]['escopo'], 'global')

    def test_atribuicoes_na_mesma_linha_nao_sao_engolidas_pela_recuperacao(self):
        r = analisar('int c=0; c=1; c=2;', 'c')
        self.assertEqual([(e['linha'], e['coluna']) for e in r['erros_sintaticos']], [(1, 10), (1, 15)])

    def test_mesmas_atribuicoes_dentro_de_funcao_sao_aceitas(self):
        r = analisar('int c=0; void alterar(void){c=1; c=2;}', 'c')
        self.assertEqual(r['erros_sintaticos'], [])
        self.assertEqual(r['erros_semanticos'], [])

    def test_declaracoes_globais_alias_e_prototipo_sao_aceitos(self):
        r = analisar('typedef int Inteiro; int c=0; Inteiro d=1; int f(int);', 'c')
        self.assertEqual(r['erros_sintaticos'], [])
        self.assertEqual(r['erros_semanticos'], [])

    def test_controles_chamadas_incrementos_e_blocos_globais_sao_rejeitados(self):
        instrucoes = ('c=1;', 'c++;', 'f();', 'if(c)c=1;else c=2;',
                      'while(c)c=1;', 'for(int i=0;i<1;i++)c=1;',
                      'do c=1;while(c);', 'return;', 'switch(c){default:break;}', '{c=1;}')
        for instrucao in instrucoes:
            with self.subTest(instrucao=instrucao):
                r = analisar('int c=0; ' + instrucao + ' int depois=2;', 'c')
                self.assertEqual(len(r['erros_sintaticos']), 1, r['erros_sintaticos'])
                self.assertIn('fora de função', r['erros_sintaticos'][0]['mensagem'])
                self.assertIn('depois', [s['lexema'] for s in r['simbolos']])

    def test_prototipo_e_funcao_fechada_nao_liberam_comandos_globais(self):
        for prefixo in ('int f(void);', 'int f(void){return 0;}'):
            with self.subTest(prefixo=prefixo):
                r = analisar(prefixo + ' int c=0; c=1;', 'c')
                self.assertEqual(len(r['erros_sintaticos']), 1)
                self.assertIn('fora de função', r['erros_sintaticos'][0]['mensagem'])

    def test_bloco_global_nao_e_confundido_com_funcao(self):
        r = analisar('int c=0; {c=1;} c=2;', 'c')
        self.assertEqual(len(r['erros_sintaticos']), 2)

    def test_campos_java_aceitam_inicializacao_mas_rejeitam_comando_solto(self):
        r = analisar('class Main {int c=0; c=1; void f(){c=2;}}', 'java')
        self.assertEqual(len(r['erros_sintaticos']), 1)
        self.assertIn('fora de função', r['erros_sintaticos'][0]['mensagem'])

    def test_classe_local_nao_herda_permissao_de_executar_da_funcao_externa(self):
        r = analisar('void externo(){class Local {int c=0; c=1; void f(){c=2;}}}', 'java')
        self.assertEqual(len(r['erros_sintaticos']), 1)
        self.assertIn('fora de função', r['erros_sintaticos'][0]['mensagem'])

    def test_apos_rejeitar_comando_global_a_funcao_seguinte_e_analisada(self):
        r = analisar('int c=0; c=1; void f(){c=2; while(c<4){c++;}} c=3;', 'c')
        self.assertEqual(len(r['erros_sintaticos']), 2)
        self.assertIn('WHILE', {n['classe'] for n in percorrer(r['ast_estruturada'])})

    def test_cli_exemplo_do_usuario_retorna_erro_e_exporta_os_dois_diagnosticos(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as pasta:
            entrada = Path(pasta)/'global.c'
            saida = Path(pasta)/'resultado.json'
            entrada.write_text('int c = 0;\nc = 1;\nc = 2;\n', encoding='utf-8')
            p = subprocess.run([sys.executable, str(root/'compilador.py'), str(entrada),
                                '--json', str(saida), '--ascii', '--sem-tokens'],
                               capture_output=True, text=True, encoding='utf-8')
            self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
            r = json.loads(saida.read_text(encoding='utf-8'))
        self.assertEqual([e['linha'] for e in r['erros_sintaticos']], [2, 3])
        self.assertEqual(p.stdout.count('[ERRO SINTÁTICO]'), 2)
        self.assertEqual(r['simbolos'][0]['lexema'], 'c')

    def test_alteracoes_de_contadores_do_pedido_anterior_nao_estao_na_versao(self):
        r = analisar('int c=0; void f(){c=1;}', 'c')
        self.assertTrue(all('usos' not in s and 'declaracoes' not in s for s in r['simbolos']))
        self.assertNotIn('ast_comandos', r)


class TesteASTCompleta(unittest.TestCase):
    def analisar_valido(self, fonte, linguagem='c'):
        r = analisar(fonte, linguagem)
        for fase in ('erros_lexicos', 'erros_sintaticos', 'erros_semanticos'):
            self.assertEqual(r[fase], [], (fase, r[fase]))
        return r

    def test_funcoes_parametros_declaracoes_e_retorno(self):
        r = self.analisar_valido('int soma(int a,int b){int total=a+b; return total;}')
        raiz = r['ast_estruturada']
        self.assertEqual(raiz['classe'], 'PROGRAMA')
        funcao = raiz['filhos'][0]
        self.assertEqual((funcao['classe'], funcao['valor']), ('FUNCAO', 'soma'))
        classes = {n['classe'] for n in percorrer(funcao)}
        self.assertTrue({'PARAMETROS', 'PARAMETRO', 'BLOCO', 'DECLARACAO', 'RETURN', 'OP'} <= classes)
        self.assertIn('Funcao (soma)', r['ast'][0])

    def test_if_else_e_while_preservam_a_hierarquia(self):
        r = self.analisar_valido('int main(){int c=0; if(c<1){c=1;}else while(c<4)c=c+1;}')
        condicional = next(n for n in percorrer(r['ast_estruturada']) if n['classe'] == 'IF')
        self.assertEqual([n['classe'] for n in condicional['filhos']], ['CONDICAO', 'ENTAO', 'ELSE'])
        self.assertIn('WHILE', {n['classe'] for n in percorrer(condicional['filhos'][2])})
        self.assertNotIn('WHILE', {n['classe'] for n in percorrer(condicional['filhos'][1])})

    def test_else_se_associa_ao_if_mais_proximo(self):
        r = self.analisar_valido('void f(){int a; int b; if(a)if(b)a=1;else a=2;}')
        condicionais = [n for n in percorrer(r['ast_estruturada']) if n['classe'] == 'IF']
        self.assertNotIn('ELSE', [n['classe'] for n in condicionais[0]['filhos']])
        self.assertIn('ELSE', [n['classe'] for n in condicionais[1]['filhos']])

    def test_for_tem_inicializacao_condicao_atualizacao_e_corpo(self):
        r = self.analisar_valido('void f(){for(int i=0;i<3;i++){continue;}}')
        laco = next(n for n in percorrer(r['ast_estruturada']) if n['classe'] == 'FOR')
        self.assertEqual([n['classe'] for n in laco['filhos']],
                         ['INICIALIZACAO', 'CONDICAO', 'ATUALIZACAO', 'CORPO'])
        self.assertIn('POSFIXO', {n['classe'] for n in percorrer(laco)})

    def test_do_while_chamadas_e_atribuicoes_compostas(self):
        r = self.analisar_valido('int f(int n){return n;} void main(){int c=0; '
                                'do{c++;c+=f(c);}while(c<3);return;}')
        self.assertTrue({'DO_WHILE', 'CHAMADA', 'POSFIXO', 'ATRIBUICAO_EXPRESSAO'} <=
                        {n['classe'] for n in percorrer(r['ast_estruturada'])})

    def test_for_vazio_e_instrucoes_vazias(self):
        r = self.analisar_valido('void f(){for(;;); while(1);}')
        self.assertTrue({'FOR', 'WHILE', 'VAZIO'} <= {n['classe'] for n in percorrer(r['ast_estruturada'])})

    def test_switch_agrupa_os_casos_e_seus_comandos(self):
        r = self.analisar_valido('void f(){int c=1; switch(c){case 0:c=2;break;default:c=3;break;}}')
        casos = [n for n in percorrer(r['ast_estruturada']) if n['classe'] in ('CASE', 'DEFAULT')]
        self.assertEqual(len(casos), 2)
        self.assertTrue(all(any(n['classe'] == 'BREAK' for n in percorrer(c)) for c in casos))

    def test_classe_java_for_aprimorado_e_tratamento_de_excecoes(self):
        r = self.analisar_valido('class Main {void f(int[] xs){for(int x:xs){continue;}'
                                'try{f(xs);}catch(Exception e){throw e;}finally{f(xs);}}}', 'java')
        self.assertTrue({'CLASSE', 'FUNCAO', 'FOR_EACH', 'TRY', 'CATCH', 'FINALLY', 'THROW'} <=
                        {n['classe'] for n in percorrer(r['ast_estruturada'])})

    def test_expressoes_array_ternario_e_operadores_logicos(self):
        r = self.analisar_valido('void f(){int xs[3];int c=xs[0];int d=c<2?1:2;}')
        self.assertTrue({'DIMENSAO', 'INDICE', 'TERNARIO'} <=
                        {n['classe'] for n in percorrer(r['ast_estruturada'])})
        self.analisar_valido('class Main{void f(){int c=1; boolean ok=c<3 && c!=2;}}', 'java')

    def test_cli_e_json_mostram_a_arvore_completa(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as pasta:
            entrada = Path(pasta)/'completo.c'
            saida = Path(pasta)/'resultado.json'
            entrada.write_text('int main(){int c=0;if(c<1)c=1;else c=2;'
                               'while(c<3)c++;for(int i=0;i<2;i++)c+=i;return c;}', encoding='utf-8')
            p = subprocess.run([sys.executable, str(root/'compilador.py'), str(entrada),
                                '--json', str(saida), '--ascii'],
                               capture_output=True, text=True, encoding='utf-8')
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
            r = json.loads(saida.read_text(encoding='utf-8'))
        self.assertEqual(r['ast_estruturada']['classe'], 'PROGRAMA')
        for no in ('Funcao (main)', 'IF', 'ELSE', 'WHILE', 'FOR', 'RETURN'):
            self.assertIn(no, r['ast'][0])
            self.assertIn(no, p.stdout)


if __name__ == '__main__':
    unittest.main()
