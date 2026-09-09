# ============================================================
# RODRIGUE PRO FOOTBALL AI — V10 ULTIMATE
# ============================================================

import math
import re
from datetime import date

import numpy as np
import pandas as pd
import requests
import streamlit as st


# ============================================================
# CONFIGURATION
# ============================================================

FOOTBALL_DATA_KEY = "ca5b8e71be93da1827e148ee1551a9b0"
SERPAPI_KEY = "6680e04a0cf677964822ad771410a129eec409d735f6e8536ecbaae276e9c7c6"

API_BASE = "https://api.football-data.org/v4"
SERP_URL = "https://serpapi.com/search.json"

COMPETITIONS = {
    "Premier League": "PL",
    "LaLiga": "PD",
    "Bundesliga": "BL1",
    "Serie A": "SA",
    "Ligue 1": "FL1",
    "Champions League": "CL",
    "Eredivisie": "DED",
    "Primeira Liga": "PPL",
    "Championship": "ELC",
    "Brasileirão": "BSA",
}

st.set_page_config(
    page_title="Rodrigue Pro Football AI V10",
    page_icon="⚽",
    layout="wide"
)

SESSION = requests.Session()

SESSION.headers.update({
    "User-Agent": "Rodrigue-Pro-Football-AI-V10"
})


# ============================================================
# OUTILS ET API
# ============================================================

def football_get(endpoint, params=None):
    try:
        response = SESSION.get(
            API_BASE + endpoint,
            headers={"X-Auth-Token": FOOTBALL_DATA_KEY},
            params=params or {},
            timeout=25
        )
        if response.status_code == 200:
            return response.json()
        return None
    except:
        return None


def fetch_matches(selected_date, competition_codes):
    # On récupère tous les matchs de la date sans bloquer par l'API
    params = {
        "dateFrom": selected_date.isoformat(),
        "dateTo": selected_date.isoformat()
    }

    data = football_get("/matches", params)
    if not data:
        return []

    matches = data.get("matches", [])

    # Filtrage local en Python pour contourner les restrictions du plan gratuit
    if competition_codes:
        matches = [
            m for m in matches 
            if m.get("competition", {}).get("code") in competition_codes
        ]

    return matches


# ============================================================
# INTERFACE STREAMLIT PRINCIPALE
# ============================================================

def main():
    st.title("⚽ Rodrigue Pro Football AI V10")
    st.markdown("### Moteur d'analyse prédictive et statistique de football")
    st.markdown("---")

    st.subheader("⚙️ Paramètres de recherche")

    selected_date = st.date_input(
        "Date des matchs",
        value=date.today()
    )

    selected_competitions = st.multiselect(
        "Compétitions",
        options=list(COMPETITIONS.keys()),
        default=["Champions League", "Premier League", "LaLiga"]
    )

    if st.button("🚀 CHERCHER LES MATCHS", type="primary", use_container_width=True):
        codes = [COMPETITIONS[c] for c in selected_competitions]

        with st.spinner("Recherche des matchs en cours..."):
            matches = fetch_matches(selected_date, codes)

        if not matches:
            st.warning("Aucun match trouvé pour cette date dans les compétitions sélectionnées.")
        else:
            st.success(f"{len(matches)} match(s) trouvé(s) !")
            for match in matches:
                home = match.get("homeTeam", {}).get("name", "Domicile")
                away = match.get("awayTeam", {}).get("name", "Extérieur")
                comp = match.get("competition", {}).get("name", "")
                utc = match.get("utcDate", "")

                st.markdown(f"---")
                st.markdown(f"🏆 **{comp}**")
                st.markdown(f"### {home} VS {away}")
                st.text(f"Heure (UTC) : {utc}")


if __name__ == "__main__":
    main()
