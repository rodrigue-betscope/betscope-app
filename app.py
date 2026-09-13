import math, time
from datetime import date
import numpy as np
import pandas as pd
import requests
import streamlit as st

# ============================================================
# RODRIGUE PRO FOOTBALL AI — V21 VALIDATED — CORRIGÉ
# Source principale : football-data.org v4
#
# CORRECTIONS IMPORTANTES :
# 1) X-Auth-Token est maintenant réellement envoyé à l'API.
# 2) La clé API est incluse dans la clé du cache bas niveau.
# 3) Les caches "métier" ont été retirés pour éviter qu'une ancienne
#    réponse 403 reste mémorisée après changement de clé.
# 4) Bouton de réinitialisation complète du cache.
# 5) Diagnostic clair des erreurs 401 / 403 / 429.
# 6) Forme V-N-D corrigée.
# ============================================================

API_BASE = "https://api.football-data.org/v4"

# IMPORTANT : ne partage jamais cette clé publiquement.
FOOTBALL_DATA_KEY = "e6bdfe3de8b24ba595262d336bea5446".strip()

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

S = requests.Session()
S.headers.update({
    "User-Agent": "Rodrigue-Pro-Football-AI-V21",
    "Accept": "application/json",
})

st.set_page_config(
    page_title="Rodrigue Pro Football AI V21",
    page_icon="⚽",
    layout="wide",
)


# ============================================================
# OUTILS
# ============================================================

def sf(x, default=None):
    try:
        x = float(x)
        return x if math.isfinite(x) else default
    except (TypeError, ValueError):
        return default


def clamp(x, a, b):
    x = sf(x, a)
    return max(a, min(b, x))


def pct(x):
    x = sf(x)
    return "N/D" if x is None else f"{100 * clamp(x, 0, 1):.1f}%"


def fmt(x):
    x = sf(x)
    return "N/D" if x is None else f"{x:.2f}"


# ============================================================
# API — CORRECTION PRINCIPALE
# ============================================================

def _get(ep, params=(), token=""):
    """Requête HTTP avec authentification football-data.org."""
    token = (token or "").strip()

    if not token:
        return {
            "status": 0,
            "data": None,
            "error": "Clé API vide.",
            "remaining": "",
        }

    try:
        r = S.get(
            API_BASE + ep,
            headers={
                "X-Auth-Token": token,
                "Accept": "application/json",
                "User-Agent": "Rodrigue-Pro-Football-AI-V21",
            },
            params=dict(params),
            timeout=25,
        )

        try:
            data_json = r.json()
        except Exception:
            data_json = None

        if r.status_code == 200:
            error = ""
        elif isinstance(data_json, dict):
            error = data_json.get("message", "") or data_json.get("error", "")
        else:
            error = r.text[:500]

        return {
            "status": r.status_code,
            "data": data_json if r.status_code == 200 else None,
            "error": error,
            "remaining": r.headers.get("X-Requests-Available-Minute", ""),
        }

    except requests.RequestException as e:
        return {
            "status": 0,
            "data": None,
            "error": str(e),
            "remaining": "",
        }


# Le token fait partie des paramètres du cache.
# Ainsi, si la clé change, l'ancienne réponse 403 n'est pas réutilisée.
@st.cache_data(ttl=300, show_spinner=False)
def api(ep, params=(), token=""):
    time.sleep(0.12)
    return _get(ep, params, token)


def data(ep, params=()):
    r = api(ep, params, FOOTBALL_DATA_KEY)
    return r["data"] if r["status"] == 200 else None


def api_error_message(r):
    status = r.get("status", 0)
    err = r.get("error") or "sans détail"

    if status == 401:
        return "HTTP 401 : clé API absente, invalide ou non reconnue."
    if status == 403:
        return (
            "HTTP 403 : la clé est reconnue mais la ressource est refusée "
            "par les permissions/abonnement/version API."
        )
    if status == 429:
        return "HTTP 429 : limite de requêtes atteinte. Attends le renouvellement du quota."
    if status == 400:
        return f"HTTP 400 : paramètres de requête incorrects. Détail : {err}"
    if status == 404:
        return f"HTTP 404 : ressource introuvable. Détail : {err}"
    if status == 0:
        return f"Connexion impossible : {err}"
    return f"HTTP {status} : {err}"


# ============================================================
# DONNÉES FOOTBALL
# ============================================================

def competition_info(code):
    return data(f"/competitions/{code}") or {}


def season_matches(code, season_year):
    d = data(
        f"/competitions/{code}/matches",
        (("season", str(season_year)),),
    )
    return (d or {}).get("matches", [])


def team_matches(tid):
    d = data(
        f"/teams/{tid}/matches",
        (("status", "FINISHED"), ("limit", "60")),
    )
    return (d or {}).get("matches", [])


def table(code):
    d = data(f"/competitions/{code}/standings")
    blocks = (d or {}).get("standings", [])

    for b in blocks:
        if b.get("type") == "TOTAL":
            return b.get("table", [])

    return blocks[0].get("table", []) if blocks else []


def h2h(mid):
    if not mid:
        return []
    d = data(
        f"/matches/{mid}/head2head",
        (("limit", "10"),),
    )
    return (d or {}).get("matches", [])


# ============================================================
# FORMES / RÉSULTATS
# ============================================================

def finished(m):
    return (
        m.get("status") == "FINISHED"
        and m.get("score", {}).get("fullTime", {}).get("home") is not None
        and m.get("score", {}).get("fullTime", {}).get("away") is not None
    )


def dt_key(m):
    return m.get("utcDate", "")


def match_result(m, tid):
    h = m.get("homeTeam", {}).get("id")
    a = m.get("awayTeam", {}).get("id")
    f = m.get("score", {}).get("fullTime", {})

    hg, ag = f.get("home"), f.get("away")

    if hg is None or ag is None:
        return None

    if tid == h:
        return {
            "gf": hg,
            "ga": ag,
            "venue": "H",
            "r": "W" if hg > ag else "D" if hg == ag else "L",
        }

    if tid == a:
        return {
            "gf": ag,
            "ga": hg,
            "venue": "A",
            "r": "W" if ag > hg else "D" if ag == hg else "L",
        }

    return None


def rows_before(matches, tid, before=None, venue=None, limit=12):
    out = []
    cutoff = before or "9999"

    for m in sorted(matches, key=dt_key, reverse=True):
        if dt_key(m) >= cutoff or not finished(m):
            continue

        r = match_result(m, tid)

        if r and (venue is None or r["venue"] == venue):
            out.append({
                "date": dt_key(m),
                "gf": r["gf"],
                "ga": r["ga"],
                "venue": r["venue"],
                "r": r["r"],
            })

            if len(out) >= limit:
                break

    return out


def stats(rows):
    if not rows:
        return {
            "n": 0,
            "gf": 1.30,
            "ga": 1.30,
            "form": 0.50,
            "draw": 0.33,
            "wins": 0,
            "draws": 0,
            "losses": 0,
        }

    w = np.array(
        [0.94 ** i for i in range(len(rows))],
        dtype=float,
    )

    gf = np.array([x["gf"] for x in rows], dtype=float)
    ga = np.array([x["ga"] for x in rows], dtype=float)
    pts = np.array([
        3 if x["r"] == "W"
        else 1 if x["r"] == "D"
        else 0
        for x in rows
    ], dtype=float)

    return {
        "n": len(rows),
        "gf": float(np.average(gf, weights=w)),
        "ga": float(np.average(ga, weights=w)),
        "form": float(np.average(pts / 3, weights=w)),
        "draw": float(np.average((pts == 1).astype(float), weights=w)),
        "wins": sum(x["r"] == "W" for x in rows),
        "draws": sum(x["r"] == "D" for x in rows),
        "losses": sum(x["r"] == "L" for x in rows),
    }


def league_stats(matches, before=None):
    fs = [
        m for m in matches
        if finished(m)
        and (before is None or dt_key(m) < before)
    ]

    if not fs:
        return {
            "n": 0,
            "home_g": 1.45,
            "away_g": 1.15,
            "total_g": 2.60,
            "ht_ratio": 0.44,
            "draw": 0.27,
        }

    hg = []
    ag = []
    ht = []
    draws = 0

    for m in fs:
        f = m["score"]["fullTime"]
        hg.append(f["home"])
        ag.append(f["away"])
        draws += f["home"] == f["away"]

        h = m["score"].get("halfTime", {})
        if h.get("home") is not None and h.get("away") is not None:
            ht.append(h["home"] + h["away"])

    total_matches = max(len(hg), 1)
    total_goal_avg = float(np.mean(np.array(hg) + np.array(ag)))

    return {
        "n": len(fs),
        "home_g": float(np.mean(hg)),
        "away_g": float(np.mean(ag)),
        "total_g": total_goal_avg,
        "ht_ratio": float(clamp(
            np.mean(ht) / total_goal_avg
            if ht and total_goal_avg > 0
            else 0.44,
            0.35,
            0.55,
        )),
        "draw": float(draws / total_matches),
    }


def team_season_rows(matches, tid, before=None):
    return rows_before(matches, tid, before, None, 60)


# ============================================================
# POISSON + DIXON-COLES
# ============================================================

def poisson_probability(lam, k):
    lam = sf(lam)
    k = int(k)

    if lam is None or not math.isfinite(lam) or lam < 0 or k < 0:
        return 0.0

    if lam == 0:
        return 1.0 if k == 0 else 0.0

    p = math.exp(
        -lam
        + k * math.log(lam)
        - math.lgamma(k + 1)
    )

    return clamp(p, 0, 1)


def poisson_matrix(hl, al, n=8):
    a = np.array([
        poisson_probability(hl, i)
        for i in range(n + 1)
    ])

    b = np.array([
        poisson_probability(al, i)
        for i in range(n + 1)
    ])

    m = np.outer(a, b)
    s = m.sum()

    return m / s if s > 0 else np.zeros_like(m)


def dc_matrix(m, hl, al, rho=-0.055):
    m = m.copy()

    corr = {
        (0, 0): 1 - hl * al * rho,
        (0, 1): 1 + hl * rho,
        (1, 0): 1 + al * rho,
        (1, 1): 1 - rho,
    }

    for (h, a), v in corr.items():
        if h < m.shape[0] and a < m.shape[1]:
            m[h, a] *= clamp(v, 0.90, 1.10)

    m = np.maximum(m, 0)
    s = m.sum()

    return m / s if s > 0 else m


# ============================================================
# MARCHÉS
# ============================================================

def market_probs(m):
    r = {
        "1": 0.0,
        "X": 0.0,
        "2": 0.0,
        "BTTS Oui": 0.0,
        "Over 1.5": 0.0,
        "Over 2.5": 0.0,
        "Over 3.5": 0.0,
    }

    for h in range(m.shape[0]):
        for a in range(m.shape[1]):
            p = float(m[h, a])

            r["1" if h > a else "X" if h == a else "2"] += p

            if h > 0 and a > 0:
                r["BTTS Oui"] += p

            if h + a >= 2:
                r["Over 1.5"] += p

            if h + a >= 3:
                r["Over 2.5"] += p

            if h + a >= 4:
                r["Over 3.5"] += p

    r["1X"] = r["1"] + r["X"]
    r["X2"] = r["X"] + r["2"]
    r["12"] = r["1"] + r["2"]

    r["BTTS Non"] = 1 - r["BTTS Oui"]

    for n in ("1.5", "2.5", "3.5"):
        r["Under " + n] = 1 - r["Over " + n]

    return r


def exact_scores(m, n=10):
    z = [
        (f"{h}-{a}", float(m[h, a]))
        for h in range(m.shape[0])
        for a in range(m.shape[1])
    ]

    return sorted(
        z,
        key=lambda x: x[1],
        reverse=True,
    )[:n]


# ============================================================
# MODÈLE
# ============================================================

def team_strength(rows, lg, venue=None):
    # Shrinkage bayésien vers les moyennes de la ligue.
    s = stats(rows)
    n = s["n"]
    prior_n = 6.0

    if venue == "H":
        pg, pa = lg["home_g"], lg["away_g"]
    elif venue == "A":
        pg, pa = lg["away_g"], lg["home_g"]
    else:
        pg = lg["total_g"] / 2
        pa = pg

    gf = (n * s["gf"] + prior_n * pg) / (n + prior_n)
    ga = (n * s["ga"] + prior_n * pa) / (n + prior_n)

    return gf, ga, s


def build_lambdas(hrows, arows, hsrows, asrows, lg):
    hgf, hga, hst = team_strength(hrows, lg)
    agf, aga, ast = team_strength(arows, lg)

    hgf_h, hga_h, _ = team_strength(hsrows, lg, "H")
    agf_a, aga_a, _ = team_strength(asrows, lg, "A")

    league_h = max(lg["home_g"], 0.25)
    league_a = max(lg["away_g"], 0.20)
    league_half = max(lg["total_g"] / 2, 0.30)

    ha = (
        0.58 * hgf_h / league_h
        + 0.42 * agf / league_half
    )

    hd = (
        0.58 * aga_a / league_a
        + 0.42 * hga / league_half
    )

    aa = (
        0.58 * agf_a / league_a
        + 0.42 * agf / league_half
    )

    ad = (
        0.58 * hga_h / league_h
        + 0.42 * aga / league_half
    )

    hl = league_h * math.sqrt(
        max(ha, 0.20) * max(hd, 0.20)
    )

    al = league_a * math.sqrt(
        max(aa, 0.20) * max(ad, 0.20)
    )

    # Ajustement forme limité.
    hl *= clamp(0.93 + 0.14 * hst["form"], 0.90, 1.07)
    al *= clamp(0.93 + 0.14 * ast["form"], 0.90, 1.07)

    return clamp(hl, 0.20, 3.80), clamp(al, 0.15, 3.50)


def halftime_model(hl, al, lg):
    ratio = lg.get("ht_ratio", 0.44)

    return dc_matrix(
        poisson_matrix(
            hl * ratio,
            al * ratio,
            6,
        ),
        hl * ratio,
        al * ratio,
    )


def htft_from_models(ht, ft):
    r = {
        f"{x}/{y}": 0.0
        for x in "1X2"
        for y in "1X2"
    }

    # Transition empirique bornée.
    trans = {
        "1": {"1": 0.74, "X": 0.16, "2": 0.10},
        "X": {"1": 0.27, "X": 0.48, "2": 0.25},
        "2": {"1": 0.10, "X": 0.16, "2": 0.74},
    }

    ht_m = market_probs(ht)
    ft_m = market_probs(ft)

    for x in "1X2":
        for y in "1X2":
            r[f"{x}/{y}"] = ht_m[x] * trans[x][y]

    # Recalage sur la marge FT.
    for y in "1X2":
        s = sum(
            r[f"{x}/{y}"]
            for x in "1X2"
        )

        if s > 0:
            scale = ft_m[y] / s

            for x in "1X2":
                r[f"{x}/{y}"] *= scale

    return sorted(
        r.items(),
        key=lambda z: z[1],
        reverse=True,
    )


def h2h_signal(ms, hid, aid):
    hw = dr = aw = 0

    for m in ms:
        if not finished(m):
            continue

        f = m["score"]["fullTime"]
        mh = m.get("homeTeam", {}).get("id")
        ma = m.get("awayTeam", {}).get("id")

        if mh == hid and ma == aid:
            x, y = f["home"], f["away"]
        elif mh == aid and ma == hid:
            x, y = f["away"], f["home"]
        else:
            continue

        if x > y:
            hw += 1
        elif x == y:
            dr += 1
        else:
            aw += 1

    n = hw + dr + aw

    return {
        "n": n,
        "home": hw / n if n else 0.50,
        "draw": dr / n if n else 0.25,
        "away": aw / n if n else 0.25,
        "hw": hw,
        "dr": dr,
        "aw": aw,
    }


def apply_h2h(m, hl, al, h2):
    # H2H volontairement très faible.
    if h2["n"] < 4:
        return m

    adj = clamp(
        (h2["home"] - h2["away"]) * 0.035,
        -0.025,
        0.025,
    )

    out = m.copy()

    for h in range(out.shape[0]):
        for a in range(out.shape[1]):
            if h > a:
                out[h, a] *= 1 + adj
            elif h < a:
                out[h, a] *= 1 - adj

    return out / out.sum()


# ============================================================
# ANALYSE D'UN MATCH
# ============================================================

def analyze_match(m):
    code = m.get("competition", {}).get("code", "")

    season_start = (
        m.get("season", {}).get("startDate", "")
    )

    try:
        season = int(season_start[:4])
    except Exception:
        season = date.today().year

    allm = season_matches(code, season)

    hid = m.get("homeTeam", {}).get("id")
    aid = m.get("awayTeam", {}).get("id")
    before = m.get("utcDate", "")

    lg = league_stats(allm, before)

    hrows = team_season_rows(
        allm, hid, before
    )

    arows = team_season_rows(
        allm, aid, before
    )

    hsrows = rows_before(
        allm, hid, before, "H", 10
    )

    asrows = rows_before(
        allm, aid, before, "A", 10
    )

    hl, al = build_lambdas(
        hrows,
        arows,
        hsrows,
        asrows,
        lg,
    )

    ft = dc_matrix(
        poisson_matrix(hl, al),
        hl,
        al,
    )

    h2 = h2h_signal(
        h2h(m.get("id")),
        hid,
        aid,
    )

    ft = apply_h2h(
        ft,
        hl,
        al,
        h2,
    )

    ht = halftime_model(
        hl,
        al,
        lg,
    )

    mk = market_probs(ft)
    htmk = market_probs(ht)

    scores = exact_scores(ft, 10)
    ht_scores = exact_scores(ht, 8)
    htft = htft_from_models(ht, ft)

    one = max(
        (
            ("1", mk["1"]),
            ("X", mk["X"]),
            ("2", mk["2"]),
        ),
        key=lambda z: z[1],
    )

    n = min(
        hrows.__len__(),
        arows.__len__(),
    )

    quality = int(clamp(
        35
        + min(lg["n"], 100) * 0.15
        + min(n, 20) * 1.2
        + (8 if h2["n"] >= 5 else 0),
        0,
        85,
    ))

    ordered = sorted(
        [mk["1"], mk["X"], mk["2"]],
        reverse=True,
    )

    spread = one[1] - ordered[1]

    confidence = int(clamp(
        50 + 30 * spread + 0.25 * quality,
        50,
        90,
    ))

    return {
        "home": m.get("homeTeam", {}).get(
            "name", "Domicile"
        ),
        "away": m.get("awayTeam", {}).get(
            "name", "Extérieur"
        ),
        "competition": m.get(
            "competition", {}
        ).get("name", ""),
        "date": before,
        "status": m.get("status", ""),
        "hl": hl,
        "al": al,
        "league": lg,
        "hf": stats(hrows),
        "af": stats(arows),
        "hs": stats(hsrows),
        "as": stats(asrows),
        "h2": h2,
        "mk": mk,
        "htmk": htmk,
        "scores": scores,
        "htscores": ht_scores,
        "htft": htft,
        "one": one,
        "quality": quality,
        "confidence": confidence,
    }


# ============================================================
# RECHERCHE DES MATCHS
# ============================================================

def find_matches(d, codes):
    # Aujourd'hui : endpoint global puis filtrage local.
    if d == date.today():
        r = api(
            "/matches",
            (),
            FOOTBALL_DATA_KEY,
        )

        ms = (
            (r["data"] or {}).get("matches", [])
            if r["status"] == 200
            else []
        )

        return sorted(
            [
                m for m in ms
                if m.get("competition", {}).get("code") in codes
                and m.get("utcDate", "")[:10] == d.isoformat()
            ],
            key=dt_key,
        )

    # Autres dates : une compétition à la fois.
    out = []
    seen = set()

    for c in codes:
        r = api(
            f"/competitions/{c}/matches",
            (("season", str(d.year)),),
            FOOTBALL_DATA_KEY,
        )

        matches = (
            (r["data"] or {}).get("matches", [])
            if r["status"] == 200
            else []
        )

        for m in matches:
            if (
                m.get("utcDate", "")[:10] == d.isoformat()
                and m.get("id") not in seen
            ):
                seen.add(m.get("id"))
                out.append(m)

    return sorted(
        out,
        key=dt_key,
    )


# ============================================================
# BACKTEST
# ============================================================

def outcome(m):
    f = m["score"]["fullTime"]
    h, a = f["home"], f["away"]

    return (
        0 if h > a
        else 1 if h == a
        else 2
    )


def brier(probs, y):
    return sum(
        (probs[i] - (1 if i == y else 0)) ** 2
        for i in range(3)
    )


def logloss(probs, y):
    return -math.log(
        clamp(probs[y], 1e-6, 1)
    )


def backtest(
    code,
    season_year,
    limit_matches=220,
):
    ms = [
        m for m in season_matches(
            code,
            season_year,
        )
        if finished(m)
    ]

    ms = sorted(
        ms,
        key=dt_key,
    )[-limit_matches:]

    preds = []
    y = []
    br = []
    ll = []

    exact_hits = 0
    o25_hits = 0
    btts_hits = 0

    o25_n = 0
    btts_n = 0

    for m in ms:
        before = m.get("utcDate", "")

        prior = [
            x for x in ms
            if dt_key(x) < before
        ]

        if len(prior) < 30:
            continue

        lg = league_stats(prior)

        hid = m["homeTeam"]["id"]
        aid = m["awayTeam"]["id"]

        hrows = team_season_rows(
            prior,
            hid,
            before,
        )

        arows = team_season_rows(
            prior,
            aid,
            before,
        )

        hsrows = rows_before(
            prior,
            hid,
            before,
            "H",
            10,
        )

        asrows = rows_before(
            prior,
            aid,
            before,
            "A",
            10,
        )

        if len(hrows) < 3 or len(arows) < 3:
            continue

        hl, al = build_lambdas(
            hrows,
            arows,
            hsrows,
            asrows,
            lg,
        )

        mat = dc_matrix(
            poisson_matrix(hl, al),
            hl,
            al,
        )

        mk = market_probs(mat)

        probs = [
            mk["1"],
            mk["X"],
            mk["2"],
        ]

        yy = outcome(m)

        preds.append(probs)
        y.append(yy)
        br.append(brier(probs, yy))
        ll.append(logloss(probs, yy))

        sc = exact_scores(mat, 1)[0][0]

        actual = (
            f'{m["score"]["fullTime"]["home"]}-'
            f'{m["score"]["fullTime"]["away"]}'
        )

        exact_hits += sc == actual

        actual_o25 = (
            m["score"]["fullTime"]["home"]
            + m["score"]["fullTime"]["away"]
        ) >= 3

        o25_hits += (
            (mk["Over 2.5"] >= 0.5)
            == actual_o25
        )

        o25_n += 1

        actual_btts = (
            m["score"]["fullTime"]["home"] > 0
            and m["score"]["fullTime"]["away"] > 0
        )

        btts_hits += (
            (mk["BTTS Oui"] >= 0.5)
            == actual_btts
        )

        btts_n += 1

    if not preds:
        return {"n": 0}

    arr = np.array(preds)

    acc = float(
        np.mean(
            np.argmax(arr, axis=1)
            == np.array(y)
        )
    )

    return {
        "n": len(y),
        "accuracy": acc,
        "brier": float(np.mean(br)),
        "logloss": float(np.mean(ll)),
        "exact_top1": exact_hits / len(y),
        "over25_acc": o25_hits / max(o25_n, 1),
        "btts_acc": btts_hits / max(btts_n, 1),
    }


# ============================================================
# INTERFACE
# ============================================================

st.title(
    "⚽ RODRIGUE PRO FOOTBALL AI — V21 VALIDATED"
)

st.caption(
    "Modèle : données disponibles avant le match + "
    "shrinkage bayésien + forme pondérée + domicile/extérieur "
    "+ Poisson corrigé + MT/FT + backtest. "
    "Les probabilités sont des estimations statistiques."
)

# ------------------------------------------------------------
# STATUS API
# ------------------------------------------------------------

api_status = api(
    "/competitions/PL",
    (),
    FOOTBALL_DATA_KEY,
)

sc = api_status["status"]

if sc == 200:
    st.success(
        "🟢 API football-data.org OK"
        f" · appels restants : "
        f'{api_status.get("remaining") or "N/D"}'
    )

elif sc == 403:
    st.error(
        "🔴 API HTTP 403 — accès refusé."
    )
    st.info(
        "La requête est maintenant correctement authentifiée. "
        "Si le 403 continue après cette version, le problème "
        "vient de l'autorisation de la clé/du compte pour cette "
        "ressource et non d'un ancien cache."
    )

elif sc == 401:
    st.error(
        "🔴 API HTTP 401 — clé API non reconnue."
    )

elif sc == 429:
    st.error(
        "🔴 API HTTP 429 — quota de requêtes atteint."
    )

else:
    st.error(
        "🔴 API indisponible : "
        + api_error_message(api_status)
    )

# ------------------------------------------------------------
# RESET CACHE
# ------------------------------------------------------------

if st.button(
    "🔄 RÉINITIALISER LE CACHE API",
    use_container_width=True,
):
    st.cache_data.clear()
    st.session_state["matches_v21"] = []
    st.success(
        "Cache réinitialisé. Recharge la page puis relance la recherche."
    )
    st.rerun()


# ------------------------------------------------------------
# RECHERCHE
# ------------------------------------------------------------

c1, c2 = st.columns(2)

with c1:
    d = st.date_input(
        "📅 Date",
        date.today(),
    )

with c2:
    names = st.multiselect(
        "🏆 Compétitions",
        list(COMPETITIONS),
        default=list(COMPETITIONS),
    )

codes = tuple(
    COMPETITIONS[x]
    for x in names
)

if st.button(
    "🚀 CHERCHER LES MATCHS",
    type="primary",
    use_container_width=True,
):
    if not codes:
        st.warning(
            "Sélectionne au moins une compétition."
        )

    elif api_status["status"] != 200:
        st.error(
            "Recherche arrêtée : API/token indisponible."
        )

    else:
        with st.spinner(
            "Recherche des matchs..."
        ):
            ms = find_matches(
                d,
                codes,
            )

        st.session_state["matches_v21"] = ms

        if ms:
            st.success(
                f"✅ {len(ms)} match(s) trouvé(s)."
            )
        else:
            st.warning(
                "⚠️ Aucun match trouvé pour cette date "
                "dans les compétitions sélectionnées."
            )


# ------------------------------------------------------------
# MATCHS
# ------------------------------------------------------------

for i, m in enumerate(
    st.session_state.get(
        "matches_v21",
        [],
    )
):
    h = m.get(
        "homeTeam",
        {},
    ).get(
        "name",
        "?",
    )

    aw = m.get(
        "awayTeam",
        {},
    ).get(
        "name",
        "?",
    )

    comp = m.get(
        "competition",
        {},
    ).get(
        "name",
        "",
    )

    match_id = m.get(
        "id",
        i,
    )

    with st.expander(
        f"⚽ {h} — {aw} | {comp}"
    ):
        st.caption(
            f'{m.get("status", "")} · '
            f'{m.get("utcDate", "")}'
        )

        if st.button(
            "🧠 ANALYSER CE MATCH",
            key=f"v21_{match_id}",
            use_container_width=True,
        ):
            with st.spinner(
                "Analyse sans fuite de données..."
            ):
                try:
                    st.session_state[
                        f"r21_{match_id}"
                    ] = analyze_match(m)
                except Exception as e:
                    st.error(
                        f"Erreur pendant l'analyse : {e}"
                    )

        r = st.session_state.get(
            f"r21_{match_id}"
        )

        if not r:
            continue

        a1, a2, a3, a4 = st.columns(4)

        a1.metric(
            "xG modèle",
            f'{r["hl"]:.2f} — {r["al"]:.2f}',
        )

        a2.metric(
            "Qualité données",
            f'{r["quality"]}/85',
        )

        a3.metric(
            "Confiance modèle",
            f'{r["confidence"]}%',
        )

        a4.metric(
            "H2H",
            str(r["h2"]["n"]),
        )

        st.info(
            "ℹ️ La confiance mesure la qualité/séparation "
            "du modèle ; elle n'est pas une garantie de gain."
        )

        st.success(
            f'🎯 1X2 principal : **{r["one"][0]}** '
            f'({pct(r["one"][1])})'
        )

        # ----------------------------------------------------
        # FORME
        # ----------------------------------------------------

        st.subheader(
            "📈 FORME RÉCENTE"
        )

        st.dataframe(
            pd.DataFrame([
                {
                    "Équipe": h,
                    "N": r["hf"]["n"],
                    "V-N-D": (
                        f'{r["hf"]["wins"]}-'
                        f'{r["hf"]["draws"]}-'
                        f'{r["hf"]["losses"]}'
                    ),
                    "GF/m": fmt(r["hf"]["gf"]),
                    "GA/m": fmt(r["hf"]["ga"]),
                },
                {
                    "Équipe": aw,
                    "N": r["af"]["n"],
                    "V-N-D": (
                        f'{r["af"]["wins"]}-'
                        f'{r["af"]["draws"]}-'
                        f'{r["af"]["losses"]}'
                    ),
                    "GF/m": fmt(r["af"]["gf"]),
                    "GA/m": fmt(r["af"]["ga"]),
                },
            ]),
            use_container_width=True,
            hide_index=True,
        )

        # ----------------------------------------------------
        # MARCHÉS
        # ----------------------------------------------------

        st.subheader(
            "🎯 MARCHÉS"
        )

        keys = [
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

        st.dataframe(
            pd.DataFrame([
                {
                    "Marché": k,
                    "Probabilité modèle": pct(
                        r["mk"][k]
                    ),
                }
                for k in keys
            ]),
            use_container_width=True,
            hide_index=True,
        )

        # ----------------------------------------------------
        # SCORES
        # ----------------------------------------------------

        st.subheader(
            "🔢 SCORES EXACTS"
        )

        st.dataframe(
            pd.DataFrame([
                {
                    "Score": s,
                    "Probabilité": pct(p),
                }
                for s, p in r["scores"]
            ]),
            use_container_width=True,
            hide_index=True,
        )

        # ----------------------------------------------------
        # MI-TEMPS
        # ----------------------------------------------------

        st.subheader(
            "⏱️ MI-TEMPS"
        )

        st.dataframe(
            pd.DataFrame([
                {
                    "Score MT": s,
                    "Probabilité": pct(p),
                }
                for s, p in r["htscores"]
            ]),
            use_container_width=True,
            hide_index=True,
        )

        # ----------------------------------------------------
        # MT / FT
        # ----------------------------------------------------

        st.subheader(
            "🔄 MT / FT"
        )

        st.dataframe(
            pd.DataFrame([
                {
                    "MT/FT": s,
                    "Probabilité": pct(p),
                }
                for s, p in r["htft"]
            ]),
            use_container_width=True,
            hide_index=True,
        )

        # ----------------------------------------------------
        # COTES
        # ----------------------------------------------------

        st.subheader(
            "💰 COTES : TEST DE VALEUR"
        )

        cols = st.columns(4)
        odds = {}

        for j, k in enumerate(
            ["1", "X", "2", "Over 2.5"]
        ):
            with cols[j]:
                odds[k] = st.number_input(
                    f"Cote {k}",
                    0.0,
                    100.0,
                    0.0,
                    0.01,
                    key=f"odd21_{match_id}_{k}",
                )

        rows = []

        for k, o in odds.items():
            if o > 1:
                evv = r["mk"][k] * o - 1

                rows.append({
                    "Marché": k,
                    "p modèle": pct(
                        r["mk"][k]
                    ),
                    "Cote": f"{o:.2f}",
                    "EV théorique": (
                        f"{100 * evv:.1f}%"
                    ),
                    "Décision": (
                        "À ÉVITER"
                        if evv <= 0
                        else "VALEUR POSSIBLE — À VALIDER"
                    ),
                })

        st.dataframe(
            pd.DataFrame(rows)
            if rows
            else pd.DataFrame([
                {
                    "Marché": "—",
                    "Décision": "Aucune cote saisie",
                }
            ]),
            use_container_width=True,
            hide_index=True,
        )


# ============================================================
# BACKTEST
# ============================================================

st.divider()

st.subheader(
    "🧪 BACKTEST — AVANT DE FAIRE CONFIANCE AU MODÈLE"
)

bc1, bc2, bc3 = st.columns(3)

with bc1:
    bt_comp = st.selectbox(
        "Compétition",
        list(COMPETITIONS),
        key="bt_comp",
    )

with bc2:
    bt_year = st.number_input(
        "Saison (année de début)",
        2018,
        2030,
        date.today().year,
        key="bt_year",
    )

with bc3:
    bt_limit = st.number_input(
        "Matchs max",
        50,
        500,
        220,
        10,
        key="bt_limit",
    )

if st.button(
    "🧪 LANCER LE BACKTEST",
    use_container_width=True,
):
    with st.spinner(
        "Backtest chronologique — "
        "aucune donnée future utilisée..."
    ):
        try:
            res = backtest(
                COMPETITIONS[bt_comp],
                int(bt_year),
                int(bt_limit),
            )

            if res.get("n", 0):
                st.dataframe(
                    pd.DataFrame([{
                        "Échantillon": res["n"],
                        "Accuracy 1X2": pct(
                            res["accuracy"]
                        ),
                        "Brier (↓ meilleur)": fmt(
                            res["brier"]
                        ),
                        "Log loss (↓ meilleur)": fmt(
                            res["logloss"]
                        ),
                        "Score exact top-1": pct(
                            res["exact_top1"]
                        ),
                        "Over 2.5": pct(
                            res["over25_acc"]
                        ),
                        "BTTS": pct(
                            res["btts_acc"]
                        ),
                    }]),
                    use_container_width=True,
                    hide_index=True,
                )

                st.warning(
                    "Le backtest mesure le comportement historique "
                    "du modèle ; il ne garantit pas les prochains matchs."
                )

            else:
                st.warning(
                    "Pas assez de données historiques "
                    "pour calculer un backtest fiable."
                )

        except Exception as e:
            st.error(
                f"Erreur du backtest : {e}"
            )


# ============================================================
# FOOTER
# ============================================================

st.caption(
    "Data provided by football-data.org · "
    "Rodrigue Pro Football AI V21"
)
