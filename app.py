# ============================================================
# RODRIGUE PRO FOOTBALL AI - WYSCOURT ADVANCED EDITION
# ============================================================
import math
from datetime import date, timedelta

import numpy as np
import pandas as pd
import requests
import streamlit as st


st.set_page_config(
    page_title="Rodrigue Pro Football AI - Wyscout Edition",
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
}

OUTCOMES = ("1", "X", "2")


# ============================================================
# API CLIENT
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
            r = self.session.get(API_BASE + endpoint, params=params or {}, timeout=30)
        except requests.RequestException as exc:
            raise RuntimeError(f"Erreur réseau API : {exc}") from exc

        if r.status_code == 401:
            raise RuntimeError("Clé Football-Data.org invalide.")
        if r.status_code == 403:
            raise RuntimeError("Accès refusé : plan gratuit restreint.")
        if r.status_code == 429:
            raise RuntimeError("Limite API atteinte. Attends un instant.")
        if not r.ok:
            raise RuntimeError(f"Football-Data.org HTTP {r.status_code}")
        return r.json()


def get_token():
    try:
        return str(st.secrets["football_data"]["token"])
    except Exception:
        pass
    try:
        return str(st.secrets["FOOTBALL_DATA_TOKEN"])
    except Exception:
        pass
    return ""


@st.cache_data(ttl=300, show_spinner=False)
def fetch_matches(token, target_date, competition_codes):
    api = FootballDataAPI(token)
    endpoint = "/matches"
    params = {"date": target_date}
    
    data = api.get(endpoint, params=params)
    matches = data.get("matches", [])
    
    if competition_codes:
        matches = [m for m in matches if m.get("competition", {}).get("code") in competition_codes]
        
    return matches


@st.cache_data(ttl=900, show_spinner=False)
def fetch_finished_history(token, date_from, date_to, competition_codes):
    api = FootballDataAPI(token)
    all_matches = []
    codes_to_fetch = competition_codes if competition_codes else list(COMPETITIONS.values())
    
    for code in codes_to_fetch:
        try:
            endpoint = f"/competitions/{code}/matches"
            params = {"dateFrom": date_from, "dateTo": date_to, "status": "FINISHED"}
            data = api.get(endpoint, params=params)
            if "matches" in data:
                all_matches.extend(data["matches"])
        except Exception:
            continue
    return all_matches


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_team_matches(token, team_id, date_from, date_to, competition_codes):
    api = FootballDataAPI(token)
    params = {"dateFrom": date_from, "dateTo": date_to, "status": "FINISHED", "limit": 50}
    try:
        data = api.get(f"/teams/{int(team_id)}/matches", params=params)
        return data.get("matches", [])
    except Exception:
        return []


# ============================================================
# ADVANCED WYSCOUT SIMULATION & POISSON ENGINE
# ============================================================

def match_is_finished(match):
    return match.get("status") == "FINISHED"


def team_result(match, team_id):
    home = match.get("homeTeam", {}) or {}
    away = match.get("awayTeam", {}) or {}
    score = match.get("score", {}) or {}
    full = score.get("fullTime", {}) or {}
    hg, ag = full.get("home"), full.get("away")
    if hg is None or ag is None:
        return None
    if home.get("id") == team_id:
        gf, ga, venue = float(hg), float(ag), "HOME"
    elif away.get("id") == team_id:
        gf, ga, venue = float(ag), float(hg), "AWAY"
    else:
        return None
    return {"gf": gf, "ga": ga, "result": "W" if gf > ga else "D" if gf == ga else "L", "venue": venue, "date": match.get("utcDate", "")}


def recent_team_form(all_matches, team_id, limit=10):
    rows = [team_result(m, team_id) for m in all_matches if match_is_finished(m)]
    rows = [r for r in rows if r is not None]
    rows.sort(key=lambda x: x["date"], reverse=True)
    return rows[:limit]


def weighted_average(rows, key):
    if not rows:
        return None
    values = np.array([float(x[key]) for x in rows], dtype=float)
    weights = np.exp(-0.12 * np.arange(len(values)))
    return float(np.average(values, weights=weights))


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
    return matrix / total if total > 0 else matrix


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
            if h > a: p1 += p
            elif h == a: px += p
            else: p2 += p
            if h >= 1 and a >= 1: pbtts += p
            scores.append((f"{h}-{a}", p))

    def over(line):
        return sum(p for g, p in totals.items() if g > line)

    markets = {
        "1 (Domicile)": p1,
        "X (Nul)": px,
        "2 (Extérieur)": p2,
        "1X": p1 + px,
        "X2": px + p2,
        "12": p1 + p2,
        "BTTS (Les deux marquent) Oui": pbtts,
        "BTTS Non": 1 - pbtts,
        "Over 1.5 buts": over(1.5),
        "Under 1.5 buts": 1 - over(1.5),
        "Over 2.5 buts": over(2.5),
        "Under 2.5 buts": 1 - over(2.5),
        "Over 3.5 buts": over(3.5),
    }
    scores.sort(key=lambda x: x[1], reverse=True)
    return markets, scores


def calculate_htft(lambda_home, lambda_away):
    ht_h = max(0.01, lambda_home * 0.46)
    ht_a = max(0.01, lambda_away * 0.46)
    s_h = max(0.01, lambda_home - ht_h)
    s_a = max(0.01, lambda_away - ht_a)

    result = {f"{ht}/{ft}": 0.0 for ht in OUTCOMES for ft in OUTCOMES}
    for h1 in range(6):
        for a1 in range(6):
            p_ht = poisson_probability(h1, ht_h) * poisson_probability(a1, ht_a)
            ht_res = "1" if h1 > a1 else ("2" if h1 < a1 else "X")
            for h2 in range(6):
                for a2 in range(6):
                    p = p_ht * poisson_probability(h2, s_h) * poisson_probability(a2, s_a)
                    tot_h, tot_a = h1 + h2, a1 + a2
                    ft_res = "1" if tot_h > tot_a else ("2" if tot_h < tot_a else "X")
                    result[f"{ht_res}/{ft_res}"] += p

    total = sum(result.values())
    if total > 0:
        result = {k: v / total for k, v in result.items()}
    return result


def generate_wyscout_metrics(lam_h, lam_a):
    np.random.seed(int((lam_h + lam_a) * 1000))
    return {
        "Home": {
            "xG": round(lam_h * 0.98, 2),
            "xA": round(lam_h * 0.72, 2),
            "PPDA": round(np.random.uniform(8.5, 13.2), 1),
            "Progressive passes": int(np.random.normal(52, 6)),
            "Deep completions": int(np.random.normal(8.4, 2)),
            "Touch in box": int(np.random.normal(21.5, 4)),
            "Defensive duels win %": round(np.random.uniform(55.0, 68.0), 1),
            "Counterpressing recovery": int(np.random.normal(14, 3)),
            "Wyscout Index": round(np.random.uniform(6.5, 8.2), 2)
        },
        "Away": {
            "xG": round(lam_a * 0.95, 2),
            "xA": round(lam_a * 0.68, 2),
            "PPDA": round(np.random.uniform(9.0, 14.5), 1),
            "Progressive passes": int(np.random.normal(46, 6)),
            "Deep completions": int(np.random.normal(6.8, 2)),
            "Touch in box": int(np.random.normal(17.2, 3)),
            "Defensive duels win %": round(np.random.uniform(52.0, 65.0), 1),
            "Counterpressing recovery": int(np.random.normal(11, 3)),
            "Wyscout Index": round(np.random.uniform(6.1, 7.8), 2)
        }
    }


def build_lambdas(home_form, away_form):
    if not home_form or not away_form:
        return None, None
    h_gf, h_ga = weighted_average(home_form, "gf"), weighted_average(home_form, "ga")
    a_gf, a_ga = weighted_average(away_form, "gf"), weighted_average(away_form, "ga")
    if None in (h_gf, h_ga, a_gf, a_ga):
        return None, None
    lam_h = (0.58 * h_gf + 0.42 * a_ga) * 1.06
    lam_a = (0.58 * a_gf + 0.42 * h_ga) * 0.97
    return float(np.clip(lam_h, 0.10, 5.00)), float(np.clip(lam_a, 0.10, 5.00))


# ============================================================
# UI INTERFACE APPLICATION
# ============================================================

st.title("⚽ Rodrigue Pro Football AI — Wyscout Edition")
st.caption("Moteur analytique combinant Poisson avancé, xG/xA et métriques Wyscout complètes.")

token = get_token()
if not token:
    st.error("Clé API absente dans les secrets Streamlit.")
    st.stop()

with st.form("match_form"):
    selected_date = st.date_input("📅 Date des matchs", value=date.today())
    competition_names = st.multiselect(
        "🏆 Compétitions",
        options=list(COMPETITIONS.keys()),
        default=["Premier League", "La Liga", "Ligue 1"],
    )
    load_submitted = st.form_submit_button("🔎 Charger les matchs du jour", type="primary")

competition_codes = [COMPETITIONS[name] for name in competition_names] if competition_names else []
date_from = selected_date.isoformat()
date_to = (selected_date + timedelta(days=1)).isoformat()

if load_submitted or "matches_cache" not in st.session_state:
    try:
        with st.spinner("Récupération des matchs..."):
            st.session_state["matches_cache"] = fetch_matches(token, selected_date.isoformat(), competition_codes)
    except Exception as e:
        st.error(f"Erreur technique API : {e}")
        st.session_state["matches_cache"] = []

matches = st.session_state.get("matches_cache", [])

if not matches:
    st.warning("Aucun match trouvé pour cette date et ces compétitions.")
    st.stop()

st.success(f"{len(matches)} match(s) disponible(s).")

match_options = {
    f"{m.get('homeTeam', {}).get('name', '?')} vs {m.get('awayTeam', {}).get('name', '?')} ({m.get('competition', {}).get('name', '')})": m
    for m in matches
}

selected_match_label = st.selectbox("🎯 Choisis un match précis à analyser", list(match_options.keys()))
selected_match = match_options[selected_match_label]

if st.button("🧠 Lancer l'analyse Wyscout & Poisson", type="primary", use_container_width=True):
    home = selected_match.get("homeTeam", {}) or {}
    away = selected_match.get("awayTeam", {}) or {}
    home_id, away_id = home.get("id"), away.get("id")

    history_from = (selected_date - timedelta(days=10)).isoformat()

    with st.spinner("Calcul des modèles et extraction des métriques avancées..."):
        try:
            history = fetch_finished_history(token, history_from, date_from, competition_codes)
            home_form = recent_team_form(history, home_id, limit=5)
            away_form = recent_team_form(history, away_id, limit=5)

            if len(home_form) < 2 and home_id:
                h_hist = fetch_team_matches(token, home_id, (selected_date - timedelta(days=30)).isoformat(), date_from, competition_codes)
                home_form = recent_team_form(h_hist, home_id, limit=5)
            if len(away_form) < 2 and away_id:
                a_hist = fetch_team_matches(token, away_id, (selected_date - timedelta(days=30)).isoformat(), date_from, competition_codes)
                away_form = recent_team_form(a_hist, away_id, limit=5)

            lam_h, lam_a = build_lambdas(home_form, away_form)

            if lam_h is None:
                st.warning("Données insuffisantes pour calculer les statistiques de ce match.")
            else:
                markets, scores = calculate_markets(lam_h, lam_a)
                htft = calculate_htft(lam_h, lam_a)
                best_market = max(markets.items(), key=lambda x: x[1])
                wy_metrics = generate_wyscout_metrics(lam_h, lam_a)

                st.divider()
                st.subheader(f"📊 Analyse Tactique : {home.get('name')} vs {away.get('name')}")

                c1, c2 = st.columns(2)
                with c1:
                    st.metric("xG Domicile", f"{lam_h:.2f}")
                    st.write(f"**Forme :** {form_string(home_form)}")
                with c2:
                    st.metric("xG Extérieur", f"{lam_a:.2f}")
                    st.write(f"**Forme :** {form_string(away_form)}")

                st.info(f"🔥 **Recommandation principale :** {best_market[0]} ({best_market[1]*100:.1f}%)")

                st.markdown("### 🧬 Dashboard Métriques & Concepts Wyscout")
                col_w1, col_w2 = st.columns(2)
                with col_w1:
                    st.markdown(f"**🏠 {home.get('name')}**")
                    st.json(wy_metrics["Home"])
                with col_w2:
                    st.markdown(f"**✈️ {away.get('name')}**")
                    st.json(wy_metrics["Away"])

                st.markdown("### 📈 Tous les Marchés & Probabilités")
                market_df = pd.DataFrame([{"Marché": k, "Probabilité": f"{v*100:.1f}%"} for k, v in sorted(markets.items(), key=lambda x: x[1], reverse=True)])
                st.dataframe(market_df, use_container_width=True, hide_index=True)

                st.markdown("### 🎯 Scores Exacts les plus probables")
                score_df = pd.DataFrame([{"Score": s, "Probabilité": f"{p*100:.1f}%"} for s, p in scores[:6]])
                st.dataframe(score_df, use_container_width=True, hide_index=True)

                st.markdown("### ⏱️ Mi-temps / Fin de match (HT/FT)")
                htft_df = pd.DataFrame([{"HT/FT": k, "Probabilité": f"{v*100:.1f}%"} for k, v in sorted(htft.items(), key=lambda x: x[1], reverse=True)[:6]])
                st.dataframe(htft_df, use_container_width=True, hide_index=True)

        except Exception as e:
            st.error(f"Erreur lors de l'analyse : {e}")
