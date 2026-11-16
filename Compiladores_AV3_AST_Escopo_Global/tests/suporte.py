"""Adaptação dos testes unitários históricos de fragmentos.

Esses testes isolam léxico, expressões, tipos e vínculos em fragmentos que nem
sempre são programas válidos. A validação global real permanece obrigatória em
compilador.analisar() e na CLI, testadas sem este adaptador na nova regressão.
"""
from compilador import analisar
from sintatico.ast import NoAST, formatar_ast
from sintatico.contexto import PREFIXO_ERRO_CONTEXTO


def analisar_fragmento(codigo, linguagem=None):
    resultado = analisar(codigo, linguagem)
    resultado['erros_contexto'] = [e for e in resultado['erros_sintaticos']
                                   if e['mensagem'].startswith(PREFIXO_ERRO_CONTEXTO)]
    resultado['erros_sintaticos'] = [e for e in resultado['erros_sintaticos']
                                     if not e['mensagem'].startswith(PREFIXO_ERRO_CONTEXTO)]
    comandos = []
    pendentes = [resultado['ast_estruturada']]
    while pendentes:
        no = pendentes.pop()
        if no['classe'] in ('DECLARACAO', 'ATRIBUICAO'):
            comandos.append(no)
        pendentes.extend(no['filhos'])

    def reconstruir(no):
        return NoAST(no['classe'], no['valor'], filhos=[reconstruir(f) for f in no['filhos']])

    resultado['ast_comandos'] = [formatar_ast(reconstruir(no)) for no in sorted(
        comandos, key=lambda n: (n['linha'], n['coluna']))]
    return resultado
