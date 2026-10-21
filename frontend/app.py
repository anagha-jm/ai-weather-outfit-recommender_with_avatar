import streamlit as st
import requests

st.set_page_config(
    page_title="AI Outfit Recommendation",
    page_icon="👕",
    layout="wide"
)

if "page" not in st.session_state:
    st.session_state.page = "login"

if "style_profile" not in st.session_state:
    st.session_state.style_profile = "Casual"

if "comfort_level" not in st.session_state:
    st.session_state.comfort_level = 50

if "user_name" not in st.session_state:
    st.session_state.user_name = "Guest"


st.markdown(
    """
    <style>
    html, body, [data-testid="stAppViewContainer"] {
        background: linear-gradient(180deg, #edf4fb 0%, #efe6f7 52%, #dce8f6 100%);
        color: #24364d;
    }

    [data-testid="stHeader"] {
        background: rgba(0, 0, 0, 0);
    }

    .stApp h1, .stApp h2, .stApp h3,
    .stApp p, .stApp label,
    .stApp .stMetric,
    .stApp .stTextInput input,
    .stApp .stButton button,
    .stApp .stAlert {
        color: #24364d !important;
    }

    .stApp h1 {
        font-size: 2.35rem;
        font-weight: 900;
        letter-spacing: 0.01em;
        text-align: center;
        color: #26394f !important;
        margin-bottom: 0.2rem;
    }

    .stApp h2 {
        color: #2f4b67 !important;
    }

    [data-testid="stMetric"] {
        background: rgba(255, 255, 255, 0.72);
        padding: 1rem;
        border-radius: 16px;
        border: 1px solid #c9d8eb;
        box-shadow: 0 12px 28px rgba(104, 135, 169, 0.22);
    }

    [data-testid="stMetricLabel"],
    [data-testid="stMetricValue"] {
        color: #24364d !important;
    }

    .stTextInput > div > div > input {
        background: rgba(255, 255, 255, 0.88);
        border: 1px solid #a8bfd9;
        border-radius: 12px;
        color: #24364d;
        padding: 0.78rem 0.95rem;
        box-shadow: inset 0 0 0 1px rgba(255,255,255,0.36);
    }

    .stButton > button {
        background: linear-gradient(180deg, #edf7ff 0%, #c9dbeb 100%);
        color: #24364d !important;
        border: 1px solid #9eb4cf;
        border-radius: 12px;
        font-weight: 700;
        padding: 0.68rem 1.3rem;
        box-shadow: 0 8px 20px rgba(126, 157, 188, 0.25);
    }

    .stButton > button:hover {
        background: linear-gradient(180deg, #ddebfb 0%, #b6cfe4 100%);
        color: #1e3450 !important;
        transform: translateY(-1px);
    }

    [data-testid="stSuccess"],
    [data-testid="stWarning"],
    [data-testid="stError"] {
        background: rgba(255, 255, 255, 0.8);
        border: 1px solid rgba(115, 137, 167, 0.5);
        color: #24364d !important;
        border-radius: 14px;
    }

    .brand-badge {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        gap: 0.5rem;
        font-size: 2.2rem;
        font-weight: 900;
        color: #2b59a6;
        margin-bottom: 1rem;
    }

    .glass-card {
        background: rgba(255, 255, 255, 0.78);
        border: 1px solid #d2dff1;
        border-radius: 20px;
        padding: 1.25rem;
        box-shadow: 0 12px 30px rgba(116, 144, 181, 0.18);
    }

    .hero-card {
        background: linear-gradient(135deg, #0f2f6b 0%, #0f6f8f 50%, #0d9a8f 100%);
        border-radius: 22px;
        padding: 1.55rem;
        color: white;
        box-shadow: 0 16px 34px rgba(20, 82, 110, 0.32);
    }

    .hero-card .hero-label {
        display: inline-block;
        font-size: 0.8rem;
        font-weight: 700;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        margin-bottom: 1rem;
        color: #dff2ff;
    }

    .hero-card .hero-title {
        font-size: 2.6rem;
        font-weight: 800;
        margin: 0.25rem 0 0.6rem 0;
    }

    .hero-card .hero-sub {
        font-size: 1rem;
        opacity: 0.96;
    }

    .fashion-card {
        background: linear-gradient(135deg, rgba(255,255,255,0.94), rgba(220,236,247,0.9));
        border: 1px solid #bcd2e6;
        border-radius: 20px;
        padding: 1.25rem;
        box-shadow: 0 14px 34px rgba(111, 145, 180, 0.24);
    }

    .fashion-card .tag {
        display: inline-block;
        padding: 0.3rem 0.7rem;
        border-radius: 999px;
        background: #d7e9f8;
        color: #4a6887;
        font-size: 0.75rem;
        font-weight: 700;
        text-transform: uppercase;
        margin-bottom: 0.75rem;
    }

    .fashion-card .title {
        font-size: 1.7rem;
        font-weight: 800;
        color: #26394f;
        margin-bottom: 0.4rem;
    }

    .fashion-card .text {
        font-size: 1rem;
        color: #2f4b67;
        line-height: 1.6;
    }

    .image-chip {
        text-align: center;
        background: rgba(255,255,255,0.9);
        border: 1px solid #d3dfef;
        border-radius: 16px;
        padding: 1rem 0.75rem;
        box-shadow: 0 8px 20px rgba(111,145,180,0.18);
    }

    .image-chip .emoji {
        font-size: 2rem;
        display: block;
        margin-bottom: 0.35rem;
    }

    .image-chip .label {
        font-size: 0.8rem;
        color: #4a6887;
        font-weight: 700;
    }

    .login-shell {
        max-width: 560px;
        margin: 0 auto;
        background: rgba(255,255,255,0.82);
        border: 1px solid #d3dff1;
        border-radius: 20px;
        padding: 2rem;
        box-shadow: 0 20px 40px rgba(114, 141, 177, 0.18);
    }

    .login-title {
        font-size: 2rem;
        font-weight: 800;
        text-align: center;
        color: #244262;
        margin-bottom: 0.5rem;
    }

    .center-wrap {
        display: flex;
        justify-content: center;
        align-items: flex-start;
        min-height: auto;
        padding-top: 0;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def style_card(label, emoji, desc):
    st.markdown(
        f"""
        <div class="image-chip">
            <span class="emoji">{emoji}</span>
            <div class="label">{label}</div>
            <div style="font-size:0.72rem;color:#6b7f96;margin-top:0.2rem;">{desc}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_login_page():
    st.markdown("<div class='center-wrap'><div class='login-shell'>", unsafe_allow_html=True)
    st.markdown("<div class='brand-badge'>🧿 Dina</div>", unsafe_allow_html=True)
    st.markdown("<div class='login-title'>Welcome back</div>", unsafe_allow_html=True)

    name = st.text_input("Enter Name or Email Address", value="", placeholder="e.g. diya@gmail.com")
    password = st.text_input("Password", type="password", placeholder="••••••••")

    if st.button("Sign In / Continue", use_container_width=True):
        if name.strip():
            st.session_state.user_name = name.strip()
            st.session_state.page = "style"
            st.rerun()
        else:
            st.warning("Please enter your name or email.")

    if st.button("Continue as Guest", use_container_width=True):
        st.session_state.user_name = "Guest"
        st.session_state.page = "style"
        st.rerun()

    st.markdown("</div></div>", unsafe_allow_html=True)


def render_style_page():
    st.title("🎨 Personalize Your Stylist")
    st.write("Configure preferences below")

    st.markdown(
        """
        <div class="glass-card">
        <div style="font-size:1rem;font-weight:700;color:#2f4b67;margin-bottom:0.6rem;">What style are you looking for today?</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    style_options = ["Casual", "Formal"]
    st.session_state.style_profile = st.radio(
        "Choose your dressing style",
        style_options,
        index=style_options.index(st.session_state.style_profile) if st.session_state.style_profile in style_options else 0,
        horizontal=True,
    )

    st.session_state.comfort_level = st.slider(
        "Your weather comfort sensitivity profile:",
        min_value=0,
        max_value=100,
        value=st.session_state.comfort_level,
    )

    if st.button("Go to Recommendation Dashboard"):
        st.session_state.page = "dashboard"
        st.rerun()


def render_dashboard():
    user_name = st.session_state.user_name
    st.title(f"Hey, {user_name} 👋")

    left_col, right_col = st.columns([1.75, 1])

    with left_col:
        st.markdown(
            f"""
            <div class="hero-card">
                <div class="hero-label">📍 Active Weather</div>
                <div class="hero-title">{st.session_state.style_profile} Mode</div>
                <div class="hero-sub">Your look selection is now being paired with live forecast data.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        city = st.text_input("Enter city", placeholder="Type a city name")

        if st.button("Predict Outfit", use_container_width=True):
            if city.strip() == "":
                st.warning("Please enter a city.")
            else:
                url = "http://127.0.0.1:5000/predict"
                try:
                    response = requests.post(
                        url,
                        json={
                            "city": city,
                            "style": st.session_state.style_profile,
                            "comfort_level": st.session_state.comfort_level,
                        }
                    )

                    if response.status_code != 200:
                        st.error("City not found.")
                        st.stop()

                    data = response.json()
                    current = data["current"]
                    forecast = data["forecast"]

                    st.success("Prediction Successful!")

                    c1, c2 = st.columns(2)
                    c1.metric("🌡 Current Temp", f"{current['temperature']} °C")
                    c2.metric("💧 Humidity", f"{current['humidity']} %")
                    c1.metric("💨 Wind Speed", f"{current['wind_speed']} km/h")
                    c2.metric("🌥 Weather Code", current["weather_code"])

                    f1, f2 = st.columns(2)
                    f1.metric("🌡 Max Temp", f"{forecast['max_temp']} °C")
                    f2.metric("❄ Min Temp", f"{forecast['min_temp']} °C")
                    f1.metric("🌧 Expected Rainfall", f"{forecast['rainfall']} mm")
                    f2.metric("💨 Max Wind Speed", f"{forecast['max_speed']} km/h")

                    st.subheader("👕 Recommended Outfit")
                    st.markdown(
                        f"""
                        <div class="fashion-card">
                            <div class="tag">{st.session_state.style_profile} fit</div>
                            <div class="title">Your Style Match</div>
                            <div class="text">{data['recommended_outfit']}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                    style_card("Top", "🟢", "Light layer")
                    style_card("Bottom", "🩳", "Comfort fit")
                    style_card("Shoes", "👟", "Weather-ready")

                except Exception as e:
                    st.error(str(e))

    with right_col:
        st.markdown(
            """
            <div class="glass-card">
                <div style="font-size:1rem;font-weight:800;color:#244262;">Model Prediction</div>
                <div style="margin-top:0.7rem;font-size:1.5rem;font-weight:800;color:#24364d;">Casual Combination</div>
                <div style="margin-top:0.4rem;color:#60809f;">Bias: Neutral</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

        outfit_image_cols = st.columns(3)
        with outfit_image_cols[0]:
            style_card("Top", "👕", "Upper garment")
        with outfit_image_cols[1]:
            style_card("Lower", "🩳", "Lower segment")
        with outfit_image_cols[2]:
            style_card("Shoes", "👟", "Footwear")

        if st.button("Reset Session", use_container_width=True):
            for key in ["page", "style_profile", "comfort_level", "user_name"]:
                st.session_state.pop(key, None)
            st.session_state.page = "login"
            st.rerun()


if st.session_state.page == "login":
    render_login_page()
elif st.session_state.page == "style":
    render_style_page()
else:
    render_dashboard()