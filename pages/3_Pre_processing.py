"""Step 4: Pre-processing Screen (real pixel-level pipeline)"""

import streamlit as st
import sys, os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import inject_global_css, render_sidebar
import backend

st.set_page_config(page_title="IQAS - Pre-processing", page_icon="🛰️", layout="wide")
inject_global_css()
render_sidebar("Pre-processing")

st.markdown('<div class="step-badge">Step 4: Pre-processing Screen</div>', unsafe_allow_html=True)
st.markdown("## Pre-processing")
st.caption("Apply real pixel-level preprocessing to the uploaded in-orbit image")

sub_steps = ["Upload Image", "Image Details", "Pre-processing", "Quality Analysis"]
sub_stepper = '<div class="stepper-wrap">'
for i, label in enumerate(sub_steps, start=1):
    if i < 3:
        circle, lbl, icon = "step-circle step-done", "step-label-done", "✓"
    elif i == 3:
        circle, lbl, icon = "step-circle step-active", "step-label-active", "3"
    else:
        circle, lbl, icon = "step-circle step-inactive", "step-label-inactive", str(i)
    sub_stepper += f'<div class="{circle}">{icon}</div><div class="{lbl}">{label}</div>'
    if i != len(sub_steps):
        sub_stepper += '<div style="width:40px;border-top:2px dashed #D1D5DB;"></div>'
sub_stepper += "</div>"
st.markdown(sub_stepper, unsafe_allow_html=True)

if not backend.has_image():
    st.warning("No image loaded yet. Please go back to **Image Upload** and upload an image first "
               "(GeoTIFF, Landsat SR band, JPEG or PNG).")
    st.stop()

state = backend.get_state()
raster = state["raster"]

defaults = {
    "radiometric_on": True, "noise_on": True, "kernel_size": "3 x 3",
    "atmos_on": True, "contrast_on": True, "sharpen_on": True, "sharpen_strength": 1.20,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

left, right = st.columns([2.2, 1])

with left:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">Image Preview</div>', unsafe_allow_html=True)

    img_col1, img_col2 = st.columns(2)

    with img_col1:
        st.markdown("**Original Image** ℹ️")
        st.image(backend.to_display_image(state["original_gray"]), use_container_width=True)
        meta = state.get("meta", {})
        st.caption(f"📄 {raster.filename} · 🛰️ {meta.get('satellite','—')} · "
                   f"📅 {meta.get('acquisition_date','—')}")

    with img_col2:
        options = {
            "radiometric_on": st.session_state.radiometric_on,
            "noise_on": st.session_state.noise_on,
            "kernel_size": st.session_state.kernel_size,
            "atmos_on": st.session_state.atmos_on,
            "contrast_on": st.session_state.contrast_on,
            "sharpen_on": st.session_state.sharpen_on,
            "sharpen_strength": st.session_state.sharpen_strength,
        }
        backend.run_preprocessing(options)
        st.markdown("**Pre-processed Image** ℹ️")
        st.image(backend.to_display_image(state["processed_gray"]), use_container_width=True)
        st.caption("✅ Processed · Real pixel-level pipeline applied to the uploaded raster")

    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">Applied Pre-processing Steps</div>', unsafe_allow_html=True)

    applied_steps = state.get("applied_steps", [])
    if applied_steps:
        chip_cols = st.columns(len(applied_steps))
        for col, (icon, title, sub) in zip(chip_cols, applied_steps):
            with col:
                st.markdown(
                    f"""<div style="border:1px solid #E5E7EB;border-radius:10px;padding:10px 12px;background:#FAFAFF;font-size:13px;">
                    {icon} <b>{title} ✅</b><br><span style="color:#6B7280;font-size:12px;">{sub}</span></div>""",
                    unsafe_allow_html=True,
                )
    else:
        st.info("No pre-processing steps enabled. Toggle options on the right to apply steps.")

    progress_pct = int(len(applied_steps) / 5 * 100)
    st.markdown("**Overall Progress**")
    st.progress(progress_pct / 100)
    st.markdown(f"<div style='text-align:right;color:#16A34A;font-weight:700;'>{progress_pct}%</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

with right:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    hcol1, hcol2 = st.columns([2, 1])
    hcol1.markdown('<div class="card-title">Pre-processing Options</div>', unsafe_allow_html=True)
    if hcol2.button("Reset All", use_container_width=True):
        for k, v in defaults.items():
            st.session_state[k] = v
        st.rerun()

    st.markdown("**☀️ Radiometric Correction**")
    st.session_state.radiometric_on = st.toggle("radiometric", value=st.session_state.radiometric_on, label_visibility="collapsed")
    if st.session_state.radiometric_on:
        st.selectbox("Method", ["DOS (Dark Object Subtraction)", "FLAASH", "6S Model"], key="radio_method",
                      help="Only DOS is actually computed on your pixels; other options are shown for future extension.")

    st.markdown("**📶 Noise Reduction**")
    st.session_state.noise_on = st.toggle("noise", value=st.session_state.noise_on, label_visibility="collapsed")
    if st.session_state.noise_on:
        st.selectbox("Method", ["Median Filter", "Gaussian Filter", "Bilateral Filter"], key="noise_method")
        st.session_state.kernel_size = st.selectbox("Kernel Size", ["3 x 3", "5 x 5", "7 x 7"], key="kernel_select")

    st.markdown("**☁️ Atmospheric Correction**")
    st.session_state.atmos_on = st.toggle("atmos", value=st.session_state.atmos_on, label_visibility="collapsed")
    if st.session_state.atmos_on:
        st.selectbox("Method", ["QUAC (Quick Atmospheric Correction)", "FLAASH", "Dark Object Subtraction"], key="atmos_method")

    st.markdown("**📊 Contrast Enhancement**")
    st.session_state.contrast_on = st.toggle("contrast", value=st.session_state.contrast_on, label_visibility="collapsed")
    if st.session_state.contrast_on:
        st.selectbox("Method", ["Histogram Equalization", "CLAHE", "Linear Stretch"], key="contrast_method")

    st.markdown("**🎯 Sharpening**")
    st.session_state.sharpen_on = st.toggle("sharpen", value=st.session_state.sharpen_on, label_visibility="collapsed")
    if st.session_state.sharpen_on:
        st.selectbox("Method", ["Unsharp Mask", "Laplacian Sharpening", "High-Pass Filter"], key="sharpen_method")
        st.session_state.sharpen_strength = st.slider("Strength", 0.1, 3.0, st.session_state.sharpen_strength, 0.05)

    st.write("")
    if st.button("⚙️ Apply Pre-processing", type="primary", use_container_width=True):
        st.success("Pre-processing pipeline recomputed on the actual uploaded raster.")
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

st.write("")
fcol1, fcol2, fcol3 = st.columns([1.4, 4, 1.6])
with fcol1:
    st.button("← Back: Image Details")
with fcol3:
    if st.button("Next: Quality Analysis →", type="primary", use_container_width=True):
        st.switch_page("pages/4_Quality_Analysis.py")
