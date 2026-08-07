import math
import streamlit as st

# Configuration de la page
st.set_page_config(page_title="NASMO IA BOT - V13 PRO", page_icon="🧠", layout="centered")

# CSS pour le look sombre et moderne
st.markdown("""
    <style>
    .main { background-color: #0e1117; color: white; }
    .card { background-color: #161b22; padding: 20px; border-radius: 15px; border: 1px solid #30363d; margin-bottom: 10px; }
    .value-bet { color: #58a6ff; font-weight: bold; }
    .high-conf { color: #3fb950; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

st.title("🧠 NASMO IA BOT - V13 Intelligent PRO")

# Organisation par Onglets
tab1, tab2, tab3 = st.tabs(["⚙️ Configuration", "📊 Analyse IA", "💎 Conseils Pro"])

with tab1:
    st.subheader("Entrées Statistiques")
    col1, col2 = st.columns(2)
    with col1:
        home = st.text_input("Équipe Domicile", "FC Cologne")
        home_gf = st.number_input("Buts marqués (Dom)", 0.0, 100.0, 34.0)
        home_ga = st.number_input("Buts encaissés (Dom)", 0.0, 100.0, 12.0)
        home_mp = st.number_input("Matchs joués (Dom)", 1.0, 50.0, 5.0)
    with col2:
        away = st.text_input("Équipe Extérieur", "Wolfsbourg")
        away_gf = st.number_input("Buts marqués (Ext)", 0.0, 100.0, 28.0)
        away_ga = st.number_input("Buts encaissés (Ext)", 0.0, 100.0, 15.0)
        away_mp = st.number_input("Matchs joués (Ext)", 1.0, 50.0, 5.0)
    
    league_avg = st.number_input("Moyenne buts championnat", 1.0, 5.0, 2.70)
    cote_1 = st.number_input("Cote Victoire (1)", 1.0, 20.0, 1.31)

with tab2:
    if st.button("Lancer le moteur d'intelligence IA"):
        # Calculs avancés
        home_att = home_gf / home_mp
        home_def = home_ga / home_mp
        away_att = away_gf / away_mp
        away_def = away_ga / away_mp
        
        # Facteur Avantage Domicile (1.1 standard)
        home_adv = 1.1 
        
        pred_home = (home_att * away_def * home_adv) / league_avg
        pred_away = (away_att * home_def) / league_avg
        
        # Probabilité
        prob_home = (pred_home / (pred_home + pred_away + 0.3)) * 100
        
        # Intelligence : Calcul Value Bet
        # Value = (Probabilité * Cote) - 1
        value_score = (prob_home / 100) * cote_1
        
        # Intelligence : Indice de confiance
        confidence = min(99, abs(pred_home - pred_away) * 25 + 40)
        
        st.markdown(f"""
        <div class="card">
            <h3>Résultat Prédictif</h3>
            <h1 style="color: #3fb950;">{round(pred_home)} - {round(pred_away)}</h1>
            <p>Probabilité Victoire : <b>{prob_home:.1f}%</b></p>
            <p>Indice de confiance IA : <b>{confidence:.0f}%</b></p>
        </div>
        """, unsafe_allow_html=True)
        
        st.session_state['value_score'] = value_score
        st.session_state['confidence'] = confidence

with tab3:
    if 'value_score' in st.session_state:
        st.subheader("Verdict de l'IA")
        if st.session_state['value_score'] > 1.1:
            st.success("💎 VALUE BET DÉTECTÉ : Cote très avantageuse !")
        else:
            st.warning("⚠️ Prudence : Pas de value bet clair.")
            
        if st.session_state['confidence'] > 70:
            st.markdown("<p class='high-conf'>🚀 Pari Fortement Recommandé</p>", unsafe_allow_html=True)
        else:
            st.markdown("<p>Pari avec risque modéré</p>", unsafe_allow_html=True)

st.sidebar.markdown("---")
st.sidebar.info("IA V13 - Optimisation 2026 💯")
