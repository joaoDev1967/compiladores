# Classificação dos tokens de #include

O lexer agrupava toda a diretiva em um token `PREPROCESSADOR`. Agora, para
`#include <stdio.h>`, produz exatamente:

| Lexema | Tipo interno e categoria exibida |
|---|---|
| `#` | `PUNCTUATOR` |
| `include` | `KEYWORD` |
| `<stdio.h>` | `HEADER_NAME` |

A separação ocorre no lexer e aparece igualmente na API, no terminal e no JSON.
Linha, coluna e ordem de cada token são preservadas. O parser reúne os três
componentes em um nó `PREPROCESSADOR` na AST, sem criar símbolos ou diagnosticar
instruções globais nessa diretiva.

A palavra `include` só é especial nesse contexto. Uma variável C com esse nome
continua sendo um `IDENTIFIER`. Também são reconhecidos cabeçalhos entre aspas,
espaços e comentários, continuação de linha e o digrafo `%:` para `#`.
Cabeçalhos vazios, não fechados ou com conteúdo extra geram diagnóstico e a
análise continua na linha seguinte.

Outras diretivas mantêm a forma opaca anterior. Um argumento de macro em
`#include CABECALHO` é preservado como `PP_ARGUMENT`; o projeto não expande
macros nem valida a existência dos arquivos de cabeçalho.

Os 17 testes em `tests/test_include.py` reproduziram a falha antes da correção
e passaram depois. A suíte completa tem **194 testes aprovados** com Python
3.12.14 em Linux. `LOG_TESTES.txt` registra a execução. As verificações incluem
as saídas do terminal e do JSON, a AST e a recuperação após cabeçalho inválido.

```bash
python compilador.py exemplos/include.c --apenas-tokens --ascii
python -m unittest discover -s tests -t . -v
```

Saída do primeiro comando:

```text
- # -> PUNCTUATOR
- include -> KEYWORD
- <stdio.h> -> HEADER_NAME
```
