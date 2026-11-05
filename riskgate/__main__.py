"""python -m riskgate"""
import argparse
import sys
from .evaluator import evaluate
from .jsonio import load
from .models import Status
from .presentation import decision_dict, output
from .scenarios import run_scenarios
from .validation import ValidationError


def main(argv=None):
    parser = argparse.ArgumentParser(description="Laboratório fictício de risco Spot BTC/USDT; não envia ordens.")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--cenario", choices=list("abcdef"), help="Executar cenário isolado; padrão: todos.")
    group.add_argument("--arquivo", help="Avaliar contrato JSON local v1.")
    args = parser.parse_args(argv)
    try:
        if args.arquivo:
            decision = evaluate(*load(args.arquivo))
            output(decision_dict(decision))
            return 0 if decision.status == Status.APPROVED else 2
        output(run_scenarios(args.cenario))
        return 0
    except ValidationError as exc:
        print(f"Erro de validação: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"Falha inesperada: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
