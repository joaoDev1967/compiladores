"""Nós da AST, exportação estruturada e exibição em árvore."""
from dataclasses import dataclass, field


@dataclass
class NoAST:
    classe: str
    valor: str = ''
    token: object = None
    filhos: list = field(default_factory=list)

    def rotulo(self):
        nomes = {'PROGRAMA': 'Programa', 'FUNCAO': 'Funcao', 'PROTOTIPO': 'Prototipo',
                 'CLASSE': 'Classe', 'INTERFACE': 'Interface', 'BLOCO': 'Bloco',
                 'ATRIBUICAO': 'Atribuicao', 'DECLARACAO': 'Declaracao',
                 'TIPO': 'TIPO', 'ID': 'ID', 'ATRIB': 'OP_ATRIB',
                 'OP': 'Expressao', 'UNARIO': 'Expressao unaria',
                 'NUM': 'NUM', 'STRING': 'STRING', 'CHAR': 'CHAR',
                 'BOOL': 'BOOL', 'NULL': 'NULL', 'CHAMADA': 'Chamada'}
        cabecalho = nomes.get(self.classe, self.classe)
        valor = self.valor.replace('\r', '\\r').replace('\n', '\\n')
        return '{} ({})'.format(cabecalho, valor) if valor else cabecalho

    def para_dict(self):
        def entrada(no):
            return {'classe': no.classe, 'valor': no.valor,
                    'linha': no.token.linha if no.token else None,
                    'coluna': no.token.coluna if no.token else None,
                    'filhos': []}
        raiz = entrada(self)
        pendentes = [(self, raiz)]
        while pendentes:
            no, registro = pendentes.pop()
            for filho in no.filhos:
                item = entrada(filho)
                registro['filhos'].append(item)
                pendentes.append((filho, item))
        return raiz


def formatar_ast(raiz):
    linhas = [raiz.rotulo()]
    pendentes = []

    def agendar(no, prefixo):
        for i in range(len(no.filhos) - 1, -1, -1):
            pendentes.append((no.filhos[i], prefixo, i == len(no.filhos) - 1))

    agendar(raiz, '')
    while pendentes:
        no, prefixo, ultimo = pendentes.pop()
        linhas.append(prefixo + ('└── ' if ultimo else '├── ') + no.rotulo())
        agendar(no, prefixo + ('    ' if ultimo else '│   '))
    return '\n'.join(linhas)


class ErroSintaxe(Exception):
    def __init__(self, token, mensagem, retomar_instrucao=False):
        self.token = token
        self.mensagem = mensagem
        self.retomar_instrucao = retomar_instrucao
        super().__init__(mensagem)
