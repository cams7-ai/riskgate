import copy
from dataclasses import replace
from datetime import timedelta, timezone
from decimal import Decimal as D, getcontext, localcontext, ROUND_UP, Inexact
import unittest

from riskgate import evaluate, Position, Reason, Status, ValidationError
from riskgate.finance import compare_execution
from riskgate.scenarios import baseline, NOW, run_scenarios


class EvaluatorTests(unittest.TestCase):
    def setUp(self):
        self.c, self.s = baseline()

    def test_exact_a_b_c_f(self):
        for fraction, balance, q, outlay, loss, limiter in (
            ("0.20", "1000", "0.002", "200.2", "4.396", "exposicao"),
            ("1", "1000", "0.004549", "455.3549", "9.998702", "risco"),
            ("1", "100", "0.000999", "99.9999", "2.195802", "saldo"),
        ):
            with self.subTest(limiter=limiter):
                d = evaluate(replace(self.c, exposure_fraction=D(fraction)), replace(self.s, free_balance=D(balance)))
                self.assertEqual((d.approved_quantity, d.sizing.outlay, d.sizing.estimated_loss), tuple(map(D, (q, outlay, loss))))
                self.assertEqual(d.sizing.limiters, (limiter,))
        a = evaluate(self.c, self.s).sizing
        self.assertEqual((a.risk_budget, a.loss_per_btc, a.risk_quantity, a.exposure_quantity, a.balance_quantity),
                         (D("10"), D("2198"), D("10") / D("2198"), D("0.002"), D("1000") / D("100100")))
        self.assertEqual((a.notional, a.entry_fee, a.planned_proceeds, a.resulting_exposure),
                         tuple(map(D, ("200", "0.2", "195.804", "200"))))
        f = compare_execution(D("0.004549"), D("100000"), D("97000"), D("0.001"), D("0.001"))
        self.assertEqual((f.purchase_cost, f.net_sale, f.realized_loss), tuple(map(D, ("455.3549", "440.811747", "14.543153"))))

    def test_minima_equality_and_no_increase(self):
        c = replace(self.c, min_quantity=D("0.002"), min_notional=D("200"))
        self.assertEqual(evaluate(c, self.s).status, Status.APPROVED)
        for changed in (replace(c, min_quantity=D("0.002001")), replace(c, min_notional=D("200.01")),
                        replace(c, step=D("1"))):
            d = evaluate(changed, self.s)
            self.assertEqual(d.reason, Reason.MINIMUM)
            self.assertEqual(d.approved_quantity, D("0"))
            self.assertIsNotNone(d.sizing)

    def test_non_power_ten_step(self):
        d = evaluate(replace(self.c, step=D("0.000003")), self.s)
        self.assertEqual(d.approved_quantity, D("0.001998"))
        self.assertEqual(d.approved_quantity % D("0.000003"), 0)

    def test_ties_and_limits_equality(self):
        c = replace(self.c, buy_fee=D("0"), sell_fee=D("0"), risk_fraction=D("0.004"))
        s = replace(self.s, free_balance=D("200"))
        d = evaluate(c, s)
        self.assertEqual(d.sizing.limiters, ("risco", "exposicao", "saldo"))
        self.assertEqual(d.approved_quantity, D("0.002"))
        self.assertEqual(d.sizing.estimated_loss, d.sizing.risk_budget)
        self.assertEqual(d.sizing.outlay, s.free_balance)
        self.assertEqual(d.sizing.resulting_exposure, d.sizing.max_exposure)

    def test_invariants_near_limits(self):
        # Matriz determinística cobrindo todos os limitadores e números recorrentes.
        for step in ("0.000001", "0.000003", "0.000000000000000000000000001"):
            for fraction in ("0.00000001", "0.01", "0.2", "1"):
                for balance in ("0.0000001", "99.99999999999999999999999", "1000"):
                    c = replace(self.c, step=D(step), risk_fraction=D(fraction),
                                min_quantity=D(step), min_notional=D("0"))
                    s = replace(self.s, free_balance=D(balance))
                    d = evaluate(c, s)
                    if d.status == Status.APPROVED:
                        z = d.sizing
                        self.assertLessEqual(z.estimated_loss, z.risk_budget)
                        self.assertLessEqual(d.approved_quantity * z.loss_per_btc, z.risk_budget)
                        self.assertLessEqual(z.outlay, s.free_balance)
                        self.assertLessEqual(z.resulting_exposure, z.max_exposure)
                        self.assertEqual(d.approved_quantity % c.step, 0)

    def test_rounding_correction(self):
        # 2/14 arredonda para cima em 28 dígitos; a multiplicação seguinte excede 2.
        c = replace(self.c, buy_fee=D("0"), sell_fee=D("0"), exposure_fraction=D("1"),
                    risk_fraction=D("1"), step=D("0.0000000000000000000000000001"),
                    min_quantity=D("0.0000000000000000000000000001"), min_notional=D("0"))
        s = replace(self.s, equity=D("2"), free_balance=D("2"), entry_price=D("14"), planned_exit=D("1"))
        d = evaluate(c, s)
        self.assertLessEqual(d.sizing.outlay, D("2"))
        self.assertEqual(d.approved_quantity, D("0.1428571428571428571428571428"))

    def test_precedence_and_immutability(self):
        # Partir de todas as condições, retirar uma a uma seguindo a precedência.
        s = replace(self.s, manual_blocked=True, unknown_order=True, daily_blocked=True,
                    entry_price=None, price_at=None, pending_intent=True, position=Position.OPEN,
                    exposure=D("200"), free_balance=D("0"))
        steps = [(Reason.MANUAL, {"manual_blocked": False}),
                 (Reason.UNKNOWN_ORDER, {"unknown_order": False}),
                 (Reason.LIMIT, {"daily_blocked": False}),
                 (Reason.MISSING_PRICE, {"entry_price": D("100000"), "price_at": NOW-timedelta(seconds=61)}),
                 (Reason.STALE_PRICE, {"price_at": NOW}),
                 (Reason.PENDING, {"pending_intent": False}),
                 (Reason.POSITION, {"position": Position.EMPTY}),
                 (Reason.EXPOSURE, {"exposure": D("0")}),
                 (Reason.BALANCE, {"free_balance": D("1000")})]
        for reason, changes in steps:
            before = copy.deepcopy(s)
            d = evaluate(self.c, s)
            self.assertEqual(d.reason, reason)
            self.assertEqual(s, before)
            self.assertEqual(d.approved_quantity, 0)
            self.assertIsNone(d.sizing)
            s = replace(s, **changes)
        self.assertEqual(evaluate(self.c, s).status, Status.APPROVED)

    def test_validation_before_rules(self):
        s = replace(self.s, manual_blocked=True, equity=D("NaN"))
        with self.assertRaises(ValidationError):
            evaluate(self.c, s)
        self.assertTrue(s.equity.is_nan())

    def test_bad_numbers_types_and_ranges(self):
        for field in ("equity", "free_balance", "exposure", "entry_price", "planned_exit"):
            for value in (D("NaN"), D("sNaN"), D("Infinity"), D("-Infinity"), D("-1"), "100", 100, True):
                with self.subTest(field=field, value=str(value)), self.assertRaises(ValidationError):
                    evaluate(self.c, replace(self.s, **{field: value}))
        for field in ("buy_fee", "sell_fee", "risk_fraction", "exposure_fraction", "step", "min_quantity", "min_notional", "max_price_age_seconds"):
            for value in (D("NaN"), D("-1"), "1", True):
                with self.subTest(field=field), self.assertRaises(ValidationError):
                    evaluate(replace(self.c, **{field: value}), self.s)
        for field in ("buy_fee", "sell_fee"):
            with self.assertRaises(ValidationError):
                evaluate(replace(self.c, **{field: D("1")}), self.s)
        for field in ("risk_fraction", "exposure_fraction", "step", "min_quantity", "max_price_age_seconds"):
            with self.assertRaises(ValidationError):
                evaluate(replace(self.c, **{field: D("0")}), self.s)
        for field in ("pending_intent", "unknown_order", "daily_blocked", "drawdown_blocked", "manual_blocked"):
            with self.assertRaises(ValidationError):
                evaluate(self.c, replace(self.s, **{field: 1}))
        with self.assertRaises(ValidationError):
            evaluate(self.c, replace(self.s, position="VAZIA"))
        for price in ("98000", "97000", "0"):
            with self.assertRaises(ValidationError):
                evaluate(self.c, replace(self.s, entry_price=D(price)))
        for change in ({"exposure": D("1")}, {"equity": D("0")}, {"planned_exit": D("0")}):
            with self.assertRaises(ValidationError):
                evaluate(self.c, replace(self.s, **change))

    def test_time_boundary_timezone_and_clock(self):
        for delta, reason in ((timedelta(seconds=60), Reason.APPROVED),
                              (timedelta(seconds=60, microseconds=1), Reason.STALE_PRICE)):
            self.assertEqual(evaluate(self.c, replace(self.s, price_at=NOW-delta)).reason, reason)
        offset = timezone(timedelta(hours=-3))
        self.assertEqual(evaluate(self.c, replace(self.s, price_at=NOW.astimezone(offset))), evaluate(self.c, self.s))
        for changes in ({"price_at": NOW+timedelta(microseconds=1)},
                        {"price_at": NOW.replace(tzinfo=None)}, {"evaluated_at": NOW.replace(tzinfo=None)}):
            with self.assertRaises(ValidationError):
                evaluate(self.c, replace(self.s, **changes))
        self.assertEqual(evaluate(self.c, self.s, clock=lambda: NOW+timedelta(seconds=61)).reason, Reason.STALE_PRICE)
        self.assertEqual(self.s.evaluated_at, NOW)

    def test_external_decimal_context(self):
        expected = evaluate(self.c, self.s)
        for precision in (3, 9, 50):
            with localcontext() as context:
                context.prec, context.rounding = precision, ROUND_UP
                context.traps[Inexact] = True
                before = context.copy()
                self.assertEqual(evaluate(self.c, self.s), expected)
                self.assertEqual(context.prec, before.prec)
                self.assertEqual(context.rounding, before.rounding)
                self.assertEqual(context.traps, before.traps)
                self.assertEqual(context.flags, before.flags)

    def test_all_scenarios(self):
        self.assertEqual([x['cenario'] for x in run_scenarios()], list('ABCDEF'))


if __name__ == '__main__':
    unittest.main()
