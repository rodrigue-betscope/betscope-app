# -*- coding: utf-8 -*-
"""
RODRIGUE PRO FOOTBALL AI — V3 RAPIDAPI DYNAMIC
==============================================
Application Streamlit d'analyse football multi-facteurs avec API-Football (RapidAPI).
"""

import os
import re
import math
from datetime import datetime
import requests
import numpy as np
import pandas as pd
import streamlit as st

# ============================================================
# CONFIG
# ============================================================

st.set_page_config(
    page_title="Rodrigue Pro Football AI V3",
    page_icon="⚽",
    layout="wide",
)

RAPIDAPI_HOST = "api-football-v1.p.rapidapi.com"
SERP_URL = "https://serpapi.com/search.json"
TIMEOUT = 20
MAX_GOALS = 8
HISTORY_LIMIT = 15

# Correspondance des ligues avec les IDs officiels de API-Football
LEAGUES = {
    "Premier League": 39,
    "LaLiga": 140,
    "Bundesliga": 78,
    "Serie A": 135,
    "Ligue 1": 61,
    "Eredivisie": 88,
    "Primeira Liga": 94,
    "Championship": 40,
    "Brasileirão": 71,
    "Champions League": 2,
}

# ============================================================
# SESSION STATE
# ============================================================

for key, default in {
    "matches": [],
    "analysis": None,
    "loaded_date": None,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# ============================================================
# OUTILS
# ============================================================

def safe_float(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return default

def clamp(x, lo, hi):
    return max(lo, min(hi, x))

def pct(x):
    return round(100.0 * float(x), 2)

def poisson(k, lam):
    lam = max(float(lam), 0.0001)
    return math.exp(-lam) * (lam ** k) / math.factorial(k)

def api_get(url, headers=None, params=None):
    response = requests.get(
        url,
        headers=headers or {},
        params=params or {},
        timeout=TIMEOUT,
    )
    if response.status_code == 429:
        raise RuntimeError("Limite API atteinte (HTTP 429).")
    if response.status_code >= 400:
        raise RuntimeError(f"API HTTP {response.status_code}: {response.text[:300]}")
    return response.json()

# ============================================================
# API-FOOTBALL (RAPIDAPI)
# ============================================================

def rapid_headers(api_key):
    if not api_key:
        raise RuntimeError("Clé RapidAPI manquante.")
    return {
        "X-RapidAPI-Key": api_key,
        "X-RapidAPI-Host": RAPIDAPI_HOST,
    }

@st.cache_data(ttl=300, show_spinner=False)
def get_matches_rapid(api_key, date_str):
    url = f"https://{RAPIDAPI_HOST}/v3/fixtures"
    data = api_get(url, rapid_headers(api_key), {"date": date_str})
    return data.get("response", [])

@st.cache_data(ttl=900, show_spinner=False)
def get_team_history_rapid(api_key, team_id, limit=HISTORY_LIMIT):
    url = f"https://{RAPIDAPI_HOST}/v3/fixtures"
    data = api_get(url, rapid_headers(api_key), {"team": team_id, "last": limit})
    return data.get("response", [])

@st.cache_data(ttl=1800, show_spinner=False)
def get_standings_rapid(api_key, league_id):
    if not league_id:
        return []
    # Année en cours dynamique (ex: 2026)
    season = datetime.now().year
    url = f"https://{RAPIDAPI_HOST}/v3/standings"
    data = api_get(url, rapid_headers(api_key), {"league": league_id, "season": season})
    response = data.get("response", [])
    if response:
        return response[0].get("league", {}).get("standings", [[]])[0]
    return []

def format_match_from_rapid(item):
    fixture = item.get("fixture", {})
    teams = item.get("teams", {})
    league = item.get("league", {})
    goals = item.get("goals", {})
    score = item.get("score", {})

    return {
        "id": fixture.get("id"),
        "utcDate": fixture.get("date"),
        "venue": fixture.get("venue", {}).get("name"),
        "competition": {
            "id": league.get("id"),
            "name": league.get("name"),
            "code": league.get("id"),
        },
        "homeTeam": {
            "id": teams.get("home", {}).get("id"),
            "name": teams.get("home", {}).get("name"),
        },
        "awayTeam": {
            "id": teams.get("away", {}).get("id"),
            "name": teams.get("away", {}).get("name"),
        },
        "score": {
            "fullTime": {"home": goals.get("home"), "away": goals.get("away")},
            "halfTime": {"home": score.get("halftime", {}).get("home"), "away": score.get("halftime", {}).get("away")}
        }
    }

def team_match_row_rapid(fixture_item, team_id):
    f = fixture_item.get("fixture", {})
    teams = fixture_item.get("teams", {})
    goals = fixture_item.get("goals", {})
    score = fixture_item.get("score", {})

    home_id = teams.get("home", {}).get("id")
    away_id = teams.get("away", {}).get("id")

    gf = goals.get("home")
    ga = goals.get("away")

    if gf is None or ga is None:
        return None

    if home_id == team_id:
        venue = "HOME"
        opponent = teams.get("away", {}).get("name", "?")
        ht_gf = score.get("halftime", {}).get("home")
        ht_ga = score.get("halftime", {}).get("away")
    elif away_id == team_id:
        venue = "AWAY"
        opponent = teams.get("home", {}).get("name", "?")
        gf, ga = ga, gf
        ht_gf = score.get("halftime", {}).get("away")
        ht_ga = score.get("halftime", {}).get("home")
    else:
        return None

    return {
        "date": f.get("date", ""),
        "gf": int(gf),
        "ga": int(ga),
        "venue": venue,
        "result": "W" if gf > ga else "D" if gf == ga else "L",
        "ht_gf": ht_gf,
        "ht_ga": ht_ga,
        "opponent": opponent,
        "competition": fixture_item.get("league", {}).get("name", ""),
    }

def summarize_history_rapid(api_key, team_id):
    matches = get_team_history_rapid(api_key, team_id, HISTORY_LIMIT)
    rows = [team_match_row_rapid(m, team_id) for m in matches]
    rows = [r for r in rows if r]

    if not rows:
        return {
            "n": 0, "gf": None, "ga": None, "home_gf": None, "home_ga": None,
            "away_gf": None, "away_ga": None, "ht_gf": None, "ht_ga": None,
            "form": "", "btts": None, "over15": None, "over25": None, "rows": []
        }

    def avg(values):
        return float(np.mean(values)) if values else None

    home = [r for r in rows if r["venue"] == "HOME"]
    away = [r for r in rows if r["venue"] == "AWAY"]

    btts = np.mean([r["gf"] > 0 and r["ga"] > 0 for r in rows])
    over15 = np.mean([r["gf"] + r["ga"] > 1.5 for r in rows])
    over25 = np.mean([r["gf"] + r["ga"] > 2.5 for r in rows])

    return {
        "n": len(rows),
        "gf": avg([r["gf"] for r in rows]),
        "ga": avg([r["ga"] for r in rows]),
        "home_gf": avg([r["gf"] for r in home]),
        "home_ga": avg([r["ga"] for r in home]),
        "away_gf": avg([r["gf"] for r in away]),
        "away_ga": avg([r["ga"] for r in away]),
        "ht_gf": avg([r["ht_gf"] for r in rows if r["ht_gf"] is not None]),
        "ht_ga": avg([r["ht_ga"] for r in rows if r["ht_ga"] is not None]),
        "form": "".join(r["result"] for r in rows[:5]),
        "btts": float(btts),
        "over15": float(over15),
        "over25": float(over25),
        "rows": rows,
    }

def standing_row_rapid(api_key, league_id, team_id):
    try:
        rows = get_standings_rapid(api_key, league_id)
    except Exception:
        return None

    for row in rows:
        if row.get("team", {}).get("id") == team_id:
            return {
                "position": row.get("rank"),
                "points": row.get("points"),
                "playedGames": row.get("all", {}).get("played"),
                "goalsFor": row.get("all", {}).get("goals", {}).get("for"),
                "goalsAgainst": row.get("all", {}).get("goals", {}).get("against"),
                "goalDifference": row.get("goalsDiff"),
            }
    return None

# ============================================================
# RECHERCHE WEB
# ============================================================

def serp_search(api_key, query, num=5):
    if not api_key:
        return []
    try:
        data = api_get(SERP_URL, params={"engine": "google", "q": query, "api_key": api_key, "hl": "fr", "gl": "cm", "num": num})
    except Exception:
        return []
    return [{"title": i.get("title", ""), "snippet": i.get("snippet", ""), "link": i.get("link", "")} for i in data.get("organic_results", [])]

def web_research(home, away, serp_key):
    queries = [
        f'"{home}" blessures absences suspensions composition probable',
        f'"{away}" blessures absences suspensions composition probable',
        f'"{home}" "{away}" preview statistiques',
    ]
    return {q: serp_search(serp_key, q, 5) for q in queries}

def extract_absence_evidence(search_results):
    evidence = []
    injury_words = ["blessé", "blessure", "injury", "injured", "suspendu", "absent", "out"]
    for q, items in search_results.items():
        for item in items:
            text = f"{item.get('title', '')} {item.get('snippet', '')}".lower()
            if any(w in text for w in injury_words):
                evidence.append(item)
    return evidence

# ============================================================
# MODELE & MARCHES (Poisson / Buts)
# ============================================================

def expected_goals(home_stats, away_stats, home_odds=None, away_odds=None):
    base = 1.35
    hxg = 0.50 * (home_stats["home_gf"] or home_stats["gf"] or base) + 0.30 * (away_stats["away_ga"] or base) + 0.20 * base
    axg = 0.50 * (away_stats["away_gf"] or away_stats["gf"] or base) + 0.30 * (home_stats["home_ga"] or base) + 0.20 * base
    hxg *= 1.05
    axg *= 0.96
    return clamp(hxg, 0.10, 4.50), clamp(axg, 0.10, 4.50)

def goal_matrix(hxg, axg):
    matrix = {}
    for h in range(MAX_GOALS + 1):
        for a in range(MAX_GOALS + 1):
            matrix[(h, a)] = poisson(h, hxg) * poisson(a, axg)
    total = sum(matrix.values())
    if total:
        matrix = {k: v / total for k, v in matrix.items()}
    return matrix

def market_probs(matrix):
    out = {"1": 0.0, "X": 0.0, "2": 0.0, "1X": 0.0, "X2": 0.0, "12": 0.0, "BTTS Oui": 0.0, "BTTS Non": 0.0}
    for line in [0.5, 1.5, 2.5, 3.5]:
        out[f"O{line}"] = 0.0

    for (h, a), p in matrix.items():
        if h > a: out["1"] += p
        elif h == a: out["X"] += p
        else: out["2"] += p
        tot = h + a
        for line in [0.5, 1.5, 2.5, 3.5]:
            if tot > line: out[f"O{line}"] += p
        if h > 0 and a > 0: out["BTTS Oui"] += p

    out["1X"] = out["1"] + out["X"]
    out["X2"] = out["X"] + out["2"]
    out["12"] = out["1"] + out["2"]
    out["BTTS Non"] = 1 - out["BTTS Oui"]
    for line in [0.5, 1.5, 2.5, 3.5]:
        out[f"U{line}"] = 1 - out[f"O{line}"]
    return out

def exact_scores(matrix, n=10):
    return sorted([{"Score": f"{h}-{a}", "Probabilité": pct(p)} for (h, a), p in matrix.items()], key=lambda x: x["Probabilité"], reverse=True)[:n]

def analyze_match(match, rapid_key, serp_key="", use_web=True, home_odds=None, draw_odds=None, away_odds=None):
    home = match["homeTeam"]
    away = match["awayTeam"]
    h_id, a_id = home["id"], away["id"]
    h_name, a_name = home["name"], away["name"]
    comp = match["competition"]

    h_stats = summarize_history_rapid(rapid_key, h_id)
    a_stats = summarize_history_rapid(rapid_key, a_id)

    h_table = standing_row_rapid(rapid_key, comp["id"], h_id)
    a_table = standing_row_rapid(rapid_key, comp["id"], a_id)

    hxg, axg = expected_goals(h_stats, a_stats, home_odds, away_odds)
    matrix = goal_matrix(hxg, axg)
    markets = market_probs(matrix)

    web = web_research(h_name, a_name, serp_key) if (use_web and serp_key) else {}
    absences = extract_absence_evidence(web)

    quality = (sum([1 for s in [h_stats, a_stats] if s["n"] >= 5]) + (2 if h_table else 0)) / 4.0
    best = max(markets.items(), key=lambda x: x[1])

    return {
        "match": f"{h_name} — {a_name}",
        "competition": comp["name"],
        "venue": match.get("venue"),
        "expected_goals": {h_name: round(hxg, 3), a_name: round(axg, 3)},
        "form": {h_name: h_stats["form"], a_name: a_stats["form"]},
        "history": {h_name: h_stats, a_name: a_stats},
        "markets": {k: pct(v) for k, v in markets.items()},
        "exact_scores": exact_scores(matrix, 10),
        "best_market": {"market": best[0], "probability": pct(best[1])},
        "data_quality": pct(quality),
        "confidence": "FORTE CONVERGENCE" if quality >= 0.7 else "MATCH INCERTAIN",
        "absence_evidence": absences,
        "standings": {h_name: h_table, a_name: a_table},
    }

# ============================================================
# INTERFACE STREAMLIT
# ============================================================

st.title("⚽ RODRIGUE PRO FOOTBALL AI — RAPIDAPI V3")
st.caption("Moteur pro multi-compétitions via API-Football (RapidAPI)")

with st.sidebar:
    st.header("🔐 API & PARAMÈTRES")
    rapid_key = st.text_input("RapidAPI Key (API-Football)", type="password")
    serp_key = st.text_input("SerpApi Key (optionnel)", type="password")
    st.divider()
    date_value = st.date_input("📅 Date des matchs", datetime.now().date())
    selected_names = st.multiselect("🏆 Compétitions", list(LEAGUES.keys()), default=["Premier League", "LaLiga", "Serie A", "Ligue 1"])
    use_web = st.checkbox("🌐 Recherche Web absences", value=False)
    load = st.button("🔎 CHARGER LES MATCHS", use_container_width=True, type="primary")

if load:
    if not rapid_key:
        st.error("Entre ta clé RapidAPI.")
    elif not selected_names:
        st.error("Sélectionne au moins une compétition.")
    else:
        try:
            with st.spinner("Chargement des matchs depuis API-Football..."):
                raw = get_matches_rapid(rapid_key, date_value.strftime("%Y-%m-%d"))
                selected_ids = [LEAGUES[n] for n in selected_names]
                matches = [format_match_from_rapid(m) for m in raw if m.get("league", {}).get("id") in selected_ids]

            st.session_state.matches = matches
            st.session_state.loaded_date = str(date_value)
            st.session_state.analysis = None

            if matches:
                st.success(f"{len(matches)} match(s) trouvé(s).")
            else:
                st.warning("Aucun match trouvé pour cette date dans les compétitions sélectionnées.")
        except Exception as e:
            st.error(f"Erreur : {e}")

matches = st.session_state.matches
if matches:
    labels = [f"{m['homeTeam']['name']} vs {m['awayTeam']['name']} — {m['competition']['name']}" for m in matches]
    selected_label = st.selectbox("⚽ Choisir le match", labels)
    selected_match = matches[labels.index(selected_label)]

    if st.button("🧠 ANALYSER LE MATCH", use_container_width=True, type="primary"):
        try:
            with st.spinner("Analyse en cours..."):
                st.session_state.analysis = analyze_match(selected_match, rapid_key, serp_key, use_web)
        except Exception as e:
            st.error(f"Erreur d'analyse : {e}")

report = st.session_state.analysis
if report:
    st.divider()
    st.header(f"🎯 {report['match']}")
    st.write(f"**Compétition :** {report['competition']} | **Stade :** {report['venue'] or 'N/D'}")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Qualité données", f"{report['data_quality']} %")
    c2.metric("Convergence", report["confidence"])
    c3.metric("xG Domicile", list(report['expected_goals'].values())[0])
    c4.metric("xG Extérieur", list(report['expected_goals'].values())[1])

    st.success(f"Meilleur choix statistique : **{report['best_market']['market']}** ({report['best_market']['probability']} %)")

    st.subheader("🎯 1X2 / Double chance")
    st.dataframe(pd.DataFrame([{"Marché": k, "Probabilité": v} for k, v in report["markets"].items() if k in ["1", "X", "2", "1X", "X2", "12"]]), use_container_width=True, hide_index=True)

    st.subheader("🎯 Scores exacts (Top 10)")
    st.dataframe(pd.DataFrame(report["exact_scores"]), use_container_width=True, hide_index=True)
