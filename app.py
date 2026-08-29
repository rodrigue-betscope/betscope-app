# ============================================================
# RODRIGUE PRO FOOTBALL AI - API-FOOTBALL V3 / FIXED V3
# ============================================================
# pip install streamlit requests pandas numpy
# Streamlit Secrets: API_FOOTBALL_KEY = "YOUR_KEY"
# ============================================================

import math
import os
from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="Rodrigue Pro Football AI", page_icon="⚽", layout="wide")

BASE_URL = "https://v3.football.api-sports.io"
TIMEOUT = 25
MAX_RECENT = 10


def pct(p: Optional[float]) -> str:
    if p is None:
        return "N/D"
    return f"{max(0.0, min(1.0, float(p))) * 100:.1f}%"


def num(x: Any, default: Optional[float] = None) -> Optional[float]:
    try:
        if x is None or x == "":
            return default
        if isinstance(x, str):
            x = x.strip().replace("%", "")
        return float(x)
    except (TypeError, ValueError):
        return default


def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def getv(obj: Any, *keys: str, default=None):
    cur = obj
    for key in keys:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(key)
    return default if cur is None else cur


# ------------------------------------------------------------
# API CLIENT
# ------------------------------------------------------------

class APIFootball:
    def __init__(self, key: str):
        self.key = key.strip()
        self.session = requests.Session()
        self.session.headers.update({
            "x-apisports-key": self.key,
            "Accept": "application/json",
        })

    def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        clean = {
            str(k): str(v)
            for k, v in (params or {}).items()
            if v is not None and v != ""
        }
        try:
            response = self.session.get(
                BASE_URL + endpoint,
                params=clean,
                timeout=TIMEOUT,
            )
        except requests.RequestException as exc:
            raise RuntimeError(f"Erreur réseau API-FOOTBALL : {exc}") from exc

        try:
            data = response.json()
        except Exception as exc:
            raise RuntimeError(
                f"Réponse API-FOOTBALL invalide (HTTP {response.status_code})."
            ) from exc

        errors = data.get("errors") if isinstance(data, dict) else None
        if errors:
            raise RuntimeError(f"API-FOOTBALL : {errors}")
        if response.status_code >= 400:
            raise RuntimeError(f"API-FOOTBALL HTTP {response.status_code}: {data}")
        return data


@st.cache_data(ttl=300, show_spinner=False)
def api_get_cached(key: str, endpoint: str, params_tuple: Tuple[Tuple[str, str], ...]):
    return APIFootball(key).get(endpoint, dict(params_tuple))


def api_get(key: str, endpoint: str, params: Optional[Dict[str, Any]] = None):
    clean = tuple(sorted((str(k), str(v)) for k, v in (params or {}).items() if v is not None and v != ""))
    return api_get_cached(key, endpoint, clean)


def api_response(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    return data.get("response", []) if isinstance(data, dict) else []


# ------------------------------------------------------------
# API CALLS - IMPORTANT: NO `last` PARAMETER
# ------------------------------------------------------------

@st.cache_data(ttl=600, show_spinner=False)
def fixtures_for_date(key: str, day: str) -> List[Dict[str, Any]]:
    data = api_get(key, "/fixtures", {"date": day, "timezone": "Africa/Douala"})
    return api_response(data)


@st.cache_data(ttl=1800, show_spinner=False)
def recent_team_fixtures(key: str, team_id: int, before_date: str) -> List[Dict[str, Any]]:
    end = date.fromisoformat(before_date) - timedelta(days=1)
    start = end - timedelta(days=120)
    # FIX: the old code used `last=10`, which caused the Free-plan error.
    # We use an explicit date range and keep the latest 10 finished matches locally.
    data = api_get(key, "/fixtures", {
        "team": team_id,
        "from": start.isoformat(),
        "to": end.isoformat(),
        "status": "FT",
        "timezone": "Africa/Douala",
    })
    rows = api_response(data)
    rows.sort(key=lambda x: getv(x, "fixture", "date", default=""), reverse=True)
    return rows[:MAX_RECENT]


@st.cache_data(ttl=1800, show_spinner=False)
def team_stats(key: str, team_id: int, league_id: int, season: int) -> Optional[Dict[str, Any]]:
    data = api_get(key, "/teams/statistics", {
        "team": team_id,
        "league": league_id,
        "season": season,
    })
    # /teams/statistics returns an OBJECT in response, not a list.
    value = data.get("response") if isinstance(data, dict) else None
    return value if isinstance(value, dict) and value else None


@st.cache_data(ttl=1800, show_spinner=False)
def match_injuries(key: str, fixture_id: int) -> List[Dict[str, Any]]:
    data = api_get(key, "/injuries", {"fixture": fixture_id})
    return api_response(data)


@st.cache_data(ttl=900, show_spinner=False)
def api_prediction(key: str, fixture_id: int) -> Optional[Dict[str, Any]]:
    data = api_get(key, "/predictions", {"fixture": fixture_id})
    rows = api_response(data)
    return rows[0] if rows else None


@st.cache_data(ttl=900, show_spinner=False)
def match_odds(key: str, fixture_id: int) -> List[Dict[str, Any]]:
    data = api_get(key, "/odds", {"fixture": fixture_id})
    return api_response(data)


@st.cache_data(ttl=1800, show_spinner=False)
def match_h2h(key: str, home_id: int, away_id: int) -> List[Dict[str, Any]]:
    # FIX: no `last` parameter. Fetch the H2H response and slice locally.
    data = api_get(key, "/fixtures/headtohead", {"h2h": f"{home_id}-{away_id}"})
    rows = api_response(data)
    rows.sort(key=lambda x: getv(x, "fixture", "date", default=""), reverse=True)
    return rows[:10]


# ------------------------------------------------------------
# DATA EXTRACTION
# ------------------------------------------------------------

def finished_form(fixtures: List[Dict[str, Any]], team_id: int) -> List[Dict[str, Any]]:
    out = []
    for f in fixtures:
        status = getv(f, "fixture", "status", "short")
        if status not in ("FT", "AET", "PEN"):
            continue
        hg = num(getv(f, "goals", "home"))
        ag = num(getv(f, "goals", "away"))
        hid = getv(f, "teams", "home", "id")
        aid = getv(f, "teams", "away", "id")
        if hg is None or ag is None:
            continue
        if team_id == hid:
            gf, ga = hg, ag
        elif team_id == aid:
            gf, ga = ag, hg
        else:
            continue
        out.append({
            "date": getv(f, "fixture", "date", default=""),
            "gf": gf,
            "ga": ga,
            "result": "W" if gf > ga else "D" if gf == ga else "L",
            "home": team_id == hid,
        })
    out.sort(key=lambda x: x["date"], reverse=True)
    return out[:MAX_RECENT]


def weighted_average(rows: List[Dict[str, Any]], key: str) -> Optional[float]:
    if not rows:
        return None
    vals = np.array([float(r[key]) for r in rows], dtype=float)
    # Recent matches have more weight, but every match remains represented.
    weights = np.array([0.82 ** i for i in range(len(vals))], dtype=float)
    return float(np.average(vals, weights=weights))


def form_points(rows: List[Dict[str, Any]]) -> Optional[float]:
    if not rows:
        return None
    pts = {"W": 3, "D": 1, "L": 0}
    return float(np.mean([pts[r["result"]] for r in rows]))


def avg_goals_home_away(rows: List[Dict[str, Any]], team_id: int, home: bool) -> Optional[Tuple[float, float]]:
    filtered = [r for r in rows if r["home"] == home]
    if not filtered:
        return None
    gf = weighted_average(filtered, "gf")
    ga = weighted_average(filtered, "ga")
    if gf is None or ga is None:
        return None
    return gf, ga


def stat_average(stats: Optional[Dict[str, Any]], section: str, side: str) -> Optional[float]:
    if not stats:
        return None
    x = getv(stats, "goals", section, "average", side)
    if x is None:
        x = getv(stats, "goals", section, "average", "all")
    return num(x)


def parse_api_prediction(pred: Optional[Dict[str, Any]]) -> Dict[str, Optional[float]]:
    if not pred:
        return {"home": None, "draw": None, "away": None, "home_goals": None, "away_goals": None}
    ph = num(getv(pred, "percent", "home"))
    pd = num(getv(pred, "percent", "draw"))
    pa = num(getv(pred, "percent", "away"))
    # API percentages may be returned as strings such as "45%".
    def normalize(x):
        if x is None:
            return None
        return x / 100.0 if x > 1 else x
    return {
        "home": normalize(ph),
        "draw": normalize(pd),
        "away": normalize(pa),
        "home_goals": num(getv(pred, "goals", "home")),
        "away_goals": num(getv(pred, "goals", "away")),
    }


def odds_1x2(rows: List[Dict[str, Any]]) -> Dict[str, Optional[float]]:
    # Use the best available 1X2 price from returned bookmakers, then remove margin.
    best = {"1": None, "X": None, "2": None}
    for bookmaker_block in rows:
        for bet in bookmaker_block.get("bookmakers", []):
            name = str(bet.get("name", "")).lower()
            for market in bet.get("bets", []):
                if str(market.get("name", "")).lower() not in ("match winner", "1x2", "fulltime result"):
                    continue
                for item in market.get("values", []):
                    odd = num(item.get("odd"))
                    val = str(item.get("value", "")).lower()
                    key = "1" if val in ("home", "1") else "X" if val in ("draw", "x") else "2" if val in ("away", "2") else None
                    if key and odd and odd > 1:
                        if best[key] is None or odd < best[key]:
                            best[key] = odd
    inv = {k: (1 / v if v else None) for k, v in best.items()}
    total = sum(x for x in inv.values() if x is not None)
    if total <= 0:
        return {"1": None, "X": None, "2": None}
    return {k: (inv[k] / total if inv[k] is not None else None) for k in best}


def h2h_result_probs(rows: List[Dict[str, Any]], home_id: int, away_id: int) -> Optional[Tuple[float, float, float]]:
    if not rows:
        return None
    p1 = px = p2 = 0.0
    total = 0.0
    for f in rows:
        hg = num(getv(f, "goals", "home"))
        ag = num(getv(f, "goals", "away"))
        hid = getv(f, "teams", "home", "id")
        aid = getv(f, "teams", "away", "id")
        if hg is None or ag is None:
            continue
        # Reorient each historical game to the current home/away teams.
        if hid == home_id and aid == away_id:
            h, a = hg, ag
        elif hid == away_id and aid == home_id:
            h, a = ag, hg
        else:
            continue
        total += 1
        if h > a: p1 += 1
        elif h == a: px += 1
        else: p2 += 1
    if total == 0:
        return None
    return p1 / total, px / total, p2 / total


# ------------------------------------------------------------
# POISSON / MARKETS
# ------------------------------------------------------------

def poisson_p(k: int, lam: float) -> float:
    lam = max(0.001, float(lam))
    return math.exp(-lam) * lam ** k / math.factorial(k)


def score_matrix(lh: float, la: float, max_goals: int = 8) -> np.ndarray:
    m = np.zeros((max_goals + 1, max_goals + 1), dtype=float)
    for h in range(max_goals + 1):
        for a in range(max_goals + 1):
            m[h, a] = poisson_p(h, lh) * poisson_p(a, la)
    s = float(m.sum())
    return m / s if s else m


def calculate_markets(lh: float, la: float):
    m = score_matrix(lh, la)
    p1 = px = p2 = btts = 0.0
    totals: Dict[int, float] = {}
    scores = []
    for h in range(m.shape[0]):
        for a in range(m.shape[1]):
            p = float(m[h, a])
            totals[h + a] = totals.get(h + a, 0.0) + p
            if h > a: p1 += p
            elif h == a: px += p
            else: p2 += p
            if h > 0 and a > 0: btts += p
            scores.append((f"{h}-{a}", p))

    def over(line):
        return sum(p for g, p in totals.items() if g > line)
    def under(line):
        return sum(p for g, p in totals.items() if g < line)

    mk = {
        "1": p1, "Nul": px, "2": p2,
        "1X": p1 + px, "X2": px + p2, "12": p1 + p2,
        "BTTS Oui": btts, "BTTS Non": 1 - btts,
    }
    for line in (0.5, 1.5, 2.5, 3.5, 4.5):
        mk[f"Over {line}"] = over(line)
        mk[f"Under {line}"] = under(line)
    mk["Over 4.0"] = sum(p for g, p in totals.items() if g > 4)
    mk["Under 4.0"] = sum(p for g, p in totals.items() if g < 4)
    mk["Push 4.0"] = totals.get(4, 0.0)
    mk["BTTS + Over 2.5"] = sum(float(m[h, a]) for h in range(9) for a in range(9) if h > 0 and a > 0 and h + a > 2)
    mk["BTTS + Under 2.5"] = sum(float(m[h, a]) for h in range(9) for a in range(9) if h > 0 and a > 0 and h + a < 3)
    scores.sort(key=lambda z: z[1], reverse=True)
    return mk, scores


def htft(lh: float, la: float):
    # A simple coherent two-period Poisson model.
    h1, a1 = lh * 0.45, la * 0.45
    h2, a2 = lh - h1, la - a1
    out = {f"{x}/{y}": 0.0 for x in ("1", "X", "2") for y in ("1", "X", "2")}
    for xh in range(7):
        for xa in range(7):
            pht = poisson_p(xh, h1) * poisson_p(xa, a1)
            rht = "1" if xh > xa else "2" if xh < xa else "X"
            for yh in range(7):
                for ya in range(7):
                    p = pht * poisson_p(yh, h2) * poisson_p(ya, a2)
                    fh, fa = xh + yh, xa + ya
                    rft = "1" if fh > fa else "2" if fh < fa else "X"
                    out[f"{rht}/{rft}"] += p
    s = sum(out.values())
    return {k: v / s for k, v in out.items()} if s else out


# ------------------------------------------------------------
# ENSEMBLE MODEL
# ------------------------------------------------------------

def blend_probabilities(poisson_probs, api_probs, odds_probs, h2h_probs, weights):
    components = []
    for probs, w in ((poisson_probs, weights["poisson"]), (api_probs, weights["api"]), (odds_probs, weights["odds"]), (h2h_probs, weights["h2h"])):
        if probs and all(x is not None for x in probs):
            components.append((np.array(probs, dtype=float), w))
    if not components:
        return None
    arr = sum(p * w for p, w in components)
    arr = arr / arr.sum()
    return tuple(float(x) for x in arr)


def poisson_1x2(lh, la):
    m = score_matrix(lh, la)
    return float(np.tril(m, -1).sum()), float(np.trace(m)), float(np.triu(m, 1).sum())


def analyze_fixture(key: str, fixture: Dict[str, Any], season: int) -> Dict[str, Any]:
    home_id = int(getv(fixture, "teams", "home", "id"))
    away_id = int(getv(fixture, "teams", "away", "id"))
    league_id = int(getv(fixture, "league", "id"))
    fixture_id = int(getv(fixture, "fixture", "id"))

    home_raw = recent_team_fixtures(key, home_id, getv(fixture, "fixture", "date")[:10])
    away_raw = recent_team_fixtures(key, away_id, getv(fixture, "fixture", "date")[:10])
    hf = finished_form(home_raw, home_id)
    af = finished_form(away_raw, away_id)

    hs = team_stats(key, home_id, league_id, season)
    ass = team_stats(key, away_id, league_id, season)
    inj = match_injuries(key, fixture_id)
    pred = api_prediction(key, fixture_id)
    odd_rows = match_odds(key, fixture_id)
    h2h = match_h2h(key, home_id, away_id)

    # Recent all-match attack/defence.
    h_gf = weighted_average(hf, "gf")
    h_ga = weighted_average(hf, "ga")
    a_gf = weighted_average(af, "gf")
    a_ga = weighted_average(af, "ga")

    # Home-specific / away-specific statistics when available.
    hs_for_home = stat_average(hs, "for", "home")
    hs_against_home = stat_average(hs, "against", "home")
    as_for_away = stat_average(ass, "for", "away")
    as_against_away = stat_average(ass, "against", "away")

    # Require real data. Do not use invented 1.20/1.35 defaults.
    home_attack_sources = [x for x in (h_gf, hs_for_home) if x is not None]
    home_def_sources = [x for x in (h_ga, hs_against_home) if x is not None]
    away_attack_sources = [x for x in (a_gf, as_for_away) if x is not None]
    away_def_sources = [x for x in (a_ga, as_against_away) if x is not None]

    api_pred = parse_api_prediction(pred)

    if not (home_attack_sources and home_def_sources and away_attack_sources and away_def_sources):
        # We can still analyze if API-Football itself supplies estimated goals.
        if api_pred["home_goals"] is None or api_pred["away_goals"] is None:
            raise RuntimeError(
                f"{getv(fixture,'teams','home','name')} vs {getv(fixture,'teams','away','name')} : "
                "données réelles insuffisantes pour calculer un modèle sans inventer de statistiques."
            )
        lh = float(api_pred["home_goals"])
        la = float(api_pred["away_goals"])
        source = "API-FOOTBALL Prediction (données équipe incomplètes)"
        poisson_weight = 0.45
    else:
        # Attack vs opposing defence, with a modest home advantage.
        home_attack = float(np.mean(home_attack_sources))
        home_defence = float(np.mean(away_def_sources))
        away_attack = float(np.mean(away_attack_sources))
        away_defence = float(np.mean(home_def_sources))
        lh = (0.58 * home_attack + 0.42 * home_defence) * 1.06
        la = (0.58 * away_attack + 0.42 * away_defence) * 0.96
        source = "Forme récente + statistiques domicile/extérieur + Poisson"
        poisson_weight = 0.55

    # Availability signal: only adjust if actual match-specific injuries are returned.
    home_inj = [x for x in inj if getv(x, "team", "id") == home_id]
    away_inj = [x for x in inj if getv(x, "team", "id") == away_id]
    # Small capped effect; no fake player ratings or invented importance.
    lh *= clamp(1.0 - 0.012 * len(home_inj), 0.88, 1.0)
    la *= clamp(1.0 - 0.012 * len(away_inj), 0.88, 1.0)
    lh = clamp(lh, 0.10, 4.5)
    la = clamp(la, 0.10, 4.5)

    mk, scores = calculate_markets(lh, la)
    ht = htft(lh, la)

    p_poisson = poisson_1x2(lh, la)
    p_api = (api_pred["home"], api_pred["draw"], api_pred["away"])
    if not all(x is not None for x in p_api):
        p_api = None

    p_odds = odds_1x2(odd_rows)
    p_odds_tuple = (p_odds["1"], p_odds["X"], p_odds["2"])
    if not all(x is not None for x in p_odds_tuple):
        p_odds_tuple = None

    p_h2h = h2h_result_probs(h2h, home_id, away_id)

    # Weights favor the independent Poisson model, then API's own model.
    weights = {"poisson": poisson_weight, "api": 0.25, "odds": 0.12, "h2h": 0.08}
    ensemble = blend_probabilities(p_poisson, p_api, p_odds_tuple, p_h2h, weights)
    if ensemble is None:
        raise RuntimeError("Impossible de calculer l'ensemble : aucune source 1X2 exploitable.")

    ensemble_markets = dict(mk)
    ensemble_markets["1"] = ensemble[0]
    ensemble_markets["Nul"] = ensemble[1]
    ensemble_markets["2"] = ensemble[2]
    ensemble_markets["1X"] = ensemble[0] + ensemble[1]
    ensemble_markets["X2"] = ensemble[1] + ensemble[2]
    ensemble_markets["12"] = ensemble[0] + ensemble[2]

    top_market, top_prob = max(ensemble_markets.items(), key=lambda z: z[1])
    top_score, top_score_prob = scores[0]
    top_htft, top_htft_prob = max(ht.items(), key=lambda z: z[1])

    # Confidence = agreement + data coverage, NOT a claimed success rate.
    agreement = 1.0 - float(np.std(np.array(ensemble, dtype=float))) * 2.0
    agreement = clamp(agreement, 0.0, 1.0)
    source_flags = [bool(hf), bool(af), bool(hs), bool(ass), bool(pred), bool(odd_rows), bool(h2h), bool(inj)]
    coverage = sum(source_flags) / len(source_flags)
    confidence = clamp(0.55 * agreement + 0.45 * coverage, 0.0, 1.0)

    return {
        "fixture": fixture,
        "lh": lh,
        "la": la,
        "markets": ensemble_markets,
        "poisson_markets": mk,
        "scores": scores,
        "htft": ht,
        "top_market": top_market,
        "top_market_prob": top_prob,
        "top_score": top_score,
        "top_score_prob": top_score_prob,
        "top_htft": top_htft,
        "top_htft_prob": top_htft_prob,
        "confidence": confidence,
        "coverage": coverage,
        "source": source,
        "home_form": hf,
        "away_form": af,
        "home_inj": home_inj,
        "away_inj": away_inj,
        "prediction": pred,
        "odds": p_odds,
        "h2h": h2h,
        "ensemble": ensemble,
    }


# ------------------------------------------------------------
# UI
# ------------------------------------------------------------

st.title("⚽ Rodrigue Pro Football AI — Ensemble + Poisson")
st.caption("API-FOOTBALL V3 • calcul par match • aucune statistique inventée")

key = os.getenv("API_FOOTBALL_KEY", "")
try:
    secret_key = st.secrets.get("API_FOOTBALL_KEY")
    if secret_key:
        key = str(secret_key)
except Exception:
    pass
key = st.sidebar.text_input("API-FOOTBALL API Key", value=key, type="password")

if not key.strip():
    st.error("Ajoute API_FOOTBALL_KEY dans les Secrets Streamlit ou dans la barre latérale.")
    st.stop()

selected_date = st.date_input("📅 Date du match", value=date.today())
# Domestic football seasons usually start in the second half of the calendar year.
default_season = selected_date.year if selected_date.month >= 7 else selected_date.year - 1
season = st.number_input("Saison API-FOOTBALL", min_value=2015, max_value=2035, value=default_season, step=1)

if st.button("🔎 Charger les matchs", type="primary", use_container_width=True):
    try:
        loaded = fixtures_for_date(key, selected_date.isoformat())
        loaded = [m for m in loaded if getv(m, "fixture", "status", "short") not in ("CANC", "PST", "ABD")]
        st.session_state["matches"] = loaded
    except Exception as exc:
        st.error(str(exc))
        st.stop()

matches = st.session_state.get("matches", [])
if matches:
    labels = [
        f"{getv(m,'teams','home','name')} vs {getv(m,'teams','away','name')} | {getv(m,'league','name')} | ID {getv(m,'fixture','id')}"
        for m in matches
    ]
    selected = st.multiselect(
        "🎯 Matchs à analyser",
        list(range(len(matches))),
        default=list(range(min(3, len(matches)))),
        format_func=lambda i: labels[i],
    )

    if st.button("🧠 Analyser les matchs sélectionnés", use_container_width=True):
        if not selected:
            st.warning("Sélectionne au moins un match.")
            st.stop()

        results = []
        progress = st.progress(0)
        for n, idx in enumerate(selected, 1):
            try:
                results.append(analyze_fixture(key, matches[idx], int(season)))
            except Exception as exc:
                st.warning(str(exc))
            progress.progress(n / len(selected))

        if results:
            table = []
            for r in results:
                f = r["fixture"]
                table.append({
                    "Match": f"{getv(f,'teams','home','name')} vs {getv(f,'teams','away','name')}",
                    "1": pct(r["markets"]["1"]),
                    "N": pct(r["markets"]["Nul"]),
                    "2": pct(r["markets"]["2"]),
                    "Meilleur marché": r["top_market"],
                    "Probabilité marché": pct(r["top_market_prob"]),
                    "Score exact le + probable": f"{r['top_score']} ({pct(r['top_score_prob'])})",
                    "HT/FT le + probable": f"{r['top_htft']} ({pct(r['top_htft_prob'])})",
                    "Confiance modèle": pct(r["confidence"]),
                })
            st.subheader(f"📊 Résultats — {len(results)} match(s)")
            st.dataframe(pd.DataFrame(table), use_container_width=True, hide_index=True)

            for r in results:
                f = r["fixture"]
                home = getv(f, "teams", "home", "name")
                away = getv(f, "teams", "away", "name")
                with st.expander(f"⚽ {home} vs {away} — {r['top_market']} {pct(r['top_market_prob'])}"):
                    a, b, c, d = st.columns(4)
                    a.metric("1", pct(r["markets"]["1"]))
                    b.metric("N", pct(r["markets"]["Nul"]))
                    c.metric("2", pct(r["markets"]["2"]))
                    d.metric("Confiance modèle", pct(r["confidence"]))

                    st.write(f"**Buts attendus Poisson :** {r['lh']:.2f} — {r['la']:.2f}")
                    st.write(f"**Marché principal :** {r['top_market']} — {pct(r['top_market_prob'])}")
                    st.write(f"**Score exact principal :** {r['top_score']} — {pct(r['top_score_prob'])}")
                    st.write(f"**HT/FT principal :** {r['top_htft']} — {pct(r['top_htft_prob'])}")
                    st.write(f"**Nul MT → domicile gagne :** {pct(r['htft']['X/1'])}")
                    st.write(f"**Nul MT → extérieur gagne :** {pct(r['htft']['X/2'])}")
                    st.write(f"**Nul MT → une équipe gagne :** {pct(r['htft']['X/1'] + r['htft']['X/2'])}")

                    st.write("### 📈 Marchés")
                    market_df = pd.DataFrame([
                        {"Marché": name, "Probabilité": pct(prob)}
                        for name, prob in sorted(r["markets"].items(), key=lambda z: z[1], reverse=True)
                    ])
                    st.dataframe(market_df, use_container_width=True, hide_index=True)

                    st.write("### 🎯 Scores exacts")
                    score_df = pd.DataFrame([
                        {"Score": score, "Probabilité": pct(prob)}
                        for score, prob in r["scores"][:15]
                    ])
                    st.dataframe(score_df, use_container_width=True, hide_index=True)

                    st.write("### 🕐 HT/FT")
                    ht_df = pd.DataFrame([
                        {"HT/FT": name, "Probabilité": pct(prob)}
                        for name, prob in sorted(r["htft"].items(), key=lambda z: z[1], reverse=True)
                    ])
                    st.dataframe(ht_df, use_container_width=True, hide_index=True)

                    st.write("### 🔥 Forme récente")
                    st.write(f"**{home} :** {''.join(x['result'] for x in r['home_form']) or 'N/D'}")
                    st.write(f"**{away} :** {''.join(x['result'] for x in r['away_form']) or 'N/D'}")

                    st.write("### 🚑 Blessures / absences")
                    st.write(f"{home} : {len(r['home_inj'])} signalement(s) • {away} : {len(r['away_inj'])} signalement(s)")
                    if r["home_inj"]:
                        st.dataframe(pd.DataFrame([
                            {"Joueur": getv(x,"player","name",default="N/D"), "Type": getv(x,"type",default="N/D"), "Raison": getv(x,"reason",default="N/D")}
                            for x in r["home_inj"]
                        ]), use_container_width=True, hide_index=True)
                    if r["away_inj"]:
                        st.dataframe(pd.DataFrame([
                            {"Joueur": getv(x,"player","name",default="N/D"), "Type": getv(x,"type",default="N/D"), "Raison": getv(x,"reason",default="N/D")}
                            for x in r["away_inj"]
                        ]), use_container_width=True, hide_index=True)

                    st.write("### 🤖 Ensemble")
                    st.write(f"Poisson 1/N/2 : {pct(poisson_1x2(r['lh'], r['la'])[0])} / {pct(poisson_1x2(r['lh'], r['la'])[1])} / {pct(poisson_1x2(r['lh'], r['la'])[2])}")
                    if r["prediction"]:
                        ap = parse_api_prediction(r["prediction"])
                        st.write(f"API-FOOTBALL : {pct(ap['home'])} / {pct(ap['draw'])} / {pct(ap['away'])}")
                        st.write(f"Conseil API : {getv(r['prediction'],'advice',default='N/D')}")
                    st.write(f"Cotes implicites normalisées : {pct(r['odds']['1'])} / {pct(r['odds']['X'])} / {pct(r['odds']['2'])}")
                    st.write(f"H2H analysés : {len(r['h2h'])}")
                    st.write(f"Sources disponibles : {pct(r['coverage'])}")
                    st.caption("La confiance du modèle mesure la qualité/couverture et l'accord des sources. Elle n'est pas un taux de réussite garanti.")

st.divider()
st.info("La version V3 ne transmet plus le paramètre `last` à API-FOOTBALL. Les 10 derniers matchs sont sélectionnés localement à partir d'une fenêtre de dates, ce qui évite l'erreur affichée sur ton écran.")
st.caption("Les probabilités sont des estimations statistiques. Aucun modèle ne peut garantir 80 %, 90 % ou 100 % de réussite sur des matchs futurs.")
