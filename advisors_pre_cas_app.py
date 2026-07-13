import json
import time
import random

import pandas as pd
import streamlit as st
from openai import OpenAI
from streamlit_autorefresh import st_autorefresh

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
QUESTION_TIME_SECONDS = 3 * 60

COURSE_PROFILES = {
    "UG – Business & Management": {
        "examples": "Business Administration; Accounting & Finance; Marketing; International Business",
        "extra_tip": "Mention business modules (finance, marketing, strategy) and how they support your career in management or entrepreneurship.",
        "keywords": ["marketing", "finance", "accounting", "strategy", "international business"],
    },
    # ... keep all your existing profiles ...
}

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])


def build_one_question_per_category():
    sequence = []
    for category, questions in QUESTION_BANK.items():
        sequence.append({"category": category, "question": random.choice(questions)})
    return sequence


def pick_question():
    idx = st.session_state.idx
    if idx >= len(st.session_state.question_sequence):
        st.session_state.completed = True
        return
    item = st.session_state.question_sequence[idx]
    st.session_state.current_category = item["category"]
    st.session_state.current_question = item["question"]
    st.session_state.show_followup = False
    st.session_state.question_start = time.time()
    st.session_state.question_closed = False
    st.session_state.auto_advanced = False


def verdict(avg: float) -> str:
    if avg >= 4.5:
        return "✅ Strong Pre-CAS performance"
    if avg >= 3.5:
        return "🟡 Borderline — strengthen weak areas"
    if avg >= 2.5:
        return "🟠 At risk — more practice needed"
    return "🔴 High risk — urgent coaching required"


def counsellor_risk(avg: float) -> str:
    if avg >= 4.5:
        return "Low risk"
    if avg >= 3.5:
        return "Moderate risk"
    if avg >= 2.5:
        return "Elevated risk"
    return "High risk"


def time_left():
    start = st.session_state.get("question_start", time.time())
    elapsed = time.time() - start
    remaining = max(0, int(QUESTION_TIME_SECONDS - elapsed))
    minutes = remaining // 60
    seconds = remaining % 60
    return remaining, f"{minutes:02d}:{seconds:02d}"


def countdown_box(seconds: int, label: str = "Next question"):
    box = st.empty()
    for s in range(seconds, 0, -1):
        box.warning(f"{label} in {s} second{'s' if s != 1 else ''}...")
        time.sleep(1)
    box.empty()


def fallback_score(answer: str) -> dict:
    lower = answer.lower()
    for f in RED_FLAGS:
        if f in lower:
            return {
                "score": 1,
                "feedback": f"Red flag detected: '{f}'.",
                "student_tip": "Avoid unclear or agent-led language and answer directly.",
                "risk_flags": [f],
                "missing_points": ["Specific personal rationale", "credible supporting detail"],
                "counsellor_note": "Student used a high-risk phrase and needs coached reframing.",
                "red_flag": True,
                "generic_pos": 0,
                "cluster_hits": 0,
                "readiness": "High risk",
            }

    generic_pos = sum(1 for p in POSITIVE if p in lower)
    course_track = st.session_state.profile.get("course_track") if "profile" in st.session_state else None
    cluster_hits = 0
    if course_track and course_track in COURSE_PROFILES:
        keywords = COURSE_PROFILES[course_track].get("keywords", [])
        cluster_hits = sum(1 for kw in keywords if kw.lower() in lower)

    wc = len(answer.split())
    score = 2
    if wc < 15:
        score = 2
    elif generic_pos >= 4 and wc >= 60:
        score = 5
    elif generic_pos >= 2 and wc >= 40:
        score = 4
    elif generic_pos >= 1 and wc >= 25:
        score = 3

    if cluster_hits >= 2 and score <= 4:
        score += 1
    elif cluster_hits == 1 and score <= 3:
        score += 1

    score = max(1, min(score, 5))
    feedback_map = {
        5: "Excellent — specific and aligned with the chosen course and goals.",
        4: "Good — add one more concrete detail to strengthen credibility.",
        3: "Average — answer is acceptable but still generic.",
        2: "Weak — too vague or incomplete.",
        1: "High risk — major credibility concerns detected.",
    }

    tip = "Mention relevant modules, course outcomes, and how they support your career."
    if course_track and course_track in COURSE_PROFILES:
        tip = COURSE_PROFILES[course_track]["extra_tip"]

    readiness_map = {5: "Low risk", 4: "Moderate risk", 3: "Moderate risk", 2: "Elevated risk", 1: "High risk"}
    return {
        "score": score,
        "feedback": feedback_map[score],
        "student_tip": tip,
        "risk_flags": [],
        "missing_points": ["More specific evidence"],
        "counsellor_note": "Fallback scoring used because OpenAI evaluation was unavailable.",
        "red_flag": False,
        "generic_pos": generic_pos,
        "cluster_hits": cluster_hits,
        "readiness": readiness_map[score],
    }


def evaluate_with_openai(answer_text: str, category: str, question: str, profile: dict) -> dict:
    system_prompt = """
You are evaluating a UK university pre-CAS interview response for counsellor review.
Return only valid JSON.
Score from 1 to 5.
Assess credibility, specificity, consistency with the student profile, and whether the answer sounds genuine and interview-ready.
Be stricter when the answer is generic and more positive when the answer is specific and relevant.
For institution choice, check whether the answer is meaningfully tied to the named university rather than sounding generic.
For course choice and course knowledge, check whether the answer is tied to the named course.
For finances, check clarity of sponsor/source/funds logic.
For future plans, flag risky migration intent.
Required JSON keys:
score, feedback, student_tip, risk_flags, missing_points, counsellor_note, red_flag, readiness
- score: integer 1-5
- feedback: short string for the student
- student_tip: short actionable improvement tip
- risk_flags: array of short strings
- missing_points: array of short strings
- counsellor_note: short note for counsellor
- red_flag: boolean
- readiness: one of Low risk, Moderate risk, Elevated risk, High risk
""".strip()

    user_payload = {
        "profile": {
            "name": profile.get("name", "Applicant"),
            "university": profile.get("university", ""),
            "course": profile.get("course", ""),
            "country": profile.get("country", ""),
            "experience": profile.get("experience", ""),
            "course_track": profile.get("course_track", ""),
        },
        "category": category,
        "question": question,
        "answer": answer_text,
        "evaluation_focus": {
            "institution_choice": "Check whether the answer is tailored to the named university or city.",
            "course_choice": "Check whether the answer links prior study/work to the exact course.",
            "course_knowledge": "Check whether modules, structure, or outcomes sound specific and plausible.",
            "finances": "Check whether funding explanation is clear, credible, and complete.",
            "future_plans": "Check whether the student clearly intends career progression and return/home-country logic.",
        },
    }

    response = client.responses.create(
        model="gpt-5-mini",
        input=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(user_payload)},
        ],
    )

    text = response.output_text.strip()
    data = json.loads(text)
    data["score"] = int(max(1, min(5, int(data.get("score", 2)))))
    data["risk_flags"] = data.get("risk_flags", []) or []
    data["missing_points"] = data.get("missing_points", []) or []
    data["red_flag"] = bool(data.get("red_flag", False))
    data["generic_pos"] = sum(1 for p in POSITIVE if p in answer_text.lower())

    course_track = profile.get("course_track")
    cluster_hits = 0
    if course_track and course_track in COURSE_PROFILES:
        keywords = COURSE_PROFILES[course_track].get("keywords", [])
        cluster_hits = sum(1 for kw in keywords if kw.lower() in answer_text.lower())
    data["cluster_hits"] = cluster_hits
    return data


def submit_current_answer(answer_text: str, idx: int):
    wc = len(answer_text.strip().split())
    if wc < st.session_state.get("min_words", 20):
        st.warning(
            f"Your answer is quite short ({wc} words). "
            f"Aim for at least {st.session_state.get('min_words', 20)} words."
        )

    try:
        result = evaluate_with_openai(
            answer_text=answer_text.strip(),
            category=st.session_state.current_category,
            question=st.session_state.current_question,
            profile=st.session_state.profile,
        )
    except Exception:
        result = fallback_score(answer_text.strip())

    st.success(f"Score: {result['score']}/5 — {result['feedback']}")
    st.info(f"Student tip: {result['student_tip']}")
    if result.get("risk_flags"):
        st.warning("Risk flags: " + ", ".join(result["risk_flags"]))

    st.session_state.scores.append(result["score"])
    st.session_state.log.append(
        {
            "Question #": idx + 1,
            "Category": st.session_state.current_category,
            "Question": st.session_state.current_question,
            "Answer": answer_text.strip(),
            "Score": result["score"],
            "Feedback": result["feedback"],
            "Student Tip": result["student_tip"],
            "Risk Flags": "; ".join(result.get("risk_flags", [])),
            "Missing Points": "; ".join(result.get("missing_points", [])),
            "Counsellor Note": result.get("counsellor_note", ""),
            "Readiness": result.get("readiness", "Moderate risk"),
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


with st.sidebar:
    st.header("👤 Applicant Profile")

    course_track = st.selectbox(
        "Course track (UK list)",
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

    total_sections = len(QUESTION_BANK)
    approx_minutes = total_sections * 3
    st.caption(
        f"Estimated interview duration: about {approx_minutes} minutes "
        f"({total_sections} categories, 1 question per category, ~3 minutes each)."
    )

    if start:
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.session_state.update(
            {
                "started": True,
                "completed": False,
                "question_sequence": build_one_question_per_category(),
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

    if st.session_state.get("started") and not st.session_state.get("completed"):
        remaining, t_str = time_left()
        st.caption(f"Time left this question: {t_str}")
        if remaining == 0:
            st.warning("Time is up for this question!")

st.title("Advisors Academy Pre-CAS Interview")
st_autorefresh(interval=1000, key="timer_refresh")
st.caption("Typed-response UK pre-CAS mock interview with OpenAI evaluation and counsellor reporting.")

with st.expander("How evaluation works"):
    st.markdown(
        """
        - Each typed answer is evaluated against the selected category, question, and applicant profile.
        - The app checks specificity, credibility, relevance to the named university/course, and risk signals.
        - A counsellor report is generated at the end with notes, missing points, and readiness bands.
        """
    )

if not st.session_state.get("started"):
    total_sections = len(QUESTION_BANK)
    approx_minutes = total_sections * 3
    st.info(
        f"Fill in the applicant profile on the left, then click 'Start Pre-CAS Interview'. "
        f"Estimated duration: about {approx_minutes} minutes for 1 question per category."
    )
else:
    if st.session_state.get("completed"):
        scores = st.session_state.scores
        avg = sum(scores) / len(scores) if scores else 0
        v = verdict(avg)
        risk = counsellor_risk(avg)

        st.subheader("📊 Pre-CAS Performance Summary")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Applicant", st.session_state.profile["name"])
        m2.metric("Questions", len(scores))
        m3.metric("Average Score", f"{avg:.1f} / 5")
        m4.metric("Verdict", v)

        df = pd.DataFrame(st.session_state.log)

        st.divider()
        st.subheader("Counsellor report")
        st.write(f"Overall counsellor risk band: **{risk}**")
        red_flag_count = int(df["Red Flag"].sum()) if not df.empty else 0
        st.write(f"Red-flagged responses: **{red_flag_count}**")

        category_summary = (
            df.groupby("Category", as_index=False)
            .agg(
                Average_Score=("Score", "mean"),
                Readiness=("Readiness", "last"),
                Red_Flags=("Red Flag", "sum"),
            )
        )
        st.dataframe(category_summary, use_container_width=True, hide_index=True)

        st.divider()
        st.subheader("Per-question review")
        st.dataframe(
            df[
                [
                    "Question #",
                    "Category",
                    "Score",
                    "Readiness",
                    "Feedback",
                    "Student Tip",
                    "Risk Flags",
                    "Missing Points",
                    "Counsellor Note",
                ]
            ],
            use_container_width=True,
            hide_index=True,
        )

        weak = df[df["Score"] <= 2]
        if not weak.empty:
            st.divider()
            st.subheader("Priority interventions")
            for _, row in weak.iterrows():
                with st.expander(f"Q{int(row['Question #'])} — {row['Category']} ({int(row['Score'])}/5)"):
                    st.write(f"**Question:** {row['Question']}")
                    st.write(f"**Answer:** {row['Answer']}")
                    st.error(f"**Feedback:** {row['Feedback']}")
                    st.info(f"**Student tip:** {row['Student Tip']}")
                    st.warning(f"**Missing points:** {row['Missing Points']}")
                    st.caption(f"Counsellor note: {row['Counsellor Note']}")

        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "⬇ Download Counsellor Report (CSV)",
            csv,
            "advisors_pre_cas_counsellor_report.csv",
            "text/csv",
        )

    else:
        categories = [item["category"] for item in st.session_state.question_sequence]
        idx = st.session_state.idx
        total_q = len(st.session_state.question_sequence)

        remaining, t_str = time_left()
        st.progress(idx / total_q, text=f"Question {idx + 1} of {total_q}")
        st.caption(f"Time left for this question: {t_str}")

        if remaining == 0:
            st.session_state.question_closed = True

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

            course_track = st.session_state.profile.get("course_track")
            if course_track and course_track in COURSE_PROFILES:
                cluster = COURSE_PROFILES[course_track]
                st.caption(
                    f"Course cluster hint ({course_track}): "
                    f"{cluster['extra_tip']} Example programmes include: {cluster['examples']}."
                )

            st.subheader("Type your answer")
            answer_key = f"answer_{idx}"
            answer_text = st.text_area(
                "Your answer",
                value=st.session_state.get(answer_key, ""),
                height=180,
                key=answer_key,
                placeholder="Type your answer here...",
                disabled=st.session_state.question_closed and not st.session_state.show_followup,
            )

            if remaining == 0 and not answer_text.strip():
                st.warning("Time is up and no answer was submitted for this question.")
                if not st.session_state.get("auto_advanced", False):
                    st.session_state.auto_advanced = True
                    st.session_state.scores.append(1)
                    st.session_state.log.append(
                        {
                            "Question #": idx + 1,
                            "Category": st.session_state.current_category,
                            "Question": st.session_state.current_question,
                            "Answer": "",
                            "Score": 1,
                            "Feedback": "No answer submitted before time expired.",
                            "Student Tip": "Give a direct answer within the time allowed.",
                            "Risk Flags": "No submission",
                            "Missing Points": "Direct response; supporting detail",
                            "Counsellor Note": "Student did not submit an answer within the time limit.",
                            "Readiness": "High risk",
                            "Red Flag": False,
                            "Generic Positives": 0,
                            "Cluster Hits": 0,
                        }
                    )
                    st.session_state.idx += 1
                    pick_question()
                    st.rerun()

            if not st.session_state.show_followup:
                if st.button("Submit Answer →", type="primary", use_container_width=True):
                    if not answer_text.strip():
                        st.warning("Please type an answer before submitting.")
                    else:
                        submit_current_answer(answer_text, idx)
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
                        submit_current_answer(follow, idx)
                    else:
                        st.warning("Please provide a sufficiently detailed follow-up (at least 20 words).")

        with right:
            st.markdown("### Time left")

            if remaining > 60:
                timer_color = "green"
            elif remaining > 30:
                timer_color = "orange"
            else:
                timer_color = "red"

            minutes, seconds = t_str.split(":")
            st.markdown(
                f"<h1 style='text-align: center; color: {timer_color};'>{minutes}:{seconds}</h1>",
                unsafe_allow_html=True,
            )

            if remaining <= 30 and remaining > 0:
                st.warning("Less than 30 seconds remaining for this question.")

            st.subheader("Live Scores")
            for i, sc in enumerate(st.session_state.scores):
                bar = "█" * sc + "░" * (5 - sc)
                cat = categories[i] if i < len(categories) else ""
                row = st.session_state.log[i]
                flag = " 🚩" if row.get("Red Flag") else ""
                st.markdown(f"`Q{i+1}` {bar} **{sc}/5**{flag}  \n_{cat}_")
                st.caption(f"Readiness: {row.get('Readiness', 'Moderate risk')}")

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
