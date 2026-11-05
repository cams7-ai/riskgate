"""Contratos imutáveis; a validação ocorre na fronteira do avaliador."""
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum


class Position(str, Enum):
    EMPTY = "VAZIA"
    OPEN = "ABERTA"


class Status(str, Enum):
    APPROVED = "APROVADA"
    REJECTED = "REJEITADA"


class Reason(str, Enum):
    MANUAL = "BLOQUEIO_MANUAL"
    UNKNOWN_ORDER = "AGUARDANDO_RECONCILIACAO"
    LIMIT = "LIMITE_PATRIMONIAL"
    MISSING_PRICE = "PRECO_AUSENTE"
    STALE_PRICE = "PRECO_DESATUALIZADO"
    PENDING = "INTENCAO_PENDENTE"
    POSITION = "POSICAO_ABERTA"
    EXPOSURE = "EXPOSICAO_SEM_ESPACO"
    BALANCE = "SALDO_ZERO"
    MINIMUM = "QUANTIDADE_ABAIXO_DOS_MINIMOS"
    APPROVED = "LIMITES_RESPEITADOS"


@dataclass(frozen=True)
class Config:
    buy_fee: Decimal = Decimal("0.001")
    sell_fee: Decimal = Decimal("0.001")
    risk_fraction: Decimal = Decimal("0.01")
    exposure_fraction: Decimal = Decimal("0.20")
    step: Decimal = Decimal("0.000001")
    min_quantity: Decimal = Decimal("0.000001")
    min_notional: Decimal = Decimal("1")
    max_price_age_seconds: Decimal = Decimal("60")


@dataclass(frozen=True)
class Snapshot:
    equity: Decimal
    free_balance: Decimal
    exposure: Decimal
    entry_price: Decimal | None
    planned_exit: Decimal
    price_at: datetime | None
    evaluated_at: datetime
    position: Position = Position.EMPTY
    pending_intent: bool = False
    unknown_order: bool = False
    daily_blocked: bool = False
    drawdown_blocked: bool = False
    manual_blocked: bool = False


@dataclass(frozen=True)
class Sizing:
    risk_budget: Decimal
    loss_per_btc: Decimal
    max_exposure: Decimal
    risk_quantity: Decimal
    exposure_quantity: Decimal
    balance_quantity: Decimal
    limiters: tuple[str, ...]
    candidate_quantity: Decimal
    notional: Decimal
    entry_fee: Decimal
    outlay: Decimal
    planned_proceeds: Decimal
    estimated_loss: Decimal
    resulting_exposure: Decimal


@dataclass(frozen=True)
class Decision:
    status: Status
    reason: Reason
    explanation: str
    approved_quantity: Decimal = Decimal("0")
    sizing: Sizing | None = None


@dataclass(frozen=True)
class ExecutionComparison:
    quantity: Decimal
    purchase_cost: Decimal
    net_sale: Decimal
    realized_loss: Decimal
