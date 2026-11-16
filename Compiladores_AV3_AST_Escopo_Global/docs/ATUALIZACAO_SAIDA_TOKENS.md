# Atualização do formato de exibição da análise léxica

O arquivo `compilador.py` passou a apresentar os tokens como linhas simples, seguindo o modelo visual solicitado:

```text
• if → KEYWORD
• else → KEYWORD
• while → KEYWORD
• contador → ID
```

- `KEYWORD`: palavra reservada de C/Java ou `include` no contexto de uma diretiva C.
- `ID`: identificador.
- `NUMBER`, `STRING`, `CHAR`, `OPERATOR`, `DELIMITER`, `PREPROCESSOR`: outras categorias de exibição.
- Em `#include <stdio.h>`, a saída é `# → PUNCTUATOR`, `include → KEYWORD` e `<stdio.h> → HEADER_NAME`. Cabeçalhos entre aspas também usam `HEADER_NAME`.
- `--apenas-tokens` mostra os tokens na saída padrão e envia diagnósticos léxicos ao canal de erro. Com `--json`, o relatório completo é gerado no arquivo.
- `--tokens-detalhados`: restabelece a tabela técnica do terminal com tipos internos e posições.
- `--sem-tokens`: oculta a lista léxica, mantendo as demais etapas.
- `--ascii`: força substituição de bullet e seta por `-` e `->`; há fallback automático para codificações incompatíveis.

Consulte o relatório AV3 para a cobertura léxica e os resultados da revisão atual.
