"""Step 8: Comparative Analysis (real SSIM/PSNR + heuristic naturalness proxies)"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import sys, os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import inject_global_css, render_sidebar, PRIMARY
import backend

st.set_page_config(page_title="IQAS - Comparative Analysis", page_icon="🛰️", layout="wide")
inject_global_css()
render_sidebar("Comparative Analysis")

top_l, top_r = st.columns([5, 1])
with top_l:
    st.markdown('<div class="step-badge">Step 8: Comparative Analysis</div>', unsafe_allow_html=True)
    st.markdown("## Comparative Analysis")
    st.caption("Compare the proposed robust metric with classical image quality metrics")
with top_r:
    st.button("⬇ Export Comparison Report", use_container_width=True)

steps = ["Upload Image", "Image Details", "Pre-processing", "Quality Analysis",
         "Robust Score", "ISO 19157", "Comparative Analysis", "Report"]
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
if "comparative" not in state:
    backend.run_quality_analysis()

comp = state["comparative"]
scores = state["scores"]
robust = state["robust"]

st.info(
    "**Methodology note:** *PRQM* (Proposed Robust Metric) is the composite score computed in the previous "
    "steps from real pixel statistics. *SSIM* and *PSNR* are computed exactly, comparing the original vs. "
    "pre-processed image using `scikit-image`. *NIQE (Inv.)* and *BRISQUE (Inv.)* here are lightweight, "
    "no-reference naturalness heuristics inspired by those metrics' MSCN-coefficient statistics — they are "
    "**not** the original trained NIQE/BRISQUE models (those require pretrained parameter sets), so treat "
    "them as approximations for relative comparison only.",
    icon="ℹ️",
)

metrics_names = ["Proposed Robust Metric\n(PRQM)", "SSIM", "PSNR", "NIQE\n(Inv., heuristic)", "BRISQUE\n(Inv., heuristic)"]
metrics_scores = [comp["PRQM"], comp["SSIM"], comp["PSNR_score"], comp["NIQE_inv"], comp["BRISQUE_inv"]]
colors = [PRIMARY, "#3B82F6", "#22C55E", "#F59E0B", "#14B8A6"]

col1, col2 = st.columns([1.3, 1])

with col1:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">Overall Comparison (Higher is Better)</div>', unsafe_allow_html=True)
    bar = go.Figure(go.Bar(x=metrics_names, y=metrics_scores, marker_color=colors, text=metrics_scores, textposition="outside"))
    bar.update_layout(height=340, margin=dict(l=10, r=10, t=20, b=10), yaxis=dict(range=[0, 100], title="Quality Score (0-100)"))
    st.plotly_chart(bar, use_container_width=True)
    st.caption(f"Raw PSNR: {comp['PSNR_dB']:.2f} dB (scaled to /100 above using a 50 dB reference ceiling).")
    st.markdown("</div>", unsafe_allow_html=True)

with col2:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">PRQM Parameter Radar (real, per-parameter)</div>', unsafe_allow_html=True)
    radar_params = list(scores.keys())
    radar_vals = [v * 100 for v in scores.values()]
    radar = go.Figure()
    radar.add_trace(go.Scatterpolar(r=radar_vals, theta=radar_params, name="Proposed Robust Metric",
                                     fill="toself", line=dict(color=PRIMARY)))
    radar.update_layout(polar=dict(radialaxis=dict(range=[0, 100])), height=300, margin=dict(l=10, r=10, t=10, b=10),
                         showlegend=True, legend=dict(orientation="h", y=-0.2))
    st.plotly_chart(radar, use_container_width=True)
    st.caption("Classical metrics (SSIM/PSNR/NIQE/BRISQUE) are whole-image scores and don't natively decompose "
               "per quality parameter, so only PRQM is shown per-parameter here.")
    st.markdown("</div>", unsafe_allow_html=True)

col3, col4 = st.columns([1.6, 1])

with col3:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">Detailed Metric Comparison</div>', unsafe_allow_html=True)
    detail = pd.DataFrame([
        ("PRQM (Proposed)", robust["overall_score"], robust["quality_level"]),
        ("SSIM (x100)", comp["SSIM"], backend.level_for_score100(comp["SSIM"])),
        (f"PSNR ({comp['PSNR_dB']:.1f} dB, scaled)", comp["PSNR_score"], backend.level_for_score100(comp["PSNR_score"])),
        ("NIQE (Inv., heuristic)", comp["NIQE_inv"], backend.level_for_score100(comp["NIQE_inv"])),
        ("BRISQUE (Inv., heuristic)", comp["BRISQUE_inv"], backend.level_for_score100(comp["BRISQUE_inv"])),
    ], columns=["Metric", "Score (0-100)", "Level"])
    st.dataframe(detail, use_container_width=True, hide_index=True)
    st.caption("Note: SSIM/PSNR compare the original image to the pre-processed image from Step 4 "
               "(they need a reference — here the reference is your own original upload).")
    st.markdown("</div>", unsafe_allow_html=True)

with col4:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">Average Performance Summary</div>', unsafe_allow_html=True)
    labels = ["PRQM", "SSIM", "NIQE (Inv.)", "BRISQUE (Inv.)", "PSNR"]
    values = [comp["PRQM"], comp["SSIM"], comp["NIQE_inv"], comp["BRISQUE_inv"], comp["PSNR_score"]]
    donut = go.Figure(go.Pie(labels=labels, values=[max(v, 0.01) for v in values],
                              marker=dict(colors=[PRIMARY, "#3B82F6", "#F59E0B", "#14B8A6", "#22C55E"]), hole=0.6, textinfo="none"))
    best_label = labels[values.index(max(values))]
    donut.update_layout(height=240, margin=dict(l=0, r=0, t=0, b=0), showlegend=False,
                         annotations=[dict(text=f"{max(values):.1f}<br>Best ({best_label})", x=0.5, y=0.5, font_size=14, showarrow=False)])
    st.plotly_chart(donut, use_container_width=True)
    for name, val in zip(labels, values):
        st.markdown(f"● {name} — **{val:.1f}**")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">Key Insights</div>', unsafe_allow_html=True)
    insights = []
    if comp["PRQM"] >= max(comp["SSIM"], comp["NIQE_inv"], comp["BRISQUE_inv"], comp["PSNR_score"]):
        insights.append(("✅", "Proposed Robust Metric achieves the highest overall quality score for this image."))
    else:
        insights.append(("ℹ️", f"{best_label} scored highest for this particular image — PRQM remains the "
                                "recommended standard as it directly aggregates 9 measured parameters."))
    top_params = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)[:3]
    insights.append(("✅", f"Strongest measured parameters: {', '.join(p for p, _ in top_params)}."))
    insights.append(("ℹ️", "SSIM/PSNR reflect similarity to the original upload; they naturally rise as "
                             "pre-processing is tuned to be gentle, and fall with aggressive enhancement."))
    insights.append(("⭐", "PRQM is the most interpretable metric for in-orbit imagery since it's built "
                             "directly from ISO 19157-aligned parameters."))
    for icon, text in insights:
        st.markdown(f'<div class="rec-box">{icon} {text}</div>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

st.write("")
fcol1, fcol2, fcol3 = st.columns([1.5, 4, 1.6])
with fcol1:
    st.button("← Back: ISO 19157 Alignment")
with fcol3:
    if st.button("Next: Results & Reports →", type="primary", use_container_width=True):
        st.switch_page("pages/8_Results_Report.py")
