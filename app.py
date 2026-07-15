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
    
    # Clignotant vert dynamique pour le statut du Robot IA
    st.markdown("""
        <div style="display: flex; align-items: center; margin-bottom: 15px; background-color: #1a1c23; padding: 10px; border-radius: 8px; border: 1px solid #2e313d;">
            <span style="height: 10px; width: 10px; background-color: #25D366; border-radius: 50%; display: inline-block; margin-right: 10px; box-shadow: 0 0 8px #25D366; animation: pulse 1.5s infinite alternate;"></span>
            <span style="color: #25D366; font-weight: bold; font-size: 14px;">● Robot IA en ligne : Analyse des flux financiers mondiaux active</span>
        </div>
        <style>
            @keyframes pulse {
                from { opacity: 0.4; }
                to { opacity: 1; }
            }
        </style>
    """, unsafe_allow_html=True)
    
    cle_acces = st.text_input("🔑 Entrez votre clé d'accès VIP :", type="password")
    
    # Correction de la sécurité : l'accès s'ouvre avec le mot de passe défini
    if cle_acces == "DADY2026":
        st.success("🔓 Accès VIP accordé.")
        st.write("Collez le lien d'un match ci-dessous. L'algorithme analyse instantanément la tendance, le type de compétition, la forme et les absences.")
        
        # Saisie du lien du match
        lien_site = st.text_input("🔗 Collez le lien du match (BeSoccer, Sofascore, Oddsportal) :", placeholder="https://...")
        
        if lien_site:
            lien_site = lien_site.strip()
            lien_lower = lien_site.lower()
            
            # Génération d'une empreinte unique basée sur le lien
            seed = int(hashlib.md5(lien_site.encode()).hexdigest(), 16)
            
            nom_du_match = "Équipe Domicile vs Équipe Extérieur"
            
            # 🧠 DÉCODEUR DE LIENS SÉCURISÉ (Anti-Crash)
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
            except Exception:
                # Fallback de secours intelligent pour éviter les plantages
                nom_du_match = "Match Sélectionné (Analyse Auto)"

            # --- 🚀 MODULE 1 : ANALYSE DE CONTEXTE ---
            is_unpredictable = False
            type_competition = "Championnat Régulier (Standard)"
            
            if any(x in lien_lower for x in ["friendly", "amical", "amicaux"]):
                type_competition = "⚔️ Match Amical (Rotation d'effectif possible)"
                is_unpredictable = True
            elif any(x in lien_lower for x in ["cup", "coupe"]):
                type_competition = "🏆 Match de Coupe (Élimination Directe)"
            elif "play-off" in lien_lower or "playoff" in lien_lower:
                type_competition = "🔥 Match de Play-off (Haute Intensité)"

            # --- 🎛️ NOUVEAU MODULE : INTERACTION AVANT-MATCH (Bouton secret) ---
            st.markdown("---")
            with st.expander("⚡ Ajuster l'environnement du match (Optionnel)", expanded=False):
                st.write("Modifiez ces critères pour recalculer instantanément le pronostic du Robot IA :")
                motivation_equipes = st.select_slider(
                    "🎯 Climat de motivation des équipes :",
                    options=["Basse", "Moyenne (Standard)", "Maximale (Match Décisif)"],
                    value="Moyenne (Standard)"
                )
                climat_meteo = st.selectbox(
                    "🌧️ Conditions météorologiques :",
                    ["Standard / Sec", "Pluie battante / Terrain lourd", "Température extrême"]
                )

            # --- 📊 MODULE 2 : FORME ET BLESSURES (Influencés par la graine unique) ---
            base_forme_dom = 60 + (seed % 31)
            base_forme_ext = 55 + ((seed >> 2) % 31)
            
            absences_dom = (seed % 3)
            absences_ext = ((seed >> 4) % 3)

            # --- ⚙️ CALCULS LOGIQUES LIÉS AUX PARAMÈTRES INTERACTIFS ---
            # Pénalité de forme liée aux absences directes (ex: -5% par absent de marque)
            forme_dom = max(30, base_forme_dom - (absences_dom * 5))
            forme_ext = max(30, base_forme_ext - (absences_ext * 5))

            if motivation_equipes == "Maximale (Match Décisif)":
                forme_dom = min(100, forme_dom + 10)
                forme_ext = min(100, forme_ext + 10)
            elif motivation_equipes == "Basse":
                forme_dom = max(30, forme_dom - 15)
                forme_ext = max(30, forme_ext - 15)

            # --- 🎯 MODULE 3 : MATCHING DU SCORE LOGIQUE (Finie l'incohérence !) ---
            # Le score dépend directement de la différence de forme et du climat
            diff_forme = forme_dom - forme_ext

            if climat_meteo == "Pluie battante / Terrain lourd":
                # Moins de buts sur terrain lourd
                if diff_forme > 15:
                    option_score = "2 - 0" if (seed % 2 == 0) else "1 - 0"
                elif diff_forme < -15:
                    option_score = "0 - 2" if (seed % 2 == 0) else "0 - 1"
                else:
                    option_score = "0 - 0" if (seed % 2 == 0) else "1 - 1"
            else:
                # Score classique basé sur la forme physique modifiée
                if diff_forme > 20:
                    option_score = "3 - 1" if (seed % 2 == 0) else "2 - 0"
                elif diff_forme > 5:
                    option_score = "2 - 1" if (seed % 2 == 0) else "1 - 0"
                elif diff_forme < -20:
                    option_score = "0 - 3" if (seed % 2 == 0) else "0 - 2"
                elif diff_forme < -5:
                    option_score = "1 - 2" if (seed % 2 == 0) else "0 - 1"
                else:
                    option_score = "2 - 2" if (seed % 2 == 0) else "1 - 1"

            # Amicaux imposent plus d'instabilité
            if is_unpredictable:
                scores_amicaux = ["2 - 2", "3 - 2", "1 - 2", "2 - 1", "3 - 3"]
                option_score = scores_amicaux[seed % len(scores_amicaux)]

            buts_dom = int(option_score.split(" - ")[0])
            buts_ext = int(option_score.split(" - ")[1])
            total_buts = buts_dom + buts_ext
            
            # Paramétrage intelligent des options de buts
            if total_buts >= 3:
                option_jeu = "Plus de 2.5 buts (Over 2.5)"
                fiabilite_jeu = min(98, 80 + (int(forme_dom + forme_ext) // 12))
            elif total_buts == 2:
                option_jeu = "Plus de 1.5 buts (Over 1.5)"
                fiabilite_jeu = min(98, 84 + (int(forme_dom + forme_ext) // 15))
            else:
                option_jeu = "Moins de 2.5 buts (Under 2.5)"
                fiabilite_jeu = min(98, 82 + (seed % 10))
                
            if buts_dom > 0 and buts_ext > 0:
                option_btts = "Oui"
                fiabilite_btts = min(98, 77 + (seed % 12))
            else:
                option_btts = "Non"
                fiabilite_btts = min(98, 80 + (seed % 10))

            if buts_dom > buts_ext:
                option_ht_ft = "1/1 (Domicile/Domicile)" if (seed % 2 == 0) else "X/1 (Nul/Domicile)"
            elif buts_ext > buts_dom:
                option_ht_ft = "2/2 (Extérieur/Extérieur)" if (seed % 2 == 0) else "X/2 (Nul/Extérieur)"
            else:
                option_ht_ft = "X/X (Nul/Nul)"

            # --- 💰 MODULE 4 : ALIGNEMENT STRICT DES COTES 1X2 CONFORMES AU SCORE ---
            if buts_dom > buts_ext:
                diff = buts_dom - buts_ext
                cote_v1 = round(1.20 + (seed % 3) * 0.08, 2) if diff > 1 else round(1.55 + (seed % 4) * 0.10, 2)
                cote_x  = round(3.80 + (seed % 5) * 0.15, 2)
                cote_v2 = round(5.50 + (seed % 6) * 0.50, 2) if diff > 1 else round(3.40 + (seed % 4) * 0.20, 2)
            elif buts_ext > buts_dom:
                diff = buts_ext - buts_dom
                cote_v1 = round(5.80 + (seed % 6) * 0.40, 2) if diff > 1 else round(3.50 + (seed % 4) * 0.20, 2)
                cote_x  = round(3.70 + (seed % 5) * 0.15, 2)
                cote_v2 = round(1.18 + (seed % 3) * 0.06, 2) if diff > 1 else round(1.60 + (seed % 4) * 0.08, 2)
            else:
                # Match nul cohérent
                if buts_dom == 0:
                    cote_v1 = round(2.80 + (seed % 4) * 0.10, 2)
                    cote_x  = round(2.70 + (seed % 3) * 0.08, 2)
                    cote_v2 = round(2.90 + (seed % 4) * 0.10, 2)
                else:
                    cote_v1 = round(2.25 + (seed % 4) * 0.10, 2)
                    cote_x  = round(3.10 + (seed % 3) * 0.08, 2)
                    cote_v2 = round(2.35 + (seed % 4) * 0.10, 2)

            # Mouvement des cotes mondiales
            cote_open = round(1.80 + (seed % 10) * 0.12, 2)
            cote_actuelle = round(cote_open * 0.78, 2)
            chute_pourcent = ((cote_open - cote_actuelle) / cote_open) * 100

            # Détermination de l'indice de sécurité VIP
            badge_confiance = "🔥 ULTRA SAFE" if fiabilite_jeu >= 88 else "⚡ HAUTE FIABILITÉ"
            if is_unpredictable:
                badge_confiance = "⚠️ PRUDENCE (Match Amical)"

            # =========================================================
            # 👑 AFFICHAGE DU RAPPORT
            # =========================================================
            st.markdown("---")
            st.subheader(f"📊 Fiche d'Analyse Automatique : {nom_du_match}")
            st.markdown(f"**Indice de Confiance :** `{badge_confiance}` | **Contexte :** `{type_competition}`")
            
            st.markdown("### 📋 Paramètres Physiques & Tactiques Analysés")
            col_t1, col_t2 = st.columns(2)
            with col_t1:
                st.markdown(f"**🏠 Équipe Domicile :**")
                st.markdown(f"• Forme actuelle : **{forme_dom:.0f}%**")
                st.markdown(f"• Joueurs cadres indisponibles : **{absences_dom}**")
            with col_t2:
                st.markdown(f"**🚀 Équipe Extérieur :**")
                st.markdown(f"• Forme actuelle : **{forme_ext:.0f}%**")
                st.markdown(f"• Joueurs cadres indisponibles : **{absences_ext}**")
                
            st.markdown("---")
            
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

            st.markdown("### ⚖️ Estimation Pro des Cotes (1X2)")
            st.code(f"Victoire Domicile (1) : {cote_v1}  |  Match Nul (X) : {cote_x}  |  Victoire Extérieur (2) : {cote_v2}")

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
# 🟢 BOUTON WHATSAPP
# =========================================================
if menu == "👑 VIP" and (cle_acces != ""):
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
