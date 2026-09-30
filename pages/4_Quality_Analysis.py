"""Step 5: Quality Analysis (bridges Pre-processing -> Robust Score)"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import sys, os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import inject_global_css, render_sidebar, PRIMARY
import backend

st.set_page_config(page_title="IQAS - Quality Analysis", page_icon="🛰️", layout="wide")
inject_global_css()
render_sidebar("Quality Analysis")

st.markdown('<div class="step-badge">Step 5: Quality Analysis</div>', unsafe_allow_html=True)
st.markdown("## Quality Analysis")
st.caption("Real, per-pixel quality parameters computed from your (pre-processed) image")

sub_steps = ["Upload Image", "Image Details", "Pre-processing", "Quality Analysis", "Robust Score"]
sub_stepper = '<div class="stepper-wrap">'
for i, label in enumerate(sub_steps, start=1):
    if i < 4:
        circle, lbl, icon = "step-circle step-done", "step-label-done", "✓"
    elif i == 4:
        circle, lbl, icon = "step-circle step-active", "step-label-active", "4"
    else:
        circle, lbl, icon = "step-circle step-inactive", "step-label-inactive", str(i)
    sub_stepper += f'<div class="{circle}">{icon}</div><div class="{lbl}">{label}</div>'
    if i != len(sub_steps):
        sub_stepper += '<div style="width:36px;border-top:2px dashed #D1D5DB;"></div>'
sub_stepper += "</div>"
st.markdown(sub_stepper, unsafe_allow_html=True)

if not backend.has_image():
    st.warning("No image loaded yet. Please go back to **Image Upload** first.")
    st.stop()

with st.spinner("Computing sharpness, contrast, SNR, noise, texture and more..."):
    scores, robust, iso, comparative = backend.run_quality_analysis()

params = pd.DataFrame(
    [(p, scores[p], backend.level_for_score01(scores[p])) for p in backend.PARAM_FUNCS_ORDER],
    columns=["Parameter", "Score (0-1)", "Level"],
)
level_color = {"Excellent": "badge-excellent", "Good": "badge-good", "Moderate": "badge-moderate", "Poor": "badge-moderate"}

col1, col2 = st.columns([1.4, 1])

with col1:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">Computed Quality Parameters</div>', unsafe_allow_html=True)
    hdr = st.columns([2.2, 1.5, 3, 1.5])
    for h, t in zip(hdr, ["Parameter", "Score", "", "Level"]):
        h.markdown(f"**{t}**")
    for _, row in params.iterrows():
        c1, c2, c3, c4 = st.columns([2.2, 1.5, 3, 1.5])
        c1.write(row["Parameter"])
        c2.write(f'{row["Score (0-1)"]:.2f}')
        c3.progress(row["Score (0-1)"])
        c4.markdown(f'<span class="{level_color[row["Level"]]}">{row["Level"]}</span>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

with col2:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">Parameter Radar</div>', unsafe_allow_html=True)
    radar = go.Figure(
        go.Scatterpolar(
            r=params["Score (0-1)"], theta=params["Parameter"], fill="toself",
            line=dict(color=PRIMARY),
        )
    )
    radar.update_layout(polar=dict(radialaxis=dict(range=[0, 1])), height=320, margin=dict(l=20, r=20, t=20, b=20))
    st.plotly_chart(radar, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

st.write("")
fcol1, fcol2, fcol3 = st.columns([1.4, 4, 1.6])
with fcol1:
    st.button("← Back: Pre-processing")
with fcol3:
    if st.button("Next: Robust Score →", type="primary", use_container_width=True):
        st.switch_page("pages/5_Robust_Score.py")
