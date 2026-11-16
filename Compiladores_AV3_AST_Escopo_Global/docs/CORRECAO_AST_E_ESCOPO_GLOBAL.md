# AST completa e validação do escopo global

Esta revisão foi seguida pela correção de `#include`, descrita em
`CORRECAO_INCLUDE.md`. O log da suíte atual está em `LOG_TESTES.txt`.

Esta entrega parte da base anterior às mudanças de contagem e unificação da
tabela de símbolos. Aplica os dois itens do pedido atual.

## 1. AST completa

A AST tem raiz `PROGRAMA`. Funções possuem tipo, parâmetros e bloco; comandos
pertencem aos respectivos corpos. A saída principal inclui declarações,
funções/protótipos, classes, `if/else`, `while`, `for`, `for` aprimorado Java,
`do/while`, `switch/case/default`, chamadas, retornos, saltos e tratamento de
exceções reconhecido. Operadores respeitam precedência e associatividade.

O `else` se associa ao `if` aberto mais próximo. Cada cláusula de `for` tem seu
próprio nó. Os métodos Java adiados para reconhecer campos posteriores preenchem
o corpo do mesmo nó da função, na ordem do fonte.

O terminal e a chave JSON `ast` mostram a árvore completa.
`ast_estruturada` exporta seus objetos com filhos recursivos. Não há uma saída
principal reduzida a declarações de variáveis.

## 2. Instruções fora de funções

`sintatico/contexto.py` percorre a hierarquia e distingue declarações de
instruções executáveis. Somente o corpo de uma função ou método autoriza estas
instruções. Classes interrompem o contexto de uma função externa; um bloco
solto não é confundido com função. Protótipos não abrem contexto de execução.

Para o código solicitado:

```c
int c = 0;
c = 1;
c = 2;
```

`c` é registrado como declaração global. As atribuições geram dois diagnósticos
sintáticos independentes, nas linhas 2 e 3, coluna 1. O analisador continua até o
fim e retorna código 1. As mesmas instruções dentro de `main` são aceitas.

Uma instrução composta global recebe um diagnóstico no seu início; o erro não
é repetido em todos os seus filhos. Declarações posteriores e funções seguintes
continuam sendo reconhecidas. A AST preserva os comandos reconhecidos para
inspeção, acompanhados dos diagnósticos de contexto.

## Verificação

Foram aprovados **177 testes** com Python 3.12.14 em Linux. Os 22 testes novos em
`tests/test_ast_escopo_global.py` usam a API pública e a CLI e cobrem a árvore,
o exemplo exato, instruções na mesma linha, comandos dentro de funções, blocos,
protótipos, classes e recuperação. O log está em `LOG_TESTES.txt`.

Os testes unitários históricos de expressões e tipos usam fragmentos isolados.
`tests/suporte.py` separa seus erros de contexto e extrai uma visão plana apenas
para aquelas verificações. Esse adaptador existe somente nos testes: a API
`compilador.analisar()` e a CLI sempre aplicam a validação global, inclusive
quando nenhuma linguagem é informada.

```bash
python compilador.py exemplos/ast_completa.c --sem-tokens
python compilador.py exemplos/Estruturas.java --json resultado.json
python compilador.py exemplos/erro_escopo_global.c --sem-tokens
python compilador.py exemplos/escopo_global_correto.c --sem-tokens
python -m unittest discover -s tests -t . -v
```

As saídas demonstrativas foram regeneradas. O projeto mantém a biblioteca padrão
e a gramática Python 3.7. A sintaxe e a validação semântica continuam didáticas;
representar uma construção na AST não implementa todas as regras de C/Java.
