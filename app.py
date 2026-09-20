# -*- coding: utf-8 -*-
"""
RODRIGUE PRO FOOTBALL AI — API-FOOTBALL + SERPAPI
=================================================
Moteur Streamlit en français.

Architecture
------------
1) API-Football : récupère les matchs et les statistiques disponibles.
2) SerpApi/Google : recherche le contexte récent (absences, compos probables,
   forme, actualités, blessures, etc.).
3) Moteur statistique : mélange forme, attaque/défense, domicile/extérieur,
   H2H et contexte, puis applique une loi de Poisson.
4) Sortie : 1X2, double chance, BTTS, O/U 0.5-3.5, score exact,
   mi-temps et HT/FT.
5) Le moteur ne force jamais une confiance >= 80 %. Si aucun marché n'atteint
   le seuil demandé, il l'indique au lieu d'inventer une fiabilité.

IMPORTANT
---------
Les clés ne sont PAS écrites dans ce fichier.
Dans Streamlit, mets-les dans Secrets :
    API_FOOTBALL_KEY = "..."
    SERPAPI_KEY = "..."

Tu peux aussi utiliser les sections :
    [api]
    football_key = "..."
    serpapi_key = "..."

Installation:
    pip install streamlit requests pandas numpy

Lancement:
    streamlit run rodrigue_pro_api_football_serpapi.py
"""

import math
import re
from datetime import datetime, date
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import requests
import streamlit as st


# ============================================================
# CONFIGURATION
# ============================================================

APP_TITLE = "RODRIGUE PRO FOOTBALL AI"
FOOTBALL_BASE = "https://v3.football.api-sports.io"
SERPAPI_URL = "https://serpapi.com/search.json"

TIMEOUT = 20
MAX_GOALS = 6
DEFAULT_LAST_MATCHES = 10
DEFAULT_H2H = 8
CONFIDENCE_THRESHOLD = 80.0


# ============================================================
# SECRETS STREAMLIT
# ============================================================

def secret_value(*names: str) -> Optional[str]:
    """Cherche une clé dans plusieurs noms possibles."""
    try:
        for name in names:
            try:
                value = st.secrets.get(name)
            except Exception:
                value = None
            if value:
                return str(value).strip()

        # Supporte aussi [api] dans secrets.toml
        try:
            api_section = st.secrets.get("api")
            if api_section:
                for name in names:
                    if name in api_section and api_section[name]:
                        return str(api_section[name]).strip()
        except Exception:
            pass
    except Exception:
        pass
    return None


API_FOOTBALL_KEY = secret_value(
    "API_FOOTBALL_KEY",
    "FOOTBALL_API_KEY",
    "API_FOOTBALL",
)

SERPAPI_KEY = secret_value(
    "SERPAPI_KEY",
    "SERP_API_KEY",
    "SERPAPI",
)


# ============================================================
# SESSION HTTP
# ============================================================

@st.cache_resource
def http_session() -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": "Rodrigue-Pro-Football-AI/1.0"})
    return s


# ============================================================
# OUTILS GENERAUX
# ============================================================

def safe_float(x: Any, default: float = 0.0) -> float:
    try:
        if x is None or x == "":
            return default
        return float(x)
    except Exception:
        return default


def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def poisson_pmf(k: int, lam: float) -> float:
    lam = max(0.001, float(lam))
    return math.exp(-lam) * (lam ** k) / math.factorial(k)


def normalize_probs(values: Dict[str, float]) -> Dict[str, float]:
    total = sum(max(0.0, v) for v in values.values())
    if total <= 0:
        n = len(values)
        return {k: 1.0 / n for k in values}
    return {k: max(0.0, v) / total for k, v in values.items()}


def pct(x: float) -> str:
    return f"{clamp(x, 0, 100):.1f}%"


def status_text() -> str:
    missing = []
    if not API_FOOTBALL_KEY:
        missing.append("API_FOOTBALL_KEY")
    if not SERPAPI_KEY:
        missing.append("SERPAPI_KEY")
    return ", ".join(missing)


# ============================================================
# API-FOOTBALL
# ============================================================

def football_get(endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    if not API_FOOTBALL_KEY:
        raise RuntimeError("Clé API-Football absente des Secrets Streamlit.")

    url = f"{FOOTBALL_BASE}/{endpoint.lstrip('/')}"
    headers = {"x-apisports-key": API_FOOTBALL_KEY}

    r = http_session().get(
        url,
        headers=headers,
        params=params or {},
        timeout=TIMEOUT,
    )

    if r.status_code >= 400:
        raise RuntimeError(f"API-Football HTTP {r.status_code}: {r.text[:400]}")

    data = r.json()

    errors = data.get("errors")
    if errors:
        # errors peut être un dict ou une liste
        if isinstance(errors, dict):
            msg = "; ".join(f"{k}: {v}" for k, v in errors.items())
        else:
            msg = str(errors)
        raise RuntimeError(f"API-Football: {msg}")

    return data


@st.cache_data(ttl=300, show_spinner=False)
def get_fixtures_for_date(day_iso: str) -> List[Dict[str, Any]]:
    data = football_get("fixtures", {"date": day_iso})
    return data.get("response", [])


@st.cache_data(ttl=120, show_spinner=False)
def get_fixture(fixture_id: int) -> Optional[Dict[str, Any]]:
    data = football_get("fixtures", {"id": fixture_id})
    arr = data.get("response", [])
    return arr[0] if arr else None


@st.cache_data(ttl=600, show_spinner=False)
def get_team_last_matches(team_id: int, n: int = DEFAULT_LAST_MATCHES) -> List[Dict[str, Any]]:
    data = football_get("fixtures", {"team": team_id, "last": n})
    return data.get("response", [])


@st.cache_data(ttl=900, show_spinner=False)
def get_h2h(home_id: int, away_id: int, n: int = DEFAULT_H2H) -> List[Dict[str, Any]]:
    data = football_get(
        "fixtures/headtohead",
        {"h2h": f"{home_id}-{away_id}", "last": n},
    )
    return data.get("response", [])


@st.cache_data(ttl=900, show_spinner=False)
def get_team_statistics(team_id: int, league_id: int, season: int) -> Dict[str, Any]:
    data = football_get(
        "teams/statistics",
        {"team": team_id, "league": league_id, "season": season},
    )
    arr = data.get("response", [])
    return arr[0] if arr else {}


@st.cache_data(ttl=300, show_spinner=False)
def get_injuries(fixture_id: int) -> List[Dict[str, Any]]:
    try:
        data = football_get("injuries", {"fixture": fixture_id})
        return data.get("response", [])
    except Exception:
        return []


@st.cache_data(ttl=300, show_spinner=False)
def get_lineups(fixture_id: int) -> List[Dict[str, Any]]:
    try:
        data = football_get("fixtures/lineups", {"fixture": fixture_id})
        return data.get("response", [])
    except Exception:
        return []


# ============================================================
# SERPAPI / GOOGLE
# ============================================================

@st.cache_data(ttl=900, show_spinner=False)
def google_search(query: str, location: str = "Cameroon") -> List[Dict[str, Any]]:
    if not SERPAPI_KEY:
        return []

    params = {
        "engine": "google",
        "q": query,
        "api_key": SERPAPI_KEY,
        "hl": "fr",
        "gl": "cm",
        "location": location,
        "num": 8,
    }

    try:
        r = http_session().get(SERPAPI_URL, params=params, timeout=TIMEOUT)
        if r.status_code >= 400:
            return []

        data = r.json()
        return data.get("organic_results", [])[:8]
    except Exception:
        return []


def web_context(home: str, away: str) -> Dict[str, Any]:
    queries = {
        "absences": f'"{home}" "{away}" blessures absents suspendus composition',
        "forme": f'"{home}" "{away}" forme récente statistiques football',
        "preview": f'"{home}" "{away}" preview statistiques match',
        "lineups": f'"{home}" "{away}" probable lineup composition',
    }

    result: Dict[str, Any] = {}
    for key, q in queries.items():
        result[key] = google_search(q)

    return result


def flatten_web_snippets(web: Dict[str, Any]) -> List[Dict[str, str]]:
    rows = []
    for category, results in web.items():
        for item in results:
            rows.append({
                "catégorie": category,
                "titre": str(item.get("title", "")),
                "source": str(item.get("displayed_link", item.get("link", ""))),
                "extrait": str(item.get("snippet", "")),
                "lien": str(item.get("link", "")),
            })
    return rows


# ============================================================
# EXTRACTION DES STATS
# ============================================================

def goals_from_match(match: Dict[str, Any], team_id: int) -> Tuple[float, float]:
    teams = match.get("teams", {})
    goals = match.get("goals", {})

    home_id = (teams.get("home") or {}).get("id")
    away_id = (teams.get("away") or {}).get("id")

    hg = safe_float(goals.get("home"), 0)
    ag = safe_float(goals.get("away"), 0)

    if team_id == home_id:
        return hg, ag
    if team_id == away_id:
        return ag, hg
    return 0.0, 0.0


def summarize_matches(matches: List[Dict[str, Any]], team_id: int) -> Dict[str, float]:
    played = 0
    gf = ga = 0.0
    home_gf = home_ga = 0.0
    away_gf = away_ga = 0.0
    wins = draws = losses = 0
    over15 = over25 = over35 = btts = 0

    for m in matches:
        status = ((m.get("fixture") or {}).get("status") or {}).get("short", "")
        if status not in {"FT", "AET", "PEN"}:
            continue

        teams = m.get("teams", {})
        hg = safe_float((m.get("goals") or {}).get("home"), 0)
        ag = safe_float((m.get("goals") or {}).get("away"), 0)

        home_id = (teams.get("home") or {}).get("id")
        away_id = (teams.get("away") or {}).get("id")

        if team_id == home_id:
            f, a = hg, ag
            home_gf += f
            home_ga += a
            is_home = True
        elif team_id == away_id:
            f, a = ag, hg
            away_gf += f
            away_ga += a
            is_home = False
        else:
            continue

        played += 1
        gf += f
        ga += a

        if f > a:
            wins += 1
        elif f == a:
            draws += 1
        else:
            losses += 1

        total = hg + ag
        if total > 1.5:
            over15 += 1
        if total > 2.5:
            over25 += 1
        if total > 3.5:
            over35 += 1
        if hg > 0 and ag > 0:
            btts += 1

    if played == 0:
        return {
            "n": 0, "gf": 0, "ga": 0, "gf_avg": 1.25, "ga_avg": 1.25,
            "home_gf": 0, "home_ga": 0, "away_gf": 0, "away_ga": 0,
            "win_rate": 0.33, "draw_rate": 0.34, "loss_rate": 0.33,
            "over15": 0.60, "over25": 0.45, "over35": 0.25, "btts": 0.50,
        }

    return {
        "n": played,
        "gf": gf,
        "ga": ga,
        "gf_avg": gf / played,
        "ga_avg": ga / played,
        "home_gf": home_gf,
        "home_ga": home_ga,
        "away_gf": away_gf,
        "away_ga": away_ga,
        "win_rate": wins / played,
        "draw_rate": draws / played,
        "loss_rate": losses / played,
        "over15": over15 / played,
        "over25": over25 / played,
        "over35": over35 / played,
        "btts": btts / played,
    }


def h2h_summary(matches: List[Dict[str, Any]], home_id: int, away_id: int) -> Dict[str, float]:
    if not matches:
        return {"n": 0, "home_win": 0.33, "draw": 0.34, "away_win": 0.33, "avg_total": 2.5}

    hw = dr = aw = 0
    totals = []

    for m in matches:
        teams = m.get("teams", {})
        hg = safe_float((m.get("goals") or {}).get("home"), 0)
        ag = safe_float((m.get("goals") or {}).get("away"), 0)
        h_id = (teams.get("home") or {}).get("id")
        a_id = (teams.get("away") or {}).get("id")

        if {h_id, a_id} != {home_id, away_id}:
            continue

        totals.append(hg + ag)

        # résultat du point de vue de l'équipe home actuelle
        if h_id == home_id:
            if hg > ag:
                hw += 1
            elif hg == ag:
                dr += 1
            else:
                aw += 1
        else:
            if ag > hg:
                hw += 1
            elif hg == ag:
                dr += 1
            else:
                aw += 1

    n = len(totals)
    if n == 0:
        return {"n": 0, "home_win": 0.33, "draw": 0.34, "away_win": 0.33, "avg_total": 2.5}

    return {
        "n": n,
        "home_win": hw / n,
        "draw": dr / n,
        "away_win": aw / n,
        "avg_total": sum(totals) / n,
    }


# ============================================================
# POISSON
# ============================================================

def score_matrix(lam_home: float, lam_away: float, max_goals: int = MAX_GOALS) -> np.ndarray:
    m = np.zeros((max_goals + 1, max_goals + 1))
    for i in range(max_goals + 1):
        for j in range(max_goals + 1):
            m[i, j] = poisson_pmf(i, lam_home) * poisson_pmf(j, lam_away)

    total = m.sum()
    return m / total if total > 0 else m


def market_probabilities(matrix: np.ndarray) -> Dict[str, float]:
    n = matrix.shape[0]
    home = float(np.tril(matrix, -1).sum())
    draw = float(np.trace(matrix))
    away = float(np.triu(matrix, 1).sum())

    total_goals = np.zeros(2 * n - 1)
    for i in range(n):
        for j in range(n):
            total_goals[i + j] += matrix[i, j]

    def under(line: float) -> float:
        return float(sum(p for k, p in enumerate(total_goals) if k < line))

    def over(line: float) -> float:
        return 1.0 - under(line)

    btts_yes = float(sum(matrix[i, j] for i in range(1, n) for j in range(1, n)))

    return {
        "1": home,
        "X": draw,
        "2": away,
        "1X": home + draw,
        "X2": draw + away,
        "12": home + away,
        "BTTS Oui": btts_yes,
        "BTTS Non": 1.0 - btts_yes,
        "Over 0.5": over(0.5),
        "Under 0.5": under(0.5),
        "Over 1.5": over(1.5),
        "Under 1.5": under(1.5),
        "Over 2.5": over(2.5),
        "Under 2.5": under(2.5),
        "Over 3.5": over(3.5),
        "Under 3.5": under(3.5),
    }


def expected_goals_from_stats(home_s: Dict[str, float], away_s: Dict[str, float],
                              h2h: Dict[str, float]) -> Tuple[float, float]:
    # Baseline de ligue neutre. Le moteur reste conservateur.
    base = 1.35

    # Attaque de l'équipe à domicile vs défense adverse.
    home_attack = max(0.10, home_s["gf_avg"])
    home_def = max(0.10, away_s["ga_avg"])

    away_attack = max(0.10, away_s["gf_avg"])
    away_def = max(0.10, home_s["ga_avg"])

    lam_home = base * (home_attack / base) ** 0.55 * (home_def / base) ** 0.45
    lam_away = base * (away_attack / base) ** 0.55 * (away_def / base) ** 0.45

    # Avantage domicile modéré.
    lam_home *= 1.08
    lam_away *= 0.96

    # H2H seulement si suffisamment d'observations.
    if h2h.get("n", 0) >= 3:
        h2h_total = clamp(h2h.get("avg_total", 2.5), 1.2, 4.2)
        scale = clamp(h2h_total / 2.5, 0.88, 1.12)
        lam_home *= scale
        lam_away *= scale

        # Petit ajustement directionnel, jamais dominant.
        lam_home *= clamp(1 + 0.08 * (h2h["home_win"] - 0.33), 0.96, 1.04)
        lam_away *= clamp(1 + 0.08 * (h2h["away_win"] - 0.33), 0.96, 1.04)

    return clamp(lam_home, 0.15, 3.80), clamp(lam_away, 0.15, 3.50)


def exact_scores(matrix: np.ndarray, top_n: int = 8) -> List[Tuple[str, float]]:
    rows = []
    for i in range(matrix.shape[0]):
        for j in range(matrix.shape[1]):
            rows.append((f"{i}-{j}", float(matrix[i, j])))
    rows.sort(key=lambda x: x[1], reverse=True)
    return rows[:top_n]


# ============================================================
# MI-TEMPS / HT-FT
# ============================================================

def half_time_matrix(lam_home: float, lam_away: float) -> np.ndarray:
    # Environ 44 % des xG du match pour la première période.
    return score_matrix(lam_home * 0.44, lam_away * 0.44, max_goals=5)


def ht_market_probs(ht: np.ndarray) -> Dict[str, float]:
    return {
        "MT 1": float(np.tril(ht, -1).sum()),
        "MT X": float(np.trace(ht)),
        "MT 2": float(np.triu(ht, 1).sum()),
    }


def ht_ft_probs(full: np.ndarray, ht: np.ndarray) -> Dict[str, float]:
    # Approximation cohérente : HT et FT ne sont pas indépendants.
    # On utilise la matrice HT comme ancre et la matrice FT comme distribution finale.
    result = {
        "1/1": 0.0, "X/X": 0.0, "2/2": 0.0,
        "X/1": 0.0, "X/2": 0.0,
        "1/X": 0.0, "1/2": 0.0,
        "2/X": 0.0, "2/1": 0.0,
    }

    for hi in range(ht.shape[0]):
        for aj in range(ht.shape[1]):
            pht = ht[hi, aj]
            if pht <= 0:
                continue

            ht_res = "1" if hi > aj else "X" if hi == aj else "2"

            # Distribution FT conditionnée grossièrement par le signe HT.
            for fi in range(full.shape[0]):
                for fj in range(full.shape[1]):
                    pft = full[fi, fj]
                    ft_res = "1" if fi > fj else "X" if fi == fj else "2"

                    if ht_res == ft_res:
                        weight = 1.25
                    elif ht_res == "X" and ft_res != "X":
                        weight = 1.10
                    else:
                        weight = 0.85

                    key = f"{ht_res}/{ft_res}"
                    result[key] += pht * pft * weight

    return normalize_probs(result)


# ============================================================
# QUALITE / CONTEXTE
# ============================================================

def data_quality(
    home_n: int,
    away_n: int,
    h2h_n: int,
    web_results: int,
    injuries_known: bool,
    lineups_known: bool,
) -> float:
    score = 0.0

    score += 25 if home_n >= 8 else 18 if home_n >= 5 else 10
    score += 25 if away_n >= 8 else 18 if away_n >= 5 else 10
    score += 15 if h2h_n >= 5 else 10 if h2h_n >= 3 else 4
    score += 15 if web_results >= 10 else 10 if web_results >= 5 else 4
    score += 10 if injuries_known else 4
    score += 10 if lineups_known else 3

    return clamp(score, 0, 100)


def confidence_label(p: float, quality: float) -> str:
    # Important : ce n'est pas une probabilité garantie de réussite.
    if p >= 0.80 and quality >= 80:
        return "Élevée"
    if p >= 0.70 and quality >= 60:
        return "Moyenne"
    return "Faible"


def select_four_predictions(
    markets: Dict[str, float],
    exacts: List[Tuple[str, float]],
    ht: Dict[str, float],
    htft: Dict[str, float],
    quality: float,
    threshold: float = CONFIDENCE_THRESHOLD,
) -> List[Dict[str, Any]]:
    candidates = []

    for market, prob in markets.items():
        candidates.append({
            "Marché": market,
            "Pronostic": market,
            "Probabilité modèle": prob,
            "Type": "marché",
        })

    for score, prob in exacts:
        candidates.append({
            "Marché": "Score exact",
            "Pronostic": score,
            "Probabilité modèle": prob,
            "Type": "score",
        })

    for market, prob in ht.items():
        candidates.append({
            "Marché": "Mi-temps",
            "Pronostic": market,
            "Probabilité modèle": prob,
            "Type": "mi-temps",
        })

    for market, prob in htft.items():
        candidates.append({
            "Marché": "HT/FT",
            "Pronostic": market,
            "Probabilité modèle": prob,
            "Type": "htft",
        })

    # On cherche d'abord les marchés au-dessus du seuil.
    # On limite les répétitions du même type.
    eligible = [
        x for x in candidates
        if x["Probabilité modèle"] * 100 >= threshold
    ]

    eligible.sort(key=lambda x: x["Probabilité modèle"], reverse=True)

    chosen = []
    used_types = set()

    for x in eligible:
        if x["Type"] not in used_types or len(chosen) < 2:
            chosen.append(x)
            used_types.add(x["Type"])
        if len(chosen) == 4:
            break

    # S'il n'existe pas 4 marchés >= seuil, on affiche les meilleurs disponibles
    # mais on conserve leur vraie probabilité et leur niveau.
    if len(chosen) < 4:
        candidates.sort(key=lambda x: x["Probabilité modèle"], reverse=True)
        seen = {(x["Marché"], x["Pronostic"]) for x in chosen}
        for x in candidates:
            key = (x["Marché"], x["Pronostic"])
            if key in seen:
                continue
            chosen.append(x)
            seen.add(key)
            if len(chosen) == 4:
                break

    for x in chosen:
        x["Fiabilité affichée"] = x["Probabilité modèle"] * 100
        x["Confiance"] = confidence_label(x["Probabilité modèle"], quality)

    return chosen


# ============================================================
# AFFICHAGE
# ============================================================

def fixture_label(f: Dict[str, Any]) -> str:
    teams = f.get("teams", {})
    home = (teams.get("home") or {}).get("name", "?")
    away = (teams.get("away") or {}).get("name", "?")
    fid = (f.get("fixture") or {}).get("id", "?")
    return f"{home} — {away}  |  ID {fid}"


def build_analysis(fixture_id: int) -> Dict[str, Any]:
    fixture = get_fixture(fixture_id)
    if not fixture:
        raise RuntimeError("Match introuvable.")

    fixture_info = fixture.get("fixture", {})
    league = fixture.get("league", {})
    teams = fixture.get("teams", {})

    home = teams.get("home") or {}
    away = teams.get("away") or {}

    home_id = int(home.get("id"))
    away_id = int(away.get("id"))
    league_id = int(league.get("id"))
    season = int(league.get("season"))

    home_matches = get_team_last_matches(home_id, DEFAULT_LAST_MATCHES)
    away_matches = get_team_last_matches(away_id, DEFAULT_LAST_MATCHES)
    h2h = get_h2h(home_id, away_id, DEFAULT_H2H)

    home_stats = summarize_matches(home_matches, home_id)
    away_stats = summarize_matches(away_matches, away_id)
    h2h_s = h2h_summary(h2h, home_id, away_id)

    # Statistiques officielles de compétition quand elles sont disponibles.
    try:
        home_comp = get_team_statistics(home_id, league_id, season)
    except Exception:
        home_comp = {}
    try:
        away_comp = get_team_statistics(away_id, league_id, season)
    except Exception:
        away_comp = {}

    injuries = get_injuries(fixture_id)
    lineups = get_lineups(fixture_id)

    web = web_context(home.get("name", ""), away.get("name", ""))
    web_rows = flatten_web_snippets(web)

    lam_home, lam_away = expected_goals_from_stats(
        home_stats, away_stats, h2h_s
    )

    full = score_matrix(lam_home, lam_away)
    markets = market_probabilities(full)

    ht = half_time_matrix(lam_home, lam_away)
    ht_probs = ht_market_probs(ht)
    htft = ht_ft_probs(full, ht)

    scores = exact_scores(full, 10)

    quality = data_quality(
        home_stats["n"],
        away_stats["n"],
        h2h_s["n"],
        len(web_rows),
        bool(injuries),
        bool(lineups),
    )

    top4 = select_four_predictions(
        markets, scores, ht_probs, htft, quality
    )

    return {
        "fixture": fixture,
        "home_stats": home_stats,
        "away_stats": away_stats,
        "h2h": h2h_s,
        "home_comp": home_comp,
        "away_comp": away_comp,
        "injuries": injuries,
        "lineups": lineups,
        "web": web,
        "web_rows": web_rows,
        "lambda_home": lam_home,
        "lambda_away": lam_away,
        "matrix": full,
        "markets": markets,
        "ht_probs": ht_probs,
        "htft": htft,
        "scores": scores,
        "quality": quality,
        "top4": top4,
        "kickoff": fixture_info.get("date"),
    }


# ============================================================
# STREAMLIT
# ============================================================

st.set_page_config(
    page_title=APP_TITLE,
    page_icon="⚽",
    layout="wide",
)

st.title("⚽ RODRIGUE PRO FOOTBALL AI")
st.caption(
    "API-Football → données du match | SerpApi/Google → contexte web | "
    "Poisson → probabilités statistiques"
)

with st.sidebar:
    st.header("⚙️ Configuration")

    if API_FOOTBALL_KEY:
        st.success("API-Football : clé détectée")
    else:
        st.error("API-Football : clé absente")

    if SERPAPI_KEY:
        st.success("SerpApi : clé détectée")
    else:
        st.error("SerpApi : clé absente")

    st.divider()
    threshold = st.slider(
        "Seuil de confiance affiché (%)",
        min_value=50,
        max_value=95,
        value=80,
        step=1,
    )

    st.info(
        "Le seuil est un filtre du modèle. Une valeur de 80 % ne signifie "
        "pas que le pari est garanti à 80 %."
    )

if not API_FOOTBALL_KEY or not SERPAPI_KEY:
    st.warning(
        "Ajoute les deux clés dans Streamlit Secrets avant de lancer une analyse."
    )
    st.code(
        '[api]\n'
        'football_key = "TA_CLE_API_FOOTBALL"\n'
        'serpapi_key = "TA_CLE_SERPAPI"\n'
    )
    st.stop()


# ------------------------------------------------------------
# Sélection de date et match
# ------------------------------------------------------------

today = date.today()

col1, col2 = st.columns([1, 2])

with col1:
    selected_date = st.date_input(
        "📅 Date des matchs",
        value=today,
    )

day = selected_date.isoformat()

try:
    fixtures = get_fixtures_for_date(day)
except Exception as e:
    st.error(f"Impossible de récupérer les matchs : {e}")
    st.stop()

# Ne garder que les matchs exploitables.
usable = []
for f in fixtures:
    status = ((f.get("fixture") or {}).get("status") or {}).get("short", "")
    if status in {"NS", "TBD"}:
        usable.append(f)

if not usable:
    st.warning(
        f"Aucun match non commencé trouvé pour le {day}. "
        "Vérifie la date ou la disponibilité des fixtures dans ton abonnement API-Football."
    )
    st.stop()

with col2:
    labels = [fixture_label(f) for f in usable]
    selected_label = st.selectbox("⚽ Choisir le match", labels)

selected_fixture = usable[labels.index(selected_label)]
selected_id = int((selected_fixture.get("fixture") or {}).get("id"))

st.divider()

if st.button("🔎 ANALYSER LE MATCH", type="primary", use_container_width=True):
    try:
        with st.spinner("Récupération des données API-Football + recherche Google..."):
            analysis = build_analysis(selected_id)
    except Exception as e:
        st.error(f"Erreur pendant l'analyse : {e}")
        st.stop()

    f = analysis["fixture"]
    teams = f.get("teams", {})
    home = (teams.get("home") or {}).get("name", "?")
    away = (teams.get("away") or {}).get("name", "?")
    league = f.get("league", {})

    st.subheader(f"🏟️ {home} — {away}")
    st.caption(
        f"{league.get('name', 'Compétition')} | "
        f"{league.get('country', '')} | "
        f"Coup d'envoi : {analysis['kickoff']}"
    )

    # --------------------------------------------------------
    # 4 pronostics
    # --------------------------------------------------------

    st.markdown("## 🎯 4 pronostics principaux")

    q = analysis["quality"]
    st.metric("Qualité des données", f"{q:.0f}%")

    top4 = analysis["top4"]

    df4 = pd.DataFrame([
        {
            "N°": i + 1,
            "Marché": x["Marché"],
            "Pronostic": x["Pronostic"],
            "Probabilité modèle": pct(x["Probabilité modèle"] * 100),
            "Confiance": x["Confiance"],
        }
        for i, x in enumerate(top4)
    ])

    st.dataframe(df4, use_container_width=True, hide_index=True)

    if not any(x["Probabilité modèle"] * 100 >= threshold for x in top4):
        st.warning(
            f"Aucun des 4 pronostics sélectionnés n'atteint réellement "
            f"{threshold} %. Le moteur conserve les probabilités calculées "
            "au lieu de les gonfler artificiellement."
        )
    else:
        st.success(
            f"Au moins un marché atteint le seuil de {threshold} % selon le modèle."
        )

    # --------------------------------------------------------
    # xG Poisson
    # --------------------------------------------------------

    st.markdown("## 🧮 Loi de Poisson")
    c1, c2, c3 = st.columns(3)
    c1.metric(f"xG {home}", f"{analysis['lambda_home']:.2f}")
    c2.metric(f"xG {away}", f"{analysis['lambda_away']:.2f}")
    c3.metric("Qualité données", f"{q:.0f}%")

    # --------------------------------------------------------
    # Marchés
    # --------------------------------------------------------

    st.markdown("## 📊 Marchés principaux")

    market_rows = []
    for market, prob in analysis["markets"].items():
        market_rows.append({
            "Marché": market,
            "Probabilité": prob * 100,
            "Confiance": confidence_label(prob, q),
        })

    df_markets = pd.DataFrame(market_rows)
    df_markets["Probabilité"] = df_markets["Probabilité"].map(lambda x: f"{x:.1f}%")
    st.dataframe(df_markets, use_container_width=True, hide_index=True)

    # --------------------------------------------------------
    # Mi-temps
    # --------------------------------------------------------

    st.markdown("## ⏱️ Mi-temps")

    ht_rows = [
        {"Marché": k, "Probabilité": f"{v * 100:.1f}%", "Confiance": confidence_label(v, q)}
        for k, v in analysis["ht_probs"].items()
    ]
    st.dataframe(pd.DataFrame(ht_rows), use_container_width=True, hide_index=True)

    # --------------------------------------------------------
    # HT/FT
    # --------------------------------------------------------

    st.markdown("## 🔄 HT / FT")

    htft_rows = [
        {"HT/FT": k, "Probabilité": f"{v * 100:.1f}%", "Confiance": confidence_label(v, q)}
        for k, v in sorted(
            analysis["htft"].items(),
            key=lambda kv: kv[1],
            reverse=True,
        )
    ]
    st.dataframe(pd.DataFrame(htft_rows), use_container_width=True, hide_index=True)

    # --------------------------------------------------------
    # Scores exacts
    # --------------------------------------------------------

    st.markdown("## 🎯 Scores exacts les plus probables")

    score_rows = [
        {
            "Score": score,
            "Probabilité modèle": f"{prob * 100:.1f}%",
        }
        for score, prob in analysis["scores"]
    ]
    st.dataframe(pd.DataFrame(score_rows), use_container_width=True, hide_index=True)

    # --------------------------------------------------------
    # Forme
    # --------------------------------------------------------

    st.markdown("## 📈 Forme récente")

    form_df = pd.DataFrame([
        {
            "Équipe": home,
            "Matchs analysés": analysis["home_stats"]["n"],
            "Buts marqués/match": round(analysis["home_stats"]["gf_avg"], 2),
            "Buts encaissés/match": round(analysis["home_stats"]["ga_avg"], 2),
            "Victoire": pct(analysis["home_stats"]["win_rate"] * 100),
            "Nul": pct(analysis["home_stats"]["draw_rate"] * 100),
            "Défaite": pct(analysis["home_stats"]["loss_rate"] * 100),
            "BTTS": pct(analysis["home_stats"]["btts"] * 100),
            "Over 2.5": pct(analysis["home_stats"]["over25"] * 100),
        },
        {
            "Équipe": away,
            "Matchs analysés": analysis["away_stats"]["n"],
            "Buts marqués/match": round(analysis["away_stats"]["gf_avg"], 2),
            "Buts encaissés/match": round(analysis["away_stats"]["ga_avg"], 2),
            "Victoire": pct(analysis["away_stats"]["win_rate"] * 100),
            "Nul": pct(analysis["away_stats"]["draw_rate"] * 100),
            "Défaite": pct(analysis["away_stats"]["loss_rate"] * 100),
            "BTTS": pct(analysis["away_stats"]["btts"] * 100),
            "Over 2.5": pct(analysis["away_stats"]["over25"] * 100),
        },
    ])

    st.dataframe(form_df, use_container_width=True, hide_index=True)

    # --------------------------------------------------------
    # H2H
    # --------------------------------------------------------

    st.markdown("## 🤝 Face-à-face")
    h = analysis["h2h"]

    st.write(
        f"Matchs H2H utilisés : **{h['n']}** | "
        f"moyenne totale : **{h['avg_total']:.2f} buts**"
    )

    h2h_df = pd.DataFrame([
        {"Résultat": "Victoire domicile", "Probabilité historique": f"{h['home_win'] * 100:.1f}%"},
        {"Résultat": "Nul", "Probabilité historique": f"{h['draw'] * 100:.1f}%"},
        {"Résultat": "Victoire extérieur", "Probabilité historique": f"{h['away_win'] * 100:.1f}%"},
    ])
    st.dataframe(h2h_df, use_container_width=True, hide_index=True)

    # --------------------------------------------------------
    # Absences / compositions
    # --------------------------------------------------------

    with st.expander("🚑 Absences / blessures"):
        if analysis["injuries"]:
            rows = []
            for item in analysis["injuries"]:
                player = item.get("player") or {}
                team = item.get("team") or {}
                rows.append({
                    "Équipe": team.get("name", ""),
                    "Joueur": player.get("name", ""),
                    "Type": player.get("type", ""),
                    "Motif": player.get("reason", ""),
                })
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        else:
            st.info("Aucune donnée d'absence retournée par l'endpoint pour ce match.")

    with st.expander("👥 Compositions"):
        if analysis["lineups"]:
            for lineup in analysis["lineups"]:
                st.write(
                    f"**{(lineup.get('team') or {}).get('name', '')}** — "
                    f"Formation : {(lineup.get('formation') or 'N/D')}"
                )
        else:
            st.info("Les compositions ne sont pas encore disponibles.")

    # --------------------------------------------------------
    # Recherche Google via SerpApi
    # --------------------------------------------------------

    with st.expander("🌐 Recherche Google / SerpApi"):
        if analysis["web_rows"]:
            web_df = pd.DataFrame(analysis["web_rows"])
            st.dataframe(
                web_df[["catégorie", "titre", "source", "extrait"]],
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("Aucun résultat web exploitable retourné.")

    st.caption(
        "⚠️ Les pourcentages sont des probabilités produites par un modèle "
        "statistique à partir des données disponibles. Ils ne constituent "
        "pas une garantie de résultat ni une garantie de rentabilité."
    )
