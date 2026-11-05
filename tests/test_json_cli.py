import json
from pathlib import Path
import subprocess
import sys
import unittest
from riskgate.jsonio import load, loads
from riskgate import ValidationError, evaluate, Status
from riskgate.presentation import decision_dict

ROOT = Path(__file__).resolve().parents[1]


class JsonTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((ROOT / 'data/exemplos/avaliacao.json').read_text())

    def test_valid_fixture(self):
        c, s = loads(json.dumps(self.data))
        self.assertEqual(evaluate(c, s).status, Status.APPROVED)
        self.assertEqual(s.price_at.utcoffset().days, 0)

    def test_malformed_duplicate_constants(self):
        for text in ('{', '[]', 'null', '{"a":1,"a":2}',
                     '{"schema_version":NaN}', '{"schema_version":Infinity}',
                     '{"schema_version":-Infinity}',
                     json.dumps(self.data).replace('"buy_fee": "0.001"', '"buy_fee":"0.001","buy_fee":"0.001"')):
            with self.subTest(text=text[:40]), self.assertRaises(ValidationError):
                loads(text)

    def test_schema_version_and_fields(self):
        for value in (True, False, "1", 1.0, 2, None):
            self.data['schema_version'] = value
            with self.assertRaises(ValidationError):
                loads(json.dumps(self.data))
        self.data['schema_version'] = 1
        for target in (self.data, self.data['config'], self.data['snapshot']):
            key = next(iter(target))
            saved = target.pop(key)
            with self.assertRaises(ValidationError):
                loads(json.dumps(self.data))
            target[key] = saved
            target['unexpected'] = 1
            with self.assertRaises(ValidationError):
                loads(json.dumps(self.data))
            del target['unexpected']

    def test_decimal_strings_and_boolean_types(self):
        for field in self.data['config']:
            original = self.data['config'][field]
            for bad in ('NaN', 'sNaN', 'Infinity', '', 'abc', True, 1, 0.1, None):
                self.data['config'][field] = bad
                with self.subTest(field=field, bad=bad), self.assertRaises(ValidationError):
                    loads(json.dumps(self.data))
            self.data['config'][field] = original
        for field in ('manual_blocked', 'pending_intent', 'daily_blocked', 'drawdown_blocked', 'unknown_order'):
            self.data['snapshot'][field] = 0
            with self.assertRaises(ValidationError):
                loads(json.dumps(self.data))
            self.data['snapshot'][field] = False
        for field in ('evaluated_at', 'price_at'):
            original = self.data['snapshot'][field]
            for bad in ('2026-01-15T12:00:00', 'invalid', 1):
                self.data['snapshot'][field] = bad
                with self.assertRaises(ValidationError):
                    loads(json.dumps(self.data))
            self.data['snapshot'][field] = original
        self.data['snapshot']['position'] = 'LONG'
        with self.assertRaises(ValidationError):
            loads(json.dumps(self.data))

    def test_missing_price_and_null_output(self):
        self.data['snapshot']['entry_price'] = None
        self.data['snapshot']['price_at'] = None
        d = evaluate(*loads(json.dumps(self.data)))
        rendered = decision_dict(d)
        self.assertIsNone(rendered['dimensionamento_candidato'])
        self.assertEqual(rendered['quantidade_aprovada'], {'valor': '0', 'unidade': 'BTC'})

    def test_missing_file(self):
        with self.assertRaises(ValidationError):
            load(ROOT / 'data/exemplos/nao-existe.json')


class CliTests(unittest.TestCase):
    def run_cli(self, *args):
        return subprocess.run([sys.executable, '-m', 'riskgate', *args], cwd=ROOT,
                              capture_output=True, text=True, check=False)

    def test_all_and_individual_scenarios(self):
        all_result = self.run_cli()
        self.assertEqual(all_result.returncode, 0, all_result.stderr)
        combined = json.loads(all_result.stdout)
        self.assertEqual([s['cenario'] for s in combined], list('ABCDEF'))
        for i, name in enumerate('abcdef'):
            result = self.run_cli('--cenario', name)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout), [combined[i]])

    def test_help(self):
        result = self.run_cli('--help')
        self.assertEqual(result.returncode, 0)
        self.assertIn('--arquivo', result.stdout)
        self.assertIn('--cenario', result.stdout)

    def test_file_exit_codes(self):
        for fixture, expected in (('avaliacao', 0), ('rejeitada', 2), ('invalida', 1), ('nao-existe', 1)):
            result = self.run_cli('--arquivo', f'data/exemplos/{fixture}.json')
            self.assertEqual(result.returncode, expected, result.stderr)
            if expected == 1:
                self.assertIn('Erro de validação:', result.stderr)
            else:
                self.assertEqual(json.loads(result.stdout)['status'], 'APROVADA' if expected == 0 else 'REJEITADA')
