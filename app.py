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
                "Accès refusé par Football-Data.org : plan gratuit restreint."
            )
        if r.status_code == 429:
            raise RuntimeError(
                "Limite API atteinte. Attends une minute."
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
# API DATA (Optimisé pour respecter la limite de 10 jours de l'API)
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
    # L'API gratuite limite strictement la période à 10 jours maximum par requête
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
        "limit": 50,
    }
    if competition_codes:
        params["competitions"] = ",".join(competition_codes)

    data = api.get(f"/teams/{int(team_id)}/matches", params=params)
    return data.get("matches", [])


# ============================================================
# MATCH / FORM / POISSON
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


def poisson_probability(k, lam):
    lam = max(float(lam), 0.001)
    return math.exp(-lam) * (lam ** k) / math.factorial(k)


def probability_matrix(lambda_home, lambda_away, max_goals=10):
    matrix = np.zeros((max_goals + 1, max_goals + 1), dtype=float)
    for h in range(max_goals + 1):
        for a in range(max_goals + 1):
            matrix[h, a] = poisson_probability(h, lambda_home) * poisson_probability(a, lambda_away)
    total = matrix.sum()
    if total <= 0:
        raise RuntimeError("Erreur modèle Poisson.")
    return matrix / total


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

    markets = {
        "1": p1,
        "X": px,
        "2": p2,
        "1X": p1 + px,
        "X2": px + p2,
        "12": p1 + p2,
        "BTTS Oui": pbtts,
        "BTTS Non": 1 - pbtts,
        "Over 1.5": over(1.5),
        "Under 1.5": 1 - over(1.5),
        "Over 2.5": over(2.5),
        "Under 2.5": 1 - over(2.5),
    }

    scores.sort(key=lambda x: x[1], reverse=True)
    return markets, scores


def build_lambdas(home_form, away_form):
    if not home_form or not away_form:
        return None, None, "Données insuffisantes"

    home_gf = weighted_average(home_form, "gf")
    home_ga = weighted_average(home_form, "ga")
    away_gf = weighted_average(away_form, "gf")
    away_ga = weighted_average(away_form, "ga")

    if None in (home_gf, home_ga, away_gf, away_ga):
        return None, None, "Données insuffisantes"

    lambda_home = (0.58 * home_gf + 0.42 * away_ga) * 1.06
    lambda_away = (0.58 * away_gf + 0.42 * home_ga) * 0.97

    return float(np.clip(lambda_home, 0.10, 5.00)), float(np.clip(lambda_away, 0.10, 5.00)), "OK"


def model_prediction(match, home_form, away_form):
    lambda_home, lambda_away, quality = build_lambdas(home_form, away_form)
    if lambda_home is None:
        return {"status": "INSUFFICIENT"}

    markets, scores = calculate_markets(lambda_home, lambda_away)
    best_market = max(markets.items(), key=lambda x: x[1])

    return {
        "status": "OK",
        "lambda_home": lambda_home,
        "lambda_away": lambda_away,
        "markets": markets,
        "scores": scores,
        "best_market": best_market,
    }


# ============================================================
# UI
# ============================================================

st.title("⚽ Rodrigue Pro Football AI")
st.caption("Football-Data.org V4 • Modèle Poisson")

token = get_token()
if not token:
    st.error("Clé API absente.")
    st.stop()

with st.form("search_form"):
    selected_date = st.date_input("📅 Date des matchs", value=date.today())
    competition_names = st.multiselect(
        "🏆 Compétitions",
        options=list(COMPETITIONS.keys()),
        default=["Premier League", "La Liga", "Ligue 1"],
    )
    col1, col2 = st.form_submit_button("🔎 Charger les matchs"), st.form_submit_button("🧠 Analyser les matchs")

if col1 or col2:
    competition_codes = [COMPETITIONS[name] for name in competition_names] if competition_names else []

    date_from = selected_date.isoformat()
    date_to = (selected_date + timedelta(days=1)).isoformat()

    try:
        with st.spinner("Chargement..."):
            matches = fetch_matches(token, date_from, date_to, competition_codes)

        if not matches:
            st.warning("Aucun match trouvé pour cette date.")
            st.stop()

        st.success(f"{len(matches)} match(s) trouvé(s).")

        if col1 and not col2:
            simple_rows = [{
                "Match": f"{m.get('homeTeam', {}).get('name', '?')} vs {m.get('awayTeam', {}).get('name', '?')}",
                "Compétition": m.get("competition", {}).get("name", ""),
                "Heure": m.get("utcDate", ""),
            } for m in matches]
            st.dataframe(pd.DataFrame(simple_rows), use_container_width=True, hide_index=True)
            st.stop()

        # Correction majeure : on limite strictement l'historique aux 10 derniers jours pour ne pas dépasser l'API gratuite
        history_from = (selected_date - timedelta(days=10)).isoformat()

        with st.spinner("Analyse Poisson en cours..."):
            history = fetch_finished_history(token, history_from, date_from, competition_codes)

            rows = []
            for match in matches:
                home = match.get("homeTeam", {}) or {}
                away = match.get("awayTeam", {}) or {}
                home_id, away_id = home.get("id"), away.get("id")

                home_form = recent_team_form(history, home_id, limit=5)
                away_form = recent_team_form(history, away_id, limit=5)

                # Si l'historique global est vide, on cherche spécifiquement l'équipe sur 30 jours max
                if len(home_form) < 2 and home_id:
                    try:
                        h_hist = fetch_team_matches(token, home_id, (selected_date - timedelta(days=30)).isoformat(), date_from, competition_codes)
                        home_form = recent_team_form(h_hist, home_id, limit=5)
                    except: pass

                if len(away_form) < 2 and away_id:
                    try:
                        a_hist = fetch_team_matches(token, away_id, (selected_date - timedelta(days=30)).isoformat(), date_from, competition_codes)
                        away_form = recent_team_form(a_hist, away_id, limit=5)
                    except: pass

                pred = model_prediction(match, home_form, away_form)

                if pred["status"] == "OK":
                    best_name, best_prob = pred["best_market"]
                    best_score, _ = pred["scores"][0]
                    rows.append({
                        "Match": f"{home.get('name', '?')} vs {away.get('name', '?')}",
                        "Compétition": match.get("competition", {}).get("name", ""),
                        "xG Domicile": round(pred["lambda_home"], 2),
                        "xG Extérieur": round(pred["lambda_away"], 2),
                        "Prédiction": best_name,
                        "Probabilité": f"{best_prob * 100:.1f}%",
                        "Score Exact": best_score,
                    })
                else:
                    rows.append({
                        "Match": f"{home.get('name', '?')} vs {away.get('name', '?')}",
                        "Compétition": match.get("competition", {}).get("name", ""),
                        "xG Domicile": "N/D",
                        "xG Extérieur": "N/D",
                        "Prédiction": "En attente de stats",
                        "Probabilité": "N/D",
                        "Score Exact": "N/D",
                    })

        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    except RuntimeError as exc:
        st.error(str(exc))
    except Exception as exc:
        st.error("Erreur inattendue.")
        st.exception(exc)
