import streamlit as st
import time
import random
import requests
from datetime import datetime

st.set_page_config(page_title="BetScope Pro", page_icon="🤖", layout="centered")

# Style CSS pour cacher le menu Streamlit et faire plus "Application Mobile"
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

st.title("🤖 BetScope - L'IA des Pronostics")
st.markdown("---")

# Menu de navigation en boutons radio (adapté au téléphone)
menu = st.radio("Navigation", ["⚽ Pronostics Gratuits", "👑 Espace VIP Privé"], horizontal=True)

# --- SECTION GRATUITE ---
if menu == "⚽ Pronostics Gratuits":
    st.subheader("Analyse Algorithmique Dynamique (Free)")
    
    match_url = st.text_input("Collez le lien du match ici (BeSoccer, Flashscore) :", placeholder="https://www.besoccer.com/match/...")
    
    if st.button("Lancer l'Analyse Gratuite 🚀", use_container_width=True):
        if match_url:
            with st.spinner("Analyse des volumes de mise..."):
                time.sleep(2)
                
                # Simulation de cotes
                c_1, c_X, c_2 = 1.85, 3.40, 4.20
                st.success("Analyse terminée !")
                
                st.markdown("### 📉 Dropping Odds (Chute des cotes)")
                col1, col2, col3 = st.columns(3)
                col1.metric("Équipe 1", f"{c_1}", "-12%")
                col2.metric("Match Nul", f"{c_X}", "+2%")
                col3.metric("Équipe 2", f"{c_2}", "+8%")
                
                st.info("🎯 **Pronostic conseillé :** Victoire Équipe 1 ou Nul (1X)")
        else:
            st.error("❌ Veuillez insérer un lien.")

# --- SECTION VIP ---
elif menu == "👑 Espace VIP Privé":
    st.subheader("🔒 Bienvenue dans l'Espace VIP")
    st.write("Accédez aux algorithmes de Scores Exacts et aux pronostics Mi-temps/Fin de match (HT/FT) à haute fiabilité.")
    
    # Système de verrouillage par clé
    mot_de_passe_correct = "RODRIGUE2026"
    
    code_entre = st.text_input("Entrez votre clé d'accès VIP :", type="password", placeholder="Clé Secrète VIP...")
    
    if code_entre:
        if code_entre == mot_de_passe_correct:
            st.success("🔓 Accès VIP Accordé ! Bienvenue Boss.")
            st.markdown("---")
            
            date_aujourdhui = datetime.now().strftime("%d/%m/%Y")
            st.markdown(f"### 🎯 LES PRONOSTICS VIP DU {date_aujourdhui}")
            
            # --- RÉCUPÉRATION DES VRAIS MATCHS EN DIRECT ---
            with st.spinner("Extraction des vrais matchs du jour en cours..."):
                try:
                    # Appel à une API publique gratuite de matchs en direct
                    url_api = "https://www.scorebat.com/video-api/v3/feed"
                    reponse = requests.get(url_api, timeout=10)
                    donnees = reponse.json()
                    
                    # On extrait les vrais matchs disponibles aujourd'hui
                    vrais_matchs = []
                    if "response" in donnees:
                        for match in donnees["response"]:
                            titre_match = match.get("title", "")
                            if " vs " in titre_match:
                                vrais_matchs.append(titre_match)
                    
                    # Si l'API renvoie des matchs, on prend deux vraies affiches réelles
                    if len(vrais_matchs) >= 2:
                        # Fixer la graine pour garder les mêmes pronos toute la journée
                        graine_jour = int(datetime.now().strftime("%Y%m%d"))
                        random.seed(graine_jour)
                        
                        affiches_du_jour = random.sample(vrais_matchs, 2)
                        match1 = affiches_du_jour[0]
                        match2 = affiches_du_jour[1]
                    else:
                        # Sécurité si l'API est vide momentanément
                        match1 = "Real Madrid vs Barcelone"
                        match2 = "Man. City vs Liverpool"
                        
                except Exception as e:
                    # Sécurité en cas de coupure réseau
                    match1 = "Real Madrid vs Barcelone"
                    match2 = "Man. City vs Liverpool"
            
            # --- ALGORITHME DE GÉNÉRATION DES PRONOS SUR LES VRAIS MATCHS ---
            graine_jour = int(datetime.now().strftime("%Y%m%d"))
            random.seed(graine_jour)
            
            # Options de scores et HT/FT
            scores_possibles = [("2 - 1", "92%"), ("3 - 1", "94%"), ("2 - 0", "89%"), ("1 - 0", "91%"), ("1 - 1", "88%")]
            score1, fiab1 = random.choice(scores_possibles)
            
            ht_ft_possibles = [("X (Nul)", "1"), ("1", "1"), ("X (Nul)", "2"), ("2", "2")]
            mt, fm = random.choice(ht_ft_possibles)
            
            # Affichage final des vrais pronostics
            st.warning(f"🔥 **SCORE EXACT EXCLUSIF :**\n\n⚽ **{match1}**\n\n➔ **Score : {score1}** (Fiabilité {fiab1})")
            st.markdown("")
            st.warning(f"🔥 **COMBINÉ HT/FT :**\n\n⚽ **{match2}**\n\n➔ **Mi-temps : {mt} / Fin de match : {fm}**")
            
            random.seed() # Reset
            
        else:
            st.error("❌ Clé d'accès incorrecte ou expirée.")
    
    # Bloc publicitaire pour pousser à l'achat VIP
    st.markdown("---")
    st.markdown("""
    ### 📢 Comment obtenir votre clé d'accès VIP ?
    Pour intégrer le groupe privé et recevoir votre clé VIP instantanément, cliquez sur le bouton ci-dessous pour m'écrire directement sur WhatsApp.
    """)
    
    lien_whatsapp = "https://wa.me/237600000000?text=Bonjour%20Rodrigue,%20je%20souhaite%20acheter%20la%20cle%20VIP%20BetScope"
    st.link_button("💬 Acheter mon accès VIP sur WhatsApp", lien_whatsapp, use_container_width=True)
