"""Sessão patrimonial em memória, sem carteira ou persistência."""
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from .validation import ValidationError, decimal_value, financial, utc


@dataclass(frozen=True)
class Metrics:
    observed_at: datetime
    equity: Decimal
    daily_base: Decimal | None
    daily_base_at: datetime | None
    peak: Decimal
    daily_loss_percent: Decimal | None
    drawdown_percent: Decimal
    daily_blocked: bool
    drawdown_blocked: bool


class EquitySession:
    """Criar uma instância é iniciar explicitamente uma nova sessão."""

    def __init__(self, daily_limit_percent: Decimal, drawdown_limit_percent: Decimal):
        for name, value in (("daily_limit_percent", daily_limit_percent),
                            ("drawdown_limit_percent", drawdown_limit_percent)):
            decimal_value(value, name, minimum=0, maximum=100, exclusive_min=True)
        self._daily_limit = daily_limit_percent
        self._drawdown_limit = drawdown_limit_percent
        self._current: Metrics | None = None

    @property
    def current(self) -> Metrics | None:
        return self._current

    @financial
    def observe(self, observed_at: datetime, equity: Decimal) -> Metrics:
        observed_at = utc(observed_at, "observed_at")
        decimal_value(equity, "equity", minimum=0)
        previous = self._current
        if previous is not None:
            if observed_at < previous.observed_at:
                raise ValidationError("Observação fora de ordem")
            if observed_at == previous.observed_at:
                if equity == previous.equity:
                    return previous
                raise ValidationError("Observação conflitante no mesmo instante")
        if previous is None and equity == 0:
            raise ValidationError("A sessão precisa de patrimônio inicial positivo para formar o pico")
        new_day = previous is None or observed_at.date() != previous.observed_at.date()
        base = None if new_day else previous.daily_base
        base_at = None if new_day else previous.daily_base_at
        if base is None and equity > 0:
            base, base_at = equity, observed_at
        peak = equity if previous is None else max(previous.peak, equity)
        daily_loss = None if base is None else max(Decimal("0"), (base - equity) / base * 100)
        drawdown = (peak - equity) / peak * 100
        daily_blocked = (equity == 0 or (daily_loss is not None and daily_loss >= self._daily_limit)
                         or (not new_day and previous.daily_blocked))
        drawdown_blocked = (equity == 0 or drawdown >= self._drawdown_limit
                            or (previous is not None and previous.drawdown_blocked))
        current = Metrics(observed_at, equity, base, base_at, peak, daily_loss, drawdown,
                          daily_blocked, drawdown_blocked)
        # Atribuição somente depois de validar e calcular tudo.
        self._current = current
        return current
