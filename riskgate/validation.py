"""Validação em tempo de execução e aritmética independente do chamador."""
from datetime import datetime, timezone
from decimal import Context, Decimal, DecimalException, ROUND_HALF_EVEN, localcontext
from functools import wraps


class ValidationError(ValueError):
    """Dados ou configuração inválidos; não é uma rejeição de política."""


def financial(function):
    @wraps(function)
    def wrapped(*args, **kwargs):
        # Um Context novo evita herdar precisão, flags e traps externos.
        with localcontext(Context(prec=28, rounding=ROUND_HALF_EVEN)):
            try:
                return function(*args, **kwargs)
            except DecimalException as exc:
                raise ValidationError("Valores excedem a capacidade aritmética decimal") from exc
    return wrapped


def decimal_value(value, name, *, minimum=None, maximum=None,
                  exclusive_min=False, exclusive_max=False):
    if not isinstance(value, Decimal) or not value.is_finite():
        raise ValidationError(f"{name}: esperado Decimal finito")
    if minimum is not None and (value < minimum or (exclusive_min and value == minimum)):
        raise ValidationError(f"{name}: abaixo do intervalo permitido")
    if maximum is not None and (value > maximum or (exclusive_max and value == maximum)):
        raise ValidationError(f"{name}: acima do intervalo permitido")
    return value


def decimal_string(value, name):
    if type(value) is not str or not value.strip():
        raise ValidationError(f"{name}: esperado decimal como string")
    try:
        result = Decimal(value)
    except (DecimalException, ValueError) as exc:
        raise ValidationError(f"{name}: decimal malformado") from exc
    return decimal_value(result, name)


def boolean(value, name):
    if type(value) is not bool:
        raise ValidationError(f"{name}: esperado booleano")


def utc(value, name):
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValidationError(f"{name}: esperado datetime com fuso")
    return value.astimezone(timezone.utc)


def iso_datetime(value, name):
    if type(value) is not str:
        raise ValidationError(f"{name}: esperado texto ISO com fuso")
    try:
        return utc(datetime.fromisoformat(value), name)
    except ValueError as exc:
        raise ValidationError(f"{name}: data ISO inválida ou sem fuso") from exc
