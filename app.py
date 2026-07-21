def analyse_ia(donnees):

    try:
        model = genai.GenerativeModel(
            "gemini-1.5-flash"
        )

        # Conversion propre des données API
        import json

        texte_donnees = json.dumps(
            donnees,
            indent=2,
            ensure_ascii=False
        )

        prompt = f"""
Tu es BetScope Pro, un analyste football professionnel.

Voici les données API-Football :

{texte_donnees[:12000]}


Fais une analyse complète :

1. Forme des équipes
2. Historique H2H
3. Blessures
4. Attaque et défense
5. Over/Under 1.5 buts
6. Over/Under 2.5 buts
7. BTTS Oui/Non
8. Mi-temps probable
9. Deuxième mi-temps
10. Score exact probable
11. Conseil de pari avec niveau de confiance

Réponds uniquement en français.
"""

        resultat = model.generate_content(
            prompt
        )

        if resultat.text:
            return resultat.text
        else:
            return "❌ Gemini n'a retourné aucun texte."


    except Exception as e:
        return f"❌ Erreur Gemini : {str(e)}"if st.button("🚀 Lancer Analyse"):

    with st.spinner("Collecte des données..."):

        donnees = {
            "Equipe 1": t1,
            "Equipe 2": t2
        }

        st.success("✅ Données API reçues")

    with st.spinner("🤖 Gemini prépare l'analyse..."):

        rapport = analyse_ia(donnees)

    st.subheader("📊 Rapport VIP")

    st.write(rapport)
