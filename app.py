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
    .pay-btn {
        background-color: #ff7900;
        color: white;
        padding: 12px 20px;
        border-radius: 8px;
        text-align: center;
        font-weight: bold;
        display: block;
        text-decoration: none;
        margin-top: 10px;
    }
    </style>
""", unsafe_allow_html=True)

# Initialisation des variables en mémoire (pour la démo)
if "unlocked" not in st.session_state:
    st.session_state.unlocked = False

if "current_prediction" not in st.session_state:
    st.session_state.current_prediction = "Match 1: Real Madrid vs Barcelone -> Victoire Real (Cote 1.85)\nMatch 2: Man City vs Arsenal -> Plus de 2.5 buts"

if "secret_code" not in st.session_state:
    st.session_state.secret_code = "VIP2026"

# --- BARRE LATÉRALE (ACCÈS ADMIN CACHÉ POUR VOUS) ---
with st.sidebar:
    st.header("⚙️ Espace Administrateur")
    admin_password = st.text_input("Mot de passe admin", type="password")
    
    if admin_password == "monadmin123": # Changez ce mot de passe admin secret
        st.success("Connecté en tant qu'admin !")
        st.markdown("---")
        st.subheader("Mettre à jour le pronostic du jour")
        new_pred = st.text_area("Collez votre analyse ici :", value=st.session_state.current_prediction)
        new_code = st.text_input("Définir le code secret du jour :", value=st.session_state.secret_code)
        
        if st.button("Enregistrer les modifications"):
            st.session_state.current_prediction = new_pred
            st.session_state.secret_code = new_code
            st.success("Pronostic mis à jour avec succès !")
    else:
        if admin_password != "":
            st.error("Mot de passe incorrect")

# --- INTERFACE PRINCIPALE (CE QUE VOIENT VOS CLIENTS) ---
st.markdown("<h2 style='text-align: center; color: white;'>⚽ DAILY PICKS</h2>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #8a9ba8;'>Carefully selected football predictions</p>", unsafe_allow_html=True)

st.markdown("---")

# ================= 1. SECTION : COUPON DU JOUR =================
st.markdown("### 🔒 TODAY'S COUPON")

if not st.session_state.unlocked:
    st.markdown("""
        <div class="locked-box">
            <h3>🔒 LOCKED</h3>
            <p style="color: #8a9ba8;">Le pronostic VIP du jour est masqué. Payez via Orange Money pour obtenir votre code d'accès instantané.</p>
        </div>
    """, unsafe_allow_html=True)
    
    # Bouton de paiement direct Orange Money (Vous pouvez remplacer le lien par votre lien de paiement direct ou votre numéro)
    st.markdown("""
        <a href="tel:#150#" class="pay-btn">🟠 Payer avec Orange Money (Ex: #150#)</a>
    """, unsafe_allow_html=True)
    
    st.info("💡 **Instructions :** Une fois le paiement effectué sur le compte Orange Money, contactez l'administrateur ou entrez votre code secret reçu.")

    # Formulaire de déblocage par code secret
    with st.form("unlock_form"):
        entered_code = st.text_input("Entrez votre code secret :", type="password")
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
