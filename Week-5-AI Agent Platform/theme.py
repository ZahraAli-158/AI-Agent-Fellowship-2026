"""
Shared visual theme for the AI Workspace Platform Streamlit frontend.
Single source of truth for colors/typography/CSS so every page looks
consistent and no page duplicates raw CSS strings.
"""
from __future__ import annotations

import streamlit as st

# --- Design tokens (fixed by design brief) ---
BG = "#09090B"
BG_SECONDARY = "#111118"
SIDEBAR_BG = "#101018"
ACCENT = "#8B5CF6"
ACCENT_2 = "#A855F7"
HOVER = "#6D28D9"
BORDER = "rgba(255,255,255,0.08)"
TEXT_PRIMARY = "#FFFFFF"
TEXT_SECONDARY = "#B8B8C7"

STATUS = {
    "green": "#22C55E",
    "red": "#EF4444",
    "yellow": "#EAB308",
    "blue": "#3B82F6",
    "purple": ACCENT,
}


def sync_theme_state() -> None:
    """Root-cause fix for Dark Mode not persisting: st.session_state is
    wiped on every full browser refresh (Streamlit assigns a fresh session),
    so a preference stored only in session_state silently reverts to the
    hardcoded default on refresh. st.query_params lives in the URL itself,
    which the browser keeps across a refresh, so we use it as the durable
    backing store.

    Two-phase sync to avoid a stale URL value clobbering a live toggle click:
      1. On the FIRST run of a session (no _theme_initialized marker yet -
         which is itself wiped on refresh, same as dark_mode), pull the
         value from the URL if present, else use the default.
      2. On every later run within the same session, trust session_state as
         the live value (the toggle widget already updates it correctly via
         its key binding) and just keep the URL mirrored to match, rather
         than re-deriving from the URL each time.

    Call this once per page, before rendering the toggle or any themed CSS.
    """
    if "_theme_initialized" not in st.session_state:
        url_theme = st.query_params.get("theme")
        st.session_state.dark_mode = (url_theme != "light") if url_theme else True
        st.session_state._theme_initialized = True

    desired = "dark" if st.session_state.dark_mode else "light"
    if st.query_params.get("theme") != desired:
        st.query_params["theme"] = desired


def inject_theme() -> None:
    sync_theme_state()
    dark_mode = st.session_state.dark_mode

    if dark_mode:
        bg, bg_secondary, sidebar_bg = BG, BG_SECONDARY, SIDEBAR_BG
        text_primary, text_secondary = TEXT_PRIMARY, TEXT_SECONDARY
        glow_opacity = "0.12"
    else:
        # Light mode variant: same accent/purple identity, inverted neutrals.
        bg, bg_secondary, sidebar_bg = "#F7F7FA", "#FFFFFF", "#FFFFFF"
        text_primary, text_secondary = "#18181B", "#52525B"
        glow_opacity = "0.06"

    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');

    html, body, [class*="css"] {{
        font-family: 'Inter', -apple-system, sans-serif;
    }}

    .stApp {{
        background: radial-gradient(ellipse 80% 50% at 50% -10%, rgba(139,92,246,{glow_opacity}), transparent),
                    {bg};
        color: {text_primary};
    }}

    section[data-testid="stSidebar"] {{
        background: {sidebar_bg};
        border-right: 1px solid {BORDER};
    }}
    section[data-testid="stSidebar"] * {{
        color: {text_primary};
    }}

    /* Headings */
    h1, h2, h3 {{
        font-weight: 800 !important;
        letter-spacing: -0.02em;
    }}
    h1 {{ background: linear-gradient(135deg, {text_primary}, {text_secondary});
          -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}

    p, span, label, div {{ color: {text_primary}; }}
    .awp-muted {{ color: {text_secondary} !important; }}

    /* Buttons */
    .stButton > button {{
        background: linear-gradient(135deg, {ACCENT}, {ACCENT_2});
        color: white;
        border: none;
        border-radius: 10px;
        padding: 0.55em 1.3em;
        font-weight: 600;
        transition: all 0.2s ease;
        box-shadow: 0 0 0 rgba(139,92,246,0);
    }}
    .stButton > button:hover {{
        background: linear-gradient(135deg, {HOVER}, {ACCENT});
        box-shadow: 0 0 20px rgba(139,92,246,0.45);
        transform: translateY(-1px);
    }}

    /* Inputs */
    .stTextInput input, .stTextArea textarea, .stSelectbox [data-baseweb="select"] > div,
    .stNumberInput input {{
        background: {bg_secondary} !important;
        border: 1px solid {BORDER} !important;
        border-radius: 10px !important;
        color: {text_primary} !important;
    }}
    .stTextInput input:focus, .stTextArea textarea:focus {{
        border-color: {ACCENT} !important;
        box-shadow: 0 0 0 1px {ACCENT} !important;
    }}

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {{ gap: 4px; }}
    .stTabs [data-baseweb="tab"] {{
        background: transparent; color: {text_secondary};
        border-radius: 8px 8px 0 0;
    }}
    .stTabs [aria-selected="true"] {{
        color: {text_primary} !important;
        border-bottom: 2px solid {ACCENT} !important;
    }}

    /* Metrics */
    div[data-testid="stMetric"] {{
        background: {bg_secondary};
        border: 1px solid {BORDER};
        border-radius: 14px;
        padding: 16px 18px;
    }}
    div[data-testid="stMetricLabel"] {{ color: {text_secondary} !important; }}

    /* Expander / containers with border */
    div[data-testid="stExpander"], div[data-testid="stVerticalBlockBorderWrapper"] {{
        background: {bg_secondary};
        border: 1px solid {BORDER} !important;
        border-radius: 14px !important;
    }}

    /* Chat bubbles */
    div[data-testid="stChatMessage"] {{
        background: {bg_secondary};
        border: 1px solid {BORDER};
        border-radius: 14px;
        padding: 4px 8px;
    }}

    /* Scrollbar */
    ::-webkit-scrollbar {{ width: 8px; height: 8px; }}
    ::-webkit-scrollbar-track {{ background: {bg}; }}
    ::-webkit-scrollbar-thumb {{ background: {ACCENT}; border-radius: 8px; }}

    /* Hide default streamlit chrome for a cleaner enterprise feel */
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}

    /* Divider */
    hr {{ border-color: {BORDER} !important; }}
    </style>
    """, unsafe_allow_html=True)
