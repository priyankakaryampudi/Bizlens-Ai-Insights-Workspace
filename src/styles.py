import streamlit as st

def inject_css():
    st.markdown('''<style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap');
    :root{--ink:#292922;--muted:#716F67;--line:#DED6C8;--brand:#6F7F54;--brand-dark:#53633F;--soft:#F3EEE4;--cream:#F7F3EA;--good:#3F6B57;--warn:#9A6B10}
    html,body,[class*="css"]{font-family:'DM Sans',sans-serif;color:var(--ink)}
    h1,h2,h3,h4{font-family:'Space Grotesk',sans-serif;letter-spacing:-.035em;color:var(--ink)}
    .stApp{background:var(--cream)}
    .block-container{max-width:1420px;padding-top:.75rem;padding-bottom:3rem}
    .hero{padding:.15rem 0 .2rem;margin:0}.hero h1{font-size:2.7rem;line-height:1.06;margin:.2rem 0 .35rem}.hero p{max-width:900px;font-size:1rem;line-height:1.45;color:var(--muted);margin:0}
    [data-testid="stSidebar"]{border-right:1px solid var(--line);background:#F1ECE2}
    [data-testid="stSidebar"] .block-container{padding:1rem 1.15rem}
    [data-testid="stSidebarNav"]{margin-bottom:.15rem}
    [data-testid="stSidebarNav"] > div{margin-bottom:0 !important;margin-top:0 !important;padding-bottom:0 !important}
    [data-testid="stSidebarNav"] ul{gap:.05rem !important;margin:0 0 .15rem 0 !important;padding:0 !important}
    [data-testid="stSidebarNav"] li{margin:0 !important}
    [data-testid="stSidebarNav"] a{border-radius:10px;padding:.32rem .65rem;color:#47463f}
    [data-testid="stSidebarNav"] a[aria-current="page"]{background:#E4DDCE;color:var(--ink);font-weight:700}
    .biz-brand{font-family:'Space Grotesk';font-size:1.55rem;font-weight:700;letter-spacing:-.05em}.biz-brand .dot{color:var(--brand)}.biz-sub{font-size:.76rem;color:var(--muted);margin-bottom:1rem}
    .upload-shell,.card,.source-card,.mini-card,.panel,.finding,.action-card,.ask-box{border:1px solid var(--line);border-radius:16px;background:#FFFDF8;box-shadow:0 6px 22px rgba(50,45,35,.035)}
    .upload-shell{border:1.5px dashed rgba(111,127,84,.38);background:#FBF8F1;padding:1.2rem;margin:.5rem 0 1rem}
    .card{padding:16px;height:100%}.card h3{margin:.2rem 0}.card p{color:var(--muted);line-height:1.45}
    .source-card{padding:14px;height:100%;min-height:110px}.source-icon{font-size:1.1rem;color:var(--brand);margin-bottom:.35rem}.source-name{font-weight:700;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.source-meta,.muted{color:var(--muted);font-size:.82rem}
    .mini-card{padding:15px}.mini-card .label{font-size:.72rem;text-transform:uppercase;letter-spacing:.08em;color:var(--muted)}.mini-card .value{font-family:'Space Grotesk';font-size:1.5rem;font-weight:700;margin:.15rem 0}.mini-card .note{font-size:.78rem;color:var(--muted)}
    .section-head{margin:.72rem 0 .45rem}.section-head h2{margin:0;font-size:1.38rem}.section-head p{color:var(--muted);margin:.12rem 0}
    .finding,.action-card{padding:14px 16px;margin:.5rem 0;line-height:1.5}.warn{padding:11px 13px;border-radius:12px;background:#FFF8DF;border:1px solid #F0DFAA;margin:.45rem 0}.success{padding:11px 13px;border-radius:12px;background:#EFFAF5;border:1px solid #CFE9DC;margin:.55rem 0}.answer-card{padding:18px 20px;margin:.5rem 0 1rem;border:1px solid rgba(111,127,84,.30);border-left:4px solid var(--brand);border-radius:16px;background:#FFFDF8;box-shadow:0 8px 26px rgba(50,45,35,.045)}.answer-head{font-family:'Space Grotesk';font-size:1.16rem;font-weight:700;line-height:1.35}.answer-body{margin-top:.55rem;line-height:1.55;color:#4d4a42}.validation-card{padding:13px 16px;margin:.6rem 0;border:1px solid #E5D8B9;border-radius:14px;background:#FAF5E8;line-height:1.5}.insight-card{padding:15px 18px;margin:.6rem 0;border:1px solid rgba(111,127,84,.25);border-radius:15px;background:#F8F6EF}
    .solution-strip{margin-top:.8rem;padding:.7rem .85rem;border-radius:12px;background:#F3F0E7;border:1px solid var(--line);line-height:1.5;color:#4d4a42}.eyebrow{display:block;color:var(--brand);font-size:.72rem;font-weight:700;letter-spacing:.11em;text-transform:uppercase;margin-bottom:.35rem}.pill{display:inline-block;border:1px solid rgba(111,127,84,.28);background:rgba(111,127,84,.08);color:var(--brand);border-radius:999px;padding:.32rem .62rem;font-size:.72rem;font-weight:700;letter-spacing:.05em;margin:.15rem .2rem .15rem 0}
    .footer-note{margin-top:1rem;text-align:center;color:#888;font-size:.75rem}.ask-examples{padding:12px 14px;margin:.35rem 0 .75rem;border:1px solid var(--line);border-radius:14px;background:#FBF8F1}.evidence-used{padding:11px 14px;margin:.55rem 0;border:1px solid rgba(111,127,84,.22);border-radius:12px;background:#F8F6EF;line-height:1.55}.doc-cover .small-note{margin-top:.35rem}.big-answer{font-size:1.02rem;line-height:1.75;padding:18px 20px}
    .stButton>button{border-radius:12px}.stTextArea textarea{border-radius:14px}.stSelectbox div[data-baseweb=select]{border-radius:10px}
    .doc-cover{padding:20px;border:1px solid var(--line);border-radius:16px;background:#FBF8F1}
    .stepbar{display:flex;gap:7px;align-items:center;margin:.5rem 0 1rem}.stepbar span{font-size:.78rem;color:var(--muted);padding:.4rem .55rem;border-radius:999px;background:var(--soft)}.stepbar .active{color:var(--brand);background:rgba(111,127,84,.10);font-weight:700}.small-note{font-size:.78rem;color:var(--muted)}
    </style>''', unsafe_allow_html=True)

def brand():
    st.markdown('<div class="biz-brand">Biz<span class="dot">Lens</span></div><div class="biz-sub">AI-assisted Business Analysis Workspace</div>', unsafe_allow_html=True)

def hero(kicker,title,body):
    st.markdown(f'<div class="hero"><div class="eyebrow">{kicker}</div><h1>{title}</h1><p>{body}</p></div>', unsafe_allow_html=True)

def section_head(title,body=''):
    st.markdown(f'<div class="section-head"><h2>{title}</h2><p>{body}</p></div>', unsafe_allow_html=True)
