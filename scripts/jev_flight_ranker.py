#!/usr/bin/env python3
"""
JeV-enhanced flight ranking.
Uses Jev API to score flight options (price, duration, stops, times).
"""
import json
import urllib.request
import urllib.error


def load_jev_api_key():
    key_path = '/home/rafael/.openclaw/workspace/jev_api_key.txt'
    try:
        with open(key_path, 'r') as f:
            return f.read().strip()
    except FileNotFoundError:
        print("Error: Jev API key not found at", key_path)
        return None


def jev_evaluate(state, question_config):
    api_key = load_jev_api_key()
    if not api_key:
        return None
    data = {
        "model": "jev-latest",
        "state": state,
        "questions": question_config
    }
    req = urllib.request.Request(
        'https://api.typesafe.ai/v1/systemone',
        data=json.dumps(data).encode('utf-8'),
        headers={
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            return json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        print(f"JeV API HTTP Error: {e.code} - {e.read().decode('utf-8')}")
        return None
    except Exception as e:
        print(f"JeV API Error: {e}")
        return None


def rank_flights(flights):
    """Score each flight option with Jev and rank."""
    ranked = []
    for f in flights:
        state = (
            f"Voo: {f['airline']} {f['flight']}\n"
            f"Rota: {f['route']}\n"
            f"Preço: {f['price']}\n"
            f"Duração: {f['duration']}\n"
            f"Escalas: {f['stops']}\n"
            f"Horário: {f['departure']} -> {f['arrival']}\n"
            f"Bagagem: {f['baggage']}"
        )
        questions = {
            "fit": {
                "type": "choice",
                "instructions": "Este voo é uma boa opção para uma viagem de Portugal para o Brasil (econômica, direta ou poucas escalas, horário razoável)?",
                "criteria": {
                    "Excelente": "Preço baixo, direto ou 1 escala curta, horários bons, bagagem incluída",
                    "Bom": "Equilíbrio razoável de preço, escala e horário",
                    "Regular": "Preço alto ou escala longa ou horário ruim",
                    "Ruim": "Preço muito alto, múltiplas escalas longas, horário péssimo ou sem bagagem"
                }
            },
            "value": {
                "type": "score",
                "instructions": "Em uma escala de 0 a 5, qual é o custo-benefício deste voo?",
                "criteria": [
                    "0 = Péssimo custo-benefício",
                    "1 = Muito caro pelo que oferece",
                    "2 = Caro",
                    "3 = Razoável",
                    "4 = Bom custo-benefício",
                    "5 = Excelente custo-benefício"
                ]
            },
            "would_book": {
                "type": "noul",
                "instructions": "Vale a pena reservar este voo sem pesquisar mais?"
            }
        }
        result = jev_evaluate(state, questions)
        if result and 'answers' in result:
            a = result['answers']
            fit = a.get('fit', {})
            val = a.get('value', {})
            book = a.get('would_book', {})
            fit_choice = fit.get('choice', 'Regular')
            fit_conf = fit.get('confidence', 0.0)
            score = val.get('score', 0.0)
            score_conf = val.get('confidence', 0.0)
            noul = book.get('noul', False)
            noul_conf = book.get('confidence', 0.0)

            fit_val = {"Excelente": 1.0, "Bom": 0.75, "Regular": 0.4, "Ruim": 0.1}.get(fit_choice, 0.4)
            # composite: fit 50%, score 40%, bookability 10%
            composite = (fit_val * 0.5) + ((score / 5.0) * 0.4) + (0.1 if noul else 0.0)
            avg_conf = (fit_conf + score_conf + noul_conf) / 3.0

            fc = f.copy()
            fc.update({
                'jev_fit': fit_choice, 'jev_fit_conf': fit_conf,
                'jev_value': score, 'jev_value_conf': score_conf,
                'jev_book': noul, 'jev_book_conf': noul_conf,
                'jev_final': composite * avg_conf
            })
            ranked.append(fc)
        else:
            fc = f.copy()
            fc.update({'jev_fit': 'Erro', 'jev_final': 0.0})
            ranked.append(fc)

    ranked.sort(key=lambda x: x['jev_final'], reverse=True)
    return ranked


def main():
    print("=== JeV-Enhanced Flight Ranking Demo ===\n")
    # Realistic sample options LIS -> GRU (mock da busca web real)
    flights = [
        {"airline": "TAP", "flight": "TP 88", "route": "LIS->GRU", "price": "€720",
         "duration": "11h30m", "stops": "Direto", "departure": "09:30", "arrival": "16:00",
         "baggage": "23kg incluída"},
        {"airline": "LATAM", "flight": "LA 8085", "route": "LIS->GRU", "price": "€680",
         "duration": "14h05m", "stops": "1 escala (MAD 2h)", "departure": "06:15", "arrival": "18:20",
         "baggage": "23kg incluída"},
        {"airline": "Air Europa", "flight": "UX 1154", "route": "LIS->GRU", "price": "€645",
         "duration": "16h40m", "stops": "1 escala (MAD 4h30m)", "departure": "11:40", "arrival": "22:20",
         "baggage": "23kg incluída"},
        {"airline": "Azul", "flight": "AD 8701", "route": "LIS->VCP", "price": "€590",
         "duration": "18h55m", "stops": "1 escala (CDG 6h)", "departure": "05:00", "arrival": "21:55",
         "baggage": "Somente mochila"},
        {"airline": "TAP", "flight": "TP 1820", "route": "LIS->REC", "price": "€830",
         "duration": "9h10m", "stops": "Direto", "departure": "22:40", "arrival": "04:50",
         "baggage": "23kg incluída"},
    ]
    print("Avaliando 5 opções de voo com Jev...\n")
    ranked = rank_flights(flights)

    print("-" * 80)
    for i, f in enumerate(ranked, 1):
        fit = f.get('jev_fit', 'N/A')
        fit_conf = f.get('jev_fit_conf', 0.0)
        value = f.get('jev_value', 0.0)
        value_conf = f.get('jev_value_conf', 0.0)
        book = f.get('jev_book', False)
        book_conf = f.get('jev_book_conf', 0.0)
        final = f.get('jev_final', 0.0)
        print(f"{i}. {f['airline']} {f['flight']} | {f['route']} | {f['price']} | {f['duration']} | {f['stops']}")
        print(f"   Jev: Fit={fit} (conf {fit_conf:.2f}) | Valor {value:.1f}/5 (conf {value_conf:.2f}) | Reservar={book} (conf {book_conf:.2f})")
        print(f"   Score final: {final:.3f}")
        print()

    if ranked:
        top = ranked[0]
        print("🏆 MELHOR OPÇÃO:")
        print(f"   {top['airline']} {top['flight']} | {top['price']} | {top['duration']} | {top['stops']}")
        print(f"   Jev: {top['jev_fit']} | Valor {top['jev_value']:.1f}/5 | Reservar={top['jev_book']}")


if __name__ == "__main__":
    main()
