"""Memória de cálculo HTML baseada nas entradas e nos resultados da avaliação."""
from decimal import Decimal
from html import escape

from .reports import number, readable
from .validation import financial


def section(rows, legend, notes=()):
    parts = ['<section class="calculations"><h4>Memória de cálculo</h4>',
             '<p class="muted">Fórmula → substituição dos valores → resultado.</p>',
             '<div class="table-wrap"><table class="formula-table"><thead><tr>',
             '<th scope="col">Etapa</th><th scope="col">Fórmula</th>',
             '<th scope="col">Aplicação neste caso</th></tr></thead><tbody>']
    for label, formula, calculation in rows:
        parts.append(f'<tr><th scope="row">{escape(label)}</th>'
                     f'<td class="formula">{escape(formula)}</td>'
                     f'<td>{escape(calculation)}</td></tr>')
    parts.append('</tbody></table></div><h4>Legenda dos símbolos</h4><dl class="legend">')
    for symbol, meaning in legend.items():
        parts.append(f'<div><dt>{escape(symbol)}</dt><dd>{escape(meaning)}</dd></div>')
    parts.append('</dl>')
    parts += [f'<p class="muted">{escape(note)}</p>' for note in notes]
    parts.append('</section>')
    return ''.join(parts)


def decimal(data, key):
    return Decimal(data[key]['valor'])


@financial
def sizing_calculations(result):
    inputs, sizing = result['entradas'], result['dimensionamento_candidato']
    p, b, x, e, s = [number(inputs[key]['valor']) for key in (
        'patrimonio', 'saldo_livre', 'exposicao_atual', 'preco_entrada', 'saida_planejada')]
    fc, fv, r, cap = [number(decimal(inputs, key) / 100) for key in (
        'taxa_compra', 'taxa_venda', 'limite_risco', 'limite_exposicao')]
    n = lambda key: number(sizing[key]['valor'])
    amount = lambda key: readable(sizing[key])
    q, step = n('candidate_quantity'), number(inputs['incremento_quantidade']['valor'])
    raw = min(decimal(sizing, key) for key in ('risk_quantity', 'exposure_quantity', 'balance_quantity'))
    # Mesmo floor inteiro exato do dimensionamento; evita arredondar raw/step.
    raw_n, raw_d = raw.as_integer_ratio()
    step_value = decimal(inputs, 'incremento_quantidade')
    step_n, step_d = step_value.as_integer_ratio()
    increments = (raw_n * step_d) // (raw_d * step_n)
    initial = Decimal(increments) * step_value
    rows = [
        ('Orçamento de risco', 'R = P × r', f'{p} × {r} = {amount("risk_budget")}'),
        ('Perda por BTC', 'L = E × (1 + f_c) − S × (1 − f_v)',
         f'{e} × (1 + {fc}) − {s} × (1 − {fv}) = {amount("loss_per_btc")}'),
        ('Teto de exposição', 'Xmáx = P × x', f'{p} × {cap} = {amount("max_exposure")}'),
        ('Quantidade pelo risco', 'qᵣ = R ÷ L', f'{n("risk_budget")} ÷ {n("loss_per_btc")} ≈ {amount("risk_quantity")}'),
        ('Quantidade pela exposição', 'qₓ = max(0, Xmáx − X) ÷ E',
         f'max(0, {n("max_exposure")} − {x}) ÷ {e} ≈ {amount("exposure_quantity")}'),
        ('Quantidade pelo saldo', 'qₛ = B ÷ [E × (1 + f_c)]',
         f'{b} ÷ [{e} × (1 + {fc})] ≈ {amount("balance_quantity")}'),
        ('Menor quantidade', 'qᵦ = min(qᵣ, qₓ, qₛ)',
         f'min({n("risk_quantity")}; {n("exposure_quantity")}; {n("balance_quantity")}) = {number(raw)} BTC'),
        ('Ajuste ao incremento', 'q₀ = ⌊qᵦ ÷ δ⌋ × δ',
         f'⌊{number(raw)} ÷ {step}⌋ × {step} = {number(initial)} BTC; q final = {q} BTC'),
        ('Valor nominal', 'N = q × E', f'{q} × {e} = {amount("notional")}'),
        ('Taxa de compra', 'T = N × f_c', f'{n("notional")} × {fc} = {amount("entry_fee")}'),
        ('Desembolso', 'C = q × E × (1 + f_c)', f'{q} × {e} × (1 + {fc}) = {amount("outlay")}'),
        ('Venda líquida planejada', 'V = q × S × (1 − f_v)', f'{q} × {s} × (1 − {fv}) = {amount("planned_proceeds")}'),
        ('Perda estimada', 'Δ = C − V', f'{n("outlay")} − {n("planned_proceeds")} = {amount("estimated_loss")}'),
        ('Exposição resultante', 'Xfinal = X + N', f'{x} + {n("notional")} = {amount("resulting_exposure")}'),
    ]
    for label, formula, left, right in (
        ('Verificação de risco', 'Δ ≤ R', 'estimated_loss', 'risk_budget'),
        ('Verificação de exposição', 'Xfinal ≤ Xmáx', 'resulting_exposure', 'max_exposure'),
    ):
        respected = decimal(sizing, left) <= decimal(sizing, right)
        rows.append((label, formula, f'{n(left)} ≤ {n(right)} USDT — {"atendida" if respected else "não atendida"}'))
    rows.append(('Verificação de saldo', 'C ≤ B', f'{n("outlay")} ≤ {b} USDT — '
                 + ('atendida' if decimal(sizing, 'outlay') <= decimal(inputs, 'saldo_livre') else 'não atendida')))
    for label, formula, value, minimum, unit in (
        ('Filtro de quantidade', 'q ≥ qmín', decimal(sizing, 'candidate_quantity'), decimal(inputs, 'quantidade_minima'), 'BTC'),
        ('Filtro nominal', 'N ≥ Nmín', decimal(sizing, 'notional'), decimal(inputs, 'valor_nominal_minimo'), 'USDT'),
    ):
        rows.append((label, formula, f'{number(value)} ≥ {number(minimum)} {unit} — '
                     + ('atendido' if value >= minimum else 'não atendido')))
    notes = ['As taxas e os limites percentuais são usados como frações: 0,1% = 0,001; 1% = 0,01.',
             '≈ indica uma divisão apresentada com a precisão decimal interna. ⌊z⌋ é o maior inteiro menor ou igual a z; min escolhe o menor valor e max o maior.',
             'q₀ é o ajuste inicial. q é a candidata final após a revalidação dos limites; eventuais excessos decimais reduzem a quantidade por incrementos.']
    if result['status'] == 'REJEITADA':
        notes.append('Estes cálculos pertencem à candidata rejeitada. A quantidade aprovada permanece zero.')
    return section(rows, {
        'P / B / X': 'Patrimônio / saldo livre / exposição atual (USDT).',
        'E / S': 'Preço de entrada / preço de saída planejada (USDT/BTC).',
        'f_c / f_v': 'Taxas de compra / venda, como frações.',
        'r / x': 'Fração de risco / fração máxima de exposição.',
        'R / L': 'Orçamento de risco (USDT) / perda por BTC (USDT/BTC).',
        'qᵣ / qₓ / qₛ': 'Quantidades máximas por risco / exposição / saldo (BTC).',
        'qᵦ / q₀ / q': 'Quantidade bruta / ajustada inicialmente / candidata final (BTC).',
        'δ / qmín / Nmín': 'Incremento (BTC) / quantidade mínima (BTC) / nominal mínimo (USDT).',
        'N / T / C / V / Δ': 'Nominal / taxa de compra / desembolso / venda líquida / perda estimada (USDT).',
        'Xmáx / Xfinal': 'Teto de exposição / exposição resultante (USDT).',
        '≤ / ≥ / × / ÷': 'Menor ou igual / maior ou igual / multiplicação / divisão.',
    }, notes)


def metrics_calculations(result):
    p, peak = readable(result['equity']), readable(result['peak'])
    pn, peakn = number(result['equity']['valor']), number(result['peak']['valor'])
    rows = []
    if result['daily_base'] is not None:
        base = number(result['daily_base']['valor'])
        rows.append(('Perda diária', 'd = max(0, (P₀ − P) ÷ P₀ × 100)',
                     f'max(0, ({base} − {pn}) ÷ {base} × 100) ≈ {readable(result["daily_loss_percent"])}'))
    else:
        rows.append(('Perda diária', 'd = max(0, (P₀ − P) ÷ P₀ × 100)',
                     'Indisponível: ainda não existe uma base diária positiva. Nenhuma divisão foi realizada.'))
    rows.append(('Drawdown', 'DD = (Pₚ − P) ÷ Pₚ × 100',
                 f'({peakn} − {pn}) ÷ {peakn} × 100 ≈ {readable(result["drawdown_percent"])}'))
    return section(rows, {
        'P': f'Patrimônio observado: {p}.', 'P₀': f'Base diária: {readable(result["daily_base"])}.',
        'Pₚ': f'Pico observado na sessão: {peak}.',
        'd / DD': 'Perda diária / drawdown, em percentual.',
        'max / ≈': 'Seleciona o maior valor / resultado com precisão decimal interna.',
    }, ['O pico é o maior patrimônio observado até este instante. Os limites de bloqueio constam na abertura de cada sessão.',
        'Atingir o limiar diário bloqueia pelo restante do dia UTC; atingir o limiar de drawdown bloqueia pelo restante da sessão. Recuperação não remove bloqueios já acionados.'])


@financial
def execution_calculations(result):
    inputs = result['entradas']
    q = number(result['quantidade']['valor'])
    buy, sell = [number(inputs[key]['valor']) for key in (
        'preco_compra_executado_ficticio', 'preco_venda_executado_ficticio')]
    fc, fv = [number(decimal(inputs, key) / 100) for key in ('taxa_compra', 'taxa_venda')]
    cost, proceeds = [number(result[key]['valor']) for key in ('custo_compra', 'recebimento_venda')]
    loss, budget = decimal(result, 'perda_realizada_ficticia'), decimal(result, 'orcamento')
    rows = [
        ('Custo executado', 'Cₑ = q × Eₑ × (1 + f_c)', f'{q} × {buy} × (1 + {fc}) = {readable(result["custo_compra"])}'),
        ('Venda líquida executada', 'Vₑ = q × Sₑ × (1 − f_v)', f'{q} × {sell} × (1 − {fv}) = {readable(result["recebimento_venda"])}'),
        ('Perda realizada fictícia', 'Δₑ = Cₑ − Vₑ', f'{cost} − {proceeds} = {readable(result["perda_realizada_ficticia"])}'),
        ('Comparação com orçamento', 'Δₑ ≤ R', f'{number(loss)} ≤ {number(budget)} USDT — '
         + ('atendida' if loss <= budget else 'não atendida')),
        ('Diferença sobre o orçamento', 'Δₑ − R', f'{number(loss)} − {number(budget)} = {number(loss - budget)} USDT'),
        ('Diferença sobre o planejado', 'Δₑ − Δ',
         f'{number(loss)} − {number(result["perda_planejada"]["valor"])} = {number(loss - decimal(result, "perda_planejada"))} USDT'),
    ]
    return section(rows, {
        'q': 'Quantidade executada (BTC).', 'Eₑ / Sₑ': 'Preços efetivos fictícios de compra / venda (USDT/BTC).',
        'f_c / f_v': 'Taxas de compra / venda, como frações; 0,1% = 0,001.',
        'Cₑ / Vₑ / Δₑ': 'Custo / recebimento líquido / perda realizada fictícia (USDT).',
        'R / Δ': 'Orçamento de risco / perda planejada (USDT).',
        '≤ / × / ÷': 'Menor ou igual / multiplicação / divisão.',
    }, ['O slippage já está incorporado no preço executado. Não há desconto adicional de slippage.'])


def calculations(result):
    if result.get('dimensionamento_candidato') and result.get('entradas'):
        return sizing_calculations(result)
    if 'observed_at' in result:
        return metrics_calculations(result)
    if 'perda_realizada_ficticia' in result:
        return execution_calculations(result)
    if 'erro_esperado' in result:
        return '<p class="muted">Memória de cálculo indisponível: as entradas foram recusadas pela validação.</p>'
    return ''
