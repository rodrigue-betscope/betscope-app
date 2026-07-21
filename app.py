import base64
import google.generativeai as genai
from gtts import gTTS
import streamlit as st

# 1. Configuration de la clé API Gemini (Doit commencer par AIzaSy...)
GEMINI_API_KEY = "VOTRE_VRAI_CLE_AIZASY"
genai.configure(api_key=GEMINI_API_KEY)


def generer_analyse_vip_complete(cible_match):
  """Génère un rapport complet et prépare le texte pour la voix IA."""
  model = genai.GenerativeModel(model_name="gemini-1.5-pro")

  prompt = f"""
    Tu es l'algorithme d'analyse prédictive principal de l'application VIP "Rodrigue Pro Puissant Prédiction".
    Ton but est de fournir une analyse d'expert mathématique, historique et contextuelle pour le match ou le lien suivant : {cible_match}
    
    Compile les éléments suivants :
    1. JOURNAL HISTORIQUE (H2H) : Comment les précédents matchs entre ces équipes se sont déroulés ? Qui a gagné ? Combien de buts ont été marqués en moyenne ?
    2. CONTEXTE ACTUEL : Les blessures récentes, les joueurs clés absents ou suspendus, la météo et son impact.
    3. FLUX FINANCIERS : Les mouvements de cotes importants sur le marché 1X2.

    Génère un rapport VIP structuré en français avec ces sections exactes :

    📖 [1] LE JOURNAL DES CONFRONTATIONS (H2H)
    - Historique des derniers face-à-face entre les deux équipes.
    - Analyse des buts marqués lors de leurs confrontations.
    - Dynamique récente et état de forme général.

    📋 [2] INFOS TERRAIN & MÉTÉO
    - Liste des joueurs blessés ou absents importants pour ce match.
    - Conditions météo locales et impact attendu sur le score.

    📈 [3] PROBABILITÉS NETTES (1X2 & Doubles Chances)
    - % Victoire Domicile : [Indiquer le % précis]
    - % Match Nul : [Indiquer le % précis]
    - % Victoire Extérieur : [Indiquer le % précis]
    - Choix conseillé ferme : (1, X, 2, 1X ou X2)

    ⚽ [4] SCORES EXACTS & MI-TEMPS (Haute Précision)
    - Score Exact Final le plus probable (ex: 2-1).
    - Score Exact à la Mi-temps (ex: 1-0).
    - Scénario Mi-temps / Fin du match (ex: 1/1, X/1, X/2).
    - Les deux équipes marquent : [Oui/Non + Pourcentage].

    🎯 [5] OPTIONS AVANCÉES & COMBOS PREMIUM
    - Over / Under : (Plus ou moins de 1.5 buts et 2.5 buts dans le match).
    - Spécial : Une équipe gagne-t-elle spécifiquement la 2ème mi-temps ?
    - Combo Premium Rentable : (Ex: Victoire Domicile + Plus de 2.5 buts).
    """

  try:
    response = model.generate_content(prompt)
    return response.text
  except Exception as e:
    return f"❌ Erreur lors de l'analyse : {str(e)}"


def creer_bouton_audio_html(texte_analyse, nom_fichier="analyse_vip.mp3"):
  """Prend le texte de l'IA, le convertit en voix parlée en français,

  et génère un lecteur audio HTML pour ton site web.
  """
  try:
    texte_propre = (
        texte_analyse.replace("*", "")
        .replace("[", "")
        .replace("]", "")
        .replace("📊", "")
        .replace("⚽", "")
    )

    tts = gTTS(text=texte_propre, lang="fr", slow=False)
    tts.save(nom_fichier)

    with open(nom_fichier, "rb") as audio_file:
      audio_bytes = audio_file.read()
    audio_base64 = base64.b64encode(audio_bytes).decode()

    html_audio_player = f"""
        <div style="margin: 20px 0; padding: 15px; background-color: #1e1e2e; border-radius: 10px; text-align: center;">
            <p style="color: #ffb000; font-weight: bold; font-size: 16px; margin-bottom: 10px;">🔊 ÉCOUTER L'ANALYSE IA EN HAUTE VOIX</p>
            <audio controls src="data:audio/mp3;base64,{audio_base64}" style="width: 100%; max-width: 400px;"></audio>
        </div>
        """
    return html_audio_player
  except Exception as e:
    return (
        f"<p style='color:red;'>Impossible de générer la voix : {str(e)}</p>"
    )


# ==========================================
# INTERFACE GRAPHIQUE STREAMLIT
# ==========================================
st.set_page_config(page_title="BetScope Pro", page_icon="👑", layout="centered")

st.markdown(
    "<h1 style='text-align: center; color: #ffb000;'>👑 BetScope Pro</h1>",
    unsafe_allow_html=True,
)
st.markdown(
    "<h3 style='text-align: center; color: #ffffff;'>Module d'Analyse"
    " Prédictive VIP</h3>",
    unsafe_allow_html=True,
)

match_cible = st.text_input(
    "Entrez le match ou les équipes à analyser :",
    "Agrobiznes Volochysk vs FC Epicentr Dunaivtsi",
)

if st.button("🚀 Lancer l'analyse VIP"):
  with st.spinner(
      "🔄 L'IA analyse le journal historique et les données en direct..."
  ):
    rapport_texte = generer_analyse_vip_complete(match_cible)

    st.markdown("---")
    st.markdown("### 📝 Rapport Textuel du Match")
    st.markdown(rapport_texte)

    st.markdown("---")
    st.markdown("### 🔊 Version Audio")
    html_lecteur_audio = creer_bouton_audio_html(rapport_texte)
    st.components.v1.html(html_lecteur_audio, height=150)
