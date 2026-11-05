"""Cenários reproduzíveis e verificações do roteiro, com sessões isoladas."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal as D
from .evaluator import evaluate, position_actions
from .finance import compare_execution
from .metrics import EquitySession
from .models import Config, Snapshot, Position, Reason, Status
from .presentation import decision_dict, measured, metrics_dict
from .validation import ValidationError


NOW = datetime(2026, 1, 15, 12, tzinfo=timezone.utc)


def baseline():
    return Config(), Snapshot(D("1000"), D("1000"), D("0"), D("100000"), D("98000"), NOW, NOW)


def check(condition, message):
    if not condition:
        raise RuntimeError(f"Cenário falhou: {message}")


def case(config, snapshot, expected, label):
    before = snapshot
    decision = evaluate(config, snapshot)
    check(decision.reason == expected, label)
    check(snapshot == before, "snapshot alterado")
    return {"caso": label, **decision_dict(decision)}


def invalid(config, snapshot, label):
    before = snapshot
    try:
        evaluate(config, snapshot)
    except ValidationError as exc:
        check(snapshot == before, "snapshot alterado após erro")
        return {"caso": label, "erro_esperado": str(exc)}
    raise RuntimeError(f"Cenário falhou: dados inválidos aceitos: {label}")


def scenario_a():
    c, s = baseline()
    d = evaluate(c, s)
    check(d.approved_quantity == D("0.002"), "quantidade A")
    z = d.sizing
    check((z.risk_budget, z.loss_per_btc, z.notional, z.entry_fee, z.outlay,
           z.planned_proceeds, z.estimated_loss, z.resulting_exposure) ==
          tuple(map(D, ("10", "2198", "200", "0.2", "200.2", "195.804", "4.396", "200"))), "valores A")
    check(z.limiters == ("exposicao",), "limitador A")
    return [decision_dict(d)]


def scenario_b():
    c, s = baseline()
    d = evaluate(replace(c, exposure_fraction=D("1")), s)
    check(d.approved_quantity == D("0.004549"), "quantidade B")
    check((d.sizing.outlay, d.sizing.estimated_loss, d.sizing.notional) ==
          (D("455.3549"), D("9.998702"), D("454.9")), "valores B")
    check(d.sizing.limiters == ("risco",), "limitador B")
    check((d.approved_quantity + c.step) * d.sizing.loss_per_btc > d.sizing.risk_budget, "arredondar para cima excederia risco")
    return [decision_dict(d), {"observacao": "O próximo incremento ultrapassaria o orçamento de 10 USDT."}]


def scenario_c():
    c, s = baseline()
    c, s = replace(c, exposure_fraction=D("1")), replace(s, free_balance=D("100"))
    d = evaluate(c, s)
    check((d.approved_quantity, d.sizing.outlay, d.sizing.estimated_loss) ==
          (D("0.000999"), D("99.9999"), D("2.195802")), "valores C")
    check(d.sizing.limiters == ("saldo",), "limitador C")
    return [decision_dict(d),
            case(c, replace(s, free_balance=D("0")), Reason.BALANCE, "saldo zero"),
            case(replace(c, min_quantity=D("0.001")), s, Reason.MINIMUM, "abaixo do mínimo"),
            case(replace(c, step=D("0.000003")), s, Reason.APPROVED, "incremento 0.000003 BTC")]


def scenario_d():
    c, s = baseline()
    cases = [
        (replace(s, position=Position.OPEN), Reason.POSITION, "posição aberta"),
        (replace(s, pending_intent=True), Reason.PENDING, "intenção pendente"),
        (replace(s, unknown_order=True), Reason.UNKNOWN_ORDER, "ordem não reconciliada"),
        (replace(s, manual_blocked=True), Reason.MANUAL, "bloqueio manual"),
        (replace(s, entry_price=None, price_at=None), Reason.MISSING_PRICE, "preço ausente"),
        (replace(s, price_at=NOW - timedelta(seconds=61)), Reason.STALE_PRICE, "preço desatualizado"),
        (replace(s, price_at=NOW - timedelta(seconds=60)), Reason.APPROVED, "idade exatamente 60 segundos"),
        (replace(s, manual_blocked=True, unknown_order=True, daily_blocked=True, pending_intent=True,
                 position=Position.OPEN), Reason.MANUAL, "precedência manual"),
    ]
    result = [case(c, snap, reason, label) for snap, reason, label in cases]
    for snap, label in (
        (replace(s, price_at=NOW + timedelta(microseconds=1)), "horário futuro"),
        (replace(s, entry_price=D("98000")), "E igual S"),
        (replace(s, equity=D("NaN")), "valor não finito"),
        (replace(s, exposure=D("1")), "snapshot inconsistente"),
    ):
        result.append(invalid(c, snap, label))
    result.append(invalid(replace(c, buy_fee=D("1")), s, "alíquota inválida"))
    return result


def scenario_e():
    result = []
    session = EquitySession(D("3"), D("5"))
    for offset, equity in enumerate(("1000", "1050", "990", "1020")):
        m = session.observe(NOW + timedelta(hours=offset), D(equity))
        result.append({"sessao": "drawdown", **metrics_dict(m)})
        if equity == "990":
            check(m.daily_loss_percent == D("1") and m.drawdown_blocked, "drawdown E")
    check(m.drawdown_blocked, "recuperação não remove drawdown")
    c, s = baseline()
    result.append(case(c, replace(s, daily_blocked=m.daily_blocked, drawdown_blocked=m.drawdown_blocked),
                       Reason.LIMIT, "nova entrada bloqueada pelas métricas"))
    result.append({"posicao": Position.OPEN.value, **position_actions(Position.OPEN),
                   "observacao": "Acompanhamento e solicitação fictícia de saída continuam permitidos; não há execução."})
    m = session.observe(NOW + timedelta(days=1), D("1060"))
    check(m.drawdown_blocked and not m.daily_blocked, "drawdown persiste na virada UTC")
    result.append({"sessao": "drawdown no dia seguinte", **metrics_dict(m)})
    daily = EquitySession(D("3"), D("20"))
    for offset, equity in enumerate(("1000", "970", "1000")):
        m = daily.observe(NOW + timedelta(hours=offset), D(equity))
        result.append({"sessao": "diario", **metrics_dict(m)})
        if offset:
            check(m.daily_blocked and not m.drawdown_blocked, "bloqueio diário persistente")
    m = daily.observe(NOW + timedelta(days=1), D("1000"))
    check(not m.daily_blocked, "reset diário UTC")
    result.append({"sessao": "diario no dia seguinte", **metrics_dict(m)})
    m = daily.observe(NOW + timedelta(days=1, hours=1), D("0"))
    check(m.drawdown_percent == D("100") and m.daily_blocked and m.drawdown_blocked, "patrimônio zero")
    result.append({"sessao": "patrimônio zero", **metrics_dict(m)})
    check(daily.observe(m.observed_at, D("0")) is m, "duplicata ignorada")
    result.append({"duplicata": "ignorada, sem alteração"})
    try:
        daily.observe(NOW, D("1000"))
    except ValidationError as exc:
        check(daily.current is m, "evento fora de ordem alterou métricas")
        result.append({"erro_esperado": str(exc)})
    else:
        raise RuntimeError("Evento fora de ordem foi aceito")
    return result


def scenario_f():
    c, s = baseline()
    d = evaluate(replace(c, exposure_fraction=D("1")), s)
    actual = compare_execution(d.approved_quantity, D("100000"), D("97000"), c.buy_fee, c.sell_fee)
    check((actual.purchase_cost, actual.net_sale, actual.realized_loss) ==
          (D("455.3549"), D("440.811747"), D("14.543153")), "valores F")
    return [{"quantidade": measured(actual.quantity, "BTC"),
             "custo_compra": measured(actual.purchase_cost, "USDT"),
             "recebimento_venda": measured(actual.net_sale, "USDT"),
             "perda_realizada_ficticia": measured(actual.realized_loss, "USDT"),
             "perda_planejada": measured(d.sizing.estimated_loss, "USDT"),
             "orcamento": measured(d.sizing.risk_budget, "USDT"),
             "observacao": "Venda fictícia a 97000 USDT abaixo de 98000 USDT excede o orçamento. "
                            "Slippage já está no preço executado e não é descontado novamente. "
                            "Stop não garante preço nem teto absoluto de perda; stop-limit pode não executar."}]


def run_scenarios(selected=None):
    scenarios = {"a": scenario_a, "b": scenario_b, "c": scenario_c,
                 "d": scenario_d, "e": scenario_e, "f": scenario_f}
    return [{"cenario": name.upper(), "resultados": scenario()}
            for name, scenario in scenarios.items() if selected is None or selected == name]
