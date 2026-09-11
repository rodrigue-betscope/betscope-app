# ============================================================
# PATCH RODRIGUE PRO FOOTBALL AI — ANALYSE COMPLÈTE
# À INSÉRER AU NIVEAU 0 (AUCUN ESPACE AVANT LES def)
# ============================================================

import math
import numpy as np

# ============================================================
# POISSON ROBUSTE
# ============================================================

def poisson_probability(lam, goals):
    try:
        lam = float(lam)
        goals = int(goals)
    except (TypeError, ValueError):
        return 0.0

    if not math.isfinite(lam) or lam < 0 or goals < 0:
        return 0.0

    if lam == 0:
        return 1.0 if goals == 0 else 0.0

    value = math.exp(
        -lam
        + goals * math.log(lam)
        - math.lgamma(goals + 1)
    )

    if not math.isfinite(value):
        return 0.0

    return max(0.0, min(1.0, value))


def poisson_matrix(home_lambda, away_lambda, max_goals=7):
    home_lambda = float(home_lambda)
    away_lambda = float(away_lambda)
    max_goals = int(max_goals)

    if home_lambda < 0 or away_lambda < 0:
        raise ValueError("Les lambdas Poisson ne peuvent pas être négatives.")

    if max_goals < 1:
        raise ValueError("max_goals doit être >= 1.")

    home_probs = np.array([
        poisson_probability(home_lambda, h)
        for h in range(max_goals + 1)
    ], dtype=float)

    away_probs = np.array([
        poisson_probability(away_lambda, a)
        for a in range(max_goals + 1)
    ], dtype=float)

    matrix = np.outer(home_probs, away_probs)

    matrix = np.nan_to_num(
        matrix,
        nan=0.0,
        posinf=0.0,
        neginf=0.0,
    )

    total = float(matrix.sum())

    if total <= 0 or not math.isfinite(total):
        raise ValueError("Matrice Poisson invalide.")

    matrix /= total

    return matrix


# ============================================================
# ANALYSE HUMAINE COMPLÈTE
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
    h2h=None,
    odds=None,
    home_stats=None,
    away_stats=None,
    home_standing=None,
    away_standing=None,
):
    p1 = float(markets.get("1", 0))
    px = float(markets.get("X", 0))
    p2 = float(markets.get("2", 0))

    results = {
        "1": p1,
        "X": px,
        "2": p2,
    }

    ordered = sorted(
        results.items(),
        key=lambda x: x[1],
        reverse=True,
    )

    main_result = ordered[0][0]
    second_result = ordered[1][0]
    gap = ordered[0][1] - ordered[1][1]

    # --------------------------------------------------------
    # LECTURE 1X2
    # --------------------------------------------------------

    if abs(p1 - p2) < 0.08 and px >= 0.27:
        reading = (
            "Match très équilibré : le nul possède un poids "
            "important et une couverture 1X/X2 mérite d'être envisagée."
        )

    elif (
        p1 > p2
        and home_form.get("form_score", 0)
        >= away_form.get("form_score", 0)
    ):
        reading = (
            "Le modèle donne l'avantage au domicile et la forme "
            "récente confirme ce signal."
        )

    elif (
        p2 > p1
        and away_form.get("form_score", 0)
        >= home_form.get("form_score", 0)
    ):
        reading = (
            "L'extérieur possède le meilleur signal 1X2 et "
            "sa dynamique récente renforce ce scénario."
        )

    else:
        reading = (
            "Les signaux sont partagés : le 1X2 sec présente "
            "davantage de risque qu'un marché de couverture."
        )

    # --------------------------------------------------------
    # BUTS
    # --------------------------------------------------------

    over25 = float(markets.get("Over 2.5", 0))
    under25 = float(markets.get("Under 2.5", 0))
    btts_yes = float(markets.get("BTTS Oui", 0))
    btts_no = float(markets.get("BTTS Non", 0))

    if over25 >= 0.60:
        goals = (
            "Le modèle favorise un match ouvert avec au moins "
            "3 buts."
        )
    elif under25 >= 0.60:
        goals = (
            "Le modèle favorise un match fermé avec moins "
            "de 3 buts."
        )
    else:
        goals = (
            "Le total de buts reste équilibré : aucun scénario "
            "Over/Under 2.5 ne domine fortement."
        )

    if btts_yes >= 0.60:
        btts = "BTTS Oui possède un signal statistique fort."

    elif btts_no >= 0.60:
        btts = "BTTS Non possède un signal statistique fort."

    else:
        btts = "Le BTTS reste difficile à départager."

    # --------------------------------------------------------
    # FORME
    # --------------------------------------------------------

    home_score = float(home_form.get("form_score", 0))
    away_score = float(away_form.get("form_score", 0))

    if home_score > away_score + 0.10:
        form_reading = (
            f"{home} possède une dynamique récente nettement "
            f"supérieure."
        )

    elif away_score > home_score + 0.10:
        form_reading = (
            f"{away} possède une dynamique récente nettement "
            f"supérieure."
        )

    else:
        form_reading = (
            "Les dynamiques récentes sont relativement proches."
        )

    # --------------------------------------------------------
    # XG
    # --------------------------------------------------------

    total_xg = home_lambda + away_lambda

    if total_xg >= 3.0:
        xg_reading = "Le niveau de buts attendus est élevé."

    elif total_xg <= 2.0:
        xg_reading = "Le niveau de buts attendus est plutôt faible."

    else:
        xg_reading = "Le niveau de buts attendus est intermédiaire."

    # --------------------------------------------------------
    # H2H
    # --------------------------------------------------------

    h2h_reading = "H2H non disponible."

    if h2h:
        h2h_matches = int(h2h.get("matches", 0))

        if h2h_matches >= 3:
            h2h_reading = (
                f"{h2h_matches} confrontations directes ont été "
                f"prises en compte."
            )

    # --------------------------------------------------------
    # CLASSEMENT
    # --------------------------------------------------------

    ranking_reading = "Classement non disponible."

    if home_standing and away_standing:
        hp = home_standing.get("position")
        ap = away_standing.get("position")

        if hp is not None and ap is not None:

            if hp < ap:
                ranking_reading = (
                    f"{home} est mieux classé ({hp}e contre {ap}e)."
                )

            elif ap < hp:
                ranking_reading = (
                    f"{away} est mieux classé ({ap}e contre {hp}e)."
                )

            else:
                ranking_reading = (
                    "Les deux équipes occupent une position "
                    "similaire au classement."
                )

    # --------------------------------------------------------
    # STATISTIQUES DÉTAILLÉES
    # --------------------------------------------------------

    stats_available = False

    if (
        home_stats
        and away_stats
        and home_stats.get("available")
        and away_stats.get("available")
    ):
        stats_available = True

    stats_reading = (
        "Les statistiques détaillées officielles sont disponibles."
        if stats_available
        else
        "Les statistiques détaillées officielles ne sont pas "
        "suffisamment disponibles."
    )

    # --------------------------------------------------------
    # COTES
    # --------------------------------------------------------

    odds_reading = "Cotes API non disponibles."

    if odds:
        odds_reading = (
            "Les probabilités implicites des cotes sont disponibles "
            "pour comparaison avec le modèle."
        )

    # --------------------------------------------------------
    # SCORE EXACT / MT-FT
    # --------------------------------------------------------

    best_score = (
        scores[0][0]
        if scores
        else "N/D"
    )

    best_htft = (
        htft[0][0]
        if htft
        else "N/D"
    )

    # --------------------------------------------------------
    # CONFIANCE
    # --------------------------------------------------------

    confidence = 50.0

    confidence += gap * 45.0

    if max(
        home_form.get("matches", 0),
        away_form.get("matches", 0),
    ) >= 6:
        confidence += 3

    if h2h and h2h.get("matches", 0) >= 5:
        confidence += 2

    if stats_available:
        confidence += 3

    if odds:
        confidence += 2

    confidence = max(
        50.0,
        min(95.0, confidence),
    )

    # --------------------------------------------------------
    # MARCHÉ LE PLUS FORT
    # --------------------------------------------------------

    market_items = [
        (k, float(v))
        for k, v in markets.items()
        if isinstance(v, (int, float))
    ]

    market_items.sort(
        key=lambda x: x[1],
        reverse=True,
    )

    top_market = (
        market_items[0]
        if market_items
        else ("N/D", 0.0)
    )

    # --------------------------------------------------------
    # RISQUE
    # --------------------------------------------------------

    if confidence >= 80:
        risk = "FAIBLE À MODÉRÉ"

    elif confidence >= 68:
        risk = "MODÉRÉ"

    elif confidence >= 58:
        risk = "MODÉRÉ À ÉLEVÉ"

    else:
        risk = "ÉLEVÉ"

    # --------------------------------------------------------
    # RECOMMANDATION
    # --------------------------------------------------------

    if main_result == "1":
        recommended_cover = "1X"

    elif main_result == "2":
        recommended_cover = "X2"

    else:
        recommended_cover = "1X ou X2 selon le contexte"

    return {
        "main_result": main_result,
        "second_result": second_result,
        "best_score": best_score,
        "best_htft": best_htft,

        "reading": reading,
        "form_reading": form_reading,
        "goals": goals,
        "btts": btts,
        "xg_reading": xg_reading,
        "h2h_reading": h2h_reading,
        "ranking_reading": ranking_reading,
        "stats_reading": stats_reading,
        "odds_reading": odds_reading,

        "confidence": confidence,
        "risk": risk,

        "top_market": top_market[0],
        "top_market_probability": top_market[1],

        "recommended_cover": recommended_cover,

        "model_summary": (
            f"xG {home}: {home_lambda:.2f} | "
            f"xG {away}: {away_lambda:.2f} | "
            f"écart 1X2: {gap * 100:.1f} points."
        ),
    }


# ============================================================
# ANALYSE DES STATISTIQUES OFFICIELLES
# ============================================================

STAT_LABELS = {
    "corner_kicks": "Corners",
    "free_kicks": "Coups francs",
    "goal_kicks": "Dégagements",
    "offsides": "Hors-jeu",
    "fouls": "Fautes",
    "ball_possession": "Possession",
    "saves": "Arrêts",
    "throw_ins": "Touches",
    "shots": "Tirs",
    "shots_on_goal": "Tirs cadrés",
    "shots_off_goal": "Tirs non cadrés",
    "yellow_cards": "Cartons jaunes",
    "yellow_red_cards": "Deuxième jaune",
    "red_cards": "Cartons rouges",
}


def summarize_official_stats(stats):
    if not stats:
        return {
            "available": False,
            "averages": {},
        }

    averages = {}

    for key, value in stats.items():
        try:
            value = float(value)
        except (TypeError, ValueError):
            continue

        if math.isfinite(value):
            averages[key] = round(value, 2)

    return {
        "available": bool(averages),
        "averages": averages,
    }


# ============================================================
# TESTS DE SÉCURITÉ
# ============================================================

def validate_model_integrity():
    assert abs(poisson_probability(0, 0) - 1.0) < 1e-12
    assert abs(poisson_probability(0, 1)) < 1e-12

    matrix = poisson_matrix(1.40, 1.10, 7)

    assert matrix.shape == (8, 8)
    assert np.isfinite(matrix).all()
    assert (matrix >= 0).all()
    assert abs(float(matrix.sum()) - 1.0) < 1e-10

    return True
