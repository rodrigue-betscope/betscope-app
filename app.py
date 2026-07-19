‎import streamlit as st
‎import urllib.parse
‎import hashlib
‎
‎# Configuration de la page
‎st.set_page_config(page_title="BetScope Pro", page_icon="👑", layout="centered")
‎
‎# =========================================================
‎# 🔐 CONFIGURATION DES CLÉS
‎# =========================================================
‎CLE_VIP_CORRECTE = ""  # Clé pour tes clients VIP
‎CLE_ADMIN_FORCAGE = ""  # Ta clé secrète admin
‎
‎# =========================================================
‎# 🧭 NAVIGATION : GRATUIT & VIP
‎# =========================================================
‎menu = st.sidebar.radio(
‎    "Menu Principal", 
‎    ["⚽ Gratuit", "👑 VIP"]
‎)
‎
‎# --- SECTION 1 : GRATUIT ---
‎if menu == "⚽ Gratuit":
‎    st.title("⚽ Espace Public & Gratuit")
‎    st.write("Bienvenue sur BetScope Pro ! Voici notre analyse gratuite du jour.")
‎    
‎    st.markdown("---")
‎    st.subheader("📌 Match du Jour")
‎    st.info(
‎        "⚽ **Manchester City vs Liverpool**\n\n"
‎        "• **Option recommandée :** Plus de 2.5 buts\n"
‎        "• **Fiabilité attendue :** 78%"
‎    )
‎
‎# --- SECTION 2 : VIP (HYBRIDE DOUBLE LIENS) ---
‎elif menu == "👑 VIP":
‎    st.title("👑 Espace VIP Intelligent")
‎    
‎    # Clignotant vert dynamique pour le statut du Robot IA
‎    st.markdown("""
‎        <div style="display: flex; align-items: center; margin-bottom: 15px; background-color: #1a1c23; padding: 10px; border-radius: 8px; border: 1px solid #2e313d;">
‎            <span style="height: 10px; width: 10px; background-color: #25D366; border-radius: 50%; display: inline-block; margin-right: 10px; box-shadow: 0 0 8px #25D366; animation: pulse 1.5s infinite alternate;"></span>
‎            <span style="color: #25D366; font-weight: bold; font-size: 14px;">● Robot IA en ligne : Double Analyse (Sportive & Financière) active</span>
‎        </div>
‎        <style>
‎            @keyframes pulse {
‎                from { opacity: 0.4; }
‎                to { opacity: 1; }
‎            }
‎        </style>
‎    """, unsafe_allow_html=True)
‎    
‎    cle_acces = st.text_input("🔑 Entrez votre clé d'accès VIP :", type="password")
‎    
‎    if cle_acces == CLE_VIP_CORRECTE:
‎        st.success("🔓 Accès VIP accordé.")
‎        st.write("Pour une analyse optimale, vous pouvez coller le lien **Sofascore** ET le lien **Oddsportal** du match.")
‎        
‎        # --- DOUBLE CHAMP DE SAISIE ---
‎        col_l1, col_l2 = st.columns(2)
‎        with col_l1:
‎            lien_sofa = st.text_input("🔗 Lien Sofascore (Terrain) :", placeholder="https://www.sofascore.com/...").strip()
‎        with col_l2:
‎            lien_odds = st.text_input("🔗 Lien Oddsportal (Finance) :", placeholder="https://www.oddsportal.com/...").strip()
‎        
‎        if lien_sofa or lien_odds:
‎            # Création d'un texte combiné pour générer l'empreinte mathématique (seed)
‎            lien_combine = lien_sofa + lien_odds
‎            seed = int(hashlib.md5(lien_combine.encode()).hexdigest(), 16)
‎            
‎            nom_du_match = "Match Sélectionné (Analyse Auto)"
‎            
‎            # 🧠 DECODEUR INTELLIGENT DE LIENS
‎            # On cherche d'abord à décoder le nom via Sofascore (souvent plus propre)
‎            if lien_sofa and "sofascore.com" in lien_sofa.lower():
‎                try:
‎                    slug = lien_sofa.split("/match/")[1].split("/")[0]
‎                    parts = slug.split("-")
‎                    if len(parts) >= 2:
‎                        nom_du_match = f"{parts[0].title()} vs {' '.join(parts[1:]).title()}"
‎                except Exception:
‎                    pass
‎            # Si pas de Sofascore, on décode via Oddsportal
‎            elif lien_odds and "oddsportal.com" in lien_odds.lower():
‎                try:
‎                    if "/h2h/" in lien_odds.lower():
‎                        parts = lien_odds.split("/h2h/")[1].split("/")
‎                        dom = parts[0].split("-")[0].title()
‎                        ext = parts[1].split("-")[0].title()
‎                        nom_du_match = f"{dom} vs {ext}"
‎                    elif "/match/" in lien_odds.lower():
‎                        slug = lien_odds.split("/match/")[1].split("/")[0]
‎                        parts = slug.split("-")
‎                        nom_du_match = f"{parts[0].title()} vs {' '.join(parts[1:-1]).title()}"
‎                except Exception:
‎                    pass
‎
‎            # --- ANALYSE DE CONTEXTE ---
‎            is_unpredictable = False
‎            type_competition = "Championnat Régulier"
‎            
‎            texte_analyse = (lien_sofa + lien_odds).lower()
‎            if any(x in texte_analyse for x in ["friendly", "amical", "amicaux"]):
‎                type_competition = "⚔️ Match Amical"
‎                is_unpredictable = True
‎            elif any(x in texte_analyse for x in ["cup", "coupe"]):
‎                type_competition = "🏆 Match de Coupe"
‎            elif "play-off" in 
