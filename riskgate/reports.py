"""Relatórios de terminal em português, derivados dos mesmos dados do JSON."""
from datetime import datetime
from decimal import Decimal, localcontext


LABELS = {
    "patrimonio": "Patrimônio", "saldo_livre": "Saldo livre",
    "exposicao_atual": "Exposição atual", "preco_entrada": "Preço de entrada",
    "saida_planejada": "Preço de saída planejada", "taxa_compra": "Taxa de compra",
    "taxa_venda": "Taxa de venda", "limite_risco": "Limite de risco",
    "limite_exposicao": "Limite de exposição", "incremento_quantidade": "Incremento de quantidade",
    "quantidade_minima": "Quantidade mínima", "valor_nominal_minimo": "Valor nominal mínimo",
    "idade_maxima_preco": "Idade máxima do preço", "horario_preco": "Horário do preço",
    "horario_avaliacao": "Horário da avaliação", "posicao": "Posição",
    "intencao_pendente": "Intenção pendente", "ordem_desconhecida": "Ordem desconhecida",
    "bloqueio_diario": "Bloqueio diário", "bloqueio_drawdown": "Bloqueio por drawdown",
    "bloqueio_manual": "Bloqueio manual", "limite_diario": "Limite diário",
    "limite_drawdown": "Limite de drawdown", "horario_observacao": "Horário da observação",
    "preco_compra_executado_ficticio": "Preço de compra executado (fictício)",
    "preco_venda_executado_ficticio": "Preço de venda executado (fictício)",
    "risk_budget": "Orçamento de perda planejada", "loss_per_btc": "Perda planejada por BTC",
    "max_exposure": "Teto de exposição nominal", "risk_quantity": "Quantidade máxima pelo risco",
    "exposure_quantity": "Quantidade máxima pela exposição",
    "balance_quantity": "Quantidade máxima pelo saldo (com taxa)",
    "candidate_quantity": "Quantidade candidata após ajuste ao incremento",
    "notional": "Valor nominal da compra", "entry_fee": "Taxa de compra em USDT",
    "outlay": "Desembolso total", "planned_proceeds": "Recebimento líquido na saída planejada",
    "estimated_loss": "Perda estimada", "resulting_exposure": "Exposição nominal resultante",
    "observed_at": "Horário da observação", "equity": "Patrimônio observado",
    "daily_base": "Patrimônio de referência do dia", "daily_base_at": "Início da base diária",
    "peak": "Maior patrimônio da sessão", "daily_loss_percent": "Perda diária",
    "drawdown_percent": "Queda em relação ao pico (drawdown)",
    "daily_blocked": "Bloqueio diário", "drawdown_blocked": "Bloqueio por drawdown",
    "base_diaria_parcial": "Base diária iniciada após 00:00 UTC",
    "quantidade": "Quantidade da execução fictícia", "custo_compra": "Custo total da compra",
    "recebimento_venda": "Recebimento líquido da venda",
    "perda_realizada_ficticia": "Perda realizada fictícia", "perda_planejada": "Perda planejada",
    "orcamento": "Orçamento de risco", "acompanhamento_permitido": "Acompanhamento permitido",
    "solicitacao_ficticia_saida_permitida": "Solicitação fictícia de saída permitida",
}

TITLES = {
    "A": "Compra limitada pela exposição",
    "B": "Compra limitada pelo orçamento de risco",
    "C": "Saldo disponível e filtros de quantidade",
    "D": "Bloqueios, validade do preço e validação de entradas",
    "E": "Perda diária, drawdown e persistência dos bloqueios",
    "F": "Comparação entre perda planejada e execução fictícia",
}


def number(value):
    """Formata sem float nem arredondamento dos valores apresentados."""
    result = format(Decimal(str(value)), ",f")
    if "." in result:
        result = result.rstrip("0").rstrip(".")
    return result.translate(str.maketrans({",": ".", ".": ","}))


def readable(value):
    if value is None:
        return "não informado / não disponível"
    if isinstance(value, bool):
        return "sim" if value else "não"
    if isinstance(value, datetime):
        return value.isoformat(sep=" ")
    if isinstance(value, dict) and "valor" in value:
        return f"{number(value['valor'])} {value['unidade']}"
    return str(value)


def fields(data, indent="  "):
    return [f"{indent}{LABELS.get(key, key.replace('_', ' ').capitalize())}: {readable(value)}"
            for key, value in data.items()]


def interpretation(result):
    sizing = result.get("dimensionamento_candidato")
    if not sizing:
        return ["  O dimensionamento não foi realizado: a avaliação foi interrompida pela regra indicada."]
    inputs = result.get("entradas", {})
    lines = ["  A quantidade é o menor dos limites de risco, exposição e saldo, ajustada para baixo ao incremento.",
             "  O saldo cobre a taxa de compra; a exposição considera o valor nominal, sem taxas.",
             "  A perda estimada é o desembolso menos a venda líquida, incluindo as duas taxas."]
    if result["status"] == "REJEITADA":
        lines.append("  Os cálculos descrevem uma candidata rejeitada; a quantidade aprovada é zero.")
    elif inputs:
        with localcontext() as ctx:
            ctx.prec = 60
            loss = Decimal(sizing["estimated_loss"]["valor"])
            equity = Decimal(inputs["patrimonio"]["valor"])
            balance = Decimal(inputs["saldo_livre"]["valor"])
            outlay = Decimal(sizing["outlay"]["valor"])
            lines.extend([
                f"  Saldo livre após a compra planejada: {number(balance - outlay)} USDT.",
                f"  Perda planejada sobre o patrimônio: {number(loss / equity * 100)} %.",
            ])
    return lines


def case_report(result, index):
    name = result.get("caso") or result.get("sessao") or (
        "avaliação principal" if "status" in result else "observação")
    lines = [f"Caso {index} — {name}"]
    if "entradas" in result:
        lines += ["Entradas:", *fields(result["entradas"])]
    if "status" in result:
        lines += [f"Decisão: {result['status']} ({result['motivo']})",
                  f"  {result['explicacao']}",
                  f"  Quantidade aprovada: {readable(result['quantidade_aprovada'])}"]
        if result["limitadores"]:
            names = {"risco": "risco", "exposicao": "exposição", "saldo": "saldo"}
            lines.append("  Restrição que determina a quantidade: " +
                         ", ".join(names.get(key, key) for key in result["limitadores"]))
        if result["dimensionamento_candidato"] is not None:
            lines += ["Dimensionamento:", *fields(result["dimensionamento_candidato"])]
        lines += ["Interpretação:", *interpretation(result)]
    elif "erro_esperado" in result:
        lines += [f"Validação: erro esperado detectado — {result['erro_esperado']}",
                  "  O dado foi recusado; esse erro faz parte do teste."]
    else:
        details = {key: value for key, value in result.items()
                   if key not in ("entradas", "sessao", "observacao", "caso")}
        if details:
            lines += ["Resultado:", *fields(details)]
        if "observed_at" in result:
            lines.append("  Perda diária compara com a base do dia; drawdown compara com o pico da sessão.")
            lines.append("  Um bloqueio acionado pode persistir mesmo após a recuperação do patrimônio.")
    if "observacao" in result:
        lines.append(f"Observação: {result['observacao']}")
    return "\n".join(lines)


def text_report(value):
    lines = ["RISKGATE — RELATÓRIO DETALHADO",
             "Simulação fictícia: nenhuma ordem é enviada. Perdas planejadas dependem dos preços de execução.", ""]
    if isinstance(value, dict):
        lines.append(case_report(value, 1))
    else:
        for scenario in value:
            name = scenario["cenario"]
            lines += [f"CENÁRIO {name} — {TITLES[name]}", "=" * 72]
            for index, result in enumerate(scenario["resultados"], 1):
                lines += [case_report(result, index), ""]
            lines += ["Verificações programadas do cenário: concluídas sem divergências.", ""]
    return "\n".join(lines)
