# Sprint 05 — Glossário

| Termo | Significado no laboratório |
| --- | --- |
| Orçamento de risco | Patrimônio × fração de risco, em USDT. Limita a perda estimada da compra, incluindo taxas; não garante perda máxima realizada. |
| Exposição | Valor nominal da posição ao preço de referência corrente, em USDT. O limite não inclui taxas. |
| Saldo livre | USDT disponíveis, descontadas reservas externas. Deve cobrir compra e taxa de entrada. |
| Patrimônio | Dinheiro total, incluindo reservas, mais posições marcadas ao preço de referência. Não é apenas saldo livre. |
| Stop | Gatilho ou convenção de saída. Não garante preço nem execução; stop-limit também pode não executar. Não há stops reais neste projeto. |
| Slippage | Diferença entre preço planejado e executado. Em F já está no preço de venda fictício; não se desconta novamente. |
| Step | Incremento permitido de quantidade em BTC. Ajusta-se para baixo por número de incrementos, inclusive quando não é potência de dez. |
| Perda realizada | Custo da compra menos recebimento líquido da venda executada, incluindo taxas. Em F os eventos são fictícios. |
| Perda não realizada | Redução do valor marcado a mercado de uma posição ainda aberta; pode afetar patrimônio sem venda. O laboratório recebe essa marcação pronta. |
| Drawdown | Queda percentual do patrimônio em relação ao maior patrimônio observado na sessão. Seu bloqueio permanece até encerrar explicitamente a sessão. |
| Perda diária | Queda percentual em relação à primeira observação positiva disponível do dia UTC, limitada inferiormente a zero. |
| Reconciliação | Verificação externa do estado de uma ordem cujo resultado é desconhecido. Enquanto pendente, novas entradas são bloqueadas. |
| Bloqueio de entradas | Impede novas compras; preserva posição, intenção, acompanhamento e possibilidade de solicitar saída fictícia. |
| Aprovação | Decisão sobre um snapshot válido. Não reserva saldo, não envia ordem e não confirma execução. |
| Snapshot | Retrato externo explícito de patrimônio, saldo, exposição, preço e condições operacionais de uma avaliação. |
| Nominal mínimo | Menor valor q × E em USDT aceito no exemplo. Uma quantidade não é aumentada para atingi-lo. |
| Relatório TXT | Visualização detalhada em texto, padrão da CLI ou `--formato texto`. Usa rótulos em português, vírgula decimal, entradas, cálculos e interpretação por caso. |
| Relatório JSON | Saída estruturada obtida com `--formato json`, para scripts. Usa decimais como strings e unidades explícitas; não é o mesmo contrato JSON de entrada de `--arquivo`. |
| Relatório HTML | Documento independente obtido com `--formato html`, para abrir no navegador e imprimir ou salvar como PDF. Não exige conexão com a internet. |
| Memória de cálculo | Seção do HTML com fórmula, valores substituídos e resultado com unidade. Inclui limites e filtros, perda diária/drawdown e comparação da execução fictícia, conforme o caso. |
| Símbolos nas fórmulas | A legenda de cada memória define letras como P (patrimônio), E (entrada) e q (quantidade). × e ÷ indicam multiplicação e divisão; ≤ e ≥ incluem igualdade; ≈ indica resultado com precisão decimal interna; ⌊z⌋ é o maior inteiro menor ou igual a z. Taxas percentuais são convertidas para frações antes do cálculo. |
| Diretório temporário | Pasta exclusiva criada com `mktemp -d`; seu caminho fica em uma variável, como `relatorios_dir`. O sistema pode removê-la em uma limpeza; copie arquivos que precisem ser mantidos. |
| Redirecionamento de saída | O operador `>` do shell grava stdout em um arquivo, criando-o ou substituindo seu conteúdo. Por exemplo, `> "$relatorios_dir/cenario-c.txt"`. Erros enviados a stderr continuam no terminal. |
