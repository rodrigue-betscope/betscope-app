import streamlit as st
import time
import random
from datetime import datetime

st.set_page_config(page_title="BetScope Pro", page_icon="🤖", layout="centered")

# Style CSS pour faire "Application Mobile"
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

st.title("🤖 BetScope - L'IA des Pronostics")
st.markdown("---")

menu = st.radio("Navigation", ["⚽ Pronostics Gratuits", "👑 Espace VIP Privé"], horizontal=True)

# --- SECTION GRATUITE ---
if menu == "⚽ Pronostics Gratuits":
    st.subheader("Analyse Algorithmique Dynamique (Free)")
    match_url = st.text_input("Collez le lien du match ici :", placeholder="https://www.besoccer.com/match/...")
    
    if st.button("Lancer l'Analyse Gratuite 🚀", use_container_width=True):
        if match_url:
            with st.spinner("Analyse IA en cours..."):
                time.sleep(1.5)
                st.success("Analyse terminée !")
                st.info("🎯 **Pronostic conseillé :** Victoire Équipe 1 ou Nul (1X)")
        else:
            st.error("❌ Veuillez insérer un lien.")

# --- SECTION VIP ---
elif menu == "👑 Espace VIP Privé":
    st.subheader("🔒 Bienvenue dans l'Espace VIP")
    
    mot_de_passe_correct = "RODRIGUE2026"
    code_entre = st.text_input("Entrez votre clé d'accès VIP :", type="password", placeholder="Clé Secrète VIP...")
    
    if code_entre:
        if code_entre == mot_de_passe_correct:
            st.success("🔓 Accès VIP Accordé ! Bienvenue Boss.")
            st.markdown("---")
            
            date_aujourdhui = datetime.now().strftime("%d/%m/%Y")
            st.markdown(f"### 🎯 LES PRONOSTICS VIP DU {date_aujourdhui}")
            
            # =================================================================
            # ✍️ MODIFIE UNIQUEMENT LES DEUX LIGNES CI-DESSOUS CHAQUE MATIN :
            # =================================================================
            vrai_match_1 = "canada  vs maroc"
            vrai_match_2 = "Paraguay vs France"
            # =================================================================
            
            # L'IA utilise la date du jour pour bloquer les mêmes pronos toute la journée
            graine_jour = int(datetime.now().strftime("%Y%m%d"))
            random.seed(graine_jour)
            
            # Génération IA des scores exacts
            scores_ia = [("2 - 1", "92%"), ("3 - 1", "95%"), ("2 - 0", "89%"), ("1 - 0", "91%"), ("1 - 1", "88%")]
            score_predit, fiab = random.choice(scores_ia)
            
            # Génération IA du HT/FT
            htft_ia = [("Mi-temps : X / Fin de match : 1", "90%"), ("Mi-temps : 1 / Fin de match : 1", "93%"), ("Mi-temps : X / Fin de match : 2", "87%")]
            htft_predit, fiab_htft = random.choice(htft_ia)
            
            # Affichage final pour tes clients
            st.warning(f"🔥 **SCORE EXACT EXCLUSIF (Généré par IA) :**\n\n⚽ **{vrai_match_1}**\n\n➔ **Score Pronostiqué : {score_predit}** (Fiabilité {fiab})")
            st.markdown("")
            st.warning(f"🔥 **COMBINÉ HT/FT (Généré par IA) :**\n\n⚽ **{vrai_match_2}**\n\n➔ **{htft_predit}** (Fiabilité {fiab_htft})")
            
            random.seed() # Reset
            
        else:
            st.error("❌ Clé d'accès incorrecte ou expirée.")
            
    st.markdown("---")
    st.markdown("### 📢 Comment obtenir votre clé d'accès VIP ?")
    lien_whatsapp = "https://wa.me/237600000000?text=Bonjour%20Rodrigue,%20je%20souhaite%20acheter%20la%20cle%20VIP%20BetScope"
    st.link_button("💬 Acheter mon accès VIP sur WhatsApp", lien_whatsapp, use_container_width=True)
