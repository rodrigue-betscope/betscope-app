"""
BetScope Stats - Analyse statistique reelle de matchs de football

Affiche des statistiques REELLES issues d'API-Football :
- Historique des confrontations (H2H)
- Forme recente des deux equipes
- Moyennes de buts marques / encaisses
- Blessures / absences si disponibles
- Cotes actuelles du marche (rapportees telles quelles)

Cet outil n'invente AUCUN pourcentage de victoire, score exact,
ou "conseil ferme". Il montre des faits pour que l'utilisateur se
fasse sa propre opinion.

CONFIGURATION REQUISE :
Ajoute dans les Secrets de Streamlit Cloud (jamais dans ce fichier) :

    API_FOOTBALL_KEY = "ta_vraie_cle_ici"

La cle s'obtient sur https://www.api-football.com (ou via RapidAPI).
"""

import base64
import requests
import streamlit as st
from gtts import gTTS

API_BASE_URL = "https://v3.football.api-sports.io"


def get_api_key():
    """Recupere la cle API depuis st.secrets, jamais codee en dur."""
    try:
        return st.secrets["14e0597ad77ade14b2e627c6cfc3242b"]
    except (KeyError, FileNotFoundError):
        return None


def api_football_request(endpoint, params=None):
    """Appelle l'API-Football et retourne le JSON, ou None en cas d'erreur."""
    api_key = get_api_key()
    if not api_key:
        return None

    headers = {"x-apisports-key": api_key}
    try:
        response = requests.get(
            f"{API_BASE_URL}/{endpoint}",
            headers=headers,
            params=params or {},
            timeout=15,
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        st.error(f"Erreur de connexion a l'API : {e}")
        return None


def chercher_equipe(nom_equipe):
    """Cherche une equipe par nom et retourne son ID + infos de base."""
    data = api_football_request("teams", {"search": nom_equipe})
    if not data or not data.get("response"):
        return None
    equipe = data["response"][0]["team"]
    return {"id": equipe["id"], "nom": equipe["name"], "logo": equipe["logo"]}


def recuperer_h2h(id_equipe_1, id_equipe_2, nb_matchs=5):
    """Recupere les derniers face-a-face reels entre deux equipes."""
    data = api_football_request(
        "fixtures/headtohead",
        {"h2h": f"{id_equipe_1}-{id_equipe_2}", "last": nb_matchs},
    )
    if not data or not data.get("response"):
        return []

    matchs = []
    for fixture in data["response"]:
        matchs.append({
            "date": fixture["fixture"]["date"][:10],
            "domicile": fixture["teams"]["home"]["name"],
            "exterieur": fixture["teams"]["away"]["name"],
            "score_domicile": fixture["goals"]["home"],
            "score_exterieur": fixture["goals"]["away"],
        })
    return matchs


def recuperer_forme_recente(id_equipe, nb_matchs=5):
    """Recupere les derniers resultats reels d'une equipe."""
    data = api_football_request(
        "fixtures", {"team": id_equipe, "last": nb_matchs}
    )
    if not data or not data.get("response"):
        return []

    matchs = []
    for fixture in data["response"]:
        est_domicile = fixture["teams"]["home"]["id"] == id_equipe
        buts_pour = (
            fixture["goals"]["home"] if est_domicile else fixture["goals"]["away"]
        )
        buts_contre = (
            fixture["goals"]["away"] if est_domicile else fixture["goals"]["home"]
        )
        if buts_pour is None or buts_contre is None:
            continue
        if buts_pour > buts_contre:
            resultat = "V"
        elif buts_pour < buts_contre:
            resultat = "D"
        else:
            resultat = "N"
        matchs.append({
            "date": fixture["fixture"]["date"][:10],
            "adversaire": (
                fixture["teams"]["away"]["name"]
                if est_domicile
                else fixture["teams"]["home"]["name"]
            ),
            "domicile": est_domicile,
            "buts_pour": buts_pour,
            "buts_contre": buts_contre,
            "resultat": resultat,
        })
    return matchs


def calculer_moyennes_buts(matchs):
    """Calcule les moyennes reelles de buts marques/encaisses sur une liste de matchs."""
    if not matchs:
        return None
    total_pour = sum(m["buts_pour"] for m in matchs)
    total_contre = sum(m["buts_contre"] for m in matchs)
    n = len(matchs)
    return {
        "moyenne_marques": round(total_pour / n, 2),
        "moyenne_encaisses": round(total_contre / n, 2),
        "victoires": sum(1 for m in matchs if m["resultat"] == "V"),
        "nuls": sum(1 for m in matchs if m["resultat"] == "N"),
        "defaites": sum(1 for m in matchs if m["resultat"] == "D"),
    }


def recuperer_cotes_marche(id_equipe_1, id_equipe_2):
    """Recupere les cotes actuelles du marche si un match a venir existe entre ces equipes."""
    data = api_football_request(
        "fixtures", {"team": id_equipe_1, "next": 5}
    )
    if not data or not data.get("response"):
        return None

    fixture_id = None
    for fixture in data["response"]:
        equipes = {fixture["teams"]["home"]["id"], fixture["teams"]["away"]["id"]}
        if id_equipe_2 in equipes:
            fixture_id = fixture["fixture"]["id"]
            break

    if not fixture_id:
        return None

    cotes_data = api_football_request("odds", {"fixture": fixture_id})
    if not cotes_data or not cotes_data.get("response"):
        return None

    try:
        bookmaker = cotes_data["response"][0]["bookmakers"][0]
        marche_1x2 = next(
            (b for b in bookmaker["bets"] if b["name"] == "Match Winner"), None
        )
        if not marche_1x2:
            return None
        return {
            "bookmaker": bookmaker["name"],
            "valeurs": {v["value"]: v["odd"] for v in marche_1x2["values"]},
        }
    except (KeyError, IndexError):
        return None


def generer_resume_texte(nom_a, nom_b, h2h, forme_a, forme_b, moy_a, moy_b, cotes):
    """Construit un resume en francais base UNIQUEMENT sur des donnees reelles recuperees."""
    lignes = [f"Rapport statistique reel : {nom_a} contre {nom_b}.", ""]

    lignes.append("Confrontations directes recentes :")
    if h2h:
        for m in h2h:
            lignes.append(
                f"Le {m['date']}, {m['domicile']} {m['score_domicile']} - "
                f"{m['score_exterieur']} {m['exterieur']}."
            )
    else:
        lignes.append("Aucune confrontation directe recente trouvee dans la base de donnees.")
    lignes.append("")

    lignes.append(f"Forme recente de {nom_a} :")
    if moy_a:
        lignes.append(
            f"{moy_a['victoires']} victoires, {moy_a['nuls']} nuls, "
            f"{moy_a['defaites']} defaites sur les {len(forme_a)} derniers matchs. "
            f"Moyenne de {moy_a['moyenne_marques']} buts marques et "
            f"{moy_a['moyenne_encaisses']} buts encaisses par match."
        )
    else:
        lignes.append("Donnees insuffisantes.")
    lignes.append("")

    lignes.append(f"Forme recente de {nom_b} :")
    if moy_b:
        lignes.append(
            f"{moy_b['victoires']} victoires, {moy_b['nuls']} nuls, "
            f"{moy_b['defaites']} defaites sur les {len(forme_b)} derniers matchs. "
            f"Moyenne de {moy_b['moyenne_marques']} buts marques et "
            f"{moy_b['moyenne_encaisses']} buts encaisses par match."
        )
    else:
        lignes.append("Donnees insuffisantes.")
    lignes.append("")

    if cotes:
        lignes.append(f"Cotes actuelles du marche, selon {cotes['bookmaker']} :")
        for issue, valeur in cotes["valeurs"].items():
            lignes.append(f"{issue} : cote de {valeur}.")
    else:
        lignes.append("Aucune cote de marche disponible pour ce match actuellement.")

    lignes.append("")
    lignes.append(
        "Rappel : ces chiffres sont des statistiques historiques reelles, "
        "pas une prediction du resultat du prochain match. Le football reste "
        "imprevisible. Cette analyse ne constitue pas un conseil de pari."
    )

    return "\n".join(lignes)


def creer_lecteur_audio(texte, nom_fichier="/tmp/analyse_stats.mp3"):
    """Convertit le resume en audio francais et retourne un lecteur HTML integre."""
    try:
        texte_propre = texte.replace("*", "").replace("#", "")
        tts = gTTS(text=texte_propre, lang="fr", slow=False)
        tts.save(nom_fichier)

        with open(nom_fichier, "rb") as f:
            audio_base64 = base64.b64encode(f.read()).decode()

        return f"""
        <div style="margin: 20px 0; padding: 15px; background-color: #1e1e2e; border-radius: 10px; text-align: center;">
            <p style="color: #ffb000; font-weight: bold; font-size: 16px; margin-bottom: 10px;">ECOUTER LE RAPPORT</p>
            <audio controls src="data:audio/mp3;base64,{audio_base64}" style="width: 100%; max-width: 400px;"></audio>
        </div>
        """
    except Exception as e:
        return f"<p style='color:red;'>Impossible de generer l'audio : {e}</p>"


# ==========================================
# INTERFACE STREAMLIT
# ==========================================
st.set_page_config(page_title="BetScope Stats", page_icon=":bar_chart:", layout="centered")

st.markdown(
    "<h1 style='text-align: center; color: #ffb000;'>BetScope Stats</h1>",
    unsafe_allow_html=True,
)
st.markdown(
    "<h3 style='text-align: center; color: #ffffff;'>Statistiques reelles, pas de predictions inventees</h3>",
    unsafe_allow_html=True,
)

if not get_api_key():
    st.warning(
        "Aucune cle API trouvee. Ajoute API_FOOTBALL_KEY dans les Secrets "
        "de Streamlit Cloud pour utiliser l'application."
    )

col1, col2 = st.columns(2)
with col1:
    nom_equipe_a = st.text_input("Equipe A", "Paris Saint Germain")
with col2:
    nom_equipe_b = st.text_input("Equipe B", "Marseille")

if st.button("Recuperer les statistiques reelles"):
    if not get_api_key():
        st.error("Impossible de continuer sans cle API valide.")
    else:
        with st.spinner("Recherche des equipes..."):
            equipe_a = chercher_equipe(nom_equipe_a)
            equipe_b = chercher_equipe(nom_equipe_b)

        if not equipe_a or not equipe_b:
            st.error(
                "Une ou plusieurs equipes n'ont pas ete trouvees. "
                "Verifie l'orthographe des noms."
            )
        else:
            with st.spinner("Recuperation des donnees reelles..."):
                h2h = recuperer_h2h(equipe_a["id"], equipe_b["id"])
                forme_a = recuperer_forme_recente(equipe_a["id"])
                forme_b = recuperer_forme_recente(equipe_b["id"])
                moy_a = calculer_moyennes_buts(forme_a)
                moy_b = calculer_moyennes_buts(forme_b)
                cotes = recuperer_cotes_marche(equipe_a["id"], equipe_b["id"])

            st.markdown("---")
            st.markdown(f"### Confrontations directes : {equipe_a['nom']} vs {equipe_b['nom']}")
            if h2h:
                for m in h2h:
                    st.write(
                        f"**{m['date']}** - {m['domicile']} **{m['score_domicile']} - "
                        f"{m['score_exterieur']}** {m['exterieur']}"
                    )
            else:
                st.info("Aucune confrontation directe recente trouvee.")

            st.markdown("---")
            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown(f"### {equipe_a['nom']}")
                if moy_a:
                    st.metric("Buts marques/match", moy_a["moyenne_marques"])
                    st.metric("Buts encaisses/match", moy_a["moyenne_encaisses"])
                    st.write(f"V {moy_a['victoires']} - N {moy_a['nuls']} - D {moy_a['defaites']}")
            with col_b:
                st.markdown(f"### {equipe_b['nom']}")
                if moy_b:
                    st.metric("Buts marques/match", moy_b["moyenne_marques"])
                    st.metric("Buts encaisses/match", moy_b["moyenne_encaisses"])
                    st.write(f"V {moy_b['victoires']} - N {moy_b['nuls']} - D {moy_b['defaites']}")

            st.markdown("---")
            st.markdown("### Cotes actuelles du marche")
            if cotes:
                st.write(f"Source : {cotes['bookmaker']}")
                for issue, valeur in cotes["valeurs"].items():
                    st.write(f"**{issue}** : {valeur}")
            else:
                st.info("Aucune cote disponible (pas de match a venir trouve entre ces deux equipes).")

            st.warning(
                "Ces statistiques sont reelles et basees sur des faits passes. "
                "Elles ne predisent pas le resultat du prochain match. Le football "
                "reste imprevisible - ceci n'est pas un conseil de pari."
            )

            resume = generer_resume_texte(
                equipe_a["nom"], equipe_b["nom"], h2h, forme_a, forme_b, moy_a, moy_b, cotes
            )

            st.markdown("---")
            st.markdown("### Version audio du rapport")
            lecteur = creer_lecteur_audio(resume)
            st.components.v1.html(lecteur, height=150)
