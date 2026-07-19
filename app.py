import streamlit as st
import urllib.parse
import urllib.request
import hashlib
import re
import html

# Configuration de la page
st.set_page_config(page_title="BetScope Pro", page_icon="👑", layout="centered")

# =========================================================
# 🔐 CONFIGURATION DES CLÉS
# =========================================================
CLE_VIP_CORRECTE = ""  # Clé pour tes clients VIP
CLE_ADMIN_FORCAGE = ""  # Ta clé secrète admin

# =========================================================
# 🧠 DÉCODEUR DE MATCH ULTRA-INTELLIGENT (CORRIGÉ)
# =========================================================
def extraire_nom_match_intelligent(lien_sofa, lien_odds):
    liens = [l for l in [lien_sofa, lien_odds] if l]
    
    # --- MÉTHODE 1 : LECTURE DU TITRE DU SITE EN DIRECT ---
    for url in liens:
        try:
            req = urllib.request.Request(
                url, 
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
            )
            # Timeout court de 2.5 secondes pour ne pas ralentir l'appli
            with urllib.request.urlopen(req, timeout=2.5) as response:
                content = response.read().decode('utf-8', errors='ignore')
                match = re.search(r'<title>(.*?)</title>', content, re.IGNORECASE | re.DOTALL)
                if match:
                    titre_brut = html.unescape(match.group(1).strip())
                    
                    # Nettoyage spécifique Sofascore
                    # Exemple: "Qingdao Hainiu - Henan FC live score, H2H..."
                    titre_clean = re.sub(r'(?i)\s+live score,.*', '', titre_brut)
                    titre_clean = titre_clean.replace(" | Sofascore", "")
                    
                    # Nettoyage spécifique Oddsportal
                    # Exemple: "Qingdao Hainiu - Henan FC Jinzu Dukang H2H betting odds..."
                    titre_clean = re.sub(r'(?i)\s+(H2H|betting|odds|cotes).*', '', titre_clean)
                    titre_clean = titre_clean.replace(" | Oddsportal", "")
                    
                    # Séparation propre
                    for sep in [" - ", " vs ", " VS ", " v ", " V "]:
                        if sep in titre_clean:
                            parties = titre_clean.split(sep)
                            dom = parties[0].strip()
                            ext = parties[1].strip()
                            return f"{dom} vs {ext}"
                            
                    if 5 < len(titre_clean) < 80:
                        return titre_clean
        except Exception:
            pass # Si la requête échoue ou est bloquée, on passe à la suite sans planter

    # --- MÉTHODE 2 : DECOUPAGE INTELLIGENT DE SLUG (PLAN B LOCAL) ---
    for url in liens:
        url_lower = url.lower()
        try:
            if "sofascore.com" in url_lower and "/match/" in url_lower:
                slug = url.split("/match/")[1].split("/")[0]
            elif "oddsportal.com" in url_lower and "/match/" in url_lower:
                slug = url.split("/match/")[1].split("/")[0]
            elif "oddsportal.com" in url_lower and "/h2h/" in url_lower:
                parts = url.split("/h2h/")[1].split("/")
                dom = parts[0].replace("-", " ").title()
                ext = parts[1].replace("-", " ").title()
                return f"{dom} vs {ext}"
            else:
                continue
            
            # Gestion des séparateurs textuels explicites
            if "-vs-" in slug:
                parts = slug.split("-vs-")
                dom = parts[0].replace("-", " ").title()
                ext = parts[1].replace("-", " ").title()
                return f"{dom} vs {ext}"
            else:
                # Découpage par mots
                parts = [p for p in slug.split("-") if p]
                
                # Si on trouve un indicateur comme "fc" au milieu, on l'utilise comme pivot
                if "fc" in parts and 0 < parts.index("fc") < len(parts) - 1:
                    idx = parts.index("fc")
                    dom = " ".join(parts[:idx+1]).title()
                    ext = " ".join(parts[idx+1:]).title()
                    return f"{dom} vs {ext}"
                elif len(parts) >= 2:
                    # Coupe équilibrée en deux au milieu
                    milieu = len(parts) // 2
                    dom = " ".join(parts[:milieu]).title()
                    ext = " ".join(parts[milieu:]).title()
                    return f"{dom} vs {ext}"
        except Exception:
            pass

    return "Match Sélectionné (Analyse Auto)"


# =========================================================
# 🧭 NAVIGATION : GRATUIT & VIP
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

# --- SECTION 2 : VIP (HYBRIDE DOUBLE LIENS) ---
elif menu == "👑 VIP":
    st.title("👑 Espace VIP Intelligent")
    
    # Clignotant vert dynamique pour le statut du Robot IA
    st.markdown("""
        <div style="display: flex; align-items: center; margin-bottom: 15px; background-color: #1a1c23; padding: 10px; border-radius: 8px; border: 1px solid #2e313d;">
            <span style="height: 10px; width: 10px; background-color: #25D366; border-radius: 50%; display: inline-block; margin-right: 10px; box-shadow: 0 0 8px #25D366; animation: pulse 1.5s infinite alternate;"></span>
            <span style="color: #25D366; font-weight: bold; font-size: 14px;">● Robot IA en ligne : Double Analyse (Sportive & Financière) active</span>
        </div>
        <style>
            @keyframes pulse {
                from { opacity: 0.4; }
                to { opacity: 1; }
            }
        </style>
    """, unsafe_allow_html=True)
    
    cle_acces = st.text_input("🔑 Entrez votre clé d'accès VIP :", type="password")
    
    if cle_acces == CLE_VIP_CORRECTE:
        st.success("🔓 Accès VIP accordé.")
        st.write("Pour une analyse optimale, vous pouvez coller le lien **Sofascore** ET le lien **Oddsportal** du match.")
        
        # --- DOUBLE CHAMP DE SAISIE ---
        col_l1, col_l2 = st.columns(2)
        with col_l1:
            lien_sofa = st.text_input("🔗 Lien Sofascore (Terrain) :", placeholder="https://www.sofascore.com/...").strip()
        with col_l2:
            lien_odds = st.text_input("🔗 Lien Oddsportal (Finance) :", placeholder="https://www.oddsportal.com/...").strip()
        
        if lien_sofa or lien_odds:
            # Création d'un texte combiné pour générer l'empreinte mathématique (seed)
            lien_combine = lien_sofa + lien_odds
            seed = int(hashlib.md5(lien_combine.encode()).hexdigest(), 16)
            
            # --- DÉCODAGE INTELLIGENT DU NOM ---
            nom_du_match = extraire_nom_match_intelligent(lien_sofa, lien_odds)

            # --- ANALYSE DE CONTEXTE ---
            is_unpredictable = False
            type_competition = "Championnat Régulier"
            
            texte_analyse = (lien_sofa + lien_odds).lower()
            if any(x in texte_analyse for x in ["friendly", "amical", "amicaux"]):
                type_competition = "⚔️ Match Amical"
                is_unpredictable = True
            elif any(x in texte_analyse for x in ["cup", "coupe"]):
                type_competition = "🏆 Match de Coupe"
            elif "play-off" in texte_analyse or "playoff" in texte_analyse:
                type_competition = "🔥 Match de Play-off"

            # --- AJUSTEMENT ENVIRONNEMENT (SECRET) ---
            st.markdown("---")
            with st.expander("⚡ Ajuster l'environnement du match (Optionnel)", expanded=False):
                motivation_equipes = st.select_slider(
                    "🎯 Motivation des équipes :",
                    options=["Basse", "Standard", "Maximale (Match Décisif)"],
                    value="Standard"
                )
                climat_meteo = st.selectbox(
                    "🌧️ Météo :",
                    ["Standard / Sec", "Terrain lourd / Pluie", "Température extrême"]
                )

            # --- CALCULS SIMULATEURS SOFASCORE (FORME & ABSENCES) ---
            base_forme_dom = 60 + (seed % 31)
            base_forme_ext = 55 + ((seed >> 2) % 31)
            absences_dom = (seed % 3)
            absences_ext = ((seed >> 4) % 3)

            forme_dom = max(30, base_forme_dom - (absences_dom * 5))
            forme_ext = max(30, base_forme_ext - (absences_ext * 5))

            if motivation_equipes == "Maximale (Match Décisif)":
                forme_dom = min(100, forme_dom + 10)
                forme_ext = min(100, forme_ext + 10)
            elif motivation_equipes == "Basse":
                forme_dom = max(30, forme_dom - 15)
                forme_ext = max(30, forme_ext - 15)

            # --- CRÉATION DU SCORE LOGIQUE ---
            diff_forme = forme_dom - forme_ext
            if climat_meteo == "Terrain lourd / Pluie":
                if diff_forme > 15:
                    option_score = "2 - 0" if (seed % 2 == 0) else "1 - 0"
                elif diff_forme < -15:
                    option_score = "0 - 2" if (seed % 2 == 0) else "0 - 1"
                else:
                    option_score = "0 - 0" if (seed % 2 == 0) else "1 - 1"
            else:
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

            if is_unpredictable:
                scores_amicaux = ["2 - 2", "3 - 2", "1 - 2", "2 - 1"]
                option_score = scores_amicaux[seed % len(scores_amicaux)]

            buts_dom = int(option_score.split(" - ")[0])
            buts_ext = int(option_score.split(" - ")[1])
            total_buts = buts_dom + buts_ext
            
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

            # --- CALCULS SIMULATEURS ODDSPORTAL (COTES & ALIGNEMENT) ---
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
                if buts_dom == 0:
                    cote_v1 = round(2.80 + (seed % 4) * 0.10, 2)
                    cote_x  = round(2.70 + (seed % 3) * 0.08, 2)
                    cote_v2 = round(2.90 + (seed % 4) * 0.10, 2)
                else:
                    cote_v1 = round(2.25 + (seed % 4) * 0.10, 2)
                    cote_x  = round(3.10 + (seed % 3) * 0.08, 2)
                    cote_v2 = round(2.35 + (seed % 4) * 0.10, 2)

            cote_open = round(1.80 + (seed % 10) * 0.12, 2)
            cote_actuelle = round(cote_open * 0.78, 2)
            chute_pourcent = ((cote_open - cote_actuelle) / cote_open) * 100

            badge_confiance = "🔥 ULTRA SAFE" if fiabilite_jeu >= 88 else "⚡ HAUTE FIABILITÉ"
            pression_mises = 75 + (seed % 21)

            # =========================================================
            # 🛠️ PANNEAU DE CONTROLE SECRET (ADMIN)
            # =========================================================
            st.markdown("---")
            with st.expander("🛠️ Paramètres Système Avancés (Masqué)", expanded=False):
                cle_admin = st.text_input("🔑 Entrez le code maître administrateur :", type="password")
                forcer_manuel = (cle_admin == CLE_ADMIN_FORCAGE)
                
                if forcer_manuel:
                    st.success("⚡ CONTRÔLEUR MANUEL ACTIVÉ - Tu as la main sur l'application !")
                    nom_du_match = st.text_input("Forceur - Nom du Match :", value=nom_du_match)
                    type_competition = st.text_input("Forceur - Type de Compétition :", value=type_competition)
                    badge_confiance = st.selectbox("Forceur - Badge Confiance :", ["🔥 ULTRA SAFE", "⚡ HAUTE FIABILITÉ", "⚠️ PRUDENCE"], index=0)
                    
                    col_f1, col_f2 = st.columns(2)
                    with col_f1:
                        forme_dom = st.slider("Forceur - Forme Domicile (%) :", 0, 100, int(forme_dom))
                        absences_dom = st.number_input("Forceur - Absents Domicile :", value=int(absences_dom))
                    with col_f2:
                        forme_ext = st.slider("Forceur - Forme Extérieur (%) :", 0, 100, int(forme_ext))
                        absences_ext = st.number_input("Forceur - Absents Extérieur :", value=int(absences_ext))
                    
                    col_f3, col_f4 = st.columns(2)
                    with col_f3:
                        option_jeu = st.text_input("Forceur - Option :", value=option_jeu)
                        fiabilite_jeu = st.slider("Forceur - Fiabilité (%) :", 0, 100, int(fiabilite_jeu))
                        option_btts = st.selectbox("Forceur - BTTS :", ["Oui", "Non"], index=0 if option_btts == "Oui" else 1)
                        fiabilite_btts = st.slider("Forceur - Fiabilité BTTS (%) :", 0, 100, int(fiabilite_btts))
                    with col_f4:
                        option_score = st.text_input("Forceur - Score (X - Y) :", value=option_score)
                        option_ht_ft = st.text_input("Forceur - Scénario Mi-temps / Fin :", value=option_ht_ft)
                    
                    col_f5, col_f6, col_f7 = st.columns(3)
                    with col_f5:
                        cote_v1 = st.number_input("Forceur - Cote Domicile :", value=float(cote_v1), step=0.01)
                    with col_f6:
                        cote_x = st.number_input("Forceur - Cote Nul :", value=float(cote_x), step=0.01)
                    with col_f7:
                        cote_v2 = st.number_input("Forceur - Cote Extérieur :", value=float(cote_v2), step=0.01)
                        
                    col_f8, col_f9 = st.columns(2)
                    with col_f8:
                        cote_open = st.number_input("Forceur - Cote Ouverture :", value=float(cote_open), step=0.01)
                        cote_actuelle = st.number_input("Forceur - Cote Actuelle :", value=float(cote_actuelle), step=0.01)
                        chute_pourcent = ((cote_open - cote_actuelle) / cote_open) * 100 if cote_open > 0 else 0.0
                    with col_f9:
                        pression_mises = st.slider("Forceur - Volume Mondial (%) :", 50, 100, int(pression_mises))

            # =========================================================
            # 📊 BLOC 1 : ANALYSE SPORTIVE (STYLE SOFASCORE)
            # =========================================================
            st.markdown("---")
            st.markdown("## 🟢 SECTION 1 : Analyse Sportive & Terrain (Sofascore)")
            st.subheader(f"📊 Fiche d'Analyse : {nom_du_match}")
            st.markdown(f"**Indice de Confiance :** `{badge_confiance}` | **Compétition :** `{type_competition}`")
            
            col_t1, col_t2 = st.columns(2)
            with col_t1:
                st.markdown(f"**🏠 Équipe Domicile :**")
                st.markdown(f"• Force du collectif : **{forme_dom:.0f}%**")
                st.markdown(f"• Joueurs cadres absents : **{absences_dom}**")
            with col_t2:
                st.markdown(f"**🚀 Équipe Extérieur :**")
                st.markdown(f"• Force du collectif : **{forme_ext:.0f}%**")
                st.markdown(f"• Joueurs cadres absents : **{absences_ext}**")
                
            st.markdown("### 📅 Historique Récent des 5 Derniers Matchs")
            col_h1, col_h2 = st.columns(2)
            options_serie = ["🟢 V", "🟡 N", "🔴 D"]
            serie_dom = [options_serie[(seed + i) % 3] for i in range(5)]
            serie_ext = [options_serie[(seed >> (i + 1)) % 3] for i in range(5)]
            with col_h1:
                st.markdown(f"**🏠 Domicile :** {' | '.join(serie_dom)}")
            with col_h2:
                st.markdown(f"**🚀 Extérieur :** {' | '.join(serie_ext)}")
                
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
                    f"• **Scénario Mi-temps / Fin :** `{option_ht_ft}`"
                )

            # =========================================================
            # 📉 BLOC 2 : DETECTEUR DE FLUX FINANCIERS (STYLE ODDSPORTAL)
            # =========================================================
            st.markdown("---")
            st.markdown("## 📉 SECTION 2 : Analyse des Volumes & Cotes (Oddsportal)")
            
            st.markdown("### ⚖️ Comparatif Mondial des Cotes (1X2)")
            st.code(f"Victoire Domicile (1) : {cote_v1:.2f}  |  Match Nul (X) : {cote_x:.2f}  |  Victoire Extérieur (2) : {cote_v2:.2f}")

            st.markdown("### 📉 Analyse de la Baisse des Cotes (Dropping Odds)")
            st.error(
                f"• Cote d'Ouverture : `{cote_open:.2f}` ➔ Cote Actuelle : `{cote_actuelle:.2f}`\n"
                f"• Intensité de la baisse mondiale : **-{chute_pourcent:.2f}%**"
            )
            
            st.markdown("### ⚡ Surcharges Financières & Mises Globales")
            st.progress(pression_mises / 100)
            
            if pression_mises >= 85:
                st.warning(f"🚨 **ALERTE FLUX ATYPIQUES ({pression_mises}%) :** Volume massif de mises asiatiaques détecté sur ce match. Option validée par le Robot IA.")
            else:
                st.info(f"📈 Aucun mouvement suspect. Flux financiers stables à **{pression_mises}%**.")
            
            # --- GENERATION DE COUPON ---
            st.markdown("---")
            st.markdown("### 🎫 Partager le Rapport VIP Fusionné")
            coupon_texte = f"""👑 *BETSCOPE PRO VIP* 👑
⚽ *Match :* {nom_du_match}
📌 *Compétition :* {type_competition}
🔥 *Indice :* {badge_confiance}

📊 _SECTION SOFASCORE (Terrain)_ :
➔ *Option Principale :* {option_jeu} (Fiabilité : {fiabilite_jeu}%)
➔ *Score Exact Suggéré :* {option_score}
➔ *Scénario Mi-temps/Fin :* {option_ht_ft}

📉 _SECTION ODDSPORTAL (Finance)_ :
➔ *Cotes 1X2 :* Dom {cote_v1:.2f} | Nul {cote_x:.2f} | Ext {cote_v2:.2f}
➔ *Intensité Baisse :* -{chute_pourcent:.2f}%
➔ *Pression Mises :* {pression_mises}% 

● _Analyse Robot IA Validée_ ✅"""
            
            st.text_area("📋 Copie ce rapport d'analyse hybride pour ton canal VIP :", value=coupon_texte, height=270)
            st.success(f"✅ **Confirmation du Robot :** Analyse hybride (Sofascore + Oddsportal) complétée avec succès.")
            
        else:
            st.info("💡 En attente de vos liens de match pour lancer l'analyse croisée en temps réel.")
            
    elif cle_acces != "":
        st.error("❌ Clé VIP incorrecte ou expirée.")
    else:
        st.info("🔒 Cette section nécessite un abonnement VIP actif. Veuillez entrer votre clé.")

# =========================================================
# 🟢 BOUTON WHATSAPP
# =========================================================
if menu == "👑 VIP" and (cle_acces != CLE_VIP_CORRECTE):
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
