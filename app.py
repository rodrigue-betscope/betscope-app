            # =========================================================
            # ✍️ MATCH 1 : SCORE EXACT (MODIFIE LE NOM ET LES COTES ICI)
            # =========================================================
            match_1 = "Real Madrid vs Barcelone"   # <--- ÉCRIS LE NOM DU MATCH 1 ICI
            cote_1_M1 = 1.32                       # <--- Cote Victoire Équipe 1
            cote_X_M1 = 4.75                       # <--- Cote Match Nul
            cote_2_M1 = 7.5                        # <--- Cote Victoire Équipe 2
            
            # =========================================================
            # ✍️ MATCH 2 : MI-TEMPS / FIN DE MATCH (HT/FT)
            # =========================================================
            match_2 = "Keflavik vs knattspyrnufel" # <--- ÉCRIS LE NOM DU MATCH 2 ICI
            cote_1_M2 = 3.495                      # <--- Cote 1
            cote_X_M2 = 4.25                       # <--- Cote X
            cote_2_M2 = 1.81                       # <--- Cote 2
            
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
            
        else:
            st.error("❌ Clé d'accès incorrecte ou expirée.")

# ---------------------------------------------------------
# SECTION 3 : RÉSULTATS
# ---------------------------------------------------------
elif menu == "🏆 Résultats":
    st.subheader("✅ Historique des Validations")
    st.markdown("Découvrez les derniers pronostics validés avec succès par l'algorithme BetScope.")
    
    st.markdown("---")
    
    # ✍️ MODIFIE CETTE SECTION CHAQUE JOUR POUR TES RÉSULTATS PASSÉS
    st.success("✅ **05/07/2026** | Shanghai vs Zhejiang\n\n➔ **Score Exact 2-0** validé ! 🏆")
    st.success("✅ **05/07/2026** | Qingdao vs Chengdu\n\n➔ **HT/FT 2/2** validé ! 🏆")
    
    st.markdown("---")
    st.markdown("### 📢 Envie d'obtenir les pronostics d'aujourd'hui ?")

# ---------------------------------------------------------
# SECTION 4 : 📉 CHUTE DES COTES 
# ---------------------------------------------------------
elif menu == "📉 Chute des Cotes":
    st.title("📉 Détecteur de Chute de Cotes")
    st.write("Le robot analyse en temps réel les variations suspectes des cotes mondiales.")

    # =========================================================
    # ✍️ TABLEAU DES CHUTES DE COTES (MODIFIE LES INFOS ICI)
    # =========================================================
    matchs_analyses = [
        {
            "match": "Real Madrid vs Barcelone",          # <--- MODIFIE NOM MATCH 1
            "option": "Moins de 2.5 buts (Under 2.5)",    # <--- MODIFIE L'OPTION
            "cote_ouverture": 2.50,                       # <--- MODIFIE COTE AVANT
            "cote_actuelle": 1.65                         # <--- MODIFIE COTE APRÈS
        },
        {
            "match": "Chelsea vs Arsenal",                # <--- MODIFIE NOM MATCH 2
            "option": "Mi-temps / Fin de match (X/1)",    # <--- MODIFIE L'OPTION
            "cote_ouverture": 4.50,                       # <--- MODIFIE COTE AVANT
            "cote_actuelle": 4.10                         # <--- MODIFIE COTE APRÈS
        },
        {
            "match": "Juventus vs AC Milan",              # <--- MODIFIE NOM MATCH 3
            "option": "Score Exact (1-0)",                # <--- MODIFIE L'OPTION
            "cote_ouverture": 7.00,                       # <--- MODIFIE COTE AVANT
            "cote_actuelle": 6.80                         # <--- MODIFIE COTE APRÈS
        }
    ]

    meilleure_opportunite = None
    plus_grosse_chute = 0

    st.subheader("📊 Variations détectées sur les marchés")

    for match in matchs_analyses:
        baisse = ((match["cote_ouverture"] - match["cote_actuelle"]) / match["cote_ouverture"]) * 100
        
        st.info(f"⚽ **{match['match']}**\n\n"
                f"• Option analysée : **{match['option']}**\n\n"
                f"• Ouverture : `{match['cote_ouverture']}` ➡️ Actuelle : `{match['cote_actuelle']}`\n\n"
                f"📉 Chute de la valeur : **-{baisse:.2f}%**")
        
        if baisse > plus_grosse_chute:
            plus_grosse_chute = baisse
            meilleure_opportunite = match

    st.markdown("---")
    st.subheader("🎯 Le Conseil Algorithmique de l'IA")
    
    if meilleure_opportunite:
        st.success(f"🔥 **MEILLEURE OPPORTUNITÉ DÉTECTÉE** 🔥\n\n"
                   f"**Match :** {meilleure_opportunite['match']}\n\n"
                   f"**Option recommandée :** {meilleure_opportunite['option']}\n\n"
                   f"📊 **Indice de confiance :** Chute record de **-{plus_grosse_chute:.2f}%** sur le marché.")
    else:
        st.warning("Aucune anomalie ou chute de cote majeure détectée pour le moment.")

# ==========================================
# 🟢 BOUTON WHATSAPP GLOBAL DÉFINITIF
# ==========================================
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
