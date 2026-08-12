import math
import numpy as np
import streamlit as st

# Configuration de la page Streamlit
st.set_page_config(
    page_title="BetScope - Poisson v12",
    page_icon="⚽",
    layout="centered"
)

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
        probs = np.zeros((self.max_goals+1, self.max_goals+1))
        for i in range(self.max_goals+1):
            for j in range(self.max_goals+1):
                probs[i, j] = self._poisson_pmf(i, self.lam_h) * self._poisson_pmf(j, self.lam_a)
        
        btts = np.sum(probs[1:, 1:])
        
        ou_stats = {}
        for t in [1.5, 2.5, 3.5, 4.5]:
            over_prob = 0
            for i in range(self.max_goals+1):
                for j in range(self.max_goals+1):
                    if (i + j) > t:
                        over_prob += probs[i, j]
            ou_stats[f"Over {t}"] = round(over_prob * 100, 2)
            ou_stats[f"Under {t}"] = round((1 - over_prob) * 100, 2)

        return {
            "lambda_home": round(self.lam_h, 3),
            "lambda_away": round(self.lam_a, 3),
            "btts_yes": round(btts * 100, 2),
            "btts_no": round((1 - btts) * 100, 2),
            "over_under": ou_stats
        }

# --- Interface Utilisateur Streamlit ---
st.title("⚽ BetScope : Poisson v12 Predictor")
st.markdown("Entrez les cotes du match pour analyser les statistiques et probabilités via le modèle de Poisson.")

with st.form("prediction_form"):
    st.subheader("📊 Saisie des Cotes du Match")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        odds_home = st.number_input("Cote Domicile (1)", min_value=1.01, value=2.33, step=0.01)
    with col2:
        odds_draw = st.number_input("Cote Nul (X)", min_value=1.01, value=2.78, step=0.01)
    with col3:
        odds_away = st.number_input("Cote Extérieur (2)", min_value=1.01, value=3.20, step=0.01)
        
    submitted = st.form_submit_button("Lancer l'analyse 🚀")

if submitted:
    analyzer = FootballAnalyzer(odds_home, odds_draw, odds_away)
    stats = analyzer.get_stats()
    
    st.success("Analyse effectuée avec succès !")
    
    # Affichage des Buts Attendus (Lambdas)
    st.subheader("🎯 Buts Attendus (Lambda)")
    col_a, col_b = st.columns(2)
    col_a.metric("Domicile (Lambda H)", stats["lambda_home"])
    col_b.metric("Extérieur (Lambda A)", stats["lambda_away"])
    
    # Affichage BTTS
    st.subheader("🤝 Les Deux Équipes Marquent (BTTS)")
    col_c, col_d = st.columns(2)
    col_c.metric("BTTS Oui", f"{stats['btts_yes']} %")
    col_d.metric("BTTS Non", f"{stats['btts_no']} %")
    
    # Affichage Over / Under
    st.subheader("📈 Seuils Over / Under")
    ou_cols = st.columns(2)
    items = list(stats["over_under"].items())
    
    for idx, (market, prob) in enumerate(items):
        with ou_cols[idx % 2]:
            st.metric(market, f"{prob} %")
