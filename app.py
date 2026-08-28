# ============================================================
# RODRIGUE PRO FOOTBALL AI
# ============================================================
# Installation:
# pip install streamlit requests pandas numpy
#
# Lancement:
# streamlit run app.py
#
# API:
# API-FOOTBALL / API-SPORTS v3
#
# Marchés:
# 1X2
# Double chance
# Over/Under 0.5
# Over/Under 1.5
# Over/Under 2.5
# Over/Under 3.5
# Over/Under 4.0
# Over/Under 4.5
# BTTS
# BTTS + Over 2.5
# BTTS + Under 2.5
# Mi-temps 1X2
# Mi-temps double chance
# HT/FT 9 combinaisons
# Scores exacts
# Forme récente
# H2H
# Blessures / absences
# Stade
# Cotes disponibles
# Contrôle avec la prédiction API
#
# AUCUNE garantie de gain.
# Les pourcentages sont des probabilités du modèle.
# ============================================================

import os
import math
from datetime import datetime
from functools import lru_cache

import numpy as np
import pandas as pd
import requests
import streamlit as st


# ============================================================
# CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Rodrigue Pro Football AI",
    page_icon="⚽",
    layout="wide"
)

API_BASE = "https://v3.football.api-sports.io"

DEFAULT_API_KEY = os.getenv(
    "API_FOOTBALL_KEY",
    ""
)

OUTCOMES = ("1", "X", "2")


# ============================================================
# API CLIENT
# ============================================================

class APIFootball:

    def __init__(self, api_key):

        self.api_key = api_key.strip()

        self.session = requests.Session()

        self.session.headers.update({
            "x-apisports-key": self.api_key,
            "Accept": "application/json"
        })

    def get(self, endpoint, params=None):

        params = params or {}

        response = self.session.get(
            API_BASE + endpoint,
            params=params,
            timeout=40
        )

        if response.status_code == 401:
            raise RuntimeError(
                "Clé API-FOOTBALL invalide."
            )

        if response.status_code == 403:
            raise RuntimeError(
                "Accès refusé par ton plan API-FOOTBALL."
            )

        if response.status_code == 429:
            raise RuntimeError(
                "Limite de requêtes API atteinte."
            )

        response.raise_for_status()

        data = response.json()

        errors = data.get("errors")

        if isinstance(errors, dict) and errors:

            message = " | ".join(
                f"{k}: {v}"
                for k, v in errors.items()
            )

            raise RuntimeError(
                f"API-FOOTBALL : {message}"
            )

        return data

    def many(self, endpoint, params=None):

        data = self.get(
            endpoint,
            params
        )

        return data.get(
            "response",
            []
        )

    def one(self, endpoint, params=None):

        items = self.many(
            endpoint,
            params
        )

        if items:
            return items[0]

        return None


# ============================================================
# OUTILS MATHÉMATIQUES
# ============================================================

def clamp(value, minimum, maximum):

    return float(
        np.clip(
            value,
            minimum,
            maximum
        )
    )


def poisson_probability(k, lam):

    if lam <= 0:

        return 1.0 if k == 0 else 0.0

    return (
        math.exp(-lam)
        * lam ** k
        / math.factorial(k)
    )


def result_score(home, away):

    if home > away:
        return "1"

    if home < away:
        return "2"

    return "X"


# ============================================================
# DIXON-COLES
# ============================================================

def dc_correction(
    home_goals,
    away_goals,
    lambda_home,
    lambda_away,
    rho=-0.06
):

    if home_goals == 0 and away_goals == 0:

        return (
            1
            - lambda_home
            * lambda_away
            * rho
        )

    if home_goals == 0 and away_goals == 1:

        return (
            1
            + lambda_away
            * rho
        )

    if home_goals == 1 and away_goals == 0:

        return (
            1
            + lambda_home
            * rho
        )

    if home_goals == 1 and away_goals == 1:

        return (
            1
            - rho
        )

    return 1.0


def probability_matrix(
    lambda_home,
    lambda_away,
    maximum_goals=10
):

    matrix = np.zeros(
        (
            maximum_goals + 1,
            maximum_goals + 1
        )
    )

    for home_goals in range(
        maximum_goals + 1
    ):

        for away_goals in range(
            maximum_goals + 1
        ):

            probability = (

                poisson_probability(
                    home_goals,
                    lambda_home
                )

                *

                poisson_probability(
                    away_goals,
                    lambda_away
                )

                *

                dc_correction(
                    home_goals,
                    away_goals,
                    lambda_home,
                    lambda_away
                )
            )

            matrix[
                home_goals,
                away_goals
            ] = max(
                probability,
                0
            )

    total = matrix.sum()

    if total > 0:

        matrix /= total

    return matrix


# ============================================================
# MARCHÉS
# ============================================================

def calculate_markets(
    lambda_home,
    lambda_away
):

    matrix = probability_matrix(
        lambda_home,
        lambda_away
    )

    p_home = 0
    p_draw = 0
    p_away = 0

    p_btts = 0

    totals = {}

    exact_scores = []

    for home in range(
        matrix.shape[0]
    ):

        for away in range(
            matrix.shape[1]
        ):

            p = float(
                matrix[
                    home,
                    away
                ]
            )

            total_goals = (
                home + away
            )

            if home > away:
                p_home += p

            elif home == away:
                p_draw += p

            else:
                p_away += p

            if (
                home >= 1
                and away >= 1
            ):
                p_btts += p

            exact_scores.append(
                (
                    f"{home}-{away}",
                    p
                )
            )

            if total_goals not in totals:
                totals[total_goals] = 0

            totals[
                total_goals
            ] += p

    def over(line):

        return sum(
            p
            for goals, p
            in totals.items()
            if goals > line
        )

    def under(line):

        return sum(
            p
            for goals, p
            in totals.items()
            if goals < line
        )

    total4 = totals.get(
        4,
        0
    )

    markets = {

        "Victoire domicile":
            p_home,

        "Match nul":
            p_draw,

        "Victoire extérieur":
            p_away,

        "1X":
            p_home + p_draw,

        "X2":
            p_draw + p_away,

        "12":
            p_home + p_away,

        "BTTS Oui":
            p_btts,

        "BTTS Non":
            1 - p_btts,

        "Over 0.5":
            over(0.5),

        "Under 0.5":
            under(0.5),

        "Over 1.5":
            over(1.5),

        "Under 1.5":
            under(1.5),

        "Over 2.5":
            over(2.5),

        "Under 2.5":
            under(2.5),

        "Over 3.5":
            over(3.5),

        "Under 3.5":
            under(3.5),

        "Over 4.5":
            over(4.5),

        "Under 4.5":
            under(4.5),

        "Over 4.0":
            over(4.0)
            + 0.5 * total4,

        "Under 4.0":
            under(4.0)
            - 0.5 * total4
    }

    markets[
        "BTTS + Over 2.5"
    ] = (
        p_btts
        * markets["Over 2.5"]
    )

    markets[
        "BTTS + Under 2.5"
    ] = (
        p_btts
        * markets["Under 2.5"]
    )

    exact_scores.sort(
        key=lambda x: x[1],
        reverse=True
    )

    return (
        markets,
        exact_scores
    )


# ============================================================
# MI-TEMPS / FIN
# ============================================================

def calculate_htft(
    lambda_home,
    lambda_away,
    ht_ratio=0.46
):

    lambda_home_ht = (
        lambda_home
        * ht_ratio
    )

    lambda_away_ht = (
        lambda_away
        * ht_ratio
    )

    lambda_home_2h = max(
        0.01,
        lambda_home
        - lambda_home_ht
    )

    lambda_away_2h = max(
        0.01,
        lambda_away
        - lambda_away_ht
    )

    results = {}

    for ht in OUTCOMES:

        for ft in OUTCOMES:

            results[
                f"{ht}/{ft}"
            ] = 0.0

    for h_ht in range(8):

        p_h_ht = poisson_probability(
            h_ht,
            lambda_home_ht
        )

        for a_ht in range(8):

            p_a_ht = poisson_probability(
                a_ht,
                lambda_away_ht
            )

            probability_ht = (
                p_h_ht
                * p_a_ht
            )

            ht_result = result_score(
                h_ht,
                a_ht
            )

            for h_2h in range(8):

                p_h_2h = poisson_probability(
                    h_2h,
                    lambda_home_2h
                )

                for a_2h in range(8):

                    p_a_2h = poisson_probability(
                        a_2h,
                        lambda_away_2h
                    )

                    final_home = (
                        h_ht + h_2h
                    )

                    final_away = (
                        a_ht + a_2h
                    )

                    ft_result = result_score(
                        final_home,
                        final_away
                    )

                    probability = (
                        probability_ht
                        * p_h_2h
                        * p_a_2h
                    )

                    results[
                        f"{ht_result}/{ft_result}"
                    ] += probability

    total = sum(
        results.values()
    )

    if total > 0:

        results = {
            k: v / total
            for k, v in results.items()
        }

    return results


# ============================================================
# EXTRACTION STATISTIQUES
# ============================================================

def number(value):

    try:

        if value is None:
            return None

        return float(value)

    except Exception:

        return None


def extract_team_stats(data):

    fixtures = (
        data.get("fixtures", {})
        if isinstance(data, dict)
        else {}
    )

    goals = (
        data.get("goals", {})
        if isinstance(data, dict)
        else {}
    )

    gf = (
        goals
        .get("for", {})
    )

    ga = (
        goals
        .get("against", {})
    )

    return {

        "played":
            number(
                fixtures
                .get("played", {})
                .get("total")
            ),

        "wins":
            number(
                fixtures
                .get("wins", {})
                .get("total")
            ),

        "draws":
            number(
                fixtures
                .get("draws", {})
                .get("total")
            ),

        "losses":
            number(
                fixtures
                .get("loses", {})
                .get("total")
            ),

        "gf":
            number(
                gf.get("average")
            ),

        "ga":
            number(
                ga.get("average")
            ),

        "clean_sheets":
            number(
                data
                .get("clean_sheet", {})
                .get("total")
            ),

        "failed_to_score":
            number(
                data
                .get("failed_to_score", {})
                .get("total")
            ),

        "form":
            data.get(
                "form",
                ""
            )
    }


# ============================================================
# FORME RÉCENTE
# ============================================================

def parse_recent_form(
    fixtures,
    team_id
):

    results = []

    for fixture in fixtures:

        teams = (
            fixture.get(
                "teams",
                {}
            )
        )

        home = teams.get(
            "home",
            {}
        )

        away = teams.get(
            "away",
            {}
        )

        goals = fixture.get(
            "goals",
            {}
        )

        if (
            home.get("id")
            != team_id
            and
            away.get("id")
            != team_id
        ):
            continue

        is_home = (
            home.get("id")
            == team_id
        )

        gf = (
            goals.get("home")
            if is_home
            else
            goals.get("away")
        )

        ga = (
            goals.get("away")
            if is_home
            else
            goals.get("home")
        )

        if gf is None or ga is None:
            continue

        result = (
            "W"
            if gf > ga
            else
            "D"
            if gf == ga
            else
            "L"
        )

        results.append({

            "date":
                fixture
                .get(
                    "fixture",
                    {}
                )
                .get(
                    "date",
                    ""
                ),

            "home":
                home.get(
                    "name",
                    ""
                ),

            "away":
                away.get(
                    "name",
                    ""
                ),

            "gf":
                gf,

            "ga":
                ga,

            "result":
                result,

            "venue":
                "Domicile"
                if is_home
                else
                "Extérieur"
        })

    results.sort(
        key=lambda x: x["date"],
        reverse=True
    )

    return results


def recent_average(
    rows
):

    if not rows:
        return (
            1.30,
            1.20
        )

    weights = []

    gf = []

    ga = []

    for index, row in enumerate(rows):

        w = math.exp(
            -0.12 * index
        )

        weights.append(w)

        gf.append(
            row["gf"]
        )

        ga.append(
            row["ga"]
        )

    gf_average = np.average(
        gf,
        weights=weights
    )

    ga_average = np.average(
        ga,
        weights=weights
    )

    return (
        float(gf_average),
        float(ga_average)
    )


# ============================================================
# BLESSURES
# ============================================================

def injury_penalty(
    injuries
):

    penalty = 0.0

    for item in injuries:

        reason = str(
            item.get(
                "reason",
                ""
            )
        ).lower()

        kind = str(
            item.get(
                "type",
                ""
            )
        ).lower()

        text = (
            reason
            + " "
            + kind
        )

        if (
            "susp" in text
        ):

            penalty += 0.035

        elif (
            "injur" in text
        ):

            penalty += 0.028

        else:

            penalty += 0.010

    return min(
        penalty,
        0.18
    )


# ============================================================
# H2H
# ============================================================

def h2h_average(
    h2h,
    home_id
):

    if not h2h:
        return (
            None,
            None
        )

    home_goals = []
    away_goals = []

    for match in h2h:

        teams = match.get(
            "teams",
            {}
        )

        goals = match.get(
            "goals",
            {}
        )

        h = teams.get(
            "home",
            {}
        )

        a = teams.get(
            "away",
            {}
        )

        gh = goals.get(
            "home"
        )

        ga = goals.get(
            "away"
        )

        if (
            gh is None
            or ga is None
        ):
            continue

        if h.get("id") == home_id:

            home_goals.append(
                gh
            )

            away_goals.append(
                ga
            )

        else:

            home_goals.append(
                ga
            )

            away_goals.append(
                gh
            )

    if not home_goals:
        return (
            None,
            None
        )

    return (
        float(
            np.mean(
                home_goals
            )
        ),
        float(
            np.mean(
                away_goals
            )
        )
    )


# ============================================================
# MODÈLE PRINCIPAL
# ============================================================

def build_prediction(
    fixture,
    home_stats,
    away_stats,
    home_form,
    away_form,
    h2h,
    home_injuries,
    away_injuries
):

    hs = extract_team_stats(
        home_stats
    )

    aws = extract_team_stats(
        away_stats
    )

    recent_h_gf, recent_h_ga = (
        recent_average(
            home_form
        )
    )

    recent_a_gf, recent_a_ga = (
        recent_average(
            away_form
        )
    )

    home_attack = (
        hs["gf"]
        if hs["gf"] is not None
        else recent_h_gf
    )

    home_defence = (
        hs["ga"]
        if hs["ga"] is not None
        else recent_h_ga
    )

    away_attack = (
        aws["gf"]
        if aws["gf"] is not None
        else recent_a_gf
    )

    away_defence = (
        aws["ga"]
        if aws["ga"] is not None
        else recent_a_ga
    )

    # Pondération statistiques saison + forme récente.

    home_attack = (
        0.68 * home_attack
        + 0.32 * recent_h_gf
    )

    home_defence = (
        0.68 * home_defence
        + 0.32 * recent_h_ga
    )

    away_attack = (
        0.68 * away_attack
        + 0.32 * recent_a_gf
    )

    away_defence = (
        0.68 * away_defence
        + 0.32 * recent_a_ga
    )

    # Modèle attaque/défense.

    lambda_home = (

        0.45 * home_attack

        +

        0.30 * away_defence

        +

        0.25 * 1.35
    )

    lambda_away = (

        0.45 * away_attack

        +

        0.30 * home_defence

        +

        0.25 * 1.10
    )

    # Avantage terrain.

    lambda_home *= 1.06

    lambda_away *= 0.97

    # H2H à faible pondération.

    h2h_home, h2h_away = (
        h2h_average(
            h2h,
            fixture
            ["teams"]
            ["home"]
            ["id"]
        )
    )

    if (
        h2h_home is not None
        and
        h2h_away is not None
    ):

        lambda_home = (
            0.92 * lambda_home
            + 0.08 * h2h_home
        )

        lambda_away = (
            0.92 * lambda_away
            + 0.08 * h2h_away
        )

    # Blessures / suspensions.

    home_penalty = injury_penalty(
        home_injuries
    )

    away_penalty = injury_penalty(
        away_injuries
    )

    lambda_home *= (
        1 - home_penalty
    )

    lambda_away *= (
        1 - away_penalty
    )

    # Limites de sécurité.

    lambda_home = clamp(
        lambda_home,
        0.15,
        4.50
    )

    lambda_away = clamp(
        lambda_away,
        0.10,
        4.00
    )

    markets, exact_scores = (
        calculate_markets(
            lambda_home,
            lambda_away
        )
    )

    htft = calculate_htft(
        lambda_home,
        lambda_away,
        0.46
    )

    # Qualité des données.
    quality_points = 0
    total_points = 10

    if hs["played"]:
        quality_points += 1

    if aws["played"]:
        quality_points += 1

    if hs["gf"] is not None:
        quality_points += 1

    if aws["gf"] is not None:
        quality_points += 1

    if hs["ga"] is not None:
        quality_points += 1

    if aws["ga"] is not None:
        quality_points += 1

    if len(home_form) >= 5:
        quality_points += 1

    if len(away_form) >= 5:
        quality_points += 1

    if h2h:
        quality_points += 1

    if fixture.get(
        "fixture",
        {}
    ).get(
        "venue",
        {}
    ).get(
        "name"
    ):

        quality_points += 1

    quality = (
        quality_points
        / total_points
        * 100
    )

    return {

        "lambda_home":
            lambda_home,

        "lambda_away":
            lambda_away,

        "markets":
            markets,

        "exact":
            exact_scores,

        "htft":
            htft,

        "quality":
            quality,

        "home_penalty":
            home_penalty,

        "away_penalty":
            away_penalty
    }


# ============================================================
# CACHE API
# ============================================================

@st.cache_data(
    ttl=600,
    show_spinner=False
)
def get_fixture(
    api_key,
    fixture_id
):

    api = APIFootball(
        api_key
    )

    return api.one(
        "/fixtures",
        {
            "id": fixture_id
        }
    )


@st.cache_data(
    ttl=600,
    show_spinner=False
)
def search_matches(
    api_key,
    match_date
):

    api = APIFootball(
        api_key
    )

    try:
        return api.many(
            "/fixtures",
            {
                "date":
                    match_date
            }
        )
    except Exception:
        return []


@st.cache_data(
    ttl=1800,
    show_spinner=False
)
def get_team_statistics(
    api_key,
    league_id,
    season,
    team_id
):

    api = APIFootball(
        api_key
    )

    return api.one(
        "/teams/statistics",
        {
            "league":
                league_id,

            "season":
                season,

            "team":
                team_id
        }
    ) or {}


@st.cache_data(
    ttl=900,
    show_spinner=False
)
def get_recent_matches(
    api_key,
    team_id
):

    api = APIFootball(
        api_key
    )

    return api.many(
        "/fixtures",
        {
            "team":
                team_id,

            "last":
                12
        }
    )


@st.cache_data(
    ttl=1800,
    show_spinner=False
)
def get_h2h(
    api_key,
    home_id,
    away_id
):

    api = APIFootball(
        api_key
    )

    return api.many(
        "/fixtures/headtohead",
        {
            "h2h":
                f"{home_id}-{away_id}",

            "last":
                10
        }
    )


@st.cache_data(
    ttl=900,
    show_spinner=False
)
def get_injuries(
    api_key,
    league_id,
    season,
    team_id
):

    api = APIFootball(
        api_key
    )

    try:

        return api.many(
            "/injuries",
            {
                "league":
                    league_id,

                "season":
                    season,

                "team":
                    team_id
            }
        )

    except Exception:

        return []


@st.cache_data(
    ttl=900,
    show_spinner=False
)
def get_api_prediction(
    api_key,
    fixture_id
):

    api = APIFootball(
        api_key
    )

    try:

        return api.one(
            "/predictions",
            {
                "fixture":
                    fixture_id
            }
        )

    except Exception:

        return None


@st.cache_data(
    ttl=900,
    show_spinner=False
)
def get_odds(
    api_key,
    fixture_id
):

    api = APIFootball(
        api_key
    )

    try:

        return api.many(
            "/odds",
            {
                "fixture":
                    fixture_id
            }
        )

    except Exception:

        return []


# ============================================================
# FORMATAGE
# ============================================================

def percent(value):

    return f"{value * 100:.2f}%"


def ranked_markets(
    markets
):

    rows = []

    for name, value in markets.items():

        if not isinstance(
            value,
            (int, float)
        ):
            continue

        rows.append(
            (
                name,
                value
            )
        )

    rows.sort(
        key=lambda x: x[1],
        reverse=True
    )

    return rows


def form_text(
    rows
):

    return " ".join(
        row["result"]
        for row in rows[:10]
    )


# ============================================================
# INTERFACE
# ============================================================

st.title(
    "⚽ RODRIGUE PRO FOOTBALL AI"
)

st.subheader(
    "🔥 Analyse complète d'un match réel"
)

st.caption(
    "Poisson corrigé + forme + statistiques + H2H + "
    "absences + stade + contrôle API."
)


with st.sidebar:

    st.header(
        "🔐 API-FOOTBALL"
    )

    api_key = st.text_input(
        "Clé API",
        value=DEFAULT_API_KEY,
        type="password"
    )

    st.divider()

    st.header(
        "🎯 MATCH"
    )

    fixture_id = st.text_input(
        "Fixture ID",
        placeholder="Exemple : 1234567"
    )

    match_date = st.date_input(
        "Date du match",
        value=datetime.now().date()
    )

    team_search = st.text_input(
        "Ou recherche par équipe",
        placeholder="Exemple : Real Madrid"
    )

    score_count = st.slider(
        "Scores exacts affichés",
        5,
        20,
        10
    )


if not api_key:

    st.info(
        "Entre ta clé API-FOOTBALL."
    )

    st.stop()


# ============================================================
# CHOIX DU MATCH
# ============================================================

selected_fixture = None


if fixture_id.strip():

    try:

        selected_fixture = get_fixture(
            api_key,
            int(
                fixture_id.strip()
            )
        )

    except ValueError:

        st.error(
            "Le Fixture ID doit être numérique."
        )

        st.stop()

else:

    with st.spinner(
        "Recherche des matchs réels..."
    ):

        fixtures = search_matches(
            api_key,
            match_date.isoformat()
        )

    if team_search.strip():

        query = (
            team_search
            .strip()
            .lower()
        )

        filtered = []

        for f in fixtures:

            teams = f.get(
                "teams",
                {}
            )

            home = teams.get(
                "home",
                {}
            ).get(
                "name",
                ""
            )

            away = teams.get(
                "away",
                {}
            ).get(
                "name",
                ""
            )

            if (
                query in home.lower()
                or
                query in away.lower()
            ):

                filtered.append(f)

        fixtures = filtered

    if not fixtures:

        st.warning(
            "Aucun match trouvé (ou restriction de l'API par date). Utilise plutôt le Fixture ID dans la barre latérale."
        )

        st.stop()

    choices = []

    for f in fixtures:

        teams = f.get(
            "teams",
            {}
        )

        league = f.get(
            "league",
            {}
        )

        home = teams.get(
            "home",
            {}
        ).get(
            "name",
            "?"
        )

        away = teams.get(
            "away",
            {}
        ).get(
            "name",
            "?"
        )

        choices.append(
            f'{f.get("fixture", {}).get("id")} | '
            f'{home} vs {away} | '
            f'{league.get("name", "")}'
        )

    choice = st.selectbox(
        "Match réel",
        choices
    )

    selected_id = int(
        choice.split(
            " | ",
            1
        )[0]
    )

    selected_fixture = get_fixture(
        api_key,
        selected_id
    )


if not selected_fixture:

    st.error(
        "Match introuvable."
    )

    st.stop()


# ============================================================
# INFORMATIONS MATCH
# ============================================================

fx = selected_fixture

teams = fx.get(
    "teams",
    {}
)

home = teams.get(
    "home",
    {}
)

away = teams.get(
    "away",
    {}
)

league = fx.get(
    "league",
    {}
)

fixture_info = fx.get(
    "fixture",
    {}
)

home_id = home.get(
    "id"
)

away_id = away.get(
    "id"
)

league_id = league.get(
    "id"
)

season = league.get(
    "season"
)

fixture_id_real = fixture_info.get(
    "id"
)


st.markdown("---")

st.header(
    f"⚽ {home.get('name', '?')} "
    f"vs "
    f"{away.get('name', '?')}"
)


c1, c2, c3, c4 = st.columns(4)

c1.metric(
    "Compétition",
    league.get(
        "name",
        "—"
    )
)

c2.metric(
    "Saison",
    str(
        season or "—"
    )
)

c3.metric(
    "Fixture ID",
    str(
        fixture_id_real or "—"
    )
)

c4.metric(
    "Statut",
    fixture_info
    .get(
        "status",
        {}
    )
    .get(
        "long",
        "—"
    )
)


venue = fixture_info.get(
    "venue",
    {}
)

st.write(
    f"🏟️ **Stade :** "
    f"{venue.get('name', 'Non disponible')}"
)

st.write(
    f"📍 **Ville :** "
    f"{venue.get('city', 'Non disponible')}"
)


# ============================================================
# ANALYSE
# ============================================================

if st.button(
    "🚀 ANALYSER CE MATCH",
    type="primary",
    use_container_width=True
):

    try:

        with st.spinner(
            "📊 Récupération des statistiques..."
        ):

            home_stats = (
                get_team_statistics(
                    api_key,
                    league_id,
                    season,
                    home_id
                )
            )

            away_stats = (
                get_team_statistics(
                    api_key,
                    league_id,
                    season,
                    away_id
                )
            )

            home_raw = (
                get_recent_matches(
                    api_key,
                    home_id
                )
            )

            away_raw = (
                get_recent_matches(
                    api_key,
                    away_id
                )
            )

            home_form = (
                parse_recent_form(
                    home_raw,
                    home_id
                )
            )

            away_form = (
                parse_recent_form(
                    away_raw,
                    away_id
                )
            )

            h2h = (
                get_h2h(
                    api_key,
                    home_id,
                    away_id
                )
            )

            home_injuries = (
                get_injuries(
                    api_key,
                    league_id,
                    season,
                    home_id
                )
            )

            away_injuries = (
                get_injuries(
                    api_key,
                    league_id,
                    season,
                    away_id
                )
            )

            api_prediction = (
                get_api_prediction(
                    api_key,
                    fixture_id_real
                )
            )

            odds = (
                get_odds(
                    api_key,
                    fixture_id_real
                )
            )


        with st.spinner(
            "🧠 Calcul du modèle Poisson..."
        ):

            prediction = (
                build_prediction(
                    fx,
                    home_stats,
                    away_stats,
                    home_form,
                    away_form,
                    h2h,
                    home_injuries,
                    away_injuries
                )
            )


        # ====================================================
        # RÉSULTAT PRINCIPAL
        # ====================================================

        st.success(
            "✅ Analyse terminée"
        )

        st.markdown(
            "## 🎯 1X2"
        )

        m = prediction[
            "markets"
        ]

        c1, c2, c3, c4 = st.columns(4)

        c1.metric(
            "🏠 Victoire domicile",
            percent(
                m[
                    "Victoire domicile"
                ]
            )
        )

        c2.metric(
            "🤝 Nul",
            percent(
                m[
                    "Match nul"
                ]
            )
        )

        c3.metric(
            "✈️ Victoire extérieur",
            percent(
                m[
                    "Victoire extérieur"
                ]
            )
        )

        c4.metric(
            "🧠 Qualité données",
            f"{prediction['quality']:.0f}%"
        )


        st.write(
            f"**Buts attendus :** "
            f"{home.get('name')} "
            f"**{prediction['lambda_home']:.2f}** "
            f"— "
            f"**{prediction['lambda_away']:.2f}** "
            f"{away.get('name')}"
        )


        # ====================================================
        # MEILLEURS MARCHÉS
        # ====================================================

        st.markdown(
            "## ⭐ MARCHÉS LES PLUS PROBABLES"
        )

        ranked = ranked_markets(
            m
        )

        market_df = pd.DataFrame(
            [
                {
                    "Marché":
                        name,

                    "Probabilité":
                        percent(
                            probability
                        )
                }

                for name, probability
                in ranked[:15]
            ]
        )

        st.dataframe(
            market_df,
            hide_index=True,
            use_container_width=True
        )


        # ====================================================
        # DOUBLE CHANCE
        # ====================================================

        st.markdown(
            "## 🛡️ DOUBLE CHANCE"
        )

        dc_df = pd.DataFrame(
            [
                {
                    "Marché":
                        "1X",

                    "Probabilité":
                        percent(
                            m["1X"]
                        )
                },

                {
                    "Marché":
                        "X2",

                    "Probabilité":
                        percent(
                            m["X2"]
                        )
                },

                {
                    "Marché":
                        "12",

                    "Probabilité":
                        percent(
                            m["12"]
                        )
                }
            ]
        )

        st.dataframe(
            dc_df,
            hide_index=True,
            use_container_width=True
        )


        # ====================================================
        # OVER UNDER
        # ====================================================

        st.markdown(
            "## ⚽ OVER / UNDER"
        )

        lines = [
            "Over 0.5",
            "Under 0.5",
            "Over 1.5",
            "Under 1.5",
            "Over 2.5",
            "Under 2.5",
            "Over 3.5",
            "Under 3.5",
            "Over 4.0",
            "Under 4.0",
            "Over 4.5",
            "Under 4.5"
        ]

        ou_df = pd.DataFrame(
            [
                {
                    "Marché":
                        line,

                    "Probabilité":
                        percent(
                            m[line]
                        )
                }

                for line in lines
            ]
        )

        st.dataframe(
            ou_df,
            hide_index=True,
            use_container_width=True
        )


        # ====================================================
        # BTTS
        # ====================================================

        st.markdown(
            "## 🥅 BTTS"
        )

        c1, c2, c3, c4 = st.columns(4)

        c1.metric(
            "BTTS Oui",
            percent(
                m["BTTS Oui"]
            )
        )

        c2.metric(
            "BTTS Non",
            percent(
                m["BTTS Non"]
            )
        )

        c3.metric(
            "BTTS + Over 2.5",
            percent(
                m[
                    "BTTS + Over 2.5"
                ]
            )
        )

        c4.metric(
            "BTTS + Under 2.5",
            percent(
                m[
                    "BTTS + Under 2.5"
                ]
            )
        )


        # ====================================================
        # MI-TEMPS
        # ====================================================

        st.markdown(
            "## ⏱️ MI-TEMPS"
        )

        ht_markets, _ = (
            calculate_markets(
                prediction[
                    "lambda_home"
                ] * 0.46,

                prediction[
                    "lambda_away"
                ] * 0.46
            )
        )

        ht_df = pd.DataFrame(
            [
                {
                    "Marché MT":
                        name,

                    "Probabilité":
                        percent(
                            ht_markets[name]
                        )
                }

                for name in [
                    "Victoire domicile",
                    "Match nul",
                    "Victoire extérieur",
                    "1X",
                    "X2",
                    "12",
                    "Over 0.5",
                    "Under 0.5",
                    "Over 1.5",
                    "Under 1.5"
                ]
            ]
        )

        st.dataframe(
            ht_df,
            hide_index=True,
            use_container_width=True
        )


        # ====================================================
        # HT / FT
        # ====================================================

        st.markdown(
            "## 🔥 HT / FT"
        )

        htft = sorted(
            prediction["htft"].items(),
            key=lambda x: x[1],
            reverse=True
        )

        htft_df = pd.DataFrame(
            [
                {
                    "HT/FT":
                        name,

                    "Probabilité":
                        percent(
                            probability
                        )
                }

                for name, probability
                in htft
            ]
        )

        st.dataframe(
            htft_df,
            hide_index=True,
            use_container_width=True
        )

        st.success(
            "HT/FT le plus probable : "
            f"**{htft[0][0]} — "
            f"{percent(htft[0][1])}**"
        )


        # ====================================================
        # SCORES EXACTS
        # ====================================================

        st.markdown(
            "## 🎯 SCORES EXACTS"
        )

        exact = prediction[
            "exact"
        ][:score_count]

        exact_df = pd.DataFrame(
            [
                {
                    "Score":
                        score,

                    "Probabilité":
                        percent(
                            probability
                        )
                }

                for score, probability
                in exact
            ]
        )

        st.dataframe(
            exact_df,
            hide_index=True,
            use_container_width=True
        )

        st.success(
            f"Score exact le plus probable : "
            f"**{exact[0][0]} — "
            f"{percent(exact[0][1])}**"
        )


        # ====================================================
        # FORME
        # ====================================================

        st.markdown(
            "## 📈 FORME RÉCENTE"
        )

        f1, f2 = st.columns(2)

        with f1:

            st.subheader(
                home.get(
                    "name",
                    "Domicile"
                )
            )

            st.write(
                "Forme :",
                form_text(
                    home_form
                )
            )

            if home_form:

                st.dataframe(
                    pd.DataFrame(
                        home_form[:10]
                    ),
                    hide_index=True,
                    use_container_width=True
                )

        with f2:

            st.subheader(
                away.get(
                    "name",
                    "Extérieur"
                )
            )

            st.write(
                "Forme :",
                form_text(
                    away_form
                )
            )

            if away_form:

                st.dataframe(
                    pd.DataFrame(
                        away_form[:10]
                    ),
                    hide_index=True,
                    use_container_width=True
                )


        # ====================================================
        # ABSENCES
        # ====================================================

        st.markdown(
            "## 🚑 BLESSURES / ABSENCES"
        )

        i1, i2 = st.columns(2)

        def injury_dataframe(
            injuries
        ):

            rows = []

            for item in injuries:

                player = item.get(
                    "player",
                    {}
                )

                rows.append({

                    "Joueur":
                        player.get(
                            "name",
                            "Inconnu"
                        ),

                    "Type":
                        item.get(
                            "type",
                            "—"
                        ),

                    "Raison":
                        item.get(
                            "reason",
                            "—"
                        )
                })

            return pd.DataFrame(
                rows
            )

        with i1:

            st.subheader(
                home.get(
                    "name",
                    ""
                )
            )

            st.write(
                f"Absences API : "
                f"{len(home_injuries)}"
            )

            df = injury_dataframe(
                home_injuries
            )

            if not df.empty:

                st.dataframe(
                    df,
                    hide_index=True,
                    use_container_width=True
                )

        with i2:

            st.subheader(
                away.get(
                    "name",
                    ""
                )
            )

            st.write(
                f"Absences API : "
                f"{len(away_injuries)}"
            )

            df = injury_dataframe(
                away_injuries
            )

            if not df.empty:

                st.dataframe(
                    df,
                    hide_index=True,
                    use_container_width=True
                )


        # ====================================================
        # H2H
        # ====================================================

        st.markdown(
            "## 🤝 H2H"
        )

        h2h_rows = []

        for match in h2h:

            teams_m = match.get(
                "teams",
                {}
            )

            goals_m = match.get(
                "goals",
                {}
            )

            h = teams_m.get(
                "home",
                {}
            )

            a = teams_m.get(
                "away",
                {}
            )

            h2h_rows.append({

                "Domicile":
                    h.get(
                        "name",
                        ""
                    ),

                "Extérieur":
                    a.get(
                        "name",
                        ""
                    ),

                "Score":
                    f"{goals_m.get('home', '?')}-"
                    f"{goals_m.get('away', '?')}",

                "Date":
                    match
                    .get(
                        "fixture",
                        {}
                    )
                    .get(
                        "date",
                        ""
                    )
            })

        if h2h_rows:

            st.dataframe(
                pd.DataFrame(
                    h2h_rows
                ),
                hide_index=True,
                use_container_width=True
            )


        # ====================================================
        # PRÉDICTION API
        # ====================================================

        if api_prediction:

            st.markdown(
                "## 🤖 CONTRÔLE API-FOOTBALL"
            )

            p = api_prediction.get(
                "percent",
                {}
            )

            c1, c2, c3 = st.columns(3)

            c1.metric(
                "API domicile",
                str(
                    p.get(
                        "home",
                        "—"
                    )
                )
            )

            c2.metric(
                "API nul",
                str(
                    p.get(
                        "draw",
                        "—"
                    )
                )
            )

            c3.metric(
                "API extérieur",
                str(
                    p.get(
                        "away",
                        "—"
                    )
                )
            )

            advice = (
                api_prediction
                .get(
                    "advice"
                )
            )

            if advice:

                st.write(
                    "**Conseil API :**",
                    advice
                )


            under_over = (
                api_prediction
                .get(
                    "under_over"
                )
            )

            if under_over:

                st.write(
                    "**Over/Under API :**",
                    under_over
                )


        # ====================================================
        # COTES
        # ====================================================

        if odds:

            st.markdown(
                "## 💰 COTES DISPONIBLES"
            )

            odds_rows = []

            for item in odds:

                bookmakers = (
                    item.get(
                        "bookmakers",
                        []
                    )
                )

                for bookmaker in bookmakers:

                    for bet in bookmaker.get(
                        "bets",
                        []
                    ):

                        for value in bet.get(
                            "values",
                            []
                        ):

                            odds_rows.append({

                                "Bookmaker":
                                    bookmaker.get(
                                        "name",
                                        ""
                                    ),

                                "Marché":
                                    bet.get(
                                        "name",
                                        ""
                                    ),

                                "Sélection":
                                    value.get(
                                        "value",
                                        ""
                                    ),

                                "Cote":
                                    value.get(
                                        "odd",
                                        ""
                                    )
                            })

            if odds_rows:

                st.dataframe(
                    pd.DataFrame(
                        odds_rows
                    ).head(100),
                    hide_index=True,
                    use_container_width=True
                )


        # ====================================================
        # SYNTHÈSE
        # ====================================================

        st.markdown(
            "## 🧠 SYNTHÈSE FINALE"
        )

        best_market = ranked[0]

        best_exact = exact[0]

        best_htft = htft[0]

        st.info(
            f"""
### 🎯 Marché principal
**{best_market[0]} — {percent(best_market[1])}**

### ⚽ Score exact le plus probable
**{best_exact[0]} — {percent(best_exact[1])}**

### ⏱️ HT/FT le plus probable
**{best_htft[0]} — {percent(best_htft[1])}**

### 📊 Buts attendus
**{prediction['lambda_home']:.2f} — {prediction['lambda_away']:.2f}**

### 🧠 Qualité des données
**{prediction['quality']:.0f}%**
"""
        )

        st.warning(
            "Les probabilités sont calculées à partir des données "
            "disponibles et du modèle statistique. Elles ne constituent "
            "pas une garantie de résultat."
        )


    except Exception as error:

        st.error(
            f"❌ Erreur pendant l'analyse : {error}"
        )
