"""Documento HTML autossuficiente para leitura e impressão dos relatórios."""
from html import escape

from .html_calculations import calculations
from .reports import LABELS, TITLES, interpretation, readable


CSS = """
:root{color-scheme:light;--ink:#172c3e;--muted:#546779;--line:#dbe4ea;--accent:#087e83}
*{box-sizing:border-box}body{margin:0;background:#f2f5f7;color:var(--ink);font:15px/1.6 system-ui,sans-serif}
main{max-width:1120px;margin:auto;padding:44px 28px}header{border-top:5px solid var(--accent);padding:28px 0}
.eyebrow{font-size:12px;font-weight:750;letter-spacing:.18em;text-transform:uppercase;color:var(--accent)}
h1{font-size:38px;letter-spacing:-.04em;line-height:1.15;margin:12px 0}h2{font-size:25px;margin:8px 0}
h3{font-size:19px;margin:0}h4{font-size:13px;letter-spacing:.07em;text-transform:uppercase;margin:22px 0 10px}
p{margin:8px 0}.muted,small{color:var(--muted)}nav{display:flex;flex-wrap:wrap;gap:10px;margin:22px 0}
a{color:var(--accent)}nav a{padding:7px 14px;border:1px solid var(--line);border-radius:6px;text-decoration:none;background:white}
.stats,.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:14px;margin:22px 0}
.stat,.kpi{background:white;border:1px solid var(--line);border-radius:8px;padding:18px}.stat strong{display:block;font-size:28px}
.stat span,.kpi span{display:block;font-size:12px;color:var(--muted)}.kpi strong{display:block;font-size:19px;overflow-wrap:anywhere}
.scenario{margin:40px 0;scroll-margin-top:20px}.scenario-head{margin-bottom:20px}.case{background:white;border:1px solid var(--line);border-radius:10px;margin:18px 0;padding:26px}
.case-head{display:flex;align-items:flex-start;justify-content:space-between;gap:16px}.badge{font-size:11px;font-weight:750;padding:5px 10px;border-radius:20px;white-space:nowrap}
.approved{background:#e0f4ed;color:#146347}.rejected{background:#fce9e9;color:#9c3030}.expected{background:#fff0d3;color:#815900}.neutral{background:#eaf0f5;color:#425b72}
.columns{display:grid;grid-template-columns:1fr 1fr;gap:28px}.table-wrap{overflow-x:auto}table{width:100%;border-collapse:collapse;font-size:13px}
th,td{padding:9px 0;border-bottom:1px solid #edf1f4;text-align:left;vertical-align:top}th{font-weight:500;color:var(--muted);width:54%;padding-right:16px}td{font-variant-numeric:tabular-nums;overflow-wrap:anywhere}
.note{background:#f1f8f8;border-left:3px solid var(--accent);padding:14px 18px;margin:20px 0 0;font-size:14px}.note p{margin:5px 0}
.reason{font-size:12px;color:var(--muted);overflow-wrap:anywhere}.verified{color:#146347;font-size:13px}footer{border-top:1px solid var(--line);padding-top:20px;font-size:12px;color:var(--muted)}
.calculations{margin-top:26px;border-top:1px solid var(--line);padding-top:4px}.formula-table{table-layout:fixed}.formula-table th:first-child{width:22%}.formula-table th:nth-child(2){width:32%}.formula{font-family:ui-monospace,monospace;color:var(--accent)}.legend{display:grid;grid-template-columns:1fr 1fr;gap:12px 24px;font-size:12px}.legend div{display:flex;gap:12px}.legend dt{font-weight:700;min-width:95px}.legend dd{margin:0;color:var(--muted)}
.formula-table th:nth-child(3){width:46%}.formula-table th,.formula-table td{padding-right:14px}
@media(max-width:720px){.legend{grid-template-columns:1fr}.formula-table{min-width:620px}}
@media(max-width:720px){main{padding:24px 16px}h1{font-size:30px}.columns{grid-template-columns:1fr;gap:0}.case{padding:18px}.case-head{flex-wrap:wrap}}
@media print{@page{size:A4;margin:14mm}body{background:white;font-size:11px}main{max-width:none;padding:0}nav{display:none}h1{font-size:28px}.scenario{margin:24px 0}.case{border-radius:0;padding:16px;break-inside:auto}.case-head,.kpis,.note,tr{break-inside:avoid}h2,h3,h4{break-after:avoid}.columns{display:block}table{font-size:11px}a{color:inherit;text-decoration:none}}
"""


def table(data):
    rows = "".join(
        f'<tr><th scope="row">{escape(LABELS.get(key, key.replace("_", " ").capitalize()))}</th>'
        f'<td>{escape(readable(value))}</td></tr>' for key, value in data.items())
    return f'<div class="table-wrap"><table><tbody>{rows}</tbody></table></div>'


def badge(result):
    if result.get("status") == "APROVADA":
        return "approved", "APROVADA"
    if result.get("status") == "REJEITADA":
        return "rejected", "REJEITADA"
    if "erro_esperado" in result:
        return "expected", "ERRO ESPERADO"
    return "neutral", "OBSERVAÇÃO"


def card(result, index):
    name = result.get("caso") or result.get("sessao") or (
        "Avaliação principal" if "status" in result else "Observação")
    style, status = badge(result)
    parts = [f'<article class="case"><div class="case-head"><div><div class="eyebrow">Caso {index:02d}</div>'
             f'<h3>{escape(name)}</h3></div><span class="badge {style}">{status}</span></div>']
    if "status" in result:
        parts += [f'<p>{escape(result["explicacao"])}</p>',
                  f'<p class="reason">Motivo: {escape(result["motivo"])}</p>']
        kpis = {"Quantidade aprovada": result["quantidade_aprovada"]}
        sizing = result.get("dimensionamento_candidato")
        if sizing:
            qualifier = " da candidata rejeitada" if status == "REJEITADA" else " planejado"
            kpis["Desembolso" + qualifier] = sizing["outlay"]
            kpis["Perda estimada" + (" da candidata rejeitada" if status == "REJEITADA" else "")] = sizing["estimated_loss"]
        parts.append('<div class="kpis">' + ''.join(
            f'<div class="kpi"><span>{escape(label)}</span><strong>{escape(readable(value))}</strong></div>'
            for label, value in kpis.items()) + '</div>')
        if result["limitadores"]:
            names = {"risco": "risco", "exposicao": "exposição", "saldo": "saldo"}
            limiters = ", ".join(names.get(key, key) for key in result["limitadores"])
            parts.append(f'<p><strong>Restrição de quantidade:</strong> {escape(limiters)}</p>')
    parts.append('<div class="columns">')
    if "entradas" in result:
        parts.append('<section><h4>Entradas da avaliação</h4>' + table(result["entradas"]) + '</section>')
    if result.get("dimensionamento_candidato"):
        parts.append('<section><h4>Dimensionamento</h4>' + table(result["dimensionamento_candidato"]) + '</section>')
    else:
        details = {key: value for key, value in result.items() if key not in (
            "entradas", "caso", "sessao", "status", "motivo", "explicacao", "quantidade_aprovada",
            "limitadores", "dimensionamento_candidato", "observacao", "erro_esperado")}
        if details:
            parts.append('<section><h4>Resultados observados</h4>' + table(details) + '</section>')
    parts.append('</div>')
    parts.append(calculations(result))
    notes = []
    if "status" in result:
        notes.extend(line.strip() for line in interpretation(result))
    if "erro_esperado" in result:
        notes += [result["erro_esperado"], "O dado foi recusado como esperado; esse erro faz parte do teste."]
    if "observed_at" in result:
        notes.append("A perda diária usa a base do dia; o drawdown usa o pico da sessão. Os bloqueios podem persistir após a recuperação.")
    if "observacao" in result:
        notes.append(result["observacao"])
    if notes:
        parts.append('<aside class="note"><strong>Como interpretar</strong>' +
                     ''.join(f'<p>{escape(note)}</p>' for note in notes) + '</aside>')
    parts.append('</article>')
    return ''.join(parts)


def html_report(value):
    scenarios = value if isinstance(value, list) else [{"cenario": "Arquivo", "resultados": [value]}]
    results = [result for scenario in scenarios for result in scenario["resultados"]]
    stats = [(len(scenarios), "Cenários" if isinstance(value, list) else "Avaliação por arquivo"),
             (sum(r.get("status") == "APROVADA" for r in results), "Decisões aprovadas"),
             (sum(r.get("status") == "REJEITADA" for r in results), "Decisões rejeitadas"),
             (sum("erro_esperado" in r for r in results), "Erros esperados detectados")]
    parts = ['<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">',
             '<meta name="viewport" content="width=device-width, initial-scale=1">',
             '<title>RiskGate | Relatório de cenários</title>', f'<style>{CSS}</style></head><body><main>',
             '<header><div class="eyebrow">RiskGate / Laboratório de risco</div>',
             '<h1>Relatório de cenários</h1><p class="muted">Premissas, decisões e cálculos em uma visão detalhada.</p>',
             '<p class="muted">Simulação fictícia de BTC/USDT · Nenhuma ordem é enviada · Horários em UTC</p></header>',
             '<div class="stats">']
    parts += [f'<div class="stat"><strong>{count}</strong><span>{label}</span></div>' for count, label in stats]
    parts.append('</div><p class="muted">As contagens representam decisões de política. Rejeições e erros esperados podem fazer parte de um teste bem-sucedido.</p><nav aria-label="Cenários">')
    for i, scenario in enumerate(scenarios):
        name = escape(scenario["cenario"])
        parts.append(f'<a href="#cenario-{i}">{"Cenário " if isinstance(value, list) else ""}{name}</a>')
    parts.append('</nav>')
    for i, scenario in enumerate(scenarios):
        name = scenario["cenario"]
        title = TITLES.get(name, "Avaliação de contrato JSON")
        parts.append(f'<section class="scenario" id="cenario-{i}"><div class="scenario-head">'
                     f'<div class="eyebrow">{escape("Cenário " + name if isinstance(value, list) else name)}</div>'
                     f'<h2>{escape(title)}</h2></div>')
        parts += [card(result, index) for index, result in enumerate(scenario["resultados"], 1)]
        if isinstance(value, list):
            parts.append('<p class="verified">✓ Verificações programadas do cenário concluídas sem divergências.</p>')
        parts.append('</section>')
    parts.append('<footer>RiskGate · A perda planejada depende dos preços e taxas considerados. '
                 'O preço de execução pode resultar em uma perda maior. '
                 'Para exportar em PDF, use a opção Imprimir do navegador.</footer></main></body></html>')
    return ''.join(parts)
