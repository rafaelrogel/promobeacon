#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script to generate a single HTML report for municipality 'Cruz' (as test).
This script avoids the previous syntax errors.
"""

import json
import urllib.request
import html

# --- Configurações ---
BASE = "/home/rafael/.openclaw/workspace/Apagar"
FILA_PATH = Path(BASE) / "fila_municipios.txt"
OUT_DIR = Path(BASE) / "RelatoriosCE"
OUT_DIR.mkdir(exist_ok=True)
ELEICAO_ID = 2045202024
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"}

# --------------------------- FUNÇÕES ---------------------------
def fetch(url: str, timeout: int = 30):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))

def ibge_populacao(ibge_code: str) -> str:
    url = f"https://servicodados.ibge.gov.br/api/v3/agregados/6579/periodos/-6/variaveis/9324?localities=N6[{ibge_code}]"
    try:
        data = fetch(url)
        series = data[0].get("resultados", [])[0].get("serie", {})
        return str(max(series.keys()) or "0")
    except Exception:
        return "0"

def ibge_area(ibge_code: str) -> str:
    url = f"https://servicodados.ibge.gov.br/api/v3/agregados/1301/periodos/-6/variaveis/615?localities=N6[{ibge_code}]"
    try:
        data = fetch(url)
        return data[0].get("resultados", [])[0].get("serie", {}).get("2010", "0")
    except Exception:
        return "0"

def tse_candidatos(tse_code: int, cargo: int) -> list:
    url = f"https://divulgacandcontas.tse.jus.br/divulgacandcontas/rest/v1/candidatura/listar/2024/{tse_code}/{ELEICAO_ID}/{cargo}/candidatos"
    try:
        return fetch(url)
    except Exception:
        return []

def tse_eleito(candidatos: list) -> list:
    return [c for c in candidatos if "Eleito" in (c.get("descricaoTotalizacao") or "")]

def html_escape(text: str) -> str:
    import html
    return html.escape(str(text))

def generate_html(mun_name: str, data: dict):
    slug = re.sub(r"[^A-Za-z0-9]", "", unicodedata.normalize("NFD", municipio))
    html = f"""<!DOCTYPE html>
<html lang="pt-BR"><head>
<meta charset="UTF-8"><title>Relatório de Inteligência PolÍtica – {municipio}</title>
<style>
body{{font-family:Arial,Helvetica,sans-serif;margin:40px;line-height:1.6;}}
h1{{color:#2e7d32;}}
table{{border-collapse:collapse;width:100%;margin-top:20px;}}
th,td{{border:1px solid #ddd;padding:8px;text-align:left;}}
th{{background:#f2f2f2;}}</style></head><body>
<h1>Relatório de Inteligência PolÍtica – {municipio}</h1>
<h2>Visão Geral</h2>
<p><strong>Município:</strong> {municipio}</p>
<p><strong>Estado:</strong> Ceará</p>
<hr>
<h2>Contexto Municipal</h2>
<table>
<tr><th>Fonte</th><th>Informação</th></tr>
<tr><td>População (IBGE est.)</td><td>{dados.get('populacao', fin)}</td></tr>
<tr><td>Densidade demográfica</td><td>{dados.get('densidade', fin)}</td></tr>
<tr><td>Área territorial</td><td>{dados.get('area', fin)}</td></tr>
<tr><td>IBGE Código</td><td>{dados.get('ibge_code', fin)}</td></tr>
<tr><td>TSE Código</td><td>{dados.get('tse_code', fin)}</td></tr>
</table>
<hr>
<h2>Indicadores Sociais</h2>
<table>
<tr><th>Fonte</th><th>Informação</th></tr>
<tr><td>PIB (2021)</td><td>{dados.get('pib', fin)}</td></tr>
</table>
<hr>
<h2>Histórico e Composição Política</h2>
<ul>
<li><strong>Prefeito eleito:</strong> {dados.get('prefeito', fin)}</li>
<li><strong>Vereadores eleitos:</strong> {', '.join(dados.get('vereadores', []))}</li>
<li><strong>Emendas municipais (2024):</strong> {dados.get('emendas', fin)}</li>
</ul>
<hr>
<h2>Referências</h2>
<ol>
<li>MCP‑Brasil – TSE DivulgaCandContas 2024.</li>
<li>MCP‑Brasil – IBGE população e área.</li>
<li>MCP‑Brasil – TransfereGov emendas.</li>
</ol>
</body></html>"""
    Path(SAIDA / f"{slug_name}.html").write_text(html, encoding="utf-8")

# --------------------------- MAIN ---------------------------
if __name__ == "__main__":
    # Só para teste rápido: gera relatório de "Cruz"
    Municipio = "Cruz"
    # Dados fictícios (substituir nas próximas iterações)
    dados = {
        "populacao": "31 847 habitantes",
        "densidade": "≈ 95 hab/km²",
        "area": "334,1 km²",
        "ibge_code": "2304251",
        "tse_code": "15890",
        "prefeito": "DERY MUNIZ (PSB)",
        "vereadores": "Ex.: ALLAN BRUNO (PSB)",
        "emendas": "Ex.: André Figueiredo – R$ 800 mil"
    }
    render_report(Municipio, dados)