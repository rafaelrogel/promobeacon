#!/usr/bin/env python3
"""
JeV integration demo: real web-search data -> Jev scoring -> ranked output.
Feeds from a JSON file so the daily cron jobs can reuse it.
"""
import json
import sys
import urllib.request
import urllib.error

KEY_PATH = '/home/rafael/.openclaw/workspace/jev_api_key.txt'

# Rafael's profile (from memory/job-search-profile.md) as fixed context
PROFILE = (
    "Perfil: Localization Specialist na Revolut (EN->PT-BR, app/UI/UX writing), "
    "15+ anos tradutor freelance (jogos, TI, software), legendagem, revisão, "
    "gestão de projetos de localização. Idiomas fonte: EN/FR/ES. "
    "Interesse: vagas remotas ou Porto/Europa; games localization, apps, software."
)


def load_key():
    with open(KEY_PATH, 'r') as f:
        return f.read().strip()


def jev_evaluate(state, questions):
    data = {"model": "jev-latest", "state": state, "questions": questions}
    req = urllib.request.Request(
        'https://api.typesafe.ai/v1/systemone',
        data=json.dumps(data).encode('utf-8'),
        headers={'Authorization': f'Bearer {load_key()}', 'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        return {"error": f"{e.code}: {e.read().decode('utf-8')}"}
    except Exception as e:
        return {"error": str(e)}


def rank_items(items, item_type):
    ranked = []
    for it in items:
        if item_type == 'job':
            state = (f"{PROFILE}\n\nVAGA: {it.get('title','?')}\n"
                     f"FONTE: {it.get('source','')}\nDESCRIÇÃO: {it.get('snippet','')}\n"
                     f"LOCAL: {it.get('location','')}\n")
            questions = {
                "fit": {
                    "type": "choice",
                    "instructions": "Esta vaga é um bom match para o perfil acima?",
                    "criteria": {
                        "Match Excelente": "Localização de software/apps/games, tradução técnica, UX writing, remoto ou Porto/Europa",
                        "Match Bom": "Tradução PT-BR em área relacionada (TI, marketing, conteúdo)",
                        "Match Parcial": "Tradução geral ou área linguística, sem foco técnico",
                        "Não Relevante": "Fora da área de tradução/localização ou requisitos incompatíveis"
                    }
                },
                "fit_score": {
                    "type": "score",
                    "instructions": "Nota 0-5 de aderência ao perfil (5=perfeito)?",
                    "criteria": ["0=nenhuma", "1=mínima", "2=fraca", "3=razoável", "4=forte", "5=perfeita"]
                }
            }
        else:  # flight
            state = (f"VOO: {it.get('airline','?')} {it.get('flight','')} {it.get('route','?')} | "
                     f"Preço {it.get('price','?')} | Duração {it.get('duration','?')} | {it.get('stops','?')} | "
                     f"Horário {it.get('departure','?')}->{it.get('arrival','?')} | Bagagem {it.get('baggage','?')}")
            questions = {
                "fit": {
                    "type": "choice",
                    "instructions": "Boa opção de voo PT->BR (preço, escalas, horário, duração)?",
                    "criteria": {
                        "Excelente": "Direto ou 1 escala curta, preço baixo, horário bom, bagagem incluída",
                        "Bom": "Equilíbrio razoável",
                        "Regular": "Preço alto ou escala longa ou horário ruim",
                        "Ruim": "Múltiplas escalas longas, preço alto, sem bagagem"
                    }
                },
                "value": {
                    "type": "score",
                    "instructions": "Custo-benefício 0-5?",
                    "criteria": ["0=péssimo", "1=muito caro", "2=caro", "3=razoável", "4=bom", "5=excelente"]
                }
            }

        res = jev_evaluate(state, questions)
        if 'error' in res:
            it['jev_error'] = res['error']
            it['jev_final'] = 0.0
            ranked.append(it)
            continue
        a = res.get('answers', {})
        fit = a.get('fit', {})
        score = a.get('fit_score' if item_type == 'job' else 'value', {})
        choice = fit.get('choice', '?')
        conf = fit.get('confidence', 0.0)
        val = score.get('score', 0.0)
        val_conf = score.get('confidence', 0.0)
        fit_val = {"Excelente": 1.0, "Bom": 0.8, "Match Excelente": 1.0, "Match Bom": 0.8,
                   "Regular": 0.45, "Match Parcial": 0.45, "Ruim": 0.1, "Não Relevante": 0.1}.get(choice, 0.4)
        composite = (fit_val * 0.6) + ((val / 5.0) * 0.4)
        avg_conf = (conf + val_conf) / 2.0
        it['jev_fit'] = choice
        it['jev_fit_conf'] = conf
        it['jev_score'] = val
        it['jev_score_conf'] = val_conf
        it['jev_final'] = composite * avg_conf
        ranked.append(it)

    ranked.sort(key=lambda x: x['jev_final'], reverse=True)
    return ranked


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else 'job'
    in_path = sys.argv[2] if len(sys.argv) > 2 else f'/home/rafael/.openclaw/workspace/jev_{mode}s_input.json'
    with open(in_path) as f:
        items = json.load(f)
    ranked = rank_items(items, mode)
    print(json.dumps(ranked, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
