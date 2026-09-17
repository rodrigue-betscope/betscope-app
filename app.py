import os
import requests
import json
import numpy as np
from datetime import datetime

# ==========================================
# CONFIGURATION DES CLÉS API ET PARAMÈTRES
# ==========================================
FOOTBALL_DATA_KEY = "e6bdfe3de8b24ba595262d336bea5446"
SERPAPI_KEY = "9c85e900c0db57a533b6f4b009854b216c38a24b9d2450a3ff9993f13c2e2cf1"

HEADERS_FD = {
    "X-Auth-Token": FOOTBALL_DATA_KEY
}

# ==========================================
# MODULE 1 : COLLECTE DES DONNÉES DE MATCH
# ==========================================
def get_match_data_from_api(match_id):
    """
    Récupère les données d'un match spécifique via football-data.org
    """
    url = f"https://api.football-data.org/v4/matches/{match_id}"
    response = requests.get(url, headers=HEADERS_FD)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Erreur API Football-Data: {response.status_code}")
        return None

def search_injuries_and_news(home_team, away_team):
    """
    Utilise SerpAPI pour fouiller le web et récupérer les informations sur les blessés,
    les absents et la forme récente des équipes.
    """
    query = f"injuries squad absents {home_team} vs {away_team} news"
    url = f"https://serpapi.com/search.json?q={requests.utils.quote(query)}&api_key={SERPAPI_KEY}"
    
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            snippets = []
            for res in data.get("organic_results", [])[:5]:
                snippets.append(res.get("snippet", ""))
            return " ".join(snippets)
    except Exception as e:
        print(f"Erreur SerpAPI: {e}")
    
    return "Aucune information spécifique d'absence trouvée via le web."

# ==========================================
# MODULE 2 : ANALYSE STATISTIQUE & MODÈLE POISSON
# ==========================================
def poisson_probability(lmbda, k):
    """Calcule la probabilité d'un nombre d'événements k selon la loi de Poisson."""
    from math import exp, factorial
    return (lmbda**k * exp(-lmbda)) / factorial(k)

def calculate_exact_scores_matrix(home_lambda, away_lambda, max_goals=5):
    """Génère une matrice de probabilité des scores exacts."""
    matrix = np.zeros((max_goals + 1, max_goals + 1))
    for i in range(max_goals + 1):
        for j in range(max_goals + 1):
            matrix[i, j] = poisson_probability(home_lambda, i) * poisson_probability(away_lambda, j)
    return matrix

# ==========================================
# MODULE 3 : MOTEUR DE PRONOSTICS COMPLÈTS
# ==========================================
def analyze_match_comprehensive(match_info):
    """
    Analyse complète du match et génération des marchés de paris :
    - 1N2 (Résultat final)
    - Mi-temps / Fin de match (HT/FT)
    - Double chance
    - Over / Under (0.5 à 4.5 buts)
    - Les deux équipes marquent (BTTS)
    - Scores exacts probables
    """
    home_team = match_info['homeTeam']['name']
    away_team = match_info['awayTeam']['name']
    
    print(f"\n--- ANALYSE AVANCÉE : {home_team} vs {away_team} ---")
    
    # Recherche d'actualités et d'absents via SerpAPI
    news_context = search_injuries_and_news(home_team, away_team)
    print(f"[Info Web / Absents/Blessés] : {news_context[:180]}...")

    # Simulation des forces offensives et défensives (basées sur les taux moyens de buts)
    # Dans un système complet, ces valeurs proviennent de l'historique des derniers matchs.
    home_lambda = 1.65  # Moyenne estimée de buts pour l'équipe à domicile
    away_lambda = 1.15  # Moyenne estimée de buts pour l'équipe extérieure

    # Ajustement basé sur le contexte web (si des joueurs clés sont blessés)
    if "missing" in news_context.lower() or "injury" in news_context.lower() or "blessé" in news_context.lower():
        home_lambda *= 0.95   Légère baisse en cas d'absences signalées

    # Calcul de la matrice des scores
    score_matrix = calculate_exact_scores_matrix(home_lambda, away_lambda, max_goals=5)
    
    # Probabilités 1N2
    prob_home_win = np.sum(np.tril(score_matrix, -1)) # Ligne > Colonne
    prob_draw = np.sum(np.diag(score_matrix))
    prob_away_win = np.sum(np.triu(score_matrix, 1))   # Ligne < Colonne
    
    total_prob = prob_home_win + prob_draw + prob_away_win
    prob_home_win /= total_prob
    prob_draw /= total_prob
    prob_away_win /= total_prob

    # Over / Under buts
    prob_over_15 = 1 - (score_matrix[0,0] + score_matrix[1,0] + score_matrix[0,1])
    prob_over_25 = 1 - np.sum([score_matrix[i, j] for i in range(4) for j in range(4) if i + j <= 2])
    prob_over_35 = 1 - np.sum([score_matrix[i, j] for i in range(5) for j in range(5) if i + j <= 3])
    
    # Les deux équipes marquent (BTTS)
    btts_yes = 1 - np.sum(score_matrix[0, :]) - np.sum(score_matrix[:, 0]) + score_matrix[0, 0]
    btts_no = 1 - btts_yes

    # Scores exacts les plus probables
    flat_indices = np.argsort(score_matrix.ravel())[::-1]
    top_scores = []
    for idx in flat_indices[:3]:
        h_goals = idx // 6
        a_goals = idx % 6
        top_scores.append((f"{h_goals}-{a_goals}", score_matrix[h_goals, a_goals] * 100))

    # Génération du Rapport de Pronostics
    print("\n==========================================")
    print("      RAPPORT DE PRONOSTICS COMPLETS      ")
    print("==========================================")
    print(1. f"Résultat Final (1N2) :")
    print(f"   - Victoire {home_team} : {prob_home_win*100:.1f}%")
    print(f"   - Match Nul : {prob_draw*100:.1f}%")
    print(f"   - Victoire {away_team} : {prob_away_win*100:.1f}%")

    print(2. f"Double Chance :")
    print(f"   - {home ou Nul} : {(prob_home_win + prob_draw)*100:.1f}%")
    print(f"   - {Nul ou away_team} : {(prob_draw + prob_away_win)*100:.1f}%")
    print(f"   - {home_team} ou {away_team} : {(prob_home_win + prob_away_win)*100:.1f}%")

    print(3. f"Buts (Over / Under) :")
    print(f"   - Over 1.5 buts : {prob_over_15*100:.1f}% (Moins de 2.5: {(1-prob_over_25)*100:.1f}%)")
    print(f"   - Over 2.5 buts : {prob_over_25*100:.1f}%")
    print(f"   - Over 3.5 buts : {prob_over_35*100:.1f}%")

    print(4. f"Les Deux Équipes Marquent (BTTS) :")
    print(f"   - Oui : {btts_yes*100:.1f}% | Non : {btts_no*100:.1f}%")

    print(5. f"Mi-Temps / Fin de Match (HT/FT Estimé) :")
    print(f"   - Nul à la Mi-temps / Victoire {home_team} (HT N / FT 1) : {(prob_draw * prob_home_win * 1.2)*100:.1f}%")
    print(f"   - Nul à la Mi-temps / Victoire {away_team} (HT N / FT 2) : {(prob_draw * prob_away_win * 1.2)*100:.1f}%")
    print(f"   - {home_team} gagne aux deux mi-temps : {(prob_home_win**2 * 1.3)*100:.1f}%")

    print(6. f"Scores Exacts Probables :")
    for score, prob in top_scores:
        print(f"   - Score {score} : {prob:.1f}% de probabilité mathématique")
    print("==========================================")

# ==========================================
# EXÉCUTION PRINCIPALE
# ==========================================
if __name__ == "__main__":
    # Exemple d'ID de match (ex: un match de Premier League ou Ligue des Champions via l'API)
    # Vous pouvez remplacer cet ID par un vrai match du jour récupéré de l'API.
    sample_match_id = 456789  
    
    # Récupération ou simulation d'un objet match pour l'exemple si l'ID direct n'est pas actif
    match_data = get_match_data_from_api(sample_match_id)
    
    if not match_data:
        # Structure de secours pour démonstration immédiate si l'ID distant est invalide
        match_data = {
            "homeTeam": {"name": "Real Madrid"},
            "awayTeam": {"name": "FC Barcelona"}
        }
    
    analyze_match_comprehensive(match_data)
