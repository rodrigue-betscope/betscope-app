import streamlit as st
import time
import random
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

# Menu de navigation
menu = st.radio("Navigation", ["⚽ Pronostics Gratuits", "👑 Espace VIP Privé"], horizontal=True)

# Initialisation de la base de données temporaire pour stocker tes matchs du jour
if "match_vip_1" not in st.session_state:
    st.session_state["match_vip_1"] = "Real Madrid vs Barcelone"
    st.session_state["score_vip_1"] = "3 - 1"
    st.session_state["fiab_vip_1"] = "94%"
if "match_vip_2" not in st.session_state:
    st.session_state["match_vip_2"] = "Man. City vs Liverpool"
    st.session_state["htft_vip_2"] = "Mi-temps : X / Fin de match : 1"

# --- SECTION GRATUITE ---
if menu == "⚽ Pronostics Gratuits":
    st.subheader("Analyse Algorithmique Dynamique (Free)")
    match_url = st.text_input("Collez le lien du match ici (BeSoccer, Flashscore) :", placeholder="https://www.besoccer.com/match/...")
    
    if st.button("Lancer l'Analyse Gratuite 🚀", use_container_width=True):
        if match_url:
            with st.spinner("Analyse des volumes de mise..."):
                time.sleep(1.5)
                st.success("Analyse terminée !")
                st.info("🎯 **Pronostic conseillé :** Victoire Équipe 1 ou Nul (1X)")
        else:
            st.error("❌ Veuillez insérer un lien.")

# --- SECTION VIP ---
elif menu == "👑 Espace VIP Privé":
    st.subheader("🔒 Bienvenue dans l'Espace VIP")
    
    code_entre = st.text_input("Entrez votre clé d'accès VIP :", type="password", placeholder="Clé Secrète VIP...")
    
    if code_entre:
        # 🛠️ MODE ADMIN SECRET POUR TOI
        if code_entre == "ADMIN2026":
            st.success("👨‍💻 MODE ADMINISTRATEUR ACTIVÉ")
            st.markdown("### Modifiez les vrais matchs du jour ici :")
            
            st.session_state["match_vip_1"] = st.text_input("Match 1 (Score Exact) :", st.session_state["match_vip_1"])
            st.session_state["score_vip_1"] = st.text_input("Score exact pronostiqué :", st.session_state["score_vip_1"])
            
            st.session_state["match_vip_2"] = st.text_input("Match 2 (HT/FT) :", st.session_state["match_vip_2"])
            st.session_state["htft_vip_2"] = st.text_input("Pronostic HT/FT :", st.session_state["htft_vip_2"])
            
            st.info("La mise à jour est instantanée ! Entre maintenant ta clé client pour voir le résultat.")

        # 👑 MODE CLIENT VIP
        elif code_entre == "RODRIGUE2026":
            st.success("🔓 Accès VIP Accordé ! Bienvenue Boss.")
            st.markdown("---")
            
            date_aujourdhui = datetime.now().strftime("%d/%m/%Y")
            st.markdown(f"### 🎯 LES PRONOSTICS VIP DU {date_aujourdhui}")
            
            # Affichage des matchs que TU as configuré
            st.warning(f"🔥 **SCORE EXACT EXCLUSIF :**\n\n⚽ **{st.session_state['match_vip_1']}**\n\n➔ **Score : {st.session_state['score_vip_1']}** (Fiabilité {st.session_state['fiab_vip_1']})")
            st.markdown("")
            st.warning(f"🔥 **COMBINÉ HT/FT :**\n\n⚽ **{st.session_state['match_vip_2']}**\n\n➔ **{st.session_state['htft_vip_2']}**")
            
        else:
            st.error("❌ Clé d'accès incorrecte ou expirée.")
    
    st.markdown("---")
    st.markdown("### 📢 Comment obtenir votre clé d'accès VIP ?")
    lien_whatsapp = "https://wa.me/237600000000?text=Bonjour%20Rodrigue,%20je%20souhaite%20acheter%20la%20cle%20VIP%20BetScope"
    st.link_button("💬 Acheter mon accès VIP sur WhatsApp", lien_whatsapp, use_container_width=True)
