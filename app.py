"""
IQAS - In-Orbit Image Quality Assessment System
app.py — Step 1: Login Screen. This is the entry point of the multipage
Streamlit project; run with: streamlit run app.py
"""

import streamlit as st

st.set_page_config(page_title="IQAS - Login", page_icon="🛰️", layout="wide")

st.markdown(
    """
    <style>
    #MainMenu, header, footer {visibility: hidden;}
    .stApp { background: radial-gradient(ellipse at top left, #1a1f4d 0%, #05061a 55%, #000000 100%); }
    .block-container { padding-top: 1rem; max-width: 1500px; }
    .step-badge {
        background-color: #4F46E5; color: white; padding: 8px 18px;
        border-radius: 6px; font-weight: 700; font-size: 15px; display: inline-block;
        margin-bottom: 24px;
    }
    .brand-title { font-size: 34px; font-weight: 800; color: white; margin-bottom: 0; }
    .brand-sub { font-size: 20px; color: #E5E7EB; font-weight: 600; line-height: 1.3; margin-top: 10px; }
    .brand-divider { width: 60px; height: 3px; background-color: #6366F1; margin: 14px 0 10px 0; }
    .brand-iso { color: #A5B4FC; font-size: 14px; margin-bottom: 30px; }
    .feature-row { display: flex; align-items: center; gap: 14px; margin-bottom: 22px; }
    .feature-icon {
        background: rgba(99,102,241,0.25); border: 1px solid rgba(99,102,241,0.4);
        border-radius: 10px; width: 44px; height: 44px; min-width: 44px;
        display: flex; align-items: center; justify-content: center; font-size: 20px;
    }
    .feature-text { color: #E5E7EB; font-size: 15px; font-weight: 500; }
    .login-card {
        background: white; border-radius: 16px; padding: 40px 44px;
        max-width: 480px; margin: 0 auto; box-shadow: 0 20px 60px rgba(0,0,0,0.5);
    }
    .lock-circle {
        background: #EEF2FF; border-radius: 50%; width: 64px; height: 64px;
        display: flex; align-items: center; justify-content: center; font-size: 28px;
        margin: 0 auto 14px auto;
    }
    .welcome-title { text-align: center; font-size: 24px; font-weight: 800; color: #111827; }
    .welcome-sub { text-align: center; color: #6B7280; font-size: 14px; margin-bottom: 20px; }
    .login-btn button { background-color: #4F46E5; color: white; border: none; border-radius: 8px; font-weight: 700; height: 46px; }
    .google-btn button { background-color: white; color: #111827; border: 1px solid #D1D5DB; border-radius: 8px; font-weight: 700; height: 46px; }
    .footer-note { color: #9CA3AF; font-size: 13px; margin-top: 30px; }
    </style>
    """,
    unsafe_allow_html=True,
)

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

st.markdown('<div class="step-badge">Step 1: Login Screen</div>', unsafe_allow_html=True)

left, right = st.columns([1.15, 1], gap="large")

with left:
    top_l, top_r = st.columns([4, 1])
    with top_r:
        st.markdown("<div style='text-align:right;color:white;'>🌗 &nbsp; English ⌄</div>", unsafe_allow_html=True)

    st.markdown('<div class="brand-title">🛰️ IQAS</div>', unsafe_allow_html=True)
    st.markdown('<div class="brand-sub">In-Orbit Image Quality<br>Assessment System</div>', unsafe_allow_html=True)
    st.markdown('<div class="brand-divider"></div>', unsafe_allow_html=True)
    st.markdown('<div class="brand-iso">ISO 19157 Aligned</div>', unsafe_allow_html=True)
    st.markdown("<br>" * 3, unsafe_allow_html=True)

    features = [
        ("🖼️", "Upload In-Orbit Images"),
        ("📊", "Analyze Quality Parameters"),
        ("🛡️", "ISO 19157 Aligned Assessment"),
        ("📄", "Generate Reports & Insights"),
    ]
    for icon, text in features:
        st.markdown(
            f'<div class="feature-row"><div class="feature-icon">{icon}</div>'
            f'<div class="feature-text">{text}</div></div>',
            unsafe_allow_html=True,
        )
    st.markdown('<div class="footer-note">© 2024 IQAS. All rights reserved.</div>', unsafe_allow_html=True)

with right:
    st.write("")
    st.markdown('<div class="login-card">', unsafe_allow_html=True)
    st.markdown('<div class="lock-circle">🔒</div>', unsafe_allow_html=True)
    st.markdown('<div class="welcome-title">Welcome Back!</div>', unsafe_allow_html=True)
    st.markdown('<div class="welcome-sub">Login to your account</div>', unsafe_allow_html=True)

    username = st.text_input("Username", placeholder="Enter your username")
    password = st.text_input("Password", placeholder="Enter your password", type="password")

    _, fp2 = st.columns([2, 1])
    with fp2:
        st.markdown(
            "<div style='text-align:right;'><a href='#' style='color:#4F46E5;font-size:13px;"
            "text-decoration:none;'>Forgot Password?</a></div>",
            unsafe_allow_html=True,
        )

    st.write("")
    st.markdown('<div class="login-btn">', unsafe_allow_html=True)
    login_clicked = st.button("Login", use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div style='text-align:center;color:#9CA3AF;font-size:13px;margin:14px 0;'>or</div>", unsafe_allow_html=True)

    st.markdown('<div class="google-btn">', unsafe_allow_html=True)
    google_clicked = st.button("🇬  Login with Google", use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

    st.checkbox("Remember me")
    st.markdown("</div>", unsafe_allow_html=True)

    if login_clicked:
        if username and password:
            st.session_state.logged_in = True
            st.success(f"Welcome, {username}! Redirecting to Dashboard...")
            st.switch_page("pages/1_Dashboard.py")
        else:
            st.error("Please enter both username and password.")
    if google_clicked:
        st.info("Google OAuth login flow would trigger here.")
