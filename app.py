from datetime import datetime
import streamlit as st

# Configuration de la page Streamlit
st.set_page_config(
    page_title="BetScope Pro - Matchs 0-0 du Jour", page_icon="⚽", layout="centered"
)

# Date exacte d'aujourd'hui : Mercredi 26 Août 2026
date_du_jour = "Mercredi 26 Août 2026"

st.title("🎯 BetScope Pro : Analyse 0-0")
st.write(f"📅 **Date officielle :** {date_du_jour}")
st.markdown("---")

st.subheader("🔥 Vos 2 Vrais Matchs du Jour (Sélection Réelle)")
st.write(
    "Entrez ou vérifiez vos affiches réelles du jour repérées sur le bookmaker"
    " pour l'analyse :"
)

# Formulaire ou affichage direct des deux vrais matchs du jour
# Vous pouvez modifier ces champs directement dans votre code avec les vrais matchs trouvés sur 1Xbet aujourd'hui
match_1 = {
    "equipes": "[Entrez le Vrai Match 1 d'aujourd'hui sur 1Xbet]",
    "championnat": "Ligue / Championnat du 26/08/2026",
    "cote_00": "À vérifier sur 1Xbet",
    "fiabilite": "Analyse Poisson active",
}

match_2 = {
    "equipes": "[Entrez le Vrai Match 2 d'aujourd'hui sur 1Xbet]",
    "championnat": "Ligue / Championnat du 26/08/2026",
    "cote_00": "À vérifier sur 1Xbet",
    "fiabilite": "Analyse Poisson active",
}

# Affichage propre du Match 1
st.success(f"### Match 1 : {match_1['equipes']}")
st.write(f"**Compétition :** {match_1['championnat']}")
st.write(f"**Cote 0-0 estimée :** {match_1['cote_00']}")
st.markdown("---")

# Affichage propre du Match 2
st.success(f"### Match 2 : {match_2['equipes']}")
st.write(f"**Compétition :** {match_2['championnat']}")
st.write(f"**Cote 0-0 estimée :** {match_2['cote_00']}")
st.markdown("---")

st.warning(
    "⚠️ **Conseil de sécurité :** Vérifiez toujours les compositions d'équipes"
    " et les côtes en direct sur 1Xbet avant de valider votre pari pour ce 26"
    " août 2026."
)
