"""Step 3: Image Upload Screen (real backend wired in)"""

import streamlit as st
import sys, os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import inject_global_css, render_sidebar
import backend

st.set_page_config(page_title="IQAS - Image Upload", page_icon="🛰️", layout="wide")
inject_global_css()
render_sidebar("Image Upload")

st.markdown('<div class="step-badge">Step 3: Image Upload Screen</div>', unsafe_allow_html=True)
st.markdown("## Image Upload")
st.caption("Upload In-Orbit Image for Quality Assessment (GeoTIFF / Landsat SR bands / JPEG / PNG)")

sub_steps = ["Upload Image", "Image Details", "Pre-view", "Confirm"]
sub_stepper = '<div class="stepper-wrap">'
for i, label in enumerate(sub_steps, start=1):
    circle = "step-circle step-active" if i == 1 else "step-circle step-inactive"
    lbl = "step-label-active" if i == 1 else "step-label-inactive"
    sub_stepper += f'<div class="{circle}">{i}</div><div class="{lbl}">{label}</div>'
    if i != len(sub_steps):
        sub_stepper += '<div style="width:40px;border-top:2px dashed #D1D5DB;"></div>'
sub_stepper += "</div>"
st.markdown(sub_stepper, unsafe_allow_html=True)

left, right = st.columns([1.4, 1])

with left:
    uploaded_file = st.file_uploader(
        "Drag & Drop your image here", type=["tif", "tiff", "jpeg", "jpg", "png"],
        label_visibility="collapsed",
    )

    parsed_meta = {}
    if uploaded_file is None:
        st.markdown(
            """
            <div style="border:2px dashed #C7C9F5;border-radius:12px;background:#F7F7FF;
                        padding:60px 20px;text-align:center;">
                <div style="font-size:40px;">☁️⬆️</div>
                <h4>Drag & Drop your image here</h4>
                <p style="color:#6B7280;">or use the uploader above (Browse Files)</p>
                <p style="font-size:12px;color:#9CA3AF;">
                    Supported formats: TIFF, GeoTIFF, JPEG, PNG &nbsp;|&nbsp; Max file size: 2 GB<br>
                    Landsat SR band files (e.g. LC08_L2SP_027031_20260531_20260605_02_T1_SR_B7.TIF) are
                    auto-parsed for satellite / sensor / path-row / date.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.success(f"Selected: {uploaded_file.name} ({uploaded_file.size / 1e6:.1f} MB)")
        with st.spinner("Reading raster and extracting metadata..."):
            try:
                parsed_meta = backend.ingest_uploaded_file(uploaded_file)
                raster = backend.get_state()["raster"]
            except Exception as e:
                st.error(f"Could not read this file: {e}")
                raster = None

        if raster is not None:
            c1, c2 = st.columns([1, 1.2])
            with c1:
                st.image(backend.to_display_image(raster.gray), caption="Preview (auto-stretched)",
                          use_container_width=True)
            with c2:
                st.markdown(f"""
                **Driver:** {raster.driver}
                **Shape:** {raster.shape}
                **Bands:** {raster.bands}
                **Bit depth:** {raster.bit_depth}-bit
                **Original dtype:** {raster.dtype_orig}
                **No-data / zero pixels:** {raster.nodata_fraction*100:.2f}%
                """)
                if raster.xres:
                    st.markdown(f"**Pixel size (from file):** {raster.xres:.2f} x {raster.yres:.2f}")
                if parsed_meta:
                    st.info(f"Auto-detected from filename: **{parsed_meta.get('satellite')}** / "
                             f"**{parsed_meta.get('sensor')}**, band {parsed_meta.get('band') or 'n/a'}, "
                             f"acquired {parsed_meta.get('acquisition_date')}")

    st.markdown("#### Recent Analyses (this machine)")
    history = backend.load_history()
    if history:
        thumb_cols = st.columns(min(4, len(history)))
        for col, row in zip(thumb_cols, reversed(history[-4:])):
            with col:
                st.markdown(
                    f"""
                    <div style="background:#1E293B;height:70px;border-radius:8px;
                                display:flex;align-items:center;justify-content:center;
                                color:#94A3B8;font-size:11px;margin-bottom:6px;">🛰️ {row['quality_level']}</div>
                    <div style="font-size:12px;color:#6B7280;line-height:1.3;">
                        <b>{row['image_name'][:24]}</b><br>{row['satellite']}<br>{row['overall_score']}/100
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
    else:
        st.caption("No images analyzed yet on this machine. Once you complete Robust Score, results appear here.")

with right:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### Image Metadata")

    def _idx(options, value, fallback=0):
        try:
            return options.index(value)
        except ValueError:
            return fallback

    sat_options = ["Select Satellite", "Sentinel-1A", "Sentinel-1B", "Sentinel-2A", "Sentinel-2B",
                   "Landsat-8", "Landsat-9", "Resourcesat-2"]
    sensor_options = ["Select Sensor", "MSI", "OLI/TIRS", "LISS-IV", "SAR-C"]
    type_options = ["Select Image Type", "Multispectral", "Panchromatic", "SAR", "Thermal", "Hyperspectral"]
    proj_options = ["Select Projection", "WGS84 / UTM", "WGS84", "Geographic (Lat/Lon)"]
    res_options = ["Select Resolution", "1", "5", "10", "15", "30"]
    fmt_options = ["Select Format", "TIFF", "GeoTIFF", "JPEG", "PNG"]
    landcover_options = ["Select Land-Cover", "Urban / Built-up", "Forest / Vegetation", "Agriculture",
                          "Water Body", "Barren / Desert", "Snow / Ice", "Mixed / Other"]
    season_options = ["Select Season", "Winter", "Summer", "Monsoon / Rainy", "Autumn / Post-Monsoon"]

    c1, c2 = st.columns(2)
    with c1:
        satellite = st.selectbox("Satellite *", sat_options,
                                  index=_idx(sat_options, parsed_meta.get("satellite", "")))
        image_type = st.selectbox("Image Type *", type_options,
                                   index=_idx(type_options, "Multispectral" if parsed_meta else "Select Image Type"))
        path_row = st.text_input("Path / Row", value=parsed_meta.get("path_row", ""), placeholder="Enter path / row")
        orbit_track = st.text_input("Orbit / Track No.", placeholder="Enter orbit / track no.")
        projection = st.selectbox("Projection", proj_options,
                                   index=_idx(proj_options, parsed_meta.get("projection", "")))
    with c2:
        sensor = st.selectbox("Sensor *", sensor_options,
                               index=_idx(sensor_options, parsed_meta.get("sensor", "")))
        acq_dt = st.text_input("Acquisition Date & Time *", value=parsed_meta.get("acquisition_date", ""),
                                placeholder="Select date & time")
        resolution = st.selectbox("Resolution (m)", res_options,
                                   index=_idx(res_options, parsed_meta.get("resolution_m", "")))
        cloud_cover = st.number_input("Cloud Cover (%)", min_value=0.0, max_value=100.0, value=0.0, step=1.0)
        file_format = st.selectbox("File Format", fmt_options,
                                    index=_idx(fmt_options, "GeoTIFF" if parsed_meta else "Select Format"))

    description = st.text_area("Image Description (Optional)", placeholder="Enter image description or any note...",
                                value=(f"Auto-parsed product: {parsed_meta.get('product')} band "
                                       f"{parsed_meta.get('band')}, tier {parsed_meta.get('tier')}"
                                       if parsed_meta else ""))

    st.markdown("##### Dataset Diversity Tags")
    st.caption("Used to track coverage across regions / land-cover types / seasons for generalization testing (RAC-4 requirement).")
    d1, d2, d3 = st.columns(3)
    with d1:
        land_cover = st.selectbox("Land-Cover Type", landcover_options)
    with d2:
        season = st.selectbox("Season", season_options)
    with d3:
        region = st.text_input("Region / Location", placeholder="e.g. Gujarat, India")

    st.markdown(
        """
        <div style="background:#FEF3C7;border-radius:8px;padding:12px 14px;font-size:13px;color:#92400E;margin-top:10px;">
            ℹ️ Please ensure the image and metadata are correct for accurate quality
            assessment aligned with ISO 19157.
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)

    # Persist metadata edits to session for later pages / report.
    if backend.has_image():
        backend.get_state()["meta"].update({
            "satellite": satellite, "sensor": sensor, "image_type": image_type,
            "path_row": path_row, "orbit_track": orbit_track, "projection": projection,
            "acquisition_date": acq_dt, "resolution_m": resolution, "cloud_cover": cloud_cover,
            "file_format": file_format, "description": description,
            "land_cover": land_cover, "season": season, "region": region,
        })

st.write("")
fcol1, fcol2, fcol3 = st.columns([1, 4, 1.3])
with fcol1:
    if st.button("Reset"):
        st.session_state.pop("iqas", None)
        st.rerun()
with fcol3:
    if st.button("Next: Image Details →", type="primary", use_container_width=True):
        required_ok = (
            backend.has_image()
            and satellite not in ("", "Select Satellite")
            and sensor not in ("", "Select Sensor")
            and image_type not in ("", "Select Image Type")
            and acq_dt.strip() != ""
        )
        if required_ok:
            st.success("All required fields captured. Proceed to Pre-processing.")
            st.switch_page("pages/3_Pre_processing.py")
        else:
            st.error("Please fill all required fields (marked *) and upload an image before continuing.")
