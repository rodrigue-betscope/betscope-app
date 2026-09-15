# -*- coding: utf-8 -*-
import io, json
from pathlib import Path
import numpy as np
import pandas as pd
import streamlit as st
from PIL import Image, ImageOps

try:
    import cv2
    CV2_OK = True
except Exception:
    CV2_OK = False

APP = "RODRIGUE APPLE AI V6"
HISTORY_FILE = Path("apple_history_v6.json")
ROWS, COLS = 7, 5

st.set_page_config(page_title=APP, page_icon="🍎", layout="wide")
st.title("🍎 RODRIGUE APPLE AI V6")
st.caption("Vision de grille • Analyse visuelle • Historique • Validation réelle")
st.warning("⚠️ Une capture ne permet pas de connaître avec certitude une case cachée si le serveur génère le résultat indépendamment. Cette version analyse ce qui est visible et n'invente pas une précision de 90 %.")

def safe_crop(img, box):
    w,h=img.size
    x1,y1,x2,y2=[int(v) for v in box]
    x1=max(0,min(x1,w-1)); y1=max(0,min(y1,h-1))
    x2=max(x1+1,min(x2,w)); y2=max(y1+1,min(y2,h))
    return img.crop((x1,y1,x2,y2))

def detect_geometry(img):
    w,h=img.size
    if CV2_OK:
        a=np.array(img)
        g=cv2.cvtColor(a,cv2.COLOR_RGB2GRAY)
        g=cv2.GaussianBlur(g,(9,9),2)
        circles=cv2.HoughCircles(g,cv2.HOUGH_GRADIENT,dp=1.2,
            minDist=max(25,int(min(w,h)*.045)),param1=100,param2=28,
            minRadius=max(12,int(min(w,h)*.035)),maxRadius=max(20,int(min(w,h)*.10)))
        if circles is not None and len(circles[0])>=10:
            pts=np.round(circles[0]).astype(int)
            pts=[p for p in pts if .10*w<p[0]<.99*w and .08*h<p[1]<.80*h]
            if len(pts)>=10:
                xs=[p[0] for p in pts]; ys=[p[1] for p in pts]
                sx=np.percentile(xs,95)-np.percentile(xs,5)
                sy=np.percentile(ys,95)-np.percentile(ys,5)
                if sx>.40*w and sy>.30*h:
                    cx=np.median(xs); cy=np.median(ys)
                    return (max(0.02*w,cx-sx/2-.07*w),
                            max(.04*h,cy-sy/2-.06*h),
                            min(.99*w,cx+sx/2+.07*w),
                            min(.86*h,cy+sy/2+.06*h),"OpenCV")
    return (.16*w,.12*h,.98*w,.72*h,"géométrie de secours")

def cells_from(img,geo):
    l,t,r,b,_=geo; gw=r-l; gh=b-t; out=[]
    for row in range(ROWS):
        for col in range(COLS):
            x1=l+col*gw/COLS; x2=l+(col+1)*gw/COLS
            y1=t+row*gh/ROWS; y2=t+(row+1)*gh/ROWS
            mx=(x2-x1)*.10; my=(y2-y1)*.10
            out.append((row+1,col+1,safe_crop(img,(x1+mx,y1+my,x2-mx,y2-my))))
    return out

def features(cell):
    a=np.asarray(cell.resize((96,96)),dtype=np.float32)
    mean=a.mean((0,1))
    dx=np.abs(np.diff(a,axis=1)).mean()
    dy=np.abs(np.diff(a,axis=0)).mean()
    return dict(brightness=float(mean.mean()),
                saturation=float(mean.max()-mean.min()),
                texture=float((dx+dy)/2),
                variation=float(a.std()))

def analyse(cells):
    rows=[]
    for row,col,cell in cells:
        d=features(cell); d.update(row=row,col=col); rows.append(d)
    df=pd.DataFrame(rows)
    for x in ["brightness","saturation","texture","variation"]:
        lo,hi=df[x].min(),df[x].max()
        df[x+"_n"]=(df[x]-lo)/(hi-lo) if hi>lo else .5
    df["indice_visuel"]=(45+45*(.35*df.texture_n+.25*df.saturation_n+.20*df.variation_n+.20*df.brightness_n)).clip(0,90)
    return df

def load_history():
    try:
        if HISTORY_FILE.exists():
            d=json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
            return d if isinstance(d,list) else []
    except Exception: pass
    return []

def save_history(d):
    HISTORY_FILE.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding="utf-8")

cap=st.file_uploader("📸 Sélectionne une capture d'écran",type=["jpg","jpeg","png","webp"])
tabs=st.tabs(["🧠 Analyse","📊 Historique","🧪 Validation"])

if cap:
    try:
        img=ImageOps.exif_transpose(Image.open(io.BytesIO(cap.getvalue())).convert("RGB"))
        if max(img.size)>1400:
            s=1400/max(img.size)
            img=img.resize((int(img.width*s),int(img.height*s)),Image.Resampling.LANCZOS)
        geo=detect_geometry(img)
        df=analyse(cells_from(img,geo))
        st.session_state["df"]=df
        st.session_state["img"]=img
        st.session_state["geo"]=geo
        st.success("✅ Capture analysée immédiatement. L'historique n'est plus obligatoire.")
        st.image(img,use_container_width=True)
        st.info(f"Grille traitée : {ROWS} × {COLS} • Méthode : {geo[4]}")
    except Exception as e:
        st.error(f"Erreur d'analyse : {e}")

with tabs[0]:
    df=st.session_state.get("df")
    if df is None:
        st.info("Charge une capture ci-dessus pour lancer l'analyse.")
    else:
        s=df.groupby("col")["indice_visuel"].mean().sort_values(ascending=False)
        st.subheader("📌 Classement des colonnes")
        cols=st.columns(5)
        for i,(c,v) in enumerate(s.items()):
            cols[i].metric(f"C{int(c)}",f"{v:.0f}/90")
        st.dataframe(df[["row","col","brightness","saturation","texture","indice_visuel"]].round(2),use_container_width=True)
        best=int(s.index[0])
        st.success(f"Colonne avec le meilleur indice visuel : C{best}")
        st.caption("Cet indice est visuel, pas une probabilité de trouver la pomme.")

with tabs[1]:
    hist=load_history()
    if hist: st.dataframe(pd.DataFrame(hist),use_container_width=True)
    else: st.info("Aucune observation enregistrée. L'analyse de capture fonctionne même sans historique.")
    st.caption(f"{len(hist)} observation(s) enregistrée(s).")

with tabs[2]:
    st.subheader("🧪 Enregistrer le résultat réellement observé")
    real=st.selectbox("Colonne réellement sûre",[1,2,3,4,5],format_func=lambda x:f"C{x}")
    pred=st.selectbox("Colonne prédite",[1,2,3,4,5],format_func=lambda x:f"C{x}")
    signal=st.selectbox("Niveau du signal",["faible","moyen","fort"],index=1)
    if st.button("💾 Enregistrer cette observation",type="primary"):
        hist=load_history()
        hist.append({"colonne_reelle":real,"colonne_predite":pred,"signal":signal,"succes":int(real==pred)})
        try:
            save_history(hist); st.success("✅ Observation enregistrée."); st.rerun()
        except Exception as e: st.error(f"Erreur d'enregistrement : {e}")

st.divider()
st.caption("RODRIGUE APPLE AI V6 — outil expérimental. Ne prétend pas connaître une case cachée générée côté serveur.")
