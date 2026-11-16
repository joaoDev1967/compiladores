# Auditoria — 10 pendências do documento recebido (15/11/2026)

Registro da auditoria anterior. Consulte `RELATORIO_AV3.md` e `LOG_TESTES.txt` para o resultado da revisão atual.

Fonte: `Erros_a_Corrigir_AV3_Compiladores.docx`. A verificação foi feita sobre a versão revisada anterior, preservando o histórico dos 59 testes existentes.

| Nº | Gravidade | Entrada de regressão | Resultado observado na nova versão |
|---|---|---|---|
| 1 | Alta | `if (x=1) y=2;` e `while (x=x-1){x=2;}` | Nenhum erro sintático falso; AST de `y=2` e `x=2` preservada. |
| 2 | Alta | `for(int i=0;i<3;i++){} i=9;` | Erro semântico de `i` fora do laço; declaração posterior `int i;` aceita. |
| 3 | Alta | `int xs[]; xs=1;`, `int f(int *a){int x=a;}` | Tipos `int[]` e `int*` preservados; atribuições incompatíveis apontadas. |
| 4 | Média | `float x=1d; float y=2.0D; float z=1.5;` | Três diagnósticos por `double`→`float`; `1.5f` aceito. |
| 5 | Média | `long long`, `long int`, `int const`, `unsigned` | Declarações reconhecidas sem erro falso. |
| 6 | Média | `typedef int Inteiro; Inteiro x=1;` | `Inteiro` registrado como alias (categoria Tipo), `x` como variável int. |
| 7 | Média | `int x=x+1;` | Diagnóstico de autorreferência; declaração sintaticamente inválida não cria `x`. |
| 8 | Baixa | `int a; {float a;}` e `int x; int x(int a){}` | Histórico por escopo; colisão variável/função no mesmo escopo sinalizada. |
| 10 | Baixa | string aberta, char `'ab'`, agregado `{1,2}`, `int x=1+;` | Próximos comandos recuperados, sem `}` artificial; declaração parcial não registrada. |

## Suíte de validação

- **98 testes** executados (59 originais + 39 novos).
- **0 falhas e 0 erros** no Python 3.13.
- Todos os scripts Python submetidos a verificação de sintaxe com gramática 3.7 no teste automatizado. Isso **não** corresponde a executar o projeto em Python 3.7.

Comando reproduzível:

```bash
python -m unittest discover -s tests -v
```

Saída integral: `docs/LOG_TESTES.txt`.

## Decisões de escopo


O tratamento de `float` é didaticamente mais rigoroso que a atribuição de C padrão, seguindo a regra solicitada na lista de correções. Os exemplos do projeto usam `f` para literais `float`.
