import streamlit as st
from prediction_engine import run_prediction_engine
from football_api import fetch_match_data

st.set_page_config(page_title="Rodrigue Pro Puissant Prédiction", page_icon="⚽", layout="centered")

st.title("⚽ Rodrigue Pro Puissant Prédiction")
st.write("Colle le lien du match ci-dessous pour lancer l'analyse instantanée.")

url_input = st.text_input("Lien du match :", placeholder="Colle le lien du match ici...")

if st.button("Lancer l'analyse 🚀", type="primary"):
    if url_input:
        with st.spinner("Analyse du match et calcul des probabilités en cours..."):
            try:
                match_data = fetch_match_data(url_input)
                analysis = run_prediction_engine(match_data)
                
                st.markdown("---")
                st.markdown(f"🏆 **{analysis['tournament']}** | ✅ **{analysis['status']}**")
                st.markdown(f"⚽ **{analysis['home_team']}** `{analysis['score_ft']}` **{analysis['away_team']}**")
                st.markdown(f"🎯 **Pronostic :** {analysis['pronostic']}")
                st.markdown(f"📊 **Probabilité :** {analysis['probability']}% · **confiance** {analysis['confidence']}")
                st.markdown(f"⏱️ **Score Prévu (MT / FT) :** `{analysis['mt_ft']}`")
                st.markdown(f"🔍 *{analysis['exact_score_status']}*")
            except Exception as e:
                st.error(f"Erreur lors de l'analyse : {str(e)}")
    else:
        st.warning("Veuillez d'abord coller un lien valide.")
        
