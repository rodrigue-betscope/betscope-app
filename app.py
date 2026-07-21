import streamlit as st
from football_api import rechercher_equipe, derniers_matchs, blessures, h2h
from gemini_ai import analyse_ia
from voice import audio_ia

st.set_page_config(
    page_title="BetScope Pro",
    page_icon="👑"
)

st.title("👑 BetScope Pro")
st.write("Analyse Football IA Premium")

equipe1 = st.text_input("Equipe domicile")
equipe2 = st.text_input("Equipe extérieur")

if st.button("🚀 Lancer Analyse"):
    if not equipe1 or not equipe2:
        st.warning("Veuillez renseigner les deux équipes.")
    else:
        with st.spinner("Collecte des données..."):
            t1 = rechercher_equipe(equipe1)
            t2 = rechercher_equipe(equipe2)

            st.write("Données récupérées")

            donnees = {
                "Equipe 1": t1,
                "Equipe 2": t2
            }

            rapport = analyse_ia(donnees)

            st.subheader("📊 Rapport VIP")
            st.write(rapport)

            lecteur = audio_ia(rapport)

            st.components.v1.html(
                lecteur,
                height=80
            )
