"""Step 7: ISO 19157 Alignment (real, computed from uploaded image)"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import sys, os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import inject_global_css, render_sidebar, PRIMARY
import backend

st.set_page_config(page_title="IQAS - ISO 19157 Alignment", page_icon="🛰️", layout="wide")
inject_global_css()
render_sidebar("ISO 19157 Alignment")

top_l, top_r = st.columns([5, 1])
with top_l:
    st.markdown('<div class="step-badge">Step 7: ISO 19157 Alignment</div>', unsafe_allow_html=True)
    st.markdown("## ISO 19157 Alignment")
    st.caption("Data quality dimensions per ISO 19157:2013, computed from your image")
with top_r:
    st.button("⬇ Export Alignment Report", use_container_width=True)

steps = ["Upload Image", "Image Details", "Pre-processing", "Quality Analysis",
         "Robust Score", "Estimation Methods", "ISO 19157", "Comparison"]
current_step = 7
stepper_html = '<div class="stepper-wrap">'
for i, label in enumerate(steps, start=1):
    if i < current_step:
        circle, lbl, icon = "step-circle step-done", "step-label-done", "✓"
    elif i == current_step:
        circle, lbl, icon = "step-circle step-active", "step-label-active", str(i)
    else:
        circle, lbl, icon = "step-circle step-inactive", "step-label-inactive", str(i)
    stepper_html += f'<div class="{circle}">{icon}</div><div class="{lbl}">{label}</div>'
    if i != len(steps):
        stepper_html += '<div style="width:16px;border-top:2px dashed #D1D5DB;"></div>'
stepper_html += "</div>"
st.markdown(stepper_html, unsafe_allow_html=True)

if not backend.has_image():
    st.warning("No image loaded yet. Please go back to **Image Upload** first.")
    st.stop()

state = backend.get_state()
if "iso" not in state:
    backend.run_quality_analysis()

dims = pd.DataFrame(state["iso"])
badge_map = {"Excellent": "badge-excellent", "Good": "badge-good", "Moderate": "badge-moderate", "Poor": "badge-moderate"}
overall_iso = dims["Score"].mean()
overall_level = backend.level_for_score01(overall_iso)

col1, col2 = st.columns([1.6, 1])

with col1:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">ISO 19157 Data Quality Dimensions</div>', unsafe_allow_html=True)
    hdr = st.columns([2, 3, 1, 2, 1.3])
    for h, t in zip(hdr, ["Dimension", "Description", "Score", "", "Achievement"]):
        h.markdown(f"**{t}**")
    for _, row in dims.iterrows():
        c1, c2, c3, c4, c5 = st.columns([2, 3, 1, 2, 1.3])
        c1.write(f'{row["Icon"]} {row["Dimension"]}')
        c2.caption(row["Description"])
        c3.write(f'{row["Score"]:.2f}')
        c4.progress(min(max(row["Score"], 0.0), 1.0))
        c5.markdown(f'<span class="{badge_map[row["Achievement"]]}">{row["Achievement"]}</span>', unsafe_allow_html=True)
    st.markdown("---")
    tot1, tot2 = st.columns([4, 2])
    tot1.markdown("**Overall ISO 19157 Alignment Score**")
    tot2.markdown(f'**{overall_iso:.2f} / 1.00 — {overall_level}**')
    st.markdown("</div>", unsafe_allow_html=True)

with col2:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">ISO 19157 Alignment Radar</div>', unsafe_allow_html=True)
    radar = go.Figure(go.Scatterpolar(r=dims["Score"], theta=dims["Dimension"], fill="toself", line=dict(color=PRIMARY)))
    radar.update_layout(polar=dict(radialaxis=dict(range=[0, 1])), height=260, margin=dict(l=20, r=20, t=20, b=20))
    st.plotly_chart(radar, use_container_width=True)

    m1, m2 = st.columns(2)
    m1.markdown("**Alignment Level**")
    color = {"Excellent": "#16A34A", "Good": "#2563EB", "Moderate": "#D97706", "Poor": "#DC2626"}[overall_level]
    m1.markdown(f'<span style="color:{color};font-weight:800;">{overall_level.upper()} {"✅" if overall_level in ("Excellent","Good") else "⚠️"}</span>', unsafe_allow_html=True)
    m2.markdown("**Alignment Score**"); m2.markdown(f'**{overall_iso:.2f} / 1.00**')
    st.markdown("</div>", unsafe_allow_html=True)

col3, col4, col5 = st.columns([1.4, 1, 1.2])

with col3:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">Dimension-wise Details</div>', unsafe_allow_html=True)
    details = dims[["Dimension", "Metric Used", "Score", "Interpretation"]].rename(columns={"Score": "Result"})
    st.dataframe(details, use_container_width=True, hide_index=True)
    st.caption("ℹ️ All dimensions are evaluated based on ISO 19157:2013 standard for geographic information data quality, "
               "using metrics computed directly from the uploaded raster.")
    st.markdown("</div>", unsafe_allow_html=True)

with col4:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">Alignment Summary</div>', unsafe_allow_html=True)
    gauge = go.Figure(go.Indicator(
        mode="gauge+number", value=overall_iso,
        number={"suffix": " of 1.00", "font": {"size": 22}},
        gauge={"axis": {"range": [0, 1]}, "bar": {"color": "#16A34A"},
               "steps": [{"range": [0, 0.4], "color": "#FEE2E2"}, {"range": [0.4, 0.6], "color": "#FEF3C7"},
                         {"range": [0.6, 0.8], "color": "#DCFCE7"}, {"range": [0.8, 1], "color": "#BBF7D0"}]},
    ))
    gauge.update_layout(height=200, margin=dict(l=10, r=10, t=10, b=0))
    st.plotly_chart(gauge, use_container_width=True)

    counts = dims["Achievement"].value_counts(normalize=True).reindex(
        ["Excellent", "Good", "Moderate", "Poor"], fill_value=0) * 100
    st.markdown("  \n".join(f"● {lvl} — {pct:.1f}%" for lvl, pct in counts.items()))
    concl = ("✅ The image quality is highly aligned with ISO 19157:2013 standard."
             if overall_level in ("Excellent", "Good") else
             "⚠️ The image shows only partial alignment with ISO 19157:2013 — review the weaker dimensions.")
    st.markdown(f'<div class="conclusion-box">{concl}</div>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

with col5:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">Recommendations</div>', unsafe_allow_html=True)
    for _, row in dims.iterrows():
        if row["Score"] >= 0.80:
            icon, text = "✅", f"{row['Dimension']} is excellent. No action required."
        elif row["Score"] >= 0.60:
            icon, text = "ℹ️", f"{row['Dimension']} is good. Further refinement can improve results."
        else:
            icon, text = "⚠️", f"{row['Dimension']} needs improvement — see interpretation above."
        st.markdown(f'<div class="rec-box">{icon} {text}</div>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

st.write("")
fcol1, fcol2, fcol3 = st.columns([1.3, 4, 1.8])
with fcol1:
    st.button("← Back: Robust Score")
with fcol3:
    if st.button("Next: Comparative Analysis →", type="primary", use_container_width=True):
        st.switch_page("pages/7_Comparative_Analysis.py")
