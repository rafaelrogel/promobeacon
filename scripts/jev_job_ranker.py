#!/usr/bin/env python3
"""
JeV-enhanced job ranking script.
Uses Jev API to score and rank job search results.
"""

import json
import os
import sys
from datetime import datetime

# Add workspace to path for imports if needed
sys.path.insert(0, '/home/rafael/.openclaw/workspace')

def load_jev_api_key():
    """Load the Jev API key from file."""
    key_path = '/home/rafael/.openclaw/workspace/jev_api_key.txt'
    try:
        with open(key_path, 'r') as f:
            return f.read().strip()
    except FileNotFoundError:
        print("Error: Jev API key not found at", key_path)
        return None

def jev_evaluate(state, question_config):
    """
    Evaluate using Jev API.
    
    Args:
        state: The content to evaluate (string or dict)
        question_config: Dict with question configuration
    
    Returns:
        Jev response dict or None on error
    """
    import urllib.request
    import urllib.error
    
    api_key = load_jev_api_key()
    if not api_key:
        return None
    
    # Prepare request - CORRECT FORMAT: state and questions at top level
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
        with urllib.request.urlopen(req, timeout=15) as response:
            return json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        print(f"JeV API HTTP Error: {e.code}")
        print(e.read().decode('utf-8'))
        return None
    except Exception as e:
        print(f"JeV API Error: {e}")
        return None

def search_jobs_web(query, count=5):
    """
    Search for jobs using web search via subprocess call to openclaw.
    Returns list of job dicts.
    """
    import subprocess
    import json
    
    # Call openclaw web_search via CLI and parse JSON output
    # Note: This is a workaround; ideally we'd use the tool directly
    print(f"Searching for: {query}")
    
    # Mock results for demo (replace with actual web_search integration)
    return [
        {
            "title": "Senior Localization Specialist - Revolut",
            "snippet": "Revolut is looking for a Localization Specialist to work on app localization EN→PT-BR. Requires experience with CAT tools and agile methodologies.",
            "url": "https://example.com/revolut-job",
            "source": "LinkedIn"
        },
        {
            "title": "Freelance Game Translator PT-BR",
            "snippet": "Looking for experienced game translator for upcoming RPG project. Must have experience with game localization and familiarity with gaming terminology.",
            "url": "https://example.com/game-translator",
            "source": "Upwork"
        },
        {
            "title": "Content Moderator - Portuguese (Brazil)",
            "snippet": "Moderate user-generated content in Portuguese. Requires fluency in PT-BR and understanding of Brazilian culture.",
            "url": "https://example.com/moderator-job",
            "source": "Indeed"
        },
        {
            "title": "Technical Writer - Software Documentation",
            "snippet": "Create and maintain technical documentation for software products. Experience with MadCap Flare or similar tools preferred.",
            "url": "https://example.com/tech-writer",
            "source": "Glassdoor"
        },
        {
            "title": "Spanish to Portuguese Translator",
            "snippet": "Translate documents from Spanish to Portuguese for legal and business clients. Certification preferred.",
            "url": "https://example.com/spanish-translator",
            "source": "ProZ.com"
        }
    ]

def rank_jobs_with_jev(jobs):
    """
    Rank jobs using Jev API for relevance scoring.
    """
    ranked_jobs = []
    
    for job in jobs:
        # Create state from job data
        state = f"Título: {job['title']}\nDescrição: {job['snippet']}\nFonte: {job['source']}"
        
        # Define Jev question for job relevance
        question_config = {
            "relevance": {
                "type": "choice",
                "instructions": "Esta vaga é relevante para um tradutor técnico especializado em jogos, TI e software, com experiência em localização de apps e UX writing?",
                "criteria": {
                    "Altamente Relevante": "Vaga diretamente relacionada à localização de software/apps/games, tradução técnica ou UX writing em PT-BR",
                    "Parcialmente Relevante": "Vaga relacionada à tradução ou linguagem, mas não especificamente técnica ou de localização",
                    "Pouco Relevante": "Vaga de tradução geral, juramentada, interpretação ou áreas não técnicas",
                    "Não Relevante": "Vaga que não requer habilidades de tradução ou está completamente fora da área linguística"
                }
            },
            "score": {
                "type": "score",
                "instructions": "Em uma escala de 0 a 5, o quão bem esta vaga corresponde ao perfil de Localization Specialist na Revolut com experiência em jogos/TI/software?",
                "criteria": [
                    "0 = Nenhuma correspondência",
                    "1 = Pouca correspondência (apenas idioma)",
                    "2 = Correspondência básica (algumas habilidades relevantes)",
                    "3 = Boa correspondência (várias habilidades relevantes)",
                    "4 = Muito boa correspondência (quase todas as habilidades relevantes)",
                    "5 = Correspondência perfeita (exatamente o que se procura)"
                ]
            },
            "is_remote": {
                "type": "noul",
                "instructions": "Esta vaga oferece trabalho remoto (total ou híbrido)?",
                # Criteria for Noul are implicit True/False
            }
        }
        
        # Evaluate with Jev
        result = jev_evaluate(state, question_config)
        
        if result and 'answers' in result:
            answers = result['answers']
            
            # Extract relevance
            relevance = answers.get('relevance', {})
            relevance_choice = relevance.get('choice', 'Não Relevante')
            relevance_confidence = relevance.get('confidence', 0.0)
            
            # Extract score
            score_answer = answers.get('score', {})
            score_value = score_answer.get('score', 0.0)
            score_confidence = score_answer.get('confidence', 0.0)
            
            # Extract Noul (remote)
            remote_answer = answers.get('is_remote', {})
            is_remote = remote_answer.get('noul', False)
            remote_confidence = remote_answer.get('confidence', 0.0)
            
            # Calculate composite score (weighted)
            # Relevance weight: 0.4, Score weight: 0.4, Remote bonus: 0.2
            relevance_score = {
                'Altamente Relevante': 1.0,
                'Parcialmente Relevante': 0.6,
                'Pouco Relevante': 0.3,
                'Não Relevante': 0.0
            }.get(relevance_choice, 0.0)
            
            normalized_score = score_value / 5.0  # Convert 0-5 to 0-1
            remote_bonus = 0.2 if is_remote else 0.0
            
            composite = (relevance_score * 0.4) + (normalized_score * 0.4) + (remote_bonus * 0.2)
            
            # Adjust by confidence
            avg_confidence = (relevance_confidence + score_confidence + remote_confidence) / 3.0
            final_score = composite * avg_confidence
            
            job_copy = job.copy()
            job_copy.update({
                'jev_relevance': relevance_choice,
                'jev_relevance_confidence': relevance_confidence,
                'jev_score': score_value,
                'jev_score_confidence': score_confidence,
                'jev_is_remote': is_remote,
                'jev_remote_confidence': remote_confidence,
                'jev_composite_score': composite,
                'jev_final_score': final_score,
                'jev_avg_confidence': avg_confidence
            })
            
            ranked_jobs.append(job_copy)
        else:
            print(f"Failed to evaluate job: {job['title']}")
            # Still add with default low score
            job_copy = job.copy()
            job_copy.update({
                'jev_relevance': 'Erro na avaliação',
                'jev_final_score': 0.0
            })
            ranked_jobs.append(job_copy)
    
    # Sort by final score descending
    ranked_jobs.sort(key=lambda x: x['jev_final_score'], reverse=True)
    return ranked_jobs

def main():
    print("=== JeV-Enhanced Job Ranking Demo ===\n")
    
    # Search for jobs (in real implementation, this would use existing job search)
    print("1. Searching for translation jobs...")
    jobs = search_jobs_web("tradutor PT-BR localization jogos TI software", count=5)
    print(f"   Found {len(jobs)} jobs\n")
    
    # Rank with Jev
    print("2. Ranking jobs with Jev API...")
    ranked_jobs = rank_jobs_with_jev(jobs)
    print(f"   Ranked {len(ranked_jobs)} jobs\n")
    
    # Display results
    print("3. Ranked Results:\n")
    print("-" * 80)
    for i, job in enumerate(ranked_jobs, 1):
        rel = job.get('jev_relevance', 'N/A')
        rel_conf = job.get('jev_relevance_confidence', 0.0)
        score = job.get('jev_score', 0.0)
        score_conf = job.get('jev_score_confidence', 0.0)
        remote = job.get('jev_is_remote', False)
        remote_conf = job.get('jev_remote_confidence', 0.0)
        final = job.get('jev_final_score', 0.0)
        print(f"{i}. {job['title']}")
        print(f"   Fonte: {job['source']}")
        print(f"   Relevância (Jev): {rel} (conf: {rel_conf:.2f})")
        print(f"   Score (Jev): {score:.1f}/5.0 (conf: {score_conf:.2f})")
        print(f"   Remoto: {remote} (conf: {remote_conf:.2f})")
        print(f"   Score Final: {final:.3f}")
        print(f"   Snippet: {job['snippet'][:100]}...")
        print()
    
    # Show top recommendation
    if ranked_jobs:
        top = ranked_jobs[0]
        print("🏆 TOP RECOMMENDATION:")
        print(f"   {top['title']}")
        print(f"   Fonte: {top['source']}")
        print(f"   Por que é top: Relevância '{top['jev_relevance']}' "
              f"(conf: {top['jev_relevance_confidence']:.2f}) + "
              f"Score {top['jev_score']:.1f}/5.0 "
              f"(conf: {top['jev_score_confidence']:.2f})")
        if top['jev_is_remote']:
            print(f"   + Trabalho remoto disponível (conf: {top['jev_remote_confidence']:.2f})")

if __name__ == "__main__":
    main()