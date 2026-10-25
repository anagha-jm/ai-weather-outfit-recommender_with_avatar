import logging
import re
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path

import requests
import streamlit as st
from werkzeug.security import check_password_hash, generate_password_hash

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.outfit_catalog import OUTFIT_AVATAR_FILES, WEATHER_SUITABLE_OUTFITS

st.set_page_config(
    page_title="Dina",
    page_icon="☀️",
    layout="wide",
)

APP_DIR = Path(__file__).resolve().parent
AVATAR_BASE_DIR = APP_DIR / "assets" / "avatars"
AUTH_DB_PATH = PROJECT_ROOT / "data" / "dina_auth.db"
API_BASE_URL = "http://127.0.0.1:5000"
STYLE_OPTIONS = ["Casual", "Any"]
OCCASION_OPTIONS = ["Casual", "College", "Work / Formal", "Presentation", "Interview", "Outdoor / Sports", "Party"]
AVATAR_STYLE_OPTIONS = ["Female", "Male"]
OCCASION_API_MAP = {
    "Casual": "Casual",
    "College": "Casual",
    "Work / Formal": "Any",
    "Presentation": "Any",
    "Interview": "Any",
    "Outdoor / Sports": "Any",
    "Party": "Any",
}

COMFORT_OPTIONS = {
    "Light & Breezy": {"comfort_level": 30, "description": "Airy, effortless and best for warm weather."},
    "Balanced Comfort": {"comfort_level": 50, "description": "A comfortable middle ground for most days."},
    "Warm & Cozy": {"comfort_level": 70, "description": "Cosier layers for cooler mornings and evenings."},
}
OCCASION_IMAGE_KEYS = {
    "Casual": "casual",
    "College": "college",
    "Work / Formal": "work",
    "Presentation": "presentation",
    "Interview": "interview",
    "Outdoor / Sports": "sports",
    "Party": "party",
}
COMFORT_IMAGE_KEYS = {
    "Light & Breezy": "light",
    "Balanced Comfort": "balanced",
    "Warm & Cozy": "warm",
}
WEATHER_IMAGE_COMFORT = {"hot": "light", "cold": "warm"}
AVATAR_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}


@dataclass(frozen=True)
class WeatherAvatarSelection:
    image_path: Path | None
    fallback_message: str | None = None


def init_auth_store():
    AUTH_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(AUTH_DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                display_name TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.commit()


def validate_email(email):
    if not email:
        return False
    pattern = re.compile(r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+$")
    return bool(pattern.fullmatch(email.strip()))


def is_strong_password(password):
    if len(password) < 8:
        return False
    has_letter = any(ch.isalpha() for ch in password)
    has_digit = any(ch.isdigit() for ch in password)
    has_symbol = any(not ch.isalnum() for ch in password)
    return has_letter and has_digit and has_symbol


def create_user_account(email, password, display_name):
    trimmed_email = (email or "").strip().lower()
    trimmed_name = (display_name or "").strip()
    if not validate_email(trimmed_email):
        return False
    if not trimmed_name:
        return False
    if not is_strong_password(password):
        return False

    with sqlite3.connect(AUTH_DB_PATH) as conn:
        existing = conn.execute("SELECT 1 FROM users WHERE email = ?", (trimmed_email,)).fetchone()
        if existing:
            return False
        password_hash = generate_password_hash(password, method="pbkdf2:sha256", salt_length=16)
        conn.execute(
            "INSERT INTO users (email, password_hash, display_name) VALUES (?, ?, ?)",
            (trimmed_email, password_hash, trimmed_name),
        )
        conn.commit()
    return True


def authenticate_user(email, password):
    trimmed_email = (email or "").strip().lower()
    if not trimmed_email or not password:
        return False

    with sqlite3.connect(AUTH_DB_PATH) as conn:
        row = conn.execute(
            "SELECT email, password_hash, display_name FROM users WHERE email = ?",
            (trimmed_email,),
        ).fetchone()

    if not row:
        return False

    stored_email, password_hash, display_name = row
    if not check_password_hash(password_hash, password):
        return False

    return {"email": stored_email, "display_name": display_name}


init_auth_store()


def get_comfort_level(choice):
    option = COMFORT_OPTIONS.get(choice, COMFORT_OPTIONS["Balanced Comfort"])
    return int(option["comfort_level"])


def build_api_payload(city, style=None, occasion=None, comfort_level=None):
    selected_occasion = occasion or st.session_state.get("occasion", "Casual")
    mapped_occasion = OCCASION_API_MAP.get(selected_occasion, "Casual")
    return {
        "city": city,
        "style": style or st.session_state.get("style", "Casual"),
        "occasion": mapped_occasion,
        "comfort_level": comfort_level if comfort_level is not None else st.session_state.get("comfort_level", 50),
    }


def set_page(page_name):
    st.session_state.page = page_name


def reset_flow():
    st.session_state.page = "welcome"
    st.session_state.authenticated = False
    st.session_state.display_name = ""
    st.session_state.email = ""
    st.session_state.city = ""
    st.session_state.style = "Casual"
    st.session_state.occasion = "Casual"
    st.session_state.avatar_style = "Female"
    st.session_state.comfort_option = "Balanced Comfort"
    st.session_state.comfort_level = get_comfort_level(st.session_state.comfort_option)
    st.session_state.last_result = None
    st.session_state.login_error = ""
    st.session_state.signup_error = ""
    st.session_state.auth_signup_mode = False


if "page" not in st.session_state:
    st.session_state.page = "welcome"
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "display_name" not in st.session_state:
    st.session_state.display_name = ""
if "email" not in st.session_state:
    st.session_state.email = ""
if "city" not in st.session_state:
    st.session_state.city = ""
if "style" not in st.session_state:
    st.session_state.style = "Casual"
if "occasion" not in st.session_state:
    st.session_state.occasion = "Casual"
if "avatar_style" not in st.session_state:
    st.session_state.avatar_style = "Female"
if "comfort_option" not in st.session_state:
    st.session_state.comfort_option = "Balanced Comfort"
if "comfort_level" not in st.session_state:
    st.session_state.comfort_level = COMFORT_OPTIONS[st.session_state.comfort_option]["comfort_level"]
if "last_result" not in st.session_state:
    st.session_state.last_result = None
if "login_error" not in st.session_state:
    st.session_state.login_error = ""
if "signup_error" not in st.session_state:
    st.session_state.signup_error = ""
if "auth_signup_mode" not in st.session_state:
    st.session_state.auth_signup_mode = False


st.markdown(
    """
    <style>
    html, body, [data-testid="stAppViewContainer"] {
        background: #C4D0BC;
        color: #344335;
        font-family: "Segoe UI", Arial, sans-serif;
    }

    [data-testid="stHeader"] {
        background: rgba(0,0,0,0);
    }

    .dina-shell {
        max-width: 1180px;
        margin: 0 auto;
        padding: 1.4rem 0 1.2rem;
    }

    .brand-bar {
        background: rgba(245, 243, 236, 0.66);
        border: 1px solid rgba(82, 102, 79, 0.12);
        border-radius: 26px;
        padding: 1rem 1.3rem;
        box-shadow: 0 10px 26px rgba(50, 66, 53, 0.08);
    }

    .brand-name {
        font-size: 2.4rem;
        font-weight: 800;
        letter-spacing: -0.07em;
        color: #344335;
        margin: 0;
    }

    .tagline {
        font-size: 1rem;
        color: #52664F;
        margin: 0.3rem 0 0;
    }

    .welcome-card {
        background: rgba(245, 243, 236, 0.88);
        border: 1px solid rgba(82, 102, 79, 0.12);
        border-radius: 30px;
        padding: 2.2rem 1.5rem 1.5rem;
        box-shadow: 0 18px 34px rgba(52, 67, 53, 0.08);
        text-align: center;
        max-width: 760px;
        margin: 0 auto;
    }

    .hero-copy {
        max-width: 640px;
        margin: 0 auto 1.4rem;
    }

    .hero-title {
        font-size: clamp(2.8rem, 5vw, 4.5rem);
        letter-spacing: -0.08em;
        font-weight: 800;
        color: #344335;
        margin: 0;
    }

    .hero-subtitle {
        margin-top: 1rem;
        font-size: 1.15rem;
        color: #52664F;
        line-height: 1.6;
    }

    .section-label {
        font-size: 0.72rem;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        color: #52664F;
        font-weight: 700;
        margin: 0 0 0.8rem;
    }

    .muted {
        color: #52664F;
    }

    .info-note {
        background: rgba(228, 233, 223, 0.9);
        border: 1px solid rgba(82, 102, 79, 0.08);
        border-radius: 14px;
        padding: 0.8rem 0.9rem;
        color: #344335;
    }

    .option-card {
        background: #E4E9DF;
        border: 1px solid rgba(82, 102, 79, 0.12);
        border-radius: 18px;
        padding: 1rem;
        min-height: 120px;
        cursor: pointer;
        transition: all 0.2s ease;
        text-align: left;
    }

    .option-card:hover {
        transform: translateY(-1px);
        box-shadow: 0 12px 20px rgba(52, 67, 53, 0.08);
    }

    .option-card.selected {
        background: #52664F;
        color: #F5F3EC;
        border: 2px solid #344335;
        box-shadow: 0 14px 24px rgba(82, 102, 79, 0.14);
    }

    .selection-head {
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 0.5rem;
        margin-bottom: 0.3rem;
    }

    .selection-check {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        min-width: 1.6rem;
        height: 1.6rem;
        border-radius: 50%;
        background: rgba(245, 243, 236, 0.14);
        border: 1px solid rgba(245, 243, 236, 0.6);
        font-weight: 800;
        font-size: 0.9rem;
    }

    .option-title {
        font-size: 1.05rem;
        font-weight: 700;
    }

    .option-desc {
        font-size: 0.9rem;
        line-height: 1.5;
        opacity: 0.92;
    }

    .metric-card {
        background: rgba(255,255,255,0.38);
        border: 1px solid rgba(82, 102, 79, 0.12);
        border-radius: 18px;
        padding: 0.8rem 0.9rem;
        min-height: 88px;
    }

    .metric-card .label {
        font-size: 0.68rem;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        color: #52664F;
        font-weight: 700;
        margin-bottom: 0.45rem;
    }

    .metric-card .value {
        font-size: 1.52rem;
        line-height: 1.1;
        font-weight: 700;
        color: #344335;
    }

    .avatar-stage {
        background: #C4D0BC;
        border-radius: 20px;
        padding: 0.15rem;
        display: flex;
        align-items: center;
        justify-content: center;
        min-height: 220px;
        overflow: hidden;
    }

    .avatar-stage img {
        display: block;
        max-width: 420px;
        width: 100%;
        height: auto;
        margin: 0 auto;
    }

    .recommendation-card {
        background: rgba(255,255,255,0.26);
        border: 1px solid rgba(82, 102, 79, 0.12);
        border-radius: 22px;
        padding: 1rem;
        margin-top: 0;
    }

    .tag-row {
        display: flex;
        flex-wrap: wrap;
        gap: 0.45rem;
        margin: 0.4rem 0 0.7rem;
    }

    .tag {
        display: inline-block;
        border-radius: 999px;
        background: #E4E9DF;
        border: 1px solid rgba(82, 102, 79, 0.12);
        color: #344335;
        padding: 0.28rem 0.6rem;
        font-size: 0.77rem;
        font-weight: 600;
    }

    .stButton > button {
        background: #E4E9DF;
        color: #344335;
        border: 1px solid rgba(82, 102, 79, 0.12);
        border-radius: 18px;
        padding: 0.9rem 1rem;
        font-weight: 700;
        text-align: center;
        width: 100%;
        box-shadow: none;
    }

    .stButton > button:hover {
        background: #DCE4D8;
        color: #344335;
    }

    div[data-testid="stButton"] > button[kind="primary"] {
        background: #52664F !important;
        color: #ffffff !important;
        border: 1px solid #52664F !important;
        box-shadow: 0 10px 18px rgba(82, 102, 79, 0.18);
    }

    div[data-testid="stButton"] > button[kind="secondary"] {
        background: #E4E9DF !important;
        color: #344335 !important;
        border: 1px solid rgba(82, 102, 79, 0.12) !important;
    }

    .stTextInput > div > div > input,
    .stSelectbox > div > div {
        background: rgba(255,255,255,0.5);
        border: 1px solid rgba(82, 102, 79, 0.12);
        border-radius: 12px;
        color: #344335;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def render_tag_list(values):
    items = values or []
    if not items:
        return "<span class='muted'>No items listed</span>"
    tags = "".join(f"<span class='tag'>{value}</span>" for value in items if value)
    return f"<div class='tag-row'>{tags}</div>"


def render_header():
    st.markdown(
        """
        <div class='dina-shell'>
            <div class='brand-bar'>
                <div class='brand-name'>Dina</div>
                <div class='tagline'>Weather-aware outfit recommendations for everyday life.</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_selection_card(label, description, selected, key_prefix):
    del description
    return st.button(label, key=f"{key_prefix}_{label}", use_container_width=True, type="primary" if selected else "secondary")


def render_recommendation_card(outfit, primary=False):
    if not isinstance(outfit, dict):
        return

    name = outfit.get("name") or "Unnamed outfit"
    score = outfit.get("weather_match_score")
    explanation = outfit.get("explanation") or "No explanation provided."
    clothing_items = outfit.get("clothing_items") or []
    accessories = outfit.get("accessories") or []
    style = outfit.get("style") or "Casual"
    occasion = outfit.get("occasion") or "Any"
    badge = "Primary recommendation" if primary else "Alternative"
    score_value = f"{score}/100" if score is not None else "Score unavailable"

    st.markdown(
        f"""
        <div class="recommendation-card">
            <div class="section-label" style="margin-bottom: 0.4rem;">{badge}</div>
            <div style="display: flex; justify-content: space-between; align-items: center; gap: 0.75rem; margin-bottom: 0.7rem;">
                <h3 style="margin: 0; font-size: 1.5rem; color: #344335;">{name}</h3>
                <span style="background: #E4E9DF; border-radius: 999px; padding: 0.28rem 0.65rem; font-size: 0.76rem; font-weight: 700; color: #344335;">{score_value}</span>
            </div>
            <div class="tag-row">
                <span class="tag">{style}</span>
                <span class="tag">{occasion}</span>
            </div>
            <div class="section-label" style="margin-top: 0.3rem;">Clothing</div>
            {render_tag_list(clothing_items)}
            <div class="section-label" style="margin-top: 0.3rem;">Accessories</div>
            {render_tag_list(accessories)}
            <div class="section-label" style="margin-top: 0.3rem;">Why it fits</div>
            <div class='muted'>{explanation}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def fetch_recommendation(city, style, occasion, comfort_level):
    payload = build_api_payload(city, style=style, occasion=occasion, comfort_level=comfort_level)
    response = requests.post(f"{API_BASE_URL}/predict", json=payload, timeout=20)

    if response.status_code != 200:
        try:
            details = response.json()
        except ValueError:
            details = {}
        message = details.get("error") if isinstance(details, dict) else None
        raise ValueError(message or "Unable to get recommendations right now.")

    try:
        data = response.json()
    except ValueError as exc:
        raise ValueError("The API returned invalid JSON.") from exc

    if not isinstance(data, dict):
        raise ValueError("The API returned an unexpected response format.")

    if not isinstance(data.get("city"), str) or not data["city"].strip():
        raise ValueError("The API response is missing a valid city.")
    if not isinstance(data.get("current"), dict) or not isinstance(data.get("forecast"), dict):
        raise ValueError("The API response is missing valid current weather or forecast data.")
    weather_category = data.get("weather_category")
    if weather_category is not None and (
        not isinstance(weather_category, str)
        or weather_category not in WEATHER_SUITABLE_OUTFITS
    ):
        raise ValueError("The API returned an invalid weather category.")

    ranked = data.get("ranked_outfits")
    if ranked is not None:
        if not isinstance(ranked, list):
            raise ValueError("The API returned an invalid ranked_outfits list.")
        if any(
            not isinstance(outfit, dict)
            or not isinstance(outfit.get("name"), str)
            or not outfit["name"].strip()
            for outfit in ranked
        ):
            raise ValueError("The API returned an invalid outfit in ranked_outfits.")

    recommended = data.get("recommended_outfit")
    if recommended is not None and recommended != "" and (
        not isinstance(recommended, str) or not recommended.strip()
    ):
        raise ValueError("The API returned an invalid recommended_outfit.")

    return data


def get_primary_outfit(data, ranked_outfits):
    recommended_name = data.get("recommended_outfit")
    if recommended_name:
        for outfit in ranked_outfits:
            if outfit["name"] == recommended_name:
                return outfit
        return {"name": recommended_name}
    return ranked_outfits[0] if ranked_outfits else None


def get_avatar_path_for_outfit(outfit_name, avatar_style):
    if not outfit_name:
        return None

    avatar_key = (avatar_style or "Female").strip().lower()
    if avatar_key not in {"female", "male"}:
        avatar_key = "female"

    image_name = OUTFIT_AVATAR_FILES.get(outfit_name)
    if not image_name:
        logging.warning("No avatar mapping found for outfit: %s", outfit_name)
        return None

    avatar_path = AVATAR_BASE_DIR / avatar_key / image_name
    if not avatar_path.exists():
        logging.warning("Missing avatar image: %s", avatar_path)
        return None

    return avatar_path


def render_avatar_for_outfit(outfit_name, avatar_style):
    avatar_path = get_avatar_path_for_outfit(outfit_name, avatar_style)
    if avatar_path is None:
        st.info(f"Avatar image unavailable for {outfit_name} in {avatar_style} style. Check the asset file for this outfit.")
        return

    st.image(str(avatar_path), use_container_width=False, width=420)


def _normalized_avatar_stem(stem):
    stem = re.sub(r"\s*\(\d+\)$", "", stem)
    return re.sub(r"[^a-z0-9]+", "_", stem.casefold()).strip("_")


def select_weather_avatar(gender, weather_category, occasion, vibe):
    """Return a same-gender image that is explicitly compatible with the weather."""
    gender_key = str(gender or "").strip().casefold()
    weather_key = str(weather_category or "").strip().casefold()
    if gender_key not in {"male", "female"}:
        logging.warning("No avatar selected for unsupported gender: %r", gender)
        return WeatherAvatarSelection(None, "Choose a male or female avatar.")
    if weather_key not in WEATHER_SUITABLE_OUTFITS:
        logging.warning("No avatar selected for unsupported weather category: %r", weather_category)
        return WeatherAvatarSelection(None, "The predicted weather category is unavailable.")
    if occasion not in OCCASION_IMAGE_KEYS:
        logging.warning("No avatar selected for unsupported occasion: %r", occasion)
        return WeatherAvatarSelection(None, "The selected occasion has no image mapping.")
    if vibe not in COMFORT_IMAGE_KEYS:
        logging.warning("No avatar selected for unsupported vibe: %r", vibe)
        return WeatherAvatarSelection(None, "The selected comfort preference has no image mapping.")

    gender_dir = AVATAR_BASE_DIR / gender_key
    if not gender_dir.is_dir():
        logging.warning("Avatar gender directory is missing: %s", gender_dir)
        return WeatherAvatarSelection(None, f"No avatar images are available for {gender_key}.")

    candidates = [
        path
        for path in gender_dir.iterdir()
        if path.is_file() and path.suffix.casefold() in AVATAR_IMAGE_EXTENSIONS
    ]
    by_stem = {}
    for path in candidates:
        by_stem.setdefault(_normalized_avatar_stem(path.stem), []).append(path)

    def find_image(stem):
        matches = by_stem.get(_normalized_avatar_stem(stem), [])
        if not matches:
            return None
        matches.sort(
            key=lambda path: (
                bool(re.search(r"\s*\(\d+\)$", path.stem)),
                path.name.casefold(),
            )
        )
        return matches[0]

    required_comfort = WEATHER_IMAGE_COMFORT.get(weather_key)
    if required_comfort:
        preferred_stem = (
            f"{OCCASION_IMAGE_KEYS[occasion]}_{required_comfort}"
        )
        preferred_image = find_image(preferred_stem)
        if preferred_image:
            if COMFORT_IMAGE_KEYS[vibe] == required_comfort:
                return WeatherAvatarSelection(preferred_image)
            message = (
                f"The {weather_key}-suitable image uses the "
                f"{required_comfort} style, which takes priority over your "
                f"{COMFORT_IMAGE_KEYS[vibe]} preference."
            )
            logging.info(
                "Weather-compatible avatar overrides vibe: gender=%s weather=%s "
                "occasion=%s requested_vibe=%s image=%s",
                gender_key,
                weather_key,
                occasion,
                vibe,
                preferred_image.name,
            )
            return WeatherAvatarSelection(preferred_image, message)

    fallback_names = [
        OUTFIT_AVATAR_FILES[outfit_name]
        for outfit_name in WEATHER_SUITABLE_OUTFITS[weather_key]
    ]
    for image_name in fallback_names:
        fallback_image = find_image(Path(image_name).stem)
        if fallback_image:
            if weather_key == "rainy":
                message = (
                    "No occasion/vibe image has verified rainy-weather suitability; "
                    "showing the catalog's rain-outfit avatar instead."
                )
            else:
                message = (
                    f"No {occasion} image is available for the {weather_key}-suitable "
                    f"style; showing a catalog avatar suitable for {weather_key} weather."
                )
            logging.warning(
                "Using weather-safe avatar fallback: gender=%s weather=%s "
                "occasion=%s vibe=%s image=%s",
                gender_key,
                weather_key,
                occasion,
                vibe,
                fallback_image.name,
            )
            return WeatherAvatarSelection(fallback_image, message)

    message = (
        f"No existing {weather_key}-suitable avatar image is available for "
        f"{gender_key}; no image was selected."
    )
    logging.error(
        "No weather-safe avatar match: gender=%s weather=%s occasion=%s vibe=%s",
        gender_key,
        weather_key,
        occasion,
        vibe,
    )
    return WeatherAvatarSelection(None, message)


def render_welcome_page():
    st.markdown(
        """
        <div class='welcome-card'>
            <div class='hero-copy'>
                <div class='hero-title'>Dina</div>
                <div class='hero-subtitle'>Dress for the forecast.</div>
            </div>
            <div style='max-width: 440px; margin: 0 auto;'>
                <p style='color: #344335; line-height: 1.6; margin-bottom: 1.5rem;'>Weather-aware outfit recommendations for everyday life.</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_left, col_center, col_right = st.columns([1, 1.1, 1])
    with col_center:
        if st.button("Get Started", use_container_width=True, key="welcome_get_started"):
            st.session_state.page = "login"
            st.rerun()


def render_login_page():
    st.subheader("Sign in to Dina")
    st.caption("Access your personal outfit recommendations securely.")

    login_error = st.session_state.get("login_error", "")
    signup_error = st.session_state.get("signup_error", "")
    if login_error:
        st.error(login_error)
    if signup_error:
        st.error(signup_error)

    if st.session_state.get("auth_signup_mode", False):
        st.markdown("### Create account")
        display_name_input = st.text_input("Display name", value=st.session_state.get("display_name", ""), key="auth_signup_name_input")
        email_input = st.text_input("Email address", value=st.session_state.get("email", ""), key="auth_signup_email_input")
        password_input = st.text_input("Password", type="password", key="auth_signup_password_input")

        if st.button("Create account", use_container_width=True, key="auth_create_account_button"):
            email_value = (email_input or "").strip()
            display_name_value = (display_name_input or "").strip()
            if not validate_email(email_value):
                st.session_state.signup_error = "Please enter a valid email address."
            elif not display_name_value:
                st.session_state.signup_error = "Please provide a display name."
            elif not is_strong_password(password_input):
                st.session_state.signup_error = "Password must be at least 8 characters and include letters, numbers, and symbols."
            elif not create_user_account(email_value, password_input, display_name_value):
                st.session_state.signup_error = "That email is already registered or the account could not be created."
            else:
                st.session_state.signup_error = ""
                st.session_state.email = email_value
                st.session_state.display_name = display_name_value
                st.session_state.authenticated = True
                st.session_state.page = "avatar"
                st.rerun()

        if st.button("Already have an account? Sign in", use_container_width=True, key="switch_to_login_button"):
            st.session_state.auth_signup_mode = False
            st.session_state.signup_error = ""
            st.rerun()
    else:
        email_input = st.text_input("Email address", value=st.session_state.get("email", ""), key="auth_login_email_input")
        password_input = st.text_input("Password", type="password", key="auth_login_password_input")

        if st.button("Sign In", use_container_width=True, key="auth_signin_button"):
            email_value = (email_input or "").strip().lower()
            if not validate_email(email_value):
                st.session_state.login_error = "Please enter a valid email address."
            else:
                user = authenticate_user(email_value, password_input)
                if not user:
                    st.session_state.login_error = "Incorrect email or password."
                else:
                    st.session_state.login_error = ""
                    st.session_state.email = user["email"]
                    st.session_state.display_name = user["display_name"]
                    st.session_state.authenticated = True
                    st.session_state.page = "avatar"
                    st.rerun()

        if st.button("Create account", use_container_width=True, key="auth_create_account_link"):
            st.session_state.auth_signup_mode = True
            st.session_state.login_error = ""
            st.rerun()

    nav_col_1, nav_col_2 = st.columns([1, 1])
    with nav_col_1:
        if st.button("Home", use_container_width=True, key="login_home_button"):
            reset_flow()
            st.rerun()
    with nav_col_2:
        if st.button("Back", use_container_width=True, key="login_back_button"):
            st.session_state.page = "welcome"
            st.rerun()


def render_avatar_page():
    st.subheader("Choose your avatar preference")
    st.caption("This selection changes the outfit model images shown in your recommendations.")

    selected_style = st.session_state.get("avatar_style", "Female")
    cols = st.columns(2)
    for index, option in enumerate(AVATAR_STYLE_OPTIONS):
        with cols[index]:
            if render_selection_card(option, "", selected_style == option, f"avatar_{option.lower()}"):
                st.session_state.avatar_style = option
                st.rerun()

    nav_col_1, nav_col_2, nav_col_3 = st.columns([1, 1, 1])
    with nav_col_1:
        if st.button("Home", use_container_width=True, key="avatar_home_button"):
            reset_flow()
            st.rerun()
    with nav_col_2:
        if st.button("Back", use_container_width=True, key="avatar_back_button"):
            st.session_state.page = "login"
            st.rerun()
    with nav_col_3:
        if st.button("Continue", use_container_width=True, key="avatar_continue_button"):
            st.session_state.page = "occasion"
            st.rerun()


def render_occasion_page():
    display_name = st.session_state.display_name or "there"
    st.subheader(f"Welcome, {display_name}")
    st.caption("Choose the vibe for today.")

    selected = st.session_state.occasion
    cols = st.columns(3)
    for index, occasion in enumerate(OCCASION_OPTIONS):
        with cols[index % 3]:
            if render_selection_card(occasion, "", selected == occasion, f"occasion_{occasion}"):
                st.session_state.occasion = occasion
                st.rerun()

    nav_col_1, nav_col_2, nav_col_3 = st.columns([1, 1, 1])
    with nav_col_1:
        if st.button("Home", use_container_width=True, key="occasion_home_button"):
            reset_flow()
            st.rerun()
    with nav_col_2:
        if st.button("Back", use_container_width=True, key="occasion_back_button"):
            st.session_state.page = "avatar"
            st.rerun()
    with nav_col_3:
        if st.button("Continue", use_container_width=True, key="occasion_continue_button"):
            st.session_state.page = "comfort"
            st.rerun()


def render_comfort_page():
    st.subheader("How do you want to feel today?")
    selected = st.session_state.comfort_option
    for label, metadata in COMFORT_OPTIONS.items():
        del metadata
        if render_selection_card(label, "", selected == label, f"comfort_{label}"):
            st.session_state.comfort_option = label
            st.session_state.comfort_level = get_comfort_level(label)
            st.rerun()

    nav_col_1, nav_col_2, nav_col_3 = st.columns([1, 1, 1])
    with nav_col_1:
        if st.button("Home", use_container_width=True, key="comfort_home_button"):
            reset_flow()
            st.rerun()
    with nav_col_2:
        if st.button("Back", use_container_width=True, key="comfort_back_button"):
            st.session_state.page = "occasion"
            st.rerun()
    with nav_col_3:
        if st.button("Continue", use_container_width=True, key="comfort_continue_button"):
            st.session_state.page = "weather"
            st.rerun()


def render_weather_page():
    st.subheader("Location & weather")
    st.caption(f"Profile: {st.session_state.display_name or 'Guest'} • {st.session_state.avatar_style} avatar • {st.session_state.occasion} • {st.session_state.comfort_option}")

    city = st.text_input("City", value=st.session_state.city, placeholder="e.g. Bengaluru", key="weather_city_input")
    st.session_state.city = city.strip()

    if st.button("Check weather", use_container_width=True, key="check_weather_button"):
        if not st.session_state.city:
            st.warning("Enter a city to fetch the live forecast.")
        else:
            with st.spinner("Fetching your weather and outfit suggestions..."):
                try:
                    st.session_state.last_result = fetch_recommendation(
                        st.session_state.city,
                        st.session_state.style,
                        st.session_state.occasion,
                        st.session_state.comfort_level,
                    )
                    st.session_state.page = "results"
                    st.rerun()
                except requests.exceptions.RequestException as exc:
                    st.error(f"Connection error: {exc}")
                    st.session_state.last_result = None
                except ValueError as exc:
                    st.error(str(exc))
                    st.session_state.last_result = None

    if st.session_state.last_result:
        data = st.session_state.last_result
        if isinstance(data, dict):
            current = data.get("current") or {}
            forecast = data.get("forecast") or {}
            weather_cols = st.columns(4)
            with weather_cols[0]:
                st.markdown(f"<div class='metric-card'><div class='label'>Temperature</div><div class='value'>{current.get('temperature', 'N/A')}°C</div></div>", unsafe_allow_html=True)
            with weather_cols[1]:
                st.markdown(f"<div class='metric-card'><div class='label'>Weather</div><div class='value'>{current.get('weather_description', 'N/A')}</div></div>", unsafe_allow_html=True)
            with weather_cols[2]:
                st.markdown(f"<div class='metric-card'><div class='label'>Humidity</div><div class='value'>{current.get('humidity', 'N/A')}%</div></div>", unsafe_allow_html=True)
            with weather_cols[3]:
                st.markdown(f"<div class='metric-card'><div class='label'>Wind</div><div class='value'>{current.get('wind_speed', 'N/A')} km/h</div></div>", unsafe_allow_html=True)

    nav_col_1, nav_col_2, nav_col_3 = st.columns([1, 1, 1])
    with nav_col_1:
        if st.button("Home", use_container_width=True, key="weather_home_button"):
            reset_flow()
            st.rerun()
    with nav_col_2:
        if st.button("Back", use_container_width=True, key="weather_back_button"):
            st.session_state.page = "comfort"
            st.rerun()
    with nav_col_3:
        if st.button("Continue", use_container_width=True, key="weather_continue_button"):
            st.session_state.page = "results"
            st.rerun()


def render_results_page():
    data = st.session_state.last_result
    if not data:
        st.markdown("<div class='info-note'>No recommendation was returned for this location. Try another city.</div>", unsafe_allow_html=True)
        if st.button("Back to weather", use_container_width=True, key="results_retry_button"):
            st.session_state.page = "weather"
            st.rerun()
        return

    name = st.session_state.display_name or "there"
    st.subheader(f"Today's look for {name}")

    ranked_outfits = data.get("ranked_outfits")
    if not isinstance(ranked_outfits, list):
        ranked_outfits = []
    primary = get_primary_outfit(data, ranked_outfits)

    city_name = data.get("city") or st.session_state.city or "Your city"
    current = data.get("current") or {}
    forecast = data.get("forecast") or {}
    weather_category = data.get("weather_category")

    st.markdown("### Weather used for this recommendation")
    if weather_category in WEATHER_SUITABLE_OUTFITS:
        st.info(f"Predicted weather category: **{weather_category}**")
    else:
        st.warning(
            "The weather classifier category was not returned. "
            "No weather-dependent avatar will be displayed."
        )
    weather_cols = st.columns(4)
    with weather_cols[0]:
        st.markdown(f"<div class='metric-card'><div class='label'>City</div><div class='value'>{city_name}</div></div>", unsafe_allow_html=True)
    with weather_cols[1]:
        st.markdown(f"<div class='metric-card'><div class='label'>Current</div><div class='value'>{current.get('temperature', 'N/A')}°C</div></div>", unsafe_allow_html=True)
    with weather_cols[2]:
        st.markdown(f"<div class='metric-card'><div class='label'>Humidity</div><div class='value'>{current.get('humidity', 'N/A')}%</div></div>", unsafe_allow_html=True)
    with weather_cols[3]:
        st.markdown(f"<div class='metric-card'><div class='label'>Wind</div><div class='value'>{current.get('wind_speed', 'N/A')} km/h</div></div>", unsafe_allow_html=True)

    forecast_cols = st.columns(4)
    with forecast_cols[0]:
        st.markdown(f"<div class='metric-card'><div class='label'>Condition</div><div class='value'>{current.get('weather_description', 'N/A')}</div></div>", unsafe_allow_html=True)
    with forecast_cols[1]:
        st.markdown(f"<div class='metric-card'><div class='label'>High</div><div class='value'>{forecast.get('max_temp', 'N/A')}°C</div></div>", unsafe_allow_html=True)
    with forecast_cols[2]:
        st.markdown(f"<div class='metric-card'><div class='label'>Low</div><div class='value'>{forecast.get('min_temp', 'N/A')}°C</div></div>", unsafe_allow_html=True)
    with forecast_cols[3]:
        st.markdown(f"<div class='metric-card'><div class='label'>Rain</div><div class='value'>{forecast.get('rainfall', 'N/A')} mm</div></div>", unsafe_allow_html=True)

    if primary is None:
        st.markdown("<div class='info-note'>Weather is available, but no outfit recommendation was returned for this location.</div>", unsafe_allow_html=True)
        if st.button("Change preferences", use_container_width=True, key="results_change_preferences_button"):
            st.session_state.page = "weather"
            st.rerun()
        return

    primary_name = primary.get("name")
    avatar_style = st.session_state.avatar_style
    st.markdown("### Weather-matched avatar and outfit")
    result_cols = st.columns([1.3, 2.0], gap="large")
    with result_cols[0]:
        st.markdown("<div class='avatar-stage'>", unsafe_allow_html=True)
        st.caption(
            f"{avatar_style} avatar · {st.session_state.get('occasion')} · "
            f"{st.session_state.get('comfort_option')}"
        )
        if weather_category in WEATHER_SUITABLE_OUTFITS:
            selection = select_weather_avatar(
                avatar_style,
                weather_category,
                st.session_state.get("occasion"),
                st.session_state.get("comfort_option"),
            )
            if selection.image_path is not None:
                st.image(
                    str(selection.image_path),
                    use_container_width=False,
                    width=420,
                )
                if selection.fallback_message:
                    st.caption(selection.fallback_message)
            else:
                st.info(selection.fallback_message)
        st.markdown("</div>", unsafe_allow_html=True)
    with result_cols[1]:
        render_recommendation_card(primary, primary=True)

    if isinstance(ranked_outfits, list) and len(ranked_outfits) > 1:
        alt_cols = st.columns(min(3, len(ranked_outfits) - 1))
        alternatives = []
        seen = set()
        for outfit in ranked_outfits:
            if not isinstance(outfit, dict):
                continue
            item_name = outfit.get("name")
            if item_name and item_name not in seen and item_name != primary_name:
                seen.add(item_name)
                alternatives.append(outfit)
            if len(alternatives) >= 3:
                break
        for index, outfit in enumerate(alternatives):
            with alt_cols[index]:
                render_recommendation_card(outfit, primary=False)

    nav_col_1, nav_col_2, nav_col_3 = st.columns([1, 1, 1])
    with nav_col_1:
        if st.button("Home", use_container_width=True, key="results_home_button"):
            reset_flow()
            st.rerun()
    with nav_col_2:
        if st.button("Change preferences", use_container_width=True, key="results_change_button"):
            st.session_state.page = "weather"
            st.rerun()
    with nav_col_3:
        if st.button("Start over", use_container_width=True, key="results_start_over_button"):
            reset_flow()
            st.rerun()

    filters = data.get("_filters") or {}
    if filters:
        st.caption(
            f"Applied filters: style={filters.get('style', 'N/A')}, "
            f"occasion={filters.get('occasion', 'N/A')}, comfort={filters.get('comfort_level', 'N/A')}"
        )


if st.session_state.page != "welcome":
    render_header()
if st.session_state.page == "welcome":
    render_welcome_page()
elif st.session_state.page == "login":
    render_login_page()
elif st.session_state.page == "avatar":
    render_avatar_page()
elif st.session_state.page == "occasion":
    render_occasion_page()
elif st.session_state.page == "comfort":
    render_comfort_page()
elif st.session_state.page == "weather":
    render_weather_page()
else:
    render_results_page()