"""Tipos de tokens, diagnósticos e palavras reservadas para a análise léxica."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Token:
    tipo: str
    lexema: str
    linha: int
    coluna: int
    ordem: int


@dataclass(frozen=True)
class Diagnostico:
    fase: str
    linha: int
    coluna: int
    mensagem: str


# Palavras reservadas de C11/C17.
TIPOS_C = set('char double float int long short void _Bool _Complex _Imaginary'.split())
TIPOS_PRIMITIVOS = TIPOS_C
PALAVRAS_C = set("""auto break case const continue default do else enum extern
for goto if inline register restrict return signed sizeof static struct switch typedef
union unsigned volatile while _Alignas _Alignof _Atomic _Generic _Noreturn
_Static_assert _Thread_local""".split()) | TIPOS_C
RESERVADAS_C = {p: p.upper() for p in PALAVRAS_C}
RESERVADAS = RESERVADAS_C
# Especiais somente dentro de diretivas; continuam identificadores no código C.
PALAVRAS_DIRETIVAS_C = frozenset({'include'})

MODIFICADORES_C = set('auto const extern inline register restrict signed static unsigned volatile'.split())


OPERADORES = {
    '...': 'ELLIPSIS',
    '#': 'HASH', '##': 'TOKEN_PASTE',
    '<<=': 'LSHIFT_ASSIGN', '>>=': 'RSHIFT_ASSIGN',
    '++': 'INCREMENT', '--': 'DECREMENT', '->': 'ARROW',
    '+=': 'PLUS_ASSIGN', '-=': 'MINUS_ASSIGN', '*=': 'TIMES_ASSIGN',
    '/=': 'DIVIDE_ASSIGN', '%=': 'MOD_ASSIGN', '&=': 'AND_ASSIGN',
    '|=': 'OR_ASSIGN', '^=': 'XOR_ASSIGN',
    '==': 'EQ', '!=': 'NE', '<=': 'LE', '>=': 'GE',
    '&&': 'AND', '||': 'OR', '<<': 'LSHIFT', '>>': 'RSHIFT',
    '+': 'PLUS', '-': 'MINUS', '*': 'TIMES', '/': 'DIVIDE', '%': 'MOD',
    '=': 'ASSIGN', '<': 'LT', '>': 'GT', '!': 'NOT',
    '&': 'BITAND', '|': 'BITOR', '^': 'BITXOR', '~': 'BITNOT',
    '(': 'LPAREN', ')': 'RPAREN', '{': 'LBRACE', '}': 'RBRACE',
    '[': 'LBRACKET', ']': 'RBRACKET', ';': 'SEMICOLON', ',': 'COMMA',
    '.': 'DOT', ':': 'COLON', '?': 'QUESTION',
    '<:': 'LBRACKET', ':>': 'RBRACKET', '<%': 'LBRACE', '%>': 'RBRACE',
    '%:': 'HASH', '%:%:': 'TOKEN_PASTE',
}

OPERADORES_C = OPERADORES


def palavra_reservada(token):
    tipo, lexema = (token['tipo'], token['lexema']) if isinstance(token, dict) else (token.tipo, token.lexema)
    return ((tipo == 'KEYWORD' and lexema in PALAVRAS_DIRETIVAS_C) or
            (tipo != 'IDENTIFIER' and RESERVADAS.get(lexema) == tipo))
