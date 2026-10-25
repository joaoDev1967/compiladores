from lexing.tokens import *

# Identificadores e palavras reservadas
def t_IDENTIFIER(t):
    r'[a-zA-Z_][a-zA-Z0-9_]*'
    t.type = reserved.get(t.value, 'IDENTIFIER')
    return t


# Números inteiros e de ponto flutuante
def t_NUMBER(t):
    r'0[xX][0-9a-fA-F]+|(?:\d+\.\d*|\.\d+|\d+)(?:[eE][+-]?\d+)?'
    if t.value.lower().startswith('0x'):
        t.value = int(t.value, 16)
    elif any(c in t.value for c in '.eE'):
        t.value = float(t.value)
    else:
        t.value = int(t.value)
    return t


# Strings
def t_STRING(t):
    r'"([^\\\n]|\\.)*"'
    return t


# Literais de caracteres
def t_CHAR_LITERAL(t):
    r"'([^\\\n]|\\.)'"
    return t


# Comentários de uma ou várias linhas
def t_COMMENT(t):
    r'(/\*(.|\n)*?\*/)|(//[^\n]*)'
    t.lexer.lineno += t.value.count('\n')
    # Não retorna token: o comentário é ignorado


# Contagem de linhas
def t_newline(t):
    r'\n+'
    t.lexer.lineno += len(t.value)


# Ignorar espaços, tabulações e etc
t_ignore = ' \t\r'


# Tratamento de caracteres inválidos
def t_error(t):
    print(
        f"Caractere ilegal {t.value[0]!r} "
        f"na linha {t.lexer.lineno}"
    )
    t.lexer.skip(1)