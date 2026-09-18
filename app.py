# -*- coding: utf-8 -*-
"""
RODRIGUE PRO FOOTBALL AI — V3 DYNAMIC
=====================================

Application Streamlit d'analyse football multi-facteurs.

Sources principales :
- football-data.org v4 : matchs, historique, classement, buteurs
- SerpApi/Google (optionnel) : absences, suspensions, compositions,
  actualités et contexte du match

IMPORTANT :
Les probabilités sont des estimations statistiques. Aucune application
ne peut garantir 90 %, 99 % ou 100 % de réussite sur des matchs réels.

Installation :
    pip install -r requirements.txt

Lancement :
    streamlit run app.py

Les clés API peuvent être saisies directement dans la barre latérale.
"""

import os
import re
import math
import json
from datetime import datetime
from typing import Dict, List, Optional

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

FD_BASE = "https://api.football-data.org/v4"
SERP_URL = "https://serpapi.com/search.json"
TIMEOUT = 20
MAX_GOALS = 8
HISTORY_LIMIT = 15

COMPETITIONS = {
    "Premier League": "PL",
    "LaLiga": "PD",
    "Bundesliga": "BL1",
    "Serie A": "SA",
    "Ligue 1": "FL1",
    "Eredivisie": "DED",
    "Primeira Liga": "PPL",
    "Championship": "ELC",
    "Brasileirão": "BSA",
    "Champions League": "CL",
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


def normalize_name(s):
    s = (s or "").lower()
    s = re.sub(r"[^a-z0-9àâçéèêëîïôûùüÿñ -]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


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
        text = response.text[:400]
        raise RuntimeError(f"API HTTP {response.status_code}: {text}")

    return response.json()


# ============================================================
# FOOTBALL-DATA.ORG
# ============================================================

def fd_headers(api_key):
    if not api_key:
        raise RuntimeError("Clé football-data.org manquante.")
    return {"X-Auth-Token": api_key}


@st.cache_data(ttl=300, show_spinner=False)
def get_matches(api_key, date_str):
    # Récupération globale par date pour contourner les restrictions de filtres d'API
    params = {
        "dateFrom": date_str,
        "dateTo": date_str,
    }

    data = api_get(
        f"{FD_BASE}/matches",
        fd_headers(api_key),
        params,
    )
    return data.get("matches", [])


@st.cache_data(ttl=900, show_spinner=False)
def get_team_history(api_key, team_id, limit=HISTORY_LIMIT):
    data = api_get(
        f"{FD_BASE}/teams/{team_id}/matches",
        fd_headers(api_key),
        {
            "status": "FINISHED",
            "limit": limit,
        },
    )
    return data.get("matches", [])


@st.cache_data(ttl=1800, show_spinner=False)
def get_standings(api_key, competition_code):
    if not competition_code:
        return []

    data = api_get(
        f"{FD_BASE}/competitions/{competition_code}/standings",
        fd_headers(api_key),
    )

    for table in data.get("standings", []):
        if table.get("type") == "TOTAL":
            return table.get("table", [])

    tables = data.get("standings", [])
    return tables[0].get("table", []) if tables else []


@st.cache_data(ttl=1800, show_spinner=False)
def get_scorers(api_key, competition_code, limit=20):
    if not competition_code:
        return []

    data = api_get(
        f"{FD_BASE}/competitions/{competition_code}/scorers",
        fd_headers(api_key),
        {"limit": limit},
    )
    return data.get("scorers", [])


def score_from_match(match):
    score = match.get("score", {})
    full = score.get("fullTime", {})
    half = score.get("halfTime", {})

    return {
        "home": full.get("home"),
        "away": full.get("away"),
        "ht_home": half.get("home"),
        "ht_away": half.get("away"),
    }


def team_match_row(match, team_id):
    home_id = match.get("homeTeam", {}).get("id")
    away_id = match.get("awayTeam", {}).get("id")

    s = score_from_match(match)

    if s["home"] is None or s["away"] is None:
        return None

    if home_id == team_id:
        gf, ga = s["home"], s["away"]
        ht_gf, ht_ga = s["ht_home"], s["ht_away"]
        venue = "HOME"
        opponent = match.get("awayTeam", {}).get("name", "?")
    elif away_id == team_id:
        gf, ga = s["away"], s["home"]
        ht_gf, ht_ga = s["ht_away"], s["ht_home"]
        venue = "AWAY"
        opponent = match.get("homeTeam", {}).get("name", "?")
    else:
        return None

    return {
        "date": match.get("utcDate", ""),
        "gf": int(gf),
        "ga": int(ga),
        "venue": venue,
        "result": "W" if gf > ga else "D" if gf == ga else "L",
        "ht_gf": ht_gf,
        "ht_ga": ht_ga,
        "opponent": opponent,
        "competition": match.get("competition", {}).get("name", ""),
    }


def summarize_history(api_key, team_id):
    matches = get_team_history(api_key, team_id, HISTORY_LIMIT)

    rows = [
        team_match_row(m, team_id)
        for m in matches
    ]
    rows = [r for r in rows if r]

    if not rows:
        return {
            "n": 0,
            "gf": None,
            "ga": None,
            "home_gf": None,
            "home_ga": None,
            "away_gf": None,
            "away_ga": None,
            "ht_gf": None,
            "ht_ga": None,
            "form": "",
            "btts": None,
            "over15": None,
            "over25": None,
            "rows": [],
        }

    def avg(values):
        return float(np.mean(values)) if values else None

    home = [r for r in rows if r["venue"] == "HOME"]
    away = [r for r in rows if r["venue"] == "AWAY"]

    btts = np.mean([
        r["gf"] > 0 and r["ga"] > 0
        for r in rows
    ])

    over15 = np.mean([
        r["gf"] + r["ga"] > 1.5
        for r in rows
    ])

    over25 = np.mean([
        r["gf"] + r["ga"] > 2.5
        for r in rows
    ])

    return {
        "n": len(rows),
        "gf": avg([r["gf"] for r in rows]),
        "ga": avg([r["ga"] for r in rows]),
        "home_gf": avg([r["gf"] for r in home]),
        "home_ga": avg([r["ga"] for r in home]),
        "away_gf": avg([r["gf"] for r in away]),
        "away_ga": avg([r["ga"] for r in away]),
        "ht_gf": avg([
            r["ht_gf"] for r in rows
            if r["ht_gf"] is not None
        ]),
        "ht_ga": avg([
            r["ht_ga"] for r in rows
            if r["ht_ga"] is not None
        ]),
        "form": "".join(r["result"] for r in rows[:5]),
        "btts": float(btts),
        "over15": float(over15),
        "over25": float(over25),
        "rows": rows,
    }


def standing_row(api_key, competition_code, team_id):
    try:
        rows = get_standings(api_key, competition_code)
    except Exception:
        return None

    for row in rows:
        if row.get("team", {}).get("id") == team_id:
            return row

    return None


# ============================================================
# RECHERCHE WEB
# ============================================================

def serp_search(api_key, query, num=5):
    if not api_key:
        return []

    try:
        data = api_get(
            SERP_URL,
            params={
                "engine": "google",
                "q": query,
                "api_key": api_key,
                "hl": "fr",
                "gl": "cm",
                "num": num,
            },
        )
    except Exception:
        return []

    results = []

    for item in data.get("organic_results", []):
        results.append({
            "title": item.get("title", ""),
            "snippet": item.get("snippet", ""),
            "link": item.get("link", ""),
        })

    return results


def web_research(home, away, serp_key):
    queries = [
        f'"{home}" blessures absences suspensions composition probable',
        f'"{away}" blessures absences suspensions composition probable',
        f'"{home}" "{away}" preview statistiques',
        f'"{home}" "{away}" lineups injuries',
        f'"{home}" "{away}" dernières nouvelles',
        f'"{home}" stade domicile',
    ]

    all_results = {}

    for query in queries:
        all_results[query] = serp_search(
            serp_key,
            query,
            num=5,
        )

    return all_results


INJURY_WORDS = [
    "blessé",
    "blessure",
    "injury",
    "injured",
    "suspendu",
    "suspension",
    "suspended",
    "absent",
    "out",
]


def extract_absence_evidence(search_results):
    evidence = []

    for query, items in search_results.items():
        for item in items:
            text = (
                f"{item.get('title', '')} "
                f"{item.get('snippet', '')}"
            )
            low = text.lower()

            if any(word in low for word in INJURY_WORDS):
                evidence.append({
                    "query": query,
                    "title": item.get("title", ""),
                    "snippet": item.get("snippet", ""),
                    "link": item.get("link", ""),
                })

    return evidence


# ============================================================
# MODELE
# ============================================================

def strength_from_standings(home_table, away_table):
    if not home_table or not away_table:
        return 0.0

    hp = safe_float(home_table.get("points"))
    ap = safe_float(away_table.get("points"))

    hg = safe_float(home_table.get("goalsFor"))
    hc = safe_float(home_table.get("goalsAgainst"))

    ag = safe_float(away_table.get("goalsFor"))
    ac = safe_float(away_table.get("goalsAgainst"))

    point_signal = clamp(
        (hp - ap) / 100.0,
        -0.25,
        0.25,
    )

    goal_signal = clamp(
        ((hg - hc) - (ag - ac)) / 100.0,
        -0.20,
        0.20,
    )

    return point_signal + goal_signal


def expected_goals(
    home_stats,
    away_stats,
    standings_signal=0.0,
    home_odds=None,
    away_odds=None,
):
    league_goal_base = 1.35

    h_attack = (
        home_stats["home_gf"]
        or home_stats["gf"]
        or league_goal_base
    )

    h_def = (
        home_stats["home_ga"]
        or home_stats["ga"]
        or league_goal_base
    )

    a_attack = (
        away_stats["away_gf"]
        or away_stats["gf"]
        or league_goal_base
    )

    a_def = (
        away_stats["away_ga"]
        or away_stats["ga"]
        or league_goal_base
    )

    hxg = (
        0.50 * h_attack
        + 0.30 * a_def
        + 0.20 * league_goal_base
    )

    axg = (
        0.50 * a_attack
        + 0.30 * h_def
        + 0.20 * league_goal_base
    )

    # Avantage domicile modéré.
    hxg *= 1.05
    axg *= 0.96

    # Signal du classement limité.
    hxg *= 1.0 + clamp(standings_signal, -0.08, 0.08)
    axg *= 1.0 - clamp(standings_signal, -0.05, 0.05)

    # Les cotes servent uniquement de petit signal de marché,
    # jamais comme preuve qu'un résultat est garanti.
    if home_odds and away_odds:
        try:
            inv_h = 1 / home_odds
            inv_a = 1 / away_odds
            total = inv_h + inv_a
            market_h = inv_h / total
            market_a = inv_a / total

            hxg *= 1 + clamp((market_h - 0.50) * 0.12, -0.06, 0.06)
            axg *= 1 + clamp((market_a - 0.50) * 0.10, -0.05, 0.05)
        except Exception:
            pass

    return (
        clamp(hxg, 0.10, 4.50),
        clamp(axg, 0.10, 4.50),
    )


def goal_matrix(hxg, axg):
    matrix = {}

    for h in range(MAX_GOALS + 1):
        for a in range(MAX_GOALS + 1):
            matrix[(h, a)] = (
                poisson(h, hxg)
                * poisson(a, axg)
            )

    total = sum(matrix.values())

    if total:
        matrix = {
            k: v / total
            for k, v in matrix.items()
        }

    return matrix


# ============================================================
# MARCHES
# ============================================================

def market_probs(matrix):
    out = {
        "1": 0.0,
        "X": 0.0,
        "2": 0.0,
        "1X": 0.0,
        "X2": 0.0,
        "12": 0.0,
        "BTTS Oui": 0.0,
        "BTTS Non": 0.0,
    }

    for line in [0.5, 1.5, 2.5, 3.5]:
        out[f"O{line}"] = 0.0

    for h, a in matrix:
        p = matrix[(h, a)]

        if h > a:
            out["1"] += p
        elif h == a:
            out["X"] += p
        else:
            out["2"] += p

        total_goals = h + a

        for line in [0.5, 1.5, 2.5, 3.5]:
            if total_goals > line:
                out[f"O{line}"] += p

        if h > 0 and a > 0:
            out["BTTS Oui"] += p

    out["1X"] = out["1"] + out["X"]
    out["X2"] = out["X"] + out["2"]
    out["12"] = out["1"] + out["2"]
    out["BTTS Non"] = 1 - out["BTTS Oui"]

    for line in [0.5, 1.5, 2.5, 3.5]:
        out[f"U{line}"] = 1 - out[f"O{line}"]

    return out


def exact_scores(matrix, n=10):
    rows = []

    for (h, a), probability in matrix.items():
        rows.append({
            "Score": f"{h}-{a}",
            "Probabilité": pct(probability),
        })

    return sorted(
        rows,
        key=lambda x: x["Probabilité"],
        reverse=True,
    )[:n]


def half_time_matrix(hxg, axg):
    # Approximation prudente : ~44 % des buts attendus avant la pause.
    return goal_matrix(
        hxg * 0.44,
        axg * 0.44,
    )


def ht_ft(ht_matrix, full_matrix):
    ht_probs = {"1": 0.0, "X": 0.0, "2": 0.0}
    ft_probs = {"1": 0.0, "X": 0.0, "2": 0.0}

    for (h, a), p in ht_matrix.items():
        result = "1" if h > a else "X" if h == a else "2"
        ht_probs[result] += p

    for (h, a), p in full_matrix.items():
        result = "1" if h > a else "X" if h == a else "2"
        ft_probs[result] += p

    rows = []

    for ht_result, hp in ht_probs.items():
        for ft_result, fp in ft_probs.items():
            dependency = 1.0

            if ht_result == ft_result:
                dependency = 1.25
            elif ht_result == "X" and ft_result != "X":
                dependency = 1.10

            rows.append({
                "HT/FT": f"{ht_result}/{ft_result}",
                "Probabilité brute": hp * fp * dependency,
            })

    total = sum(row["Probabilité brute"] for row in rows)

    for row in rows:
        row["Probabilité"] = pct(
            row["Probabilité brute"] / total
            if total else 0
        )

    return sorted(
        rows,
        key=lambda x: x["Probabilité"],
        reverse=True,
    )


# ============================================================
# QUALITE / CONFIANCE
# ============================================================

def data_quality(
    home_stats,
    away_stats,
    home_table,
    away_table,
):
    score = 0
    maximum = 6

    if home_stats["n"] >= 5:
        score += 1

    if away_stats["n"] >= 5:
        score += 1

    if home_stats["home_gf"] is not None:
        score += 1

    if away_stats["away_gf"] is not None:
        score += 1

    if home_table:
        score += 1

    if away_table:
        score += 1

    return score / maximum


def confidence_label(markets, quality):
    top = max(
        markets["1"],
        markets["X"],
        markets["2"],
    )

    if quality < 0.50:
        return "DONNÉES INSUFFISANTES"

    if top >= 0.65 and quality >= 0.80:
        return "FORTE CONVERGENCE"

    if top >= 0.52 and quality >= 0.65:
        return "CONVERGENCE MOYENNE"

    return "MATCH OUVERT / INCERTAIN"


def best_market(markets):
    candidates = {
        "1": markets["1"],
        "X": markets["X"],
        "2": markets["2"],
        "1X": markets["1X"],
        "X2": markets["X2"],
        "12": markets["12"],
        "BTTS Oui": markets["BTTS Oui"],
        "BTTS Non": markets["BTTS Non"],
        "O1.5": markets["O1.5"],
        "U1.5": markets["U1.5"],
        "O2.5": markets["O2.5"],
        "U2.5": markets["U2.5"],
        "O3.5": markets["O3.5"],
        "U3.5": markets["U3.5"],
    }

    return max(
        candidates.items(),
        key=lambda item: item[1],
    )


# ============================================================
# ANALYSE COMPLETE
# ============================================================

def analyze_match(
    match,
    football_key,
    serp_key="",
    use_web=True,
    home_odds=None,
    draw_odds=None,
    away_odds=None,
):
    home = match.get("homeTeam", {})
    away = match.get("awayTeam", {})

    home_id = home.get("id")
    away_id = away.get("id")

    if not home_id or not away_id:
        raise ValueError(
            "Identifiants des équipes indisponibles."
        )

    home_name = home.get("name", "Domicile")
    away_name = away.get("name", "Extérieur")
    competition = match.get("competition", {})
    comp_code = competition.get("code", "")

    home_stats = summarize_history(
        football_key,
        home_id,
    )

    away_stats = summarize_history(
        football_key,
        away_id,
    )

    home_table = standing_row(
        football_key,
        comp_code,
        home_id,
    )

    away_table = standing_row(
        football_key,
        comp_code,
        away_id,
    )

    standings_signal = strength_from_standings(
        home_table,
        away_table,
    )

    hxg, axg = expected_goals(
        home_stats,
        away_stats,
        standings_signal,
        home_odds,
        away_odds,
    )

    full_matrix = goal_matrix(hxg, axg)
    ht_matrix = half_time_matrix(hxg, axg)

    markets = market_probs(full_matrix)
    ht_markets = market_probs(ht_matrix)

    if use_web and serp_key:
        web = web_research(
            home_name,
            away_name,
            serp_key,
        )
    else:
        web = {}

    absence_evidence = extract_absence_evidence(web)

    quality = data_quality(
        home_stats,
        away_stats,
        home_table,
        away_table,
    )

    best = best_market(markets)

    return {
        "match": f"{home_name} — {away_name}",
        "home": home_name,
        "away": away_name,
        "date": match.get("utcDate"),
        "competition": competition.get("name"),
        "venue": match.get("venue"),
        "expected_goals": {
            home_name: round(hxg, 3),
            away_name: round(axg, 3),
        },
        "form": {
            home_name: home_stats["form"],
            away_name: away_stats["form"],
        },
        "history": {
            home_name: home_stats,
            away_name: away_stats,
        },
        "markets": {
            key: pct(value)
            for key, value in markets.items()
        },
        "half_time_markets": {
            key: pct(value)
            for key, value in ht_markets.items()
        },
        "exact_scores": exact_scores(full_matrix, 10),
        "ht_ft": ht_ft(
            ht_matrix,
            full_matrix,
        ),
        "best_market": {
            "market": best[0],
            "probability": pct(best[1]),
        },
        "data_quality": pct(quality),
        "confidence": confidence_label(
            markets,
            quality,
        ),
        "absence_evidence": absence_evidence,
        "web_sources": web,
        "standings": {
            home_name: home_table,
            away_name: away_table,
        },
        "odds": {
            "1": home_odds,
            "X": draw_odds,
            "2": away_odds,
        },
    }


# ============================================================
# INTERFACE
# ============================================================

st.title("⚽ RODRIGUE PRO FOOTBALL AI — V3 DYNAMIC")
st.caption(
    "Forme • domicile/extérieur • classement • buts • Poisson • "
    "cotes • absences • recherche Web • HT/FT • scores exacts"
)

with st.sidebar:
    st.header("🔐 API & PARAMÈTRES")

    football_key = st.text_input(
        "Football-data.org API Key",
        value=os.getenv("FOOTBALL_DATA_KEY", ""),
        type="password",
    )

    serp_key = st.text_input(
        "SerpApi Key (optionnel)",
        value=os.getenv("SERPAPI_KEY", ""),
        type="password",
    )

    st.divider()

    date_value = st.date_input(
        "📅 Date des matchs",
        datetime.now().date(),
    )

    selected_names = st.multiselect(
        "🏆 Compétitions",
        list(COMPETITIONS.keys()),
        default=[
            "Premier League",
            "LaLiga",
            "Bundesliga",
            "Serie A",
            "Ligue 1",
        ],
    )

    use_web = st.checkbox(
        "🌐 Recherche Web absences",
        value=bool(serp_key),
        disabled=not bool(serp_key),
    )

    st.divider()
    st.subheader("💰 Cotes optionnelles")

    home_odds = st.number_input(
        "Cote 1",
        min_value=1.01,
        value=2.00,
        step=0.01,
    )

    draw_odds = st.number_input(
        "Cote X",
        min_value=1.01,
        value=3.20,
        step=0.01,
    )

    away_odds = st.number_input(
        "Cote 2",
        min_value=1.01,
        value=3.20,
        step=0.01,
    )

    load = st.button(
        "🔎 CHARGER LES MATCHS",
        use_container_width=True,
        type="primary",
    )


# ============================================================
# CHARGEMENT
# ============================================================

if load:
    if not football_key:
        st.error(
            "Entre d'abord ta clé Football-data.org."
        )
    elif not selected_names:
        st.error(
            "Sélectionne au moins une compétition."
        )
    else:
        try:
            with st.spinner(
                "Chargement des matchs..."
            ):
                # Récupération de tous les matchs de la date
                raw_matches = get_matches(
                    football_key,
                    date_value.strftime("%Y-%m-%d"),
                )

            # Filtrage local en Python selon les compétitions cochées
            codes = [
                COMPETITIONS[name]
                for name in selected_names
            ]
            matches = [
                m for m in raw_matches
                if m.get("competition", {}).get("code") in codes
            ]

            st.session_state.matches = matches
            st.session_state.loaded_date = str(
                date_value
            )
            st.session_state.analysis = None

            if matches:
                st.success(
                    f"{len(matches)} match(s) trouvé(s)."
                )
            else:
                st.warning(
                    "Aucun match trouvé pour cette date "
                    "dans les compétitions sélectionnées."
                )

        except Exception as exc:
            st.error(
                f"Erreur de chargement : {exc}"
            )


# ============================================================
# SELECTION / ANALYSE
# ============================================================

matches = st.session_state.matches

if matches:
    labels = []

    for i, match in enumerate(matches):
        home = match.get(
            "homeTeam", {}
        ).get("name", "?")

        away = match.get(
            "awayTeam", {}
        ).get("name", "?")

        comp = match.get(
            "competition", {}
        ).get("name", "")

        labels.append(
            f"{i + 1}. {home} vs {away} — {comp}"
        )

    selected_label = st.selectbox(
        "⚽ Choisir le match",
        labels,
    )

    index = labels.index(
        selected_label
    )

    selected_match = matches[index]

    if st.button(
        "🧠 ANALYSER LE MATCH",
        use_container_width=True,
        type="primary",
    ):
        try:
            with st.spinner(
                "Analyse dynamique : historique, "
                "classement, Poisson et recherche Web..."
            ):
                report = analyze_match(
                    selected_match,
                    football_key,
                    serp_key,
                    use_web,
                    home_odds,
                    draw_odds,
                    away_odds,
                )

            st.session_state.analysis = report

        except Exception as exc:
            st.error(
                f"Erreur pendant l'analyse : {exc}"
            )


# ============================================================
# AFFICHAGE
# ============================================================

report = st.session_state.analysis

if report:
    st.divider()

    st.header(
        f"🎯 {report['match']}"
    )

    st.write(
        f"**Compétition :** {report['competition']}  |  "
        f"**Stade :** {report['venue'] or 'non fourni'}"
    )

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Qualité données",
        f"{report['data_quality']} %",
    )

    c2.metric(
        "Convergence",
        report["confidence"],
    )

    c3.metric(
        "xG domicile",
        f"{list(report['expected_goals'].values())[0]:.2f}",
    )

    c4.metric(
        "xG extérieur",
        f"{list(report['expected_goals'].values())[1]:.2f}",
    )

    st.success(
        f"Marché statistiquement le plus probable dans le modèle : "
        f"{report['best_market']['market']} "
        f"({report['best_market']['probability']} %)"
    )

    # --------------------------------------------------------
    # 1X2
    # --------------------------------------------------------

    st.subheader("🎯 1X2 / Double chance")

    keys = ["1", "X", "2", "1X", "X2", "12"]

    df = pd.DataFrame([
        {
            "Marché": key,
            "Probabilité": report["markets"][key],
        }
        for key in keys
    ])

    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
    )

    # --------------------------------------------------------
    # BUTS
    # --------------------------------------------------------

    st.subheader("⚽ Buts / BTTS")

    goal_keys = [
        "O0.5", "U0.5",
        "O1.5", "U1.5",
        "O2.5", "U2.5",
        "O3.5", "U3.5",
        "BTTS Oui", "BTTS Non",
    ]

    df_goals = pd.DataFrame([
        {
            "Marché": key,
            "Probabilité": report["markets"][key],
        }
        for key in goal_keys
    ])

    st.dataframe(
        df_goals,
        use_container_width=True,
        hide_index=True,
    )

    # --------------------------------------------------------
    # HT
    # --------------------------------------------------------

    st.subheader("🕐 Résultat mi-temps")

    df_ht = pd.DataFrame([
        {
            "Résultat HT": key,
            "Probabilité": report["half_time_markets"][key],
        }
        for key in ["1", "X", "2"]
    ])

    st.dataframe(
        df_ht,
        use_container_width=True,
        hide_index=True,
    )

    # --------------------------------------------------------
    # HT/FT
    # --------------------------------------------------------

    st.subheader("🔥 HT / FT")

    df_htft = pd.DataFrame(
        report["ht_ft"][:9]
    )

    st.dataframe(
        df_htft,
        use_container_width=True,
        hide_index=True,
    )

    # --------------------------------------------------------
    # SCORES
    # --------------------------------------------------------

    st.subheader("🎯 Scores exacts — top 10")

    df_scores = pd.DataFrame(
        report["exact_scores"]
    )

    st.dataframe(
        df_scores,
        use_container_width=True,
        hide_index=True,
    )

    # --------------------------------------------------------
    # FORME
    # --------------------------------------------------------

    st.subheader("📈 Forme récente")

    form_rows = []

    for team, form in report["form"].items():
        stats = report["history"][team]

        form_rows.append({
            "Équipe": team,
            "5 derniers": form,
            "Matchs analysés": stats["n"],
            "Buts/match": round(
                stats["gf"], 2
            ) if stats["gf"] is not None else "N/D",
            "Buts encaissés/match": round(
                stats["ga"], 2
            ) if stats["ga"] is not None else "N/D",
            "BTTS": pct(stats["btts"])
            if stats["btts"] is not None else "N/D",
            "Over 1.5": pct(stats["over15"])
            if stats["over15"] is not None else "N/D",
            "Over 2.5": pct(stats["over25"])
            if stats["over25"] is not None else "N/D",
        })

    st.dataframe(
        pd.DataFrame(form_rows),
        use_container_width=True,
        hide_index=True,
    )

    # --------------------------------------------------------
    # CLASSEMENT
    # --------------------------------------------------------

    st.subheader("🏆 Classement")

    standing_rows = []

    for team, row in report["standings"].items():
        if row:
            standing_rows.append({
                "Équipe": team,
                "Position": row.get("position"),
                "Points": row.get("points"),
                "MJ": row.get("playedGames"),
                "Buts pour": row.get("goalsFor"),
                "Buts contre": row.get("goalsAgainst"),
                "Différence": row.get("goalDifference"),
            })

    if standing_rows:
        st.dataframe(
            pd.DataFrame(standing_rows),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info(
            "Classement indisponible pour cette compétition."
        )

    # --------------------------------------------------------
    # ABSENCES
    # --------------------------------------------------------

    st.subheader(
        "🏥 Absences / informations Web"
    )

    if report["absence_evidence"]:
        for item in report["absence_evidence"][:15]:
            st.markdown(
                f"**{item['title']}**\n\n"
                f"{item['snippet']}\n\n"
                f"{item['link']}"
            )
    else:
        st.info(
            "Aucune preuve Web d'absence détectée. "
            "Cela ne prouve pas qu'il n'y a aucune absence."
        )

    # --------------------------------------------------------
    # AVERTISSEMENT
    # --------------------------------------------------------

    st.warning(
        "⚠️ Le modèle ne connaît pas l'avenir. Les compositions "
        "officielles, blessures de dernière minute, cartons, météo, "
        "arbitrage et événements du match peuvent modifier les probabilités. "
        "Les informations Web doivent être vérifiées auprès de sources fiables."
    )

    with st.expander("📦 Voir le rapport JSON complet"):
        st.json(report)


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    "RODRIGUE PRO FOOTBALL AI V3 — modèle probabiliste dynamique. "
    "Aucune probabilité n'est une garantie de gain."
)
