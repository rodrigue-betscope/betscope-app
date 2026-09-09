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

    # Part moyenne des buts attendus avant la pause.
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

    # suppression des doublons
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

    # --------------------------------------------------------
    # Attaque
    # --------------------------------------------------------

    home_attack = (
        0.55 * home_form["gf_avg"] +
        0.45 * home_split["gf_avg"]
    )

    away_attack = (
        0.55 * away_form["gf_avg"] +
        0.45 * away_split["gf_avg"]
    )

    # --------------------------------------------------------
    # Défense adverse
    # --------------------------------------------------------

    home_defense_weakness = (
        0.55 * away_form["ga_avg"] +
        0.45 * away_split["ga_avg"]
    )

    away_defense_weakness = (
        0.55 * home_form["ga_avg"] +
        0.45 * home_split["ga_avg"]
    )

    # --------------------------------------------------------
    # Modèle de base
    # --------------------------------------------------------

    home_lambda = (
        0.58 * home_attack +
        0.42 * home_defense_weakness
    )

    away_lambda = (
        0.58 * away_attack +
        0.42 * away_defense_weakness
    )

    # Avantage domicile
    home_lambda *= 1.08
    away_lambda *= 0.94

    # --------------------------------------------------------
    # Forme récente
    # --------------------------------------------------------

    home_lambda *= (
        0.92 +
        0.16 * home_form["form_score"]
    )

    away_lambda *= (
        0.92 +
        0.16 * away_form["form_score"]
    )

    # --------------------------------------------------------
    # Classement
    # --------------------------------------------------------

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

    # résultat principal
    result_probs = {
        "Victoire domicile": p1,
        "Match nul": px,
        "Victoire extérieur": p2
    }

    main_result = max(
        result_probs,
        key=result_probs.get
    )

    # score exact
    best_score = exact_scores[0][0]

    # MT/FT
    best_htft = htft[0][0]

    # lecture humaine
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
            "L'équipe extérieure présente le meilleur signal "
            "global malgré le désavantage du terrain."
        )

    else:
        reading = (
            "Les signaux sont partagés : prudence sur le 1X2 "
            "et préférence pour un marché de couverture."
        )

    # buts
    if markets["Under 2.5"] >= 0.60:
        goals_reading = "Tendance vers un match fermé."
    elif markets["Over 2.5"] >= 0.60:
        goals_reading = "Tendance vers un match ouvert."
    else:
        goals_reading = "Total de buts difficile à trancher."

    return {
        "main_result": main_result,
        "best_score": best_score,
        "best_htft": best_htft,
        "reading": reading,
        "goals_reading": goals_reading
    }


# ============================================================
# ANALYSE D'UN MATCH
# ============================================================

def analyze_match(match):

    home = match.get("homeTeam", {})
    away = match.get("awayTeam", {})

    home_id = home.get("id")
    away_id = away.get("id")

    home_name = home.get("name", "Domicile")
    away_name = away.get("name", "Extérieur")

    competition = (
        match.get("competition", {})
        .get("name", "")
    )

    # historique
    home_history = fetch_team_history(home_id, 12)
    away_history = fetch_team_history(away_id, 12)

    home_form = analyze_form(
        home_history,
        home_id,
        8
    )

    away_form = analyze_form(
        away_history,
        away_id,
        8
    )

    home_split = analyze_home_away(
        home_history,
        home_id,
        home=True,
        last_n=8
    )

    away_split = analyze_home_away(
        away_history,
        away_id,
        home=False,
        last_n=8
    )

    # classement
    competition_code = (
        match.get("competition", {})
        .get("code")
    )

    table = []

    if competition_code:
        table = fetch_standings(
            competition_code
        )

    standing_home = get_team_standing(
        table,
        home_id
    )

    standing_away = get_team_standing(
        table,
        away_id
    )

    # lambdas
    home_lambda, away_lambda = build_lambdas(
        home_form,
        away_form,
        home_split,
        away_split,
        standing_home,
        standing_away
    )

    # informations web
    match_date = match.get(
        "utcDate",
        ""
    )[:10]

    home_news = search_team_information(
        home_name,
        match_date
    )

    away_news = search_team_information(
        away_name,
        match_date
    )

    home_info = classify_information(
        home_news
    )

    away_info = classify_information(
        away_news
    )

    # correction contextuelle
    home_lambda, away_lambda = human_context_adjustment(
        home_lambda,
        away_lambda,
        home_info,
        away_info
    )

    # matrice
    matrix = poisson_matrix(
        home_lambda,
        away_lambda,
        7
    )

    markets = calculate_markets(
        matrix
    )

    exact_scores = top_exact_scores(
        matrix,
        8
    )

    ht = calculate_half_time(
        home_lambda,
        away_lambda
    )

    htft = calculate_htft(
        home_lambda,
        away_lambda
    )

    verdict = human_verdict(
        home_name,
        away_name,
        markets,
        exact_scores,
        htft,
        home_form,
        away_form,
        home_lambda,
        away_lambda
    )

    return {
        "home": home_name,
        "away": away_name,
        "competition": competition,
        "home_form": home_form,
        "away_form": away_form,
        "home_split": home_split,
        "away_split": away_split,
        "standing_home": standing_home,
        "standing_away": standing_away,
        "home_lambda": home_lambda,
        "away_lambda": away_lambda,
        "markets": markets,
        "exact_scores": exact_scores,
        "ht": ht,
        "htft": htft,
        "home_info": home_info,
        "away_info": away_info,
        "verdict": verdict
    }


# ============================================================
# AFFICHAGE FORM
# ============================================================

def form_string(form):

    chars = []

    for r in form["results"]:
        chars.append(r["result"])

    return " ".join(chars)


# ============================================================
# INTERFACE
# ============================================================

st.title("⚽ RODRIGUE PRO FOOTBALL AI — V9")

st.markdown(
    """
### 🧠 Analyse Football : données réelles + modèle Poisson + lecture humaine

Le programme combine :
- forme récente ;
- buts marqués et encaissés ;
- rendement domicile/extérieur ;
- classement ;
- contexte d'absences et suspensions trouvé sur le Web ;
- probabilités 1X2 ;
- Double Chance ;
- BTTS ;
- Over/Under ;
- scores exacts ;
- score à la mi-temps ;
- MT/FT ;
- synthèse finale.
"""
)

st.warning(
    "Les résultats sont des probabilités calculées à partir des données disponibles. "
    "Les informations d'absences issues du Web doivent être vérifiées avant utilisation."
)


# ============================================================
# PARAMÈTRES
# ============================================================

col1, col2 = st.columns(2)

with col1:
    selected_date = st.date_input(
        "📅 Date des matchs",
        value=date.today()
    )

with col2:
    selected_competitions = st.multiselect(
        "🏆 Compétitions",
        options=list(COMPETITIONS.keys()),
        default=[
            "Premier League",
            "LaLiga",
            "Bundesliga",
            "Serie A",
            "Ligue 1"
        ]
    )


competition_codes = [
    COMPETITIONS[x]
    for x in selected_competitions
]


# ============================================================
# BOUTON
# ============================================================

if st.button(
    "🚀 LANCER L'ANALYSE",
    type="primary",
    use_container_width=True
):

    with st.spinner(
        "🔎 Recherche des matchs et analyse en cours..."
    ):

        matches = fetch_matches(
            selected_date,
            competition_codes
        )

    if not matches:

        st.error(
            "❌ Aucun match disponible pour cette date "
            "dans les compétitions sélectionnées."
        )

        st.info(
            "Vérifie la date et les compétitions sélectionnées."
        )

    else:

        st.success(
            f"✅ {len(matches)} match(s) trouvé(s)."
        )

        st.session_state["matches"] = matches


# ============================================================
# AFFICHAGE
# ============================================================

if "matches" in st.session_state:

    matches = st.session_state["matches"]

    st.subheader("📋 Matchs disponibles")

    for i, match in enumerate(matches):

        home = match.get(
            "homeTeam", {}
        ).get("name", "?")

        away = match.get(
            "awayTeam", {}
        ).get("name", "?")

        competition = match.get(
            "competition", {}
        ).get("name", "")

        utc = match.get(
            "utcDate",
            ""
        )

        with st.expander(
            f"⚽ {home} — {away} | {competition}"
        ):

            if utc:
                st.caption(
                    f"Date UTC : {utc}"
                )

            if st.button(
                f"🔬 Analyser {home} — {away}",
                key=f"analyse_{i}"
            ):

                with st.spinner(
                    "🧠 Analyse approfondie..."
                ):

                    result = analyze_match(
                        match
                    )

                # ------------------------------------------------
                # TITRE
                # ------------------------------------------------

                st.markdown(
                    f"# ⚽ {result['home']} — {result['away']}"
                )

                st.markdown(
                    f"**Compétition :** {result['competition']}"
                )

                # ------------------------------------------------
                # LAMBDAS
                # ------------------------------------------------

                c1, c2, c3 = st.columns(3)

                c1.metric(
                    "xG modèle domicile",
                    f"{result['home_lambda']:.2f}"
                )

                c2.metric(
                    "xG modèle extérieur",
                    f"{result['away_lambda']:.2f}"
                )

                c3.metric(
                    "Total buts attendu",
                    f"{result['home_lambda'] + result['away_lambda']:.2f}"
                )

                # ------------------------------------------------
                # FORME
                # ------------------------------------------------

                st.subheader("📈 Forme récente")

                f1, f2 = st.columns(2)

                with f1:

                    st.markdown(
                        f"### 🏠 {result['home']}"
                    )

                    st.write(
                        f"Forme : **{form_string(result['home_form'])}**"
                    )

                    st.write(
                        f"Victoires : {result['home_form']['wins']}"
                    )

                    st.write(
                        f"Nuls : {result['home_form']['draws']}"
                    )

                    st.write(
                        f"Défaites : {result['home_form']['losses']}"
                    )

                    st.write(
                        f"Buts : "
                        f"{result['home_form']['gf']} pour / "
                        f"{result['home_form']['ga']} contre"
                    )

                with f2:

                    st.markdown(
                        f"### ✈️ {result['away']}"
                    )

                    st.write(
                        f"Forme : **{form_string(result['away_form'])}**"
                    )

                    st.write(
                        f"Victoires : {result['away_form']['wins']}"
                    )

                    st.write(
                        f"Nuls : {result['away_form']['draws']}"
                    )

                    st.write(
                        f"Défaites : {result['away_form']['losses']}"
                    )

                    st.write(
                        f"Buts : "
                        f"{result['away_form']['gf']} pour / "
                        f"{result['away_form']['ga']} contre"
                    )

                # ------------------------------------------------
                # CLASSEMENT
                # ------------------------------------------------

                st.subheader("🏆 Classement")

                s1, s2 = st.columns(2)

                with s1:

                    if result["standing_home"]:
                        row = result["standing_home"]

                        st.write(
                            f"**{result['home']}**"
                        )

                        st.write(
                            f"Position : {row.get('position', '-')}"
                        )

                        st.write(
                            f"Points : {row.get('points', '-')}"
                        )

                        st.write(
                            f"Différence : "
                            f"{row.get('goalDifference', '-')}"
                        )

                    else:
                        st.info(
                            "Classement non disponible."
                        )

                with s2:

                    if result["standing_away"]:
                        row = result["standing_away"]

                        st.write(
                            f"**{result['away']}**"
                        )

                        st.write(
                            f"Position : {row.get('position', '-')}"
                        )

                        st.write(
                            f"Points : {row.get('points', '-')}"
                        )

                        st.write(
                            f"Différence : "
                            f"{row.get('goalDifference', '-')}"
                        )

                    else:
                        st.info(
                            "Classement non disponible."
                        )

                # ------------------------------------------------
                # 1X2
                # ------------------------------------------------

                st.subheader("🎯 1X2")

                markets = result["markets"]

                table = pd.DataFrame({
                    "Marché": [
                        "Victoire domicile",
                        "Match nul",
                        "Victoire extérieur",
                        "Double Chance 1X",
                        "Double Chance X2",
                        "Double Chance 12",
                    ],
                    "Probabilité": [
                        markets["1"],
                        markets["X"],
                        markets["2"],
                        markets["1X"],
                        markets["X2"],
                        markets["12"],
                    ]
                })

                table["Probabilité"] = (
                    table["Probabilité"] * 100
                ).round(2).astype(str) + "%"

                st.dataframe(
                    table,
                    use_container_width=True,
                    hide_index=True
                )

                # ------------------------------------------------
                # BUTS
                # ------------------------------------------------

                st.subheader("⚽ Marchés de buts")

                goals_table = pd.DataFrame({
                    "Marché": [
                        "BTTS Oui",
                        "BTTS Non",
                        "Over 1.5",
                        "Under 1.5",
                        "Over 2.5",
                        "Under 2.5",
                        "Over 3.5",
                        "Under 3.5"
                    ],
                    "Probabilité": [
                        markets["BTTS Oui"],
                        markets["BTTS Non"],
                        markets["Over 1.5"],
                        markets["Under 1.5"],
                        markets["Over 2.5"],
                        markets["Under 2.5"],
                        markets["Over 3.5"],
                        markets["Under 3.5"]
                    ]
                })

                goals_table["Probabilité"] = (
                    goals_table["Probabilité"] * 100
                ).round(2).astype(str) + "%"

                st.dataframe(
                    goals_table,
                    use_container_width=True,
                    hide_index=True
                )

                # ------------------------------------------------
                # SCORES EXACTS
                # ------------------------------------------------

                st.subheader("🔢 Scores exacts les plus probables")

                score_table = pd.DataFrame(
                    result["exact_scores"],
                    columns=[
                        "Score",
                        "Probabilité"
                    ]
                )

                score_table["Probabilité"] = (
                    score_table["Probabilité"] * 100
                ).round(2).astype(str) + "%"

                st.dataframe(
                    score_table,
                    use_container_width=True,
                    hide_index=True
                )

                # ------------------------------------------------
                # MI-TEMPS
                # ------------------------------------------------

                st.subheader("⏱️ Mi-temps")

                ht_scores = pd.DataFrame(
                    result["ht"]["scores"],
                    columns=[
                        "Score MT",
                        "Probabilité"
                    ]
                )

                ht_scores["Probabilité"] = (
                    ht_scores["Probabilité"] * 100
                ).round(2).astype(str) + "%"

                st.dataframe(
                    ht_scores,
                    use_container_width=True,
                    hide_index=True
                )

                # ------------------------------------------------
                # MT/FT
                # ------------------------------------------------

                st.subheader("🔄 Mi-temps / Fin du match")

                htft_table = pd.DataFrame(
                    result["htft"],
                    columns=[
                        "MT/FT",
                        "Probabilité"
                    ]
                )

                htft_table["Probabilité"] = (
                    htft_table["Probabilité"] * 100
                ).round(2).astype(str) + "%"

                st.dataframe(
                    htft_table,
                    use_container_width=True,
                    hide_index=True
                )

                # ------------------------------------------------
                # ABSENCES
                # ------------------------------------------------

                st.subheader(
                    "🚑 Blessures / absences / suspensions"
                )

                a1, a2 = st.columns(2)

                with a1:

                    st.markdown(
                        f"### {result['home']}"
                    )

                    if result["home_info"]:

                        for info in result["home_info"][:8]:

                            st.write(
                                "• " +
                                info["title"]
                            )

                            if info["snippet"]:
                                st.caption(
                                    info["snippet"]
                                )

                    else:

                        st.info(
                            "Aucune information exploitable trouvée."
                        )

                with a2:

                    st.markdown(
                        f"### {result['away']}"
                    )

                    if result["away_info"]:

                        for info in result["away_info"][:8]:

                            st.write(
                                "• " +
                                info["title"]
                            )

                            if info["snippet"]:
                                st.caption(
                                    info["snippet"]
                                )

                    else:

                        st.info(
                            "Aucune information exploitable trouvée."
                        )

                # ------------------------------------------------
                # SYNTHÈSE HUMAINE
                # ------------------------------------------------

                st.subheader("🧠 SYNTHÈSE RODRIGUE PRO")

                verdict = result["verdict"]

                st.success(
                    f"🎯 Résultat principal : "
                    f"**{verdict['main_result']}**"
                )

                st.info(
                    f"🔢 Score exact principal : "
                    f"**{verdict['best_score']}**"
                )

                st.info(
                    f"⏱️ MT/FT principal : "
                    f"**{verdict['best_htft']}**"
                )

                st.write(
                    f"**Lecture humaine :** "
                    f"{verdict['reading']}"
                )

                st.write(
                    f"**Lecture buts :** "
                    f"{verdict['goals_reading']}"
                )

                # ------------------------------------------------
                # TOP CHOIX
                # ------------------------------------------------

                st.subheader("🔥 TOP CHOIX")

                top_market = max(
                    markets.items(),
                    key=lambda x: x[1]
                )

                c1, c2, c3 = st.columns(3)

                c1.metric(
                    "Marché le plus fort",
                    top_market[0],
                    f"{top_market[1] * 100:.1f}%"
                )

                c2.metric(
                    "Score exact",
                    verdict["best_score"]
                )

                c3.metric(
                    "MT/FT",
                    verdict["best_htft"]
                )

                st.divider()

                st.caption(
                    "Rodrigue Pro Football AI V9 — "
                    "analyse basée sur les données disponibles "
                    "et une combinaison modèle statistique + lecture contextuelle."
                )
