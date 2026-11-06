"""python -m riskgate"""
import argparse
import sys
from .evaluator import evaluate
from .jsonio import load
from .html_report import html_report
from .models import Status
from .presentation import decision_dict, output
from .reports import text_report
from .scenarios import evaluation_result, run_scenarios
from .validation import ValidationError


def main(argv=None):
    parser = argparse.ArgumentParser(description="Laboratório fictício de risco Spot BTC/USDT; não envia ordens.")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--cenario", choices=list("abcdef"), help="Executar cenário isolado; padrão: todos.")
    group.add_argument("--arquivo", help="Avaliar contrato JSON local v1.")
    parser.add_argument("--formato", choices=("texto", "json", "html"), default="texto",
                        help="Formato da saída; padrão: relatório em texto.")
    args = parser.parse_args(argv)
    try:
        if args.arquivo:
            config, snapshot = load(args.arquivo)
            decision = evaluate(config, snapshot)
            if args.formato == "json":
                output(decision_dict(decision))
            elif args.formato == "html":
                print(html_report(evaluation_result(config, snapshot, decision)))
            else:
                print(text_report(evaluation_result(config, snapshot, decision)))
            return 0 if decision.status == Status.APPROVED else 2
        results = run_scenarios(args.cenario)
        if args.formato == "json":
            output(results)
        elif args.formato == "html":
            print(html_report(results))
        else:
            print(text_report(results))
        return 0
    except ValidationError as exc:
        print(f"Erro de validação: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"Falha inesperada: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
