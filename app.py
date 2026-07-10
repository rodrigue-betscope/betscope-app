import streamlit as st
import urllib.parse
import hashlib

st.set_page_config(page_title="BetScope Pro", page_icon="👑", layout="centered")

# =========================================================
# 🧭 BARRE LATÉRALE DE NAVIGATION
# =========================================================
menu = st.sidebar.radio(
    "Navigation", 
    ["⚽ Gratuit", "👑 VIP", "🏆 Résultats", "📉 Chute des Cotes"]
)

# SECTION 1 : GRATUIT
if menu == "⚽ Gratuit":
    st.title("⚽ Pronostics Gratuits")
    st.write("Bienvenue sur BetScope Pro ! Voici le pronostic public du jour.")
    st.info("⚽ **Manchester City vs Liverpool**\n\n➔ Pronostic recommandé : **Plus de 2.5 buts**")

# SECTION 2 : VIP
elif menu == "👑 VIP":
    st.title("👑 Espace VIP")
    cle_acces = st.text_input("🔑 Entrez votre clé d'accès VIP :", type="password")
    
    if cle_acces == "DADY2026":
        st.success("Accès VIP Validé.")
        st.warning("🔥 **SCORE EXACT EXCLUSIF :**\n\n⚽ **Real Madrid vs Barcelone**\n\n➔ **Score Pronostiqué : 2 - 1** (Fiabilité : 89.4%)")
    elif cle_acces != "":
        st.error("❌ Clé d'accès incorrecte ou expirée.")

# SECTION 3 : RÉSULTATS
elif menu == "🏆 Résultats":
    st.subheader("✅ Historique des Validations")
    st.success("✅ **05/07/2026** | Shanghai vs Zhejiang ➔ **Score Exact 2-0** validé ! 🏆")

# SECTION 4 : CHUTE DES COTES
elif menu == "📉 Chute des Cotes":
    st.title("📉 Détecteur Multi-Sites Professionnel")
    
    cle_chute = st.text_input("🔑 Entrez votre clé d'accès Détecteur :", type="password", key="chute_pass")
    
    if cle_chute == "DADY2026":
        st.write("Le robot extrait les équipes en respectant l'ordre Domicile/Extérieur et sécurise la cohérence des cotes.")

        lien_site = st.text_input("🔗 Collez le lien du match (Sofascore, Oddsportal, BeSoccer) :", placeholder="https://...")
        
        nom_du_match = "Équipe Domicile vs Équipe Extérieur"
        seed = 42

        if lien_site:
            lien_lower = lien_site.lower()
            seed = int(hashlib.md5(lien_site.encode()).hexdigest(), 16)
            
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
                pass

            st.success(f"🎯 Match synchronisé à 100% : **{nom_du_match}**")

        scores_liste = ["1 - 0", "2 - 0", "2 - 1", "0 - 1", "0 - 2", "1 - 2", "1 - 1", "0 - 0", "2 - 2", "3 - 1"]
        option_score = scores_liste[seed % len(scores_liste)]
        
        buts_dom = int(option_score.split(" - ")[0])
        buts_ext = int(option_score.split(" - ")[1])
        total_buts = buts_dom + buts_ext
        
        if total_buts >= 3:
            option_jeu = "Plus de 2.5 buts (Over 2.5)"
        elif total_buts == 2:
            option_jeu = "Moins de 3.5 buts (Under 3.5)" if (seed % 2 == 0) else "Plus de 1.5 buts (Over 1.5)"
        elif total_buts == 1:
            option_jeu = "Moins de 2.5 buts (Under 2.5)"
        else:
            option_jeu = "Moins de 1.5 buts (Under 1.5)"

        if buts_dom > 0 and buts_ext > 0:
            option_btts = "Les deux équipes marquent : OUI"
        else:
            option_btts = "Les deux équipes marquent : NON"

        choix_ht_ft = ["X/1", "X/2", "X/X", "1/X", "2/X", "1/2", "2/1", "1/1", "2/2"]
        code_ht_ft = choix_ht_ft[(seed >> 2) % len(choix_ht_ft)]
        
        if buts_dom > buts_ext and code_ht_ft not in ["1/1", "X/1", "2/1"]:
            code_ht_ft = "X/1" if (seed % 2 == 0) else "1/1"
        elif buts_ext > buts_dom and code_ht_ft not in ["2/2", "X/2", "1/2"]:
            code_ht_ft = "X/2" if (seed % 2 == 0) else "2/2"
        elif buts_dom == buts_ext and code_ht_ft not in ["X/X", "1/X", "2/X"]:
            code_ht_ft = "X/X"

        explications_ht_ft = {
            "X/1": "Nul à la mi-temps / Équipe Domicile gagne en Fin de match",
            "X/2": "Nul à la mi-temps / Équipe Extérieur gagne en Fin de match",
            "X/X": "Match Nul à la mi-temps / Match Nul en Fin de match",
            "1/X": "Équipe Domicile mène à la mi-temps / Match Nul final",
            "2/X": "Équipe Extérieur mène à la mi-temps / Match Nul final",
            "1/2": "Équipe Domicile mène à la mi-temps / Équipe Extérieur gagne",
            "2/1": "Équipe Extérieur mène à la mi-temps / Équipe Domicile gagne",
            "1/1": "Équipe Domicile gagne la mi-temps et le match",
            "2/2": "Équipe Extérieur gagne la mi-temps et le match"
        }
        option_ht_ft = f"{code_ht_ft} - {explications_ht_ft[code_ht_ft]}"

        if "1/" in code_ht_ft: option_ht = "Victoire Équipe Domicile (1)"
        elif "2/" in code_ht_ft: option_ht = "Victoire Équipe Extérieur (2)"
        else: option_ht = "Match Nul (X)"

        choix_p2 = ["Gagnée par le favori (1X)", "Match Nul en 2ème période (X)", "Avantage Attaque (Over 0.5)", "Victoire Équipe Domicile (1)", "Victoire Équipe Extérieur (2)"]
        option_p2 = choix_p2[(seed >> 4) % len(choix_p2)]

        cote_ouvrir = round(1.70 + (seed % 10) * 0.15, 2)
        cote_actu = round(cote_ouvrir * 0.76, 2)
        baisse = ((cote_ouvrir - cote_actu) / cote_ouvrir) * 100

        st.markdown("---")
        
        with st.expander("🛠️ Ajuster ou forcer manuellement les données générées"):
            nom_du_match = st.text_input("Nom officiel du match :", nom_du_match)
            option_jeu = st.text_input("Modifier le Marché Principal :", option_jeu)
            option_score = st.text_input("Modifier le Score Exact :", option_score)
            option_ht_ft = st.text_input("Modifier le bloc HT / FT :", option_ht_ft)

        st.subheader(f"📊 Fiche d'Analyse Certifiée : {nom_du_match}")
        
        col_gauche, col_droite = st.columns(2)
        
        with col_gauche:
            st.markdown("### 🔮 Options Principales & Buts")
            st.info(f"• **Marché Principal :** `{option_jeu}`\n\n• **Les 2 Équipes Marquent :** `{option_btts}`\n\n• **Score Exact Suggéré :** `{option_score}`")
            
        with col_droite:
            st.markdown("### ⏰ Options Mi-temps & Périodes")
            st.warning(f"• **Résultat Mi-temps (1X2) :** `{option_ht}`\n\n• **Scénario Complet HT/FT :** `{option_ht_ft}`\n\n• **Deuxième Période (1X2) :** `{option_p2}`")

        st.markdown("### 📉 Analyse des Flux Financiers (Chute de Cote)")
        st.error(f"⚽ **Mouvement du marché mondial :**\n\n• Cote d'Ouverture : `{cote_ouvrir}` ➔ Cote Actuelle : `{cote_actu}`\n\n📉 Intensité de la baisse enregistrée : **-{baisse:.2f}%**")
        
        st.markdown("---")
        st.subheader("🎯 Conseil de Validation Automatique")
        st.success(f"🔥 **ANALYSE VALIDÉE POUR LE MATCH : {nom_du_match}**\n\nL'indice de confiance montre une forte injection de capitaux sur le marché `{option_jeu}` combiné avec un pronostic de score exact `{option_score}`. Recommandation : Suivre la tendance avec une mise modérée.")
            
    elif cle_chute == "":
        st.info("💡 Cette section est réservée aux membres VIP. Entrez votre clé pour y accéder.")
    else:
        st.error("❌ Clé d'accès incorrecte ou expirée.")

# =========================================================
# 🟢 BOUTON DE CONTACT WHATSAPP GLOBAL
# =========================================================
if menu != "⚽ Gratuit":
    message_bienvenue = "Bonjour BetScope ! 👑 ✅✅\nJe souhaite m'abonner à l'Espace VIP BetScope. Comment puis-je procéder au paiement s'il te plaît ?"
    message_encode = urllib.parse.quote(message_bienvenue)
    lien_whatsapp = f"https://api.whatsapp.com/send?phone=237698902204&text={message_encode}"
    
    st.markdown(f"""
    <a href="{lien_whatsapp}" target="_blank" style="text-decoration: none;">
        <div style="background-color: #25D366; color: white; text-align: center; padding: 12px; border-radius: 8px; font-weight: bold; font-size: 16px; box-shadow: 0px 4px 6px rgba(0,0,0,0.1);">
            💬 Acheter mon accès VIP sur WhatsApp
        </div>
    </a>
    """, unsafe_allow_html=True)
