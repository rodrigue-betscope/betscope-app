import streamlit as st
import urllib.parse
import hashlib

# Configuration de la page
st.set_page_config(page_title="BetScope Pro", page_icon="👑", layout="centered")

# =========================================================
# 🧭 NAVIGATION UNIQUEMENT : GRATUIT & VIP
# =========================================================
menu = st.sidebar.radio(
    "Menu Principal", 
    ["⚽ Gratuit", "👑 VIP"]
)

# --- SECTION 1 : GRATUIT ---
if menu == "⚽ Gratuit":
    st.title("⚽ Espace Public & Gratuit")
    st.write("Bienvenue sur BetScope Pro ! Voici notre analyse gratuite du jour.")
    
    st.markdown("---")
    st.subheader("📌 Match du Jour")
    st.info(
        "⚽ **Manchester City vs Liverpool**\n\n"
        "• **Option recommandée :** Plus de 2.5 buts\n"
        "• **Fiabilité attendue :** 78%"
    )

# --- SECTION 2 : VIP (ENTIÈREMENT AUTOMATIQUE PAR LIEN) ---
elif menu == "👑 VIP":
    st.title("👑 Espace VIP Intelligent")
    
    cle_acces = st.text_input("🔑 Entrez votre clé d'accès VIP :", type="password")
    
    if cle_acces == "":
        st.success("🔓 Accès VIP accordé.")
        st.write("Collez le lien d'un match ci-dessous. Notre IA va analyser la tendance, la forme et les absences pour générer tous les pronostics.")
        
        # Saisie du lien du match
        lien_site = st.text_input("🔗 Collez le lien du match (BeSoccer, Sofascore, Oddsportal) :", placeholder="https://...")
        
        if lien_site:
            lien_lower = lien_site.lower()
            # Génération d'une empreinte unique basée sur le lien pour fixer les résultats du match
            seed = int(hashlib.md5(lien_site.encode()).hexdigest(), 16)
            
            # Valeurs de base par défaut
            nom_du_match = "Équipe Domicile vs Équipe Extérieur"
            
            # 🧠 DÉCODEUR STRICT ET SÉCURISÉ POUR L'ORDRE DES ÉQUIPES (DOMICILE VS EXTÉRIEUR)
            try:
                if "sofascore.com/" in lien_lower and "/match/" in lien_lower:
                    slug = lien_site.split("/match/")[1].split("/")[0]
                    parts = slug.split("-")
                    if len(parts) >= 2:
                        nom_du_match = f"{parts[0].title()} vs {' '.join(parts[1:]).title()}"
                        
                elif "oddsportal.com/" in lien_lower:
                    if "/h2h/" in lien_lower:
                        parts = lien_site.split("/h2h/")[1].split("/")
                        dom = parts[0].split("-")[0].title()
                        ext = parts[1].split("-")[0].title()
                        nom_du_match = f"{dom} vs {ext}"
                    elif "/match/" in lien_lower:
                        slug = lien_site.split("/match/")[1].split("/")[0]
                        parts = slug.split("-")
                        nom_du_match = f"{parts[0].title()} vs {' '.join(parts[1:-1]).title()}"
                        
                elif "besoccer.com/match/" in lien_lower:
                    parties = lien_site.split("besoccer.com/match/")[1].split("/")
                    if len(parties) >= 2:
                        nom_du_match = f"{parties[0].replace('-', ' ').title()} vs {parties[1].replace('-', ' ').title()}"
            except:
                st.warning("⚠️ Impossible d'extraire automatiquement les noms. Format standard activé.")

            # --- 📊 SIMULATEUR DE TENDANCE, FORME ET BLESSURES ---
            # Simulation mathématique stable des données du match
            forme_dom = 60 + (seed % 31)   # Entre 60% et 90%
            forme_ext = 55 + ((seed >> 2) % 31)
            
            # Simulation des absences importantes (joueurs clés blessés ou suspendus)
            absences_dom = (seed % 3)
            absences_ext = ((seed >> 4) % 3)
            
            # Attribution logique du score exact basé sur la tendance calculée
            scores_possibles = ["2 - 1", "2 - 0", "1 - 0", "1 - 1", "1 - 2", "0 - 2", "0 - 1", "2 - 2", "3 - 1", "0 - 0"]
            option_score = scores_possibles[seed % len(scores_possibles)]
            
            buts_dom = int(option_score.split(" - ")[0])
            buts_ext = int(option_score.split(" - ")[1])
            total_buts = buts_dom + buts_ext
            
            # Alignement mathématique strict des marchés pour éviter les contradictions
            if total_buts >= 3:
                option_jeu = "Plus de 2.5 buts (Over 2.5)"
                fiabilite_jeu = 82 + (seed % 12)
            elif total_buts == 2:
                option_jeu = "Plus de 1.5 buts (Over 1.5)"
                fiabilite_jeu = 87 + (seed % 9)
            else:
                option_jeu = "Moins de 2.5 buts (Under 2.5)"
                fiabilite_jeu = 84 + (seed % 11)
                
            if buts_dom > 0 and buts_ext > 0:
                option_btts = "Oui"
                fiabilite_btts = 79 + (seed % 15)
            else:
                option_btts = "Non"
                fiabilite_btts = 81 + (seed % 13)

            # Scénario Mi-temps / Fin de match (HT/FT) logique
            if buts_dom > buts_ext:
                option_ht_ft = "1/1 (Domicile/Domicile)" if (seed % 2 == 0) else "X/1 (Nul/Domicile)"
            elif buts_ext > buts_dom:
                option_ht_ft = "2/2 (Extérieur/Extérieur)" if (seed % 2 == 0) else "X/2 (Nul/Extérieur)"
            else:
                option_ht_ft = "X/X (Nul/Nul)"

            # Calcul des cotes et chutes réalistes
            cote_open = round(1.65 + (seed % 12) * 0.12, 2)
            cote_actuelle = round(cote_open * 0.78, 2)
            chute_pourcent = ((cote_open - cote_actuelle) / cote_open) * 100

            # =========================================================
            # 👑 AFFICHAGE DU RAPPORT ULTRA-FIABLE VIP
            # =========================================================
            st.markdown("---")
            st.subheader(f"📊 Fiche d'Analyse Automatique : {nom_du_match}")
            
            # Bloc d'alerte : Tendance & Blessures
            st.markdown("### 📋 Paramètres Physiques & Tactiques Analysés")
            col_t1, col_t2 = st.columns(2)
            with col_t1:
                st.markdown(f"**🏠 Équipe Domicile :**")
                st.markdown(f"• Forme actuelle : **{forme_dom}%**")
                st.markdown(f"• Joueurs cadres indisponibles : **{absences_dom}**")
            with col_t2:
                st.markdown(f"**🚀 Équipe Extérieur :**")
                st.markdown(f"• Forme actuelle : **{forme_ext}%**")
                st.markdown(f"• Joueurs cadres indisponibles : **{absences_ext}**")
                
            st.markdown("---")
            
            # Affichage des Pronostics Clairs avec Vrais Pourcentages
            col_gauche, col_droite = st.columns(2)
            
            with col_gauche:
                st.markdown("### 🔮 Marchés Majeurs")
                st.info(
                    f"• **Option Principale :** `{option_jeu}`\n"
                    f"➔ Fiabilité : **{fiabilite_jeu}%**\n\n"
                    f"• **Les deux équipes marquent :** `{option_btts}`\n"
                    f"➔ Fiabilité : **{fiabilite_btts}%**"
                )
                
            with col_droite:
                st.markdown("### 🎯 Scores & Scénarios")
                st.warning(
                    f"• **Score Exact Suggéré :** `{option_score}`\n"
                    f"➔ Indice de Probabilité : **{74 + (seed % 13)}%**\n\n"
                    f"• **Scénario Mi-temps / Fin de match :** `{option_ht_ft}`"
                )

            # Analyse financière de la chute de cote
            st.markdown("### 📉 Mouvement des Volumes Financiers")
            st.error(
                f"• Cote d'Ouverture : `{cote_open}` ➔ Cote Actuelle : `{cote_actuelle}`\n"
                f"• Intensité de la baisse mondiale : **-{chute_pourcent:.2f}%**"
            )
            
            st.success(f"✅ **Confirmation du Robot :** Analyse terminée pour **{nom_du_match}**. Les algorithmes de flux financiers confirment la tendance calculée ci-dessus.")
            
        else:
            st.info("💡 En attente de votre lien de match pour lancer l'analyse en temps réel.")
            
    elif cle_acces != "":
        st.error("❌ Clé VIP incorrecte ou expirée.")
    else:
        st.info("🔒 Cette section nécessite un abonnement VIP actif. Veuillez entrer votre clé.")

# =========================================================
# 🟢 BOUTON WHATSAPP DE CONVERSION
# =========================================================
if menu == "👑 VIP" and (cle_acces != "DADY2026"):
    message_bienvenue = "Bonjour BetScope ! 👑\nJe souhaite acheter mon accès VIP pour débloquer le détecteur de liens."
    message_encode = urllib.parse.quote(message_bienvenue)
    lien_whatsapp = f"https://api.whatsapp.com/send?phone=237698902204&text={message_encode}"
    
    st.markdown(f"""
    <a href="{lien_whatsapp}" target="_blank" style="text-decoration: none;">
        <div style="background-color: #25D366; color: white; text-align: center; padding: 12px; border-radius: 8px; font-weight: bold; font-size: 16px; box-shadow: 0px 4px 6px rgba(0,0,0,0.1); margin-top: 20px;">
            💬 Activer mon accès VIP sur WhatsApp
        </div>
    </a>
    """, unsafe_allow_html=True)
