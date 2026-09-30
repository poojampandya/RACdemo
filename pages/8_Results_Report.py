"""Step 9: Results & Report (real data, downloadable HTML/CSV report)"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import sys, os
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import inject_global_css, render_sidebar, PRIMARY
import backend

st.set_page_config(page_title="IQAS - Results & Report", page_icon="🛰️", layout="wide")
inject_global_css()
render_sidebar("Results & Reports")

top_l, top_r = st.columns([5, 1])
with top_l:
    st.markdown('<div class="step-badge">Step 9: Results & Report</div>', unsafe_allow_html=True)
    st.markdown("## Results & Report")
    st.caption("Final results summary and report generation")

steps = ["Upload Image", "Image Details", "Pre-processing", "Quality Analysis",
         "Robust Score", "ISO 19157", "Comparative Analysis", "Report"]
current_step = 8
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
if "robust" not in state:
    backend.run_quality_analysis()

raster = state["raster"]
meta = state.get("meta", {})
robust = state["robust"]
scores = state["scores"]
iso = state["iso"]
comp = state["comparative"]
iso_score = sum(d["Score"] for d in iso) / len(iso)

now_str = datetime.now().strftime("%d-%m-%Y %I:%M %p")

col1, col2, col3 = st.columns([1, 1.3, 1.3])

with col1:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">Final Quality Summary</div>', unsafe_allow_html=True)
    gauge = go.Figure(go.Indicator(
        mode="gauge+number", value=robust["overall_score"], number={"font": {"size": 36}},
        gauge={"axis": {"range": [0, 100]}, "bar": {"color": "#1E1B4B", "thickness": 0.25},
               "steps": [{"range": [0, 40], "color": "#EF4444"}, {"range": [40, 60], "color": "#F59E0B"},
                         {"range": [60, 80], "color": "#EAB308"}, {"range": [80, 100], "color": "#22C55E"}]},
    ))
    gauge.update_layout(height=220, margin=dict(l=10, r=10, t=10, b=0))
    st.plotly_chart(gauge, use_container_width=True)
    st.markdown("⭐" * int(round(robust["overall_score"] / 20)) + "✨")
    badge_class = {"Excellent": "badge-excellent", "Good": "badge-good",
                   "Moderate": "badge-moderate", "Poor": "badge-moderate"}[robust["quality_level"]]
    st.markdown(f'<div class="{badge_class}">{robust["quality_level"].upper()}</div>', unsafe_allow_html=True)
    st.write("")
    st.caption(f"Computed from {raster.filename} ({raster.shape[0]}x{raster.shape[1]}, {raster.bands} band(s)).")
    st.markdown("</div>", unsafe_allow_html=True)

with col2:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">Key Results Overview</div>', unsafe_allow_html=True)
    kpis = [
        ("📊", "Robust Image Quality Score", f"{robust['overall_score']} / 100"),
        ("🛡️", "ISO 19157 Alignment Score", f"{iso_score:.2f} / 1.00"),
        ("✅", "Quality Level", robust["quality_level"].upper()),
        ("ℹ️", "Confidence Level", f"{robust['confidence_pct']:.0f}%"),
        ("🏆", "Best Performing Metric", "Proposed Robust Metric (PRQM)"),
        ("🖼️", "Image ID", raster.filename),
        ("🛰️", "Satellite / Sensor", f"{meta.get('satellite','—')} / {meta.get('sensor','—')}"),
        ("📅", "Acquisition Date", meta.get("acquisition_date", "—")),
        ("📄", "Processing Level", meta.get("processing_level", meta.get("file_format", "—"))),
    ]
    kcols = st.columns(3)
    for i, (icon, label, val) in enumerate(kpis):
        with kcols[i % 3]:
            st.markdown(
                f"""<div style="border:1px solid #E5E7EB;border-radius:8px;padding:10px 12px;margin-bottom:10px;">
                <div style="font-size:12px;color:#6B7280;">{icon} {label}</div>
                <div style="font-weight:700;color:#111827;">{val}</div></div>""",
                unsafe_allow_html=True,
            )
    concl = ("The analyzed in-orbit image shows high quality with strong compliance to ISO 19157 "
             "standards and is suitable for most geospatial applications."
             if robust["quality_level"] in ("Excellent", "Good") else
             "The analyzed in-orbit image shows moderate-to-limited quality; review the weaker "
             "parameters before using it for precision applications.")
    st.markdown(f"""<div class="conclusion-box">✅ <b>Overall Conclusion</b><br>{concl}</div>""",
                unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

report_html = f"""
<div style="border:1px solid #E5E7EB;border-radius:8px;padding:16px;">
    <div style="text-align:center;color:#4F46E5;font-weight:800;">IQAS</div>
    <div style="text-align:center;font-size:12px;color:#6B7280;">In-Orbit Image Quality Assessment System (ISO 19157 Aligned)</div>
    <div style="text-align:center;font-weight:700;margin:6px 0;">QUALITY ASSESSMENT REPORT</div>
    <hr>
    <b>IMAGE</b>
    <p style="font-size:13px;">{raster.filename}<br>{meta.get('satellite','—')} / {meta.get('sensor','—')}
    · Acquired {meta.get('acquisition_date','—')}</p>
    <b>SUMMARY OF RESULTS</b>
    <p style="font-size:13px;">
    Robust Image Quality Score: <b>{robust['overall_score']} / 100</b><br>
    ISO 19157 Alignment Score: <b>{iso_score:.2f} / 1.00</b><br>
    Quality Level: <b style="color:#16A34A;">{robust['quality_level'].upper()}</b><br>
    Confidence Level: <b>{robust['confidence_pct']:.0f}%</b>
    </p>
    <b>KEY HIGHLIGHTS</b>
    <p style="font-size:13px;">
    ✅ SSIM (vs. original): {comp['SSIM']:.1f}/100 · PSNR: {comp['PSNR_dB']:.1f} dB<br>
    ✅ ISO 19157 dimensions computed from raster statistics, not fixed values.<br>
    ✅ Proposed robust metric aggregates 9 measured parameters with Huber-robust weighting.<br>
    ✅ Radiometric quality: {scores['Radiometric Quality']:.2f} · Sharpness: {scores['Sharpness']:.2f}
    </p>
</div>
"""

with col3:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">Report Preview</div>', unsafe_allow_html=True)
    st.markdown(report_html, unsafe_allow_html=True)
    st.caption(f"Generated on: {now_str}  ·  IQAS v1.0")
    st.markdown("</div>", unsafe_allow_html=True)

col4, col5 = st.columns([1, 1])

history = backend.load_history()
with col4:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">Score Trend (All Analyzed Images)</div>', unsafe_allow_html=True)
    if history:
        hist_df = pd.DataFrame(history[-10:])
        trend_df = pd.DataFrame({
            "Image": [f"IMG-{i+1:03d}" for i in range(len(hist_df))],
            "Score": hist_df["overall_score"].astype(float),
        })
    else:
        trend_df = pd.DataFrame({"Image": ["IMG-001"], "Score": [robust["overall_score"]]})
    line = go.Figure(go.Scatter(x=trend_df["Image"], y=trend_df["Score"], mode="lines+markers+text",
                                 text=trend_df["Score"], textposition="top center",
                                 line=dict(color=PRIMARY, width=3), marker=dict(size=8, color=PRIMARY)))
    line.update_layout(height=260, margin=dict(l=10, r=10, t=20, b=10), yaxis=dict(range=[0, 100]))
    st.plotly_chart(line, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

with col5:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">Metric Contribution to Final Score</div>', unsafe_allow_html=True)
    contrib = pd.DataFrame(robust["breakdown"])
    contrib["Contribution (%)"] = (contrib["Weighted Score"] / contrib["Weighted Score"].sum() * 100).round(1)
    donut = go.Figure(go.Pie(labels=contrib["Parameter"], values=contrib["Contribution (%)"], hole=0.6, textinfo="none"))
    donut.update_layout(height=240, margin=dict(l=0, r=0, t=0, b=0), showlegend=False,
                         annotations=[dict(text=f"{robust['overall_score']}<br>Final Score", x=0.5, y=0.5, font_size=16, showarrow=False)])
    st.plotly_chart(donut, use_container_width=True)
    for _, row in contrib.iterrows():
        st.markdown(f"● {row['Parameter']} — **{row['Contribution (%)']}%**")
    st.markdown("</div>", unsafe_allow_html=True)

col6, col7 = st.columns([1, 1])

with col6:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">Recommendations</div>', unsafe_allow_html=True)
    recs = []
    if scores["Noise (Inv.)"] < 0.6:
        recs.append("Noise levels are elevated — consider a stronger denoising pass before analysis.")
    if raster.nodata_fraction > 0.05:
        recs.append(f"{raster.nodata_fraction*100:.1f}% of pixels are zero/no-data — mask these before further processing.")
    if scores["Radiometric Quality"] < 0.6:
        recs.append("Radiometric normalization is recommended; the histogram shows clipping or a narrow used range.")
    if scores["Sharpness"] >= 0.7:
        recs.append("Sharpness and edge strength are sufficient for classification, change detection and feature extraction.")
    if not recs:
        recs.append("No critical issues detected — the image is suitable for standard geospatial workflows.")
    for text in recs:
        st.markdown(f'<div class="rec-box">✅ {text}</div>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

with col7:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">Notes</div>', unsafe_allow_html=True)
    for text in [
        "This report is generated based on the proposed robust metric aligned with ISO 19157:2013, "
        "computed directly from your uploaded raster's pixel statistics.",
        "NIQE/BRISQUE-style scores in Comparative Analysis are heuristic approximations, not the "
        "original trained models.",
        "Scores will change if you adjust the pre-processing options in Step 4 and re-run analysis.",
    ]:
        st.markdown(f'<div class="note-box">ℹ️ {text}</div>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown('<div class="card">', unsafe_allow_html=True)
st.markdown('<div class="card-title">Export Report</div>', unsafe_allow_html=True)

full_report_html = f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<title>IQAS Report - {raster.filename}</title></head><body style="font-family:Arial, sans-serif;max-width:800px;margin:auto;">
<h1 style="color:#4F46E5;">IQAS Quality Assessment Report</h1>
<p>Generated: {now_str}</p>
{report_html}
<h3>Quality Parameters</h3>
<table border="1" cellspacing="0" cellpadding="6" style="border-collapse:collapse;">
<tr><th>Parameter</th><th>Score (0-1)</th><th>Level</th></tr>
{''.join(f"<tr><td>{p}</td><td>{v:.3f}</td><td>{backend.level_for_score01(v)}</td></tr>" for p, v in scores.items())}
</table>
<h3>ISO 19157 Dimensions</h3>
<table border="1" cellspacing="0" cellpadding="6" style="border-collapse:collapse;">
<tr><th>Dimension</th><th>Score</th><th>Achievement</th></tr>
{''.join(f"<tr><td>{d['Dimension']}</td><td>{d['Score']:.3f}</td><td>{d['Achievement']}</td></tr>" for d in iso)}
</table>
<h3>Comparative Metrics</h3>
<table border="1" cellspacing="0" cellpadding="6" style="border-collapse:collapse;">
<tr><th>Metric</th><th>Score</th></tr>
<tr><td>PRQM</td><td>{comp['PRQM']}</td></tr>
<tr><td>SSIM</td><td>{comp['SSIM']}</td></tr>
<tr><td>PSNR (dB)</td><td>{comp['PSNR_dB']}</td></tr>
<tr><td>NIQE (Inv., heuristic)</td><td>{comp['NIQE_inv']}</td></tr>
<tr><td>BRISQUE (Inv., heuristic)</td><td>{comp['BRISQUE_inv']}</td></tr>
</table>
</body></html>"""

csv_rows = [{"Parameter": p, "Score_0_1": round(v, 4), "Level": backend.level_for_score01(v)} for p, v in scores.items()]
csv_rows += [{"Parameter": f"ISO: {d['Dimension']}", "Score_0_1": d["Score"], "Level": d["Achievement"]} for d in iso]
csv_df = pd.DataFrame(csv_rows)

ecol1, ecol2, ecol3, ecol4 = st.columns(4)
ecol1.download_button("📕 Download HTML Report", data=full_report_html,
                       file_name=f"IQAS_Report_{raster.filename.split('.')[0]}.html",
                       mime="text/html", use_container_width=True)
ecol2.download_button("📗 Download CSV (all metrics)", data=csv_df.to_csv(index=False),
                       file_name=f"IQAS_Metrics_{raster.filename.split('.')[0]}.csv",
                       mime="text/csv", use_container_width=True)
ecol3.download_button("📘 Download Robust Score Breakdown", data=pd.DataFrame(robust["breakdown"]).to_csv(index=False),
                       file_name=f"IQAS_Breakdown_{raster.filename.split('.')[0]}.csv",
                       mime="text/csv", use_container_width=True)
if history:
    ecol4.download_button("🖼️ Download History (all images)", data=pd.DataFrame(history).to_csv(index=False),
                           file_name="IQAS_History.csv", mime="text/csv", use_container_width=True)
st.markdown("</div>", unsafe_allow_html=True)

st.write("")
fcol1, fcol2, fcol3 = st.columns([1.6, 4, 1.8])
with fcol1:
    st.button("← Back: Comparative Analysis")
with fcol3:
    st.button("💾 Finish (already saved to iqas_history.csv) ✅", type="primary", use_container_width=True)
