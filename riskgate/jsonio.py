"""Contrato JSON v1 estrito; a fronteira financeira usa somente Decimal."""
from dataclasses import fields
import json
from pathlib import Path
from .evaluator import validate
from .models import Config, Snapshot, Position
from .validation import ValidationError, boolean, decimal_string, iso_datetime


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValidationError(f"Chave duplicada: {key}")
        result[key] = value
    return result


def _constant(value):
    raise ValidationError(f"Constante JSON não permitida: {value}")


def _keys(value, expected, name):
    if type(value) is not dict:
        raise ValidationError(f"{name}: esperado objeto JSON")
    missing, extra = set(expected) - value.keys(), value.keys() - set(expected)
    if missing or extra:
        raise ValidationError(f"{name}: campos ausentes={sorted(missing)}, inesperados={sorted(extra)}")


def loads(text: str) -> tuple[Config, Snapshot]:
    try:
        data = json.loads(text, object_pairs_hook=_pairs, parse_constant=_constant)
    except (ValueError, TypeError, RecursionError) as exc:
        raise ValidationError(f"JSON inválido: {exc}") from exc
    _keys(data, {"schema_version", "config", "snapshot"}, "raiz")
    if type(data["schema_version"]) is not int or data["schema_version"] != 1:
        raise ValidationError("schema_version deve ser inteiro 1")
    _keys(data["config"], {f.name for f in fields(Config)}, "config")
    _keys(data["snapshot"], {f.name for f in fields(Snapshot)}, "snapshot")
    config = Config(**{key: decimal_string(value, key) for key, value in data["config"].items()})
    source = data["snapshot"]
    values = {}
    for name in ("equity", "free_balance", "exposure", "planned_exit"):
        values[name] = decimal_string(source[name], name)
    values["entry_price"] = None if source["entry_price"] is None else decimal_string(source["entry_price"], "entry_price")
    values["price_at"] = None if source["price_at"] is None else iso_datetime(source["price_at"], "price_at")
    values["evaluated_at"] = iso_datetime(source["evaluated_at"], "evaluated_at")
    try:
        values["position"] = Position(source["position"])
    except (ValueError, TypeError) as exc:
        raise ValidationError("position deve ser VAZIA ou ABERTA") from exc
    for name in ("pending_intent", "unknown_order", "daily_blocked", "drawdown_blocked", "manual_blocked"):
        boolean(source[name], name)
        values[name] = source[name]
    snapshot = validate(config, Snapshot(**values))
    return config, snapshot


def load(path: str | Path) -> tuple[Config, Snapshot]:
    try:
        text = Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise ValidationError(f"Não foi possível ler arquivo: {exc}") from exc
    return loads(text)
