# Gramática, AST e escopos

Esta versão representa a hierarquia das construções reconhecidas e valida o
contexto das instruções. A extensão seleciona as palavras reservadas e os
formatos de literal. A cobertura de C/Java continua didática.

## Declarações e instruções

```text
programa      ::= { declaracao_externa }
declaracao_externa ::= declaracao | typedef | funcao | classe | diretiva
bloco         ::= "{" { item } "}"
item          ::= declaracao | typedef | bloco | if | while | for | do_while
                | switch | try | retorno | salto | instrucao_expressao | ";"
declaracao    ::= tipo declarador [ "=" expressao ]
                  { "," declarador [ "=" expressao ] } ";"
funcao        ::= tipo ID "(" [ parametros ] ")" [ throws ] ( bloco | ";" )
if            ::= "if" "(" expressao ")" item [ "else" item ]
while         ::= "while" "(" expressao ")" item
for           ::= "for" "(" [ inicializacao ] ";" [ expressao ] ";"
                  [ expressoes ] ")" item
for_java      ::= "for" "(" tipo declarador ":" expressao ")" item
do_while      ::= "do" item "while" "(" expressao ")" ";"
retorno       ::= "return" [ expressao ] ";"
```

A AST também representa classes/interfaces Java, modificadores, parâmetros,
herança, `throws`, `switch/case/default`, `try/catch/finally`, `throw`, chamadas,
`break`, `continue`, `goto`, rótulos, `synchronized`, `assert`, anotações,
`package`, `import`, diretivas C e instruções vazias reconhecidas.

No léxico, `#include <stdio.h>` é separado em `PUNCTUATOR`, `KEYWORD` e
`HEADER_NAME`, preservando os três lexemas e suas posições. O parser os agrupa
em um nó `PREPROCESSADOR` com três filhos. `include` só recebe `KEYWORD` nesse
contexto; fora dele continua sendo um identificador. Outras diretivas e
argumentos de macro permanecem opacos, sem expansão de macros.

As expressões preservam precedência e associatividade: atribuições simples e
compostas, ternário, lógica, operadores bit a bit, comparação, deslocamento,
adição/subtração e multiplicação/divisão/módulo. Incluem unários, incremento e
decremento, chamadas, acesso a membros e indexação. Atribuições associam à direita.

Os declaradores mantêm os tipos conhecidos da base: primitivos, composições C,
`String` no Java e aliases visíveis. Asteriscos pertencem aos declaradores C.
Arrays mantêm dimensões e tamanhos reconhecidos em nós `DIMENSAO`.

## Hierarquia da AST

A raiz é `PROGRAMA`. Uma `FUNCAO` contém tipo, identificador, `PARAMETROS` e
`BLOCO`; protótipos não têm corpo. Os comandos pertencem ao bloco onde aparecem.
O `IF` tem `CONDICAO`, `ENTAO` e, se existir, `ELSE`. Um `else if` contém outro
`IF`, e o `else` se associa ao `if` aberto mais próximo.

O `FOR` tem filhos separados para `INICIALIZACAO`, `CONDICAO`, `ATUALIZACAO` e
`CORPO`. Cláusulas omitidas mantêm seus nós vazios. O `FOR_EACH` Java tem declaração,
`ITERAVEL` e corpo. Os casos de `SWITCH` agrupam suas instruções. Métodos Java
adiados preenchem o mesmo nó de função, mantendo a ordem original.

O terminal e o campo JSON `ast` mostram a árvore completa. O campo
`ast_estruturada` contém `classe`, `valor`, `linha`, `coluna` e `filhos`.

## Validação de contexto

Declarações globais são permitidas. Instruções executáveis exigem o corpo de uma
função ou método. Uma atribuição, chamada, incremento, retorno, condicional ou
laço externo recebe um diagnóstico sintático na sua posição inicial.

Um bloco solto não equivale a uma função. Protótipos e funções já encerradas
não autorizam comandos seguintes no escopo global. Uma classe também não herda
a permissão de execução de uma função externa; seus métodos têm seus próprios
corpos. Blocos de inicialização de classes Java não pertencem ao subconjunto
implementado nesta versão.

Cada instrução externa completa recebe um erro, inclusive quando várias estão
na mesma linha. Um comando composto inválido recebe o erro no início, sem
repeti-lo em todos os filhos. A análise continua e a AST preserva a sintaxe
reconhecida para inspeção junto dos diagnósticos.

No exemplo `int c=0; c=1; c=2;`, a declaração de `c` permanece global e as duas
atribuições recebem erros separados. Dentro de `main`, as mesmas atribuições
são aceitas. A API pública valida o contexto mesmo sem informar a linguagem.

## Tabela e semântica

A tabela mantém o modelo da base anterior às alterações de contadores. Há
histórico de declarações e vínculos ativos por escopo. Palavras reservadas não
são entradas de símbolos; permanecem na análise léxica. Não foram incluídas as
mudanças de contagem e unificação do pedido anterior.

A busca de variáveis começa no escopo mais interno. A saída de um bloco encerra
seus vínculos ativos e conserva o histórico. O mesmo vale para parâmetros,
variáveis de `for` e aliases. Campos Java podem ser usados por métodos escritos
antes deles. Campos e métodos homônimos têm espaços de nomes distintos.

A validação mantém regras didáticas para declarações, atribuições, tipos,
assinaturas, autorreferência e `final` em atribuições simples. A AST cobre mais
construções que a validação semântica completa. Condições, efeitos de incrementos
e atribuições compostas, argumentos de chamadas e fluxo de retornos não recebem
todas as verificações de um compilador real. Casts, genéricos, `new`, lambdas e
agregados completos não foram implementados. Trechos atravessados sem
interpretação aparecem como `NAO_SUPORTADO`; outras formas podem gerar erro
sintático. Não há geração de código executável.
