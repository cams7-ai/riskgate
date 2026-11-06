"""Contratos imutáveis; a validação ocorre na fronteira do avaliador."""
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum


class Position(str, Enum):
    EMPTY = "VAZIA"
    OPEN = "ABERTA"


class Status(str, Enum):
    APPROVED = "APROVADA" # A compra planejada passou pelas regras de validação e limites
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
    APPROVED = "LIMITES_RESPEITADOS" # Código que identifica a razão da aprovação


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
    risk_budget: Decimal # Orçamento máximo de perda planejada. Ex.: 1% do patrimônio de 1.000 USDT é 10 USDT
    loss_per_btc: Decimal # Perda estimada para cada BTC comprado, considerando entrada, saída planejada e ambas as taxas. ex.: 2.198 USDT/BTC
    max_exposure: Decimal # Teto do valor nominal da posição. Ex.: 20% do patrimônio de 1.000 USDT é 200 USDT
    risk_quantity: Decimal # Quantidade máxima permitida pelo orçamento de risco. Ex.: ≈ 0,00454959 BTC
    exposure_quantity: Decimal # Quantidade máxima permitida pelo teto de exposição. Ex.: 0,002 BTC
    balance_quantity: Decimal # Quantidade máxima que o saldo permite comprar, incluindo a taxa de compra. Ex.: ≈ 0,00999001 BTC
    limiters: tuple[str, ...] # O teto de exposição foi a restrição que determinou essa quantidade
    candidate_quantity: Decimal # Menor dos três limites, ajustado ao incremento permitido de quantidade. Ex.: 0,002 BTC
    notional: Decimal # Valor da compra sem taxa: quantidade × preço de entrada. Ex.: 200 USDT
    entry_fee: Decimal # Taxa cobrada na compra. Ex.: 0,20 USDT
    outlay: Decimal # Total necessário para comprar: valor nominal + taxa. Ex.: 200,20 USDT
    planned_proceeds: Decimal # Valor líquido que seria recebido na saída planejada, após a taxa de venda. Ex.: 195,804 USDT
    estimated_loss: Decimal # Diferença entre o total desembolsado e o recebimento planejado. Ex.: 4,396 USDT
    resulting_exposure: Decimal # Exposição nominal total após a compra; neste cenário, não havia exposição anterior. Ex.: 200 USDT


@dataclass(frozen=True)
class Decision:
    status: Status
    reason: Reason
    explanation: str # Descrição da decisão em linguagem simples
    approved_quantity: Decimal = Decimal("0") # Quantidade que o sistema permite comprar. Ex.: 0,002 BTC
    sizing: Sizing | None = None


@dataclass(frozen=True)
class ExecutionComparison:
    quantity: Decimal
    purchase_cost: Decimal
    net_sale: Decimal
    realized_loss: Decimal
