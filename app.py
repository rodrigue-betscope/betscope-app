import streamlit as st

# Configuration de la page
st.set_page_config(page_title="VIP Pronostics", page_icon="⚽", layout="centered")

# Style CSS pour un look sombre et professionnel (similaire à vos captures)
st.markdown("""
    <style>
    .main { background-color: #0b1315; color: white; }
    .stApp { background-color: #0b1315; }
    .locked-box {
        background-color: #121f24;
        border: 1px solid #1e353c;
        padding: 20px;
        border-radius: 12px;
        text-align: center;
        margin-bottom: 15px;
    }
    .result-box {
        background-color: #121f24;
        border: 1px solid #1e353c;
        padding: 15px;
        border-radius: 10px;
        margin-bottom: 10px;
    }
    .won-badge {
        background-color: #1b4d3e;
        color: #2ecc71;
        padding: 4px 10px;
        border-radius: 5px;
        font-weight: bold;
        font-size: 12px;
        float: right;
    }
    </style>
""", unsafe_allow_html=True)

# Initialisation de la session pour stocker les données (simulation simple)
if "unlocked" not in st.session_state:
    st.session_state.unlocked = False

# --- MOT DE PASSE SECRET ADMIN (Modifiez-le ici) ---
ADMIN_SECRET_CODE = "RODRIGUE2026"  # Le code que vous donnez après paiement
DAILY_SECRET_MATCH = "Match 1: Real Madrid vs Barcelone -> Victoire Real (Cote 1.85)\nMatch 2: Man City vs Arsenal -> Plus de 2.5 buts"

# --- TITRE DE L'APPLICATION ---
st.markdown("<h2 style='text-align: center; color: white;'>⚽ DAILY PICKS</h2>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #8a9ba8;'>Carefully selected football predictions</p>", unsafe_allow_html=True)

st.markdown("---")

# ================= 1. SECTION : COUPONS DU JOUR (BLOQUÉS / DÉBLOQUÉS) =================
st.markdown("### 🔒 TODAY'S COUPON")

if not st.session_state.unlocked:
    # Affichage verrouillé
    st.markdown("""
        <div class="locked-box">
            <h3>🔒 LOCKED</h3>
            <p style="color: #8a9ba8;">Le pronostic VIP du jour est masqué. Payez via Orange Money pour recevoir votre code secret.</p>
        </div>
    """, unsafe_allow_html=True)
    
    # Formulaire pour entrer le code secret
    with st.form("unlock_form"):
        entered_code = st.text_input("Entrez votre code secret reçu après paiement :", type="password")
        submit_button = st.form_submit_button("🔓 Débloquer le pronostic")
        
        if submit_button:
            if entered_code == ADMIN_SECRET_CODE:
                st.session_state.unlocked = True
                st.success("Accès autorisé ! Vos pronostics sont maintenant débloqués.")
                st.rerun()
            else:
                st.error("Code secret incorrect. Vérifiez auprès de l'administrateur.")
else:
    # Affichage débloqué (Le client voit le pronostic secret)
    st.success("✅ COUPON DÉBLOQUÉ AVEC SUCCÈS")
    st.info(f"**Voici l'analyse du jour :**\n\n{DAILY_SECRET_MATCH}")
    if st.button("Verrouiller à nouveau"):
        st.session_state.unlocked = False
        st.rerun()

st.markdown("---")

# ================= 2. SECTION : RÉSULTATS VALIDÉS (PAST RESULTS) =================
st.markdown("### 📅 PAST RESULTS")

# Vous pouvez modifier ces résultats facilement dans le code pour mettre vos 3-4 derniers succès
results_list = [
    {"date": "08/10/2026", "match": "Calcio Brusoporto - AC Chievo Verona", "prediction": "HOME WIN (1)", "status": "WON"},
    {"date": "07/10/2026", "match": "Azerbaijan U21 vs Gibraltar", "prediction": "HOME WIN (1)", "status": "WON"},
    {"date": "06/10/2026", "match": "Grenada vs Bonaire", "prediction": "ov1.5", "status": "WON"},
    {"date": "05/10/2026", "match": "Switzerland vs North Macedonia", "prediction": "BTTS", "status": "WON"}
]

for res in results_list:
    st.markdown(f"""
        <div class="result-box">
            <span style="font-size: 12px; color: #8a9ba8;">{res['date']}</span>
            <span class="won-badge">{res['status']}</span>
            <p style="margin: 5px 0 0 0; font-weight: bold; color: white;">{res['match']}</p>
            <p style="margin: 0; color: #2ecc71; font-size: 14px;">{res['prediction']}</p>
        </div>
    """, unsafe_allow_html=True)
