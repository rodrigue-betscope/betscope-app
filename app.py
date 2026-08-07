import math
import streamlit as st

# Configuration de la page
st.set_page_config(
    page_title="NASMO IA BOT - V16 MI-TEMPS PRO", page_icon="⏱️", layout="centered"
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

st.title("⏱️ NASMO IA BOT - V16 MI-TEMPS PRO")
st.markdown(
    "<p style='color: #8b949e;'>Spécialiste des prédictions et scores exacts en"
    " 1ère Mi-Temps (HT) 💯🔥</p>",
    unsafe_allow_html=True,
)


def poisson(lmbda, k):
  return (math.exp(-max(0.01, lmbda)) * (max(0.01, lmbda) ** k)) / math.factorial(
      k
  )


# Organisation par Onglets
tab1, tab2, tab3 = st.tabs(
    ["⚙️ Stats 1ère Mi-Temps", "📊 Analyse HT", "💎 Marchés & Scores HT"]
)

with tab1:
  st.subheader("🏠 Équipe Domicile (1ère Période)")
  home = st.text_input("Nom domicile :", "FC Cologne")
  c1, c2 = st.columns(2)
  with c1:
    h_ht_gf = st.number_input(
        "Buts marqués en 1ère mi-temps (Dom) :",
        min_value=0.0,
        value=1.5,
        step=0.5,
    )
    h_ht_mp = st.number_input(
        "Matchs joués (Dom) :", min_value=1.0, value=5.0, step=1.0
    )
  with c2:
    h_ht_ga = st.number_input(
        "Buts encaissés en 1ère mi-temps (Dom) :",
        min_value=0.0,
        value=0.5,
        step=0.5,
    )

  st.markdown("---")
  st.subheader("🚀 Équipe Extérieure (1ère Période)")
  away = st.text_input("Nom extérieur :", "Wolfsbourg")
  c3, c4 = st.columns(2)
  with c3:
    a_ht_gf = st.number_input(
        "Buts marqués en 1ère mi-temps (Ext) :",
        min_value=0.0,
        value=1.0,
        step=0.5,
    )
    a_ht_mp = st.number_input(
        "Matchs joués (Ext) :", min_value=1.0, value=5.0, step=1.0
    )
  with c4:
    a_ht_ga = st.number_input(
        "Buts encaissés en 1ère mi-temps (Ext) :",
        min_value=0.0,
        value=0.8,
        step=0.5,
    )

  st.markdown("---")
  ht_league_avg = st.number_input(
      "⚽ Moyenne de buts championnat en 1ère mi-temps :",
      min_value=0.1,
      value=1.15,
      step=0.05,
  )

with tab2:
  st.subheader("Lancer l'analyse 1ère Mi-Temps")
  if st.button("🎯 Calculer les tendances Mi-Temps (HT)"):
    with st.spinner("Analyse des stats de première période..."):
      # Calculs Poisson 1ère mi-temps
      h_att_ht = h_ht_gf / h_ht_mp
      h_def_ht = h_ht_ga / h_ht_mp
      a_att_ht = a_ht_gf / a_ht_mp
      a_def_ht = a_ht_ga / a_ht_mp

      lambda_h_ht = (h_att_ht * a_def_ht * 1.05) / ht_league_avg
      lambda_a_ht = (a_att_ht * h_def_ht * 0.95) / ht_league_avg

      max_g = 4
      best_h_ht, best_a_ht = 0, 0
      max_p_ht = -1.0

      p_h_win_ht, p_draw_ht, p_a_win_ht = 0.0, 0.0, 0.0
      p_over05_ht, p_under15_ht = 0.0, 0.0

      for h in range(max_g):
        for a in range(max_g):
          p = poisson(lambda_h_ht, h) * poisson(lambda_a_ht, a)
          if p > max_p_ht:
            max_p_ht = p
            best_h_ht, best_a_ht = h, a

          if h > a:
            p_h_win_ht += p
          elif h == a:
            p_draw_ht += p
          else:
            p_a_win_ht += p

          if h + a >= 1:
            p_over05_ht += p
          if h + a <= 1:
            p_under15_ht += p

      tot_p = p_h_win_ht + p_draw_ht + p_a_win_ht
      if tot_p > 0:
        p_h_win_ht = (p_h_win_ht / tot_p) * 100
        p_draw_ht = (p_draw_ht / tot_p) * 100
        p_a_win_ht = (p_a_win_ht / tot_p) * 100

      p_over05_ht = p_over05_ht * 100
      p_under15_ht = p_under15_ht * 100

      confidence_ht = min(
          95, int(max(p_h_win_ht, p_draw_ht, p_a_win_ht) * 0.85 + 20)
      )

      st.session_state["analyzed_ht"] = True
      st.session_state["sh_ht"] = best_h_ht
      st.session_state["sa_ht"] = best_a_ht
      st.session_state["ph_ht"] = p_h_win_ht
      st.session_state["pd_ht"] = p_draw_ht
      st.session_state["pa_ht"] = p_a_win_ht
      st.session_state["p_ov05"] = p_over05_ht
      st.session_state["p_un15"] = p_under15_ht
      st.session_state["conf_ht"] = confidence_ht

    st.success("✅ Analyse Mi-Temps prête avec succès !")

    st.markdown(
        f"""
        <div class="card" style="text-align: center;">
            <h3>{home} vs {away} — <span style="color: #64DD17;">1ère Mi-Temps (HT)</span></h3>
            <h1 style="color: #00C853; font-size: 3.5rem;">{best_h_ht} - {best_a_ht}</h1>
            <p style="color: #8b949e;">Score Exact Prédit à la Pause (HT)</p>
            <hr style="border-color: #30363d;">
            <div style="text-align: left;">
                <p><b>Victoire Dom (1) HT :</b> {p_h_win_ht:.0f}%</p>
                <div style="background-color: #30363d; border-radius: 10px; height: 8px;"><div style="background-color: #00C853; width: {p_h_win_ht}%; height: 8px; border-radius: 10px;"></div></div>
                <p style="margin-top: 8px;"><b>Match Nul (X) HT :</b> {p_draw_ht:.0f}%</p>
                <div style="background-color: #30363d; border-radius: 10px; height: 8px;"><div style="background-color: #f1e05a; width: {p_draw_ht}%; height: 8px; border-radius: 10px;"></div></div>
                <p style="margin-top: 8px;"><b>Victoire Ext (2) HT :</b> {p_a_win_ht:.0f}%</p>
                <div style="background-color: #30363d; border-radius: 10px; height: 8px;"><div style="background-color: #ff5252; width: {p_a_win_ht}%; height: 8px; border-radius: 10px;"></div></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
  else:
    st.info("Renseigne les stats de 1ère mi-temps et lance l'analyse.")

with tab3:
  st.subheader("💎 Conseils Pro & Marchés Spécifiques Mi-Temps")
  if "analyzed_ht" in st.session_state and st.session_state["analyzed_ht"]:
    sh = st.session_state["sh_ht"]
    sa = st.session_state["sa_ht"]
    ov05 = st.session_state["p_ov05"]
    un15 = st.session_state["p_un15"]
    conf = st.session_state["conf_ht"]

    col_x, col_y = st.columns(2)
    with col_x:
      st.markdown(
          f"""
            <div class="card">
                <p style="color: #00C853; font-weight: bold;">⚡ Over 0.5 Buts (HT)</p>
                <h3>{'🟢 OUI' if ov05 > 50 else '🔴 NON'}</h3>
                <p>Probabilité : <b>{ov05:.1f}%</b></p>
            </div>
            """,
          unsafe_allow_html=True,
      )
    with col_y:
      st.markdown(
          f"""
            <div class="card">
                <p style="color: #00C853; font-weight: bold;">🛡️ Under 1.5 Buts (HT)</p>
                <h3>{'🟢 TRÈS SÛR' if un15 > 65 else '⚡ STANDARD'}</h3>
                <p>Probabilité : <b>{un15:.1f}%</b></p>
            </div>
            """,
          unsafe_allow_html=True,
      )

    st.markdown(
        f"""
        <div class="card">
            <h4>🎯 Synthèse & Options Recommandées (Mi-Temps)</h4>
            <p><b>Indice de Confiance HT :</b> <span style="color: #3fb950; font-weight: bold;">{conf}%</span></p>
            <p><b>Score exact mi-temps conseillé :</b> {sh} - {sa}</p>
            <hr style="border-color: #30363d;">
            <p style="color: #58a6ff;"><b>Options validées :</b> Match Nul à la mi-temps / Moins de 1.5 buts en 1ère mi-temps / 1-0 ou 0-0 à la pause.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
  else:
    st.warning("⚠️ Veuillez d'abord lancer l'analyse dans l'onglet 'Analyse HT'.")
