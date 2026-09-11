
# ============================================================
# RODRIGUE PRO FOOTBALL AI — V10 ULTIMATE — VERSION CORRIGÉE
# ============================================================
# Sources :
#   - football-data.org : matchs, résultats, classement
#   - SerpApi / Google : contexte, blessures, suspensions,
#     statistiques détaillées et événements disponibles sur le Web
#
# CORRECTIONS PRINCIPALES :
#   1) Une seule requête /v4/matches pour la date, puis filtrage local.
#   2) Pour la date du jour, /v4/matches est appelé SANS filtre de date,
#      puis les matchs sont filtrés localement. Cela évite tout problème lié
#      aux filtres dateFrom/dateTo.
#   3) Pour une autre date, le code utilise les compétitions sélectionnées
#      avec le filtre season=AAAA, puis filtre la date localement.
#   4) Diagnostic et recherche réutilisent exactement les mêmes résultats en cache.
# ============================================================

import math
import re
from datetime import date, timedelta

import numpy as np
import pandas as pd
import requests
import streamlit as st


# ============================================================
# CONFIGURATION
# ============================================================

FOOTBALL_DATA_KEY = st.secrets["FOOTBALL_DATA_KEY"]
SERPAPI_KEY = st.secrets["SERPAPI_KEY"]

API_BASE = "https://api.football-data.org/v4"
SERP_URL = "https://serpapi.com/search.json"

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

st.set_page_config(
    page_title="Rodrigue Pro Football AI V10",
    page_icon="⚽",
    layout="wide",
)

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "Rodrigue-Pro-Football-AI-V10",
    "Accept": "application/json",
})


# ============================================================
# OUTILS
# ============================================================

def safe_float(value):
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def percent(value):
    if value is None:
        return "N/D"
    return f"{value * 100:.1f}%"


def number(value):
    if value is None:
        return "N/D"
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value)


# ============================================================
# FOOTBALL-DATA.ORG
# ============================================================

@st.cache_data(ttl=300, show_spinner=False)
def _football_request(endpoint, params_items=()):
    """Effectue UNE requête et mémorise aussi les erreurs pendant 5 min."""
    params = dict(params_items)
    try:
        response = SESSION.get(
            API_BASE + endpoint,
            headers={"X-Auth-Token": FOOTBALL_DATA_KEY},
            params=params,
            timeout=25,
        )

        raw_text = response.text or ""
        try:
            payload = response.json()
        except ValueError:
            payload = None

        error = ""
        if isinstance(payload, dict):
            error = str(payload.get("error", "") or "")
        if not error and raw_text and response.status_code != 200:
            error = raw_text[:500]

        return {
            "status": response.status_code,
            "data": payload if response.status_code == 200 else None,
            "error": error,
            "raw": raw_text[:500],
            "authenticated_client": response.headers.get("X-Authenticated-Client", ""),
            "remaining": response.headers.get("X-Requests-Available-Minute", ""),
            "reset": response.headers.get("X-RequestCounter-Reset", ""),
        }

    except requests.RequestException as exc:
        return {
            "status": 0,
            "data": None,
            "error": str(exc),
        }


@st.cache_data(ttl=300, show_spinner=False)
def validate_football_api():
    """Teste uniquement l'authentification avec une ressource officielle simple."""
    return _football_request("/competitions/PL", ())


def api_auth_ok(result):
    return bool(result and result.get("status") == 200)


def api_error_message(result):
    if not result:
        return "Aucune réponse reçue de football-data.org."
    detail = (result.get("error") or result.get("raw") or "").strip()
    if detail.startswith("{") and detail.endswith("}"):
        try:
            payload = requests.models.complexjson.loads(detail)
            detail = str(payload.get("message") or payload.get("error") or detail)
        except Exception:
            pass
    if len(detail) > 350:
        detail = detail[:350] + "…"
    return detail or f"Réponse HTTP {result.get('status', 0)} sans détail."


def football_get(endpoint, params=None, show_error=True):
    """GET football-data.org sans répéter inutilement les appels."""
    params_items = tuple(sorted((params or {}).items()))
    result = _football_request(endpoint, params_items)
    status = result["status"]

    if status == 200:
        return result["data"]

    if not show_error:
        return None

    detail = result.get("error", "")

    if status == 400:
        st.warning(
            f"⚠️ Requête football-data.org refusée (400). {detail}".strip()
        )
    elif status == 401:
        st.error(
            "❌ Clé football-data.org non authentifiée (401). "
            "Vérifie le token dans le code."
        )
    elif status == 403:
        st.warning(
            f"⚠️ Ressource non autorisée (403). {detail}".strip()
        )
    elif status == 404:
        st.warning(f"⚠️ Ressource introuvable : {endpoint}")
    elif status == 429:
        st.warning(
            "⚠️ Limite football-data.org atteinte (429). "
            "Le code réutilise maintenant les résultats en cache pour "
            "éviter les appels répétés."
        )
    elif status == 0:
        st.warning(f"🌐 Erreur réseau football-data.org : {detail}")
    else:
        st.warning(
            f"⚠️ football-data.org a répondu HTTP {status}. {detail}".strip()
        )

    return None


def football_status(endpoint, params=None):
    """Retourne le statut détaillé sans déclencher de seconde requête."""
    params_items = tuple(sorted((params or {}).items()))
    return _football_request(endpoint, params_items)


# ============================================================
# SERPAPI
# ============================================================

def serp_search(query, num=8):
    params = {
        "engine": "google",
        "q": query,
        "api_key": SERPAPI_KEY,
        "hl": "fr",
        "gl": "cm",
        "num": num,
    }

    try:
        response = SESSION.get(
            SERP_URL,
            params=params,
            timeout=25,
        )

        if response.status_code != 200:
            return []

        data = response.json()
        return data.get("organic_results", [])

    except (requests.RequestException, ValueError):
        return []


# ============================================================
# MATCHS — MOTEUR CENTRAL SANS RÉPÉTITION
# ============================================================

@st.cache_data(ttl=300, show_spinner=False)
def get_matches_date_once(selected_date, competition_codes=()):
    """Charge les matchs seulement après validation de l'API.

    L'authentification est testée une seule fois sur /competitions/PL.
    Si le token est refusé, aucun appel de match n'est lancé.
    """
    codes = tuple(competition_codes or ())
    target = selected_date.isoformat()

    auth = validate_football_api()
    if not api_auth_ok(auth):
        return {
            "mode": "auth_failed",
            "target_date": target,
            "auth": auth,
            "results": [],
        }

    # Cas principal : aujourd'hui -> une seule requête globale.
    if selected_date == date.today():
        return {
            "mode": "today_global",
            "target_date": target,
            "results": [
                ("ALL", _football_request("/matches", ()))
            ],
        }

    # Autre date -> saison par compétition, puis filtrage local.
    season = str(selected_date.year)
    results = []
    for code in codes:
        results.append((
            code,
            _football_request(
                f"/competitions/{code}/matches",
                (("season", season),),
            ),
        ))
        # Ne jamais gaspiller le quota après une erreur d'authentification
        # ou de limitation.
        if results[-1][1]["status"] in (401, 429):
            break

    return {
        "mode": "season_by_competition",
        "target_date": target,
        "results": results,
    }


def _filter_matches_by_competition(matches, competition_codes):
    wanted = set(competition_codes)
    selected = []
    seen = set()

    for match in matches or []:
        code = (
            match.get("competition", {})
            .get("code")
        )
        if code not in wanted:
            continue

        match_id = match.get("id")
        key = match_id if match_id is not None else (
            match.get("utcDate", ""),
            match.get("homeTeam", {}).get("id"),
            match.get("awayTeam", {}).get("id"),
        )

        if key in seen:
            continue
        seen.add(key)
        selected.append(match)

    return sorted(
        selected,
        key=lambda m: m.get("utcDate", ""),
    )


@st.cache_data(ttl=300, show_spinner=False)
def fetch_matches(selected_date, competition_codes):
    """Récupère les matchs une seule fois et filtre localement."""
    codes = tuple(competition_codes or ())
    if not codes:
        return []

    bundle = get_matches_date_once(selected_date, codes)
    target = bundle["target_date"]
    all_matches = []

    for code, result in bundle["results"]:
        if result["status"] != 200:
            continue
        all_matches.extend((result.get("data") or {}).get("matches", []))

    # Filtrage strict de la date + compétition.
    wanted = set(codes)
    selected = []
    seen = set()
    for match in all_matches:
        mcode = match.get("competition", {}).get("code")
        mdate = match.get("utcDate", "")[:10]
        if mcode not in wanted or mdate != target:
            continue

        key = match.get("id") or (
            match.get("utcDate", ""),
            match.get("homeTeam", {}).get("id"),
            match.get("awayTeam", {}).get("id"),
        )
        if key in seen:
            continue
        seen.add(key)
        selected.append(match)

    return sorted(selected, key=lambda m: m.get("utcDate", ""))


def diagnostic_competitions(selected_date, competition_codes):
    """Diagnostic : authentification d'abord, puis matchs seulement si OK."""
    codes = tuple(competition_codes or ())
    if not codes:
        return []

    auth = validate_football_api()
    if not api_auth_ok(auth):
        return [{
            "Test": "AUTHENTIFICATION API",
            "HTTP": auth.get("status", 0),
            "Statut": "TOKEN REFUSÉ",
            "Matchs": 0,
            "Détail": api_error_message(auth),
            "Client API": auth.get("authenticated_client", ""),
            "Appels restants": auth.get("remaining", ""),
        }]

    bundle = get_matches_date_once(selected_date, codes)
    target = bundle["target_date"]
    rows = [{
        "Test": "AUTHENTIFICATION API",
        "HTTP": auth.get("status", 0),
        "Statut": "TOKEN ACCEPTÉ",
        "Matchs": "—",
        "Détail": "Le token est accepté par /competitions/PL.",
        "Client API": auth.get("authenticated_client", ""),
        "Appels restants": auth.get("remaining", ""),
    }]

    for request_code, result in bundle["results"]:
        status = result["status"]
        detail = result.get("error", "")
        data = result.get("data") or {}
        matches = data.get("matches", [])

        if request_code == "ALL":
            for code in codes:
                count = sum(
                    1 for match in matches
                    if match.get("competition", {}).get("code") == code
                    and match.get("utcDate", "")[:10] == target
                )
                rows.append({
                    "Test": code,
                    "HTTP": status,
                    "Statut": "OK — requête unique" if status == 200 else "Erreur",
                    "Matchs": count if status == 200 else 0,
                    "Détail": "Filtrage local" if status == 200 else (detail or "Réponse API sans détail"),
                    "Client API": result.get("authenticated_client", ""),
                    "Appels restants": result.get("remaining", ""),
                })
            continue

        count = sum(
            1 for match in matches
            if match.get("competition", {}).get("code") == request_code
            and match.get("utcDate", "")[:10] == target
        )
        rows.append({
            "Test": request_code,
            "HTTP": status,
            "Statut": "OK — saison + filtrage local" if status == 200 else "Erreur",
            "Matchs": count if status == 200 else 0,
            "Détail": (
                "Filtre season=%s ; date filtrée localement" % selected_date.year
                if status == 200 else (detail or "Réponse API sans détail")
            ),
            "Client API": result.get("authenticated_client", ""),
            "Appels restants": result.get("remaining", ""),
        })

    return rows

# ============================================================
# HISTORIQUE
# ============================================================

@st.cache_data(ttl=900, show_spinner=False)
def fetch_team_history(team_id, limit=12):
    if not team_id:
        return []

    data = football_get(
        f"/teams/{team_id}/matches",
        {
            "status": "FINISHED",
            "limit": limit,
        },
        show_error=False,
    )

    if not data:
        return []

    return data.get("matches", [])


# ============================================================
# CLASSEMENT
# ============================================================

@st.cache_data(ttl=1800, show_spinner=False)
def fetch_standings(competition_code):
    if not competition_code:
        return []

    data = football_get(
        f"/competitions/{competition_code}/standings",
        show_error=False,
    )

    if not data:
        return []

    standings = data.get("standings", [])

    if not standings:
        return []

    # TOTAL en priorité.
    for standing in standings:
        if standing.get("type") == "TOTAL":
            return standing.get("table", [])

    return standings[0].get("table", [])


def get_standing(table, team_id):
    for row in table:
        if row.get("team", {}).get("id") == team_id:
            return row
    return None


# ============================================================
# RÉSULTAT ÉQUIPE
# ============================================================

def team_result(match, team_id):
    home = match.get("homeTeam", {})
    away = match.get("awayTeam", {})
    score = match.get("score", {})
    full = score.get("fullTime", {})

    hg = full.get("home")
    ag = full.get("away")

    if hg is None or ag is None:
        return None

    if home.get("id") == team_id:
        gf, ga = hg, ag
        opponent = away.get("name")
    elif away.get("id") == team_id:
        gf, ga = ag, hg
        opponent = home.get("name")
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
        "gf": gf,
        "ga": ga,
        "date": match.get("utcDate", ""),
        "opponent": opponent,
    }


# ============================================================
# FORME
# ============================================================

def analyze_form(matches, team_id, last_n=8):
    results = []

    for match in matches:
        result = team_result(match, team_id)
        if result:
            results.append(result)

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
            "gf_avg": 0,
            "ga_avg": 0,
            "points": 0,
            "points_avg": 0,
            "form_score": 0,
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


# ============================================================
# DOMICILE / EXTÉRIEUR
# ============================================================

def analyze_home_away(matches, team_id, home=True, last_n=8):
    filtered = []

    for match in matches:
        home_id = match.get("homeTeam", {}).get("id")
        away_id = match.get("awayTeam", {}).get("id")

        if home and home_id == team_id:
            filtered.append(match)
        elif not home and away_id == team_id:
            filtered.append(match)

    return analyze_form(filtered, team_id, last_n)


# ============================================================
# POISSON
# ============================================================

def poisson_probability(lam, goals):
    try:
        lam = float(lam)
        goals = int(goals)
    except (TypeError, ValueError, OverflowError):
        return 0.0

    if not math.isfinite(lam) or lam < 0:
        return 0.0

    if goals < 0:
        return 0.0

    # Cas λ = 0
    if lam == 0.0:
        return 1.0 if goals == 0 else 0.0

    try:
        log_probability = (
            -lam
            + goals * math.log(lam)
            - math.lgamma(goals + 1)
        )

        probability = math.exp(log_probability)

    except (ValueError, OverflowError):
        return 0.0

    if not math.isfinite(probability):
        return 0.0

    return max(0.0, min(1.0, probability))


def poisson_matrix(home_lambda, away_lambda, max_goals=7):
    try:
        home_lambda = float(home_lambda)
        away_lambda = float(away_lambda)
        max_goals = int(max_goals)
    except (TypeError, ValueError, OverflowError):
        raise ValueError(
            "Paramètres Poisson invalides."
        )

    if not math.isfinite(home_lambda) or home_lambda < 0:
        raise ValueError("home_lambda invalide.")

    if not math.isfinite(away_lambda) or away_lambda < 0:
        raise ValueError("away_lambda invalide.")

    if max_goals < 1:
        raise ValueError("max_goals doit être >= 1.")

    # Probabilités de buts de chaque équipe
    home_probs = np.array([
        poisson_probability(home_lambda, h)
        for h in range(max_goals + 1)
    ], dtype=float)

    away_probs = np.array([
        poisson_probability(away_lambda, a)
        for a in range(max_goals + 1)
    ], dtype=float)

    # Matrice des scores exacts
    matrix = np.outer(home_probs, away_probs)

    # Nettoyage des valeurs numériques
    matrix = np.nan_to_num(
        matrix,
        nan=0.0,
        posinf=0.0,
        neginf=0.0
    )

    matrix = np.maximum(matrix, 0.0)

    # Normalisation
    total = float(matrix.sum())

    if total <= 0.0 or not math.isfinite(total):
        raise ValueError(
            "Matrice de Poisson invalide."
        )

    matrix /= total

    # Contrôle final
    final_total = float(matrix.sum())

    if final_total <= 0.0 or not math.isfinite(final_total):
        raise ValueError(
            "Erreur de normalisation de la matrice."
        )

    matrix /= final_total

    return matrix

# ============================================================
# MARCHÉS
# ============================================================

def calculate_markets(matrix):
    home_win = 0.0
    draw = 0.0
    away_win = 0.0

    btts = 0.0
    over15 = 0.0
    over25 = 0.0
    over35 = 0.0

    for h in range(matrix.shape[0]):
        for a in range(matrix.shape[1]):
            p = matrix[h, a]

            if h > a:
                home_win += p
            elif h == a:
                draw += p
            else:
                away_win += p

            if h >= 1 and a >= 1:
                btts += p

            if h + a >= 2:
                over15 += p

            if h + a >= 3:
                over25 += p

            if h + a >= 4:
                over35 += p

    return {
        "1": home_win,
        "X": draw,
        "2": away_win,
        "1X": home_win + draw,
        "X2": draw + away_win,
        "12": home_win + away_win,
        "BTTS Oui": btts,
        "BTTS Non": 1 - btts,
        "Over 1.5": over15,
        "Under 1.5": 1 - over15,
        "Over 2.5": over25,
        "Under 2.5": 1 - over25,
        "Over 3.5": over35,
        "Under 3.5": 1 - over35,
    }


# ============================================================
# SCORES EXACTS
# ============================================================

def exact_scores(matrix, limit=10):
    scores = []

    for h in range(matrix.shape[0]):
        for a in range(matrix.shape[1]):
            scores.append(
                (f"{h}-{a}", matrix[h, a])
            )

    scores.sort(
        key=lambda x: x[1],
        reverse=True,
    )

    return scores[:limit]


# ============================================================
# MI-TEMPS
# ============================================================

def half_time_model(home_lambda, away_lambda):
    matrix = poisson_matrix(
        home_lambda * 0.44,
        away_lambda * 0.44,
        5,
    )

    return {
        "matrix": matrix,
        "markets": calculate_markets(matrix),
        "scores": exact_scores(matrix, 6),
    }


# ============================================================
# MT / FT
# ============================================================

def htft_model(home_lambda, away_lambda):
    ht = half_time_model(
        home_lambda,
        away_lambda,
    )

    ft = poisson_matrix(
        home_lambda,
        away_lambda,
        7,
    )

    combinations = {}

    for ht_home in range(ht["matrix"].shape[0]):
        for ht_away in range(ht["matrix"].shape[1]):
            ht_probability = ht["matrix"][ht_home, ht_away]

            ht_result = (
                "1"
                if ht_home > ht_away
                else "X"
                if ht_home == ht_away
                else "2"
            )

            for ft_home in range(ft.shape[0]):
                for ft_away in range(ft.shape[1]):
                    ft_probability = ft[ft_home, ft_away]

                    ft_result = (
                        "1"
                        if ft_home > ft_away
                        else "X"
                        if ft_home == ft_away
                        else "2"
                    )

                    key = f"{ht_result}/{ft_result}"

                    combinations[key] = (
                        combinations.get(key, 0)
                        + ht_probability * ft_probability
                    )

    total = sum(combinations.values())

    if total:
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
# RECHERCHE STATISTIQUES DÉTAILLÉES
# ============================================================

STAT_QUERY_TYPES = {
    "corners": ["corners", "corner stats"],
    "cartons": ["yellow cards", "red cards", "cartons"],
    "tirs": ["shots", "tirs"],
    "tirs_cadres": ["shots on target", "tirs cadrés"],
    "possession": ["possession"],
    "fautes": ["fouls", "fautes"],
    "hors_jeu": ["offsides", "hors jeu"],
}


def search_detailed_stats(team_name):
    all_results = {}

    for stat_name, keywords in STAT_QUERY_TYPES.items():
        collected = []

        for keyword in keywords:
            query = (
                f'"{team_name}" football '
                f'{keyword} statistics'
            )

            results = serp_search(query, num=5)

            for result in results:
                collected.append({
                    "title": result.get("title", ""),
                    "snippet": result.get("snippet", ""),
                    "link": result.get("link", ""),
                })

        unique = {}

        for item in collected:
            key = (
                item["title"],
                item["snippet"],
            )
            unique[key] = item

        all_results[stat_name] = list(
            unique.values()
        )[:10]

    return all_results


# ============================================================
# EXTRACTION DE NOMBRES
# ============================================================

def extract_numbers(text):
    if not text:
        return []

    pattern = r"(?<!\w)(\d+(?:[.,]\d+)?)(?!\w)"
    values = re.findall(pattern, text)

    numbers = []

    for value in values:
        try:
            numbers.append(
                float(value.replace(",", "."))
            )
        except (TypeError, ValueError):
            pass

    return numbers


def summarize_stat_results(results):
    if not results:
        return {
            "available": False,
            "signals": [],
            "numbers": [],
        }

    signals = []
    numbers = []

    for item in results:
        text = (
            item["title"]
            + " "
            + item["snippet"]
        )

        numbers.extend(
            extract_numbers(text)
        )

        signals.append({
            "title": item["title"],
            "snippet": item["snippet"],
            "link": item["link"],
        })

    return {
        "available": True,
        "signals": signals,
        "numbers": numbers,
    }


# ============================================================
# BLESSURES / ABSENCES
# ============================================================

def search_absences(team_name, match_date):
    queries = [
        f'"{team_name}" injuries suspensions absences {match_date}',
        f'"{team_name}" blessures absents suspendus {match_date}',
        f'"{team_name}" probable lineup {match_date}',
        f'"{team_name}" composition probable {match_date}',
        f'"{team_name}" unavailable players {match_date}',
    ]

    collected = []

    for query in queries:
        results = serp_search(query, 6)

        for result in results:
            collected.append({
                "title": result.get("title", ""),
                "snippet": result.get("snippet", ""),
                "link": result.get("link", ""),
            })

    unique = {}

    for item in collected:
        key = (
            item["title"],
            item["snippet"],
        )
        unique[key] = item

    return list(unique.values())[:15]


# ============================================================
# CLASSIFICATION ABSENCES
# ============================================================

def classify_absences(results):
    categories = {
        "Blessures": [
            "injury",
            "injured",
            "blessure",
            "blessé",
            "blessés",
        ],
        "Suspensions": [
            "suspended",
            "suspension",
            "suspendu",
            "carton rouge",
        ],
        "Absences": [
            "absence",
            "absent",
            "unavailable",
            "forfait",
            "manquera",
            "out",
        ],
    }

    output = []

    for result in results:
        text = (
            result["title"]
            + " "
            + result["snippet"]
        ).lower()

        found = []

        for category, words in categories.items():
            if any(word in text for word in words):
                found.append(category)

        if found:
            output.append({
                **result,
                "categories": found,
            })

    return output


# ============================================================
# LAMBDA PRINCIPAL
# ============================================================

def build_lambdas(
    home_form,
    away_form,
    home_split,
    away_split,
    home_standing=None,
    away_standing=None,
):
    home_attack = (
        0.55 * home_form["gf_avg"]
        + 0.45 * home_split["gf_avg"]
    )

    away_attack = (
        0.55 * away_form["gf_avg"]
        + 0.45 * away_split["gf_avg"]
    )

    home_defense = (
        0.55 * away_form["ga_avg"]
        + 0.45 * away_split["ga_avg"]
    )

    away_defense = (
        0.55 * home_form["ga_avg"]
        + 0.45 * home_split["ga_avg"]
    )

    home_lambda = (
        0.58 * home_attack
        + 0.42 * home_defense
    )

    away_lambda = (
        0.58 * away_attack
        + 0.42 * away_defense
    )

    # Avantage domicile.
    home_lambda *= 1.08
    away_lambda *= 0.94

    # Forme.
    home_lambda *= (
        0.92
        + 0.16 * home_form["form_score"]
    )

    away_lambda *= (
        0.92
        + 0.16 * away_form["form_score"]
    )

    # Classement.
    if home_standing and away_standing:
        hp = home_standing.get("position", 10)
        ap = away_standing.get("position", 10)

        if hp < ap:
            home_lambda *= 1.03
            away_lambda *= 0.98
        elif ap < hp:
            away_lambda *= 1.03
            home_lambda *= 0.98

    return (
        max(0.20, min(home_lambda, 3.8)),
        max(0.15, min(away_lambda, 3.5)),
    )


# ============================================================
# AJUSTEMENT CONTEXTUEL
# ============================================================

def contextual_adjustment(
    home_lambda,
    away_lambda,
    home_absences,
    away_absences,
):
    important_words = [
        "key player",
        "star",
        "captain",
        "capitaine",
        "top scorer",
        "meilleur buteur",
        "principal attaquant",
        "important player",
    ]

    home_text = " ".join(
        x["title"] + " " + x["snippet"]
        for x in home_absences
    ).lower()

    away_text = " ".join(
        x["title"] + " " + x["snippet"]
        for x in away_absences
    ).lower()

    home_penalty = 0
    away_penalty = 0

    for word in important_words:
        if word in home_text:
            home_penalty += 0.025
        if word in away_text:
            away_penalty += 0.025

    home_penalty = min(home_penalty, 0.12)
    away_penalty = min(away_penalty, 0.12)

    home_lambda *= (1 - home_penalty)
    away_lambda *= (1 - away_penalty)

    return (
        max(home_lambda, 0.15),
        max(away_lambda, 0.15),
    )


# ============================================================
# ANALYSE HUMAINE
# ============================================================

def human_analysis(
    home,
    away,
    markets,
    scores,
    htft,
    home_form,
    away_form,
    home_lambda,
    away_lambda,
):
    p1 = markets["1"]
    px = markets["X"]
    p2 = markets["2"]

    results = {
        "1": p1,
        "X": px,
        "2": p2,
    }

    main_result = max(
        results,
        key=results.get,
    )

    best_score = scores[0][0]
    best_htft = htft[0][0]

    if (
        abs(p1 - p2) < 0.08
        and px >= 0.27
    ):
        reading = (
            "Les deux équipes sont proches. "
            "Le scénario nul est à surveiller."
        )
    elif (
        p1 > p2
        and home_form["form_score"]
        >= away_form["form_score"]
    ):
        reading = (
            "Le modèle et la dynamique récente "
            "convergent vers l'équipe à domicile."
        )
    elif (
        p2 > p1
        and away_form["form_score"]
        >= home_form["form_score"]
    ):
        reading = (
            "L'équipe extérieure possède "
            "un signal statistique supérieur."
        )
    else:
        reading = (
            "Les signaux sont partagés. "
            "Une couverture est préférable au 1X2 sec."
        )

    if markets["Over 2.5"] >= 0.60:
        goals = (
            "Le scénario d'au moins 3 buts "
            "est dominant dans le modèle."
        )
    elif markets["Under 2.5"] >= 0.60:
        goals = (
            "Le modèle privilégie "
            "un match à faible total de buts."
        )
    else:
        goals = "Le total de buts reste équilibré."

    if markets["BTTS Oui"] >= 0.60:
        btts = (
            "Les deux équipes ont un signal favorable "
            "pour marquer."
        )
    elif markets["BTTS Non"] >= 0.60:
        btts = "Une des deux équipes pourrait rester muette."
    else:
        btts = "Le BTTS est difficile à départager."

    return {
        "main_result": main_result,
        "best_score": best_score,
        "best_htft": best_htft,
        "reading": reading,
        "goals": goals,
        "btts": btts,
    }


# ============================================================
# ANALYSE COMPLÈTE
# ============================================================

def analyze_match(match):
    home = match.get("homeTeam", {})
    away = match.get("awayTeam", {})

    home_id = home.get("id")
    away_id = away.get("id")

    home_name = home.get("name", "Domicile")
    away_name = away.get("name", "Extérieur")

    competition_data = match.get("competition", {})

    competition = competition_data.get("name", "")
    competition_code = competition_data.get("code")

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
    table = []

    if competition_code:
        table = fetch_standings(
            competition_code
        )

    home_standing = get_standing(
        table,
        home_id,
    )

    away_standing = get_standing(
        table,
        away_id,
    )

    # Lambdas.
    home_lambda, away_lambda = build_lambdas(
        home_form,
        away_form,
        home_split,
        away_split,
        home_standing,
        away_standing,
    )

    match_date = match.get(
        "utcDate",
        "",
    )[:10]

    # Absences.
    home_absences_raw = search_absences(
        home_name,
        match_date,
    )

    away_absences_raw = search_absences(
        away_name,
        match_date,
    )

    home_absences = classify_absences(
        home_absences_raw
    )

    away_absences = classify_absences(
        away_absences_raw
    )

    home_lambda, away_lambda = contextual_adjustment(
        home_lambda,
        away_lambda,
        home_absences,
        away_absences,
    )

    # Modèle.
    matrix = poisson_matrix(
        home_lambda,
        away_lambda,
    )

    markets = calculate_markets(matrix)

    scores = exact_scores(
        matrix,
        10,
    )

    ht = half_time_model(
        home_lambda,
        away_lambda,
    )

    htft = htft_model(
        home_lambda,
        away_lambda,
    )

    # Statistiques Web.
    home_stats_raw = search_detailed_stats(
        home_name
    )

    away_stats_raw = search_detailed_stats(
        away_name
    )

    home_stats = {
        key: summarize_stat_results(value)
        for key, value in home_stats_raw.items()
    }

    away_stats = {
        key: summarize_stat_results(value)
        for key, value in away_stats_raw.items()
    }

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
    )

    return {
        "home": home_name,
        "away": away_name,
        "competition": competition,
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
        "home_absences": home_absences,
        "away_absences": away_absences,
        "home_stats": home_stats,
        "away_stats": away_stats,
        "verdict": verdict,
    }


# ============================================================
# AFFICHAGE STATISTIQUES
# ============================================================

STAT_LABELS = {
    "corners": "🚩 Corners",
    "cartons": "🟨 Cartons",
    "tirs": "🎯 Tirs",
    "tirs_cadres": "🥅 Tirs cadrés",
    "possession": "📊 Possession",
    "fautes": "🟥 Fautes",
    "hors_jeu": "🚩 Hors-jeu",
}


def display_detailed_stats(title, stats):
    st.markdown(f"### {title}")

    for key, label in STAT_LABELS.items():
        data = stats.get(key, {})

        st.markdown(f"**{label}**")

        if not data.get("available", False):
            st.caption(
                "Donnée non trouvée dans les résultats disponibles."
            )
            continue

        signals = data.get("signals", [])

        if not signals:
            st.caption("Aucun signal exploitable.")
            continue

        for signal in signals[:3]:
            st.write("• " + signal["title"])

            if signal["snippet"]:
                st.caption(signal["snippet"])


# ============================================================
# INTERFACE
# ============================================================

st.title(
    "⚽ RODRIGUE PRO FOOTBALL AI — V10 ULTIMATE"
)

st.markdown(
    """
## 🧠 Analyse avancée

**Données + statistiques + contexte + lecture humaine**

Le moteur recherche notamment :

- ⚽ buts
- 📈 forme
- 🏠 domicile / extérieur
- 🏆 classement
- 🎯 tirs
- 🥅 tirs cadrés
- 🚩 corners
- 🟨 cartons
- 📊 possession
- 🟥 fautes
- 🚩 hors-jeu
- 🚑 blessures
- ⛔ suspensions
- 👤 absences
- 🔢 scores exacts
- ⏱️ mi-temps
- 🔄 MT/FT

### 🔧 Correction technique
La recherche des matchs se fait désormais **compétition par compétition**.
Cela évite l'erreur HTTP 400 provoquée par la requête groupée
`competitions=PL,PD,BL1,...`.
"""
)

st.warning(
    "Les statistiques détaillées provenant de recherches Web "
    "ne sont affichées que lorsqu'une information exploitable est trouvée. "
    "Aucune statistique manquante n'est remplacée par une valeur inventée."
)


# ============================================================
# ÉTAT DE L'API
# ============================================================

api_check = validate_football_api()
if api_auth_ok(api_check):
    st.success(
        "🟢 football-data.org : token accepté — authentification OK."
    )
else:
    st.error(
        "🔴 football-data.org refuse actuellement le token. "
        "Aucun appel de matchs ne sera lancé tant que ce test échoue."
    )
    st.code(api_error_message(api_check))
    st.caption(
        f"HTTP {api_check.get('status', 0)} · "
        f"Client API : {api_check.get('authenticated_client', '') or 'non détecté'}"
    )


# ============================================================
# PARAMÈTRES
# ============================================================

col1, col2 = st.columns(2)

with col1:
    selected_date = st.date_input(
        "📅 Date",
        value=date.today(),
    )

with col2:
    selected_competitions = st.multiselect(
        "🏆 Compétitions",
        list(COMPETITIONS.keys()),
        default=list(COMPETITIONS.keys()),
    )

competition_codes = [
    COMPETITIONS[x]
    for x in selected_competitions
]


# ============================================================
# DIAGNOSTIC
# ============================================================

with st.expander("🔧 DIAGNOSTIC FOOTBALL-DATA.ORG"):
    st.caption(
        "Ce diagnostic utilise une requête unique pour la date du jour, sans dateFrom/dateTo. Pour une autre date, il utilise season=AAAA par compétition puis filtre la date localement. Il n'utilise jamais le filtre groupé."
    )

    if st.button(
        "🔍 Tester les compétitions",
        use_container_width=True,
    ):
        if not competition_codes:
            st.warning(
                "Sélectionne au moins une compétition."
            )
        else:
            with st.spinner(
                "Test de football-data.org..."
            ):
                diagnostic = diagnostic_competitions(
                    selected_date,
                    competition_codes,
                )

            st.dataframe(
                pd.DataFrame(diagnostic),
                use_container_width=True,
                hide_index=True,
            )


# ============================================================
# CHARGEMENT
# ============================================================

if st.button(
    "🚀 CHERCHER LES MATCHS",
    type="primary",
    use_container_width=True,
):
    if not competition_codes:
        st.error(
            "❌ Sélectionne au moins une compétition."
        )
        st.stop()

    if not api_auth_ok(api_check):
        st.error(
            "❌ Recherche arrêtée : football-data.org n'accepte pas le token. "
            "Corrige/renouvelle le token puis relance l'application."
        )
        st.stop()

    with st.spinner(
        "🔎 Chargement des matchs..."
    ):
        matches = fetch_matches(
            selected_date,
            tuple(competition_codes),
        )

    if not matches:
        st.error(
            "❌ Aucun match trouvé pour cette date "
            "dans les compétitions sélectionnées."
        )

        st.info(
            "💡 La recherche n'utilise plus dateFrom/dateTo. Pour aujourd'hui, /matches est appelé sans paramètre ; pour une autre date, la saison est chargée puis la date est filtrée localement."
        )

        st.session_state.pop(
            "matches_v10",
            None,
        )

    else:
        st.success(
            f"✅ {len(matches)} match(s) trouvé(s)."
        )

        st.session_state["matches_v10"] = matches


# ============================================================
# AFFICHAGE MATCHS
# ============================================================

if "matches_v10" in st.session_state:
    matches = st.session_state["matches_v10"]

    st.subheader("📋 MATCHS")

    # Petit résumé par compétition.
    competition_counts = {}

    for match in matches:
        name = match.get(
            "competition",
            {},
        ).get(
            "name",
            "Compétition inconnue",
        )
        competition_counts[name] = (
            competition_counts.get(name, 0) + 1
        )

    if competition_counts:
        summary_rows = [
            {
                "Compétition": name,
                "Matchs": count,
            }
            for name, count in sorted(
                competition_counts.items()
            )
        ]

        st.dataframe(
            pd.DataFrame(summary_rows),
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
            f"⚽ {home} — {away} | {competition}"
        ):
            if utc_date:
                st.caption(
                    f"🕐 Date API : {utc_date}"
                )

            if st.button(
                "🧠 ANALYSER CE MATCH",
                key=f"v10_{index}",
                use_container_width=True,
            ):
                with st.spinner(
                    "🧠 Analyse complète en cours..."
                ):
                    result = analyze_match(match)

                # =================================================
                # EN-TÊTE
                # =================================================

                st.header(
                    f"⚽ {result['home']} — {result['away']}"
                )

                st.caption(
                    result["competition"]
                )

                # =================================================
                # XG
                # =================================================

                c1, c2, c3 = st.columns(3)

                c1.metric(
                    "xG domicile",
                    number(result["home_lambda"]),
                )

                c2.metric(
                    "xG extérieur",
                    number(result["away_lambda"]),
                )

                c3.metric(
                    "Buts attendus",
                    number(
                        result["home_lambda"]
                        + result["away_lambda"]
                    ),
                )

                # =================================================
                # FORME
                # =================================================

                st.subheader("📈 FORME")

                f1, f2 = st.columns(2)

                with f1:
                    st.markdown(
                        f"### 🏠 {result['home']}"
                    )

                    form = result["home_form"]

                    st.write(
                        f"**V-N-D :** "
                        f"{form['wins']}-"
                        f"{form['draws']}-"
                        f"{form['losses']}"
                    )

                    st.write(
                        f"**Buts :** "
                        f"{form['gf']} / {form['ga']}"
                    )

                    st.write(
                        f"**Moyenne buts marqués :** "
                        f"{form['gf_avg']:.2f}"
                    )

                    st.write(
                        f"**Moyenne buts encaissés :** "
                        f"{form['ga_avg']:.2f}"
                    )

                with f2:
                    st.markdown(
                        f"### ✈️ {result['away']}"
                    )

                    form = result["away_form"]

                    st.write(
                        f"**V-N-D :** "
                        f"{form['wins']}-"
                        f"{form['draws']}-"
                        f"{form['losses']}"
                    )

                    st.write(
                        f"**Buts :** "
                        f"{form['gf']} / {form['ga']}"
                    )

                    st.write(
                        f"**Moyenne buts marqués :** "
                        f"{form['gf_avg']:.2f}"
                    )

                    st.write(
                        f"**Moyenne buts encaissés :** "
                        f"{form['ga_avg']:.2f}"
                    )

                # =================================================
                # CLASSEMENT
                # =================================================

                st.subheader("🏆 CLASSEMENT")

                s1, s2 = st.columns(2)

                for column, team_name, standing in [
                    (
                        s1,
                        result["home"],
                        result["home_standing"],
                    ),
                    (
                        s2,
                        result["away"],
                        result["away_standing"],
                    ),
                ]:
                    with column:
                        st.markdown(
                            f"**{team_name}**"
                        )

                        if standing:
                            st.write(
                                "Position : "
                                + str(
                                    standing.get(
                                        "position",
                                        "N/D",
                                    )
                                )
                            )

                            st.write(
                                "Points : "
                                + str(
                                    standing.get(
                                        "points",
                                        "N/D",
                                    )
                                )
                            )

                            st.write(
                                "Différence : "
                                + str(
                                    standing.get(
                                        "goalDifference",
                                        "N/D",
                                    )
                                )
                            )
                        else:
                            st.caption(
                                "Classement non disponible."
                            )

                # =================================================
                # 1X2
                # =================================================

                st.subheader(
                    "🎯 1X2 / DOUBLE CHANCE"
                )

                market_rows = []

                for market in [
                    "1",
                    "X",
                    "2",
                    "1X",
                    "X2",
                    "12",
                ]:
                    market_rows.append({
                        "Marché": market,
                        "Probabilité": percent(
                            result["markets"][market]
                        ),
                    })

                st.dataframe(
                    pd.DataFrame(market_rows),
                    use_container_width=True,
                    hide_index=True,
                )

                # =================================================
                # BUTS
                # =================================================

                st.subheader("⚽ BUTS")

                goals_rows = []

                for market in [
                    "BTTS Oui",
                    "BTTS Non",
                    "Over 1.5",
                    "Under 1.5",
                    "Over 2.5",
                    "Under 2.5",
                    "Over 3.5",
                    "Under 3.5",
                ]:
                    goals_rows.append({
                        "Marché": market,
                        "Probabilité": percent(
                            result["markets"][market]
                        ),
                    })

                st.dataframe(
                    pd.DataFrame(goals_rows),
                    use_container_width=True,
                    hide_index=True,
                )

                # =================================================
                # SCORES EXACTS
                # =================================================

                st.subheader("🔢 SCORES EXACTS")

                score_rows = []

                for score, probability in result["scores"]:
                    score_rows.append({
                        "Score": score,
                        "Probabilité": percent(
                            probability
                        ),
                    })

                st.dataframe(
                    pd.DataFrame(score_rows),
                    use_container_width=True,
                    hide_index=True,
                )

                # =================================================
                # MI-TEMPS
                # =================================================

                st.subheader("⏱️ MI-TEMPS")

                ht_rows = []

                for score, probability in result["ht"]["scores"]:
                    ht_rows.append({
                        "Score MT": score,
                        "Probabilité": percent(
                            probability
                        ),
                    })

                st.dataframe(
                    pd.DataFrame(ht_rows),
                    use_container_width=True,
                    hide_index=True,
                )

                # =================================================
                # MT/FT
                # =================================================

                st.subheader("🔄 MT / FT")

                htft_rows = []

                for combination, probability in result["htft"][:9]:
                    htft_rows.append({
                        "MT/FT": combination,
                        "Probabilité": percent(
                            probability
                        ),
                    })

                st.dataframe(
                    pd.DataFrame(htft_rows),
                    use_container_width=True,
                    hide_index=True,
                )

                # =================================================
                # STATISTIQUES DÉTAILLÉES
                # =================================================

                st.subheader(
                    "📊 STATISTIQUES DÉTAILLÉES"
                )

                stats1, stats2 = st.columns(2)

                with stats1:
                    display_detailed_stats(
                        "🏠 " + result["home"],
                        result["home_stats"],
                    )

                with stats2:
                    display_detailed_stats(
                        "✈️ " + result["away"],
                        result["away_stats"],
                    )

                # =================================================
                # ABSENCES
                # =================================================

                st.subheader(
                    "🚑 ABSENCES / BLESSURES / SUSPENSIONS"
                )

                abs1, abs2 = st.columns(2)

                with abs1:
                    st.markdown(
                        f"### {result['home']}"
                    )

                    if result["home_absences"]:
                        for item in result["home_absences"][:8]:
                            st.write(
                                "• " + item["title"]
                            )

                            if item["snippet"]:
                                st.caption(
                                    item["snippet"]
                                )
                    else:
                        st.info(
                            "Aucune information exploitable trouvée."
                        )

                with abs2:
                    st.markdown(
                        f"### {result['away']}"
                    )

                    if result["away_absences"]:
                        for item in result["away_absences"][:8]:
                            st.write(
                                "• " + item["title"]
                            )

                            if item["snippet"]:
                                st.caption(
                                    item["snippet"]
                                )
                    else:
                        st.info(
                            "Aucune information exploitable trouvée."
                        )

                # =================================================
                # SYNTHÈSE
                # =================================================

                st.subheader(
                    "🧠 SYNTHÈSE HUMAINE RODRIGUE PRO"
                )

                verdict = result["verdict"]

                st.success(
                    "🎯 Résultat principal : "
                    f"**{verdict['main_result']}**"
                )

                st.info(
                    "🔢 Score exact : "
                    f"**{verdict['best_score']}**"
                )

                st.info(
                    "⏱️ MT/FT : "
                    f"**{verdict['best_htft']}**"
                )

                st.write(
                    "**Lecture du match :** "
                    + verdict["reading"]
                )

                st.write(
                    "**Lecture des buts :** "
                    + verdict["goals"]
                )

                st.write(
                    "**Lecture BTTS :** "
                    + verdict["btts"]
                )

                # =================================================
                # TOP 5
                # =================================================

                st.subheader(
                    "🔥 TOP SÉLECTIONS DU MODÈLE"
                )

                top_markets = sorted(
                    result["markets"].items(),
                    key=lambda x: x[1],
                    reverse=True,
                )

                top_rows = []

                for market, probability in top_markets[:5]:
                    top_rows.append({
                        "Marché": market,
                        "Probabilité": percent(
                            probability
                        ),
                    })

                st.dataframe(
                    pd.DataFrame(top_rows),
                    use_container_width=True,
                    hide_index=True,
                )

                # =================================================
                # CONCLUSION
                # =================================================

                st.divider()

                st.markdown(
                    f"""
### 🏁 PRONOSTIC FINAL

**{result['home']} — {result['away']}**

- 🎯 **1X2 :** {verdict['main_result']}
- 🔢 **Score :** {verdict['best_score']}
- ⏱️ **MT/FT :** {verdict['best_htft']}
- ⚽ **BTTS :** {verdict['btts']}
- 📊 **Lecture :** {verdict['reading']}
"""
                )

                st.caption(
                    "Rodrigue Pro Football AI V10 — "
                    "les données absentes ne sont pas remplacées "
                    "par des valeurs artificielles."
                )


st.caption(
    "Data provided by football-data.org"
)
