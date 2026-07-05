import streamlit as st

# 1. LA FONCTION DE CALCUL DU ROBOT
def analyser_match_vip(cotes_double_chance, cotes_score_exact, cotes_mt_fin):
    analyses_valides = {}
    
    # Analyse Mi-temps / Fin de match
    confiance_mt_fin = 0
    meilleur_choix_mt = ""
    if cotes_mt_fin['V1/V1'] < 2.80:
        confiance_mt_fin = (1 / cotes_mt_fin['V1/V1']) * 200
        meilleur_choix_mt = "1/1 (Domination Domicile HT/FT)"
    elif cotes_mt_fin['V2/V2'] < 2.80:
        confiance_mt_fin = (1 / cotes_mt_fin['V2/V2']) * 200
        meilleur_choix_mt = "2/2 (Domination Extérieur HT/FT)"
    else:
        confiance_mt_fin = (1 / cotes_mt_fin['X/X']) * 150
        meilleur_choix_mt = "X/X (Match Serré - Nul à la mi-temps)"

    if confiance_mt_fin >= 80:
        analyses_valides['Mi-temps / Fin'] = {"Pronto": meilleur_choix_mt, "Confiance": round(min(confiance_mt_fin, 98), 2)}

    # Analyse Score Exact
    score_le_plus_bas = min(cotes_score_exact, key=cotes_score_exact.get)
    cote_score = cotes_score_exact[score_le_plus_bas]
    confiance_score = 100 - (cote_score * 4)
    if confiance_score >= 75:
        analyses_valides['Score Exact'] = {"Pronto": score_le_plus_bas, "Confiance": round(confiance_score, 2)}

    # Analyse Double Chance
    for option, cote in cotes_double_chance.items():
        probabilite = (1 / cote) * 100
        if probabilite >= 82:
            analyses_valides[f'Double Chance {option}'] = {"Pronto": "Gagnant Sûr", "Confiance": round(probabilite, 2)}

    return analyses_valides

# 2. INTERFACE GRAPHIQUE STREAMLIT
st.set_page_config(page_title="BetScope Pro VIP", page_icon="🤖", layout="centered")

st.title("🤖 Rodrigue Pro Puissant Prédiction")
st.write("Entrez les cotes pour générer les 5 pronostics VIP ultra-fiables du jour.")

st.markdown("---")

# Formulaire pour entrer les cotes du match
st.header("📊 Formulaire d'analyse de match")

# Inputs Double Chance (Réf: Image 74844.jpg)
st.subheader("1. Marché Double Chance")
col1, col2, col3 = st.columns(3)
with col1:
    dc_1X = st.number_input("Cote 1X", min_value=1.01, value=1.22, step=0.01)
with col2:
    dc_12 = st.number_input("Cote 12", min_value=1.01, value=1.31, step=0.01)
with col3:
    dc_2X = st.number_input("Cote 2X", min_value=1.01, value=2.06, step=0.01)

# Inputs MT-Fin (Réf: Image 74850.jpg)
st.subheader("2. Marché Mi-temps / Fin de match (HT/FT)")
col4, col5, col6 = st.columns(3)
with col4:
    mf_v1v1 = st.number_input("Cote V1/V1", min_value=1.01, value=2.65, step=0.01)
with col5:
    mf_xx = st.number_input("Cote X/X", min_value=1.01, value=5.50, step=0.01)
with col6:
    mf_v2v2 = st.number_input("Cote V2/V2", min_value=1.01, value=7.90, step=0.01)

# Inputs Score Exact (Réf: Image 74852.jpg)
st.subheader("3. Cotes des Scores Exacts les plus probables")
col7, col8, col9 = st.columns(3)
with col7:
    se_10 = st.number_input("Cote 1-0", min_value=1.01, value=8.0, step=0.1)
with col8:
    se_11 = st.number_input("Cote 1-1", min_value=1.01, value=7.0, step=0.1)
with col9:
    se_21 = st.number_input("Cote 2-1", min_value=1.01, value=7.0, step=0.1)

# Bouton d'analyse
st.markdown("---")
if st.button("🚀 LANCER L'ANALYSE VIP DU ROBOT", use_container_width=True):
    
    # Organisation des dictionnaires pour la fonction
    cotes_dc = {'1X': dc_1X, '12': dc_12, '2X': dc_2X}
    cotes_mf = {'V1/V1': mf_v1v1, 'X/X': mf_xx, 'V2/V2': mf_v2v2}
    cotes_score = {'1-0': se_10, '1-1': se_11, '2-1': se_21}
    
    # Lancement du calcul
    resultats = analyser_match_vip(cotes_dc, cotes_score, cotes_mf)
    
    st.header("🎯 Résultats de l'Analyse VIP")
    
    if resultats:
        for marche, info in resultats.items():
            st.success(f"🟩 **{marche}** : {info['Pronto']} — **Fiabilité : {info['Confiance']}%** ✅")
    else:
        st.warning("⚠️ Ce match est trop risqué ! L'indice de confiance est en dessous de 80%. Le robot conseille de NE PAS le mettre dans le ticket VIP.")
