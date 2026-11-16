"""Parser C/Java didático com AST hierárquica, escopos e recuperação."""
from contextlib import contextmanager
from lexing.tokens import (
    Diagnostico, MODIFICADORES_C, MODIFICADORES_JAVA, TIPOS_C, TIPOS_JAVA,
)
from semantica.analisador import AmbienteSemantico
from sintatico.ast import ErroSintaxe, NoAST, formatar_ast
from sintatico.contexto import validar_contexto
from sintatico.expressoes import ExpressaoParser


class AnalisadorSintatico:
    """Declarações, funções, expressões e estruturas de controle reconhecidas."""
    def __init__(self, tokens, tabela, linguagem=None):
        self.tokens = tokens
        self.i = 0
        self.linguagem = linguagem
        self.ambiente = AmbienteSemantico(tabela, linguagem)
        self.modificadores = {
            'c': MODIFICADORES_C, 'java': MODIFICADORES_JAVA,
            None: MODIFICADORES_C | MODIFICADORES_JAVA,
        }[linguagem]
        self.tipos = {
            'c': TIPOS_C, 'java': TIPOS_JAVA | {'String'},
            None: TIPOS_C | TIPOS_JAVA | {'String'},
        }[linguagem]
        self._declaradores = {}
        self.arvore = NoAST('PROGRAMA', token=tokens[0] if tokens else None)
        self._destinos_ast = [self.arvore.filhos]
        self.erros = []
        self.ignorados = 0

    def _emitir(self, no):
        self._destinos_ast[-1].append(no)
        return no

    @contextmanager
    def _contexto_ast(self, no):
        self._destinos_ast.append(no.filhos)
        try:
            yield
        finally:
            self._destinos_ast.pop()

    def _expressao_trecho(self, tokens):
        if not tokens:
            return None
        parser = ExpressaoParser(tokens, 0)
        expressoes = [parser.expressao()]
        while parser.atual() and parser.atual().tipo == 'COMMA':
            parser.i += 1
            expressoes.append(parser.expressao())
        if parser.atual():
            raise ErroSintaxe(parser.atual(), "Token inesperado na expressão: '{}'.".format(parser.atual().lexema))
        return expressoes[0] if len(expressoes) == 1 else NoAST('LISTA_EXPRESSOES', '', tokens[0], expressoes)

    def _corpo(self, dono, rotulo='CORPO'):
        if not self.atual() or self.atual().tipo == 'RBRACE':
            raise ErroSintaxe(dono.token, 'Falta corpo do {}.'.format(dono.valor or dono.classe.lower()))
        no = NoAST(rotulo, token=self.atual())
        dono.filhos.append(no)
        with self._contexto_ast(no):
            self._item()
        return no

    def atual(self):
        return self.tokens[self.i] if self.i < len(self.tokens) else None

    def _olhar(self, n=1):
        pos = self.i + n
        return self.tokens[pos] if pos < len(self.tokens) else None

    def _exigir(self, tipo, mensagem, *, retomar_instrucao=False):
        tok = self.atual()
        if tok is None or tok.tipo != tipo:
            raise ErroSintaxe(tok or (self.tokens[-1] if self.tokens else None),
                              mensagem, retomar_instrucao)
        self.i += 1
        return tok

    def _erro(self, erro, origem=None):
        onde = erro.token or origem or (self.tokens[-1] if self.tokens else None)
        if onde is not None and not onde.tipo.startswith('INVALID_'):
            self.erros.append(Diagnostico('SINTÁTICO', onde.linha, onde.coluna, erro.mensagem))

    def _parse_expressao(self):
        parser = ExpressaoParser(self.tokens, self.i)
        expr = parser.expressao()
        self.i = parser.i
        return expr

    def _tipo_base(self, tok):
        return tok and (tok.lexema in self.tipos or self.ambiente.tipo_alias(tok.lexema))

    def _tipo_comeco(self, tok):
        return bool(tok and (tok.lexema in self.modificadores or self._tipo_base(tok)))

    def _tipo(self):
        """Reconhece tipos compostos e para no nome de um declarador."""
        inicio = self.atual()
        qualif, bases = [], []
        alias = None
        while self.atual() is not None:
            palavra = self.atual().lexema
            if palavra in self.modificadores:
                qualif.append(palavra)
            elif palavra in self.tipos and not (bases and palavra == 'String'):
                bases.append(palavra)
            elif not bases and not {'signed', 'unsigned'}.intersection(qualif):
                alias = self.ambiente.tipo_alias(palavra)
                if alias is None:
                    break
                bases.append(palavra)
            else:
                break
            self.i += 1
        sinais = [q for q in qualif if q in ('signed', 'unsigned')]
        if not bases:
            if not sinais:
                raise ErroSintaxe(inicio, 'Esperado tipo após modificadores.')
            bases = ['int']
        base = alias or ' '.join(bases)
        if len(bases) > 1:
            partes = sorted(bases)
            combinacoes = {
                ('int', 'long'): 'long int', ('int', 'short'): 'short int',
                ('long', 'long'): 'long long', ('int', 'long', 'long'): 'long long int',
                ('double', 'long'): 'long double',
            }
            base = combinacoes.get(tuple(partes))
            if not base or self.linguagem == 'java':
                raise ErroSintaxe(inicio, 'Combinação de tipos inválida: {}.'.format(' '.join(bases)))
        if sinais:
            if len(sinais) != 1 or alias or base not in {
                'char', 'short', 'short int', 'int', 'long', 'long int', 'long long', 'long long int'
            }:
                raise ErroSintaxe(inicio, 'Qualificador signed/unsigned incompatível com o tipo.')
            base = sinais[0] + ' ' + base
        while self.atual() and self.atual().tipo == 'LBRACKET' and self.linguagem != 'c':
            self.i += 1
            self._exigir('RBRACKET', "Esperado ']' em tipo de array.")
            base += '[]'
        return inicio, base, qualif

    def _nome_declarador(self, base, nome_opcional=False):
        ponteiros = 0
        while self.atual() and self.atual().tipo == 'TIMES':
            if self.linguagem == 'java':
                raise ErroSintaxe(self.atual(), 'Declarador de ponteiro fora da gramática Java.')
            ponteiros += 1
            self.i += 1
        nome = self.atual()
        if nome_opcional and (nome is None or nome.tipo != 'IDENTIFIER'):
            nome = None
        else:
            nome = self._exigir('IDENTIFIER', 'Esperado nome de variável/função após tipo.')
        tipo = base + '*' * ponteiros
        dimensoes = []
        while self.atual() and self.atual().tipo == 'LBRACKET':
            abertura = self.atual()
            self.i += 1
            tamanho = []
            if self.linguagem != 'java' and self.atual() and self.atual().tipo in ('NUMBER', 'IDENTIFIER'):
                token = self.atual()
                tamanho.append(NoAST('NUM' if token.tipo == 'NUMBER' else 'ID', token.lexema, token))
                self.i += 1
            self._exigir('RBRACKET', "Esperado ']' na declaração de array.")
            dimensoes.append(NoAST('DIMENSAO', '', abertura, tamanho))
            tipo += '[]'
        if nome is not None and dimensoes:
            self._declaradores[nome.ordem] = dimensoes
        return nome, tipo

    def _parametros(self):
        self._exigir('LPAREN', "Esperado '(' na função.")
        tok = self.atual()
        if tok and tok.tipo == 'RPAREN':
            self.i += 1
            return [], False
        if (self.linguagem != 'java' and tok and tok.tipo == 'VOID' and
                self._olhar() and self._olhar().tipo == 'RPAREN'):
            self.i += 2
            return [], False

        parametros = []
        while True:
            inicio, base, qualificadores = self._tipo()
            variadico_java = self.linguagem == 'java' and self.atual() and self.atual().tipo == 'ELLIPSIS'
            if variadico_java:
                self.i += 1
                base += '[]'
            nome, tipo = self._nome_declarador(base, nome_opcional=self.linguagem != 'java')
            if tipo == 'void' or tipo.startswith('void[]'):
                raise ErroSintaxe(nome or inicio, 'Parâmetro precisa ter um tipo diferente de void.')
            parametros.append((nome, tipo, 'final' in qualificadores))
            if self.atual() and self.atual().tipo == 'COMMA' and not variadico_java:
                self.i += 1
                if (self.linguagem != 'java' and self.atual() and self.atual().tipo == 'ELLIPSIS'):
                    self.i += 1
                    self._exigir('RPAREN', "Esperado ')' após '...' na assinatura.")
                    return parametros, True
                continue
            self._exigir('RPAREN', "Esperado ',' ou ')' na lista de parâmetros.")
            return parametros, False

    def _pular_parenteses(self):
        self._exigir('LPAREN', "Esperado '('.")
        inicio, profundidade = self.i, 1
        while self.atual():
            tok = self.atual()
            if tok.tipo == 'LPAREN':
                profundidade += 1
            elif tok.tipo == 'RPAREN':
                profundidade -= 1
                if profundidade == 0:
                    partes = self.tokens[inicio:self.i]
                    self.i += 1
                    return partes
            self.i += 1
        raise ErroSintaxe(self.tokens[-1], "Falta ')' no cabeçalho.")

    def _adiar_corpo_java(self, metodos, parametros, funcao):
        """Guarda o bloco para depois de cadastrar os campos da classe."""
        inicio = self.i
        profundidade = 0
        while self.atual():
            token = self.atual()
            self.i += 1
            if token.tipo == 'LBRACE':
                profundidade += 1
            elif token.tipo == 'RBRACE':
                profundidade -= 1
                if profundidade == 0:
                    break
        metodos.append((inicio, self.i, parametros, funcao))

    def _funcao(self, nome, tipo, metodos, qualificadores=()):
        parametros, variadico = self._parametros()
        excecoes = []
        if self.linguagem != 'c' and self.atual() and self.atual().tipo == 'THROWS':
            throws = self.atual()
            self.i += 1
            while True:
                excecao = self._exigir('IDENTIFIER', "Esperado nome de exceção após 'throws' ou ','.")
                partes = [excecao.lexema]
                while self.atual() and self.atual().tipo == 'DOT':
                    self.i += 1
                    partes.append(self._exigir('IDENTIFIER', "Esperado nome após '.'.").lexema)
                excecoes.append(NoAST('TIPO_REFERENCIA', '.'.join(partes), excecao))
                if not self.atual() or self.atual().tipo != 'COMMA':
                    break
                self.i += 1
        seguinte = self.atual()
        if not seguinte or seguinte.tipo not in ('LBRACE', 'SEMICOLON'):
            raise ErroSintaxe(seguinte or nome, "Esperado '{' ou ';' após função.")
        definido = seguinte.tipo == 'LBRACE'
        if definido and any(tok is None for tok, _, _ in parametros):
            raise ErroSintaxe(nome, 'Parâmetro sem nome na definição da função.')
        assinatura = tuple(tipo for _, tipo, _ in parametros) + (('...',) if variadico else ())
        self.ambiente.declarar(nome, tipo, 'Função', assinatura, definido)
        filhos = [NoAST('TIPO', tipo, nome), NoAST('ID', nome.lexema, nome)]
        if qualificadores:
            filhos.insert(0, NoAST('MODIFICADORES', ' '.join(qualificadores), nome))
        nos_parametros = []
        for tok, tipo_parametro, final in parametros:
            nos = [NoAST('TIPO', tipo_parametro, tok or nome)]
            if tok is not None:
                nos.append(NoAST('ID', tok.lexema, tok))
                if tok.ordem in self._declaradores:
                    nos.append(NoAST('DIMENSOES', '', tok, self._declaradores[tok.ordem]))
            if final:
                nos.insert(0, NoAST('MODIFICADORES', 'final', tok or nome))
            nos_parametros.append(NoAST('PARAMETRO', tok.lexema if tok else '', tok or nome, nos))
        if variadico:
            nos_parametros.append(NoAST('VARIADICO', '...', nome))
        filhos.append(NoAST('PARAMETROS', '', nome, nos_parametros))
        if excecoes:
            filhos.append(NoAST('THROWS', '', throws, excecoes))
        funcao = self._emitir(NoAST('FUNCAO' if definido else 'PROTOTIPO', nome.lexema, nome, filhos))
        if definido and metodos is not None:
            self._adiar_corpo_java(metodos, parametros, funcao)
        elif definido:
            with self._contexto_ast(funcao):
                self._bloco(parametros=parametros, rotulo='funcao')
        else:
            self.i += 1
            if parametros:
                self.ambiente.tabela.entrar_escopo('prototipo')
                for tok, tipo_parametro, final in parametros:
                    if tok is not None:
                        self.ambiente.declarar(tok, tipo_parametro, 'Parâmetro',
                                               final=final, inicializado=True)
                self.ambiente.tabela.sair_escopo()

    def declaracao(self, typedef=False, permite_funcao=True, metodos=None):
        """Transação: não registra nomes/AST até validar toda a sintaxe."""
        token_tipo, base, qualificadores = self._tipo()
        if typedef:
            nome, tipo = self._nome_declarador(base)
            if tipo != base:
                raise ErroSintaxe(nome, 'typedef de ponteiro/array fora da gramática simplificada.')
            self._exigir('SEMICOLON', "Falta ';' após typedef.", retomar_instrucao=True)
            self.ambiente.declarar(nome, tipo, 'Tipo')
            self._emitir(NoAST('TYPEDEF', nome.lexema, nome,
                               [NoAST('TIPO', tipo, token_tipo), NoAST('ID', nome.lexema, nome)]))
            return

        primeiro, tipo = self._nome_declarador(base)
        if self.atual() and self.atual().tipo == 'LPAREN':
            if not permite_funcao:
                raise ErroSintaxe(primeiro, 'Função não pode iniciar um laço for.')
            self._funcao(primeiro, tipo, metodos, qualificadores)
            return
        novos = []
        nome = primeiro
        while True:
            if tipo == 'void' or tipo.startswith('void[]'):
                raise ErroSintaxe(nome, 'Variável precisa ter um tipo diferente de void.')
            expr = None
            tok = self.atual()
            if tok and tok.tipo == 'ASSIGN':
                self.i += 1
                if self.atual() and self.atual().tipo == 'LBRACE':
                    raise ErroSintaxe(self.atual(),
                        'Inicializador de agregado { ... } fora da gramática simplificada.')
                expr = self._parse_expressao()
            novos.append((nome, tipo, expr, tok if tok and tok.tipo == 'ASSIGN' else None))
            tok = self.atual()
            if tok and tok.tipo == 'COMMA':
                self.i += 1
                nome, tipo = self._nome_declarador(base)
                continue
            self._exigir('SEMICOLON', "Falta ';' ao final da declaração.", retomar_instrucao=True)
            break
        for nome, tipo, expr, igual in novos:
            if self.ambiente.declarar(nome, tipo, final='final' in qualificadores,
                                       inicializado=expr is not None) and expr is not None:
                self.ambiente.validar_inicializador(nome, tipo, expr)
            nos = [NoAST('TIPO', tipo, token_tipo), NoAST('ID', nome.lexema, nome)]
            if qualificadores:
                nos.insert(0, NoAST('MODIFICADORES', ' '.join(qualificadores), token_tipo))
            if nome.ordem in self._declaradores:
                nos.append(NoAST('DIMENSOES', '', nome, self._declaradores[nome.ordem]))
            if expr is not None:
                nos.extend([NoAST('ATRIB', '=', igual), expr])
            self._emitir(NoAST('DECLARACAO', '', nome, nos))

    def atribuicao(self):
        alvo = self._exigir('IDENTIFIER', 'Esperado identificador à esquerda de =.')
        igual = self._exigir('ASSIGN', "Falta '=' na atribuição.")
        expr = self._parse_expressao()
        self._exigir('SEMICOLON', "Falta ';' ao final da atribuição.", retomar_instrucao=True)
        self._emitir(NoAST('ATRIBUICAO', '', alvo, [
            NoAST('ID', alvo.lexema, alvo), NoAST('ATRIB', igual.lexema, igual), expr]))
        self.ambiente.validar_atribuicao(alvo, expr)

    def _recuperar(self, origem, erro):
        """Sincronização por ';', respeitando {} internos de um inicializador."""
        n = 0
        while self.atual():
            tok = self.atual()
            seguinte = self._olhar()
            inicio_provavel = tok.linha > origem.linha or (erro.retomar_instrucao and tok is erro.token)
            if n == 0 and inicio_provavel and (
                    self._tipo_comeco(tok) or tok.tipo == 'TYPEDEF' or
                    (tok.tipo == 'IDENTIFIER' and seguinte and seguinte.tipo == 'ASSIGN')):
                return
            if tok.tipo == 'LBRACE':
                n += 1
            elif tok.tipo == 'RBRACE':
                if n == 0:
                    return
                n -= 1
            elif tok.tipo == 'SEMICOLON' and n == 0:
                self.i += 1
                return
            self.i += 1

    def _bloco(self, parametros=None, rotulo='bloco'):
        abertura = self._exigir('LBRACE', "Esperado '{'.")
        bloco = self._emitir(NoAST('BLOCO', token=abertura))
        self.ambiente.tabela.entrar_escopo(rotulo)
        for tok, tipo, final in (parametros or []):
            self.ambiente.declarar(tok, tipo, 'Parâmetro', final=final, inicializado=True)
        metodos = [] if rotulo == 'classe' else None
        with self._contexto_ast(bloco):
            caso = None
            while self.atual() and self.atual().tipo != 'RBRACE':
                pos = self.i
                if rotulo == 'switch' and self.atual().tipo in ('CASE', 'DEFAULT'):
                    try:
                        caso = self._caso()
                    except ErroSintaxe as erro:
                        self._erro(erro)
                        self._recuperar(self.tokens[pos], erro)
                elif caso is not None:
                    with self._contexto_ast(caso):
                        self._item(metodos)
                else:
                    self._item(metodos)
                if self.i <= pos:
                    self.i += 1
            fechamento = self.atual() or (self.tokens[-1] if self.tokens else abertura)
            if not self.atual():
                self._erro(ErroSintaxe(abertura, "Faltam 1 chave(s) de fechamento '}'."))
            else:
                self.i += 1
            if metodos:
                self._analisar_corpos_java(metodos)
        self.ambiente.tabela.sair_escopo()
        return bloco

    def _analisar_corpos_java(self, metodos):
        tokens, posicao = self.tokens, self.i
        try:
            for inicio, fim, parametros, funcao in metodos:
                self.tokens, self.i = tokens[inicio:fim], 0
                with self._contexto_ast(funcao):
                    self._bloco(parametros=parametros, rotulo='funcao')
        finally:
            self.tokens, self.i = tokens, posicao

    def _controle(self):
        tok = self.atual()
        self.i += 1
        cabecalho = self._pular_parenteses()
        expr = self._expressao_trecho(cabecalho)
        if expr is None:
            raise ErroSintaxe(tok, 'Condição/seletor não pode ser vazio.')
        if not self.atual() or self.atual().tipo == 'RBRACE':
            raise ErroSintaxe(tok, f'Falta corpo do {tok.lexema}.')
        rotulo = {'SWITCH': 'SELETOR', 'SYNCHRONIZED': 'MONITOR'}.get(tok.tipo, 'CONDICAO')
        no = self._emitir(NoAST(tok.tipo, token=tok, filhos=[NoAST(rotulo, '', tok, [expr])]))
        antes = (self.ambiente.atribuicoes_finais.copy()
                 if tok.tipo == 'IF' and self.linguagem != 'c' else None)
        if tok.tipo == 'SWITCH' and self.atual().tipo == 'LBRACE':
            corpo = NoAST('CORPO', token=self.atual())
            no.filhos.append(corpo)
            with self._contexto_ast(corpo):
                self._bloco(rotulo='switch')
        else:
            self._corpo(no, 'ENTAO' if tok.tipo == 'IF' else 'CORPO')
        if tok.lexema == 'if' and self.atual() and self.atual().lexema == 'else':
            token_else = self.atual()
            self.i += 1
            if not self.atual() or self.atual().tipo == 'RBRACE':
                raise ErroSintaxe(tok, 'Falta corpo do else.')
            depois_if = self.ambiente.atribuicoes_finais
            if antes is not None:
                self.ambiente.atribuicoes_finais = antes
            outro = self._corpo(no, 'ELSE')
            outro.token = token_else
            # Os ramos são mutuamente exclusivos. Após o if, ambos podem ter inicializado.
            if antes is not None:
                self.ambiente.atribuicoes_finais.update(depois_if)

    def _for(self):
        inicio = self.atual()
        self.i += 1
        cabecalho = self._pular_parenteses()
        nivel, separadores, dois_pontos = 0, [], []
        for indice, tok in enumerate(cabecalho):
            if tok.tipo in ('LPAREN', 'LBRACKET', 'LBRACE'):
                nivel += 1
            elif tok.tipo in ('RPAREN', 'RBRACKET', 'RBRACE'):
                nivel -= 1
            elif tok.tipo == 'SEMICOLON' and nivel == 0:
                separadores.append(indice)
            elif tok.tipo == 'COLON' and nivel == 0:
                dois_pontos.append(indice)
        aprimorado = self.linguagem == 'java' and not separadores and len(dois_pontos) == 1
        no = self._emitir(NoAST('FOR_EACH' if aprimorado else 'FOR', token=inicio))
        inicializacao = NoAST('INICIALIZACAO', token=inicio)
        no.filhos.append(inicializacao)
        self.ambiente.tabela.entrar_escopo('for')
        try:
            if len(separadores) == 2:
                tokens, pos = self.tokens, self.i
                self.tokens, self.i = cabecalho[:separadores[0] + 1], 0
                try:
                    with self._contexto_ast(inicializacao):
                        if self._tipo_comeco(self.atual()):
                            self.declaracao(permite_funcao=False)
                        elif separadores[0] > 0:
                            expr = self._expressao_trecho(self.tokens[:-1])
                            if expr.classe == 'ATRIBUICAO_EXPRESSAO' and expr.valor == '=' and expr.filhos[0].classe == 'ID':
                                alvo, valor = expr.filhos
                                self._emitir(NoAST('ATRIBUICAO', '', alvo.token,
                                    [alvo, NoAST('ATRIB', '=', expr.token), valor]))
                                self.ambiente.validar_atribuicao(alvo.token, valor)
                            else:
                                self._emitir(expr)
                except ErroSintaxe as erro:
                    self._erro(erro, inicio)
                finally:
                    self.tokens, self.i = tokens, pos
                for rotulo, trecho in (
                    ('CONDICAO', cabecalho[separadores[0] + 1:separadores[1]]),
                    ('ATUALIZACAO', cabecalho[separadores[1] + 1:]),
                ):
                    expr = self._expressao_trecho(trecho)
                    no.filhos.append(NoAST(rotulo, '', trecho[0] if trecho else inicio,
                                          [expr] if expr is not None else []))
            elif aprimorado:
                tokens, pos = self.tokens, self.i
                self.tokens, self.i = cabecalho[:dois_pontos[0]], 0
                try:
                    token_tipo, base, qualificadores = self._tipo()
                    nome, tipo = self._nome_declarador(base)
                    if self.atual():
                        raise ErroSintaxe(self.atual(), 'Declaração inválida no for aprimorado.')
                    self.ambiente.declarar(nome, tipo, final='final' in qualificadores, inicializado=True)
                    with self._contexto_ast(inicializacao):
                        self._emitir(NoAST('DECLARACAO', '', nome,
                            [NoAST('TIPO', tipo, token_tipo), NoAST('ID', nome.lexema, nome)]))
                finally:
                    self.tokens, self.i = tokens, pos
                iteravel = self._expressao_trecho(cabecalho[dois_pontos[0] + 1:])
                if iteravel is None:
                    raise ErroSintaxe(inicio, 'Falta expressão iterável no for aprimorado.')
                no.filhos.append(NoAST('ITERAVEL', '', iteravel.token, [iteravel]))
            else:
                self._erro(ErroSintaxe(inicio, "Cabeçalho for requer dois ';'."))
            if self.atual() and self.atual().tipo != 'RBRACE':
                self._corpo(no)
            else:
                self._erro(ErroSintaxe(inicio, 'Falta corpo do for.'))
        finally:
            self.ambiente.tabela.sair_escopo()

    def _ignorar_instrucao(self):
        """Preserva explicitamente um trecho fora da gramática implementada."""
        inicio = self.i
        nivel = 0
        while self.atual():
            tok = self.atual()
            if tok.tipo == 'LPAREN':
                nivel += 1
            elif tok.tipo == 'RPAREN':
                nivel = max(nivel - 1, 0)
            elif tok.tipo == 'SEMICOLON' and nivel == 0:
                self.i += 1
                break
            elif tok.tipo in ('LBRACE', 'RBRACE') and nivel == 0:
                break
            self.ignorados += 1
            self.i += 1
        partes = self.tokens[inicio:self.i]
        if partes:
            self._emitir(NoAST('NAO_SUPORTADO', ' '.join(t.lexema for t in partes), partes[0]))

    def _classe_java(self, qualificadores=()):
        inicio = self.atual()
        self.i += 1
        nome = self._exigir('IDENTIFIER', 'Esperado nome após declaração de classe.')
        inicio_cabecalho = self.i
        while self.atual() and self.atual().tipo not in ('LBRACE', 'SEMICOLON', 'RBRACE'):
            self.i += 1
        if not self.atual() or self.atual().tipo != 'LBRACE':
            raise ErroSintaxe(self.atual() or nome, "Esperado '{' após o cabeçalho da classe.")
        self.ambiente.declarar(nome, nome.lexema, 'Classe')
        no = self._emitir(NoAST('CLASSE' if inicio.tipo == 'CLASS' else 'INTERFACE', nome.lexema,
                               inicio, [NoAST('ID', nome.lexema, nome)]))
        if qualificadores:
            no.filhos.insert(0, NoAST('MODIFICADORES', ' '.join(qualificadores), inicio))
        cabecalho = self.tokens[inicio_cabecalho:self.i]
        if cabecalho:
            no.filhos.append(NoAST('HERANCA', ' '.join(t.lexema for t in cabecalho), cabecalho[0]))
        with self._contexto_ast(no):
            self._bloco(rotulo='classe')

    def _caso(self):
        tok = self.atual()
        self.i += 1
        filhos = []
        if tok.tipo == 'CASE':
            filhos.append(self._parse_expressao())
        self._exigir('COLON', "Esperado ':' após case/default.")
        return self._emitir(NoAST(tok.tipo, token=tok, filhos=filhos))

    def _do(self):
        tok = self.atual()
        self.i += 1
        no = self._emitir(NoAST('DO_WHILE', token=tok))
        self._corpo(no)
        self._exigir('WHILE', "Esperado 'while' após o corpo do do.")
        partes = self._pular_parenteses()
        expr = self._expressao_trecho(partes)
        if expr is None:
            raise ErroSintaxe(tok, 'Falta condição do do/while.')
        self._exigir('SEMICOLON', "Falta ';' após do/while.")
        no.filhos.append(NoAST('CONDICAO', '', partes[0], [expr]))

    def _salto(self):
        tok = self.atual()
        self.i += 1
        filhos = []
        if tok.tipo in ('RETURN', 'THROW'):
            if self.atual() and self.atual().tipo != 'SEMICOLON':
                filhos.append(self._parse_expressao())
            elif tok.tipo == 'THROW':
                raise ErroSintaxe(tok, 'Falta expressão após throw.')
        elif self.atual() and self.atual().tipo == 'IDENTIFIER':
            nome = self.atual()
            self.i += 1
            filhos.append(NoAST('ROTULO_REFERENCIA', nome.lexema, nome))
        elif tok.tipo == 'GOTO':
            raise ErroSintaxe(tok, 'Esperado rótulo após goto.')
        self._exigir('SEMICOLON', "Falta ';' após {}.".format(tok.lexema), retomar_instrucao=True)
        self._emitir(NoAST(tok.tipo, token=tok, filhos=filhos))

    def _instrucao_expressao(self):
        tok = self.atual()
        expressoes = [self._parse_expressao()]
        while self.atual() and self.atual().tipo == 'COMMA':
            self.i += 1
            expressoes.append(self._parse_expressao())
        self._exigir('SEMICOLON', "Falta ';' após expressão.", retomar_instrucao=True)
        self._emitir(NoAST('INSTRUCAO_EXPRESSAO', token=tok, filhos=expressoes))

    def _try(self):
        tok = self.atual()
        self.i += 1
        no = self._emitir(NoAST('TRY', token=tok))
        recursos = False
        if self.atual() and self.atual().tipo == 'LPAREN':
            partes = self._pular_parenteses()
            no.filhos.append(NoAST('RECURSOS', ' '.join(t.lexema for t in partes), tok))
            recursos = True
        if not self.atual() or self.atual().tipo != 'LBRACE':
            raise ErroSintaxe(self.atual() or tok, "Esperado bloco '{ ... }' após try.")
        self._corpo(no)
        tratados = 0
        while self.atual() and self.atual().tipo == 'CATCH':
            tratados += 1
            captura = self.atual()
            self.i += 1
            partes = self._pular_parenteses()
            if len(partes) < 2 or partes[-1].tipo != 'IDENTIFIER':
                raise ErroSintaxe(captura, 'Esperado tipo e nome do parâmetro de catch.')
            nome = partes[-1]
            final = partes[0].tipo == 'FINAL'
            tipo = ' '.join(t.lexema for t in partes[int(final):-1])
            if not tipo:
                raise ErroSintaxe(captura, 'Falta tipo do parâmetro de catch.')
            parametro = NoAST('PARAMETRO', nome.lexema, nome,
                              [NoAST('TIPO', tipo, partes[0]), NoAST('ID', nome.lexema, nome)])
            caso = NoAST('CATCH', '', captura, [parametro])
            no.filhos.append(caso)
            with self._contexto_ast(caso):
                self._bloco(parametros=[(nome, tipo, final)], rotulo='catch')
        if self.atual() and self.atual().tipo == 'FINALLY':
            tratados += 1
            fim = self.atual()
            self.i += 1
            caso = NoAST('FINALLY', token=fim)
            no.filhos.append(caso)
            if not self.atual() or self.atual().tipo != 'LBRACE':
                raise ErroSintaxe(self.atual() or fim, "Esperado bloco após finally.")
            with self._contexto_ast(caso):
                self._bloco()
        if not tratados and not recursos:
            raise ErroSintaxe(tok, 'Try requer catch ou finally.')

    def _diretiva_java(self):
        tok = self.atual()
        self.i += 1
        partes = []
        while self.atual() and self.atual().tipo not in ('SEMICOLON', 'LBRACE', 'RBRACE'):
            partes.append(self.atual())
            self.i += 1
        self._exigir('SEMICOLON', "Falta ';' após {}.".format(tok.lexema))
        self._emitir(NoAST(tok.tipo, ' '.join(t.lexema for t in partes), tok))

    def _anotacao(self):
        tok = self.atual()
        self.i += 1
        nome = self._exigir('IDENTIFIER', 'Esperado nome da anotação.')
        partes = [nome.lexema]
        while self.atual() and self.atual().tipo == 'DOT':
            self.i += 1
            partes.append(self._exigir('IDENTIFIER', "Esperado identificador após '.'.").lexema)
        filhos = []
        if self.atual() and self.atual().tipo == 'LPAREN':
            argumentos = self._expressao_trecho(self._pular_parenteses())
            if argumentos is not None:
                filhos.append(argumentos)
        self._emitir(NoAST('ANOTACAO', '.'.join(partes), tok, filhos))

    def _assert(self):
        tok = self.atual()
        self.i += 1
        filhos = [self._parse_expressao()]
        if self.atual() and self.atual().tipo == 'COLON':
            self.i += 1
            filhos.append(self._parse_expressao())
        self._exigir('SEMICOLON', "Falta ';' após assert.")
        self._emitir(NoAST('ASSERT', token=tok, filhos=filhos))

    def _include(self):
        marca = self._exigir('PUNCTUATOR', "Esperado '#' na diretiva.")
        nome = self._exigir('KEYWORD', "Esperado 'include' após '#'.")
        filhos = [NoAST('PUNCTUATOR', marca.lexema, marca), NoAST('KEYWORD', nome.lexema, nome)]
        partes = [marca.lexema + nome.lexema]
        if self.atual() and self.atual().tipo in ('HEADER_NAME', 'INVALID_HEADER_NAME', 'PP_ARGUMENT'):
            argumento = self.atual()
            self.i += 1
            filhos.append(NoAST(argumento.tipo, argumento.lexema, argumento))
            partes.append(argumento.lexema)
        else:
            self._erro(ErroSintaxe(nome, 'Falta nome de cabeçalho após #include.'))
        while self.atual() and self.atual().tipo == 'INVALID_PREPROCESSOR':
            invalido = self.atual()
            self.i += 1
            filhos.append(NoAST(invalido.tipo, invalido.lexema, invalido))
            partes.append(invalido.lexema)
        self._emitir(NoAST('PREPROCESSADOR', ' '.join(partes), marca, filhos))

    def _item(self, metodos=None):
        tok = self.atual()
        if tok is None:
            return
        origem = self.i
        try:
            if tok.tipo == 'LBRACE':
                self._bloco()
            elif tok.tipo == 'RBRACE':
                self._erro(ErroSintaxe(tok, "Chave '}' sem abertura correspondente."))
                self.i += 1
            elif tok.tipo == 'FOR':
                self._for()
            elif tok.tipo in ('IF', 'WHILE', 'SWITCH') or (
                    tok.tipo == 'SYNCHRONIZED' and self._olhar() and self._olhar().tipo == 'LPAREN'):
                self._controle()
            elif tok.tipo == 'DO':
                self._do()
            elif tok.tipo == 'TYPEDEF':
                self.i += 1
                self.declaracao(typedef=True)
            elif tok.tipo in ('CLASS', 'INTERFACE') and self.linguagem != 'c':
                self._classe_java()
            elif tok.tipo == 'TRY':
                self._try()
            elif tok.tipo in ('ELSE', 'CATCH', 'FINALLY'):
                raise ErroSintaxe(tok, "'{}' sem construção correspondente.".format(tok.lexema))
            elif tok.tipo in ('RETURN', 'BREAK', 'CONTINUE', 'GOTO', 'THROW'):
                self._salto()
            elif tok.tipo in ('IMPORT', 'PACKAGE') and self.linguagem != 'c':
                self._diretiva_java()
            elif tok.tipo == 'ASSERT' and self.linguagem != 'c':
                self._assert()
            elif tok.tipo == 'PUNCTUATOR' and tok.lexema in ('#', '%:'):
                self._include()
            elif tok.tipo == 'PREPROCESSADOR':
                self._emitir(NoAST('PREPROCESSADOR', tok.lexema, tok))
                self.i += 1
            elif tok.tipo == 'SEMICOLON':
                self._emitir(NoAST('VAZIO', token=tok))
                self.i += 1
            elif tok.tipo == 'IDENTIFIER' and self._olhar() and self._olhar().tipo == 'ASSIGN':
                self.atribuicao()
            elif tok.lexema in self.modificadores:
                # Modificadores podem anteceder uma classe Java ou uma declaração.
                j = self.i
                while j < len(self.tokens) and self.tokens[j].lexema in self.modificadores:
                    j += 1
                proximo = self.tokens[j] if j < len(self.tokens) else None
                if self._tipo_base(proximo) or any(
                        t.lexema in ('unsigned', 'signed') for t in self.tokens[self.i:j]):
                    self.declaracao(metodos=metodos)
                elif proximo and proximo.tipo in ('CLASS', 'INTERFACE') and self.linguagem != 'c':
                    modificadores = [t.lexema for t in self.tokens[self.i:j]]
                    self.i = j
                    self._classe_java(modificadores)
                else:
                    self.i = j
            elif self._tipo_comeco(tok):
                self.declaracao(metodos=metodos)
            elif tok.tipo == 'AT':
                self._anotacao()
            elif (tok.tipo == 'IDENTIFIER' and self._olhar() and self._olhar().tipo == 'IDENTIFIER'
                  and self.linguagem != 'java'):
                raise ErroSintaxe(tok, f"Tipo '{tok.lexema}' não reconhecido neste escopo.")
            elif (tok.tipo == 'IDENTIFIER' and self._olhar() and self._olhar().tipo == 'COLON'):
                self.i += 2
                no = self._emitir(NoAST('ROTULO', tok.lexema, tok))
                self._corpo(no)
            elif tok.tipo in ('CASE', 'DEFAULT'):
                self._caso()
            elif tok.tipo in ('IDENTIFIER', 'LPAREN', 'PLUS', 'MINUS', 'NOT', 'BITNOT',
                              'INCREMENT', 'DECREMENT', 'THIS', 'SUPER', 'NUMBER', 'STRING'):
                self._instrucao_expressao()
            else:
                self._ignorar_instrucao()
        except ErroSintaxe as erro:
            self._erro(erro, tok)
            self._recuperar(tok, erro)
        # Antitravamento para erros com sincronização em posições já inválidas.
        if self.i == origem:
            self.i += 1

    def executar(self):
        while self.atual():
            self._item()
        self.erros.extend(validar_contexto(self.arvore))
        return ([self.arvore] if self.arvore.filhos else []), self.erros, self.ambiente.erros
