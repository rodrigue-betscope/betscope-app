# ============================================================
# RODRIGUE PRO FOOTBALL AI - FOOTBALL-DATA.ORG V5
# ============================================================
# API: Football-Data.org V4
#
# Secrets Streamlit:
# [football_data]
# token = "TA_CLE"
#
# IMPORTANT:
# - No invented team statistics.
# - No fixed 1.20/1.35 defaults when history is missing.
# - Probabilities are model probabilities, not guarantees.
# - Football-Data.org does not provide all bookmaker/injury/player
#   information on every plan/competition, so unavailable data is
#   explicitly marked N/D.
# ============================================================

import math
from datetime import date, timedelta

import numpy as np
import pandas as pd
import requests
import streamlit as st


st.set_page_config(
    page_title="Rodrigue Pro Football AI",
    page_icon="⚽",
    layout="wide",
)

API_BASE = "https://api.football-data.org/v4"

COMPETITIONS = {
    "Premier League": "PL",
    "La Liga": "PD",
    "Bundesliga": "BL1",
    "Serie A": "SA",
    "Ligue 1": "FL1",
    "Champions League": "CL",
    "Eredivisie": "DED",
    "Primeira Liga": "PPL",
    "Championship": "ELC",
    "Brasileirão Série A": "BSA",
    "World Cup": "WC",
    "European Championship": "EC",
}

OUTCOMES = ("1", "X", "2")


# ============================================================
# EVENEMENTS / METRIQUES / CONCEPTS
# ============================================================
EVENT_CATALOG = [
    "Accélération", "Duel aérien", "Assister", "Ball out", "Autorisation",
    "Corner", "Contre-attaque", "Récupération par contrepoids", "Coéquipier de couverture",
    "Croix", "Croix profonde achevée", "Complétion profonde", "Duel défensif",
    "Positionnement défensif", "Dribble", "Dribbler devant", "Duel", "Fair-play",
    "Faute", "Faute subie", "Coup franc", "Centre de coup de franc", "Interruption du jeu",
    "But", "But encaissé", "Coup de pied de but", "Le gardien de but quitte la ligne",
    "Handball", "Passe de main", "Passe de tête", "Interception", "Carte d'accès",
    "Faute de carton en fin de match", "Jeu en réseau", "Long col", "Duel de balle libre",
    "Perte", "Balle manquée", "Non-ball", "Mouvements sans ballon", "Duel offensif",
    "Hors-jeu", "Opportunité", "Faute hors jeu", "But contre son camp", "Passer",
    "Passage dans le dernier tiers", "Passe dans la surface de réparation", "Faute de pénalité",
    "Penalty", "Duel pressant", "Passage progressif", "Course progressive",
    "Protestation déloyale", "Récupération", "Carton rouge", "Les réflexes sauvent",
    "Sauvegarder", "Deuxième passe décisive", "Coups de pied arrêtés", "Passage court/moyen",
    "Tir", "Tir après corner", "Tir contré (Tentative d'arrêt)", "Passe décisive",
    "Simulation ratée", "Palan coulissant", "Passe intelligente", "Troisième passe décisive",
    "Passage", "Ajouter", "Temps perdu", "Touche", "Toucher dans la boîte", "Transition",
    "Violent et immonde", "Carton jaune",
]
METRIC_CATALOG = ["Progression de la balle", "Intensité du défi", "Métriques au niveau du match", "PPDA", "Métriques physiques", "Statistiques des joueurs", "Index Wyscout"]
CONCEPT_CATALOG = ["Attaque", "Possession du ballon", "Minutes jouées", "Coordonnées de terrain", "Rapports des joueurs", "Ajusté en fonction de la possession", "xG"]

def _num(v):
    if v is None or isinstance(v, bool): return None
    try: return float(str(v).replace('%','').replace(',','.').strip())
    except (TypeError, ValueError): return None

def extract_match_statistics(match):
    raw = match.get("statistics") or match.get("teamStatistics")
    out = {}
    if not isinstance(raw, list): return out
    for block in raw:
        if not isinstance(block, dict): continue
        tid = (block.get("team") or {}).get("id")
        if tid is None: continue
        vals = {}
        for item in block.get("statistics", []) or []:
            if isinstance(item, dict):
                name = item.get("type") or item.get("name")
                if name: vals[str(name).strip().lower()] = _num(item.get("value"))
        out[int(tid)] = vals
    return out

def _stat(vals, *names):
    for n in names:
        n=n.lower()
        for k,v in vals.items():
            if k == n or n in k:
                return v
    return None

def match_event_metric_report(match):
    raw = extract_match_statistics(match)
    home_id=(match.get("homeTeam") or {}).get("id")
    away_id=(match.get("awayTeam") or {}).get("id")
    hs,as_ = raw.get(home_id,{}),raw.get(away_id,{})
    mapped = {
        "Possession": (_stat(hs,"possession"), _stat(as_,"possession")),
        "Tirs": (_stat(hs,"shots"), _stat(as_,"shots")),
        "Tirs cadrés": (_stat(hs,"shots on target"), _stat(as_,"shots on target")),
        "Corners": (_stat(hs,"corner kicks","corners"), _stat(as_,"corner kicks","corners")),
        "Fautes": (_stat(hs,"fouls"), _stat(as_,"fouls")),
        "Hors-jeu": (_stat(hs,"offsides"), _stat(as_,"offsides")),
        "Cartons jaunes": (_stat(hs,"yellow cards"), _stat(as_,"yellow cards")),
        "Cartons rouges": (_stat(hs,"red cards"), _stat(as_,"red cards")),
        "Arrêts": (_stat(hs,"saves"), _stat(as_,"saves")),
        "Passes": (_stat(hs,"passes"), _stat(as_,"passes")),
    }
    return mapped, raw


# ============================================================
# API
# ============================================================

class FootballDataAPI:
    def __init__(self, token: str):
        self.token = str(token or "").strip()
        self.session = requests.Session()
        self.session.headers.update({
            "X-Auth-Token": self.token,
            "Accept": "application/json",
        })

    def get(self, endpoint: str, params=None):
        if not self.token:
            raise RuntimeError("Clé Football-Data.org absente.")

        try:
            r = self.session.get(
                API_BASE + endpoint,
                params=params or {},
                timeout=30,
            )
        except requests.RequestException as exc:
            raise RuntimeError(f"Erreur réseau API : {exc}") from exc

        if r.status_code == 401:
            raise RuntimeError("Clé Football-Data.org invalide.")
        if r.status_code == 403:
            raise RuntimeError(
                "Accès refusé par Football-Data.org : "
                "cette ressource ou cette compétition n'est pas comprise "
                "dans ton plan."
            )
        if r.status_code == 429:
            raise RuntimeError(
                "Limite API atteinte. Attends avant de relancer."
            )
        if not r.ok:
            try:
                detail = r.json()
            except Exception:
                detail = r.text
            raise RuntimeError(
                f"Football-Data.org HTTP {r.status_code}: {detail}"
            )

        return r.json()


def get_token():
    # Streamlit Cloud: Secrets > [football_data] token = "..."
    try:
        token = st.secrets["football_data"]["token"]
        if token:
            return str(token)
    except Exception:
        pass

    # Alternative: Secrets > FOOTBALL_DATA_TOKEN = "..."
    try:
        token = st.secrets["FOOTBALL_DATA_TOKEN"]
        if token:
            return str(token)
    except Exception:
        pass

    return ""


# ============================================================
# API DATA
# ============================================================


import time

@st.cache_data(ttl=900, show_spinner=False)
def fetch_finished_history(token, date_from_str, date_to_str, competition_codes):
    api = FootballDataAPI(token)
    d_from = date.fromisoformat(date_from_str)
    d_to = date.fromisoformat(date_to_str)
    
    all_matches = []
    current_to = d_to
    
    while current_to > d_from:
        current_from = max(d_from, current_to - timedelta(days=9))
        data = api.get(
            "/matches",
            params={
                "dateFrom": current_from.isoformat(),
                "dateTo": current_to.isoformat(),
                "competitions": ",".join(competition_codes),
                "status": "FINISHED",
                "limit": 100,
            },
        )
        all_matches.extend(data.get("matches", []))
        current_to = current_from - timedelta(days=1)
        
        # Pause pour éviter de saturer la limite de l'API gratuite
        time.sleep(0.6)
        
    return all_matches


@st.cache_data(ttl=900, show_spinner=False)
@st.cache_data(ttl=900, show_spinner=False)
def fetch_finished_history(token, date_from_str, date_to_str, competition_codes):
    api = FootballDataAPI(token)
    d_from = date.fromisoformat(date_from_str)
    d_to = date.fromisoformat(date_to_str)
    
    all_matches = []
    current_to = d_to
    
    # Découpage automatique par blocs de 9 jours pour respecter la limite de l'API
    while current_to > d_from:
        current_from = max(d_from, current_to - timedelta(days=9))
        data = api.get(
            "/matches",
            params={
                "dateFrom": current_from.isoformat(),
                "dateTo": current_to.isoformat(),
                "competitions": ",".join(competition_codes),
                "status": "FINISHED",
                "limit": 100,
            },
        )
        all_matches.extend(data.get("matches", []))
        current_to = current_from - timedelta(days=1)
        
    return all_matches
    


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_team_matches(
    token,
    team_id,
    date_from,
    date_to,
    competition_codes,
):
    """Fallback/precision source: only this team's matches."""
    api = FootballDataAPI(token)
    data = api.get(
        f"/teams/{int(team_id)}/matches",
        params={
            "dateFrom": date_from,
            "dateTo": date_to,
            "competitions": ",".join(competition_codes),
            "status": "FINISHED",
            "limit": 100,
        },
    )
    return data.get("matches", [])


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_standings(token, competition_code, season_year=None):
    api = FootballDataAPI(token)
    params = {}
    if season_year:
        params["season"] = int(season_year)

    data = api.get(
        f"/competitions/{competition_code}/standings",
        params=params,
    )
    return data.get("standings", [])


# ============================================================
# MATCH / FORM
# ============================================================

def match_is_finished(match):
    return match.get("status") == "FINISHED"


def team_result(match, team_id):
    home = match.get("homeTeam", {}) or {}
    away = match.get("awayTeam", {}) or {}
    score = match.get("score", {}) or {}
    full = score.get("fullTime", {}) or {}

    hg = full.get("home")
    ag = full.get("away")

    if hg is None or ag is None:
        return None

    if home.get("id") == team_id:
        gf, ga = float(hg), float(ag)
        venue = "HOME"
    elif away.get("id") == team_id:
        gf, ga = float(ag), float(hg)
        venue = "AWAY"
    else:
        return None

    result = "W" if gf > ga else "D" if gf == ga else "L"
    return {
        "gf": gf,
        "ga": ga,
        "result": result,
        "venue": venue,
        "date": match.get("utcDate", ""),
    }


def recent_team_form(all_matches, team_id, limit=10):
    rows = []

    for match in all_matches:
        if not match_is_finished(match):
            continue

        item = team_result(match, team_id)
        if item:
            rows.append(item)

    rows.sort(key=lambda x: x["date"], reverse=True)
    return rows[:limit]


def weighted_average(rows, key):
    if not rows:
        return None

    values = np.array([float(x[key]) for x in rows], dtype=float)
    weights = np.exp(-0.12 * np.arange(len(values)))
    return float(np.average(values, weights=weights))


def average_for_venue(rows, venue):
    selected = [x for x in rows if x["venue"] == venue]
    if not selected:
        return None
    return {
        "gf": weighted_average(selected, "gf"),
        "ga": weighted_average(selected, "ga"),
        "n": len(selected),
    }


def form_string(rows):
    return "".join(x["result"] for x in rows) if rows else "N/D"


# ============================================================
# POISSON
# ============================================================

def poisson_probability(k, lam):
    lam = max(float(lam), 0.001)
    return math.exp(-lam) * (lam ** k) / math.factorial(k)


def probability_matrix(lambda_home, lambda_away, max_goals=10):
    matrix = np.zeros((max_goals + 1, max_goals + 1), dtype=float)

    for h in range(max_goals + 1):
        for a in range(max_goals + 1):
            matrix[h, a] = (
                poisson_probability(h, lambda_home)
                * poisson_probability(a, lambda_away)
            )

    total = matrix.sum()
    if total <= 0:
        raise RuntimeError("Impossible de normaliser le modèle Poisson.")

    return matrix / total


def result_score(home, away):
    if home > away:
        return "1"
    if home < away:
        return "2"
    return "X"


def calculate_markets(lambda_home, lambda_away):
    matrix = probability_matrix(lambda_home, lambda_away)
    totals = {}
    p1 = px = p2 = pbtts = 0.0
    scores = []

    for h in range(matrix.shape[0]):
        for a in range(matrix.shape[1]):
            p = float(matrix[h, a])
            goals = h + a
            totals[goals] = totals.get(goals, 0.0) + p

            if h > a:
                p1 += p
            elif h == a:
                px += p
            else:
                p2 += p

            if h >= 1 and a >= 1:
                pbtts += p

            scores.append((f"{h}-{a}", p))

    def over(line):
        return sum(p for g, p in totals.items() if g > line)

    def under(line):
        return sum(p for g, p in totals.items() if g < line)

    markets = {
        "1": p1,
        "X": px,
        "2": p2,
        "1X": p1 + px,
        "X2": px + p2,
        "12": p1 + p2,
        "BTTS Oui": pbtts,
        "BTTS Non": 1 - pbtts,
        "Over 0.5": over(0.5),
        "Under 0.5": under(0.5),
        "Over 1.5": over(1.5),
        "Under 1.5": under(1.5),
        "Over 2.5": over(2.5),
        "Under 2.5": under(2.5),
        "Over 3.5": over(3.5),
        "Under 3.5": under(3.5),
        "Over 4.5": over(4.5),
        "Under 4.5": under(4.5),
        "BTTS + Over 2.5": sum(
            float(matrix[h, a])
            for h in range(matrix.shape[0])
            for a in range(matrix.shape[1])
            if h >= 1 and a >= 1 and h + a >= 3
        ),
        "BTTS + Under 2.5": sum(
            float(matrix[h, a])
            for h in range(matrix.shape[0])
            for a in range(matrix.shape[1])
            if h >= 1 and a >= 1 and h + a <= 2
        ),
    }

    markets["Over 4.0"] = over(4.0)
    markets["Under 4.0"] = under(4.0)
    markets["Exactement 4 buts"] = totals.get(4, 0.0)

    scores.sort(key=lambda x: x[1], reverse=True)

    return markets, scores


def calculate_htft(lambda_home, lambda_away):
    ht_home = max(0.01, lambda_home * 0.46)
    ht_away = max(0.01, lambda_away * 0.46)
    second_home = max(0.01, lambda_home - ht_home)
    second_away = max(0.01, lambda_away - ht_away)

    result = {f"{ht}/{ft}": 0.0 for ht in OUTCOMES for ft in OUTCOMES}

    for h1 in range(8):
        for a1 in range(8):
            p_ht = (
                poisson_probability(h1, ht_home)
                * poisson_probability(a1, ht_away)
            )
            ht_result = result_score(h1, a1)

            for h2 in range(8):
                for a2 in range(8):
                    p = (
                        p_ht
                        * poisson_probability(h2, second_home)
                        * poisson_probability(a2, second_away)
                    )
                    ft_result = result_score(h1 + h2, a1 + a2)
                    result[f"{ht_result}/{ft_result}"] += p

    total = sum(result.values())
    if total:
        result = {k: v / total for k, v in result.items()}

    return result


# ============================================================
# MODEL
# ============================================================

def build_lambdas(home_form, away_form):
    if not home_form or not away_form:
        return None, None, "Données insuffisantes"

    home_gf = weighted_average(home_form, "gf")
    home_ga = weighted_average(home_form, "ga")
    away_gf = weighted_average(away_form, "gf")
    away_ga = weighted_average(away_form, "ga")

    if None in (home_gf, home_ga, away_gf, away_ga):
        return None, None, "Données insuffisantes"

    home_home = average_for_venue(home_form, "HOME")
    away_away = average_for_venue(away_form, "AWAY")

    if home_home and home_home["n"] >= 3:
        home_attack = 0.70 * home_home["gf"] + 0.30 * home_gf
        home_defence = 0.70 * home_home["ga"] + 0.30 * home_ga
    else:
        home_attack = home_gf
        home_defence = home_ga

    if away_away and away_away["n"] >= 3:
        away_attack = 0.70 * away_away["gf"] + 0.30 * away_gf
        away_defence = 0.70 * away_away["ga"] + 0.30 * away_ga
    else:
        away_attack = away_gf
        away_defence = away_ga

    lambda_home = (0.58 * home_attack + 0.42 * away_defence) * 1.06
    lambda_away = (0.58 * away_attack + 0.42 * home_defence) * 0.97

    lambda_home = float(np.clip(lambda_home, 0.10, 5.00))
    lambda_away = float(np.clip(lambda_away, 0.10, 5.00))

    return lambda_home, lambda_away, "OK"


def model_prediction(match, home_form, away_form):
    lambda_home, lambda_away, quality = build_lambdas(
        home_form, away_form
    )

    if lambda_home is None or lambda_away is None:
        return {
            "status": "INSUFFICIENT",
            "quality": quality,
            "home_id": match["homeTeam"]["id"],
            "away_id": match["awayTeam"]["id"],
            "lambda_home": None,
            "lambda_away": None,
            "markets": {},
            "scores": [],
            "htft": {},
        }

    markets, scores = calculate_markets(
        lambda_home,
        lambda_away,
    )
    htft = calculate_htft(lambda_home, lambda_away)
    best_market = max(markets.items(), key=lambda x: x[1])

    return {
        "status": "OK",
        "quality": quality,
        "home_id": match["homeTeam"]["id"],
        "away_id": match["awayTeam"]["id"],
        "lambda_home": lambda_home,
        "lambda_away": lambda_away,
        "markets": markets,
        "scores": scores,
        "htft": htft,
        "best_market": best_market,
    }


# ============================================================
# UI
# ============================================================

st.title("⚽ Rodrigue Pro Football AI")
st.caption(
    "Football-Data.org V4 • statistiques réelles disponibles • "
    "modèle Poisson • aucune statistique inventée"
)

token = get_token()

if not token:
    st.error("Clé API Football-Data.org absente.")
    st.code(
        '[football_data]\n'
        'token = "TA_CLE_FOOTBALL_DATA"',
        language="toml",
    )
    st.info(
        "Dans Streamlit Cloud : Settings → Secrets → ajoute le bloc ci-dessus."
    )
    st.stop()

selected_date = st.date_input(
    "📅 Date des matchs",
    value=date.today(),
)

competition_names = st.multiselect(
    "🏆 Compétitions",
    options=list(COMPETITIONS.keys()),
    default=[
        "Premier League",
        "La Liga",
        "Bundesliga",
        "Serie A",
        "Ligue 1",
    ],
)

if not competition_names:
    st.warning("Sélectionne au moins une compétition.")
    st.stop()

competition_codes = [
    COMPETITIONS[name] for name in competition_names
]

history_days = st.slider(
    "📊 Historique utilisé",
    min_value=30,
    max_value=180,
    value=120,
    step=15,
)

col1, col2 = st.columns(2)

with col1:
    load_button = st.button(
        "🔎 Charger les matchs",
        type="primary",
        use_container_width=True,
    )

with col2:
    analyze_button = st.button(
        "🧠 Analyser les matchs",
        use_container_width=True,
    )

if load_button or analyze_button:
    # CORRECTION : Élargir la fenêtre de recherche de l'API de quelques jours 
    # autour de la date sélectionnée pour éviter le blocage "Aucun match renvoyé" 
    # si le calendrier exact décale les heures UTC ou les journées.
    date_from = (selected_date - timedelta(days=2)).isoformat()
    date_to = (selected_date + timedelta(days=2)).isoformat()

    try:
        with st.spinner("Récupération des matchs Football-Data.org..."):
            matches = fetch_matches(
                token,
                date_from,
                date_to,
                competition_codes,
            )

        # Filtrage local optionnel pour ne garder que la date exacte sélectionnée par l'utilisateur si désiré, 
        # ou laisser la souplesse de la fenêtre élargie. Gardons le filtrage exact sur la date si l'utilisateur 
        # veut cibler précisément ce jour-là, tout en évitant le zéro match sec à cause du décalage UTC.
        exact_date_str = selected_date.isoformat()
        filtered_matches = [
            m for m in matches 
            if m.get("utcDate", "").startswith(exact_date_str)
        ]
        
        # Si aucun match ne matche pile la date UTC exacte mais qu'il y en a dans la fenêtre élargie, 
        # on prend la fenêtre élargie ou on affiche les matchs proches pour ne pas bloquer l'application.
        if not filtered_matches and matches:
            filtered_matches = matches

        if not filtered_matches:
            st.warning(
                "Aucun match renvoyé par Football-Data.org pour cette "
                "date et ces compétitions. Essaie d'élargir ta sélection de compétitions "
                "ou de choisir une autre date."
            )
            st.stop()

        matches = filtered_matches
        st.success(f"{len(matches)} match(s) trouvé(s).")

        if not analyze_button:
            simple_rows = []
            for match in matches:
                simple_rows.append({
                    "Match": (
                        f"{match.get('homeTeam', {}).get('name', '?')} "
                        f"vs "
                        f"{match.get('awayTeam', {}).get('name', '?')}"
                    ),
                    "Compétition": match.get(
                        "competition", {}
                    ).get("name", ""),
                    "Date": match.get("utcDate", ""),
                    "Stade": match.get("venue") or "N/D",
                    "Statut": match.get("status", ""),
                })

            st.dataframe(
                pd.DataFrame(simple_rows),
                use_container_width=True,
                hide_index=True,
            )
            st.stop()

        history_from = (
            selected_date - timedelta(days=history_days)
        ).isoformat()

        with st.spinner(
            "Calcul des formes réelles et du modèle Poisson..."
        ):
            history = fetch_finished_history(
                token,
                history_from,
                selected_date.isoformat(),
                competition_codes,
            )

            rows = []

            for match in matches:
                home = match.get("homeTeam", {}) or {}
                away = match.get("awayTeam", {}) or {}

                home_id = home.get("id")
                away_id = away.get("id")

                home_form = recent_team_form(
                    history,
                    home_id,
                    limit=10,
                )
                away_form = recent_team_form(
                    history,
                    away_id,
                    limit=10,
                )

                if len(home_form) < 5 and home_id:
                    try:
                        home_history = fetch_team_matches(
                            token,
                            home_id,
                            history_from,
                            selected_date.isoformat(),
                            competition_codes,
                        )
                        home_form = recent_team_form(
                            home_history,
                            home_id,
                            limit=10,
                        )
                    except RuntimeError:
                        pass

                if len(away_form) < 5 and away_id:
                    try:
                        away_history = fetch_team_matches(
                            token,
                            away_id,
                            history_from,
                            selected_date.isoformat(),
                            competition_codes,
                        )
                        away_form = recent_team_form(
                            away_history,
                            away_id,
                            limit=10,
                        )
                    except RuntimeError:
                        pass

                prediction = model_prediction(
                    match,
                    home_form,
                    away_form,
                )

                if prediction["status"] == "OK":
                    best_name, best_prob = prediction["best_market"]
                    best_score, best_score_prob = prediction["scores"][0]
                    best_htft, best_htft_prob = max(
                        prediction["htft"].items(),
                        key=lambda x: x[1],
                    )

                    rows.append({
                        "Match": (
                            f"{home.get('name', '?')} vs "
                            f"{away.get('name', '?')}"
                        ),
                        "Compétition": match.get(
                            "competition", {}
                        ).get("name", ""),
                        "Forme domicile": form_string(home_form),
                        "Forme extérieur": form_string(away_form),
                        "N matchs domicile": len(home_form),
                        "N matchs extérieur": len(away_form),
                        "xG modèle domicile": round(
                            prediction["lambda_home"], 2
                        ),
                        "xG modèle extérieur": round(
                            prediction["lambda_away"], 2
                        ),
                        "Sélection principale": best_name,
                        "Probabilité": round(
                            best_prob * 100, 1
                        ),
                        "Score exact modèle": best_score,
                        "P(score)": round(
                            best_score_prob * 100, 1
                        ),
                        "HT/FT modèle": best_htft,
                        "P(HT/FT)": round(
                            best_htft_prob * 100, 1
                        ),
                        "_prediction": prediction,
                        "_match": match,
                        "_home_form": home_form,
                        "_away_form": away_form,
                    })
                else:
                    rows.append({
                        "Match": (
                            f"{home.get('name', '?')} vs "
                            f"{away.get('name', '?')}"
                        ),
                        "Compétition": match.get(
                            "competition", {}
                        ).get("name", ""),
                        "Forme domicile": form_string(home_form),
                        "Forme extérieur": form_string(away_form),
                        "N matchs domicile": len(home_form),
                        "N matchs extérieur": len(away_form),
                        "xG modèle domicile": "N/D",
                        "xG modèle extérieur": "N/D",
                        "Sélection principale": "N/D",
                        "Probabilité": None,
                        "Score exact modèle": "N/D",
                        "P(score)": None,
                        "HT/FT modèle": "N/D",
                        "P(HT/FT)": None,
                        "_prediction": prediction,
                        "_match": match,
                        "_home_form": home_form,
                        "_away_form": away_form,
                    })

        rows.sort(
            key=lambda r: (
                r["Probabilité"]
                if isinstance(r["Probabilité"], (int, float))
                else -1
            ),
            reverse=True,
        )

        display_rows = []
        for row in rows:
            clean = {
                k: v
                for k, v in row.items()
                if not k.startswith("_")
            }
            display_rows.append(clean)

        st.subheader(f"📊 Analyse — {len(rows)} match(s)")
        st.dataframe(
            pd.DataFrame(display_rows),
            use_container_width=True,
            hide_index=True,
        )

        st.subheader("🎯 Détail des analyses")

        for index, row in enumerate(rows):
            prediction = row["_prediction"]
            home_form = row["_home_form"]
            away_form = row["_away_form"]

            with st.expander(
                f"{index + 1}. {row['Match']}"
            ):
                if prediction["status"] != "OK":
                    st.warning(
                        "Données insuffisantes pour calculer un modèle "
                        "fiable pour ce match. Le programme ne fabrique "
                        "pas de pourcentage."
                    )
                    st.write(
                        f"Matchs historiques trouvés : "
                        f"{len(home_form)} domicile / "
                        f"{len(away_form)} extérieur."
                    )
                    continue

                c1, c2, c3 = st.columns(3)

                with c1:
                    st.metric(
                        "Buts attendus domicile",
                        f"{prediction['lambda_home']:.2f}",
                    )

                with c2:
                    st.metric(
                        "Buts attendus extérieur",
                        f"{prediction['lambda_away']:.2f}",
                    )

                with c3:
                    st.metric(
                        "Sélection principale",
                        prediction["best_market"][0],
                        f"{prediction['best_market'][1] * 100:.1f}%",
                    )

                st.write(
                    f"**Forme récente :** "
                    f"{form_string(home_form)} — "
                    f"{form_string(away_form)}"
                )

                market_df = pd.DataFrame([
                    {
                        "Marché": name,
                        "Probabilité": f"{prob * 100:.1f}%",
                    }
                    for name, prob in sorted(
                        prediction["markets"].items(),
                        key=lambda x: x[1],
                        reverse=True,
                    )
                ])

                st.write("**📈 Marchés**")
                st.dataframe(
                    market_df,
                    use_container_width=True,
                    hide_index=True,
                )

                score_df = pd.DataFrame([
                    {
                        "Score": score,
                        "Probabilité": f"{prob * 100:.1f}%",
                    }
                    for score, prob in prediction["scores"][:10]
                ])

                st.write("**🎯 Scores exacts les plus probables**")
                st.dataframe(
                    score_df,
                    use_container_width=True,
                    hide_index=True,
                )

                htft_df = pd.DataFrame([
                    {
                        "HT/FT": name,
                        "Probabilité": f"{prob * 100:.1f}%",
                    }
                    for name, prob in sorted(
                        prediction["htft"].items(),
                        key=lambda x: x[1],
                        reverse=True,
                    )
                ])

                st.write("**🕐 HT/FT**")
                st.dataframe(
                    htft_df,
                    use_container_width=True,
                    hide_index=True,
                )

                st.caption(
                    "Les probabilités sont calculées par le modèle "
                    "à partir des données réellement disponibles. "
                    "Elles ne constituent pas une garantie de résultat."
                )

    except RuntimeError as exc:
        st.error(str(exc))
    except Exception as exc:
        st.error("Erreur inattendue.")
        st.exception(exc)


if "matches" in locals() and "analyze_button" in locals() and analyze_button:
    st.subheader("🧩 Événements, métriques et concepts")
    rows=[]
    for m in matches:
        mapped, raw = match_event_metric_report(m)
        h=(m.get("homeTeam") or {}).get("name","?")
        a=(m.get("awayTeam") or {}).get("name","?")
        row={"Match":f"{h} vs {a}"}
        for label,(hv,av) in mapped.items():
            row[f"{label} domicile"]=hv if hv is not None else "N/D"
            row[f"{label} extérieur"]=av if av is not None else "N/D"
        rows.append(row)
    if rows: st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    with st.expander("📚 Catalogue des événements"):
        st.write(" • ".join(EVENT_CATALOG))
    with st.expander("📐 Métriques et concepts"):
        st.write("**Métriques :** " + " • ".join(METRIC_CATALOG))
        st.write("**Concepts :** " + " • ".join(CONCEPT_CATALOG))
    st.info("Les événements Wyscout/tracking (accélérations, coordonnées, PPDA exact, progression de balle, Index Wyscout, métriques physiques, xG par tir, rapports joueurs, etc.) ne sont pas inventés : ils restent N/D tant qu'une source événementielle dédiée ne les fournit pas. Les statistiques réellement renvoyées par Football-Data.org sont utilisées telles quelles.")

st.divider()
st.caption(
    "Rodrigue Pro Football AI • Football-Data.org V4 • "
    "Pas de statistiques inventées."
)
