import math, time
from datetime import date
import numpy as np
import pandas as pd
import requests
import streamlit as st

# ============================================================
# RODRIGUE PRO FOOTBALL AI — V20
# football-data.org v4 / moteur probabiliste / MT-FT / valeur
# ============================================================
API_BASE='https://api.football-data.org/v4'
FOOTBALL_DATA_KEY='d212fb8b550d4756b16521dbe73b708d'
COMPETITIONS={'Premier League':'PL','LaLiga':'PD','Bundesliga':'BL1','Serie A':'SA','Ligue 1':'FL1','Champions League':'CL','Eredivisie':'DED','Primeira Liga':'PPL','Championship':'ELC','Brasileirão':'BSA'}
S=requests.Session(); S.headers.update({'User-Agent':'Rodrigue-Pro-Football-AI-V20','Accept':'application/json'})
st.set_page_config(page_title='Rodrigue Pro Football AI V20',page_icon='⚽',layout='wide')

def sf(x,d=None):
    try:
        x=float(x); return x if math.isfinite(x) else d
    except: return d

def clamp(x,a,b): return max(a,min(b,sf(x,a)))
def pct(x): return 'N/D' if sf(x) is None else f'{100*clamp(x,0,1):.1f}%'
def fmt(x): return 'N/D' if sf(x) is None else f'{x:.2f}'

def _get(ep,params=()):
    try:
        r=S.get(API_BASE+ep,headers={'X-Auth-Token':FOOTBALL_DATA_KEY},params=dict(params),timeout=25)
        try: data=r.json()
        except: data=None
        return {'status':r.status_code,'data':data if r.status_code==200 else None,'error':(data or {}).get('message','') if isinstance(data,dict) else r.text[:400],'remaining':r.headers.get('X-Requests-Available-Minute','')}
    except requests.RequestException as e: return {'status':0,'data':None,'error':str(e),'remaining':''}

@st.cache_data(ttl=300,show_spinner=False)
def api(ep,params=()):
    time.sleep(.12); return _get(ep,params)

def data(ep,params=()):
    r=api(ep,params); return r['data'] if r['status']==200 else None

@st.cache_data(ttl=300,show_spinner=False)
def auth(): return api('/competitions/PL')

def form_rows(matches,tid,n=10):
    out=[]
    for m in matches:
        h=m.get('homeTeam',{}); a=m.get('awayTeam',{}); f=m.get('score',{}).get('fullTime',{})
        hg,ag=f.get('home'),f.get('away')
        if hg is None or ag is None: continue
        if h.get('id')==tid: gf,ga,ven=hg,ag,'H'
        elif a.get('id')==tid: gf,ga,ven=ag,hg,'A'
        else: continue
        out.append({'date':m.get('utcDate',''),'gf':gf,'ga':ga,'r':'W' if gf>ga else 'D' if gf==ga else 'L','venue':ven})
    out.sort(key=lambda x:x['date'],reverse=True); return out[:n]

def form_stats(rows):
    if not rows: return {'matches':0,'wins':0,'draws':0,'losses':0,'gf_avg':0.0,'ga_avg':0.0,'form':.5}
    w=np.array([.94**i for i in range(len(rows))]); gf=np.array([r['gf'] for r in rows]); ga=np.array([r['ga'] for r in rows]); pts=np.array([3 if r['r']=='W' else 1 if r['r']=='D' else 0 for r in rows])
    return {'matches':len(rows),'wins':sum(r['r']=='W' for r in rows),'draws':sum(r['r']=='D' for r in rows),'losses':sum(r['r']=='L' for r in rows),'gf_avg':float(np.average(gf,weights=w)),'ga_avg':float(np.average(ga,weights=w)),'form':float(np.average(pts/3,weights=w))}

@st.cache_data(ttl=900,show_spinner=False)
def history(tid):
    d=data(f'/teams/{tid}/matches',(('status','FINISHED'),('limit','20'))); return (d or {}).get('matches',[])

@st.cache_data(ttl=1800,show_spinner=False)
def table(code):
    d=data(f'/competitions/{code}/standings'); blocks=(d or {}).get('standings',[])
    for b in blocks:
        if b.get('type')=='TOTAL': return b.get('table',[])
    return blocks[0].get('table',[]) if blocks else []

def standing(t,tid):
    return next((r for r in t if r.get('team',{}).get('id')==tid),None)

@st.cache_data(ttl=1800,show_spinner=False)
def get_h2h(mid):
    d=data(f'/matches/{mid}/head2head',(('limit','10'),)); return (d or {}).get('matches',[])

def h2h_signal(ms,hid,aid):
    hw=dr=aw=0
    for m in ms:
        f=m.get('score',{}).get('fullTime',{}); hg,ag=f.get('home'),f.get('away')
        if hg is None or ag is None: continue
        mh=m.get('homeTeam',{}).get('id'); ma=m.get('awayTeam',{}).get('id')
        if mh==hid and ma==aid: x,y=hg,ag
        elif mh==aid and ma==hid: x,y=ag,hg
        else: continue
        if x>y: hw+=1
        elif x==y: dr+=1
        else: aw+=1
    n=hw+dr+aw
    return {'n':n,'home':hw/n if n else .5,'draw':dr/n if n else .25,'away':aw/n if n else .25,'hw':hw,'dr':dr,'aw':aw}

def pois(lam,k):
    lam=sf(lam); k=int(k)
    if lam is None or lam<0 or k<0:return 0
    if lam==0:return 1.0 if k==0 else 0
    return math.exp(-lam+k*math.log(lam)-math.lgamma(k+1))

def matrix(hl,al,n=8):
    a=np.array([pois(hl,i) for i in range(n+1)]); b=np.array([pois(al,i) for i in range(n+1)]); m=np.outer(a,b); m/=m.sum(); return m

def dc(m,hl,al,rho=-.08):
    m=m.copy(); c={(0,0):1-hl*al*rho,(0,1):1+hl*rho,(1,0):1+al*rho,(1,1):1-rho}
    for (h,a),v in c.items():
        if h<m.shape[0] and a<m.shape[1]:m[h,a]*=clamp(v,.85,1.15)
    m=np.maximum(m,0); m/=m.sum(); return m

def markets(m):
    r={'1':0,'X':0,'2':0,'BTTS Oui':0,'Over 1.5':0,'Over 2.5':0,'Over 3.5':0}
    for h in range(m.shape[0]):
        for a in range(m.shape[1]):
            p=float(m[h,a]); r['1' if h>a else 'X' if h==a else '2']+=p
            r['BTTS Oui']+=p if h and a else 0
            r['Over 1.5']+=p if h+a>=2 else 0; r['Over 2.5']+=p if h+a>=3 else 0; r['Over 3.5']+=p if h+a>=4 else 0
    r.update({'1X':r['1']+r['X'],'X2':r['X']+r['2'],'12':r['1']+r['2']})
    for x in ['BTTS','Over 1.5','Over 2.5','Over 3.5']:
        key='BTTS Oui' if x=='BTTS' else x; r[('BTTS Non' if x=='BTTS' else 'Under '+x.split(' ')[1])]=1-r[key]
    return r

def scores(m,n=12):
    z=[(f'{h}-{a}',float(m[h,a])) for h in range(m.shape[0]) for a in range(m.shape[1])]; return sorted(z,key=lambda x:x[1],reverse=True)[:n]

def htft(hl,al):
    ht=dc(matrix(hl*.44,al*.44,6),hl*.44,al*.44); ft=dc(matrix(hl,al,8),hl,al); r={f'{x}/{y}':0 for x in '1X2' for y in '1X2'}
    for h in range(ht.shape[0]):
        for a in range(ht.shape[1]):
            hr='1' if h>a else 'X' if h==a else '2'
            for H in range(ft.shape[0]):
                for A in range(ft.shape[1]):
                    fr='1' if H>A else 'X' if H==A else '2'; r[f'{hr}/{fr}']+=ht[h,a]*ft[H,A]
    return sorted(r.items(),key=lambda x:x[1],reverse=True)

def lambdas(hf,af,hs,as_,hstand,astand,h2):
    ha=.55*hf['gf_avg']+.45*hs['gf_avg']; aa=.55*af['gf_avg']+.45*as_['gf_avg']; hd=.55*af['ga_avg']+.45*as_['ga_avg']; ad=.55*hf['ga_avg']+.45*hs['ga_avg']
    hl=(.60*ha+.40*hd)*1.08*(.92+.16*hf['form']); al=(.60*aa+.40*ad)*.94*(.92+.16*af['form'])
    hp=(hstand or {}).get('position'); ap=(astand or {}).get('position')
    if hp and ap:
        if hp<ap:hl*=1.03;al*=.985
        elif ap<hp:al*=1.03;hl*=.985
    if h2['n']>=3:
        hl*=clamp(.98+.06*(h2['home']-.33),.95,1.03); al*=clamp(.98+.06*(h2['away']-.33),.95,1.03)
    return clamp(hl,.20,3.8),clamp(al,.15,3.5)

def quality(hf,af,hs,as_,hst,ast,h2):
    q=10
    q+=18 if hf['matches']>=8 else 10 if hf['matches']>=5 else 5 if hf['matches']>=3 else 0
    q+=18 if af['matches']>=8 else 10 if af['matches']>=5 else 5 if af['matches']>=3 else 0
    q+=14 if hs['matches']>=5 else 6 if hs['matches']>=2 else 0; q+=14 if as_['matches']>=5 else 6 if as_['matches']>=2 else 0
    q+=16 if hst and ast else 0; q+=10 if h2['n'] else 0
    return int(clamp(q,0,100))

def ev(p,odd):
    return p*odd-1 if odd>1 and p>0 else None

@st.cache_data(ttl=900,show_spinner=False)
def analyze(m):
    h=m.get('homeTeam',{}); a=m.get('awayTeam',{}); hid=h.get('id'); aid=a.get('id'); code=m.get('competition',{}).get('code','')
    hh=history(hid); ah=history(aid); hf=form_stats(form_rows(hh,hid,10)); af=form_stats(form_rows(ah,aid,10)); hs=form_stats([x for x in form_rows(hh,hid,10) if x['venue']=='H']); as_=form_stats([x for x in form_rows(ah,aid,10) if x['venue']=='A'])
    t=table(code); hst=standing(t,hid); ast=standing(t,aid); h2=h2h_signal(get_h2h(m.get('id')),hid,aid)
    hl,al=lambdas(hf,af,hs,as_,hst,ast,h2); mat=dc(matrix(hl,al),hl,al); mk=markets(mat); sc=scores(mat); ht=dc(matrix(hl*.44,al*.44,6),hl*.44,al*.44)
    q=quality(hf,af,hs,as_,hst,ast,h2); one=max((('1',mk['1']),('X',mk['X']),('2',mk['2'])),key=lambda x:x[1])
    return {'home':h.get('name','Domicile'),'away':a.get('name','Extérieur'),'competition':m.get('competition',{}).get('name',''),'status':m.get('status',''),'date':m.get('utcDate',''),'hl':hl,'al':al,'hf':hf,'af':af,'hs':hs,'as':as_,'hst':hst,'ast':ast,'h2':h2,'mk':mk,'scores':sc,'htscores':scores(ht,8),'htmk':markets(ht),'htft':htft(hl,al),'quality':q,'confidence':clamp(50+30*(one[1]-sorted([mk['1'],mk['X'],mk['2']],reverse=True)[1])+.15*q,50,95),'one':one}

def find_matches(d,codes):
    if d==date.today():
        r=api('/matches'); ms=(r['data'] or {}).get('matches',[]) if r['status']==200 else []
        return [m for m in ms if m.get('competition',{}).get('code') in codes and m.get('utcDate','')[:10]==d.isoformat()]
    out=[];seen=set()
    for c in codes:
        r=api(f'/competitions/{c}/matches',(('season',str(d.year)),))
        for m in ((r['data'] or {}).get('matches',[]) if r['status']==200 else []):
            if m.get('utcDate','')[:10]==d.isoformat() and m.get('id') not in seen:seen.add(m.get('id'));out.append(m)
    return sorted(out,key=lambda x:x.get('utcDate',''))

# ============================================================
# UI
# ============================================================
st.title('⚽ RODRIGUE PRO FOOTBALL AI — V20 MAX')
st.caption('Moteur probabiliste : forme pondérée + domicile/extérieur + classement + H2H + Poisson + correction petits scores + MT/FT + contrôle qualité.')
a=auth()
if a['status']==200: st.success(f'🟢 API football-data.org OK · appels restants : {a.get("remaining") or "N/D"}')
else: st.error(f'🔴 API indisponible : HTTP {a["status"]} — {a.get("error") or "sans détail"}')

c1,c2=st.columns(2)
with c1:d=st.date_input('📅 Date',date.today())
with c2:names=st.multiselect('🏆 Compétitions',list(COMPETITIONS),default=list(COMPETITIONS))
codes=tuple(COMPETITIONS[x] for x in names)

if st.button('🚀 CHERCHER LES MATCHS',type='primary',use_container_width=True):
    if not codes: st.warning('Sélectionne au moins une compétition.')
    elif a['status']!=200: st.error('Recherche arrêtée : token/API non valide.')
    else:
        with st.spinner('Recherche...'): ms=find_matches(d,codes)
        st.session_state['matches_v20']=ms
        st.success(f'✅ {len(ms)} match(s) trouvé(s).') if ms else st.warning('Aucun match trouvé pour cette date.')

for i,m in enumerate(st.session_state.get('matches_v20',[])):
    h=m.get('homeTeam',{}).get('name','?'); aw=m.get('awayTeam',{}).get('name','?'); comp=m.get('competition',{}).get('name','')
    with st.expander(f'⚽ {h} — {aw} | {comp}'):
        st.caption(f"{m.get('status','')} · {m.get('utcDate','')}")
        if st.button('🧠 ANALYSER CE MATCH',key=f'v20_{m.get("id",i)}',use_container_width=True):
            with st.spinner('Calcul avancé...'): st.session_state[f'r_{m.get("id",i)}']=analyze(m)
        r=st.session_state.get(f'r_{m.get("id",i)}')
        if not r: continue
        x1,x2,x3,x4=st.columns(4); x1.metric('xG domicile',fmt(r['hl']));x2.metric('xG extérieur',fmt(r['al']));x3.metric('Confiance',f"{r['confidence']:.1f}%");x4.metric('Qualité',f"{r['quality']}/100")
        st.success(f"🎯 1X2 principal : **{r['one'][0]}** ({pct(r['one'][1])})")
        st.subheader('📈 FORME')
        st.dataframe(pd.DataFrame([{'Équipe':h,'V-N-D':f"{r['hf']['wins']}-{r['hf']['draws']}-{r['hf']['losses']}",'GF/m':fmt(r['hf']['gf_avg']),'GA/m':fmt(r['hf']['ga_avg'])},{'Équipe':aw,'V-N-D':f"{r['af']['wins']}-{r['af']['draws']}-{r['af']['losses']}",'GF/m':fmt(r['af']['gf_avg']),'GA/m':fmt(r['af']['ga_avg'])}]),use_container_width=True,hide_index=True)
        st.subheader('🏆 CLASSEMENT / H2H')
        st.write(f"{h} : position {r['hst'].get('position','N/D') if r['hst'] else 'N/D'} · {aw} : position {r['ast'].get('position','N/D') if r['ast'] else 'N/D'}")
        st.write(f"H2H disponibles : {r['h2']['n']} · {h} V {r['h2']['hw']} · N {r['h2']['dr']} · {aw} V {r['h2']['aw']}")
        st.subheader('🎯 1X2 / DOUBLE CHANCE / BUTS')
        st.dataframe(pd.DataFrame([{'Marché':k,'Probabilité':pct(r['mk'][k])} for k in ['1','X','2','1X','X2','12','BTTS Oui','BTTS Non','Over 1.5','Under 1.5','Over 2.5','Under 2.5','Over 3.5','Under 3.5']]),use_container_width=True,hide_index=True)
        st.subheader('🔢 SCORES EXACTS')
        st.dataframe(pd.DataFrame([{'Score':s,'Probabilité':pct(p)} for s,p in r['scores']]),use_container_width=True,hide_index=True)
        st.subheader('⏱️ MI-TEMPS')
        st.dataframe(pd.DataFrame([{'Score MT':s,'Probabilité':pct(p)} for s,p in r['htscores']]),use_container_width=True,hide_index=True)
        htm=r['htmk']; q1,q2,q3=st.columns(3);q1.metric('MT 1',pct(htm['1']));q2.metric('MT X',pct(htm['X']));q3.metric('MT 2',pct(htm['2']))
        st.subheader('🔄 MT / FT')
        st.dataframe(pd.DataFrame([{'MT/FT':s,'Probabilité':pct(p)} for s,p in r['htft']]),use_container_width=True,hide_index=True)
        st.subheader('💰 VALEUR AVEC COTES RÉELLES')
        oc=st.columns(4); odds={}
        for j,k in enumerate(['1','X','2','Over 2.5']):
            with oc[j]: odds[k]=st.number_input(f'Cote {k}',0.0,100.0,0.0,.01,key=f'o_{m.get("id",i)}_{k}')
        rows=[]
        for k,o in odds.items():
            if o>1:
                e=ev(r['mk'][k],o);rows.append({'Marché':k,'Probabilité modèle':pct(r['mk'][k]),'Cote':f'{o:.2f}','EV':f'{100*e:.1f}%' if e is not None else 'N/D','Signal':'VALEUR' if e and e>=.05 else 'PAS DE VALEUR FORTE'})
        if rows:st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)
        else:st.info('Aucune cote saisie : aucune opportunité rentable n’est inventée.')
        st.subheader('🧠 SYNTHÈSE RODRIGUE PRO')
        best=r['scores'][0][0]; mtft=r['htft'][0][0]
        st.markdown(f"**1X2 : {r['one'][0]} · Score : {best} · MT/FT : {mtft} · Qualité : {r['quality']}/100 · Confiance modèle : {r['confidence']:.1f}%**")

st.caption('Data provided by football-data.org')
