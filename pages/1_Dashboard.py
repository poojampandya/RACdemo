"""Step 2: Dashboard (reads real analysis history from backend.iqas_history.csv)"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import sys, os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import inject_global_css, render_sidebar, PRIMARY
import backend

st.set_page_config(page_title="IQAS - Dashboard", page_icon="🛰️", layout="wide")
inject_global_css()
render_sidebar("Dashboard")

st.markdown('<div class="step-badge">Step 2: Dashboard</div>', unsafe_allow_html=True)
st.markdown("## Dashboard")
st.caption("Overview of In-Orbit Image Quality Assessment (live data from analyses run on this machine)")

history = backend.load_history()

if not history:
    st.info("No images have been analyzed yet. Go to **Image Upload** to analyze your first image — "
             "the dashboard fills in automatically once you complete a Robust Score run.")
    hist_df = pd.DataFrame(columns=backend.HISTORY_FIELDS)
else:
    hist_df = pd.DataFrame(history)
    hist_df["overall_score"] = hist_df["overall_score"].astype(float)
    hist_df["iso_score"] = hist_df["iso_score"].astype(float)

total_images = len(hist_df)
avg_score = hist_df["overall_score"].mean() if total_images else 0.0
n_datasets = hist_df["satellite"].nunique() if total_images else 0

kpis = [
    ("🖼️", "Total Images Analyzed", str(total_images), "#EEF2FF"),
    ("✅", "Analyzed Images", str(total_images), "#EFF6FF"),
    ("⭐", "Avg. Quality Score", f"{avg_score:.1f} /100" if total_images else "—", "#ECFDF5"),
    ("🗄️", "Distinct Satellites", str(n_datasets), "#FFFBEB"),
    ("📄", "Reports Generated", str(total_images), "#FEF2F2"),
]
kpi_cols = st.columns(5)
for col, (icon, label, value, bg) in zip(kpi_cols, kpis):
    with col:
        st.markdown(
            f"""
            <div class="kpi-card" style="background:{bg};">
                <div style="font-size:20px;">{icon}</div>
                <div class="kpi-label">{label}</div>
                <div class="kpi-value">{value}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

st.write("")
col1, col2 = st.columns([1.6, 1.4])

with col1:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    hc1, hc2 = st.columns([3, 1])
    hc1.markdown('<div class="card-title">Recent Analysis</div>', unsafe_allow_html=True)
    hc2.button("View All", use_container_width=True)

    badge_map = {"Excellent": "badge-excellent", "Good": "badge-good", "Moderate": "badge-moderate", "Poor": "badge-moderate"}

    if total_images:
        recent = hist_df.tail(5).iloc[::-1]
        hdr = st.columns([2.2, 1.4, 1.2, 1.2, 1.2])
        for h, t in zip(hdr, ["Image Name", "Satellite", "Date", "Quality Score", "Quality Level"]):
            h.markdown(f"**{t}**")
        for _, row in recent.iterrows():
            c1, c2, c3, c4, c5 = st.columns([2.2, 1.4, 1.2, 1.2, 1.2])
            c1.write(f"🖼️ {row['image_name']}")
            c2.write(row["satellite"] or "—")
            c3.write((row["date"] or row["timestamp"])[:10])
            c4.write(f"{row['overall_score']:.1f}")
            c5.markdown(f'<span class="{badge_map.get(row["quality_level"], "badge-moderate")}">{row["quality_level"]}</span>',
                        unsafe_allow_html=True)
    else:
        st.caption("No analyses yet.")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">Quality Level Distribution</div>', unsafe_allow_html=True)
    if total_images:
        counts = hist_df["quality_level"].value_counts().reindex(
            ["Excellent", "Good", "Moderate", "Poor"], fill_value=0)
        dist = pd.DataFrame({"Level": counts.index, "Count": counts.values})
    else:
        dist = pd.DataFrame({"Level": ["Excellent", "Good", "Moderate", "Poor"], "Count": [0, 0, 0, 0]})
    donut = go.Figure(
        go.Pie(
            labels=dist["Level"], values=dist["Count"], hole=0.6,
            marker=dict(colors=["#3B82F6", "#22C55E", "#F59E0B", "#EF4444"]),
            textinfo="none" if total_images else "none",
        )
    )
    donut.update_layout(
        height=260, margin=dict(l=0, r=0, t=0, b=0), showlegend=True,
        annotations=[dict(text=f"{total_images}<br>Images", x=0.5, y=0.5, font_size=16, showarrow=False)],
    )
    st.plotly_chart(donut, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

with col2:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">Quality Trend (Recent Analyses)</div>', unsafe_allow_html=True)
    if total_images:
        trend = pd.DataFrame({
            "Label": [t[5:16] for t in hist_df["timestamp"].tail(10)],
            "Score": hist_df["overall_score"].tail(10).values,
        })
    else:
        trend = pd.DataFrame({"Label": [], "Score": []})
    line = go.Figure(
        go.Scatter(
            x=trend["Label"], y=trend["Score"], mode="lines+markers+text",
            text=trend["Score"].round(1) if total_images else [], textposition="top center",
            line=dict(color=PRIMARY, width=3), marker=dict(size=7, color=PRIMARY),
        )
    )
    line.update_layout(height=260, margin=dict(l=10, r=10, t=20, b=10), yaxis=dict(range=[0, 100]))
    st.plotly_chart(line, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">ISO 19157 Alignment Overview</div>', unsafe_allow_html=True)
    if backend.has_image() and "iso" in backend.get_state():
        for d in backend.get_state()["iso"]:
            c1, c2 = st.columns([1.4, 3])
            c1.write(f"✅ {d['Dimension']}")
            with c2:
                st.progress(min(max(d["Score"], 0.0), 1.0))
            st.caption(f"{d['Score']*100:.0f}%")
    else:
        st.caption("Analyze an image to see live ISO 19157 dimension scores here.")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">System Status</div>', unsafe_allow_html=True)
    hist_writable = "Writable ✅" if os.access(backend.PROJECT_DIR, os.W_OK) else "Read-only (history won't persist)"
    status = [
        ("🗄️", "History Log", f"{backend.HISTORY_CSV}"),
        ("⚙️", "Processing Engine", "Running (backend.py)"),
        ("🗄️", "Storage", hist_writable),
        ("📄", "Analyses Logged", str(total_images)),
    ]
    for icon, label, val in status:
        c1, c2, c3 = st.columns([0.5, 2, 2.2])
        c1.write(icon)
        c2.write(label)
        c3.write(val)
    st.markdown("</div>", unsafe_allow_html=True)
