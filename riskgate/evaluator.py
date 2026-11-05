"""Validação antes das regras; aprovação não reserva nem executa nada."""
from dataclasses import replace
from datetime import datetime
from decimal import Decimal
from typing import Callable
from .finance import size_purchase
from .models import Config, Snapshot, Decision, Position, Reason, Status
from .validation import ValidationError, boolean, decimal_value, financial, utc


@financial
def validate(config: Config, snapshot: Snapshot) -> Snapshot:
    if not isinstance(config, Config) or not isinstance(snapshot, Snapshot):
        raise ValidationError("Esperados Config e Snapshot")
    for name in ("buy_fee", "sell_fee"):
        decimal_value(getattr(config, name), name, minimum=0, maximum=1, exclusive_max=True)
    for name in ("risk_fraction", "exposure_fraction"):
        decimal_value(getattr(config, name), name, minimum=0, maximum=1, exclusive_min=True)
    for name in ("step", "min_quantity", "max_price_age_seconds"):
        decimal_value(getattr(config, name), name, minimum=0, exclusive_min=True)
    decimal_value(config.min_notional, "min_notional", minimum=0)
    decimal_value(snapshot.equity, "equity", minimum=0, exclusive_min=True)
    for name in ("free_balance", "exposure"):
        decimal_value(getattr(snapshot, name), name, minimum=0)
    if snapshot.free_balance + snapshot.exposure > snapshot.equity:
        raise ValidationError("Saldo livre + exposição excedem patrimônio")
    decimal_value(snapshot.planned_exit, "planned_exit", minimum=0, exclusive_min=True)
    if not isinstance(snapshot.position, Position):
        raise ValidationError("position: esperado Position")
    for name in ("pending_intent", "unknown_order", "daily_blocked", "drawdown_blocked", "manual_blocked"):
        boolean(getattr(snapshot, name), name)
    evaluated_at = utc(snapshot.evaluated_at, "evaluated_at")
    price_at = None if snapshot.price_at is None else utc(snapshot.price_at, "price_at")
    if price_at is not None and price_at > evaluated_at:
        raise ValidationError("Horário do preço no futuro")
    if snapshot.entry_price is not None:
        decimal_value(snapshot.entry_price, "entry_price", minimum=0, exclusive_min=True)
        if snapshot.entry_price <= snapshot.planned_exit:
            raise ValidationError("Exige entry_price > planned_exit > 0")
    return replace(snapshot, evaluated_at=evaluated_at, price_at=price_at)


def age_seconds(snapshot: Snapshot) -> Decimal:
    delta = snapshot.evaluated_at - snapshot.price_at
    return (Decimal(delta.days) * Decimal("86400") + Decimal(delta.seconds)
            + Decimal(delta.microseconds) / Decimal("1000000"))


@financial
def evaluate(config: Config, snapshot: Snapshot, *, clock: Callable[[], datetime] | None = None) -> Decision:
    if clock is not None:
        if not isinstance(snapshot, Snapshot):
            raise ValidationError("Esperado Snapshot")
        snapshot = replace(snapshot, evaluated_at=utc(clock(), "clock"))
    snapshot = validate(config, snapshot)
    rules = (
        (snapshot.manual_blocked, Reason.MANUAL, "Bloqueio manual ativo."),
        (snapshot.unknown_order, Reason.UNKNOWN_ORDER, "Reconcilie a ordem com resultado desconhecido."),
        (snapshot.daily_blocked or snapshot.drawdown_blocked, Reason.LIMIT, "Limite diário ou drawdown bloqueou novas entradas."),
        (snapshot.entry_price is None or snapshot.price_at is None, Reason.MISSING_PRICE, "Preço ou horário de referência ausente."),
    )
    for blocked, reason, explanation in rules:
        if blocked:
            return Decision(Status.REJECTED, reason, explanation)
    if age_seconds(snapshot) > config.max_price_age_seconds:
        return Decision(Status.REJECTED, Reason.STALE_PRICE, "Preço acima da idade máxima permitida.")
    for blocked, reason, explanation in (
        (snapshot.pending_intent, Reason.PENDING, "Existe intenção pendente."),
        (snapshot.position == Position.OPEN, Reason.POSITION, "Já existe posição aberta."),
        (snapshot.exposure >= snapshot.equity * config.exposure_fraction, Reason.EXPOSURE, "Sem espaço de exposição nominal."),
        (snapshot.free_balance == 0, Reason.BALANCE, "Saldo livre zero USDT."),
    ):
        if blocked:
            return Decision(Status.REJECTED, reason, explanation)
    sizing = size_purchase(config, snapshot)
    if (sizing.candidate_quantity == 0 or sizing.candidate_quantity < config.min_quantity
            or sizing.notional < config.min_notional):
        return Decision(Status.REJECTED, Reason.MINIMUM,
                        "Quantidade candidata abaixo dos filtros; não será aumentada.", sizing=sizing)
    return Decision(Status.APPROVED, Reason.APPROVED, "Compra planejada respeita risco, saldo e exposição.",
                    sizing.candidate_quantity, sizing)


def position_actions(position: Position) -> dict[str, bool]:
    """Permissões didáticas; nenhuma ordem é enviada ou execução garantida."""
    if not isinstance(position, Position):
        raise ValidationError("position: esperado Position")
    return {"acompanhamento_permitido": True, "solicitacao_ficticia_saida_permitida": position == Position.OPEN}
