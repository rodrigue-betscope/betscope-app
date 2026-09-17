# -*- coding: utf-8 -*-
"""
RODRIGUE PRO FOOTBALL AI — V2 ULTIMATE + BLUE SCORE
===================================================

Objectif:
    Analyse multi-facteurs de matchs de football à partir de données réelles 
    ou en mode manuel pour les matchs virtuels / eSports.
"""

import os
import re
import math
import json
from datetime import datetime, timedelta
from collections import Counter
from typing import Dict, List, Tuple, Optional

import requests
import numpy as np
import pandas as pd
import streamlit as st


# ============================================================
# CONFIGURATION
# ============================================================

FD_BASE = "https://api.football-data.org/v4"
SERP_URL = "https://serpapi.com/search.json"
TIMEOUT = 20
MAX_GOALS = 7
HISTORY_LIMIT = 15

FOOTBALL_DATA_KEY = os.getenv("FOOTBALL_DATA_KEY", "")
SERPAPI_KEY = os.getenv("SERPAPI_KEY", "")

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
    "Europa League": "EL",
    "Conference League": "UECL",
}


# ============================================================
# OUTILS
# ============================================================

def safe_float(x, default=0.0):
    try:
        return float(x)
    except Exception:
        return default


def clamp(x, lo, hi):
    return max(lo, min(hi, x))


def pct(x):
    return round(100 * float(x), 2)


def poisson(k, lam):
    if lam <= 0:
        return 1.0 if k == 0 else 0.0
    return math.exp(-lam) * (lam ** k) / math.factorial(k)


def normalize_name(s):
    s = (s or "").lower()
    s = re.sub(r"[^a-z0-9àâçéèêëîïôûùüÿñ -]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def api_get(url, headers=None, params=None):
    r = requests.get(url, headers=headers or {}, params=params or {}, timeout=TIMEOUT)
    if r.status_code == 429:
        raise RuntimeError("Limite API atteinte (429). Attends avant de relancer.")
    if r.status_code >= 400:
        raise RuntimeError(f"API HTTP {r.status_code}: {r.text[:300]}")
    return r.json()


# ============================================================
# FOOTBALL-DATA.ORG
# ============================================================

def fd_headers():
    if not FOOTBALL_DATA_KEY:
        raise RuntimeError(
            "FOOTBALL_DATA_KEY manquante. Configure-la dans les variables "
            "d'environnement avant de lancer l'application."
        )
    return {"X-Auth-Token": FOOTBALL_DATA_KEY}


@st.cache_data(ttl=300, show_spinner=False)
def get_matches(date_str, competition_codes):
    params = {"dateFrom": date_str, "dateTo": date_str}
    if competition_codes:
        params["competitions"] = ",".join(competition_codes)

    data = api_get(f"{FD_BASE}/matches", fd_headers(), params)
    return data.get("matches", [])


@st.cache_data(ttl=900, show_spinner=False)
def get_team_history(team_id, limit=HISTORY_LIMIT):
    data = api_get(
        f"{FD_BASE}/teams/{team_id}/matches",
        fd_headers(),
        {"status": "FINISHED", "limit": limit},
    )
    return data.get("matches", [])


@st.cache_data(ttl=1800, show_spinner=False)
def get_standings(code):
    data = api_get(f"{FD_BASE}/competitions/{code}/standings", fd_headers())
    for table in data.get("standings", []):
        if table.get("type") == "TOTAL":
            return table.get("table", [])
    tables = data.get("standings", [])
    return tables[0].get("table", []) if tables else []


def score_from_match(match):
    s = match.get("score", {})
    ft = s.get("fullTime", {})
    ht = s.get("halfTime", {})
    return {
        "home": ft.get("home"),
        "away": ft.get("away"),
        "ht_home": ht.get("home"),
        "ht_away": ht.get("away"),
    }


def team_match_row(match, team_id):
    h_id = match.get("homeTeam", {}).get("id")
    a_id = match.get("awayTeam", {}).get("id")
    s = score_from_match(match)

    if s["home"] is None or s["away"] is None:
        return None

    if h_id == team_id:
        gf, ga, venue = s["home"], s["away"], "HOME"
        ht_gf, ht_ga = s["ht_home"], s["ht_away"]
    elif a_id == team_id:
        gf, ga, venue = s["away"], s["home"], "AWAY"
        ht_gf, ht_ga = s["ht_away"], s["ht_home"]
    else:
        return None

    return {
        "date": match.get("utcDate", ""),
        "gf": gf,
        "ga": ga,
        "venue": venue,
        "result": "W" if gf > ga else "D" if gf == ga else "L",
        "ht_gf": ht_gf,
        "ht_ga": ht_ga,
        "opponent": (
            match.get("awayTeam", {}).get("name")
            if venue == "HOME"
            else match.get("homeTeam", {}).get("name")
        ),
    }


def summarize_history(team_id):
    matches = get_team_history(team_id)
    rows = [team_match_row(m, team_id) for m in matches]
    rows = [r for r in rows if r]

    if not rows:
        return {
            "n": 0, "gf": None, "ga": None, "home_gf": None, "home_ga": None,
            "away_gf": None, "away_ga": None, "ht_gf": None, "ht_ga": None,
            "form": "", "btts": None, "over25": None
        }

    def avg(vals):
        return float(np.mean(vals)) if vals else None

    home = [r for r in rows if r["venue"] == "HOME"]
    away = [r for r in rows if r["venue"] == "AWAY"]

    btts = np.mean([r["gf"] > 0 and r["ga"] > 0 for r in rows])
    over25 = np.mean([(r["gf"] + r["ga"]) > 2.5 for r in rows])

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
        "over25": float(over25),
    }


def standing_row(competition_code, team_id):
    try:
        rows = get_standings(competition_code)
    except Exception:
        return None
    for row in rows:
        if row.get("team", {}).get("id") == team_id:
            return row
    return None


# ============================================================
# SERPAPI / RECHERCHE WEB
# ============================================================

def serp_search(query, num=5):
    if not SERPAPI_KEY:
        return []

    params = {
        "engine": "google",
        "q": query,
        "api_key": SERPAPI_KEY,
        "hl": "fr",
        "gl": "cm",
        "num": num,
    }

    try:
        data = api_get(SERP_URL, params=params)
    except Exception:
        return []

    return [
        {
            "title": x.get("title", ""),
            "snippet": x.get("snippet", ""),
            "link": x.get("link", ""),
        }
        for x in data.get("organic_results", [])
    ]


def web_research(home, away, venue=""):
    queries = [
        f'"{home}" blessures absences suspensions composition probable',
        f'"{away}" blessures absences suspensions composition probable',
        f'"{home}" "{away}" preview statistiques',
    ]
    result = {}
    for q in queries:
        result[q] = serp_search(q)
    return result


def extract_absence_evidence(search_results):
    injury_words = ["blessé", "blessure", "injury", "injured", "absent", "suspendu", "suspension", "suspended", "out"]
    evidence = []
    for query, items in search_results.items():
        for item in items:
            text = f"{item.get('title','')} {item.get('snippet','')}"
            low = text.lower()
            if any(word in low for word in injury_words):
                evidence.append({
                    "query": query,
                    "title": item.get("title"),
                    "snippet": item.get("snippet"),
                    "link": item.get("link"),
                })
    return evidence


# ============================================================
# MODÈLE DE PERFORMANCE & MATHS
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

    point_signal = clamp((hp - ap) / 100.0, -0.25, 0.25)
    goal_signal = clamp(((hg - hc) - (ag - ac)) / 100.0, -0.20, 0.20)

    return point_signal + goal_signal


def expected_goals(home_stats, away_stats, standings_signal=0.0):
    league = 1.35
    h_attack = home_stats["home_gf"] or home_stats["gf"] or league
    h_def = home_stats["home_ga"] or home_stats["ga"] or league
    a_attack = away_stats["away_gf"] or away_stats["gf"] or league
    a_def = away_stats["away_ga"] or away_stats["ga"] or league

    hxg = 0.55 * h_attack + 0.25 * a_def + 0.20 * league
    axg = 0.55 * a_attack + 0.25 * h_def + 0.20 * league

    hxg *= 1.05 + clamp(standings_signal, -0.08, 0.08)
    axg *= 0.96 - clamp(standings_signal, -0.05, 0.05)

    return clamp(hxg, 0.10, 4.50), clamp(axg, 0.10, 4.50)


def goal_matrix(hxg, axg):
    m = {}
    total = 0.0
    for h in range(MAX_GOALS + 1):
        for a in range(MAX_GOALS + 1):
            p = poisson(h, hxg) * poisson(a, axg)
            m[(h, a)] = p
            total += p
    if total:
        m = {k: v / total for k, v in m.items()}
    return m


def market_probs(m):
    out = {
        "1": 0.0, "X": 0.0, "2": 0.0,
        "1X": 0.0, "X2": 0.0, "12": 0.0,
        "BTTS Oui": 0.0, "BTTS Non": 0.0,
        "O0.5": 0.0, "O1.5": 0.0, "O2.5": 0.0, "O3.5": 0.0,
    }

    for (h, a), p in m.items():
        if h > a:
            out["1"] += p
        elif h == a:
            out["X"] += p
        else:
            out["2"] += p

        total = h + a
        for line in [0.5, 1.5, 2.5, 3.5]:
            if total > line:
                out[f"O{line}"] += p

        if h > 0 and a > 0:
            out["BTTS Oui"] += p

    out["1X"] = out["1"] + out["X"]
    out["X2"] = out["X"] + out["2"]
    out["12"] = out["1"] + out["2"]
    out["BTTS Non"] = 1 - out["BTTS Oui"]

    return out


def exact_scores(m, n=10):
    rows = []
    for (h, a), p in m.items():
        rows.append({
            "Score": f"{h}-{a}",
            "Probabilité": pct(p)
        })
    return sorted(rows, key=lambda x: x["Probabilité"], reverse=True)[:n]


def data_quality(home_stats, away_stats, home_table, away_table):
    score = 0
    maximum = 6
    if home_stats["n"] >= 5: score += 1
    if away_stats["n"] >= 5: score += 1
    if home_stats["home_gf"] is not None: score += 1
    if away_stats["away_gf"] is not None: score += 1
    if home_table: score += 1
    if away_table: score += 1
    return score / maximum


def confidence_from_model(markets, quality):
    top = max(markets["1"], markets["X"], markets["2"])
    if quality < 0.50: return "Faible"
    if top >= 0.65 and quality >= 0.80: return "Élevée"
    if top >= 0.50: return "Moyenne"
    return "Faible"


def analyze_match(match, use_web=True):
    home = match.get("homeTeam", {})
    away = match.get("awayTeam", {})
    hid, aid = home.get("id"), away.get("id")

    if not hid or not aid:
        raise ValueError("Identifiants des équipes indisponibles.")

    home_name = home.get("name", "Domicile")
    away_name = away.get("name", "Extérieur")
    comp_code = match.get("competition", {}).get("code", "")

    hs = summarize_history(hid)
    aws = summarize_history(aid)

    htable = standing_row(comp_code, hid) if comp_code else None
    atable = standing_row(comp_code, aid) if comp_code else None

    standings_signal = strength_from_standings(htable, atable)
    hxg, axg = expected_goals(hs, aws, standings_signal)

    fm = goal_matrix(hxg, axg)
    markets = market_probs(fm)
    quality = data_quality(hs, aws, htable, atable)

    web = web_research(home_name, away_name) if use_web else {}
    absences = extract_absence_evidence(web)

    return {
        "match": f"{home_name} — {away_name}",
        "competition": match.get("competition", {}).get("name"),
        "venue": match.get("venue"),
        "expected_goals": {home_name: round(hxg, 3), away_name: round(axg, 3)},
        "markets": {k: pct(v) for k, v in markets.items()},
        "exact_scores": exact_scores(fm),
        "data_quality": pct(quality),
        "confidence": confidence_from_model(markets, quality),
        "absence_evidence": absences,
    }


# ============================================================
# INTERFACE STREAMLIT & DASHBOARD BLUE SCORE
# ============================================================

st.set_page_config(
    page_title="Rodrigue Pro Football AI V2",
    page_icon="⚽",
    layout="wide",
)

st.title("⚽ RODRIGUE PRO FOOTBALL AI — V2 ULTIMATE")
st.caption(
    "Analyse multi-facteurs : forme • domicile/extérieur • classement • "
    "buts • Poisson • absences • recherche web • scores exacts"
)

with st.sidebar:
    st.header("⚙️ Configuration")

    if FOOTBALL_DATA_KEY:
        st.success("Football-data.org : clé détectée")
    else:
        st.error("Football-data.org : clé absente")

    if SERPAPI_KEY:
        st.success("SerpApi : clé détectée")
    else:
        st.warning("SerpApi : clé absente — recherche Web désactivée")

    date_value = st.date_input("Date des matchs", datetime.now().date())

    selected_names = st.multiselect(
        "Compétitions",
        list(COMPETITIONS.keys()),
        default=[
            "Premier League",
            "LaLiga",
            "Bundesliga",
            "Serie A",
            "Ligue 1",
            "Europa League",
        ],
    )

    use_web = st.checkbox(
        "Recherche complémentaire Web",
        value=True,
        disabled=not bool(SERPAPI_KEY),
    )

    load = st.button("🔎 CHARGER LES MATCHS", use_container_width=True)

# Chargement des matchs depuis l'API
matches = []
if load:
    try:
        codes = [COMPETITIONS[x] for x in selected_names]
        matches = get_matches(
            date_value.strftime("%Y-%m-%d"),
            tuple(codes),
        )
    except Exception as e:
        st.error(f"Erreur API : {e}")

# Si aucun match n'est trouvé via l'API (ex: matchs virtuels / eSports / trêves), on propose le mode manuel
if not matches:
    st.info("💡 Aucun match réel trouvé via l'API pour cette date. Utilise le formulaire ci-dessous pour analyser tes matchs virtuels (ex: Ligue Europa eSports).")
    
    with st.form("manual_match_form"):
        st.subheader("⚙️ Saisie Manuelle (Match Virtuel / Autre)")
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            m_home = st.text_input("Équipe Domicile", "Beşiktaş")
            hxg_input = st.number_input("Buts attendus (xG) Domicile", min_value=0.1, max_value=5.0, value=1.65, step=0.05)
        with col_m2:
            m_away = st.text_input("Équipe Extérieur", "Olympique de Marseille")
            axg_input = st.number_input("Buts attendus (xG) Extérieur", min_value=0.1, max_value=5.0, value=1.25, step=0.05)
            
        submitted = st.form_submit_button("🚀 LANCER L'ANALYSE BLUE SCORE", use_container_width=True)
        
        if submitted:
            st.success("Analyse générée avec succès !")
            fm = goal_matrix(hxg_input, axg_input)
            mk = market_probs(fm)
            
            # Dashboard Blue Score Visuel
            st.markdown(
                f"""
                <div style="background: linear-gradient(135deg, #0b1d3a, #163b6d); padding: 20px; border-radius: 12px; color: white; text-align: center; box-shadow: 0 4px 15px rgba(0,0,0,0.3);">
                    <h2 style="margin: 0; font-family: sans-serif; letter-spacing: 2px; color: #00d2ff;">🔵 BLUE SCORE ANALYTICS</h2>
                    <p style="font-size: 14px; color: #cbd5e1; margin-top: 5px;">Modèle Prédictif Avancé — BetScope Pro</p>
                    <hr style="border: 0.5px solid rgba(255,255,255,0.2);">
                    <h3 style="margin: 10px 0;">{m_home} &nbsp;VS&nbsp; {m_away}</h3>
                    
                    <div style="display: flex; justify-content: space-around; background: rgba(0,0,0,0.2); padding: 12px; border-radius: 8px; margin-top: 15px;">
                        <div>
                            <span style="display: block; font-size: 12px; color: #94a3b8;">1 (DOM)</span>
                            <strong style="font-size: 18px; color: #4ade80;">{mk["1"] * 100:.2f}%</strong>
                        </div>
                        <div>
                            <span style="display: block; font-size: 12px; color: #94a3b8;">X (NUL)</span>
                            <strong style="font-size: 18px; color: #facc15;">{mk["X"] * 100:.2f}%</strong>
                        </div>
                        <div>
                            <span style="display: block; font-size: 12px; color: #94a3b8;">2 (EXT)</span>
                            <strong style="font-size: 18px; color: #f87171;">{mk["2"] * 100:.2f}%</strong>
                        </div>
                    </div>
                    
                    <div style="margin-top: 15px; background: rgba(15, 23, 42, 0.6); padding: 10px; border-radius: 8px;">
                        <span style="font-size: 14px; color: #38bdf8;">🔥 Indice BTTS (Les deux équipes marquent) : </span>
                        <strong style="font-size: 16px; color: #fff;">{mk["BTTS Oui"] * 100:.1f}%</strong>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )
            
            st.markdown("#### 🎯 Top Scores Recommandés (Blue Score)")
            top_scores = exact_scores(fm, n=3)
            col1, col2, col3 = st.columns(3)
            cols = [col1, col2, col3]
            for i, item in enumerate(top_scores):
                prob_val = item["Probabilité"]
                implied_odds = round(100 / prob_val, 2) if prob_val > 0 else 99.0
                with cols[i]:
                    st.markdown(
                        f"<div style='background: #1e293b; padding: 12px; border-radius: 8px; text-align: center; border: 1px solid #334155;'>"
                        f"<span style='color: #94a3b8; font-size: 12px;'>Option {i+1}</span><br>"
                        f"<strong style='font-size: 20px; color: #38bdf8;'>{item['Score']}</strong><br>"
                        f"<span style='color: #4ade80; font-size: 14px;'>Prob: {prob_val:.1f}%</span><br>"
                        f"<span style='color: #fbbf24; font-size: 12px;'>Côte est. : {implied_odds}</span>"
                        f"</div>",
                        unsafe_allow_html=True
                    )
else:
    st.success(f"{len(matches)} match(s) trouvé(s) via l'API.")
    labels = [
        f"{i+1}. {m.get('homeTeam', {}).get('name')} vs {m.get('awayTeam', {}).get('name')}"
        for i, m in enumerate(matches)
    ]
    selected_label = st.selectbox("Choisir le match", labels)
    idx = labels.index(selected_label)

    if st.button("🧠 ANALYSER LE MATCH", use_container_width=True):
        with st.spinner("Analyse statistique en cours..."):
            report = analyze_match(matches[idx], use_web=use_web)

        st.subheader(report["match"])
        st.write(
            f"**Compétition :** {report['competition']}  |  "
            f"**Stade :** {report['venue'] or 'non fourni'}"
        )

        c1, c2, c3 = st.columns(3)
        c1.metric("Qualité données", f"{report['data_quality']} %")
        c2.metric("Confiance", report["confidence"])
        
        h_name = list(report['expected_goals'].keys())[0]
        a_name = list(report['expected_goals'].keys())[1]
        c3.metric("xG Prédit", f"{report['expected_goals'][h_name]} - {report['expected_goals'][a_name]}")

        # Dashboard Blue Score avec les données de l'API
        hxg_val = report['expected_goals'][h_name]
        axg_val = report['expected_goals'][a_name]
        fm_api = goal_matrix(hxg_val, axg_val)
        mk_api = market_probs(fm_api)

        st.markdown(
            f"""
            <div style="background: linear-gradient(135deg, #0b1d3a, #163b6d); padding: 20px; border-radius: 12px; color: white; text-align: center; box-shadow: 0 4px 15px rgba(0,0,0,0.3); margin-top: 20px;">
                <h2 style="margin: 0; font-family: sans-serif; letter-spacing: 2px; color: #00d2ff;">🔵 BLUE SCORE ANALYTICS</h2>
                <p style="font-size: 14px; color: #cbd5e1; margin-top: 5px;">Modèle Prédictif Avancé — BetScope Pro</p>
                <hr style="border: 0.5px solid rgba(255,255,255,0.2);">
                <h3 style="margin: 10px 0;">{h_name} &nbsp;VS&nbsp; {a_name}</h3>
                
                <div style="display: flex; justify-content: space-around; background: rgba(0,0,0,0.2); padding: 12px; border-radius: 8px; margin-top: 15px;">
                    <div>
                        <span style="display: block; font-size: 12px; color: #94a3b8;">1 (DOM)</span>
                        <strong style="font-size: 18px; color: #4ade80;">{mk_api["1"] * 100:.2f}%</strong>
                    </div>
                    <div>
                        <span style="display: block; font-size: 12px; color: #94a3b8;">X (NUL)</span>
                        <strong style="font-size: 18px; color: #facc15;">{mk_api["X"] * 100:.2f}%</strong>
                    </div>
                    <div>
                        <span style="display: block; font-size: 12px; color: #94a3b8;">2 (EXT)</span>
                        <strong style="font-size: 18px; color: #f87171;">{mk_api["2"] * 100:.2f}%</strong>
                    </div>
                </div>
                
                <div style="margin-top: 15px; background: rgba(15, 23, 42, 0.6); padding: 10px; border-radius: 8px;">
                    <span style="font-size: 14px; color: #38bdf8;">🔥 Indice BTTS (Les deux équipes marquent) : </span>
                    <strong style="font-size: 16px; color: #fff;">{mk_api["BTTS Oui"] * 100:.1f}%</strong>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        st.markdown("#### 🎯 Top Scores Recommandés (Blue Score)")
        top_scores_api = report['exact_scores'][:3]
        col1, col2, col3 = st.columns(3)
        cols = [col1, col2, col3]
        for i, item in enumerate(top_scores_api):
            prob_val = item["Probabilité"]
            implied_odds = round(100 / prob_val, 2) if prob_val > 0 else 99.0
            with cols[i]:
                st.markdown(
                    f"<div style='background: #1e293b; padding: 12px; border-radius: 8px; text-align: center; border: 1px solid #334155;'>"
                    f"<span style='color: #94a3b8; font-size: 12px;'>Option {i+1}</span><br>"
                    f"<strong style='font-size: 20px; color: #38bdf8;'>{item['Score']}</strong><br>"
                    f"<span style='color: #4ade80; font-size: 14px;'>Prob: {prob_val:.1f}%</span><br>"
                    f"<span style='color: #fbbf24; font-size: 12px;'>Côte est. : {implied_odds}</span>"
                    f"</div>",
                    unsafe_allow_html=True
                )
