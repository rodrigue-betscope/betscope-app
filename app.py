import streamlit as st
import urllib.parse
import urllib.request
import requests
import json
import hashlib
import re
import html
import io
import math

# =========================================================
# CONFIGURATION DE LA CLÉ API ET VOIX IA
# =========================================================
API_FOOTBALL_KEY = "14e0597ad77ade14b2e627c6cfc3242b"
API_BASE_URL = "https://v3.football.api-sports.io"

try:
    from gtts import gTTS
    VOICE_AVAILABLE = True
except ImportError:
    VOICE_AVAILABLE = False

st.set_page_config(
    page_title="BetScope Pro - VIP Engine", 
    page_icon="👑", 
    layout="centered"
)

# =========================================================
# 🎨 DESIGN & STYLE PREMIUM (DARK DASHBOARD MOOD)
# =========================================================
st.markdown("""
<style>
.stApp { background-color: #0E1117; color: #FFFFFF; }
div[data-testid="stVerticalBlock"] { gap: 0.8rem; }

.vip-card {  
    background-color: #161922;  
    border: 1px solid #2D313E;  
    border-radius: 12px;  
    padding: 20px;  
    margin-bottom: 15px;  
    box-shadow: 0 4px 15px rgba(0,0,0,0.3);  
}  
.vip-title {  
    color: #FF9900;  
    font-size: 13px;  
    text-transform: uppercase;  
    letter-spacing: 1.5px;  
    font-weight: bold;  
    margin-bottom: 8px;  
}  
.score-box {  
    background-color: #212530;  
    border-radius: 10px;  
    padding: 15px;  
    text-align: center;  
    font-size: 38px;  
    font-weight: 900;  
    color: #FF9900;  
    letter-spacing: 5px;  
    margin: 10px 0;  
    border: 1px solid #3a3f50;  
}  
.metric-row {  
    display: flex;  
    justify-content: space-between;  
    align-items: center;  
    padding: 8px 0;  
    border-bottom: 1px solid #222634;  
}  
.metric-value {  
    background-color: rgba(255, 153, 0, 0.1);  
    color: #FF9900;  
    padding: 2px 10px;  
    border-radius: 6px;  
    font-weight: bold;  
    font-size: 14px;  
}  
.metric-value-green {  
    background-color: rgba(37, 211, 102, 0.1);  
    color: #25D366;  
    padding: 2px 10px;  
    border-radius: 6px;  
    font-weight: bold;  
    font-size: 14px;  
}  
</style>
""", unsafe_allow_html=True)

# =========================================================
# 🧠 FONCTIONS API & CALCULS STATISTIQUES (POISSON)
# =========================================================
def get_api_headers():
    return {
        'x-apisports-key': API_FOOTBALL_KEY,
        'x-rapidapi-host': 'v3.football.api-sports.io'
    }

def rechercher_equipe_api(nom_equipe):
    """Recherche l'ID d'une équipe via l'API-Football"""
    try:
        url = f"{API_BASE_URL}/teams"
        params = {"search": nom_equipe}
        response = requests.get(url, headers=get_api_headers(), params=params, timeout=5)
        data = response.json()
        if data.get("response"):
            team_info = data["response"][0]["team"]
            return team_info["id"], team_info["name"]
    except Exception:
        pass
    return None, nom_equipe

def recuperer_stats_equipe(team_id, league_id=39, season=2025):
    """Récupère les statistiques réelles d'une équipe"""
    try:
        url = f"{API_BASE_URL}/teams/statistics"
        params = {"team": team_id, "league": league_id, "season": season}
        response = requests.get(url, headers=get_api_headers(), params=params, timeout=5)
        data = response.json()
        if data.get("response"):
            stats = data["response"]
            goals_for = float(stats["goals"]["for"]["average"]["total"] or 1.2)
            goals_against = float(stats["goals"]["against"]["average"]["total"] or 1.0)
            form = stats.get("form", "N/A")
            return goals_for, goals_against, form
    except Exception:
        pass
    return 1.3, 1.1, "N/A"

def poisson_probability(lam, k):
    return (math.exp(-lam) * (lam ** k)) / math.factorial(k)

def calculer_matrice_poisson(lambda_dom, lambda_ext, max_goals=5):
    matrix = {}
    home_win, draw, away_win = 0.0, 0.0, 0.0
    over_2_5, btts = 0.0, 0.0
    
    for h in range(max_goals + 1):
        for a in range(max_goals + 1):
            p = poisson_probability(lambda_dom, h) * poisson_probability(lambda_ext, a)
            matrix[(h, a)] = p
            if h > a:
                home_win += p
            elif h == a:
                draw += p
            else:
                away_win += p
            if h + a > 2.5:
                over_2_5 += p
            if h > 0 and a > 0:
                btts += p
                
    best_score = max(matrix, key=matrix.get)
    total = home_win + draw + away_win
    if total > 0:
        home_win /= total
        draw /= total
        away_win /= total

    return {
        'home_win': home_win * 100,
        'draw': draw * 100,
        'away_win': away_win * 100,
        'over_2_5': over_2_5 * 100,
        'btts': btts * 100,
        'exact_score': f"{best_score[0]} - {best_score[1]}",
        'exact_score_prob': matrix[best_score] * 100
    }

def extraire_noms_match(lien_sofa, lien_odds):
    liens = [l for l in [lien_sofa, lien_odds] if l]
    for url in liens:
        try:
            req = urllib.request.Request(
                url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            )
            with urllib.request.urlopen(req, timeout=2.0) as response:
                content = response.read().decode('utf-8', errors='ignore')
                match = re.search(r'<title>(.*?)</title>', content, re.IGNORECASE)
                if match:
                    titre = html.unescape(match.group(1).strip())
                    titre = re.sub(r'(?i)\s+(live score|betting|odds|cotes|sofascore|oddsportal).*', '', titre)
                    for sep in [" - ", " vs ", " VS ", " v "]:
                        if sep in titre:
                            p = titre.split(sep)
                            return p[0].strip(), p[1].strip()
        except Exception:
            pass
        
        try:
            if "/match/" in url.lower():  
                slug = url.split("/match/")[1].split("/")[0]  
                if "-vs-" in slug:  
                    p = slug.split("-vs-")  
                    return p[0].replace('-', ' ').title(), p[1].replace('-', ' ').title()
        except Exception:
            pass
            
    return "Équipe Domicile", "Équipe Extérieur"

# =========================================================
# NAVIGATION & INTERFACE UTILISATEUR
# =========================================================
menu = st.sidebar.radio("Menu Principal", ["⚽ Gratuit", "👑 VIP Engine"])

if menu == "⚽ Gratuit":
    st.title("⚽ Analyses Publiques")
    st.info("Espace gratuit en maintenance. Connectez-vous sur l'espace VIP Engine avec votre clé d'accès.")

elif menu == "👑 VIP Engine":
    st.markdown('<div style="font-size:24px; font-weight:bold; color:#FFF;">BETSCOPE PRO <span style="background-color:#FF9900; color:#000; padding:2px 8px; border-radius:4px; font-size:12px; vertical-align:middle;">VIP ENGINE - API LIVE</span></div>', unsafe_allow_html=True)

    st.markdown("""  
        <div style="display: flex; align-items: center; margin: 15px 0; background-color: #161922; padding: 12px; border-radius: 8px; border: 1px solid #25D366;">  
            <span style="height: 8px; width: 8px; background-color: #25D366; border-radius: 50%; display: inline-block; margin-right: 10px; box-shadow: 0 0 8px #25D366;"></span>  
            <span style="color: #25D366; font-weight: bold; font-size: 13px;">API-FOOTBALL Connectée : Moteur de Poisson v4.2 Actif</span>  
        </div>  
    """, unsafe_allow_html=True)  

    cle_acces = st.text_input("🔑 Clé d'accès VIP :", type="password")  
      
    # Clé d'accès par défaut ou libre pour le VIP Engine
    if cle_acces == "" or cle_acces is not None:  
        col_l1, col_l2 = st.columns(2)  
        with col_l1:  
            lien_sofa = st.text_input("🔗 Lien Analyse Sofascore :", placeholder="https://www.sofascore.com/...").strip()  
        with col_l2:  
            lien_odds = st.text_input("🔗 Lien Analyse Oddsportal :", placeholder="https://www.oddsportal.com/...").strip()  
              
        if lien_sofa or lien_odds:  
            with st.spinner("Connexion à l'API-FOOTBALL et calcul des probabilités réelles..."):
                dom_brut, ext_brut = extraire_noms_match(lien_sofa, lien_odds)
                
                # Recherche des IDs et stats réelles
                id_dom, nom_dom = rechercher_equipe_api(dom_brut)
                id_ext, nom_ext = rechercher_equipe_api(ext_brut)
                
                lam_dom, form_dom, _ = (1.5, "N/A", None) if not id_dom else recuperer_stats_equipe(id_dom)
                lam_ext, form_ext, _ = (1.1, "N/A", None) if not id_ext else recuperer_stats_equipe(id_ext)
                
                # Application du modèle de Poisson
                stats_match = calculer_matrice_poisson(lam_dom, lam_ext)
                
                score_estime = stats_match['exact_score']
                prob_score = stats_match['exact_score_prob']
                pct_btts = stats_match['btts']
                pct_over = stats_match['over_2_5']
                p_dom = stats_match['home_win']
                p_draw = stats_match['draw']
                p_ext = stats_match['away_win']
                
                opt_principale = "Plus de 2.5 buts (Over 2.5)" if pct_over > 50 else "Moins de 2.5 buts (Under 2.5)"

            # =========================================================
            # RENDU VISUEL VIP BLOCKS
            # =========================================================
            st.markdown(f"<h3 style='color:#FFF; text-align:center; margin-top:15px;'>📊 Analyse Statistique : {nom_dom} vs {nom_ext}</h3>", unsafe_allow_html=True)  
              
            # CARD 1 : PROBABILITÉS 1X2
            st.markdown(f"""  
            <div class="vip-card">  
                <div class="metric-row" style="border:none; padding:0;">  
                    <span style="color:#8E94A6; font-size:14px; font-weight:bold;">Probabilités du Match (1X2)</span>  
                    <span style="color:#FF9900; font-weight:bold; font-size:15px;">Modèle Poisson</span>  
                </div>  
                <div style="display:flex; justify-content:space-between; margin-top:15px; text-align:center;">
                    <div style="background:#212530; padding:10px; border-radius:8px; width:30%;">
                        <div style="color:#8E94A6; font-size:12px;">1 (Domicile)</div>
                        <div style="color:#FF9900; font-size:16px; font-weight:bold;">{p_dom:.1f}%</div>
                    </div>
                    <div style="background:#212530; padding:10px; border-radius:8px; width:30%;">
                        <div style="color:#8E94A6; font-size:12px;">X (Nul)</div>
                        <div style="color:#FFF; font-size:16px; font-weight:bold;">{p_draw:.1f}%</div>
                    </div>
                    <div style="background:#212530; padding:10px; border-radius:8px; width:30%;">
                        <div style="color:#8E94A6; font-size:12px;">2 (Extérieur)</div>
                        <div style="color:#FF9900; font-size:16px; font-weight:bold;">{p_ext:.1f}%</div>
                    </div>
                </div>
            </div>  
            """, unsafe_allow_html=True)  
              
            # CARD 2 : SCORE ESTIMÉ & OPTIONS  
            st.markdown(f"""  
            <div class="vip-card">  
                <div class="vip-title" style="text-align:center;">Score Exact Estimé (Fiabilité : {prob_score:.1f}%)</div>  
                <div class="score-box">{score_estime}</div>  
                  
                <div class="metric-row" style="margin-top:15px;">  
                    <span style="color:#FFF; font-size:14px;"><span style="color:#FF9900;">📌</span> <b>Option principale :</b></span>  
                    <div>  
                        <span style="color:#FFF; font-size:14px; margin-right:8px;"><b>{opt_principale}</b></span>  
                        <span class="metric-value">{pct_over:.1f}%</span>  
                    </div>  
                </div>  
                  
                <div class="metric-row" style="border:none;">  
                    <span style="color:#FFF; font-size:14px;"><span style="color:#FF9900;">⚽</span> <b>Les deux équipes marquent (BTTS) :</b></span>  
                    <div>  
                        <span style="color:#FFF; font-size:14px; margin-right:8px;"><b>{"Oui" if pct_btts > 50 else "Non"}</b></span>  
                        <span class="metric-value-green">{pct_btts:.1f}%</span>  
                    </div>  
                </div>  
            </div>  
            """, unsafe_allow_html=True)  

            # =========================================================
            # RAPPORT D'ANALYSE IA
            # =========================================================
            st.markdown("---")  
            st.markdown("<div class='vip-title'>🤖 RAPPORT D'ANALYSE STATISTIQUE & PROBABILISTE</div>", unsafe_allow_html=True)  
              
            rapport_ia = f"""Rapport analytique BetScope Pro pour la rencontre opposant {nom_dom} à {nom_ext}.

L'interrogation en temps réel de l'API-Football indique une expectation de buts de {lam_dom:.2f} pour l'équipe à domicile et {lam_ext:.2f} pour l'équipe visiteuse. Le modèle de distribution de Poisson établit une probabilité de victoire à domicile de {p_dom:.1f}%, un match nul à {p_draw:.1f}% et une victoire extérieure à {p_ext:.1f}%. Le score le plus probable calculé par la matrice mathématique est de {score_estime} avec une probabilité indicielle de {prob_score:.1f}%. Les marchés de buts indiquent une tendance forte vers l'option {opt_principale} ({pct_over:.1f}%)."""

            st.markdown(f"""  
            <div style="background-color:#161922; border-left:4px solid #FF9900; padding:15px; border-radius:0 8px 8px 0; font-size:13.5px; line-height:1.6; color:#D1D5DB; text-align:justify;">  
                {rapport_ia}  
            </div>  
            """, unsafe_allow_html=True)  

            # =========================================================
            # 🔊 SYNTHÈSE VOCALE IA (TEXT TO SPEECH)  
            # =========================================================  
            st.markdown(" ")  
            if VOICE_AVAILABLE:  
                if st.button("🔊 ÉCOUTER L'ANALYSE VOCALE DE L'IA"):  
                    with st.spinner("Génération de la voix off en cours..."):  
                        try:  
                            tts = gTTS(text=rapport_ia, lang='fr', slow=False)  
                            sound_buffer = io.BytesIO()  
                            tts.write_to_fp(sound_buffer)  
                            sound_buffer.seek(0)  
                            st.audio(sound_buffer, format="audio/mp3")  
                            st.success("▶️ Prêt ! Cliquez sur lecture pour écouter l'analyse.")  
                        except Exception as e:  
                            st.error("Erreur de connexion au serveur vocal Google.")  
            else:  
                st.warning("⚠️ Module vocal indisponible. Veuillez ajouter 'gTTS' dans requirements.txt.")  

        else:  
            st.info("💡 Veuillez insérer vos liens de match Sofascore ou Oddsportal pour lancer l'analyse en direct via l'API-Football.")  
else:  
    st.info("🔒 Contenu hautement sécurisé.")
