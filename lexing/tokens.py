# Palavras reservadas da linguagem C
reserved = {
    'auto': 'AUTO',
    'break': 'BREAK',
    'case': 'CASE',
    'char': 'CHAR',
    'const': 'CONST',
    'continue': 'CONTINUE',
    'default': 'DEFAULT',
    'do': 'DO',
    'double': 'DOUBLE',
    'else': 'ELSE',
    'enum': 'ENUM',
    'extern': 'EXTERN',
    'float': 'FLOAT',
    'for': 'FOR',
    'goto': 'GOTO',
    'if': 'IF',
    'int': 'INT',
    'long': 'LONG',
    'register': 'REGISTER',
    'return': 'RETURN',
    'short': 'SHORT',
    'signed': 'SIGNED',
    'sizeof': 'SIZEOF',
    'static': 'STATIC',
    'struct': 'STRUCT',
    'switch': 'SWITCH',
    'typedef': 'TYPEDEF',
    'union': 'UNION',
    'unsigned': 'UNSIGNED',
    'void': 'VOID',
    'volatile': 'VOLATILE',
    'while': 'WHILE'
}

# Lista de tokens
tokens = [
    'IDENTIFIER',
    'NUMBER',
    'STRING',
    'CHAR_LITERAL',

    'PLUS', 'MINUS', 'TIMES', 'DIVIDE', 'MOD',
    'ASSIGN', 'EQ', 'NE', 'LT', 'GT', 'LE', 'GE',
    'AND', 'OR', 'NOT',
    'BITAND', 'BITOR', 'BITXOR', 'BITNOT',
    'LSHIFT', 'RSHIFT',
    'INCREMENT', 'DECREMENT',
    'PLUS_ASSIGN', 'MINUS_ASSIGN',
    'TIMES_ASSIGN', 'DIVIDE_ASSIGN', 'MOD_ASSIGN',
    'AND_ASSIGN', 'OR_ASSIGN', 'XOR_ASSIGN',
    'LSHIFT_ASSIGN', 'RSHIFT_ASSIGN',
    'ARROW',

    'LPAREN', 'RPAREN',
    'LBRACE', 'RBRACE',
    'LBRACKET', 'RBRACKET',
    'SEMICOLON', 'COMMA',
    'DOT', 'COLON', 'QUESTION'
] + list(reserved.values())


# Operadores com mais de um caractere
# As regras de string do PLY priorizam expressões mais longas.
t_LSHIFT_ASSIGN = r'<<='
t_RSHIFT_ASSIGN = r'>>='
t_PLUS_ASSIGN = r'\+='
t_MINUS_ASSIGN = r'-='
t_TIMES_ASSIGN = r'\*='
t_DIVIDE_ASSIGN = r'/='
t_MOD_ASSIGN = r'%='
t_AND_ASSIGN = r'&='
t_OR_ASSIGN = r'\|='
t_XOR_ASSIGN = r'\^='

t_INCREMENT = r'\+\+'
t_DECREMENT = r'--'
t_ARROW = r'->'
t_EQ = r'=='
t_NE = r'!='
t_LE = r'<='
t_GE = r'>='
t_AND = r'&&'
t_OR = r'\|\|'
t_LSHIFT = r'<<'
t_RSHIFT = r'>>'

# Operadores de um caractere
t_PLUS = r'\+'
t_MINUS = r'-'
t_TIMES = r'\*'
t_DIVIDE = r'/'
t_MOD = r'%'
t_ASSIGN = r'='
t_LT = r'<'
t_GT = r'>'
t_NOT = r'!'
t_BITAND = r'&'
t_BITOR = r'\|'
t_BITXOR = r'\^'
t_BITNOT = r'~'

# Delimitadores
t_LPAREN = r'\('
t_RPAREN = r'\)'
t_LBRACE = r'\{'
t_RBRACE = r'\}'
t_LBRACKET = r'\['
t_RBRACKET = r'\]'
t_SEMICOLON = r';'
t_COMMA = r','
t_DOT = r'\.'
t_COLON = r':'
t_QUESTION = r'\?'
