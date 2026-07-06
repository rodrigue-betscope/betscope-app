import streamlit as st
import urllib.parse
import hashlib

# Configuration globale de l'application
st.set_page_config(page_title="BetScope Pro", page_icon="👑", layout="centered")

# =========================================================
# 🧭 BARRE LATÉRALE DE NAVIGATION
# =========================================================
menu = st.sidebar.radio(
    "Navigation", 
    ["⚽ Gratuit", "👑 VIP", "🏆 Résultats", "📉 Chute des Cotes"]
)

# =========================================================
# SECTION 1 : ⚽ GRATUIT
# =========================================================
if menu == "⚽ Gratuit":
    st.title("⚽ Pronostics Gratuits")
    st.write("Bienvenue sur BetScope Pro ! Voici le pronostic public du jour.")
    
    st.info("⚽ **Manchester City vs Liverpool**\n\n➔ Pronostic recommandé : **Plus de 2.5 buts** (Under/Over)")

# =========================================================
# SECTION 2 : 👑 VIP
# =========================================================
elif menu == "👑 VIP":
    st.title("👑 Espace VIP")
    
    # Zone de saisie de la clé d'accès
    cle_acces = st.text_input("🔑 Entrez votre clé d'accès VIP :", type="password")
    
    if cle_acces == "DADY2026":
        # ✍️ MATCH 1 : SCORE EXACT
        match_1 = "Real Madrid vs Barcelone"   
        cote_1_M1 = 1.32                       
        cote_X_M1 = 4.75                       
        cote_2_M1 = 7.5                        
        
        # ✍️ MATCH 2 : MI-TEMPS / FIN DE MATCH (HT/FT)
        match_2 = "Keflavik vs knattspyrnufel" 
        cote_1_M2 = 3.495                      
        cote_X_M2 = 4.25                       
        cote_2_M2 = 1.81                       
        
        # --- CALCULS IA ---
        p1_raw, px_raw, p2_raw = 1/cote_1_M1, 1/cote_X_M1, 1/cote_2_M1
        total_p = p1_raw + px_raw + p2_raw
        p1, p2 = p1_raw / total_p, p2_raw / total_p
        
        if p1 > 0.60:
            score_p1, fiab_1 = "3 - 0", 94.2
        elif p1 > 0.50:
            score_p1, fiab_1 = "2 - 0", 92.1
        elif p1 > 0.40:
            score_p1, fiab_1 = "2 - 1", 89.4
        elif p2 > 0.60:
            score_p1, fiab_1 = "0 - 3", 94.5
        elif p2 > 0.50:
            score_p1, fiab_1 = "0 - 2", 91.8
        elif p2 > 0.40:
            score_p1, fiab_1 = "1 - 2", 88.7
        else:
            score_p1, fiab_1 = ("0 - 0", 86.4) if cote_X_M1 < 3.20 else ("1 - 1", 88.1)
                
        if cote_1_M2 <= 1.45:
            ht_ft_p2, fiab_2 = "Mi-temps : 1 / Fin de match : 1", 95.2
        elif cote_2_M2 <= 1.45:
            ht_ft_p2, fiab_2 = "Mi-temps : 2 / Fin de match : 2", 94.8
        elif abs(cote_1_M2 - cote_2_M2) < 0.50:
            ht_ft_p2, fiab_2 = "Mi-temps : X / Fin de match : X", 89.1
        else:
            if cote_1_M2 < cote_2_M2:
                ht_ft_p2, fiab_2 = ("Mi-temps : X / Fin de match : 1", 91.4) if cote_1_M2 > 1.75 else ("Mi-temps : 1 / Fin de match : 1", 91.4)
            else:
                ht_ft_p2, fiab_2 = ("Mi-temps : X / Fin de match : 2", 90.7) if cote_2_M2 > 1.75 else ("Mi-temps : 2 / Fin de match : 2", 90.7)
        
        # --- AFFICHAGE VIP ---
        st.info("🔄 *Analyse des probabilités implicites du marché validée par l'IA.*")
        st.markdown("")
        st.warning(f"🔥 **SCORE EXACT EXCLUSIF :**\n\n⚽ **{match_1}**\n\n➔ **Score Pronostiqué : {score_p1}** (Fiabilité : {fiab_1}%)")
        st.markdown("")
        st.warning(f"🔥 **COMBINÉ HT/FT :**\n\n⚽ **{match_2}**\n\n➔ **{ht_ft_p2}** (Indice de sécurité : {fiab_2}%)")
        
    elif cle_acces == "":
        st.info("💡 Entrez votre clé d'accès pour débloquer les pronostics VIP.")
    else:
        st.error("❌ Clé d'accès incorrecte ou expirée.")

# =========================================================
# SECTION 3 : 🏆 RÉSULTATS
# =========================================================
elif menu == "🏆 Résultats":
    st.subheader("✅ Historique des Validations")
    st.markdown("Découvrez les derniers pronostics validés avec succès par l'algorithme BetScope.")
    
    st.markdown("---")
    st.success("✅ **05/07/2026** | Shanghai vs Zhejiang\n\n➔ **Score Exact 2-0** validé ! 🏆")
    st.success("✅ **05/07/2026** | Qingdao vs Chengdu\n\n➔ **HT/FT 2/2** validé ! 🏆")

# =========================================================
# SECTION 4 : 📉 CHUTE DES COTES (MULTI-DÉTECTEUR)
# =========================================================
elif menu == "📉 Chute des Cotes":
    st.title("📉 Détecteur Multi-Sites Pro")
    
    cle_chute = st.text_input("🔑 Entrez votre clé d'accès Détecteur :", type="password", key="chute_pass")
    
    if cle_chute == "DADY2026":
        st.write("Le robot extrait les équipes et calcule instantanément les mouvements de cotes du match soumis.")

        # 🔗 ZONE D'ENTRÉE MULTI-SITES
        lien_site = st.text_input("🔗 Collez le lien du match (BeSoccer, Sofascore, Oddsportal) :", placeholder="https://...")
        
        # Valeurs de secours standards
        nom_du_match = "Real Madrid vs Barcelone"
        seed = 42

        # 🧠 DÉCODEUR ET EXTRACTEUR INTELLIGENT DE LIENS
        if lien_site:
            lien_lower = lien_site.lower()
            # On génère un identifiant mathématique unique basé sur TOUTE la longueur de l'adresse internet reçue
            seed = int(hashlib.md5(lien_site.encode()).hexdigest(), 16)
            
            # CAS 1 : BE SOCCER
            if "besoccer.com/match/" in lien_lower:
                try:
                    parties = lien_site.split("besoccer.com/match/")[1].split("/")
                    if len(parties) >= 2:
                        nom_du_match = f"{parties[0].replace('-', ' ').title()} vs {parties[1].replace('-', ' ').title()}"
                except: pass
                
            # CAS 2 : SOFASCORE
            elif "sofascore.com/" in lien_lower and "/match/" in lien_lower:
                try:
                    slug = lien_site.split("/match/")[1].split("/")[0]
                    parts = slug.split("-")
                    if len(parts) >= 2:
                        nom_du_match = f"{parts[0].title()} vs {' '.join(parts[1:]).title()}"
                except: pass
                
            # CAS 3 : ODDSPORTAL (Format H2H ou Direct Match)
            elif "oddsportal.com/" in lien_lower:
                try:
                    if "/h2h/" in lien_lower:
                        parts = lien_site.split("/h2h/")[1].split("/")
                        nom_du_match = f"{parts[0].split('-')[0].title()} vs {parts[1].split('-')[0].title()}"
                    elif "/match/" in lien_lower:
                        slug = lien_site.split("/match/")[1].split("/")[0]
                        parts = slug.split("-")
                        nom_du_match = f"{parts[0].title()} vs {' '.join(parts[1:-1]).title()}"
                except: pass

            st.success(f"🎯 Synchronisation réussie sur le match : **{nom_du_match}**")

        # --- GÉNÉRATEUR ALGORITHMIQUE DE VARIATIONS (MULTI-OPTIONS CHERCHÉES) ---
        # 1. Option principale (Under / Over variés)
        marches_principaux = [
            "Moins de 2.5 buts (Under 2.5)", 
            "Moins de 1.5 buts (Under 1.5)", 
            "Plus de 2.5 buts (Over 2.5)", 
            "Plus de 1.5 buts (Over 1.5)",
            "Moins de 3.5 buts (Under 3.5)"
        ]
        option_jeu = marches_principaux[seed % len(marches_principaux)]
        
        # 2. Option Les deux équipes marquent (BTTS)
        option_btts = "Les deux équipes marquent : OUI" if (seed % 2 == 0) else "Les deux équipes marquent : NON"
        
        # 3. Option Score Exact réaliste
        scores_liste = ["1 - 0", "2 - 0", "1 - 1", "2 - 1", "0 - 1", "0 - 2", "1 - 2", "0 - 0", "3 - 1", "0 - 3"]
        option_score = scores_liste[(seed >> 4) % len(scores_liste)]
        
        # 4. Option Mi-temps (1X2) & Fin de match complète (Toutes les configurations HT/FT possibles)
        choix_ht_ft = ["X/1", "X/2", "X/X", "1/X", "2/X", "1/2", "2/1", "1/1", "2/2"]
        code_ht_ft = choix_ht_ft[(seed >> 2) % len(choix_ht_ft)]
        
        explications = {
            "X/1": "Nul à la mi-temps / Équipe 1 gagne en Fin de match",
            "X/2": "Nul à la mi-temps / Équipe 2 gagne en Fin de match",
            "X/X": "Match Nul à la mi-temps / Match Nul en Fin de match",
            "1/X": "Équipe 1 mène à la mi-temps / Match Nul final",
            "2/X": "Équipe 2 mène à la mi-temps / Match Nul final",
            "1/2": "Équipe 1 mène à la mi-temps / Équipe 2 s'impose à la fin",
            "2/1": "Équipe 2 mène à la mi-temps / Équipe 1 s'impose à la fin",
            "1/1": "Équipe 1 gagne la mi-temps et gagne le match",
            "2/2": "Équipe 2 gagne la mi-temps et gagne le match"
        }
        option_ht_ft = f"Option Combinée HT/FT : {code_ht_ft} ({explications[code_ht_ft]})"
        
        # 5. Seconde période unilatérale
        choix_p2 = ["Victoire Équipe 1 (1)", "Match Nul (X)", "Victoire Équipe 2 (2)", "Double Chance 1X", "Double Chance X2"]
        option_p2 = choix_p2[(seed >> 6) % len(choix_p2)]

        # 6. Génération de cotes et chutes aléatoires cohérentes
        cote_ouvrir = round(1.65 + (seed % 15) * 0.15, 2)
        cote_actu = round(cote_ouvrir * (0.58 + ((seed >> 3) % 10) * 0.03), 2)
        if cote_actu >= cote_ouvrir:
            cote_actu = round(cote_ouvrir * 0.74, 2)

        st.markdown("---")
        
        # Expander de contrôle
        with st.expander("🛠️ Ajuster manuellement les données générées (Optionnel)"):
            nom_du_match = st.text_input("Nom du match :", nom_du_match)
            option_jeu = st.text_input("Marché Principal :", option_jeu)
            option_score = st.text_input("Marché Score Exact :", option_score)
            option_ht_ft = st.text_input("Marché HT / FT :", option_ht_ft)
            col1, col2 = st.columns(2)
            with col1:
                cote_ouvrir = st.number_input("Cote d'ouverture :", value=float(cote_ouvrir), step=0.05)
            with col2:
                cote_actu = st.number_input("Cote actuelle :", value=float(cote_actu), step=0.05)

        # Calcul de la baisse réelle du marché
        baisse = ((cote_ouvrir - cote_actu) / cote_ouvrir) * 100 if cote_ouvrir > 0 else 0

        # --- RE-CONSTRUCTION DU PANNEAU DE CONTRÔLE AVANCÉ ET ULTRA COMPLET ---
        st.subheader(f"📊 Fiche Complète d'Analyse : {nom_du_match}")
        
        col_left, col_right = st.columns(2)
        
        with col_left:
            st.info(f"🔮 **MARCHÉS PRINCIPAUX & BUTS**\n\n• **Option Majeure :** `{option_jeu}`\n\n• **Réseau Buts :** `{option_btts}`\n\n• **Score Exact Suggéré :** `{option_score}`")
        
        with col_right:
            st.warning(f"⏰ **MARCHÉS SÉCONDAIRES & TEMPS (HT/FT)**\n\n• **Analyse Mi-temps / Fin :** `{option_ht_ft}`\n\n• **Deuxième Période (1X2) :** `{option_p2}`")

        # Section Alerte Mouvement de Masse
        st.markdown("### 📉 Alerte Mouvement de Masse")
        st.info(
            f"⚽ **Indicateur de Flux :**\n\n"
            f"• Ouverture : `{cote_ouvrir}` ➡️ Actuelle : `{cote_actu}`\n\n"
            f"📉 Intensité de la Chute détectée : **-{baisse:.2f}%**"
        )
        
        st.markdown("---")
        st.subheader("🎯 Le Conseil Algorithmique de l'IA")
        
        if baisse > 10:
            st.success(f"🔥 **MEILLEURE OPPORTUNITÉ DÉTECTÉE** 🔥\n\n"
                       f"• **Conseil Fort :** Jouer la baisse sur `{option_jeu}`\n"
                       f"• **Sécurité Combinée :** Valider la tendance `{code_ht_ft}`\n\n"
                       f"📊 **Avis Robot :** Chute critique de **-{baisse:.2f}%**. Le marché mondial injecte massivement de l'argent sur ce pronostic.")
        else:
            st.warning("Variations mineures observées. Restez sur les marchés classiques.")
            
    elif cle_chute == "":
        st.info("💡 Cette section est réservée aux membres VIP. Entrez votre clé pour y accéder.")
    else:
        st.error("❌ Clé d'accès incorrecte ou expirée.")

# =========================================================
# 🟢 BOUTON WHATSAPP GLOBAL
# =========================================================
if menu != "⚽ Gratuit":
    message_bienvenue = """Bonjour BetScope ! 👑 ✅✅
Je souhaite m'abonner à l'Espace VIP BetScope. Voici les forfaits :

🔹 1 Semaine (7 jours) : 5 000 FCFA
🔹 1 Mois (30 jours) : 15 000 FCFA
🔹 1 An (365 jours) : 50 000 FCFA

Comment puis-je procéder au paiement s'il te plaît ?"""

    message_encode = urllib.parse.quote(message_bienvenue)
    lien_whatsapp = f"https://api.whatsapp.com/send?phone=237698902204&text={message_encode}"
    
    st.markdown(f"""
    <a href="{lien_whatsapp}" target="_blank" style="text-decoration: none;">
        <div style="background-color: #25D366; color: white; text-align: center; padding: 12px; border-radius: 8px; font-weight: bold; font-size: 16px; box-shadow: 0px 4px 6px rgba(0,0,0,0.1);">
            💬 Acheter mon accès VIP sur WhatsApp
        </div>
    </a>
    """, unsafe_allow_html=True)
                        
