# ============================================================
# ANALYSE
# ============================================================

if st.button("🚀 ANALYSER LES VRAIS MATCHS", type="primary", use_container_width=True):

    try:

        date_string = selected_date.isoformat()

        with st.spinner("🔎 Récupération des vrais matchs..."):

            matches = get_matches_for_date(
                date_string,
                selected_competitions,
            )

        # Ne garder que les matchs à venir
        # ou non terminés.
        matches = [
            match
            for match in matches
            if match.get("status") not in [
                "FINISHED",
                "CANCELLED",
                "POSTPONED",
            ]
        ]

        if not matches:

            st.error(
                "❌ Aucun match disponible "
                "dans les compétitions sélectionnées."
            )

            st.stop()

        # Limite pour protéger le quota API
        matches = matches[:max_matches]

        st.success(
            f"✅ {len(matches)} vrais matchs trouvés."
        )

        results = []

        progress = st.progress(0)

        status_text = st.empty()

        for index, match in enumerate(matches):

            home = match.get("homeTeam", {}).get("name", "?")
            away = match.get("awayTeam", {}).get("name", "?")

            status_text.write(
                f"🔎 Analyse : {home} — {away}"
            )

            try:

                result = analyze_match(
                    match,
                    date_string,
                )

                if result:
                    results.append(result)

            except Exception as e:
                pass

            progress.progress(
                (index + 1) / len(matches)
            )

        status_text.empty()

        if not results:

            st.error(
                "❌ Impossible de calculer les probabilités. "
                "Les matchs sélectionnés ne possèdent peut-être "
                "pas assez d'historique accessible avec ta clé."
            )

            st.stop()

        # Classement
        results.sort(
            key=lambda x: x["selection_score"],
            reverse=True,
        )

        top3 = results[:3]

        st.success(
            f"🏆 {len(results)} matchs analysés."
        )

        # ====================================================
        # TOP 3
        # ====================================================

        for rank, result in enumerate(top3, 1):

            ranked = result["probabilities"]

            best_market, best_prob = ranked[0]
            second_market, second_prob = ranked[1]
            third_market, third_prob = ranked[2]

            st.markdown("---")

            st.subheader(
                f"🏆 #{rank} {result['home']} — {result['away']}"
            )

            st.caption(
                f"🏆 {result['competition']}"
            )

            c1, c2, c3 = st.columns(3)

            c1.metric(
                "🎯 MT/FT",
                best_market,
            )

            c2.metric(
                "📊 Probabilité",
                f"{best_prob * 100:.2f}%",
            )

            c3.metric(
                "🧠 Qualité",
                f"{result['quality']:.0f}%",
            )

            c4, c5 = st.columns(2)

            c4.metric(
                "⚽ Buts attendus domicile",
                f"{result['lh']:.2f}",
            )

            c5.metric(
                "⚽ Buts attendus extérieur",
                f"{result['la']:.2f}",
            )

            st.write(
                f"🥈 Alternative : **{second_market}** — {second_prob * 100:.2f}%"
            )

            st.write(
                f"🥉 Alternative : **{third_market}** — {third_prob * 100:.2f}%"
            )

            st.write(
                f"📚 Historique utilisé : {result['home_matches']} matchs domicile/équipe + {result['away_matches']} matchs équipe extérieure"
            )

            table = pd.DataFrame(
                [
                    {
                        "Rang": i + 1,
                        "MT/FT": market,
                        "Probabilité": f"{prob * 100:.2f}%",
                    }
                    for i, (market, prob) in enumerate(ranked)
                ]
            )

            st.dataframe(
                table,
                hide_index=True,
                use_container_width=True,
            )

        # ====================================================
        # AVERTISSEMENT
        # ====================================================

        st.markdown("---")

        st.warning(
            "⚠️ Les pourcentages sont des vrais probabilités "
            "par le modèle à partir des données "
            "réelles disponibles. Ils ne constituent en aucun cas "
            "une garantie de résultat à 100 %."
        )

        st.info(
            "💡 Conseil : plus l'historique disponible est "
            "important et récent, plus l'estimation statistique "
            "est exploitable."
        )

    except RuntimeError as e:
        st.error(str(e))

    except Exception as e:
        st.error(f"❌ Erreur : {e}")
