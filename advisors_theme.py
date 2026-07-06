import streamlit as st

ADVISORS_CSS = """
<style>
/* Load a consistent web font */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');

.stApp {
    background-color: #F5F7FB;
    font-family: "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}

/* Top brand bar */
.advisors-brand-bar {
    background: linear-gradient(90deg, #0F6CBD 0%, #103E73 100%);
    color: #FFFFFF;
    padding: 0.75rem 1.25rem;
    border-radius: 0 0 8px 8px;
    box-shadow: 0 2px 6px rgba(0,0,0,0.12);
}

/* Brand title and subtitle */
.advisors-title {
    font-size: 1.1rem;
    font-weight: 600;
    letter-spacing: 0.03em;
    text-transform: uppercase;
}

.advisors-subtitle {
    font-size: 0.9rem;
    opacity: 0.86;
}

/* Card-style containers */
.advisors-card {
    background-color: #FFFFFF;
    border-radius: 10px;
    padding: 1rem 1.25rem;
    box-shadow: 0 1px 4px rgba(15, 107, 189, 0.08);
    border: 1px solid #E3E8EF;
}

/* Heading colors */
h1, h2, h3 {
    color: #103E73;
}

/* Hide Streamlit default footer & menu for cleaner branding */
footer {visibility: hidden;}
#MainMenu {visibility: hidden;}
</style>
"""


def apply_advisors_theme():
    """Apply Advisors Academy CSS and brand bar."""
    st.markdown(ADVISORS_CSS, unsafe_allow_html=True)
    st.markdown(
        """
        <div class="advisors-brand-bar">
            <div class="advisors-title">Advisors Academy</div>
            <div class="advisors-subtitle">
                Pre-CAS Interview Practice & Compliance Readiness
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )