# Sprint 05 — Gestão de risco

**Projeto fictício:** RiskGate  
**Diretório sugerido:** `riskgate`  
**Etapa de estudo:** 5 — Gestão de risco  
**Objetivo:** criar um laboratório que dimensione uma compra Spot, aplique limites de saldo e exposição e bloqueie novas entradas quando as condições definidas forem atingidas.

O RiskGate é independente dos projetos das etapas anteriores. Utiliza dados locais fictícios; percentuais, limites e regras de quantidade são convenções didáticas. Uma aprovação representa uma decisão do avaliador, não uma ordem enviada ou uma execução confirmada.

## 1. Conhecimentos trabalhados

| Conhecimento | Aplicação no exemplo |
| --- | --- |
| Orçamento de risco | Definir a perda estimada admitida no planejamento |
| Dimensionamento | Calcular quantidade por risco, exposição e saldo |
| Taxas e slippage | Distinguir estimativa de resultado efetivamente realizado |
| Incremento de quantidade | Ajustar para baixo sem ultrapassar os limites |
| Patrimônio e drawdown | Calcular perda diária e queda em relação ao pico |
| Bloqueio de entradas | Impedir novas compras preservando acompanhamento e saídas |
| Qualidade operacional | Rejeitar preço desatualizado e situação não reconciliada |
| Testes determinísticos | Conferir decisões, limites e invariantes |

## 2. Resultado esperado

Uma aplicação de terminal que retorne aprovação ou rejeição, quantidade, estimativas e motivos verificáveis. Deve demonstrar que uma saída pior que a planejada pode produzir perda superior ao orçamento de risco, sem apresentar o stop como garantia.

A visualização padrão é um relatório detalhado em texto. As opções `--formato json`
e `--formato html` oferecem, respectivamente, dados estruturados e um relatório
para navegador e impressão. O [README](../README.md#salvar-relatórios-em-diretório-temporário)
mostra como criar um diretório com `relatorios_dir=$(mktemp -d)` e salvar os três
formatos de cada cenário e da execução completa sem gravá-los na raiz do projeto.

## 3. Prompt autossuficiente de execução

Copie o bloco abaixo para o agente responsável pela implementação. O projeto não depende de documentos ou código das sprints anteriores.

````text
Você é um desenvolvedor Python experiente. Implemente a Sprint 05 do projeto fictício RiskGate: um laboratório de gestão de risco para uma compra Spot sem alavancagem.

OBJETIVO E DIRETÓRIO

O usuário conhece desenvolvimento de software e está aprendendo os fundamentos de um robô de criptomoedas. Implemente código, exemplos e documentação; não entregue apenas um plano.

Trabalhe em um diretório próprio chamado riskgate no diretório indicado pelo usuário ou, na ausência de indicação, dentro do diretório atual. Se existir, preserve trabalho alheio. Não altere outros projetos nem importe seus módulos.

TECNOLOGIA E ESCOPO

- Python 3.11 ou superior; somente biblioteca padrão, incluindo Decimal, datetime, dataclasses, Enum, json, argparse e unittest.
- Dados locais fictícios; sem rede, credenciais, Binance ou envio de ordens.
- Um ativo BTC, cotação USDT e uma posição comprada por sessão. Não abrir posição adicional quando já houver posição ou intenção pendente.
- O avaliador recebe um snapshot explícito e retorna decisão. Não implemente estratégia, indicadores, backtest, carteira persistente, livro de ofertas, motor de ordens ou servidor.
- Não implemente stops reais. Use um preço de saída planejada para estimar perda e eventos fictícios de execução para comparar com o realizado.
- Percentuais e filtros de quantidade são parâmetros didáticos, não recomendações ou regras atuais de exchange.

MODELOS E SEPARAÇÃO

Use modelos tipados simples para configuração, snapshot de avaliação, decisão e métricas patrimoniais. Use dataclasses e Enum quando ajudarem.

Separe cálculo financeiro, validação, regras de bloqueio e apresentação. Funções de cálculo devem retornar dados, sem print. Não use estado global mutável.

Uma avaliação não altera saldo, exposição, posição ou patrimônio. A aprovação não cria automaticamente uma reserva, ordem ou execução. Receba um snapshot novo para cada avaliação. Explique que validação e reserva precisariam ser coordenadas atomicamente numa integração real para evitar aprovações concorrentes sobre o mesmo saldo.

VALORES E DATAS

- Use Decimal construído de strings para todos os valores financeiros, percentuais e quantidades. Não use float nem conversão intermediária via float.
- Rejeite NaN, sNaN, infinitos, strings vazias/malformadas e tipos inadequados. Anotações de tipo não substituem validação.
- Defina contexto local com precisão 28 e ROUND_HALF_EVEN; preserve o contexto externo. Calcule com precisão interna e arredonde só apresentação, exceto o ajuste obrigatório da quantidade para baixo.
- Datas devem ter fuso, normalizadas para UTC. Use relógio injetável e horários fixos nos cenários.
- Todo valor exibido deve identificar unidade: BTC, USDT, percentual ou segundos.

ENTRADAS DO AVALIADOR

Defina pelo menos:
- Patrimônio atual em USDT, maior que zero para uma entrada.
- Saldo livre em USDT, não negativo e já descontadas quaisquer reservas externas.
- Exposição nominal atual em USDT, não negativa.
- Preço estimado de entrada E e preço de saída planejada S, com E > S > 0.
- Alíquota de compra fc e venda fv, ambas no intervalo [0, 1).
- Fração de risco r e fração máxima de exposição x, ambas em (0, 1].
- Incremento de quantidade step e quantidade mínima, positivos; valor nominal mínimo, não negativo.
- Snapshot da posição: vazia ou aberta; intenção pendente: sim/não; ordem com resultado desconhecido: sim/não.
- Horário do preço, instante de avaliação e idade máxima permitida, positiva.
- Estado de bloqueio diário/drawdown, calculado pelas regras abaixo, e eventual bloqueio manual.

No laboratório, patrimônio, saldo e exposição são fornecidos por um snapshot confiável externo; não derive patrimônio de saldo livre apenas. Documente que exposição usa o mesmo preço de referência corrente da avaliação. Valide saldo livre + exposição <= patrimônio, admitindo que a diferença possa representar recursos reservados. Não invente saldo para ajustar snapshot inconsistente.

FÓRMULAS DE DIMENSIONAMENTO

Taxas são cobradas em USDT nas duas pontas. O orçamento de risco cobre a perda estimada entre compra e saída planejada, incluindo essas taxas, mas sem slippage no cenário-base.

R = patrimônio * r
L = E * (1 + fc) - S * (1 - fv)
q_risco = R / L
exposição_máxima = patrimônio * x
exposição_restante = max(0, exposição_máxima - exposição_atual)
q_exposição = exposição_restante / E
q_saldo = saldo_livre / (E * (1 + fc))
q_bruta = min(q_risco, q_exposição, q_saldo)
q = floor(q_bruta / step) * step

O floor deve ser aplicado ao número de incrementos. Não use apenas quantize: step pode ser "0.000003", não somente potência de dez.

Após o ajuste, recalcule:
- Valor nominal da compra = q * E.
- Taxa de entrada = q * E * fc.
- Desembolso estimado = q * E * (1 + fc).
- Recebimento líquido planejado = q * S * (1 - fv).
- Perda estimada = desembolso - recebimento líquido planejado = q * L.
- Exposição resultante = exposição_atual + q * E.

Confirme as desigualdades finais usando os valores internos: perda <= R, desembolso <= saldo livre e exposição resultante <= exposição máxima. Trate eventuais excessos por arredondamento decimal reduzindo um incremento e revalidando, nunca arredondando quantidade para cima.

Se q for zero, inferior à quantidade mínima ou q*E inferior ao nominal mínimo, rejeite. Não aumente a compra para atingir um mínimo. Igualdade com mínimo/limite é permitida.

O limite de exposição usa valor nominal e não inclui taxas; o saldo deve cobrir taxas. Declare essa diferença.

MOTIVOS E PRECEDÊNCIA

Validação de dados vem antes de regras comerciais. Entrada estruturalmente inválida deve produzir erro de validação, sem divisão por zero ou resultado financeiro fictício.

Para snapshots válidos, adote precedência determinística:
1. Bloqueio manual.
2. Ordem com resultado desconhecido, aguardando reconciliação.
3. Limite diário ou drawdown bloqueado.
4. Preço ausente/desatualizado.
5. Intenção pendente.
6. Posição já aberta.
7. Exposição sem espaço.
8. Saldo livre zero.
9. Quantidade ajustada zero ou abaixo dos filtros mínimos.
10. Aprovação da quantidade calculada.

Preço com horário futuro em relação à avaliação é dado inválido. Preço com idade exatamente igual à máxima é aceito; acima dela é desatualizado. Preço ausente é bloqueio esperado e não deve ser substituído por zero.

Permita reduzir a quantidade por saldo: não rejeite uma compra menor válida apenas porque a quantidade pelo risco exigiria mais saldo. Informe o(s) limitador(es) ativo(s), incluindo empates, e os três candidatos antes do ajuste.

RETORNO DA AVALIAÇÃO

Retorne APROVADA ou REJEITADA, motivo estável, explicação, limitadores, orçamento de risco, quantidades candidatas e quantidade aprovada, desembolso, perda estimada e exposição resultante.

Na rejeição, quantidade aprovada é zero. Valores que não foram calculados devem ser null/indisponíveis, não estimativas inventadas. Se mostrar quantidade candidata rejeitada por mínimo, diferencie-a da aprovada.

MÉTRICAS PATRIMONIAIS E BLOQUEIOS

Crie um componente pequeno que receba observações cronológicas de patrimônio marcado a mercado e calcule métricas. Nos exemplos não existem depósitos ou retiradas.

Patrimônio é dinheiro total mais valor das posições abertas ao preço de referência; reservas de caixa são parte do dinheiro total, não um ativo adicional. O laboratório recebe a série patrimonial pronta e não implementa o cálculo de uma carteira completa. Falta de preço válido impede novas entradas, em vez de tratar posição como sem valor.

- Início do dia: 00:00 UTC por convenção didática.
- Para cada dia, a primeira observação válida é a base diária; se não for à meia-noite, informe que a medida vale desde a primeira observação disponível.
- Perda diária (%) = max(0, (base_diária - patrimônio_atual) / base_diária * 100).
- Pico = maior patrimônio observado desde o início da sessão, inclusive o atual.
- Drawdown (%) = (pico - patrimônio_atual) / pico * 100.
- As bases devem ser positivas; patrimônio observado pode ser zero. Zero aciona bloqueio, sem impedir calcular drawdown de 100%.
- Atingir ou ultrapassar limiar de perda diária bloqueia novas entradas até a mudança do dia UTC. Uma recuperação posterior no mesmo dia não desbloqueia.
- Atingir ou ultrapassar limiar de drawdown bloqueia novas entradas pelo restante da sessão. Recuperação e mudança de dia não removem esse bloqueio.
- Não implemente desbloqueio automático do drawdown, nem esconda o bloqueio reiniciando o pico. Uma nova sessão é uma ação explícita do laboratório, com limites claramente documentados.
- Observação fora de ordem é rejeitada sem alterar métricas; mesma data/hora e valor é duplicata ignorada; mesma data/hora com valor diferente é conflito.

Bloqueios de entrada não encerram posição nem apagam intenção. Demonstre separadamente que acompanhamento e uma solicitação fictícia de saída de posição existente continuam permitidos. Não aplique orçamento de risco de compra a uma saída que reduz a posição. Não implemente venda real nem afirme execução garantida.

CENÁRIOS OBRIGATÓRIOS

Cada cenário usa configuração e estado próprios, sem herdar bloqueios dos demais.

A. Dimensionamento limitado pela exposição
   Patrimônio=1.000 USDT; saldo livre=1.000; exposição atual=0; posição vazia.
   E=100.000; S=98.000; fc=fv=0,001; r=0,01; x=0,20.
   step=0,000001 BTC; mínimo=0,000001 BTC; nominal mínimo=1 USDT.
   Preço atual válido, sem bloqueios ou pendências.
   Esperado: R=10 USDT; L=2.198 USDT por BTC; q_risco=10/2.198; q_exposição=0,002 BTC; q_saldo=1.000/100.100 BTC.
   Quantidade aprovada=0,002 BTC; nominal=200 USDT; taxa de entrada=0,2 USDT; desembolso=200,2 USDT; recebimento planejado=195,804 USDT; perda estimada=4,396 USDT; exposição final=200 USDT.
   Limitador: exposição.

B. Dimensionamento limitado pelo risco
   Use A, mas x=1.
   Esperado: quantidade após ajuste=0,004549 BTC; desembolso=455,3549 USDT; perda estimada=9,998702 USDT; exposição nominal=454,9 USDT.
   Limitador: risco. Demonstre que não arredondar para cima preserva o orçamento de 10 USDT.

C. Saldo e filtros mínimos
   Use A com saldo livre=100 USDT e x=1.
   Esperado: q_saldo=100/100.100; quantidade aprovada=0,000999 BTC; desembolso=99,9999 USDT; perda estimada=2,195802 USDT.
   Limitador: saldo. Demonstre também saldo zero e um caso com quantidade candidata abaixo do mínimo: rejeitar sem aumentar quantidade.
   Acrescente teste de incremento não decimal simples, como step=0,000003.

D. Bloqueios e dados inválidos
   Demonstre separadamente posição aberta, intenção pendente, ordem não reconciliada, bloqueio manual, preço ausente e preço acima da idade máxima.
   Valide idade exatamente no limite, horário futuro inválido, E<=S, alíquotas inválidas, valor não finito e snapshot inconsistente.
   Em cada rejeição/erro, estado original permanece intacto. Teste a precedência quando mais de uma condição estiver presente.

E. Perda diária e drawdown
   Série no mesmo dia UTC: 1.000 → 1.050 → 990 USDT, em horários crescentes fixos.
   No último ponto: perda diária=1%; drawdown=60/1.050*100, aproximadamente 5,714286%.
   Com limiar de drawdown=5%, novas entradas ficam bloqueadas. Se patrimônio recuperar para 1.020, o bloqueio continua.
   Em outra sessão: 1.000 → 970 USDT, limiar diário=3% e drawdown=20%: bloqueio diário na igualdade.
   Recuperação no mesmo dia não desbloqueia; primeira observação do dia UTC seguinte redefine apenas base/bloqueio diário.
   Demonstre patrimônio zero, duplicata e evento fora de ordem. Mostre que saída fictícia de posição existente não é bloqueada pelo limite de entrada.

F. Execução pior que a saída planejada
   Use a quantidade aprovada em B: 0,004549 BTC; compra confirmada a 100.000 USDT e venda confirmada a 97.000 USDT, ambas com taxa 0,10% em USDT.
   Custo da compra=455,3549 USDT; recebimento líquido da venda=440,811747 USDT; perda realizada=14,543153 USDT.
   Compare com perda planejada de 9,998702 USDT e orçamento de 10 USDT. Explique que a execução abaixo de 98.000 faz ultrapassar a estimativa.
   Não desconte slippage novamente: seu efeito já está no preço executado de 97.000. Stop é um gatilho/convenção de saída e não garante preço nem teto absoluto de perda. Stop-limit também pode não executar.

INTERFACE E FIXTURES

Implemente:
- python -m riskgate: todos os cenários em ordem, com sessões isoladas.
- python -m riskgate --cenario a: seleção a, b, c, d, e ou f.
- python -m riskgate --arquivo data/exemplos/avaliacao.json: avalia snapshot e configuração locais.
- --formato texto|json|html: texto detalhado como padrão, JSON para scripts e HTML independente para navegador/impressão. Funciona com cenários e modo arquivo, preservando códigos de saída.
- python -m riskgate --help.
- python -m unittest discover -s tests -v.

Nos relatórios, exiba as entradas efetivamente usadas, decisão, motivos, limitadores, cálculos e interpretação por caso. Diferencie uma candidata rejeitada da quantidade aprovada e indique quando o dimensionamento não foi realizado. Em E, mostre limites das sessões e observações patrimoniais; em F, mostre preços da execução fictícia. No HTML, inclua resumo, tabelas, navegação por cenário e estilo de impressão, sem dependências externas. Escape os dados interpolados no HTML.
Inclua no HTML uma memória de cálculo com fórmula simbólica, substituição numérica, resultado com unidade e legenda das letras e operadores. Explique taxas como frações, ajuste por floor ao incremento e possível redução adicional por revalidação decimal. Exiba desigualdades de risco, exposição, saldo e filtros mínimos, distinguindo condição atendida de não atendida. Em E, apresente perda diária e drawdown sem dividir por uma base diária indisponível; em F, custo, recebimento, perda e comparação com orçamento/planejado. Não calcule dimensionamento para entradas inválidas ou bloqueios anteriores ao cálculo.

Documente a exportação em uma mesma sessão Bash, na raiz do projeto:

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
```

Explique que mktemp cria um diretório exclusivo no local temporário do sistema, os arquivos são escritos pelo redirecionamento do shell e devem ser copiados para um local permanente caso precisem ser mantidos. Não confunda .txt de saída com contrato JSON de entrada.

Documente contrato JSON versionado com schema_version inteiro 1, decimais como strings, booleanos reais e datas ISO com fuso. Rejeite JSON malformado, chaves duplicadas, campos inesperados/ausentes, versões diferentes e constantes NaN/Infinity. Não aceite bool como versão.

Código de saída no modo arquivo: 0 para APROVADA; 2 para REJEITADA por política; 1 para erro de arquivo ou dados/configuração inválidos. Nos cenários demonstrativos, rejeições/erros esperados fazem parte do sucesso; uma falha inesperada deve produzir saída não zero.

ENTREGÁVEIS

- pyproject.toml, pacote riskgate, fixtures JSON, testes e .gitignore.
- README.md com comandos, fórmulas, unidades, contrato de entrada, limites e diferença entre aprovação, ordem e execução.
- docs/sprint05-glossario.md: orçamento de risco, exposição, saldo livre, patrimônio, stop, slippage, step, perda realizada/não realizada, drawdown, reconciliação e bloqueio de entradas.
- docs/sprint05-validacao.md com roteiro, valores esperados, comandos efetivamente executados e resultados observados.

TESTES E ACEITE

Confira os valores exatos de A/B/C/F com Decimal. Teste mínimos e limites na igualdade, arredondamento para baixo e incremento não potência de dez. As quantidades aprovadas devem respeitar risco, saldo e exposição simultaneamente, mesmo nos casos próximos de limites.

Teste rejeições sem mutação, precedência, preço desatualizado, datas com/sem fuso, virada UTC, bloqueios persistentes e série patrimonial inválida. Verifique o contexto decimal externo preservado e resultados estáveis quando a precisão externa variar.

Execute todos os cenários juntos e separados, ajuda, modo arquivo aprovado/rejeitado/inválido e unittest. Corrija falhas. Não apresente resultado esperado como se fosse execução real.
Confira os três formatos de relatório e a exportação para diretório temporário: seis cenários e execução completa devem produzir 21 arquivos não vazios, sendo sete de cada formato. Verifique conteúdo, JSON válido e códigos de saída; rejeições e erros esperados não devem aparecer como falhas do teste no relatório HTML.

Finalize informando arquivos criados, comandos executados, resultados, limitações e pendências reais. Não faça commits, publicação ou ações externas sem solicitação.
````

## 4. Conclusão da etapa

A etapa estará concluída quando as decisões puderem ser conferidas por fórmulas e motivos explícitos, as compras aprovadas respeitarem os limites e o exemplo demonstrar que perda estimada não é garantia de perda máxima.

A próxima etapa será backtest, com dados históricos, custos e regras explícitas de execução.
