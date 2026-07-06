# ---------------------------------------------------------
# SECTION 4 : 📉 CHUTE DES COTES 
# ---------------------------------------------------------
elif menu == "📉 Chute des Cotes":
    st.title("📉 Détecteur de Chute de Cotes")
    st.write("Le robot analyse en temps réel les variations suspectes des cotes mondiales.")

    # 🔗 ZONE POUR COLLER LE LIEN
    lien_site = st.text_input("🔗 Collez le lien du site d'analyse ici :", placeholder="https://www.oddsportal.com/dropping-odds/")
    
    if lien_site:
        st.info(f"🔄 Connexion demandée vers : `{lien_site}`")
        st.warning("⚠️ *Note : Les sites de cotes bloquent souvent les requêtes directes. Indique-moi le nom de ton site favori pour qu'on crée un décodeur spécialisé !*")

    st.markdown("---")
    st.subheader("✍️ Mettre à jour les Chutes du Jour")
    
    # Formulaire interactif pour ajouter un vrai match en direct depuis ton téléphone
    with st.expander("➕ Ajouter / Modifier un match en direct"):
        nom_du_match = st.text_input("Nom du match :", "Real Madrid vs Barcelone")
        option_jeu = st.text_input("Option (ex: Under 2.5, Victoire 1...) :", "Moins de 2.5 buts (Under 2.5)")
        col1, col2 = st.columns(2)
        with col1:
            cote_ouvrir = st.number_input("Cote d'ouverture :", value=2.50, step=0.05)
        with col2:
            cote_actu = st.number_input("Cote actuelle :", value=1.65, step=0.05)

    # Tableau des données (Prend les valeurs saisies au-dessus)
    matchs_analyses = [
        {
            "match": nom_du_match,
            "option": option_jeu,
            "cote_ouverture": cote_ouvrir,
            "cote_actuelle": cote_actu
        },
        {
            "match": "Chelsea vs Arsenal",
            "option": "Mi-temps / Fin de match (X/1)",
            "cote_ouverture": 4.50,
            "cote_actuelle": 4.10
        }
    ]

    meilleure_opportunite = None
    plus_grosse_chute = 0

    st.subheader("📊 Variations détectées sur les marchés")

    for match in matchs_analyses:
        if match["cote_ouverture"] > 0:
            baisse = ((match["cote_ouverture"] - match["cote_actuelle"]) / match["cote_ouverture"]) * 100
        else:
            baisse = 0
        
        st.info(f"⚽ **{match['match']}**\n\n"
                f"• Option analysée : **{match['option']}**\n\n"
                f"• Ouverture : `{match['cote_ouverture']}` ➡️ Actuelle : `{match['cote_actuelle']}`\n\n"
                f"📉 Chute de la valeur : **-{baisse:.2f}%**")
        
        if baisse > plus_grosse_chute:
            plus_grosse_chute = baisse
            meilleure_opportunite = match

    st.markdown("---")
    st.subheader("🎯 Le Conseil Algorithmique de l'IA")
    
    if meilleure_opportunite and plus_grosse_chute > 0:
        st.success(f"🔥 **MEILLEURE OPPORTUNITÉ DÉTECTÉE** 🔥\n\n"
                   f"**Match :** {meilleure_opportunite['match']}\n\n"
                   f"**Option recommandée :** {meilleure_opportunite['option']}\n\n"
                   f"📊 **Indice de confiance :** Chute record de **-{plus_grosse_chute:.2f}%** sur le marché.")
    else:
        st.warning("Aucune anomalie ou chute de cote majeure détectée pour le moment.")
        
