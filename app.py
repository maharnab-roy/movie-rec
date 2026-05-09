import os
import json
import hashlib
import secrets
from datetime import datetime

import requests
import streamlit as st


# =============================
# CONFIG
# =============================
API_BASE = st.secrets.get("API_BASE", os.getenv("API_BASE", "http://127.0.0.1:8000"))
TMDB_IMG = "https://image.tmdb.org/t/p/w500"
USERS_FILE = "users.json"

st.set_page_config(
    page_title="MovieMind",
    page_icon="🎬",
    layout="wide",
)


# =============================
# CSS - NEW OTT STYLE UI
# =============================
st.markdown(
    """
<style>
/* Hide Streamlit top and bottom default UI */
[data-testid="stToolbar"] {
    display: none !important;
}

[data-testid="stDeployButton"] {
    display: none !important;
}

#MainMenu {
    visibility: hidden !important;
}

footer {
    visibility: hidden !important;
    display: none !important;
}

header {
    visibility: hidden !important;
    display: none !important;
}

[data-testid="stDecoration"] {
    display: none !important;
}

[data-testid="stStatusWidget"] {
    display: none !important;
}
:root {
    --bg: #070914;
    --panel: rgba(255,255,255,0.055);
    --panel-2: rgba(255,255,255,0.085);
    --line: rgba(255,255,255,0.12);
    --text: #f8fafc;
    --muted: #94a3b8;
    --hot: #ff2d55;
    --hot-2: #7c3aed;
    --cyan: #38bdf8;
}

html, body, [data-testid="stAppViewContainer"] {
    background:
        radial-gradient(circle at top left, rgba(124,58,237,0.25), transparent 32%),
        radial-gradient(circle at top right, rgba(255,45,85,0.18), transparent 28%),
        linear-gradient(180deg, #070914 0%, #0b1020 55%, #070914 100%);
    color: var(--text);
}

.block-container {
    padding-top: 1rem;
    padding-bottom: 2rem;
    max-width: 1500px;
}

[data-testid="stHeader"] {
    display: none !important;
}

h1, h2, h3 {
    letter-spacing: -0.035em;
}

.small-muted, .muted {
    color: var(--muted);
    font-size: 0.92rem;
}

.hero {
    border: 1px solid var(--line);
    border-radius: 30px;
    padding: 34px;
    background:
        linear-gradient(135deg, rgba(255,45,85,0.18), rgba(124,58,237,0.14)),
        linear-gradient(180deg, rgba(255,255,255,0.07), rgba(255,255,255,0.025));
    box-shadow: 0 24px 70px rgba(0,0,0,0.35);
    margin-bottom: 22px;
}

.hero-kicker {
    display: inline-block;
    padding: 6px 12px;
    border-radius: 999px;
    background: rgba(255,255,255,0.10);
    border: 1px solid rgba(255,255,255,0.12);
    color: #e5e7eb;
    font-size: 0.82rem;
    font-weight: 700;
    margin-bottom: 12px;
}

.hero-title {
    font-size: clamp(2.1rem, 5vw, 4.2rem);
    line-height: 0.98;
    font-weight: 900;
    color: white;
    margin: 0 0 12px 0;
}

.hero-text {
    color: #cbd5e1;
    font-size: 1.05rem;
    max-width: 760px;
}

.glass-card, .card {
    border: 1px solid var(--line);
    border-radius: 22px;
    padding: 16px;
    background: linear-gradient(180deg, rgba(255,255,255,0.075), rgba(255,255,255,0.028));
    box-shadow: 0 12px 35px rgba(0,0,0,0.24);
}

.movie-shell {
    border: 1px solid rgba(255,255,255,0.10);
    background: rgba(255,255,255,0.035);
    border-radius: 18px;
    padding: 10px;
    transition: transform 0.18s ease, border-color 0.18s ease, background 0.18s ease;
    min-height: 100%;
}

.movie-shell:hover {
    transform: translateY(-3px);
    border-color: rgba(255,45,85,0.45);
    background: rgba(255,255,255,0.065);
}

.movie-title {
    font-size: 0.92rem;
    font-weight: 750;
    line-height: 1.18rem;
    min-height: 2.4rem;
    max-height: 2.4rem;
    overflow: hidden;
    margin-top: 0.45rem;
    color: #f8fafc;
}

.poster-empty {
    height: 245px;
    border-radius: 14px;
    display: grid;
    place-items: center;
    background: rgba(255,255,255,0.06);
    color: #cbd5e1;
}

.profile-card {
    border: 1px solid rgba(255,255,255,0.14);
    border-radius: 28px;
    padding: 24px 18px;
    text-align: center;
    background: linear-gradient(180deg, rgba(255,255,255,0.085), rgba(255,255,255,0.028));
    min-height: 300px;
    box-shadow: 0 18px 45px rgba(0,0,0,0.25);
}

.profile-card:hover {
    border-color: rgba(56,189,248,0.45);
}

.profile-icon {
    font-size: 4.4rem;
    margin-bottom: 0.55rem;
    filter: drop-shadow(0 10px 18px rgba(0,0,0,0.35));
}

.profile-chip {
    display: inline-block;
    margin: 4px 3px 0 3px;
    padding: 4px 9px;
    border-radius: 999px;
    background: rgba(255,255,255,0.08);
    color: #cbd5e1;
    font-size: 0.74rem;
    border: 1px solid rgba(255,255,255,0.09);
}

.auth-box {
    max-width: 510px;
    margin: 7vh auto 0 auto;
    padding: 30px;
    border-radius: 28px;
    border: 1px solid rgba(255,255,255,0.14);
    background: linear-gradient(180deg, rgba(255,255,255,0.09), rgba(255,255,255,0.035));
    box-shadow: 0 26px 70px rgba(0,0,0,0.35);
}

.auth-logo {
    font-size: 2.2rem;
    font-weight: 900;
    color: #fff;
    margin-bottom: 4px;
}

.stButton > button {
    border-radius: 14px;
    border: 1px solid rgba(255,255,255,0.12);
    background: linear-gradient(135deg, rgba(255,45,85,0.92), rgba(124,58,237,0.92));
    color: white;
    font-weight: 800;
    min-height: 2.65rem;
}

.stButton > button:hover {
    border-color: rgba(255,255,255,0.35);
    transform: translateY(-1px);
}

[data-testid="stSidebar"] {
    background:
        radial-gradient(circle at top, rgba(255,45,85,0.18), transparent 35%),
        linear-gradient(180deg, #090b16 0%, #10172a 100%);
    border-right: 1px solid rgba(255,255,255,0.10);
}

[data-testid="stSidebar"] .block-container {
    padding-top: 1rem;
    padding-bottom: 1.5rem;
}

[data-testid="stSidebar"] .stButton > button {
    width: 100%;
    background: rgba(255,255,255,0.06);
    border: 1px solid rgba(255,255,255,0.12);
    color: #f8fafc;
}

[data-testid="stSidebar"] .stButton > button:hover {
    background: rgba(255,255,255,0.10);
}

.sidebar-brand {
    font-size: 1.55rem;
    font-weight: 950;
    color: #ffffff;
    margin-bottom: 0.25rem;
}

.sidebar-subtitle {
    color: #94a3b8;
    font-size: 0.88rem;
    margin-bottom: 1rem;
}

.sidebar-profile-card {
    border: 1px solid rgba(255,255,255,0.13);
    border-radius: 22px;
    padding: 16px;
    background: linear-gradient(180deg, rgba(255,255,255,0.09), rgba(255,255,255,0.035));
    margin-bottom: 0.9rem;
}

.sidebar-profile-top {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 12px;
}

.sidebar-avatar {
    width: 56px;
    height: 56px;
    border-radius: 18px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.9rem;
    background: linear-gradient(135deg, rgba(255,45,85,0.25), rgba(56,189,248,0.15));
    border: 1px solid rgba(255,255,255,0.13);
}

.sidebar-profile-name {
    font-size: 1.12rem;
    font-weight: 900;
    color: #ffffff;
    line-height: 1.15;
}

.sidebar-profile-type, .sidebar-mini, .sidebar-note {
    color: #cbd5e1;
    font-size: 0.84rem;
}

.sidebar-section-title {
    font-size: 0.95rem;
    font-weight: 900;
    color: #f8fafc;
    margin-top: 0.9rem;
    margin-bottom: 0.55rem;
}

.sidebar-divider {
    height: 1px;
    background: rgba(255,255,255,0.10);
    margin: 1rem 0;
}

.sidebar-chip-wrap { 
    margin-top: 10px; 
    line-height: 1.9; 
}

.sidebar-chip {
    display: inline-block;
    padding: 4px 10px;
    border-radius: 999px;
    font-size: 0.74rem;
    color: #e5e7eb;
    background: rgba(255,255,255,0.085);
    border: 1px solid rgba(255,255,255,0.08);
    margin-right: 6px;
    margin-bottom: 6px;
}

.detail-title {
    font-size: clamp(2rem, 4vw, 3.6rem);
    line-height: 1;
    font-weight: 950;
    color: white;
}

.badge {
    display: inline-block;
    padding: 6px 11px;
    border-radius: 999px;
    border: 1px solid rgba(255,255,255,0.12);
    background: rgba(255,255,255,0.08);
    color: #e5e7eb;
    font-size: 0.82rem;
    margin-right: 6px;
    margin-bottom: 6px;
}

.details-label-box,
.details-info-box {
    width: 100%;
    min-height: 42px;
    border-radius: 999px;
    padding: 8px 16px;
    margin-bottom: 12px;

    display: flex;
    align-items: center;
    justify-content: center;
    gap: 12px;

    background:
        linear-gradient(90deg, rgba(255,45,85,0.22), rgba(124,58,237,0.26)),
        linear-gradient(180deg, rgba(255,255,255,0.12), rgba(255,255,255,0.04));

    border: 1px solid rgba(255,255,255,0.18);
    box-shadow:
        inset 0 1px 0 rgba(255,255,255,0.12),
        0 10px 24px rgba(0,0,0,0.25);
}

.details-box-line {
    height: 2px;
    flex: 1;
    border-radius: 999px;
    background: linear-gradient(
        90deg,
        transparent,
        rgba(255,255,255,0.65),
        transparent
    );
}

.details-box-text {
    white-space: nowrap;
    font-weight: 900;
    font-size: 15px;
    letter-spacing: 0.25px;
    color: #f8fafc;
}
</style>
""",
    unsafe_allow_html=True,
)


# =============================
# USER STORAGE
# =============================
def load_users():
    if not os.path.exists(USERS_FILE):
        return {}

    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_users(users):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=4)


def hash_password(password, salt=None):
    if salt is None:
        salt = secrets.token_hex(16)

    password_hash = hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
    return salt, password_hash


def verify_password(password, salt, stored_hash):
    _, password_hash = hash_password(password, salt)
    return password_hash == stored_hash


def default_profiles():
    return [
        {
            "id": "kids",
            "name": "Kids",
            "icon": "🧒",
            "profile_type": "Kids",
            "genre_ids": [16, 10751, 12, 35],
            "genre_names": ["Animation", "Family", "Adventure", "Comedy"],
            "allow_adult": False,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        },
        {
            "id": "guest",
            "name": "Guest",
            "icon": "👤",
            "profile_type": "Guest",
            "genre_ids": [28, 12, 35, 18],
            "genre_names": ["Action", "Adventure", "Comedy", "Drama"],
            "allow_adult": False,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        },
    ]


def ensure_profiles(username):
    users = load_users()

    if username not in users:
        return

    if "profiles" not in users[username] or not users[username]["profiles"]:
        users[username]["profiles"] = default_profiles()
        save_users(users)


def get_user_profiles(username):
    ensure_profiles(username)
    users = load_users()
    return users.get(username, {}).get("profiles", [])


def get_current_profile():
    username = st.session_state.username
    profile_id = st.session_state.current_profile_id

    if not username or not profile_id:
        return None

    profiles = get_user_profiles(username)

    for p in profiles:
        if p.get("id") == profile_id:
            return p

    return None


def add_profile(username, name, profile_type, genre_ids, genre_names, allow_adult):
    users = load_users()

    if username not in users:
        return False, "User not found."

    ensure_profiles(username)
    users = load_users()

    profile_id = secrets.token_hex(6)

    if profile_type == "Kids":
        icon = "🧒"
        allow_adult = False
    elif profile_type == "Guest":
        icon = "👤"
    else:
        icon = "😎"

    new_profile = {
        "id": profile_id,
        "name": name.strip(),
        "icon": icon,
        "profile_type": profile_type,
        "genre_ids": genre_ids,
        "genre_names": genre_names,
        "allow_adult": bool(allow_adult),
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    users[username]["profiles"].append(new_profile)
    save_users(users)

    return True, "Profile added successfully."


def delete_profile(username, profile_id):
    users = load_users()

    if username not in users:
        return False, "User not found."

    ensure_profiles(username)
    users = load_users()

    if profile_id in ["kids", "guest"]:
        return False, "Default profiles cannot be deleted."

    profiles = users[username].get("profiles", [])

    new_profiles = []
    deleted = False

    for profile in profiles:
        if profile.get("id") == profile_id:
            deleted = True
        else:
            new_profiles.append(profile)

    if not deleted:
        return False, "Profile not found."

    users[username]["profiles"] = new_profiles
    save_users(users)

    return True, "Profile deleted successfully."


def signup_user(username, password):
    users = load_users()
    username = username.strip().lower()

    if username in users:
        return False, "Username already exists."

    salt, password_hash = hash_password(password)

    users[username] = {
        "username": username,
        "salt": salt,
        "password_hash": password_hash,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "last_login": None,
        "profiles": default_profiles(),
    }

    save_users(users)
    return True, "Signup successful. Please login."


def login_user(username, password):
    users = load_users()
    username = username.strip().lower()

    if username not in users:
        return False, "User not found."

    user = users[username]

    if not verify_password(password, user["salt"], user["password_hash"]):
        return False, "Wrong password."

    users[username]["last_login"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if "profiles" not in users[username] or not users[username]["profiles"]:
        users[username]["profiles"] = default_profiles()

    save_users(users)

    st.session_state.logged_in = True
    st.session_state.username = username
    st.session_state.last_login = users[username]["last_login"]
    st.session_state.view = "profile_select"
    st.session_state.current_profile_id = None

    return True, "Login successful."


def logout_user():
    st.session_state.logged_in = False
    st.session_state.username = None
    st.session_state.last_login = None
    st.session_state.auth_page = "login"
    st.session_state.view = "home"
    st.session_state.selected_tmdb_id = None
    st.session_state.current_profile_id = None
    st.rerun()


# =============================
# SESSION STATE
# =============================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "username" not in st.session_state:
    st.session_state.username = None

if "last_login" not in st.session_state:
    st.session_state.last_login = None

if "auth_page" not in st.session_state:
    st.session_state.auth_page = "login"

if "view" not in st.session_state:
    st.session_state.view = "home"

if "selected_tmdb_id" not in st.session_state:
    st.session_state.selected_tmdb_id = None

if "current_profile_id" not in st.session_state:
    st.session_state.current_profile_id = None
if "movie_search_text" not in st.session_state:
    st.session_state.movie_search_text = ""

if "back_view" not in st.session_state:
    st.session_state.back_view = "home"

if "back_search_text" not in st.session_state:
    st.session_state.back_search_text = ""


# =============================
# API HELPERS
# =============================
@st.cache_data(ttl=60)
def api_get_json(path: str, params=None):
    try:
        r = requests.get(f"{API_BASE}{path}", params=params, timeout=30)

        if r.status_code >= 400:
            return None, f"HTTP {r.status_code}: {r.text[:500]}"

        return r.json(), None

    except Exception as e:
        return None, f"Request failed: {e}"


@st.cache_data(ttl=3600)
def get_genres():
    data, err = api_get_json("/genres")

    if err or not data:
        return [
            {"id": 28, "name": "Action"},
            {"id": 12, "name": "Adventure"},
            {"id": 16, "name": "Animation"},
            {"id": 35, "name": "Comedy"},
            {"id": 80, "name": "Crime"},
            {"id": 18, "name": "Drama"},
            {"id": 10751, "name": "Family"},
            {"id": 14, "name": "Fantasy"},
            {"id": 27, "name": "Horror"},
            {"id": 10749, "name": "Romance"},
            {"id": 878, "name": "Science Fiction"},
            {"id": 53, "name": "Thriller"},
        ]

    return data


def safe_img(image_url):
    if image_url:
        return image_url
    return None


def goto_home():
    st.session_state.view = "home"
    st.session_state.selected_tmdb_id = None
    st.query_params["view"] = "home"

    if "id" in st.query_params:
        del st.query_params["id"]

    st.rerun()


def goto_details(tmdb_id: int):
    # Save exact previous page state before opening details
    if st.session_state.get("view") != "details":
        st.session_state.back_view = st.session_state.get("view", "home")
        st.session_state.back_search_text = st.session_state.get("movie_search_text", "")

    st.session_state.view = "details"
    st.session_state.selected_tmdb_id = int(tmdb_id)

    st.query_params["view"] = "details"
    st.query_params["id"] = str(int(tmdb_id))

    st.rerun()


def go_back_previous():
    previous = st.session_state.get("back_view", "home")

    st.session_state.view = previous
    st.session_state.selected_tmdb_id = None

    # Restore previous search text also
    st.session_state.movie_search_text = st.session_state.get("back_search_text", "")

    st.query_params["view"] = previous

    if "id" in st.query_params:
        del st.query_params["id"]

    st.rerun()


def goto_profile_select():
    st.session_state.view = "profile_select"
    st.session_state.current_profile_id = None
    st.query_params["view"] = "profile_select"

    if "id" in st.query_params:
        del st.query_params["id"]

    st.rerun()


def choose_profile(profile_id):
    st.session_state.current_profile_id = profile_id
    st.session_state.view = "home"
    st.query_params["view"] = "home"

    if "id" in st.query_params:
        del st.query_params["id"]

    st.rerun()


def goto_add_profile():
    st.session_state.view = "add_profile"
    st.query_params["view"] = "add_profile"
    st.rerun()


def poster_grid(cards, cols=6, key_prefix="grid"):
    if not cards:
        st.info("No movies to show.")
        return

    try:
        cols = int(cols)
    except Exception:
        cols = 6

    cols = max(2, min(cols, 8))
    rows = (len(cards) + cols - 1) // cols
    idx = 0

    for r in range(rows):
        colset = st.columns(cols)

        for c in range(cols):
            if idx >= len(cards):
                break

            m = cards[idx]
            idx += 1

            tmdb_id = m.get("tmdb_id") or m.get("id")
            title = m.get("title", "Untitled")
            poster = m.get("poster_url")

            with colset[c]:
                st.markdown("<div class='movie-shell'>", unsafe_allow_html=True)

                if poster:
                    st.image(poster, use_column_width=True)
                else:
                    st.markdown("<div class='poster-empty'>No Poster</div>", unsafe_allow_html=True)

                st.markdown(
                    f"<div class='movie-title'>{title}</div>",
                    unsafe_allow_html=True,
                )

                if st.button("Open", key=f"{key_prefix}_{r}_{c}_{idx}_{tmdb_id}"):
                    if tmdb_id:
                        goto_details(int(tmdb_id))

                st.markdown("</div>", unsafe_allow_html=True)


def parse_tmdb_search_to_cards(data, keyword: str, limit: int = 24):
    keyword_l = keyword.strip().lower()

    if isinstance(data, dict) and "results" in data:
        raw = data.get("results") or []
        raw_items = []

        for m in raw:
            title = (m.get("title") or "").strip()
            tmdb_id = m.get("id")
            poster_path = m.get("poster_path")

            if not title or not tmdb_id:
                continue

            raw_items.append(
                {
                    "tmdb_id": int(tmdb_id),
                    "title": title,
                    "poster_url": f"{TMDB_IMG}{poster_path}" if poster_path else None,
                    "release_date": m.get("release_date", ""),
                }
            )
    else:
        return [], []

    matched = [x for x in raw_items if keyword_l in x["title"].lower()]
    final_list = matched if matched else raw_items

    suggestions = []

    for x in final_list[:10]:
        year = (x.get("release_date") or "")[:4]
        label = f"{x['title']} ({year})" if year else x["title"]
        suggestions.append((label, x["tmdb_id"]))

    cards = [
        {
            "tmdb_id": x["tmdb_id"],
            "title": x["title"],
            "poster_url": x["poster_url"],
        }
        for x in final_list[:limit]
    ]

    return suggestions, cards


def build_sidebar_profile_html(profile, username, last_login):
    profile_type = profile.get("profile_type", "Normal")
    icon = profile.get("icon", "👤")
    name = profile.get("name", "Profile")
    interests = profile.get("genre_names", [])

    if profile_type == "Kids":
        mode_text = "Kids Safe"
    elif profile.get("allow_adult"):
        mode_text = "18+ Enabled"
    else:
        mode_text = "General Mode"

    chips = "".join([f"<span class='sidebar-chip'>{g}</span>" for g in interests[:7]])
    last_login_text = last_login if last_login else "-"

    return f"""
    <div class="sidebar-profile-card">
        <div class="sidebar-profile-top">
            <div class="sidebar-avatar">{icon}</div>
            <div>
                <div class="sidebar-profile-name">{name}</div>
                <div class="sidebar-profile-type">{profile_type}</div>
            </div>
        </div>
        <div class="sidebar-mini"><b>User:</b> {username}</div>
        <div class="sidebar-mini"><b>Last login:</b> {last_login_text}</div>
        <div class="sidebar-mini"><b>Mode:</b> {mode_text}</div>
        <div class="sidebar-chip-wrap">{chips}</div>
    </div>
    """


# =============================
# LOGIN / SIGNUP UI
# =============================
def show_login_page():
    st.markdown(
        "<div class='small-muted' style='text-align:center; margin-bottom:24px;'>Login to continue your movie world.</div>",
        unsafe_allow_html=True,
    )

    username = st.text_input("Username", key="login_username")
    password = st.text_input("Password", type="password", key="login_password")

    if st.button("Login", use_container_width=True):
        if not username or not password:
            st.error("Please enter username and password.")
        else:
            ok, msg = login_user(username, password)

            if ok:
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)

    st.markdown("---")
    st.write("Don't have an account?")

    if st.button("Create new account", use_container_width=True):
        st.session_state.auth_page = "signup"
        st.rerun()


def show_signup_page():
    st.markdown(
        "<div class='small-muted' style='text-align:center; margin-bottom:24px;'>Create account and start watching.</div>",
        unsafe_allow_html=True,
    )

    username = st.text_input("Choose username", key="signup_username")
    password = st.text_input("Create password", type="password", key="signup_password")
    confirm_password = st.text_input(
        "Confirm password",
        type="password",
        key="signup_confirm_password",
    )

    if st.button("Signup", use_container_width=True):
        if not username or not password or not confirm_password:
            st.error("Please fill all fields.")
        elif len(username) < 3:
            st.error("Username must be at least 3 characters.")
        elif len(password) < 6:
            st.error("Password must be at least 6 characters.")
        elif password != confirm_password:
            st.error("Passwords do not match.")
        else:
            ok, msg = signup_user(username, password)

            if ok:
                st.success(msg)
                st.session_state.auth_page = "login"
            else:
                st.error(msg)

    st.markdown("---")
    st.write("Already have an account?")

    if st.button("Back to login", use_container_width=True):
        st.session_state.auth_page = "login"
        st.rerun()


if not st.session_state.logged_in:
    left, mid, right = st.columns([1, 1.2, 1])

    with mid:
        st.markdown(
            """
            <div class='auth-box' style='text-align:center; margin-bottom: 20px;'>
                <div class='auth-logo'>🎬 MovieMind</div>
                <div class='small-muted'>Your personal movie recommendation system</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if st.session_state.auth_page == "login":
            show_login_page()
        else:
            show_signup_page()

    st.stop()


# =============================
# ROUTING
# =============================
qp_view = st.query_params.get("view")
qp_id = st.query_params.get("id")

if qp_view in ("home", "details", "profile_select", "add_profile"):
    st.session_state.view = qp_view

if qp_id:
    try:
        st.session_state.selected_tmdb_id = int(qp_id)
        st.session_state.view = "details"
    except Exception:
        pass


# =============================
# PROFILE SELECT PAGE
# =============================
if st.session_state.view == "profile_select":
    ensure_profiles(st.session_state.username)

    st.markdown(
        """
        <div class='hero'>
            <div class='hero-kicker'>MovieMind Profiles</div>
            <div class='hero-title'>Who's watching?</div>
            <div class='hero-text'>Choose your profile and get a personalized movie home screen.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    profiles = get_user_profiles(st.session_state.username)

    total_cards = profiles + [
        {
            "id": "__add__",
            "name": "Add Profile",
            "icon": "➕",
            "profile_type": "Create Profile",
            "genre_names": [],
        }
    ]

    cols = st.columns(3, gap="large")

    for i, profile in enumerate(total_cards):
        profile_id = profile.get("id")
        genres = profile.get("genre_names", [])

        if genres:
            chips = "".join(
                [f"<span class='profile-chip'>{g}</span>" for g in genres[:5]]
            )
        else:
            chips = "<span class='profile-chip'>New</span>"

        with cols[i % 3]:
            profile_html = f"""
        <div class="profile-card">
            <div class="profile-icon">{profile.get('icon', '👤')}</div>
            <div style="font-size:1.65rem; font-weight:900; color:white; margin-bottom:8px;">
                {profile.get('name')}
            </div>
            <div style="color:#94a3b8; font-size:0.95rem; margin-bottom:14px;">
                {profile.get('profile_type', 'Normal')}
            </div>
            <div style="margin-bottom:20px;">
                {chips}
            </div>
        </div>
        """
            st.markdown(profile_html, unsafe_allow_html=True)

            if profile_id == "__add__":
                if st.button("Add", key="add_profile_btn", use_container_width=True):
                    goto_add_profile()

            else:
                if st.button(
                    "Open Profile",
                    key=f"profile_open_{profile_id}",
                    use_container_width=True,
                ):
                    choose_profile(profile_id)

                if profile_id not in ["kids", "guest"]:
                    if st.button(
                        "🗑 Delete",
                        key=f"profile_delete_{profile_id}",
                        use_container_width=True,
                    ):
                        ok, msg = delete_profile(
                            st.session_state.username,
                            profile_id,
                        )

                        if ok:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)
                else:
                    st.markdown(
                        "<div class='small-muted' style='text-align:center; margin-top:10px;'>Default profile</div>",
                        unsafe_allow_html=True,
                    )

    st.markdown("---")

    if st.button("Logout"):
        logout_user()

    st.stop()


# =============================
# ADD PROFILE PAGE
# =============================
if st.session_state.view == "add_profile":
    st.markdown(
        """
        <div class='hero'>
            <div class='hero-kicker'>Create profile</div>
            <div class='hero-title'>Customize your watch space.</div>
            <div class='hero-text'>Pick a profile type and movie interests. Your home page will change based on this.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.button("← Back to Profiles"):
        goto_profile_select()

    form_col, info_col = st.columns([1.6, 1], gap="large")

    with form_col:
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)

        all_genres = get_genres()
        genre_name_to_id = {g["name"]: g["id"] for g in all_genres}
        genre_names = list(genre_name_to_id.keys())

        name = st.text_input("Profile name", placeholder="Example: Dad, Kids, Guest")
        profile_type = st.selectbox("Profile type", ["Normal", "Kids", "Guest"])

        if profile_type == "Kids":
            default_selection = [
                g for g in ["Animation", "Family", "Adventure", "Comedy"]
                if g in genre_names
            ]
        else:
            default_selection = [
                g for g in ["Action", "Adventure", "Comedy", "Drama"]
                if g in genre_names
            ]

        selected_genres = st.multiselect(
            "Choose movie interests",
            genre_names,
            default=default_selection,
            max_selections=7,
        )

        allow_adult = False

        if profile_type != "Kids":
            allow_adult = st.checkbox(
                "Allow 18+ / adult movies for this profile",
                value=False,
            )
        else:
            st.info("Kids profile will only show child-safe content.")

        if st.button("Create Profile", use_container_width=True):
            if not name.strip():
                st.error("Profile name is required.")
            elif not selected_genres:
                st.error("Choose at least one movie interest.")
            else:
                selected_ids = [genre_name_to_id[g] for g in selected_genres]

                ok, msg = add_profile(
                    username=st.session_state.username,
                    name=name,
                    profile_type=profile_type,
                    genre_ids=selected_ids,
                    genre_names=selected_genres,
                    allow_adult=allow_adult,
                )

                if ok:
                    st.success(msg)
                    st.session_state.view = "profile_select"
                    st.rerun()
                else:
                    st.error(msg)

        st.markdown("</div>", unsafe_allow_html=True)

    with info_col:
        st.markdown(
            """
            <div class='glass-card'>
                <h3>Profile rules</h3>
                <p class='small-muted'>Kids profile blocks adult content and uses child-safe discovery.</p>
                <p class='small-muted'>Normal and Guest profiles can use selected genres for “For You”.</p>
                <p class='small-muted'>You can delete custom profiles anytime from the profile page.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.stop()


# =============================
# CHECK PROFILE
# =============================
current_profile = get_current_profile()

if not current_profile:
    st.session_state.view = "profile_select"
    st.rerun()


# =============================
# SIDEBAR
# =============================
with st.sidebar:
    st.markdown("<div class='sidebar-brand'>🎬 MovieMind</div>", unsafe_allow_html=True)
    st.markdown("<div class='sidebar-subtitle'>Your OTT-style movie hub</div>", unsafe_allow_html=True)

    st.markdown(
        build_sidebar_profile_html(
            current_profile,
            st.session_state.username,
            st.session_state.last_login,
        ),
        unsafe_allow_html=True,
    )

    st.markdown("<div class='sidebar-section-title'>Navigation</div>", unsafe_allow_html=True)

    if st.button("🏠 Home", key="sidebar_home_btn"):
        goto_home()

    if st.button("👥 Switch / Manage Profiles", key="sidebar_profiles_btn"):
        goto_profile_select()

    if st.button("➕ Add Profile", key="sidebar_add_profile_btn"):
        goto_add_profile()

    st.markdown("<div class='sidebar-divider'></div>", unsafe_allow_html=True)
    st.markdown("<div class='sidebar-section-title'>Browse</div>", unsafe_allow_html=True)

    category_map = {
        "🎯 For You": "for_you",
        "🔥 Trending": "trending",
        "⭐ Popular": "popular",
        "🏆 Top Rated": "top_rated",
        "🎥 Now Playing": "now_playing",
        "🚀 Upcoming": "upcoming",
    }

    category_label = st.selectbox("Category", list(category_map.keys()), index=0)
    home_category = category_map[category_label]

    grid_cols = st.slider("Poster columns", 4, 8, 6)

    st.markdown(
        "<div class='sidebar-note'>“For You” uses this profile’s selected genres.</div>",
        unsafe_allow_html=True,
    )

    st.markdown("<div class='sidebar-divider'></div>", unsafe_allow_html=True)

    if st.button("🚪 Logout", key="sidebar_logout_btn"):
        logout_user()


# =============================
# HEADER
# =============================
st.markdown(
    f"""
    <div class='hero'>
        <div class='hero-kicker'>Now watching as {current_profile.get('icon', '👤')} {current_profile.get('name', 'Profile')}</div>
        <div class='hero-title'>Find your next movie.</div>
        <div class='hero-text'>Search any movie, open details, and get similar movies plus genre-based recommendations.</div>
    </div>
    """,
    unsafe_allow_html=True,
)


# =============================
# HOME PAGE
# =============================
if st.session_state.view == "home":
    search_col, hint_col = st.columns([2.2, 1], gap="large")

    with search_col:
        typed = st.text_input(
            "Search by movie title",
            placeholder="Try: avenger, batman, harry potter...",
            key="movie_search_text",
        )

    with hint_col:
        st.markdown(
            "<div class='glass-card'><b>Tip</b><br><span class='small-muted'>Choose a movie result, then scroll for recommendations.</span></div>",
            unsafe_allow_html=True,
        )

    st.divider()

    profile_type = current_profile.get("profile_type", "Normal")
    is_kids = profile_type == "Kids"
    include_adult = bool(current_profile.get("allow_adult", False)) and not is_kids

    if typed.strip():
        if len(typed.strip()) < 2:
            st.caption("Type at least 2 characters for suggestions.")
        else:
            data, err = api_get_json(
                "/tmdb/search",
                params={
                    "query": typed.strip(),
                    "include_adult": include_adult,
                },
            )

            if err or data is None:
                st.error(f"Search failed: {err}")
            else:
                suggestions, cards = parse_tmdb_search_to_cards(
                    data,
                    typed.strip(),
                    limit=24,
                )

                if suggestions:
                    labels = ["-- Select a movie --"] + [s[0] for s in suggestions]
                    selected = st.selectbox("Suggestions", labels, index=0)

                    if selected != "-- Select a movie --":
                        label_to_id = {s[0]: s[1] for s in suggestions}
                        goto_details(label_to_id[selected])
                else:
                    st.info("No suggestions found. Try another keyword.")

                st.markdown("### Results")
                poster_grid(cards, cols=grid_cols, key_prefix="search_results")

        st.stop()

    if home_category == "for_you":
        genre_ids = current_profile.get("genre_ids", [])

        if genre_ids:
            genre_ids_text = ",".join([str(x) for x in genre_ids])
            st.markdown(f"### 🎯 For {current_profile.get('name')}")

            home_cards, err = api_get_json(
                "/home/by-genres",
                params={
                    "genre_ids": genre_ids_text,
                    "limit": 24,
                    "include_adult": include_adult,
                    "kids": is_kids,
                },
            )
        else:
            st.markdown("### 🏠 Home — Trending")
            home_cards, err = api_get_json(
                "/home",
                params={"category": "trending", "limit": 24},
            )
    else:
        st.markdown(f"### 🏠 Home — {home_category.replace('_', ' ').title()}")

        home_cards, err = api_get_json(
            "/home",
            params={"category": home_category, "limit": 24},
        )

    if err or not home_cards:
        st.error(f"Home feed failed: {err or 'Unknown error'}")
        st.stop()

    poster_grid(home_cards, cols=grid_cols, key_prefix="home_feed")


# =============================
# DETAILS PAGE
# =============================
elif st.session_state.view == "details":
    tmdb_id = st.session_state.selected_tmdb_id

    if not tmdb_id:
        st.warning("No movie selected.")

        if st.button("← Back"):
            go_back_previous()

        st.stop()

    a, b = st.columns([3, 1])

    with a:
        st.markdown("### 📄 Movie Details")

    with b:
        if st.button("← Back", key="details_back_btn", use_container_width=True):
            go_back_previous()

    data, err = api_get_json(f"/movie/id/{tmdb_id}")

    if err or not data:
        st.error(f"Could not load details: {err or 'Unknown error'}")
        st.stop()

    profile_type = current_profile.get("profile_type", "Normal")
    is_kids = profile_type == "Kids"
    include_adult = bool(current_profile.get("allow_adult", False)) and not is_kids

    left, right = st.columns([1, 2.55], gap="large")

    with left:
        st.markdown(
            """
            <div class='details-label-box'>
                <span class='details-box-line'></span>
                <span class='details-box-text'>🎬 Movie Poster</span>
                <span class='details-box-line'></span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if data.get("poster_url"):
            st.image(data["poster_url"], use_column_width=True)
        else:
            st.markdown(
                "<div class='poster-empty'>No Poster Available</div>",
                unsafe_allow_html=True,
            )

    with right:
        movie_title = data.get("title", "Movie Details")

        st.markdown(
            f"""
            <div class='details-info-box'>
                <span class='details-box-line'></span>
                <span class='details-box-text'>✨ Movie Information — {movie_title}</span>
                <span class='details-box-line'></span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown(
            f"<div class='detail-title'>{movie_title}</div>",
            unsafe_allow_html=True,
        )

        release = data.get("release_date") or "-"
        genres_list = [g["name"] for g in data.get("genres", [])]
        adult_status = "18+ / Adult" if data.get("adult") else "General / Non-adult"

        badges = f"""
        <span class='badge'>📅 {release}</span>
        <span class='badge'>🔒 {adult_status}</span>
        """

        badges += "".join(
            [f"<span class='badge'>{g}</span>" for g in genres_list[:5]]
        )

        st.markdown(badges, unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("### Overview")
        st.write(data.get("overview") or "No overview available.")

    if data.get("backdrop_url"):
        st.markdown("#### Backdrop")
        st.image(data["backdrop_url"], use_column_width=True)

    st.divider()
    st.markdown("### ✅ Recommendations")

    rec_data, rec_err = api_get_json(
        "/movie/recommendations",
        params={
            "tmdb_id": tmdb_id,
            "limit": 18,
            "include_adult": include_adult,
            "kids": is_kids,
        },
    )

    if rec_err or not rec_data:
        st.info("No recommendations available right now. Try again after a few seconds.")
    else:
        similar_movies = rec_data.get("similar_movies", [])
        more_like_this = rec_data.get("more_like_this", [])

        st.markdown("#### 🔎 Similar Movies")

        if similar_movies:
            poster_grid(
                similar_movies,
                cols=grid_cols,
                key_prefix="details_similar_movies",
            )
        else:
            st.info("No similar movies found.")

        st.markdown("#### 🎭 More Like This")

        if more_like_this:
            poster_grid(
                more_like_this,
                cols=grid_cols,
                key_prefix="details_more_like_this",
            )
        else:
            st.info("No more like this movies found.")