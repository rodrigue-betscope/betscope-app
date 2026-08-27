# app.py
import math
import time
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
import numpy as np
import pandas as pd
import requests
import streamlit as st

# ============================================================
# RODRIGUE MT/FT PRO — FOOTBALL-DATA.ORG v4
# ============================================================

st.set_page_config(
    page_title="Rodrigue MT/FT PRO",
    page_icon="⚽",
    layout="wide",
)

BASE_URL = "https://api.football-data.org/v4"
TZ = ZoneInfo("Africa/Douala")
DEFAULT_API_KEY = "0b5a0d95508247ed93aa7c9cd536f58f"

try:
    API_KEY = st.secrets.get("FOOTBALL_DATA_API_KEY", DEFAULT_API_KEY)
except Exception:
    API_KEY = DEFAULT_API_KEY

COMPETITIONS = {
    "PL": "Premier League",
    "BL1": "Bundesliga",
    "SA": "Serie A",
    "PD": "La Liga",
    "FL1": "Ligue 1",
    "DED": "Eredivisie",
    "PPL": "Primeira Liga",
    "CL": "Champions League",
}

session = requests.Session()
session.headers.update({
    "X-Auth-Token": API_KEY,
    "Accept": "application/json",
    "User-Agent": "Rodrigue-MTFT-Pro/1.0",
})

def api_get(endpoint, params=None, retry=True):
    url = f"{BASE_URL}{endpoint}"
    try:
        response = session.get(url, params=params or {}, timeout=30)
    except requests.RequestException as e:
        raise RuntimeError(f"Erreur réseau : {e}")

    if response.status_code == 401:
        raise RuntimeError("❌ Clé Football-Data.org invalide.")
    if response.status_code == 403:
        raise RuntimeError("❌ Donnée indisponible avec ton abonnement.")
    if response.status_code == 429:
        if retry:
            time.sleep(12)
            return api_get(endpoint, params, retry=False)
        raise RuntimeError("❌ Limite de requêtes Football-Data.org atteinte.")

    response.raise_for_status()
    try:
        return response.json()
    except Exception:
        raise RuntimeError("❌ Réponse JSON invalide.")

@st.cache_data(ttl=300, show_spinner=False)
def get_matches_for_date(selected_date, competitions_list):
    if not competitions_list:
        return []
    comps_str = ",".join(competitions_list)
    try:
        data = api_get("/matches", {"dateFrom": selected_date, "dateTo": selected_date, "competitions": comps_str})
        return data.get("matches", [])
    except Exception as e:
        st.warning(f"Impossible de charger les matchs : {e}")
        return []

@st.cache_data(ttl=1800, show_spinner=False)
def get_team_history(team_id, before_date, limit=15):
    try:
        end_date = datetime.strptime(before_date, "%Y-%m-%d").date() - timedelta(days=1)
        start_date = end_date - timedelta(days=120)
        data = api_get(f"/teams/{team_id}/matches", {
            "dateFrom": start_date.isoformat(),
            "dateTo": end_date.isoformat(),
            "status": "FINISHED",
            "limit": limit,
        })
        matches = data.get("matches", [])
        matches.sort(key=lambda x: x.get("utcDate", ""), reverse=True)
        return matches[:limit]
    except Exception:
        return []

def get_score(match, period="fullTime"):
    score = match.get("score", {})
    period_score = score.get(period, {})
    home = period_score.get("home")
    away = period_score.get("away")
    if home is None or away is None:
        return None, None
    try:
        return int(home), int(away)
    except Exception:
        return None, None

# ============================================================
# STATISTIQUES RÉCENTES (FIN DU SCRIPT ET CORRECTION PONDÉRATION)
# ============================================================
def calculate_team_stats(matches, team_id):
    full_for, full_against = [], []
    ht_for, ht_against = [], []
    
    for index, match in enumerate(matches):
        home_team = match.get("homeTeam", {})
        away_team = match.get("awayTeam", {})
        home_id = home_team.get("id")
        away_id = away_team.get("id")

        if home_id != team_id and away_id != team_id:
            continue

        fh, fa = get_score(match, "fullTime")
        hh, ha = get_score(match, "halfTime")

        if fh is None or fa is None or hh is None or ha is None:
            continue

        # Calcul du coefficient de récence (pondération temporelle décroissante)
        weight = max(0.35, 1.0 - index * 0.04)

        if home_id == team_id:
            full_for.append((fh, weight))
            full_against.append((fa, weight))
            ht_for.append((hh, weight))
            ht_against.append((ha, weight))
        else:
            full_for.append((fa, weight))
            full_against.append((fh, weight))
            ht_for.append((ha, weight))
            ht_against.append((hh, weight))

    def weighted_avg(tuples_list, fallback=1.35):
        if not tuples_list:
            return fallback
        s_vals = sum(val * w for val, w in tuples_list)
        s_w = sum(w for val, w in tuples_list)
        return s_vals / s_w if s_w > 0 else fallback

    return {
        "ft_for": weighted_avg(full_for, 1.35),
        "ft_against": weighted_avg(full_against, 1.25),
        "ht_for": weighted_avg(ht_for, 0.60),
        "ht_against": weighted_avg(ht_against, 0.50),
        "n_matches": len(full_for)
    }

# ============================================================
# LOGIQUE PRÉDICTIVE : POISSON BIVARIÉ & MT/FT
# ============================================================
def poisson_pmf(k, lam):
    if lam <= 0:
        return 1.0 if k == 0 else 0.0
    return math.exp(-lam) * (lam ** k) / math.factorial(k)

def generate_half_matrix(lam_h, lam_a, max_goals=4):
    m = np.zeros((max_goals + 1, max_goals + 1))
    for i in range(max_goals + 1):
        for j in range(max_goals + 1):
            m[i, j] = poisson_pmf(i, lam_h) * poisson_pmf(j, lam_a)
    s = m.sum()
    if s > 0:
        m /= s
    return m

def get_1x2_probs(matrix):
    home = np.tril(matrix, -1).sum()
    draw = np.trace(matrix)
    away = np.triu(matrix, 1).sum()
    return home, draw, away

def predict_mt_ft(home_stats, away_stats):
    # Calcul des forces croisées (Attaque vs Défense adverse)
    lam_h_ft = max(0.2, (home_stats["ft_for"] + away_stats["ft_against"]) / 2)
    lam_a_ft = max(0.2, (away_stats["ft_for"] + home_stats["ft_against"]) / 2)
    
    lam_h_ht = max(0.1, (home_stats["ht_for"] + away_stats["ht_against"]) / 2)
    lam_a_ht = max(0.1, (away_stats["ht_for"] + home_stats["ht_against"]) / 2)

    # Simulation empirique de la seconde période (Modèle Dixon-Coles simplifié)
    lam_h_st = max(0.2, lam_h_ft - lam_h_ht)
    lam_a_st = max(0.2, lam_a_ft - lam_a_ht)

    # Obtention des probabilités sur chaque période
    m_ht = generate_half_matrix(lam_h_ht, lam_a_ht)
    m_st = generate_half_matrix(lam_h_st, lam_a_st)

    h_m1, d_m1, a_m1 = get_1x2_probs(m_ht)
    h_m2, d_m2, a_m2 = get_1x2_probs(m_st)

    # Matrice combinée Mi-Temps / Fin du Match (MT/FT)
    scenarios = {
        "1/1": h_m1 * h_m2, "1/X": h_m1 * d_m2, "1/2": h_m1 * a_m2,
        "X/1": d_m1 * h_m2, "X/X": d_m1 * d_m2, "X/2": d_m1 * a_m2,
        "2/1": a_m1 * h_m2, "2/X": a_m1 * d_m2, "2/2": a_m1 * a_m2
    }
    
    # Normalisation mathématique stricte
    total_s = sum(scenarios.values())
    for k in scenarios:
        scenarios[k] = (scenarios[k] / total_s) * 100

    # Évaluation de la pertinence (Index de Confiance Analytique)
    sample_factor = min(1.0, (home_stats["n_matches"] + away_stats["n_matches"]) / 16)
    max_prob = max(scenarios.values())
    confidence_score = 65 + (max_prob * 0.4) + (sample_factor * 15)
    confidence_score = min(100.0, confidence_score)

    if confidence_score >= 95: label, color = "🔥 SIGNAL EXCEPTIONNEL", "error"
    elif confidence_score >= 90: label, color = "🟢 SIGNAL TRÈS FORT", "success"
    elif confidence_score >= 80: label, color = "🟢 SIGNAL FORT", "success"
    else: label, color = "🔴 PRUDENCE / PAS DE PARI", "warning"

    return scenarios, round(confidence_score, 1), label, color, (lam_h_ft, lam_a_ft)

# ============================================================
# INTERFACE STREAMLIT UTILSATEUR
# ============================================================
st.title("⚽ Rodrigue MT/FT PRO")
st.caption("Modélisation statistique de Poisson prédictive pour les marchés Mi-Temps / Fin du Match.")

# Paramètres généraux en barre latérale
with st.sidebar:
    st.header("⚙️ Configuration")
    target_date = st.date_input("Date d'analyse :", date(2026, 8, 26))
    selected_comps = st.multiselect(
        "Compétitions cibles :", 
        list(COMPETITIONS.keys()), 
        default=["PL", "SA", "PD", "FL1"],
        format_func=lambda x: COMPETITIONS[x]
    )

date_str = target_date.strftime("%Y-%m-%d")

with st.spinner("Analyse du calendrier Football-Data.org..."):
    matches = get_matches_for_date(date_str, selected_comps)

if not matches:
    st.info(f"Aucun match de football programmé pour le {date_str} dans les championnats sélectionnés.")
else:
    st.subheader(f"📅 Analyses des rencontres du {date_str}")
    
    for match in matches:
        home_team = match.get("homeTeam", {})
        away_team = match.get("awayTeam", {})
        comp_info = match.get("competition", {})
        
        h_id, h_name = home_team.get("id"), home_team.get("name")
        a_id, a_name = away_team.get("id"), away_team.get("name")
        
        if not h_id or not a_id:
            continue
            
        with st.expander(f"📊 {comp_info.get('name')} : {h_name} — {a_name}"):
            # Récupération historique des données
            h_hist = get_team_history(h_id, date_str)
            a_hist = get_team_history(a_id, date_str)
            
            h_stats = calculate_team_stats(h_hist, h_id)
            a_stats = calculate_team_stats(a_hist, a_id)
            
            if h_stats["n_matches"] < 3 or a_stats["n_matches"] < 3:
