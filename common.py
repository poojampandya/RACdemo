"""
common.py
Shared CSS, sidebar navigation and step-progress helpers for the
IQAS (In-Orbit Image Quality Assessment System) Streamlit project.
Import and call these from every page so the look stays consistent.
"""

import streamlit as st

PRIMARY = "#4F46E5"

NAV_ITEMS = [
    ("📊", "Dashboard", "pages/1_Dashboard.py"),
    ("☁️", "Image Upload", "pages/2_Image_Upload.py"),
    ("⚙️", "Pre-processing", "pages/3_Pre_processing.py"),
    ("📈", "Quality Analysis", "pages/4_Quality_Analysis.py"),
    ("⭐", "Robust Score", "pages/5_Robust_Score.py"),
    ("🛡️", "ISO 19157 Alignment", "pages/6_ISO19157_Alignment.py"),
    ("📉", "Comparative Analysis", "pages/7_Comparative_Analysis.py"),
    ("📄", "Results & Reports", "pages/8_Results_Report.py"),
    ("🗄️", "Datasets", None),
    ("⚙️", "Settings", None),
    ("❓", "Help", None),
]

ALL_STEPS = [
    "Upload Image", "Image Details", "Pre-processing", "Quality Analysis",
    "Robust Score", "ISO 19157", "Comparative Analysis", "Report",
]


def inject_global_css():
    st.markdown(
        f"""
        <style>
        #MainMenu, header, footer {{visibility: hidden;}}
        .block-container {{ padding-top: 1rem; }}

        section[data-testid="stSidebar"] {{ background-color: #0B0F2E; }}
        section[data-testid="stSidebar"] * {{ color: #E2E4F5 !important; }}
        .sidebar-title {{ font-size: 22px; font-weight: 800; color: white !important; }}
        .sidebar-sub {{ font-size: 13px; color: #A9ADD6 !important; margin-top: -6px; }}
        .sidebar-iso {{ font-size: 12px; color: #8B8FE8 !important; margin-bottom: 18px; }}
        .nav-item {{ padding: 8px 10px; border-radius: 8px; font-size: 14px; margin-bottom: 2px; }}
        .nav-item-active {{ background-color: {PRIMARY}; color: white !important; font-weight: 600; }}

        .step-badge {{
            background-color: #1E1B4B; color: white; padding: 6px 16px;
            border-radius: 6px; font-weight: 700; font-size: 14px; display: inline-block;
            margin-bottom: 14px;
        }}
        .stepper-wrap {{ display: flex; align-items: center; gap: 6px; margin-bottom: 18px; flex-wrap: wrap; }}
        .step-circle {{
            width: 24px; height: 24px; border-radius: 50%; display: flex;
            align-items: center; justify-content: center; font-size: 12px; font-weight: 700;
        }}
        .step-done {{ background-color: #DCFCE7; color: #16A34A; }}
        .step-active {{ background-color: {PRIMARY}; color: white; }}
        .step-inactive {{ background-color: #E5E7EB; color: #9CA3AF; }}
        .step-label-done {{ color: #111827; font-size: 13px; }}
        .step-label-active {{ font-weight: 700; color: #111827; font-size: 13px; }}
        .step-label-inactive {{ color: #9CA3AF; font-size: 13px; }}

        .card {{
            border: 1px solid #E5E7EB; border-radius: 12px; padding: 18px 20px;
            background: white; margin-bottom: 18px; height: 100%;
        }}
        .card-title {{ font-weight: 700; font-size: 16px; color: #111827; margin-bottom: 10px; }}

        .kpi-card {{
            border-radius: 12px; padding: 16px 18px; margin-bottom: 10px;
        }}
        .kpi-label {{ font-size: 12px; color: #6B7280; }}
        .kpi-value {{ font-size: 22px; font-weight: 800; color: #111827; }}

        .badge-good {{ background:#DCFCE7; color:#15803D; font-weight:700; padding:4px 14px; border-radius:6px; display:inline-block; }}
        .badge-excellent {{ background:#DBEAFE; color:#1D4ED8; font-weight:700; padding:4px 14px; border-radius:6px; display:inline-block; }}
        .badge-moderate {{ background:#FEF3C7; color:#B45309; font-weight:700; padding:4px 14px; border-radius:6px; display:inline-block; }}

        .conclusion-box {{
            background:#ECFDF5; border:1px solid #A7F3D0; border-radius:8px; padding:12px 14px; font-size:13px;
        }}
        .note-box {{
            background:#F3F4F6; border-radius:8px; padding:10px 14px; font-size:13px; margin-bottom:8px;
        }}
        .rec-box {{
            background:#F0FDF4; border-radius:8px; padding:10px 14px; font-size:13px; margin-bottom:8px;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar(active_label: str):
    with st.sidebar:
        st.markdown('<div class="sidebar-title">🛰️ IQAS</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="sidebar-sub">In-Orbit Image Quality<br>Assessment System</div>',
            unsafe_allow_html=True,
        )
        st.markdown('<div class="sidebar-iso">ISO 19157 Aligned</div>', unsafe_allow_html=True)

        for icon, label, target in NAV_ITEMS:
            css_class = "nav-item nav-item-active" if label == active_label else "nav-item"
            if target:
                st.page_link(target, label=f"{icon}  {label}")
            else:
                st.markdown(f'<div class="{css_class}">{icon}&nbsp;&nbsp;{label}</div>', unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("👤 **Researcher**\n\nresearcher@iqas.com")


def render_stepper(current_step: int, steps=None):
    """current_step is 1-indexed into `steps` (defaults to ALL_STEPS)."""
    steps = steps or ALL_STEPS
    html = '<div class="stepper-wrap">'
    for i, label in enumerate(steps, start=1):
        if i < current_step:
            circle, lbl, icon = "step-circle step-done", "step-label-done", "✓"
        elif i == current_step:
            circle, lbl, icon = "step-circle step-active", "step-label-active", str(i)
        else:
            circle, lbl, icon = "step-circle step-inactive", "step-label-inactive", str(i)
        html += f'<div class="{circle}">{icon}</div><div class="{lbl}">{label}</div>'
        if i != len(steps):
            html += '<div style="width:24px;border-top:2px dashed #D1D5DB;"></div>'
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)


def page_header(step_badge: str, title: str, subtitle: str):
    st.markdown(f'<div class="step-badge">{step_badge}</div>', unsafe_allow_html=True)
    st.markdown(f"## {title}")
    st.caption(subtitle)
