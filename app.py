# ============================================================
# RODRIGUE PRO FOOTBALL AI — V9
# Football-data.org + SerpApi
# Analyse humaine + modèle statistique
# Compatible Pydroid 3 / Streamlit / RStudio
# ============================================================

import math
import re
from datetime import date, timedelta

import numpy as np
import pandas as pd
import requests
import streamlit as st


# ============================================================
# CONFIGURATION
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
    page_title="Rodrigue Pro Football AI V9",
    page_icon="⚽",
    layout="wide"
)


# ============================================================
# SESSION HTTP
# ============================================================

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "Rodrigue-Pro-Football-AI/9.0"
})


# ============================================================
# FOOTBALL-DATA.ORG
# ============================================================

def football_get(endpoint, params=None):
    url = f"{API_BASE}{endpoint}"

    try:
        response = SESSION.get(
            url,
            headers={"X-Auth-Token": FOOTBALL_DATA_KEY},
            params=params or {},
            timeout=25
        )

        if response.status_code == 200:
            return response.json()

        if response.status_code == 429:
            st.warning("⚠️ Limite de requêtes football-data.org atteinte.")
            return None

        if response.status_code == 403:
            st.error("❌ Clé football-data.org refusée.")
            return None

        st.warning(
            f"⚠️ football-data.org HTTP {response.status_code}"
        )
        return None

    except requests.RequestException as e:
        st.error(f"❌ Erreur réseau : {e}")
        return None


# ============================================================
# SERPAPI
# ============================================================

def serp_search(query, num=8):
    params = {
        "engine": "google",
        "q": query,
        "api_key": SERPAPI_KEY,
        "hl": "fr",
        "gl": "cm",
        "num": num
    }

    try:
        response = SESSION.get(
            SERP_URL,
            params=params,
            timeout=25
        )

        if response.status_code != 200:
            return []

        data = response.json()

        return data.get("organic_results", [])

    except requests.RequestException:
        return []


# ============================================================
# MATCHES DU JOUR
# ============================================================

def fetch_matches(selected_date, competition_codes):
    params = {
        "dateFrom": selected_date.isoformat(),
        "dateTo": selected_date.isoformat(),
    }

    if competition_codes:
        params["competitions"] = ",".join(competition_codes)

    data = football_get("/matches", params)

    if not data:
        return []

    return data.get("matches", [])


# ============================================================
# HISTORIQUE D'UNE ÉQUIPE
# ============================================================

@st.cache_data(ttl=900)
def fetch_team_history(team_id, limit=12):
    data = football_get(
        f"/teams/{team_id}/matches",
        {
            "status": "FINISHED",
            "limit": limit
        }
    )

    if not data:
        return []

    return data.get("matches", [])


# ============================================================
# CLASSEMENT
# ============================================================

@st.cache_data(ttl=1800)
def fetch_standings(competition_code):
    data = football_get(
        f"/competitions/{competition_code}/standings"
    )

    if not data:
        return []

    standings = data.get("standings", [])

    if not standings:
        return []

    table = standings[0].get("table", [])

    return table


# ============================================================
# RÉSULTAT D'UN MATCH POUR UNE ÉQUIPE
# ============================================================

def team_result(match, team_id):
    home = match.get("homeTeam", {})
    away = match.get("awayTeam", {})
    score = match.get("score", {})
    full = score.get("fullTime", {})

    hg = full.get("home")
    ag = full.get("away")

    if hg is None or ag is None:
        return None

    if home.get("id") == team_id:
        gf = hg
        ga = ag
    elif away.get("id") == team_id:
        gf = ag
        ga = hg
    else:
        return None

    if gf > ga:
        result = "W"
    elif gf == ga:
        result = "D"
    else:
        result = "L"

    return {
        "result": result,
        "gf": gf,
        "ga": ga,
        "date": match.get("utcDate", ""),
        "opponent": (
            away.get("name")
            if home.get("id") == team_id
            else home.get("name")
        )
    }


# ============================================================
# FORME RÉCENTE
# ============================================================

def analyze_form(matches, team_id, last_n=8):

    results = []

    for match in matches:
        r = team_result(match, team_id)

        if r:
            results.append(r)

    results = sorted(
        results,
        key=lambda x: x["date"],
        reverse=True
    )[:last_n]

    if not results:
        return {
            "matches": 0,
            "wins": 0,
            "draws": 0,
            "losses": 0,
            "gf": 0,
            "ga": 0,
            "gf_avg": 0.0,
            "ga_avg": 0.0,
            "points_avg": 0.0,
            "form_score": 0.0,
            "results": []
        }

    wins = sum(r["result"] == "W" for r in results)
    draws = sum(r["result"] == "D" for r in results)
    losses = sum(r["result"] == "L" for r in results)

    gf = sum(r["gf"] for r in results)
    ga = sum(r["ga"] for r in results)

    points = (
        wins * 3 +
        draws
    )

    form_score = points / (len(results) * 3)

    return {
        "matches": len(results),
        "wins": wins,
        "draws": draws,
        "losses": losses,
        "gf": gf,
        "ga": ga,
        "gf_avg": gf / len(results),
        "ga_avg": ga / len(results),
        "points_avg": points / len(results),
        "form_score": form_score,
        "results": results
    }


# ============================================================
# FORME DOMICILE / EXTÉRIEUR
# ============================================================

def analyze_home_away(matches, team_id, home=True, last_n=8):

    filtered = []

    for match in matches:
        home_id = match.get("homeTeam", {}).get("id")
        away_id = match.get("awayTeam", {}).get("id")

        if home and home_id == team_id:
            filtered.append(match)

        elif not home and away_id == team_id:
            filtered.append(match)

    return analyze_form(filtered, team_id, last_n)


# ============================================================
# POISSON
# ============================================================

def poisson_probability(lam, goals):
    return (
        math.exp(-lam) *
        (lam ** goals) /
        math.factorial(goals)
    )


def poisson_matrix(home_lambda, away_lambda, max_goals=7):

    matrix = np.zeros(
        (max_goals + 1, max_goals + 1)
    )

    for h in range(max_goals + 1):
        for a in range(max_goals + 1):
            matrix[h, a] = (
                poisson_probability(home_lambda, h) *
                poisson_probability(away_lambda, a)
            )

    total = matrix.sum()

    if total > 0:
        matrix /= total

    return matrix


# ============================================================
# MARCHÉS
# ============================================================

def calculate_markets(matrix):

    max_goals = matrix.shape[0] - 1

    home_win = 0
    draw = 0
    away_win = 0

    btts_yes = 0
    over15 = 0
    over25 = 0
    over35 = 0

    for h in range(max_goals + 1):
        for a in range(max_goals + 1):

            p = matrix[h, a]

            if h > a:
                home_win += p
            elif h == a:
                draw += p
            else:
                away_win += p

            if h >= 1 and a >= 1:
                btts_yes += p

            if h + a >= 2:
                over15 += p

            if h + a >= 3:
                over25 += p

            if h + a >= 4:
                over35 += p

    under15 = 1 - over15
    under25 = 1 - over25
    under35 = 1 - over35
    btts_no = 1 - btts_yes

    return {
        "1": home_win,
        "X": draw,
        "2": away_win,
        "1X": home_win + draw,
        "X2": draw + away_win,
        "12": home_win + away_win,
        "BTTS Oui": btts_yes,
        "BTTS Non": btts_no,
        "Over 1.5": over15,
        "Under 1.5": under15,
        "Over 2.5": over25,
        "Under 2.5": under25,
        "Over 3.5": over35,
        "Under 3.5": under35,
    }


# ============================================================
# SCORES EXACTS
# ============================================================

def top_exact_scores(matrix, n=8):

    scores = []

    for h in range(matrix.shape[0]):
        for a in range(matrix.shape[1]):
            scores.append(
                (
                    f"{h}-{a}",
                    float(matrix[h, a])
                )
            )

    scores.sort(
        key=lambda x: x[1],
        reverse=True
    )

    return scores[:n]


# ============================================================
# MI-TEMPS
# ============================================================

def calculate_half_time(home_lambda, away_lambda):

    ht_home = home_lambda * 0.44
    ht_away = away_lambda * 0.44

    matrix = poisson_matrix(
        ht_home,
        ht_away,
        max_goals=5
    )

    markets = calculate_markets(matrix)

    scores = top_exact_scores(matrix, 6)

    return {
        "matrix": matrix,
        "markets": markets,
        "scores": scores
    }


# ============================================================
# MT/FT
# ============================================================

def calculate_htft(home_lambda, away_lambda):

    ht = calculate_half_time(
        home_lambda,
        away_lambda
    )

    ht_matrix = ht["matrix"]

    ft_matrix = poisson_matrix(
        home_lambda,
        away_lambda,
        max_goals=7
    )

    combinations = {
        "1/1": 0.0,
        "1/X": 0.0,
        "1/2": 0.0,
        "X/1": 0.0,
        "X/X": 0.0,
        "X/2": 0.0,
        "2/1": 0.0,
        "2/X": 0.0,
        "2/2": 0.0
    }

    for hh in range(ht_matrix.shape[0]):
        for ha in range(ht_matrix.shape[1]):

            ht_p = ht_matrix[hh, ha]

            if ht_p <= 0:
                continue

            ht_result = (
                "1" if hh > ha
                else "X" if hh == ha
                else "2"
            )

            for fh in range(ft_matrix.shape[0]):
                for fa in range(ft_matrix.shape[1]):

                    ft_p = ft_matrix[fh, fa]

                    if ft_p <= 0:
                        continue

                    ft_result = (
                        "1" if fh > fa
                        else "X" if fh == fa
                        else "2"
                    )

                    key = f"{ht_result}/{ft_result}"

                    combinations[key] += (
                        ht_p * ft_p
                    )

    total = sum(combinations.values())

    if total > 0:
        combinations = {
            k: v / total
            for k, v in combinations.items()
        }

    ranked = sorted(
        combinations.items(),
        key=lambda x: x[1],
        reverse=True
    )

    return ranked


# ============================================================
# INFORMATIONS HUMAINES : BLESSURES / ABSENCES
# ============================================================

def search_team_information(team_name, match_date):

    queries = [
        f'"{team_name}" blessures absents suspendus football {match_date}',
        f'"{team_name}" injuries suspensions absences football {match_date}',
        f'"{team_name}" probable lineup football {match_date}',
        f'"{team_name}" composition probable {match_date}',
    ]

    results = []

    for query in queries:
        found = serp_search(query, num=5)

        for item in found:
            results.append({
                "title": item.get("title", ""),
                "snippet": item.get("snippet", ""),
                "link": item.get("link", "")
            })

    unique = {}

    for item in results:
        key = (
            item["title"],
            item["snippet"]
        )

        unique[key] = item

    return list(unique.values())


# ============================================================
# CLASSIFICATION DES INFORMATIONS
# ============================================================

def classify_information(results):

    injury_words = [
        "injury",
        "injured",
        "blessé",
        "blessure",
        "blessés",
        "indisponible",
        "indisponibles",
        "forfait",
        "forfaits"
    ]

    suspension_words = [
        "suspendu",
        "suspension",
        "suspended",
        "carton rouge",
        "red card"
    ]

    absence_words = [
        "absent",
        "absence",
        "out",
        "manquera",
        "miss",
        "unavailable"
    ]

    classified = []

    for item in results:

        text = (
            item["title"] +
            " " +
            item["snippet"]
        ).lower()

        categories = []

        if any(w in text for w in injury_words):
            categories.append("Blessure")

        if any(w in text for w in suspension_words):
            categories.append("Suspension")

        if any(w in text for w in absence_words):
            categories.append("Absence")

        if categories:
            classified.append({
                **item,
                "categories": categories
            })

    return classified


# ============================================================
# AJUSTEMENT HUMAIN
# ============================================================

def human_context_adjustment(
    base_home,
    base_away,
    home_info,
    away_info
):

    home_penalty = 0.0
    away_penalty = 0.0

    home_text = " ".join(
        x["title"] + " " + x["snippet"]
        for x in home_info
    ).lower()

    away_text = " ".join(
        x["title"] + " " + x["snippet"]
        for x in away_info
    ).lower()

    strong_absence = [
        "key player",
        "star player",
        "meilleur buteur",
        "capitaine",
        "principal attaquant",
        "top scorer",
        "important player"
    ]

    for word in strong_absence:

        if word in home_text:
            home_penalty += 0.04

        if word in away_text:
            away_penalty += 0.04

    home_lambda = base_home * (
        1 - min(home_penalty, 0.15)
    )

    away_lambda = base_away * (
        1 - min(away_penalty, 0.15)
    )

    return max(home_lambda, 0.15), max(away_lambda, 0.15)


# ============================================================
# CONSTRUCTION DES LAMBDAS
# ============================================================

def build_lambdas(
    home_form,
    away_form,
    home_split,
    away_split,
    standings_home=None,
    standings_away=None
):

    home_attack = (
        0.55 * home_form["gf_avg"] +
        0.45 * home_split["gf_avg"]
    )

    away_attack = (
        0.55 * away_form["gf_avg"] +
        0.45 * away_split["gf_avg"]
    )

    home_defense_weakness = (
        0.55 * away_form["ga_avg"] +
        0.45 * away_split["ga_avg"]
    )

    away_defense_weakness = (
        0.55 * home_form["ga_avg"] +
        0.45 * home_split["ga_avg"]
    )

    home_lambda = (
        0.58 * home_attack +
        0.42 * home_defense_weakness
    )

    away_lambda = (
        0.58 * away_attack +
        0.42 * away_defense_weakness
    )

    home_lambda *= 1.08
    away_lambda *= 0.94

    home_lambda *= (
        0.92 +
        0.16 * home_form["form_score"]
    )

    away_lambda *= (
        0.92 +
        0.16 * away_form["form_score"]
    )

    if standings_home and standings_away:

        hp = standings_home.get("position", 10)
        ap = standings_away.get("position", 10)

        if hp < ap:
            home_lambda *= 1.03
            away_lambda *= 0.98

        elif ap < hp:
            away_lambda *= 1.03
            home_lambda *= 0.98

    home_lambda = max(
        0.20,
        min(home_lambda, 3.80)
    )

    away_lambda = max(
        0.15,
        min(away_lambda, 3.50)
    )

    return home_lambda, away_lambda


# ============================================================
# CLASSEMENT — RECHERCHE ÉQUIPE
# ============================================================

def get_team_standing(table, team_id):

    for row in table:
        if row.get("team", {}).get("id") == team_id:
            return row

    return None


# ============================================================
# SCORE DE CONFIANCE
# ============================================================

def confidence_score(
    probability,
    form_matches,
    data_quality
):

    base = probability * 100

    if form_matches >= 8:
        base += 2

    elif form_matches >= 5:
        base += 1

    if data_quality >= 3:
        base += 2

    return min(99.0, max(1.0, base))


# ============================================================
# ANALYSE HUMAINE
# ============================================================

def human_verdict(
    home,
    away,
    markets,
    exact_scores,
    htft,
    home_form,
    away_form,
    home_lambda,
    away_lambda
):

    p1 = markets["1"]
    px = markets["X"]
    p2 = markets["2"]

    result_probs = {
        "Victoire domicile": p1,
        "Match nul": px,
        "Victoire extérieur": p2
    }

    main_result = max(
        result_probs,
        key=result_probs.get
    )

    best_score = exact_scores[0][0]
    best_htft = htft[0][0]

    gap = abs(p1 - p2)

    if gap < 0.08 and px >= 0.27:
        reading = (
            "Match très équilibré. "
            "Le nul mérite une attention particulière."
        )

    elif p1 > p2 and home_form["form_score"] >= away_form["form_score"]:
        reading = (
            "Avantage cohérent pour l'équipe à domicile : "
            "forme et avantage du terrain vont dans le même sens."
        )

    elif p2 > p1 and away_form["form_score"] >= home_form["form_score"]:
        reading = (
            "Attention au déplacement : "
            "l'équipe visiteuse affiche une meilleure dynamique."
        )

    else:
        reading = (
            "Configuration complexe. "
            "Les marchés secondaires (Double chance ou Over) sont privilégiés."
        )

    return {
        "main_result": main_result,
        "best_score": best_score,
        "best_htft": best_htft,
        "reading": reading
    }


# ============================================================
# INTERFACE STREAMLIT
# ============================================================

def main():
    st.sidebar.title("⚙️ Paramètres & Filtres")

    selected_date = st.sidebar.date_input(
        "Date des matchs",
        value=date.today()
    )

    selected_competitions = st.sidebar.multiselec
