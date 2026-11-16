# Compiladores AV3


**Versão desta entrega: AST completa, escopo global e tokens de `#include`.** Extraia em
uma pasta nova para executar esta versão sem misturar arquivos de entregas anteriores.

## Executar

Extraia o ZIP e abra o terminal na pasta que contém `compilador.py`. Use Python 3.7 ou superior. O programa usa a biblioteca padrão.

```bash
python compilador.py exemplos/demonstracao_tokens.c
python compilador.py exemplos/correto.c --sem-tokens
python compilador.py exemplos/ast_completa.c --sem-tokens
python compilador.py exemplos/erro_escopo_global.c --sem-tokens
python compilador.py exemplos/escopo_global_correto.c --sem-tokens
python compilador.py exemplos/include.c --apenas-tokens --ascii
python compilador.py exemplos/erro_tipos.c --sem-tokens
python compilador.py exemplos/erro_nao_declarada.c --sem-tokens
python -m unittest discover -s tests -t . -v
```

No Linux, execute `./INICIAR_LINUX.sh` para abrir a demonstração. Para analisar outro fonte, passe o caminho como argumento, por exemplo `./INICIAR_LINUX.sh exemplos/correto.c`, ou rode `python3 compilador.py "caminho do arquivo.c"` no terminal. Use `./TESTAR_LINUX.sh` para rodar a suíte.

No Windows, execute `INICIAR_WINDOWS.bat` para abrir a demonstração. Para analisar outro fonte, arraste-o sobre esse arquivo ou rode `py -3 compilador.py "caminho do arquivo.c"` no terminal. Use `TESTAR_WINDOWS.bat` para rodar a suíte. A leitura aceita UTF-8, UTF-16 com BOM e Windows-1252.

| Opção | Saída |
|---|---|
| Padrão | Tokens no formato `• if → KEYWORD`, tabela de símbolos, AST e diagnósticos por etapa. |
| `--tokens-detalhados` | Lexema completo, tipo interno, ordem, linha e coluna de cada token. |
| `--apenas-tokens` | Lista de tokens na saída padrão. Diagnósticos léxicos no canal de erro. |
| `--sem-tokens` | Tabela de símbolos, AST e diagnósticos. |
| `--ascii` | Marcadores ASCII na lista de tokens e nos ramos da AST. |
| `--json resultado.json` | Relatório completo em JSON UTF-8. |

O código de saída é **0** para uma análise sem diagnósticos com ao menos uma AST, **1** para diagnósticos ou ausência de AST e **2** para problemas de leitura, extensão ou gravação. Com `--apenas-tokens`, o código **1** indica erro léxico. Os exemplos `erro_*.c` incluem erros intencionais.

As seções [4], [5] e [6] mostram os diagnósticos léxicos, sintáticos e semânticos, respectivamente. A seção [7] resume as contagens. Com `--apenas-tokens --json resultado.json`, o console mostra a análise léxica e o arquivo recebe o relatório completo.

## Tokens de `#include`

A diretiva `#include <stdio.h>` emite três tokens distintos, tanto no terminal
quanto no JSON:

| Lexema | Tipo |
|---|---|
| `#` | `PUNCTUATOR` |
| `include` | `KEYWORD` |
| `<stdio.h>` | `HEADER_NAME` |

Cabeçalhos entre aspas também são `HEADER_NAME`. `include` continua sendo um
identificador comum fora da diretiva. A AST reúne esses tokens em um nó
`PREPROCESSADOR`; eles não viram declarações da tabela de símbolos. Veja
`docs/CORRECAO_INCLUDE.md` para a verificação e os limites do pré-processamento.

## AST e escopo global

A seção [3] mostra uma árvore com raiz `Programa`. Funções têm tipo, parâmetros
e bloco. Declarações e instruções ficam dentro do bloco correspondente. A árvore
representa `if/else`, `while`, `for`, `do/while`, `switch/case/default`, chamadas,
retornos e outras construções reconhecidas.
O `for` possui nós separados para inicialização, condição, atualização e corpo.

O JSON contém `ast`, com a mesma árvore textual do terminal, e `ast_estruturada`,
com objetos que possuem `classe`, `valor`, `linha`, `coluna` e `filhos`.

Declarações globais são permitidas. Instruções executáveis devem estar dentro de
funções. No exemplo abaixo, há exatamente dois diagnósticos sintáticos, nas
linhas 2 e 3, e a execução do analisador retorna código 1:

```c
int c = 0;
c = 1;
c = 2;
```

`exemplos/escopo_global_correto.c` contém as mesmas atribuições dentro de `main`
e é aceito. Blocos soltos, protótipos e funções já encerradas não autorizam
instruções no escopo global.

## Leitura da tabela de símbolos

- **[2] Tabela de símbolos.** Contém apenas declarações reconhecidas (variáveis, parâmetros, funções e aliases de tipos), numeradas na ordem do fonte. As colunas mostram nome, categoria, tipo declarado, escopo, linha e coluna.
- Palavras reservadas como `int`, `if` e `return` aparecem como `KEYWORD` na lista de tokens e não são entradas da tabela de símbolos.
- Cada declaração tem sua própria linha com tipo e escopo. Em `demonstracao_tokens.c`, as duas declarações de `contador` aparecem com tipos `int` e `float`.
- Em `erro_nao_declarada.c`, `total` aparece como identificador na lista de tokens. Seu uso sem declaração é diagnosticado na análise semântica.
- Na análise semântica, a consulta começa pelo escopo ativo mais interno. O fechamento do bloco remove o vínculo ativo e conserva a declaração no histórico. A mesma regra vale para parâmetros, variáveis do `for` e aliases de `typedef`.
- A chave JSON `tabela_simbolos` reproduz a seção [2]. A chave `simbolos` contém as mesmas declarações, com o tipo interno do token. As frequências e posições das palavras reservadas ficam exclusivamente na chave separada `palavras_reservadas`.

## O que demonstrar

| Critério | Como conferir |
|---|---|
| Lista de tokens e assertividade léxica | Execute `demonstracao_tokens.c` e use `--tokens-detalhados` para conferir posições. |
| Tabela de símbolos | Veja os dois tipos e os dois escopos de `contador` em `demonstracao_tokens.c`. |
| Sintática e AST | Em `correto.c`, mostre a atribuição `x = a + 5;` e os nós da árvore. |
| Semântica | Execute `erro_tipos.c` para mostrar incompatibilidade de tipos, e `erro_nao_declarada.c` para mostrar o nome `total` sem declaração. |
| Defesa | Siga `docs/ROTEIRO_APRESENTACAO_5_MIN.md` e aponte as funções indicadas. |

`lexing/lexer.py` tokeniza a entrada. `sintatico/parser.py` monta a AST hierárquica;
`sintatico/expressoes.py` trata precedência e expressões;
`sintatico/contexto.py` valida onde as instruções podem aparecer;
`sintatico/ast.py` formata e exporta a árvore. `semantica/analisador.py` mantém os
vínculos e a validação de tipos. `compilador.py` lê e apresenta os resultados.
Consulte `docs/CORRECAO_AST_E_ESCOPO_GLOBAL.md` para os detalhes desta entrega.

A cobertura sintática e os limites semânticos estão em `docs/GRAMATICA_E_ESCOPOS.md`.
A AST abrange mais construções do que as verificações semânticas didáticas.
Genéricos e agregados completos não foram implementados.
Trechos atravessados sem interpretação aparecem como `NAO_SUPORTADO`; outras
formas não cobertas podem gerar diagnóstico. O PDF técnico original foi
preservado como histórico; os relatórios Markdown descrevem a versão atual.
