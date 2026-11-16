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


# Palavras reservadas de C11/C17 e Java, além dos literais Java.
# Sem extensão informada, a API mantém o modo didático que aceita os dois conjuntos.
TIPOS_C = set('char double float int long short void _Bool _Complex _Imaginary'.split())
TIPOS_JAVA = set('boolean byte char double float int long short void'.split())
TIPOS_PRIMITIVOS = TIPOS_C | TIPOS_JAVA
PALAVRAS_C = set("""auto break case const continue default do else enum extern
for goto if inline register restrict return signed sizeof static struct switch typedef
union unsigned volatile while _Alignas _Alignof _Atomic _Generic _Noreturn
_Static_assert _Thread_local""".split()) | TIPOS_C
PALAVRAS_JAVA = set("""abstract assert break case catch class const continue default do
else enum extends final finally for goto if implements import instanceof interface
native new package private protected public return static strictfp super switch
synchronized this throw throws transient try volatile while true false null _""".split()) | TIPOS_JAVA
RESERVADAS_C = {p: p.upper() for p in PALAVRAS_C}
RESERVADAS_JAVA = {p: p.upper() for p in PALAVRAS_JAVA}
RESERVADAS = {**RESERVADAS_C, **RESERVADAS_JAVA}
# Especiais somente dentro de diretivas; continuam identificadores no código C.
PALAVRAS_DIRETIVAS_C = frozenset({'include'})

MODIFICADORES_C = set('auto const extern inline register restrict signed static unsigned volatile'.split())
MODIFICADORES_JAVA = set('abstract final native private protected public static strictfp synchronized transient volatile'.split())


OPERADORES = {
    '...': 'ELLIPSIS',
    '>>>=': 'URSHIFT_ASSIGN', '>>>': 'URSHIFT', '::': 'METHOD_REF',
    '@': 'AT', '#': 'HASH', '##': 'TOKEN_PASTE',
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

_OPERADORES_JAVA = {'>>>=', '>>>', '::', '@'}
_OPERADORES_C = {'#', '##', '<:', ':>', '<%', '%>', '%:', '%:%:'}
OPERADORES_C = {op: tipo for op, tipo in OPERADORES.items() if op not in _OPERADORES_JAVA}
OPERADORES_JAVA = {op: tipo for op, tipo in OPERADORES.items() if op not in _OPERADORES_C}


def palavra_reservada(token):
    tipo, lexema = (token['tipo'], token['lexema']) if isinstance(token, dict) else (token.tipo, token.lexema)
    return ((tipo == 'KEYWORD' and lexema in PALAVRAS_DIRETIVAS_C) or
            (tipo != 'IDENTIFIER' and RESERVADAS.get(lexema) == tipo))
