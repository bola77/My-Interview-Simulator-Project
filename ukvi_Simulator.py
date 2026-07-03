import random
import json
import streamlit as st
import pandas as pd
import requests

st.set_page_config(page_title="UKVI Interview Simulator", page_icon="🎓", layout="wide")

OLLAMA_URL = "http://localhost:11434/api/chat"

OPEN_SOURCE_MODELS = [
    "llama3.2", "llama3.1", "mistral", "mistral-nemo",
    "gemma2", "gemma3", "phi4", "qwen2.5", "deepseek-r1",
]

QUESTION_BANK = {
    "Why UK": [
        "Why have you chosen to study in the UK rather than your home country or another destination like the US or Canada?",
        "The costs of studying in the UK are higher than in your home country. Why incur these extra costs?",
        "Have you considered studying in other countries? Why did you not choose them?",
    ],
    "Why University": [
        "Why did you choose this university over others in the UK?",
        "What do you know about the city or area where your university is located?",
        "What facilities or resources at this university are relevant to your course?",
    ],
    "Why Course": [
        "Why did you choose this specific course?",
        "How does this course relate to your previous education or work experience?",
        "How will this course help you achieve your long-term career goals?",
    ],
    "Course Knowledge": [
        "What are the names or topics of some modules you will study?",
        "How long does your course last and how is it structured?",
        "How will your course be assessed — exams, coursework, dissertation?",
    ],
    "Financial Circumstances": [
        "How do you plan to pay for your tuition fees and living expenses in the UK?",
        "Who is financing your studies and what is the source of those funds?",
        "What is the approximate total cost of your studies including living expenses?",
    ],
    "Accommodation & Logistics": [
        "Where will you be living while studying in the UK?",
        "How will you travel from your accommodation to campus?",
        "Do you know the monthly cost of accommodation in the area?",
    ],
    "Academic & Personal Background": [
        "Where have you studied previously and what qualifications did you obtain?",
        "Can you explain any gaps in your study or employment history?",
        "Have you ever been refused a visa for the UK or any other country?",
    ],
    "Future Plans": [
        "What do you plan to do after completing your course?",
        "Do you intend to return to your home country after your studies?",
        "What specific job roles are you targeting after graduation?",
    ],
}

FOLLOW_UPS = {
    "Why UK": "Can you be more specific about why the UK suits your career goals compared to Canada or Australia?",
    "Why University": "What do you know about the specific strengths of your department or research environment?",
    "Why Course": "How exactly does this course connect to your previous experience and qualifications?",
    "Course Knowledge": "Can you name at least two specific modules and explain what they cover?",
    "Financial Circumstances": "Can you explain the exact source of the funds and how long they have been held?",
    "Accommodation & Logistics": "Have you actually confirmed accommodation, or is this still under consideration?",
    "Academic & Personal Background": "What were you doing between finishing your previous study and applying for this course?",
    "Future Plans": "What specific role will you return to in your home country and which organisation are you targeting?",
}

QUESTION_HINTS = {
    "Why UK": "State 1-2 concrete reasons: course structure, recognition, registration route, or proximity.",
    "Why University": "Mention a specific feature: module, ranking, location, placement, or teaching style.",
    "Why Course": "Link the course to your previous study, work experience, and career goal.",
    "Course Knowledge": "Name at least one module, assessment method, or professional outcome.",
    "Financial Circumstances": "Explain the funding source, amount, and evidence clearly.",
    "Accommodation & Logistics": "Say where you will live, cost, and how you will commute.",
    "Academic & Personal Background": "Give a short timeline and explain any gaps honestly.",
    "Future Plans": "State your post-study plan and how the course helps you return home or progress professionally.",
}

def pick_question():
    idx = st.session_state.idx
    if idx >= len(st.session_state.categories):
        st.session_state.completed = True
        return
    cat = st.session_state.categories[idx]
    st.session_state.current_category = cat
    st.session_state.current_question = random.choice(QUESTION_BANK[cat])
    st.session_state.show_followup = False

def verdict(avg):
    if avg >= 4.5: return "✅ Likely to Pass"
    if avg >= 3.5: return "🟡 Borderline Pass"
    if avg >= 2.5: return "🟠 At Risk"
    return "🔴 High Risk of Refusal"

def check_ollama(model):
    try:
        r = requests.post(
            OLLAMA_URL,
            json={"model": model, "messages": [{"role": "user", "content": "hi"}], "stream": False},
            timeout=8
        )
        return r.status_code == 200
    except:
        return False

def fallback_score(answer, error=""):
    RED_FLAGS = ["i don't know", "not sure", "my agent", "i haven't researched",
                 "i plan to stay", "might not return", "i just want"]
    POSITIVE = ["because", "specifically", "nmc", "nclex", "osce", "module",
                "dissertation", "band", "nhs", "clinical", "return", "sponsor",
                "tuition", "i researched", "accredited", "career", "back home"]
    lower = answer.lower()
    for f in RED_FLAGS:
        if f in lower:
            return {
                "score": 1,
                "feedback": f"Red flag: '{f}' detected.",
                "tip": "Remove immigration-focused language.",
                "red_flag": True
            }
    pos = sum(1 for p in POSITIVE if p in lower)
    wc = len(answer.split())
    s = 2
    if wc < 15:
        s = 2
    elif pos >= 4 and wc >= 60:
        s = 5
    elif pos >= 2 and wc >= 40:
        s = 4
    elif pos >= 1 and wc >= 25:
        s = 3
    msgs = {
        5: "Excellent.",
        4: "Good — add specifics.",
        3: "Average — needs depth.",
        2: "Weak — too vague."
    }
    note = f" (Keyword fallback{': ' + error if error else ''})"
    return {
        "score": s,
        "feedback": msgs[s] + note,
        "tip": "Add module names, licensing exams, and career goals.",
        "red_flag": False
    }

def ollama_score(question, answer, category, profile, model):
    system_prompt = f"""You are a strict UKVI immigration officer conducting a student visa credibility interview.

Applicant profile:
- Name: {profile['name']}
- University: {profile['university']}
- Course: {profile['course']}
- Home Country: {profile['country']}
- Experience: {profile['experience']}
-Previous Qualification: {profile.get('previous_qualification', '')}
- Work Experience: {profile.get('experience', '')}
- Career Goal: {profile.get('career_goal', '')}

Score the answer 1-5:
5 – Excellent: Excellent: directly answers the question, specific, natural, consistent with the profile, and shows genuine intent.
4 – Good: clear and relevant but missing some specifics
3 – Average: answers the question but lacks depth
2 – Weak: vague, generic, or inconsistent with profile
1 – Poor: contains red flags (immigration focus, "I don't know", relies on agent, no return plan)

Return ONLY valid JSON — no markdown, no code fences:
{{"score": <1-5>, "feedback": "<one sentence>", "tip": "<one actionable tip>", "red_flag": <true|false>}}"""

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Category: {category}\nQuestion: {question}\nAnswer: {answer}"},
        ],
        "stream": False,
        "options": {"temperature": 0.2},
    }

    try:
        resp = requests.post(OLLAMA_URL, json=payload, timeout=60)
        resp.raise_for_status()
        content = resp.json()["message"]["content"].strip()
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        return json.loads(content)
    except Exception as e:
        return fallback_score(answer, str(e))

with st.sidebar:
    st.header("🤖 LLM Engine")
    engine = st.radio("Scoring engine", ["Ollama (local)", "Keyword fallback (offline)"])
    selected_model = st.selectbox("Model", OPEN_SOURCE_MODELS, index=0) if engine == "Ollama (local)" else None
    think_time = st.slider("Thinking time before next question (sec)", 0, 10, 3)
    hint_mode = st.checkbox("Show answer coaching hints", value=True)
    min_words = st.slider("Minimum answer words", 5, 60, 20)

    if engine == "Ollama (local)":
        if st.button("🔌 Test connection"):
            if check_ollama(selected_model):
                st.success(f"✅ Connected to {selected_model}")
            else:
                st.error("❌ Cannot reach Ollama. Is it running? Run: ollama serve")
        with st.expander("How to install Ollama"):
            st.markdown("""
1. Download from [ollama.com](https://ollama.com)
2. Run `ollama serve` in terminal
3. Pull a model: `ollama pull llama3.2`
4. Click **Test connection** above
""")

    st.divider()
    st.header("👤 Student Profile")
    s_name = st.text_input("Full Name")
    s_university = st.text_input("University")
    s_course = st.text_input("Course")
    s_country = st.text_input("Home Country", value="Nigeria")
    s_experience = st.text_input("Experience", placeholder="e.g. 2 years clinical nursing")

    c1, c2 = st.columns(2)
    with c1:
        start = st.button("▶ Start", use_container_width=True, type="primary")
    with c2:
        if st.button("↺ Reset", use_container_width=True):
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.rerun()

    if start:
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        cats = list(QUESTION_BANK.keys())
        random.shuffle(cats)
        st.session_state.update({
            "started": True,
            "completed": False,
            "categories": cats,
            "idx": 0,
            "scores": [],
            "log": [],
            "show_followup": False,
            "engine": engine,
            "model": selected_model,
            "profile": {
                "name": s_name or "Applicant",
                "university": s_university or "your university",
                "course": s_course or "your course",
                "country": s_country or "Nigeria",
                "experience": s_experience or "",
            },
            "think_time": think_time,
            "hint_mode": hint_mode,
            "min_words": min_words,
        })
        pick_question()
        st.rerun()

st.title("🎓 UKVI Credibility Interview Simulator")
st.caption("Open-source AI scoring via Ollama | Prime Crown Consulting")

if not st.session_state.get("started"):
    st.info("Configure the LLM engine and student profile in the sidebar, then click ▶ Start.")
    col1, col2, col3 = st.columns(3)
    col1.markdown("#### 🦙 Llama 3.2\nMeta's fast, instruction-tuned model. Excellent for structured JSON output.")
    col2.markdown("#### 🌀 Mistral\nStrong European open-source model. Great for nuanced credibility evaluation.")
    col3.markdown("#### 🔷 Phi-4\nMicrosoft's compact but powerful reasoning model. Fast and efficient.")
    st.markdown("---")
    st.markdown("All models run **100% locally** via Ollama — no API keys, no data leaves your machine.")

elif st.session_state.get("completed"):
    scores = st.session_state.scores
    avg = sum(scores) / len(scores) if scores else 0
    v = verdict(avg)

    st.subheader("📊 Performance Report")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Applicant", st.session_state.profile["name"])
    m2.metric("Questions", len(scores))
    m3.metric("Average Score", f"{avg:.1f} / 5")
    m4.metric("Verdict", v)

    df = pd.DataFrame(st.session_state.log)
    st.divider()
    st.dataframe(df[["Question #", "Category", "Score", "Feedback", "Tip"]],
                 use_container_width=True, hide_index=True)

    weak = df[df["Score"] <= 2]
    if not weak.empty:
        st.divider()
        st.subheader("⚠️ Areas Requiring Improvement")
        for _, row in weak.iterrows():
            with st.expander(f"Q{int(row['Question #'])} — {row['Category']} ({int(row['Score'])}/5)"):
                st.write(f"**Question:** {row['Question']}")
                st.write(f"**Answer:** {row['Answer']}")
                st.error(f"**Feedback:** {row['Feedback']}")
                st.info(f"**Tip:** {row['Tip']}")

    st.divider()
    st.subheader("📋 General Tips")
    for tip in [
        "Name specific modules and link them to your career goals.",
        "Prepare a financial narrative: source → amount → 28-day rule → total cost.",
        "Know your university city, transport links, and nearest NHS trust.",
        "Mention the licensing exam by name — NMC CBT + OSCE for UK nurses.",
        "Close every future-plans answer with a clear return intention.",
        "Avoid any phrase suggesting long-term settlement intent.",
    ]:
        st.write(f"- {tip}")

    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button("⬇ Download Report (CSV)", csv, "ukvi_report.csv", "text/csv")

else:
    categories = st.session_state.categories
    idx = st.session_state.idx
    total_q = len(categories)

    st.progress(idx / total_q, text=f"Question {idx + 1} of {total_q}")

    left, right = st.columns([2, 1])

    with left:
        st.markdown(f"**Category:** `{st.session_state.current_category}`")
        st.markdown(f"### {st.session_state.current_question}")

        if st.session_state.get("hint_mode", True):
            st.info(QUESTION_HINTS.get(st.session_state.current_category, "Give a clear, specific answer."))

        if not st.session_state.show_followup:
            answer = st.text_area(
                "Your answer",
                height=170,
                key=f"ans_{idx}",
                placeholder="Be specific, personal, and clear — as you would in the real interview."
            )
            if st.button("Submit Answer →", type="primary", use_container_width=True):
                if answer.strip():
                    wc = len(answer.strip().split())
                    if wc < st.session_state.get("min_words", 20):
                        st.warning(
                            f"Your answer is too short ({wc} words). "
                            f"Aim for at least {st.session_state.get('min_words', 20)} words."
                        )
                    with st.spinner("Officer is evaluating your response…"):
                        if st.session_state.engine == "Ollama (local)" and st.session_state.model:
                            result = ollama_score(
                                st.session_state.current_question,
                                answer.strip(),
                                st.session_state.current_category,
                                st.session_state.profile,
                                st.session_state.model,
                            )
                        else:
                            result = fallback_score(answer.strip())

                    st.session_state.scores.append(result["score"])
                    st.session_state.log.append({
                        "Question #": idx + 1,
                        "Category": st.session_state.current_category,
                        "Question": st.session_state.current_question,
                        "Answer": answer.strip(),
                        "Score": result["score"],
                        "Feedback": result["feedback"],
                        "Tip": result["tip"],
                        "Red Flag": result.get("red_flag", False),
                    })

                    if result["score"] <= 2:
                        st.session_state.show_followup = True
                        st.session_state.last_result = result
                    else:
                        if st.session_state.get("think_time", 0) > 0:
                            import time
                            time.sleep(st.session_state.get("think_time", 0))
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
                placeholder="Provide more specific details to recover credibility…"
            )
            if st.button("Submit Follow-up →", type="primary", use_container_width=True):
                if follow.strip() and len(follow.split()) >= 20:
                    new_score = min(r["score"] + 1, 4)
                    st.session_state.scores[-1] = new_score
                    st.session_state.log[-1].update({
                        "Score": new_score,
                        "Feedback": "Follow-up accepted — credibility partially recovered."
                    })
                st.session_state.show_followup = False
                st.session_state.idx += 1
                pick_question()
                st.rerun()

    with right:
        st.subheader("Live Scores")
        for i, sc in enumerate(st.session_state.scores):
            bar = "█" * sc + "░" * (5 - sc)
            cat = categories[i] if i < len(categories) else ""
            flag = " 🚩" if st.session_state.log[i].get("Red Flag") else ""
            st.markdown(f"`Q{i+1}` {bar} **{sc}/5**{flag}  \n_{cat}_")

        st.divider()
        p = st.session_state.profile
        st.markdown(f"👤 **{p['name']}**")
        st.markdown(f"🎓 {p['course']}")
        st.markdown(f"🏫 {p['university']}")
        st.markdown(f"🌍 {p['country']}")
        if p["experience"]:
            st.markdown(f"💼 {p['experience']}")
        st.divider()
        model_label = st.session_state.model or "Keyword fallback"
        st.caption(f"Engine: {st.session_state.engine}  \nModel: {model_label}")