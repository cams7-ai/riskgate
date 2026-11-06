# RiskGate

Laboratório fictício de gestão de risco para uma compra Spot de BTC cotada em
USDT, sem alavancagem. Python **3.11+**, somente biblioteca padrão em execução e
testes. Não acessa rede, credenciais ou exchanges e não envia ordens.
Percentuais e filtros são convenções didáticas.

## Executar

Na raiz deste repositório, sem instalação ou dependências adicionais:

```bash
python -m riskgate
python -m riskgate --cenario a
python -m riskgate --cenario b
python -m riskgate --cenario c
python -m riskgate --cenario d
python -m riskgate --cenario e
python -m riskgate --cenario f
python -m riskgate --cenario c --formato json
python -m riskgate --arquivo data/exemplos/avaliacao.json
python -m riskgate --arquivo data/exemplos/rejeitada.json
python -m riskgate --arquivo data/exemplos/invalida.json
python -m riskgate --help
python -m unittest discover -s tests -v
```

O terminal apresenta por padrão um relatório detalhado em texto, com entradas,
decisão, restrições, dimensionamento e interpretação por caso. Os números usam
vírgula decimal e unidades explícitas; horários mantêm seu fuso UTC.
Para salvar os relatórios em um diretório temporário, use o exemplo abaixo.
Sem seleção, executa A–F nessa ordem em sessões independentes.
Use `--formato json` para obter a saída estruturada com decimais como strings
e datas UTC, inclusive no modo `--arquivo`. O JSON continua disponível para
scripts; consumidores da antiga saída padrão devem acrescentar essa opção.
Uma terceira opção, `--formato html`, gera um documento independente, sem acesso
à rede ou dependências externas, com resumo de decisões, navegação por cenário,
indicadores, tabelas e interpretação por caso. Redirecione a saída para `.html`
e abra o arquivo no navegador. Para obter um PDF, use Imprimir → Salvar como PDF
no navegador; o relatório possui estilo específico para impressão. Essa opção
também funciona com `--arquivo` e preserva os mesmos códigos de saída.
O HTML inclui uma memória de cálculo por caso: fórmula simbólica, substituição
dos valores, resultado com unidade e legenda dos símbolos. Mostra o ajuste por
incremento, verificações de limites e filtros, métricas de E e comparação de
execução em F. Casos recusados antes do dimensionamento não recebem cálculos
financeiros inventados; candidatas rejeitadas são identificadas explicitamente.

### Salvar relatórios em diretório temporário

Execute o bloco na raiz do projeto, na mesma sessão Bash. `mktemp -d` cria um
diretório exclusivo no local temporário do sistema (`TMPDIR`, quando definido).
Cada cenário gera três arquivos; o relatório completo também é salvo nos três
formatos. Os caminhos entre aspas permitem diretórios com espaços.

```bash
relatorios_dir=$(mktemp -d)

for cenario in a b c d e f; do
  python -m riskgate --cenario "$cenario" --formato texto > "$relatorios_dir/cenario-$cenario.txt"
  python -m riskgate --cenario "$cenario" --formato json > "$relatorios_dir/cenario-$cenario.json"
  python -m riskgate --cenario "$cenario" --formato html > "$relatorios_dir/cenario-$cenario.html"
done

python -m riskgate --formato texto > "$relatorios_dir/completo.txt"
python -m riskgate --formato json > "$relatorios_dir/completo.json"
python -m riskgate --formato html > "$relatorios_dir/completo.html"

printf 'Relatórios salvos em: %s\n' "$relatorios_dir"
ls -lh "$relatorios_dir"
```

Leia os arquivos `.txt` no terminal e abra os `.html` no navegador; os `.json`
servem para processamento por scripts. Por exemplo, `cat "$relatorios_dir/cenario-c.txt"`
exibe o relatório C. No Linux com ambiente gráfico, `xdg-open "$relatorios_dir/completo.html"`
abre o relatório completo no navegador padrão.
Os arquivos são gravados pelo redirecionamento do shell; a aplicação não cria
diretórios automaticamente. Copie os relatórios que quiser manter para um local
permanente, pois o sistema pode limpar o diretório temporário. Executar novamente
`mktemp -d` cria outro diretório e redefine a variável, preservando o anterior.

### Entradas e códigos de saída

A opção `--cenario` aceita letras minúsculas a–f; é incompatível com `--arquivo`.
Nos cenários A–D e nas avaliações de E–F, o bloco `entradas` mostra patrimônio,
saldo livre, exposição atual, preços, taxas, limites, filtros, horários e bloqueios
efetivamente usados em cada caso, inclusive nas rejeições e erros esperados.
Em E, cada sessão informa seus limites diário e de drawdown antes das observações;
cada observação já exibe horário (`observed_at`) e patrimônio (`equity`). Em F,
as entradas incluem também os preços fictícios executados de compra e venda.

No modo arquivo: código **0** = APROVADA, **2** = REJEITADA por política,
**1** = arquivo/dados/configuração inválidos. Erros são escritos em stderr.
Nos cenários, erros e rejeições previstos são verificados e fazem parte do
sucesso (0); divergências inesperadas retornam 1. Erros de uso do argparse
retornam 2.

## Estrutura

- `riskgate/models.py`: dataclasses imutáveis e enums dos contratos.
- `riskgate/validation.py`: validação de tipos, datas, decimais e contexto local.
- `riskgate/finance.py`: dimensionamento e comparação de execuções fictícias.
- `riskgate/evaluator.py`: validação e regras de aprovação/rejeição, sem mutação.
- `riskgate/metrics.py`: sessão patrimonial em memória, com bloqueios persistentes.
- `riskgate/jsonio.py`: contrato JSON estrito e leitura de arquivo.
- `riskgate/presentation.py`: serialização com unidades.
- `riskgate/reports.py`: relatório em texto e formatação em português.
- `riskgate/html_report.py`: relatório HTML independente, com estilo de impressão.
- `riskgate/html_calculations.py`: fórmulas, substituições e legendas do relatório HTML.
- `riskgate/scenarios.py`: demonstrações determinísticas e verificações A–F.
- `riskgate/__main__.py`: interface de terminal.
- `data/exemplos/`: fixtures aprovada, rejeitada e inválida.
- `tests/`: cálculos exatos, invariantes, validação, métricas e interface.

## Fórmulas e unidades

Entradas: patrimônio `P`, saldo livre `B` e exposição atual `X` em USDT;
entrada `E` e saída planejada `S` em USDT/BTC; taxas `fc`, `fv`, risco `r`
e exposição máxima `x` como frações ("0.01" = 1%). Quantidades em BTC.

```text
R = P * r                                      [USDT]
L = E * (1 + fc) - S * (1 - fv)                 [USDT/BTC]
q_risco = R / L                                 [BTC]
exposição_máxima = P * x                        [USDT]
q_exposição = max(0, P * x - X) / E              [BTC]
q_saldo = B / (E * (1 + fc))                     [BTC]
q_bruta = min(q_risco, q_exposição, q_saldo)      [BTC]
q = floor(q_bruta / step) * step                [BTC]
nominal = q * E                                 [USDT]
taxa_entrada = q * E * fc                        [USDT]
desembolso = q * E * (1 + fc)                    [USDT]
recebimento_planejado = q * S * (1 - fv)          [USDT]
perda_estimada = desembolso - recebimento        [USDT]
exposição_resultante = X + q * E                [USDT]
```

Taxas são cobradas em USDT nas duas pontas. Exposição usa valor nominal,
sem taxas; o saldo precisa cobrir as taxas. A perda estimada inclui as duas
taxas e não pressupõe slippage no cenário-base. São informados os três
candidatos e todos os limitadores ativos, inclusive empates.

Usamos `Decimal` construído de strings, contexto **local** com precisão 28 e
`ROUND_HALF_EVEN`, preservando precisão, arredondamento, traps e flags externos.
O ajuste para baixo usa o número de incrementos, incluindo `step="0.000003"`.
Após recalcular a compra, eventuais excessos decimais sobre os limites causam
redução de um incremento e nova verificação. Uma quantidade mínima ou nominal
mínimo nunca justifica aumentar a compra. Igualdade com limites/mínimos é aceita.
A apresentação conserva os valores internos, sem converter para float.
Valores que excedem a capacidade aritmética do contexto são erros de validação.

## Contrato JSON v1

O exemplo completo e executável está em
[`data/exemplos/avaliacao.json`](data/exemplos/avaliacao.json).
Todos os campos abaixo são obrigatórios, mesmo quando coincidem com padrões da
API Python. Não são aceitos campos extras em nenhum objeto.

| Objeto | Campo | Tipo e regra |
| --- | --- | --- |
| raiz | `schema_version` | Inteiro 1; bool, 1.0 e "1" são inválidos |
| raiz | `config`, `snapshot` | Objetos com os campos abaixo |
| config | `buy_fee`, `sell_fee` | Strings decimais, frações em [0, 1) |
| config | `risk_fraction`, `exposure_fraction` | Strings decimais, frações em (0, 1] |
| config | `step`, `min_quantity` | Strings decimais positivas em BTC |
| config | `min_notional` | String decimal não negativa em USDT |
| config | `max_price_age_seconds` | String decimal positiva em segundos |
| snapshot | `equity` | String decimal positiva em USDT |
| snapshot | `free_balance`, `exposure` | Strings decimais não negativas em USDT |
| snapshot | `entry_price` | String decimal positiva em USDT/BTC ou null para preço ausente |
| snapshot | `planned_exit` | String decimal positiva em USDT/BTC; menor que entrada quando presente |
| snapshot | `price_at` | Data/hora ISO com fuso ou null para preço ausente |
| snapshot | `evaluated_at` | Data/hora ISO com fuso |
| snapshot | `position` | "VAZIA" ou "ABERTA" |
| snapshot | `pending_intent`, `unknown_order` | Booleanos JSON reais |
| snapshot | `daily_blocked`, `drawdown_blocked`, `manual_blocked` | Booleanos JSON reais |

Datas com offset são normalizadas para UTC; datas sem fuso ou preço futuro
são inválidos. Idade exatamente no limite é válida, acima do limite bloqueia.
`entry_price=null` ou `price_at=null` significa preço ausente, sem substituir por
zero. Mesmo um snapshot bloqueado passa primeiro pela validação estrutural.

JSON malformado, chaves duplicadas (inclusive aninhadas), versões diferentes,
constantes NaN/Infinity, strings decimais vazias/malformadas/não finitas,
tipos inadequados e booleanos usados como números são rejeitados.
`free_balance + exposure <= equity` é obrigatório. A diferença pode representar
recursos reservados. Não há correção automática de snapshots inconsistentes.

Na resposta, `quantidade_aprovada` é sempre BTC e é zero em toda rejeição.
`dimensionamento_candidato` é null se o cálculo não ocorreu. Quando houver
rejeição por mínimo, esse objeto contém a quantidade **candidata rejeitada**,
seus candidatos por limite e estimativas; não representa compra aprovada.
Seus campos incluem orçamento, perda por BTC, exposição máxima, nominal,
taxa, desembolso, recebimento planejado, perda e exposição resultante.
Cada valor possui `valor` (string decimal) e `unidade`. Motivos são códigos
estáveis definidos em `Reason`; explicações são texto de apresentação.

## Precedência de decisões

Após validar todos os dados:

1. `BLOQUEIO_MANUAL`.
2. `AGUARDANDO_RECONCILIACAO`.
3. `LIMITE_PATRIMONIAL`: diário ou drawdown.
4. `PRECO_AUSENTE` ou `PRECO_DESATUALIZADO`.
5. `INTENCAO_PENDENTE`.
6. `POSICAO_ABERTA`.
7. `EXPOSICAO_SEM_ESPACO`.
8. `SALDO_ZERO`.
9. `QUANTIDADE_ABAIXO_DOS_MINIMOS`.
10. `LIMITES_RESPEITADOS` (APROVADA).

Uma compra pode ser reduzida pelo saldo e continuar válida. Uma aprovação não
altera o snapshot, não reserva dinheiro, não cria ordem e não comprova execução.
Cada avaliação recebe um novo snapshot externo confiável. Em uma integração
real, validar e reservar precisariam ocorrer atomicamente para evitar duas
aprovações concorrentes sobre o mesmo saldo.

## Patrimônio e bloqueios

Patrimônio é dinheiro total mais posições marcadas ao preço corrente de
referência. Reservas já fazem parte do dinheiro total, sem somá-las novamente.
Exposição usa esse mesmo preço de referência da avaliação. O laboratório
recebe patrimônio, saldo e exposição prontos, sem implementar carteira completa.
Falta de preço impede novas entradas; não atribui valor zero à posição.
Não há depósitos ou retiradas nas séries fictícias.

`EquitySession(limite_diario_percentual, limite_drawdown_percentual)` recebe
limiares em **percentuais** (por exemplo `Decimal("3")` = 3%), em (0, 100].
`observe(instante, patrimonio)` recebe observações cronológicas e retorna
métricas imutáveis. A primeira observação da sessão precisa ser positiva para
formar um pico válido. Depois disso, zero é aceito e bloqueia entradas com
drawdown de 100%.

```text
perda_diária_% = max(0, (base_diária - patrimônio) / base_diária * 100)
pico = maior patrimônio desde o início da sessão, inclusive o atual
drawdown_% = (pico - patrimônio) / pico * 100
```

A primeira observação positiva do dia UTC estabelece a base diária. O dia
começa às 00:00 UTC; se a base for posterior, a medida vale desde a primeira
observação disponível (`daily_base_at`, `base_diaria_parcial` na apresentação).
Se um novo dia começar com patrimônio zero, não há base positiva: base e perda
diária ficam null, os bloqueios são acionados e o drawdown continua disponível.
A próxima observação positiva estabelece a base sem desfazer o bloqueio diário
já acionado nesse dia.

Atingir ou ultrapassar o limite diário bloqueia pelo restante do dia UTC;
recuperação não desbloqueia. A mudança do dia redefine somente base e bloqueio
diário. O limite de drawdown bloqueia pelo restante da sessão, inclusive após
recuperação, novo pico e virada de dia. Criar **explicitamente uma nova instância**
inicia outra sessão e descarta seu histórico em memória; isso é demonstrativo,
sem persistência ou mecanismo de desbloqueio operacional.

Duplicata (mesmo instante e valor) é ignorada. Conflito (mesmo instante com valor
diferente) e observação fora de ordem são erros, sem alterar métricas. A API
`evaluate(..., clock=callable)` permite injetar um relógio; por padrão utiliza
`evaluated_at` do snapshot. Todos os cenários usam instantes fixos.

Bloqueios de compra não encerram posições nem apagam intenções. A função
`position_actions` demonstra permissões de acompanhamento e solicitação fictícia
de saída de posição existente, sem aplicar orçamento de compra à saída.
Permissão não é ordem enviada ou execução garantida.

## Resultado demonstrado e limites

| Cenário | Quantidade aprovada (BTC) | Desembolso (USDT) | Perda estimada (USDT) | Limitador |
| --- | --- | --- | --- | --- |
| A | 0.002 | 200.2 | 4.396 | exposição |
| B | 0.004549 | 455.3549 | 9.998702 | risco |
| C | 0.000999 | 99.9999 | 2.195802 | saldo |

F simula compra de B a 100000 USDT/BTC e venda a 97000 USDT/BTC: recebimento
líquido de 440.811747 USDT e perda realizada fictícia de **14.543153 USDT**,
acima dos 10 USDT orçados. O efeito do slippage já está no preço executado;
não é descontado novamente. Stop é gatilho/convenção de saída e não garante
preço nem teto absoluto de perda. Stop-limit também pode não executar.

Sem estratégia, indicadores, backtest, carteira persistente, livro de ofertas,
servidor, motor de ordens ou stops reais. Uma posição e um ativo por sessão.
Veja o [glossário](docs/sprint05-glossario.md) e o
[registro de validação](docs/sprint05-validacao.md).
