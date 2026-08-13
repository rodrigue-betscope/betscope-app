import math
import numpy as np
from flask import Flask, request, jsonify

app = Flask(__name__)

def poisson_pmf(k, lam):
    if lam <= 0:
        return 1.0 if k == 0 else 0.0
    return math.exp(-lam) * (lam ** k) / math.factorial(k)

def remove_margin_from_odds(odds):
    """Retire la marge du bookmaker pour obtenir les vraies probabilités nettes."""
    inv = [1/o for o in odds]
    s = sum(inv)
    return [x / s for x in inv]

def estimate_lambdas_from_1x2(p1, px, p2):
    """Trouve les paramètres de buts (lambdas) les plus fidèles aux cotes du marché."""
    best = None
    best_err = 1e9

    # Balayage précis des scénarios de buts
    for lam_h in np.linspace(0.3, 4.0, 75):
        for lam_a in np.linspace(0.2, 3.5, 67):
            max_goals = 8
            p_home, p_draw, p_away = 0.0, 0.0, 0.0

            for i in range(max_goals + 1):
                pi = poisson_pmf(i, lam_h)
                for j in range(max_goals + 1):
                    pj = poisson_pmf(j, lam_a)
                    p = pi * pj
                    if i > j:
                        p_home += p
                    elif i == j:
                        p_draw += p
                    else:
                        p_away += p

            err = (p_home - p1) ** 2 + (p_draw - px) ** 2 + (p_away - p2) ** 2
            if err < best_err:
                best_err = err
                best = (lam_h, lam_a, p_home, p_draw, p_away)

    return best[0], best[1]

def get_exact_scores(lam_h, lam_a, max_goals=5):
    """Calcule la grille des scores exacts avec des pourcentages normalisés à 100%."""
    dist = []
    total_p = 0.0
    
    # Calcul initial
    for i in range(max_goals + 1):
        for j in range(max_goals + 1):
            p = poisson_pmf(i, lam_h) * poisson_pmf(j, lam_a)
            dist.append({"score": f"{i}-{j}", "prob_raw": p})
            total_p += p
            
    # Normalisation pour obtenir de vrais pourcentages exacts sur les scores affichés
    for item in dist:
        item["percentage"] = round((item["prob_raw"] / total_p) * 100, 2)
        del item["prob_raw"]
        
    dist.sort(key=lambda x: x["percentage"], reverse=True)
    return dist

@app.route("/predict", methods=["POST"])
def predict():
    data = request.get_json(force=True)

    odds = data["odds"]
    p1, px, p2 = remove_margin_from_odds([float(odds["home"]), float(odds["draw"]), float(odds["away"])])

    # Estimation des forces d'attaque à 90 min
    lam_h_full, lam_a_full = estimate_lambdas_from_1x2(p1, px, p2)

    # Ajustement scientifique pour la 1ère mi-temps (45% de la masse de buts générale)
    lam_h_ht = lam_h_full * 0.45
    lam_a_ht = lam_a_full * 0.45

    # Génération des vrais pourcentages de scores exacts (Top 6)
    scores_mt1 = get_exact_scores(lam_h_ht, lam_a_ht, max_goals=4)[:6]
    scores_fm = get_exact_scores(lam_h_full, lam_a_full, max_goals=5)[:6]

    return jsonify({
        "status": "success",
        "notice": "Les pourcentages représentent des probabilités statistiques réelles basées sur les forces offensives.",
        "exact_scores_first_half_percentage": scores_mt1,
        "exact_scores_full_time_percentage": scores_fm
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
    
