"""Step 6: Robust Image Quality Score (real, computed from uploaded image)"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import sys, os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import inject_global_css, render_sidebar, PRIMARY
import backend

st.set_page_config(page_title="IQAS - Robust Score", page_icon="🛰️", layout="wide")
inject_global_css()
render_sidebar("Robust Score")

top_l, top_r = st.columns([5, 1])
with top_l:
    st.markdown('<div class="step-badge">Step 6: Robust Image Quality Score</div>', unsafe_allow_html=True)
    st.markdown("## Robust Image Quality Score")
    st.caption("Overall quality score using the proposed robust metric (Huber-weighted, ISO 19157 aligned)")
with top_r:
    st.button("⬇ Export Result", use_container_width=True)

steps = ["Upload Image", "Image Details", "Pre-processing", "Quality Analysis", "Robust Score", "ISO 19157"]
current_step = 5
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
        stepper_html += '<div style="width:24px;border-top:2px dashed #D1D5DB;"></div>'
stepper_html += "</div>"
st.markdown(stepper_html, unsafe_allow_html=True)

if not backend.has_image():
    st.warning("No image loaded yet. Please go back to **Image Upload** first.")
    st.stop()

state = backend.get_state()
if "robust" not in state:
    backend.run_quality_analysis()

robust = state["robust"]
scores = state["scores"]
overall_score = robust["overall_score"]
quality_level = robust["quality_level"]

breakdown = pd.DataFrame(robust["breakdown"])

history = backend.load_history()
if history:
    hist_df = pd.DataFrame(history[-10:])
    trend_df = pd.DataFrame({
        "Image": [f"IMG-{i+1:03d}" for i in range(len(hist_df))],
        "Score": hist_df["overall_score"].astype(float),
    })
else:
    trend_df = pd.DataFrame({"Image": ["IMG-001"], "Score": [overall_score]})

col1, col2, col3 = st.columns([1, 1.4, 1.1])

with col1:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">Robust Image Quality Score</div>', unsafe_allow_html=True)
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=overall_score, number={"font": {"size": 40}},
        gauge={"axis": {"range": [0, 100]}, "bar": {"color": "#1E1B4B", "thickness": 0.25},
               "steps": [{"range": [0, 40], "color": "#EF4444"}, {"range": [40, 60], "color": "#F59E0B"},
                         {"range": [60, 80], "color": "#EAB308"}, {"range": [80, 100], "color": "#22C55E"}]},
    ))
    fig.update_layout(height=230, margin=dict(l=10, r=10, t=10, b=0))
    st.plotly_chart(fig, use_container_width=True)
    stars = "⭐" * int(round(overall_score / 20)) + "✨"
    st.markdown(stars)
    badge_class = {"Excellent": "badge-excellent", "Good": "badge-good",
                   "Moderate": "badge-moderate", "Poor": "badge-moderate"}[quality_level]
    st.markdown(f'<div class="{badge_class}">{quality_level.upper()}</div>', unsafe_allow_html=True)
    st.write("")
    captions = {
        "Excellent": "The image quality is excellent and suitable for all geospatial applications.",
        "Good": "The image quality is good and suitable for most geospatial applications.",
        "Moderate": "The image quality is moderate; some applications may be limited.",
        "Poor": "The image quality is poor; results should be used with caution.",
    }
    st.caption(captions[quality_level])
    st.markdown("</div>", unsafe_allow_html=True)

with col2:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">Score Breakdown (Weighted Parameters)</div>', unsafe_allow_html=True)
    header = st.columns([2.2, 1, 1, 2, 1.2])
    for h, txt in zip(header, ["Parameter", "Weight (%)", "Score (0-1)", "", "Weighted"]):
        h.markdown(f"**{txt}**")
    for _, row in breakdown.iterrows():
        c1, c2, c3, c4, c5 = st.columns([2.2, 1, 1, 2, 1.2])
        c1.write(row["Parameter"]); c2.write(f'{row["Weight (%)"]}')
        c3.write(f'{row["Score (0-1)"]:.2f}'); c4.progress(min(max(row["Score (0-1)"], 0.0), 1.0))
        c5.write(f'{row["Weighted Score"]:.3f}')
    st.markdown("---")
    tot1, tot2, tot3 = st.columns([2.2, 1, 2.2])
    tot1.markdown("**Total**"); tot2.markdown(f'**{breakdown["Weight (%)"].sum():.0f}**')
    tot3.markdown(f'**{breakdown["Weighted Score"].sum():.3f}**')
    st.markdown("</div>", unsafe_allow_html=True)

with col3:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">Quality Level Interpretation</div>', unsafe_allow_html=True)
    interp = [
        ("#F0FDF4", "✅", "Excellent (0.80 – 1.00)", "Image quality is excellent for all applications."),
        ("#ECFDF5", "✅", "Good (0.60 – 0.79)", "Image quality is good for most applications."),
        ("#FFFBEB", "⚠️", "Moderate (0.40 – 0.59)", "Image quality is moderate, may have limitations."),
        ("#FEF2F2", "❌", "Poor (0.00 – 0.39)", "Image quality is poor, not recommended."),
    ]
    for bg, icon, title, desc in interp:
        st.markdown(
            f"""<div style="background:{bg};border-radius:8px;padding:10px 14px;margin-bottom:10px;">
            <b>{icon} {title}</b><br><span style="font-size:12px;color:#4B5563;">{desc}</span></div>""",
            unsafe_allow_html=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)

col4, col5, col6 = st.columns([1, 1.4, 1.1])

with col4:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">Score Contribution (%)</div>', unsafe_allow_html=True)
    contrib = breakdown.copy()
    contrib["Contribution (%)"] = (contrib["Weighted Score"] / contrib["Weighted Score"].sum() * 100).round(1)
    donut = go.Figure(go.Pie(labels=contrib["Parameter"], values=contrib["Contribution (%)"], hole=0.6, textinfo="none"))
    donut.update_layout(height=260, margin=dict(l=0, r=0, t=0, b=0), showlegend=False,
                         annotations=[dict(text=f"{overall_score}<br>Total Score", x=0.5, y=0.5, font_size=16, showarrow=False)])
    st.plotly_chart(donut, use_container_width=True)
    for _, row in contrib.iterrows():
        st.markdown(f"<span style='font-size:13px;'>● {row['Parameter']} — {row['Contribution (%)']}%</span>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

with col5:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">Score Trend (All Analyzed Images)</div>', unsafe_allow_html=True)
    line = go.Figure(go.Scatter(x=trend_df["Image"], y=trend_df["Score"], mode="lines+markers+text",
                                 text=trend_df["Score"], textposition="top center",
                                 line=dict(color=PRIMARY, width=3), marker=dict(size=8, color=PRIMARY)))
    line.update_layout(height=280, margin=dict(l=10, r=10, t=30, b=10),
                        yaxis=dict(range=[0, 100], title="Quality Score"), xaxis=dict(title="Image Index"))
    st.plotly_chart(line, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

with col6:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">Robust Score Summary</div>', unsafe_allow_html=True)
    for label, val in [
        ("Robust Quality Score", f"{overall_score} / 100"), ("Quality Level", quality_level.upper()),
        ("Confidence Level", f"High ({robust['confidence_pct']:.0f}%)" if robust['confidence_pct'] >= 80
         else f"Moderate ({robust['confidence_pct']:.0f}%)"),
        ("Metric Used", "Proposed Robust Metric (PRQM)"),
        ("Alignment", "ISO 19157 Aligned ✅"),
    ]:
        c1, c2 = st.columns([1.3, 1]); c1.write(label); c2.markdown(f"**{val}**")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">Key Strengths & Weaknesses</div>', unsafe_allow_html=True)
    sorted_params = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    strengths = [p for p, v in sorted_params if v >= 0.75][:4]
    weaknesses = [p for p, v in sorted_params if v < 0.6][-4:]
    sw1, sw2 = st.columns(2)
    with sw1:
        lines = "".join(f"✔ {p} ({scores[p]:.2f})<br>" for p in strengths) or "No standout strengths above 0.75."
        st.markdown(f"""<div style="background:#F0FDF4;border-radius:8px;padding:12px 14px;font-size:13px;">
        <b>✅ Strengths</b><br>{lines}</div>""", unsafe_allow_html=True)
    with sw2:
        lines = "".join(f"• {p} ({scores[p]:.2f})<br>" for p in weaknesses) or "No parameters below 0.60."
        st.markdown(f"""<div style="background:#FFFBEB;border-radius:8px;padding:12px 14px;font-size:13px;">
        <b>⚠️ Weaknesses</b><br>{lines}</div>""", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

st.write("")
with st.expander("🤖 ML-Based Robust Score Estimator (experimental — alternative estimation method)"):
    st.caption(
        "Trains a small regressor on synthetically-distorted versions of THIS image "
        "(blur / noise / contrast-loss / quantization at known severities), then predicts "
        "a quality score from the same feature set used by the classical formula above. "
        "This is the learning-based estimator being compared against the fixed-weight "
        "Huber/MAD formula for the 'suitable methods for estimation' part of the study."
    )
    ml_result = backend.ml_robust_score(state.get("processed_gray"), state["raster"].bit_depth)
    mcol1, mcol2 = st.columns([1, 1.6])
    with mcol1:
        st.metric("ML-Estimated Score", f"{ml_result['ml_overall_score']} / 100",
                   delta=f"{ml_result['ml_overall_score'] - overall_score:+.1f} vs classical PRQM")
        st.caption(f"Model: {ml_result['backend']} · trained on {ml_result['n_training_samples']} synthetic samples")
    with mcol2:
        fi_df = pd.DataFrame(
            [{"Feature": k, "Learned Importance": v} for k, v in ml_result["feature_importance"].items()]
        ).sort_values("Learned Importance", ascending=False)
        st.markdown("**Learned feature importance** (vs. the classical formula's fixed weights):")
        st.dataframe(fi_df, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.markdown("**Held-out evaluation (RAC-4 requirement): RMSE / MAE / R² + runtime**")
    st.caption(
        "The metrics below are computed on a held-out test split of the synthetic-distortion "
        "samples — i.e. samples the model did NOT see during training — so this is a genuine "
        "generalization check, not a training-set fit."
    )
    ml_eval = backend.get_or_compute_ml_eval()
    if ml_eval:
        e1, e2, e3, e4 = st.columns(4)
        e1.metric("RMSE", ml_eval["rmse"], help="Root Mean Squared Error, lower is better (0 = perfect)")
        e2.metric("MAE", ml_eval["mae"], help="Mean Absolute Error, lower is better (0 = perfect)")
        e3.metric("R² Score", ml_eval["r2"], help="Coefficient of determination, closer to 1 is better")
        e4.metric("Runtime", f"{ml_eval['runtime_sec']}s", help="Wall-clock time to train + evaluate")
        st.caption(
            f"Trained on {ml_eval['n_train']} synthetic samples, tested on {ml_eval['n_test']} held-out "
            f"samples · Model: {ml_eval['backend']}"
        )
    else:
        st.info("Upload and pre-process an image to run the held-out evaluation.")

fcol1, fcol2, fcol3 = st.columns([1.3, 4, 1.6])
with fcol1:
    st.button("← Back: Quality Analysis")
with fcol3:
    if st.button("Next: ISO 19157 Alignment →", type="primary", use_container_width=True):
        st.switch_page("pages/6_ISO19157_Alignment.py")
