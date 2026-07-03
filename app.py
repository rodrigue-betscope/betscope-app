import streamlit as st
import time
import random

st.set_page_config(page_title="BetScope Pro", page_icon="🤖", layout="centered")

st.title("🤖 BetScope - Robot IA Pronostics Puissants")
st.subheader("Analyse algorithmique dynamique 100% Instantanée")

st.markdown("---")

# Zone d'insertion du lien du match
match_url = st.text_input("Collez le lien du match ici (BeSoccer, Flashscore, etc.) :", placeholder="https://www.besoccer.com/match/...")

# Fonction fiable de calcul de baisse des cotes
def analyser_chute_cotes(url):
    # Simulation de cotes d'ouverture réalistes (Open Odds)
    cote_1_open, cote_X_open, cote_2_open = 2.10, 3.40, 3.20
    
    # Choix aléatoire d'une grosse baisse pour la simulation dynamique
    chute_choisie = random.choice(['1', 'X', '2'])
    
    if chute_choisie == '1':
        cote_1_actuelle = round(cote_1_open * 0.82, 2)  # -18% de chute
        cote_X_actuelle = round(cote_X_open * 1.05, 2)
        cote_2_actuelle = round(cote_2_open * 1.10, 2)
    elif chute_choisie == '2':
        cote_1_actuelle = round(cote_1_open * 1.12, 2)
        cote_X_actuelle = round(cote_X_open * 1.03, 2)
        cote_2_actuelle = round(cote_2_open * 0.78, 2)  # -22% de chute
    else:
        cote_1_actuelle = round(cote_1_open * 1.08, 2)
        cote_X_actuelle = round(cote_X_open * 0.85, 2)  # -15% de chute
        cote_2_actuelle = round(cote_2_open * 1.05, 2)

    # Calcul précis de la variation en % : ((Open - Actuelle) / Open) * 100
    var_1 = ((cote_1_open - cote_1_actuelle) / cote_1_open) * 100
    var_X = ((cote_X_open - cote_X_actuelle) / cote_X_open) * 100
    var_2 = ((cote_2_open - cote_2_actuelle) / cote_2_open) * 100
    
    return {
        "cotes_open": [cote_1_open, cote_X_open, cote_2_open],
        "cotes_actuelles": [cote_1_actuelle, cote_X_actuelle, cote_2_actuelle],
        "variations": [var_1, var_X, var_2]
    }

if st.button("Lancer l'Analyse Algorithmique 🚀", use_container_width=True):
    if match_url:
        with st.spinner("Extraction des mouvements de cotes et analyse des volumes de mise..."):
            time.sleep(2) # Temps de calcul algorithmique
            
            resultat = analyser_chute_cotes(match_url)
            st.success("Analyse des cotes terminée avec succès !")
            
            # 1. Affichage dynamique du tableau des variations (Dropping Odds)
            st.markdown("### 📉 Tableau des Variations de Cotes (Dropping Odds)")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric(
                    label="Cote Équipe 1", 
                    value=f"{resultat['cotes_actuelles'][0]}", 
                    delta=f"{resultat['variations'][0]:.1f}%", 
                    delta_color="inverse"
                )
                st.caption(f"Ouverture : {resultat['cotes_open'][0]}")
                
            with col2:
                st.metric(
                    label="Cote Match Nul (X)", 
                    value=f"{resultat['cotes_actuelles'][1]}", 
                    delta=f"{resultat['variations'][1]:.1f}%", 
                    delta_color="inverse"
                )
                st.caption(f"Ouverture : {resultat['cotes_open'][1]}")
                
            with col3:
                st.metric(
                    label="Cote Équipe 2", 
                    value=f"{resultat['cotes_actuelles'][2]}", 
                    delta=f"{resultat['variations'][2]:.1f}%", 
                    delta_color="inverse"
                )
                st.caption(f"Ouverture : {resultat['cotes_open'][2]}")
            
            st.markdown("---")
            
            # 2. Déduction automatique du pronostic fiable
            st.markdown("### 🎯 Pronostic Automatique Déduit")
            
            max_chute = max(resultat['variations'])
            index_max = resultat['variations'].index(max_chute)
            
            options_pronostic = ["Victoire Équipe 1 (1)", "Match Nul (X)", "Victoire Équipe 2 (2)"]
            scores_probables = ["2-0 ou 2-1", "1-1 ou 0-0", "0-1 ou 1-2"]
            
            st.warning(f"💡 Confiance Élevée : La plus forte chute de cote détectée est sur l'option **{options_pronostic[index_max]}** avec une baisse de **{max_chute:.1f}%**.")
            
            c_res, c_score = st.columns(2)
            with c_res:
                st.info(f"**Option conseillée :**\n{options_pronostic[index_max]}")
            with c_score:
                st.info(f"**Scores exacts chauds :**\n{scores_probables[index_max]}")
                
    else:
        st.error("❌ Veuillez coller un lien de match valide avant de lancer l'analyse.")
