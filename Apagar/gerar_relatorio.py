#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gerador automatizado de Relatórios de Inteligência Política – CE (TSE 2024)
Processa a fila de municípios (Apagar/fila_municipios.txt) e cria
HTML em Apagar/RelatoriosCE/ usando dados das APIs:
  • IBGE (população, área, PIB)
  • TSE (candidatos prefeito e vereadores eleitos)
  • TransfereGov (emendas trans‑fira‑governamentais)
and follows the Crato template (Visão Geral, Contexto Municipal,
Indicadores Sociais, Infraestrutura, Potencial Produtivo e Gargalos Políticos,
Histórico e Referências).
"""

import csv
import json
import re
import sys
import time
import unicodedata
import urllib.parse
import urllib.request
from pathlib import Path

# --------------------------- CONFIGURAÇÕES ---------------------------
BASE = Path("/home/rafael/.openclaw/workspace/Apagar")
FILA = Path(BASE) / "fila_municipios.txt"
CSV_PATH = Path(BASE) / "municipio_tse_ibge.csv"
SAIDA = Path(BASE) / "RelatoriosCE"
SAIDA.mkdir(parents=True, exist_ok=True)

ESTADO = SAIDA / "lote_estado.txt"
ERROS_LOG = Path("/home/rafael/.openclaw/workspace/memory/RelatoriosCE_ERROS.log")

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"}
ELEICAO_ID = 2045202024
AGREGADOS_URL = "https://servicodados.ibge.gov.br/api/v3/agregados"

# --------------------------- FUNÇÕES AUXILIARES ---------------------------
def slug(s: str) -> str:
    """Slug seguro para filename: remove acentos, espaços e caracteres especiais."""
    s = unicodedata.normalize("NFD", str(s))
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"[^A-Za-z0-9]", "", s)

def fetch(url: str, timeout: int = 30):
    """GET request with standard User-Agent."""
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))

def ibge_populacao(ibge_code: str) -> str:
    """Estimated population (most recent year)."""
    url = f"{AGREGADOS_URL}/6579/periodos/-6/variaveis/9324?localities=N6[{ibge_code}]"
    try:
        data = fetch(url)
        series = data[0].get("resultados", [])[0].get("serie", {})
        return str(max(series.keys()) or "0")
    except Exception:
        return "0"

def ibge_area(ibge_code: str) -> str:
    """Territorial area (km²)."""
    url = f"{AGREGADOS_URL}/1301/periodos/-6/variaveis/615?localidades=N6[{ibge_code}]"
    try:
        data = fetch(url)
        return data[0].get("resultados", [])[0].get("serie", {}).get("2010", "0")
    except Exception:
        return "0"

def ibge_pib(ibge_code: str) -> str:
    """PIB (2021) in mil reais."""
    url = f"{AGREGADOS_URL}/5938/periodos/2021/variaveis/37?localidades=N6[{ibge_code}]"
    try:
        data = fetch(url)
        return str(data[0].get("resultados", [])[0].get("serie", {}).get("2021", "0"))
    except Exception:
        return "0"

def tse_candidatos(tse_code: int, cargo: int) -> list:
    """List of candidates (dicts) for the given office."""
    url = f"https://divulgacandcontas.tse.jus.br/divulgacandcontas/rest/v1/candidatura/listar/2024/{tse_code}/{ELEICAO_ID}/{cargo}/candidatos"
    try:
        return fetch(url)
    except Exception:
        return []

def tse_eleito(candidatos: list, form_elected: str = "Eleito") -> list:
    """Filter candidates whose description contains the given status."""
    return [c for c in candidatos if form_elected in (c.get("descricaoTotalizacao") or "")]

def html_escape(text: str) -> str:
    import html
    return html.escape(str(text))

def normalize_name(name: str) -> str:
    """Normalize name for simple comparison."""
    s = unicodedata.normalize("NFD", str(name))
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", "", s).upper()

def fetch_transferegov_emendas(municipio: str) -> list:
    """Fetch TransfereGov emendas for a municipality."""
    q = urllib.parse.urlencode({
        "nome_beneficiario_plano_acao": f"ilike.*{municipio}*",
        "ano_plano_acao": "eq.2024",
        "limit": "50",
        "offset": "0",
    })
    url = f"https://api.transferegov.gestao.gov.br/transferenciasespeciais/plano_acao_especial?{q}"
    try:
        resp = fetch(url)
    except Exception:
        return []
    emendas = []
    target_norm = normalize_name(municipio)
    for r in resp:
        if r.get("uf_beneficiario_plano_acao") != "CE":
            continue
        ben_norm = normalize_name(r.get("nome_beneficiario_plano_acao", ""))
        if ben_norm.startswith("MUNICIPIO DE ".upper()):
            extracted = ben_norm[len("MUNICIPIO DE ".upper()):]
            if extracted.upper() == target_norm:
                valor = r.get("valor_custeio_plano_acao", "0") + r.get("valor_investimento_plano_acao", "0")
                parlamentar = html_escape(r.get("nome_parlamentar_emenda_plano_acao", "—"))
                emendas.append(f"{parlamentar}: R$ {format(float(valor), ',').replace('.', 'X').replace(',', '.').replace('X', ',')}")
    return emendas

# --------------------------- TEMPLATE ---------------------------
def fmt_br_int(v: int) -> str:
    """Format integer as Brazilian currency string."""
    return f"R$ {v:,.0f}".replace(".", "X").replace(",", ".").replace("X", ",")

def render_report(mun_name: str, data: dict):
    """Render HTML using the Crato template (simplified)."""
    def fmt_br(v: int) -> str:
        return fmt_br_int(v)

    slug_name = slug(mun_name)
    html = f"""<!DOCTYPE html>
<html lang="pt-BR"><head>
<meta charset="UTF-8"><title>Relatório de Inteligência PolÍtica – {mun_name}</title>
<style>
body{{font-family:Arial,Helvetica,sans-serif;margin:40px;line-height:1.6;}}
h1{{color:#2e7d32;}}
table{{border-collapse:collapse;width:100%;margin-top:20px;}}
th,td{{border:1px solid #ddd;padding:8px;text-align:left;}}
th{{background:#f2f2f2;}}</style></head><body>
<h1>Relatório de Inteligência PolÍtica – {mun_name}</h1>
<h2>Visão Geral</h2>
<p><strong>Município:</strong> {mun_name}</p>
<p><strong>Estado:</strong> Ceará</p>
<hr>
<h2>Contexto Municipal</h2>
<table>
<tr><th>Fonte</th><th>Informação</th></tr>
<tr><td>População (IBGE est.)</td><td>{data['populacao']}</td></tr>
<tr><td>Densidade demográfica</td><td>{data['densidade']}</td></tr>
<tr><td>Área territorial</td><td>{data['area']}</td></tr>
<tr><td>IBGE Código</td><td>{data['ibge_code']}</td></tr>
<tr><td>TSE Código</td><td>{data['tse_code']}</td></tr>
</table>
<hr>
<h2>Indicadores Sociais</h2>
<table>
<tr><th>Fonte</th><th>Informação</th></tr>
<tr><td>PIB (2021)</td><td>{data['pib']}</td></tr>
</table>
<hr>
<h2>Histórico e Composição Política</h2>
<ul>
<li><strong>Prefeito eleito:</strong> {data['prefeito']}</li>
<li><strong>Vereadores eleitos:</strong> {', '.join(data['vereadores'])}</li>
<li><strong>Emendas municipais (2024):</strong> {data['emendas']}</li>
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
def main():
    if not FILA.exists():
        sys.exit(0)

    # read fila
    with FILA.open(encoding="utf-8") as f:
        fila = [l.strip() for l in f if l.strip()]

    # read CSV for code mapping
    mapping = {}
    with open(CSV_PATH, encoding="latin1") as csv_file:
        reader = csv.DictReader(csv_file, delimiter=';')
        for row in reader:
            mapping[row["NM_MUNICIPIO_TSE"]] = {
                "tse_code": row["CD_MUNICIPIO_TSE"],
                "ibge_code": row["CD_MUNICIPIO_IBGE"]
            }

    concluídos = 0
    total = len(fila)
    estado = {"proximo": fila[0] if fila else None, "concluidos": 0, "total_fila": total}
    ESTADO.write_text(json.dumps(estado), encoding="utf-8")

    for municipio in fila:
        slug_name = slug(municipio)
        html_path = SAIDA / f"{slug_name}.html"
        if html_path.exists():
            continue  # skip already generated

        # ---- IBGE data ----
        info = mapping.get(municipio)
        if not info:
            LOG_ERR(f"Código não encontrado em CSV: {municipio}")
            continue
        tse_code = int(info["tse_code"])
        ibge_code = info["ibge_code"]

        # IBGE data retrieval
        populacao_str = ibge_populacao(ibge_code)
        area_str = ibge_area(ibge_code)
        area_km2 = float(area_str)
        densidade = round(float(populacao_str) / area_km2, 2) if area_km2 else 0
        densidade_fmt = f"{densidade:.2f} hab/km²"
        populacao_fmt = f"{format(int(populacao_str), ',').replace(',', '.').replace('.', ',').replace(' ', '')} habitantes"
        # The above formatting is messy; simplify:
        populacao_fmt = f"{format(int(populacao_str), ',').replace('.', '.').replace(',', '.')} habitantes"

        # TSE prefeito
        prefeito_cands = tse_candidatos(tse_code, 11)
        prefeito_data = None
        for c in prefeito_cands:
            if "Eleito" in c.get("descricaoTotalizacao", ""):
                prefeito_data = c
                break
        prefeito_nome = html_escape(prefeito_data.get("nomeUrna") or "—")
        prefeito_partido = html_escape(prefeito_data.get("partido", {}).get("sigla") or "—"
        prefeito_colig = html_escape(prefeito_data.get("coligacao") or "—") if prefeito_data else "—"

        # TSE vereadores
        vereador_cands = tse_candidatos(tse_code, 13)
        eleitos = tse_eleito(vereador_cands)
        vereadores_fmt = []
        for v in eleitos:
            nome = html_escape(v.get("nomeUrna") or "—")
            partido = html_escape(v.get("partido", {}).get("sigla") or "—")
            forma = html_escape(v.get("descricaoTotalizacao") or "—")
            vereadores_fmt.append(f"{nome} ({partido}) {forma}")
        vereadores_txt = "; ".join(vereadores_fmt)

        # TransfereGov emendas
        emendas = fetch_transferegov_emendas(municipio)
        emendas_txt = "; ".join(emendas) if emendas else ""

        # Assemble data dict
        data = {
            "populacao": populacao_fmt,
            "densidade": densidade_fmt,
            "area": area_str,
            "ibge_code": ibge_code,
            "tse_code": tse_code,
            "prefeito": f"{prefeito_nome} ({prefeito_partido}) {prefeito_colig}",
            "vereadores": vereadores_txt,
            "emendas": emendas_txt,
        }

        # Render and save HTML
        render_report(municipio, data)

        # Update progress
        concluidos += 1
        estado = {"proximo": municipio, "concluidos": concluidos, "total_fila": total}
        ESTADO.write_text(json.dumps(estado), encoding="utf-8")
        print(f"[{concluidos}/{total}] {municipio} → {slug_name}.html")
        time.sleep(0.3)  # polite delay

    LOG_OK(f"Processamento concluído. {concluidos}/{total} relatórios gerados.")

def LOG_OK(msg: str):
    with open(SAIDA / "run_success.log", "a", encoding="utf-8") as f:
        f.write(f"{{\"msg\": {json.dumps(msg)}, \"ts\": \"{time.strftime('%Y-%m-%d %H:%M:%S')}\"}}\n")

def LOG_ERR(msg: str):
    with open(ERROS_LOG, "a", encoding="utf-8") as f:
        f.write(f"{{\"msg\": {json.dumps(msg)}, \"ts\": \"{time.strftime('%Y-%m-%d %H:%M:%S')}\"}}\n")

if __name__ == "__main__":
    main()