# ============================================================
# RODRIGUE PRO FOOTBALL AI - FOOTBALL-DATA.ORG V5
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
    def __init__(self, token: str):
        self.token = str(token or "").strip()
        self.session = requests.Session()
        self.session.headers.update({
            "X-Auth-Token": self.token,
            "Accept": "application/json",
        })

    def get(self, endpoint: str, params=None):
        if not self.token:
            raise RuntimeError("Clé Football-Data.org absente.")

        try:
            r = self.session.get(
                API_BASE + endpoint,
                params=params or {},
                timeout=30,
            )
        except requests.RequestException as exc:
            raise RuntimeError(f"Erreur réseau API : {exc}") from exc

        if r.status_code == 401:
            raise RuntimeError("Clé Football-Data.org invalide.")
        if r.status_code == 403:
            raise RuntimeError(
                "Accès refusé par Football-Data.org : "
                "cette ressource ou cette compétition n'est pas comprise "
                "dans ton plan."
            )
        if r.status_code == 429:
            raise RuntimeError(
                "Limite API atteinte. Attends une minute avant de relancer."
            )
        if not r.ok:
            try:
                detail = r.json()
            except Exception:
                detail = r.text
            raise RuntimeError(
                f"Football-Data.org HTTP {r.status_code}: {detail}"
            )

        return r.json()


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


# ============================================================
# API DATA
# ============================================================

@st.cache_data(ttl=300, show_spinner=False)
def fetch_matches(token, date_from, date_to, competition_codes):
    api = FootballDataAPI(token)
    params = {
        "dateFrom": date_from,
        "dateTo": date_to,
    }
    if competition_codes:
        params["competitions"] = ",".join(competition_codes)

    data = api.get("/matches", params=params)
    return data.get("matches", [])


@st.cache_data(ttl=900, show_spinner=False)
def fetch_finished_history(token, date_from, date_to, competition_codes):
    api = FootballDataAPI(token)
    params = {
        "dateFrom": date_from,
        "dateTo": date_to,
        "status": "FINISHED",
        "limit": 100,
    }
    if competition_codes:
        params["competitions"] = ",".join(competition_codes)

    data = api.get("/matches", params=params)
    return data.get("matches", [])


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_team_matches(token, team_id, date_from, date_to, competition_codes):
    api = FootballDataAPI(token)
    params = {
        "dateFrom": date_from,
        "dateTo": date_to,
        "status": "FINISHED",
        "limit": 100,
    }
    if competition_codes:
        params["competitions"] = ",".join(competition_codes)

    data = api.get(f"/teams/{int(team_id)}/matches", params=params)
    return data.get("matches", [])


# ============================================================
# MATCH / FORM
# ============================================================

def match_is_finished(match):
    return match.get("status") == "FINISHED"


def team_result(match, team_id):
    home = match.get("homeTeam", {}) or {}
    away = match.get("awayTeam", {}) or {}
    score = match.get("score", {}) or {}
    full = score.get("fullTime", {}) or {}

    hg = full.get("home")
    ag = full.get("away")

    if hg is None or ag is None:
        return None

    if home.get("id") == team_id:
        gf, ga = float(hg), float(ag)
        venue = "HOME"
    elif away.get("id") == team_id:
        gf, ga = float(ag), float(hg)
        venue = "AWAY"
    else:
        return None

    result = "W" if gf > ga else "D" if gf == ga else "L"
    return {
        "gf": gf,
        "ga": ga,
        "result": result,
        "venue": venue,
        "date": match.get("utcDate", ""),
    }


def recent_team_form(all_matches, team_id, limit=10):
    rows = []
    for match in all_matches:
        if not match_is_finished(match):
            continue
        item = team_result(match, team_id)
        if item:
            rows.append(item)

    rows.sort(key=lambda x: x["date"], reverse=True)
    return rows[:limit]


def weighted_average(rows, key):
    if not rows:
        return None
    values = np.array([float(x[key]) for x in rows], dtype=float)
    weights = np.exp(-0.12 * np.arange(len(values)))
    return float(np.average(values, weights=weights))


def average_for_venue(rows, venue):
    selected = [x for x in rows if x["venue"] == venue]
    if not selected:
        return None
    return {
        "gf": weighted_average(selected, "gf"),
        "ga": weighted_average(selected, "ga"),
        "n": len(selected),
    }


def form_string(rows):
    return "".join(x["result"] for x in rows) if rows else "N/D"


# ============================================================
# POISSON
# ============================================================

def poisson_probability(k, lam):
    lam = max(float(lam), 0.001)
    return math.exp(-lam) * (lam ** k) / math.factorial(k)


def probability_matrix(lambda_home, lambda_away, max_goals=10):
    matrix = np.zeros((max_goals + 1, max_goals + 1), dtype=float)

    for h in range(max_goals + 1):
        for a in range(max_goals + 1):
            matrix[h, a] = (
                poisson_probability(h, lambda_home)
                * poisson_probability(a, lambda_away)
            )

    total = matrix.sum()
    if total <= 0:
        raise RuntimeError("Impossible de normaliser le modèle Poisson.")

    return matrix / total


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
            goals = h + a
            totals[goals] = totals.get(goals, 0.0) + p

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
        return sum(p for g, p in totals.items() if g > line)

    def under(line):
        return sum(p for g, p in totals.items() if g < line)

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
    }

    scores.sort(key=lambda x: x[1], reverse=True)
    return markets, scores


def calculate_htft(lambda_home, lambda_away):
    ht_home = max(0.01, lambda_home * 0.46)
    ht_away = max(0.01, lambda_away * 0.46)
    second_home = max(0.01, lambda_home - ht_home)
    second_away = max(0.01, lambda_away - ht_away)

    result = {f"{ht}/{ft}": 0.0 for ht in OUTCOMES for ft in OUTCOMES}

    for h1 in range(8):
        for a1 in range(8):
            p_ht = (
                poisson_probability(h1, ht_home)
                * poisson_probability(a1, ht_away)
            )
            ht_result = result_score(h1, a1)

            for h2 in range(8):
                for a2 in range(8):
                    p = (
                        p_ht
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
# MODEL
# ============================================================

def build_lambdas(home_form, away_form):
    if not home_form or not away_form:
        return None, None, "Données insuffisantes"

    home_gf = weighted_average(home_form, "gf")
    home_ga = weighted_average(home_form, "ga")
    away_gf = weighted_average(away_form, "gf")
    away_ga = weighted_average(away_form, "ga")

    if None in (home_gf, home_ga, away_gf, away_ga):
        return None, None, "Données insuffisantes"

    home_home = average_for_venue(home_form, "HOME")
    away_away = average_for_venue(away_form, "AWAY")

    if home_home and home_home["n"] >= 3:
        home_attack = 0.70 * home_home["gf"] + 0.30 * home_gf
        home_defence = 0.70 * home_home["ga"] + 0.30 * home_ga
    else:
        home_attack = home_gf
        home_defence = home_ga

    if away_away and away_away["n"] >= 3:
        away_attack = 0.70 * away_away["gf"] + 0.30 * away_gf
        away_defence = 0.70 * away_away["ga"] + 0.30 * away_ga
    else:
        away_attack = away_gf
        away_defence = away_ga

    lambda_home = (0.58 * home_attack + 0.42 * away_defence) * 1.06
    lambda_away = (0.58 * away_attack + 0.42 * home_defence) * 0.97

    lambda_home = float(np.clip(lambda_home, 0.10, 5.00))
    lambda_away = float(np.clip(lambda_away, 0.10, 5.00))

    return lambda_home, lambda_away, "OK"


def model_prediction(match, home_form, away_form):
    lambda_home, lambda_away, quality = build_lambdas(home_form, away_form)

    if lambda_home is None or lambda_away is None:
        return {
            "status": "INSUFFICIENT",
            "quality": quality,
            "home_id": match["homeTeam"]["id"],
            "away_id": match["awayTeam"]["id"],
            "lambda_home": None,
            "lambda_away": None,
            "markets": {},
            "scores": [],
            "htft": {},
        }

    markets, scores = calculate_markets(lambda_home, lambda_away)
    htft = calculate_htft(lambda_home, lambda_away)
    best_market = max(markets.items(), key=lambda x: x[1])

    return {
        "status": "OK",
        "quality": quality,
        "home_id": match["homeTeam"]["id"],
        "away_id": match["awayTeam"]["id"],
        "lambda_home": lambda_home,
        "lambda_away": lambda_away,
        "markets": markets,
        "scores": scores,
        "htft": htft,
        "best_market": best_market,
    }


# ============================================================
# UI
# ============================================================

st.title("⚽ Rodrigue Pro Football AI")
st.caption("Football-Data.org V4 • Modèle Poisson")

token = get_token()

if not token:
    st.error("Clé API Football-Data.org absente.")
    st.stop()

# Formulaire pour éviter que la page recharche à chaque changement de date
with st.form("search_form"):
    selected_date = st.date_input("📅 Date des matchs", value=date.today())

    competition_names = st.multiselect(
        "🏆 Compétitions",
        options=list(COMPETITIONS.keys()),
        default=["Premier League", "La Liga", "Ligue 1"],
    )

    history_days = st.slider(
        "📊 Historique utilisé (jours)",
        min_value=30,
        max_value=180,
        value=120,
        step=15,
    )

    col1, col2 = st.form_submit_button("🔎 Charger les matchs"), st.form_submit_button("🧠 Analyser les matchs")

if col1 or col2:
    competition_codes = [COMPETITIONS[name] for name in competition_names] if competition_names else []

    # Recherche sur une fenêtre de 3 jours pour trouver les matchs récents/à venir proches
    date_from = selected_date.isoformat()
    date_to = (selected_date + timedelta(days=2)).isoformat()

    try:
        with st.spinner("Récupération des matchs..."):
            matches = fetch_matches(token, date_from, date_to, competition_codes)

        if not matches:
            st.warning("Aucun match renvoyé pour cette date ou ces compétitions.")
            st.stop()

        st.success(f"{len(matches)} match(s) trouvé(s).")

        if col1 and not col2:
            simple_rows = []
            for match in matches:
                simple_rows.append({
                    "Match": f"{match.get('homeTeam', {}).get('name', '?')} vs {match.get('awayTeam', {}).get('name', '?')}",
                    "Compétition": match.get("competition", {}).get("name", ""),
                    "Date": match.get("utcDate", ""),
                    "Statut": match.get("status", ""),
                })
            st.dataframe(pd.DataFrame(simple_rows), use_container_width=True, hide_index=True)
            st.stop()

        history_from = (selected_date - timedelta(days=history_days)).isoformat()

        with st.spinner("Calcul des formes réelles et analyse Poisson..."):
            history = fetch_finished_history(token, history_from, date_from, competition_codes)

            rows = []
            for match in matches:
                home = match.get("homeTeam", {}) or {}
                away = match.get("awayTeam", {}) or {}

                home_id = home.get("id")
                away_id = away.get("id")

                home_form = recent_team_form(history, home_id, limit=10)
                away_form = recent_team_form(history, away_id, limit=10)

                if len(home_form) < 5 and home_id:
                    try:
                        home_history = fetch_team_matches(token, home_id, history_from, date_from, competition_codes)
                        home_form = recent_team_form(home_history, home_id, limit=10)
                    except RuntimeError:
                        pass

                if len(away_form) < 5 and away_id:
                    try:
                        away_history = fetch_team_matches(token, away_id, history_from, date_from, competition_codes)
                        away_form = recent_team_form(away_history, away_id, limit=10)
                    except RuntimeError:
                        pass

                prediction = model_prediction(match, home_form, away_form)

                if prediction["status"] == "OK":
                    best_name, best_prob = prediction["best_market"]
                    best_score, best_score_prob = prediction["scores"][0]
                    rows.append({
                        "Match": f"{home.get('name', '?')} vs {away.get('name', '?')}",
                        "Compétition": match.get("competition", {}).get("name", ""),
                        "Forme Domicile": form_string(home_form),
                        "Forme Extérieur": form_string(away_form),
                        "xG Domicile": round(prediction["lambda_home"], 2),
                        "xG Extérieur": round(prediction["lambda_away"], 2),
                        "Prédiction": best_name,
                        "Probabilité": f"{best_prob * 100:.1f}%",
                        "Score Exact": best_score,
                    })
                else:
                    rows.append({
                        "Match": f"{home.get('name', '?')} vs {away.get('name', '?')}",
                        "Compétition": match.get("competition", {}).get("name", ""),
                        "Forme Domicile": form_string(home_form),
                        "Forme Extérieur": form_string(away_form),
                        "xG Domicile": "N/D",
                        "xG Extérieur": "N/D",
                        "Prédiction": "Données insuffisantes",
                        "Probabilité": "N/D",
                        "Score Exact": "N/D",
                    })

        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    except RuntimeError as exc:
        st.error(str(exc))
    except Exception as exc:
        st.error("Erreur inattendue.")
        st.exception(exc)
