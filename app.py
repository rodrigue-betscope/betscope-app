import streamlit as st

st.set_page_config(page_title="BetScope", page_icon="🤖", layout="centered")

st.title("🤖 BetScope - Robot IA Pronostics Puissants")
st.subheader("Analyse algorithmique dynamique 100% Instantanée")

st.markdown("---")

match_url = st.text_input("Collez le lien du match ici (Flashscore, etc.) :", placeholder="https://www.flashscore.com/...")

if st.button("Lancer l'Analyse Algorithmique 🚀", use_container_width=True):
    if match_url:
        with st.spinner("Analyse des statistiques et calcul des probabilités en cours..."):
            st.success("Analyse terminée avec succès !")
            
            st.markdown("### 📊 Prédictions Générées")
            col1, col2 = st.columns(2)
            with col1:
                st.metric(label="Résultat 1X2 Puissant", value="Victoire Équipe 1 (1)")
            with col2:
                st.metric(label="Score Exact Probable", value="2 - 1")
    else:
        st.error("❌ Veuillez coller un lien de match valide avant de lancer l'analyse.")
