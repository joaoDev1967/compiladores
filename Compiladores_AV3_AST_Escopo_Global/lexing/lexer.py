"""Tokenização de C com lexemas, localizações e recuperação lexical."""
import re

from lexing.tokens import (
    Diagnostico, OPERADORES, OPERADORES_C, RESERVADAS, RESERVADAS_C, Token,
)


def _regex_operadores(operadores):
    return re.compile('|'.join(re.escape(op) for op in sorted(operadores, key=len, reverse=True)))


_REGEX_OPERADORES = {None: _regex_operadores(OPERADORES),
                    'c': _regex_operadores(OPERADORES_C)}
_RESERVADAS = {None: RESERVADAS, 'c': RESERVADAS_C}
_ESPACOS = re.compile(r'\s+')
_QUEBRA = re.compile(r'\r\n|\r|\n')
_DIRETIVA = re.compile(r'(?:#|%:)(?:\\(?:\r\n|\r|\n)|[^\r\n])*')
# Lê números candidatos de uma vez para evitar, por exemplo, 0x -> 0 + x.
_CANDIDATO_DEC = re.compile(r'(?:[0-9]|\.[0-9])(?:[eE][+-]|[\w$.])*')
_CANDIDATO_HEX = re.compile(r'0[xX](?:[pP][+-]|[\w$.])*')
_ESCAPE_C = r"\\(?:['\"?\\abfnrtv]|[0-7]{1,3}|x[0-9A-Fa-f]+|u[0-9A-Fa-f]{4}|U[0-9A-Fa-f]{8})"
_CHAR = {
    'c': re.compile(r"[^'\\\r\n]|" + _ESCAPE_C),
    None: re.compile(r"[^'\\\r\n]|" + _ESCAPE_C),
}
_STRING = {
    'c': re.compile(r"(?:[^\\]|" + _ESCAPE_C + r"|\\(?:\r\n|\r|\n))*"),
    None: re.compile(r"(?:[^\\]|" + _ESCAPE_C + ")*"),
}
_ABERTURA_BLOCO_TEXTO = re.compile(r'[ \t\f]*(?:\r\n|\r|\n)')
_PREFIXO_C = re.compile(r"""(?:u8|[LuU])(?=['"])""")


def _regex_numeros(linguagem):
    separador = '_*' if linguagem != 'c' else ''
    dig = r'[0-9](?:' + separador + r'[0-9])*'
    hexdig = r'[0-9a-fA-F](?:' + separador + r'[0-9a-fA-F])*'
    bindig = r'[01](?:' + separador + r'[01])*'
    octdig = r'0(?:' + separador + r'[0-7])*'
    sufixo_int_c = r'(?:[uU](?:ll|LL|[lL])?|(?:ll|LL|[lL])[uU]?)?'
    sufixo_int = sufixo_int_c
    sufixo_real = r'[fFlL]?'
    expoente = r'[eE][+-]?' + dig
    decimal = r'(?:' + dig + r'\.(?:' + dig + r')?|\.' + dig + ')'
    hex_real = r'0[xX](?:' + hexdig + r'(?:\.(?:' + hexdig + r')?)?|\.' + hexdig + ')'
    formas = [
        r'(?:[1-9](?:' + separador + '[0-9])*|' + octdig + ')' + sufixo_int,
        r'0[xX]' + hexdig + sufixo_int,
        r'0[bB]' + bindig + sufixo_int,
        r'(?:' + decimal + r'(?:' + expoente + ')?|' + dig + expoente + ')' + sufixo_real,
        hex_real + r'[pP][+-]?' + dig + sufixo_real,
    ]
    return re.compile('|'.join(formas))


_NUMEROS = {linguagem: _regex_numeros(linguagem) for linguagem in (None, 'c')}


def _fim_aspas(codigo, inicio, aspas, aceita_continuacao=False):
    i = inicio + len(aspas)
    while i < len(codigo):
        if codigo.startswith(aspas, i):
            return i + len(aspas)
        if len(aspas) == 1 and codigo[i] in '\r\n':
            break
        if codigo[i] == '\\' and i + 1 < len(codigo):
            quebra = _QUEBRA.match(codigo, i + 1)
            if quebra and aceita_continuacao:
                i = quebra.end()
                continue
            if not quebra:
                i += 1
        i += 1
    return None


def _inicio_id(caractere):
    return caractere == '$' or caractere.isidentifier()


def _parte_id(caractere):
    return caractere == '$' or ('_' + caractere).isidentifier()


def _pular_espacos_diretiva(texto, posicao):
    while posicao < len(texto):
        if texto[posicao] in ' \t\f\v':
            posicao += 1
        elif texto[posicao] == '\\' and _QUEBRA.match(texto, posicao + 1):
            posicao = _QUEBRA.match(texto, posicao + 1).end()
        elif texto.startswith('/*', posicao):
            fim = texto.find('*/', posicao + 2)
            if fim < 0:
                break
            posicao = fim + 2
        elif texto.startswith('//', posicao):
            return len(texto)
        else:
            break
    return posicao


def _separar_include(texto, linha, coluna, primeira_ordem):
    """Separa a diretiva sem reservar globalmente a palavra include.

    Outras diretivas permanecem opacas. Um argumento de macro também é mantido
    como trecho do pré-processador; não há expansão de macros neste analisador.
    """
    tamanho_marca = 2 if texto.startswith('%:') else 1
    inicio_nome = _pular_espacos_diretiva(texto, tamanho_marca)
    fim_nome = inicio_nome
    while fim_nome < len(texto) and _parte_id(texto[fim_nome]):
        fim_nome += 1
    if texto[inicio_nome:fim_nome] != 'include':
        return None
    tokens, erros = [], []

    def localizacao(offset):
        partes = _QUEBRA.split(texto[:offset])
        if len(partes) > 1:
            return linha + len(partes) - 1, len(partes[-1]) + 1
        return linha, coluna + offset

    def emitir(tipo, inicio, fim):
        l, c = localizacao(inicio)
        tokens.append(Token(tipo, texto[inicio:fim], l, c, primeira_ordem + len(tokens)))

    def diagnosticar(offset, mensagem):
        l, c = localizacao(offset)
        erros.append(Diagnostico('LÉXICO', l, c, mensagem))

    emitir('PUNCTUATOR', 0, tamanho_marca)
    emitir('KEYWORD', inicio_nome, fim_nome)
    inicio = _pular_espacos_diretiva(texto, fim_nome)
    if inicio == len(texto):
        diagnosticar(fim_nome, 'Falta nome de cabeçalho após #include.')
        return tokens, erros
    if texto[inicio] not in ('<', '"'):
        emitir('PP_ARGUMENT', inicio, len(texto))
        return tokens, erros

    fechamento = '>' if texto[inicio] == '<' else '"'
    fim = texto.find(fechamento, inicio + 1)
    if fim < 0:
        emitir('INVALID_HEADER_NAME', inicio, len(texto))
        diagnosticar(inicio, 'Nome de cabeçalho não fechado em #include.')
        return tokens, erros
    if fim == inicio + 1:
        emitir('INVALID_HEADER_NAME', inicio, fim + 1)
        diagnosticar(inicio, 'Nome de cabeçalho vazio em #include.')
    else:
        emitir('HEADER_NAME', inicio, fim + 1)
    restante = _pular_espacos_diretiva(texto, fim + 1)
    if restante < len(texto):
        emitir('INVALID_PREPROCESSOR', restante, len(texto))
        diagnosticar(restante, 'Conteúdo inesperado após o cabeçalho de #include.')
    return tokens, erros


def tokenizar(codigo: str, linguagem=None):
    """Reconhece os tokens da extensão ou do modo didático padrão."""
    reservadas = _RESERVADAS[linguagem]
    operadores = _REGEX_OPERADORES[linguagem]
    tokens, erros = [], []
    posicao, linha, coluna = 0, 1, 1
    linha_so_espaco = True

    while posicao < len(codigo):
        inicio = posicao
        atual = codigo[inicio]
        tipo, erro = None, None
        espacos = _ESPACOS.match(codigo, inicio) if atual.isspace() else None

        if espacos:
            posicao = espacos.end()
        elif codigo.startswith('//', inicio):
            quebra = _QUEBRA.search(codigo, inicio)
            # Em C, a junção de linhas ocorre antes de remover comentários.
            while quebra and codigo[quebra.start() - 1] == '\\':
                quebra = _QUEBRA.search(codigo, quebra.end())
            posicao = quebra.start() if quebra else len(codigo)
        elif codigo.startswith('/*', inicio):
            fechamento = codigo.find('*/', inicio + 2)
            if fechamento < 0:
                erros.append(Diagnostico('LÉXICO', linha, coluna, 'Comentário de bloco não terminado.'))
                break
            posicao = fechamento + 2
        elif (linha_so_espaco and
              (atual == '#' or (codigo.startswith('%:', inicio) and
                                not codigo.startswith('%:%:', inicio)))):
            tipo, posicao = 'PREPROCESSADOR', _DIRETIVA.match(codigo, inicio).end()
        else:
            # Prefixos C de string/char fazem parte do mesmo lexema.
            prefixo = _PREFIXO_C.match(codigo, inicio) if atual in 'LuU' else None
            pos_aspa = prefixo.end() if prefixo else inicio
            aspa = codigo[pos_aspa]
            if aspa in ('"', "'"):
                aspas = aspa
                fim = _fim_aspas(codigo, pos_aspa, aspas,
                                 aceita_continuacao=linguagem == 'c' and aspa == '"')
                if fim is None:
                    if len(aspas) == 3:
                        posicao = len(codigo)
                    else:
                        quebra = _QUEBRA.search(codigo, pos_aspa)
                        limite = quebra.start() if quebra else len(codigo)
                        semi = codigo.find(';', pos_aspa, limite)
                        posicao = semi if semi >= 0 else limite
                    tipo, erro = 'INVALID_LITERAL', 'Literal não fechado.'
                else:
                    posicao = fim
                    tipo = 'STRING' if aspa == '"' else 'CHAR_LITERAL'
                    conteudo = codigo[pos_aspa + len(aspas):fim - len(aspas)]
                    if tipo == 'CHAR_LITERAL' and not _CHAR[linguagem].fullmatch(conteudo):
                        tipo, erro = 'INVALID_LITERAL', 'Literal de caractere inválido.'
                    elif tipo == 'STRING':
                        padrao = _STRING[linguagem]
                        if not padrao.fullmatch(conteudo):
                            tipo, erro = 'INVALID_LITERAL', 'Escape inválido no literal de texto.'
            else:
                numero = (_CANDIDATO_HEX if codigo.startswith(('0x', '0X'), inicio)
                          else _CANDIDATO_DEC).match(codigo, inicio)
                if numero:
                    posicao = numero.end()
                    texto = numero.group()
                    tipo = 'NUMBER'
                    if not _NUMEROS[linguagem].fullmatch(texto):
                        tipo, erro = 'INVALID_NUMBER', 'Número inválido: {!r}.'.format(texto)
                elif _inicio_id(atual):
                    posicao = inicio + 1
                    while posicao < len(codigo) and _parte_id(codigo[posicao]):
                        posicao += 1
                    texto = codigo[inicio:posicao]
                    tipo = reservadas.get(texto, 'IDENTIFIER')
                    if linguagem == 'c' and '$' in texto:
                        tipo, erro = 'INVALID_IDENTIFIER', "Identificador inválido em C: {!r}.".format(texto)
                else:
                    operador = operadores.match(codigo, inicio)
                    # A chamada sem linguagem preserva o formato de anotação do modo didático.
                    arroba_solto = (linguagem is None and atual == '@' and
                                   not (inicio + 1 < len(codigo) and _inicio_id(codigo[inicio + 1])))
                    if operador and not arroba_solto:
                        posicao, tipo = operador.end(), OPERADORES[operador.group()]
                    else:
                        posicao = inicio + 1
                        tipo, erro = 'INVALID_CHARACTER', 'Caractere inválido: {!r}.'.format(atual)

        texto = codigo[inicio:posicao]
        if erro:
            erros.append(Diagnostico('LÉXICO', linha, coluna, erro))
        if tipo:
            inclusao = (_separar_include(texto, linha, coluna, len(tokens) + 1)
                        if tipo == 'PREPROCESSADOR' else None)
            if inclusao is None:
                tokens.append(Token(tipo, texto, linha, coluna, len(tokens) + 1))
            else:
                novos, diagnosticos = inclusao
                tokens.extend(novos)
                erros.extend(diagnosticos)
        partes = _QUEBRA.split(texto)
        if len(partes) > 1:
            linha += len(partes) - 1
            coluna = len(partes[-1]) + 1
            linha_so_espaco = not tipo or not partes[-1].strip()
        else:
            coluna += len(texto)
            if tipo:
                linha_so_espaco = False
    return tokens, erros
