import numpy as np
import streamlit as st
from scipy.stats import poisson


def calculer_poisson_securise(
    lam_home, lam_away, max_buts=5
):  #
  """Calcule la matrice des scores exacts avec la loi de Poisson de manière sécurisée."""
  matrice = np.zeros((max_buts + 1, max_buts + 1))
  for i in range(max_buts + 1):
    for j in range(max_buts + 1):
      prob_home = poisson.pmf(i, lam_home)
      prob_away = poisson.pmf(j, lam_away)
      matrice[i, j] = prob_home * prob_away
  return matrice


def lancer_analyse_match(match_data):
  st.subheader(
      f"🎯 {match_data.get('home_team', 'Domicile')} vs"
      f" {match_data.get('away_team', 'Extérieur')}"
  )

  # Récupération des données API
  qualite_donnees = match_data.get(
      "completeness", 0.0
  )  # Ex: 0.001 (0.1%) ou 0.2 (20%)
  home_goals = match_data.get("home_goals_avg")
  away_goals = match_data.get("away_goals_avg")

  st.write(
      f"**Qualité des données disponibles :** {qualite_donnees * 100:.1f}%"
  )

  # -------------------------------------------------------------
  # SÉCURITÉ ANTI-DONNÉES VIDES OU CORROMPUES
  # -------------------------------------------------------------
  # Si la qualité est quasi nulle ou que les buts sont manquants/N/D
  if (
      qualite_donnees < 0.02
      or home_goals is None
      or away_goals is None
      or home_goals == "N/D"
      or away_goals == "N/D"
  ):
    st.warning(
        "⚠️ **Données API insuffisantes ou non disponibles pour ce match"
        " (Ligues mineures / Réserves).**"
    )
    st.info(
        "💡 *Activation du mode de secours :* Application d'une moyenne"
        " statistique standard du championnat pour stabiliser les"
        " prévisions."
    )

    # Valeurs de repli (Moyennes standard observées dans ce type de championnat)
    lam_home = 1.35
    lam_away = 1.15
    fiabilite_modele = (
        "Faible (Basé sur les moyennes standards de la ligue)"  #
    )
  else:
    # Utilisation des vraies données de l'API si elles sont valides
    lam_home = float(home_goals)
    lam_away = float(away_goals)
    fiabilite_modele = "Normale (Basé sur l'historique API)"  #

  st.write(f"**Confiance du modèle :** {fiabilite_modele}")

  # -------------------------------------------------------------
  # CALCUL DE POISSON PROPRE
  # -------------------------------------------------------------
  matrice_prob = calculer_poisson_securise(lam_home, lam_away)

  # Calcul des issues 1N2 basées sur la matrice
  prob_victoire_home = np.sum(np.tril(matrice_prob, -1))  # Home > Away
  prob_nul = np.sum(np.diag(matrice_prob))  # Home == Away
  prob_visiteur = np.sum(np.triu(matrice_prob, 1))  # Home < Away

  # Normalisation en pourcentages réels
  total = prob_victoire_home + prob_nul + prob_visiteur
  if total > 0:
    p1 = (prob_victoire_home / total) * 100
    pn = (prob_nul / total) * 100
    p2 = (prob_visiteur / total) * 100
  else:
    p1, pn, p2 = 33.3, 33.3, 33.3

  # Affichage propre des probabilités 1N2
  col1, col2, col3 = st.columns(3)
  col1.metric("1 (Domicile)", f"{p1:.1f}%")
  col2.metric("Nul (X)", f"{pn:.1f}%")
  col3.metric("2 (Extérieur)", f"{p2:.1f}%")

  # Extraction des scores exacts les plus probables
  scores_probables = []
  for i in range(matrice_prob.shape[0]):
    for j in range(matrice_prob.shape[1]):
      scores_probables.append(
          (f"{i}-{j}", (matrice_prob[i, j] / total) * 100)
      )

  # Trier du plus probable au moins probable
  scores_probables.sort(key=lambda x: x[1], reverse=True)

  st.markdown("### ⚽ Scores exacts les plus probables")
  for score, prob in scores_probables[:5]:  # Afficher le Top 5
    st.text(f"Score : {score}  —  Probabilité : {prob:.1f}%")


# Simulation d'appel avec les données de ton image (cas vide / N/D)
match_exemple_vide = {
    "home_team": "Heroes de Zaci 2",
    "away_team": "Irapuato II",
    "completeness": 0.001,  # 0.1% comme sur ton screen
    "home_goals_avg": "N/D",
    "away_goals_avg": "N/D",
}

# Pour tester dans ton application :
# lancer_analyse_match(match_exemple_vide)
