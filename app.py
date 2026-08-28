# ============================================================
# RODRIGUE PRO FOOTBALL AI - FOOTBALL-DATA.ORG V4
# ============================================================
# Installation:
#   pip install streamlit requests pandas numpy
#
# Streamlit Cloud:
#   Settings > Secrets
#   [football_data]
#   token = "TA_CLE_FOOTBALL_DATA"
#
# Local:
#   create .streamlit/secrets.toml with:
#   [football_data]
#   token = "TA_CLE_FOOTBALL_DATA"
#
# API: https://api.football-data.org/v4
#
# Important:
# football-data.org does NOT expose injuries, H2H, bookmaker odds,
# corners/cards and detailed statistics on the basic/free coverage.
# The application therefore does not invent those data.
# ============================================================

import math
from datetime import date, timedelta

import numpy as np
import pandas as pd
import requests
import streamlit as st


st.set_page_config(
    page_title="Rodrigue Pro Football AI",
    page_icon="⚽",
    layout="wide",
)

API_BASE = "https://api.football-data.org/v4"

# Main competitions commonly available on the free tier.
COMPETITIONS = {
    "Premier League": "PL",
    "La Liga": "PD",
    "Bundesliga": "BL1",
    "Serie A": "SA",
    "Ligue 1": "FL1",
    "Champions League": "CL",
    "Eredivisie": "DED",
    "Primeira Liga": "PPL",
    "Championship": "ELC",
    "Brasileirão Série A": "BSA",
    "World Cup": "WC",
    "European Championship": "EC",
}

OUTCOMES = ("1", "X", "2")


# ============================================================
# API
# ============================================================

class FootballDataAPI:
    def __init__(self, token):
        self.token = token.strip()
        self.session = requests.Session()
        self.session.headers.update({
            "X-Auth-Token": self.token,
            "Accept": "application/json",
        })

    def get(self, endpoint, params=None):
        if not self.token:
            raise RuntimeError("Clé Football-Data.org absente.")

        try:
            response = self.session.get(
                API_BASE + endpoint,
                params=params or {},
                timeout=30,
            )
        except requests.RequestException as exc:
            raise RuntimeError(f"Erreur réseau: {exc}") from exc

        if response.status_code == 401:
            raise RuntimeError("Clé Football-Data.org invalide.")
        if response.status_code == 403:
            raise RuntimeError(
                "Accès refusé: cette compétition ou cette donnée "
                "n'est pas incluse dans ton abonnement."
            )
        if response.status_code == 429:
            raise RuntimeError(
                "Limite API atteinte. Attends environ une minute puis réessaie."
            )

        if not response.ok:
            try:
                detail = response.json()
            except Exception:
                detail = response.text
            raise RuntimeError(
                f"Football-Data.org HTTP {response.status_code}: {detail}"
            )

        return response.json()


# ============================================================
# MATHS
# ============================================================

def poisson_probability(k, lam):
    lam = max(float(lam), 0.001)
    return math.exp(-lam) * lam ** k / math.factorial(k)


def probability_matrix(lambda_home, lambda_away, max_goals=8):
    matrix = np.zeros((max_goals + 1, max_goals + 1))

    for h in range(max_goals + 1):
        for a in range(max_goals + 1):
            matrix[h, a] = (
                poisson_probability(h, lambda_home)
                * poisson_probability(a, lambda_away)
            )

    total = matrix.sum()
    if total:
        matrix /= total
    return matrix


def result_score(home, away):
    if home > away:
        return "1"
    if home < away:
        return "2"
    return "X"


def calculate_markets(lambda_home, lambda_away):
    matrix = probability_matrix(lambda_home, lambda_away)
    totals = {}
    p1 = px = p2 = pbtts = 0.0
    scores = []

    for h in range(matrix.shape[0]):
        for a in range(matrix.shape[1]):
            p = float(matrix[h, a])
            totals[h + a] = totals.get(h + a, 0.0) + p

            if h > a:
                p1 += p
            elif h == a:
                px += p
            else:
                p2 += p

            if h >= 1 and a >= 1:
                pbtts += p

            scores.append((f"{h}-{a}", p))

    def over(line):
        return sum(p for goals, p in totals.items() if goals > line)

    def under(line):
        return sum(p for goals, p in totals.items() if goals < line)

    markets = {
        "1": p1,
        "X": px,
        "2": p2,
        "1X": p1 + px,
        "X2": px + p2,
        "12": p1 + p2,
        "BTTS Oui": pbtts,
        "BTTS Non": 1 - pbtts,
        "Over 0.5": over(0.5),
        "Under 0.5": under(0.5),
        "Over 1.5": over(1.5),
        "Under 1.5": under(1.5),
        "Over 2.5": over(2.5),
        "Under 2.5": under(2.5),
        "Over 3.5": over(3.5),
        "Under 3.5": under(3.5),
        "Over 4.5": over(4.5),
        "Under 4.5": under(4.5),
    }

    # Asian total 4.0: push is handled separately.
    p_eq_4 = totals.get(4, 0.0)
    markets["Over 4.0"] = over(4.0)
    markets["Under 4.0"] = under(4.0)

    # These are intentionally approximations, not independent probabilities.
    markets["BTTS + Over 2.5"] = sum(
        float(matrix[h, a])
        for h in range(matrix.shape[0])
        for a in range(matrix.shape[1])
        if h >= 1 and a >= 1 and h + a > 2.5
    )
    markets["BTTS + Under 2.5"] = sum(
        float(matrix[h, a])
        for h in range(matrix.shape[0])
        for a in range(matrix.shape[1])
        if h >= 1 and a >= 1 and h + a < 2.5
    )

    scores.sort(key=lambda x: x[1], reverse=True)
    return markets, scores, p_eq_4


def calculate_htft(lambda_home, lambda_away):
    ht_home = max(0.01, lambda_home * 0.46)
    ht_away = max(0.01, lambda_away * 0.46)
    second_home = max(0.01, lambda_home - ht_home)
    second_away = max(0.01, lambda_away - ht_away)

    result = {f"{ht}/{ft}": 0.0 for ht in OUTCOMES for ft in OUTCOMES}

    for h1 in range(7):
        for a1 in range(7):
            p1 = poisson_probability(h1, ht_home)
            p2 = poisson_probability(a1, ht_away)
            ht_p = p1 * p2
            ht_result = result_score(h1, a1)

            for h2 in range(7):
                for a2 in range(7):
                    p = (
                        ht_p
                        * poisson_probability(h2, second_home)
                        * poisson_probability(a2, second_away)
                    )
                    ft_result = result_score(h1 + h2, a1 + a2)
                    result[f"{ht_result}/{ft_result}"] += p

    total = sum(result.values())
    if total:
        result = {k: v / total for k, v in result.items()}
    return result


# ============================================================
# MATCHES / FORM
# ============================================================

def match_is_finished(match):
    return match.get("status") == "FINISHED"


def team_result(match, team_id):
    home = match.get("homeTeam", {})
    away = match.get("awayTeam", {})
    score = match.get("score", {}).get("fullTime", {})

    hg = score.get("home")
    ag = score.get("away")

    if hg is None or ag is None:
        return None

    if home.get("id") == team_id:
        gf, ga = hg, ag
    elif away.get("id") == team_id:
        gf, ga = ag, hg
    else:
        return None

    result = "W" if gf > ga else "D" if gf == ga else "L"
    return {"gf": gf, "ga": ga, "result": result}


def recent_team_form(all_matches, team_id, limit=10):
    rows = []

    for match in all_matches:
        if not match_is_finished(match):
            continue

        data = team_result(match, team_id)
        if not data:
            continue

        rows.append({
            "date": match.get("utcDate", ""),
            "gf": data["gf"],
            "ga": data["ga"],
            "result": data["result"],
        })

    rows.sort(key=lambda x: x["date"], reverse=True)
    return rows[:limit]


def weighted_average(rows, key, default):
    if not rows:
        return default

    values = [float(r[key]) for r in rows]
    weights = [math.exp(-0.15 * i) for i in range(len(values))]
    return float(np.average(values, weights=weights))


def form_string(rows):
    return "".join(r["result"] for r in rows)


# ============================================================
# MODEL
# ============================================================

def model_prediction(match, home_form, away_form):
    home_id = match["homeTeam"]["id"]
    away_id = match["awayTeam"]["id"]

    home_gf = weighted_average(home_form, "gf", 1.35)
    home_ga = weighted_average(home_form, "ga", 1.20)
    away_gf = weighted_average(away_form, "gf", 1.20)
    away_ga = weighted_average(away_form, "ga", 1.35)

    # Recent form is the available data source. Home advantage is modest.
    lambda_home = (
        0.58 * home_gf
        + 0.42 * away_ga
    ) * 1.06

    lambda_away = (
        0.58 * away_gf
        + 0.42 * home_ga
    ) * 0.97

    lambda_home = float(np.clip(lambda_home, 0.15, 4.50))
    lambda_away = float(np.clip(lambda_away, 0.15, 4.50))

    markets, scores, p4 = calculate_markets(
        lambda_home, lambda_away
    )
    htft = calculate_htft(lambda_home, lambda_away)

    best_market = max(markets.items(), key=lambda x: x[1])

    return {
        "home_id": home_id,
        "away_id": away_id,
        "lambda_home": lambda_home,
        "lambda_away": lambda_away,
        "markets": markets,
        "scores": scores,
        "htft": htft,
        "best_market": best_market,
        "p4": p4,
    }


# ============================================================
# API HELPERS
# ============================================================

@st.cache_data(ttl=300, show_spinner=False)
def fetch_matches(token, date_from, date_to, competition_codes):
    api = FootballDataAPI(token)
    data = api.get(
        "/matches",
        params={
            "dateFrom": date_from,
            "dateTo": date_to,
            "competitions": ",".join(competition_codes),
        },
    )
    return data.get("matches", [])


@st.cache_data(ttl=600, show_spinner=False)
def fetch_recent_matches(token, date_from, date_to, competition_codes):
    api = FootballDataAPI(token)
    data = api.get(
        "/matches",
        params={
            "dateFrom": date_from,
            "dateTo": date_to,
            "competitions": ",".join(competition_codes),
            "status": "FINISHED",
        },
    )
    return data.get("matches", [])


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_competitions(token):
    api = FootballDataAPI(token)
    data = api.get("/competitions")
    return data.get("competitions", [])


# ============================================================
# INTERFACE
# ============================================================

def get_token():
    try:
        token = st.secrets["football_data"]["token"]
        if token:
            return str(token)
    except Exception:
        pass

    try:
        token = st.secrets["FOOTBALL_DATA_TOKEN"]
        if token:
            return str(token)
    except Exception:
        pass

    return ""


st.title("⚽ Rodrigue Pro Football AI")
st.caption(
    "Analyse probabiliste basée sur les résultats disponibles via Football-Data.org. "
    "Aucune garantie de gain."
)

token = get_token()

if not token:
    st.error(
        "Clé API absente. Ajoute ta clé dans les Secrets Streamlit."
    )
    st.code(
        '[football_data]\n'
        'token = "TA_CLE_FOOTBALL_DATA"',
        language="toml",
    )
    st.info(
        "Sur Streamlit Cloud : Settings → Secrets → colle le bloc ci-dessus."
    )
    st.stop()

# Date du jour du serveur. L'utilisateur peut choisir une autre date.
selected_date = st.date_input(
    "📅 Date des matchs",
    value=date.today(),
)

competition_names = st.multiselect(
    "🏆 Compétitions",
    options=list(COMPETITIONS.keys()),
    default=[
        "Premier League",
        "La Liga",
        "Bundesliga",
        "Serie A",
        "Ligue 1",
    ],
)

if not competition_names:
    st.warning("Sélectionne au moins une compétition.")
    st.stop()

competition_codes = [
    COMPETITIONS[name] for name in competition_names
]

col1, col2 = st.columns(2)

with col1:
    load_button = st.button(
        "🔎 Charger les matchs",
        type="primary",
        use_container_width=True,
    )

with col2:
    analyze_button = st.button(
        "🧠 Analyser les matchs",
        use_container_width=True,
    )

if load_button or analyze_button:
    date_from = selected_date.isoformat()
    date_to = selected_date.isoformat()

    try:
        with st.spinner("Récupération des vrais matchs..."):
            matches = fetch_matches(
                token,
                date_from,
                date_to,
                competition_codes,
            )

        if not matches:
            st.warning(
                "Aucun match disponible dans les compétitions sélectionnées "
                f"pour le {selected_date.strftime('%d/%m/%Y')}."
            )
            st.info(
                "Cela signifie qu'aucun match n'est renvoyé par "
                "Football-Data.org pour cette date/ces compétitions. "
                "Ce n'est pas une erreur du modèle."
            )
            st.stop()

        # Analyse uniquement si demandée.
        if analyze_button:
            history_from = (
                selected_date - timedelta(days=90)
            ).isoformat()

            with st.spinner(
                "Calcul de la forme récente et des probabilités..."
            ):
                history = fetch_recent_matches(
                    token,
                    history_from,
                    date_from,
                    competition_codes,
                )

                rows = []

                for match in matches:
                    home = match.get("homeTeam", {})
                    away = match.get("awayTeam", {})

                    home_form = recent_team_form(
                        history,
                        home.get("id"),
                    )
                    away_form = recent_team_form(
                        history,
                        away.get("id"),
                    )

                    prediction = model_prediction(
                        match,
                        home_form,
                        away_form,
                    )

                    best_name, best_prob = prediction["best_market"]

                    rows.append({
                        "Match": (
                            f"{home.get('name', '?')} "
                            f"vs "
                            f"{away.get('name', '?')}"
                        ),
                        "Compétition": (
                            match.get("competition", {})
                            .get("name", "")
                        ),
                        "Heure UTC": (
                            match.get("utcDate", "")
                            .replace("T", " ")
                            .replace("Z", "")
                        ),
                        "Forme domicile": form_string(home_form),
                        "Forme extérieur": form_string(away_form),
                        "Buts attendus domicile": round(
                            prediction["lambda_home"], 2
                        ),
                        "Buts attendus extérieur": round(
                            prediction["lambda_away"], 2
                        ),
                        "Meilleure sélection": best_name,
                        "Probabilité": round(
                            best_prob * 100, 1
                        ),
                        "_prediction": prediction,
                    })

                # Tri par probabilité décroissante.
                rows.sort(
                    key=lambda x: x["Probabilité"],
                    reverse=True,
                )

            display_rows = [
                {k: v for k, v in row.items() if k != "_prediction"}
                for row in rows
            ]

            st.subheader(
                f"📊 Analyses — {len(rows)} match(s)"
            )

            st.dataframe(
                pd.DataFrame(display_rows),
                use_container_width=True,
                hide_index=True,
            )

            st.subheader("🎯 Détail des prédictions")

            for index, row in enumerate(rows):
                match = matches[
                    next(
                        i for i, m in enumerate(matches)
                        if (
                            m.get("homeTeam", {}).get("id")
                            == row["_prediction"]["home_id"]
                            and
                            m.get("awayTeam", {}).get("id")
                            == row["_prediction"]["away_id"]
                        )
                    )
                ]

                prediction = row["_prediction"]

                with st.expander(
                    f"{index + 1}. {row['Match']} — "
                    f"{row['Meilleure sélection']} "
                    f"({row['Probabilité']:.1f}%)"
                ):
                    c1, c2, c3 = st.columns(3)

                    with c1:
                        st.metric(
                            "Buts attendus domicile",
                            f"{prediction['lambda_home']:.2f}",
                        )

                    with c2:
                        st.metric(
                            "Buts attendus extérieur",
                            f"{prediction['lambda_away']:.2f}",
                        )

                    with c3:
                        st.metric(
                            "Meilleure sélection",
                            f"{row['Meilleure sélection']}",
                            f"{row['Probabilité']:.1f}%",
                        )

                    market_df = pd.DataFrame([
                        {
                            "Marché": name,
                            "Probabilité": f"{prob * 100:.1f}%",
                        }
                        for name, prob in sorted(
                            prediction["markets"].items(),
                            key=lambda x: x[1],
                            reverse=True,
                        )
                    ])

                    st.write("**📈 Marchés principaux**")
                    st.dataframe(
                        market_df,
                        use_container_width=True,
                        hide_index=True,
                    )

                    score_df = pd.DataFrame([
                        {
                            "Score": score,
                            "Probabilité": f"{prob * 100:.1f}%",
                        }
                        for score, prob
                        in prediction["scores"][:10]
                    ])

                    st.write("**🎯 10 scores exacts les plus probables**")
                    st.dataframe(
                        score_df,
                        use_container_width=True,
                        hide_index=True,
                    )

                    htft_df = pd.DataFrame([
                        {
                            "HT/FT": name,
                            "Probabilité": f"{prob * 100:.1f}%",
                        }
                        for name, prob in sorted(
                            prediction["htft"].items(),
                            key=lambda x: x[1],
                            reverse=True,
                        )[:9]
                    ])

                    st.write("**🕐 HT/FT**")
                    st.dataframe(
                        htft_df,
                        use_container_width=True,
                        hide_index=True,
                    )

                    st.caption(
                        "Les probabilités sont celles du modèle Poisson "
                        "à partir des résultats récents disponibles. "
                        "Elles ne représentent pas une certitude."
                    )

        else:
            # Mode affichage simple.
            simple_rows = []

            for match in matches:
                simple_rows.append({
                    "Heure UTC": (
                        match.get("utcDate", "")
                        .replace("T", " ")
                        .replace("Z", "")
                    ),
                    "Compétition": (
                        match.get("competition", {})
                        .get("name", "")
                    ),
                    "Domicile": (
                        match.get("homeTeam", {})
                        .get("name", "")
                    ),
                    "Extérieur": (
                        match.get("awayTeam", {})
                        .get("name", "")
                    ),
                    "Statut": match.get("status", ""),
                    "Stade": match.get("venue", ""),
                })

            st.dataframe(
                pd.DataFrame(simple_rows),
                use_container_width=True,
                hide_index=True,
            )

except RuntimeError as exc:
    st.error(str(exc))

except Exception as exc:
    st.error(
        "Une erreur inattendue est survenue."
    )
    st.code(
        str(exc),
        language="text",
    )


st.divider()

st.markdown(
    """
### ℹ️ Données non disponibles avec l'API de base

Football-Data.org fournit notamment les matchs, résultats et classements,
mais les **blessures**, **cotes bookmakers**, **H2H détaillé** et plusieurs
statistiques avancées ne sont pas inclus dans la couverture gratuite de base.

L'application ne les invente pas : elle affiche uniquement les données
réellement reçues de l'API.
"""
)

st.caption(
    "Rodrigue Pro Football AI • Probabilités statistiques, pas garantie de gain."
)
