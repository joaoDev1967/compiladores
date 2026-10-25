
#   PLY é uma lib própria para criação de compiladores.
#   .lex é o módulo de análise léxica
import ply.lex as lex
from lexing.lexer import *

#   Instancia do o analisador léxico em um objeto
lexer = lex.lex()


#   Exemplo de utilização
if __name__ == '__main__':
    
    # === FASE DE LEXING ===
    # BTW: Atualizar para suportar o nome do arquivo via args
    with open('hello.c', 'r') as f:
        codigo = f.read()

    lexer.input(codigo)

    while True:
        token = lexer.token()
        if token is None:
            break

    # BTW:  A tabela de lexing e de simbolos geralmente ficam
    #       armazenadas na RAM, é bom colocar pelo menos um dict
    #       pra deixar armazenado.
        print(
            f"Tipo: {token.type:<15} "
            f"Valor: {token.value!r:<22} "
            f"Linha: {token.lineno}"
        )
