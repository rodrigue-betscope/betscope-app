import math
import streamlit as st

# Configuration de la page
st.set_page_config(
    page_title="NASMO IA BOT - V17 ULTRA-STRICT", page_icon="🛡️", layout="centered"
)

# Style CSS sombre et moderne
st.markdown(
    """
    <style>
    .main { background-color: #0e1117; color: white; }
    .card { background-color: #161b22; padding: 20px; border-radius: 15px; border: 1px solid #30363d; margin-bottom: 15px; }
    .stButton>button {
        background: linear-gradient(135deg, #FF3D00 0%, #DD2C00 100%);
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

st.title("🛡️ NASMO IA BOT - V17 ULTRA-STRICT")
st.markdown(
    "<p style='color: #8b949e;'>Filtre Anti-Piège & Sécurité Maximale 1ère"
    " Mi-Temps (HT) 🔥</p>",
    unsafe_allow_html=True,
)


def poisson(lmbda, k):
  return (math.exp(-max(0.01, lmbda)) * (max(0.01, lmbda) ** k)) / math.factorial(
      k
  )


# Organisation par Onglets
tab1, tab2, tab3 = st.tabs(
    ["⚙️ Stats & Clean Sheets HT", "📊 Analyse de Sécurité", "💎 Verdict Anti-Piège"]
)

with tab1:
  st.subheader("🏠 Équipe Domicile (1ère Période)")
  home = st.text_input("Nom domicile :", "Newcastle Olympic")
  c1, c2 = st.columns(2)
  with c1:
    h_ht_gf = st.number_input(
        "Buts marqués HT (Dom) :", min_value=0.0, value=0.4, step=0.1
    )
    h_clean = st.number_input(
        "Clean Sheets HT (Dom / 5 matchs) :", min_value=0.0, value=3.0, step=1.0
    )
  with c2:
    h_ht_ga = st.number_input(
        "Buts encaissés HT (Dom) :", min_value=0.0, value=0.4, step=0.1
    )
    h_mp = st.number_input(
        "Matchs joués (Dom) :", min_value=1.0, value=5.0, step=1.0
    )

  st.markdown("---")
  st.subheader("🚀 Équipe Extérieure (1ère Période)")
  away = st.text_input("Nom extérieur :", "Valentine Phoenix")
  c3, c4 = st.columns(2)
  with c3:
    a_ht_gf = st.number_input(
        "Buts marqués HT (Ext) :", min_value=0.0, value=0.5, step=0.1
    )
    a_clean = st.number_input(
        "Clean Sheets HT (Ext / 5 matchs) :", min_value=0.0, value=2.0, step=1.0
    )
  with c4:
    a_ht_ga = st.number_input(
        "Buts encaissés HT (Ext) :", min_value=0.0, value=0.6, step=0.1
    )
    a_mp = st.number_input(
        "Matchs joués (Ext) :", min_value=1.0, value=5.0, step=1.0
    )

  st.markdown("---")
  ht_league_avg = st.number_input(
      "⚽ Moyenne buts championnat (HT) :",
      min_value=0.1,
      value=1.15,
      step=0.05,
  )

with tab2:
  st.subheader("Lancer l'audit de sécurité")
  if st.button("🔒 Exécuter le filtre anti-piège V17"):
    with st.spinner("Vérification des indices de hermétisme..."):
      # Calculs de base
      h_att = h_ht_gf / h_mp
      h_def = h_ht_ga / h_mp
      a_att = a_ht_gf / a_mp
      a_def = a_ht_ga / a_mp

      # Application du bonus de clean sheet (réduction du risque de but)
      clean_factor_h = max(0.6, 1.0 - (h_clean / h_mp) * 0.3)
      clean_factor_a = max(0.6, 1.0 - (a_clean / a_mp) * 0.3)

      lambda_h = (h_att * a_def * clean_factor_h) / ht_league_avg
      lambda_a = (a_att * h_def * clean_factor_a) / ht_league_avg

      max_g = 4
      best_h, best_away = 0, 0
      max_p = -1.0

      p_draw_ht = 0.0
      p_under15_ht = 0.0
      p_00_ht = 0.0

      for h in range(max_g):
        for a in range(max_g):
          p = poisson(lambda_h, h) * poisson(lambda_a, a)
          if p > max_p:
            max_p = p
            best_h, best_away = h, a

          if h == a:
            p_draw_ht += p
          if h + a <= 1:
            p_under15_ht += p
          if h == 0 and a == 0:
            p_00_ht += p

      p_draw_ht = p_draw_ht * 100
      p_under15_ht = p_under15_ht * 100
      p_00_ht = p_00_ht * 100

      # Indice de sécurité strict
      total_expected_ht_goals = lambda_h + lambda_a
      is_safe_match = (
          total_expected_ht_goals < 0.95 and (h_clean + a_clean >= 4)
      )

      confidence = min(
          98, int(p_under15_ht * 0.6 + ((h_clean + a_clean) / 10) * 40)
      )

      st.session_state["v17_done"] = True
      st.session_state["sh"] = best_h
      st.session_state["sa"] = best_away
      st.session_state["p_draw"] = p_draw_ht
      st.session_state["p_under"] = p_under15_ht
      st.session_state["p_00"] = p_00_ht
      st.session_state["safe"] = is_safe_match
      st.session_state["conf"] = confidence
      st.session_state["goals"] = total_expected_ht_goals

    st.success("✅ Audit de sécurité terminé !")

    st.markdown(
        f"""
        <div class="card" style="text-align: center;">
            <h3>{home} vs {away}</h3>
            <h1 style="color: {'#00C853' if best_h + best_away == 0 else '#FF3D00'}; font-size: 3.5rem;">{best_h} - {best_away}</h1>
            <p style="color: #8b949e;">Prédiction Score Strict (HT)</p>
            <hr style="border-color: #30363d;">
            <div style="text-align: left;">
                <p><b>Probabilité Match Nul HT :</b> {p_draw_ht:.1f}%</p>
                <div style="background-color: #30363d; border-radius: 10px; height: 8px;"><div style="background-color: #00C853; width: {p_draw_ht}%; height: 8px; border-radius: 10px;"></div></div>
                <p style="margin-top: 8px;"><b>Probabilité Under 1.5 HT :</b> {p_under15_ht:.1f}%</p>
                <div style="background-color: #30363d; border-radius: 10px; height: 8px;"><div style="background-color: #2196F3; width: {p_under15_ht}%; height: 8px; border-radius: 10px;"></div></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
  else:
    st.info(
        "Renseigne les statistiques et les clean sheets pour lancer l'audit."
    )

with tab3:
  st.subheader("💎 Verdict de Sécurité & Validation")
  if "v17_done" in st.session_state and st.session_state["v17_done"]:
    safe = st.session_state["safe"]
    conf = st.session_state["conf"]
    p_00 = st.session_state["p_00"]
    p_un = st.session_state["p_under"]
    sh = st.session_state["sh"]
    sa = st.session_state["sa"]
    goals = st.session_state["goals"]

    if safe:
      st.markdown(
          """
            <div class="card" style="border: 2px solid #00C853;">
                <h3 style="color: #00C853;">🟢 VALIDÉ : Profil Défensif Détecté</h3>
                <p>Les critères de clean sheets et de faible moyenne de buts sont réunis. Le match présente un bon profil de verrouillage.</p>
            </div>
            """,
          unsafe_allow_html=True,
      )
    else:
      st.markdown(
          """
            <div class="card" style="border: 2px solid #FF3D00;">
                <h3 style="color: #FF3D00;">🔴 ALERTE : Match Trop Ouvert (À ÉVITER)</h3>
                <p>L'algorithme détecte trop de risques de buts en première période. Aucun pari sécurisé conseillé sur ce match.</p>
            </div>
            """,
          unsafe_allow_html=True,
      )

    st.markdown(
        f"""
        <div class="card">
            <h4>📋 Indicateurs Clés V17</h4>
            <p><b>Indice de Sécurité Global :</b> <span style="color: #3fb950; font-weight: bold;">{conf}%</span></p>
            <p><b>Risque de 0-0 à la pause :</b> {p_00:.1f}%</p>
            <p><b>Sécurité Under 1.5 HT :</b> {p_un:.1f}%</p>
            <p><b>Buts attendus (HT) :</b> {goals:.2f}</p>
            <p><b>Score conseillé :</b> {sh} - {sa}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
  else:
    st.warning("Veuillez d'abord exécuter l'audit dans l'onglet 'Analyse'.")
