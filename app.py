# ==========================================
# BETSCOPE PRO AI - API FOOTBALL + GEMINI
# ==========================================

import os
import requests
import streamlit as st
import google.generativeai as genai
from gtts import gTTS
import base64


# ============================
# CLÉS API
# ============================

SPORT_API_KEY =("getenv118e42213a9421c97067fe8a2c992a92")
GEMINI_API_KEY =("AQAb8RN6Lf-C7eoe0oqQNSvH6ht1yvF9HAedhHrpTIm8mFsRFvZA")

genai.configure(api_key=GEMINI_API_KEY)


API_URL = "https://v3.football.api-sports.io"


HEADERS = {
    "x-apisports-key": SPORT_API_KEY
}



# ============================
# RECHERCHER UNE EQUIPE
# ============================

def chercher_equipe(nom):

    url = f"{API_URL}/teams"

    params = {
        "search": nom
    }

    r = requests.get(
        url,
        headers=HEADERS,
        params=params
    )

    return r.json()



# ============================
# DERNIERS MATCHS
# ============================

def derniers_matchs(team_id):

    url = f"{API_URL}/fixtures"

    params = {
        "team": team_id,
        "last": 10
    }

    r = requests.get(
        url,
        headers=HEADERS,
        params=params
    )

    return r.json()



# ============================
# BLESSURES
# ============================

def blessures(team_id):

    url = f"{API_URL}/injuries"

    params = {
        "team": team_id
    }

    r = requests.get(
        url,
        headers=HEADERS,
        params=params
    )

    return r.json()



# ============================
# H2H
# ============================

def historique_h2h(team1, team2):

    url = f"{API_URL}/fixtures/headtohead"

    params = {
        "h2h": f"{team1}-{team2}",
        "last": 10
    }

    r = requests.get(
        url,
        headers=HEADERS,
        params=params
    )

    return r.json()



# ============================
# GEMINI ANALYSE VIP
# ============================

def analyse_ia(donnees):

    model = genai.GenerativeModel(
        "gemini-1.5-flash"
    )


    prompt = f"""

Tu es BetScope Pro, expert en analyse football.

Analyse ces données réelles API-Football :

{donnees}


Donne un rapport professionnel :

📌 Forme récente
📌 H2H
📌 Blessures
📌 Statistiques attaque/défense
📌 Over 1.5
📌 Over 2.5
📌 Under
📌 BTTS
📌 Mi-temps probable
📌 Deuxième mi-temps
📌 Score exact probable
📌 Risques du pari


Réponds en français.
Donne un niveau de confiance mais aucune garantie.
"""


    resultat = model.generate_content(prompt)

    return resultat.text



# ============================
# AUDIO IA
# ============================

def audio_ia(texte):

    voix = gTTS(
        texte,
        lang="fr"
    )

    fichier="betscope.mp3"

    voix.save(fichier)


    with open(fichier,"rb") as f:
        audio = base64.b64encode(
            f.read()
        ).decode()


    return f"""
    <audio controls>
    <source src="data:audio/mp3;base64,{audio}">
    </audio>
    """



# ============================
# INTERFACE BETSCOPE PRO
# ============================

st.set_page_config(
    page_title="BetScope Pro",
    page_icon="👑"
)


st.title("👑 BetScope Pro")
st.write(
    "Analyse Football IA Premium"
)



equipe1 = st.text_input(
    "Equipe domicile"
)

equipe2 = st.text_input(
    "Equipe extérieur"
)



if st.button("🚀 Lancer Analyse"):

    with st.spinner(
        "Collecte des données..."
    ):

        t1 = chercher_equipe(equipe1)
        t2 = chercher_equipe(equipe2)


        st.write("Données récupérées")


        donnees = {
            "Equipe 1": t1,
            "Equipe 2": t2
        }


        rapport = analyse_ia(
            donnees
        )


        st.subheader(
            "📊 Rapport VIP"
        )

        st.write(
            rapport
        )


        lecteur = audio_ia(
            rapport
        )


        st.components.v1.html(
            lecteur,
            height=80
        )
