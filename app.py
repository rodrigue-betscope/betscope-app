import math
import numpy as np
from flask import Flask, request, jsonify

app = Flask(__name__)

class FootballAnalyzer:
    """Moteur de calcul statistique pour les probabilités de matchs."""
    
    def __init__(self, odds_home, odds_draw, odds_away, max_goals=8):
        self.odds = [odds_home, odds_draw, odds_away]
        self.max_goals = max_goals
        self.p1, self.px, self.p2 = self._remove_margin()
        self.lam_h, self.lam_a = self._estimate_lambdas()

    def _remove_margin(self):
        inv = [1/o for o in self.odds]
        s = sum(inv)
        return [x/s for x in inv]

    def _poisson_pmf(self, k, lam):
        return math.exp(-lam) * (lam ** k) / math.factorial(k)

    def _estimate_lambdas(self):
        best = None
        best_err = 1e9
        # Recherche optimisée par grille
        for lam_h in np.linspace(0.4, 3.5, 40):
            for lam_a in np.linspace(0.3, 3.2, 40):
                p_home, p_draw, p_away = 0.0, 0.0, 0.0
                for i in range(self.max_goals + 1):
                    pi = self._poisson_pmf(i, lam_h)
                    for j in range(self.max_goals + 1):
                        pj = self._poisson_pmf(j, lam_a)
                        p = pi * pj
                        if i > j: p_home += p
                        elif i == j: p_draw += p
                        else: p_away += p
                
                err = (p_home - self.p1)**2 + (p_draw - self.px)**2 + (p_away - self.p2)**2
                if err < best_err:
                    best_err = err
                    best = (lam_h, lam_a)
        return best

    def get_stats(self):
        # Distribution complète des scores
        probs = np.zeros((self.max_goals+1, self.max_goals+1))
        for i in range(self.max_goals+1):
            for j in range(self.max_goals+1):
                probs[i, j] = self._poisson_pmf(i, self.lam_h) * self._poisson_pmf(j, self.lam_a)
        
        # BTTS (Buts > 0 pour les deux)
        btts = np.sum(probs[1:, 1:])
        
        # Over/Under
        ou_stats = {}
        for t in [1.5, 2.5, 3.5, 4.5]:
            # Over = Somme des probas où (i+j) > t
            over_prob = 0
            for i in range(self.max_goals+1):
                for j in range(self.max_goals+1):
                    if (i + j) > t:
                        over_prob += probs[i, j]
            ou_stats[f"Over_{t}"] = round(over_prob, 4)
            ou_stats[f"Under_{t}"] = round(1 - over_prob, 4)

        return {
            "lambdas": {"home": round(self.lam_h, 3), "away": round(self.lam_a, 3)},
            "BTTS_Yes": round(btts, 4),
            "BTTS_No": round(1 - btts, 4),
            "Over_Under": ou_stats
        }

@app.route("/predict", methods=["POST"])
def predict():
    data = request.get_json()
    analyzer = FootballAnalyzer(
        data["odds"]["home"], 
        data["odds"]["draw"], 
        data["odds"]["away"]
    )
    return jsonify(analyzer.get_stats())

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
