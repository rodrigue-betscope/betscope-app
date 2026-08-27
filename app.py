import math
import time
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import requests
import streamlit as st


# ============================================================
# RODRIGUE MT/FT PRO
# FOOTBALL-DATA.ORG v4
#
# 1/1 - X/1 - 2/1
# 1/X - X/X - 2/X
# 1/2 - X/2 - 2/2
#
# DONNÉES :
# - vrais matchs Football-Data.org
# - résultats historiques réels
# - buts marqués / encaissés
# - domicile / extérieur
# - résultats mi-temps
#
# MODÈLE :
# - Poisson
# - Dixon-Coles
# - pondération des matchs récents
# - séparation 1re / 2e période
#
# IMPORTANT :
# Les probabilités sont des estimations.
# Aucun modèle sérieux ne peut garantir 100 %.
# ============================================================


st.set_page_config(
    page_title="Rodrigue MT/FT PRO",
    page_icon="⚽",
    layout="wide",
)


# ============================================================
# CONFIGURATION
# ============================================================

BASE_URL = "https://api.football-data.org/v4"

TZ = ZoneInfo("Africa/Douala")

# Ta clé :
#
# Pour une application publique, mets-la plutôt dans :
# .streamlit/secrets.toml
#
# FOOTBALL_DATA_API_KEY = "TA_CLE"
#
# Le code utilise d'abord secrets.toml.
# Si absent, il utilise la valeur ci-dessous.

DEFAULT_API_KEY = "0b5a0d95508247ed93aa7c9cd536f58f"

try:
    API_KEY = st.secrets.get(
        "FOOTBALL_DATA_API_KEY",
        DEFAULT_API_KEY,
    )
except Exception:
    API_KEY = DEFAULT_API_KEY


# ============================================================
# COMPÉTITIONS PRINCIPALES
# ============================================================

# Ces codes sont ceux utilisés par Football-Data.org.
# L'API gratuite peut limiter certaines compétitions.
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


# ============================================================
# SESSION HTTP
# ============================================================

session = requests.Session()

session.headers.update(
    {
        "X-Auth-Token": API_KEY,
        "Accept": "application/json",
        "User-Agent": "Rodrigue-MTFT-Pro/1.0",
    }
)


# ============================================================
# REQUÊTE API
# ============================================================

def api_get(
    endpoint,
    params=None,
    retry=True,
):

    url = f"{BASE_URL}{endpoint}"

    try:

        response = session.get(
            url,
            params=params or {},
            timeout=30,
        )

    except requests.RequestException as e:

        raise RuntimeError(
            f"Erreur réseau : {e}"
        )

    if response.status_code == 401:

        raise RuntimeError(
            "❌ Clé Football-Data.org invalide."
        )

    if response.status_code == 403:

        raise RuntimeError(
            "❌ Accès refusé. "
            "Cette compétition ou cette donnée "
            "n'est peut-être pas disponible avec ton abonnement."
        )

    if response.status_code == 429:

        if retry:

            time.sleep(12)

            return api_get(
                endpoint,
                params,
                retry=False,
            )

        raise RuntimeError(
            "❌ Limite de requêtes Football-Data.org atteinte."
        )

    response.raise_for_status()

    try:

        return response.json()

    except Exception:

        raise RuntimeError(
            "❌ Réponse JSON invalide."
        )


# ============================================================
# MATCHS D'UNE DATE
# ============================================================

@st.cache_data(
    ttl=300,
    show_spinner=False,
)
def get_matches_for_date(
    selected_date,
):

    data = api_get(
        "/matches",
        {
            "dateFrom": selected_date,
            "dateTo": selected_date,
        },
    )

    return data.get(
        "matches",
        [],
    )


# ============================================================
# HISTORIQUE D'UNE ÉQUIPE
# ============================================================

@st.cache_data(
    ttl=1800,
    show_spinner=False,
)
def get_team_history(
    team_id,
    before_date,
    limit=20,
):

    end_date = (
        datetime.strptime(
            before_date,
            "%Y-%m-%d",
        ).date()
        - timedelta(days=1)
    )

    start_date = (
        end_date
        - timedelta(days=180)
    )

    data = api_get(
        f"/teams/{team_id}/matches",
        {
            "dateFrom": start_date.isoformat(),
            "dateTo": end_date.isoformat(),
            "status": "FINISHED",
            "limit": limit,
        },
    )

    matches = data.get(
        "matches",
        [],
    )

    # Les plus récents d'abord
    matches.sort(
        key=lambda x: x.get(
            "utcDate",
            "",
        ),
        reverse=True,
    )

    return matches[:limit]


# ============================================================
# EXTRACTION SCORE
# ============================================================

def get_score(
    match,
    period="fullTime",
):

    score = match.get(
        "score",
        {},
    )

    period_score = score.get(
        period,
        {},
    )

    home = period_score.get(
        "home",
    )

    away = period_score.get(
        "away",
    )

    if home is None or away is None:
        return None, None

    try:

        return (
            int(home),
            int(away),
        )

    except Exception:

        return None, None


# ============================================================
# STATISTIQUES RÉCENTES
# ============================================================

def calculate_team_stats(
    matches,
    team_id,
):

    full_for = []
    full_against = []

    ht_for = []
    ht_against = []

    home_for = []
    home_against = []

    away_for = []
    away_against = []

    weights = []

    valid = 0

    for index, match in enumerate(matches):

        home_team = match.get(
            "homeTeam",
            {},
        )

        away_team = match.get(
            "awayTeam",
            {},
        )

        home_id = home_team.get(
            "id"
        )

        away_id = away_team.get(
            "id"
        )

        if (
            home_id != team_id
            and away_id != team_id
        ):
            continue

        fh, fa = get_score(
            match,
            "fullTime",
        )

        hh, ha = get_score(
            match,
            "halfTime",
        )

        if (
            fh is None
            or fa is None
            or hh is None
            or ha is None
        ):
            continue

        valid += 1

        # Plus récent = poids supérieur
        weight = max(
            0.35,
            1.0 - index * 0.035,
        )

        weights.append(weight)

        if home_id == team_id:

            full_for.append(
                (fh, weight)
            )

            full_against.append(
                (fa, weight)
            )

            ht_for.append(
                (hh, weight)
            )

            ht_against.append(
                (ha, weight)
            )

            home_for.append(
                (fh, weight)
            )

            home_against.append(
                (fa, weight)
            )

        else:

            full_for.append(
                (fa, weight)
            )

            full_against.append(
                (fh, weight)
            )

            ht_for.append(
                (ha, weight)
            )

            ht_against.append(
                (hh, weight)
            )

            away_for.append(
                (fa, weight)
            )

            away_against.append(
                (fh, weight)
            )

    def weighted_avg(values):

        if not values:
            return None

        numerator = sum(
            value * weight
            for value, weight in values
        )

        denominator = sum(
            weight
            for _, weight in values
        )

        if denominator <= 0:
            return None

        return numerator / denominator

    return {
        "matches": valid,

        "full_for": weighted_avg(
            full_for
        ),

        "full_against": weighted_avg(
            full_against
        ),

        "ht_for": weighted_avg(
            ht_for
        ),

        "ht_against": weighted_avg(
            ht_against
        ),

        "home_for": weighted_avg(
            home_for
        ),

        "home_against": weighted_avg(
            home_against
        ),

        "away_for": weighted_avg(
            away_for
        ),

        "away_against": weighted_avg(
            away_against
        ),
    }


# ============================================================
# BUTS ATTENDUS
# ============================================================

def expected_goals(
    home_stats,
    away_stats,
):

    # -------------------------------
    # DOMICILE
    # -------------------------------

    values_home = []

    if (
        home_stats["home_for"]
        is not None
    ):

        values_home.append(
            home_stats["home_for"]
        )

    if (
        away_stats["away_against"]
        is not None
    ):

        values_home.append(
            away_stats[
                "away_against"
            ]
        )

    # -------------------------------
    # EXTÉRIEUR
    # -------------------------------

    values_away = []

    if (
        away_stats["away_for"]
        is not None
    ):

        values_away.append(
            away_stats["away_for"]
        )

    if (
        home_stats["home_against"]
        is not None
    ):

        values_away.append(
            home_stats[
                "home_against"
            ]
        )

    if (
        not values_home
        or not values_away
    ):

        return None, None

    lambda_home = np.mean(
        values_home
    )

    lambda_away = np.mean(
        values_away
    )

    # Petit avantage domicile.
    lambda_home *= 1.05

    lambda_away *= 0.97

    lambda_home = float(
        np.clip(
            lambda_home,
            0.10,
            4.50,
        )
    )

    lambda_away = float(
        np.clip(
            lambda_away,
            0.10,
            4.00,
        )
    )

    return (
        lambda_home,
        lambda_away,
    )


# ============================================================
# POISSON
# ============================================================

def poisson(
    goals,
    expected,
):

    return (
        math.exp(-expected)
        * expected ** goals
        / math.factorial(goals)
    )


# ============================================================
# DIXON-COLES
# ============================================================

def dixon_coles(
    home,
    away,
    lh,
    la,
    rho=-0.08,
):

    if home == 0 and away == 0:

        return (
            1
            - lh
            * la
            * rho
        )

    if home == 0 and away == 1:

        return (
            1
            + lh * rho
        )

    if home == 1 and away == 0:

        return (
            1
            + la * rho
        )

    if home == 1 and away == 1:

        return (
            1 - rho
        )

    return 1.0


# ============================================================
# MATRICE SCORE
# ============================================================

def score_matrix(
    lh,
    la,
):

    matrix = {}

    max_goals = 8

    for h in range(
        max_goals + 1
    ):

        for a in range(
            max_goals + 1
        ):

            probability = (
                poisson(h, lh)
                * poisson(a, la)
            )

            probability *= dixon_coles(
                h,
                a,
                lh,
                la,
            )

            matrix[
                (h, a)
            ] = probability

    total = sum(
        matrix.values()
    )

    if total > 0:

        matrix = {
            score: value / total
            for score, value
            in matrix.items()
        }

    return matrix


# ============================================================
# MT/FT
# ============================================================

def mtft_probability(
    home_stats,
    away_stats,
    lh,
    la,
):

    # Part des buts en première période
    ht_factor = 0.46

    lh_ht = (
        lh * ht_factor
    )

    la_ht = (
        la * ht_factor
    )

    lh_2h = (
        lh - lh_ht
    )

    la_2h = (
        la - la_ht
    )

    markets = {
        "1/1": 0.0,
        "X/1": 0.0,
        "2/1": 0.0,
        "1/X": 0.0,
        "X/X": 0.0,
        "2/X": 0.0,
        "1/2": 0.0,
        "X/2": 0.0,
        "2/2": 0.0,
    }

    max_goals = 7

    for h_ht in range(
        max_goals + 1
    ):

        p_h_ht = poisson(
            h_ht,
            lh_ht,
        )

        for a_ht in range(
            max_goals + 1
        ):

            p_a_ht = poisson(
                a_ht,
                la_ht,
            )

            p_ht = (
                p_h_ht
                * p_a_ht
            )

            if h_ht > a_ht:
                ht = "1"
            elif h_ht < a_ht:
                ht = "2"
            else:
                ht = "X"

            for h2 in range(
                max_goals + 1
            ):

                p_h2 = poisson(
                    h2,
                    lh_2h,
                )

                for a2 in range(
                    max_goals + 1
                ):

                    p_a2 = poisson(
                        a2,
                        la_2h,
                    )

                    probability = (
                        p_ht
                        * p_h2
                        * p_a2
                    )

                    hf = (
                        h_ht + h2
                    )

                    af = (
                        a_ht + a2
                    )

                    if hf > af:
                        ft = "1"
                    elif hf < af:
                        ft = "2"
                    else:
                        ft = "X"

                    probability *= dixon_coles(
                        hf,
                        af,
                        lh,
                        la,
                    )

                    markets[
                        f"{ht}/{ft}"
                    ] += probability

    total = sum(
        markets.values()
    )

    if total > 0:

        markets = {
            key: value / total
            for key, value
            in markets.items()
        }

    return markets


# ============================================================
# QUALITÉ
# ============================================================

def quality_score(
    home_stats,
    away_stats,
):

    home_matches = (
        home_stats["matches"]
    )

    away_matches = (
        away_stats["matches"]
    )

    match_quality = min(
        100,
        (
            min(home_matches, 10)
            + min(away_matches, 10)
        )
        * 5,
    )

    fields = [
        "full_for",
        "full_against",
        "ht_for",
        "ht_against",
    ]

    data_count = 0

    for field in fields:

        if home_stats.get(
            field
        ) is not None:

            data_count += 1

        if away_stats.get(
            field
        ) is not None:

            data_count += 1

    field_quality = (
        data_count
        / 8
        * 100
    )

    return (
        0.65 * match_quality
        + 0.35 * field_quality
    )


# ============================================================
# ANALYSE D'UN MATCH
# ============================================================

def analyze_match(
    match,
    selected_date,
):

    home_team = match.get(
        "homeTeam",
        {},
    )

    away_team = match.get(
        "awayTeam",
        {},
    )

    home_id = home_team.get(
        "id"
    )

    away_id = away_team.get(
        "id"
    )

    if not home_id or not away_id:
        return None

    history_home = get_team_history(
        home_id,
        selected_date,
        20,
    )

    history_away = get_team_history(
        away_id,
        selected_date,
        20,
    )

    home_stats = calculate_team_stats(
        history_home,
        home_id,
    )

    away_stats = calculate_team_stats(
        history_away,
        away_id,
    )

    # Minimum de données
    if (
        home_stats["matches"] < 3
        or away_stats["matches"] < 3
    ):
        return None

    lh, la = expected_goals(
        home_stats,
        away_stats,
    )

    if lh is None or la is None:
        return None

    probabilities = mtft_probability(
        home_stats,
        away_stats,
        lh,
        la,
    )

    ranked = sorted(
        probabilities.items(),
        key=lambda x: x[1],
        reverse=True,
    )

    quality = quality_score(
        home_stats,
        away_stats,
    )

    best_probability = (
        ranked[0][1] * 100
    )

    # Score de sélection :
    # probabilité + qualité
    selection_score = (
        best_probability * 0.75
        + quality * 0.25
    )

    return {
        "id": match.get("id"),

        "home": home_team.get(
            "name",
            "Équipe domicile",
        ),

        "away": away_team.get(
            "name",
            "Équipe extérieure",
        ),

        "competition": match.get(
            "competition",
            {},
        ).get(
            "name",
            "Compétition",
        ),

        "utcDate": match.get(
            "utcDate",
            "",
        ),

        "lh": lh,

        "la": la,

        "quality": quality,

        "selection_score":
            selection_score,

        "probabilities":
            ranked,

        "home_matches":
            home_stats["matches"],

        "away_matches":
            away_stats["matches"],
    }


# ============================================================
# INTERFACE
# ============================================================

st.title(
    "⚽ RODRIGUE MT/FT PRO"
)

st.subheader(
    "🔥 Football-Data.org • Poisson • MT/FT"
)

st.caption(
    "Data provided by football-data.org"
)


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.header(
        "⚙️ Configuration"
    )

    today = datetime.now(
        TZ
    ).date()

    selected_date = st.date_input(
        "📅 Date des matchs",
        value=today,
        min_value=date(
            2020,
            1,
            1,
        ),
        max_value=date(
            2035,
            12,
            31,
        ),
    )

    selected_competitions = st.multiselect(
        "🏆 Compétitions",
        options=list(
            COMPETITIONS.keys()
        ),
        default=[
            "PL",
            "BL1",
            "SA",
            "PD",
            "FL1",
            "DED",
            "PPL",
        ],
        format_func=lambda x:
            COMPETITIONS[x],
    )

    max_matches = st.slider(
        "⚽ Nombre de matchs",
        min_value=3,
        max_value=20,
        value=6,
        step=1,
    )


# ============================================================
# ANALYSE
# ============================================================

if st.button(
    "🚀 ANALYSER LES VRAIS MATCHS",
    type="primary",
    use_container_width=True,
):

    try:

        date_string = (
            selected_date.isoformat()
        )

        with st.spinner(
            "🔎 Récupération des vrais matchs..."
        ):

            matches = get_matches_for_date(
                date_string
            )

        # Filtre compétitions
        if selected_competitions:

            matches = [
                match
                for match in matches
                if match.get(
                    "competition",
                    {},
                ).get(
                    "code"
                )
                in selected_competitions
            ]

        # Ne garder que les matchs à venir
        # ou non terminés.
        matches = [
            match
            for match in matches
            if match.get(
                "status"
            )
            not in [
                "FINISHED",
                "CANCELLED",
                "POSTPONED",
            ]
        ]

        if not matches:

            st.error(
                "❌ Aucun match disponible "
                "dans les compétitions sélectionnées."
            )

            st.stop()

        # Limite pour protéger le quota API
        matches = matches[
            :max_matches
        ]

        st.success(
            f"✅ {len(matches)} vrais matchs trouvés."
        )

        results = []

        progress = st.progress(
            0
        )

        status_text = st.empty()

        for index, match in enumerate(
            matches
        ):

            home = match.get(
                "homeTeam",
                {},
            ).get(
                "name",
                "?",
            )

            away = match.get(
                "awayTeam",
                {},
            ).get(
                "name",
                "?",
            )

            status_text.write(
                f"🔎 Analyse : "
                f"{home} — {away}"
            )

            try:

                result = analyze_match(
                    match,
                    date_string,
                )

                if result:
                    results.append(
                        result
                    )

            except Exception as e:

                # Ne bloque pas les autres matchs
                pass

            progress.progress(
                (index + 1)
                / len(matches)
            )

        status_text.empty()

        if not results:

            st.error(
                "❌ Impossible de calculer les probabilités. "
                "Les matchs sélectionnés ne possèdent peut-être "
                "pas assez d'historique accessible avec ta clé."
            )

            st.stop()

        # Classement
        results.sort(
            key=lambda x:
                x["selection_score"],
            reverse=True,
        )

        top3 = results[:3]

        st.success(
            f"🏆 {len(results)} matchs analysés."
        )

        # ====================================================
        # TOP 3
        # ====================================================

        for rank, result in enumerate(
            top3,
            1,
        ):

            ranked = result[
                "probabilities"
            ]

            best_market, best_prob = (
                ranked[0]
            )

            second_market, second_prob = (
                ranked[1]
            )

            third_market, third_prob = (
                ranked[2]
            )

            st.markdown(
                "---"
            )

            st.subheader(
                f"🏆 #{rank} "
                f"{result['home']} "
                f"— "
                f"{result['away']}"
            )

            st.caption(
                f"🏆 {result['competition']}"
            )

            c1, c2, c3 = st.columns(
                3
            )

            c1.metric(
                "🎯 MT/FT",
                best_market,
            )

            c2.metric(
                "📊 Probabilité",
                f"{best_prob * 100:.2f}%",
            )

            c3.metric(
                "🧠 Qualité",
                f"{result['quality']:.0f}%",
            )

            c4, c5 = st.columns(
                2
            )

            c4.metric(
                "⚽ Buts attendus domicile",
                f"{result['lh']:.2f}",
            )

            c5.metric(
                "⚽ Buts attendus extérieur",
                f"{result['la']:.2f}",
            )

            st.write(
                f"🥈 Alternative : "
                f"**{second_market}** "
                f"— {second_prob * 100:.2f}%"
            )

            st.write(
                f"🥉 Alternative : "
                f"**{third_market}** "
                f"— {third_prob * 100:.2f}%"
            )

            st.write(
                f"📚 Historique utilisé : "
                f"{result['home_matches']} matchs "
                f"domicile/équipe + "
                f"{result['away_matches']} matchs "
                f"équipe extérieure"
            )

            table = pd.DataFrame(
                [
                    {
                        "Rang": i + 1,
                        "MT/FT": market,
                        "Probabilité":
                            f"{prob * 100:.2f}%",
                    }
                    for i, (
                        market,
                        prob,
                    ) in enumerate(
                        ranked
                    )
                ]
            )

            st.dataframe(
                table,
                hide_index=True,
                use_container_width=True,
            )

        # ====================================================
        # AVERTISSEMENT
        # ====================================================

        st.markdown(
            "---"
        )

        st.warning(
            "⚠️ Les pourcentages sont des probabilités "
            "estimées par le modèle à partir des données "
            "réelles disponibles. Ils ne constituent jamais "
            "une garantie de résultat à 100 %."
        )

        st.info(
            "💡 Conseil : plus l'historique disponible est "
            "important et récent, plus l'estimation statistique "
            "est exploitable."
        )

    except RuntimeError as e:

        st.error(
            str(e)
        )

    except Exception as e:

        st.error(
            f"❌ Erreur : {e}"
        )
