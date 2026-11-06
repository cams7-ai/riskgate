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
        all_result = self.run_cli('--formato', 'json')
        self.assertEqual(all_result.returncode, 0, all_result.stderr)
        combined = json.loads(all_result.stdout)
        self.assertEqual([s['cenario'] for s in combined], list('ABCDEF'))
        for i, name in enumerate('abcdef'):
            result = self.run_cli('--cenario', name, '--formato', 'json')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout), [combined[i]])

    def test_help(self):
        result = self.run_cli('--help')
        self.assertEqual(result.returncode, 0)
        self.assertIn('--arquivo', result.stdout)
        self.assertIn('--cenario', result.stdout)
        self.assertIn('--formato', result.stdout)

    def test_text_reports_for_all_scenarios(self):
        for name in 'abcdef':
            with self.subTest(scenario=name):
                result = self.run_cli('--cenario', name)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn(f'CENÁRIO {name.upper()}', result.stdout)
                self.assertIn('Verificações programadas do cenário: concluídas sem divergências.', result.stdout)
                self.assertNotIn('"valor":', result.stdout)

    def test_html_reports_for_all_scenarios(self):
        from html.parser import HTMLParser

        class ReportParser(HTMLParser):
            def __init__(self):
                super().__init__()
                self.tables = 0
                self.links = []
                self.ids = set()

            def handle_starttag(self, tag, attrs):
                attrs = dict(attrs)
                self.tables += tag == 'table'
                if tag == 'a':
                    self.links.append(attrs.get('href', ''))
                if 'id' in attrs:
                    self.ids.add(attrs['id'])

        for args in ((), *(('--cenario', name) for name in 'abcdef')):
            with self.subTest(args=args):
                result = self.run_cli(*args, '--formato', 'html')
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertTrue(result.stdout.startswith('<!doctype html>'))
                parser = ReportParser()
                parser.feed(result.stdout)
                self.assertGreater(parser.tables, 0)
                self.assertTrue(all(link.startswith('#') and link[1:] in parser.ids
                                    for link in parser.links))
                self.assertNotIn('<script', result.stdout)
                self.assertIn('@media print', result.stdout)

    def test_html_file_rejection_and_escaping(self):
        from riskgate.html_report import html_report

        result = self.run_cli('--arquivo', 'data/exemplos/rejeitada.json', '--formato', 'html')
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn('REJEITADA', result.stdout)
        self.assertNotIn('Verificações programadas do cenário concluídas', result.stdout)
        html = html_report([{'cenario': 'D', 'resultados': [
            {'caso': '<script>alert(1)</script>', 'erro_esperado': '<img src=x onerror=alert(1)>'}
        ]}])
        self.assertNotIn('<script>', html)
        self.assertNotIn('<img ', html)
        self.assertIn('&lt;script&gt;', html)

    def test_html_rejected_candidate_is_identified(self):
        result = self.run_cli('--cenario', 'c', '--formato', 'html')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('Desembolso da candidata rejeitada', result.stdout)
        self.assertIn('99,9999 USDT', result.stdout)
        self.assertIn('O dimensionamento não foi realizado', result.stdout)

    def test_text_report_rejections_and_calculations(self):
        result = self.run_cli('--cenario', 'c')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('Desembolso total: 99,9999 USDT', result.stdout)
        self.assertIn('Perda estimada: 2,195802 USDT', result.stdout)
        self.assertIn('Saldo livre após a compra planejada: 0,0001 USDT', result.stdout)
        self.assertIn('O dimensionamento não foi realizado', result.stdout)
        self.assertIn('candidata rejeitada', result.stdout)
        self.assertEqual(result.stdout.count('Quantidade aprovada: 0 BTC'), 2)

    def test_text_file_exit_codes(self):
        for fixture, expected in (('avaliacao', 0), ('rejeitada', 2)):
            with self.subTest(fixture=fixture):
                result = self.run_cli('--arquivo', f'data/exemplos/{fixture}.json')
                self.assertEqual(result.returncode, expected, result.stderr)
                self.assertIn('RISKGATE — RELATÓRIO DETALHADO', result.stdout)
                self.assertIn('Entradas:', result.stdout)

    def test_file_exit_codes(self):
        for fixture, expected in (('avaliacao', 0), ('rejeitada', 2), ('invalida', 1), ('nao-existe', 1)):
            result = self.run_cli('--arquivo', f'data/exemplos/{fixture}.json', '--formato', 'json')
            self.assertEqual(result.returncode, expected, result.stderr)
            if expected == 1:
                self.assertIn('Erro de validação:', result.stderr)
            else:
                self.assertEqual(json.loads(result.stdout)['status'], 'APROVADA' if expected == 0 else 'REJEITADA')
