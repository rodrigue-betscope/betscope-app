import math
import numpy as np
import streamlit as st

st.set_page_config(
    page_title="BetScope - Poisson v12 Ultra-Précis",
    page_icon="⚽",
    layout="centered"
)

class UltraFootballAnalyzer:
    def __init__(self, odds_home, odds_draw, odds_away, max_goals=10):
        self.odds = [odds_home, odds_draw, odds_away]
        self.max_goals = max_goals
        self.p1, self.px, self.p2 = self._remove_margin()
        self.lam_h, self.lam_a = self._high_precision_lambdas()

    def _remove_margin(self):
        inv = [1/o for o in self.odds]
        s = sum(inv)
        return [x/s for x in inv]

    def _poisson_pmf(self, k, lam):
        return math.exp(-lam) * (lam ** k) / math.factorial(k)

    def _high_precision_lambdas(self):
        """Recherche optimisée avec une haute résolution pour une précision maximale."""
        best = None
        best_err = 1e9
        # Résolution fine (pas de 0.02) pour capturer la valeur exacte
        for lam_h in np.linspace(0.2, 4.0, 100):
            for lam_a in np.linspace(0.2, 4.0, 100):
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

    def get_full_analysis(self):
        probs = np.zeros((self.max_goals+1, self.max_goals+1))
        score_list = []
        
        for i in range(self.max_goals+1):
            for j in range(self.max_goals+1):
                p = self._poisson_pmf(i, self.lam_h) * self._poisson_pmf(j, self.lam_a)
                probs[i, j] = p
                score_list.append((i, j, p))
        
        score_list.sort(key=lambda x: x[2], reverse=True)
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

        ph_val, pd_val, pa_val = 0.0, 0.0, 0.0
        for i in range(self.max_goals+1):
            for j in range(self.max_goals+1):
                if i > j: ph_val += probs[i, j]
                elif i == j: pd_val += probs[i, j]
                else: pa_val += probs[i, j]

        return {
            "lambda_home": round(self.lam_h, 3),
            "lambda_away": round(self.lam_a, 3),
            "p_1x2": {"1": round(ph_val*100, 2), "X": round(pd_val*100, 2), "2": round(pa_val*100, 2)},
            "btts_yes": round(btts * 100, 2),
            "btts_no": round((1 - btts) * 100, 2),
            "over_under": ou_stats,
            "top_scores": score_list[:5]
        }

st.title("⚽ BetScope : Moteur Poisson Ultra-Précis")
st.markdown("Calculs mathématiques avancés pour estimer les probabilités réelles sans marge.")

with st.form("prediction_form"):
    st.subheader("📊 Paramètres du Match")
    col1, col2, col3 = st.columns(3)
    with col1:
        odds_home = st.number_input("Cote Domicile (1)", min_value=1.01, value=2.33, step=0.01)
    with col2:
        odds_draw = st.number_input("Cote Nul (X)", min_value=1.01, value=2.78, step=0.01)
    with col3:
        odds_away = st.number_input("Cote Extérieur (2)", min_value=1.01, value=3.20, step=0.01)
        
    submitted = st.form_submit_button("Lancer les calculs de haute précision 🚀")

if submitted:
    with st.spinner("Analyse statistique approfondie en cours..."):
        analyzer = UltraFootballAnalyzer(odds_home, odds_draw, odds_away)
        stats = analyzer.get_full_analysis()
    
    st.success("Calculs terminés avec succès !")
    
    st.subheader("🎯 Probabilités Réelles (1X2)")
    c1, c2, c3 = st.columns(3)
    c1.metric("1 (Domicile)", f"{stats['p_1x2']['1']} %")
    c2.metric("X (Nul)", f"{stats['p_1x2']['X']} %")
    c3.metric("2 (Extérieur)", f"{stats['p_1x2']['2']} %")
    
    st.subheader("📈 Buts Attendus (Lambdas)")
    la, lb = st.columns(2)
    la.metric("Lambda Domicile", stats["lambda_home"])
    lb.metric("Lambda Extérieur", stats["lambda_away"])

    st.subheader("🏆 Top 5 Scores Exacts")
    cols_score = st.columns(5)
    for idx, (h, a, p) in enumerate(stats["top_scores"]):
        with cols_score[idx]:
            st.metric(f"{h} - {a}", f"{round(p*100, 1)} %")

    st.subheader("📊 Seuils Over / Under & BTTS")
    col_x, col_y = st.columns(2)
    with col_x:
        st.write("**Over / Under 2.5 :**")
        st.metric("Over 2.5", f"{stats['over_under']['Over 2.5']} %")
        st.metric("Under 2.5", f"{stats['over_under']['Under 2.5']} %")
    with col_y:
        st.write("**Les deux équipes marquent (BTTS) :**")
        st.metric("BTTS Oui", f"{stats['btts_yes']} %")
        st.metric("BTTS Non", f"{stats['btts_no']} %")
