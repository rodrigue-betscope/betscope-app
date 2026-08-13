import math
import numpy as np
import streamlit as st

st.set_page_config(
    page_title="BetScope - Poisson v12 Pro",
    page_icon="⚽",
    layout="centered"
)

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
                best = (lam_h, lam_a)

    return best[0], best[1]

def get_exact_scores(lam_h, lam_a, max_goals=5):
    """Calcule la grille des scores exacts avec des pourcentages normalisés à 100%."""
    dist = []
    total_p = 0.0
    
    for i in range(max_goals + 1):
        for j in range(max_goals + 1):
            p = poisson_pmf(i, lam_h) * poisson_pmf(j, lam_a)
            dist.append({"score": f"{i}-{j}", "prob_raw": p})
            total_p += p
            
    for item in dist:
        item["percentage"] = round((item["prob_raw"] / total_p) * 100, 2)
        del item["prob_raw"]
        
    dist.sort(key=lambda x: x["percentage"], reverse=True)
    return dist

# --- Interface Graphique Streamlit ---
st.title("⚽ BetScope : Moteur Poisson Précis")
st.markdown("Calculs statistiques rigoureux avec pourcentages normalisés à 100%.")

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
    with st.spinner("Analyse des forces et calcul des scores en cours..."):
        p1, px, p2 = remove_margin_from_odds([float(odds_home), float(odds_draw), float(odds_away)])

        # Estimation des forces d'attaque
        lam_h_full, lam_a_full = estimate_lambdas_from_1x2(p1, px, p2)

        # Ajustement pour la 1ère mi-temps (45% de la masse de buts)
        lam_h_ht = lam_h_full * 0.45
        lam_a_ht = lam_a_full * 0.45

        # Génération des pourcentages normalisés
        scores_mt1 = get_exact_scores(lam_h_ht, lam_a_ht, max_goals=4)[:4]
        scores_fm = get_exact_scores(lam_h_full, lam_a_full, max_goals=5)[:6]

    st.success("Analyse effectuée avec succès !")

    # Affichage Mi-Temps
    st.subheader("⏱️ Top Scores Exacts - 1ère Mi-Temps (HT)")
    cols_ht = st.columns(len(scores_mt1))
    for idx, item in enumerate(scores_mt1):
        with cols_ht[idx]:
            st.metric(f"Score {item['score']}", f"{item['percentage']} %")

    # Affichage Fin de Match
    st.subheader("🏆 Top Scores Exacts - Fin du Match (FT)")
    cols_ft = st.columns(3)
    for idx, item in enumerate(scores_fm):
        col_target = cols_ft[idx % 3]
        col_target.metric(f"Score {item['score']}", f"{item['percentage']} %")
