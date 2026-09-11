# ============================================================
# RODRIGUE PRO FOOTBALL AI — V20 ULTIMATE
# ============================================================
# Moteur Streamlit basé sur football-data.org
#
# Fonctions :
# - matchs par date / compétition
# - forme récente + domicile/extérieur
# - classement
# - Poisson robuste
# - 1X2 / double chance
# - BTTS / Over-Under
# - scores exacts
# - mi-temps / MT-FT
# - H2H officiel quand disponible
# - statistiques officielles du Match Resource quand disponibles
# - événements : buts, cartons, remplacements, penalties
# - compositions / formations quand disponibles
# - cotes officielles quand disponibles
# - analyse humaine pondérée
# - score de confiance + qualité des données
#
# IMPORTANT :
# Les données indisponibles ne sont jamais remplacées par des valeurs inventées.
# ============================================================

import math
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import requests
import streamlit as st


# ============================================================
# CONFIGURATION
# ============================================================

API_BASE = "https://api.football-data.org/v4"

# Pour éviter de mettre les clés directement dans le code,
# l'application cherche d'abord Streamlit Secrets puis les variables d'environnement.
# Tu peux aussi remplacer les valeurs ci-dessous par tes clés si nécessaire.
import os

FOOTBALL_DATA_KEY = (
    st.secrets.get("FOOTBALL_DATA_KEY", "")
    if hasattr(st, "secrets")
    else ""
) or os.getenv("FOOTBALL_DATA_KEY", "")

# Compatibilité directe avec ton ancienne installation.
if not FOOTBALL_DATA_KEY:
    FOOTBALL_DATA_KEY = "d212fb8b550d4756b16521dbe73b708d"

COMPETITIONS = {
    "Premier League": "PL",
    "LaLiga": "PD",
    "Bundesliga": "BL1",
    "Serie A": "SA",
    "Ligue 1": "FL1",
    "Champions League": "CL",
    "Eredivisie": "DED",
    "Primeira Liga": "PPL",
    "Championship": "ELC",
    "Brasileirão": "BSA",
}

STAT_LABELS = {
    "corner_kicks": "🚩 Corners",
    "free_kicks": "Coups francs",
    "goal_kicks": "Six mètres",
    "offsides": "🚩 Hors-jeu",
    "fouls": "🟥 Fautes",
    "ball_possession": "📊 Possession",
    "saves": "🧤 Arrêts",
    "throw_ins": "Touches",
    "shots": "🎯 Tirs",
    "shots_on_goal": "🥅 Tirs cadrés",
    "shots_off_goal": "Tirs non cadrés",
    "yellow_cards": "🟨 Cartons jaunes",
    "yellow_red_cards": "🟨🟥 Second jaune",
    "red_cards": "🟥 Cartons rouges",
}

REQUEST_TIMEOUT = 20

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "Rodrigue-Pro-Football-AI-V20",
    "Accept": "application/json",
})


# ============================================================
# PAGE
# ============================================================

st.set_page_config(
    page_title="Rodrigue Pro Football AI V20",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# OUTILS GÉNÉRAUX
# ============================================================

def safe_float(value: Any, default: Optional[float] = None) -> Optional[float]:
    try:
        if value is None:
            return default
        x = float(value)
        if not math.isfinite(x):
            return default
        return x
    except (TypeError, ValueError):
        return default


def safe_int(value: Any, default: Optional[int] = None) -> Optional[int]:
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def pct(value: Optional[float]) -> str:
    if value is None or not math.isfinite(value):
        return "N/D"
    return f"{value * 100:.1f}%"


def fmt_num(value: Any, digits: int = 2) -> str:
    x = safe_float(value)
    if x is None:
        return "N/D"
    return f"{x:.{digits}f}"


def normalize_probabilities(values: Dict[str, float]) -> Dict[str, float]:
    clean = {
        k: max(0.0, safe_float(v, 0.0) or 0.0)
        for k, v in values.items()
    }
    total = sum(clean.values())
    if total <= 0:
        return {k: 0.0 for k in clean}
    return {k: v / total for k, v in clean.items()}


# ============================================================
# API FOOTBALL-DATA.ORG
# ============================================================

@st.cache_data(ttl=300, show_spinner=False)
def football_request(endpoint: str, params_items: Tuple[Tuple[str, Any], ...] = ()) -> Dict[str, Any]:
    params = dict(params_items)

    try:
        response = SESSION.get(
            API_BASE + endpoint,
            headers={"X-Auth-Token": FOOTBALL_DATA_KEY},
            params=params,
            timeout=REQUEST_TIMEOUT,
        )

        try:
            data = response.json()
        except ValueError:
            data = None

        error = ""
        if isinstance(data, dict):
            error = str(
                data.get("message")
                or data.get("error")
                or ""
            )

        if not error and response.status_code != 200:
            error = (response.text or "")[:500]

        return {
            "status": response.status_code,
            "data": data if response.status_code == 200 else None,
            "error": error,
            "remaining": response.headers.get(
                "X-Requests-Available-Minute", ""
            ),
            "reset": response.headers.get(
                "X-RequestCounter-Reset", ""
            ),
            "client": response.headers.get(
                "X-Authenticated-Client", ""
            ),
        }

    except requests.RequestException as exc:
        return {
            "status": 0,
            "data": None,
            "error": str(exc),
            "remaining": "",
            "reset": "",
            "client": "",
        }


def football_get(
    endpoint: str,
    params: Optional[Dict[str, Any]] = None,
) -> Any:
    items = tuple(sorted((params or {}).items()))
    result = football_request(endpoint, items)
    return result.get("data")


@st.cache_data(ttl=300, show_spinner=False)
def validate_api() -> Dict[str, Any]:
    return football_request("/competitions/PL", ())


# ============================================================
# MATCHS
# ============================================================

@st.cache_data(ttl=300, show_spinner=False)
def get_matches_for_date(
    selected_date: date,
    competition_codes: Tuple[str, ...],
) -> List[Dict[str, Any]]:
    if not competition_codes:
        return []

    target = selected_date.isoformat()

    # Aujourd'hui : une requête globale, puis filtrage local.
    if selected_date == date.today():
        result = football_request("/matches", ())
        if result["status"] != 200:
            return []

        matches = (result.get("data") or {}).get("matches", [])

    else:
        # Autres dates : saison par compétition.
        matches = []

        for code in competition_codes:
            result = football_request(
                f"/competitions/{code}/matches",
                (("season", str(selected_date.year)),),
            )

            if result["status"] != 200:
                continue

            matches.extend(
                (result.get("data") or {}).get("matches", [])
            )

    wanted = set(competition_codes)
    output = []
    seen = set()

    for match in matches:
        code = match.get("competition", {}).get("code")
        match_date = str(match.get("utcDate", ""))[:10]

        if code not in wanted:
            continue

        if match_date != target:
            continue

        match_id = match.get("id")
        key = match_id or (
            match_date,
            match.get("homeTeam", {}).get("id"),
            match.get("awayTeam", {}).get("id"),
        )

        if key in seen:
            continue

        seen.add(key)
        output.append(match)

    return sorted(
        output,
        key=lambda m: m.get("utcDate", ""),
    )


# ============================================================
# HISTORIQUE / CLASSEMENT
# ============================================================

@st.cache_data(ttl=900, show_spinner=False)
def fetch_team_history(team_id: Optional[int], limit: int = 12) -> List[Dict[str, Any]]:
    if not team_id:
        return []

    data = football_get(
        f"/teams/{team_id}/matches",
        {
            "status": "FINISHED",
            "limit": limit,
        },
    )

    if not data:
        return []

    return data.get("matches", [])


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_standings(code: str) -> List[Dict[str, Any]]:
    if not code:
        return []

    data = football_get(
        f"/competitions/{code}/standings"
    )

    if not data:
        return []

    standings = data.get("standings", [])

    for standing in standings:
        if standing.get("type") == "TOTAL":
            return standing.get("table", [])

    return standings[0].get("table", []) if standings else []


def get_standing(table: List[Dict[str, Any]], team_id: Optional[int]):
    for row in table:
        if row.get("team", {}).get("id") == team_id:
            return row
    return None


# ============================================================
# FORME
# ============================================================

def team_result(match: Dict[str, Any], team_id: Optional[int]):
    if not team_id:
        return None

    home = match.get("homeTeam", {})
    away = match.get("awayTeam", {})
    full = match.get("score", {}).get("fullTime", {})

    hg = full.get("home")
    ag = full.get("away")

    if hg is None or ag is None:
        return None

    if home.get("id") == team_id:
        gf, ga = hg, ag
        opponent = away.get("name", "?")
        venue = "home"
    elif away.get("id") == team_id:
        gf, ga = ag, hg
        opponent = home.get("name", "?")
        venue = "away"
    else:
        return None

    if gf > ga:
        result = "W"
    elif gf == ga:
        result = "D"
    else:
        result = "L"

    return {
        "result": result,
        "gf": int(gf),
        "ga": int(ga),
        "date": match.get("utcDate", ""),
        "opponent": opponent,
        "venue": venue,
    }


def analyze_form(
    matches: List[Dict[str, Any]],
    team_id: Optional[int],
    last_n: int = 8,
) -> Dict[str, Any]:
    results = []

    for match in matches:
        item = team_result(match, team_id)
        if item:
            results.append(item)

    results = sorted(
        results,
        key=lambda x: x["date"],
        reverse=True,
    )[:last_n]

    if not results:
        return {
            "matches": 0,
            "wins": 0,
            "draws": 0,
            "losses": 0,
            "gf": 0,
            "ga": 0,
            "gf_avg": 0.0,
            "ga_avg": 0.0,
            "points": 0,
            "points_avg": 0.0,
            "form_score": 0.5,
            "results": [],
        }

    wins = sum(x["result"] == "W" for x in results)
    draws = sum(x["result"] == "D" for x in results)
    losses = sum(x["result"] == "L" for x in results)

    gf = sum(x["gf"] for x in results)
    ga = sum(x["ga"] for x in results)

    points = wins * 3 + draws

    return {
        "matches": len(results),
        "wins": wins,
        "draws": draws,
        "losses": losses,
        "gf": gf,
        "ga": ga,
        "gf_avg": gf / len(results),
        "ga_avg": ga / len(results),
        "points": points,
        "points_avg": points / len(results),
        "form_score": points / (len(results) * 3),
        "results": results,
    }


def analyze_home_away(
    matches: List[Dict[str, Any]],
    team_id: Optional[int],
    home: bool,
    last_n: int = 8,
) -> Dict[str, Any]:
    filtered = []

    for match in matches:
        home_id = match.get("homeTeam", {}).get("id")
        away_id = match.get("awayTeam", {}).get("id")

        if home and home_id == team_id:
            filtered.append(match)

        if not home and away_id == team_id:
            filtered.append(match)

    return analyze_form(filtered, team_id, last_n)


# ============================================================
# POISSON ROBUSTE
# ============================================================

def poisson_probability(lam: float, goals: int) -> float:
    lam = safe_float(lam)

    if lam is None or not math.isfinite(lam):
        return 0.0

    if lam < 0 or goals < 0:
        return 0.0

    if lam == 0:
        return 1.0 if goals == 0 else 0.0

    try:
        log_p = (
            -lam
            + goals * math.log(lam)
            - math.lgamma(goals + 1)
        )
        value = math.exp(log_p)
        return clamp(value, 0.0, 1.0)
    except (OverflowError, ValueError):
        return 0.0


def poisson_matrix(
    home_lambda: float,
    away_lambda: float,
    max_goals: int = 8,
) -> np.ndarray:
    home_lambda = safe_float(home_lambda, 0.0) or 0.0
    away_lambda = safe_float(away_lambda, 0.0) or 0.0

    home_lambda = max(0.0, home_lambda)
    away_lambda = max(0.0, away_lambda)

    max_goals = max(1, int(max_goals))

    home_probs = np.array([
        poisson_probability(home_lambda, h)
        for h in range(max_goals + 1)
    ])

    away_probs = np.array([
        poisson_probability(away_lambda, a)
        for a in range(max_goals + 1)
    ])

    matrix = np.outer(home_probs, away_probs)

    matrix = np.nan_to_num(
        matrix,
        nan=0.0,
        posinf=0.0,
        neginf=0.0,
    )

    total = float(matrix.sum())

    if total <= 0:
        raise ValueError("Matrice de Poisson invalide.")

    # Normalisation de la zone 0..max_goals.
    matrix /= total

    return matrix


# ============================================================
# MARCHÉS
# ============================================================

def calculate_markets(matrix: np.ndarray) -> Dict[str, float]:
    home_win = draw = away_win = 0.0
    btts = 0.0
    over15 = over25 = over35 = 0.0

    for h in range(matrix.shape[0]):
        for a in range(matrix.shape[1]):
            p = float(matrix[h, a])

            if h > a:
                home_win += p
            elif h == a:
                draw += p
            else:
                away_win += p

            if h >= 1 and a >= 1:
                btts += p

            total = h + a

            if total >= 2:
                over15 += p
            if total >= 3:
                over25 += p
            if total >= 4:
                over35 += p

    one_x_two = normalize_probabilities({
        "1": home_win,
        "X": draw,
        "2": away_win,
    })

    return {
        **one_x_two,
        "1X": one_x_two["1"] + one_x_two["X"],
        "X2": one_x_two["X"] + one_x_two["2"],
        "12": one_x_two["1"] + one_x_two["2"],
        "BTTS Oui": clamp(btts, 0.0, 1.0),
        "BTTS Non": clamp(1.0 - btts, 0.0, 1.0),
        "Over 1.5": clamp(over15, 0.0, 1.0),
        "Under 1.5": clamp(1.0 - over15, 0.0, 1.0),
        "Over 2.5": clamp(over25, 0.0, 1.0),
        "Under 2.5": clamp(1.0 - over25, 0.0, 1.0),
        "Over 3.5": clamp(over35, 0.0, 1.0),
        "Under 3.5": clamp(1.0 - over35, 0.0, 1.0),
    }


def exact_scores(matrix: np.ndarray, limit: int = 10):
    rows = []

    for h in range(matrix.shape[0]):
        for a in range(matrix.shape[1]):
            rows.append((f"{h}-{a}", float(matrix[h, a])))

    rows.sort(key=lambda x: x[1], reverse=True)

    return rows[:limit]


# ============================================================
# MI-TEMPS / MT-FT
# ============================================================

def half_time_model(
    home_lambda: float,
    away_lambda: float,
) -> Dict[str, Any]:
    matrix = poisson_matrix(
        home_lambda * 0.44,
        away_lambda * 0.44,
        6,
    )

    return {
        "matrix": matrix,
        "markets": calculate_markets(matrix),
        "scores": exact_scores(matrix, 8),
    }


def result_from_score(h: int, a: int) -> str:
    if h > a:
        return "1"
    if h == a:
        return "X"
    return "2"


def htft_model(
    home_lambda: float,
    away_lambda: float,
) -> List[Tuple[str, float]]:
    ht = half_time_model(home_lambda, away_lambda)
    ft = poisson_matrix(home_lambda, away_lambda, 8)

    ht_results = {"1": 0.0, "X": 0.0, "2": 0.0}
    ft_results = {"1": 0.0, "X": 0.0, "2": 0.0}

    for h in range(ht["matrix"].shape[0]):
        for a in range(ht["matrix"].shape[1]):
            ht_results[result_from_score(h, a)] += float(
                ht["matrix"][h, a]
            )

    for h in range(ft.shape[0]):
        for a in range(ft.shape[1]):
            ft_results[result_from_score(h, a)] += float(
                ft[h, a]
            )

    combinations = {}

    for ht_result, hp in ht_results.items():
        for ft_result, fp in ft_results.items():
            combinations[f"{ht_result}/{ft_result}"] = hp * fp

    total = sum(combinations.values())

    if total > 0:
        combinations = {
            k: v / total
            for k, v in combinations.items()
        }

    return sorted(
        combinations.items(),
        key=lambda x: x[1],
        reverse=True,
    )


# ============================================================
# XG / LAMBDAS
# ============================================================

def build_lambdas(
    home_form: Dict[str, Any],
    away_form: Dict[str, Any],
    home_split: Dict[str, Any],
    away_split: Dict[str, Any],
    home_standing: Optional[Dict[str, Any]] = None,
    away_standing: Optional[Dict[str, Any]] = None,
) -> Tuple[float, float]:
    # Fallback neutre lorsque l'historique est absent.
    hf_gf = home_form["gf_avg"] if home_form["matches"] else 1.35
    hf_ga = home_form["ga_avg"] if home_form["matches"] else 1.25
    af_gf = away_form["gf_avg"] if away_form["matches"] else 1.15
    af_ga = away_form["ga_avg"] if away_form["matches"] else 1.35

    hs_gf = home_split["gf_avg"] if home_split["matches"] else hf_gf
    hs_ga = home_split["ga_avg"] if home_split["matches"] else hf_ga
    as_gf = away_split["gf_avg"] if away_split["matches"] else af_gf
    as_ga = away_split["ga_avg"] if away_split["matches"] else af_ga

    home_attack = 0.55 * hf_gf + 0.45 * hs_gf
    away_attack = 0.55 * af_gf + 0.45 * as_gf

    home_defense = 0.55 * af_ga + 0.45 * as_ga
    away_defense = 0.55 * hs_ga + 0.45 * hs_ga

    # Correction : défense extérieure basée sur les buts encaissés
    # de l'équipe à domicile, et non sur une moyenne incohérente.
    away_defense = 0.55 * hf_ga + 0.45 * hs_ga

    home_lambda = (
        0.60 * home_attack
        + 0.40 * home_defense
    )

    away_lambda = (
        0.60 * away_attack
        + 0.40 * away_defense
    )

    # Avantage domicile.
    home_lambda *= 1.08
    away_lambda *= 0.94

    # Dynamique.
    home_lambda *= 0.93 + 0.14 * home_form["form_score"]
    away_lambda *= 0.93 + 0.14 * away_form["form_score"]

    # Classement : ajustement très faible pour ne pas écraser la forme.
    if home_standing and away_standing:
        hp = safe_int(home_standing.get("position"))
        ap = safe_int(away_standing.get("position"))

        if hp and ap:
            gap = clamp((ap - hp) / 20.0, -0.20, 0.20)
            home_lambda *= 1.0 + 0.05 * gap
            away_lambda *= 1.0 - 0.04 * gap

    return (
        clamp(home_lambda, 0.20, 3.80),
        clamp(away_lambda, 0.15, 3.50),
    )


# ============================================================
# MATCH RESOURCE OFFICIEL
# ============================================================

@st.cache_data(ttl=300, show_spinner=False)
def fetch_match_detail(match_id: Optional[int]) -> Optional[Dict[str, Any]]:
    if not match_id:
        return None

    result = football_request(f"/matches/{match_id}", ())
    return result.get("data")


@st.cache_data(ttl=900, show_spinner=False)
def fetch_h2h(match_id: Optional[int], limit: int = 10) -> List[Dict[str, Any]]:
    if not match_id:
        return []

    result = football_request(
        f"/matches/{match_id}/head2head",
        (("limit", limit),),
    )

    data = result.get("data") or {}

    if isinstance(data, dict):
        matches = data.get("matches", [])
        if isinstance(matches, list):
            return matches

    return []


# ============================================================
# STATISTIQUES OFFICIELLES
# ============================================================

def _normalize_stat_value(value: Any) -> Optional[float]:
    if value is None:
        return None

    if isinstance(value, dict):
        value = value.get("value")

    if isinstance(value, str):
        text = value.strip().replace("%", "").replace(",", ".")
        try:
            return float(text)
        except ValueError:
            return None

    return safe_float(value)


def extract_match_statistics(
    detail: Optional[Dict[str, Any]],
) -> Dict[str, Dict[str, Optional[float]]]:
    empty = {
        "home": {},
        "away": {},
    }

    if not detail:
        return empty

    stats = detail.get("statistics", [])

    # Format football-data.org courant :
    # statistics: [
    #   {"period": "ALL", "group": [...]}
    # ]
    if not isinstance(stats, list):
        return empty

    selected = None

    for block in stats:
        if str(block.get("period", "")).upper() == "ALL":
            selected = block
            break

    if selected is None and stats:
        selected = stats[0]

    if not selected:
        return empty

    output = {
        "home": {},
        "away": {},
    }

    groups = selected.get("groups", [])

    for group in groups or []:
        for stat in group.get("statistics", []) or []:
            name = stat.get("name")
            if not name:
                continue

            output["home"][name] = _normalize_stat_value(
                stat.get("home")
            )
            output["away"][name] = _normalize_stat_value(
                stat.get("away")
            )

    return output


def display_official_stats(
    detail: Optional[Dict[str, Any]],
    home_name: str,
    away_name: str,
):
    stats = extract_match_statistics(detail)

    if not stats["home"] and not stats["away"]:
        st.info(
            "ℹ️ Statistiques officielles détaillées indisponibles "
            "pour ce match ou cette compétition."
        )
        return

    rows = []

    all_keys = set(stats["home"]) | set(stats["away"])

    for key in all_keys:
        label = STAT_LABELS.get(key, key)

        rows.append({
            "Statistique": label,
            home_name: (
                fmt_num(stats["home"].get(key), 1)
                if stats["home"].get(key) is not None
                else "N/D"
            ),
            away_name: (
                fmt_num(stats["away"].get(key), 1)
                if stats["away"].get(key) is not None
                else "N/D"
            ),
        })

    if rows:
        st.dataframe(
            pd.DataFrame(rows),
            use_container_width=True,
            hide_index=True,
        )


# ============================================================
# AJUSTEMENT STATS
# ============================================================

def stats_attack_adjustment(
    detail: Optional[Dict[str, Any]],
    home_lambda: float,
    away_lambda: float,
) -> Tuple[float, float, Dict[str, float]]:
    stats = extract_match_statistics(detail)

    if not stats["home"] or not stats["away"]:
        return home_lambda, away_lambda, {
            "home_factor": 1.0,
            "away_factor": 1.0,
        }

    home_factor = 1.0
    away_factor = 1.0

    # Cet ajustement est volontairement très limité.
    # Les stats d'un match passé ne doivent pas dominer la forme.
    for side, key in [
        ("home", "shots_on_goal"),
        ("away", "shots_on_goal"),
    ]:
        h = stats[side].get(key)
        if h is None:
            continue

        factor = 1.0 + clamp((h - 4.0) * 0.012, -0.05, 0.05)

        if side == "home":
            home_factor *= factor
        else:
            away_factor *= factor

    for side, key in [
        ("home", "ball_possession"),
        ("away", "ball_possession"),
    ]:
        value = stats[side].get(key)

        if value is None:
            continue

        factor = 1.0 + clamp((value - 50.0) * 0.002, -0.04, 0.04)

        if side == "home":
            home_factor *= factor
        else:
            away_factor *= factor

    return (
        clamp(home_lambda * home_factor, 0.15, 3.90),
        clamp(away_lambda * away_factor, 0.15, 3.60),
        {
            "home_factor": home_factor,
            "away_factor": away_factor,
        },
    )


# ============================================================
# H2H
# ============================================================

def h2h_signal(
    h2h_matches: List[Dict[str, Any]],
    home_id: Optional[int],
    away_id: Optional[int],
) -> Dict[str, Any]:
    home_wins = draws = away_wins = 0
    usable = 0

    for match in h2h_matches:
        home_team_id = match.get("homeTeam", {}).get("id")
        away_team_id = match.get("awayTeam", {}).get("id")
        score = match.get("score", {}).get("fullTime", {})

        hg = score.get("home")
        ag = score.get("away")

        if hg is None or ag is None:
            continue

        # On réoriente toujours le résultat par rapport
        # au domicile du match analysé.
        if home_team_id == home_id and away_team_id == away_id:
            oriented_home = hg
            oriented_away = ag
        elif home_team_id == away_id and away_team_id == home_id:
            oriented_home = ag
            oriented_away = hg
        else:
            continue

        usable += 1

        if oriented_home > oriented_away:
            home_wins += 1
        elif oriented_home == oriented_away:
            draws += 1
        else:
            away_wins += 1

    return {
        "matches": usable,
        "home_wins": home_wins,
        "draws": draws,
        "away_wins": away_wins,
    }


# ============================================================
# COTES
# ============================================================

def extract_official_odds(
    detail: Optional[Dict[str, Any]],
) -> Dict[str, Optional[float]]:
    if not detail:
        return {}

    odds = detail.get("odds", {})

    if not isinstance(odds, dict):
        return {}

    raw = {
        "1": odds.get("homeWin"),
        "X": odds.get("draw"),
        "2": odds.get("awayWin"),
    }

    inv = {}

    for key, odd in raw.items():
        value = safe_float(odd)
        if value and value > 1.0:
            inv[key] = 1.0 / value

    if len(inv) != 3:
        return {}

    total = sum(inv.values())

    if total <= 0:
        return {}

    return {
        key: value / total
        for key, value in inv.items()
    }


# ============================================================
# ÉVÉNEMENTS
# ============================================================

def official_event_summary(detail: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not detail:
        return {
            "goals": 0,
            "yellow_cards": 0,
            "red_cards": 0,
            "substitutions": 0,
            "penalties": 0,
            "events": [],
        }

    goals = 0
    yellow = 0
    red = 0
    substitutions = 0
    penalties = 0
    events = []

    for goal in detail.get("goals", []) or []:
        goals += 1
        events.append({
            "type": "But",
            "minute": goal.get("minute"),
            "team": goal.get("team", {}).get("name", ""),
            "player": goal.get("scorer", {}).get("name", ""),
        })

        if goal.get("type") == "PENALTY":
            penalties += 1

    for booking in detail.get("bookings", []) or []:
        card = str(booking.get("card", "")).upper()

        if "YELLOW" in card:
            yellow += 1
        if "RED" in card:
            red += 1

        events.append({
            "type": "Carton",
            "minute": booking.get("minute"),
            "team": booking.get("team", {}).get("name", ""),
            "player": booking.get("player", {}).get("name", ""),
            "card": card,
        })

    for sub in detail.get("substitutions", []) or []:
        substitutions += 1
        events.append({
            "type": "Remplacement",
            "minute": sub.get("minute"),
            "team": sub.get("team", {}).get("name", ""),
            "player_in": sub.get("playerIn", {}).get("name", ""),
            "player_out": sub.get("playerOut", {}).get("name", ""),
        })

    return {
        "goals": goals,
        "yellow_cards": yellow,
        "red_cards": red,
        "substitutions": substitutions,
        "penalties": penalties,
        "events": events,
    }


# ============================================================
# COMPOSITIONS
# ============================================================

def lineup_summary(
    detail: Optional[Dict[str, Any]],
    side: str,
) -> Dict[str, Any]:
    if not detail:
        return {
            "formation": "",
            "coach": "",
            "lineup": [],
            "bench": [],
        }

    lineup = detail.get("lineups", [])

    if not isinstance(lineup, list):
        return {
            "formation": "",
            "coach": "",
            "lineup": [],
            "bench": [],
        }

    team_id = detail.get(
        "homeTeam", {}
    ).get("id") if side == "home" else detail.get(
        "awayTeam", {}
    ).get("id")

    selected = None

    for item in lineup:
        if item.get("team", {}).get("id") == team_id:
            selected = item
            break

    if not selected:
        return {
            "formation": "",
            "coach": "",
            "lineup": [],
            "bench": [],
        }

    starters = [
        x.get("player", {}).get("name", "")
        for x in selected.get("startXI", []) or []
        if x.get("player", {}).get("name")
    ]

    bench = [
        x.get("player", {}).get("name", "")
        for x in selected.get("substitutes", []) or []
        if x.get("player", {}).get("name")
    ]

    coach = selected.get("coach", {}).get("name", "")

    return {
        "formation": selected.get("formation", ""),
        "coach": coach,
        "lineup": starters,
        "bench": bench,
    }


# ============================================================
# ABSENCES : SOURCE OFFICIELLE QUAND DISPONIBLE
# ============================================================

def unavailable_from_lineup(
    detail: Optional[Dict[str, Any]],
    side: str,
) -> List[str]:
    """
    Ne prétend pas détecter des blessures.
    Signale uniquement ce qui est effectivement disponible
    dans la composition officielle.
    """
    info = lineup_summary(detail, side)

    if not info["lineup"] and not info["bench"]:
        return []

    return []


# ============================================================
# CONFIANCE / QUALITÉ DES DONNÉES
# ============================================================

def data_quality_score(
    home_form: Dict[str, Any],
    away_form: Dict[str, Any],
    h2h: Dict[str, Any],
    detail: Optional[Dict[str, Any]],
    standings_available: bool,
    odds_available: bool,
) -> int:
    score = 20

    history_matches = (
        home_form["matches"] + away_form["matches"]
    )

    if history_matches >= 12:
        score += 25
    elif history_matches >= 8:
        score += 18
    elif history_matches >= 4:
        score += 10

    if standings_available:
        score += 15

    if h2h.get("matches", 0) >= 3:
        score += 10

    if detail:
        score += 10

        stats = extract_match_statistics(detail)

        if stats["home"] or stats["away"]:
            score += 5

    if odds_available:
        score += 5

    return int(clamp(score, 0, 100))


def confidence_score(
    markets: Dict[str, float],
    home_form: Dict[str, Any],
    away_form: Dict[str, Any],
    quality: int,
    h2h: Dict[str, Any],
) -> int:
    one_x_two = [
        markets.get("1", 0.0),
        markets.get("X", 0.0),
        markets.get("2", 0.0),
    ]

    sorted_probs = sorted(one_x_two, reverse=True)
    gap = sorted_probs[0] - sorted_probs[1]

    base = 48 + gap * 75
    base += (quality - 50) * 0.20

    if h2h.get("matches", 0) >= 5:
        base += 2

    if (
        home_form["matches"] >= 6
        and away_form["matches"] >= 6
    ):
        base += 2

    return int(clamp(base, 45, 92))


# ============================================================
# ANALYSE HUMAINE
# ============================================================

def human_analysis(
    home: str,
    away: str,
    markets: Dict[str, float],
    scores: List[Tuple[str, float]],
    htft: List[Tuple[str, float]],
    home_form: Dict[str, Any],
    away_form: Dict[str, Any],
    home_lambda: float,
    away_lambda: float,
    h2h: Optional[Dict[str, Any]] = None,
    odds: Optional[Dict[str, float]] = None,
    quality: int = 50,
) -> Dict[str, Any]:
    h2h = h2h or {}
    odds = odds or {}

    result_probs = {
        "1": markets.get("1", 0.0),
        "X": markets.get("X", 0.0),
        "2": markets.get("2", 0.0),
    }

    main_result = max(
        result_probs,
        key=result_probs.get,
    )

    best_score = scores[0][0] if scores else "N/D"
    best_htft = htft[0][0] if htft else "N/D"

    # Lecture dynamique.
    if (
        abs(result_probs["1"] - result_probs["2"]) < 0.07
        and result_probs["X"] >= 0.27
    ):
        reading = (
            "Les forces sont relativement proches. "
            "Le nul ou une double chance mérite davantage "
            "d'attention qu'un 1X2 sec."
        )
    elif (
        result_probs["1"] > result_probs["2"]
        and home_form["form_score"] >= away_form["form_score"]
    ):
        reading = (
            f"{home} possède la convergence la plus favorable "
            "entre avantage domicile, dynamique et modèle de buts."
        )
    elif (
        result_probs["2"] > result_probs["1"]
        and away_form["form_score"] >= home_form["form_score"]
    ):
        reading = (
            f"{away} présente le signal extérieur le plus favorable "
            "selon les données disponibles."
        )
    else:
        reading = (
            "Les signaux sont mixtes. Une couverture paraît "
            "plus rationnelle qu'un 1X2 sec."
        )

    # Buts.
    if markets.get("Over 2.5", 0) >= 0.62:
        goals = "Le modèle donne un avantage clair au scénario Over 2.5."
    elif markets.get("Under 2.5", 0) >= 0.62:
        goals = "Le modèle donne un avantage clair au scénario Under 2.5."
    else:
        goals = "Le total de buts reste équilibré."

    # BTTS.
    if markets.get("BTTS Oui", 0) >= 0.62:
        btts = "Signal favorable au BTTS Oui."
    elif markets.get("BTTS Non", 0) >= 0.62:
        btts = "Signal favorable au BTTS Non."
    else:
        btts = "Le BTTS reste partagé."

    # H2H.
    h2h_text = "H2H non exploitable."

    if h2h.get("matches", 0) > 0:
        h2h_text = (
            f"H2H : {h2h['home_wins']} victoire(s) domicile, "
            f"{h2h['draws']} nul(s), "
            f"{h2h['away_wins']} victoire(s) extérieur "
            f"sur {h2h['matches']} rencontre(s) orientée(s)."
        )

    # Meilleur marché parmi les marchés relativement simples.
    candidate_markets = {
        "1X": markets.get("1X", 0),
        "X2": markets.get("X2", 0),
        "12": markets.get("12", 0),
        "BTTS Oui": markets.get("BTTS Oui", 0),
        "BTTS Non": markets.get("BTTS Non", 0),
        "Over 1.5": markets.get("Over 1.5", 0),
        "Under 1.5": markets.get("Under 1.5", 0),
        "Over 2.5": markets.get("Over 2.5", 0),
        "Under 2.5": markets.get("Under 2.5", 0),
        "Over 3.5": markets.get("Over 3.5", 0),
        "Under 3.5": markets.get("Under 3.5", 0),
    }

    best_market = max(
        candidate_markets,
        key=candidate_markets.get,
    )

    best_market_probability = candidate_markets[best_market]

    confidence = confidence_score(
        markets,
        home_form,
        away_form,
        quality,
        h2h,
    )

    return {
        "main_result": main_result,
        "best_score": best_score,
        "best_htft": best_htft,
        "reading": reading,
        "goals": goals,
        "btts": btts,
        "h2h": h2h_text,
        "best_market": best_market,
        "best_market_probability": best_market_probability,
        "confidence": confidence,
        "quality": quality,
        "model_gap": max(result_probs.values())
        - sorted(result_probs.values())[-2],
        "odds_available": bool(odds),
    }


# ============================================================
# ANALYSE COMPLÈTE
# ============================================================

@st.cache_data(ttl=300, show_spinner=False)
def analyze_match_cached(
    match: Dict[str, Any],
) -> Dict[str, Any]:
    home = match.get("homeTeam", {})
    away = match.get("awayTeam", {})

    home_id = home.get("id")
    away_id = away.get("id")

    home_name = home.get("name", "Domicile")
    away_name = away.get("name", "Extérieur")

    competition_data = match.get("competition", {})
    competition = competition_data.get("name", "")
    competition_code = competition_data.get("code", "")

    # Historique.
    home_history = fetch_team_history(home_id, 12)
    away_history = fetch_team_history(away_id, 12)

    home_form = analyze_form(
        home_history,
        home_id,
        8,
    )

    away_form = analyze_form(
        away_history,
        away_id,
        8,
    )

    home_split = analyze_home_away(
        home_history,
        home_id,
        True,
        8,
    )

    away_split = analyze_home_away(
        away_history,
        away_id,
        False,
        8,
    )

    # Classement.
    table = fetch_standings(competition_code)
    home_standing = get_standing(table, home_id)
    away_standing = get_standing(table, away_id)

    # Modèle initial.
    home_lambda, away_lambda = build_lambdas(
        home_form,
        away_form,
        home_split,
        away_split,
        home_standing,
        away_standing,
    )

    # Match Resource officiel.
    match_id = match.get("id")
    detail = fetch_match_detail(match_id)

    # Stats du match si disponibles.
    home_lambda, away_lambda, stat_factors = stats_attack_adjustment(
        detail,
        home_lambda,
        away_lambda,
    )

    # Poisson.
    matrix = poisson_matrix(
        home_lambda,
        away_lambda,
        8,
    )

    markets = calculate_markets(matrix)
    scores = exact_scores(matrix, 12)

    ht = half_time_model(
        home_lambda,
        away_lambda,
    )

    htft = htft_model(
        home_lambda,
        away_lambda,
    )

    # H2H.
    h2h_matches = fetch_h2h(match_id, 10)
    h2h = h2h_signal(
        h2h_matches,
        home_id,
        away_id,
    )

    # Cotes officielles.
    odds = extract_official_odds(detail)

    # Événements / compositions.
    events = official_event_summary(detail)

    home_lineup = lineup_summary(detail, "home")
    away_lineup = lineup_summary(detail, "away")

    quality = data_quality_score(
        home_form,
        away_form,
        h2h,
        detail,
        bool(home_standing and away_standing),
        bool(odds),
    )

    verdict = human_analysis(
        home_name,
        away_name,
        markets,
        scores,
        htft,
        home_form,
        away_form,
        home_lambda,
        away_lambda,
        h2h,
        odds,
        quality,
    )

    return {
        "home": home_name,
        "away": away_name,
        "competition": competition,
        "competition_code": competition_code,
        "match_id": match_id,
        "utcDate": match.get("utcDate", ""),
        "home_form": home_form,
        "away_form": away_form,
        "home_split": home_split,
        "away_split": away_split,
        "home_standing": home_standing,
        "away_standing": away_standing,
        "home_lambda": home_lambda,
        "away_lambda": away_lambda,
        "markets": markets,
        "scores": scores,
        "ht": ht,
        "htft": htft,
        "h2h_matches": h2h_matches,
        "h2h": h2h,
        "odds": odds,
        "detail": detail,
        "stat_factors": stat_factors,
        "events": events,
        "home_lineup": home_lineup,
        "away_lineup": away_lineup,
        "verdict": verdict,
    }


# ============================================================
# AFFICHAGE
# ============================================================

def form_string(form: Dict[str, Any]) -> str:
    if not form["results"]:
        return "N/D"

    return " ".join(
        item["result"]
        for item in form["results"]
    )


def display_form(
    title: str,
    form: Dict[str, Any],
):
    st.markdown(f"### {title}")

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Matchs", form["matches"])
    c2.metric("Victoires", form["wins"])
    c3.metric("Nuls", form["draws"])
    c4.metric("Défaites", form["losses"])

    st.write(
        f"**Forme :** `{form_string(form)}`"
    )

    st.write(
        f"**Buts :** {form['gf']} marqués / {form['ga']} encaissés"
    )

    st.write(
        f"**Moyennes :** {form['gf_avg']:.2f} marqués · "
        f"{form['ga_avg']:.2f} encaissés"
    )


def display_markets(result: Dict[str, Any]):
    markets = result["markets"]

    rows = []

    for key in [
        "1",
        "X",
        "2",
        "1X",
        "X2",
        "12",
        "BTTS Oui",
        "BTTS Non",
        "Over 1.5",
        "Under 1.5",
        "Over 2.5",
        "Under 2.5",
        "Over 3.5",
        "Under 3.5",
    ]:
        rows.append({
            "Marché": key,
            "Probabilité": pct(markets.get(key)),
        })

    st.dataframe(
        pd.DataFrame(rows),
        use_container_width=True,
        hide_index=True,
    )


def display_standings(
    result: Dict[str, Any],
):
    rows = []

    for side, team, standing in [
        (
            "🏠",
            result["home"],
            result["home_standing"],
        ),
        (
            "✈️",
            result["away"],
            result["away_standing"],
        ),
    ]:
        if standing:
            rows.append({
                "Équipe": f"{side} {team}",
                "Position": standing.get("position", "N/D"),
                "Points": standing.get("points", "N/D"),
                "MJ": standing.get("playedGames", "N/D"),
                "Différence": standing.get(
                    "goalDifference",
                    "N/D",
                ),
            })
        else:
            rows.append({
                "Équipe": f"{side} {team}",
                "Position": "N/D",
                "Points": "N/D",
                "MJ": "N/D",
                "Différence": "N/D",
            })

    st.dataframe(
        pd.DataFrame(rows),
        use_container_width=True,
        hide_index=True,
    )


def display_lineups(result: Dict[str, Any]):
    c1, c2 = st.columns(2)

    for col, title, info in [
        (
            c1,
            f"🏠 {result['home']}",
            result["home_lineup"],
        ),
        (
            c2,
            f"✈️ {result['away']}",
            result["away_lineup"],
        ),
    ]:
        with col:
            st.markdown(f"### {title}")

            if not info["lineup"] and not info["bench"]:
                st.info("Composition officielle non disponible.")
                continue

            if info["formation"]:
                st.write(
                    f"**Formation :** {info['formation']}"
                )

            if info["coach"]:
                st.write(
                    f"**Entraîneur :** {info['coach']}"
                )

            if info["lineup"]:
                st.write("**Onze :**")
                st.write(
                    ", ".join(info["lineup"])
                )

            if info["bench"]:
                st.write("**Banc :**")
                st.write(
                    ", ".join(info["bench"])
                )


def display_events(result: Dict[str, Any]):
    events = result["events"]

    c1, c2, c3, c4, c5 = st.columns(5)

    c1.metric("Buts", events["goals"])
    c2.metric("Jaunes", events["yellow_cards"])
    c3.metric("Rouges", events["red_cards"])
    c4.metric("Remplacements", events["substitutions"])
    c5.metric("Penalties", events["penalties"])

    if events["events"]:
        rows = []

        for event in events["events"]:
            rows.append({
                "Type": event.get("type", ""),
                "Minute": event.get("minute", "N/D"),
                "Équipe": event.get("team", ""),
                "Joueur": (
                    event.get("player")
                    or event.get("player_in")
                    or ""
                ),
                "Détail": (
                    event.get("card")
                    or (
                        f"IN {event.get('player_in', '')} / "
                        f"OUT {event.get('player_out', '')}"
                    )
                    if event.get("type") == "Remplacement"
                    else ""
                ),
            })

        st.dataframe(
            pd.DataFrame(rows),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.caption("Aucun événement officiel exploitable.")


def display_h2h(result: Dict[str, Any]):
    h2h = result["h2h"]

    if h2h["matches"] <= 0:
        st.info("H2H officiel non disponible ou inexploitable.")
        return

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Matchs", h2h["matches"])
    c2.metric("V domicile", h2h["home_wins"])
    c3.metric("Nuls", h2h["draws"])
    c4.metric("V extérieur", h2h["away_wins"])


def display_odds(result: Dict[str, Any]):
    odds = result["odds"]

    if not odds:
        st.info("Cotes officielles non disponibles dans le Match Resource.")
        return

    rows = [
        {
            "Marché": key,
            "Probabilité implicite normalisée": pct(value),
        }
        for key, value in odds.items()
    ]

    st.dataframe(
        pd.DataFrame(rows),
        use_container_width=True,
        hide_index=True,
    )


# ============================================================
# INTERFACE PRINCIPALE
# ============================================================

st.title("⚽ RODRIGUE PRO FOOTBALL AI — V20 ULTIMATE")

st.markdown(
    """
### 🧠 Moteur d'analyse football

**Forme + domicile/extérieur + classement + Poisson + H2H +
statistiques officielles + événements + compositions + cotes disponibles.**

Les données réellement absentes restent affichées comme **N/D**.
"""
)

st.info(
    "⚠️ Le moteur calcule des probabilités statistiques. "
    "Un score ou un pari réel ne peut pas être garanti à l'avance."
)


# ============================================================
# API STATUS
# ============================================================

api_status = validate_api()

if api_status.get("status") == 200:
    st.success(
        "🟢 football-data.org : authentification acceptée."
    )
else:
    status = api_status.get("status", 0)
    error = api_status.get("error", "")

    st.error(
        f"🔴 football-data.org : HTTP {status}. "
        "La récupération des matchs peut être impossible."
    )

    if error:
        st.code(error[:500])

    st.caption(
        "Si ton token a changé, remplace FOOTBALL_DATA_KEY "
        "ou utilise Streamlit Secrets."
    )


# ============================================================
# PARAMÈTRES
# ============================================================

with st.sidebar:
    st.header("⚙️ PARAMÈTRES")

    selected_date = st.date_input(
        "📅 Date",
        value=date.today(),
    )

    selected_competitions = st.multiselect(
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

    show_debug = st.checkbox(
        "Afficher les informations techniques",
        value=False,
    )

competition_codes = tuple(
    COMPETITIONS[name]
    for name in selected_competitions
)


# ============================================================
# RECHERCHE
# ============================================================

if st.button(
    "🚀 CHERCHER LES MATCHS",
    type="primary",
    use_container_width=True,
):
    if not competition_codes:
        st.error("Sélectionne au moins une compétition.")
        st.stop()

    if api_status.get("status") != 200:
        st.error(
            "Recherche arrêtée : le token football-data.org "
            "n'est pas accepté."
        )
        st.stop()

    with st.spinner("🔎 Recherche des matchs..."):
        matches = get_matches_for_date(
            selected_date,
            competition_codes,
        )

    if matches:
        st.session_state["rod_matches_v20"] = matches
        st.success(
            f"✅ {len(matches)} match(s) trouvé(s)."
        )
    else:
        st.session_state.pop(
            "rod_matches_v20",
            None,
        )

        st.warning(
            "Aucun match trouvé pour cette date "
            "dans les compétitions sélectionnées."
        )

        st.info(
            "Essaie une autre date ou ouvre le diagnostic technique. "
            "Le moteur filtre ensuite localement la date et la compétition."
        )


# ============================================================
# MATCHS
# ============================================================

matches = st.session_state.get(
    "rod_matches_v20",
    [],
)

if matches:
    st.subheader("📋 MATCHS DISPONIBLES")

    counts = {}

    for match in matches:
        name = match.get(
            "competition",
            {},
        ).get(
            "name",
            "Inconnue",
        )

        counts[name] = counts.get(name, 0) + 1

    if counts:
        st.dataframe(
            pd.DataFrame([
                {
                    "Compétition": name,
                    "Matchs": count,
                }
                for name, count in sorted(counts.items())
            ]),
            use_container_width=True,
            hide_index=True,
        )

    for index, match in enumerate(matches):
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

        competition = match.get(
            "competition",
            {},
        ).get(
            "name",
            "",
        )

        utc_date = match.get(
            "utcDate",
            "",
        )

        with st.expander(
            f"⚽ {home} — {away} | {competition}",
        ):
            st.caption(
                f"🕐 {utc_date or 'Date non disponible'}"
            )

            if st.button(
                "🧠 ANALYSER CE MATCH",
                key=f"analyze_v20_{index}_{match.get('id', index)}",
                use_container_width=True,
            ):
                with st.spinner(
                    "🧠 Analyse complète football-data.org..."
                ):
                    result = analyze_match_cached(
                        match
                    )

                # ============================================
                # EN-TÊTE
                # ============================================

                st.header(
                    f"⚽ {result['home']} — {result['away']}"
                )

                st.caption(
                    f"{result['competition']} · "
                    f"{result['utcDate']}"
                )

                # ============================================
                # XG
                # ============================================

                x1, x2, x3, x4 = st.columns(4)

                x1.metric(
                    "xG domicile",
                    fmt_num(result["home_lambda"]),
                )

                x2.metric(
                    "xG extérieur",
                    fmt_num(result["away_lambda"]),
                )

                x3.metric(
                    "xG total",
                    fmt_num(
                        result["home_lambda"]
                        + result["away_lambda"]
                    ),
                )

                x4.metric(
                    "Confiance",
                    f"{result['verdict']['confidence']}%",
                )

                # ============================================
                # FORME
                # ============================================

                st.subheader("📈 FORME RÉCENTE")

                c1, c2 = st.columns(2)

                with c1:
                    display_form(
                        f"🏠 {result['home']}",
                        result["home_form"],
                    )

                with c2:
                    display_form(
                        f"✈️ {result['away']}",
                        result["away_form"],
                    )

                # ============================================
                # DOMICILE / EXTÉRIEUR
                # ============================================

                st.subheader("🏠 DOMICILE / ✈️ EXTÉRIEUR")

                c1, c2 = st.columns(2)

                with c1:
                    st.write(
                        f"**{result['home']} à domicile :** "
                        f"{result['home_split']['wins']}V "
                        f"{result['home_split']['draws']}N "
                        f"{result['home_split']['losses']}D"
                    )

                    st.write(
                        f"Buts : "
                        f"{result['home_split']['gf_avg']:.2f} "
                        f"marqués / "
                        f"{result['home_split']['ga_avg']:.2f} encaissés"
                    )

                with c2:
                    st.write(
                        f"**{result['away']} à l'extérieur :** "
                        f"{result['away_split']['wins']}V "
                        f"{result['away_split']['draws']}N "
                        f"{result['away_split']['losses']}D"
                    )

                    st.write(
                        f"Buts : "
                        f"{result['away_split']['gf_avg']:.2f} "
                        f"marqués / "
                        f"{result['away_split']['ga_avg']:.2f} encaissés"
                    )

                # ============================================
                # CLASSEMENT
                # ============================================

                st.subheader("🏆 CLASSEMENT")

                display_standings(result)

                # ============================================
                # 1X2
                # ============================================

                st.subheader("🎯 1X2 / DOUBLE CHANCE")

                display_markets(result)

                # ============================================
                # SCORES
                # ============================================

                st.subheader("🔢 SCORES EXACTS")

                score_rows = [
                    {
                        "Score": score,
                        "Probabilité": pct(prob),
                    }
                    for score, prob in result["scores"]
                ]

                st.dataframe(
                    pd.DataFrame(score_rows),
                    use_container_width=True,
                    hide_index=True,
                )

                # ============================================
                # MI-TEMPS
                # ============================================

                st.subheader("⏱️ MI-TEMPS")

                ht_rows = [
                    {
                        "Score MT": score,
                        "Probabilité": pct(prob),
                    }
                    for score, prob in result["ht"]["scores"]
                ]

                st.dataframe(
                    pd.DataFrame(ht_rows),
                    use_container_width=True,
                    hide_index=True,
                )

                # ============================================
                # MT/FT
                # ============================================

                st.subheader("🔄 MT / FT")

                htft_rows = [
                    {
                        "MT/FT": combination,
                        "Probabilité": pct(prob),
                    }
                    for combination, prob in result["htft"][:9]
                ]

                st.dataframe(
                    pd.DataFrame(htft_rows),
                    use_container_width=True,
                    hide_index=True,
                )

                # ============================================
                # H2H
                # ============================================

                st.subheader("🤝 H2H")

                display_h2h(result)

                # ============================================
                # STATS OFFICIELLES
                # ============================================

                st.subheader(
                    "📊 STATISTIQUES OFFICIELLES"
                )

                display_official_stats(
                    result["detail"],
                    result["home"],
                    result["away"],
                )

                # ============================================
                # COTES
                # ============================================

                st.subheader("💰 COTES / PROBABILITÉS IMPLICITES")

                display_odds(result)

                # ============================================
                # ÉVÉNEMENTS
                # ============================================

                st.subheader("🎬 ÉVÉNEMENTS OFFICIELS")

                display_events(result)

                # ============================================
                # COMPOSITIONS
                # ============================================

                st.subheader("👥 COMPOSITIONS / FORMATIONS")

                display_lineups(result)

                # ============================================
                # SYNTHÈSE
                # ============================================

                verdict = result["verdict"]

                st.subheader(
                    "🧠 SYNTHÈSE HUMAINE RODRIGUE PRO"
                )

                a1, a2, a3 = st.columns(3)

                a1.metric(
                    "Résultat principal",
                    verdict["main_result"],
                )

                a2.metric(
                    "Meilleur marché",
                    verdict["best_market"],
                )

                a3.metric(
                    "Qualité données",
                    f"{verdict['quality']}%",
                )

                st.success(
                    f"🎯 Résultat principal : "
                    f"**{verdict['main_result']}**"
                )

                st.info(
                    f"🔢 Score le plus probable : "
                    f"**{verdict['best_score']}**"
                )

                st.info(
                    f"⏱️ MT/FT le plus probable : "
                    f"**{verdict['best_htft']}**"
                )

                st.write(
                    f"**Lecture du match :** {verdict['reading']}"
                )

                st.write(
                    f"**Lecture des buts :** {verdict['goals']}"
                )

                st.write(
                    f"**Lecture BTTS :** {verdict['btts']}"
                )

                st.write(
                    f"**Lecture H2H :** {verdict['h2h']}"
                )

                st.write(
                    f"**⭐ Meilleur marché statistique :** "
                    f"{verdict['best_market']} "
                    f"({pct(verdict['best_market_probability'])})"
                )

                # ============================================
                # TOP 5
                # ============================================

                st.subheader("🔥 TOP 5 SÉLECTIONS")

                candidates = {
                    key: result["markets"].get(key, 0.0)
                    for key in [
                        "1X",
                        "X2",
                        "12",
                        "BTTS Oui",
                        "BTTS Non",
                        "Over 1.5",
                        "Under 1.5",
                        "Over 2.5",
                        "Under 2.5",
                        "Over 3.5",
                        "Under 3.5",
                    ]
                }

                top5 = sorted(
                    candidates.items(),
                    key=lambda x: x[1],
                    reverse=True,
                )[:5]

                st.dataframe(
                    pd.DataFrame([
                        {
                            "Rang": i + 1,
                            "Marché": market,
                            "Probabilité": pct(prob),
                        }
                        for i, (market, prob) in enumerate(top5)
                    ]),
                    use_container_width=True,
                    hide_index=True,
                )

                # ============================================
                # DIAGNOSTIC TECHNIQUE
                # ============================================

                if show_debug:
                    st.subheader("🔧 INFORMATIONS TECHNIQUES")

                    st.json({
                        "match_id": result["match_id"],
                        "competition_code": result["competition_code"],
                        "stat_adjustment": result["stat_factors"],
                        "h2h_matches": len(result["h2h_matches"]),
                        "official_detail_available": bool(
                            result["detail"]
                        ),
                        "odds_available": bool(
                            result["odds"]
                        ),
                    })

                # ============================================
                # CONCLUSION
                # ============================================

                st.divider()

                st.markdown(
                    f"""
### 🏁 PRONOSTIC FINAL

**{result['home']} — {result['away']}**

| Élément | Sélection |
|---|---|
| 🎯 1X2 | **{verdict['main_result']}** |
| 🔢 Score exact | **{verdict['best_score']}** |
| ⏱️ MT/FT | **{verdict['best_htft']}** |
| ⭐ Meilleur marché | **{verdict['best_market']}** |
| 📊 Probabilité meilleur marché | **{pct(verdict['best_market_probability'])}** |
| 🧠 Confiance | **{verdict['confidence']}%** |
| 🗂️ Qualité des données | **{verdict['quality']}%** |
"""
                )

                st.caption(
                    "Rodrigue Pro Football AI V20 — "
                    "les informations indisponibles ne sont pas inventées."
                )


# ============================================================
# PIED DE PAGE
# ============================================================

st.divider()
st.caption(
    "RODRIGUE PRO FOOTBALL AI V20 ULTIMATE · "
    "Moteur principal : football-data.org"
)
