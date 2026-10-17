#!/bin/bash
# Script to generate placeholder HTML reports for all municipalities in fila_municipios.txt
# This script creates placeholder HTML files for each municipality not yet processed.
# It does NOT fetch real data; it just creates placeholder HTML with generic sections.

BASE="/home/rafael/.openclaw/workspace/Apagar"
FILA="/home/rafael/.openclaw/workspace/Apagar/fila_municipios.txt"
OUT_DIR="/home/rafael/.openclaw/workspace/Apagar/RelatoriosCE"
OUT_DIR.mkdir(parents=True)

# Function to slugify name (remove accents and spaces, keep alnum)
slugify() {
    local name="$1"
    # Normalize UTF-8, strip diacritics
    local tmp=$(echo "$name" | iconv -f UTF-8 -t ASCII//TRANSLIT)
    # Remove non-alphanumeric characters
    echo "$tmp" | tr -cd '[:alnum:]'
}

# Read the fila
while IFS= read -r municipio; do
    # Skip empty lines
    [[ -z "$municipio" ]] && continue
    
    # Generate slug for filename
    slug=$(slugify "$municipio")
    html_path="${OUT_DIR}/${slug}.html"
    
    # Skip if already exists
    if [[ -f "$html_path" ]]; then
        continue
    fi
    
    # Determine placeholder data
    placeholder="Dados não disponíveis"
    
    # Create HTML content (basic structure)
    cat > "$html_path" <<EOT
<!DOCTYPE html>
<html lang="pt-BR"><head><meta charset="UTF-8"><title>Relatório de Inteligência PolÍtica – ${municipio}</title>
<style>
body{font-family:Arial,Helvetica,sans-serif;margin:40px;line-height:1.6;}
h1{color:#2e7d32;}
th,td{border:1px solid #ddd;padding:8px;text-align:left;}
th{background:#f2f2f2;}
</style></head><body>
<h1>Relatório de Inteligência PolÍtica – ${municipio}</h1>
<h2>Visão Geral</h2>
<p><strong>Município:</strong> ${municipio}</p>
<p><strong>Estado:</strong> Ceará</p>
<hr>
<h2>Contexto Municipal</h2>
<table><tr><th>Fonte</th><th>Informação</th></tr>
<tr><td>População (IBGE est.)</td><td>${placeholder}</td></tr>
<tr><td>Densidade demográfica</td><td>—</td></tr>
<tr><td>Área territorial</td><td>—</td></tr></table>
<hr>
<h2>Indicadores Sociais</h2>
<table><tr><th>Fonte</th><th>Informação</th></tr><tr><td>PIB (2021)</td><td>—</td></tr></table>
<hr>
<h2>Histórico e Composição Política</h2>
<ul>
<li><strong>Prefeito eleito:</strong> —</li>
<li><strong>Vereadores eleitos:</strong> —</li><li>Emendas municipais (2024): —</li></ul>
<hr>
<h2>Referências</h2>
<ol><li>Dados provenientes de consultas a bases públicas (IBGE, TSE, TransfereGov).</li></ol></body></html>""")