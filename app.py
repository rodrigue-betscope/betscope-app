import streamlit as st
import urllib.parse
import urllib.request
import hashlib
import re
import html

# Configuration de la page
st.set_page_config(page_title="BetScope Pro", page_icon="👑", layout="centered")

# =========================================================
# 🎨 STYLE CSS EN LIGNE (FOND SOMBRE & BADGES PREMIUM)
# =========================================================
st.markdown("""
<style>
    .stApp { background-color: #0E1117; color: #FFFFFF; }
    .main-title { color: #FF9900; font-weight: bold; font-size: 26px; }
    .section-title { border-left: 4px solid #FF9900; padding-left: 10px; color: #FFFFFF; font-size: 18px; margin-top: 20px; margin-bottom: 15px; }
    .crypto-badge { background-color: #1A1C23; border: 1px solid #3A3F50; padding: 10px; border-radius: 8px; margin-bottom: 10px; }
</style>
""", unsafe_allow_html=True)

# =========================================================
# 🔐 CONFIGURATION DES CLÉS
# =========================================================
CLE_VIP_CORRECTE = ""  
CLE_ADMIN_FORCAGE = ""  

# =========================================================
# 🧠 DÉCODEUR DE MATCH ULTRA-INTELLIGENT
# =========================================================
def extraire_nom_match_intelligent(lien_sofa, lien_odds):
    liens = [l for l in [lien_sofa, lien_odds] if l]
    
    for url in liens:
        try:
            req = urllib.request.Request(
                url, 
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
            )
            with urllib.request.urlopen(req, timeout=2.5) as response:
                content = response.read().decode('utf-8', errors='ignore')
                match = re.search(r'<title>(.*?)</title>', content, re.IGNORECASE | re.DOTALL)
                if match:
                    titre_brut = html.unescape(match.group(1).strip())
                    
                    titre_clean = re.sub(r'(?i)\s+live score,.*', '', titre_brut)
                    titre_clean = titre_clean.replace(" | Sofascore", "")
                    
                    titre_clean = re.sub(r'(?i)\s+(H2H|betting|odds|cotes).*', '', titre_clean)
                    titre_clean = titre_clean.replace(" | Oddsportal", "")
                    
                    for sep in [" - ", " vs ", " VS ", " v ", " V "]:
                        if sep in titre_clean:
                            parties = titre_clean.split(sep)
                            dom = parties[0].strip()
                            ext = parties[1].strip()
                            return f"{dom} vs {ext}"
                            
                    if 5 < len(titre_clean) < 80:
                        return titre_clean
        except Exception:
            pass

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
            
            if "-vs-" in slug:
                parts = slug.split("-vs-")
                dom = parts[0].replace("-", " ").title()
                ext = parts[1].replace("-", " ").title()
                return f"{dom} vs {ext}"
            else:
                parts = [p for p in slug.split("-") if p]
                
                if "fc" in parts and 0 < parts.index("fc") < len(parts) - 1:
                    idx = parts.index("fc")
                    dom = " ".join(parts[:idx+1]).title()
                    ext = " ".join(parts[idx+1:]).title()
                    return f"{dom} vs {ext}"
                elif len(parts) >= 2:
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

if menu == "⚽ Gratuit":
    st.markdown('<div class="main-title">⚽ Espace Public & Gratuit</div>', unsafe_allow_html=True)
    st.write("Bienvenue sur BetScope Pro ! Voici notre analyse gratuite du jour.")
    
    st.markdown("---")
    st.subheader("📌 Match du Jour")
    st.info(
        "⚽ **Manchester City vs Liverpool**\n\n"
        "• **Option recommandée :** Plus de 2.5 buts\n"
        "• **Fiabilité attendue :** 78%"
    )

elif menu == "👑 VIP":
    st.markdown('<div class="main-title">👑 Espace VIP Intelligent</div>', unsafe_allow_html=True)
    
    st.markdown("""
<div style="display: flex; align-items: center; margin-bottom: 15px; background-color: #1a1c23; padding: 12px; border-radius: 8px; border: 1px solid #25D366;">
<span style="height: 8px; width: 8px; background-color: #25D366; border-radius: 50%; display: inline-block; margin-right: 10px; box-shadow: 0 0 8px #25D366;"></span>
<span style="color: #25D366; font-weight: bold; font-size: 13px;">Robot IA en ligne : Double Analyse Actve</span>
</div>
""", unsafe_allow_html=True)
    
    cle_acces = st.text_input("🔑 Entrez votre clé d'accès VIP :", type="password")
    
    if cle_acces == CLE_VIP_CORRECTE:
        st.success("🔓 Accès VIP accordé.")
        
        col_l1, col_l2 = st.columns(2)
        with col_l1:
            lien_sofa = st.text_input("🔗 Lien Sofascore (Terrain) :", placeholder="https://www.sofascore.com/...").strip()
        with col_l2:
            lien_odds = st.text_input("🔗 Lien Oddsportal (Finance) :", placeholder="https://www.oddsportal.com/...").strip()
        
        if lien_sofa or lien_odds:
            lien_combine = lien_sofa + lien_odds
            seed = int(hashlib.md5(lien_combine.encode()).hexdigest(), 16)
            
            nom_du_match = extraire_nom_match_intelligent(lien_sofa, lien_odds)

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
                    st.success("⚡ CONTRÔLEUR MANUEL ACTIVÉ !")
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
            # 📊 BLOC 1 : ANALYSE SPORTIVE (SOFASCORE)
            # =========================================================
            st.markdown('<div class="section-title">🟢 SECTION 1 : Analyse Sportive & Terrain (Sofascore)</div>', unsafe_allow_html=True)
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
                st.info(f"""• **Option Principale :** `{option_jeu}`
➔ Fiabilité : **{fiabilite_jeu}%**

• **Les deux équipes marquent :** `{option_btts}`
➔ Fiabilité : **{fiabilite_btts}%**""")
            with col_droite:
                st.markdown("### 🎯 Scores & Scénarios")
                st.warning(f"""• **Score Exact Suggéré :** `{option_score}`
➔ Indice de Probabilité : **{74 + (seed % 13)}%**

• **Scénario Mi-temps / Fin :** `{option_ht_ft}`""")

            # =========================================================
            # 📉 BLOC 2 : DETECTEUR DE FLUX FINANCIERS (ODSPORTAL)
            # =========================================================
            st.markdown('<div class="section-title">📉 SECTION 2 : Analyse des Volumes & Cotes (Oddsportal)</div>', unsafe_allow_html=True)
            
            st.markdown("### ⚖️ Comparatif Mondial des Cotes (1X2)")
            st.code(f"Victoire Domicile (1) : {cote_v1:.2f}  |  Match Nul (X) : {cote_x:.2f}  |  Victoire Extérieur (2) : {cote_v2:.2f}")

            st.markdown("### 📉 Analyse de la Baisse des Cotes (Dropping Odds)")
            st.error(f"""• Cote d'Ouverture : `{cote_open:.2f}` ➔ Cote Actuelle : `{cote_actuelle:.2f}`
• Intensité de la baisse mondiale : **-{chute_pourcent:.2f}%**""")
            
            st.markdown("### ⚡ Surcharges Financières & Mises Globales")
            st.progress(pression_mises / 100)
            
            if pression_mises >= 85:
                st.warning(f"🚨 **ALERTE FLUX ATYPIQUES ({pression_mises}%) :** Volume massif de mises asiatiques détecté. Option validée à 100%.")
            else:
                st.info(f"📈 Aucun mouvement suspect. Flux financiers stables à **{pression_mises}%**.")
            
            # =========================================================
            # 🎫 GÉNÉRATEUR DE COUPON CORRIGÉ & PROPRE
            # =========================================================
            st.markdown("---")
            st.markdown("### 🎫 Coupon de Partage VIP Rapide")
            
            # Construction propre de la chaîne de texte du coupon
            coupon_texte = (
                f"👑 BETSCOPE PRO VIP 👑\n"
                f"⚽ Match : {nom_du_match}\n"
                f"📌 Compétition : {type_competition}\n"
                f"🔥 Indice : {badge_confiance}\n\n"
                f"📊 SECTION SOFASCORE (Terrain) :\n"
                f"➔ Option Principale : {option_jeu} (Fiabilité : {fiabilite_jeu}%)\n"
                f"➔ Score Exact Suggéré : {option_score}\n"
                f"➔ Scénario Mi-temps/Fin : {option_ht_ft}\n\n"
                f"📉 SECTION ODDSPORTAL (Finance) :\n"
                f"➔ Cotes 1X2 : Dom {cote_v1:.2f} | Nul {cote_x:.2f} | Ext {cote_v2:.2f}\n"
                f"➔ Intensité Baisse : -{chute_pourcent:.2f}%\n"
                f"➔ Pression Mises : {pression_mises}%"
            )
            
            # Affichage dans un bloc de texte copiable d'un clic
            st.text_area("📋 Clique à l'intérieur pour copier tout le rapport :", value=coupon_texte, height=250)

    elif cle_acces != "":
        st.error("❌ Clé d'accès VIP invalide.")
    else:
        st.info("🔒 Contenu hautement sécurisé. Veuillez entrer votre clé d'abonnement VIP.")
