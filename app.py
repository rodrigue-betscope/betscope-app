# -*- coding: utf-8 -*-
"""
RODRIGUE PRO FOOTBALL AI V23 FIXED+
football-data.org v4 only.

Corrections:
- X-Auth-Token is always sent.
- Token is part of the API cache key.
- API cache can be reset.
- Fixed the Streamlit DeltaGenerator display bug:
  never pass st.success()/st.warning() into st.write(), st.help(), etc.
- Match search uses /matches with dateFrom/dateTo and local competition filtering.
- Search diagnostics show how many raw matches the API returned.
- Multi-season chronological backtest with full historical context.
- Poisson + Dixon-Coles + Bayesian shrinkage + home/away form.
- Half-time, HT/FT, exact scores, 1X2, double chance, BTTS, totals.
- No future data is used for a historical prediction.
- Probabilities are estimates, not guarantees.
"""
import math
import os
import time
from datetime import date

import numpy as np
import pandas as pd
import requests
import streamlit as st

API_BASE = "https://api.football-data.org/v4"

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

UA = "Rodrigue-Pro-Football-AI-V23"
st.set_page_config(
    page_title="Rodrigue Pro Football AI V23",
    page_icon="⚽",
    layout="wide",
)

S = requests.Session()
S.headers.update({"User-Agent": UA, "Accept": "application/json"})


# ============================================================
# UTILITAIRES
# ============================================================

def sf(x, d=None):
    try:
        x = float(x)
        return x if math.isfinite(x) else d
    except (TypeError, ValueError):
        return d


def clamp(x, a, b):
    x = sf(x, a)
    return max(a, min(b, x))


def pct(x):
    x = sf(x)
    return "N/D" if x is None else f"{100 * clamp(x, 0, 1):.1f}%"


def fmt(x):
    x = sf(x)
    return "N/D" if x is None else f"{x:.3f}"


def token_from_ui():
    try:
        secret = st.secrets.get("FOOTBALL_DATA_KEY", "")
    except Exception:
        secret = ""

    return str(
        secret
        or os.getenv("FOOTBALL_DATA_KEY", "")
        or st.session_state.get("api_key", "")
    ).strip()


# ============================================================
# API FOOTBALL-DATA.ORG
# ============================================================

def _get(ep, params=(), token=""):
    if not token:
        return {
            "status": 0,
            "data": None,
            "error": "Clé API absente",
            "remaining": "",
        }

    try:
        response = S.get(
            API_BASE + ep,
            headers={
                "X-Auth-Token": token,
                "Accept": "application/json",
                "User-Agent": UA,
            },
            params=dict(params),
            timeout=30,
        )

        try:
            payload = response.json()
        except Exception:
            payload = None

        if isinstance(payload, dict):
            message = payload.get("message") or payload.get("error") or ""
        else:
            message = response.text[:500]

        return {
            "status": response.status_code,
            "data": payload if response.status_code == 200 else None,
            "error": message,
            "remaining": response.headers.get(
                "X-Requests-Available-Minute", ""
            ),
        }

    except requests.RequestException as exc:
        return {
            "status": 0,
            "data": None,
            "error": str(exc),
            "remaining": "",
        }


@st.cache_data(ttl=180, show_spinner=False)
def api(ep, params=(), token=""):
    time.sleep(0.08)
    return _get(ep, params, token)


def data(ep, params=(), token=""):
    result = api(ep, params, token)
    return result["data"] if result["status"] == 200 else None


def api_message(result):
    status = result.get("status", 0)
    error = result.get("error") or "sans détail"

    known = {
        400: "HTTP 400 — paramètres de requête invalides.",
        401: "HTTP 401 — clé non authentifiée.",
        403: (
            "HTTP 403 — ressource restreinte : "
            "authentification, permissions ou plan."
        ),
        404: "HTTP 404 — ressource introuvable.",
        429: "HTTP 429 — quota dépassé.",
    }
    return known.get(status, f"HTTP {status} — {error}")


# ============================================================
# MATCH / HISTORIQUE
# ============================================================

def finished(match):
    full_time = match.get("score", {}).get("fullTime", {})
    return (
        match.get("status") == "FINISHED"
        and full_time.get("home") is not None
        and full_time.get("away") is not None
    )


def dkey(match):
    return match.get("utcDate", "")


def result_row(match, team_id):
    home_id = match.get("homeTeam", {}).get("id")
    away_id = match.get("awayTeam", {}).get("id")

    full_time = match.get("score", {}).get("fullTime", {})
    home_goals = full_time.get("home")
    away_goals = full_time.get("away")

    if home_goals is None or away_goals is None:
        return None

    if team_id == home_id:
        return {
            "gf": home_goals,
            "ga": away_goals,
            "venue": "H",
            "r": (
                "W" if home_goals > away_goals
                else "D" if home_goals == away_goals
                else "L"
            ),
        }

    if team_id == away_id:
        return {
            "gf": away_goals,
            "ga": home_goals,
            "venue": "A",
            "r": (
                "W" if away_goals > home_goals
                else "D" if away_goals == home_goals
                else "L"
            ),
        }

    return None


def rows_before(matches, team_id, before=None, venue=None, limit=60):
    output = []
    cutoff = before or "9999"

    for match in sorted(matches, key=dkey, reverse=True):
        if dkey(match) >= cutoff or not finished(match):
            continue

        row = result_row(match, team_id)

        if row and (venue is None or row["venue"] == venue):
            output.append({"date": dkey(match), **row})

            if len(output) >= limit:
                break

    return output


def stats(rows):
    if not rows:
        return {
            "n": 0,
            "wins": 0,
            "draws": 0,
            "losses": 0,
            "gf": 1.30,
            "ga": 1.30,
            "form": 0.50,
        }

    weights = np.array(
        [0.94 ** i for i in range(len(rows))],
        dtype=float,
    )
    gf = np.array([x["gf"] for x in rows], dtype=float)
    ga = np.array([x["ga"] for x in rows], dtype=float)
    points = np.array(
        [
            3 if x["r"] == "W"
            else 1 if x["r"] == "D"
            else 0
            for x in rows
        ],
        dtype=float,
    )

    return {
        "n": len(rows),
        "wins": int(sum(x["r"] == "W" for x in rows)),
        "draws": int(sum(x["r"] == "D" for x in rows)),
        "losses": int(sum(x["r"] == "L" for x in rows)),
        "gf": float(np.average(gf, weights=weights)),
        "ga": float(np.average(ga, weights=weights)),
        "form": float(np.average(points / 3.0, weights=weights)),
    }


@st.cache_data(ttl=1800, show_spinner=False)
def competition_info(code, token):
    return data(f"/competitions/{code}", (), token) or {}


@st.cache_data(ttl=900, show_spinner=False)
def season_matches(code, year, token):
    payload = data(
        f"/competitions/{code}/matches",
        (("season", str(year)),),
        token,
    ) or {}
    return payload.get("matches", [])


@st.cache_data(ttl=900, show_spinner=False)
def h2h(match_id, token):
    payload = data(
        f"/matches/{match_id}/head2head",
        (("limit", "10"),),
        token,
    ) or {}
    return payload.get("matches", [])


def seasons(code, token):
    info = competition_info(code, token)
    years = []

    for season in info.get("seasons", []):
        start = str(season.get("startDate", ""))
        if len(start) >= 4:
            try:
                years.append(int(start[:4]))
            except ValueError:
                pass

    current = str(info.get("currentSeason", {}).get("startDate", ""))
    if len(current) >= 4:
        try:
            years.append(int(current[:4]))
        except ValueError:
            pass

    return sorted(set(years), reverse=True)


# ============================================================
# STATISTIQUES DE LIGUE
# ============================================================

def league_stats(matches, before=None):
    finished_matches = [
        m
        for m in matches
        if finished(m) and (before is None or dkey(m) < before)
    ]

    if not finished_matches:
        return {
            "n": 0,
            "home_g": 1.45,
            "away_g": 1.15,
            "total_g": 2.60,
            "ht_ratio": 0.44,
            "draw": 0.27,
        }

    home_goals = []
    away_goals = []
    ht_goals = []
    draws = 0

    for match in finished_matches:
        full = match["score"]["fullTime"]
        hg = full["home"]
        ag = full["away"]

        home_goals.append(hg)
        away_goals.append(ag)

        if hg == ag:
            draws += 1

        half = match.get("score", {}).get("halfTime", {})
        if half.get("home") is not None and half.get("away") is not None:
            ht_goals.append(half["home"] + half["away"])

    total_goals = float(
        np.mean(np.array(home_goals) + np.array(away_goals))
    )

    ratio = (
        float(np.mean(ht_goals)) / total_goals
        if ht_goals and total_goals > 0
        else 0.44
    )

    return {
        "n": len(home_goals),
        "home_g": float(np.mean(home_goals)),
        "away_g": float(np.mean(away_goals)),
        "total_g": total_goals,
        "ht_ratio": clamp(ratio, 0.35, 0.55),
        "draw": draws / max(len(home_goals), 1),
    }


# ============================================================
# POISSON / DIXON-COLES
# ============================================================

def pois(lam, k):
    lam = sf(lam)
    k = int(k)

    if lam is None or lam < 0 or k < 0:
        return 0.0

    if lam == 0:
        return 1.0 if k == 0 else 0.0

    try:
        value = math.exp(
            -lam
            + k * math.log(lam)
            - math.lgamma(k + 1)
        )
        return clamp(value, 0.0, 1.0)
    except (ValueError, OverflowError):
        return 0.0


def matrix(home_lambda, away_lambda, n=8):
    home = np.array(
        [pois(home_lambda, i) for i in range(n + 1)]
    )
    away = np.array(
        [pois(away_lambda, i) for i in range(n + 1)]
    )

    mat = np.outer(home, away)
    total = mat.sum()

    if total > 0:
        return mat / total

    return np.zeros_like(mat)


def dc(mat, home_lambda, away_lambda, rho=-0.055):
    output = mat.copy()

    corrections = {
        (0, 0): 1 - home_lambda * away_lambda * rho,
        (0, 1): 1 + home_lambda * rho,
        (1, 0): 1 + away_lambda * rho,
        (1, 1): 1 - rho,
    }

    for (home_goals, away_goals), factor in corrections.items():
        if (
            home_goals < output.shape[0]
            and away_goals < output.shape[1]
        ):
            output[home_goals, away_goals] *= clamp(
                factor, 0.90, 1.10
            )

    output = np.maximum(output, 0)
    total = output.sum()

    return output / total if total > 0 else output


# ============================================================
# MARCHES
# ============================================================

def markets(mat):
    result = {
        "1": 0.0,
        "X": 0.0,
        "2": 0.0,
        "BTTS Oui": 0.0,
        "Over 1.5": 0.0,
        "Over 2.5": 0.0,
        "Over 3.5": 0.0,
    }

    for home_goals in range(mat.shape[0]):
        for away_goals in range(mat.shape[1]):
            p = float(mat[home_goals, away_goals])

            if home_goals > away_goals:
                result["1"] += p
            elif home_goals == away_goals:
                result["X"] += p
            else:
                result["2"] += p

            if home_goals > 0 and away_goals > 0:
                result["BTTS Oui"] += p

            if home_goals + away_goals >= 2:
                result["Over 1.5"] += p

            if home_goals + away_goals >= 3:
                result["Over 2.5"] += p

            if home_goals + away_goals >= 4:
                result["Over 3.5"] += p

    result["1X"] = result["1"] + result["X"]
    result["X2"] = result["X"] + result["2"]
    result["12"] = result["1"] + result["2"]
    result["BTTS Non"] = 1 - result["BTTS Oui"]

    for line in ("1.5", "2.5", "3.5"):
        result["Under " + line] = 1 - result["Over " + line]

    return result


def scores(mat, n=10):
    values = [
        (f"{h}-{a}", float(mat[h, a]))
        for h in range(mat.shape[0])
        for a in range(mat.shape[1])
    ]

    return sorted(
        values,
        key=lambda z: z[1],
        reverse=True,
    )[:n]


# ============================================================
# FORCES DES EQUIPES
# ============================================================

def strength(rows, league, venue=None):
    current = stats(rows)
    n = current["n"]
    prior = 6.0

    if venue == "H":
        prior_gf = league["home_g"]
        prior_ga = league["away_g"]
    elif venue == "A":
        prior_gf = league["away_g"]
        prior_ga = league["home_g"]
    else:
        prior_gf = league["total_g"] / 2
        prior_ga = league["total_g"] / 2

    gf = (
        n * current["gf"] + prior * prior_gf
    ) / (n + prior)

    ga = (
        n * current["ga"] + prior * prior_ga
    ) / (n + prior)

    return gf, ga, current


def lambdas(home_rows, away_rows, home_home_rows, away_away_rows, league):
    home_gf, home_ga, home_stats = strength(
        home_rows, league
    )
    away_gf, away_ga, away_stats = strength(
        away_rows, league
    )

    home_gf_home, home_ga_home, _ = strength(
        home_home_rows, league, "H"
    )
    away_gf_away, away_ga_away, _ = strength(
        away_away_rows, league, "A"
    )

    league_home = max(league["home_g"], 0.25)
    league_away = max(league["away_g"], 0.20)
    league_avg = max(league["total_g"] / 2, 0.20)

    home_attack = (
        0.58 * home_gf_home / league_home
        + 0.42 * away_gf / league_avg
    )

    home_defense = (
        0.58 * away_ga_away / league_away
        + 0.42 * home_ga / league_avg
    )

    away_attack = (
        0.58 * away_gf_away / league_away
        + 0.42 * away_gf / league_avg
    )

    away_defense = (
        0.58 * home_ga_home / league_home
        + 0.42 * away_ga / league_avg
    )

    home_lambda = league_home * math.sqrt(
        max(home_attack, 0.20)
        * max(home_defense, 0.20)
    )

    away_lambda = league_away * math.sqrt(
        max(away_attack, 0.20)
        * max(away_defense, 0.20)
    )

    # Forme récente : correction faible et bornée.
    home_lambda *= clamp(
        0.93 + 0.14 * home_stats["form"],
        0.90,
        1.07,
    )

    away_lambda *= clamp(
        0.93 + 0.14 * away_stats["form"],
        0.90,
        1.07,
    )

    return (
        clamp(home_lambda, 0.20, 3.80),
        clamp(away_lambda, 0.15, 3.50),
    )


# ============================================================
# H2H / MI-TEMPS / MT-FT
# ============================================================

def h2h_signal(matches, home_id, away_id):
    home_wins = 0
    draws = 0
    away_wins = 0

    for match in matches:
        if not finished(match):
            continue

        full = match["score"]["fullTime"]
        match_home = match.get("homeTeam", {}).get("id")
        match_away = match.get("awayTeam", {}).get("id")

        if match_home == home_id and match_away == away_id:
            x, y = full["home"], full["away"]
        elif match_home == away_id and match_away == home_id:
            x, y = full["away"], full["home"]
        else:
            continue

        if x > y:
            home_wins += 1
        elif x == y:
            draws += 1
        else:
            away_wins += 1

    total = home_wins + draws + away_wins

    return {
        "n": total,
        "home": home_wins / total if total else 0.50,
        "away": away_wins / total if total else 0.25,
        "draw": draws / total if total else 0.25,
        "hw": home_wins,
        "dr": draws,
        "aw": away_wins,
    }


def apply_h2h(mat, h2h_data):
    if h2h_data["n"] < 4:
        return mat

    adjustment = clamp(
        (h2h_data["home"] - h2h_data["away"]) * 0.035,
        -0.025,
        0.025,
    )

    output = mat.copy()

    for h in range(output.shape[0]):
        for a in range(output.shape[1]):
            if h > a:
                output[h, a] *= 1 + adjustment
            elif h < a:
                output[h, a] *= 1 - adjustment

    return output / output.sum()


def ht_model(home_lambda, away_lambda, league):
    ratio = clamp(
        league.get("ht_ratio", 0.44),
        0.35,
        0.55,
    )

    home_ht = home_lambda * ratio
    away_ht = away_lambda * ratio

    return dc(
        matrix(home_ht, away_ht, 6),
        home_ht,
        away_ht,
    )


def htft(ht, ft):
    ht_markets = markets(ht)
    ft_markets = markets(ft)

    transitions = {
        "1": {"1": 0.74, "X": 0.16, "2": 0.10},
        "X": {"1": 0.27, "X": 0.48, "2": 0.25},
        "2": {"1": 0.10, "X": 0.16, "2": 0.74},
    }

    output = {
        f"{x}/{y}": ht_markets[x] * transitions[x][y]
        for x in "1X2"
        for y in "1X2"
    }

    for y in "1X2":
        total = sum(
            output[f"{x}/{y}"]
            for x in "1X2"
        )

        if total > 0:
            for x in "1X2":
                output[f"{x}/{y}"] *= (
                    ft_markets[y] / total
                )

    return sorted(
        output.items(),
        key=lambda z: z[1],
        reverse=True,
    )


# ============================================================
# ANALYSE D'UN MATCH
# ============================================================

def analyze(match, token):
    competition_code = (
        match.get("competition", {}).get("code", "")
    )

    season_start = str(
        match.get("season", {}).get("startDate", "")
    )

    try:
        year = int(season_start[:4])
    except (TypeError, ValueError):
        year = date.today().year

    all_matches = season_matches(
        competition_code,
        year,
        token,
    )

    before = dkey(match)
    home_id = match["homeTeam"]["id"]
    away_id = match["awayTeam"]["id"]

    league = league_stats(
        all_matches,
        before,
    )

    home_rows = rows_before(
        all_matches,
        home_id,
        before,
        None,
        60,
    )

    away_rows = rows_before(
        all_matches,
        away_id,
        before,
        None,
        60,
    )

    home_home_rows = rows_before(
        all_matches,
        home_id,
        before,
        "H",
        20,
    )

    away_away_rows = rows_before(
        all_matches,
        away_id,
        before,
        "A",
        20,
    )

    home_lambda, away_lambda = lambdas(
        home_rows,
        away_rows,
        home_home_rows,
        away_away_rows,
        league,
    )

    full_time = dc(
        matrix(home_lambda, away_lambda),
        home_lambda,
        away_lambda,
    )

    h2h_data = h2h_signal(
        h2h(match["id"], token),
        home_id,
        away_id,
    )

    full_time = apply_h2h(
        full_time,
        h2h_data,
    )

    half_time = ht_model(
        home_lambda,
        away_lambda,
        league,
    )

    market = markets(full_time)

    quality = int(
        clamp(
            35
            + min(league["n"], 100) * 0.15
            + min(
                min(len(home_rows), len(away_rows)),
                20,
            ) * 1.2
            + (8 if h2h_data["n"] >= 5 else 0),
            0,
            85,
        )
    )

    sorted_1x2 = sorted(
        [
            market["1"],
            market["X"],
            market["2"],
        ],
        reverse=True,
    )

    confidence = int(
        clamp(
            50
            + 30 * (sorted_1x2[0] - sorted_1x2[1])
            + 0.25 * quality,
            50,
            90,
        )
    )

    principal = max(
        (
            ("1", market["1"]),
            ("X", market["X"]),
            ("2", market["2"]),
        ),
        key=lambda z: z[1],
    )

    return {
        "home": match["homeTeam"]["name"],
        "away": match["awayTeam"]["name"],
        "competition": match["competition"]["name"],
        "date": before,
        "status": match.get("status", ""),
        "hl": home_lambda,
        "al": away_lambda,
        "league": league,
        "hs": stats(home_rows),
        "as": stats(away_rows),
        "h2": h2h_data,
        "mk": market,
        "scores": scores(full_time),
        "htscores": scores(half_time, 8),
        "htft": htft(half_time, full_time),
        "quality": quality,
        "confidence": confidence,
        "one": principal,
    }


# ============================================================
# BACKTEST
# ============================================================

def outcome(match):
    full = match["score"]["fullTime"]

    if full["home"] > full["away"]:
        return 0

    if full["home"] == full["away"]:
        return 1

    return 2


def brier(probabilities, target):
    return float(
        sum(
            (
                probabilities[i]
                - (1 if i == target else 0)
            ) ** 2
            for i in range(3)
        )
    )


def logloss(probabilities, target):
    return float(
        -math.log(
            clamp(
                probabilities[target],
                1e-7,
                1,
            )
        )
    )


def predict_from_history(history, match):
    before = dkey(match)
    home_id = match["homeTeam"]["id"]
    away_id = match["awayTeam"]["id"]

    league = league_stats(
        history,
        before,
    )

    home_rows = rows_before(
        history,
        home_id,
        before,
        None,
        60,
    )

    away_rows = rows_before(
        history,
        away_id,
        before,
        None,
        60,
    )

    home_home_rows = rows_before(
        history,
        home_id,
        before,
        "H",
        20,
    )

    away_away_rows = rows_before(
        history,
        away_id,
        before,
        "A",
        20,
    )

    if len(home_rows) < 3 or len(away_rows) < 3:
        return None

    home_lambda, away_lambda = lambdas(
        home_rows,
        away_rows,
        home_home_rows,
        away_away_rows,
        league,
    )

    mat = dc(
        matrix(home_lambda, away_lambda),
        home_lambda,
        away_lambda,
    )

    market = markets(mat)

    return (
        np.array(
            [
                market["1"],
                market["X"],
                market["2"],
            ]
        ),
        market,
        home_lambda,
        away_lambda,
        league,
    )


def run_backtest(
    code,
    year,
    token,
    max_eval=220,
    warmup=30,
):
    all_matches = sorted(
        [
            m
            for m in season_matches(
                code,
                year,
                token,
            )
            if finished(m)
        ],
        key=dkey,
    )

    if len(all_matches) <= warmup:
        return {
            "status": "insufficient",
            "n": 0,
            "available": len(all_matches),
            "message": (
                "Pas assez de matchs historiques "
                "après la période de warm-up."
            ),
        }

    evaluations = all_matches[warmup:]

    if len(evaluations) > max_eval:
        evaluations = evaluations[-max_eval:]

    predictions = []
    targets = []

    brier_values = []
    logloss_values = []

    baseline_brier = []
    baseline_logloss = []

    over25_hits = 0
    over25_n = 0

    btts_hits = 0
    btts_n = 0

    exact_hits = 0

    for match in evaluations:
        history = [
            x
            for x in all_matches
            if dkey(x) < dkey(match)
        ]

        if len(history) < warmup:
            continue

        prediction = predict_from_history(
            history,
            match,
        )

        if prediction is None:
            continue

        probabilities, market, home_lambda, away_lambda, league = prediction

        target = outcome(match)

        predictions.append(probabilities)
        targets.append(target)

        brier_values.append(
            brier(probabilities, target)
        )

        logloss_values.append(
            logloss(probabilities, target)
        )

        draw_rate = clamp(
            league["draw"],
            0.15,
            0.40,
        )

        # Baseline volontairement simple.
        baseline = np.array(
            [
                0.45 * (1 - draw_rate),
                draw_rate,
                0.55 * (1 - draw_rate),
            ]
        )

        baseline_brier.append(
            brier(baseline, target)
        )

        baseline_logloss.append(
            logloss(baseline, target)
        )

        full = match["score"]["fullTime"]

        actual_over25 = (
            full["home"] + full["away"] >= 3
        )

        over25_hits += (
            market["Over 2.5"] >= 0.50
        ) == actual_over25
        over25_n += 1

        actual_btts = (
            full["home"] > 0
            and full["away"] > 0
        )

        btts_hits += (
            market["BTTS Oui"] >= 0.50
        ) == actual_btts
        btts_n += 1

        top_score = scores(
            dc(
                matrix(
                    home_lambda,
                    away_lambda,
                ),
                home_lambda,
                away_lambda,
            ),
            1,
        )[0][0]

        actual_score = (
            f'{full["home"]}-{full["away"]}'
        )

        exact_hits += top_score == actual_score

    n = len(targets)

    if not n:
        return {
            "status": "insufficient",
            "n": 0,
            "available": len(all_matches),
            "message": (
                "Pas assez de matchs exploitables "
                "pour calculer le backtest."
            ),
        }

    prediction_array = np.array(predictions)
    target_array = np.array(targets)

    accuracy = float(
        np.mean(
            np.argmax(prediction_array, axis=1)
            == target_array
        )
    )

    brier_score = float(np.mean(brier_values))
    logloss_score = float(np.mean(logloss_values))

    base_brier = float(np.mean(baseline_brier))
    base_logloss = float(np.mean(baseline_logloss))

    brier_gain = (
        1 - brier_score / max(base_brier, 1e-9)
    )

    logloss_gain = (
        1 - logloss_score / max(base_logloss, 1e-9)
    )

    if n < 50:
        reliability = "INSUFFISANTE"
    elif n < 150:
        reliability = "LIMITEE"
    elif not (
        brier_score < base_brier
        and logloss_score < base_logloss
    ):
        reliability = "A AMELIORER"
    else:
        reliability = "SOLIDE"

    return {
        "status": "ok",
        "n": n,
        "available": len(all_matches),
        "accuracy": accuracy,
        "brier": brier_score,
        "logloss": logloss_score,
        "baseline_brier": base_brier,
        "baseline_logloss": base_logloss,
        "brier_gain": brier_gain,
        "logloss_gain": logloss_gain,
        "over25": over25_hits / max(over25_n, 1),
        "btts": btts_hits / max(btts_n, 1),
        "exact": exact_hits / max(n, 1),
        "reliability": reliability,
    }


def multi_backtest(
    code,
    years,
    token,
    max_eval=220,
    warmup=30,
):
    results = []

    for year in years:
        results.append(
            {
                **run_backtest(
                    code,
                    int(year),
                    token,
                    max_eval,
                    warmup,
                ),
                "season": int(year),
            }
        )

    valid = [
        result
        for result in results
        if result.get("status") == "ok"
    ]

    total_n = sum(
        result["n"]
        for result in valid
    )

    if not valid:
        return {
            "seasons": results,
            "aggregate": None,
        }

    def weighted(key):
        return sum(
            result[key] * result["n"]
            for result in valid
        ) / total_n

    aggregate = {
        "n": total_n,
        "accuracy": weighted("accuracy"),
        "brier": weighted("brier"),
        "logloss": weighted("logloss"),
        "baseline_brier": weighted("baseline_brier"),
        "baseline_logloss": weighted("baseline_logloss"),
        "brier_gain": weighted("brier_gain"),
        "logloss_gain": weighted("logloss_gain"),
        "over25": weighted("over25"),
        "btts": weighted("btts"),
        "exact": weighted("exact"),
    }

    if total_n < 50:
        reliability = "INSUFFISANTE"
    elif total_n < 150:
        reliability = "LIMITEE"
    elif total_n < 500:
        reliability = "MOYENNE"
    elif (
        aggregate["brier"] < aggregate["baseline_brier"]
        and aggregate["logloss"] < aggregate["baseline_logloss"]
    ):
        reliability = "SOLIDE"
    else:
        reliability = "A AMELIORER"

    aggregate["reliability"] = reliability

    return {
        "seasons": results,
        "aggregate": aggregate,
    }


# ============================================================
# RECHERCHE DES MATCHS — VERSION CORRIGEE
# ============================================================

def find_matches(day, codes, token):
    """
    Recherche les matchs de la journée via /matches.

    Important:
    - on récupère d'abord les matchs de la date;
    - on filtre ensuite localement par compétition;
    - on ne fait jamais st.success()/st.warning() dans st.write().
    """

    payload = data(
        "/matches",
        (
            ("dateFrom", day.isoformat()),
            ("dateTo", day.isoformat()),
        ),
        token,
    ) or {}

    raw_matches = payload.get("matches", [])
    wanted = set(codes)

    selected = [
        match
        for match in raw_matches
        if match.get("competition", {}).get("code") in wanted
    ]

    selected.sort(key=dkey)

    return selected, {
        "raw_count": len(raw_matches),
        "selected_count": len(selected),
    }


# ============================================================
# CACHE
# ============================================================

def clear_cache():
    try:
        st.cache_data.clear()
    except Exception:
        pass


# ============================================================
# INTERFACE
# ============================================================

st.title(
    "⚽ RODRIGUE PRO FOOTBALL AI — V23 FIXED+"
)

st.caption(
    "football-data.org v4 · validation chronologique · "
    "anti-fuite · Poisson/Dixon-Coles · multi-saisons. "
    "Les probabilités sont des estimations, pas des garanties."
)


with st.sidebar:
    st.header("🔐 API football-data.org")

    st.text_input(
        "Clé API",
        type="password",
        key="api_key",
        help="Ta clé reste dans la session Streamlit.",
    )

    token = token_from_ui()

    if st.button(
        "🔄 Réinitialiser le cache API",
        use_container_width=True,
    ):
        clear_cache()
        st.rerun()


if not token:
    st.warning(
        "⚠️ Entre ta clé API football-data.org "
        "dans la barre latérale."
    )

else:
    status = api(
        "/competitions/PL",
        (),
        token,
    )

    if status["status"] == 200:
        st.success(
            "🟢 API OK · appels restants : "
            + str(status.get("remaining") or "N/D")
        )
    else:
        st.error(
            api_message(status)
            + " · "
            + str(status.get("error") or "")
        )

    c1, c2 = st.columns(2)

    with c1:
        day = st.date_input(
            "📅 Date",
            date.today(),
        )

    with c2:
        names = st.multiselect(
            "🏆 Compétitions",
            list(COMPETITIONS),
            default=[
                "Premier League",
                "LaLiga",
                "Bundesliga",
            ],
        )

    codes = [
        COMPETITIONS[name]
        for name in names
    ]

    # --------------------------------------------------------
    # RECHERCHE
    # --------------------------------------------------------

    if st.button(
        "🚀 CHERCHER LES MATCHS",
        type="primary",
        use_container_width=True,
    ):
        if status["status"] != 200:
            st.error(
                "🔴 Recherche arrêtée : "
                "API/token indisponible."
            )

        elif not codes:
            st.warning(
                "⚠️ Sélectionne au moins une compétition."
            )

        else:
            with st.spinner(
                "🔎 Recherche des matchs..."
            ):
                matches, diagnostic = find_matches(
                    day,
                    codes,
                    token,
                )

            st.session_state["matches_v23"] = matches
            st.session_state["search_diag_v23"] = diagnostic

            # IMPORTANT :
            # Ne PAS écrire st.success()/st.warning() dans st.write().
            # Cela évite l'affichage DeltaGenerator.
            if matches:
                st.success(
                    f"✅ {len(matches)} match(s) trouvé(s) "
                    f"pour le {day.strftime('%d/%m/%Y')}."
                )
            else:
                st.warning(
                    f"⚠️ Aucun match trouvé pour le "
                    f"{day.strftime('%d/%m/%Y')} "
                    f"dans les compétitions sélectionnées."
                )

                st.caption(
                    "Diagnostic : "
                    f"{diagnostic['raw_count']} match(s) "
                    "brut(s) retourné(s) par l'API avant "
                    "filtrage des compétitions."
                )

    # --------------------------------------------------------
    # DIAGNOSTIC DE LA DERNIERE RECHERCHE
    # --------------------------------------------------------

    diagnostic = st.session_state.get(
        "search_diag_v23"
    )

    if diagnostic:
        with st.expander(
            "🔍 Diagnostic de recherche",
            expanded=False,
        ):
            st.write(
                "Matchs bruts retournés par l'API :",
                diagnostic["raw_count"],
            )
            st.write(
                "Matchs après filtrage des compétitions :",
                diagnostic["selected_count"],
            )

    # --------------------------------------------------------
    # ANALYSE DES MATCHS
    # --------------------------------------------------------

    for index, match in enumerate(
        st.session_state.get(
            "matches_v23",
            [],
        )
    ):
        home = match.get(
            "homeTeam",
            {},
        ).get("name", "?")

        away = match.get(
            "awayTeam",
            {},
        ).get("name", "?")

        match_id = match.get(
            "id",
            index,
        )

        competition = match.get(
            "competition",
            {},
        ).get("name", "")

        with st.expander(
            f"⚽ {home} — {away} | {competition}"
        ):
            st.caption(
                f'{match.get("status", "")} · '
                f'{match.get("utcDate", "")}'
            )

            if st.button(
                "🧠 ANALYSER CE MATCH",
                key=f"ana_v23_{match_id}",
                use_container_width=True,
            ):
                try:
                    with st.spinner(
                        "🧠 Analyse chronologique..."
                    ):
                        st.session_state[
                            f"res_v23_{match_id}"
                        ] = analyze(
                            match,
                            token,
                        )

                    st.session_state[
                        f"err_v23_{match_id}"
                    ] = ""

                except Exception as exc:
                    st.session_state[
                        f"err_v23_{match_id}"
                    ] = str(exc)

            error = st.session_state.get(
                f"err_v23_{match_id}",
                "",
            )

            if error:
                st.error(
                    "Erreur pendant l'analyse : "
                    + error
                )

            result = st.session_state.get(
                f"res_v23_{match_id}"
            )

            if result:
                q1, q2, q3, q4 = st.columns(4)

                q1.metric(
                    "xG modèle",
                    f'{result["hl"]:.2f} — '
                    f'{result["al"]:.2f}',
                )

                q2.metric(
                    "Qualité données",
                    f'{result["quality"]}/85',
                )

                q3.metric(
                    "Confiance modèle",
                    f'{result["confidence"]}%',
                )

                q4.metric(
                    "H2H",
                    str(result["h2"]["n"]),
                )

                st.info(
                    "ℹ️ La confiance modèle mesure la "
                    "qualité/séparation du modèle. "
                    "Elle n'est pas une garantie de gain."
                )

                st.success(
                    f'🎯 1X2 principal : '
                    f'**{result["one"][0]}** '
                    f'({pct(result["one"][1])})'
                )

                st.subheader(
                    "📈 FORME RÉCENTE"
                )

                form_table = pd.DataFrame(
                    [
                        {
                            "Équipe": result["home"],
                            "Matchs": result["hs"]["n"],
                            "V": result["hs"]["wins"],
                            "N": result["hs"]["draws"],
                            "D": result["hs"]["losses"],
                            "GF/m": fmt(result["hs"]["gf"]),
                            "GA/m": fmt(result["hs"]["ga"]),
                        },
                        {
                            "Équipe": result["away"],
                            "Matchs": result["as"]["n"],
                            "V": result["as"]["wins"],
                            "N": result["as"]["draws"],
                            "D": result["as"]["losses"],
                            "GF/m": fmt(result["as"]["gf"]),
                            "GA/m": fmt(result["as"]["ga"]),
                        },
                    ]
                )

                st.dataframe(
                    form_table,
                    use_container_width=True,
                    hide_index=True,
                )

                st.subheader(
                    "🎯 MARCHÉS"
                )

                market_keys = [
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
                ]

                market_table = pd.DataFrame(
                    [
                        {
                            "Marché": key,
                            "Probabilité modèle": pct(
                                result["mk"][key]
                            ),
                        }
                        for key in market_keys
                    ]
                )

                st.dataframe(
                    market_table,
                    use_container_width=True,
                    hide_index=True,
                )

                st.subheader(
                    "🔢 SCORES EXACTS"
                )

                score_table = pd.DataFrame(
                    [
                        {
                            "Score": score,
                            "Probabilité": pct(probability),
                        }
                        for score, probability
                        in result["scores"]
                    ]
                )

                st.dataframe(
                    score_table,
                    use_container_width=True,
                    hide_index=True,
                )

                st.subheader(
                    "⏱️ MI-TEMPS"
                )

                ht_table = pd.DataFrame(
                    [
                        {
                            "Score MT": score,
                            "Probabilité": pct(probability),
                        }
                        for score, probability
                        in result["htscores"]
                    ]
                )

                st.dataframe(
                    ht_table,
                    use_container_width=True,
                    hide_index=True,
                )

                st.subheader(
                    "🔄 MT / FT"
                )

                htft_table = pd.DataFrame(
                    [
                        {
                            "MT/FT": combination,
                            "Probabilité": pct(probability),
                        }
                        for combination, probability
                        in result["htft"]
                    ]
                )

                st.dataframe(
                    htft_table,
                    use_container_width=True,
                    hide_index=True,
                )

    # --------------------------------------------------------
    # BACKTEST
    # --------------------------------------------------------

    st.divider()

    st.subheader(
        "🧪 BACKTEST INTELLIGENT — MULTI-SAISONS"
    )

    b1, b2, b3 = st.columns(3)

    with b1:
        backtest_name = st.selectbox(
            "Compétition",
            list(COMPETITIONS),
            key="btc_v23",
        )

    backtest_code = COMPETITIONS[backtest_name]

    available_years = seasons(
        backtest_code,
        token,
    )

    previous_years = [
        year
        for year in available_years
        if year < date.today().year
    ][:5]

    with b2:
        selected_years = st.multiselect(
            "Saisons",
            available_years,
            default=previous_years,
            key="bty_v23",
        )

    with b3:
        limit_per_season = st.number_input(
            "Matchs max / saison",
            min_value=50,
            max_value=500,
            value=220,
            step=10,
            key="btl_v23",
        )

    st.info(
        "📌 Pour une validation sérieuse, utilise plusieurs "
        "saisons. Une saison récente avec quelques matchs "
        "ne permet pas de conclure."
    )

    if st.button(
        "🧪 LANCER LE BACKTEST MULTI-SAISONS",
        use_container_width=True,
    ):
        if not selected_years:
            st.warning(
                "⚠️ Sélectionne au moins une saison."
            )
        else:
            with st.spinner(
                "⏳ Backtest chronologique "
                "sans données futures..."
            ):
                st.session_state["bt_v23"] = multi_backtest(
                    backtest_code,
                    selected_years,
                    token,
                    int(limit_per_season),
                    30,
                )

    backtest_result = st.session_state.get(
        "bt_v23"
    )

    if backtest_result:
        aggregate = backtest_result.get(
            "aggregate"
        )

        if aggregate:
            reliability = aggregate["reliability"]

            if reliability == "SOLIDE":
                st.success(
                    f'🟢 Validation SOLIDE · '
                    f'{aggregate["n"]} matchs'
                )
            elif aggregate["n"] < 150:
                st.warning(
                    f'🟠 Échantillon encore limité · '
                    f'{aggregate["n"]} matchs'
                )
            else:
                st.warning(
                    f'🟠 Résultat : {reliability} · '
                    f'{aggregate["n"]} matchs'
                )

            backtest_table = pd.DataFrame(
                [
                    {
                        "Matchs": aggregate["n"],
                        "Accuracy 1X2": pct(
                            aggregate["accuracy"]
                        ),
                        "Brier ↓": fmt(
                            aggregate["brier"]
                        ),
                        "Baseline Brier ↓": fmt(
                            aggregate["baseline_brier"]
                        ),
                        "Gain Brier": pct(
                            aggregate["brier_gain"]
                        ),
                        "Log loss ↓": fmt(
                            aggregate["logloss"]
                        ),
                        "Baseline Log loss ↓": fmt(
                            aggregate["baseline_logloss"]
                        ),
                        "Gain Log loss": pct(
                            aggregate["logloss_gain"]
                        ),
                        "Over 2.5": pct(
                            aggregate["over25"]
                        ),
                        "BTTS": pct(
                            aggregate["btts"]
                        ),
                        "Score exact top-1": pct(
                            aggregate["exact"]
                        ),
                        "Validation": reliability,
                    }
                ]
            )

            st.dataframe(
                backtest_table,
                use_container_width=True,
                hide_index=True,
            )

        else:
            st.warning(
                "⚠️ Aucune saison ne contient assez "
                "de données exploitables."
            )

        season_results = backtest_result.get(
            "seasons",
            [],
        )

        if season_results:
            st.subheader(
                "📚 Détail par saison"
            )

            detail_rows = []

            for result in season_results:
                row = {
                    "Saison": result.get("season"),
                    "Matchs disponibles": result.get(
                        "available",
                        0,
                    ),
                    "Matchs évalués": result.get(
                        "n",
                        0,
                    ),
                    "Statut": result.get(
                        "reliability",
                        result.get("status", ""),
                    ),
                }

                if result.get("status") == "ok":
                    row.update(
                        {
                            "Accuracy": pct(
                                result["accuracy"]
                            ),
                            "Brier": fmt(
                                result["brier"]
                            ),
                            "Log loss": fmt(
                                result["logloss"]
                            ),
                            "Over 2.5": pct(
                                result["over25"]
                            ),
                            "BTTS": pct(
                                result["btts"]
                            ),
                            "Exact top-1": pct(
                                result["exact"]
                            ),
                        }
                    )

                detail_rows.append(row)

            st.dataframe(
                pd.DataFrame(detail_rows),
                use_container_width=True,
                hide_index=True,
            )

st.divider()

st.caption(
    "Data provided by football-data.org · "
    "RODRIGUE PRO FOOTBALL AI V23 FIXED+ · "
    "Les statistiques historiques servent à évaluer "
    "le modèle et ne transforment pas une probabilité "
    "en certitude."
)

# ============================================================
# AUDIT TECHNIQUE V23
# ============================================================
#
# 01. AUTHENTIFICATION
#     Chaque appel API passe X-Auth-Token.
#
# 02. CACHE
#     Le token fait partie des arguments de api(), donc un
#     changement de clé ne réutilise pas une ancienne réponse.
#
# 03. DELTAGENERATOR
#     st.success() et st.warning() sont appelés directement.
#     Leur valeur de retour n'est jamais envoyée à st.write().
#
# 04. RECHERCHE DES MATCHS
#     /matches reçoit dateFrom/dateTo puis les compétitions
#     sont filtrées localement.
#
# 05. DIAGNOSTIC
#     L'interface affiche le nombre brut retourné par l'API.
#     Cela permet de distinguer absence réelle de matchs et
#     problème de filtrage.
#
# 06. BACKTEST
#     Pour chaque match évalué, l'historique est limité aux
#     matchs dont la date est strictement antérieure au match.
#     Les données futures ne sont donc pas utilisées.
#
# 07. WARM-UP
#     Les premiers matchs de la saison ne sont pas évalués
#     avant d'avoir suffisamment de contexte historique.
#
# 08. MULTI-SAISON
#     Plusieurs saisons peuvent être agrégées afin d'éviter
#     une conclusion basée sur 5 ou 10 matchs seulement.
#
# 09. BRIER
#     Plus petit = meilleur.
#
# 10. LOG LOSS
#     Plus petit = meilleur.
#
# 11. ACCURACY
#     Mesure la fréquence du choix 1X2 ayant le maximum de
#     probabilité. Elle ne mesure pas la calibration.
#
# 12. SCORE EXACT
#     Le score exact top-1 est beaucoup plus difficile que 1X2.
#
# 13. CONFIANCE
#     La confiance affichée dans l'application est un indicateur
#     de séparation/qualité du modèle. Elle n'est pas la
#     probabilité de gagner un pari.
#
# 14. POISSON
#     Le cas lambda=0 est traité explicitement pour éviter une
#     matrice nulle ou des valeurs incohérentes.
#
# 15. DIXON-COLES
#     La correction est faible et bornée afin de ne pas laisser
#     un ajustement théorique dominer les données.
#
# 16. H2H
#     Le face-à-face est volontairement peu pondéré.
#
# 17. SHRINKAGE
#     Les petits échantillons sont rapprochés des moyennes de
#     la ligue plutôt que d'être utilisés sans correction.
#
# 18. ROBUSTESSE
#     Les réponses API non-200 ne sont pas traitées comme des
#     données valides.
#
# 19. QUOTA
#     Le nombre d'appels restants fourni par l'API est affiché
#     lorsque l'en-tête est disponible.
#
# 20. ATTRIBUTION
#     L'attribution football-data.org est conservée dans l'UI.
#
# 21. COMPATIBILITE
#     Le script vise Python 3 + Streamlit + NumPy + Pandas +
#     Requests.
#
# 22. SECURITE DE LA CLE
#     La clé n'est pas écrite en dur dans le fichier. Utiliser
#     Streamlit Secrets ou la zone protégée de la barre latérale.
#
# 23. LIMITES DES DONNEES
#     Si le compte football-data.org ne donne pas accès à une
#     ressource historique, le modèle ne peut pas inventer les
#     données manquantes.
#
# 24. VALIDATION
#     Un nombre élevé de lignes de code ne constitue pas un
#     échantillon statistique. La fiabilité doit être jugée sur
#     le nombre de vrais matchs historiques évalués.
#
# 25. REGLE DE CONFIANCE
#     Ne pas déclarer un modèle solide sur un très petit
#     échantillon, même si l'accuracy semble élevée.
#
# 26. DATE UTC
#     Les horaires football-data.org sont en UTC. La recherche
#     utilise la date API puis filtre les compétitions.
#
# 27. ETAT STREAMLIT
#     Les résultats de recherche et d'analyse sont conservés
#     dans st.session_state pour éviter de les perdre à chaque
#     interaction.
#
# 28. ERREURS D'ANALYSE
#     Une exception d'analyse est capturée et affichée dans
#     l'expander du match au lieu de casser toute l'application.
#
# 29. REINITIALISATION
#     Le bouton de cache permet de forcer une nouvelle lecture
#     de l'API après modification de la clé ou des données.
#
# 30. OBJECTIF
#     Le but de cette version est d'être techniquement robuste,
#     reproductible et mesurable, pas de promettre une certitude
#     impossible sur un résultat sportif.
#
