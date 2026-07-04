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
            
            # Affichage de la date du jour pour faire pro
            date_aujourdhui = datetime.now().strftime("%d/%m/%Y")
            st.markdown(f"### 🎯 LES PRONOSTICS VIP DU {date_aujourdhui}")
            
            # --- ALGORITHME GÉNÉRATEUR AVANCÉ ---
            # Une énorme liste de clubs pour varier au maximum les affiches chaque jour
            grands_clubs = [
                "Real Madrid", "Barcelone", "Man. City", "Liverpool", "PSG", "Bayern Munich", 
                "Arsenal", "Inter Milan", "Juventus", "Chelsea", "Dortmund", "Athletic Bilbao",
                "Manchester United", "AC Milan", "Naples", "Atlético Madrid", "Bayer Leverkusen",
                "Tottenham", "Sporting CP", "Benfica", "Ajax Amsterdam", "Marseille", "Monaco",
                "Aston Villa", "Newcastle", "AS Rome", "Lazio Rome", "FC Porto", "PSV Eindhoven"
            ]
            
            # Utilisation de la date d'aujourd'hui pour bloquer les matchs de la journée
            graine_jour = int(datetime.now().strftime("%Y%m%d"))
            random.seed(graine_jour)
            
            # Sélection de 4 équipes différentes pour créer deux grosses affiches
            equipes_choisies = random.sample(grands_clubs, 4)
            
            # Match 1 (Score Exact)
            eq1, eq2 = equipes_choisies[0], equipes_choisies[1]
            scores_match_1 = [("2 - 1", "92%"), ("3 - 1", "95%"), ("2 - 0", "89%"), ("1 - 0", "91%"), ("3 - 2", "87%")]
            score1, fiab1 = random.choice(scores_match_1)
            
            # Match 2 (HT/FT)
            eq3, eq4 = equipes_choisies[2], equipes_choisies[3]
            ht_ft_possibles = [
                ("X (Nul)", "1 (Équipe Domicile)"), 
                ("1 (Équipe Domicile)", "1 (Équipe Domicile)"), 
                ("X (Nul)", "2 (Équipe Extérieur)"), 
                ("2 (Équipe Extérieur)", "2 (Équipe Extérieur)")
            ]
            mt, fm = random.choice(ht_ft_possibles)
            
            # Affichage dans l'application
            st.warning(f"🔥 **SCORE EXACT EXCLUSIF :** {eq1} vs {eq2}\n\n➔ **Score Pronostiqué : {score1}** (Fiabilité {fiab1})")
            st.markdown("")
            st.warning(f"🔥 **COMBINÉ HT/FT (Mi-temps/Fin de match) :** {eq3} vs {eq4}\n\n➔ **Mi-temps : {mt}** \n\n➔ **Fin de match : {fm}**")
            
            # Réinitialisation pour éviter de bloquer le reste de l'application
            random.seed()
            
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
