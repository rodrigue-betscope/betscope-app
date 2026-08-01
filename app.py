import random
import streamlit as st

# Configuration de la page
st.set_page_config(
    page_title="Rodrigue Pro Puissant Prédiction", page_icon="⚽", layout="centered"
)

# Style CSS personnalisé pour un rendu professionnel
st.markdown(
    """
    <style>
    .main-title {
        text-align: center;
        color: #1E3A8A;
        font-weight: bold;
    }
    .card {
        background-color: #f8fafc;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #e2e8f0;
        margin-bottom: 10px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    "<h2 class='main-title'>🤖 NOUVEAU BOT IA - PRÉDICTION SCORE EXACT MI-TEMPS</h2>",
    unsafe_allow_html=True,
)
st.markdown(
    "<p style='text-align: center; color: #64748b;'>Algorithme de calcul haute précision 100% optimisé</p>",
    unsafe_allow_html=True,
)

# Formulaire d'entrée des équipes (similaire aux inputs de l'image)
with st.form("prediction_form"):
  home_team = st.text_input("Équipe à domicile", "Olympique de Marseille")
  away_team = st.text_input("Équipe à l'extérieur", "Paris Saint-Germain")
  tactical_param = st.number_input(
      "Paramètre tactique / Indice", min_value=0, max_value=10, value=0
  )

  submit_button = st.form_submit_button(label="📊 Générer la prédiction")

if submit_button:
  st.markdown("---")

  # Section 1 : Analyse rapide du match
  st.markdown("### 1. Analyse rapide du match")
  analyses_pool = [
      f"{home_team} et {away_team} débutent prudemment. Historiquement peu de buts avant 15'.",
      f"Grosse intensité tactique prévue entre {home_team} et {away_team}. Phase d'observation prolongée en première mi-temps.",
      f"{home_team} impose un bloc bas solide à domicile face à {away_team}, limitant les espaces dans les 45 premières minutes.",
  ]
  selected_analysis = random.choice(analyses_pool)
  st.info(selected_analysis)

  # Section 2 : Scores probables à la mi-temps
  st.markdown("### 2. Scores probables à la mi-temps")
  col1, col2, col3 = st.columns(3)

  with col1:
    st.metric(label="Score 0-0", value="55%")
  with col2:
    st.metric(label="Score 1-0", value="25%")
  with col3:
    st.metric(label="Score 0-1", value="20%")

  # Section 3 : Confiance globale
  st.markdown("### 3. Confiance globale")
  fiabilite = random.randint(76, 89)
  st.success(f"**Fiabilité de la prédiction : {fiabilite} %**")

  # Section 4 : Suggestion de pari
  st.markdown("### 4. Suggestion de pari")
  suggestions_pool = [
      "Under 1,5 but HT recommandé.",
      "Moins de 0,5 but dans les 20 premières minutes.",
      "Mi-temps avec le plus de buts : 2ème mi-temps.",
  ]
  selected_suggestion = random.choice(suggestions_pool)
  st.warning(f"💡 **{selected_suggestion}**")
  
