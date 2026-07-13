import json
import random
import time

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from openai import OpenAI

from advisors_theme import apply_advisors_theme

st.set_page_config(
    page_title="Advisors Academy Pre-CAS Interview",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="collapsed",
)

apply_advisors_theme()

st.markdown(
    """
    <style>
    .stAppDeployButton, .stDeployButton { display: none; }
    div[data-testid="stToolbar"] { display: none; }
    header[data-testid="stHeader"] { display: none; }
    #MainMenu { visibility: hidden; }

    .block-container {
        padding-top: 1.2rem;
        padding-bottom: 2rem;
        max-width: 1500px;
    }

    h1 {
        font-size: 3rem !important;
        font-weight: 800 !important;
        line-height: 1.1 !important;
    }

    h2 {
        font-size: 2rem !important;
        font-weight: 700 !important;
    }

    h3 {
        font-size: 1.45rem !important;
        font-weight: 700 !important;
    }

    p, li, label, div {
        font-size: 1.05rem;
    }

    .stCaption {
        font-size: 0.98rem !important;
    }

    textarea {
        font-size: 1.08rem !important;
        line-height: 1.6 !important;
    }

    div[data-testid="stTextArea"] textarea {
        min-height: 280px !important;
        padding: 1rem !important;
        border-radius: 14px !important;
    }

    div[data-testid="stButton"] button {
        font-size: 1.05rem !important;
        font-weight: 700 !important;
        padding-top: 0.75rem !important;
        padding-bottom: 0.75rem !important;
        border-radius: 12px !important;
    }

    div[data-testid="stRadio"] label,
    div[data-testid="stSelectbox"] label,
    div[data-testid="stTextInput"] label {
        font-size: 1rem !important;
        font-weight: 600 !important;
    }

    section[data-testid="stSidebar"] * {
        font-size: 1rem !important;
    }

    @media (min-width: 1200px) {
        .block-container {
            padding-left: 2rem;
            padding-right: 2rem;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

QUESTION_BANK = {
    "Study destination": [
        "Why have you chosen to study in the UK rather than your home country or another destination like the US or Canada?",
        "The costs of studying in the UK are higher than in your home country. Why incur these extra costs?",
    ],
    "Institution choice": [
        "Why did you choose this university over others in the UK?",
        "What do you know about the city or area where your university is located?",
    ],
    "Course choice": [
        "Why did you choose this specific course?",
        "How does this course relate to your previous education or work experience?",
    ],
    "Course knowledge": [
        "What are the names or topics of some modules you will study?",
        "How long does your course last and how is it structured?",
    ],
    "Finances": [
        "How do you plan to pay for your tuition fees and living expenses in the UK?",
        "Who is financing your studies and what is the source of those funds?",
    ],
    "Accommodation": [
        "Where will you be living while studying in the UK?",
        "How will you travel from your accommodation to campus?",
    ],
    "Background": [
        "Where have you studied previously and what qualifications did you obtain?",
        "Can you explain any gaps in your study or employment history?",
    ],
    "Future plans": [
        "What do you plan to do after completing your course?",
        "Do you intend to return to your home country after your studies?",
    ],
}

FOLLOW_UPS = {
    "Study destination": "Can you be more specific about why the UK suits your goals compared to other countries?",
    "Institution choice": "What do you know about the specific strengths of your department or faculty?",
    "Course choice": "How exactly does this course connect to your previous experience and qualifications?",
    "Course knowledge": "Can you name at least two specific modules and explain what they cover?",
    "Finances": "Can you explain the exact source of the funds and how long they have been held?",
    "Accommodation": "Have you actually confirmed accommodation, or is this still under consideration?",
    "Background": "What were you doing between finishing your previous study and applying for this course?",
    "Future plans": "What specific role will you return to in your home country, and which organisation are you targeting?",
}

QUESTION_HINTS = {
    "Study destination": "Mention 1–2 concrete reasons: course quality, recognition, Graduate Route, or proximity.",
    "Institution choice": "Mention a specific feature: ranking, facilities, location, or placement links.",
    "Course choice": "Link the course to your previous study, work experience, and career goal.",
    "Course knowledge": "Name at least one module, assessment method, or professional outcome.",
    "Finances": "Explain the funding source, amount, and evidence clearly.",
    "Accommodation": "Say where you will live, cost, and how you will commute.",
    "Background": "Give a short timeline and explain any gaps honestly.",
    "Future plans": "State your post-study plan and how the course helps you return home or progress professionally.",
}

ANSWER_TIPS = {
    "default": "Use: direct answer → one specific detail → one short link to your goal.",
    "Study destination": "Mention one UK-specific advantage and one career reason.",
    "Institution choice": "Mention one university strength, one department feature, or one location reason.",
    "Course choice": "Connect previous study or work directly to this exact course.",
    "Course knowledge": "Mention a real module, assessment style, and practical outcome.",
    "Finances": "State source of funds, amount available, and what costs will be covered.",
    "Accommodation": "Name where you will stay, estimated cost, and how you will commute.",
    "Background": "Give a clear timeline and explain any gaps honestly.",
    "Future plans": "State your post-study role, target sector, and why you plan to return home.",
}

RED_FLAGS = [
    "i don't know",
    "not sure",
    "my agent",
    "i haven't researched",
    "i plan to stay",
    "might not return",
    "i just want",
]

POSITIVE = [
    "because",
    "specifically",
    "module",
    "dissertation",
    "placement",
    "nhs",
    "career",
    "return",
    "back home",
    "sponsor",
    "tuition",
]

DEFAULT_THINK_TIME = 3
DEFAULT_HINT_MODE = True
DEFAULT_MIN_WORDS = 20
QUESTION_TIME_SECONDS = 3 * 60

# ... rest of file continues ...
