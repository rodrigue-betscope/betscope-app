# ============================================================
# RODRIGUE PRO FOOTBALL AI — V10 ULTIMATE (COMPLET)
# ============================================================

import math
from datetime import date
import numpy as np
import pandas as pd
import requests
import streamlit as st

# ============================================================
# CONFIGURATION ET CLES
# ============================================================

FOOTBALL_DATA_KEY = "ca5b8e71be93da1827e148ee1551a9b0"
SERPAPI_KEY = "6680e04a0cf677964822ad771410a129eec409d735f6e8536ecbaae276e9c7c6"

API_BASE = "https://api.football-data.org/v4"
SERP_URL = "https://serpapi.com/search.json"

COMPETITIONS = {
    "Premier League": "PL",
    "LaLiga": "PD",
    "Bundesliga": "BL1",
    "Serie A": "SA",
    "Ligue 1": "FL1",
    "Champions League": "CL",
    "Eredivisie": "DED",
    "Primeira Liga": "PPL",
    "Championship": "ELC",
    "Brasileirão": "BSA",
}

st.set_page_config(
    page_title="Rodrigue Pro Football AI V10",
    page_icon="⚽",
    layout="wide"
)

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "Rodrigue-Pro-Football-AI-V10"
})

# ============================================================
# FONCTIONS API & RECHERCHE
# ============================================================

def football_get(endpoint, params=None):
    try:
        response = SESSION.get(
            API_BASE + endpoint,
            headers={"X-Auth-Token": FOOTBALL_DATA_KEY},
            params=params or {},
            timeout=25
        )
        if response.status_code == 200:
            return response.json()
        return None
    except:
        return None

def fetch_matches(selected_date, competition_codes):
    params = {
        "dateFrom": selected_date.isoformat(),
        "dateTo": selected_date.isoformat()
    }
    data = football_get("/matches", params)
    if not data:
        return []

    matches = data.get("matches", [])
    if competition_codes:
        matches = [
            m for m in matches 
            if m.get("competition", {}).get("code") in competition_codes
        ]
    return matches

def fetch_team_recent_matches(team_id):
    data = football_get(f"/teams/{team_id}/matches", {"status": "FINISHED", "limit": 5})
    if not data:
        return []
    return data.get("matches", [])

# ============================================================
# MODELE STATISTIQUE & POISSON
# ============================================================

def poisson_pmf(lmbda, k):
    return (math.exp(-lmbda) * (lmbda ** k)) / math.factorial(k)

def calculate_form_and_goals(team_id):
    matches = fetch_team_recent_matches(team_id)
    if not matches:
        return {"scored_avg": 1.2, "conceded_avg": 1.1, "form_score": 1.0}
    
    scored = 0
    conceded = 0
    points = 0
    count = len(matches)

    for m in matches:
        is_home = m.get("homeTeam", {}).get("id") == team_id
        score = m.get("score", {}).get("fullTime", {})
        h_goals = score.get("home", 0) or 0
        a_goals = score.get("away", 0) or 0

        if is_home:
            scored += h_goals
            conceded += a_goals
            if h_goals > a_goals: points += 3
            elif h_goals == a_goals: points += 1
        else:
            scored += a_goals
            conceded += h_goals
            if a_goals > h_goals: points += 3
            elif a_goals == h_goals: points += 1

    return {
        "scored_avg": max(scored / count, 0.2),
        "conceded_avg": max(conceded / count, 0.2),
        "form_score": points / (count * 3)
    }

def predict_match(home_id, away_id):
    home_stats = calculate_form_and_goals(home_id)
    away_stats = calculate_form_and_goals(away_id)

    lambda_home = (home_stats["scored_avg"] + away_stats["conceded_avg"]) / 2
    lambda_away = (away_stats["scored_avg"] + home_stats["conceded_avg"]) / 2

    team_loc_bonus = 0.15
    lambda_home += team_loc_bonus

    max_goals = 6
    matrix = np.zeros((max_goals + 1, max_goals + 1))
    for h in range(max_goals + 1):
        for a in range(max_goals + 1):
            matrix[h, a] = poisson_pmf(lambda_home, h) * poisson_pmf(lambda_away, a)

    p_home = np.sum(np.tril(matrix, -1)) # Victoire domicile (lignes > colonnes)
    p_draw = np.sum(np.diag(matrix))
    p_away = np.sum(np.triu(matrix, 1))

    total = p_home + p_draw + p_away
    if total > 0:
        p_home /= total
        p_draw /= total
        p_away /= total

    # Scores exacts probables
    exact_scores = []
    for h in range(4):
        for a in range(4):
            exact_scores.append((f"{h}-{a}", matrix[h, a]))
    exact_scores.sort(key=lambda x: x[1], reverse=True)

    # Marchés annexes
    btts_prob = sum(matrix[h, a] for h in range(1, 7) for a in range(1, 7))
    over_25 = sum(matrix[h, a] for h in range(7) for a in range(7) if h + a > 2.5)

    return {
        "p_home": p_home,
        "p_draw": p_draw,
        "p_away": p_away,
        "exact_scores": exact_scores[:3],
        "btts": btts_prob,
        "over_25": over_25,
        "home_stats": home_stats,
        "away_stats": away_stats
    }

# ============================================================
# INTERFACE PRINCIPALE (MOBILE FRIENDLY)
# ============================================================

def main():
    st.title("⚽ Rodrigue Pro Football AI V10")
    st.markdown("### Moteur d'analyse prédictive, statistique et lecture humaine")
    st.markdown("---")

    st.subheader("⚙️ Paramètres de recherche")

    selected_date = st.date_input(
        "Date des matchs",
        value=date.today()
    )

    selected_competitions = st.multiselect(
        "Compétitions",
        options=list(COMPETITIONS.keys()),
        default=["Champions League", "Premier League", "LaLiga"]
    )

    if st.button("🚀 LANCER L'ANALYSE GLOBALE", type="primary", use_container_width=True):
        codes = [COMPETITIONS[c] for c in selected_competitions]

        with st.spinner("Analyse des matchs et calculs statistiques en cours..."):
            matches = fetch_matches(selected_date, codes)

        if not matches:
            st.warning("Aucun match trouvé pour cette date dans les compétitions sélectionnées.")
        else:
            st.success(f"{len(matches)} match(s) analysé(s) avec succès !")
            
            for match in matches:
                home_team = match.get("homeTeam", {})
                away_team = match.get("awayTeam", {})
                home_name = home_team.get("name", "Domicile")
                away_name = away_team.get("name", "Extérieur")
                home_id = home_team.get("id")
                away_id = away_team.get("id")
                comp = match.get("competition", {}).get("name", "")
                utc = match.get("utcDate", "")

                st.markdown(f"---")
                st.markdown(f"🏆 **{comp}**")
                st.markdown(f"### {home_name} VS {away_name}")
                st.text(f"Heure (UTC) : {utc}")

                if home_id and away_id:
                    pred = predict_match(home_id, away_id)

                    # Affichage des métriques 1X2
                    col1, col2, col3 = st.columns(3)
                    col1.metric("Victoire Domicile", f"{pred['p_home']*100:.1f}%")
                    col2.metric("Match Nul", f"{pred['p_draw']*100:.1f}%")
                    col3.metric("Victoire Extérieur", f"{pred['p_away']*100:.1f}%")

                    # Marchés et Scores Exacts
                    st.markdown(f"🎯 **Score exact le plus probable :** `{pred['exact_scores'][0][0]}`")
                    st.markdown(f"📊 **Options de paris :** BTTS (Les deux marquent) : `{pred['btts']*100:.1f}%` | Plus de 2.5 buts : `{pred['over_25']*100:.1f}%`")
                    
                    # Lecture humaine contextuelle
                    gap = abs(pred['p_home'] - pred['p_away'])
                    if gap < 0.08 and pred['p_draw'] >= 0.27:
                        reading = "Match très équilibré. Le nul mérite une attention particulière."
                    elif pred['p_home'] > pred['p_away']:
                        reading = f"Avantage cohérent pour l'équipe à domicile ({home_name}), appuyé par sa forme récente."
                    else:
                        reading = f"Attention coup possible à l'extérieur pour ({away_name}) au vu des dynamiques actuelles."
                    
                    st.info(f"🧠 **Lecture humaine :** {reading}")
                else:
                    st.info("Données statistiques indisponibles pour ce match.")

if __name__ == "__main__":
    main()
    
