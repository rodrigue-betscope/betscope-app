import base64
from io import BytesIO
from PIL import Image
import requests
import streamlit as st

st.title("⚽ BetScope - Analyseur de Jeux Virtuels FIFA")
st.write(
    "Télécharge une capture d'écran de tes matchs virtuels FIFA (Championnat"
    " d'Angleterre 4x4, cotes 1X2...) pour lancer l'analyse prédictive."
)

# Récupération sécurisée de la clé API
try:
  api_key = st.secrets["api"]["gemini_key"]
except Exception:
  st.error(
      "Clé API introuvable dans les secrets Streamlit (`st.secrets['api']['gemini_key']`)."
  )
  api_key = None

uploaded_file = st.file_uploader(
    "Upload Instant Virtual Match screenshot", type=["png", "jpg", "jpeg"]
)

if uploaded_file is not None and api_key:
  image = Image.open(uploaded_file)
  st.image(image, caption="Capture d'écran chargée", use_column_width=True)

  if st.button("Lancer l'analyse du match virtuel"):
    with st.spinner(
        "L'intelligence artificielle analyse les cotes et les tendances FIFA..."
    ):
      try:
        # Redimensionnement et conversion de l'image en base64 pour l'API HTTP
        image.thumbnail((800, 800))
        buffered = BytesIO()
        image.save(buffered, format="JPEG")
        img_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")

        # URL de l'API Gemini v1beta avec le modèle flash
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"

        headers = {"Content-Type": "application/json"}

        prompt_text = (
            "Analyse cette capture d'écran de jeux virtuels de football FIFA"
            " (championnat 4x4, affiches, cotes 1X2). Identifie les équipes en"
            " présence, analyse les cotes affichées, et fournis un pronostic"
            " précis et stratégique adapté aux spécificités des matchs"
            " virtuels (probabilités de buts, issues 1X2)."
        )

        payload = {
            "contents": [{
                "parts": [
                    {"text": prompt_text},
                    {
                        "inline_data": {
                            "mime_type": "image/jpeg",
                            "data": img_base64,
                        }
                    },
                ]
            }]
        }

        # Appel HTTP avec un timeout de 30 secondes pour éviter le blocage infini
        response = requests.post(url, json=payload, headers=headers, timeout=30)

        if response.status_code == 200:
          data = response.json()
          # Extraction du texte de la réponse de l'API
          ai_response = (
              data.get("candidates", [{}])[0]
              .get("content", {})
              .get("parts", [{}])[0]
              .get("text", "Aucune réponse générée.")
          )
          st.success("Analyse du match virtuel terminée avec succès !")
          st.write(ai_response)
        else:
          st.error(
              f"Erreur API ({response.status_code}) : {response.text}"
          )

      except requests.exceptions.Timeout:
        st.error(
            "L'appel à l'API a pris trop de temps (timeout). Vérifie ta"
            " connexion ou réessaie."
        )
      except Exception as e:
        st.error(f"Une erreur est survenue lors de l'analyse : {e}")
