import streamlit as st
from PIL import Image
import google.generativeai as genai

# 1. Configuration de la clé Gemini depuis les secrets Streamlit
genai.configure(api_key=st.secrets["api"]["gemini_key"])

st.title("⚽ BetScope - Analyseur de Match par IA")
st.write("Télécharge une capture d'écran de ton match (liste des équipes, cotes...) pour lancer l'analyse prédictive.")

# 2. Zone de téléchargement de l'image (exactement comme sur l'application de référence)
uploaded_file = st.file_uploader("Upload Instant Football screenshot", type=["png", "jpg", "jpeg"])

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption="Capture d'écran chargée", use_column_width=True)
    
    if st.button("Lancer l'analyse du match"):
        with st.spinner("L'intelligence artificielle analyse le match et les probabilités..."):
            try:
                # Utilisation d'un modèle multimodal stable
                model = genai.GenerativeModel('gemini-1.5-flash')
                
                prompt = (
                    "Analyse cette capture d'écran de match de football. "
                    "Identifie les équipes en présence, analyse les informations ou cotes visibles, "
                    "et fournis un pronostic détaillé avec les probabilités de buts et une analyse stratégique."
                )
                
                # Envoi de l'image et du prompt à l'IA
                response = model.generate_content([prompt, image])
                
                st.success("Analyse terminée avec succès !")
                st.write(response.text)
                
            except Exception as e:
                st.error(f une erreur est survenue lors de l'analyse : {e}")
