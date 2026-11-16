# Correção: palavras reservadas na tabela de símbolos

O lexer já diferenciava palavras reservadas de identificadores. O problema estava
em `TabelaSimbolos.listar_tabela()`: esse método misturava as declarações com a
primeira ocorrência de cada palavra reservada. Tanto o terminal quanto o JSON
usavam essa lista, por isso ambos apresentavam a tabela incorreta.

O método agora retorna apenas o histórico de declarações, usando `listar()`.
Isso mantém a ordem no fonte, a numeração contínua, os tipos e os escopos. Nomes
repetidos em escopos diferentes continuam em linhas distintas. A mensagem para
uma tabela vazia também foi ajustada.

Por exemplo, para `int main(void) { int contador=1; return contador; }`, a tabela
passa a conter apenas `main` (função) e `contador` (variável). `int`, `void` e
`return` continuam na lista de tokens como `KEYWORD`. As frequências e posições
dessas palavras permanecem no campo JSON separado `palavras_reservadas`.

## Verificação da primeira revisão

Este documento descreve a correção inicial. A entrega atual de AST e escopo
global está em `CORRECAO_AST_E_ESCOPO_GLOBAL.md`, com seu log em `LOG_TESTES.txt`.

Os testes adicionados reproduziram a falha antes da correção. Foram ajustados os
três testes existentes que exigiam palavras reservadas na tabela. A suíte completa
naquela revisão tinha 155 testes e foi executada com Python 3.12.14 em Linux.

A cobertura inclui todas as palavras reservadas reconhecidas pelo lexer em C,
com palavras reservadas; palavras reservadas usadas como nomes inválidos;
frequências léxicas; tabela vazia; ordem e escopos; e saída no terminal e em JSON.

Para repetir a verificação na pasta que contém `compilador.py`:

```bash
python -m unittest discover -s tests -t . -v
python compilador.py exemplos/demonstracao_tokens.c
```

O projeto continua com a gramática didática documentada em
`GRAMATICA_E_ESCOPOS.md`. Esta correção trata da tabela de símbolos; não adiciona
geração de código executável. O PDF técnico original foi preservado; as regras
atualizadas da tabela estão neste documento e nos relatórios Markdown.
