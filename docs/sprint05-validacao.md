# Sprint 05 — Registro de validação

Validação executada em **05/11/2026**, no diretório do projeto, com
**Python 3.12.14**. O projeto declara suporte a Python 3.11 ou superior;
nesta execução não foi usada uma segunda versão de Python.

## Roteiro e resultados observados

Os comandos abaixo foram efetivamente executados. Os cenários conferem seus
resultados antes de concluir; rejeições e erros previstos são parte da demonstração.

| Comando | Código observado | Resultado observado |
| --- | --- | --- |
| `python -m riskgate` | 0 | Cenários A, B, C, D, E, F verificados sem divergência |
| `python -m riskgate --cenario a` | 0 | Cenários A verificados sem divergência |
| `python -m riskgate --cenario b` | 0 | Cenários B verificados sem divergência |
| `python -m riskgate --cenario c` | 0 | Cenários C verificados sem divergência |
| `python -m riskgate --cenario d` | 0 | Cenários D verificados sem divergência |
| `python -m riskgate --cenario e` | 0 | Cenários E verificados sem divergência |
| `python -m riskgate --cenario f` | 0 | Cenários F verificados sem divergência |
| `python -m riskgate --help` | 0 | Ajuda com --cenario e --arquivo |
| `python -m riskgate --arquivo data/exemplos/avaliacao.json` | 0 | APROVADA |
| `python -m riskgate --arquivo data/exemplos/rejeitada.json` | 2 | REJEITADA |
| `python -m riskgate --arquivo data/exemplos/invalida.json` | 1 | Erro de validação: equity: esperado Decimal finito |
| `python -m unittest discover -s tests -v` | 0 | 27 testes passaram (OK) |
| `git diff --check` | 0 | Nenhum erro de whitespace reportado |
| `python --version` | 0 | Python 3.12.14 |

A suíte também repete todos os cenários juntos e isolados, compara as saídas,
executa ajuda e verifica os códigos de arquivo aprovado, rejeitado, inválido e
inexistente. O teste de correção decimal usa divisão recorrente 2/14, cujo
produto arredondado excede o saldo e exige reduzir um incremento.

## Valores esperados e conferidos

Comparações financeiras são feitas com Decimal, sem tolerância baseada em float.

| Caso | Esperado | Observado |
| --- | --- | --- |
| A: orçamento | 10 USDT | 10 USDT |
| A: perda por BTC | 2198 USDT/BTC | 2198 USDT/BTC |
| A: quantidade | 0.002 BTC | 0.002 BTC; limitador exposição |
| A: nominal / taxa | 200 / 0.2 USDT | 200 / 0.2 USDT |
| A: desembolso / recebimento | 200.2 / 195.804 USDT | 200.2 / 195.804 USDT |
| A: perda / exposição final | 4.396 / 200 USDT | 4.396 / 200 USDT |
| B: quantidade | 0.004549 BTC | 0.004549 BTC; limitador risco |
| B: desembolso / perda | 455.3549 / 9.998702 USDT | 455.3549 / 9.998702 USDT |
| B: exposição | 454.9 USDT | 454.9 USDT |
| C: quantidade | 0.000999 BTC | 0.000999 BTC; limitador saldo |
| C: desembolso / perda | 99.9999 / 2.195802 USDT | 99.9999 / 2.195802 USDT |
| E: 1000 → 1050 → 990 USDT | Perda diária 1%; drawdown 60/1050 × 100% | 1%; 5.714285714285714285714285714%; bloqueio drawdown |
| E: recuperação para 1020 USDT | Bloqueio drawdown persiste | Persistiu |
| E: 1000 → 970 USDT, limite diário 3% | Bloqueio na igualdade | Bloqueou e persistiu após recuperação no mesmo dia |
| E: virada UTC | Reinicia somente a base/bloqueio diário | Confirmado; drawdown persiste |
| E: patrimônio zero | Drawdown 100%; entradas bloqueadas | Confirmado |
| F: custo da compra | 455.3549 USDT | 455.3549 USDT |
| F: recebimento líquido | 440.811747 USDT | 440.811747 USDT |
| F: perda realizada fictícia | 14.543153 USDT | 14.543153 USDT; excede orçamento de 10 USDT |

A/B/C conferem os candidatos anteriores ao ajuste. B verifica que o próximo
incremento excederia o risco; C inclui saldo zero, candidato abaixo do mínimo e
step de 0.000003 BTC. Os testes cobrem empate dos três limitadores, igualdade
com mínimos e limites, e uma matriz de saldos, riscos e incrementos próximos
de fronteiras decimais, verificando simultaneamente risco, saldo e exposição.

D e os testes conferem precedência completa, ausência de preço, idade exatamente
no limite e acima dele, horário futuro, E <= S, alíquotas inválidas, valores não
finitos, tipos inadequados e snapshot inconsistente. Rejeições mantêm quantidade
aprovada zero; cálculos não executados ficam null. Snapshots não são alterados.

As métricas são verificadas quanto a base diária, horário UTC, pico,
recuperação, bloqueios persistentes, patrimônio zero, duplicatas, conflitos e
eventos fora de ordem. Erros não alteram o estado. Acompanhamento e solicitação
fictícia de saída permanecem permitidos em posição aberta sob bloqueio de entrada.

O contexto decimal externo é preservado (precisão, arredondamento, traps e
flags), inclusive com precisão externa reduzida e trap de Inexact ativo.
As séries e os cálculos têm resultados estáveis nesse contexto.

O contrato JSON foi exercitado com campos ausentes/inesperados, chaves duplicadas,
versões inválidas (inclusive bool e 1.0), constantes NaN/Infinity, strings não
finitas/malformadas, números sem string, booleanos incorretos, datas sem fuso,
posição desconhecida e arquivo ausente.

## Limitações e pendências

Não há pendências conhecidas no escopo implementado. As demonstrações usam
apenas dados fictícios locais e não comprovam execução em exchange. Não há
carteira persistente, estratégia, backtest, reservas atômicas ou ordens reais.
A aprovação depende de snapshot externo confiável e não reserva saldo.

A primeira observação da sessão deve ser positiva para definir o pico; uma
sessão já iniciada aceita patrimônio zero e bloqueia entradas. Um dia novo que
começa em zero mantém base/perda diária indisponíveis até observação positiva,
sem divisão por zero e sem remover o bloqueio. Criar uma nova sessão é uma ação
explícita em memória, sem proteção contra reinício operacional.

F demonstra que stop não garante preço nem teto de perda: a execução fictícia
pior que a planejada ultrapassa o orçamento. Slippage não é descontado duas vezes.

Nenhum commit, publicação ou ação externa foi realizado.
