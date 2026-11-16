"""Expressões com precedência, chamadas, acesso, indexação e efeitos de escrita."""
from sintatico.ast import ErroSintaxe, NoAST


class ExpressaoParser:
    PRECEDENCIA = {
        'ASSIGN': 1, 'PLUS_ASSIGN': 1, 'MINUS_ASSIGN': 1, 'TIMES_ASSIGN': 1,
        'DIVIDE_ASSIGN': 1, 'MOD_ASSIGN': 1, 'AND_ASSIGN': 1, 'OR_ASSIGN': 1,
        'XOR_ASSIGN': 1, 'LSHIFT_ASSIGN': 1, 'RSHIFT_ASSIGN': 1, 'URSHIFT_ASSIGN': 1,
        'QUESTION': 2, 'OR': 3, 'AND': 4, 'BITOR': 5, 'BITXOR': 6, 'BITAND': 7,
        'EQ': 8, 'NE': 8, 'LT': 9, 'LE': 9, 'GT': 9, 'GE': 9, 'INSTANCEOF': 9,
        'LSHIFT': 10, 'RSHIFT': 10, 'URSHIFT': 10,
        'PLUS': 11, 'MINUS': 11, 'TIMES': 12, 'DIVIDE': 12, 'MOD': 12,
    }

    def __init__(self, tokens, posicao=0):
        self.tokens, self.i = tokens, posicao

    def atual(self):
        return self.tokens[self.i] if self.i < len(self.tokens) else None

    def exigir(self, tipo, mensagem):
        tok = self.atual()
        if tok is None or tok.tipo != tipo:
            raise ErroSintaxe(tok or (self.tokens[-1] if self.tokens else None), mensagem)
        self.i += 1
        return tok

    def expressao(self, minima=0):
        esquerdo = self.primario()
        while self.atual():
            tok = self.atual()
            prec = self.PRECEDENCIA.get(tok.tipo, -1)
            if prec < minima:
                break
            self.i += 1
            if tok.tipo == 'QUESTION':
                meio = self.expressao()
                self.exigir('COLON', "Falta ':' na expressão condicional.")
                direito = self.expressao(prec)
                esquerdo = NoAST('TERNARIO', '?:', tok, [esquerdo, meio, direito])
            else:
                atribuicao = prec == 1
                if atribuicao and esquerdo.classe not in ('ID', 'ACESSO', 'INDICE'):
                    raise ErroSintaxe(tok, 'Lado esquerdo de atribuição inválido.')
                if tok.tipo == 'INSTANCEOF':
                    nome = self.exigir('IDENTIFIER', 'Esperado tipo após instanceof.')
                    direito = NoAST('TIPO_REFERENCIA', nome.lexema, nome)
                else:
                    direito = self.expressao(prec if atribuicao else prec + 1)
                classe = 'ATRIBUICAO_EXPRESSAO' if atribuicao else 'OP'
                esquerdo = NoAST(classe, tok.lexema, tok, [esquerdo, direito])
        return esquerdo

    def primario(self):
        tok = self.atual()
        if tok is None:
            raise ErroSintaxe(None, 'Expressão incompleta: operando ausente.')
        self.i += 1
        classes = {'NUMBER': 'NUM', 'IDENTIFIER': 'ID', 'STRING': 'STRING',
                   'CHAR_LITERAL': 'CHAR', 'TRUE': 'BOOL', 'FALSE': 'BOOL',
                   'NULL': 'NULL', 'THIS': 'REFERENCIA', 'SUPER': 'REFERENCIA'}
        if tok.tipo in classes:
            no = NoAST(classes[tok.tipo], tok.lexema, tok)
        elif tok.tipo in ('PLUS', 'MINUS', 'NOT', 'BITNOT', 'TIMES', 'BITAND',
                          'INCREMENT', 'DECREMENT'):
            filho = self.expressao(13)
            if tok.tipo in ('INCREMENT', 'DECREMENT') and filho.classe not in ('ID', 'ACESSO', 'INDICE'):
                raise ErroSintaxe(tok, 'Operando inválido para incremento/decremento.')
            return NoAST('UNARIO', tok.lexema, tok, [filho])
        elif tok.tipo == 'LPAREN':
            no = self.expressao()
            self.exigir('RPAREN', "Falta ')' na expressão.")
        else:
            raise ErroSintaxe(tok, "Esperado identificador, número ou literal; encontrado '{}'.".format(tok.lexema))
        return self.posfixo(no)

    def posfixo(self, no):
        while self.atual():
            tok = self.atual()
            if tok.tipo == 'LPAREN':
                self.i += 1
                argumentos = []
                if self.atual() and self.atual().tipo != 'RPAREN':
                    while True:
                        argumentos.append(self.expressao())
                        if not self.atual() or self.atual().tipo != 'COMMA':
                            break
                        self.i += 1
                self.exigir('RPAREN', "Falta ')' na chamada.")
                no = NoAST('CHAMADA', no.valor if no.classe == 'ID' else '', no.token,
                           [no, NoAST('ARGUMENTOS', '', tok, argumentos)])
            elif tok.tipo == 'LBRACKET':
                self.i += 1
                indice = self.expressao()
                self.exigir('RBRACKET', "Falta ']' na indexação.")
                no = NoAST('INDICE', '', tok, [no, indice])
            elif tok.tipo in ('DOT', 'ARROW', 'METHOD_REF'):
                self.i += 1
                membro = self.exigir('IDENTIFIER', 'Esperado nome do membro.')
                no = NoAST('ACESSO', tok.lexema, tok,
                           [no, NoAST('MEMBRO', membro.lexema, membro)])
            elif tok.tipo in ('INCREMENT', 'DECREMENT'):
                if no.classe not in ('ID', 'ACESSO', 'INDICE'):
                    raise ErroSintaxe(tok, 'Operando inválido para incremento/decremento.')
                self.i += 1
                no = NoAST('POSFIXO', tok.lexema, tok, [no])
            else:
                break
        return no
