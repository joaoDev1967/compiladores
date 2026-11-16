"""Tabela de símbolos, escopos reais e validação semântica simplificada."""
import re
from dataclasses import dataclass, replace
from lexing.tokens import Diagnostico, palavra_reservada


@dataclass
class Declaracao:
    categoria: str
    tipo: str
    escopo: str
    linha: int
    coluna: int
    ordem_token: int


@dataclass
class Simbolo:
    ordem: int
    lexema: str
    categoria: str
    token: str
    tipo_declarado: str
    escopo: str
    linha: int
    coluna: int


@dataclass
class PalavraReservada:
    ordem: int
    lexema: str
    token: str
    linha: int
    coluna: int
    ocorrencias: int = 0


@dataclass
class Vinculo:
    declaracao: Declaracao
    assinatura: tuple = ()
    definido: bool = False
    final: bool = False
    inicializado: bool = False


def _array_c(tipo):
    return tipo.endswith('[]') and '(*)' not in tipo


def _ajustar_parametro_c(tipo):
    if not _array_c(tipo):
        return tipo
    base, _, dimensoes = tipo.partition('[]')
    return base + ('(*)' + dimensoes if dimensoes else '*')


def _tipo_c_canonico(tipo):
    """Unifica grafias equivalentes para comparar tipos, preservando a exibição."""
    base = re.match(r'[^*\[(]+', tipo).group()
    palavras = base.split()
    if palavras[0] == 'signed' and palavras[1] != 'char':
        palavras.pop(0)
    if palavras[-2:] in (['short', 'int'], ['long', 'int']):
        palavras.pop()
    return ' '.join(palavras) + tipo[len(base):]


class TabelaSimbolos:
    """Declarações por escopo e inventário léxico separado de palavras reservadas."""
    def __init__(self, tokens):
        self._simbolos = {}
        self._reservadas = {}
        self._escopos = [('global', {})]
        self._proximo_escopo = 0
        for tok in tokens:
            if not palavra_reservada(tok):
                continue
            if tok.lexema not in self._reservadas:
                self._reservadas[tok.lexema] = PalavraReservada(
                    ordem=len(self._reservadas) + 1, lexema=tok.lexema,
                    token=tok.tipo, linha=tok.linha, coluna=tok.coluna)
            self._reservadas[tok.lexema].ocorrencias += 1

    def entrar_escopo(self, rotulo):
        self._proximo_escopo += 1
        pai, _ = self._escopos[-1]
        self._escopos.append((f'{pai}/{rotulo}{self._proximo_escopo}', {}))

    def sair_escopo(self):
        self._escopos.pop()

    def resolver(self, nome):
        vinculo = self.resolver_vinculo(nome)
        return vinculo.declaracao if vinculo else None

    def resolver_vinculo(self, nome):
        outra_categoria = None
        for _, escopo in reversed(self._escopos):
            vinculos = escopo.get((nome, None))
            if vinculos:
                return vinculos[0]
            if outra_categoria is None:
                outros = escopo.get((nome, 'Função')) or escopo.get((nome, 'Classe'))
                if outros:
                    outra_categoria = outros[0]
        return outra_categoria

    def resolver_funcoes(self, nome):
        for _, escopo in reversed(self._escopos):
            vinculos = escopo.get((nome, 'Função')) or escopo.get((nome, None))
            if vinculos:
                return [v for v in vinculos if v.declaracao.categoria == 'Função']
        return []


    def registrar(self, token, tipo, categoria, assinatura=(), definido=False,
                  *, final=False, inicializado=False):
        caminho, escopo = self._escopos[-1]
        vinculos = escopo.setdefault((token.lexema, None), [])
        if categoria == 'Função':
            assinatura = tuple(_tipo_c_canonico(_ajustar_parametro_c(p)) for p in assinatura)
        for anterior in vinculos:
            if categoria != 'Função' or anterior.declaracao.categoria != 'Função':
                return 'duplicado'
            if assinatura != anterior.assinatura:
                return 'assinatura'
            tipo_anterior = anterior.declaracao.tipo
            retorno_compativel = _tipo_c_canonico(tipo) == _tipo_c_canonico(tipo_anterior)
            if not retorno_compativel:
                return 'assinatura'
            if definido and anterior.definido:
                return 'duplicado'
            anterior.definido = anterior.definido or definido
            break
        else:
            # A primeira entrada com esta assinatura é a usada na consulta.
            anterior = None

        declaracao = Declaracao(categoria, tipo, caminho, token.linha, token.coluna, token.ordem)
        if anterior is None:
            vinculos.append(Vinculo(declaracao, assinatura, definido, final, inicializado))
        self._simbolos[token.ordem] = Simbolo(
            ordem=0, lexema=token.lexema,
            categoria=categoria, token=token.tipo, tipo_declarado=tipo,
            escopo=caminho, linha=token.linha, coluna=token.coluna)
        return None

    def listar(self):
        return [replace(self._simbolos[pos], ordem=i)
                for i, pos in enumerate(sorted(self._simbolos), start=1)]

    def listar_reservadas(self):
        return list(self._reservadas.values())

    def listar_tabela(self):
        """Lista apenas declarações, numeradas na ordem em que aparecem no fonte."""
        return self.listar()


class AmbienteSemantico:
    def __init__(self, tabela, linguagem=None):
        self.tabela = tabela
        self.linguagem = linguagem
        self.erros = []
        self.atribuicoes_finais = set()

    def declarar(self, token, tipo, categoria='Variável', assinatura=(), definido=False,
                 *, final=False, inicializado=False):
        problema = self.tabela.registrar(
            token, tipo, categoria, assinatura, definido,
            final=final, inicializado=inicializado)
        if problema:
            mensagem = (f"Assinatura de '{token.lexema}' incompatível com a declaração anterior."
                        if problema == 'assinatura' else
                        f"Há uma entidade já declarada como '{token.lexema}' neste escopo (declaração duplicada).")
            self.erros.append(Diagnostico('SEMÂNTICO', token.linha, token.coluna, mensagem))
        return problema is None

    def tipo_alias(self, nome):
        declaracao = self.tabela.resolver(nome)
        if declaracao and declaracao.categoria == 'Tipo':
            return declaracao.tipo
        return None

    def _consultar_variavel(self, token):
        vinculo = self.tabela.resolver_vinculo(token.lexema)
        if vinculo:
            if vinculo.declaracao.categoria in ('Variável', 'Parâmetro'):
                return vinculo
            mensagem = "'{}' não é uma variável.".format(token.lexema)
        else:
            mensagem = "Variável '{}' utilizada sem declaração prévia.".format(token.lexema)
        self.erros.append(Diagnostico('SEMÂNTICO', token.linha, token.coluna, mensagem))
        return None

    def _tipo_variavel(self, vinculo):
        declaracao = vinculo.declaracao
        if self.linguagem == 'c' and declaracao.categoria == 'Parâmetro':
            return _ajustar_parametro_c(declaracao.tipo)
        return declaracao.tipo

    def consultar(self, token):
        vinculo = self._consultar_variavel(token)
        return self._tipo_variavel(vinculo) if vinculo else None

    @staticmethod
    def tipo_numerico(texto):
        """Tipos didáticos (int/long/float/double), sem verificar overflow."""
        texto = texto.replace('_', '')
        if texto.lower().startswith(('0x', '0b')):
            if 'p' in texto.lower():
                return 'float' if texto[-1] in 'fF' else ('long double' if texto[-1] in 'lL' else 'double')
            return 'long' if re.search(r'[lL](?:[uU])?$', texto) else 'int'
        if texto[-1:] in ('f', 'F'):
            return 'float'
        if texto[-1:] in ('d', 'D'):
            return 'double'
        if '.' in texto or 'e' in texto.lower():
            return 'long double' if texto[-1] in 'lL' else 'double'
        if re.search(r'[lL](?:[uU])?$', texto):
            return 'long'
        return 'int'

    def inferir(self, arvore):
        if arvore.classe == 'NUM':
            return self.tipo_numerico(arvore.valor)
        if arvore.classe == 'STRING':
            return 'String'
        if arvore.classe == 'CHAR':
            return 'char'
        if arvore.classe == 'BOOL':
            return 'boolean'
        if arvore.classe == 'NULL':
            return 'null'
        if arvore.classe == 'ID':
            return self.consultar(arvore.token)
        if arvore.classe == 'CHAMADA':
            callee, argumentos = arvore.filhos
            tipos = tuple(self.inferir(a) for a in argumentos.filhos)
            if callee.classe != 'ID':
                return None
            funcoes = self.tabela.resolver_funcoes(callee.valor)
            exatas = [f for f in funcoes if f.assinatura == tipos]
            compativeis = exatas or [f for f in funcoes if len(f.assinatura) == len(tipos)]
            return compativeis[0].declaracao.tipo if len(compativeis) == 1 else None
        if arvore.classe == 'POSFIXO':
            return self.inferir(arvore.filhos[0])
        if arvore.classe == 'INDICE':
            tipo = self.inferir(arvore.filhos[0])
            self.inferir(arvore.filhos[1])
            if tipo and tipo.endswith('[]'):
                return tipo[:-2]
            return tipo[:-1] if tipo and tipo.endswith('*') else None
        if arvore.classe == 'TERNARIO':
            self.inferir(arvore.filhos[0])
            esquerda, direita = [self.inferir(n) for n in arvore.filhos[1:]]
            if esquerda == direita:
                return esquerda
            if esquerda is None or direita is None:
                return None
            if esquerda == 'null':
                return direita
            if direita == 'null':
                return esquerda
            tipos = [self._numerico(t) for t in (esquerda, direita)]
            return (max(tipos, key=('int', 'long', 'long long', 'float', 'double', 'long double').index)
                    if None not in tipos else None)
        if arvore.classe == 'ATRIBUICAO_EXPRESSAO':
            esquerda, direita = [self.inferir(n) for n in arvore.filhos]
            return direita if esquerda and direita else None
        if arvore.classe == 'UNARIO':
            tipo = self.inferir(arvore.filhos[0])
            if tipo is None:
                return None
            if arvore.valor == '&':
                return tipo + '*'
            if arvore.valor == '*' and tipo.endswith('*'):
                return tipo[:-1]
            if arvore.valor == '!':
                if tipo == 'boolean':
                    return 'boolean' if self.linguagem != 'c' else 'int'
                if (self._numerico(tipo) or tipo.endswith(('*', '[]'))):
                    return 'int'
            if arvore.valor in ('++', '--') and self._numerico(tipo):
                return tipo
            promovido = self._numerico(tipo)
            if arvore.valor in ('!', '*', '&') or (arvore.valor == '~' and promovido in ('float', 'double', 'long double')):
                promovido = None
            if promovido is None:
                self.erros.append(Diagnostico('SEMÂNTICO', arvore.token.linha, arvore.token.coluna,
                    "Operação unária '{}' inválida para {}.".format(arvore.valor, tipo)))
            return promovido
        if arvore.classe == 'OP':
            if arvore.valor == 'instanceof':
                self.inferir(arvore.filhos[0])
                return 'boolean'
            esquerda, direita = self.inferir(arvore.filhos[0]), self.inferir(arvore.filhos[1])
            if esquerda is None or direita is None:
                return None
            if arvore.valor in ('==', '!=', '<', '<=', '>', '>='):
                return 'int'
            if arvore.valor in ('&&', '||', '&', '|', '^') and esquerda == direita == 'boolean':
                return 'boolean'
            if arvore.valor == '+' and (
                    esquerda == direita == 'String' or
                    False):
                return 'String'
            promovidos = [self._numerico(tipo) for tipo in (esquerda, direita)]
            modulo_real_c = (self.linguagem == 'c' and arvore.valor == '%' and
                             any(t in ('float', 'double', 'long double') for t in promovidos))
            bits_reais = (arvore.valor in ('&', '|', '^', '<<', '>>', '>>>') and
                          any(t in ('float', 'double', 'long double') for t in promovidos))
            if None in promovidos or modulo_real_c or bits_reais :
                self.erros.append(Diagnostico('SEMÂNTICO', arvore.token.linha,
                    arvore.token.coluna, "Operação '{}' inválida entre {} e {}.".format(
                        arvore.valor, esquerda, direita)))
                return None
            if arvore.valor in ('&&', '||'):
                return 'int'
            return max(promovidos, key=('int', 'long', 'long long', 'float', 'double', 'long double').index)
        return None

    @staticmethod
    def _numerico(tipo):
        base = tipo
        if base.startswith(('signed ', 'unsigned ')):
            base = base.split(' ', 1)[1]
        if base in ('char', 'byte', 'short', 'short int', 'int', '_Bool'):
            return 'int'
        if base in ('long', 'long int'):
            return 'long'
        if base in ('long long', 'long long int'):
            return 'long long'
        if base in ('float', 'double', 'long double'):
            return base
        return None

    def _normalizar(self, tipo):
        if tipo == 'char':
            return tipo
        categoria = self._numerico(tipo)
        return 'int' if categoria in ('int', 'long', 'long long') else (categoria or tipo)

    def _tipos_compativeis(self, tipo_destino, tipo_origem, expressao, inicializador):
        if expressao.classe == 'STRING':
            literal_char = expressao.valor.startswith(('"', 'u8"'))
            if literal_char and (tipo_destino == 'char*' or (inicializador and tipo_destino == 'char[]')):
                return True
        if self.linguagem == 'c':
            if _array_c(tipo_destino):
                return False
            if '*' in tipo_destino:
                tipo_origem = _ajustar_parametro_c(tipo_origem)
                return _tipo_c_canonico(tipo_destino) == _tipo_c_canonico(tipo_origem)
        if tipo_origem == 'null' and tipo_destino.endswith('*'):
            return True
        dest, orig = self._normalizar(tipo_destino), self._normalizar(tipo_origem)
        compativeis = {
            'int': {'int'}, 'long': {'int', 'long'},
            'long long': {'int', 'long', 'long long'},
            'float': {'int', 'long', 'long long', 'float'},
            'double': {'int', 'long', 'long long', 'float', 'double'},
            'long double': {'int', 'long', 'long long', 'float', 'double', 'long double'},
            'char': {'char'},
        }
        return orig in compativeis.get(dest, {dest})

    def validar_atribuicao(self, alvo, expressao, tipo_destino=None):
        inicializador = tipo_destino is not None
        vinculo = None
        if not inicializador:
            vinculo = self._consultar_variavel(alvo)
            tipo_destino = self._tipo_variavel(vinculo) if vinculo else None
        tipo_origem = self.inferir(expressao)
        final = vinculo and vinculo.final
        if final:
            pos = vinculo.declaracao.ordem_token
            if vinculo.inicializado or pos in self.atribuicoes_finais:
                self.erros.append(Diagnostico('SEMÂNTICO', alvo.linha, alvo.coluna,
                    f"Não é possível reatribuir a variável final '{alvo.lexema}'."))
                return
        if not tipo_destino or not tipo_origem:
            return
        if not self._tipos_compativeis(tipo_destino, tipo_origem, expressao, inicializador):
            mensagem = "Incompatibilidade de tipos: não é possível atribuir {} a {} ('{}').".format(
                tipo_origem, tipo_destino, alvo.lexema)
            if self.linguagem == 'c' and _array_c(tipo_destino):
                mensagem += ' Arrays em C não recebem atribuição direta.'
            self.erros.append(Diagnostico('SEMÂNTICO', alvo.linha, alvo.coluna, mensagem))
        elif final:
            self.atribuicoes_finais.add(pos)

    @staticmethod
    def _literal_cabe(destino, expressao):
        sinal = 1
        while expressao.classe == 'UNARIO':
            if expressao.valor == '-':
                sinal = -sinal
            expressao = expressao.filhos[0]
        if expressao.classe != 'NUM':
            return False
        texto = expressao.valor.replace('_', '')
        try:
            base = 8 if texto.startswith('0') and texto.isdigit() else 0
            numero = sinal * int(texto, base)
        except ValueError:
            return False
        minimo, maximo = {'byte': (-128, 127), 'short': (-32768, 32767), 'char': (0, 65535)}[destino]
        return minimo <= numero <= maximo

    def validar_inicializador(self, nome, tipo, arvore):
        """Rejeita autorreferência em declaração, inclusive antes de registrar nome."""
        def procurar(no):
            return ((no.classe == 'ID' and no.valor == nome.lexema)
                    or any(procurar(filho) for filho in no.filhos))
        if procurar(arvore):
            self.erros.append(Diagnostico('SEMÂNTICO', nome.linha, nome.coluna,
                "Variável '{}' utilizada no próprio inicializador antes de estar inicializada.".format(
                    nome.lexema)))
            return
        self.validar_atribuicao(nome, arvore, tipo)
