import streamlit as st

# Configuration de la page Streamlit
st.set_page_config(
    page_title="BetScope Pro - Matchs 0-0 du Jour", page_icon="⚽", layout="centered"
)

date_du_jour = "Mercredi 26 Août 2026"

st.title("🎯 BetScope Pro : Saisie des Matchs 0-0")
st.write(f"📅 **Date officielle :** {date_du_jour}")
st.write(
    "Entrez ci-dessous les vrais matchs repérés sur votre bookmaker pour"
    " aujourd'hui :"
)
st.markdown("---")

# Création de champs interactifs où vous pouvez taper ce que vous voulez
match_1_saisi = st.text_input(
    "📝 Nom du Match 1 (ex: Équipe A vs Équipe B)",
    "Entrez le match 1 d'aujourd'hui",
)
cote_1 = st.text_input("📊 Cote 0-0 estimée pour le Match 1", "7.20")

st.markdown("---")

match_2_saisi = st.text_input(
    "📝 Nom du Match 2 (ex: Équipe C vs Équipe D)",
    "Entrez le match 2 d'aujourd'hui",
)
cote_2 = st.text_input("📊 Cote 0-0 estimée pour le Match 2", "6.90")

st.markdown("---")

# Affichage dynamique de votre sélection validée
st.subheader("🔥 Votre Sélection Validée du Jour")

st.success(f"### Match 1 : {match_1_saisi}")
st.write(f"**Cote 0-0 :** {cote_1}")

st.success(f"### Match 2 : {match_2_saisi}")
st.write(f"**Cote 0-0 :** {cote_2}")

st.info(
    "💡 Dès que vous tapez les noms dans les cases ci-dessus, ils s'affichent"
    " instantanément en bas !"
)
