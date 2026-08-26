import streamlit as st

st.set_page_config(
    page_title="BetScope Pro - Analyseur Réel", page_icon="⚽", layout="centered"
)

st.title("🎯 BetScope Pro : Analyseur 0-0 Rigoureux")
st.write(
    "Entrez la vraie affiche et la vraie cote 0-0 vue sur 1Xbet pour un"
    " véritable calcul."
)
st.markdown("---")

# Saisie réelle basée sur ce que vous voyez sur le bookmaker
match_saisi = st.text_input(
    "📝 Nom du Match (ex: Nagoya Grampus vs Gainare Tottori)",
    "Nagoya Grampus vs Gainare Tottori",
)
cote_reelle = st.number_input(
    "📊 Cote exacte du 0-0 sur 1Xbet", min_value=1.0, max_value=50.0, value=18.0
)

if st.button("🔍 Analyser la vraie viabilité du 0-0"):
  # Calcul mathématique réel de la probabilité implicite basée sur la cote (1 / Cote * 100)
  probabilite_reelle = (1 / cote_reelle) * 100

  st.markdown("### 📋 Rapport d'analyse de l'algorithme")
  st.success(f"**Match :** {match_saisi}")
  st.write(f"**Cote analysée :** {cote_reelle}")
  st.write(f"**Probabilité mathématique réelle :** {probabilite_reelle:.2f}%")

  # Logique de décision stricte pour éviter de perdre de l'argent
  st.markdown("---")
  if cote_reelle >= 7.0 and cote_reelle <= 12.0:
    st.success(
        "✅ **Statut : Favorable.** La cote se situe dans la zone statistique"
        " idéale pour un score vierge serré."
    )
  elif cote_reelle > 12.0:
    st.warning(
        f"⚠️ **Attention (Cas de {match_saisi}) :** Une cote de {cote_reelle}"
        " signifie que le marché s'attend à de nombreux buts (écart de"
        " niveau important). Le risque de score fleuve est très élevé. **Ne"
        " pas risquer un 0-0 sur ce profil.**"
    )
  else:
    st.error(
        "❌ **Statut : Déconseillé.** Cote trop basse, risque de 1-1 ou de buts"
        " précoces."
    )
