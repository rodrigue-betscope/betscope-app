# ============================================================
# RODRIGUE PRO FOOTBALL AI — API-FOOTBALL V3 (PRODUCTION READY)
# ============================================================
# Installation requirements.txt:
#   streamlit>=1.28.0
#   requests>=2.31.0
#   pandas>=2.0.0
#   numpy>=1.24.0
#
# Lancement local ou GitHub/Streamlit Cloud:
#   streamlit run app.py
# ============================================================

import math
import os
import time
from collections import defaultdict
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import requests
import streamlit as st

BASE_URL = "https://v3.football.api-sports.io"
DEFAULT_TZ = "Africa/Douala"
TIMEOUT = 25

st.set_page_config(
    page_title="Rodrigue Pro Football AI",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ----------------------------- CSS -----------------------------
st.markdown("""
<style>
.block-container {padding-top: 1rem; padding-bottom: 2rem;}
.big-title {font-size: 2.0rem; font-weight: 800;}
.subtle {color:#6b7280;}
.pred {font-size: 1.45rem; font-weight: 800;}
.good {font-weight: 800;}
.small {font-size: .86rem;}
</style>
""", unsafe_allow_html=True)

# ----------------------------- Helpers -----------------------------
def safe_float(x, default=0.0) -> float:
    try:
        if x is None or x == "":
            return default
        return float(x)
    except Exception:
        return default

def pct(x: float) -> str:
    return f"{max(0.0, min(100.0, x)):.1f}%"

def clamp(x: float, lo=0.0, hi=1.0) -> float:
    return max(lo, min(hi, x))

def poisson_pmf(k: int, lam: float) -> float:
    lam = max(0.0001, float(lam))
    return math.exp(-lam) * (lam ** k) / math.factorial(k)

def normalize_probs(d: Dict[str, float]) -> Dict[str, float]:
    s = sum(max(0.0, v) for v in d.values())
    if s <= 0:
        return {k: 1.0 / len(d) for k in d}
    return {k: max(0.0, v) / s for k, v in d.items()}

def val(obj, *keys, default=None):
    cur = obj
    for k in keys:
        if isinstance(cur, dict):
            cur = cur.get(k, default)
        else:
            return default
    return cur

# ----------------------------- API client -----------------------------
class APIFootball:
    def __init__(self, key: str):
        self.key = key.strip()
        self.session = requests.Session()
        self.session.headers.update({
            "x-apisports-key": self.key,
            "Accept": "application/json",
            "User-Agent": "Rodrigue-Pro-Football-AI/1.0",
        })

    @st.cache_data(ttl=60, show_spinner=False)
    def _get_cached(_self, endpoint: str, params_tuple: Tuple[Tuple[str, str], ...]):
        params = dict(params_tuple)
        r = _self.session.get(BASE_URL + endpoint, params=params, timeout=TIMEOUT)
        if r.status_code in (429, 500, 502, 503, 504):
            time.sleep(1.2)
            r = _self.session.get(BASE_URL + endpoint, params=params, timeout=TIMEOUT)
        try:
            data = r.json()
        except Exception:
            raise RuntimeError(f"Réponse API invalide HTTP {r.status_code}")
        if r.status_code >= 400:
            raise RuntimeError(f"HTTP {r.status_code}: {data}")
        errors = data.get("errors")
        if errors:
            raise RuntimeError(f"API-FOOTBALL: {errors}")
        return data

    def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None):
        params = params or {}
        clean = {}
        for k, v in params.items():
            if v is not None and v != "":
                clean[k] = str(v)
        return self._get_cached(endpoint, tuple(sorted(clean.items())))

# ----------------------------- Extraction -----------------------------
def response_data(data):
    return data.get("response", []) if isinstance(data, dict) else []

def fixture_name(f):
    return f"{val(f,'teams','home','name',default='Home')} — {val(f,'teams','away','name',default='Away')}"

def fixture_score(f):
    h = val(f, "goals", "home", default=None)
    a = val(f, "goals", "away", default=None)
    return h, a

def team_stats_basic(api, team_id, league_id, season):
    try:
        d = api.get("/teams/statistics", {
            "team": team_id, "league": league_id, "season": season
        })
        r = response_data(d)
        return r[0] if r else {}
    except Exception:
        return {}

def recent_fixtures(api, team_id, last=10):
    try:
        d = api.get("/fixtures", {"team": team_id, "last": last})
        return response_data(d)
    except Exception:
        return []

def get_h2h(api, home_id, away_id, last=10):
    try:
        d = api.get("/fixtures/headtohead", {
            "h2h": f"{home_id}-{away_id}", "last": last
        })
        return response_data(d)
    except Exception:
        return []

def get_injuries(api, fixture_id=None, league_id=None, season=None, team_id=None):
    p = {}
    if fixture_id:
        p["fixture"] = fixture_id
    else:
        if league_id: p["league"] = league_id
        if season: p["season"] = season
        if team_id: p["team"] = team_id
    try:
        return response_data(api.get("/injuries", p))
    except Exception:
        return []

def extract_form(fixtures, team_id):
    out = []
    for f in fixtures:
        status = val(f, "fixture", "status", "short", default="")
        if status not in ("FT", "AET", "PEN"):
            continue
        home_id = val(f, "teams", "home", "id")
        away_id = val(f, "teams", "away", "id")
        gh, ga = fixture_score(f)
        if gh is None or ga is None:
            continue
        if team_id == home_id:
            gf, gc = gh, ga
            result = "W" if gh > ga else "D" if gh == ga else "L"
        elif team_id == away_id:
            gf, gc = ga, gh
            result = "W" if ga > gh else "D" if ga == gh else "L"
        else:
            continue
        out.append({"result": result, "gf": gf, "ga": ga, "fixture": f})
    return out

def weighted_form(form_rows):
    if not form_rows:
        return {"ppg": 1.0, "gf": 1.2, "ga": 1.2, "attack": 1.0, "def": 1.0}
    weights = np.array([0.55 ** i for i in range(len(form_rows))], dtype=float)
    if weights.sum() > 0:
        weights = weights / weights.sum()
    gf = sum(r["gf"] * w for r, w in zip(form_rows, weights))
    ga = sum(r["ga"] * w for r, w in zip(form_rows, weights))
    pts = sum((3 if r["result"]=="W" else 1 if r["result"]=="D" else 0) * w
              for r, w in zip(form_rows, weights))
    attack = clamp(gf / 1.35, .35, 2.2)
    defense = clamp(1.35 / max(.25, ga), .35, 2.2)
    return {"ppg": pts, "gf": gf, "ga": ga, "attack": attack, "def": defense}

def stat_percent(stats, path, default=0.0):
    x = stats
    for k in path:
        if isinstance(x, dict):
            x = x.get(k)
        else:
            x = None
            break
    if isinstance(x, dict):
        x = x.get("percentage", x.get("total"))
    return safe_float(x, default)

# ----------------------------- Model -----------------------------
def poisson_matrix(lh, la, max_goals=7):
    mat = np.zeros((max_goals+1, max_goals+1))
    for h in range(max_goals+1):
        for a in range(max_goals+1):
            mat[h, a] = poisson_pmf(h, lh) * poisson_pmf(a, la)
    s = mat.sum()
    if s > 0:
        return mat / s
    return mat

def markets_from_matrix(mat):
    n = mat.shape[0]
    home = float(sum(mat[h,a] for h in range(n) for a in range(n) if h > a))
    draw = float(sum(mat[h,a] for h in range(n) for a in range(n) if h == a))
    away = float(sum(mat[h,a] for h in range(n) for a in range(n) if h < a))
    over05 = float(sum(mat[h,a] for h in range(n) for a in range(n) if h+a > .5))
    over15 = float(sum(mat[h,a] for h in range(n) for a in range(n) if h+a > 1.5))
    over25 = float(sum(mat[h,a] for h in range(n) for a in range(n) if h+a > 2.5))
    over35 = float(sum(mat[h,a] for h in range(n) for a in range(n) if h+a > 3.5))
    over45 = float(sum(mat[h,a] for h in range(n) for a in range(n) if h+a > 4.5))
    btts = float(sum(mat[h,a] for h in range(n) for a in range(n) if h > 0 and a > 0))
    return {
        "1": home, "X": draw, "2": away,
        "1X": home+draw, "X2": draw+away, "12": home+away,
        "O0.5": over05, "U0.5": 1-over05,
        "O1.5": over15, "U1.5": 1-over15,
        "O2.5": over25, "U2.5": 1-over25,
        "O3.5": over35, "U3.5": 1-over35,
        "O4.5": over45, "U4.5": 1-over45,
        "BTTS Oui": btts, "BTTS Non": 1-btts,
    }

def exact_scores(mat, topn=15):
    items = []
    for h in range(mat.shape[0]):
        for a in range(mat.shape[1]):
            items.append((float(mat[h,a]), h, a))
    items.sort(reverse=True)
    return items[:topn]

def infer_lambdas(home_stats, away_stats, home_form, away_form, h2h,
                  home_injuries, away_injuries, api_prediction=None,
                  home_odds=None, away_odds=None):
    hg = stat_percent(home_stats, ["goals", "for", "average", "home"], 1.45)
    ag = stat_percent(away_stats, ["goals", "for", "average", "away"], 1.15)
    hga = stat_percent(home_stats, ["goals", "against", "average", "home"], 1.10)
    aga = stat_percent(away_stats, ["goals", "against", "average", "away"], 1.25)

    if hg <= .05: hg = stat_percent(home_stats, ["goals","for","average","all"], 1.45)
    if ag <= .05: ag = stat_percent(away_stats, ["goals","for","average","all"], 1.15)
    if hga <= .05: hga = stat_percent(home_stats, ["goals","against","average","all"], 1.10)
    if aga <= .05: aga = stat_percent(away_stats, ["goals","against","average","all"], 1.25)

    lh = 0.52 * hg + 0.23 * home_form["gf"] + 0.25 * aga
    la = 0.52 * ag + 0.23 * away_form["gf"] + 0.25 * hga

    lh *= (0.82 + 0.18 * clamp(home_form["attack"], .5, 1.7))
    la *= (0.82 + 0.18 * clamp(away_form["attack"], .5, 1.7))

    h2h_rows = []
    for f in h2h:
        if val(f,"fixture","status","short") not in ("FT","AET","PEN"):
            continue
        gh, ga = fixture_score(f)
        if gh is not None and ga is not None:
            h2h_rows.append((gh,ga))
    if h2h_rows:
        hh = np.mean([x[0] for x in h2h_rows[-5:]])
        ha = np.mean([x[1] for x in h2h_rows[-5:]])
        lh = .92*lh + .08*max(.2, hh)
        la = .92*la + .08*max(.2, ha)

    def injury_factor(rows):
        factor = 1.0
        for _ in rows:
            factor -= 0.025
        return clamp(factor, .75, 1.0)

    lh *= injury_factor(home_injuries)
    la *= injury_factor(away_injuries)

    lh *= 1.07
    la *= 0.96

    if home_odds and away_odds and home_odds > 1 and away_odds > 1:
        qh, qa = 1/home_odds, 1/away_odds
        s = qh + qa
        if s > 0:
            qh, qa = qh/s, qa/s
            total = lh + la
            lh = .90*lh + .10*total*qh
            la = .90*la + .10*total*qa

    if api_prediction:
        p = api_prediction
        ph = safe_float(val(p,"percent","home",default=0))/100
        pa = safe_float(val(p,"percent","away",default=0))/100
        if ph > 0 and pa > 0:
            if ph > pa:
                lh *= 1.025
                la *= .985
            elif pa > ph:
                la *= 1.025
                lh *= .985

    return clamp(lh, .15, 4.2), clamp(la, .15, 4.0)

def half_time_matrix(lh, la):
    return poisson_matrix(lh * .44, la * .44, 6)

def confidence_from_data(data_quality, edge, dispersion):
    score = 55 + 25*data_quality + 18*clamp(edge,0,.5) - 12*clamp(dispersion,0,.5)
    return clamp(score/100, .50, .97)

# ----------------------------- Odds -----------------------------
def extract_1x2_odds(odds_response):
    home = draw = away = None
    for book in odds_response:
        for bet in book.get("bookmakers", []):
            for b in bet.get("bets", []):
                name = str(b.get("name","")).lower()
                if "match winner" not in name and name not in ("1x2","fulltime result"):
                    continue
                for v in b.get("values", []):
                    vn = str(v.get("value","")).lower()
                    odd = safe_float(v.get("odd"), None)
                    if odd is None: continue
                    if vn in ("home","1"): home = odd if home is None else min(home, odd)
                    elif vn in ("draw","x"): draw = odd if draw is None else min(draw, odd)
                    elif vn in ("away","2"): away = odd if away is None else min(away, odd)
    return home, draw, away

def fetch_odds(api, fixture_id):
    try:
        return response_data(api.get("/odds", {"fixture": fixture_id}))
    except Exception:
        return []

# ----------------------------- Player form -----------------------------
def player_form_summary(api, team_id, fixtures, max_matches=3):
    ratings = defaultdict(list)
    names = {}
    used = 0
    for f in fixtures[:max_matches]:
        fid = val(f,"fixture","id")
        if not fid: continue
        try:
            rows = response_data(api.get("/fixtures/players", {"fixture": fid}))
        except Exception:
            continue
        for team_block in rows:
            if val(team_block,"team","id") != team_id:
                continue
            for p in team_block.get("players", []):
                pid = val(p,"player","id")
                if not pid: continue
                rating = safe_float(val(p,"statistics",0,"rating"), None)
                if rating is not None:
                    ratings[pid].append(rating)
                    names[pid] = val(p,"player","name",default=f"Player {pid}")
        used += 1
    result = []
    for pid, rr in ratings.items():
        if rr:
            result.append((np.mean(rr), names.get(pid, str(pid)), len(rr)))
    result.sort(reverse=True)
    return result[:10], used

# ----------------------------- Fixture lookup -----------------------------
def find_teams(api, query):
    try:
        return response_data(api.get("/teams", {"search": query}))
    except Exception:
        return []

def find_fixtures_by_date(api, d):
    try:
        return response_data(api.get("/fixtures", {
            "date": d.isoformat(), "timezone": DEFAULT_TZ
        }))
    except Exception:
        return []

def get_fixture(api, fixture_id):
    d = api.get("/fixtures", {"id": fixture_id})
    r = response_data(d)
    return r[0] if r else None

# ----------------------------- Analysis -----------------------------
def analyze_fixture(api, f, season, analyze_players=False):
    home = val(f,"teams","home","name",default="Home")
    away = val(f,"teams","away","name",default="Away")
    hid = val(f,"teams","home","id")
    aid = val(f,"teams","away","id")
    league_id = val(f,"league","id")
    fixture_id = val(f,"fixture","id")
    league_name = val(f,"league","name",default="Unknown")
    venue = val(f,"fixture","venue","name",default="Unknown")
    city = val(f,"fixture","venue","city",default="")
    kickoff = val(f,"fixture","date",default="")

    hf = extract_form(recent_fixtures(api, hid, 10), hid)
    af = extract_form(recent_fixtures(api, aid, 10), aid)
    hform = weighted_form(hf)
    aform = weighted_form(af)

    hs = team_stats_basic(api, hid, league_id, season)
    ass = team_stats_basic(api, aid, league_id, season)
    h2h = get_h2h(api, hid, aid, 10)

    hi = get_injuries(api, fixture_id=fixture_id)
    if not hi:
        hi = get_injuries(api, league_id=league_id, season=season, team_id=hid)
        ai = get_injuries(api, league_id=league_id, season=season, team_id=aid)
    else:
        ai = [x for x in get_injuries(api, fixture_id=fixture_id) if val(x,"team","id") == aid]
        hi = [x for x in hi if val(x,"team","id") == hid]

    api_pred = None
    try:
        pr = response_data(api.get("/predictions", {"fixture": fixture_id}))
        api_pred = pr[0] if pr else None
    except Exception:
        pass

    odds = fetch_odds(api, fixture_id)
    oh, od, oa = extract_1x2_odds(odds)

    lh, la = infer_lambdas(
        hs, ass, hform, aform, h2h, hi, ai,
        api_prediction=api_pred,
        home_odds=oh, away_odds=oa
    )
    mat = poisson_matrix(lh, la)
    markets = markets_from_matrix(mat)
    htmat = half_time_matrix(lh, la)
    htmarkets = markets_from_matrix(htmat)

    scores = exact_scores(mat, 15)
    ht_scores = exact_scores(htmat, 8)

    second = poisson_matrix(lh*.56, la*.56)
    hm = markets_from_matrix(htmat)
    sm = markets_from_matrix(second)
    htft = {
        "1/1": hm["1"]*sm["1"], "1/X": hm["1"]*sm["X"], "1/2": hm["1"]*sm["2"],
        "X/1": hm["X"]*sm["1"], "X/X": hm["X"]*sm["X"], "X/2": hm["X"]*sm["2"],
        "2/1": hm["2"]*sm["1"], "2/X": hm["2"]*sm["X"], "2/2": hm["2"]*sm["2"],
    }
    htft = normalize_probs(htft)

    draw_ht_winner_2h = hm["X"] * (sm["1"] + sm["2"])
    ht_draw_home = hm["X"] * sm["1"]
    ht_draw_away = hm["X"] * sm["2"]

    components = [
        bool(hf), bool(af), bool(hs), bool(ass),
        bool(h2h), bool(api_pred), bool(odds), bool(hi or ai)
    ]
    quality = sum(components) / len(components)
    dispersion = abs(markets["1"] - markets["2"])
    top = max(markets, key=markets.get)
    confidence = confidence_from_data(quality, markets[top]-1/3, dispersion)

    ranked = sorted(markets.items(), key=lambda kv: kv[1], reverse=True)
    strong = [(k,v) for k,v in ranked if v >= .62][:10]

    player_home, player_away = [], []
    player_calls = 0
    if analyze_players:
        player_home, c1 = player_form_summary(api, hid, recent_fixtures(api,hid,5), 3)
        player_away, c2 = player_form_summary(api, aid, recent_fixtures(api,aid,5), 3)
        player_calls = c1 + c2

    return {
        "fixture_id": fixture_id, "home": home, "away": away,
        "home_id": hid, "away_id": aid, "league_id": league_id,
        "league": league_name, "venue": venue, "city": city,
        "kickoff": kickoff, "lh": lh, "la": la,
        "home_form": hform, "away_form": aform,
        "home_form_rows": hf, "away_form_rows": af,
        "home_stats": hs, "away_stats": ass,
        "h2h": h2h, "home_injuries": hi, "away_injuries": ai,
        "api_prediction": api_pred, "odds": (oh,od,oa),
        "markets": markets, "htmarkets": htmarkets,
        "scores": scores, "ht_scores": ht_scores,
        "htft": htft,
        "ht_draw_winner_2h": draw_ht_winner_2h,
        "ht_draw_home": ht_draw_home, "ht_draw_away": ht_draw_away,
        "quality": quality, "confidence": confidence,
        "strong": strong, "player_home": player_home,
        "player_away": player_away, "player_calls": player_calls
    }

# ----------------------------- UI -----------------------------
st.markdown('<div class="big-title">⚽ RODRIGUE PRO FOOTBALL AI</div>', unsafe_allow_html=True)
st.caption("Analyseur pré-match API-FOOTBALL V3 • Poisson + forme + H2H + blessures + modèle API + cotes")

with st.sidebar:
    st.header("🔐 API")
    env_key = os.getenv("API_FOOTBALL_KEY", "")
    api_key = st.text_input(
        "API-FOOTBALL API Key",
        value=env_key,
        type="password",
        help="Colle ici ta clé API-FOOTBALL."
    )
    st.markdown("**Quota Free : 100 requêtes/jour.**")
    st.divider()
    st.header("⚙️ Analyse")
    season_default = datetime.now().year
    season = st.number_input("Saison", min_value=2015, max_value=2035, value=season_default, step=1)
    analyze_players = st.checkbox(
        "Analyser la forme des joueurs",
        value=False,
        help="Consomme davantage de requêtes API."
    )

if not api_key:
    st.warning("Colle ta clé API-FOOTBALL dans la barre de gauche pour commencer.")
    st.stop()

api = APIFootball(api_key)

try:
    status = api.get("/status")
    st.sidebar.success("API connectée")
    st.sidebar.caption(str(val(status, "response", "requests", default={})))
except Exception as e:
    st.error(f"Connexion API impossible : {e}")
    st.stop()

tab1, tab2 = st.tabs(["🔎 Analyser un match", "📅 Matchs par date"])

with tab1:
    c1, c2 = st.columns([1,1])
    with c1:
        fixture_id_text = st.text_input("ID du match (optionnel)", placeholder="Ex: 1234567")
    with c2:
        date_match = st.date_input("Date du match", value=date.today())

    b1, b2 = st.columns([1,1])
    with b1:
        home_query = st.text_input("Équipe domicile", placeholder="Ex: Barcelona")
    with b2:
        away_query = st.text_input("Équipe extérieure", placeholder="Ex: Real Madrid")

    fixture = None

    if fixture_id_text.strip().isdigit():
        try:
            fixture = get_fixture(api, int(fixture_id_text.strip()))
        except Exception as e:
            st.error(str(e))

    if fixture is None and home_query and away_query:
        with st.spinner("Recherche du match..."):
            fixtures = find_fixtures_by_date(api, date_match)
        candidates = [
            x for x in fixtures
            if home_query.lower() in val(x,"teams","home","name",default="").lower()
            and away_query.lower() in val(x,"teams","away","name",default="").lower()
        ]
        if not candidates:
            candidates = [
                x for x in fixtures
                if (home_query.lower() in fixture_name(x).lower()
                    and away_query.lower() in fixture_name(x).lower())
            ]
        if candidates:
            labels = [f"{fixture_name(x)} | ID {val(x,'fixture','id')} | {val(x,'league','name')}" for x in candidates]
            choice = st.selectbox("Match trouvé", range(len(candidates)), format_func=lambda i: labels[i])
            fixture = candidates[choice]
        else:
            st.info("Aucun match correspondant à cette date et à ces deux équipes.")

    if fixture is not None:
        st.success(f"Match sélectionné : {fixture_name(fixture)}")
        if st.button("🚀 LANCER L'ANALYSE COMPLÈTE", type="primary", use_container_width=True):
            with st.spinner("Récupération des statistiques et calcul des marchés..."):
                try:
                    result = analyze_fixture(api, fixture, int(season), analyze_players)
                    st.session_state["analysis"] = result
                except Exception as e:
                    st.error(f"Analyse impossible : {e}")

    result = st.session_state.get("analysis")

    if result:
        st.divider()
        st.subheader(f"🎯 {result['home']} vs {result['away']}")
        st.caption(
            f"Compétition : {result['league']} • Stade : {result['venue']} {result['city']} • "
            f"ID : {result['fixture_id']}"
        )

        m = result["markets"]
        top_market = max(m, key=m.get)
        top_prob = m[top_market]

        a,b,c,d = st.columns(4)
        a.metric("1", pct(m["1"]))
        b.metric("Nul", pct(m["X"]))
        c.metric("2", pct(m["2"]))
        d.metric("Confiance modèle", pct(result["confidence"]))

        st.info(
            f"🏆 Sélection principale : **{top_market} — {pct(top_prob)}**. "
            "La probabilité est statistique."
        )

        st.subheader("📊 Marchés principaux")
        market_rows = [
            ("Victoire domicile (1)", m["1"]),
            ("Match nul (X)", m["X"]),
            ("Victoire extérieur (2)", m["2"]),
            ("Double chance 1X", m["1X"]),
            ("Double chance X2", m["X2"]),
            ("Double chance 12", m["12"]),
            ("BTTS Oui", m["BTTS Oui"]),
            ("BTTS Non", m["BTTS Non"]),
            ("Over 0.5", m["O0.5"]),
            ("Under 0.5", m["U0.5"]),
            ("Over 1.5", m["O1.5"]),
            ("Under 1.5", m["U1.5"]),
            ("Over 2.5", m["O2.5"]),
            ("Under 2.5", m["U2.5"]),
            ("Over 3.5", m["O3.5"]),
            ("Under 3.5", m["U3.5"]),
            ("Over 4.5", m["O4.5"]),
            ("Under 4.5", m["U4.5"]),
        ]
        dfm = pd.DataFrame(market_rows, columns=["Marché","Probabilité"])
        dfm["Probabilité"] = dfm["Probabilité"].map(pct)
        st.dataframe(dfm, use_container_width=True, hide_index=True)

        st.subheader("⚽ Scores exacts les plus probables")
        score_rows = [{"Score": f"{h}-{a}", "Probabilité": pct(p)} for p,h,a in result["scores"]]
        st.dataframe(pd.DataFrame(score_rows), use_container_width=True, hide_index=True)

        st.subheader("⏱️ Mi-temps")
        hm = result["htmarkets"]
        hta, htb, htc = st.columns(3)
        hta.metric("1 à la MT", pct(hm["1"]))
        htb.metric("Nul à la MT", pct(hm["X"]))
        htc.metric("2 à la MT", pct(hm["2"]))

        st.markdown(
            f"**Nul à la mi-temps → domicile gagne en 2e MT :** {pct(result['ht_draw_home'])}  \n"
            f"**Nul à la mi-temps → extérieur gagne en 2e MT :** {pct(result['ht_draw_away'])}  \n"
            f"**Nul à la mi-temps → une équipe gagne en 2e MT :** {pct(result['ht_draw_winner_2h'])}"
        )

        htft_rows = [{"HT/FT": k, "Probabilité": pct(v)} for k,v in
                     sorted(result["htft"].items(), key=lambda x:x[1], reverse=True)]
        st.subheader("🔄 HT/FT")
        st.dataframe(pd.DataFrame(htft_rows), use_container_width=True, hide_index=True)

        st.subheader("🔥 Forme récente")
        f1,f2 = st.columns(2)
        with f1:
            st.markdown(f"**{result['home']}**")
            st.write("Résultats :", " ".join(x["result"] for x in result["home_form_rows"][:10]) or "N/D")
            st.write(f"Buts marqués pondérés : **{result['home_form']['gf']:.2f}**")
            st.write(f"Buts encaissés pondérés : **{result['home_form']['ga']:.2f}**")
        with f2:
            st.markdown(f"**{result['away']}**")
            st.write("Résultats :", " ".join(x["result"] for x in result["away_form_rows"][:10]) or "N/D")
            st.write(f"Buts marqués pondérés : **{result['away_form']['gf']:.2f}**")
            st.write(f"Buts encaissés pondérés : **{result['away_form']['ga']:.2f}**")

        st.subheader("🚑 Blessés / absents")
        i1,i2 = st.columns(2)
        with i1:
            st.markdown(f"**{result['home']} — {len(result['home_injuries'])} signalement(s)**")
            for x in result["home_injuries"][:20]:
                st.write(f"• {val(x,'player','name',default='Joueur')} — {val(x,'player','type',default='absence')}")
        with i2:
            st.markdown(f"**{result['away']} — {len(result['away_injuries'])} signalement(s)**")
            for x in result["away_injuries"][:20]:
                st.write(f"• {val(x,'player','name',default='Joueur')} — {val(x,'player','type',default='absence')}")

        if analyze_players:
            st.subheader("👤 Forme des joueurs")
            p1,p2 = st.columns(2)
            with p1:
                st.markdown(f"**{result['home']}**")
                st.dataframe(
                    pd.DataFrame(result["player_home"], columns=["Note moyenne","Joueur","Matchs"]),
                    use_container_width=True, hide_index=True
                )
            with p2:
                st.markdown(f"**{result['away']}**")
                st.dataframe(
                    pd.DataFrame(result["player_away"], columns=["Note moyenne","Joueur","Matchs"]),
                    use_container_width=True, hide_index=True
                )
            st.caption(f"Appels de statistiques joueurs utilisés : {result['player_calls']}")

        st.subheader("🤝 Face-à-face")
        h2h_rows = []
        for x in result["h2h"][:10]:
            gh,ga = fixture_score(x)
            h2h_rows.append({
                "Date": str(val(x,"fixture","date",default=""))[:10],
                "Match": fixture_name(x),
                "Score": f"{gh}-{ga}" if gh is not None else "N/D",
                "Compétition": val(x,"league","name",default="")
            })
        if h2h_rows:
            st.dataframe(pd.DataFrame(h2h_rows), use_container_width=True, hide_index=True)
        else:
            st.caption("Pas assez de H2H disponible.")

        st.subheader("💰 Cotes 1X2 détectées")
        oh,od,oa = result["odds"]
        st.write({
            "1": oh if oh else "N/D",
            "X": od if od else "N/D",
            "2": oa if oa else "N/D"
        })

        if result["api_prediction"]:
            ap = result["api_prediction"]
            st.subheader("🧠 Prévision API-FOOTBALL")
            st.write(
                f"Conseil API : **{val(ap,'advice',default='N/D')}** • "
                f"Score estimé : **{val(ap,'goals','home',default='?')}-{val(ap,'goals','away',default='?')}**"
            )

        st.caption(
            f"Qualité des données disponibles pour ce match : {pct(result['quality'])}. "
            "Modèle probabiliste optimisé."
        )

with tab2:
    d = st.date_input("Date à charger", value=date.today(), key="calendar_date")
    if st.button("📅 Charger les matchs", use_container_width=True):
        with st.spinner("Chargement..."):
            try:
                rows = find_fixtures_by_date(api, d)
                rows = [
                    x for x in rows
                    if val(x,"fixture","status","short") not in ("CANC","PST","ABD")
                ]
                if not rows:
                    st.warning("Aucun match disponible pour cette date avec cette API.")
                else:
                    data = []
                    for x in rows:
                        data.append({
                            "ID": val(x,"fixture","id"),
                            "Heure": str(val(x,"fixture","date","",default=""))[-14:-9],
                            "Compétition": val(x,"league","name"),
                            "Domicile": val(x,"teams","home","name"),
                            "Extérieur": val(x,"teams","away","name"),
                            "Statut": val(x,"fixture","status","short")
                        })
                    st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)
                    st.caption("Copie l'ID du match dans l'onglet « Analyser un match ».")
            except Exception as e:
                st.error(str(e))

st.divider()
st.caption("Rodrigue Pro Football AI • Prêt pour déploiement sur GitHub / Streamlit Cloud.")
