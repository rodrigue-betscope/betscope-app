import google.generativeai as genai
from PIL import Image
import streamlit as st

# 1. Configuration de la clé Gemini depuis les secrets Streamlit
genai.configure(api_key=st.secrets["api"]["gemini_key"])

st.title("⚽ BetScope - Analyseur de Jeux Virtuels FIFA")
st.write(
    "Télécharge une capture d'écran de tes matchs virtuels FIFA (Championnat"
    " d'Angleterre 4x4, cotes 1X2...) pour lancer l'analyse prédictive."
)

# 2. Zone de téléchargement de l'image
uploaded_file = st.file_uploader(
    "Upload Instant Virtual Match screenshot", type=["png", "jpg", "jpeg"]
)

if uploaded_file is not None:
  image = Image.open(uploaded_file)
  st.image(image, caption="Capture d'écran chargée", use_column_width=True)

  if st.button("Lancer l'analyse du match virtuel"):
    with st.spinner(
        "L'intelligence artificielle analyse les cotes et les tendances FIFA..."
    ):
      try:
        # Utilisation du modèle requis gemini-3.8-flash
        model = genai.GenerativeModel("gemini-3.8-flash")

        prompt = (
            "Analyse cette capture d'écran de jeux virtuels de football FIFA"
            " (championnat 4x4, affiches, cotes 1X2). Identifie les équipes en"
            " présence, analyse les cotes affichées, et fournis un pronostic"
            " précis et stratégique adapté aux spécificités des matchs"
            " virtuels (probabilités de buts, issues 1X2)."
        )

        # Envoi de l'image et du prompt à l'IA
        response = model.generate_content([prompt, image])

        st.success("Analyse du match virtuel terminée avec succès !")
        st.write(response.text)

      except Exception as e:
        st.error(f"Une erreur est survenue lors de l'analyse : {e}")
