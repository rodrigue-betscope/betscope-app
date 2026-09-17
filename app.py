# -*- coding: utf-8 -*-
"""
RODRIGUE PRO FOOTBALL AI — V1
Analyse statistique football : 1X2, double chance, buts, BTTS,
scores exacts, mi-temps et HT/FT.

IMPORTANT :
- Les probabilités sont des estimations, jamais des garanties.
- Les clés API doivent être placées dans des variables d'environnement.
- Football-data.org ne fournit pas toutes les statistiques détaillées des joueurs.
- SerpAPI sert ici à rechercher des informations complémentaires, qui doivent
  être vérifiées avant d'être considérées comme certaines.
"""

import os
import re
import math
import json
import argparse
from datetime import datetime, timedelta
from collections import Counter
from typing import Dict, List, Optional, Tuple

import requests


# ============================================================
# CONFIGURATION
# ============================================================

FOOTBALL_DATA_KEY = os.getenv("FOOTBALL_DATA_KEY", "")
SERPAPI_KEY = os.getenv("SERPAPI_KEY", "")

FD_BASE = "https://api.football-data.org/v4"
SERP_URL = "https://serpapi.com/search.json"

TIMEOUT = 20
HISTORY_LIMIT = 12
MAX_GOALS = 7


# ============================================================
# OUTILS GÉNÉRAUX
# ============================================================

def safe_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def pct(value):
    return round(100 * value, 2)


def normalize(text):
    text = (text or "").lower()
    text = re.sub(r"[^a-z0-9àâçéèêëîïôûùüÿñ -]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def poisson(k, lam):
    if lam <= 0:
        return 1.0 if k == 0 else 0.0
    return math.exp(-lam) * (lam ** k) / math.factorial(k)


def get_json(url, headers=None, params=None):
    response = requests.get(
        url,
        headers=headers or {},
        params=params or {},
        timeout=TIMEOUT,
    )
    response.raise_for_status()
    return response.json()


# ============================================================
# FOOTBALL-DATA.ORG
# ============================================================

def fd_headers():
    if not FOOTBALL_DATA_KEY:
        raise RuntimeError(
            "FOOTBALL_DATA_KEY est absent. Configure la variable d'environnement."
        )
    return {"X-Auth-Token": FOOTBALL_DATA_KEY}


def search_competition_matches(date_str, competition_codes=None):
    """
    Recherche les matchs d'une date.
    date_str : YYYY-MM-DD
    competition_codes : ex. ['PL', 'PD', 'SA', 'BL1', 'FL1']
    """
    params = {
        "dateFrom": date_str,
        "dateTo": date_str,
    }

    if competition_codes:
        params["competitions"] = ",".join(competition_codes)

    data = get_json(
        f"{FD_BASE}/matches",
        headers=fd_headers(),
        params=params,
    )
    return data.get("matches", [])


def team_matches(team_id, status="FINISHED", limit=HISTORY_LIMIT):
    data = get_json(
        f"{FD_BASE}/teams/{team_id}/matches",
        headers=fd_headers(),
        params={
            "status": status,
            "limit": limit,
        },
    )
    return data.get("matches", [])


def get_standings(competition_code):
    data = get_json(
        f"{FD_BASE}/competitions/{competition_code}/standings",
        headers=fd_headers(),
    )
    standings = data.get("standings", [])
    if not standings:
        return []

    rows = standings[0].get("table", [])
    return rows


def extract_score(match):
    score = match.get("score", {})
    full = score.get("fullTime", {})
    half = score.get("halfTime", {})

    return {
        "home": full.get("home"),
        "away": full.get("away"),
        "ht_home": half.get("home"),
        "ht_away": half.get("away"),
    }


def result_for_team(match, team_id):
    home_id = match.get("homeTeam", {}).get("id")
    away_id = match.get("awayTeam", {}).get("id")
    score = extract_score(match)

    if score["home"] is None or score["away"] is None:
        return None

    if home_id == team_id:
        gf, ga = score["home"], score["away"]
        venue = "home"
    elif away_id == team_id:
        gf, ga = score["away"], score["home"]
        venue = "away"
    else:
        return None

    outcome = "W" if gf > ga else "D" if gf == ga else "L"

    return {
        "gf": gf,
        "ga": ga,
        "outcome": outcome,
        "venue": venue,
        "ht_gf": (
            score["ht_home"] if venue == "home" else score["ht_away"]
        ),
        "ht_ga": (
            score["ht_away"] if venue == "home" else score["ht_home"]
        ),
    }


def summarize_team(team_id):
    matches = team_matches(team_id)
    rows = []

    for match in matches:
        item = result_for_team(match, team_id)
        if item:
            rows.append(item)

    if not rows:
        return {
            "matches": 0,
            "gf_avg": None,
            "ga_avg": None,
            "home_gf_avg": None,
            "home_ga_avg": None,
            "away_gf_avg": None,
            "away_ga_avg": None,
            "ht_gf_avg": None,
            "ht_ga_avg": None,
            "form": "",
        }

    def avg(values):
        return sum(values) / len(values) if values else None

    home = [x for x in rows if x["venue"] == "home"]
    away = [x for x in rows if x["venue"] == "away"]

    return {
        "matches": len(rows),
        "gf_avg": avg([x["gf"] for x in rows]),
        "ga_avg": avg([x["ga"] for x in rows]),
        "home_gf_avg": avg([x["gf"] for x in home]),
        "home_ga_avg": avg([x["ga"] for x in home]),
        "away_gf_avg": avg([x["gf"] for x in away]),
        "away_ga_avg": avg([x["ga"] for x in away]),
        "ht_gf_avg": avg([x["ht_gf"] for x in rows if x["ht_gf"] is not None]),
        "ht_ga_avg": avg([x["ht_ga"] for x in rows if x["ht_ga"] is not None]),
        "form": "".join(x["outcome"] for x in rows[:5]),
    }


# ============================================================
# RECHERCHE SERPAPI
# ============================================================

def search_web(query, num=5):
    if not SERPAPI_KEY:
        return []

    params = {
        "engine": "google",
        "q": query,
        "api_key": SERPAPI_KEY,
        "hl": "fr",
        "gl": "cm",
        "num": num,
    }

    try:
        data = get_json(SERP_URL, params=params)
    except Exception:
        return []

    results = []
    for item in data.get("organic_results", []):
        results.append({
            "title": item.get("title", ""),
            "snippet": item.get("snippet", ""),
            "link": item.get("link", ""),
        })
    return results


def supplementary_research(home_name, away_name):
    """
    Retourne des résultats de recherche bruts.
    Le programme ne transforme pas automatiquement un article en blessure
    certaine : une validation humaine est nécessaire.
    """
    queries = [
        f"{home_name} blessures absences suspensions composition probable",
        f"{away_name} blessures absences suspensions composition probable",
        f"{home_name} {away_name} statistiques match preview",
        f"{home_name} {away_name} stade localisation météo",
    ]

    output = {}
    for query in queries:
        output[query] = search_web(query)
    return output


# ============================================================
# MODÈLE DE BUTS
# ============================================================

def estimate_expected_goals(home_stats, away_stats):
    """
    Modèle simple et prudent basé sur les moyennes disponibles.
    Les valeurs de secours ne sont pas des statistiques réelles :
    elles servent uniquement à éviter une division par zéro.
    """

    league_baseline = 1.35

    h_attack = home_stats.get("home_gf_avg") or home_stats.get("gf_avg")
    h_def = home_stats.get("home_ga_avg") or home_stats.get("ga_avg")

    a_attack = away_stats.get("away_gf_avg") or away_stats.get("gf_avg")
    a_def = away_stats.get("away_ga_avg") or away_stats.get("ga_avg")

    h_attack = h_attack if h_attack is not None else league_baseline
    h_def = h_def if h_def is not None else league_baseline
    a_attack = a_attack if a_attack is not None else league_baseline
    a_def = a_def if a_def is not None else league_baseline

    # Pondération modérée pour limiter les valeurs extrêmes.
    home_xg = 0.55 * h_attack + 0.25 * a_def + 0.20 * league_baseline
    away_xg = 0.55 * a_attack + 0.25 * h_def + 0.20 * league_baseline

    home_xg = min(max(home_xg, 0.15), 4.5)
    away_xg = min(max(away_xg, 0.15), 4.5)

    return home_xg, away_xg


def goal_matrix(home_xg, away_xg, max_goals=MAX_GOALS):
    matrix = {}
    total = 0.0

    for h in range(max_goals + 1):
        for a in range(max_goals + 1):
            p = poisson(h, home_xg) * poisson(a, away_xg)
            matrix[(h, a)] = p
            total += p

    # Normalisation, car la matrice est tronquée à MAX_GOALS.
    if total:
        matrix = {k: v / total for k, v in matrix.items()}

    return matrix


def market_probabilities(matrix):
    home = draw = away = 0.0
    over = {0.5: 0, 1.5: 0, 2.5: 0, 3.5: 0}
    btts_yes = 0.0
    ht_home = ht_draw = ht_away = 0.0

    for (h, a), p in matrix.items():
        if h > a:
            home += p
        elif h == a:
            draw += p
        else:
            away += p

        total = h + a
        for line in over:
            if total > line:
                over[line] += p

        if h > 0 and a > 0:
            btts_yes += p

    # Approximation de la mi-temps : 44 % des buts attendus.
    for (h, a), p in matrix.items():
        # On réutilise une approximation conditionnelle pour la pause.
        # Cette partie sera plus précise avec une API fournissant les buts HT.
        if h > a:
            ht_home += p * 0.44
        elif h == a:
            ht_draw += p * 0.44
        else:
            ht_away += p * 0.44

    # Recalibrage pour obtenir une distribution HT cohérente.
    s = ht_home + ht_draw + ht_away
    if s:
        ht_home, ht_draw, ht_away = (
            ht_home / s, ht_draw / s, ht_away / s
        )

    return {
        "1": home,
        "X": draw,
        "2": away,
        "1X": home + draw,
        "X2": draw + away,
        "12": home + away,
        "over_0.5": over[0.5],
        "under_0.5": 1 - over[0.5],
        "over_1.5": over[1.5],
        "under_1.5": 1 - over[1.5],
        "over_2.5": over[2.5],
        "under_2.5": 1 - over[2.5],
        "over_3.5": over[3.5],
        "under_3.5": 1 - over[3.5],
        "btts_yes": btts_yes,
        "btts_no": 1 - btts_yes,
        "ht_1": ht_home,
        "ht_X": ht_draw,
        "ht_2": ht_away,
    }


def top_exact_scores(matrix, n=5):
    return sorted(
        [
            {"score": f"{h}-{a}", "probability": pct(p)}
            for (h, a), p in matrix.items()
        ],
        key=lambda x: x["probability"],
        reverse=True,
    )[:n]


def ht_ft_probabilities(matrix):
    """
    Approximation HT/FT :
    - la mi-temps est estimée par une réduction des buts attendus ;
    - la fin du match vient de la matrice principale.
    Cette méthode ne doit pas être présentée comme une donnée officielle.
    """
    combos = Counter()

    for (h, a), p in matrix.items():
        final = "1" if h > a else "X" if h == a else "2"

        # Approximation grossière du résultat HT à partir du score final.
        if h == 0 and a == 0:
            half = "X"
        elif h > a:
            half = "1"
        elif h < a:
            half = "2"
        else:
            half = "X"

        combos[f"{half}/{final}"] += p

    return [
        {"combination": k, "probability": pct(v)}
        for k, v in combos.most_common()
    ]


# ============================================================
# RAPPORT
# ============================================================

def confidence_label(probabilities, data_quality):
    strongest = max(
        probabilities["1"],
        probabilities["X"],
        probabilities["2"],
    )

    if data_quality < 0.50:
        return "Faible — données insuffisantes"
    if strongest >= 0.65 and data_quality >= 0.80:
        return "Élevée — à confirmer avec les compositions"
    if strongest >= 0.50:
        return "Moyenne"
    return "Faible — match équilibré"


def analyze_match(match, include_web=True):
    home = match.get("homeTeam", {})
    away = match.get("awayTeam", {})

    home_id = home.get("id")
    away_id = away.get("id")
    home_name = home.get("name", "Domicile")
    away_name = away.get("name", "Extérieur")

    if not home_id or not away_id:
        raise ValueError("Identifiants des équipes absents.")

    home_stats = summarize_team(home_id)
    away_stats = summarize_team(away_id)

    home_xg, away_xg = estimate_expected_goals(home_stats, away_stats)
    matrix = goal_matrix(home_xg, away_xg)
    markets = market_probabilities(matrix)

    available_data = (
        int(home_stats["matches"] > 0)
        + int(away_stats["matches"] > 0)
    )
    data_quality = available_data / 2

    report = {
        "match": f"{home_name} - {away_name}",
        "date": match.get("utcDate"),
        "competition": match.get("competition", {}).get("name"),
        "venue": home.get("venue"),
        "expected_goals": {
            "home": round(home_xg, 3),
            "away": round(away_xg, 3),
        },
        "team_form": {
            home_name: home_stats,
            away_name: away_stats,
        },
        "markets_percent": {
            key: pct(value)
            for key, value in markets.items()
        },
        "exact_scores": top_exact_scores(matrix),
        "ht_ft": ht_ft_probabilities(matrix),
        "confidence": confidence_label(markets, data_quality),
        "data_quality_percent": pct(data_quality),
        "limitations": [
            "Les blessures et suspensions doivent être vérifiées dans les sources.",
            "Les statistiques détaillées des joueurs ne sont pas garanties par football-data.org.",
            "La météo et la localisation du stade ne sont pas automatiquement converties en avantage numérique.",
            "La mi-temps et le HT/FT sont des approximations sans données spécifiques de mi-temps.",
            "Aucune probabilité ne constitue une garantie de gain.",
        ],
    }

    if include_web:
        report["web_research"] = supplementary_research(home_name, away_name)

    return report


def print_report(report):
    print("\n" + "=" * 72)
    print("RODRIGUE PRO FOOTBALL AI")
    print("=" * 72)
    print("Match :", report["match"])
    print("Date  :", report["date"])
    print("Compétition :", report["competition"])
    print("Buts attendus :", report["expected_goals"])
    print("Qualité des données :", report["data_quality_percent"], "%")
    print("Confiance :", report["confidence"])

    print("\n--- MARCHÉS ---")
    for key, value in report["markets_percent"].items():
        print(f"{key:15s}: {value:6.2f}%")

    print("\n--- SCORES EXACTS PROBABLES ---")
    for item in report["exact_scores"]:
        print(f"{item['score']:8s}: {item['probability']:.2f}%")

    print("\n--- MI-TEMPS / FIN ---")
    for item in report["ht_ft"][:9]:
        print(f"{item['combination']:8s}: {item['probability']:.2f}%")

    print("\n--- LIMITES ---")
    for item in report["limitations"]:
        print("-", item)


# ============================================================
# MODE TERMINAL
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="Analyseur football statistique Rodrigue Pro"
    )
    parser.add_argument("--date", required=True, help="Date YYYY-MM-DD")
    parser.add_argument(
        "--competitions",
        default="PL,PD,BL1,SA,FL1",
        help="Codes séparés par virgules",
    )
    parser.add_argument(
        "--match-index",
        type=int,
        default=0,
        help="Index du match dans la liste",
    )
    parser.add_argument(
        "--no-web",
        action="store_true",
        help="Désactive la recherche SerpAPI",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Affiche le rapport au format JSON",
    )

    args = parser.parse_args()
    codes = [x.strip() for x in args.competitions.split(",") if x.strip()]

    matches = search_competition_matches(args.date, codes)

    if not matches:
        print("Aucun match trouvé pour cette date et ces compétitions.")
        print("Vérifie la date, les codes de compétition et la clé API.")
        return

    if args.match_index < 0 or args.match_index >= len(matches):
        raise IndexError(
            f"match-index invalide. Choisis une valeur entre 0 et {len(matches)-1}."
        )

    report = analyze_match(
        matches[args.match_index],
        include_web=not args.no_web,
    )

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print_report(report)


if __name__ == "__main__":
    main()
