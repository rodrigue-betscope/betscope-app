import math
import streamlit as st

# Configuration de la page
st.set_page_config(
    page_title="NASMO IA BOT - V15 ULTIMATE", page_icon="🧠", layout="centered"
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

st.title("🧠 NASMO IA BOT - V15 ULTIMATE")
st.markdown(
    "<p style='color: #8b949e;'>Moteur prédictif à Loi de Poisson dynamique"
    " 💯🔥</p>",
    unsafe_allow_html=True,
)

# Organisation par Onglets
tab1, tab2, tab3 = st.tabs(
    ["⚙️ Configuration & Cotes", "📊 Analyse IA", "💎 Conseils Pro & Marchés"]
)


def poisson_prob(lmbda, k):
  return (math.exp(-max(0.01, lmbda)) * (max(0.01, lmbda) ** k)) / math.factorial(
      k
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

  c1, c2, c3 = st.columns(3)
  with c1:
    cote_1 = st.number_input("Cote 1 (Dom)", value=1.85)
  with c2:
    cote_X = st.number_input("Cote X (Nul)", value=3.40)
  with c3:
    cote_2 = st.number_input("Cote 2 (Ext)", value=4.20)

  c4, c5 = st.columns(2)
  with c4:
    cote_over25 = st.number_input("Cote Over 2.5", value=1.95)
  with c5:
    cote_under25 = st.number_input("Cote Under 2.5", value=1.85)

  c6, c7 = st.columns(2)
  with c6:
    cote_btts_oui = st.number_input("Cote BTTS Oui", value=1.80)
  with c7:
    cote_btts_non = st.number_input("Cote BTTS Non", value=1.95)

with tab2:
  st.subheader("Lancer l'analyse intelligente")
  if st.button("🎯 Générer l'analyse V15 ULTIMATE"):
    with st.spinner(
        "Calcul des matrices de Poisson et des probabilités de match..."
    ):
      # Calcul des forces
      h_att = home_gf / home_mp
      h_def = home_ga / home_mp
      a_att = away_gf / away_mp
      a_def = away_ga / away_mp

      # Expected goals avec avantage domicile
      lambda_home = (h_att * a_def * 1.08) / league_avg
      lambda_away = (a_att * h_def * 0.95) / league_avg

      # Matrice de Poisson (0 à 6 buts)
      max_goals = 6
      matrix = [[0.0] * max_goals for _ in range(max_goals)]
      max_p = -1.0
      best_h, best_away = 1, 0

      p_home_win = 0.0
      p_draw = 0.0
      p_away_win = 0.0
      p_over25 = 0.0
      p_btts_oui = 0.0

      for h in range(max_goals):
        for a in range(max_goals):
          p = poisson_prob(lambda_home, h) * poisson_prob(lambda_away, a)
          matrix[h][a] = p
          if p > max_p:
            max_p = p
            best_h, best_away = h, a

          if h > a:
            p_home_win += p
          elif h == a:
            p_draw += p
          else:
            p_away_win += p

          if h + a > 2.5:
            p_over25 += p
          if h > 0 and a > 0:
            p_btts_oui += p

      # Normalisation
      total_sum = p_home_win + p_draw + p_away_win
      if total_sum > 0:
        p_home_win = (p_home_win / total_sum) * 100
        p_draw = (p_draw / total_sum) * 100
        p_away_win = (p_away_win / total_sum) * 100

      p_over25 = p_over25 * 100
      p_under25 = 100 - p_over25
      p_btts_oui = p_btts_oui * 100
      p_btts_non = 100 - p_btts_oui

      # Indice de confiance basé sur l'écart de probabilité
      max_prob_1x2 = max(p_home_win, p_draw, p_away_win)
      confidence = min(96, int(max_prob_1x2 * 0.8 + abs(lambda_home - lambda_away) * 15 + 25))

      # Stockage session
      st.session_state["analyzed"] = True
      st.session_state["sh"] = best_h
      st.session_state["sa"] = best_away
      st.session_state["ph"] = p_home_win
      st.session_state["pd"] = p_draw
      st.session_state["pa"] = p_away_win
      st.session_state["p_over"] = p_over25
      st.session_state["p_under"] = p_under25
      st.session_state["p_btts_o"] = p_btts_oui
      st.session_state["p_btts_n"] = p_btts_non
      st.session_state["conf"] = confidence
      st.session_state["tot_goals"] = lambda_home + lambda_away

    st.success("✅ Analyse générée avec un succès total !")

    # Affichage carte principale
    st.markdown(
        f"""
        <div class="card" style="text-align: center;">
            <h3>{home} vs {away}</h3>
            <h1 style="color: #00C853; font-size: 3.5rem;">{best_h} - {best_away}</h1>
            <p style="color: #8b949e;">Score Exact le plus probable (Loi de Poisson)</p>
            <hr style="border-color: #30363d;">
            <div style="text-align: left;">
                <p><b>{home} :</b> {p_home_win:.0f}%</p>
                <div style="background-color: #30363d; border-radius: 10px; height: 8px;"><div style="background-color: #00C853; width: {p_home_win}%; height: 8px; border-radius: 10px;"></div></div>
                <p style="margin-top: 8px;"><b>Match nul :</b> {p_draw:.0f}%</p>
                <div style="background-color: #30363d; border-radius: 10px; height: 8px;"><div style="background-color: #f1e05a; width: {p_draw}%; height: 8px; border-radius: 10px;"></div></div>
                <p style="margin-top: 8px;"><b>{away} :</b> {p_away_win:.0f}%</p>
                <div style="background-color: #30363d; border-radius: 10px; height: 8px;"><div style="background-color: #ff5252; width: {p_away_win}%; height: 8px; border-radius: 10px;"></div></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
  else:
    st.info("Renseigne tes données dans l'onglet 'Configuration' puis lance l'analyse.")

with tab3:
  st.subheader("💎 Conseils Pro, Over/Under & Marchés")
  if "analyzed" in st.session_state and st.session_state["analyzed"]:
    sh = st.session_state["sh"]
    sa = st.session_state["sa"]
    p_over = st.session_state["p_over"]
    p_under = st.session_state["p_under"]
    p_btts_o = st.session_state["p_btts_o"]
    p_btts_n = st.session_state["p_btts_n"]
    conf = st.session_state["conf"]
    tot = st.session_state["tot_goals"]

    # Affichage des marchés détaillés
    col_a, col_b = st.columns(2)
    with col_a:
      st.markdown(
          f"""
            <div class="card">
                <p style="color: #00C853; font-weight: bold;">📊 Over / Under 2.5</p>
                <h3>{'🟢 Over 2.5' if p_over > 50 else '🔴 Under 2.5'}</h3>
                <p>Probabilité : <b>{max(p_over, p_under):.1f}%</b></p>
                <p style="font-size: 0.85rem; color: #8b949e;">Buts attendus : {tot:.2f}</p>
            </div>
            """,
          unsafe_allow_html=True,
      )
    with col_b:
      st.markdown(
          f"""
            <div class="card">
                <p style="color: #00C853; font-weight: bold;">⚽ Les 2 équipes marquent (BTTS)</p>
                <h3>{'✅ OUI' if p_btts_o > 50 else '❌ NON'}</h3>
                <p>Probabilité : <b>{max(p_btts_o, p_btts_n):.1f}%</b></p>
            </div>
            """,
          unsafe_allow_html=True,
      )

    st.markdown(
        f"""
        <div class="card">
            <h4>💡 Synthèse & Pari le Plus Safe</h4>
            <p><b>Indice de Confiance IA :</b> <span style="color: #3fb950; font-weight: bold;">{conf}%</span></p>
            <p><b>Score exact recommandé :</b> {sh} - {sa}</p>
            <hr style="border-color: #30363d;">
            <p style="color: #58a6ff;"><b>Conseil de l'algorithme :</b> Privilégier une double chance ou un pari sécurisé sur les buts si l'écart de force est serré.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
  else:
    st.warning("⚠️ Veuillez d'abord lancer l'analyse dans l'onglet 'Analyse IA'.")
