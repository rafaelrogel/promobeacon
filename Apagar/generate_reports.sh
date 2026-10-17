#!/bin/bash
# Script to generate simple HTML reports for each municipality in Ceará
# Saves HTML files to /home/rafael/.openclaw/workspace/Apagar/

LIST_FILE="municipios.txt"
OUTPUT_DIR="Apagar"

mkdir -p "$OUTPUT_DIR"

while IFS= read -r line; do
  # Extract municipality name: remove leading number and trailing digits (IBGE code)
  name=$(echo "$line" | sed -r 's/^[0-9]+//; s/([0-9]+).*$//' | xargs)
  if [ -z "$name" ]; then
    continue
  fi
  # Create simple HTML report
  html=$(cat <<EOF
<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <title>Relatório de Inteligência PolÍtica – $name (CE)</title>
  <style>
    body {font-family: Arial, sans-serif; margin: 40px; line-height: 1.6;}
    h1 {color: #2e7d32;}
    table {border-collapse: collapse; width: 100%; margin-top: 20px;}
    th, td {border: 1px solid #ddd; padding: 8px; text-align: left;}
    th {background-color: #f2f2f2;}
  </style>
</head>
<body>
  <h1>Relatório de Inteligência PolÍtica – $name (CE)</h1>
  <h2>Visão Geral</h2>
  <p><strong>Município:</strong> $name</p>
  <p><strong>Estado:</strong> Ceará</p>
  <hr>
  <h2>Dados Básicos</h2>
  <table>
    <tr><th>Fonte</th><th>Informação</th></tr>
    <tr><td>População (IBGE)</td><td>[Inserir população]</td></tr>
    <tr><td>Área</td><td>[Inserir área]</td></tr>
    <tr><td>IDH</td><td>[Inserir IDH]</td></tr>
    <tr><td>PIB per capita</td><td>[Inserir valor]</td></tr>
  </table>
  <hr>
  <h2>liderança política</h2>
  <ul>
    <li><strong>Prefeito(a):</strong> [Inserir prefeito]</li>
    <li><strong>Partido:</strong> [Inserir partido]</li>
    <li><strong>Eleição 2024:</strong> [Inserir % de votos]</li>
  </ul>
  <hr>
  <h2>Referências</h2>
  <ol>
    <li>Fonte: Wikipedia – ${name}</li>
  </ol>
</body>
</html>
EOF
)
  # Write HTML file
  echo "$html" > "Apagar/${name}.html"
done < "$LIST_FILE"
echo "Relatórios HTML gerados em $OUTPUT_DIR"