import streamlit as st
from scipy.stats import poisson

# Configuration de la page
st.set_page_config(page_title="VIP Daily Picks & Moteur Poisson", page_icon="⚽", layout="centered")

# Style CSS sombre pour un look professionnel
st.markdown("""
    <style>
    .main { background-color: #0b1315; color: white; }
    .stApp { background-color: #0b1315; }
    </style>
""", unsafe_allow_html=True)

# Initialisation des variables en mémoire
if "unlocked" not in st.session_state:
    st.session_state.unlocked = False

if "current_prediction" not in st.session_state:
    st.session_state.current_prediction = "Match 1: Real Madrid vs Barcelone -> Victoire Real (Cote 1.85)\nMatch 2: Man City vs Arsenal -> Plus de 2.5 buts"

if "secret_code" not in st.session_state:
    st.session_state.secret_code = "2026"

# --- TITRE DE L'APPLICATION ---
st.markdown("<h2 style='text-align: center; color: white;'>⚽ DAILY PICKS</h2>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #8a9ba8;'>Carefully selected football predictions</p>", unsafe_allow_html=True)

st.markdown("---")

# ================= 1. ESPACE ADMIN (MODIFICATION & MOTEUR MATHÉMATIQUE) =================
with st.expander("🔐 Espace Administrateur & Moteur d'Analyse"):
    admin_pwd = st.text_input("Mot de passe admin", type="password")
    if admin_pwd == "monadmin123":
        st.success("Connecté en mode Admin !")
        
        tab_admin, tab_poisson = st.tabs(["📝 Gestion du Coupon", "🧮 Moteur de Calcul Poisson"])
        
        with tab_admin:
            new_match = st.text_area("Collez vos nouveaux matchs analysés ici :", value=st.session_state.current_prediction, height=150)
            new_code = st.text_input("Définir le code secret de déblocage :", value=st.session_state.secret_code)
            
            if st.button("Mettre à jour le pronostic"):
                st.session_state.current_prediction = new_match
                st.session_state.secret_code = new_code
                st.success("Pronostic mis à jour avec succès !")
                st.rerun()
                
        with tab_poisson:
            st.subheader("Calcul de Probabilités (Loi de Poisson)")
            c1, c2 = st.columns(2)
            lambda_dom = c1.number_input("Espérance buts Domicile (λ1)", min_value=0.1, max_value=6.0, value=1.6, step=0.1)
            lambda_ext = c2.number_input("Espérance buts Extérieur (λ2)", min_value=0.1, max_value=6.0, value=1.1, step=0.1)
            
            if st.button("Calculer les Marchés"):
                # Matrices de score mi-temps (50% de la moyenne) et fin de match
                max_goals = 8
                mt_dom, mt_ext = lambda_dom * 0.45, lambda_ext * 0.45
                
                # Distribution mi-temps
                prob_mt_nul = sum(poisson.pmf(i, mt_dom) * poisson.pmf(i, mt_ext) for i in range(5))
                
                # Distribution fin de match
                matrix = [[poisson.pmf(i, lambda_dom) * poisson.pmf(j, lambda_ext) for j in range(max_goals)] for i in range(max_goals)]
                
                u05 = matrix[0][0]
                u15 = u05 + matrix[1][0] + matrix[0][1]
                u25 = u15 + matrix[2][0] + matrix[1][1] + matrix[0][2]
                u35 = u25 + matrix[3][0] + matrix[2][1] + matrix[1][2] + matrix[0][3]
                o55 = 1 - sum(matrix[i][j] for i in range(max_goals) for j in range(max_goals) if i + j <= 5)
                
                # Affichage des probabilités mathématiques
                st.write(f"**Mi-temps Nul :** {prob_mt_nul*100:.1f}%")
                st.write(f"**Under 0.5 :** {u05*100:.1f}% | **Under 1.5 :** {u15*100:.1f}%")
                st.write(f"**Under 2.5 :** {u25*100:.1f}% | **Under 3.5 :** {u35*100:.1f}%")
                st.write(f"**Over 5.5 :** {o55*100:.1f}%")

    elif admin_pwd != "":
        st.error("Mot de passe incorrect")

# ================= 2. SECTION : COUPON DU JOUR =================
st.markdown("### 🔒 TODAY'S COUPON")

if not st.session_state.unlocked:
    st.info("🔒 **Le pronostic VIP du jour est verrouillé.** Effectuez votre dépôt pour obtenir le code secret.")
    
    st.warning("""
    **💳 CHOISISSEZ VOTRE MOYEN DE PAIEMENT :**
    
    * **🟠 Orange Money :** `6 98 90 22 04`
    * **🟡 MTN Mobile Money :** `6 83 29 07 39`
    
    *Après votre dépôt, contactez-moi avec votre capture pour recevoir votre code secret.*
    """)

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
    st.success("✅ COUPON DÉBLOQUÉ AVEC SUCCÈS")
    
    st.markdown("#### Vos matchs analysés du jour :")
    st.code(st.session_state.current_prediction, language=None)
    
    if st.button("Verrouiller à nouveau pour un client"):
        st.session_state.unlocked = False
        st.rerun()

st.markdown("---")

# ================= 3. SECTION : HISTORIQUE DES RÉSULTATS =================
st.markdown("### 📅 PAST RESULTS")

results_list = [
    {"date": "08/10/2026", "match": "Calcio Brusoporto - AC Chievo Verona", "prediction": "HOME WIN (1)", "status": "WON"},
    {"date": "07/10/2026", "match": "Azerbaijan U21 vs Gibraltar", "prediction": "HOME WIN (1)", "status": "WON"},
    {"date": "06/10/2026", "match": "Grenada vs Bonaire", "prediction": "ov1.5", "status": "WON"}
]

for res in results_list:
    st.markdown(f"""
    <div style="background-color: #121f24; border: 1px solid #1e353c; padding: 12px; border-radius: 8px; margin-bottom: 8px;">
        <span style="font-size: 11px; color: #8a9ba8;">{res['date']}</span>
        <span style="background-color: #1b4d3e; color: #2ecc71; padding: 2px 8px; border-radius: 4px; font-weight: bold; font-size: 11px; float: right;">{res['status']}</span>
        <p style="margin: 4px 0 2px 0; font-weight: bold; color: white;">{res['match']}</p>
        <p style="margin: 0; color: #2ecc71; font-size: 13px;">{res['prediction']}</p>
    </div>
    """, unsafe_allow_html=True)
