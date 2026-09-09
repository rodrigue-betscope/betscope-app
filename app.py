# ============================================================
# RODRIGUE PRO FOOTBALL AI — V10 ULTIMATE
# ============================================================
# Sources :
#   - football-data.org : matchs, résultats, classement
#   - SerpApi / Google : contexte, blessures, suspensions,
#     statistiques détaillées et événements disponibles sur le Web
#
# Analyse :
#   - Forme récente
#   - Domicile / extérieur
#   - Classement
#   - Buts
#   - Poisson
#   - 1X2 / Double Chance
#   - BTTS
#   - Over / Under
#   - Scores exacts
#   - Mi-temps
#   - MT/FT
#   - Corners
#   - Cartons
#   - Tirs
#   - Tirs cadrés
#   - Possession
#   - Fautes
#   - Hors-jeu
#   - Blessures / absences / suspensions
#   - Lecture humaine finale
#
# Compatible :
#   - Pydroid 3
#   - Streamlit
#   - RStudio avec Python
# ============================================================

import math
import re
from datetime import date

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
    page_title="Rodrigue Pro Football AI V10",
    page_icon="⚽",
    layout="wide"
)

SESSION = requests.Session()

SESSION.headers.update({
    "User-Agent": "Rodrigue-Pro-Football-AI-V10"
})


# ============================================================
# OUTILS
# ============================================================

def safe_float(value):
    if value is None:
        return None

    try:
        return float(value)
    except:
        return None


def percent(value):
    if value is None:
        return "N/D"

    return f"{value * 100:.1f}%"


def number(value):
    if value is None:
        return "N/D"

    if isinstance(value, float):
        return f"{value:.2f}"

    return str(value)


# ============================================================
# FOOTBALL-DATA.ORG
# ============================================================

def football_get(endpoint, params=None):

    try:

        response = SESSION.get(
            API_BASE + endpoint,
            headers={
                "X-Auth-Token": FOOTBALL_DATA_KEY
            },
            params=params or {},
            timeout=25
        )

        if response.status_code == 200:
            return response.json()

        if response.status_code == 429:
            st.warning(
                "⚠️ Limite football-data.org atteinte."
            )
            return None

        if response.status_code == 403:
            st.error(
                "❌ Clé football-data.org refusée."
            )
            return None

        return None

    except requests.RequestException as error:

        st.warning(
            f"Erreur football-data.org : {error}"
        )

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

        return data.get(
            "organic_results",
            []
        )

    except requests.RequestException:

        return []


# ============================================================
# MATCHS (Corrigé et robuste)
# ============================================================

def fetch_matches(
    selected_date,
    competition_codes
):

    params = {
        "dateFrom": selected_date.isoformat(),
        "dateTo": selected_date.isoformat()
    }

    if competition_codes:
        params["competitions"] = ",".join(competition_codes)

    data = football_get(
        "/matches",
        params
    )

    if not data:
        return []

    matches = data.get("matches", [])

    # Si aucun match n'est retourné avec le filtre strict des compétitions, 
    # on tente un appel sans le filtre de compétition pour voir tous les matchs du jour disponibles sur le compte.
    if not matches and competition_codes:
        fallback_data = football_get(
            "/matches",
            {
                "dateFrom": selected_date.isoformat(),
                "dateTo": selected_date.isoformat()
            }
        )
        if fallback_data:
            all_matches = fallback_data.get("matches", [])
            # On filtre manuellement selon les compétitions demandées
            matches = [
                m for m in all_matches 
                if m.get("competition", {}).get("code") in competition_codes
            ]

    return matches


# ============================================================
# HISTORIQUE
# ============================================================

@st.cache_data(ttl=900)
def fetch_team_history(
    team_id,
    limit=12
):

    data = football_get(
        f"/teams/{team_id}/matches",
        {
            "status": "FINISHED",
            "limit": limit
        }
    )

    if not data:
        return []

    return data.get(
        "matches",
        []
    )


# ============================================================
# CLASSEMENT
# ============================================================

@st.cache_data(ttl=1800)
def fetch_standings(
    competition_code
):

    data = football_get(
        f"/competitions/{competition_code}/standings"
    )

    if not data:
        return []

    standings = data.get(
        "standings",
        []
    )

    if not standings:
        return []

    return standings[0].get(
        "table",
        []
    )


def get_standing(
    table,
    team_id
):

    for row in table:

        if row.get(
            "team",
            {}
        ).get("id") == team_id:

            return row

    return None


# ============================================================
# RÉSULTAT ÉQUIPE
# ============================================================

def team_result(
    match,
    team_id
):

    home = match.get(
        "homeTeam",
        {}
    )

    away = match.get(
        "awayTeam",
        {}
    )

    score = match.get(
        "score",
        {}
    )

    full = score.get(
        "fullTime",
        {}
    )

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
        "date": match.get(
            "utcDate",
            ""
        ),
        "opponent": (
            away.get("name")
            if home.get("id") == team_id
            else home.get("name")
        )
    }


# ============================================================
# FORME
# ============================================================

def analyze_form(
    matches,
    team_id,
    last_n=8
):

    results = []

    for match in matches:

        result = team_result(
            match,
            team_id
        )

        if result:
            results.append(result)

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
            "gf_avg": 0,
            "ga_avg": 0,
            "points": 0,
            "points_avg": 0,
            "form_score": 0,
            "results": []
        }

    wins = sum(
        x["result"] == "W"
        for x in results
    )

    draws = sum(
        x["result"] == "D"
        for x in results
    )

    losses = sum(
        x["result"] == "L"
        for x in results
    )

    gf = sum(
        x["gf"]
        for x in results
    )

    ga = sum(
        x["ga"]
        for x in results
    )

    points = wins * 3 + draws

    return {
        "matches": len(results),
        "wins": wins,
        "draws": draws,
        "losses": losses,
        "gf": gf,
        "ga": ga,
        "gf_avg": gf / len(results),
        "ga_avg": ga / len(results),
        "points": points,
        "points_avg": points / len(results),
        "form_score": points / (len(results) * 3),
        "results": results
    }


# ============================================================
# DOMICILE / EXTÉRIEUR
# ============================================================

def analyze_home_away(
    matches,
    team_id,
    home=True,
    last_n=8
):

    filtered = []

    for match in matches:

        home_id = match.get(
            "homeTeam",
            {}
        ).get("id")

        away_id = match.get(
            "awayTeam",
            {}
        ).get("id")

        if home and home_id == team_id:
            filtered.append(match)

        elif not home and away_id == team_id:
            filtered.append(match)

    return analyze_form(
        filtered,
        team_id,
        last_n
    )


# ============================================================
# POISSON
# ============================================================

def poisson_probability(
    lam,
    goals
):

    return (
        math.exp(-lam)
        * (lam ** goals)
        / math.factorial(goals)
    )


def poisson_matrix(
    home_lambda,
    away_lambda,
    max_goals=7
):

    matrix = np.zeros(
        (
            max_goals + 1,
            max_goals + 1
        )
    )

    for h in range(
        max_goals + 1
    ):

        for a in range(
            max_goals + 1
        ):

            matrix[h, a] = (
                poisson_probability(
                    home_lambda,
                    h
                )
                *
                poisson_probability(
                    away_lambda,
                    a
                )
            )

    total = matrix.sum()

    if total > 0:
        matrix /= total

    return matrix


# ============================================================
# MARCHÉS
# ============================================================

def calculate_markets(matrix):

    home_win = 0
    draw = 0
    away_win = 0

    btts = 0

    over15 = 0
    over25 = 0
    over35 = 0

    for h in range(
        matrix.shape[0]
    ):

        for a in range(
            matrix.shape[1]
        ):

            p = matrix[h, a]

            if h > a:
                home_win += p

            elif h == a:
                draw += p

            else:
                away_win += p

            if h >= 1 and a >= 1:
                btts += p

            if h + a >= 2:
                over15 += p

            if h + a >= 3:
                over25 += p

            if h + a >= 4:
                over35 += p

    return {

        "1": home_win,
        "X": draw,
        "2": away_win,

        "1X": home_win + draw,
        "X2": draw + away_win,
        "12": home_win + away_win,

        "BTTS Oui": btts,
        "BTTS Non": 1 - btts,

        "Over 1.5": over15,
        "Under 1.5": 1 - over15,

        "Over 2.5": over25,
        "Under 2.5": 1 - over25,

        "Over 3.5": over35,
        "Under 3.5": 1 - over35
    }


# ============================================================
# SCORES EXACTS
# ============================================================

def exact_scores(
    matrix,
    limit=10
):

    scores = []

    for h in range(
        matrix.shape[0]
    ):

        for a in range(
            matrix.shape[1]
        ):

            scores.append(
                (
                    f"{h}-{a}",
                    matrix[h, a]
                )
            )

    scores.sort(
        key=lambda x: x[1],
        reverse=True
    )

    return scores[:limit]


# ============================================================
# MI-TEMPS
# ============================================================

def half_time_model(
    home_lambda,
    away_lambda
):

    matrix = poisson_matrix(
        home_lambda * 0.44,
        away_lambda * 0.44,
        5
    )

    markets = calculate_markets(
        matrix
    )

    return {
        "matrix": matrix,
        "markets": markets,
        "scores": exact_scores(
            matrix,
            6
        )
    }


# ============================================================
# MT / FT
# ============================================================

def htft_model(
    home_lambda,
    away_lambda
):

    ht = half_time_model(
        home_lambda,
        away_lambda
    )

    ft = poisson_matrix(
        home_lambda,
        away_lambda,
        7
    )

    combinations = {}

    for ht_home in range(
        ht["matrix"].shape[0]
    ):

        for ht_away in range(
            ht["matrix"].shape[1]
        ):

            ht_probability = ht[
                "matrix"
            ][ht_home, ht_away]

            ht_result = (
                "1"
                if ht_home > ht_away
                else "X"
                if ht_home == ht_away
                else "2"
            )

            for ft_home in range(
                ft.shape[0]
            ):

                for ft_away in range(
                    ft.shape[1]
                ):

                    ft_probability = ft[
                        ft_home,
                        ft_away
                    ]

                    ft_result = (
                        "1"
                        if ft_home > ft_away
                        else "X"
                        if ft_home == ft_away
                        else "2"
                    )

                    key = (
                        f"{ht_result}/{ft_result}"
                    )

                    combinations[key] = (
                        combinations.get(
                            key,
                            0
                        )
                        +
                        ht_probability
                        * ft_probability
                    )

    total = sum(
        combinations.values()
    )

    if total:

        combinations = {
            k: v / total
            for k, v in combinations.items()
        }

    return sorted(
        combinations.items(),
        key=lambda x: x[1],
        reverse=True
    )


# ============================================================
# RECHERCHE STATISTIQUES DÉTAILLÉES
# ============================================================

STAT_QUERY_TYPES = {

    "corners": [
        "corners",
        "corner stats"
    ],

    "cartons": [
        "yellow cards",
        "red cards",
        "cartons"
    ],

    "tirs": [
        "shots",
        "tirs"
    ],

    "tirs_cadres": [
        "shots on target",
        "tirs cadrés"
    ],

    "possession": [
        "possession"
    ],

    "fautes": [
        "fouls",
        "fautes"
    ],

    "hors_jeu": [
        "offsides",
        "hors jeu"
    ]
}


def search_detailed_stats(
    team_name
):

    all_results = {}

    for stat_name, keywords in STAT_QUERY_TYPES.items():

        queries = []

        for keyword in keywords:

            queries.append(
                f'"{team_name}" football {keyword} statistics'
            )

        collected = []

        for query in queries:

            results = serp_search(
                query,
                num=5
            )

            for result in results:

                collected.append({
                    "title": result.get(
                        "title",
                        ""
                    ),
                    "snippet": result.get(
                        "snippet",
                        ""
                    ),
                    "link": result.get(
                        "link",
                        ""
                    )
                })

        unique = {}

        for item in collected:

            key = (
                item["title"],
                item["snippet"]
            )

            unique[key] = item

        all_results[stat_name] = list(
            unique.values()
        )[:10]

    return all_results


# ============================================================
# EXTRACTION DE NOMBRES
# ============================================================

def extract_numbers(text):

    if not text:
        return []

    pattern = r'(?<!\w)(\d+(?:[.,]\d+)?)(?!\w)'

    values = re.findall(
        pattern,
        text
    )

    numbers = []

    for value in values:

        try:

            numbers.append(
                float(
                    value.replace(
                        ",",
                        "."
                    )
                )
            )

        except:
            pass

    return numbers


# ============================================================
# LECTURE DES STATISTIQUES
# ============================================================

def summarize_stat_results(
    results
):

    if not results:

        return {
            "available": False,
            "signals": [],
            "numbers": []
        }

    signals = []
    numbers = []

    for item in results:

        text = (
            item["title"]
            + " "
            + item["snippet"]
        )

        nums = extract_numbers(
            text
        )

        numbers.extend(nums)

        signals.append({
            "title": item["title"],
            "snippet": item["snippet"],
            "link": item["link"]
        })

    return {
        "available": True,
        "signals": signals,
        "numbers": numbers
    }


# ============================================================
# BLESSURES / ABSENCES
# ============================================================

def search_absences(
    team_name,
    match_date
):

    queries = [

        f'"{team_name}" injuries suspensions absences {match_date}',

        f'"{team_name}" blessures absents suspendus {match_date}',

        f'"{team_name}" probable lineup {match_date}',

        f'"{team_name}" composition probable {match_date}',

        f'"{team_name}" unavailable players {match_date}'
    ]

    collected = []

    for query in queries:

        results = serp_search(
            query,
            6
        )

        for result in results:

            collected.append({
                "title": result.get(
                    "title",
                    ""
                ),
                "snippet": result.get(
                    "snippet",
                    ""
                ),
                "link": result.get(
                    "link",
                    ""
                )
            })

    unique = {}

    for item in collected:

        key = (
            item["title"],
            item["snippet"]
        )

        unique[key] = item

    return list(
        unique.values()
    )[:15]


# ============================================================
# CLASSIFICATION ABSENCES
# ============================================================

def classify_absences(
    results
):

    categories = {

        "Blessures": [
            "injury",
            "injured",
            "blessure",
            "blessé",
            "blessés"
        ],

        "Suspensions": [
            "suspended",
            "suspension",
            "suspendu",
            "carton rouge"
        ],

        "Absences": [
            "absence",
            "absent",
            "unavailable",
            "forfait",
            "manquera",
            "out"
        ]
    }

    output = []

    for result in results:

        text = (
            result["title"]
            + " "
            + result["snippet"]
        ).lower()

        found = []

        for category, words in categories.items():

            if any(w in text for w in words):
                found.append(category)

        if found:
            output.append({
                "title": result["title"],
                "snippet": result["snippet"],
                "link": result["link"],
                "categories": found
            })

    return output


# ============================================================
# INTERFACE STREAMLIT
# ============================================================

def main():
    st.title("⚽ Rodrigue Pro Football AI V10")
    st.markdown("### Moteur d'analyse prédictive et statistique de football")

    st.sidebar.header("Paramètres de recherche")

    selected_date = st.sidebar.date_input(
        "Date des matchs",
        value=date.today()
    )

    selected_competitions = st.sidebar.multiselect(
        "Compétitions",
        options=list(COMPETITIONS.keys()),
        default=["Champions League", "Premier League", "LaLiga"]
    )

    if st.sidebar.button("🚀 CHERCHER LES MATCHS"):
        codes = [COMPETITIONS[c] for c in selected_competitions]

        with st.spinner("Recherche des matchs en cours..."):
            matches = fetch_matches(selected_date, codes)

        if not matches:
            st.warning("Aucun match trouvé pour cette date dans les compétitions sélectionnées.")
        else:
            st.success(f"{len(matches)} match(s) trouvé(s) !")
            for i, match in enumerate(matches):
                home = match.get("homeTeam", {}).get("name", "Domicile")
                away = match.get("awayTeam", {}).get("name", "Extérieur")
                comp = match.get("competition", {}).get("name", "")
                utc = match.get("utcDate", "")

                st.markdown(f"---")
                st.markdown(f"### 🏆 {comp} : **{home}** vs **{away}**")
                st.text(f"Heure (UTC) : {utc}")


if __name__ == "__main__":
    main()
