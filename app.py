import math
import streamlit as st

# Configuration de la page
st.set_page_config(
    page_title="NASMO IA BOT - V14 PRO", page_icon="🧠", layout="centered"
)

# Style CSS sombre et moderne
st.markdown(
    """
    <style>
    .main { background-color: #0e1117; color: white; }
    .card { background-color: #161b22; padding: 20px; border-radius: 15px; border: 1px solid #30363d; margin-bottom: 15px; }
    .stButton>button {
        background: linear-gradient(135deg, #00C853 0%, #64DD17 100%);
        color: white;
        font-weight: bold;
        border-radius: 12px;
        padding: 0.75rem 1rem;
        width: 100%;
        border: none;
    }
    </style>
""",
    unsafe_allow_html=True,
)

st.title("🧠 NASMO IA BOT - V14 Intelligent PRO")

# Organisation par Onglets
tab1, tab2, tab3 = st.tabs(
    ["⚙️ Configuration & Cotes", "📊 Analyse IA", "💎 Conseils Pro"]
)

with tab1:
  st.subheader("🏠 Bloc Équipe Domicile")
  home = st.text_input("Nom du club domicile :", "FC Cologne")
  col1, col2 = st.columns(2)
  with col1:
    home_gf = st.number_input(
        "Total Buts marqués (Dom) :", min_value=0.0, value=34.0, step=1.0
    )
    home_mp = st.number_input(
        "Matchs joués (Dom) :", min_value=1.0, value=5.0, step=1.0
    )
  with col2:
    home_ga = st.number_input(
        "Total Buts encaissés (Dom) :", min_value=0.0, value=12.0, step=1.0
    )

  st.markdown("---")
  st.subheader("🚀 Bloc Équipe Extérieur")
  away = st.text_input("Nom du club visiteur :", "Wolfsbourg")
  col3, col4 = st.columns(2)
  with col3:
    away_gf = st.number_input(
        "Total Buts marqués (Ext) :", min_value=0.0, value=28.0, step=1.0
    )
    away_mp = st.number_input(
        "Matchs joués (Ext) :", min_value=1.0, value=5.0, step=1.0
    )
  with col4:
    away_ga = st.number_input(
        "Total Buts encaissés (Ext) :", min_value=0.0, value=15.0, step=1.0
    )

  st.markdown("---")
  league_avg = st.number_input(
      "⚽ Constante de buts par match du championnat :",
      min_value=0.1,
      value=2.70,
      step=0.05,
  )

  st.markdown("---")
  st.subheader("📊 Cotes des Bookmakers")

  st.markdown("**Résultat du match (1X2)**")
  c1, c2, c3 = st.columns(3)
  with c1:
    cote_1 = st.number_input("1 (Dom)", value=1.31)
  with c2:
    cote_X = st.number_input("X (Nul)", value=5.00)
  with c3:
    cote_2 = st.number_input("2 (Ext)", value=10.50)

  st.markdown("**Total de buts**")
  c4, c5 = st.columns(2)
  with c4:
    cote_over25 = st.number_input("+2.5 buts", value=1.744)
  with c5:
    cote_under25 = st.number_input("-2.5 buts", value=2.085)

  st.markdown("**Les deux équipes marquent (BTTS)**")
  c6, c7 = st.columns(2)
  with c6:
    cote_btts_oui = st.number_input("BTTS Oui", value=1.744)
  with c7:
    cote_btts_non = st.number_input("BTTS Non", value=2.085)

with tab2:
  st.subheader("Lancer le moteur d'intelligence IA")
  if st.button("🎯 Générer la prédiction IA V14"):
    with st.spinner("Analyse des statistiques et calcul des cotes..."):
      # Calculs avancés
      home_att = home_gf / home_mp
      home_def = home_ga / home_mp
      away_att = away_gf / away_mp
      away_def = away_ga / away_mp

      # Avantage domicile
      home_adv = 1.1

      pred_home = (home_att * away_def * home_adv) / league_avg
      pred_away = (away_att * home_def) / league_avg
      total_buts_prevu = pred_home + pred_away

      # Probabilités 1X2
      raw_home = (pred_home / (pred_home + pred_away + 0.2)) * 100
      raw_away = (pred_away / (pred_home + pred_away + 0.2)) * 100
      prob_draw = max(5.0, 100.0 - raw_home - raw_away)
      total_p = raw_home + prob_draw + raw_away
      prob_home = (raw_home / total_p) * 100
      prob_away = (raw_away / total_p) * 100

      score_home = max(0, round(pred_home))
      score_away = max(0, round(pred_away))

      # Value bet sur le favori domicile
      value_score = (prob_home / 100) * cote_1
      confidence = min(99, abs(pred_home - pred_away) * 25 + 45)

      # Stockage pour l'onglet conseils
      st.session_state["val_score"] = value_score
      st.session_state["conf"] = confidence
      st.session_state["shome"] = score_home
      st.session_state["saway"] = score_away
      st.session_state["phome"] = prob_home
      st.session_state["pdraw"] = prob_draw
      st.session_state["paway"] = prob_away
      st.session_state["tot"] = total_buts_prevu

    st.success("✅ Analyse terminée avec succès !")

    # Affichage du résultat style carte
    st.markdown(
        f"""
        <div class="card" style="text-align: center;">
            <h3>{home} vs {away}</h3>
            <h1 style="color: #00C853; font-size: 3rem;">{score_home} - {score_away}</h1>
            <p style="color: #8b949e;">Score prédit par l'IA</p>
            <hr style="border-color: #30363d;">
            <div style="text-align: left;">
                <p><b>{home} :</b> {prob_home:.0f}%</p>
                <div style="background-color: #30363d; border-radius: 10px; height: 8px;"><div style="background-color: #00C853; width: {prob_home}%; height: 8px; border-radius: 10px;"></div></div>
                <p style="margin-top: 6px;"><b>Match nul :</b> {prob_draw:.0f}%</p>
                <div style="background-color: #30363d; border-radius: 10px; height: 8px;"><div style="background-color: #f1e05a; width: {prob_draw}%; height: 8px; border-radius: 10px;"></div></div>
                <p style="margin-top: 6px;"><b>{away} :</b> {prob_away:.0f}%</p>
                <div style="background-color: #30363d; border-radius: 10px; height: 8px;"><div style="background-color: #ff5252; width: {prob_away}%; height: 8px; border-radius: 10px;"></div></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
  else:
    st.info(
        "Remplis bien tes paramètres dans l'onglet 'Configuration' puis clique"
        " sur le bouton."
    )

with tab3:
  st.subheader("💎 Conseils Pro & Value Bets")
  if "conf" in st.session_state:
    st.markdown(
        f"""
        <div class="card">
            <p><b>Indice de confiance IA :</b> {st.session_state['conf']:.0f}%</p>
            <p><b>Total buts attendus :</b> {st.session_state['tot']:.2f}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.session_state["val_score"] > 1.05:
      st.success(
          "💎 **VALUE BET DÉTECTÉ** : La cote de la victoire domicile est"
          " mathématiquement avantageuse par rapport au risque !"
      )
    else:
      st.warning(
          "⚠️ Pas de value bet flagrant sur le 1X2, examine les marchés Over/Under"
          " ou BTTS."
      )
  else:
    st.warning("Veuillez d'abord lancer l'analyse dans l'onglet 'Analyse IA'.")
