"""Distingue declarações de instruções executáveis na hierarquia da AST."""
from lexing.tokens import Diagnostico


PREFIXO_ERRO_CONTEXTO = 'Instrução executável fora de função'

_DECLARACOES = {
    'DECLARACAO', 'TYPEDEF', 'PROTOTIPO', 'PREPROCESSADOR',
    'PACKAGE', 'IMPORT', 'ANOTACAO', 'VAZIO',
}
_INSTRUCOES = {
    'ATRIBUICAO', 'INSTRUCAO_EXPRESSAO', 'IF', 'WHILE', 'FOR', 'FOR_EACH',
    'DO_WHILE', 'SWITCH', 'TRY', 'RETURN', 'THROW', 'BREAK', 'CONTINUE',
    'GOTO', 'ROTULO', 'CASE', 'DEFAULT', 'SYNCHRONIZED', 'ASSERT',
}


def validar_contexto(raiz):
    """Produz um diagnóstico para cada instrução externa completa.

    Um bloco sem função não concede permissão de execução. Classes também
    interrompem o contexto de uma função externa; seus métodos abrem o próprio.
    Cabeçalhos e inicializadores de declarações não são instruções isoladas.
    """
    erros = []
    pendentes = [(raiz, False, False)]
    while pendentes:
        no, em_funcao, bloco_container = pendentes.pop()
        if no.classe in _DECLARACOES:
            continue
        if no.classe in ('FUNCAO', 'CLASSE', 'INTERFACE'):
            corpo_em_funcao = no.classe == 'FUNCAO'
            for filho in reversed(no.filhos):
                if filho.classe == 'BLOCO':
                    pendentes.append((filho, corpo_em_funcao, True))
            continue
        bloco_externo = no.classe == 'BLOCO' and not bloco_container
        if not em_funcao and (no.classe in _INSTRUCOES or bloco_externo):
            token = no.token
            erros.append(Diagnostico(
                'SINTÁTICO', token.linha, token.coluna,
                "{}: '{}'. Comandos devem estar dentro de funções.".format(
                    PREFIXO_ERRO_CONTEXTO, token.lexema)))
            # O comando composto já é inválido; não repete o mesmo erro em seu corpo.
            continue
        for filho in reversed(no.filhos):
            pendentes.append((filho, em_funcao, False))
    return erros
