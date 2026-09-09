# ============================================================
# MATCHS — RÉCUPÉRATION ROBUSTE
# ============================================================

def fetch_matches(
    selected_date,
    competition_codes
):

    date_str = selected_date.isoformat()

    # --------------------------------------------------------
    # 1. Recherche avec les compétitions sélectionnées
    # --------------------------------------------------------

    params = {
        "dateFrom": date_str,
        "dateTo": date_str
    }

    if competition_codes:

        params["competitions"] = ",".join(
            competition_codes
        )

    data = football_get(
        "/matches",
        params
    )

    if data:

        matches = data.get(
            "matches",
            []
        )

        if matches:
            return matches

    # --------------------------------------------------------
    # 2. Recherche de secours sans filtre
    # --------------------------------------------------------

    fallback_params = {
        "dateFrom": date_str,
        "dateTo": date_str
    }

    fallback_data = football_get(
        "/matches",
        fallback_params
    )

    if not fallback_data:
        return []

    all_matches = fallback_data.get(
        "matches",
        []
    )

    # --------------------------------------------------------
    # 3. Filtrer localement les compétitions choisies
    # --------------------------------------------------------

    if competition_codes:

        selected_matches = []

        for match in all_matches:

            competition = match.get(
                "competition",
                {}
            )

            code = competition.get(
                "code"
            )

            if code in competition_codes:

                selected_matches.append(
                    match
                )

        if selected_matches:
            return selected_matches

    # --------------------------------------------------------
    # 4. Aucun match dans les compétitions choisies
    # --------------------------------------------------------

    if all_matches:

        available_competitions = sorted(
            set(
                match.get(
                    "competition",
                    {}
                ).get(
                    "name",
                    "Inconnue"
                )
                for match in all_matches
            )
        )

        st.info(
            "ℹ️ Aucun match dans les compétitions "
            "sélectionnées pour cette date."
        )

        st.write(
            "**Compétitions disponibles ce jour :**"
        )

        for competition in available_competitions:

            st.write(
                f"• {competition}"
            )

    return []
