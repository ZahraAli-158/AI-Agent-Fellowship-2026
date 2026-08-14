"""
Reusable glass-panel UI components. Every page imports from here instead of
writing its own raw HTML/CSS, keeping the visual language consistent and
avoiding duplicate styling code across pages.
"""
from __future__ import annotations

import html as _html

import streamlit as st

from theme import ACCENT, ACCENT_2, BG_SECONDARY, BORDER, STATUS, TEXT_SECONDARY


def glass_card_open(extra_style: str = "") -> None:
    st.markdown(f"""
    <div style="
        background: linear-gradient(135deg, rgba(139,92,246,0.06), rgba(17,17,24,0.6));
        backdrop-filter: blur(12px);
        border: 1px solid {BORDER};
        border-radius: 16px;
        padding: 20px 22px;
        margin-bottom: 14px;
        {extra_style}
    ">
    """, unsafe_allow_html=True)


def glass_card_close() -> None:
    st.markdown("</div>", unsafe_allow_html=True)


def badge(text: str, color: str = "purple") -> str:
    hex_color = STATUS.get(color, ACCENT)
    return (
        f'<span style="background:{hex_color}22; color:{hex_color}; '
        f'border:1px solid {hex_color}55; padding:2px 10px; border-radius:999px; '
        f'font-size:12px; font-weight:600; box-shadow:0 0 12px {hex_color}33;">{_html.escape(text)}</span>'
    )


def status_dot(color: str = "green") -> str:
    hex_color = STATUS.get(color, STATUS["green"])
    return (
        f'<span style="display:inline-block; width:8px; height:8px; border-radius:50%; '
        f'background:{hex_color}; box-shadow:0 0 8px {hex_color}; margin-right:6px;"></span>'
    )


def section_title(title: str, subtitle: str = "") -> None:
    st.markdown(f"<h2 style='margin-bottom:2px'>{_html.escape(title)}</h2>", unsafe_allow_html=True)
    if subtitle:
        st.markdown(f"<p class='awp-muted' style='margin-top:0'>{_html.escape(subtitle)}</p>", unsafe_allow_html=True)


def empty_state(icon: str, title: str, subtitle: str) -> None:
    st.markdown(f"""
    <div style="
        text-align:center; padding: 56px 20px;
        background:{BG_SECONDARY}; border:1px dashed {BORDER}; border-radius:16px;
    ">
        <div style="font-size:40px; margin-bottom:8px;">{icon}</div>
        <div style="font-weight:700; font-size:17px;">{_html.escape(title)}</div>
        <div class="awp-muted" style="margin-top:4px;">{_html.escape(subtitle)}</div>
    </div>
    """, unsafe_allow_html=True)


def skeleton_lines(n: int = 3) -> None:
    bars = "".join(
        f'<div style="height:14px; width:{85 - i*10}%; border-radius:6px; '
        f'background:linear-gradient(90deg,{BG_SECONDARY},#1c1c26,{BG_SECONDARY}); '
        f'background-size:200% 100%; animation:awp-shimmer 1.4s infinite; margin-bottom:8px;"></div>'
        for i in range(n)
    )
    st.markdown(f"""
    <style>
    @keyframes awp-shimmer {{
        0% {{ background-position: 200% 0; }}
        100% {{ background-position: -200% 0; }}
    }}
    </style>
    <div>{bars}</div>
    """, unsafe_allow_html=True)


def metric_glow(label: str, value: str, color: str = "purple") -> None:
    hex_color = STATUS.get(color, ACCENT)
    st.markdown(f"""
    <div style="
        background:{BG_SECONDARY}; border:1px solid {BORDER}; border-radius:14px;
        padding:16px 18px; position:relative; overflow:hidden;
    ">
        <div style="position:absolute; top:-20px; right:-20px; width:80px; height:80px;
                    background:{hex_color}; opacity:0.15; filter:blur(30px); border-radius:50%;"></div>
        <div class="awp-muted" style="font-size:13px;">{_html.escape(label)}</div>
        <div style="font-size:26px; font-weight:800; margin-top:2px;">{_html.escape(value)}</div>
    </div>
    """, unsafe_allow_html=True)


def gradient_divider() -> None:
    st.markdown(f"""
    <div style="height:1px; margin:18px 0; background:linear-gradient(90deg, transparent, {ACCENT}55, transparent);"></div>
    """, unsafe_allow_html=True)


def page_header(icon: str, title: str, subtitle: str = "") -> None:
    st.markdown(f"""
    <div style="display:flex; align-items:center; gap:14px; margin-bottom:6px;">
        <div style="
            width:44px; height:44px; border-radius:12px; display:flex; align-items:center; justify-content:center;
            background:linear-gradient(135deg, {ACCENT}, {ACCENT_2}); font-size:22px;
            box-shadow:0 0 24px {ACCENT}55;
        ">{icon}</div>
        <div>
            <div style="font-size:24px; font-weight:800;">{_html.escape(title)}</div>
            {f'<div class="awp-muted" style="font-size:14px;">{_html.escape(subtitle)}</div>' if subtitle else ''}
        </div>
    </div>
    """, unsafe_allow_html=True)
