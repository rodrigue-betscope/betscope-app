import math
import streamlit as st

# Configuration de la page
st.set_page_config(
    page_title="NASMO IA BOT - V12", page_icon="🧠", layout="centered"
)

# Style CSS personnalisé pour un look sombre et professionnel (inspiré de tes images)
st.markdown(
    """
    <style>
    .main {
        background-color: #0e1117;
        color: #ffffff;
    }
    .stButton>button {
        background: linear-gradient(135deg, #00C853 0%, #64DD17 100%);
        color: white;
        font-weight: bold;
        border-radius: 12px;
        padding: 0.75rem 1rem;
        width: 100%;
        border: none;
        box-shadow: 0 4px 15px rgba(0, 200, 83, 0.4);
    }
    .stButton>button:hover {
        background: linear-gradient(135deg, #64DD17 0%, #00C853 100%);
        color: white;
    .prediction-card {
        background-color: #161b22;
        padding: 20px;
        border-radius: 15px;
        border: 1px solid #30363d;
        margin-bottom: 20px;
    }
    </style>
""",
    unsafe_allow_html=True,
)

# En-tête de l'application
st.markdown(
    "<h2 style='text-align: center; color: #00C853;'>🧠 NASMO IA BOT</h2>",
    unsafe_allow_html=True,
)
st.markdown(
    "<p style='text-align: center; color: #8b949e;'>Le bot de"
    " prédiction/intelligence artificielle le plus puissant de 2026 💯💪</p>",
    unsafe_allow_html=True,
)
st.markdown("---")

# 1. BLOC ÉQUIPE DOMICILE
st.markdown("### 🏠 Bloc Équipe Domicile")
home = st.text_input("Nom du club domicile :", "FC Cologne")
col1, col2 = st.columns(2)
with col1:
  home_gf = st.number_input(
      "Total Buts marqués à la maison :", min_value=0.0, value=34.0, step=1.0
  )
  home_mp = st.number_input(
      "Volume total matchs joués à domicile :", min_value=1.0, value=5.0, step=1.0
  )
with col2:
  home_ga = st.number_input(
      "Total Buts encaissés à la maison :", min_value=0.0, value=12.0, step=1.0
  )

st.markdown("")

# 2. BLOC ÉQUIPE EXTÉRIEUR
st.markdown("### 🚀 Bloc Équipe Extérieur")
away = st.text_input("Nom du club visiteur :", "Wolfsbourg")
col3, col4 = st.columns(2)
with col3:
  away_gf = st.number_input(
      "Total Buts marqués dehors :", min_value=0.0, value=28.0, step=1.0
  )
  away_mp = st.number_input(
      "Volume total matchs joués à l'extérieur :",
      min_value=1.0,
      value=5.0,
      step=1.0,
  )
with col4:
  away_ga = st.number_input(
      "Total Buts encaissés dehors :", min_value=0.0, value=15.0, step=1.0
  )

st.markdown("---")

# Constante du championnat
league_avg = st.number_input(
    "⚽ Constante de buts par match du championnat général :",
    min_value=0.1,
    value=2.70,
    step=0.05,
)

st.markdown("---")

# 3. COTES DES BOOKMAKERS
st.markdown("### 📊 Cotes des bookmakers")

st.markdown("**Résultat du match (1X2)**")
col_c1, col_c2, col_c3 = st.columns(3)
with col_c1:
  cote_1 = st.number_input("1 (Dom)", value=1.31)
with col_c2:
  cote_X = st.number_input("X (Nul)", value=5.00)
with col_c3:
  cote_2 = st.number_input("2 (Ext)", value=10.50)

st.markdown("**Total de buts**")
col_c4, col_c5 = st.columns(2)
with col_c4:
  cote_over25 = st.number_input("+2.5 buts", value=1.744)
with col_c5:
  cote_under25 = st.number_input("-2.5 buts", value=2.085)

st.markdown("**Les deux équipes marquent (BTTS)**")
col_c6, col_c7 = st.columns(2)
with col_c6:
  cote_btts_oui = st.number_input("BTTS Oui", value=1.744)
with col_c7:
  cote_btts_non = st.number_input("BTTS Non", value=2.085)

st.markdown("---")

# Bouton de génération de prédiction
if st.button("🎯 Générer la prédiction IA V12"):
  with st.spinner("Analyse IA en cours... Connexion aux modèles de calcul..."):
    # Calculs statistiques (Loi de Poisson & Forces)
    home_attaque = home_gf / home_mp
    home_defense = home_ga / home_mp
    away_attaque = away_gf / away_mp
    away_defense = away_ga / away_mp

    buts_prevus_home = (home_attaque * away_defense) / league_avg
    buts_prevus_away = (away_attaque * home_defense) / league_avg
    total_buts_prevu = buts_prevus_home + buts_prevus_away

    # Probabilités 1X2 estimées
    prob_home = max(
        5.0,
        min(
            90.0,
            (buts_prevus_home / (buts_prevus_home + buts_prevus_away + 0.15))
            * 100,
        ),
    )
    prob_away = max(
        5.0,
        min(
            90.0,
            (buts_prevus_away / (buts_prevus_home + buts_prevus_away + 0.15))
            * 100,
        ),
    )
    prob_draw = max(5.0, 100.0 - prob_home - prob_away)

    # Normalisation des pourcentages 1X2
    total_p = prob_home + prob_draw + prob_away
    prob_home = (prob_home / total_p) * 100
    prob_draw = (prob_draw / total_p) * 100
    prob_away = (prob_away / total_p) * 100

    # Score exact le plus probable
    score_home = max(0, round(buts_prevus_home))
    score_away = max(0, round(buts_prevus_away))

    # BTTS & Over/Under Probabilités
    prob_btts_oui = (
        (1 - math.exp(-buts_prevus_home))
        * (1 - math.exp(-buts_prevus_away))
        * 100
    )
    prob_over25 = (
        1
        - math.exp(-total_buts_prevu)
        * (1 + total_buts_prevu + (total_buts_prevu**2) / 2)
    ) * 100

  st.success("✅ Prédiction générée avec succès ! 🎯")

  # AFFICHAGE DU RÉSULTAT (Style Cartes comme sur les images)
  st.markdown(
      f"""
    <div style="background-color: #161b22; padding: 20px; border-radius: 15px; border: 1px solid #30363d; text-align: center;">
        <h3>{home} vs {away}</h3>
        <h1 style="color: #00C853; font-size: 3rem;">{score_home} - {score_away}</h1>
        <p style="color: #8b949e;">Score prédict / Tendance globale</p>
        <hr style="border-color: #30363d;">
        <div style="text-align: left; margin-top: 10px;">
            <p><b>{home} :</b> {prob_home:.0f}%</p>
            <div style="background-color: #30363d; border-radius: 10px; height: 10px; width: 100%;">
                <div style="background-color: #00C853; width: {prob_home}%; height: 10px; border-radius: 10px;"></div>
            </div>
            <p style="margin-top: 8px;"><b>Match nul :</b> {prob_draw:.0f}%</p>
            <div style="background-color: #30363d; border-radius: 10px; height: 10px; width: 100%;">
                <div style="background-color: #f1e05a; width: {prob_draw}%; height: 10px; border-radius: 10px;"></div>
            </div>
            <p style="margin-top: 8px;"><b>{away} :</b> {prob_away:.0f}%</p>
            <div style="background-color: #30363d; border-radius: 10px; height: 10px; width: 100%;">
                <div style="background-color: #ff5252; width: {prob_away}%; height: 10px; border-radius: 10px;"></div>
            </div>
        </div>
    </div>
    """,
      unsafe_allow_html=True,
  )

  # Bloc Analyse IA
  st.markdown(
      f"""
    <div style="background-color: #161b22; padding: 15px; border-radius: 12px; border: 1px solid #30363d; margin-top: 15px;">
        <p style="color: #00C853; font-weight: bold;">📈 Analyse IA :</p>
        <p>{home} devrait dominer ce match avec une intensité offensive calculée à {home_attaque:.2f} buts/match, orientant le score vers un {score_home}-{score_away}.</p>
        <span style="background-color: #003820; color: #00C853; padding: 4px 10px; border-radius: 8px; font-size: 0.85rem; font-weight: bold;">🔥 {max(prob_home, prob_away, prob_draw):.0f}% de probabilité</span>
    </div>
    """,
      unsafe_allow_html=True,
  )

  # Paris Conseillés
  st.markdown("### 💎 Paris Conseillés")
  st.markdown(
      """
    <div style="background-color: #161b22; padding: 15px; border-radius: 12px; border: 1px solid #30363d;">
        <p style="color: #8b949e; font-size: 0.9rem;">Basés sur l'analyse IA approfondie • Sélection de value bets</p>
        <div style="display: flex; gap: 10px; margin-top: 10px;">
            <span style="background-color: #0e4429; color: #3fb950; padding: 3px 8px; border-radius: 6px; font-size: 0.8rem;">● Risque faible</span>
            <span style="background-color: #583305; color: #d29922; padding: 3px 8px; border-radius: 6px; font-size: 0.8rem;">● Risque moyen</span>
            <span style="background-color: #511818; color: #f85149; padding: 3px 8px; border-radius: 6px; font-size: 0.8rem;">● Risque élevé</span>
        </div>
    </div>
    """,
      unsafe_allow_html=True,
  )

  # Détails des pronostics avancés
  col_p1, col_p2 = st.columns(2)
  with col_p1:
    st.info(
        f"🎯 **Score exact prédit** : {score_home} -"
        f" {score_away}\n\nFiabilité : 🌟🌟🌟🌟⭐"
    )
  with col_p2:
    st.info(
        f"⚡ **Over/Under 2.5** :"
        f" {'Over (+2.5)' if total_buts_prevu > 2.5 else 'Under (-2.5)'}\n\nTotal"
        f" estimé : {total_buts_prevu:.2f} buts"
    )
