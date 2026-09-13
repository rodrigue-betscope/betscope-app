
import math, time
from datetime import date, datetime
import numpy as np
import pandas as pd
import requests
import streamlit as st

API_BASE = "https://api.football-data.org/v4"
FOOTBALL_DATA_KEY = "d212fb8b550d4756b16521dbe73b708d"
COMPETITIONS = {
    "Premier League":"PL","LaLiga":"PD","Bundesliga":"BL1","Serie A":"SA",
    "Ligue 1":"FL1","Champions League":"CL","Eredivisie":"DED",
    "Primeira Liga":"PPL","Championship":"ELC","Brasileirão":"BSA"
}
S = requests.Session()
S.headers.update({"User-Agent":"Rodrigue-Pro-Football-AI-V21","Accept":"application/json"})
st.set_page_config(page_title="Rodrigue Pro Football AI V21", page_icon="⚽", layout="wide")

def sf(x, default=None):
    try:
        x=float(x)
        return x if math.isfinite(x) else default
    except (TypeError, ValueError):
        return default

def clamp(x,a,b):
    x=sf(x,a)
    return max(a,min(b,x))

def pct(x):
    x=sf(x)
    return "N/D" if x is None else f"{100*clamp(x,0,1):.1f}%"

def fmt(x):
    x=sf(x)
    return "N/D" if x is None else f"{x:.2f}"

def _get(ep, params=()):
    try:
        r=S.get(API_BASE+ep, params=dict(params), timeout=25)
        try: data=r.json()
        except Exception: data=None
        return {
            "status":r.status_code,
            "data":data if r.status_code==200 else None,
            "error":(data or {}).get("message","") if isinstance(data,dict) else r.text[:500],
            "remaining":r.headers.get("X-Requests-Available-Minute","")
        }
    except requests.RequestException as e:
        return {"status":0,"data":None,"error":str(e),"remaining":""}

@st.cache_data(ttl=300, show_spinner=False)
def api(ep, params=()):
    time.sleep(.12)
    return _get(ep, params)

def data(ep, params=()):
    r=api(ep,params)
    return r["data"] if r["status"]==200 else None

@st.cache_data(ttl=1800, show_spinner=False)
def competition_info(code):
    return data(f"/competitions/{code}") or {}

@st.cache_data(ttl=900, show_spinner=False)
def season_matches(code, season_year):
    d=data(f"/competitions/{code}/matches", (("season",str(season_year)),))
    return (d or {}).get("matches",[])

@st.cache_data(ttl=900, show_spinner=False)
def team_matches(tid):
    d=data(f"/teams/{tid}/matches", (("status","FINISHED"),("limit","60")))
    return (d or {}).get("matches",[])

@st.cache_data(ttl=1800, show_spinner=False)
def table(code):
    d=data(f"/competitions/{code}/standings")
    blocks=(d or {}).get("standings",[])
    for b in blocks:
        if b.get("type")=="TOTAL":
            return b.get("table",[])
    return blocks[0].get("table",[]) if blocks else []

@st.cache_data(ttl=900, show_spinner=False)
def h2h(mid):
    d=data(f"/matches/{mid}/head2head",(("limit","10"),))
    return (d or {}).get("matches",[])

def finished(m):
    return m.get("status")=="FINISHED" and \
        m.get("score",{}).get("fullTime",{}).get("home") is not None and \
        m.get("score",{}).get("fullTime",{}).get("away") is not None

def dt_key(m):
    return m.get("utcDate","")

def match_result(m, tid):
    h=m.get("homeTeam",{}).get("id"); a=m.get("awayTeam",{}).get("id")
    f=m.get("score",{}).get("fullTime",{})
    hg,ag=f.get("home"),f.get("away")
    if hg is None or ag is None: return None
    if tid==h: return {"gf":hg,"ga":ag,"venue":"H","r":"W" if hg>ag else "D" if hg==ag else "L"}
    if tid==a: return {"gf":ag,"ga":hg,"venue":"A","r":"W" if ag>hg else "D" if ag==hg else "L"}
    return None

def rows_before(matches, tid, before=None, venue=None, limit=12):
    out=[]
    cutoff=before or "9999"
    for m in sorted(matches,key=dt_key,reverse=True):
        if dt_key(m)>=cutoff or not finished(m): continue
        r=match_result(m,tid)
        if r and (venue is None or r["venue"]==venue):
            out.append({"date":dt_key(m),"gf":r["gf"],"ga":r["ga"],"venue":r["venue"],"r":r["r"]})
            if len(out)>=limit: break
    return out

def stats(rows):
    if not rows:
        return {"n":0,"gf":1.30,"ga":1.30,"form":.5,"draw":.33}
    w=np.array([.94**i for i in range(len(rows))],dtype=float)
    gf=np.array([x["gf"] for x in rows],dtype=float)
    ga=np.array([x["ga"] for x in rows],dtype=float)
    pts=np.array([3 if x["r"]=="W" else 1 if x["r"]=="D" else 0 for x in rows],dtype=float)
    return {
        "n":len(rows),
        "gf":float(np.average(gf,weights=w)),
        "ga":float(np.average(ga,weights=w)),
        "form":float(np.average(pts/3,weights=w)),
        "draw":float(np.average((pts==1).astype(float),weights=w))
    }

def league_stats(matches, before=None):
    fs=[m for m in matches if finished(m) and (before is None or dt_key(m)<before)]
    if not fs:
        return {"n":0,"home_g":1.45,"away_g":1.15,"total_g":2.60,"ht_ratio":.44,"draw":.27}
    hg=[]; ag=[]; ht=[]; draws=0
    for m in fs:
        f=m["score"]["fullTime"]; hg.append(f["home"]); ag.append(f["away"]); draws += f["home"]==f["away"]
        h=m["score"].get("halfTime",{})
        if h.get("home") is not None and h.get("away") is not None:
            ht.append(h["home"]+h["away"])
    total=max(len(hg),1)
    return {
        "n":len(fs),
        "home_g":float(np.mean(hg)),
        "away_g":float(np.mean(ag)),
        "total_g":float(np.mean(np.array(hg)+np.array(ag))),
        "ht_ratio":float(clamp(np.mean(ht)/(np.mean(np.array(hg)+np.array(ag))) if ht and np.mean(np.array(hg)+np.array(ag))>0 else .44,.35,.55)),
        "draw":float(draws/total)
    }

def team_season_rows(matches,tid,before=None):
    return rows_before(matches,tid,before,None,60)

def poisson_probability(lam,k):
    lam=sf(lam); k=int(k)
    if lam is None or not math.isfinite(lam) or lam<0 or k<0: return 0.0
    if lam==0: return 1.0 if k==0 else 0.0
    p=math.exp(-lam+k*math.log(lam)-math.lgamma(k+1))
    return clamp(p,0,1)

def poisson_matrix(hl,al,n=8):
    a=np.array([poisson_probability(hl,i) for i in range(n+1)])
    b=np.array([poisson_probability(al,i) for i in range(n+1)])
    m=np.outer(a,b); s=m.sum()
    return m/s if s>0 else np.zeros_like(m)

def dc_matrix(m,hl,al,rho=-.055):
    m=m.copy()
    corr={(0,0):1-hl*al*rho,(0,1):1+hl*rho,(1,0):1+al*rho,(1,1):1-rho}
    for (h,a),v in corr.items():
        m[h,a]*=clamp(v,.90,1.10)
    m=np.maximum(m,0); s=m.sum()
    return m/s if s>0 else m

def market_probs(m):
    r={"1":0.0,"X":0.0,"2":0.0,"BTTS Oui":0.0,"Over 1.5":0.0,"Over 2.5":0.0,"Over 3.5":0.0}
    for h in range(m.shape[0]):
        for a in range(m.shape[1]):
            p=float(m[h,a])
            r["1" if h>a else "X" if h==a else "2"]+=p
            if h>0 and a>0: r["BTTS Oui"]+=p
            if h+a>=2: r["Over 1.5"]+=p
            if h+a>=3: r["Over 2.5"]+=p
            if h+a>=4: r["Over 3.5"]+=p
    r["1X"]=r["1"]+r["X"]; r["X2"]=r["X"]+r["2"]; r["12"]=r["1"]+r["2"]
    r["BTTS Non"]=1-r["BTTS Oui"]
    for n in ("1.5","2.5","3.5"): r["Under "+n]=1-r["Over "+n]
    return r

def exact_scores(m,n=10):
    z=[(f"{h}-{a}",float(m[h,a])) for h in range(m.shape[0]) for a in range(m.shape[1])]
    return sorted(z,key=lambda x:x[1],reverse=True)[:n]

def team_strength(rows, lg, venue=None):
    # Bayesian shrinkage toward league averages; prevents 3-match hot streaks
    s=stats(rows)
    n=s["n"]
    prior_n=6.0
    if venue=="H":
        pg,pa=lg["home_g"],lg["away_g"]
    elif venue=="A":
        pg,pa=lg["away_g"],lg["home_g"]
    else:
        pg=lg["total_g"]/2; pa=pg
    gf=(n*s["gf"]+prior_n*pg)/(n+prior_n)
    ga=(n*s["ga"]+prior_n*pa)/(n+prior_n)
    return gf,ga,s

def build_lambdas(hrows, arows, hsrows, asrows, lg):
    hgf,hga,hst=team_strength(hrows,lg)
    agf,aga,ast=team_strength(arows,lg)
    hgf_h,hga_h,_=team_strength(hsrows,lg,"H")
    agf_a,aga_a,_=team_strength(asrows,lg,"A")
    league_h=max(lg["home_g"],.25); league_a=max(lg["away_g"],.20)
    ha=0.58*hgf_h/league_h + 0.42*agf/((lg["total_g"]/2) or 1)
    hd=0.58*aga_a/league_a + 0.42*hga/((lg["total_g"]/2) or 1)
    aa=0.58*agf_a/league_a + 0.42*agf/((lg["total_g"]/2) or 1)
    ad=0.58*hga_h/league_h + 0.42*aga/((lg["total_g"]/2) or 1)
    hl=league_h*math.sqrt(max(ha,0.2)*max(hd,0.2))
    al=league_a*math.sqrt(max(aa,0.2)*max(ad,0.2))
    # small, bounded recent-form adjustment
    hl*=clamp(.93+.14*hst["form"],.90,1.07)
    al*=clamp(.93+.14*ast["form"],.90,1.07)
    return clamp(hl,.20,3.8),clamp(al,.15,3.5)

def halftime_model(hl,al,lg):
    ratio=lg.get("ht_ratio",.44)
    return dc_matrix(poisson_matrix(hl*ratio,al*ratio,6),hl*ratio,al*ratio)

def htft_from_models(ht,ft):
    r={f"{x}/{y}":0.0 for x in "1X2" for y in "1X2"}
    # Use a transition prior rather than assuming HT and FT independent.
    trans={
        "1":{"1":.74,"X":.16,"2":.10},
        "X":{"1":.27,"X":.48,"2":.25},
        "2":{"1":.10,"X":.16,"2":.74},
    }
    ht_m=market_probs(ht); ft_m=market_probs(ft)
    for x in "1X2":
        for y in "1X2":
            r[f"{x}/{y}"]=ht_m[x]*trans[x][y]
    # blend transition model with FT marginal to avoid impossible calibration
    for y in "1X2":
        s=sum(r[f"{x}/{y}"] for x in "1X2")
        if s>0:
            scale=ft_m[y]/s
            for x in "1X2": r[f"{x}/{y}"]*=scale
    return sorted(r.items(),key=lambda z:z[1],reverse=True)

def h2h_signal(ms,hid,aid):
    hw=dr=aw=0
    for m in ms:
        if not finished(m): continue
        f=m["score"]["fullTime"]; mh=m.get("homeTeam",{}).get("id"); ma=m.get("awayTeam",{}).get("id")
        if mh==hid and ma==aid: x,y=f["home"],f["away"]
        elif mh==aid and ma==hid: x,y=f["away"],f["home"]
        else: continue
        if x>y: hw+=1
        elif x==y: dr+=1
        else: aw+=1
    n=hw+dr+aw
    return {"n":n,"home":hw/n if n else .5,"draw":dr/n if n else .25,"away":aw/n if n else .25,"hw":hw,"dr":dr,"aw":aw}

def apply_h2h(m,hl,al,h2):
    # H2H is deliberately weakly weighted: it must not override current form.
    if h2["n"]<4: return m
    adj=clamp((h2["home"]-h2["away"])*.035,-.025,.025)
    # tilt 1/2 probabilities by a tiny amount through score cells
    out=m.copy()
    for h in range(out.shape[0]):
        for a in range(out.shape[1]):
            if h>a: out[h,a]*=(1+adj)
            elif h<a: out[h,a]*=(1-adj)
    return out/out.sum()

def standings_dynamic(matches, before, tid):
    pts=gf=ga=played=0
    for m in matches:
        if not finished(m) or dt_key(m)>=before: continue
        r=match_result(m,tid)
        if not r: continue
        played+=1; gf+=r["gf"]; ga+=r["ga"]; pts += 3 if r["r"]=="W" else 1 if r["r"]=="D" else 0
    return {"played":played,"points":pts,"gf":gf,"ga":ga,"gd":gf-ga}

def analyze_match(m):
    code=m.get("competition",{}).get("code","")
    season=int(m.get("season",{}).get("startDate","")[:4] or date.today().year)
    allm=season_matches(code,season)
    hid=m.get("homeTeam",{}).get("id"); aid=m.get("awayTeam",{}).get("id")
    before=m.get("utcDate","")
    lg=league_stats(allm,before)
    hrows=team_season_rows(allm,hid,before)
    arows=team_season_rows(allm,aid,before)
    hsrows=rows_before(allm,hid,before,"H",10)
    asrows=rows_before(allm,aid,before,"A",10)
    hl,al=build_lambdas(hrows,arows,hsrows,asrows,lg)
    ft=dc_matrix(poisson_matrix(hl,al),hl,al)
    h2=h2h_signal(h2h(m.get("id")),hid,aid)
    ft=apply_h2h(ft,hl,al,h2)
    ht=halftime_model(hl,al,lg)
    mk=market_probs(ft)
    htmk=market_probs(ht)
    scores=exact_scores(ft,10)
    ht_scores=exact_scores(ht,8)
    htft=htft_from_models(ht,ft)
    one=max((("1",mk["1"]),("X",mk["X"]),("2",mk["2"])),key=lambda z:z[1])
    # Confidence is a quality flag, NOT the probability of winning a bet.
    n=min(hrows.__len__(),arows.__len__())
    quality=int(clamp(35 + min(lg["n"],100)*.15 + min(n,20)*1.2 + (8 if h2["n"]>=5 else 0),0,85))
    spread=one[1]-sorted([mk["1"],mk["X"],mk["2"]],reverse=True)[1]
    confidence=int(clamp(50 + 30*spread + .25*quality,50,90))
    return {
        "home":m.get("homeTeam",{}).get("name","Domicile"),
        "away":m.get("awayTeam",{}).get("name","Extérieur"),
        "competition":m.get("competition",{}).get("name",""),
        "date":before,"status":m.get("status",""),
        "hl":hl,"al":al,"league":lg,"hf":stats(hrows),"af":stats(arows),
        "hs":stats(hsrows),"as":stats(asrows),"h2":h2,"mk":mk,"htmk":htmk,
        "scores":scores,"htscores":ht_scores,"htft":htft,"one":one,
        "quality":quality,"confidence":confidence
    }

def find_matches(d,codes):
    if d==date.today():
        r=api("/matches")
        ms=(r["data"] or {}).get("matches",[]) if r["status"]==200 else []
        return sorted([m for m in ms if m.get("competition",{}).get("code") in codes and m.get("utcDate","")[:10]==d.isoformat()],key=dt_key)
    out=[]; seen=set()
    for c in codes:
        r=api(f"/competitions/{c}/matches",(("season",str(d.year)),))
        for m in ((r["data"] or {}).get("matches",[]) if r["status"]==200 else []):
            if m.get("utcDate","")[:10]==d.isoformat() and m.get("id") not in seen:
                seen.add(m.get("id")); out.append(m)
    return sorted(out,key=dt_key)

def outcome(m):
    f=m["score"]["fullTime"]; h,a=f["home"],f["away"]
    return 0 if h>a else 1 if h==a else 2

def brier(probs,y):
    return sum((probs[i]-(1 if i==y else 0))**2 for i in range(3))

def logloss(probs,y):
    return -math.log(clamp(probs[y],1e-6,1))

def backtest(code,season_year,limit_matches=220):
    ms=[m for m in season_matches(code,season_year) if finished(m)]
    ms=sorted(ms,key=dt_key)[-limit_matches:]
    preds=[]; y=[]; br=[]; ll=[]; exact_hits=0; o25_hits=0; btts_hits=0; o25_n=0; btts_n=0
    for idx,m in enumerate(ms):
        before=m.get("utcDate","")
        prior=[x for x in ms if dt_key(x)<before]
        # Require enough prior matches so early-season noise is not scored as mature model.
        if len(prior)<30: continue
        lg=league_stats(prior)
        hid=m["homeTeam"]["id"]; aid=m["awayTeam"]["id"]
        hrows=team_season_rows(prior,hid,before); arows=team_season_rows(prior,aid,before)
        hsrows=rows_before(prior,hid,before,"H",10); asrows=rows_before(prior,aid,before,"A",10)
        if len(hrows)<3 or len(arows)<3: continue
        hl,al=build_lambdas(hrows,arows,hsrows,asrows,lg)
        mat=dc_matrix(poisson_matrix(hl,al),hl,al)
        mk=market_probs(mat)
        probs=[mk["1"],mk["X"],mk["2"]]; yy=outcome(m)
        preds.append(probs); y.append(yy); br.append(brier(probs,yy)); ll.append(logloss(probs,yy))
        sc=exact_scores(mat,1)[0][0]
        actual=f'{m["score"]["fullTime"]["home"]}-{m["score"]["fullTime"]["away"]}'
        exact_hits += sc==actual
        actual_o25=(m["score"]["fullTime"]["home"]+m["score"]["fullTime"]["away"])>=3
        o25_hits += (mk["Over 2.5"]>=.5)==actual_o25; o25_n+=1
        actual_btts=m["score"]["fullTime"]["home"]>0 and m["score"]["fullTime"]["away"]>0
        btts_hits += (mk["BTTS Oui"]>=.5)==actual_btts; btts_n+=1
    if not preds: return {"n":0}
    arr=np.array(preds)
    acc=float(np.mean(np.argmax(arr,axis=1)==np.array(y)))
    return {
        "n":len(y),"accuracy":acc,"brier":float(np.mean(br)),"logloss":float(np.mean(ll)),
        "exact_top1":exact_hits/len(y),"over25_acc":o25_hits/max(o25_n,1),
        "btts_acc":btts_hits/max(btts_n,1)
    }

st.title("⚽ RODRIGUE PRO FOOTBALL AI — V21 VALIDATED")
st.caption("Modèle : données disponibles avant le match + shrinkage bayésien + forme pondérée + domicile/extérieur + Poisson corrigé + MT/FT + backtest. Aucune probabilité n'est une garantie.")

api_status=api("/competitions/PL")
if api_status["status"]==200:
    st.success(f"🟢 API football-data.org OK · appels restants : {api_status.get('remaining') or 'N/D'}")
else:
    st.error(f"🔴 API indisponible : HTTP {api_status['status']} — {api_status.get('error') or 'sans détail'}")

c1,c2=st.columns(2)
with c1: d=st.date_input("📅 Date",date.today())
with c2: names=st.multiselect("🏆 Compétitions",list(COMPETITIONS),default=list(COMPETITIONS))
codes=tuple(COMPETITIONS[x] for x in names)

if st.button("🚀 CHERCHER LES MATCHS",type="primary",use_container_width=True):
    if not codes: st.warning("Sélectionne au moins une compétition.")
    elif api_status["status"]!=200: st.error("Recherche arrêtée : API/token indisponible.")
    else:
        with st.spinner("Recherche..."): ms=find_matches(d,codes)
        st.session_state["matches_v21"]=ms
        if ms: st.success(f"✅ {len(ms)} match(s) trouvé(s).")
        else: st.warning("⚠️ Aucun match trouvé pour cette date.")

for i,m in enumerate(st.session_state.get("matches_v21",[])):
    h=m.get("homeTeam",{}).get("name","?")
    aw=m.get("awayTeam",{}).get("name","?")
    comp=m.get("competition",{}).get("name","")
    with st.expander(f"⚽ {h} — {aw} | {comp}"):
        st.caption(f'{m.get("status","")} · {m.get("utcDate","")}')
        if st.button("🧠 ANALYSER CE MATCH",key=f"v21_{m.get('id',i)}",use_container_width=True):
            with st.spinner("Analyse sans fuite de données..."):
                st.session_state[f"r21_{m.get('id',i)}"]=analyze_match(m)
        r=st.session_state.get(f"r21_{m.get('id',i)}")
        if not r: continue
        a1,a2,a3,a4=st.columns(4)
        a1.metric("xG modèle",f'{r["hl"]:.2f} — {r["al"]:.2f}')
        a2.metric("Qualité données",f'{r["quality"]}/85')
        a3.metric("Confiance modèle",f'{r["confidence"]}%')
        a4.metric("H2H",str(r["h2"]["n"]))
        st.info("⚠️ « Confiance modèle » mesure la qualité/séparation du modèle, pas une garantie de gain.")
        st.success(f'🎯 1X2 principal : **{r["one"][0]}** ({pct(r["one"][1])})')
        st.subheader("📈 FORME RÉCENTE")
        st.dataframe(pd.DataFrame([
            {"Équipe":h,"N":r["hf"]["n"],"V-N-D":f'{sum(x=="W" for x in [] )}-{0}-{0}',"GF/m":fmt(r["hf"]["gf"]),"GA/m":fmt(r["hf"]["ga"])},
            {"Équipe":aw,"N":r["af"]["n"],"V-N-D":"voir historique","GF/m":fmt(r["af"]["gf"]),"GA/m":fmt(r["af"]["ga"])}
        ]),use_container_width=True,hide_index=True)
        st.subheader("🎯 MARCHÉS")
        keys=["1","X","2","1X","X2","12","BTTS Oui","BTTS Non","Over 1.5","Under 1.5","Over 2.5","Under 2.5","Over 3.5","Under 3.5"]
        st.dataframe(pd.DataFrame([{"Marché":k,"Probabilité modèle":pct(r["mk"][k])} for k in keys]),use_container_width=True,hide_index=True)
        st.subheader("🔢 SCORES EXACTS")
        st.dataframe(pd.DataFrame([{"Score":s,"Probabilité":pct(p)} for s,p in r["scores"]]),use_container_width=True,hide_index=True)
        st.subheader("⏱️ MI-TEMPS")
        st.dataframe(pd.DataFrame([{"Score MT":s,"Probabilité":pct(p)} for s,p in r["htscores"]]),use_container_width=True,hide_index=True)
        st.subheader("🔄 MT / FT")
        st.dataframe(pd.DataFrame([{"MT/FT":s,"Probabilité":pct(p)} for s,p in r["htft"]]),use_container_width=True,hide_index=True)
        st.subheader("💰 COTES : TEST DE VALEUR")
        cols=st.columns(4); odds={}
        for j,k in enumerate(["1","X","2","Over 2.5"]):
            with cols[j]: odds[k]=st.number_input(f"Cote {k}",0.0,100.0,0.0,.01,key=f"odd21_{m.get('id',i)}_{k}")
        rows=[]
        for k,o in odds.items():
            if o>1:
                evv=r["mk"][k]*o-1
                rows.append({"Marché":k,"p modèle":pct(r["mk"][k]),"Cote":f"{o:.2f}","EV théorique":f"{100*evv:.1f}%","Décision":"À ÉVITER" if evv<=0 else "VALEUR POSSIBLE — À VALIDER"})
        st.dataframe(pd.DataFrame(rows) if rows else pd.DataFrame([{"Marché":"—","Décision":"Aucune cote saisie"}]),use_container_width=True,hide_index=True)

st.divider()
st.subheader("🧪 BACKTEST — AVANT DE FAIRE CONFIANCE AU MODÈLE")
bc1,bc2,bc3=st.columns(3)
with bc1: bt_comp=st.selectbox("Compétition",list(COMPETITIONS),key="bt_comp")
with bc2: bt_year=st.number_input("Saison (année de début)",2018,2030,date.today().year,key="bt_year")
with bc3: bt_limit=st.number_input("Matchs max",50,500,220,10,key="bt_limit")
if st.button("🧪 LANCER LE BACKTEST",use_container_width=True):
    with st.spinner("Backtest chronologique — aucune donnée future utilisée..."):
        res=backtest(COMPETITIONS[bt_comp],int(bt_year),int(bt_limit))
    if res.get("n",0):
        st.dataframe(pd.DataFrame([{
            "Échantillon":res["n"],
            "Accuracy 1X2":pct(res["accuracy"]),
            "Brier (↓ meilleur)":fmt(res["brier"]),
            "Log loss (↓ meilleur)":fmt(res["logloss"]),
            "Score exact top-1":pct(res["exact_top1"]),
            "Over 2.5":pct(res["over25_acc"]),
            "BTTS":pct(res["btts_acc"])
        }]),use_container_width=True,hide_index=True)
        st.warning("Un backtest positif ne garantit pas les prochains matchs. Il sert à détecter si le modèle possède un signal historique réel.")
    else:
        st.warning("Pas assez de données historiques pour calculer un backtest fiable.")

st.caption("Data provided by football-data.org · V21 refuse de transformer une probabilité en garantie.")
