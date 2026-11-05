from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal as D, localcontext, Inexact
import unittest
from riskgate import EquitySession, evaluate, Position, Reason, ValidationError, position_actions
from riskgate.scenarios import NOW, baseline


class MetricsTests(unittest.TestCase):
    def test_drawdown_latched_across_days(self):
        s = EquitySession(D("3"), D("5"))
        for i, value in enumerate(("1000", "1050", "990")):
            m = s.observe(NOW+timedelta(hours=i), D(value))
        self.assertEqual(m.daily_loss_percent, D("1"))
        self.assertEqual(m.drawdown_percent, D("60") / D("1050") * 100)
        self.assertTrue(m.drawdown_blocked)
        self.assertFalse(m.daily_blocked)
        self.assertTrue(s.observe(NOW+timedelta(hours=3), D("1020")).drawdown_blocked)
        m = s.observe(NOW+timedelta(days=1), D("1100"))
        self.assertTrue(m.drawdown_blocked)
        self.assertEqual(m.peak, D("1100"))
        self.assertEqual(m.drawdown_percent, 0)
        fresh = EquitySession(D("3"), D("5"))
        self.assertFalse(fresh.observe(m.observed_at, m.equity).drawdown_blocked)

    def test_daily_equality_recovery_and_utc_midnight(self):
        session = EquitySession(D("3"), D("20"))
        # 20:00 -03 = 23:00 UTC; 21:00 -03 = próximo dia UTC.
        tz = timezone(timedelta(hours=-3))
        t = datetime(2026, 1, 15, 20, tzinfo=tz)
        session.observe(t, D("1000"))
        m = session.observe(t+timedelta(minutes=10), D("970"))
        self.assertEqual(m.daily_loss_percent, D("3"))
        self.assertTrue(m.daily_blocked)
        self.assertFalse(m.drawdown_blocked)
        m = session.observe(t+timedelta(minutes=20), D("1000"))
        self.assertTrue(m.daily_blocked)
        m = session.observe(t+timedelta(hours=1), D("990"))
        self.assertFalse(m.daily_blocked)
        self.assertEqual(m.daily_base, D("990"))
        self.assertEqual(m.daily_base_at.hour, 0)
        self.assertEqual(m.peak, D("1000"))

    def test_zero_and_unavailable_daily_base(self):
        s = EquitySession(D("3"), D("20"))
        with self.assertRaises(ValidationError):
            s.observe(NOW, D("0"))
        self.assertIsNone(s.current)
        s.observe(NOW, D("1000"))
        m = s.observe(NOW+timedelta(days=1), D("0"))
        self.assertEqual(m.drawdown_percent, D("100"))
        self.assertIsNone(m.daily_base)
        self.assertIsNone(m.daily_loss_percent)
        self.assertTrue(m.daily_blocked and m.drawdown_blocked)
        m = s.observe(NOW+timedelta(days=1, hours=1), D("100"))
        self.assertEqual(m.daily_base, D("100"))
        self.assertTrue(m.daily_blocked and m.drawdown_blocked)

    def test_duplicate_conflict_order_and_bad_data_are_atomic(self):
        s = EquitySession(D("3"), D("5"))
        m = s.observe(NOW, D("1000"))
        self.assertIs(s.observe(NOW, D("1000")), m)
        for t, value in ((NOW, D("1001")), (NOW-timedelta(seconds=1), D("1000")),
                         (NOW+timedelta(seconds=1), D("-1")), (NOW, D("NaN")),
                         (NOW.replace(tzinfo=None), D("1000")), (NOW, 1000), (NOW, True)):
            with self.assertRaises(ValidationError):
                s.observe(t, value)
            self.assertIs(s.current, m)
        for value in (D("0"), D("101"), D("NaN"), True):
            with self.assertRaises(ValidationError):
                EquitySession(value, D("5"))

    def test_inputs_normalized_and_context_preserved(self):
        expected = EquitySession(D("3"), D("5"))
        expected.observe(NOW, D("1000"))
        wanted = expected.observe(NOW+timedelta(hours=1), D("970"))
        for precision in (3, 50):
            with localcontext() as context:
                context.prec = precision
                context.traps[Inexact] = True
                before = context.copy()
                s = EquitySession(D("3"), D("5"))
                s.observe(NOW, D("1000"))
                self.assertEqual(s.observe(NOW+timedelta(hours=1), D("970")), wanted)
                self.assertEqual(context.flags, before.flags)
                self.assertEqual(context.prec, precision)

    def test_entry_block_does_not_disable_exit_or_monitoring(self):
        session = EquitySession(D("3"), D("5"))
        session.observe(NOW, D("1000"))
        m = session.observe(NOW+timedelta(hours=1), D("900"))
        c, s = baseline()
        s = replace(s, daily_blocked=m.daily_blocked, drawdown_blocked=m.drawdown_blocked,
                    position=Position.OPEN, pending_intent=True)
        self.assertEqual(evaluate(c, s).reason, Reason.LIMIT)
        self.assertEqual(position_actions(s.position), {
            "acompanhamento_permitido": True, "solicitacao_ficticia_saida_permitida": True})
        self.assertTrue(s.pending_intent)
        self.assertEqual(s.position, Position.OPEN)
        self.assertFalse(position_actions(Position.EMPTY)["solicitacao_ficticia_saida_permitida"])
