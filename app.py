import os
import requests
import numpy as np
import streamlit as st

# ==========================================
# CONFIGURATION STREAMLIT
# ==========================================
st.set_page_config(page_title="BetScope Pro", page_icon="⚽", layout="wide")

st.title("⚽ BetScope Pro - Analyseur de Matchs")
st.markdown("Analyse automatique des matchs avec recherche web des blessés et prédictions complètes.")

# ==========================================
# CLÉS API
# ==========================================
FOOTBALL_DATA_KEY = "e6bdfe3de8b24ba595262d336bea5446"
SERPAPI_KEY = "9c85e900c0db57a533b6f4b009854b216c38a24b9d2450a3ff9993f13c2e2cf1"

HEADERS_FD = {"X-Auth-Token": FOOTBALL_DATA_KEY}

# ==========================================
# FONCTIONS API FOOTBALL-DATA
# ==========================================
@st.cache_data(ttl=3600)
def get_upcoming_matches():
    """
    Récupère automatiquement tous les matchs prévus dans l'API
    """
    url = "https://api.football-data.org/v4/matches"
    try:
        response = requests.get(url, headers=HEADERS_FD)
        if response.status_code == 200:
            return response.json().get("matches", [])
    except Exception as e:
        st.error(f"Erreur lors de la récupération des matchs: {e}")
    return []

def search_injuries_and_news(home_team, away_team):
    """
    Fouille le web via SerpAPI pour trouver les absents/blessés
    """
    query = f"injuries squad absents {home_team} vs {away_team} news"
    url = f"https://serpapi.com/search.json?q={requests.utils.quote(query)}&api_key={SERPAPI_KEY}"
    
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            snippets = [res.get("snippet", "") for res in data.get("organic_results", [])[:5]]
            return " ".join(snippets)
    except Exception:
        pass
    
    return "Aucune information d'absence majeure trouvée sur le web."

# ==========================================
# MODÈLE PROBABILISTE DE POISSON
# ==========================================
def poisson_probability(lmbda, k):
    from math import exp, factorial
    return (lmbda**k * exp(-lmbda)) / factorial(k)

def calculate_exact_scores_matrix(home_lambda, away_lambda, max_goals=5):
    matrix = np.zeros((max_goals + 1, max_goals + 1))
    for i in range(max_goals + 1):
        for j in range(max_goals + 1):
            matrix[i, j] = poisson_probability(home_lambda, i) * poisson_probability(away_lambda, j)
    return matrix

# ==========================================
# ANALYSE ET GÉNÉRATION DU RAPPORT
# ==========================================
def analyze_teams(home_team, away_team):
    st.subheader(f"📊 Analyse détaillée : {home_team} vs {away_team}")
    
    with st.spinner("Recherche des blessés, absents et actualités du match..."):
        news_context = search_injuries_and_news(home_team, away_team)
    
    st.info(f"**Recherche Web (Blessés/Absents) :** {news_context[:300]}...")

    # Moyennes d'attaque/défense estimées
    home_lambda = 1.65
    away_lambda = 1.15

    if any(word in news_context.lower() for word in ["missing", "injury", "blessé", "absent"]):
        home_lambda *= 0.95

    score_matrix = calculate_exact_scores_matrix(home_lambda, away_lambda)
    
    # Calculs 1N2
    prob_home_win = np.sum(np.tril(score_matrix, -1))
    prob_draw = np.sum(np.diag(score_matrix))
    prob_away_win = np.sum(np.triu(score_matrix, 1))
    
    total = prob_home_win + prob_draw + prob_away_win
    prob_home_win /= total
    prob_draw /= total
    prob_away_win /= total

    # Over / Under
    prob_over_15 = 1 - (score_matrix[0,0] + score_matrix[1,0] + score_matrix[0,1])
    prob_over_25 = 1 - np.sum([score_matrix[i, j] for i in range(4) for j in range(4) if i + j <= 2])
    prob_over_35 = 1 - np.sum([score_matrix[i, j] for i in range(5) for j in range(5) if i + j <= 3])
    
    # BTTS
    btts_yes = 1 - np.sum(score_matrix[0, :]) - np.sum(score_matrix[:, 0]) + score_matrix[0, 0]
    btts_no = 1 - btts_yes

    # Scores probables
    flat_indices = np.argsort(score_matrix.ravel())[::-1]
    top_scores = []
    for idx in flat_indices[:4]:
        h = idx // 6
        a = idx % 6
        top_scores.append((f"{h}-{a}", score_matrix[h, a] * 100))

    # Affichage
    st.success("Analyse terminée !")
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 🏆 Résultat Final (1N2)")
        st.write(f"- Victoire **{home_team}** : **{prob_home_win*100:.1f}%**")
        st.write(f"- Match Nul : **{prob_draw*100:.1f}%**")
        st.write(f"- Victoire **{away_team}** : **{prob_away_win*100:.1f}%**")

        st.markdown("### 🛡️ Double Chance")
        st.write(f"- **{home_team}** ou Nul : **{(prob_home_win + prob_draw)*100:.1f}%**")
        st.write(f"- Nul ou **{away_team}** : **{(prob_draw + prob_away_win)*100:.1f}%**")
        st.write(f"- **{home_team}** ou **{away_team}** : **{(prob_home_win + prob_away_win)*100:.1f}%**")

        st.markdown("### ⚽ Buts (Over / Under)")
        st.write(f"- Plus de 1.5 buts : **{prob_over_15*100:.1f}%**")
        st.write(f"- Plus de 2.5 buts : **{prob_over_25*100:.1f}%** (Moins de 2.5 : **{(1-prob_over_25)*100:.1f}%**)")
        st.write(f"- Plus de 3.5 buts : **{prob_over_35*100:.1f}%**")

    with col2:
        st.markdown("### 🎯 Les Deux Équipes Marquent")
        st.write(f"- Oui : **{btts_yes*100:.1f}%** | Non : **{btts_no*100:.1f}%**")

        st.markdown("### ⏱️ Mi-Temps / Fin de Match (HT/FT)")
        st.write(f"- Nul à la MT / Victoire **{home_team}** : **{(prob_draw * prob_home_win * 1.2)*100:.1f}%**")
        st.write(f"- Nul à la MT / Victoire **{away_team}** : **{(prob_draw * prob_away_win * 1.2)*100:.1f}%**")

        st.markdown("### 🔢 Scores Exacts les plus probables")
        for score, prob in top_scores:
            st.write(f"- Score **{score}** : **{prob:.1f}%**")

# ==========================================
# INTERFACE SÉLECTION DU MATCH
# ==========================================
mode = st.radio("Méthode de sélection du match :", ["Sélectionner dans la liste des matchs à venir", "Saisir les noms manuellement"])

if mode == "Sélectionner dans la liste des matchs à venir":
    upcoming_matches = get_upcoming_matches()
    
    if upcoming_matches:
        options = {f"{m['homeTeam']['name']} vs {m['awayTeam']['name']} ({m['competition']['name']})": m for m in upcoming_matches}
        selected_option = st.selectbox("Choisissez le match à analyser :", list(options.keys()))
        match_data = options[selected_option]
        
        if st.button("Lancer l'analyse du match sélectionné"):
            analyze_teams(match_data['homeTeam']['name'], match_data['awayTeam']['name'])
    else:
        st.warning("Aucun match direct trouvé pour aujourd'hui dans l'offre gratuite API. Passez en saisie manuelle ci-dessous.")

else:
    col_h, col_a = st.columns(2)
    with col_h:
        home_input = st.text_input("Équipe à domicile :", value="Besiktas")
    with col_a:
        away_input = st.text_input("Équipe extérieure :", value="Olympique de Marseille")
        
    if st.button("Lancer l'analyse"):
        analyze_teams(home_input, away_input)
