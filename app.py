import math
from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="Rodrigue Pro Football AI", page_icon="⚽", layout="wide")

BASE_URL = "https://v3.football.api-sports.io"
DEFAULT_LEAGUES = {
    "Premier League": 39,
    "La Liga": 140,
    "Bundesliga": 78,
    "Serie A": 135,
    "Ligue 1": 61,
    "Champions League": 2,
    "MLS": 253,
    "Liga MX": 262,
    "Brasileirão": 71,
    "Primeira Liga": 94,
    "Eredivisie": 88,
}

# ------------------------- API -------------------------
class APIFootball:
    def __init__(self, key: str):
        self.key = key.strip()
        self.session = requests.Session()
        self.session.headers.update({"x-apisports-key": self.key})

    def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        r = self.session.get(BASE_URL + endpoint, params=params or {}, timeout=30)
        try:
            data = r.json()
        except Exception:
            data = {"errors": {"http": r.text}}
        if r.status_code == 401:
            raise RuntimeError("Clé API-FOOTBALL invalide ou absente.")
        if r.status_code == 429:
            raise RuntimeError("Limite API atteinte (429). Attends le renouvellement du quota.")
        if not r.ok:
            raise RuntimeError(f"API-FOOTBALL HTTP {r.status_code}: {data.get('errors', data)}")
        errors = data.get("errors")
        if errors:
            raise RuntimeError(f"API-FOOTBALL : {errors}")
        return data


def get_key() -> str:
    for path in [("api_football", "key"), ("API_FOOTBALL_KEY",), ("football_api", "key")]:
        try:
            obj = st.secrets
            for p in path:
                obj = obj[p]
            if obj:
                return str(obj).strip()
        except Exception:
            pass
    return ""

# ------------------------- math -------------------------
def poisson_p(k: int, lam: float) -> float:
    lam = max(float(lam), 1e-6)
    return math.exp(-lam) * lam ** k / math.factorial(k)


def score_matrix(lh: float, la: float, max_goals: int = 8) -> np.ndarray:
    m = np.zeros((max_goals + 1, max_goals + 1), dtype=float)
    for h in range(max_goals + 1):
        for a in range(max_goals + 1):
            m[h, a] = poisson_p(h, lh) * poisson_p(a, la)
    s = m.sum()
    return m / s if s else m


def outcome(h: int, a: int) -> str:
    return "1" if h > a else "X" if h == a else "2"


def markets(lh: float, la: float) -> Tuple[Dict[str, float], List[Tuple[str, float]], np.ndarray]:
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
            if h >= 1 and a >= 1: btts += p
            scores.append((f"{h}-{a}", p))

    def over(x: float) -> float:
        return sum(p for g, p in totals.items() if g > x)
    def under(x: float) -> float:
        return sum(p for g, p in totals.items() if g < x)

    mk = {
        "1": p1, "Nul": px, "2": p2,
        "1X": p1 + px, "X2": px + p2, "12": p1 + p2,
        "BTTS Oui": btts, "BTTS Non": 1 - btts,
    }
    for x in (0.5, 1.5, 2.5, 3.5, 4.5):
        mk[f"Over {x}"] = over(x)
        mk[f"Under {x}"] = under(x)
    mk["Over 4.0"] = over(4.0)
    mk["Under 4.0"] = under(4.0)
    mk["BTTS + Over 2.5"] = sum(float(m[h,a]) for h in range(9) for a in range(9) if h >= 1 and a >= 1 and h+a > 2)
    mk["BTTS + Under 2.5"] = sum(float(m[h,a]) for h in range(9) for a in range(9) if h >= 1 and a >= 1 and h+a < 3)
    scores.sort(key=lambda x: x[1], reverse=True)
    return mk, scores[:15], m


def htft(lh: float, la: float) -> Dict[str, float]:
    # Independent Poisson split: ~45% of expected goals before HT.
    hh, aa = lh * 0.45, la * 0.45
    sh, sa = lh - hh, la - aa
    out = {f"{x}/{y}": 0.0 for x in ("1", "X", "2") for y in ("1", "X", "2")}
    for h1 in range(7):
        for a1 in range(7):
            pht = poisson_p(h1, hh) * poisson_p(a1, aa)
            rt = outcome(h1, a1)
            for h2 in range(7):
                for a2 in range(7):
                    p = pht * poisson_p(h2, sh) * poisson_p(a2, sa)
                    out[f"{rt}/{outcome(h1+h2, a1+a2)}"] += p
    total = sum(out.values())
    return {k: v / total for k, v in out.items()} if total else out

# ------------------------- parsing -------------------------
def pct(v: Any) -> Optional[float]:
    if v is None: return None
    try:
        if isinstance(v, str):
            v = v.strip().replace("%", "")
        x = float(v)
        return x / 100 if x > 1 else x
    except Exception:
        return None


def num(v: Any) -> Optional[float]:
    try:
        if v is None or v == "-": return None
        return float(str(v).replace("%", "").replace(",", "."))
    except Exception:
        return None


def nested(d: Dict[str, Any], *keys: str, default=None):
    x: Any = d
    for k in keys:
        if not isinstance(x, dict): return default
        x = x.get(k)
    return default if x is None else x


def team_goal_rates(stats: Dict[str, Any]) -> Dict[str, Optional[float]]:
    r = (stats.get("response") or [{}])[0]
    gf = nested(r, "goals", "for", "total", "average", default=None)
    ga = nested(r, "goals", "against", "total", "average", default=None)
    # API can return strings like "1.4" or "-".
    return {"gf": num(gf), "ga": num(ga)}


def recent_rows(fixtures: List[Dict[str, Any]], team_id: int, before: str, limit: int = 10) -> List[Dict[str, Any]]:
    rows = []
    for f in fixtures:
        if f.get("fixture", {}).get("status", {}).get("short") not in {"FT", "AET", "PEN"}:
            continue
        if f.get("fixture", {}).get("date", "") >= before:
            continue
        h = f.get("teams", {}).get("home", {})
        a = f.get("teams", {}).get("away", {})
        hs = f.get("goals", {}).get("home")
        as_ = f.get("goals", {}).get("away")
        if hs is None or as_ is None: continue
        if h.get("id") == team_id:
            gf, ga = hs, as_
        elif a.get("id") == team_id:
            gf, ga = as_, hs
        else:
            continue
        rows.append({"date": f["fixture"]["date"], "gf": float(gf), "ga": float(ga), "result": "W" if gf > ga else "D" if gf == ga else "L"})
    rows.sort(key=lambda x: x["date"], reverse=True)
    return rows[:limit]


def weighted(rows: List[Dict[str, Any]], key: str) -> Optional[float]:
    if not rows: return None
    vals = [r[key] for r in rows]
    w = np.exp(-0.18 * np.arange(len(vals)))
    return float(np.average(vals, weights=w))

# ------------------------- API calls -------------------------
@st.cache_data(ttl=300, show_spinner=False)
def fixtures_for_date(key: str, league: int, season: int, day: str):
    api = APIFootball(key)
    return api.get("/fixtures", {"league": league, "season": season, "date": day}).get("response", [])

@st.cache_data(ttl=900, show_spinner=False)
def team_history(key: str, team: int, season: int, start: str, end: str):
    api = APIFootball(key)
    # Deliberately do NOT use the restricted `last` parameter.
    return api.get("/fixtures", {"team": team, "season": season, "from": start, "to": end, "status": "FT"}).get("response", [])

@st.cache_data(ttl=1800, show_spinner=False)
def team_stats(key: str, league: int, season: int, team: int):
    api = APIFootball(key)
    return api.get("/teams/statistics", {"league": league, "season": season, "team": team}).get("response", [])

@st.cache_data(ttl=1800, show_spinner=False)
def h2h_data(key: str, home: int, away: int):
    api = APIFootball(key)
    return api.get("/fixtures/headtohead", {"h2h": f"{home}-{away}"}).get("response", [])[:10]

@st.cache_data(ttl=900, show_spinner=False)
def prediction_data(key: str, fixture: int):
    api = APIFootball(key)
    return api.get("/predictions", {"fixture": fixture}).get("response", [])

@st.cache_data(ttl=900, show_spinner=False)
def odds_data(key: str, fixture: int):
    api = APIFootball(key)
    return api.get("/odds", {"fixture": fixture}).get("response", [])

@st.cache_data(ttl=600, show_spinner=False)
def injuries_data(key: str, team: int, day: str):
    api = APIFootball(key)
    return api.get("/injuries", {"team": team, "date": day}).get("response", [])

# ------------------------- ensemble -------------------------
def implied_1x2(odds_resp: List[Dict[str, Any]]) -> Optional[Dict[str, float]]:
    vals = []
    for book in odds_resp:
        for bm in book.get("bookmakers", []):
            for bet in bm.get("bets", []):
                if str(bet.get("name", "")).lower() in {"match winner", "1x2"}:
                    local = {}
                    for v in bet.get("values", []):
                        odd = num(v.get("odd"))
                        value = str(v.get("value", ""))
                        key = "1" if value in {"Home", "1"} else "X" if value in {"Draw", "X"} else "2" if value in {"Away", "2"} else None
                        if key and odd and odd > 1: local[key] = 1 / odd
                    if len(local) == 3:
                        s = sum(local.values()); vals.append({k: x/s for k,x in local.items()})
    if not vals: return None
    return {k: float(np.mean([v[k] for v in vals])) for k in ("1","X","2")}


def api_prediction(resp: List[Dict[str, Any]]) -> Optional[Dict[str, float]]:
    if not resp: return None
    p = resp[0].get("predictions", {})
    percent = p.get("percent", {})
    out = {"1": pct(percent.get("home")), "X": pct(percent.get("draw")), "2": pct(percent.get("away"))}
    if any(v is None for v in out.values()): return None
    s = sum(out.values())
    return {k: v/s for k,v in out.items()} if s else None


def analyse_match(key: str, match: Dict[str, Any], season: int, selected_day: date) -> Dict[str, Any]:
    league = int(match["league"]["id"])
    actual_season = int(match["league"].get("season") or season)
    fixture_id = int(match["fixture"]["id"])
    home = match["teams"]["home"]; away = match["teams"]["away"]
    hid, aid = int(home["id"]), int(away["id"])
    end = selected_day.isoformat()
    start = (selected_day - timedelta(days=120)).isoformat()

    hf = recent_rows(team_history(key, hid, actual_season, start, end), hid, end)
    af = recent_rows(team_history(key, aid, actual_season, start, end), aid, end)
    hs = team_stats(key, league, actual_season, hid)
    ass = team_stats(key, league, actual_season, aid)
    hr = team_goal_rates(hs); ar = team_goal_rates(ass)

    hgf = weighted(hf, "gf"); hga = weighted(hf, "ga")
    agf = weighted(af, "gf"); aga = weighted(af, "ga")
    # Use real team-season rates when present, otherwise recent form. No fabricated fixed defaults.
    hgf = hgf if hgf is not None else hr["gf"]
    hga = hga if hga is not None else hr["ga"]
    agf = agf if agf is not None else ar["gf"]
    aga = aga if aga is not None else ar["ga"]
    if None in (hgf, hga, agf, aga):
        raise RuntimeError(f"Données insuffisantes pour {home['name']} vs {away['name']} : statistiques réelles indisponibles.")

    # Blend recent form with season rates. Home advantage is deliberately small and transparent.
    lh = (0.60*hgf + 0.40*aga) * 1.05
    la = (0.60*agf + 0.40*hga) * 0.97
    lh = float(np.clip(lh, 0.05, 5.0)); la = float(np.clip(la, 0.05, 5.0))

    mk, scores, matrix = markets(lh, la)
    ht = htft(lh, la)
    odds = implied_1x2(odds_data(key, fixture_id))
    ap = api_prediction(prediction_data(key, fixture_id))

    # Ensemble: Poisson gets the strongest weight; available independent market/API signals adjust it.
    p_model = {"1": mk["1"], "X": mk["Nul"], "2": mk["2"]}
    components = [(p_model, 0.65)]
    if odds: components.append((odds, 0.20))
    if ap: components.append((ap, 0.15))
    weights = sum(w for _,w in components)
    final = {k: sum(src[k]*w for src,w in components)/weights for k in ("1","X","2")}
    fs = sum(final.values()); final = {k:v/fs for k,v in final.items()}

    h2h = h2h_data(key, hid, aid)
    try: injuries_h = injuries_data(key, hid, selected_day.isoformat())
    except Exception: injuries_h = []
    try: injuries_a = injuries_data(key, aid, selected_day.isoformat())
    except Exception: injuries_a = []

    best_score, best_score_p = scores[0]
    best_htft, best_htft_p = max(ht.items(), key=lambda x:x[1])
    best_1x2, best_1x2_p = max(final.items(), key=lambda x:x[1])
    data_count = sum(x is not None for x in (hgf,hga,agf,aga))
    quality = int(round(100 * (data_count/4) * (0.7 + 0.1*bool(odds) + 0.1*bool(ap) + 0.1*bool(h2h))))

    return {
        "fixture": fixture_id, "home": home["name"], "away": away["name"], "league": match["league"]["name"],
        "lambda_home": lh, "lambda_away": la, "form_home": "".join(r["result"] for r in hf), "form_away": "".join(r["result"] for r in af),
        "injuries_home": injuries_h, "injuries_away": injuries_a, "h2h_count": len(h2h), "odds": odds, "api_pred": ap,
        "final_1x2": final, "markets": mk, "scores": scores, "htft": ht, "best_score": (best_score,best_score_p),
        "best_htft": (best_htft,best_htft_p), "best_1x2": (best_1x2,best_1x2_p), "quality": quality,
    }

# ------------------------- UI -------------------------
key = get_key()
st.title("⚽ Rodrigue Pro Football AI — API-FOOTBALL")
st.caption("Ensemble Poisson + forme réelle + statistiques de saison + cotes + prédiction API quand disponibles.")

with st.sidebar:
    st.subheader("⚙️ Configuration")
    manual = st.text_input("Clé API-FOOTBALL", type="password", value="")
    if manual.strip(): key = manual.strip()
    selected_day = st.date_input("Date des matchs", value=date.today())
    season = st.number_input("Saison API", min_value=2000, max_value=2035, value=2026, step=1)
    names = st.multiselect("Compétitions", list(DEFAULT_LEAGUES.keys()), default=["Premier League", "La Liga", "Bundesliga", "Serie A", "Ligue 1"])

if not key:
    st.warning("Ajoute la clé API-FOOTBALL dans Secrets ou dans la case de la barre latérale.")
    st.stop()
if not names:
    st.info("Sélectionne au moins une compétition.")
    st.stop()

load = st.button("🔎 Charger les matchs", type="primary", use_container_width=True)
if load:
    all_matches = []
    errors = []
    for name in names:
        try:
            ms = fixtures_for_date(key, DEFAULT_LEAGUES[name], int(season), selected_day.isoformat())
            all_matches.extend(ms)
        except Exception as e:
            errors.append(f"{name}: {e}")
    if errors:
        for e in errors: st.warning(e)
    if not all_matches:
        st.warning("Aucun match renvoyé pour les compétitions/saison/date sélectionnées.")
        st.stop()

    st.session_state["matches"] = all_matches

matches = st.session_state.get("matches", [])
if matches:
    labels = {f"{m['teams']['home']['name']} vs {m['teams']['away']['name']} | {m['league']['name']} | ID {m['fixture']['id']}": m for m in matches}
    chosen = st.multiselect("🎯 Matchs à analyser", list(labels.keys()), default=list(labels.keys())[:3])
    if st.button("🧠 Analyser les matchs sélectionnés", use_container_width=True):
        for label in chosen:
            m = labels[label]
            try:
                with st.spinner(f"Analyse réelle : {m['teams']['home']['name']} vs {m['teams']['away']['name']}..."):
                    a = analyse_match(key, m, int(season), selected_day)
                st.divider()
                st.header(f"🎯 {a['home']} vs {a['away']}")
                c1,c2,c3,c4 = st.columns(4)
                c1.metric("1", f"{a['final_1x2']['1']*100:.1f}%")
                c2.metric("Nul", f"{a['final_1x2']['X']*100:.1f}%")
                c3.metric("2", f"{a['final_1x2']['2']*100:.1f}%")
                c4.metric("Qualité données", f"{a['quality']}%")
                st.success(f"Sélection 1X2 modèle : {a['best_1x2'][0]} — {a['best_1x2'][1]*100:.1f}%")
                st.info(f"🎯 Score exact le plus probable : {a['best_score'][0]} — {a['best_score'][1]*100:.1f}%")
                st.info(f"🕐 HT/FT le plus probable : {a['best_htft'][0]} — {a['best_htft'][1]*100:.1f}%")

                mkdf = pd.DataFrame([{"Marché":k,"Probabilité":f"{v*100:.1f}%"} for k,v in sorted(a['markets'].items(), key=lambda x:x[1], reverse=True)])
                st.subheader("📊 Marchés")
                st.dataframe(mkdf, use_container_width=True, hide_index=True)

                sdf = pd.DataFrame([{"Score":s,"Probabilité":f"{p*100:.2f}%"} for s,p in a['scores']])
                st.subheader("🎯 Scores exacts")
                st.dataframe(sdf, use_container_width=True, hide_index=True)

                hdf = pd.DataFrame([{"HT/FT":k,"Probabilité":f"{v*100:.2f}%"} for k,v in sorted(a['htft'].items(), key=lambda x:x[1], reverse=True)])
                st.subheader("🕐 HT/FT")
                st.dataframe(hdf, use_container_width=True, hide_index=True)

                st.write(f"Forme domicile : **{a['form_home'] or 'N/D'}** | Forme extérieur : **{a['form_away'] or 'N/D'}**")
                st.write(f"H2H disponibles : **{a['h2h_count']}** | Blessures domicile : **{len(a['injuries_home'])}** | Blessures extérieur : **{len(a['injuries_away'])}**")
                st.caption("Les pourcentages sont des probabilités statistiques du modèle. Ils ne constituent pas une garantie de résultat ou de gain.")
            except Exception as e:
                st.error(f"Analyse impossible pour {label}: {e}")
