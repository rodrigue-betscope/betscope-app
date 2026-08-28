# RODRIGUE PRO FOOTBALL AI - API-FOOTBALL V3 FIXED
# Streamlit + API-FOOTBALL V3
# pip install streamlit requests pandas numpy

import math
import os
from datetime import date, datetime, timedelta
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="Rodrigue Pro Football AI", page_icon="⚽", layout="wide")

BASE_URL = "https://v3.football.api-sports.io"
TZ = "Africa/Douala"
TIMEOUT = 25


def pct(p: float) -> str:
    """p is a probability in [0,1]."""
    return f"{max(0.0, min(1.0, float(p))) * 100:.1f}%"


def num(x, default=None):
    try:
        return float(x) if x is not None and x != "" else default
    except (TypeError, ValueError):
        return default


def clamp(x, lo, hi):
    return max(lo, min(hi, x))


def poisson(k, lam):
    lam = max(0.01, float(lam))
    return math.exp(-lam) * lam**k / math.factorial(k)


class APIFootball:
    def __init__(self, key: str):
        self.key = key.strip()
        self.s = requests.Session()
        self.s.headers.update({"x-apisports-key": self.key, "Accept": "application/json"})

    @st.cache_data(ttl=300, show_spinner=False)
    def request(_self, endpoint: str, params_tuple: Tuple[Tuple[str, str], ...]):
        params = dict(params_tuple)
        r = _self.s.get(BASE_URL + endpoint, params=params, timeout=TIMEOUT)
        try:
            data = r.json()
        except Exception:
            raise RuntimeError(f"Réponse API invalide HTTP {r.status_code}")
        if r.status_code >= 400:
            raise RuntimeError(f"API-FOOTBALL HTTP {r.status_code}: {data}")
        if data.get("errors"):
            raise RuntimeError(f"API-FOOTBALL: {data['errors']}")
        return data

    def get(self, endpoint, params=None):
        clean = {k: str(v) for k, v in (params or {}).items() if v is not None and v != ""}
        return self.request(endpoint, tuple(sorted(clean.items())))


def response(data):
    return data.get("response", []) if isinstance(data, dict) else []


def v(obj, *keys, default=None):
    cur = obj
    for key in keys:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(key, default)
    return cur


def finished_rows(fixtures, team_id):
    rows = []
    for f in fixtures:
        if v(f, "fixture", "status", "short") not in ("FT", "AET", "PEN"):
            continue
        h = num(v(f, "goals", "home"))
        a = num(v(f, "goals", "away"))
        if h is None or a is None:
            continue
        hid = v(f, "teams", "home", "id")
        aid = v(f, "teams", "away", "id")
        if team_id == hid:
            gf, ga = h, a
        elif team_id == aid:
            gf, ga = a, h
        else:
            continue
        rows.append({
            "date": v(f, "fixture", "date", default=""),
            "gf": gf, "ga": ga,
            "result": "W" if gf > ga else "D" if gf == ga else "L",
        })
    rows.sort(key=lambda x: x["date"], reverse=True)
    return rows


def weighted(rows, key):
    if not rows:
        return None
    weights = np.array([0.82**i for i in range(len(rows))], dtype=float)
    values = np.array([float(r[key]) for r in rows], dtype=float)
    return float(np.average(values, weights=weights))


def matrix(lh, la, max_goals=8):
    m = np.zeros((max_goals + 1, max_goals + 1), dtype=float)
    for h in range(max_goals + 1):
        for a in range(max_goals + 1):
            m[h, a] = poisson(h, lh) * poisson(a, la)
    s = m.sum()
    return m / s if s else m


def markets(lh, la):
    m = matrix(lh, la)
    p1 = px = p2 = btts = 0.0
    totals = {}
    scores = []
    for h in range(m.shape[0]):
        for a in range(m.shape[1]):
            p = float(m[h, a])
            totals[h+a] = totals.get(h+a, 0.0) + p
            p1 += p if h > a else 0
            px += p if h == a else 0
            p2 += p if h < a else 0
            btts += p if h > 0 and a > 0 else 0
            scores.append((f"{h}-{a}", p))

    def over(x): return sum(p for g, p in totals.items() if g > x)
    def under(x): return sum(p for g, p in totals.items() if g < x)

    out = {
        "1": p1, "X": px, "2": p2,
        "1X": p1+px, "X2": px+p2, "12": p1+p2,
        "BTTS Oui": btts, "BTTS Non": 1-btts,
    }
    for x in (0.5, 1.5, 2.5, 3.5, 4.5):
        out[f"Over {x}"] = over(x)
        out[f"Under {x}"] = under(x)
    out["Over 4.0"] = sum(p for g,p in totals.items() if g > 4)
    out["Under 4.0"] = sum(p for g,p in totals.items() if g < 4)
    out["Push 4.0"] = totals.get(4, 0.0)
    out["BTTS + Over 2.5"] = sum(float(m[h,a]) for h in range(9) for a in range(9) if h>0 and a>0 and h+a>2)
    out["BTTS + Under 2.5"] = sum(float(m[h,a]) for h in range(9) for a in range(9) if h>0 and a>0 and h+a<3)
    scores.sort(key=lambda z: z[1], reverse=True)
    return out, scores


def htft(lh, la):
    # Split expected goals between halves, then build a coherent HT/FT distribution.
    h1, a1 = lh*0.45, la*0.45
    h2, a2 = lh-h1, la-a1
    out = {f"{x}/{y}": 0.0 for x in ("1","X","2") for y in ("1","X","2")}
    for xh in range(7):
        for xa in range(7):
            pht = poisson(xh,h1)*poisson(xa,a1)
            rht = "1" if xh>xa else "2" if xh<xa else "X"
            for yh in range(7):
                for ya in range(7):
                    p = pht*poisson(yh,h2)*poisson(ya,a2)
                    rft = "1" if xh+yh>xa+ya else "2" if xh+yh<xa+ya else "X"
                    out[f"{rht}/{rft}"] += p
    s=sum(out.values())
    return {k:v/s for k,v in out.items()} if s else out


@st.cache_data(ttl=600, show_spinner=False)
def fixtures_by_date(key, d):
    return response(APIFootball(key).get("/fixtures", {"date": d, "timezone": TZ}))


@st.cache_data(ttl=900, show_spinner=False)
def team_recent(key, team_id, last=10):
    return response(APIFootball(key).get("/fixtures", {"team": team_id, "last": last, "timezone": TZ}))


@st.cache_data(ttl=1800, show_spinner=False)
def team_stats(key, team_id, league_id, season):
    return response(APIFootball(key).get("/teams/statistics", {"team": team_id, "league": league_id, "season": season}))


@st.cache_data(ttl=1800, show_spinner=False)
def injuries(key, fixture_id):
    return response(APIFootball(key).get("/injuries", {"fixture": fixture_id}))


@st.cache_data(ttl=900, show_spinner=False)
def prediction(key, fixture_id):
    r = response(APIFootball(key).get("/predictions", {"fixture": fixture_id}))
    return r[0] if r else None


@st.cache_data(ttl=900, show_spinner=False)
def odds(key, fixture_id):
    return response(APIFootball(key).get("/odds", {"fixture": fixture_id}))


@st.cache_data(ttl=1800, show_spinner=False)
def h2h(key, home_id, away_id):
    return response(APIFootball(key).get("/fixtures/headtohead", {"h2h": f"{home_id}-{away_id}", "last": 10}))


def extract_1x2(rows):
    best = {"1": None, "X": None, "2": None}
    for bookmaker in rows:
        for bet in bookmaker.get("bookmakers", []):
            if str(bet.get("name", "")).lower() not in ("match winner", "1x2", "fulltime result"):
                continue
            for item in bet.get("values", []):
                odd = num(item.get("odd"))
                if odd is None or odd <= 1: continue
                val0 = str(item.get("value", "")).lower()
                key = "1" if val0 in ("home","1") else "X" if val0 in ("draw","x") else "2" if val0 in ("away","2") else None
                if key and (best[key] is None or odd < best[key]): best[key] = odd
    return best


def stat_avg(stats, side, section, fallback=None):
    # API-FOOTBALL teams/statistics structure: goals -> for/against -> average -> home/away/all
    x = v(stats, "goals", section, "average", side)
    if x is None: x = v(stats, "goals", section, "average", "all")
    return num(x, fallback)


def injury_penalty(rows):
    # No player importance is invented. We only use a small availability signal.
    n = len(rows)
    return clamp(1.0 - 0.015*n, 0.82, 1.0)


def analyze(api_key, fixture, season):
    hid = v(fixture,"teams","home","id")
    aid = v(fixture,"teams","away","id")
    lid = v(fixture,"league","id")
    fid = v(fixture,"fixture","id")

    hf = finished_rows(team_recent(api_key,hid), hid)
    af = finished_rows(team_recent(api_key,aid), aid)
    hs = team_stats(api_key,hid,lid,season)
    ass = team_stats(api_key,aid,lid,season)
    inj = injuries(api_key,fid)
    hp = [x for x in inj if v(x,"team","id") == hid]
    ap = [x for x in inj if v(x,"team","id") == aid]
    pred = prediction(api_key,fid)
    odd = extract_1x2(odds(api_key,fid))
    hh = h2h(api_key,hid,aid)

    # REAL DATA ONLY: no fixed 1.20/1.35 team-form values.
    home_gf = weighted(hf,"gf")
    home_ga = weighted(hf,"ga")
    away_gf = weighted(af,"gf")
    away_ga = weighted(af,"ga")

    shgf = stat_avg(hs,"home","for")
    shga = stat_avg(hs,"home","against")
    sagf = stat_avg(ass,"away","for")
    saga = stat_avg(ass,"away","against")

    # Build each side from whichever real observations exist.
    h_attack = [x for x in (home_gf, shgf, away_ga, saga) if x is not None]
    a_attack = [x for x in (away_gf, sagf, home_ga, shga) if x is not None]
    if not h_attack or not a_attack:
        # API prediction is used only if available; otherwise mark as insufficient data.
        if not pred:
            raise RuntimeError(f"Données insuffisantes pour {v(fixture,'teams','home','name')} vs {v(fixture,'teams','away','name')}: l'API ne fournit pas assez de statistiques réelles.")
        # derive a non-identical baseline from API estimated goals if available
        ph = num(v(pred,"goals","home"))
        pa = num(v(pred,"goals","away"))
        if ph is None or pa is None:
            raise RuntimeError("Données insuffisantes pour calculer une probabilité fiable.")
        lh, la = ph, pa
        source = "Prévision API-FOOTBALL (statistiques d'équipe insuffisantes)"
    else:
        # Weighted attack/defence blend. Different teams therefore produce different lambdas.
        lh = 0.35*float(np.mean([x for x in (home_gf, shgf) if x is not None])) + 0.35*float(np.mean([x for x in (away_ga, saga) if x is not None])) + 0.30*(home_gf if home_gf is not None else shgf)
        la = 0.35*float(np.mean([x for x in (away_gf, sagf) if x is not None])) + 0.35*float(np.mean([x for x in (home_ga, shga) if x is not None])) + 0.30*(away_gf if away_gf is not None else sagf)
        source = "Forme récente + statistiques d'équipe API-FOOTBALL"

    # Modest home advantage, availability adjustment, and API prediction direction.
    lh *= 1.05 * injury_penalty(hp)
    la *= 0.98 * injury_penalty(ap)
    if pred:
        ph = num(v(pred,"percent","home")); pa = num(v(pred,"percent","away")); px = num(v(pred,"percent","draw"))
        if ph is not None and pa is not None:
            if ph > pa: lh *= 1.015
            elif pa > ph: la *= 1.015

    lh = clamp(lh,0.15,4.5); la = clamp(la,0.15,4.5)
    mk, scores = markets(lh,la)
    ht = htft(lh,la)
    top = max(mk.items(), key=lambda z:z[1])

    # Data quality is the proportion of requested real sources that actually returned data.
    flags = [bool(hf),bool(af),bool(hs),bool(ass),bool(pred),bool(odd["1"] or odd["X"] or odd["2"]),bool(hh),bool(inj)]
    quality = sum(flags)/len(flags)
    return {
        "fixture": fixture, "lh": lh, "la": la, "markets": mk, "scores": scores,
        "htft": ht, "top": top, "quality": quality, "source": source,
        "home_form": hf, "away_form": af, "home_inj": hp, "away_inj": ap,
        "prediction": pred, "odds": odd, "h2h": hh,
    }


st.title("⚽ Rodrigue Pro Football AI — V3 FIXED")
st.caption("Les pourcentages sont maintenant affichés correctement : une probabilité 0–1 est convertie en 0–100 %. Les valeurs manquantes ne sont plus remplacées par les mêmes statistiques fictives.")

key = os.getenv("API_FOOTBALL_KEY", "")
try:
    key = str(st.secrets.get("API_FOOTBALL_KEY", key))
except Exception:
    pass
key = st.sidebar.text_input("API-FOOTBALL API Key", value=key, type="password")

if not key.strip():
    st.error("Ajoute ta clé API-FOOTBALL dans Secrets sous API_FOOTBALL_KEY, ou colle-la dans la barre latérale.")
    st.stop()

selected_date = st.date_input("📅 Date", value=date.today())
season = st.number_input("Saison API-FOOTBALL", min_value=2015, max_value=2035, value=selected_date.year, step=1)

matches = []
if st.button("🔎 Charger les matchs", type="primary", use_container_width=True):
    try:
        matches = fixtures_by_date(key, selected_date.isoformat())
        matches = [m for m in matches if v(m,"fixture","status","short") not in ("CANC","PST","ABD")]
        st.session_state["matches"] = matches
    except Exception as e:
        st.error(str(e))
        st.stop()

matches = st.session_state.get("matches", matches)
if matches:
    labels = [f"{v(m,'teams','home','name')} vs {v(m,'teams','away','name')} | {v(m,'league','name')} | ID {v(m,'fixture','id')}" for m in matches]
    selected = st.multiselect("🎯 Matchs à analyser", range(len(matches)), default=list(range(min(3,len(matches)))), format_func=lambda i: labels[i])
    if st.button("🧠 Analyser les matchs sélectionnés", use_container_width=True):
        results=[]
        progress=st.progress(0)
        for n,i in enumerate(selected,1):
            try:
                r=analyze(key,matches[i],int(season))
                results.append(r)
            except Exception as e:
                st.warning(str(e))
            progress.progress(n/max(1,len(selected)))

        if results:
            table=[]
            for r in results:
                f=r["fixture"]; top,p=r["top"]
                table.append({
                    "Match": f"{v(f,'teams','home','name')} vs {v(f,'teams','away','name')}",
                    "1":pct(r["markets"]["1"]),"N":pct(r["markets"]["X"]),"2":pct(r["markets"]["2"]),
                    "Meilleure sélection":top,"Probabilité":pct(p),
                    "Buts attendus":f"{r['lh']:.2f} - {r['la']:.2f}",
                    "Qualité données":pct(r["quality"]),
                })
            st.subheader("📊 Résultats — chaque match a son propre calcul")
            st.dataframe(pd.DataFrame(table),use_container_width=True,hide_index=True)

            for r in results:
                f=r["fixture"]; home=v(f,"teams","home","name"); away=v(f,"teams","away","name")
                with st.expander(f"⚽ {home} vs {away} — {r['top'][0]} {pct(r['top'][1])}"):
                    a,b,c,d=st.columns(4)
                    a.metric("1",pct(r["markets"]["1"])); b.metric("N",pct(r["markets"]["X"])); c.metric("2",pct(r["markets"]["2"])); d.metric("Qualité",pct(r["quality"]))
                    rows=[]
                    for name,p in sorted(r["markets"].items(),key=lambda z:z[1],reverse=True): rows.append({"Marché":name,"Probabilité":pct(p)})
                    st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)
                    st.write("**🎯 Scores exacts**")
                    st.dataframe(pd.DataFrame([{"Score":s,"Probabilité":pct(p)} for s,p in r["scores"][:12]]),use_container_width=True,hide_index=True)
                    st.write("**🕐 HT/FT**")
                    st.dataframe(pd.DataFrame([{"HT/FT":k,"Probabilité":pct(p)} for k,p in sorted(r["htft"].items(),key=lambda z:z[1],reverse=True)]),use_container_width=True,hide_index=True)
                    st.write(f"**Nul MT → domicile gagne en 2e MT :** {pct(r['htft']['X/1'])}")
                    st.write(f"**Nul MT → extérieur gagne en 2e MT :** {pct(r['htft']['X/2'])}")
                    st.write(f"**Nul MT → une équipe gagne en 2e MT :** {pct(r['htft']['X/1']+r['htft']['X/2'])}")
                    st.write(f"**Source du calcul :** {r['source']}")
                    st.write(f"**Blessures/absences disponibles :** {len(r['home_inj'])} domicile, {len(r['away_inj'])} extérieur")
                    st.write(f"**H2H disponibles :** {len(r['h2h'])}")
                    st.write(f"**Cotes 1X2 :** {r['odds']}")
                    if r["prediction"]:
                        st.write(f"**Prévision API-FOOTBALL :** {v(r['prediction'],'advice',default='N/D')}")

st.caption("Les probabilités sont des estimations statistiques. Elles ne constituent pas une garantie de résultat.")
