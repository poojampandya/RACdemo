"""
backend.py
==========
Real image-processing / image-quality-assessment backend for the IQAS
(In-Orbit Image Quality Assessment System) Streamlit app.

This module replaces every hard-coded / mock value used across the
Streamlit pages with numbers computed from the actual image the user
uploads (GeoTIFF band files such as Landsat Collection-2 SR bands,
plain TIFF, JPEG, PNG, ...).

Everything a page needs lives in `st.session_state["iqas"]`, a single
dict built by `ingest_uploaded_file()` and updated by
`run_preprocessing()` / `run_quality_analysis()`. Pages just read it.

Sections:
    1. Filename parsing (Landsat / Sentinel naming conventions)
    2. Raster loading (TIFF / GeoTIFF / JPEG / PNG -> numpy array)
    3. Display helpers (numpy -> PIL for st.image)
    4. Pre-processing pipeline (real pixel operations)
    5. No-reference quality metrics (0-1 scores computed on real pixels)
    6. Robust composite score + ISO 19157 dimension mapping
    7. Comparative analysis vs. classical IQA metrics (SSIM / PSNR / etc.)
    8. Lightweight on-disk history log used by Dashboard / trend charts
    9. Session-state orchestration helpers used directly by the pages
"""

from __future__ import annotations

import csv
import io
import os
import re
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

import numpy as np
from PIL import Image, ImageFilter, ImageEnhance

try:
    import tifffile
    HAS_TIFFFILE = True
except ImportError:
    HAS_TIFFFILE = False

from scipy import ndimage
from skimage.exposure import equalize_hist, equalize_adapthist
from skimage.metrics import structural_similarity as sk_ssim, peak_signal_noise_ratio as sk_psnr
from skimage.feature import graycomatrix, graycoprops
from skimage.filters import sobel

try:
    from sklearn.ensemble import RandomForestRegressor
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False

# --------------------------------------------------------------------------
# Paths
# --------------------------------------------------------------------------
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
HISTORY_CSV = os.path.join(PROJECT_DIR, "iqas_history.csv")

# --------------------------------------------------------------------------
# 1. Filename parsing
# --------------------------------------------------------------------------
# Landsat Collection-2 naming convention, e.g.:
#   LC08_L2SP_027031_20260531_20260605_02_T1_SR_B7.TIF
#   L  C  08   _  L2SP  _  027031  _  20260531  _ 20260605 _ 02 _ T1 _ SR_B7
#   sat sensor#     level      path/row     acq.date     proc.date  coll tier  band
LANDSAT_RE = re.compile(
    r"^L(?P<sensor>[COTEM])(?P<satnum>\d{2})_"
    r"(?P<level>L\d\w{2,3})_"
    r"(?P<pathrow>\d{6})_"
    r"(?P<acq_date>\d{8})_"
    r"(?P<proc_date>\d{8})_"
    r"(?P<collection>\d{2})_"
    r"(?P<tier>T\d)"
    r"(?:_(?P<product>SR|ST|BT|TOA))?"
    r"(?:_(?P<band>B\d{1,2}|B\d{1,2}QA|QA_PIXEL|QA_RADSAT))?",
    re.IGNORECASE,
)

SENSOR_MAP = {
    "C": "OLI/TIRS", "O": "OLI", "T": "TIRS", "E": "ETM+", "M": "MSS",
}

# --------------------------------------------------------------------------
# Sentinel-2 naming conventions (both come out of Earth Explorer depending
# on whether you download the whole product or a single band from inside
# the .SAFE/GRANULE/IMG_DATA folder):
#
#   Full product ID:
#     S2A_MSIL2A_20260531T054641_N0511_R005_T43QCU_20260605T091234
#      sat  level    sensing datetime      N=baseline R=orbit T=tile  proc dt
#
#   Single band/tile raster:
#     T43QCU_20260531T054641_B04_10m
#      tile      sensing datetime      band  resolution
# --------------------------------------------------------------------------
SENTINEL2_FULL_RE = re.compile(
    r"^S2(?P<sat>[AB])_MSIL(?P<level>1C|2A|1B)_"
    r"(?P<sensing>\d{8}T\d{6})_"
    r"N(?P<baseline>\d{4})_"
    r"R(?P<orbit>\d{3})_"
    r"T(?P<tile>\w{5})_"
    r"(?P<proc>\d{8}T\d{6})",
    re.IGNORECASE,
)

SENTINEL2_BAND_RE = re.compile(
    r"^T(?P<tile>\w{5})_"
    r"(?P<sensing>\d{8}T\d{6})_"
    r"(?P<band>B\d{1,2}A?|TCI|AOT|WVP|SCL)"
    r"(?:_(?P<res>10|20|60)m)?$",
    re.IGNORECASE,
)

# Sentinel-1 SAR naming: S1A_IW_GRDH_1SDV_20260531T...
SENTINEL1_RE = re.compile(
    r"^S1(?P<sat>[AB])_(?P<mode>IW|EW|SM|WV)_"
    r"(?P<prodtype>GRDH|GRDM|SLC|OCN)_(?P<sarclass>1S|2S)(?P<pol>SH|SV|DH|DV)_"
    r"(?P<sensing>\d{8}T\d{6})_",
    re.IGNORECASE,
)

# Ground-sample-distance per Sentinel-2 band (metres).
S2_BAND_GSD = {
    "B01": "60", "B02": "10", "B03": "10", "B04": "10", "B05": "20",
    "B06": "20", "B07": "20", "B08": "10", "B8A": "20", "B09": "60",
    "B10": "60", "B11": "20", "B12": "20", "TCI": "10", "AOT": "10",
    "WVP": "10", "SCL": "20",
}


def _parse_dt(raw: str, fmt: str) -> str:
    try:
        return datetime.strptime(raw, fmt).strftime("%Y-%m-%d %H:%M")
    except ValueError:
        return raw


def _parse_sentinel2(stem: str) -> dict:
    m = SENTINEL2_FULL_RE.match(stem)
    if m:
        g = m.groupdict()
        return {
            "satellite": f"Sentinel-2{g['sat'].upper()}",
            "sensor": "MSI",
            "processing_level": g["level"].upper(),
            "tile": g["tile"].upper(),
            "path_row": g["tile"].upper(),
            "orbit_track": g["orbit"],
            "acquisition_date": _parse_dt(g["sensing"], "%Y%m%dT%H%M%S"),
            "processing_baseline": g["baseline"],
            "projection": "WGS84 / UTM",
            "resolution_m": "10",
        }
    m = SENTINEL2_BAND_RE.match(stem)
    if m:
        g = m.groupdict()
        band = g["band"].upper()
        return {
            "satellite": "Sentinel-2A",  # not encoded in the band filename
            "sensor": "MSI",
            "tile": g["tile"].upper(),
            "path_row": g["tile"].upper(),
            "acquisition_date": _parse_dt(g["sensing"], "%Y%m%dT%H%M%S"),
            "band": band,
            "projection": "WGS84 / UTM",
            "resolution_m": g["res"] or S2_BAND_GSD.get(band, "10"),
        }
    return {}


def _parse_sentinel1(stem: str) -> dict:
    m = SENTINEL1_RE.match(stem)
    if not m:
        return {}
    g = m.groupdict()
    return {
        "satellite": f"Sentinel-1{g['sat'].upper()}",
        "sensor": "SAR-C",
        "acquisition_date": _parse_dt(g["sensing"], "%Y%m%dT%H%M%S"),
        "projection": "WGS84 / UTM",
        "resolution_m": "10" if g["prodtype"].upper() == "GRDH" else "30",
    }


def parse_filename_metadata(filename: str) -> dict:
    """Best-effort extraction of satellite/sensor/date/band metadata from
    Landsat Collection-2, Sentinel-2 (MSI) or Sentinel-1 (SAR) filenames.
    Returns {} if none of the known naming conventions match, in which case
    the Image Upload form is left for the user to fill in manually.
    """
    base = os.path.basename(filename)
    stem = re.sub(r"\.(tif|tiff|jpg|jpeg|png|jp2|safe|zip)$", "", base, flags=re.IGNORECASE)

    s2 = _parse_sentinel2(stem)
    if s2:
        return s2
    s1 = _parse_sentinel1(stem)
    if s1:
        return s1

    m = LANDSAT_RE.match(stem)
    if not m:
        return {}
    g = m.groupdict()
    satnum = int(g["satnum"])
    acq = g["acq_date"]
    try:
        acq_dt = datetime.strptime(acq, "%Y%m%d")
        acq_str = acq_dt.strftime("%Y-%m-%d 00:00")
    except ValueError:
        acq_str = acq
    path = g["pathrow"][:3]
    row = g["pathrow"][3:]
    return {
        "satellite": f"Landsat-{satnum}",
        "sensor": SENSOR_MAP.get(g["sensor"].upper(), "OLI/TIRS"),
        "processing_level": g["level"].upper(),
        "path": path,
        "row": row,
        "path_row": f"{path}/{row}",
        "acquisition_date": acq_str,
        "processing_date": g["proc_date"],
        "collection": g["collection"],
        "tier": g["tier"].upper(),
        "product": (g["product"] or "").upper(),
        "band": (g["band"] or "").upper(),
        "projection": "WGS84 / UTM",
        "resolution_m": "30" if (g["band"] or "").upper() not in ("B8",) else "15",
    }


# --------------------------------------------------------------------------
# 2. Raster loading
# --------------------------------------------------------------------------
@dataclass
class LoadedRaster:
    array: np.ndarray            # float32, shape (H, W) or (H, W, C)
    gray: np.ndarray             # float32, shape (H, W) - luminance / single band
    dtype_orig: str
    bit_depth: int
    bands: int
    shape: tuple
    nodata_fraction: float
    driver: str
    xres: Optional[float] = None
    yres: Optional[float] = None
    filename: str = ""


def _read_tiff_bytes(data: bytes) -> np.ndarray:
    with io.BytesIO(data) as bio:
        arr = tifffile.imread(bio)
    return arr


def _read_tiff_resolution(data: bytes):
    """Try to pull XResolution/YResolution tags (pixel size) from a TIFF."""
    try:
        with io.BytesIO(data) as bio:
            with tifffile.TiffFile(bio) as tf:
                tags = tf.pages[0].tags
                xres = tags.get("XResolution")
                yres = tags.get("YResolution")
                # ModelPixelScaleTag (GeoTIFF) gives (x, y, z) pixel size in
                # map units (usually metres) - this is far more useful for
                # satellite products than the plain TIFF resolution tags.
                pixscale = tags.get("ModelPixelScaleTag")
                if pixscale is not None:
                    vals = pixscale.value
                    if len(vals) >= 2 and vals[0] > 0:
                        return float(vals[0]), float(vals[1])
                if xres is not None and yres is not None:
                    return float(xres.value[1] / xres.value[0]) if isinstance(xres.value, tuple) else float(xres.value), \
                           float(yres.value[1] / yres.value[0]) if isinstance(yres.value, tuple) else float(yres.value)
    except Exception:
        pass
    return None, None


def load_raster(uploaded_file) -> LoadedRaster:
    """Load a Streamlit UploadedFile (or a path string) into a LoadedRaster.

    Supports single/multi-band GeoTIFF (e.g. Landsat *_SR_B7.TIF), regular
    TIFF, JPEG and PNG. Values are converted to float32.
    """
    if hasattr(uploaded_file, "read"):
        name = getattr(uploaded_file, "name", "uploaded")
        uploaded_file.seek(0)
        data = uploaded_file.read()
        uploaded_file.seek(0)
    else:
        name = str(uploaded_file)
        with open(uploaded_file, "rb") as f:
            data = f.read()

    ext = os.path.splitext(name)[1].lower()
    xres = yres = None
    driver = "PIL"

    if ext in (".tif", ".tiff") and HAS_TIFFFILE:
        arr = _read_tiff_bytes(data)
        xres, yres = _read_tiff_resolution(data)
        driver = "GeoTIFF/TIFF (tifffile)"
    else:
        with io.BytesIO(data) as bio:
            pil_img = Image.open(bio)
            pil_img.load()
        arr = np.array(pil_img)
        driver = f"{pil_img.format or ext.upper()} (PIL)"

    dtype_orig = str(arr.dtype)
    if np.issubdtype(arr.dtype, np.integer):
        bit_depth = arr.dtype.itemsize * 8
    else:
        bit_depth = 32

    arr = arr.astype(np.float32)

    # Normalise shape handling: (H, W) single band, (H, W, C) multi-band
    if arr.ndim == 2:
        bands = 1
        gray = arr.copy()
    elif arr.ndim == 3:
        bands = arr.shape[-1] if arr.shape[-1] <= 8 else arr.shape[0]
        if arr.shape[-1] > 8 and arr.shape[0] <= 8:
            # (C, H, W) -> (H, W, C)
            arr = np.moveaxis(arr, 0, -1)
            bands = arr.shape[-1]
        if bands >= 3:
            gray = (0.2989 * arr[..., 0] + 0.5870 * arr[..., 1] + 0.1140 * arr[..., 2])
        else:
            gray = arr[..., 0]
    else:
        raise ValueError(f"Unsupported array shape {arr.shape} for {name}")

    nodata_fraction = float(np.mean(gray <= 0)) if gray.size else 0.0

    return LoadedRaster(
        array=arr, gray=gray, dtype_orig=dtype_orig, bit_depth=bit_depth,
        bands=bands, shape=arr.shape, nodata_fraction=nodata_fraction,
        driver=driver, xres=xres, yres=yres, filename=name,
    )


# --------------------------------------------------------------------------
# 3. Display helpers
# --------------------------------------------------------------------------
def to_display_image(gray_or_rgb: np.ndarray, p_low: float = 2, p_high: float = 98) -> Image.Image:
    """Percentile-stretch any float array (8/16-bit satellite data included)
    into an 8-bit PIL image suitable for st.image()."""
    arr = np.asarray(gray_or_rgb, dtype=np.float32)
    lo, hi = np.percentile(arr, [p_low, p_high])
    if hi <= lo:
        hi = lo + 1.0
    stretched = np.clip((arr - lo) / (hi - lo), 0, 1)
    img8 = (stretched * 255).astype(np.uint8)
    if img8.ndim == 2:
        return Image.fromarray(img8, mode="L").convert("RGB")
    if img8.ndim == 3 and img8.shape[-1] >= 3:
        return Image.fromarray(img8[..., :3], mode="RGB")
    return Image.fromarray(img8[..., 0], mode="L").convert("RGB")


# --------------------------------------------------------------------------
# 4. Pre-processing pipeline (operates on the float32 gray array)
# --------------------------------------------------------------------------
def radiometric_correction(gray: np.ndarray) -> np.ndarray:
    """Dark Object Subtraction (DOS): subtract the 1st percentile ("dark
    object" / haze value) from every pixel."""
    dark = np.percentile(gray, 1)
    return np.clip(gray - dark, 0, None)


def noise_reduction(gray: np.ndarray, kernel: int = 3) -> np.ndarray:
    return ndimage.median_filter(gray, size=kernel)


def atmospheric_correction(gray: np.ndarray) -> np.ndarray:
    """QUAC-style relative correction: rescale so the 0.5-99.5 percentile
    range fills the working dynamic range, approximating haze/atmosphere
    normalisation without needing per-band radiance calibration."""
    lo, hi = np.percentile(gray, [0.5, 99.5])
    if hi <= lo:
        hi = lo + 1.0
    return np.clip((gray - lo) / (hi - lo), 0, 1) * (hi - lo) + lo


def contrast_enhancement(gray: np.ndarray) -> np.ndarray:
    """Histogram equalisation on a normalised copy, then rescaled back to
    the original data range so downstream metrics stay comparable."""
    lo, hi = float(gray.min()), float(gray.max())
    if hi <= lo:
        return gray.copy()
    norm = (gray - lo) / (hi - lo)
    eq = equalize_hist(norm)
    return eq * (hi - lo) + lo


def sharpening(gray: np.ndarray, strength: float = 1.2, radius: float = 2.0) -> np.ndarray:
    blurred = ndimage.gaussian_filter(gray, sigma=radius)
    return gray + strength * (gray - blurred)


def run_preprocessing_pipeline(gray: np.ndarray, options: dict) -> tuple[np.ndarray, list]:
    """Apply the enabled steps in `options` in a fixed, sensible order and
    return (processed_array, applied_steps_metadata)."""
    out = gray.astype(np.float32).copy()
    applied = []

    if options.get("radiometric_on", True):
        out = radiometric_correction(out)
        applied.append(("☀️", "Radiometric Correction", "DOS Method"))

    if options.get("noise_on", True):
        k = int(str(options.get("kernel_size", "3 x 3")).split("x")[0].strip())
        out = noise_reduction(out, kernel=k)
        applied.append(("📶", "Noise Reduction", f"Median Filter ({options.get('kernel_size','3 x 3')})"))

    if options.get("atmos_on", True):
        out = atmospheric_correction(out)
        applied.append(("☁️", "Atmospheric Correction", "QUAC-style Method"))

    if options.get("contrast_on", True):
        out = contrast_enhancement(out)
        applied.append(("📊", "Contrast Enhancement", "Histogram Equalization"))

    if options.get("sharpen_on", True):
        strength = float(options.get("sharpen_strength", 1.2))
        out = sharpening(out, strength=strength)
        applied.append(("🎯", "Sharpening", f"Unsharp Mask ({strength:.2f})"))

    return out, applied


# --------------------------------------------------------------------------
# 5. No-reference quality metrics (each returns a score in [0, 1])
# --------------------------------------------------------------------------
def _norm01(x, lo, hi):
    if hi <= lo:
        return 0.5
    return float(np.clip((x - lo) / (hi - lo), 0.0, 1.0))


def m_sharpness(gray: np.ndarray) -> float:
    """Variance of the Laplacian - a standard focus/sharpness measure."""
    lap = ndimage.laplace(gray)
    var = float(np.var(lap))
    # Empirically, well-focused 8-16 bit remote sensing chips land ~ [0, 4000]
    ref = max(np.var(gray) * 0.02, 1e-6)
    return _norm01(var, 0, ref * 12)


def m_contrast(gray: np.ndarray) -> float:
    """RMS (Michelson-style) contrast normalised by the achievable dynamic
    range of the data."""
    dr = gray.max() - gray.min()
    if dr <= 0:
        return 0.0
    rms = float(np.std(gray))
    return _norm01(rms / dr, 0, 0.35)


def m_snr(gray: np.ndarray) -> float:
    """Signal to noise ratio estimated as mean(signal) / std(local noise),
    where local noise is estimated from a high-pass residual."""
    smooth = ndimage.gaussian_filter(gray, sigma=2)
    noise = gray - smooth
    noise_std = float(np.std(noise)) or 1e-6
    signal_mean = float(np.mean(np.abs(gray))) or 1e-6
    snr_db = 20 * np.log10(signal_mean / noise_std) if signal_mean > 0 else 0
    return _norm01(snr_db, 5, 45)


def m_noise_inverse(gray: np.ndarray) -> float:
    """Robust noise sigma estimate (median absolute deviation of the
    Laplacian, per Immerkaer 1996), inverted so higher = cleaner."""
    lap = ndimage.laplace(gray)
    sigma = float(np.median(np.abs(lap - np.median(lap)))) * 1.4826
    dr = (gray.max() - gray.min()) or 1.0
    rel_noise = sigma / dr
    return 1.0 - _norm01(rel_noise, 0, 0.08)


def m_brightness(gray: np.ndarray) -> float:
    """How close the mean brightness sits to the mid-point of the dynamic
    range (extremes -> under/over-exposed)."""
    lo, hi = gray.min(), gray.max()
    if hi <= lo:
        return 0.5
    mean_norm = (float(np.mean(gray)) - lo) / (hi - lo)
    return float(np.clip(1.0 - 2 * abs(mean_norm - 0.5), 0, 1))


def m_resolution(shape: tuple, xres: Optional[float], yres: Optional[float]) -> float:
    """Prefer real ground-sample-distance (GSD) from GeoTIFF tags when
    available; otherwise fall back to a pixel-count heuristic."""
    if xres and yres and xres > 0:
        gsd = (abs(xres) + abs(yres)) / 2
        # <=10m -> excellent, ~30m -> good, >=100m -> poor
        return _norm01(100 - gsd, 0, 95)
    h, w = shape[0], shape[1]
    megapixels = (h * w) / 1e6
    return _norm01(megapixels, 0.2, 20)


def m_edge_strength(gray: np.ndarray) -> float:
    norm = (gray - gray.min()) / ((gray.max() - gray.min()) or 1)
    edges = sobel(norm)
    return _norm01(float(np.mean(edges)), 0, 0.25)


def m_texture(gray: np.ndarray) -> float:
    """GLCM-based texture richness (contrast + inverse of homogeneity, i.e.
    more structural variety = higher score)."""
    lo, hi = gray.min(), gray.max()
    if hi <= lo:
        return 0.5
    q = np.clip(((gray - lo) / (hi - lo)) * 31, 0, 31).astype(np.uint8)
    # Downsample very large chips for speed.
    if q.shape[0] > 512 or q.shape[1] > 512:
        step_r = max(1, q.shape[0] // 512)
        step_c = max(1, q.shape[1] // 512)
        q = q[::step_r, ::step_c]
    glcm = graycomatrix(q, distances=[1], angles=[0, np.pi / 4, np.pi / 2, 3 * np.pi / 4],
                         levels=32, symmetric=True, normed=True)
    contrast = float(np.mean(graycoprops(glcm, "contrast")))
    homogeneity = float(np.mean(graycoprops(glcm, "homogeneity")))
    score = 0.5 * _norm01(contrast, 0, 40) + 0.5 * (1 - homogeneity)
    return float(np.clip(score, 0, 1))


def m_radiometric_quality(gray: np.ndarray, bit_depth: int) -> float:
    """How well the data uses the available radiometric range (a clipped or
    saturated histogram indicates poor radiometric quality)."""
    max_val = (2 ** bit_depth) - 1 if bit_depth < 32 else float(gray.max() or 1)
    used_range = (gray.max() - gray.min()) / max_val if max_val else 0
    clip_low = float(np.mean(gray <= np.percentile(gray, 0.1)))
    clip_high = float(np.mean(gray >= np.percentile(gray, 99.9)))
    saturation_penalty = clip_low + clip_high
    return float(np.clip(_norm01(used_range, 0.05, 0.6) - saturation_penalty, 0, 1))


PARAM_FUNCS_ORDER = [
    "Sharpness", "Contrast", "SNR", "Noise (Inv.)", "Brightness",
    "Resolution", "Edge Strength", "Texture Quality", "Radiometric Quality",
]

DEFAULT_WEIGHTS = {
    "Sharpness": 15, "Contrast": 15, "SNR": 15, "Noise (Inv.)": 10,
    "Brightness": 10, "Resolution": 15, "Edge Strength": 10,
    "Texture Quality": 5, "Radiometric Quality": 5,
}


def compute_quality_parameters(raster: LoadedRaster) -> dict:
    gray = raster.gray
    scores = {
        "Sharpness": m_sharpness(gray),
        "Contrast": m_contrast(gray),
        "SNR": m_snr(gray),
        "Noise (Inv.)": m_noise_inverse(gray),
        "Brightness": m_brightness(gray),
        "Resolution": m_resolution(raster.shape, raster.xres, raster.yres),
        "Edge Strength": m_edge_strength(gray),
        "Texture Quality": m_texture(gray),
        "Radiometric Quality": m_radiometric_quality(gray, raster.bit_depth),
    }
    return scores


def level_for_score01(score: float) -> str:
    if score >= 0.80:
        return "Excellent"
    if score >= 0.60:
        return "Good"
    if score >= 0.40:
        return "Moderate"
    return "Poor"


def level_for_score100(score: float) -> str:
    if score >= 90:
        return "Excellent"
    if score >= 70:
        return "Good"
    if score >= 50:
        return "Moderate"
    return "Poor"


# --------------------------------------------------------------------------
# 6. Robust composite score
# --------------------------------------------------------------------------
def robust_composite(scores: dict, weights: dict = None) -> dict:
    """Weighted aggregation with a Huber-style robustness adjustment: a
    parameter that disagrees strongly with the (weighted) median of the
    others is down-weighted before the final sum, which is the "robust" in
    Robust Quality Score - a single corrupted metric can't dominate.
    """
    weights = weights or DEFAULT_WEIGHTS
    params = list(scores.keys())
    vals = np.array([scores[p] for p in params], dtype=np.float64)
    med = np.median(vals)
    mad = np.median(np.abs(vals - med)) or 1e-6
    # Huber weight: 1 for inliers, shrinks for points >1.5*MAD from median.
    robust_w = np.clip(1.5 * mad / (np.abs(vals - med) + 1e-9), 0.4, 1.0)

    raw_weights = np.array([weights.get(p, 0) for p in params], dtype=np.float64)
    adj_weights = raw_weights * robust_w
    adj_weights = adj_weights / adj_weights.sum() * raw_weights.sum()

    breakdown_rows = []
    for p, w_raw, w_adj, v in zip(params, raw_weights, adj_weights, vals):
        breakdown_rows.append({
            "Parameter": p, "Weight (%)": round(float(w_raw), 1),
            "Score (0-1)": round(float(v), 3),
            "Weighted Score": round(float(w_adj / 100 * v), 4),
        })
    overall = sum(r["Weighted Score"] for r in breakdown_rows) / (raw_weights.sum() / 100)
    overall_100 = float(np.clip(overall * 100, 0, 100))
    return {
        "overall_score": round(overall_100, 1),
        "quality_level": level_for_score100(overall_100),
        "breakdown": breakdown_rows,
        "confidence_pct": round(float(np.clip(100 - mad * 60, 55, 99)), 0),
    }


# --------------------------------------------------------------------------
# ISO 19157 dimension mapping
# --------------------------------------------------------------------------
def compute_iso19157(scores: dict, raster: LoadedRaster, meta: dict) -> list:
    completeness = float(np.clip(1 - raster.nodata_fraction, 0, 1))

    if raster.bands > 1:
        band_means = [float(np.mean(raster.array[..., b])) for b in range(min(raster.bands, 6))]
        cv = np.std(band_means) / (np.mean(band_means) + 1e-6)
        logical_consistency = float(np.clip(1 - cv, 0, 1))
    else:
        logical_consistency = float(np.clip(0.7 + 0.3 * scores["Radiometric Quality"], 0, 1))

    has_geo = bool(raster.xres and raster.yres)
    positional_accuracy = 0.90 if has_geo else 0.75

    temporal_quality = 0.92 if meta.get("acquisition_date") else 0.70

    thematic_accuracy = float(np.clip(
        0.4 * scores["Radiometric Quality"] + 0.3 * scores["SNR"] + 0.3 * scores["Contrast"], 0, 1
    ))

    usability = float(np.clip(np.mean([
        completeness, logical_consistency, positional_accuracy, temporal_quality, thematic_accuracy,
        scores["Sharpness"],
    ]), 0, 1))

    dims = [
        ("✅", "Completeness", "Degree to which all required data is present in the image",
         completeness, "Missing Data %, Coverage",
         f"{(1-completeness)*100:.1f}% no-data / zero pixels detected."),
        ("🧩", "Logical Consistency", "Degree to which data is logically consistent across bands/values",
         logical_consistency, "Consistency Index",
         "Band statistics are consistent." if raster.bands > 1 else "Single-band consistency proxy used."),
        ("📍", "Positional Accuracy", "Accuracy of geometric position of image objects",
         positional_accuracy, "GeoTIFF pixel-scale presence",
         "Geo-referencing tags detected in the file." if has_geo else "No geo-referencing tags found; using conservative estimate."),
        ("🕒", "Temporal Quality", "Accuracy of time information of the image",
         temporal_quality, "Filename/EXIF Timestamp Parse",
         "Acquisition date parsed from filename." if meta.get("acquisition_date") else "No acquisition date could be parsed."),
        ("🎯", "Thematic Accuracy", "Accuracy of thematic/radiometric & spectral information",
         thematic_accuracy, "Radiometric+SNR+Contrast composite",
         "Derived from radiometric quality, SNR and contrast scores."),
        ("👤", "Usability", "Suitability of image for the intended use",
         usability, "Fitness-for-use composite",
         "Aggregate of all dimensions above plus sharpness."),
    ]
    rows = []
    for icon, name, desc, score, metric_used, interp in dims:
        rows.append({
            "Icon": icon, "Dimension": name, "Description": desc,
            "Score": round(float(score), 3), "Achievement": level_for_score01(score),
            "Metric Used": metric_used, "Interpretation": interp,
        })
    return rows


# --------------------------------------------------------------------------
# 7. Comparative analysis vs. classical IQA metrics
# --------------------------------------------------------------------------
def _prep_pair(a: np.ndarray, b: np.ndarray):
    """Resize/clip a pair of arrays so reference-based metrics can run."""
    if a.shape != b.shape:
        h = min(a.shape[0], b.shape[0])
        w = min(a.shape[1], b.shape[1])
        a = a[:h, :w]
        b = b[:h, :w]
    lo = min(a.min(), b.min())
    hi = max(a.max(), b.max())
    if hi <= lo:
        hi = lo + 1
    a_n = (a - lo) / (hi - lo)
    b_n = (b - lo) / (hi - lo)
    return a_n.astype(np.float64), b_n.astype(np.float64)


def _niqe_like(gray: np.ndarray) -> float:
    """Lightweight, no-reference 'naturalness' proxy in the spirit of NIQE:
    natural images have Gaussian-like local mean-subtracted-contrast-
    normalised (MSCN) coefficient statistics. We score by how close the
    MSCN kurtosis is to the Gaussian value of 3. This is a heuristic
    approximation, not the trained NIQE model."""
    mu = ndimage.gaussian_filter(gray, 7 / 6)
    mu_sq = mu * mu
    sigma = np.sqrt(np.abs(ndimage.gaussian_filter(gray * gray, 7 / 6) - mu_sq)) + 1e-6
    mscn = (gray - mu) / sigma
    kurt = float(np.mean(mscn ** 4) / (np.mean(mscn ** 2) ** 2 + 1e-9))
    naturalness = 1.0 - min(abs(kurt - 3.0) / 6.0, 1.0)
    return float(np.clip(naturalness, 0, 1))


def _brisque_like(gray: np.ndarray) -> float:
    """Heuristic naturalness proxy inspired by BRISQUE's use of MSCN
    coefficient variance/skewness across scales. Approximation only."""
    scores = []
    g = gray.copy()
    for _ in range(2):
        mu = ndimage.gaussian_filter(g, 7 / 6)
        sigma = np.sqrt(np.abs(ndimage.gaussian_filter(g * g, 7 / 6) - mu * mu)) + 1e-6
        mscn = (g - mu) / sigma
        var = float(np.var(mscn))
        scores.append(1.0 - min(abs(var - 1.0), 1.0))
        g = g[::2, ::2] if g.shape[0] > 8 and g.shape[1] > 8 else g
    return float(np.clip(np.mean(scores), 0, 1))


def compute_comparative_metrics(original_gray: np.ndarray, processed_gray: np.ndarray, robust_score_100: float) -> dict:
    a, b = _prep_pair(original_gray, processed_gray)
    try:
        ssim_val = float(sk_ssim(a, b, data_range=1.0))
    except Exception:
        ssim_val = 0.0
    try:
        psnr_val = float(sk_psnr(a, b, data_range=1.0))
    except Exception:
        psnr_val = 0.0

    niqe_inv = _niqe_like(processed_gray)
    brisque_inv = _brisque_like(processed_gray)

    return {
        "PRQM": robust_score_100,
        "SSIM": round(ssim_val * 100, 1),
        "PSNR_dB": round(psnr_val, 2),
        "PSNR_score": round(float(np.clip(psnr_val / 50 * 100, 0, 100)), 1),
        "NIQE_inv": round(niqe_inv * 100, 1),
        "BRISQUE_inv": round(brisque_inv * 100, 1),
    }


# --------------------------------------------------------------------------
# 7b. ML-based robust-score estimator ("suitable methods for estimation")
# --------------------------------------------------------------------------
# The classical PRQM (Section 6) combines hand-crafted metrics with FIXED
# weights + a Huber/MAD robustness correction. This section implements an
# ALTERNATIVE, machine-learning-based estimator over the same feature
# space, so the two can be compared - this is the "suitable methods for
# estimation" half of the thesis title, and it is the one genuinely
# learning-based component in the pipeline (everything else is classical
# digital image processing / robust statistics, not AI/ML).
#
# There is no human Mean-Opinion-Score dataset for in-orbit imagery here,
# so - exactly as BRISQUE/NIQE do in the published literature - the
# uploaded image itself is treated as the best available "pristine"
# reference, and a family of controlled synthetic distortions (blur,
# noise, contrast loss, quantization) is injected at known severities to
# generate (feature_vector -> ground_truth_quality) training pairs. A
# regressor then learns the mapping from features to quality, instead of
# the fixed weights used by the classical formula.
FEATURE_NAMES = ["Sharpness", "Contrast", "SNR", "Noise (Inv.)", "Edge Strength", "Radiometric Quality"]


def _feature_vector(gray: np.ndarray, bit_depth: int) -> np.ndarray:
    return np.array([
        m_sharpness(gray), m_contrast(gray), m_snr(gray),
        m_noise_inverse(gray), m_edge_strength(gray),
        m_radiometric_quality(gray, bit_depth),
    ], dtype=np.float64)


def _apply_synthetic_distortion(gray: np.ndarray, kind: str, severity: float, rng) -> np.ndarray:
    """severity in [0,1] (0 = untouched, 1 = worst)."""
    g = gray.copy()
    dr = float(g.max() - g.min()) or 1.0
    if kind == "blur":
        g = ndimage.gaussian_filter(g, sigma=0.4 + 4.0 * severity)
    elif kind == "noise":
        g = g + rng.normal(0.0, 0.15 * severity * dr, size=g.shape)
    elif kind == "contrast":
        mean = float(g.mean())
        g = mean + (g - mean) * (1.0 - 0.85 * severity)
    elif kind == "quantize":
        levels = max(2, int(256 * (1.0 - severity)))
        g = np.round((g - g.min()) / dr * (levels - 1)) / (levels - 1) * dr + g.min()
    return g


class _LinearFallback:
    """Closed-form least-squares regressor used only if scikit-learn isn't
    installed, so the estimator degrades gracefully rather than crashing."""
    def __init__(self, coef):
        self.coef = coef

    def predict(self, Xq):
        Aq = np.hstack([Xq, np.ones((Xq.shape[0], 1))])
        return Aq @ self.coef


def train_ml_quality_estimator(processed_gray: np.ndarray, bit_depth: int,
                                n_per_kind: int = 6, seed: int = 42):
    """Builds a small synthetic-distortion training set from the current
    image and fits a regressor (RandomForest if scikit-learn is available,
    otherwise a least-squares linear model) mapping feature -> quality.
    Returns (model, feature_importance_dict, X, y).
    """
    rng = np.random.default_rng(seed)
    X, y = [_feature_vector(processed_gray, bit_depth)], [1.0]  # pristine anchor
    for kind in ("blur", "noise", "contrast", "quantize"):
        for i in range(n_per_kind):
            severity = (i + 1) / n_per_kind
            distorted = _apply_synthetic_distortion(processed_gray, kind, severity, rng)
            X.append(_feature_vector(distorted, bit_depth))
            y.append(1.0 - severity)
    X = np.array(X, dtype=np.float64)
    y = np.array(y, dtype=np.float64)

    if HAS_SKLEARN:
        model = RandomForestRegressor(n_estimators=80, max_depth=5, random_state=seed)
        model.fit(X, y)
        importances = dict(zip(FEATURE_NAMES, np.round(model.feature_importances_, 3).tolist()))
    else:
        A = np.hstack([X, np.ones((X.shape[0], 1))])
        coef, *_ = np.linalg.lstsq(A, y, rcond=None)
        model = _LinearFallback(coef)
        w = np.abs(coef[:-1])
        w = w / (w.sum() + 1e-9)
        importances = dict(zip(FEATURE_NAMES, np.round(w, 3).tolist()))
    return model, importances, X, y


def ml_robust_score(processed_gray: np.ndarray, bit_depth: int) -> dict:
    """Runs the ML estimator on the current image and returns a result dict
    comparable in shape to `robust_composite()`'s output."""
    model, importances, X, y = train_ml_quality_estimator(processed_gray, bit_depth)
    feat = _feature_vector(processed_gray, bit_depth).reshape(1, -1)
    pred = float(np.clip(model.predict(feat)[0], 0.0, 1.0))
    return {
        "ml_overall_score": round(pred * 100, 1),
        "quality_level": level_for_score100(pred * 100),
        "feature_importance": importances,
        "n_training_samples": int(len(y)),
        "backend": "RandomForestRegressor (scikit-learn)" if HAS_SKLEARN else "Least-squares linear (fallback)",
    }


def evaluate_ml_estimator(processed_gray: np.ndarray, bit_depth: int,
                           n_per_kind: int = 8, test_fraction: float = 0.3,
                           seed: int = 7) -> dict:
    """Held-out evaluation of the ML estimator (RAC-4 requirement): builds
    the same synthetic-distortion sample set as `train_ml_quality_estimator`,
    but splits it into train/test BEFORE fitting, so RMSE/MAE/R2 are
    computed on samples the model never saw during training - not on the
    training data itself. Also reports wall-clock runtime as a proxy for
    "computational efficiency", one of the criteria requested by the
    committee.
    """
    t0 = time.time()
    rng = np.random.default_rng(seed)
    X, y = [_feature_vector(processed_gray, bit_depth)], [1.0]
    for kind in ("blur", "noise", "contrast", "quantize"):
        for i in range(n_per_kind):
            severity = (i + 1) / n_per_kind
            distorted = _apply_synthetic_distortion(processed_gray, kind, severity, rng)
            X.append(_feature_vector(distorted, bit_depth))
            y.append(1.0 - severity)
    X = np.array(X, dtype=np.float64)
    y = np.array(y, dtype=np.float64)

    n = len(y)
    idx = rng.permutation(n)
    n_test = max(1, int(round(n * test_fraction)))
    test_idx, train_idx = idx[:n_test], idx[n_test:]
    X_train, y_train = X[train_idx], y[train_idx]
    X_test, y_test = X[test_idx], y[test_idx]

    if HAS_SKLEARN:
        model = RandomForestRegressor(n_estimators=80, max_depth=5, random_state=seed)
        model.fit(X_train, y_train)
        backend_name = "RandomForestRegressor (scikit-learn)"
    else:
        A = np.hstack([X_train, np.ones((len(X_train), 1))])
        coef, *_ = np.linalg.lstsq(A, y_train, rcond=None)
        model = _LinearFallback(coef)
        backend_name = "Least-squares linear (fallback)"

    y_pred = np.clip(model.predict(X_test), 0.0, 1.0)
    resid = y_test - y_pred
    rmse = float(np.sqrt(np.mean(resid ** 2)))
    mae = float(np.mean(np.abs(resid)))
    ss_res = float(np.sum(resid ** 2))
    ss_tot = float(np.sum((y_test - y_test.mean()) ** 2)) or 1e-9
    r2 = float(1.0 - ss_res / ss_tot)
    runtime = time.time() - t0

    return {
        "rmse": round(rmse, 4),
        "mae": round(mae, 4),
        "r2": round(r2, 4),
        "n_train": int(len(train_idx)),
        "n_test": int(len(test_idx)),
        "runtime_sec": round(runtime, 3),
        "backend": backend_name,
    }


def get_or_compute_ml_eval() -> Optional[dict]:
    """Cache the held-out ML evaluation in session state so it isn't
    recomputed on every Streamlit rerun (e.g. every widget click)."""
    state = get_state()
    if "ml_eval" not in state and "processed_gray" in state and "raster" in state:
        state["ml_eval"] = evaluate_ml_estimator(state["processed_gray"], state["raster"].bit_depth)
    return state.get("ml_eval")


# --------------------------------------------------------------------------
# 8. Lightweight on-disk history log (drives Dashboard + trend charts)
# --------------------------------------------------------------------------
HISTORY_FIELDS = ["timestamp", "image_name", "satellite", "sensor", "date",
                   "overall_score", "quality_level", "iso_score",
                   "region", "land_cover", "season",
                   "ml_rmse", "ml_mae", "ml_r2", "ml_runtime_sec"]


def log_result(row: dict):
    exists = os.path.isfile(HISTORY_CSV)
    try:
        with open(HISTORY_CSV, "a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=HISTORY_FIELDS)
            if not exists:
                writer.writeheader()
            writer.writerow({k: row.get(k, "") for k in HISTORY_FIELDS})
    except OSError:
        pass  # read-only environment - history simply won't persist


def load_history() -> list:
    if not os.path.isfile(HISTORY_CSV):
        return []
    with open(HISTORY_CSV, newline="") as f:
        return list(csv.DictReader(f))


# --------------------------------------------------------------------------
# 9. Session-state orchestration helpers (used directly by the pages)
# --------------------------------------------------------------------------
def get_state() -> dict:
    import streamlit as st
    if "iqas" not in st.session_state:
        st.session_state["iqas"] = {}
    return st.session_state["iqas"]


def ingest_uploaded_file(uploaded_file) -> dict:
    """Called from the Image Upload page. Loads the raster, parses filename
    metadata, and stashes everything into session state."""
    raster = load_raster(uploaded_file)
    meta = parse_filename_metadata(raster.filename)
    state = get_state()
    state["raster"] = raster
    state["meta"] = meta
    state["original_gray"] = raster.gray.copy()
    state["processed_gray"] = raster.gray.copy()
    state["applied_steps"] = []
    state.pop("scores", None)
    state.pop("robust", None)
    state.pop("iso", None)
    state.pop("comparative", None)
    return meta


def run_preprocessing(options: dict):
    state = get_state()
    if "original_gray" not in state:
        return
    processed, applied = run_preprocessing_pipeline(state["original_gray"], options)
    state["processed_gray"] = processed
    state["applied_steps"] = applied
    state["preproc_options"] = options


def run_quality_analysis():
    state = get_state()
    if "raster" not in state:
        return None
    raster = state["raster"]
    gray_for_scoring = state.get("processed_gray", raster.gray)
    scoring_raster = LoadedRaster(
        array=raster.array, gray=gray_for_scoring, dtype_orig=raster.dtype_orig,
        bit_depth=raster.bit_depth, bands=raster.bands, shape=raster.shape,
        nodata_fraction=raster.nodata_fraction, driver=raster.driver,
        xres=raster.xres, yres=raster.yres, filename=raster.filename,
    )
    scores = compute_quality_parameters(scoring_raster)
    robust = robust_composite(scores)
    iso = compute_iso19157(scores, raster, state.get("meta", {}))
    comparative = compute_comparative_metrics(
        state.get("original_gray", raster.gray), gray_for_scoring, robust["overall_score"]
    )
    state["scores"] = scores
    state["robust"] = robust
    state["iso"] = iso
    state["comparative"] = comparative

    ml_eval = get_or_compute_ml_eval() or {}

    meta = state.get("meta", {})
    log_result({
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "image_name": raster.filename,
        "satellite": meta.get("satellite", "Unknown"),
        "sensor": meta.get("sensor", "Unknown"),
        "date": meta.get("acquisition_date", ""),
        "overall_score": robust["overall_score"],
        "quality_level": robust["quality_level"],
        "iso_score": round(float(np.mean([d["Score"] for d in iso])), 3),
        "region": meta.get("region", ""),
        "land_cover": meta.get("land_cover", ""),
        "season": meta.get("season", ""),
        "ml_rmse": ml_eval.get("rmse", ""),
        "ml_mae": ml_eval.get("mae", ""),
        "ml_r2": ml_eval.get("r2", ""),
        "ml_runtime_sec": ml_eval.get("runtime_sec", ""),
    })
    return scores, robust, iso, comparative


def has_image() -> bool:
    return "raster" in get_state()
