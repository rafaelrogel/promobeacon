#!/usr/bin/env bash
# Apoio ao lote de relatórios CE: mostrar próximo município / andamento.
set -euo pipefail
WS="$HOME/.openclaw/workspace"
ESTADO="$WS/Apagar/lote_estado.txt"
FILA="$WS/Apagar/fila_municipios.txt"

case "${1:-status}" in
  status)
    echo "=== Estado do lote ==="
    cat "$ESTADO" 2>/dev/null || echo "(sem estado ainda)"
    echo
    echo "=== Relatórios gerados ==="
    ls "$WS/Apagar/RelatoriosCE/"*.html 2>/dev/null | wc -l
    ;;
  proximo)
    # próximo município = primeiro da fila que ainda não tem relatório
    while IFS= read -r m; do
      [ -z "$m" ] && continue
      f="$WS/Apagar/RelatoriosCE/${m//[^a-zA-Z0-9]/}.html"
      [ -f "$f" ] && continue
      echo "$m"
      exit 0
    done < "$FILA"
    echo "(fila completa)"
    ;;
  *)
    echo "uso: $0 [status|proximo]" >&2; exit 2 ;;
esac
