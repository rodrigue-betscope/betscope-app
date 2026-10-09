import streamlit as st

# Configuration de la page
st.set_page_config(page_title="VIP Daily Picks", page_icon="⚽", layout="centered")

# Style CSS sombre (style application de paris)
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
    .payment-box {
        background-color: #121f24;
        border: 1px solid #ff7900;
        padding: 15px;
        border-radius: 10px;
        text-align: center;
        margin-bottom: 15px;
    }
    </style>
""", unsafe_allow_html=True)

# Initialisation des variables en mémoire
if "unlocked" not in st.session_state:
    st.session_state.unlocked = False

if "current_prediction" not in st.session_state:
    st.session_state.current_prediction = "Match 1: Real Madrid vs Barcelone -> Victoire Real (Cote 1.85)\nMatch 2: Man City vs Arsenal -> Plus de 2.5 buts"

if "secret_code" not in st.session_state:
    st.session_state.secret_code = "VIP2026"

# --- BARRE LATÉRALE (ESPACE ADMIN POUR VOUS) ---
with st.sidebar:
    st.header("⚙️ Espace Administrateur")
    admin_password = st.text_input("Mot de passe admin", type="password")
    
    if admin_password == "monadmin123": # Changez ce mot de passe admin secret si besoin
        st.success("Connecté !")
        st.markdown("---")
        st.subheader("Mettre à jour le pronostic")
        new_pred = st.text_area("Collez votre analyse ici :", value=st.session_state.current_prediction)
        new_code = st.text_input("Définir le code secret du jour :", value=st.session_state.secret_code)
        
        if st.button("Enregistrer"):
            st.session_state.current_prediction = new_pred
            st.session_state.secret_code = new_code
            st.success("Mis à jour avec succès !")
    else:
        if admin_password != "":
            st.error("Mot de passe incorrect")

# --- INTERFACE PUBLIQUE (POUR VOS CLIENTS) ---
st.markdown("<h2 style='text-align: center; color: white;'>⚽ DAILY PICKS</h2>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #8a9ba8;'>Carefully selected football predictions</p>", unsafe_allow_html=True)

st.markdown("---")

# ================= 1. SECTION : COUPON DU JOUR =================
st.markdown("### 🔒 TODAY'S COUPON")

if not st.session_state.unlocked:
    st.markdown("""
        <div class="locked-box">
            <h3>🔒 LOCKED</h3>
            <p style="color: #8a9ba8;">Le pronostic VIP du jour est masqué.</p>
        </div>
    """, unsafe_allow_html=True)
    
    # ENCADRÉ DE PAIEMENT AVEC ORANGE ET MTN
    st.markdown("""
        <div class="payment-box">
            <h4 style="color: #ff7900; margin-top: 0;">💳 CHOISISsez VOTRE MOYEN DE PAIEMENT</h4>
            <p style="color: white; margin-bottom: 10px;">Effectuez votre dépôt sur l'un des numéros ci-dessous :</p>
            
            <div style="background-color: #1a2c32; padding: 10px; border-radius: 8px; margin-bottom: 8px;">
                <span style="color: #ff7900; font-weight: bold;">🟠 Orange Money :</span><br>
                <b style="color: #2ecc71; font-size: 16px;">6 98 90 22 04</b>
            </div>
            
            <div style="background-color: #1a2c32; padding: 10px; border-radius: 8px; margin-bottom: 10px;">
                <span style="color: #ffcc00; font-weight: bold;">🟡 MTN Mobile Money :</span><br>
                <b style="color: #2ecc71; font-size: 16px;">6 83 29 07 39</b>
            </div>
            
            <p style="font-size: 12px; color: #d1d5db; margin-bottom: 0;">Après paiement, contactez-moi avec votre capture pour recevoir votre <b>code secret</b>.</p>
        </div>
    """, unsafe_allow_html=True)

    # Formulaire de déblocage par code secret
    with st.form("unlock_form"):
        entered_code = st.text_input("Entrez le code secret reçu :", type="password")
        submit_btn = st.form_submit_button("🔓 Débloquer le pronostic")
        
        if submit_btn:
            if entered_code == st.session_state.secret_code:
                st.session_state.unlocked = True
                st.success("Accès autorisé !")
                st.rerun()
            else:
                st.error("Code secret incorrect.")
else:
    st.success("✅ COUPON DÉBLOQUÉ")
    st.markdown(f"""
        <div style="background-color: #121f24; padding: 20px; border-radius: 10px; border: 1px solid #2ecc71;">
            <h4>Vos matchs analysés du jour :</h4>
            <p style="white-space: pre-wrap; color: white;">{st.session_state.current_prediction}</p>
        </div>
    """, unsafe_allow_html=True)
    
    if st.button("Verrouiller à nouveau"):
        st.session_state.unlocked = False
        st.rerun()

st.markdown("---")

# ================= 2. SECTION : HISTORIQUE DES RÉSULTATS =================
st.markdown("### 📅 PAST RESULTS")

results_list = [
    {"date": "08/10/2026", "match": "Calcio Brusoporto - AC Chievo Verona", "prediction": "HOME WIN (1)", "status": "WON"},
    {"date": "07/10/2026", "match": "Azerbaijan U21 vs Gibraltar", "prediction": "HOME WIN (1)", "status": "WON"},
    {"date": "06/10/2026", "match": "Grenada vs Bonaire", "prediction": "ov1.5", "status": "WON"}
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
