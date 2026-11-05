"""Apresentação JSON com unidades; cálculos não imprimem mensagens."""
from dataclasses import asdict
from datetime import datetime
from decimal import Decimal
from enum import Enum
import json
from .models import Decision


SIZING_UNITS = {
    "risk_budget": "USDT", "loss_per_btc": "USDT/BTC", "max_exposure": "USDT",
    "risk_quantity": "BTC", "exposure_quantity": "BTC", "balance_quantity": "BTC",
    "candidate_quantity": "BTC", "notional": "USDT", "entry_fee": "USDT",
    "outlay": "USDT", "planned_proceeds": "USDT", "estimated_loss": "USDT",
    "resulting_exposure": "USDT",
}


def measured(value, unit):
    return None if value is None else {"valor": str(value), "unidade": unit}


def decision_dict(decision: Decision):
    sizing = None
    if decision.sizing is not None:
        sizing = {name: measured(getattr(decision.sizing, name), unit)
                  for name, unit in SIZING_UNITS.items()}
    return {
        "status": decision.status.value, "motivo": decision.reason.value,
        "explicacao": decision.explanation,
        "quantidade_aprovada": measured(decision.approved_quantity, "BTC"),
        "limitadores": [] if decision.sizing is None else list(decision.sizing.limiters),
        "dimensionamento_candidato": sizing,
    }


def metrics_dict(metrics):
    result = asdict(metrics)
    for name in ("equity", "daily_base", "peak"):
        result[name] = measured(result[name], "USDT")
    for name in ("daily_loss_percent", "drawdown_percent"):
        result[name] = measured(result[name], "%")
    result["base_diaria_parcial"] = (metrics.daily_base_at is None or any((
        metrics.daily_base_at.hour, metrics.daily_base_at.minute,
        metrics.daily_base_at.second, metrics.daily_base_at.microsecond)))
    return result


def _default(value):
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Decimal):
        return str(value)
    raise TypeError(f"Não serializável: {type(value)}")


def output(value):
    print(json.dumps(value, default=_default, ensure_ascii=False, indent=2))
