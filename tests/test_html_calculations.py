from dataclasses import replace
from datetime import timedelta
from decimal import Decimal as D
from html import unescape
import unittest

from riskgate.evaluator import evaluate
from riskgate.html_calculations import calculations
from riskgate.metrics import EquitySession
from riskgate.presentation import metrics_dict
from riskgate.scenarios import baseline, evaluation_result, NOW, run_scenarios


class CalculationReportTests(unittest.TestCase):
    def test_risk_sizing_substitution_and_units(self):
        result = run_scenarios('b')[0]['resultados'][0]
        rendered = unescape(calculations(result))
        self.assertIn('R = P × r', rendered)
        self.assertIn('1.000 × 0,01 = 10 USDT', rendered)
        self.assertIn('100.000 × (1 + 0,001) − 98.000 × (1 − 0,001) = 2.198 USDT/BTC', rendered)
        self.assertIn('0,004549 × 100.000 × (1 + 0,001) = 455,3549 USDT', rendered)
        self.assertIn('9,998702 ≤ 10 USDT — atendida', rendered)
        self.assertIn('Legenda dos símbolos', rendered)

    def test_rejected_minimum_and_skipped_calculations(self):
        results = run_scenarios('c')[0]['resultados']
        rendered = unescape(calculations(results[2]))
        self.assertIn('0,000999 ≥ 0,001 BTC — não atendido', rendered)
        self.assertIn('candidata rejeitada', rendered)
        self.assertEqual(calculations(results[1]), '')
        invalid = run_scenarios('d')[0]['resultados'][-1]
        self.assertIn('entradas foram recusadas', calculations(invalid))
        self.assertNotIn('Fórmula', calculations(invalid))

    def test_decimal_correction_is_distinguished_from_initial_floor(self):
        config, snapshot = baseline()
        config = replace(config, buy_fee=D('0'), sell_fee=D('0'), exposure_fraction=D('1'),
                         risk_fraction=D('1'), step=D('1e-28'), min_quantity=D('1e-28'), min_notional=D('0'))
        snapshot = replace(snapshot, equity=D('2'), free_balance=D('2'), entry_price=D('14'), planned_exit=D('1'))
        result = evaluation_result(config, snapshot, evaluate(config, snapshot))
        rendered = unescape(calculations(result))
        self.assertIn('0,1428571428571428571428571429 BTC; q final = 0,1428571428571428571428571428 BTC', rendered)

    def test_metrics_and_missing_daily_base(self):
        metrics = next(r for r in run_scenarios('e')[0]['resultados']
                       if r.get('equity', {}).get('valor') == '990')
        rendered = unescape(calculations(metrics))
        self.assertIn('max(0, (1.000 − 990) ÷ 1.000 × 100) ≈ 1 %', rendered)
        self.assertIn('(1.050 − 990) ÷ 1.050 × 100 ≈ 5,714285', rendered)
        session = EquitySession(D('3'), D('5'))
        session.observe(NOW, D('1000'))
        rendered = unescape(calculations(metrics_dict(session.observe(NOW + timedelta(days=1), D('0')))))
        self.assertIn('Nenhuma divisão foi realizada', rendered)
        self.assertIn('(1.000 − 0) ÷ 1.000 × 100 ≈ 100 %', rendered)

    def test_execution_uses_executed_price_and_compares_budget(self):
        result = run_scenarios('f')[0]['resultados'][0]
        rendered = unescape(calculations(result))
        self.assertIn('0,004549 × 97.000 × (1 − 0,001) = 440,811747 USDT', rendered)
        self.assertIn('14,543153 ≤ 10 USDT — não atendida', rendered)
        self.assertIn('14,543153 − 10 = 4,543153 USDT', rendered)
        self.assertIn('14,543153 − 9,998702 = 4,544451 USDT', rendered)
