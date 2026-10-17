# BATCH_GUIDE.md – Instruções completas para o lote de relatórios de Inteligência Política – Ceará

## Contexto
O objetivo é gerar, de forma autônoma e sem intervenção humana, relatórios de Inteligência Política para **todos os municípios do Ceará** publicados no arquivo `Apagar/fila_municipios.txt`. Esses relatórios seguem um modelo padronizado (baseado em `Crato.html`) e contêm:

- Visão Geral (população, área, densidade, IDHM, PIB, localização)
- Contexto Municipal (governador, prefeito, eleitos, emendas Pix)
- Infraestrutura e Serviços Básicos (água, esgoto, banda larga)
- Potencial Produtivo / Gargalos
- Histórico e Composição Política
- Referências (IBGE, TransfereGov, TSE, Wikipedia)

## Saída esperada
Cada relatório deve ser salvo em:  
```
Apagar/RelatoriosCE/<MUNICIPIO>.html
```
onde `<MUNICIPIO>` deve ter **acentos removidos** e **espaços substituídos por ""** (ex: "Vara_Ze.html", "Crato.html").

## Pipeline de dados
Para **cada município** repetir na ordem da fila:

1. **Buscar códigos (TSE ↔ IBGE)**
   - Abra `Apagar/municipio_tse_ibge.csv` (encoding latin-1)
   - Procure a linha onde `NM_MUNICIPIO_IBGE` corresponde ao nome do município (case-insensitive, match substring)
   - Extraia:
     - `CD_MUNICIPIO_TSE` → código_TSE (5‑digitos)
     - `CD_MUNICIPIO_IBGE` → código_IBGE (7‑digitos)
   - **Importante:** o CSV usa `;` como delimitador.

2. **Coletar dados do IBGE**
   - Use `mcp_probe.py ibge_consultar_agregado` com parâmetros:
     ```json
     {
       "indicador": "populacao",
       "nivel": "municipio",
       "localidade": "<IBGE>"
     }
     ```
   - Obrigatório agregarador: "populacao", "area_territorial", "pib", "densidade".
   - Se o IBGE API estiver fora do ar, use a Wikipedia como fallback (ex.: página do município em vi.wikipedia.org ou pt.wikipedia.org).
   - Salvem:
     - População (estimada)
     - Área (km²)
     - Densidade
     - IDHM (disponível na página da Wiki ou via API de IDHM se existir)
     - PIB (se disponível)

3. **Obter resultados eleições 2024**
   - Use `tse_listar_candidatos` com:
     ```json
     {
       "ano": 2024,
       "municipio": "<TSE>",
       "eleicao_id": "2045202024",
       "cargo": 11
     }
     ```
     → Votação do prefeito.
   - Use `tse_resultado_eleicao` com:
     ```json
     {
       "ano": 2024,
       "municipio": "<TSE>",
       "eleicao_id": "2045202024",
       "cargo": 11
     }
     ```
     → Resultado final (eleito ou não) e % do 1.º turno.
   - Use `tse_listar_candidatos` com `cargo": 13` para lista de vereadores.

4. **Emendas Pix**
   - Use `transferegov_emendas_por_municipio` com:
     ```json
     {
       "ano": 2024,
       "nome_municipio": "<Nome do município>"
     }
     ```
   - O resultado é uma lista de emendas com:
     - Parlamentar
     - Valor
     - Beneficiário (contém o nome do município, mas pode aparecer com variações como "MUNICIPIO DE BELLA CRUZ")
   - Filtrar apenas as linhas cujo `beneficiario` contenha **exatamente** o nome do município (case-insensitive) **e** a UF seja CE.
   - Se houver paginação (pagina=2, etc.), continue até uma página sem resultados ou até um limite razoável (ex.: até valores > 0 desaparecem).
   - Salve como lista em viñtura no relatório.

5. **Template**
   - Ler exemplos já gerados: `Apagar/RelatoriosCE/Crato.html` (ou `Caririacu.html`).
   - Copiar a estructura, substituir:
     - `<Nome>` → nome do município (sem acentos)
     - `<Populacao>`, `<Area>`, `<Densidade>`, `<PixEl>` etc.
     - `<Prefeito>` → nome eleito com % do 1.º turno
     - `<PrefeitoPartido>` → sigla do partido
     - `<CdemVereadores>` → lista de vereadores (nome + partido + votação)
     - `<EmendasPix>` → tabela das emendas com parlamentares e valores
     - `<Gargalos>`, `<Referencias>` etc. conforme modelo original.
   - Certifique‑se de manter o HTML bem‑formado e **use CR/LF Unix** (não Windows).
   - Nome do arquivo: `<Municipio>.html` → sem acentos, espaços vazios, somente alfanumérico + `_` como separador.

6. **Progresso e checkpoint**
   - Após **cada** município concluído:
     - Append a `Apagar/RelatoriosCE/PROGRESSO.md` linha no formato:
       ```
       • <Municipio> (✓) – <data> – [(X) de (Y)]
       ```
       onde X = número de concluídos até então, Y = total da fila original.
     - Append a resumo ao final de `memory/2026-08-04.md` (até 2 linhas, contendo “Lote CE: X/X concluídos”).
     - Atualizar `Apagar/lote_estado.txt`:
       - `proximo: <Próximo_Municipio>`
       - `concluidos: <novos>`
       - Incrementar total concluídos.
   - **Never terminate** a município por erro: logue o problema (ex.: “Erro ao buscar IBGE”), registre no `memory/RelatoriosCE_ERROS.log` e continue com o próximo.

7. **Fallbacks e resiliência**
   - Se a consulta ao IBGE retornar erro ou ficar sem resposta após 2 tentativas (timeout), usar dados da Wikipedia (população 2025, densidade, área, história). Certifique‑se de atribuir nota “WIKI‑Fallback”.
   - Se o relatório não puder ser gerado por qualquer motivo (ex.: falta de dados de vereadores, dados faltantes), crie um relatório **simplificado** contendo apenas as seções “Visão Geral” e “Referências”, além duma nota de erro. Ainda assim salve o HTML.
   - Não paro o lote por tentativa falida. Sempre siga para o próximo município.

8. **Comunicação**
   - O **único motivo** para gerar texto adicional fora do HTML é ao final de todo o lote: gerar um resumo curto em 1‑2 linhas informando “Concluído: X/X relatórios gerados” e enviá‑lo como **MEDIA:prog.txt** (arquivo de texto simples).
   - Cada Relatório HTML deve ser anexado usando **MEDIA:**<caminho> numa linha própria antes do texto de confirmação (como nas sessões de relatório únicas anteriores).

9. **Ferramentas disponíveis**
   - `exec` → rodar comandos shell no host.
   - `read` → ler arquivos textuais (CSV, HTML modelo, etc.).
   - `write` → escrever arquivos textuais (HTML, estado, progresso).
   - `web_search` → caso algum dado esteja incompleto (ex.: PIB da Wiki).
   - `mcp_probe.py` → via `exec` rodar:
     ```
     cd /home/rafael/.openclaw/workspace/MCP-Brasil && python3 scripts/mcp_probe.py call <tool> '<json>'' 
     ```
   - O probe retorna JSON/Pythonish, mas o parse deve ser feito manualmente (usar `python3 - <<EOF` se necessário).

10. **Instalações de código**
    - Todos os scripts PHP/Python devem usar o folheto de codificação UTF‑8, mas conforme o CSV está em latin‑1, abrir com `encoding='latin-1'` ou usar `cat -A` para debug.

## Comandos úteis (exemplo)
```bash
# 1. Buscar TSE/CTI (ID)
grep -i "cruz" /home/rafael/.openclaw/workspace/municipio_tse_ibge.csv | head -1
# → CD_MUNICIPIO_TSE=15890 ; CD_MUNICIPIO_IBGE=2304251

# 2. Consultar IBGE
curl -s "https://servicodados.ibge.gov.br/api/v3/agregados/6579/periodos/-6/variaveis/9324?localidades=N6.<IBGE>" | python3 - <<EOF
import sys, json
obj = json.load(sys.stdin)
print(obj['aggregations'][0]['results'][0]['value'])
EOF

# 3. Listar candidatos
/home/rafael/.openclaw/workspace/MCP-Brasil/.venv/bin/python scripts/mcp_probe.py call '{"ano":2024,"municipio":"15890","eleicao_id":"2045202024","cargo":11}'
/home/rafael/.openclaw/workspace/MCP-Brasil/.venv/bin/python scripts/mcp_probe.py call '{"ano":2024,"municipio":"15890","eleicao_id":"2045202024","cargo":13}'

# 4. Emendas
/home/rafael/.openclaw/workspace/MCP-Brasil/.venv/bin/python scripts/mcp_probe.py call '{"ano":2024,"nome_municipio":"Cruz"}' | python3 - <<EOF
import json, sys
data = json.load(sys.stdin)
res = [r for r in data if "Cruz" in r.get("beneficiario", "").upper()]
print(data)
EOF
```

## Estratégia de salvamento
- **Nome do relatório**: `<Municipio>.html` (sem acentos, sem espaços)
- **Padronização**: usar a mesma codificação UTF-8 e seguir o estelar HTML de exemplo
- **Checkbox**: `MEDIA:<caminho>` linha DEVE aparecer antes de *qualquer* texto de resposta

Após toda a fila ser processada, gerar um arquivo `PROGRESSO.txt` contendo:
```
Lote CE concluído: X/Y municípios
Último município processado: <Nome>
Erros: Z ocorrências (listadas em RelatoriosCE/ERROS.log)
Relatórios gerados: /srv/app/Apagar/RelatoriosCE/
```

## Conclusão
Este workflow deve ser executado **solo em modo autônomo** (subagent) para não bloquear o fluxo principal. Não espere interação humana; apenas registre estado e entregue um resumo final.

# END OF BATCH_GUIDE