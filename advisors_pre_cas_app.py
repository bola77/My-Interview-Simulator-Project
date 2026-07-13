import json
import random
import time
from pathlib import Path
from tempfile import NamedTemporaryFile

import pandas as pd
import streamlit as st
from openai import OpenAI
from audio_recorder_streamlit import audio_recorder

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
    .timer-box {
        border-radius: 16px;
        padding: 1rem 1.25rem;
        background: rgba(15, 23, 42, 0.04);
        text-align: center;
        margin-bottom: 1rem;
    }
    .timer-value {
        font-size: 3rem;
        font-weight: 800;
        line-height: 1;
        margin: 0;
    }
    .timer-label {
        font-size: 0.95rem;
        opacity: 0.75;
        margin-top: 0.4rem;
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
MAX_VOICE_ATTEMPTS = 3

COURSE_PROFILES = {
    "UG – Business & Management": {
        "examples": "Business Administration; Accounting & Finance; Marketing; International Business",
        "extra_tip": "Mention business modules like finance, marketing, or strategy and explain how they fit your career plan.",
        "keywords": ["marketing", "finance", "accounting", "strategy", "international business"],
    },
}

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])


def init_session_state():
    defaults = {
        "started": False,
        "completed": False,
        "categories": [],
        "idx": 0,
        "scores": [],
        "log": [],
        "show_followup": False,
        "profile": {},
        "think_time": DEFAULT_THINK_TIME,
        "hint_mode": DEFAULT_HINT_MODE,
        "min_words": DEFAULT_MIN_WORDS,
        "current_category": "",
        "current_question": "",
        "question_start": None,
        "voice_attempts": [],
        "last_result": None,
        "question_expired": False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def reset_interview_state():
    keys_to_clear = [
        "started",
        "completed",
        "categories",
        "idx",
        "scores",
        "log",
        "show_followup",
        "profile",
        "think_time",
        "hint_mode",
        "min_words",
        "current_category",
        "current_question",
        "question_start",
        "voice_attempts",
        "last_result",
        "question_expired",
    ]
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]
    init_session_state()


def transcribe_audio_bytes(audio_bytes: bytes) -> str:
    with NamedTemporaryFile(delete=True, suffix=".wav") as temp_file:
        temp_file.write(audio_bytes)
        temp_file.flush()
        with open(temp_file.name, "rb") as audio_file:
            response = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
            )
    return response.text


def pick_question():
    idx = st.session_state.idx
    if idx >= len(st.session_state.categories):
        st.session_state.completed = True
        return
    cat = st.session_state.categories[idx]
    st.session_state.current_category = cat
    st.session_state.current_question = random.choice(QUESTION_BANK[cat])
    st.session_state.show_followup = False
    st.session_state.question_start = time.time()
    st.session_state.voice_attempts = []
    st.session_state.question_expired = False


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
    course_track = st.session_state.profile.get("course_track") if st.session_state.profile else None
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

    category = st.session_state.get("current_category", "")
    student_tip = ANSWER_TIPS.get(category, ANSWER_TIPS["default"])

    return {
        "score": score,
        "feedback": feedback_map[score],
        "student_tip": student_tip,
        "risk_flags": [],
        "missing_points": ["More specific evidence"],
        "counsellor_note": "Fallback scoring used because OpenAI evaluation was unavailable.",
        "red_flag": False,
        "generic_pos": generic_pos,
        "cluster_hits": cluster_hits,
        "readiness": {5: "Low risk", 4: "Moderate risk", 3: "Moderate risk", 2: "Elevated risk", 1: "High risk"}[score],
    }


def evaluate_with_openai(answer_text: str, category: str, question: str, profile: dict) -> dict:
    prompt = {
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
        "instructions": {
            "goal": "Evaluate a UK pre-CAS interview answer for counsellor review.",
            "institution_choice": "Check whether the answer is genuinely tailored to the named university or city.",
            "course_choice": "Check whether the answer links prior study/work to the exact course.",
            "course_knowledge": "Check whether modules, structure, or outcomes sound specific and plausible.",
            "finances": "Check whether funding explanation is clear, credible, and complete.",
            "future_plans": "Check whether the student shows credible return or career logic and avoids risky migration intent.",
        },
    }

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": (
                    "You are evaluating a UK university pre-CAS interview response. "
                    "Return only valid JSON with these keys exactly: "
                    "score, feedback, student_tip, risk_flags, missing_points, "
                    "counsellor_note, red_flag, readiness. "
                    "score must be an integer from 1 to 5. "
                    "risk_flags and missing_points must be arrays of short strings. "
                    "red_flag must be true or false. "
                    "readiness must be one of: Low risk, Moderate risk, Elevated risk, High risk."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(prompt),
            },
        ],
    )

    raw = response.choices[0].message.content
    if not raw:
        raise ValueError("OpenAI returned empty content.")

    try:
        data = json.loads(raw)
    except Exception as e:
        raise ValueError(f"Invalid JSON from OpenAI: {raw[:300]}") from e

    data["score"] = int(max(1, min(5, int(data.get("score", 2)))))
    data["feedback"] = str(data.get("feedback", "Response evaluated."))
    data["student_tip"] = str(data.get("student_tip", ANSWER_TIPS.get(category, ANSWER_TIPS["default"])))
    data["risk_flags"] = data.get("risk_flags", []) or []
    data["missing_points"] = data.get("missing_points", []) or []
    data["counsellor_note"] = str(data.get("counsellor_note", ""))
    data["red_flag"] = bool(data.get("red_flag", False))
    data["readiness"] = str(data.get("readiness", "Moderate risk"))

    valid_readiness = {"Low risk", "Moderate risk", "Elevated risk", "High risk"}
    if data["readiness"] not in valid_readiness:
        data["readiness"] = "Moderate risk"

    data["generic_pos"] = sum(1 for p in POSITIVE if p in answer_text.lower())

    course_track = profile.get("course_track")
    cluster_hits = 0
    if course_track and course_track in COURSE_PROFILES:
        keywords = COURSE_PROFILES[course_track].get("keywords", [])
        cluster_hits = sum(1 for kw in keywords if kw.lower() in answer_text.lower())
    data["cluster_hits"] = cluster_hits

    return data


def countdown_box(seconds: int, label: str = "Next question"):
    box = st.empty()
    for s in range(seconds, 0, -1):
        box.warning(f"{label} in {s} second{'s' if s != 1 else ''}...")
        time.sleep(1)
    box.empty()


def time_left():
    start = st.session_state.get("question_start")
    if not start:
        return QUESTION_TIME_SECONDS, f"{QUESTION_TIME_SECONDS // 60:02d}:00"
    elapsed = time.time() - start
    remaining = max(0, int(QUESTION_TIME_SECONDS - elapsed))
    minutes = remaining // 60
    seconds = remaining % 60
    return remaining, f"{minutes:02d}:{seconds:02d}"


def timer_component(remaining_seconds: int):
    color = "#15803d" if remaining_seconds > 60 else "#d97706" if remaining_seconds > 30 else "#dc2626"
    st.components.v1.html(
        f"""
        <div class="timer-box">
            <div id="timer" class="timer-value" style="color:{color};"></div>
            <div class="timer-label">Time left</div>
        </div>
        <script>
        const end = Date.now() + ({remaining_seconds} * 1000);
        const el = document.getElementById('timer');
        function format(sec) {{
            const m = String(Math.floor(sec / 60)).padStart(2, '0');
            const s = String(sec % 60).padStart(2, '0');
            return `${{m}}:${{s}}`;
        }}
        function tick() {{
            const left = Math.max(0, Math.floor((end - Date.now()) / 1000));
            el.textContent = format(left);
            if (left <= 0) clearInterval(window.__aaTimerInterval);
        }}
        tick();
        if (window.__aaTimerInterval) clearInterval(window.__aaTimerInterval);
        window.__aaTimerInterval = setInterval(tick, 1000);
        </script>
        """,
        height=140,
    )


def submit_answer(answer_text: str, idx: int):
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
        st.caption("OpenAI evaluation used.")
    except Exception as e:
        st.warning(f"OpenAI evaluation failed, using fallback scoring. Error: {e}")
        result = fallback_score(answer_text.strip())

    st.success(f"Score: {result['score']}/5 — {result['feedback']}")
    st.info(f"Student tip: {result['student_tip']}")
    st.caption(
        f"Signals detected: {result.get('generic_pos', 0)} generic positives, "
        f"{result.get('cluster_hits', 0)} course-cluster keywords."
    )

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


init_session_state()

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
        reset = st.button("Reset Session", use_container_width=True)

    if reset:
        reset_interview_state()
        st.rerun()

    total_sections = len(QUESTION_BANK)
    approx_minutes = total_sections * 3
    st.caption(
        f"Estimated interview duration: about {approx_minutes} minutes "
        f"({total_sections} categories, 1 question per category, ~3 minutes each)."
    )

    if start:
        reset_interview_state()
        cats = list(QUESTION_BANK.keys())
        random.shuffle(cats)
        st.session_state.started = True
        st.session_state.completed = False
        st.session_state.categories = cats
        st.session_state.idx = 0
        st.session_state.scores = []
        st.session_state.log = []
        st.session_state.show_followup = False
        st.session_state.profile = {
            "name": s_name or "Applicant",
            "university": s_university or "your university",
            "course": s_course or "your course",
            "country": s_country or "Nigeria",
            "experience": s_experience or "",
            "course_track": course_track,
        }
        st.session_state.think_time = DEFAULT_THINK_TIME
        st.session_state.hint_mode = DEFAULT_HINT_MODE
        st.session_state.min_words = DEFAULT_MIN_WORDS
        pick_question()
        st.rerun()

    if st.session_state.started and not st.session_state.completed:
        remaining, t_str = time_left()
        st.caption(f"Time left this question: {t_str}")
        if remaining == 0:
            st.warning("Time is up for this question!")

st.title("Advisors Academy Pre-CAS Interview")
st.caption("Practice realistic UK university Pre-CAS questions with OpenAI-backed evaluation.")

with st.expander("How your answers are scored"):
    st.markdown(
        """
**Score meanings**

- 5/5 – Excellent: clear, specific, and aligned with your UK course and career plan.
- 4/5 – Good: strong answer; add one more concrete detail.
- 3/5 – Average: basically correct but still generic.
- 2/5 – Weak: vague or incomplete.
- 1/5 – High risk: unclear or risky language.

**What the system checks**

1. Structure and clarity.
2. Relevance to the question category.
3. Specificity about university, course, finance, accommodation, background, or future plans.
        """
    )

if not st.session_state.started:
    st.info(
        f"Fill in the applicant profile on the left, then click 'Start Pre-CAS Interview'. "
        f"Estimated duration: about {approx_minutes} minutes."
    )
else:
    if st.session_state.completed:
        scores = st.session_state.scores
        avg = sum(scores) / len(scores) if scores else 0
        v = verdict(avg)

        st.subheader("📊 Pre-CAS Performance Summary")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Applicant", st.session_state.profile.get("name", "Applicant"))
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
                    "Student Tip",
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
                    st.info(f"**Student tip:** {row['Student Tip']}")

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

        remaining, t_str = time_left()
        st.progress(idx / total_q if total_q else 0, text=f"Question {idx + 1} of {total_q}")
        st.caption(f"Server timer snapshot: {t_str}")

        if remaining == 0:
            st.session_state.question_expired = True

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

            if "voice_attempts" not in st.session_state:
                st.session_state.voice_attempts = []

            st.subheader("Record your answer")
            current_attempts = len(st.session_state.voice_attempts)
            if current_attempts > 0:
                st.caption(f"{current_attempts} recorded attempt(s). Maximum allowed: {MAX_VOICE_ATTEMPTS}.")

            if current_attempts < MAX_VOICE_ATTEMPTS and remaining > 0:
                audio_bytes = audio_recorder(pause_threshold=30)
                if audio_bytes:
                    st.audio(audio_bytes, format="audio/wav")
                    if st.button("Transcribe this recording"):
                        with st.spinner("Transcribing..."):
                            text_ans = transcribe_audio_bytes(audio_bytes)
                        st.session_state.voice_attempts.append({"audio": audio_bytes, "text": text_ans})
                        st.success("Recording transcribed. This will be used as your answer.")
                        st.rerun()
            else:
                if remaining == 0:
                    st.warning("Time is up for this question. No new recordings allowed.")
                elif current_attempts >= MAX_VOICE_ATTEMPTS:
                    st.warning("You have reached the maximum of 3 voice attempts for this question.")

            if st.session_state.voice_attempts:
                latest_text = st.session_state.voice_attempts[-1]["text"]
                st.text_area("Latest transcript", latest_text, height=180, disabled=True)

            if remaining == 0 and not st.session_state.voice_attempts and not st.session_state.question_expired:
                st.session_state.question_expired = True

            if not st.session_state.show_followup:
                if st.button("Submit Answer →", type="primary", use_container_width=True):
                    if not st.session_state.voice_attempts:
                        st.warning("Please record and transcribe an answer before submitting.")
                    else:
                        answer_text = st.session_state.voice_attempts[-1]["text"]
                        submit_answer(answer_text, idx)
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
                        submit_answer(follow, idx)
                    else:
                        st.warning("Please provide a sufficiently detailed follow-up (at least 20 words).")

        with right:
            st.subheader("Live Timer")
            timer_component(remaining)
            if remaining <= 30 and remaining > 0:
                st.warning("Less than 30 seconds remaining for this question.")
            if remaining == 0:
                st.error("Time is up. Submit is disabled until next rerun action.")

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
            st.markdown(f"👤 **{p.get('name', 'Applicant')}**")
            st.markdown(f"🎓 {p.get('course', '')}")
            st.markdown(f"🏫 {p.get('university', '')}")
            st.markdown(f"🌍 {p.get('country', '')}")
            if p.get("experience"):
                st.markdown(f"💼 {p['experience']}")
            if p.get("course_track"):
                st.markdown(f"📚 Track: {p['course_track']}")
