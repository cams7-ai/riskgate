"""Cálculos financeiros puros; entradas previamente validadas pelo avaliador."""
from decimal import Decimal
from .models import Config, Snapshot, Sizing, ExecutionComparison
from .validation import decimal_value, financial


@financial
def size_purchase(config: Config, snapshot: Snapshot) -> Sizing:
    e, s = snapshot.entry_price, snapshot.planned_exit
    budget = snapshot.equity * config.risk_fraction
    loss = e * (1 + config.buy_fee) - s * (1 - config.sell_fee)
    max_exposure = snapshot.equity * config.exposure_fraction
    candidates = {
        "risco": budget / loss,
        "exposicao": max(Decimal("0"), max_exposure - snapshot.exposure) / e,
        "saldo": snapshot.free_balance / (e * (1 + config.buy_fee)),
    }
    raw = min(candidates.values())
    limiters = tuple(key for key, value in candidates.items() if value == raw)
    # Divisão inteira exata impede que raw/step seja arredondado para o
    # incremento seguinte antes de aplicar floor, em fronteiras de 28 dígitos.
    raw_n, raw_d = raw.as_integer_ratio()
    step_n, step_d = config.step.as_integer_ratio()
    increments = (raw_n * step_d) // (raw_d * step_n)
    quantity = Decimal(increments) * config.step
    while True:
        notional = quantity * e
        fee = notional * config.buy_fee
        outlay = quantity * e * (1 + config.buy_fee)
        proceeds = quantity * s * (1 - config.sell_fee)
        estimated_loss = outlay - proceeds
        resulting_exposure = snapshot.exposure + notional
        # Verifica as duas formas da perda para não ocultar erro de arredondamento.
        if (quantity <= raw and estimated_loss <= budget and quantity * loss <= budget
                and outlay <= snapshot.free_balance and resulting_exposure <= max_exposure):
            break
        reduced = max(Decimal("0"), quantity - config.step)
        if reduced == quantity:
            from .validation import ValidationError
            raise ValidationError("Incremento não representável na precisão interna")
        quantity = reduced
    return Sizing(budget, loss, max_exposure, *candidates.values(), limiters,
                  quantity, notional, fee, outlay, proceeds, estimated_loss, resulting_exposure)


@financial
def compare_execution(quantity: Decimal, buy_price: Decimal, sell_price: Decimal,
                      buy_fee: Decimal, sell_fee: Decimal) -> ExecutionComparison:
    for name, value in (("quantity", quantity), ("buy_price", buy_price), ("sell_price", sell_price)):
        decimal_value(value, name, minimum=0, exclusive_min=True)
    for name, value in (("buy_fee", buy_fee), ("sell_fee", sell_fee)):
        decimal_value(value, name, minimum=0, maximum=1, exclusive_max=True)
    cost = quantity * buy_price * (1 + buy_fee)
    proceeds = quantity * sell_price * (1 - sell_fee)
    return ExecutionComparison(quantity, cost, proceeds, cost - proceeds)
