import math
import streamlit as st


def analyse_match():
  st.title("===== IA PREDICTION BOT V1.0 💯 =====")

  # 1. DONNEES ENTREES
  st.subheader("1. Paramètres des Équipes")
  home = st.text_input("Nom équipe Domicile", "Équipe Domicile")
  away = st.text_input("Nom équipe Extérieur", "Équipe Extérieur")

  col1, col2 = st.columns(2)
  with col1:
    home_gf = st.number_input(
        f"Total Buts marqués à la maison ({home})", min_value=0.0, value=10.0
    )
    home_ga = st.number_input(
        f"Total Buts encaissés à la maison ({home})", min_value=0.0, value=5.0
    )
    home_mp = st.number_input(
        f"Matchs joués à domicile ({home})", min_value=1.0, value=5.0
    )

  with col2:
    away_gf = st.number_input(
        f"Total Buts marqués dehors ({away})", min_value=0.0, value=8.0
    )
    away_ga = st.number_input(
        f"Total Buts encaissés dehors ({away})", min_value=0.0, value=7.0
    )
    away_mp = st.number_input(
        f"Matchs joués à l'extérieur ({away})", min_value=1.0, value=5.0
    )

  league_avg = st.number_input(
      "Constante de buts par match du championnat", min_value=0.1, value=2.5
  )

  # Côtes bookmakers
  st.subheader("2. Côtes Bookmakers")
  c1, c2, c3 = st.columns(3)
  with c1:
    cote_1 = st.number_input("Côte 1 (Domicile)", value=2.0)
    cote_over25 = st.number_input("Côte Over 2.5", value=1.85)
    cote_over15 = st.number_input("Côte Over 1.5", value=1.30)
  with c2:
    cote_X = st.number_input("Côte X (Nul)", value=3.20)
    cote_under25 = st.number_input("Côte Under 2.5", value=1.95)
    cote_under15 = st.number_input("Côte Under 1.5", value=3.00)
  with c3:
    cote_2 = st.number_input("Côte 2 (Extérieur)", value=3.50)
    cote_btts_oui = st.number_input("Côte BTTS Oui", value=1.90)
    cote_btts_non = st.number_input("Côte BTTS Non", value=1.80)

  # Bouton pour lancer le calcul
  if st.button("Lancer l'analyse du match"):
    # 2. CALCULS VRAIS
    home_attaque = home_gf / home_mp
    home_defense = home_ga / home_mp
    away_attaque = away_gf / away_mp
    away_defense = away_ga / away_mp

    buts_prevus_home = (home_attaque * away_defense) / league_avg
    buts_prevus_away = (away_attaque * home_defense) / league_avg
    total_buts_prevu = buts_prevus_home + buts_prevus_away

    # Probabilités 1X2 avec poisson
    prob_home = (
        buts_prevus_home / (buts_prevus_home + buts_prevus_away + 0.2)
    ) * 100
    prob_away = (
        buts_prevus_away / (buts_prevus_home + buts_prevus_away + 0.2)
    ) * 100
    prob_draw = 100 - prob_home - prob_away

    # BTTS
    prob_btts_oui = (
        (1 - math.exp(-buts_prevus_home))
        * (1 - math.exp(-buts_prevus_away))
        * 100
    )
    prob_btts_non = 100 - prob_btts_oui

    # Over/Under
    prob_over25 = (
        1 - math.exp(-total_buts_prevu) * (1 + total_buts_prevu + total_buts_prevu**2 / 2)
    ) * 100
    prob_under25 = 100 - prob_over25
    prob_over15 = (1 - math.exp(-total_buts_prevu) * (1 + total_buts_prevu)) * 100
    prob_under15 = 100 - prob_over15

    # Score exact le plus probable
    score_home = round(buts_prevus_home)
    score_away = round(buts_prevus_away)
    if score_home == score_away:
      score_home += 1  # éviter 0-0 si attaque forte

    # Mi-temps: 40% des buts en 1ere
    mt_home = round(score_home * 0.5)
    mt_away = round(score_away * 0.5)

    # 3. RESULTAT FORMATÉ
    st.markdown("---")
    st.header("===== RESULTAT ANALYSE IA =====")

    st.markdown("📊 **COTES BOOKMAKERS**")
    st.write(f"1(Dom): {cote_1} | X(Nul): {cote_X} | 2(Ext): {cote_2}")
    st.write(f"Over 2.5: {cote_over25} | Under 2.5: {cote_under25}")
    st.write(f"BTTS Oui: {cote_btts_oui} | BTTS Non: {cote_btts_non}")

    st.markdown("🔥 **PROBABILITES 1X2**")
    st.write(
        f"{home}: {prob_home:.0f}% | Nul: {prob_draw:.0f}% | {away}:"
        f" {prob_away:.0f}%"
    )

    st.markdown("🎯 **PREDICTION IA**")
    st.write(f"Score Exact: {score_home}-{score_away},00")
    st.write(f"Mi-temps: {mt_home}-{mt_away},00")
    st.write(
        f"Over/Under 2.5: {'Over' if prob_over25 > 55 else 'Under'}"
        f" {prob_over25:.0f}%"
    )
    st.write(
        f"BTTS: {'Oui' if prob_btts_oui > 55 else 'Non'} {prob_btts_oui:.0f}%"
    )

    # Meilleur pari
    if prob_home > 60:
      meilleur = f"Victoire {home}"
    elif prob_away > 60:
      meilleur = f"Victoire {away}"
    else:
      meilleur = "Nul ou Double Chance"

    st.success(f"💎 **PARI LE PLUS SAFE: {meilleur}**")
    st.write(f"Fiabilité: {max(prob_home, prob_away, prob_draw):.0f}%")

    st.markdown("📈 **STATS CALCULÉES**")
    st.write(
        f"{home} Attaque: {home_attaque:.2f} buts/m | Défense: {home_defense:.2f}"
    )
    st.write(
        f"{away} Attaque: {away_attaque:.2f} buts/m | Défense: {away_defense:.2f}"
    )
    st.write(f"Total buts prévu: {total_buts_prevu:.2f}")


analyse_match()
