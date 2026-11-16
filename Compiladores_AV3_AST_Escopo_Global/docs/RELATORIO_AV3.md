# Relatório de verificação — Compiladores AV3

Revisão do analisador entregue para o barema de Compiladores, semestre 2026.2. A aplicação lê arquivos C e Java, exibe a análise léxica, gera AST de comandos simples e valida declarações e tipos.

## Matriz de atendimento ao barema

| Item | Implementação | Evidência de execução |
|---|---|---|
| Lista de tokens (3,0) | `lexing/lexer.py` e `compilador.py` | Ordem, tipo e lexema no terminal. `--tokens-detalhados` acrescenta linha e coluna. |
| Tabela de símbolos (3,0) | `TabelaSimbolos` em `semantica/analisador.py` | A seção [2] contém apenas declarações com tipo e escopo, na ordem do fonte. O JSON a disponibiliza em `tabela_simbolos`. Palavras reservadas permanecem na análise léxica. |
| Assertividade léxica (1,0) | Regras próprias para C e Java | Testes de palavras reservadas, operadores, números malformados, literais e localizações. |
| Sintática e AST (2,0) | `AnalisadorSintatico`, `sintatico/ast.py`, `expressoes.py` e `contexto.py` | `ast_completa.c` mostra funções, parâmetros, if/else, laços, chamadas e retornos na árvore do programa. `erro_escopo_global.c` rejeita separadamente as duas atribuições fora de função. |
| Semântica (1,0) | `AmbienteSemantico` e consulta aos escopos ativos da tabela | `erro_tipos.c` apresenta String para int. `erro_nao_declarada.c` apresenta uso de `total` sem declaração. |
| Defesa (1,0) | Roteiro de 5 minutos | `ROTEIRO_APRESENTACAO_5_MIN.md` identifica os comandos e os trechos do código a explicar. |

## Problemas reproduzidos e correções

- **Léxico.** Comentários `//` em C respeitam continuação de linha. Digrafos como `<%` e `%>` produzem os tokens correspondentes. Escapes inválidos em blocos de texto Java geram diagnóstico léxico.
- **Tabela e escopos.** A montagem da tabela deixa de inserir palavras reservadas: terminal e JSON passam a listar apenas declarações, com numeração contínua. O inventário de reservadas permanece separado. Em C, assinaturas com `long` e `long int` são compatíveis. Parâmetros array são ajustados para a comparação com ponteiros. Em Java, o corpo de um método pode acessar campos declarados depois. Campos e métodos podem compartilhar o nome.
- **Semântica.** Em C, a análise rejeita atribuição direta a arrays e módulo entre reais e aceita literais de texto em ponteiros para `char`. Em Java, rejeita reatribuições a `final` nas instruções simples cobertas pela gramática.
- **Recuperação.** Quando falta o ponto e vírgula entre comandos reconhecíveis na mesma linha, a análise sinaliza o erro e retoma no comando seguinte.
- **Saída do console.** A lista exibe as classes dos tokens e a seção de AST exibe as árvores. Os diagnósticos aparecem em seções próprias para cada etapa.
- **AST completa.** A saída principal passa a ter uma raiz `PROGRAMA`, com a hierarquia de funções, blocos, condicionais, laços e instruções reconhecidas. O JSON exporta também `ast_estruturada`.
- **Escopo global.** Declarações permanecem permitidas. Atribuições, chamadas, incrementos e controles executáveis fora de funções geram diagnósticos sintáticos. No teste `int c=0; c=1; c=2;`, são emitidos dois erros, um por atribuição.

## Validação desta atualização

- 194 testes aprovados em Python 3.12.14/Linux, incluindo 22 regressões de AST/contexto global e 17 de `#include`. O lexer, o terminal e o JSON usam `PUNCTUATOR`, `KEYWORD` e `HEADER_NAME` para os três lexemas. Veja `LOG_TESTES.txt` e `CORRECAO_INCLUDE.md`.
- O pacote original registrava 149 testes aprovados em Python 3.12 e 3.13 e 37 casos independentes com GCC C11 e OpenJDK 21. Esses resultados são históricos; a validação atual está descrita no log e em `CORRECAO_PALAVRAS_RESERVADAS.md`.
- `LOG_TESTES.txt` registra a execução da suíte. A sintaxe dos arquivos também passou pela verificação estática com a gramática do Python 3.7.
- A execução dos scripts `.bat` na máquina Windows da apresentação é uma verificação prática pendente. Use `INICIAR_WINDOWS.bat` com um arquivo de cada extensão.
- A soma dos valores por item do barema é 11,0 e a linha TOTAL informa 10,0. A matriz usa os valores publicados para localizar cada critério.

Consulte `GRAMATICA_E_ESCOPOS.md` e `CORRECAO_AST_E_ESCOPO_GLOBAL.md` para a gramática, a validação e os limites. O PDF técnico original está preservado como histórico.
