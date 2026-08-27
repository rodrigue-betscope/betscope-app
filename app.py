if st.button("🚀 ANALYSER LES VRAIS MATCHS", type="primary", use_container_width=True):
    try:
        # Utilisation de la date UTC pour correspondre exactement aux filtres de l'API v4
        date_string = selected_date.isoformat()
        
        with st.spinner("🔎 Récupération des matchs..."):
            matches = get_matches_for_date(date_string, selected_competitions)

        # On garde les matchs à venir ou en cours pour être sûr de ne rien rater
        valid_statuses = ["TIMED", "SCHEDULED", "LIVE", "IN_PLAY", "PAUSED"]
        filtered_matches = [m for m in matches if m.get("status") in valid_statuses]

        # Si l'API retourne du vide sur le filtre strict, on essaie d'élargir aux matchs du jour globalement
        if not filtered_matches and matches:
            filtered_matches = [m for m in matches if m.get("status") not in ["CANCELLED", "POSTPONED"]]

        if not filtered_matches:
            st.error(f"❌ Aucun match disponible pour la date du {selected_date} dans les compétitions sélectionnées.")
            st.info("💡 **Astuce :** Vérifie si les championnats choisis ont des matchs programmés aujourd'hui, ou essaie de sélectionner d'autres ligues dans la barre latérale.")
            st.stop()

        matches = filtered_matches[:max_matches]
        results = []
        progress = st.progress(0)
        status_text = st.empty()

        for index, match in enumerate(matches):
            home = match.get("homeTeam", {}).get("name", "?")
            away = match.get("awayTeam", {}).get("name", "?")
            status_text.write(f"🔎 Analyse : {home} — {away}")

            try:
                result = analyze_match(match, date_string)
                if result:
                    results.append(result)
            except Exception:
                pass

            progress.progress((index + 1) / len(matches))

        status_text.empty()

        if not results:
            st.error("❌ Impossible de calculer les probabilités (historique insuffisant pour ces équipes sur l'API).")
            st.stop()

        results.sort(key=lambda x: x["selection_score"], reverse=True)
        top3 = results[:3]

        st.success(f"🏆 {len(results)} matchs analysés avec succès !")

        for rank, result in enumerate(top3, 1):
            ranked = result["probabilities"]
            best_market, best_prob = ranked[0]
            second_market, second_prob = ranked[1]
            third_market, third_prob = ranked[2]

            st.markdown("---")
            st.subheader(f"🏆 #{rank} {result['home']} — {result['away']}")
            st.caption(f"🏆 {result['competition']}")

            c1, c2, c3 = st.columns(3)
            c1.metric("🎯 MT/FT", best_market)
            c2.metric("📊 Probabilité", f"{best_prob * 100:.2f}%")
            c3.metric("🧠 Qualité", f"{result['quality']:.0f}%")

            c4, c5 = st.columns(2)
            c4.metric("⚽ Buts dom. attendus", f"{result['lh']:.2f}")
            c5.metric("⚽ Buts ext. attendus", f"{result['la']:.2f}")

            st.write(f"🥈 Alternative : **{second_market}** — {second_prob * 100:.2f}%")
            st.write(f"🥉 Alternative : **{third_market}** — {third_prob * 100:.2f}%")

            table = pd.DataFrame(
                [{"Rang": i + 1, "MT/FT": m, "Probabilité": f"{p * 100:.2f}%"} for i, (m, p) in enumerate(ranked)]
            )
            st.dataframe(table, hide_index=True, use_container_width=True)

        st.markdown("---")
        st.warning("⚠️ Les pourcentages sont des estimations statistiques et ne garantissent pas un gain à 100%.")
        st.info("💯 Conseil : Privilégie les championnats majeurs avec beaucoup d'historique.")

    except Exception as e:
        st.error(f"❌ Une erreur est survenue : {e}")
