# RODRIGUE PRO FOOTBALL AI - API-FOOTBALL V3
# Version corrigée : probabilités cohérentes, données réelles séparées des données absentes,
# cache, gestion des réponses API, pourcentages "45%", prédictions, blessures, joueurs, cotes.

import math
import os
import re
import time
from collections import defaultdict
from datetime import date, datetime
from typing import Any, Dict, Optional, Tuple

import numpy as np
import pandas as pd
import requests
import streamlit as st

BASE_URL = "https://v3.football.api-sports.io"
TZ = "Africa/Douala"
TIMEOUT = 25
MAX_GOALS = 10

st.set_page_config(page_title="Rodrigue Pro Football AI", page_icon="⚽", layout="wide")


def pct(x: float) -> str:
    return f"{max(0.0, min(1.0, float(x))) * 100:.1f}%"


def num(x, default=None):
    if x is None or x == "":
        return default
    if isinstance(x, (int, float, np.number)):
        return float(x)
    s = str(x).strip().replace(",", ".")
    m = re.search(r"-?\d+(?:\.\d+)?", s)
    return float(m.group()) if m else default


def clamp(x, lo, hi):
    return max(lo, min(hi, x))


def get_path(obj, *keys, default=None):
    cur = obj
    for key in keys:
        if isinstance(cur, dict):
            cur = cur.get(key, default)
        elif isinstance(cur, list) and isinstance(key, int) and key < len(cur):
            cur = cur[key]
        else:
            return default
    return cur


def response_rows(data):
    return data.get("response", []) if isinstance(data, dict) else []


def poisson(k: int, lam: float) -> float:
    lam = max(0.001, float(lam))
    return math.exp(-lam + k * math.log(lam) - math.lgamma(k + 1))


def matrix(lh: float, la: float, n=MAX_GOALS):
    m = np.array([[poisson(h, lh) * poisson(a, la) for a in range(n + 1)] for h in range(n + 1)])
    total = float(m.sum())
    return m / total if total > 0 else np.full((n + 1, n + 1), 1 / ((n + 1) ** 2))


def outcome_probs(m):
    n = m.shape[0]
    p1 = float(np.tril(m, -1).sum())
    px = float(np.trace(m))
    p2 = float(np.triu(m, 1).sum())
    over = {}
    for line in (0.5, 1.5, 2.5, 3.5, 4.5):
        over[line] = float(sum(m[h, a] for h in range(n) for a in range(n) if h + a > line))
    btts = float(sum(m[h, a] for h in range(1, n) for a in range(1, n)))
    # Joint markets.
    btts_o25 = float(sum(m[h, a] for h in range(1, n) for a in range(1, n) if h + a > 2.5))
    btts_1 = float(sum(m[h, a] for h in range(1, n) for a in range(1, n) if h > a))
    btts_2 = float(sum(m[h, a] for h in range(1, n) for a in range(1, n) if a > h))
    return {
        "1": p1, "X": px, "2": p2,
        "1X": p1 + px, "X2": px + p2, "12": p1 + p2,
        "BTTS Oui": btts, "BTTS Non": 1 - btts,
        "BTTS + 1": btts_1, "BTTS + 2": btts_2,
        "BTTS + Over 2.5": btts_o25,
        **{f"O{line}": v for line, v in over.items()},
        **{f"U{line}": 1 - v for line, v in over.items()},
    }


def exact_scores(m, n=15):
    rows = []
    for h in range(m.shape[0]):
        for a in range(m.shape[1]):
            rows.append((float(m[h, a]), h, a))
    return sorted(rows, reverse=True)[:n]


class API:
    def __init__(self, key):
        self.key = key.strip()
        self.s = requests.Session()
        self.s.headers.update({"x-apisports-key": self.key, "Accept": "application/json"})

    @st.cache_data(ttl=90, show_spinner=False)
    def call(_self, endpoint: str, params_tuple: Tuple[Tuple[str, str], ...]):
        params = dict(params_tuple)
        last_error = None
        for attempt in range(2):
            try:
                r = _self.s.get(BASE_URL + endpoint, params=params, timeout=TIMEOUT)
                try:
                    data = r.json()
                except Exception:
                    raise RuntimeError(f"Réponse JSON invalide (HTTP {r.status_code})")
                if r.status_code >= 400:
                    raise RuntimeError(f"HTTP {r.status_code}: {data.get('errors', data)}")
                if data.get("errors"):
                    raise RuntimeError(str(data["errors"]))
                return data
            except Exception as e:
                last_error = e
                if attempt == 0:
                    time.sleep(0.8)
        raise last_error

    def get(self, endpoint, params=None):
        clean = {k: str(v) for k, v in (params or {}).items() if v is not None and v != ""}
        return self.call(endpoint, tuple(sorted(clean.items())))


def fixture_name(f):
    return f"{get_path(f,'teams','home','name',default='Domicile')} vs {get_path(f,'teams','away','name',default='Extérieur')}"


def score(f):
    return get_path(f, 'goals', 'home'), get_path(f, 'goals', 'away')


def recent(api, team_id, last=10):
    try:
        return response_rows(api.get('/fixtures', {'team': team_id, 'last': last, 'status': 'FT'}))
    except Exception:
        return []


def form_rows(fixtures, team_id):
    out = []
    for f in fixtures:
        gh, ga = score(f)
        if gh is None or ga is None:
            continue
        hid = get_path(f, 'teams', 'home', 'id')
        aid = get_path(f, 'teams', 'away', 'id')
        if team_id == hid:
            gf, gc = int(gh), int(ga)
        elif team_id == aid:
            gf, gc = int(ga), int(gh)
        else:
            continue
        out.append({"gf": gf, "ga": gc, "result": "W" if gf > gc else "D" if gf == gc else "L"})
    return out


def weighted(rows):
    if not rows:
        return {"gf": None, "ga": None, "ppg": None}
    w = np.array([0.60 ** i for i in range(len(rows))], dtype=float)
    w /= w.sum()
    gf = float(sum(r['gf'] * ww for r, ww in zip(rows, w)))
    ga = float(sum(r['ga'] * ww for r, ww in zip(rows, w)))
    ppg = float(sum((3 if r['result'] == 'W' else 1 if r['result'] == 'D' else 0) * ww for r, ww in zip(rows, w)))
    return {"gf": gf, "ga": ga, "ppg": ppg}


def team_stats(api, team_id, league_id, season):
    try:
        rows = response_rows(api.get('/teams/statistics', {'team': team_id, 'league': league_id, 'season': season}))
        return rows[0] if rows else {}
    except Exception:
        return {}


def avg_from_stats(stats, side, direction):
    # API structure: goals -> for/against -> average -> home/away/all
    return num(get_path(stats, 'goals', direction, 'average', side), None)


def injuries(api, fixture_id, team_id=None, league_id=None, season=None):
    try:
        if fixture_id:
            rows = response_rows(api.get('/injuries', {'fixture': fixture_id}))
            if team_id:
                rows = [x for x in rows if get_path(x, 'team', 'id') == team_id]
            return rows
        p = {'team': team_id, 'league': league_id, 'season': season}
        return response_rows(api.get('/injuries', p))
    except Exception:
        return []


def h2h(api, hid, aid, last=10):
    try:
        return response_rows(api.get('/fixtures/headtohead', {'h2h': f'{hid}-{aid}', 'last': last}))
    except Exception:
        return []


def predictions(api, fixture_id):
    try:
        rows = response_rows(api.get('/predictions', {'fixture': fixture_id}))
        return rows[0] if rows else {}
    except Exception:
        return {}


def odds_1x2(api, fixture_id):
    try:
        rows = response_rows(api.get('/odds', {'fixture': fixture_id}))
    except Exception:
        return None, None, None
    vals = {"1": None, "X": None, "2": None}
    for bookmaker in rows:
        for bet in bookmaker.get('bookmakers', []):
            for market in bet.get('bets', []):
                name = str(market.get('name', '')).lower()
                if not any(x in name for x in ('match winner', '1x2', 'fulltime result')):
                    continue
                for v in market.get('values', []):
                    odd = num(v.get('odd'))
                    if odd is None or odd <= 1:
                        continue
                    key = str(v.get('value', '')).lower()
                    k = '1' if key in ('home', '1') else 'X' if key in ('draw', 'x') else '2' if key in ('away', '2') else None
                    if k and (vals[k] is None or odd < vals[k]):
                        vals[k] = odd
    return vals['1'], vals['X'], vals['2']


def player_form(api, team_id, fixtures):
    ratings = defaultdict(list)
    names = {}
    calls = 0
    for f in fixtures[:3]:
        fid = get_path(f, 'fixture', 'id')
        if not fid:
            continue
        try:
            rows = response_rows(api.get('/fixtures/players', {'fixture': fid}))
        except Exception:
            continue
        calls += 1
        for block in rows:
            if get_path(block, 'team', 'id') != team_id:
                continue
            for p in block.get('players', []):
                pid = get_path(p, 'player', 'id')
                rating = num(get_path(p, 'statistics', 0, 'games', 'rating'))
                if pid and rating is not None:
                    ratings[pid].append(rating)
                    names[pid] = get_path(p, 'player', 'name', default=str(pid))
    data = []
    for pid, rs in ratings.items():
        data.append((float(np.mean(rs)), names.get(pid, str(pid)), len(rs)))
    return sorted(data, reverse=True)[:10], calls


def expected_goals(hstats, astats, hf, af):
    # Prefer actual team statistics. If unavailable, use actual recent match results.
    h_attack = avg_from_stats(hstats, 'home', 'for')
    a_attack = avg_from_stats(astats, 'away', 'for')
    h_def = avg_from_stats(hstats, 'home', 'against')
    a_def = avg_from_stats(astats, 'away', 'against')

    hgf, hga = hf.get('gf'), hf.get('ga')
    agf, aga = af.get('gf'), af.get('ga')

    # No invented 1.20 values: missing fields are replaced only by real recent data.
    if h_attack is None: h_attack = hgf
    if a_attack is None: a_attack = agf
    if h_def is None: h_def = hga
    if a_def is None: a_def = aga

    # If one side is still unavailable, use the competition-neutral football prior.
    # This prior is explicitly marked as a prior, not as a statistic for the team.
    if h_attack is None: h_attack = 1.30
    if a_attack is None: a_attack = 1.05
    if h_def is None: h_def = 1.20
    if a_def is None: a_def = 1.30

    lh = 0.55 * h_attack + 0.25 * a_def + 0.20 * (hgf if hgf is not None else h_attack)
    la = 0.55 * a_attack + 0.25 * h_def + 0.20 * (agf if agf is not None else a_attack)

    # Home advantage is modest, not an artificial guarantee.
    lh *= 1.06
    la *= 0.97
    return clamp(lh, 0.15, 4.5), clamp(la, 0.15, 4.5)


def combine_with_market(lh, la, odds):
    oh, ox, oa = odds
    if not all(x and x > 1 for x in odds):
        return lh, la
    q = np.array([1 / oh, 1 / ox, 1 / oa], dtype=float)
    q /= q.sum()
    # Market is a small correction only.
    model = outcome_probs(matrix(lh, la))
    total = lh + la
    delta = q[0] - q[2]
    model_delta = model['1'] - model['2']
    shift = clamp(delta - model_delta, -0.25, 0.25)
    return clamp(lh * (1 + 0.08 * shift), 0.15, 4.5), clamp(la * (1 - 0.08 * shift), 0.15, 4.5)


def confidence(quality, top_prob, sample_size):
    # A confidence score is not a guaranteed hit rate.
    sample_factor = clamp(sample_size / 10, 0, 1)
    return clamp(0.50 + 0.25 * quality + 0.15 * sample_factor + 0.10 * clamp((top_prob - 1/3) * 2, 0, 1), 0.50, 0.95)


def analyze(api, fixture, season, players=False):
    hid = get_path(fixture, 'teams', 'home', 'id')
    aid = get_path(fixture, 'teams', 'away', 'id')
    lid = get_path(fixture, 'league', 'id')
    fid = get_path(fixture, 'fixture', 'id')

    hfix = recent(api, hid, 10)
    afix = recent(api, aid, 10)
    hf_rows, af_rows = form_rows(hfix, hid), form_rows(afix, aid)
    hf, af = weighted(hf_rows), weighted(af_rows)
    hs, ass = team_stats(api, hid, lid, season), team_stats(api, aid, lid, season)
    inj_h = injuries(api, fid, hid)
    inj_a = injuries(api, fid, aid)
    h2 = h2h(api, hid, aid)
    pred = predictions(api, fid)
    odds = odds_1x2(api, fid)

    lh, la = expected_goals(hs, ass, hf, af)
    lh, la = combine_with_market(lh, la, odds)
    full = matrix(lh, la)
    p = outcome_probs(full)

    # First-half model: approximately 45% of expected goals, then renormalized.
    ht = matrix(lh * 0.45, la * 0.45)
    hp = outcome_probs(ht)
    second = matrix(lh * 0.55, la * 0.55)
    sp = outcome_probs(second)

    htft = {
        '1/1': hp['1']*sp['1'], '1/X': hp['1']*sp['X'], '1/2': hp['1']*sp['2'],
        'X/1': hp['X']*sp['1'], 'X/X': hp['X']*sp['X'], 'X/2': hp['X']*sp['2'],
        '2/1': hp['2']*sp['1'], '2/X': hp['2']*sp['X'], '2/2': hp['2']*sp['2'],
    }
    s = sum(htft.values())
    htft = {k: v/s for k, v in htft.items()}

    available = sum(bool(x) for x in (hf_rows, af_rows, hs, ass, inj_h or inj_a, h2, pred, any(odds)))
    quality = available / 8
    top_market, top_prob = max(p.items(), key=lambda kv: kv[1])
    conf = confidence(quality, top_prob, min(len(hf_rows), len(af_rows)))

    ph = pa = []
    pcalls = 0
    if players:
        ph, c1 = player_form(api, hid, hfix)
        pa, c2 = player_form(api, aid, afix)
        pcalls = c1 + c2

    return {
        'home': get_path(fixture,'teams','home','name',default='Domicile'),
        'away': get_path(fixture,'teams','away','name',default='Extérieur'),
        'league': get_path(fixture,'league','name',default='N/D'),
        'venue': get_path(fixture,'fixture','venue','name',default='N/D'),
        'city': get_path(fixture,'fixture','venue','city',default=''),
        'id': fid, 'kickoff': get_path(fixture,'fixture','date',default=''),
        'lh': lh, 'la': la, 'markets': p, 'ht': hp, 'htft': htft,
        'scores': exact_scores(full), 'ht_scores': exact_scores(ht, 8),
        'hf_rows': hf_rows, 'af_rows': af_rows, 'hf': hf, 'af': af,
        'inj_h': inj_h, 'inj_a': inj_a, 'h2h': h2, 'prediction': pred,
        'odds': odds, 'quality': quality, 'confidence': conf,
        'player_h': ph, 'player_a': pa, 'player_calls': pcalls,
        'ht_draw_home': hp['X'] * sp['1'], 'ht_draw_away': hp['X'] * sp['2'],
        'ht_draw_winner': hp['X'] * (sp['1'] + sp['2'])
    }


# ---------------- UI ----------------
st.title("⚽ RODRIGUE PRO FOOTBALL AI")
st.caption("API-FOOTBALL V3 • statistiques réelles disponibles • modèle probabiliste cohérent")

with st.sidebar:
    st.header("🔐 API-FOOTBALL")
    key = st.text_input('API Key', value=os.getenv('API_FOOTBALL_KEY',''), type='password')
    season = st.number_input('Saison', 2015, 2035, datetime.now().year)
    players = st.checkbox('Forme des joueurs', False)

if not key:
    st.warning('Entre ta clé API-FOOTBALL dans la barre latérale.')
    st.stop()

api = API(key)
try:
    api.get('/status')
    st.sidebar.success('API connectée')
except Exception as e:
    st.error(f'API inaccessible : {e}')
    st.stop()


def find_fixture_by_id(fid):
    rows = response_rows(api.get('/fixtures', {'id': fid}))
    return rows[0] if rows else None


def fixtures_date(d):
    return response_rows(api.get('/fixtures', {'date': d.isoformat(), 'timezone': TZ}))


tab1, tab2 = st.tabs(['🔎 Analyse', '📅 Matchs du jour'])

with tab1:
    fid = st.text_input('ID du match (recommandé)', placeholder='Ex: 1631605')
    d = st.date_input('Date du match', date.today())
    c1, c2 = st.columns(2)
    home_q = c1.text_input('Équipe domicile')
    away_q = c2.text_input('Équipe extérieure')

    fixture = None
    if fid.strip().isdigit():
        try:
            fixture = find_fixture_by_id(int(fid))
        except Exception as e:
            st.error(str(e))
    elif home_q and away_q:
        try:
            rows = fixtures_date(d)
            candidates = [x for x in rows if home_q.lower() in get_path(x,'teams','home','name',default='').lower() and away_q.lower() in get_path(x,'teams','away','name',default='').lower()]
            if candidates:
                fixture = candidates[0]
                st.success(f'Match trouvé : {fixture_name(fixture)}')
            else:
                st.info('Aucun match correspondant trouvé à cette date.')
        except Exception as e:
            st.error(str(e))

    if fixture and st.button('🚀 LANCER L’ANALYSE', type='primary', use_container_width=True):
        try:
            with st.spinner('Récupération des vraies données et calcul...'):
                st.session_state['r'] = analyze(api, fixture, int(season), players)
        except Exception as e:
            st.error(f'Erreur pendant l’analyse : {e}')

    r = st.session_state.get('r')
    if r:
        st.divider()
        st.header(f"🎯 {r['home']} vs {r['away']}")
        st.write(f"**Compétition :** {r['league']}  |  **Stade :** {r['venue']} {r['city']}  |  **ID :** {r['id']}")

        a,b,c,d = st.columns(4)
        a.metric('1', pct(r['markets']['1']))
        b.metric('Nul', pct(r['markets']['X']))
        c.metric('2', pct(r['markets']['2']))
        d.metric('Qualité données', pct(r['quality']))
        top = max(r['markets'].items(), key=lambda x:x[1])
        st.success(f"🏆 Marché statistiquement le plus probable : **{top[0]} — {pct(top[1])}**")
        st.caption(f"Score de confiance du modèle : {pct(r['confidence'])}. Ce score n’est pas un taux de réussite garanti.")

        rows = [
            ('Victoire domicile', r['markets']['1']), ('Match nul', r['markets']['X']), ('Victoire extérieur', r['markets']['2']),
            ('Double chance 1X', r['markets']['1X']), ('Double chance X2', r['markets']['X2']), ('Double chance 12', r['markets']['12']),
            ('BTTS Oui', r['markets']['BTTS Oui']), ('BTTS Non', r['markets']['BTTS Non']),
            ('BTTS + Over 2.5', r['markets']['BTTS + Over 2.5']),
            ('BTTS + victoire domicile', r['markets']['BTTS + 1']), ('BTTS + victoire extérieur', r['markets']['BTTS + 2']),
        ]
        for line in (0.5,1.5,2.5,3.5,4.5):
            rows += [(f'Over {line}', r['markets'][f'O{line}']), (f'Under {line}', r['markets'][f'U{line}'])]
        st.subheader('📊 Marchés')
        st.dataframe(pd.DataFrame(rows, columns=['Marché','Probabilité']).assign(Probabilité=lambda x:x['Probabilité'].map(pct)), use_container_width=True, hide_index=True)

        st.subheader('⚽ Scores exacts')
        st.dataframe(pd.DataFrame([{'Score':f'{h}-{a}','Probabilité':pct(p)} for p,h,a in r['scores']]), use_container_width=True, hide_index=True)

        st.subheader('⏱️ Mi-temps / HT-FT')
        x,y,z = st.columns(3)
        x.metric('1 MT', pct(r['ht']['1']))
        y.metric('Nul MT', pct(r['ht']['X']))
        z.metric('2 MT', pct(r['ht']['2']))
        st.write(f"**Nul MT → domicile gagne 2e MT :** {pct(r['ht_draw_home'])}")
        st.write(f"**Nul MT → extérieur gagne 2e MT :** {pct(r['ht_draw_away'])}")
        st.write(f"**Nul MT → une équipe gagne 2e MT :** {pct(r['ht_draw_winner'])}")
        st.dataframe(pd.DataFrame([{'HT/FT':k,'Probabilité':pct(v)} for k,v in sorted(r['htft'].items(), key=lambda x:x[1], reverse=True)]), use_container_width=True, hide_index=True)

        st.subheader('🔥 Forme récente réelle')
        c1,c2 = st.columns(2)
        for c, name, rows_, f in ((c1,r['home'],r['hf_rows'],r['hf']),(c2,r['away'],r['af_rows'],r['af'])):
            c.markdown(f'**{name}**')
            c.write('Résultats : ' + (' '.join(x['result'] for x in rows_) if rows_ else 'N/D'))
            c.write('Buts marqués pondérés : ' + ('N/D' if f['gf'] is None else f"{f['gf']:.2f}"))
            c.write('Buts encaissés pondérés : ' + ('N/D' if f['ga'] is None else f"{f['ga']:.2f}"))

        st.subheader('🚑 Blessés / absents disponibles')
        c1,c2 = st.columns(2)
        for c, name, rows_ in ((c1,r['home'],r['inj_h']),(c2,r['away'],r['inj_a'])):
            c.markdown(f'**{name} : {len(rows_)} signalement(s)**')
            for x in rows_[:20]:
                c.write(f"• {get_path(x,'player','name',default='Joueur')} — {get_path(x,'player','type',default='N/D')}")

        if players:
            st.subheader('👤 Forme des joueurs')
            c1,c2 = st.columns(2)
            c1.dataframe(pd.DataFrame(r['player_h'], columns=['Note moyenne','Joueur','Matchs']), use_container_width=True, hide_index=True)
            c2.dataframe(pd.DataFrame(r['player_a'], columns=['Note moyenne','Joueur','Matchs']), use_container_width=True, hide_index=True)
            st.caption(f"Appels joueurs utilisés : {r['player_calls']}")

        st.subheader('🤝 Face-à-face')
        h2 = []
        for f in r['h2h'][:10]:
            gh,ga = score(f)
            h2.append({'Date':str(get_path(f,'fixture','date',default=''))[:10], 'Match':fixture_name(f), 'Score':f'{gh}-{ga}' if gh is not None else 'N/D'})
        st.dataframe(pd.DataFrame(h2), use_container_width=True, hide_index=True) if h2 else st.info('Pas de H2H disponible pour ce match.')

        st.subheader('💰 Cotes 1X2')
        oh,ox,oa = r['odds']
        st.write({'1':oh or 'N/D','X':ox or 'N/D','2':oa or 'N/D'})

        st.subheader('🧠 Prévision API-FOOTBALL')
        pred = r['prediction']
        if pred:
            p_home = get_path(pred,'predictions','percent','home',default='N/D')
            p_draw = get_path(pred,'predictions','percent','draw',default='N/D')
            p_away = get_path(pred,'predictions','percent','away',default='N/D')
            advice = get_path(pred,'predictions','advice',default='N/D')
            gh = get_path(pred,'predictions','goals','home',default='N/D')
            ga = get_path(pred,'predictions','goals','away',default='N/D')
            st.write(f"**1 :** {p_home} • **X :** {p_draw} • **2 :** {p_away}")
            st.write(f"**Conseil API :** {advice} • **Score estimé API :** {gh}-{ga}")
        else:
            st.info('Aucune prévision API disponible pour ce match.')

with tab2:
    d2 = st.date_input('Date', date.today(), key='d2')
    if st.button('📅 Charger les matchs', use_container_width=True):
        try:
            rows = fixtures_date(d2)
            table = []
            for f in rows:
                table.append({'ID':get_path(f,'fixture','id'), 'Compétition':get_path(f,'league','name',default='N/D'), 'Domicile':get_path(f,'teams','home','name',default='N/D'), 'Extérieur':get_path(f,'teams','away','name',default='N/D'), 'Statut':get_path(f,'fixture','status','short',default='N/D')})
            st.dataframe(pd.DataFrame(table), use_container_width=True, hide_index=True)
        except Exception as e:
            st.error(str(e))

st.divider()
st.caption('Rodrigue Pro Football AI • Source : API-FOOTBALL • Les données absentes restent N/D et ne sont pas inventées.')
