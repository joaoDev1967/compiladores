# Roteiro de defesa — 5 minutos

**Antes da aula.** Extraia o ZIP, execute `python --version` e rode o exemplo no computador da apresentação. Abra `compilador.py`, `lexing/lexer.py`, `sintatico/parser.py` e `semantica/analisador.py` no editor.

| Tempo | Demonstração | Código a explicar |
|---|---|---|
| 0:00–0:35 | Execute `python compilador.py exemplos/demonstracao_tokens.c`. | Em `compilador.py`, mostre `main()` lendo o fonte e selecionando a linguagem pela extensão. |
| 0:35–1:50 | Mostre `• if → KEYWORD` e `• contador → ID`. Em [2], mostre `main` e as duas declarações de `contador` com seus tipos e escopos. Explique que `int` e `if` são tokens reservados e não entram na tabela de símbolos. | Mostre `tokenizar()` e como `TabelaSimbolos.listar_tabela()` usa apenas as declarações reconhecidas pelo parser. |
| 1:50–3:05 | Execute `python compilador.py exemplos/ast_completa.c --sem-tokens`. Mostre Programa, funções, parâmetros, if/else e os quatro filhos do for. | Aponte `_funcao()`, `_controle()` e `_for()` em `parser.py`; mostre a precedência em `expressoes.py`. |
| 3:05–4:20 | Execute `python compilador.py exemplos/erro_tipos.c --sem-tokens` e `python compilador.py exemplos/erro_nao_declarada.c --sem-tokens`. Mostre em [6] os diagnósticos de `resultado` e `total`. | Aponte `consultar()` e `validar_atribuicao()` em `AmbienteSemantico`. Explique a busca a partir do escopo mais interno. |
| 4:20–5:00 | Compare `exemplos/erro_escopo_global.c` com `exemplos/escopo_global_correto.c`. Mostre os dois erros nas atribuições externas e a aceitação dentro de main. | Aponte `validar_contexto()` em `sintatico/contexto.py`. Distinga a AST reconhecida das verificações semânticas didáticas. |

Os exemplos `erro_*.c` retornam 1 intencionalmente. Em um terminal Windows, `py -3` também pode ser usado no lugar de `python`.
