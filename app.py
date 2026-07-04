import streamlit as st
import time
import random

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
    mot_de_passe_correct = "RODRIGUE2026" # Tu pourras changer ce mot de passe quand tu veux
    
    code_entre = st.text_input("Entrez votre clé d'accès VIP :", type="password", placeholder="Clé Secrète VIP...")
    
    if code_entre:
        if code_entre == mot_de_passe_correct:
            st.success("🔓 Accès VIP Accordé ! Bienvenue Boss.")
            st.markdown("---")
            
            # Contenu ultra fiable réservé aux VIP
            st.markdown("### 🎯 LES PRONOSTICS VIP DU JOUR")
            
            st.warning("🔥 **SCORE EXACT EXCLUSIF :** Real Madrid vs Barcelone ➔ **Score : 3 - 1** (Fiabilité 92%)")
            st.warning("🔥 **COMBINÉ HT/FT :** Man. City vs Liverpool ➔ **Mi-temps : X / Fin de match : 1**")
            
        else:
            st.error("❌ Clé d'accès incorrecte ou expirée.")
    
    # Bloc publicitaire pour pousser à l'achat VIP
    st.markdown("---")
    st.markdown("""
    ### 📢 Comment obtenir votre clé d'accès VIP ?
    Pour intégrer le groupe privé et recevoir votre clé VIP instantanément, cliquez sur le bouton ci-dessous pour m'écrire directement sur WhatsApp.
    """)
    
    # Remplace le numéro ci-dessous par ton vrai numéro WhatsApp (ex: 237600000000)
    lien_whatsapp = "https://wa.me/237600000000?text=Bonjour%20Rodrigue,%20je%20souhaite%20acheter%20la%20cle%20VIP%20BetScope"
    st.link_button("💬 Acheter mon accès VIP sur WhatsApp", lien_whatsapp, use_container_width=True)
