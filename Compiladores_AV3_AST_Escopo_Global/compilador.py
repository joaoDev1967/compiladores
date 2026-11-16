#!/usr/bin/env python3
"""AV3 Compiladores: tokenização, tabela de símbolos, parser/AST e semântica.

Exemplos:
    python compilador.py hello.c
    python compilador.py exemplos/erro_tipos.c --sem-tokens
"""
import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys

from lexing.lexer import tokenizar
from lexing.tokens import Diagnostico, OPERADORES, palavra_reservada
from semantica.analisador import TabelaSimbolos
from sintatico.parser import AnalisadorSintatico, formatar_ast


def analisar(codigo, linguagem=None):
    """Interface importável utilizada nos testes automatizados."""
    tokens, erros_lexicos = tokenizar(codigo, linguagem=linguagem)
    tabela = TabelaSimbolos(tokens)
    sintatico = AnalisadorSintatico(tokens, tabela, linguagem)
    try:
        arvores, erros_sintaticos, erros_semanticos = sintatico.executar()
    except RecursionError:
        token = sintatico.atual() or tokens[-1]
        arvores, erros_semanticos = [], sintatico.ambiente.erros
        erros_sintaticos = sintatico.erros + [Diagnostico(
            'SINTÁTICO', token.linha, token.coluna,
            'Entrada excede o limite de profundidade do analisador didático.')]
    entradas_tabela = [asdict(simbolo) for simbolo in tabela.listar_tabela()]
    for entrada in entradas_tabela:
        del entrada['token']
    return {
        'tokens': [asdict(t) for t in tokens],
        'tabela_simbolos': entradas_tabela,
        'simbolos': [asdict(s) for s in tabela.listar()],
        'palavras_reservadas': [asdict(p) for p in tabela.listar_reservadas()],
        'ast': [formatar_ast(no) for no in sorted(arvores, key=lambda no: no.token.ordem)],
        'ast_estruturada': sintatico.arvore.para_dict(),
        'erros_lexicos': [asdict(e) for e in erros_lexicos],
        'erros_sintaticos': [asdict(e) for e in sorted(erros_sintaticos, key=_posicao_diagnostico)],
        'erros_semanticos': [asdict(e) for e in sorted(erros_semanticos, key=_posicao_diagnostico)],
        'observacao': (
            'AST hierárquica das construções reconhecidas, com validação do contexto: '
            'declarações são permitidas no escopo global; instruções executáveis '
            'devem estar dentro de funções. A validação semântica é didática. '
            'Não há geração de código executável.'
        ),
        'tokens_fora_do_escopo': sintatico.ignorados,
    }


def _posicao_diagnostico(erro):
    return erro.linha, erro.coluna


def preparar_ast_terminal(arvore, somente_ascii=False):
    """Preserva a AST e evita UnicodeEncodeError em consoles Windows antigos."""
    codificacao = getattr(sys.stdout, 'encoding', None) or 'utf-8'
    try:
        arvore.encode(codificacao)
    except (UnicodeError, LookupError):
        somente_ascii = True
    if somente_ascii:
        return (arvore.replace('├── ', '+-- ')
                      .replace('└── ', '`-- ')
                      .replace('│   ', '|   '))
    return arvore


# Apresentação simplificada, sem alterar os tokens internos usados pelo parser.
_DELIMITADORES = {
    'LPAREN', 'RPAREN', 'LBRACE', 'RBRACE', 'LBRACKET', 'RBRACKET',
    'SEMICOLON', 'COMMA', 'DOT', 'COLON', 'QUESTION', 'ELLIPSIS', 'AT',
}
_OPERADORES = set(OPERADORES.values()) - _DELIMITADORES


def categoria_exibicao(token):
    """Mapeia tokens internos para as classes simples do exemplo visual."""
    tipo = token['tipo'] if isinstance(token, dict) else token.tipo
    if palavra_reservada(token):
        return 'KEYWORD'
    if tipo == 'IDENTIFIER':
        return 'ID'
    if tipo in _DELIMITADORES:
        return 'DELIMITER'
    if tipo in _OPERADORES:
        return 'OPERATOR'
    if tipo == 'CHAR_LITERAL':
        return 'CHAR'
    if tipo in ('PREPROCESSADOR', 'PP_ARGUMENT'):
        return 'PREPROCESSOR'
    return tipo


def preparar_linha_token(token, somente_ascii=False, codificacao=None):
    """Renderiza '• if → KEYWORD', com fallback ASCII para consoles antigos."""
    lexema = token['lexema'] if isinstance(token, dict) else token.lexema
    lexema = lexema.replace('\r', '\\r').replace('\n', '\\n')
    linha = '• {} → {}'.format(lexema, categoria_exibicao(token))
    if not somente_ascii:
        codificacao = codificacao or getattr(
            sys.stdout, 'encoding', None) or 'utf-8'
        try:
            linha.encode(codificacao)
        except (UnicodeError, LookupError):
            somente_ascii = True
    if somente_ascii:
        linha = '- {} -> {}'.format(lexema, categoria_exibicao(token))
    return linha


def mostrar_tokens(tokens, somente_ascii=False, detalhados=False):
    if detalhados:
        print(f"{'Ordem':>5}  {'Tipo':<21} {'Lexema':<26} {'Linha':>5} {'Col':>4}")
        print('-' * 80)
        for t in tokens:
            lexe = t['lexema'].replace('\r', '\\r').replace('\n', '\\n')
            print(f"{t['ordem']:>5}  {t['tipo']:<21} {lexe:<26} "
                  f"{t['linha']:>5} {t['coluna']:>4}")
    else:
        for t in tokens:
            print(preparar_linha_token(t, somente_ascii))


def mostrar(resultado, caminho, sem_tokens=False, somente_ascii=False, tokens_detalhados=False):
    print('=' * 80)
    print('ANALISADOR AV3 - COMPILADORES | Fonte:', caminho)
    print('=' * 80)
    if not sem_tokens:
        print('\n[1] ANÁLISE LÉXICA - LISTA DE TOKENS')
        mostrar_tokens(resultado['tokens'], somente_ascii, tokens_detalhados)

    print('\n[2] TABELA DE SÍMBOLOS - ordem de inserção')
    print(f"{'N':>3}  {'Nome':<20} {'Categoria':<22} {'Tipo declarado':<16} "
          f"{'Escopo':<32} {'Linha':>5} {'Col':>4}")
    print('-' * 110)
    for s in resultado['tabela_simbolos']:
        print(f"{s['ordem']:>3}  {s['lexema']:<20} {s['categoria']:<22} "
              f"{s['tipo_declarado']:<16} {s['escopo']:<32} "
              f"{s['linha']:>5} {s['coluna']:>4}")
    if not resultado['tabela_simbolos']:
        print('Nenhuma declaração registrada.')

    print('\n[3] ANÁLISE SINTÁTICA - AST DO PROGRAMA')
    if resultado['ast']:
        for n, arvore in enumerate(resultado['ast'], start=1):
            print(f'\nÁrvore {n}:')
            print(preparar_ast_terminal(arvore, somente_ascii))
    else:
        print('Nenhum comando da gramática simplificada foi reconhecido.')

    diagnosticos = (
        ('DIAGNÓSTICOS LÉXICOS', resultado['erros_lexicos']),
        ('DIAGNÓSTICOS SINTÁTICOS', resultado['erros_sintaticos']),
        ('ANÁLISE SEMÂNTICA - DIAGNÓSTICOS', resultado['erros_semanticos']),
    )
    for numero, (titulo, erros) in enumerate(diagnosticos, start=4):
        print(f'\n[{numero}] {titulo}')
        if erros:
            mostrar_diagnosticos(erros)
        else:
            print('Nenhum diagnóstico nesta etapa.')

    print('\n[7] RESUMO')
    total_erros = sum(len(erros) for _, erros in diagnosticos)
    print(f"Tokens: {len(resultado['tokens'])} | Entradas na tabela: {len(resultado['tabela_simbolos'])} "
          f"| Declarações: {len(resultado['simbolos'])} "
          f"| ASTs: {len(resultado['ast'])} | Erros: {total_erros}")


def mostrar_diagnosticos(erros, arquivo=None):
    for e in sorted(erros, key=lambda d: (d['linha'], d['coluna'])):
        print(f"[ERRO {e['fase']}] Linha {e['linha']}, coluna {e['coluna']}: {e['mensagem']}",
              file=arquivo)


def ler_fonte(caminho):
    conteudo = caminho.read_bytes()
    if conteudo.startswith((b'\xff\xfe', b'\xfe\xff')):
        return conteudo.decode('utf-16')
    try:
        return conteudo.decode('utf-8-sig')
    except UnicodeDecodeError:
        return conteudo.decode('cp1252')


def main(argv=None):
    cli = argparse.ArgumentParser(
        description='AV3: analisador léxico, sintático e semântico básico.')
    cli.add_argument('arquivo', nargs='?', type=Path,
                     default=Path(__file__).resolve().with_name('hello.c'),
                     help='Caminho para arquivo .c (padrão: hello.c).')
    grupo_tokens = cli.add_mutually_exclusive_group()
    grupo_tokens.add_argument(
        '--sem-tokens', action='store_true', help='Ocultar a lista de tokens.')
    grupo_tokens.add_argument('--apenas-tokens', action='store_true',
                              help='Mostrar apenas lexema → categoria, sem AST/tabela.')
    cli.add_argument('--tokens-detalhados', action='store_true',
                     help='Mostrar a tabela técnica antiga dos tokens com linha e coluna.')
    cli.add_argument('--ascii', action='store_true',
                     help='Exibir AST usando apenas caracteres ASCII.')
    cli.add_argument('--json', type=Path,
                     help='Exportar saída completa em JSON UTF-8.')
    args = cli.parse_args(argv)
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(errors='backslashreplace')

    if args.arquivo.suffix.lower() != '.c':
        print('ERRO: o arquivo de entrada deve terminar em .c.',
              file=sys.stderr)
        return 2
    try:
        codigo = ler_fonte(args.arquivo)
    except (OSError, UnicodeError) as exc:
        print(f'ERRO: falha ao ler {args.arquivo}: {exc}', file=sys.stderr)
        return 2

    linguagem = 'c'
    if args.apenas_tokens and not args.json:
        tokens, erros = tokenizar(codigo, linguagem)
        mostrar_tokens([asdict(token) for token in tokens],
                       args.ascii, args.tokens_detalhados)
        mostrar_diagnosticos([asdict(erro) for erro in erros], sys.stderr)
        return 1 if erros else 0

    resultado = analisar(codigo, linguagem)
    if args.apenas_tokens:
        mostrar_tokens(resultado['tokens'], args.ascii, args.tokens_detalhados)
        mostrar_diagnosticos(resultado['erros_lexicos'], sys.stderr)
    else:
        mostrar(resultado, args.arquivo, args.sem_tokens,
                args.ascii, args.tokens_detalhados)
    if args.json:
        try:
            if (args.json.resolve() == args.arquivo.resolve() or
                    (args.json.exists() and args.json.samefile(args.arquivo))):
                print(
                    'ERRO: a saída JSON deve ser diferente do arquivo fonte.', file=sys.stderr)
                return 2
            args.json.parent.mkdir(parents=True, exist_ok=True)
            args.json.write_text(json.dumps(resultado, ensure_ascii=False, indent=2),
                                 encoding='utf-8')
            if not args.apenas_tokens:
                print(f'\n[8] EXPORTAÇÃO JSON\nRelatório salvo em {args.json}')
        except OSError as exc:
            print(f'ERRO: falha ao gravar JSON: {exc}', file=sys.stderr)
            return 2
    if args.apenas_tokens:
        return 1 if resultado['erros_lexicos'] else 0
    if (resultado['erros_lexicos'] or resultado['erros_sintaticos']
            or resultado['erros_semanticos'] or not resultado['ast']):
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
