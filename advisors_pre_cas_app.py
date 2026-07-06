import random
import time
import streamlit as st
import pandas as pd

from advisors_theme import apply_advisors_theme

# Page config
st.set_page_config(
    page_title="Advisors Academy Pre-CAS Interview",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="collapsed",
)

apply_advisors_theme()

# ------------ Question bank & hints ------------

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
    "Institution choice": "Mention one course feature, one module, or one location factor.",
    "Course choice": "Connect previous study/work to this exact course.",
    "Course knowledge": "Say one module, one assessment method, and one practical outcome.",
    "Finances": "State source of funds, evidence, and total cost clearly.",
    "Accommodation": "Name accommodation, cost, and commute.",
    "Background": "Give a simple timeline and explain gaps honestly.",
    "Future plans": "State return plan and how the course helps your career.",
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

# ------------ Prime Crown UK course clusters ------------

COURSE_PROFILES = {
    # Undergraduate
    "UG – Business & Management": {
        "examples": "Business Administration; Accounting & Finance; Marketing; International Business",
        "extra_tip": "Mention business modules (finance, marketing, strategy) and how they support your career in management or entrepreneurship.",
        "keywords": ["marketing", "finance", "accounting", "strategy", "international business"],
    },
    "UG – Computer Science & IT": {
        "examples": "Computer Science; Software Engineering; Networking; Cybersecurity; Data Science (foundation)",
        "extra_tip": "Refer to programming, networking, or cybersecurity content and link these to your target IT role.",
        "keywords": ["programming", "software engineering", "networking", "cybersecurity", "data science"],
    },
    "UG – Engineering": {
        "examples": "Civil Engineering; Mechanical; Electrical/Electronic; Petroleum; Chemical",
        "extra_tip": "Mention core engineering subjects and how UK lab or project work prepares you for industry or licensing back home.",
        "keywords": ["civil engineering", "mechanical", "electrical", "petroleum", "chemical engineering", "lab", "project"],
    },
    "UG – Nursing & Healthcare": {
        "examples": "Adult Nursing; Mental Health Nursing; Health Sciences",
        "extra_tip": "Highlight clinical placements, NMC-related content, and how UK training fits your nursing registration and practice.",
        "keywords": ["nursing", "nmc", "clinical placement", "ward", "hospital", "health sciences"],
    },
    "UG – Law": {
        "examples": "LLB (undergraduate Law)",
        "extra_tip": "Explain why studying Law in the UK helps you understand common law and supports your legal career in your home jurisdiction.",
        "keywords": ["llb", "common law", "legal practice", "case law"],
    },
    "UG – Architecture & Built Environment": {
        "examples": "Architecture; Construction; Quantity Surveying",
        "extra_tip": "Mention design studios, construction modules, and how this supports work in built environment or infrastructure.",
        "keywords": ["architecture", "construction", "quantity surveying", "studio", "design"],
    },
    "UG – Media & Communication": {
        "examples": "Media Studies; Communication; Digital Marketing",
        "extra_tip": "Refer to content on media, communication strategy, or digital marketing and connect to your creative or marketing goals.",
        "keywords": ["media", "communication", "digital marketing", "content creation"],
    },
    "UG – Psychology": {
        "examples": "BSc Psychology",
        "extra_tip": "Mention core psychology modules and how they relate to your interest in mental health or human behaviour.",
        "keywords": ["psychology", "mental health", "behaviour", "counselling"],
    },
    "UG – Education & TESOL": {
        "examples": "Education Studies; Teaching routes; TESOL",
        "extra_tip": "Connect the course to teaching or TESOL plans in schools, colleges, or language centres.",
        "keywords": ["education", "tesol", "teaching", "classroom", "curriculum"],
    },

    # Top-up
    "Top-up – Business": {
        "examples": "BA/BSc (Hons) Business top-up from HND/OND Business",
        "extra_tip": "Clarify how the top-up completes your HND/OND and helps you progress to management and graduate roles.",
        "keywords": ["top-up", "hnd", "ond", "business administration"],
    },
    "Top-up – Accounting & Finance": {
        "examples": "BA/BSc (Hons) Accounting & Finance top-up",
        "extra_tip": "Mention progression from HND/OND to honours degree and how this supports professional exams or finance roles.",
        "keywords": ["accounting", "finance", "top-up", "professional exams"],
    },
    "Top-up – Computing / IT / Cybersecurity": {
        "examples": "BSc (Hons) Computing / IT / Cybersecurity top-up",
        "extra_tip": "Highlight advanced computing or cybersecurity topics and how they build on your HND/OND foundation.",
        "keywords": ["computing", "it", "cybersecurity", "top-up"],
    },
    "Top-up – Engineering Technology": {
        "examples": "BEng/BSc Engineering Technology top-up",
        "extra_tip": "Explain how the top-up enhances your technical skills and improves engineering career prospects.",
        "keywords": ["engineering technology", "top-up", "hnd", "technical skills"],
    },
    "Top-up – Health & Social Care / Public Health": {
        "examples": "Health & Social Care top-up; Public Health top-up",
        "extra_tip": "Link the course to health or social care work and community impact in your home country.",
        "keywords": ["health and social care", "public health", "community"],
    },
    "Top-up – Hospitality & Tourism": {
        "examples": "Hospitality & Tourism Management top-up",
        "extra_tip": "Describe how UK hospitality/tourism content prepares you for international service or tourism roles.",
        "keywords": ["hospitality", "tourism", "service industry"],
    },

    # Postgraduate
    "PG – Public Health & Health Management": {
        "examples": "MPH; MSc Public Health; Health Policy & Management",
        "extra_tip": "Mention public health, health systems, or policy modules and how they support leadership roles in health.",
        "keywords": ["public health", "health policy", "health management", "epidemiology"],
    },
    "PG – Data Science, AI & Advanced Computing": {
        "examples": "MSc Data Science; Artificial Intelligence; Big Data; Business Analytics",
        "extra_tip": "Connect modules in data science, AI or analytics to specific data-driven problems you want to solve.",
        "keywords": ["data science", "ai", "analytics", "big data", "machine learning"],
    },
    "PG – Business, Management & Project Management": {
        "examples": "MBA; MSc Management; International Business; Project Management",
        "extra_tip": "Show how the course builds your management, leadership, or project skills for specific roles.",
        "keywords": ["mba", "management", "leadership", "project management"],
    },
    "PG – Cybersecurity & IT Masters": {
        "examples": "MSc Cybersecurity; Information Security; Advanced Computer Science",
        "extra_tip": "Refer to security, cryptography, or advanced computing content and link to cyber roles.",
        "keywords": ["cybersecurity", "information security", "advanced computing"],
    },
    "PG – Engineering Masters": {
        "examples": "Civil; Electrical/Electronic; Renewable Energy; Oil & Gas / Engineering Management",
        "extra_tip": "Explain how advanced engineering modules prepare you for specialist or management engineering roles.",
        "keywords": ["renewable energy", "engineering management", "civil", "electrical"],
    },
    "PG – Nursing / Advanced Nursing & Health": {
        "examples": "MSc Nursing; Advanced Clinical Practice",
        "extra_tip": "Highlight advanced clinical or leadership content and its impact on your nursing practice.",
        "keywords": ["advanced practice", "clinical leadership", "msc nursing"],
    },
    "PG – Education & TESOL": {
        "examples": "MA Education; TESOL; Early Childhood Studies",
        "extra_tip": "Connect the programme to curriculum development, classroom practice, or TESOL work.",
        "keywords": ["ma education", "tesol", "early childhood", "curriculum"],
    },
    "PG – Finance, Accounting & Banking": {
        "examples": "MSc Finance; Accounting & Finance; Banking & Financial Technology",
        "extra_tip": "Mention finance, banking or fintech modules and how they support your target roles in financial services.",
        "keywords": ["finance", "banking", "fintech", "accounting"],
    },
    "PG – International Relations & Development": {
        "examples": "International Relations; Development Studies; Global Governance",
        "extra_tip": "Relate global governance or development modules to issues in your region and your policy or NGO goals.",
        "keywords": ["international relations", "development studies", "global governance", "ngo"],
    },
}

# ------------ Helpers ------------

def pick_question():
    idx = st.session_state.idx
    if idx >= len(st.session_state.categories):
        st.session_state.completed = True
        return
    cat = st.session_state.categories[idx]
    st.session_state.current_category = cat
    st.session_state.current_question = random.choice(QUESTION_BANK[cat])
    st.session_state.show_followup = False


def verdict(avg: float) -> str:
    if avg >= 4.5:
        return "✅ Strong Pre-CAS performance"
    if avg >= 3.5:
        return "🟡 Borderline — strengthen weak areas"
    if avg >= 2.5:
        return "🟠 At risk — more practice needed"
    return "🔴 High risk — urgent coaching required"


def fallback_score(answer: str) -> dict:
    lower = answer.lower()

    # 1. Hard red flags
    for f in RED_FLAGS:
        if f in lower:
            return {
                "score": 1,
                "feedback": f"Red flag detected: '{f}'.",
                "tip": "Avoid immigration-focused, unclear or agent-led language.",
                "red_flag": True,
                "generic_pos": 0,
                "cluster_hits": 0,
            }

    # 2. Generic positives
    generic_pos = sum(1 for p in POSITIVE if p in lower)

    # 3. Course-cluster-specific keywords
    course_track = st.session_state.profile.get("course_track") if "profile" in st.session_state else None
    cluster_hits = 0
    if course_track and course_track in COURSE_PROFILES:
        keywords = COURSE_PROFILES[course_track].get("keywords", [])
        cluster_hits = sum(1 for kw in keywords if kw.lower() in lower)

    wc = len(answer.split())

    # Base score from length + generic positives
    s = 2
    if wc < 15:
        s = 2
    elif generic_pos >= 4 and wc >= 60:
        s = 5
    elif generic_pos >= 2 and wc >= 40:
        s = 4
    elif generic_pos >= 1 and wc >= 25:
        s = 3

    # Boost if student uses course-cluster language
    if cluster_hits >= 2 and s <= 4:
        s += 1
    elif cluster_hits == 1 and s <= 3:
        s += 1

    s = max(1, min(s, 5))

    msgs = {
        5: "Excellent — specific and aligned with your chosen course.",
        4: "Good — add one more concrete detail about your course or university.",
        3: "Average — bring in more course or module details.",
        2: "Weak — too vague or generic.",
    }

    tip = "Mention relevant modules, course outcomes, and how they support your career."
    if course_track and course_track in COURSE_PROFILES:
        tip = COURSE_PROFILES[course_track]["extra_tip"]

    return {
        "score": s,
        "feedback": msgs.get(s, "Response evaluated."),
        "tip": tip,
        "red_flag": False,
        "generic_pos": generic_pos,
        "cluster_hits": cluster_hits,
    }


def countdown_box(seconds: int, label: str = "Next question"):
    box = st.empty()
    for s in range(seconds, 0, -1):
        box.warning(f"{label} in {s} second{'s' if s != 1 else ''}...")
        time.sleep(1)
    box.empty()


# ------------ Sidebar: applicant profile ------------

with st.sidebar:
    st.header("👤 Applicant Profile")

    course_track = st.selectbox(
        "Course track (Prime Crown UK list)",
        list(COURSE_PROFILES.keys()),
        index=0,
        help="Choose the closest cluster for your UK course.",
    )

    s_name = st.text_input("Full Name")
    s_university = st.text_input("University")
    s_course = st.text_input("Course")
    s_country = st.text_input("Home Country", value="Nigeria")
    s_experience = st.text_input("Experience", placeholder="e.g. 2 years work or study")

    c1, c2 = st.columns(2)
    with c1:
        start = st.button("Start Pre-CAS Interview", use_container_width=True, type="primary")
    with c2:
        if st.button("Reset Session", use_container_width=True):
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.rerun()

    if start:
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        cats = list(QUESTION_BANK.keys())
        random.shuffle(cats)
        st.session_state.update(
            {
                "started": True,
                "completed": False,
                "categories": cats,
                "idx": 0,
                "scores": [],
                "log": [],
                "show_followup": False,
                "profile": {
                    "name": s_name or "Applicant",
                    "university": s_university or "your university",
                    "course": s_course or "your course",
                    "country": s_country or "Nigeria",
                    "experience": s_experience or "",
                    "course_track": course_track,
                },
                "think_time": DEFAULT_THINK_TIME,
                "hint_mode": DEFAULT_HINT_MODE,
                "min_words": DEFAULT_MIN_WORDS,
            }
        )
        pick_question()
        st.rerun()

# ------------ Main UI ------------

st.title("Advisors Academy Pre-CAS Interview")
st.caption("Practice realistic UK university Pre-CAS questions with instant feedback.")

with st.expander("How your answers are scored"):
    st.markdown(
        """
**Score meanings**

- 5/5 – Excellent: clear, specific, and aligned with your UK course and career plan.
- 4/5 – Good: strong answer; add one more concrete detail (module, exam, placement, outcome).
- 3/5 – Average: basically correct but generic; needs more course/university detail.
- 2/5 – Weak: vague or incomplete; needs clearer reasons and better link to your course.
- 1/5 – High risk: uses unclear or risky language (“I don’t know”, “my agent decided everything”, “I just want to stay in the UK”).

**What the system checks**

1. Structure and clarity — direct answer, reason, example, and link to course/career.
2. Connection to your actual UK course — real modules, exams, placements, or specialist topics.
"""
    )

if not st.session_state.get("started"):
    st.info("Fill in the applicant profile on the left, then click 'Start Pre-CAS Interview'.")
else:
    if st.session_state.get("completed"):
        scores = st.session_state.scores
        avg = sum(scores) / len(scores) if scores else 0
        v = verdict(avg)

        st.subheader("📊 Pre-CAS Performance Summary")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Applicant", st.session_state.profile["name"])
        m2.metric("Questions", len(scores))
        m3.metric("Average Score", f"{avg:.1f} / 5")
        m4.metric("Verdict", v)

        df = pd.DataFrame(st.session_state.log)
        st.divider()
        st.dataframe(
            df[
                [
                    "Question #",
                    "Category",
                    "Score",
                    "Feedback",
                    "Tip",
                    "Generic Positives",
                    "Cluster Hits",
                ]
            ],
            use_container_width=True,
            hide_index=True,
        )

        weak = df[df["Score"] <= 2]
        if not weak.empty:
            st.divider()
            st.subheader("⚠️ Areas to Improve Before CAS")
            for _, row in weak.iterrows():
                with st.expander(f"Q{int(row['Question #'])} — {row['Category']} ({int(row['Score'])}/5)"):
                    st.write(f"**Question:** {row['Question']}")
                    st.write(f"**Answer:** {row['Answer']}")
                    st.error(f"**Feedback:** {row['Feedback']}")
                    st.info(f"**Tip:** {row['Tip']}")

        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "⬇ Download Interview Report (CSV)",
            csv,
            "advisors_pre_cas_report.csv",
            "text/csv",
        )

    else:
        categories = st.session_state.categories
        idx = st.session_state.idx
        total_q = len(categories)

        st.progress(idx / total_q, text=f"Question {idx + 1} of {total_q}")

        left, right = st.columns([2, 1])

        with left:
            st.markdown(f"**Topic:** `{st.session_state.current_category}`")
            st.markdown("### Interview Question")
            st.write(st.session_state.current_question)

            if st.session_state.get("hint_mode", True):
                st.info(
                    QUESTION_HINTS.get(
                        st.session_state.current_category,
                        "Give a clear, specific answer.",
                    )
                )
                st.caption(
                    ANSWER_TIPS.get(
                        st.session_state.current_category,
                        ANSWER_TIPS["default"],
                    )
                )

                # Prime Crown course cluster tip
                course_track = st.session_state.profile.get("course_track")
                if course_track and course_track in COURSE_PROFILES:
                    cluster = COURSE_PROFILES[course_track]
                    st.caption(
                        f"Course cluster hint ({course_track}): "
                        f"{cluster['extra_tip']} Example programmes include: {cluster['examples']}."
                    )

            if not st.session_state.show_followup:
                answer = st.text_area(
                    "Your answer",
                    height=170,
                    key=f"ans_{idx}",
                    placeholder="Answer as you would in a real Pre-CAS interview.",
                )
                if st.button("Submit Answer →", type="primary", use_container_width=True):
                    if answer.strip():
                        wc = len(answer.strip().split())
                        if wc < st.session_state.get("min_words", 20):
                            st.warning(
                                f"Your answer is quite short ({wc} words). "
                                f"Aim for at least {st.session_state.get('min_words', 20)} words."
                            )
                        result = fallback_score(answer.strip())

                        # Immediate scoring breakdown
                        st.success(f"Score: {result['score']}/5 — {result['feedback']}")
                        st.caption(
                            f"Signals detected: {result.get('generic_pos', 0)} generic positives, "
                            f"{result.get('cluster_hits', 0)} course-cluster keywords."
                        )

                        st.session_state.scores.append(result["score"])
                        st.session_state.log.append(
                            {
                                "Question #": idx + 1,
                                "Category": st.session_state.current_category,
                                "Question": st.session_state.current_question,
                                "Answer": answer.strip(),
                                "Score": result["score"],
                                "Feedback": result["feedback"],
                                "Tip": result["tip"],
                                "Red Flag": result.get("red_flag", False),
                                "Generic Positives": result.get("generic_pos", 0),
                                "Cluster Hits": result.get("cluster_hits", 0),
                            }
                        )

                        if result["score"] <= 2:
                            st.session_state.show_followup = True
                            st.session_state.last_result = result
                        else:
                            wait_s = int(st.session_state.get("think_time", 0))
                            if wait_s > 0:
                                countdown_box(wait_s, label="Next question")
                            st.session_state.idx += 1
                            pick_question()
                        st.rerun()
                    else:
                        st.warning("Please enter your answer before submitting.")
            else:
                r = st.session_state.last_result
                stars = "★" * r["score"] + "☆" * (5 - r["score"])
                st.error(f"Score: {stars} ({r['score']}/5) — {r['feedback']}")
                st.warning(f"🔍 Follow-up: {FOLLOW_UPS[st.session_state.current_category]}")
                follow = st.text_area(
                    "Follow-up answer",
                    height=130,
                    key=f"follow_{idx}",
                    placeholder="Provide more specific details to recover credibility…",
                )
                if st.button("Submit Follow-up →", type="primary", use_container_width=True):
                    if follow.strip() and len(follow.split()) >= 20:
                        new_score = min(r["score"] + 1, 4)
                        st.session_state.scores[-1] = new_score
                        st.session_state.log[-1].update(
                            {
                                "Score": new_score,
                                "Feedback": "Follow-up accepted — credibility partially recovered.",
                            }
                        )
                    st.session_state.show_followup = False
                    st.session_state.idx += 1
                    pick_question()
                    st.rerun()

        with right:
            st.subheader("Live Scores")
            for i, sc in enumerate(st.session_state.scores):
                bar = "█" * sc + "░" * (5 - sc)
                cat = categories[i] if i < len(categories) else ""
                row = st.session_state.log[i]
                flag = " 🚩" if row.get("Red Flag") else ""
                gp = row.get("Generic Positives", 0)
                ch = row.get("Cluster Hits", 0)
                st.markdown(f"`Q{i+1}` {bar} **{sc}/5**{flag}  \n_{cat}_")
                st.caption(f"Signals: {gp} generic positives, {ch} cluster hits.")

            st.divider()
            p = st.session_state.profile
            st.markdown(f"👤 **{p['name']}**")
            st.markdown(f"🎓 {p['course']}")
            st.markdown(f"🏫 {p['university']}")
            st.markdown(f"🌍 {p['country']}")
            if p["experience"]:
                st.markdown(f"💼 {p['experience']}")
            course_track = p.get("course_track")
            if course_track:
                st.markdown(f"📚 Track: {course_track}")